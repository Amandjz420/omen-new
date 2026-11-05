"""Client office and contact maintenance."""
import re
from django.http import JsonResponse
from . import models as m
from apps.common.http import IntakeError, endpoint, payload, find
from apps.common.validation import validated
from apps.audit.services import record, snapshot

# ifsc as on the legacy client form, so a client added from the bank directory keeps it.
OFFICE_FIELDS = ['name', 'branch_name', 'address', 'bank', 'client_type', 'state', 'district', 'ifsc', 'gstin', 'pan', 'block']
GSTIN = re.compile(r'\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]')
PAN = re.compile(r'[A-Z]{5}\d{4}[A-Z]')


def office_check(obj):
    """Client review 2026-11-05: every client has a name, address, GST/PAN; only a
    Financial Institution has an IFSC and a bank. A corporate or individual client
    keeps neither, so a stale IFSC cannot pick a bank's own valuation form."""
    obj.gstin, obj.pan, obj.ifsc = (obj.gstin or '').strip().upper(), (obj.pan or '').strip().upper(), (obj.ifsc or '').strip().upper()
    if obj.gstin and not GSTIN.fullmatch(obj.gstin):
        raise IntakeError('Enter the GST number as 15 characters, e.g. 23ABCDE1234F1Z5')
    if obj.pan and not PAN.fullmatch(obj.pan):
        raise IntakeError('Enter the PAN as 10 characters, e.g. ABCDE1234F')
    if obj.client_type_id and obj.client_type.name != 'Financial Institution':
        obj.ifsc, obj.bank, obj.directory_branch = '', None, None
    elif obj.ifsc and not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', obj.ifsc):
        raise IntakeError('An IFSC is 11 characters: four letters, 0, then six letters or digits')
    if obj.block_id:                                      # the city fills its district and state
        district = obj.block.district
        if district:
            obj.district = district.name
            obj.state = district.state.name if district.state_id else obj.state


CONTACT_FIELDS = ['name', 'office', 'designation', 'phone', 'alternate_phone']


@endpoint(['GET', 'POST', 'PATCH'])
def offices(request, pk=None):
    if request.method == 'GET':
        obj = find(m.ClientOffice, pk)
        return JsonResponse({'id': obj.pk, **snapshot(obj)})
    if (pk is None) != (request.method == 'POST'):
        raise IntakeError('Use POST to create or PATCH an existing office', 405)
    existing = find(m.ClientOffice, pk) if pk else None
    before = snapshot(existing) if existing else None
    obj = validated(m.ClientOffice, OFFICE_FIELDS, payload(request, OFFICE_FIELDS), existing)
    office_check(obj)
    if obj.directory_branch_id and obj.bank_id != obj.directory_branch.bank_id:
        raise IntakeError('The bank must match this office’s linked directory branch')
    obj.save()
    record(request.user, obj, before, 'office.update' if existing else 'office.create')
    return JsonResponse({'id': obj.pk, **snapshot(obj)}, status=200 if existing else 201)


@endpoint(['GET', 'POST', 'PATCH'])
def contacts(request, pk=None):
    if request.method == 'GET':
        office = find(m.ClientOffice, request.GET.get('office'))
        return JsonResponse({'results': list(m.Contact.objects.filter(office=office).order_by('name').values(
            'id', 'name', 'office_id', 'phone', 'alternate_phone', 'designation_id'))})
    if (pk is None) != (request.method == 'POST'):
        raise IntakeError('Use POST to create or PATCH an existing contact', 405)
    existing = find(m.Contact, pk) if pk else None
    before = snapshot(existing) if existing else None
    data = payload(request, CONTACT_FIELDS)
    obj = validated(m.Contact, CONTACT_FIELDS, data, existing)
    if existing and str(before['office']) != str(obj.office_id):
        raise IntakeError('Create a new contact when changing client office')
    obj.save()
    record(request.user, obj, before, 'contact.update' if existing else 'contact.create')
    return JsonResponse({'id': obj.pk, **snapshot(obj)}, status=200 if existing else 201)

