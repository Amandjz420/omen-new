"""Common form validation for intake and directory writes."""
from django import forms
from django.forms.models import model_to_dict
from apps.common.http import IntakeError

OPTIONAL = {'bank', 'client_type', 'directory_branch', 'designation', 'contact', 'assigned_employee',
            'subtype', 'agreed_fee', 'property_count', 'party_count', 'case_count'}


def validated(model, fields, data, instance=None):
    form_type = forms.modelform_factory(model, fields=fields)
    for field in OPTIONAL.intersection(form_type.base_fields):
        form_type.base_fields[field].required = False
    if instance:
        data = {**model_to_dict(instance, fields=fields), **data}
    form = form_type(data, instance=instance)
    if not form.is_valid():
        raise IntakeError('; '.join(f'{key}: {", ".join(errors)}' for key, errors in form.errors.items()))
    obj = form.save(commit=False)
    for field in ('name',):
        if field in fields and not getattr(obj, field).strip():
            raise IntakeError(f'{field} is required')
    if hasattr(obj, 'agreed_fee') and obj.agreed_fee is not None and obj.agreed_fee < 0:
        raise IntakeError('Agreed fee cannot be negative')
    for field in ('party_count', 'case_count', 'property_count'):
        if field in fields and getattr(obj, field) is not None and getattr(obj, field) < 1:
            raise IntakeError(f'{field} must be at least one')
    return obj

