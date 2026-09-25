from django.db.models import Q
from django.views.decorators.http import require_GET
from target_core.models import ClientOffice as Office, SourceIdentity
from target_core.sync import source_key
from apps.accounts.api import staff_api
from apps.common.read_api import page


def office_json(obj,references):
    reference=references.get(obj.id) or {}
    return {'id': obj.id, 'source_id': reference.get('source_id'), 'name': obj.name, 'branch': obj.branch_name,
            'bank': obj.bank.name if obj.bank else None, 'state': obj.state,
            'district': obj.district, 'issues': reference.get('issues', [])}


@require_GET
@staff_api
def offices(request):
    qs = Office.objects.select_related('bank').order_by('name', 'id')
    q = request.GET.get('q', '').strip()
    if q:
        ids=SourceIdentity.objects.filter(target_model=Office._meta.label,environment='main',key=source_key(q)).values('target_id')
        qs = qs.filter(Q(name__icontains=q) | Q(branch_name__icontains=q) | Q(id__in=ids))
    return page(request, qs, office_json)

