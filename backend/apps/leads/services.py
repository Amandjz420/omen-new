"""Admin-only lead intake. Business role policy is deliberately deferred."""
from apps.valuations.services import require_lead
from apps.common.http import IntakeError, endpoint, payload, find
from apps.audit.services import snapshot, record
from apps.common.validation import validated
import hashlib
import json
import re
import uuid
from functools import wraps

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from target_core import models as m
from apps.accounts.api import staff_api


















def editable(lead):
    if lead.legacy_deleted not in ('', '0') or lead.legacy_status not in ('1', '2'):
        raise IntakeError('Cancelled, closed or unknown-status leads cannot be changed through intake', 409)
    if lead.workorder_set.exists():
        raise IntakeError('This lead already has a work order; intake changes are locked', 409)


def service_check(obj):
    if obj.subtype_id and obj.subtype.service_id != obj.service_id:
        raise IntakeError('The subtype does not belong to the selected service')


def lead_check(lead):
    if lead.contact_id and lead.contact.office_id != lead.office_id:
        raise IntakeError('Select a contact from the selected client office')
    if lead.assigned_employee_id:
        # Existing employee records without accounts remain assignable. Explicitly
        # disabled linked accounts are not offered for new work.
        user = lead.assigned_employee.user
        if user and not user.is_active:
            raise IntakeError('The selected employee account is inactive')


LEAD_FIELDS = ['office', 'contact', 'assigned_employee', 'received_date']
SERVICE_FIELDS = ['service', 'subtype', 'party_count', 'case_count']
BORROWER_FIELDS = ['name', 'agreed_fee', 'property_count']








def next_number():
    m.LeadCounter.objects.get_or_create(name='lead')
    # Acquire a database write lock before reading the source maximum. A DB
    # conflict returns 409; the whole request rolls back and may be retried.
    m.LeadCounter.objects.filter(name='lead').update(value=F('value') + 1)
    counter = m.LeadCounter.objects.get(name='lead')
    maximum = max((int(n[8:]) for n in m.Lead.objects.values_list('number', flat=True)
                   if re.fullmatch(r'L-\d{6}\d+', n)), default=0)
    counter.value = max(counter.value, maximum + 1)
    counter.save(update_fields=['value'])
    return f'L-{timezone.localdate():%m%y%d}{counter.value}', counter.value


@endpoint(['POST'])
def create_lead(request):
    data = payload(request, [*LEAD_FIELDS, 'request_id', 'services', 'borrowers'])
    try:
        key = uuid.UUID(str(data.get('request_id')))
    except ValueError:
        raise IntakeError('request_id must be a UUID, reused when retrying the same creation')
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    existing = m.Lead.objects.filter(intake_key=key).first()
    if existing:
        if existing.intake_hash != digest:
            raise IntakeError('This request ID was already used for different lead data', 409)
        return JsonResponse({'id': existing.pk, 'number': existing.number, 'replayed': True})
    services, borrowers = data.get('services', []), data.get('borrowers', [])
    if any(not isinstance(rows, list) or len(rows) > 100 for rows in (services, borrowers)):
        raise IntakeError('services and borrowers must be lists of at most 100 items')
    lead = validated(m.Lead, LEAD_FIELDS, {k:v for k,v in data.items() if k in LEAD_FIELDS})
    lead_check(lead)
    lead.number, lead.local_sequence = next_number()
    lead.intake_key, lead.intake_hash = key, digest
    lead.legacy_status, lead.legacy_deleted, lead.date_basis = '1', '0', 'actual_intake'
    lead.save()
    for rows, model, fields in [(services, m.RequestedService, SERVICE_FIELDS), (borrowers, m.Borrower, BORROWER_FIELDS)]:
        for row in rows:
            add_child(lead, model, fields, row, request.user)
    record(request.user, lead, action='lead.create')
    return JsonResponse({'id': lead.pk, 'number': lead.number, 'replayed': False}, status=201)


def add_child(lead, model, fields, data, user):
    if not isinstance(data, dict) or set(data) - set(fields):
        raise IntakeError('Unexpected child record fields')
    obj = validated(model, fields, data)
    obj.lead = lead
    if model is m.RequestedService:
        service_check(obj)
        if lead.requestedservice_set.filter(service=obj.service, subtype=obj.subtype).exists():
            raise IntakeError('This service and subtype are already requested', 409)
        if lead.legacy_status == '1':
            before = snapshot(lead)
            lead.legacy_status = '2'
            lead.save(update_fields=['legacy_status', 'updated_at'])
            record(user, lead, before, 'lead.services_started')
    if model is m.Borrower:
        obj.currency = 'INR'
    obj.save()
    record(user, obj, action=f'{model._meta.model_name}.create')
    return obj


