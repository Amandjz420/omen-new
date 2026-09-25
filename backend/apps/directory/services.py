"""Client office and contact maintenance."""
from django.http import JsonResponse
from . import models as m
from apps.common.http import IntakeError, endpoint, payload, find
from apps.common.validation import validated
from apps.audit.services import record, snapshot

OFFICE_FIELDS = ['name', 'branch_name', 'address', 'bank', 'client_type', 'state', 'district']


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

