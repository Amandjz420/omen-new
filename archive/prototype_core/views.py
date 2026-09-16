import json
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from core.models import Office, Contact, Lead, Case, ImportBatch, LeadNote


def staff_api(fn):
    @wraps(fn)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Sign in to continue'}, status=401)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Staff access is required for this migration preview'}, status=403)
        return fn(request, *args, **kwargs)
    return wrapped


def body(request):
    try:
        value = json.loads(request.body)
        return value if isinstance(value, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


@require_GET
def session(request):
    return JsonResponse({'csrf': get_token(request), 'username': request.user.get_username() if request.user.is_authenticated else None,
                         'staff': request.user.is_authenticated and request.user.is_staff})


@require_POST
def sign_in(request):
    data = body(request)
    if not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
        return JsonResponse({'error': 'Enter your username and password'}, status=400)
    user = authenticate(request, username=data['username'], password=data['password'])
    if user is None or not user.is_staff:
        return JsonResponse({'error': 'Invalid staff credentials'}, status=401)
    login(request, user)
    return JsonResponse({'username': user.username, 'staff': True, 'csrf': get_token(request)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})


def page(request, qs, serialize):
    try:
        number = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        return JsonResponse({'error': 'page must be an integer'}, status=400)
    count = qs.count()
    return JsonResponse({'count': count, 'page': number, 'page_size': 30,
                         'results': [serialize(r) for r in qs[(number - 1)*30:number*30]]})


def office_json(obj):
    return {'id': obj.id, 'source_id': obj.source_id, 'name': obj.name, 'branch': obj.branch,
            'bank': obj.bank.name if obj.bank else None, 'state': obj.raw.get('state_name'),
            'district': obj.raw.get('district_name'), 'issues': obj.issues}


def lead_json(obj):
    return {'id': obj.id, 'source_id': obj.source_id, 'number': obj.number, 'status': obj.status,
            'status_label': {'1': 'New lead', '2': 'In process', '3': 'Cancelled', '4': 'Closed (legacy)'}.get(obj.status, 'Unknown'),
            'received_date': obj.received_date, 'office': office_json(obj.office) if obj.office else None,
            'issues': obj.issues}


@require_GET
@staff_api
def offices(request):
    qs = Office.objects.select_related('bank').order_by('name', 'id')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(branch__icontains=q) | Q(source_id=q))
    return page(request, qs, office_json)


@require_GET
@staff_api
def leads(request):
    qs = Lead.objects.select_related('office__bank').order_by('-received_date', '-id')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(office__name__icontains=q) | Q(source_id=q))
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    return page(request, qs, lead_json)


@require_http_methods(['GET', 'POST'])
@staff_api
def lead_detail(request, pk):
    obj = Lead.objects.select_related('office__bank', 'contact').filter(pk=pk).first()
    if obj is None:
        return JsonResponse({'error': 'Lead not found'}, status=404)
    if request.method == 'POST':
        note = body(request).get('body')
        if not isinstance(note, str) or not note.strip() or len(note) > 4000:
            return JsonResponse({'error': 'Write a note between 1 and 4,000 characters'}, status=400)
        LeadNote.objects.create(lead=obj, author=request.user, body=note.strip())
    result = lead_json(obj)
    result['contact'] = {'name': obj.contact.name, 'phone': obj.contact.raw.get('mobile_no')} if obj.contact else None
    result['cases'] = list(obj.cases.order_by('id').values('source_id', 'service', 'subtype', 'district', 'issues'))
    result['notes'] = list(obj.notes.order_by('-created_at').values('id', 'body', 'created_at', 'author__username'))
    return JsonResponse(result, status=201 if request.method == 'POST' else 200)


@require_GET
@staff_api
def summary(request):
    year = request.GET.get('year')
    qs = Case.objects.all()
    if year:
        try:
            year = int(year)
            if not 1900 <= year <= 9998:
                raise ValueError()
            qs = qs.filter(lead__received_date__gte=f'{year}-04-01', lead__received_date__lt=f'{year+1}-04-01')
        except ValueError:
            return JsonResponse({'error': 'year must be the financial-year start, e.g. 2026'}, status=400)
    latest = ImportBatch.objects.order_by('-id').first()
    return JsonResponse({'offices': Office.objects.count(), 'leads': Lead.objects.count(), 'contacts': Contact.objects.count(),
                         'cases': qs.count(), 'unlinked_cases': qs.filter(lead__isnull=True).count(),
                         'services': list(qs.values('service').annotate(count=Count('id')).order_by('-count')),
                         'policy': 'Recorded cases, all source statuses retained. Dates use the lead-entry proxy.',
                         'latest_import': {'created_at': latest.created_at, 'summary': latest.summary} if latest else None})
