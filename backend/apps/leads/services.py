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


# The fields of the legacy intake forms (design/add_lead.jsp, add_client.jsp, add_case.jsp,
# add_feedback.jsp), with their required ones required, as the legacy forms did.
LEAD_FIELDS = ['office', 'contact', 'assigned_employee', 'received_date', 'enquiry_mode', 'received_by', 'party_count']
SERVICE_FIELDS = ['service', 'subtype', 'party_count', 'case_count']
BORROWER_FIELDS = ['name', 'contact_number', 'email', 'gst_number', 'property_count', 'payer', 'fee_basis', 'agreed_fee',
                   'payment_reference_name', 'payment_reference_number', 'pay_by_date', 'customer_payment_method']
CONTACT_REGISTRATION = ['name', 'phone', 'alternate_phone', 'office', 'designation', 'division', 'subdivision']
CASE_FIELDS = ['borrower', 'service', 'subtype', 'report_usages', 'scrutiny_documents', 'expected_report_date', 'asset_amount',
               'remarks', 'contact_person_name', 'contact_number', 'asset_address', 'state', 'district', 'block', 'asset_pin_code']
MOBILE = re.compile(r'[6-9]\d{9}')


def mobile(value, label):
    digits = re.sub(r'\D', '', str(value or ''))[-10:]
    if not MOBILE.fullmatch(digits):
        raise IntakeError(f'Enter {label} as a 10-digit mobile number')
    return digits








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


def register_contact(data, user):
    """A new lead giver, registered with the lead as the legacy form did: client,
    name, mobile, division, sub-division and designation."""
    if not isinstance(data, dict) or set(data) - set(CONTACT_REGISTRATION):
        raise IntakeError('Unexpected lead giver fields')
    for field, label in (('name', 'the lead giver\'s name'), ('office', 'the client'), ('designation', 'the designation'),
                         ('division', 'the division'), ('subdivision', 'the sub-division')):
        if not data.get(field):
            raise IntakeError(f'Choose or enter {label}')
    data = {**data, 'phone': mobile(data.get('phone'), 'the lead giver\'s mobile')}
    if data.get('alternate_phone'):
        data['alternate_phone'] = mobile(data['alternate_phone'], 'the alternate number')
    if m.Contact.objects.filter(phone__endswith=data['phone']).exists():
        raise IntakeError('A lead giver with this mobile number is already registered; find them by number', 409)
    contact = validated(m.Contact, CONTACT_REGISTRATION, data)
    if contact.subdivision.division_id != contact.division_id:
        raise IntakeError('The sub-division does not belong to the division')
    contact.save()
    record(user, contact, action='contact.register')
    return contact


@endpoint(['POST'])
def create_lead(request):
    data = payload(request, [*LEAD_FIELDS, 'request_id', 'services', 'borrowers', 'new_contact', 'alternate_phone'])
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
    if not services:
        raise IntakeError('Add at least one requested service')
    from apps.leads.lookups import MODES
    if data.get('enquiry_mode') not in [c for c, _ in MODES]:
        raise IntakeError('Choose how the lead came in')
    for field, label in (('received_by', 'who received the lead'), ('assigned_employee', 'who the lead is assigned to')):
        if not data.get(field):
            raise IntakeError(f'Choose {label}')
    # The lead giver: found by mobile number, or registered with the lead. The client
    # office is the lead giver's, as on the legacy form.
    contact = register_contact(data['new_contact'], request.user) if data.get('new_contact') else (
        find(m.Contact, data['contact']) if data.get('contact') else None)
    if contact is None:
        raise IntakeError('Find the lead giver by mobile number, or register them')
    if data.get('alternate_phone'):
        alternate = mobile(data['alternate_phone'], 'the alternate number')
        if alternate != contact.alternate_phone:
            before = snapshot(contact)
            contact.alternate_phone = alternate
            contact.save(update_fields=['alternate_phone', 'updated_at'])
            record(request.user, contact, before, 'contact.update')
    fields = {k: v for k, v in data.items() if k in LEAD_FIELDS}
    fields.update({'contact': contact.pk, 'office': contact.office_id})
    fields.setdefault('received_date', timezone.localdate().isoformat())
    lead = validated(m.Lead, LEAD_FIELDS, fields)
    lead_check(lead)
    lead.client_type_id = lead.office.client_type_id
    lead.case_count = sum(int(r.get('case_count') or 0) for r in services if isinstance(r, dict))
    lead.number, lead.local_sequence = next_number()
    lead.intake_key, lead.intake_hash = key, digest
    lead.legacy_status, lead.legacy_deleted, lead.date_basis = '1', '0', 'actual_intake'
    lead.save()
    for row in services:
        if not isinstance(row, dict) or row.get('case_count') in (None, ''):
            raise IntakeError('Enter the number of cases for each service')
        add_child(lead, m.RequestedService, SERVICE_FIELDS, row, request.user)
    for row in borrowers:
        add_borrower(lead, row, request.user)
    record(request.user, lead, action='lead.create')
    return JsonResponse({'id': lead.pk, 'number': lead.number, 'replayed': False}, status=201)


