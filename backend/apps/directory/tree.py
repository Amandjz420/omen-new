"""The organisations and their clients as a bank -> branch -> client tree (client review
2026-11-25: the old screen showed 30 organisations in a dropdown, and about 1,400 exist).

Bank branches are grouped by their bank without changing any record: the bank linked
to the organisation; else the bank its IFSC belongs to (the bank directory, or another
organisation with the same IFSC prefix); else a bank whose name the organisation's name
starts with, case and spacing ignored, so "State Bank Of India" and "State Bank of
India" fall together. A Corporate or Individual organisation is grouped by its type,
and a bank branch matched by none of these goes under "Bank not identified".

Groups and branches are ordered by their latest lead, most recent first. The counts
come from three grouped queries; the grouping itself runs over the organisations in
memory, which is cheap at this size.
"""
import datetime
import re

from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from target_core import models as m
from apps.accounts.api import staff_api

IFSC = re.compile(r'^([A-Z]{4})0[A-Z0-9]{6}$')
FI = 'Financial Institution'
UNIDENTIFIED = 'none'
PAGE = 25


def norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()


def prefix(ifsc):
    match = IFSC.match((ifsc or '').strip().upper())
    return match.group(1) if match else None


def organisations():
    """Every organisation with its group, client and lead counts and latest lead."""
    rows = list(m.ClientOffice.objects.values('id', 'name', 'branch_name', 'ifsc', 'bank_id', 'bank__name', 'client_type__name',
                                              'state', 'district', 'address', 'gstin', 'pan'))
    leads = {r['office_id']: r for r in m.Lead.objects.exclude(legacy_deleted='1').values('office_id')
             .annotate(leads=Count('id'), last_lead=Max('received_date'))}
    clients = dict(m.Contact.objects.values('office_id').annotate(n=Count('id')).values_list('office_id', 'n'))
    banks = {r['bank_id']: r['bank__name'] for r in rows if r['bank_id']}
    by_prefix = {}
    for r in rows:
        if r['bank_id'] and prefix(r['ifsc']):
            by_prefix.setdefault(prefix(r['ifsc']), r['bank_id'])
    unlinked = {(r['ifsc'] or '').strip().upper() for r in rows if not r['bank_id'] and prefix(r['ifsc'])}
    directory = {ifsc.upper(): (bank, name) for ifsc, bank, name in m.BankBranch.objects.filter(ifsc__in=unlinked)
                 .values_list('ifsc', 'bank_id', 'bank__name')} if unlinked else {}
    names = sorted(((norm(n), b) for b, n in banks.items()), key=lambda x: -len(x[0]))       # longest name first
    for r in rows:
        bank = r['bank_id']
        if not bank and prefix(r['ifsc']):
            found = directory.get((r['ifsc'] or '').strip().upper())
            if found:
                bank = found[0]; banks.setdefault(bank, found[1])
            else:
                bank = by_prefix.get(prefix(r['ifsc']))
        if not bank and r['client_type__name'] in (None, '', FI):
            name = norm(r['name'])
            bank = next((b for n, b in names if n and (name == n or name.startswith(n + ' '))), None)
        kind = r['client_type__name'] or ''
        if bank and kind in ('', FI):
            r['group'], r['group_name'] = f'bank:{bank}', banks[bank]
        elif kind in ('', FI):
            r['group'], r['group_name'] = UNIDENTIFIED, 'Bank not identified'
        else:
            r['group'], r['group_name'] = f'type:{kind}', kind
        counted = leads.get(r['id']) or {}
        r['leads'], r['last_lead'], r['clients'] = counted.get('leads', 0), counted.get('last_lead'), clients.get(r['id'], 0)
    return rows


def filtered(request, rows):
    g = request.GET
    if g.get('type'):
        rows = [r for r in rows if (r['client_type__name'] or FI) == g['type']]
    if g.get('bank'):
        rows = [r for r in rows if r['group'] == g['bank']]
    if g.get('state'):
        rows = [r for r in rows if norm(r['state']) == norm(g['state'])]
    if g.get('district'):
        rows = [r for r in rows if norm(r['district']) == norm(g['district'])]
    if g.get('active'):
        try:
            months = max(1, min(120, int(g['active'])))
        except ValueError:
            months = 0
        if months:
            since = datetime.date.today() - datetime.timedelta(days=round(months * 30.44))
            rows = [r for r in rows if r['last_lead'] and r['last_lead'] >= since]
    return rows


def recent_first(rows, key='last_lead'):
    return sorted(rows, key=lambda r: (r[key] is None, -(r[key].toordinal() if r[key] else 0), norm(r.get('name') or r.get('group_name'))))