def lead_result(lead):
    result = {'id': lead.pk, **snapshot(lead), 'updated_at': lead.updated_at, 'editable': lead.legacy_status in ('1','2')
              and lead.legacy_deleted in ('','0') and not lead.workorder_set.exists()}
    result['services'] = list(lead.requestedservice_set.values('id','service_id','subtype_id','party_count','case_count'))
    result['borrowers'] = list(lead.borrower_set.values('id','name','agreed_fee','property_count'))
    result['cases'] = list(lead.case_set.values('id','borrower_id','service_id','subtype_id','asset_address','asset_district'))
    result['follow_ups'] = list(lead.follow_ups.order_by('-created_at').values('id','call_status','remark','logged_date_text','logged_time_text'))
    result['office_name'] = lead.office.name
    result['audit'] = list(m.IntakeAudit.objects.filter(target_model=lead._meta.label,target_id=lead.pk)
                           .order_by('-created_at').values('action','created_at','actor__username')[:30])
    return result


@endpoint(['GET', 'PATCH'])
def lead_detail(request, pk):
    lead = require_lead(request.user, find(m.Lead, pk))
    if request.method == 'PATCH':
        editable(lead)
        before = snapshot(lead)
        data = payload(request, ['contact','assigned_employee','received_date','cancel_reason'])
        if not data:
            raise IntakeError('Provide fields to update')
        lead = validated(m.Lead, LEAD_FIELDS, {k:v for k,v in data.items() if k != 'cancel_reason'}, lead)
        lead_check(lead)
        if 'received_date' in data:
            lead.date_basis = 'actual_intake'
        if 'cancel_reason' in data:
            reason = data['cancel_reason']
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 4000:
                raise IntakeError('Provide a cancellation reason of at most 4,000 characters')
            lead.legacy_status = '3'
        lead.save()
        record(request.user, lead, before, 'lead.cancel' if 'cancel_reason' in data else 'lead.update')
        if 'cancel_reason' in data:
            m.LeadNote.objects.create(lead=lead, author=request.user, body='Cancellation: '+data['cancel_reason'].strip())
    return JsonResponse(lead_result(lead))


@endpoint(['POST'])
def lead_children(request, pk, kind):
    lead = require_lead(request.user, find(m.Lead, pk))
    editable(lead)
    if kind in ('services', 'borrowers'):
        model, fields = (m.RequestedService, SERVICE_FIELDS) if kind == 'services' else (m.Borrower, BORROWER_FIELDS)
        obj = add_child(lead, model, fields, payload(request, fields), request.user)
    elif kind == 'cases':
        fields = ['borrower', 'service', 'subtype', 'asset_address', 'asset_district', 'asset_state']
        obj = validated(m.Case, fields, payload(request, fields))
        if obj.borrower.lead_id != lead.pk:
            raise IntakeError('The borrower belongs to another lead')
        service_check(obj)
        if not lead.requestedservice_set.filter(service=obj.service, subtype=obj.subtype).exists():
            raise IntakeError('Request this service/subtype on the lead before adding a case')
        if not obj.asset_address.strip():
            raise IntakeError('An asset address is required')
        obj.lead, obj.legacy_status = lead, '0'
        obj.save()
        record(request.user, obj, action='case.create')
    elif kind == 'follow-ups':
        # Local outcomes are readable labels. Legacy codes remain unchanged.
        data = payload(request, ['outcome', 'remark'])
        if data.get('outcome') not in ('Contacted','No answer','Callback requested'):
            raise IntakeError('Choose a supported follow-up outcome')
        remark = data.get('remark')
        if not isinstance(remark, str) or not remark.strip() or len(remark) > 4000:
            raise IntakeError('Enter a follow-up remark of at most 4,000 characters')
        now = timezone.localtime()
        obj = m.FollowUp.objects.create(lead=lead,call_status=data['outcome'],remark=remark.strip(),
                                        logged_date_text=now.date().isoformat(),logged_time_text=now.strftime('%H:%M:%S'))
        record(request.user, obj, action='followup.create')
    else:
        raise IntakeError('Unknown intake action', 404)
    return JsonResponse({'id': obj.pk}, status=201)

# Public imports kept for callers of the original intake module.
from apps.directory.services import offices, contacts, OFFICE_FIELDS, CONTACT_FIELDS
from apps.catalog.api import catalog
