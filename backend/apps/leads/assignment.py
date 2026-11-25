"""Who received a lead, who picks it up, and who may reassign it (client review 2026-11-25).

A new lead is received by the person who records it and is assigned to nobody. It
waits in the unassigned queue until someone with a pickup role picks it up; that
person fills in the work-order details and later allots the cases. A manager (an
unrestricted user) can reassign it.

Which roles may pick up is not decided yet, so it is a setting: LEAD_PICKUP_ROLES,
role names separated by commas (a Railway variable). Until it is set, only
unrestricted users (managers and administrators) can pick up.
"""
from django.conf import settings
from django.http import JsonResponse

from target_core import models as m
from apps.audit.services import record, snapshot
from apps.common.http import IntakeError, endpoint, find, payload


def employee_of(user):
    """The employee record a login belongs to: its legacy account's, else the one
    linked to the login itself. None for an account with neither (an administrator)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    account = getattr(user, 'legacy_account', None)
    if account is not None and account.employee_id:
        return account.employee
    return m.Employee.objects.filter(user=user).first()


def pickup_roles():
    return {r.strip().lower() for r in getattr(settings, 'LEAD_PICKUP_ROLES', []) if r and r.strip()}


def role_names(user):
    from apps.accounts.grants import eligible_lead_grants
    account = getattr(user, 'legacy_account', None)
    if account is None:
        return set()
    accounts = [account, *account.merged_accounts.all()]
    return {n.strip().lower() for n in eligible_lead_grants().filter(account__in=accounts)
            .values_list('role__name', flat=True) if n}


def unrestricted(user):
    from apps.valuations.services import scoped_employee
    return scoped_employee(user) is None


def can_pick_up(user):
    """Picking up assigns the lead to the user's own employee record, so it needs one."""
    if employee_of(user) is None:
        return False
    return unrestricted(user) or bool(role_names(user) & pickup_roles())


def can_reassign(user):
    return unrestricted(user)


def open_lead(lead):
    if lead.legacy_deleted not in ('', '0') or lead.legacy_status not in ('1', '2'):
        raise IntakeError('Only an open lead can be picked up or reassigned', 409)


def assign(lead, employee, user, action):
    from apps.leads.services import lead_check, lead_result
    before = snapshot(lead)
    lead.assigned_employee = employee
    lead_check(lead)
    if lead.legacy_status == '1':
        lead.legacy_status = '2'                         # picked up: in process
    lead.save(update_fields=['assigned_employee', 'legacy_status', 'updated_at'])
    record(user, lead, before, action)
    return JsonResponse(lead_result(lead))


@endpoint(['POST'])
def pick_up(request, pk):
    from apps.valuations.services import require_lead
    lead = require_lead(request.user, find(m.Lead, pk))
    open_lead(lead)
    if not can_pick_up(request.user):
        raise IntakeError('Your role cannot pick up leads', 403)
    if lead.assigned_employee_id:
        raise IntakeError(f'{lead.assigned_employee.name} has already picked up this lead', 409)
    return assign(lead, employee_of(request.user), request.user, 'lead.pickup')


@endpoint(['POST'])
def reassign(request, pk):
    from apps.valuations.services import require_lead
    lead = require_lead(request.user, find(m.Lead, pk))
    open_lead(lead)
    if not can_reassign(request.user):
        raise IntakeError('Only a manager can reassign a lead', 403)
    data = payload(request, ['employee'])
    if not data.get('employee'):
        raise IntakeError('Choose who the lead is assigned to')
    employee = find(m.Employee, data['employee'])
    if lead.assigned_employee_id == employee.pk:
        raise IntakeError(f'The lead is already assigned to {employee.name}', 409)
    return assign(lead, employee, request.user, 'lead.reassign')