def branch_json(r):
    return {'id': r['id'], 'name': r['name'], 'branch': r['branch_name'], 'ifsc': r['ifsc'], 'district': r['district'], 'state': r['state'],
            'address': r['address'], 'gstin': r['gstin'], 'pan': r['pan'], 'type': r['client_type__name'] or '',
            'group': r['group'], 'group_name': r['group_name'], 'clients': r['clients'], 'leads': r['leads'], 'last_lead': r['last_lead']}


@require_GET
@staff_api
def groups(request):
    """The banks (and Corporate, Individual, Bank not identified) with their totals,
    and the choices the filters offer."""
    everything = organisations()
    rows = filtered(request, everything)
    out = {}
    for r in rows:
        g = out.setdefault(r['group'], {'key': r['group'], 'name': r['group_name'], 'kind': r['group'].split(':')[0],
                                        'branches': 0, 'clients': 0, 'leads': 0, 'last_lead': None})
        g['branches'] += 1; g['clients'] += r['clients']; g['leads'] += r['leads']
        if r['last_lead'] and (not g['last_lead'] or r['last_lead'] > g['last_lead']):
            g['last_lead'] = r['last_lead']
    places = {}
    for r in everything:
        if (r['state'] or '').strip():
            places.setdefault(r['state'].strip(), set()).add((r['district'] or '').strip())
    banks = sorted({(r['group'], r['group_name']) for r in everything if r['group'].startswith('bank:')}, key=lambda b: norm(b[1]))
    return JsonResponse({
        'groups': recent_first(list(out.values())),
        'totals': {'organisations': len(rows), 'clients': sum(r['clients'] for r in rows)},
        'filters': {'types': sorted({r['client_type__name'] or FI for r in everything}),
                    'banks': [{'value': k, 'label': n} for k, n in banks],
                    'states': [{'name': s, 'districts': sorted(d for d in ds if d)} for s, ds in sorted(places.items())]}})


SORTS = {'last_lead': None, 'name': lambda r: (norm(r['name']), norm(r['branch_name'])), 'leads': lambda r: -r['leads'],
         'clients': lambda r: -r['clients'], 'district': lambda r: norm(r['district'])}


@require_GET
@staff_api
def branches(request):
    """One group's organisations, filtered, sorted and a page at a time."""
    group = request.GET.get('group', '')
    rows = [r for r in filtered(request, organisations()) if r['group'] == group]
    sort = request.GET.get('sort', 'last_lead')
    rows = recent_first(rows) if SORTS.get(sort) is None else sorted(rows, key=SORTS[sort])
    try:
        number = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        return JsonResponse({'error': 'page must be an integer'}, status=400)
    return JsonResponse({'count': len(rows), 'page': number, 'page_size': PAGE,
                         'results': [branch_json(r) for r in rows[(number - 1) * PAGE:number * PAGE]]})


def client_rows(qs):
    qs = (qs.select_related('designation', 'office')
          .annotate(leads=Count('lead', filter=~Q(lead__legacy_deleted='1')), last_lead=Max('lead__received_date')))
    return [{'id': c.pk, 'name': c.name, 'phone': c.phone, 'alternate_phone': c.alternate_phone, 'designation_id': c.designation_id,
             'designation': c.designation.name if c.designation_id else '', 'office': c.office_id,
             'office_name': ', '.join(x for x in (c.office.name, c.office.branch_name) if x), 'leads': c.leads, 'last_lead': c.last_lead}
            for c in qs]


@require_GET
@staff_api
def clients(request):
    """An organisation's clients, the one who gave work most recently first."""
    import uuid
    try:
        office = uuid.UUID(request.GET.get('office', ''))
    except ValueError:
        return JsonResponse({'error': 'Choose an organisation'}, status=400)
    rows = client_rows(m.Contact.objects.filter(office_id=office))
    return JsonResponse({'results': recent_first(rows)})


@require_GET
@staff_api
def search(request):
    """Branches by name, branch, IFSC or place, and clients by name or mobile, across
    every group, for when the person knows what they are looking for."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'branches': [], 'clients': []})
    words = norm(q).split()
    rows = [r for r in filtered(request, organisations())
            if all(w in norm(' '.join(str(r[k] or '') for k in ('name', 'branch_name', 'ifsc', 'district', 'state'))) for w in words)]
    digits = re.sub(r'\D', '', q)
    match = Q(name__icontains=q) | (Q(phone__contains=digits) | Q(alternate_phone__contains=digits) if len(digits) >= 4 else Q(pk=None))
    found = recent_first(client_rows(m.Contact.objects.filter(match)[:200]))[:PAGE]
    return JsonResponse({'branches': [branch_json(r) for r in recent_first(rows)[:PAGE]], 'branch_count': len(rows), 'clients': found})
