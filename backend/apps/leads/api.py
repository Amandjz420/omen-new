from django.db.models import Q
from apps.valuations.services import scope_leads
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from target_core.models import Lead, LeadNote, SourceIdentity
from target_core.sync import source_key
from apps.accounts.api import staff_api, body
from apps.common.read_api import page, source_references
from apps.directory.api import office_json


def lead_json(obj,references):
    reference=references.get(obj.id) or {}
    return {'id': obj.id, 'source_id': reference.get('source_id'), 'number': obj.number, 'status': obj.legacy_status,
            'status_label': {'1': 'New lead', '2': 'In process', '3': 'Cancelled', '4': 'Closed (legacy)'}.get(obj.legacy_status, 'Unknown'),
            'received_date': obj.received_date, 'date_basis': obj.date_basis,
            'office': office_json(obj.office,references) if obj.office else None,
            'issues': reference.get('issues', [])}


@require_GET
@staff_api
def leads(request):
    qs = scope_leads(request.user, Lead.objects.select_related('office__bank')).order_by('-received_date', '-id')
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
    # Scoped before anything is read or written, including a note (review BF1).
    obj = scope_leads(request.user, Lead.objects.select_related('office__bank', 'contact')).filter(pk=pk).first()
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
    result['contact'] = {'name': obj.contact.name, 'phone': obj.contact.phone} if obj.contact else None
    # A case whose subtype was remapped or cleared carries the importer's note here.
    result['cases'] = [{'id':c.id,'source_id':(references.get(c.id) or {}).get('source_id'),'service':c.service.name,
                       'subtype':c.subtype.name if c.subtype else None,'district':c.asset_district,
                       'issues':(references.get(c.id) or {}).get('issues',[])} for c in cases]
    result['notes'] = list(obj.notes.order_by('-created_at').values('id', 'body', 'created_at', 'author__username'))
    return JsonResponse(result, status=201 if request.method == 'POST' else 200)