def add_borrower(lead, data, user, instance=None):
    """The client's customer with the fee agreement (design/add_client.jsp). Paid by
    the client: the payer is the lead's client and lead giver, filled in. A fixed fee
    needs the work order amount; a circular rate takes none."""
    from apps.leads.lookups import FEE_BASES, PAYERS, PAYMENT_METHODS
    if not isinstance(data, dict) or set(data) - set(BORROWER_FIELDS):
        raise IntakeError('Unexpected borrower fields')
    for field, label in (('name', "the client's customer name"), ('property_count', 'the number of cases'),
                         ('payment_reference_name', 'who is responsible for payment'), ('pay_by_date', 'the pay-by date')):
        if data.get(field) in (None, ''):
            raise IntakeError(f'Enter {label}')
    data = {**data, 'contact_number': mobile(data.get('contact_number'), "the customer's contact number"),
            'payment_reference_number': mobile(data.get('payment_reference_number'), "the payment responsible person's number")}
    for field, codes, label in (('payer', PAYERS, 'who pays'), ('fee_basis', FEE_BASES, 'whether the fee is by circular or fixed'),
                                ('customer_payment_method', PAYMENT_METHODS, 'how payment is made')):
        if data.get(field) not in [c for c, _ in codes]:
            raise IntakeError(f'Choose {label}')
    if data['fee_basis'] == 2 and data.get('agreed_fee') in (None, ''):
        raise IntakeError('Enter the work order amount for a fixed fee')
    if data['fee_basis'] == 1:
        data['agreed_fee'] = None                         # by the client's circular
    before = snapshot(instance) if instance else None
    obj = (validated(m.Borrower, BORROWER_FIELDS, data, instance) if instance
           else add_child(lead, m.Borrower, BORROWER_FIELDS, data, user, save=False))
    if obj.payer == 1:
        obj.payer_name = f"{lead.office.name}{', ' + lead.office.branch_name if lead.office.branch_name else ''}"[:200]
        obj.payer_mobile = lead.contact.phone if lead.contact_id else ''
    else:
        obj.payer_name = obj.payer_mobile = ''
    obj.save()
    record(user, obj, before, 'borrower.update') if instance else record(user, obj, action='borrower.create')
    return obj


def add_child(lead, model, fields, data, user, save=True):
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
    if save:
        obj.save()
        record(user, obj, action=f'{model._meta.model_name}.create')
    return obj


