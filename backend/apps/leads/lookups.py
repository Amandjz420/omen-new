"""What the intake forms fill in for the person, as the legacy forms did.

Traced to design/add_lead.jsp (the lead giver found by mobile number; a client by
IFSC), design/add_client.jsp and design/add_case.jsp (their cascades). The small
lists come in one response, so each cascade answers without a request per choice;
a value's code is its legacy id, as imported records store it.
"""
import json
import re

from django.db.models import Count, F, Max, Q
from django.http import JsonResponse

from target_core import models as m
from apps.common.http import IntakeError, endpoint

# The legacy codes (omen-lead-new enums), stored as the imported records store them.
MODES = [(1, 'Phone'), (2, 'Email'), (3, 'Online'), (4, 'Walk in'), (5, 'Letter')]                   # ModeEnum
FOLLOW_UP_STATUSES = [('1', 'Start entry'), ('3', 'Not picked call'), ('4', 'Call back'), ('5', 'Not connected'),
                      ('6', 'Meeting has been scheduled'), ('7', 'Incorrect number')]                    # ModeFollowUpEnum
PAYERS = [(1, 'By client'), (2, 'By client customer')]                                                   # PaidByEnum
FEE_BASES = [(1, 'By circular'), (2, 'Fixed amount')]                                                     # PaymentByEnum
PAYMENT_METHODS = [(1, 'By bank'), (2, 'By cash'), (3, 'By any other')]                                  # PaidByModeEnum


def legacy_codes(schema, table):
    """target id -> legacy id, from the import's identity records."""
    out = {}
    for key, target in m.SourceIdentity.objects.filter(environment='main', schema=schema, table=table).values_list('key', 'target_id'):
        try:
            out[str(target)] = str(json.loads(key)[0][1])
        except (ValueError, IndexError, TypeError):
            pass
    return out


def live(qs):
    """Rows not deleted in the previous system."""
    model = qs.model
    if any(f.name == 'legacy_deleted' for f in model._meta.fields):
        qs = qs.exclude(legacy_deleted='1')
    return qs


@endpoint(['GET'])
def lookups(request):
    usage_code, document_code, block_code = (legacy_codes('lead_mngt', 'usage_of_reports'), legacy_codes('lead_mngt', 'scrutiny_document'),
                                             legacy_codes('uam_user', 'block'))
    rows = lambda qs, *fields: list(qs.values('id', 'name', *fields))
    account = getattr(request.user, 'legacy_account', None)
    return JsonResponse({
        # The signed-in person's employee record: "Lead received by" defaults to them.
        'me': {'employee_id': account.employee_id if account else None},
        'modes': [{'code': c, 'label': n} for c, n in MODES],
        'follow_up_statuses': [{'code': c, 'label': n} for c, n in FOLLOW_UP_STATUSES],
        'payers': [{'code': c, 'label': n} for c, n in PAYERS],
        'fee_bases': [{'code': c, 'label': n} for c, n in FEE_BASES],
        'payment_methods': [{'code': c, 'label': n} for c, n in PAYMENT_METHODS],
        'client_types': rows(m.ClientType.objects.order_by('name')),
        'designations': rows(m.ContactDesignation.objects.order_by('name')),
        'divisions': rows(live(m.LeadDivision.objects).order_by('name')),
        'subdivisions': rows(live(m.LeadSubdivision.objects).order_by('name'), 'division_id'),
        'states': rows(m.State.objects.order_by('name')),
        'districts': rows(m.District.objects.order_by('name'), 'state_id'),
        'blocks': [{**b, 'code': block_code.get(str(b['id']), '')} for b in rows(m.Block.objects.order_by('name'), 'district_id')],
        'report_usages': [{**u, 'code': usage_code.get(str(u['id']), '')}
                          for u in rows(live(m.ReportUsage.objects).order_by('name'), 'service_id', 'subtype_id')],
        'scrutiny_documents': [{**d, 'code': document_code.get(str(d['id']), '')}
                               for d in rows(live(m.ScrutinyRequirement.objects).order_by('name'), 'service_id', 'subtype_id',
                                             'client_type_id', 'report_usage_id')],
    })


def office_json(o):
    if o is None:
        return None
    return {'id': o.pk, 'name': o.name, 'branch': o.branch_name, 'client_type_id': o.client_type_id,
            'client_type': o.client_type.name if o.client_type_id else '', 'address': o.address, 'ifsc': o.ifsc,
            'gstin': o.gstin, 'state': o.state, 'district': o.district, 'city': o.block.name if o.block_id else '',
            'block_id': o.block_id, 'bank': o.bank.name if o.bank_id else ''}


def contact_json(c):
    return {'id': c.pk, 'name': c.name, 'phone': c.phone, 'alternate_phone': c.alternate_phone,
            'designation_id': c.designation_id, 'designation': c.designation.name if c.designation_id else '',
            'division_id': c.division_id, 'division': c.division.name if c.division_id else '',
            'subdivision_id': c.subdivision_id, 'subdivision': c.subdivision.name if c.subdivision_id else '',
            'office': office_json(c.office)}


@endpoint(['GET'])
def orderer(request):
    """The lead giver by mobile number, with everything the lead form shows for them.
    Several may share a number; the one most recently giving leads comes first."""
    mobile = re.sub(r'\D', '', request.GET.get('mobile', ''))[-10:]
    if len(mobile) != 10:
        raise IntakeError('Enter the 10-digit mobile number')
    found = (live(m.Contact.objects).filter(Q(phone__endswith=mobile) | Q(alternate_phone__endswith=mobile))
             .select_related('office__client_type', 'office__block', 'office__bank', 'designation', 'division', 'subdivision')
             .annotate(last=Max('lead__received_date'), leads=Count('lead'))
             # Lead givers with no leads sort last: PostgreSQL otherwise puts nulls first when descending.
             .order_by(F('last').desc(nulls_last=True), '-leads', 'name'))
    return JsonResponse({'mobile': mobile, 'matches': [{**contact_json(c), 'leads': c.leads} for c in found[:5]]})


@endpoint(['GET'])
def offices(request):
    """Client offices of a client type, for the new lead giver's client."""
    qs = live(m.ClientOffice.objects).select_related('client_type', 'block', 'bank')
    if request.GET.get('client_type'):
        qs = qs.filter(client_type_id=request.GET['client_type'])
    if request.GET.get('q'):
        q = request.GET['q'].strip()
        qs = qs.filter(Q(name__icontains=q) | Q(branch_name__icontains=q) | Q(ifsc__iexact=q))
    return JsonResponse({'results': [office_json(o) for o in qs.order_by('name', 'branch_name')[:200]]})


@endpoint(['GET'])
def ifsc(request):
    """A client by IFSC: the client office if one exists; otherwise the bank's
    directory entry, so a new client's bank, branch, address and place fill in."""
    code = request.GET.get('code', '').strip().upper()
    if not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', code):
        raise IntakeError('An IFSC is 11 characters: four letters, 0, then six letters or digits')
    offices_found = [office_json(o) for o in live(m.ClientOffice.objects).filter(ifsc__iexact=code)
                     .select_related('client_type', 'block', 'bank')]
    branch = m.BankBranch.objects.filter(ifsc__iexact=code).select_related('bank').first()
    directory = branch and {'bank': branch.bank.name if branch.bank_id else '', 'bank_id': branch.bank_id, 'branch': branch.name, 'address': branch.address,
                            'city': branch.city, 'district': branch.district, 'state': branch.state, 'ifsc': branch.ifsc}
    return JsonResponse({'ifsc': code, 'offices': offices_found, 'directory': directory})
