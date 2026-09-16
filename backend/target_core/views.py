import json
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from target_core.models import ClientOffice as Office, Contact, Lead, Case, ImportBatch, LeadNote, SourceIdentity, SourceRow, MigrationIssue
from target_core.sync import source_key


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
    rows=list(qs[(number - 1)*30:number*30])
    references=source_references(rows+[r.office for r in rows if isinstance(r,Lead) and r.office])
    return JsonResponse({'count': count, 'page': number, 'page_size': 30,
                         'results': [serialize(r,references) for r in rows]})


def source_references(objects):
    return {r.target_id:json.loads(r.key)[0][1] for r in SourceIdentity.objects.filter(environment='main',target_id__in=[o.id for o in objects])}


def office_json(obj,references):
    return {'id': obj.id, 'source_id': references.get(obj.id), 'name': obj.name, 'branch': obj.branch_name,
            'bank': obj.bank.name if obj.bank else None, 'state': obj.state,
            'district': obj.district, 'issues': []}


def lead_json(obj,references):
    return {'id': obj.id, 'source_id': references.get(obj.id), 'number': obj.number, 'status': obj.legacy_status,
            'status_label': {'1': 'New lead', '2': 'In process', '3': 'Cancelled', '4': 'Closed (legacy)'}.get(obj.legacy_status, 'Unknown'),
            'received_date': obj.received_date, 'office': office_json(obj.office,references), 'issues': []}


@require_GET
@staff_api
def offices(request):
    qs = Office.objects.select_related('bank').order_by('name', 'id')
    q = request.GET.get('q', '').strip()
    if q:
        ids=SourceIdentity.objects.filter(target_model=Office._meta.label,environment='main',key=source_key(q)).values('target_id')
        qs = qs.filter(Q(name__icontains=q) | Q(branch_name__icontains=q) | Q(id__in=ids))
    return page(request, qs, office_json)


@require_GET
@staff_api
def leads(request):
    qs = Lead.objects.select_related('office__bank').order_by('-received_date', '-id')
    q = request.GET.get('q', '').strip()
    if q:
        ids=SourceIdentity.objects.filter(target_model=Lead._meta.label,environment='main',key=source_key(q)).values('target_id')
        qs = qs.filter(Q(number__icontains=q) | Q(office__name__icontains=q) | Q(id__in=ids))
    if request.GET.get('status'):
        qs = qs.filter(legacy_status=request.GET['status'])
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
    cases=list(obj.case_set.select_related('service','subtype').order_by('id'))
    references=source_references([obj,obj.office,*cases])
    result = lead_json(obj,references)
    source=SourceIdentity.objects.filter(target_model=Lead._meta.label,target_id=obj.id).first()
    if source:
        stage=SourceRow.objects.filter(schema=source.schema,table=source.table,key=source.key).first()
        result['issues']=stage.problems if stage else []
    result['contact'] = {'name': obj.contact.name, 'phone': obj.contact.phone} if obj.contact else None
    result['cases'] = [{'id':c.id,'source_id':references.get(c.id),'service':c.service.name,
                       'subtype':c.subtype.name if c.subtype else None,'district':c.asset_district,'issues':[]} for c in cases]
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
    latest = ImportBatch.objects.filter(status__startswith='completed',conversion_version__startswith='mysql-target').order_by('-created_at').first()
    services=[{'service':r['service__name'],'count':r['count']} for r in qs.values('service__name').annotate(count=Count('id')).order_by('-count')]
    return JsonResponse({'offices': Office.objects.count(), 'leads': Lead.objects.count(), 'contacts': Contact.objects.count(),
                         'cases': qs.count(), 'unlinked_cases': qs.filter(lead__isnull=True).count(),
                         'services': services, 'quarantined_source_rows':SourceRow.objects.filter(outcome='quarantined').count(),
                         'policy': 'Validated imported cases; all source statuses retained. Unresolved rows are quarantined. Dates use the lead-entry proxy.',
                         'latest_import': {'created_at': latest.created_at, 'summary': latest.summary} if latest else None})