def lead_result(lead):
    result = {'id': lead.pk, **snapshot(lead), 'updated_at': lead.updated_at, 'editable': lead.legacy_status in ('1','2')
              and lead.legacy_deleted in ('','0') and not lead.workorder_set.exists()}
    result['services'] = list(lead.requestedservice_set.values('id','service_id','subtype_id','party_count','case_count'))
    result['borrowers'] = list(lead.borrower_set.exclude(legacy_deleted='1').values(
        'id', 'name', 'contact_number', 'email', 'gst_number', 'property_count', 'payer', 'fee_basis', 'agreed_fee',
        'payer_name', 'payer_mobile', 'payment_reference_name', 'payment_reference_number', 'pay_by_date', 'customer_payment_method'))
    result['cases'] = list(lead.case_set.exclude(legacy_status='1').values(
        'id', 'borrower_id', 'service_id', 'subtype_id', 'usage_of_report_code', 'scrutiny_document_code', 'expected_report_date',
        'asset_amount', 'remarks', 'contact_person_name', 'contact_number', 'asset_address', 'asset_state', 'asset_district',
        'asset_block_code', 'asset_pin_code'))
    result['follow_ups'] = list(lead.follow_ups.order_by('-created_at').values('id', 'call_status', 'remark', 'logged_date_text',
                                                                               'logged_time_text', 'created_at'))
    result['contact'] = lead.contact_id and {'id': lead.contact_id, 'name': lead.contact.name, 'phone': lead.contact.phone}
    result['office_name'] = lead.office.name
    from apps.leads.lookups import office_json
    result['office_detail'] = office_json(lead.office)        # the case form's default place
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
        # Only the fields sent are validated: an imported lead may lack fields the
        # intake form now requires, and an edit must not fail on those.
        changed = [k for k in LEAD_FIELDS if k in data]
        if changed:
            lead = validated(m.Lead, changed, {k: data[k] for k in changed}, lead)
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
    if kind == 'services':
        obj = add_child(lead, m.RequestedService, SERVICE_FIELDS, payload(request, SERVICE_FIELDS), request.user)
    elif kind == 'borrowers':
        obj = add_borrower(lead, payload(request, BORROWER_FIELDS), request.user)
    elif kind == 'cases':
        obj = add_case(lead, payload(request, CASE_FIELDS), request.user)
    elif kind == 'follow-ups':
        obj = add_follow_up(lead, payload(request, ['status', 'notify_date', 'notify_time', 'remark']), request.user)
    else:
        raise IntakeError('Unknown intake action', 404)
    return JsonResponse({'id': obj.pk}, status=201)

def add_case(lead, data, user, instance=None):
    """A case (design/add_case.jsp): the borrower, service and subtype; the usages of
    report for that subtype; the scrutiny documents for those usages; the expected
    report date and output amount; the property's address and its state, district
    and city, each within the one before. Stored as imported cases store them: legacy
    codes, comma-separated where several are chosen, and place names."""
    from apps.leads.lookups import legacy_codes
    for field, label in (('borrower', "the client's customer"), ('service', 'the service'), ('subtype', 'the service sub type'),
                         ('expected_report_date', 'the expected date of report'), ('asset_amount', 'the output amount'),
                         ('asset_address', 'the property address'), ('state', 'the state'), ('district', 'the district'),
                         ('block', 'the city'), ('asset_pin_code', 'the PIN code')):
        if data.get(field) in (None, '', []):
            raise IntakeError(f'Enter {label}')
    if not re.fullmatch(r'[1-9]\d{5}', str(data['asset_pin_code']).strip()):
        raise IntakeError('Enter the six-digit PIN code')
    usages = list(m.ReportUsage.objects.exclude(legacy_deleted='1').filter(pk__in=[str(x) for x in data.get('report_usages') or []]))
    documents = list(m.ScrutinyRequirement.objects.exclude(legacy_deleted='1').filter(pk__in=[str(x) for x in data.get('scrutiny_documents') or []]))
    if not usages:
        raise IntakeError('Choose the usage of report')
    if not documents:
        raise IntakeError('Choose the scrutiny documents')
    state, district, block = find(m.State, data['state']), find(m.District, data['district']), find(m.Block, data['block'])
    if district.state_id != state.pk or block.district_id != district.pk:
        raise IntakeError('The district must be in the state, and the city in the district')
    fields = ['borrower', 'service', 'subtype', 'expected_report_date', 'asset_amount', 'remarks', 'contact_person_name',
              'contact_number', 'asset_address', 'asset_pin_code']
    before = snapshot(instance) if instance else None
    obj = validated(m.Case, fields, {k: data.get(k) for k in fields if data.get(k) not in (None,)}, instance)
    if obj.borrower.lead_id != lead.pk:
        raise IntakeError('The borrower belongs to another lead')
    service_check(obj)
    if not lead.requestedservice_set.filter(service=obj.service, subtype=obj.subtype).exists():
        raise IntakeError('Request this service/subtype on the lead before adding a case')
    if any(u.subtype_id != obj.subtype_id for u in usages):
        raise IntakeError('A usage of report does not belong to the service sub type')
    chosen = {u.pk for u in usages}
    if any(d.report_usage_id not in chosen for d in documents):
        raise IntakeError('A scrutiny document does not belong to the chosen usage of report')
    if obj.contact_number:
        obj.contact_number = mobile(obj.contact_number, "the contact person's number")
    usage_code, document_code = legacy_codes('lead_mngt', 'usage_of_reports'), legacy_codes('lead_mngt', 'scrutiny_document')
    block_code = legacy_codes('uam_user', 'block').get(str(block.pk), '')
    # Imported cases store legacy codes; new cases store the same, so both read alike.
    # Every imported usage, document and city has one; one added since has none, and
    # is refused rather than stored in a form no report could read.
    if any(str(u.pk) not in usage_code for u in usages) or any(str(d.pk) not in document_code for d in documents) or not block_code:
        raise IntakeError('A chosen usage of report, scrutiny document or city has no code from the previous system')
    obj.usage_of_report_code = ','.join(usage_code[str(u.pk)] for u in usages)
    obj.scrutiny_document_code = ','.join(document_code[str(d.pk)] for d in documents)
    obj.asset_state, obj.asset_district, obj.asset_block_code = state.name, district.name, block_code
    obj.lead, obj.legacy_status = lead, '0'
    obj.save()
    record(user, obj, before, 'case.update') if instance else record(user, obj, action='case.create')
    return obj


def add_follow_up(lead, data, user):
    """A follow-up call (design/add_feedback.jsp): its status, when to call back, and a
    remark, all required. The call-back date and time are stored where imported
    follow-ups keep them; the status is the legacy code."""
    import datetime
    from apps.leads.lookups import FOLLOW_UP_STATUSES
    if data.get('status') not in [c for c, _ in FOLLOW_UP_STATUSES]:
        raise IntakeError('Choose the follow-up status')
    try:
        notify = datetime.date.fromisoformat(str(data.get('notify_date')))
    except ValueError:
        raise IntakeError('Enter the date to be notified')
    if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', str(data.get('notify_time') or '')):
        raise IntakeError('Enter the time to be notified as hour and minute')
    remark = data.get('remark')
    if not isinstance(remark, str) or not remark.strip() or len(remark) > 4000:
        raise IntakeError('Enter a remark of at most 4,000 characters')
    obj = m.FollowUp.objects.create(lead=lead, call_status=data['status'], remark=remark.strip(),
                                    logged_date_text=notify.isoformat(), logged_time_text=data['notify_time'])
    record(user, obj, action='followup.create')
    return obj


@endpoint(['PATCH', 'DELETE'])
def lead_child(request, pk, kind, cid):
    """Edit or delete a client's customer or a case, as the legacy edit_client,
    client_delete, edit_case and case_delete did, while the lead is open to intake.
    An edit goes through the same checks as adding. A deletion sets the delete flag
    imported records carry; a customer with live cases keeps them until they are
    deleted first, so no case is left without its customer."""
    lead = require_lead(request.user, find(m.Lead, pk))
    editable(lead)
    if kind == 'borrowers':
        obj = m.Borrower.objects.filter(pk=cid, lead=lead).exclude(legacy_deleted='1').first()
        if obj is None:
            raise IntakeError("Client's customer not found", 404)
        if request.method == 'DELETE':
            if m.Case.objects.filter(borrower=obj).exclude(legacy_status='1').exists():
                raise IntakeError("Delete this customer's cases first", 409)
            before = snapshot(obj)
            obj.legacy_deleted = '1'
            obj.save(update_fields=['legacy_deleted', 'updated_at'])
            record(request.user, obj, before, 'borrower.delete')
        else:
            add_borrower(lead, payload(request, BORROWER_FIELDS), request.user, instance=obj)
    elif kind == 'cases':
        obj = m.Case.objects.filter(pk=cid, lead=lead).exclude(legacy_status='1').first()
        if obj is None:
            raise IntakeError('Case not found', 404)
        if request.method == 'DELETE':
            before = snapshot(obj)
            obj.legacy_status = '1'
            obj.save(update_fields=['legacy_status', 'updated_at'])
            record(request.user, obj, before, 'case.delete')
        else:
            add_case(lead, payload(request, CASE_FIELDS), request.user, instance=obj)
    else:
        raise IntakeError('Only customers and cases can be edited or deleted here', 404)
    lead.refresh_from_db()
    return JsonResponse(lead_result(lead))


# Public imports kept for callers of the original intake module.
from apps.directory.services import offices, contacts, OFFICE_FIELDS, CONTACT_FIELDS
from apps.catalog.api import catalog
