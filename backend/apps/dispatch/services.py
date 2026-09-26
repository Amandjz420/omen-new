"""Dispatch: sending approved reports and tracking them to delivery.

Traced to DispatchController (/add, /save, /edit, /list, /view_report,
/dispatch_list/{reportNo}, /delete) and ModeOfDispatchEnum, DispatchStatusEnum and
CourierByEnum.

A dispatch sends one consignment: one or more approved reports and any other
documents, by a chosen mode, and moves from Lying at HO to Under Transit to
Delivered. It is numbered D- + MMYYDD + a four-digit counter.

Numbering. The legacy maximum query read only numbers shorter than 13 characters,
to skip 794 dispatches from early 2021 that used a 17-character scheme
(D-022117820280002). That filter would also skip its own numbers once the counter
passed 9,999, so every later dispatch would be numbered 10,000. The seed here
excludes only the old scheme, so the series continues past 9,999.

Legacy defects not carried over:
  * A report already dispatched could be dispatched again silently; 356 approved
    reports appear in more than one legacy dispatch with nothing to say why. A
    resend now needs saying so, with a reason.
  * Delivered needed no delivery date; 6,057 legacy deliveries have none.
  * Status could be moved in any direction. It moves forward only.
  * Delete removed a dispatch. It is cancelled with a reason instead, and not once
    delivered.
  * The document count was typed separately and could disagree with the documents
    listed. It is counted.
  * Marking delivered sent an SMS using only the first report, and failed outright
    when none was valid. No SMS gateway is configured here, so none is sent.

Awaiting dispatch: approved reports with a current bank report that are in no live
dispatch. Legacy dispatch tracking began in 2021, so the 881 approved reports from
2020 that were never recorded are history rather than a backlog; the queue lists
newest first.

Dispatch is a head-office function: a user restricted to their own leads sees none.
"""
import datetime
import hashlib
import json
import re
import uuid
from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.audit.services import record, snapshot
from apps.billing.valuation import money
from apps.common.http import IntakeError, endpoint, find, payload
from apps.common.numbering import allocate, format_number
from apps.reports.services import current as current_report
from apps.valuations.services import scoped_employee
from apps.valuations.verification import actor

MODES, STATUSES, COURIERS = dict(m.Dispatch.MODES), dict(m.Dispatch.STATUSES), dict(m.Dispatch.COURIERS)
AT = {1: 'Addressee', 2: 'Extension Office', 3: 'Other', 4: 'Client Customer will pick up'}   # AddToBeDispatchedatEnum
BY = {1: 'Speed post', 2: 'Courier', 3: 'Deliver by hand'}                                     # ToBeDispatchedByEnum
LYING, TRANSIT, DELIVERED = 1, 2, 3
TRACKED = (1, 2, 6)                     # courier, speed post and normal post carry a consignment number
OLD_SCHEME = r'^D-[0-9]{15}$'
PAGE_SIZE = 25


def head_office(user):
    if scoped_employee(user) is not None:
        raise IntakeError('Dispatch is handled by head office', 404)


def current_reports():
    """Bank reports that can be dispatched: finally approved, current (not superseded)
    and with a document record. A report whose file is still in legacy storage is
    dispatchable; its document exists, only the file has not been retrieved here.

    Selected from the reports themselves. The previous filter on the valuation's
    reverse relation also matched a valuation with no report at all, since the outer
    join supplies nulls, so an approved valuation with no report could be dispatched
    (review N2)."""
    return m.BankReport.objects.filter(superseded_at__isnull=True, document__isnull=False,
                                       valuation__verifications__final_status='Verified')


def current_report_of(valuation):
    return current_reports().filter(valuation=valuation).order_by('-revision').first()


def approved_reports():
    return m.Valuation.objects.filter(pk__in=current_reports().values('valuation'))


def live_items():
    return m.DispatchItem.objects.filter(dispatch__cancelled=False, valuation__isnull=False)


def dispatched_reports():
    """Current reports already in a live dispatch. An item made here names the revision
    it sent. An item from the previous system names none, and that system produced
    only revision 0, so it covers revision 0 alone: a corrected revision made here
    is never hidden by an earlier revision's dispatch (review N3)."""
    live = live_items()
    named = live.filter(bank_report__isnull=False).values('bank_report')
    legacy = live.filter(bank_report__isnull=True).values('valuation')
    return current_reports().filter(Q(pk__in=named) | Q(revision=0, valuation__in=legacy))


def item_json(i):
    return {'reference': i.reference, 'valuation': i.valuation_id, 'resolution': i.get_resolution_display(),
            'revision': i.bank_report.revision if i.bank_report_id else None,
            'resend': i.resend, 'resend_reason': i.resend_reason}


def dispatch_json(d):
    items = list(d.items.order_by('position'))
    return {'id': d.pk, 'number': d.number, 'origin': 'local' if d.local_sequence else 'legacy',
            'status': d.status, 'status_label': STATUSES.get(d.status, ''), 'cancelled': d.cancelled, 'cancel_remark': d.cancel_remark,
            'mode': d.mode, 'mode_label': MODES.get(d.mode, ''), 'courier': d.courier, 'courier_label': COURIERS.get(d.courier, ''),
            'other_courier': d.other_courier, 'consignment_number': d.consignment_number, 'authorized_person': d.authorized_person,
            'cost': str(d.cost) if d.cost is not None else '', 'outward_date': d.outward_date, 'delivered_date': d.delivered_date,
            'town': d.town, 'client_name': d.client_name, 'customer_name': d.customer_name,
            'document_count': d.document_count, 'other_documents': [x.strip() for x in (d.other_documents or '').split(',') if x.strip()],
            'items': [item_json(i) for i in items], 'created_by': d.created_by_name,
            'next_statuses': [] if d.cancelled else [s for s in (TRANSIT, DELIVERED) if (d.status or LYING) < s]}


@endpoint(['GET'])
def awaiting(request):
    head_office(request.user)
    rows = approved_reports().exclude(pk__in=dispatched_reports().values('valuation'))
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(report_number__icontains=text) | Q(case__lead__number__icontains=text)
                           | Q(case__borrower__name__icontains=text) | Q(case__lead__office__name__icontains=text))
    total = rows.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    items = rows.select_related('case__lead__office', 'case__borrower').order_by('-valuation_date', '-report_number')
    return JsonResponse({'total': total, 'page': page, 'page_size': PAGE_SIZE,
                         'results': [{'valuation': v.pk, 'report_number': v.report_number, 'lead_number': v.case.lead.number,
                                      'borrower': v.case.borrower.name if v.case.borrower_id else '',
                                      'office': v.case.lead.office.name, 'valued_on': v.valuation_date,
                                      'to_be_dispatched_at': AT.get(v.dispatch_at_code, ''), 'to_be_dispatched_by': BY.get(v.dispatch_by_code, '')}
                                     for v in items[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]]})


BUCKETS = {'lying': Q(cancelled=False, status=LYING), 'transit': Q(cancelled=False, status=TRANSIT),
           'delivered': Q(cancelled=False, status=DELIVERED), 'cancelled': Q(cancelled=True)}


@endpoint(['GET', 'POST'])
def dispatches(request):
    head_office(request.user)
    if request.method == 'POST':
        return create(request)
    state = request.GET.get('state', 'lying')
    counts = {k: m.Dispatch.objects.filter(v).count() for k, v in BUCKETS.items()}
    rows = m.Dispatch.objects.filter(BUCKETS.get(state, BUCKETS['lying']))
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(number__icontains=text) | Q(report_references__icontains=text) | Q(consignment_number__icontains=text)
                           | Q(client_name__icontains=text) | Q(customer_name__icontains=text))
    total = rows.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    rows = rows.order_by('-outward_date', '-number')[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
    return JsonResponse({'state': state, 'total': total, 'page': page, 'page_size': PAGE_SIZE, 'counts': counts,
                         'results': [{'id': d.pk, 'number': d.number, 'outward_date': d.outward_date, 'reports': d.report_references,
                                      'client': d.client_name, 'mode': MODES.get(d.mode, ''), 'consignment': d.consignment_number,
                                      'status': STATUSES.get(d.status, ''), 'delivered_date': d.delivered_date} for d in rows]})


def date_of(data, field, label, not_before=None):
    if not data.get(field):
        return None
    try:
        value = datetime.date.fromisoformat(str(data[field]))
    except ValueError:
        raise IntakeError(f'Enter the {label} as YYYY-MM-DD')
    if value > timezone.localdate():
        raise IntakeError(f'The {label} cannot be in the future')
    if not_before and value < not_before:
        raise IntakeError(f'The {label} cannot be before the outward date')
    return value


FIELDS = ('reports', 'resend', 'other_documents', 'mode', 'courier', 'other_courier', 'consignment_number', 'authorized_person',
          'cost', 'outward_date', 'town', 'client_name', 'customer_name', 'status', 'delivered_date')


def create(request):
    data = payload(request, ['operation_id', *FIELDS])
    try:
        key = uuid.UUID(str(data.get('operation_id')))
    except (TypeError, ValueError):
        raise IntakeError('operation_id is required: a new UUID for each dispatch')
    digest = hashlib.sha256(json.dumps({f: data.get(f) for f in FIELDS}, sort_keys=True, default=str).encode()).hexdigest()
    done = m.Dispatch.objects.filter(request_key=key).first()
    if done is not None:
        if done.request_hash != digest:
            raise IntakeError('This operation_id was already used for a different dispatch', 409)
        return JsonResponse({**dispatch_json(done), 'replayed': True})

    chosen = [str(x) for x in (data.get('reports') or [])]
    if len(set(chosen)) != len(chosen):
        raise IntakeError('A report is listed twice')
    resend = {str(k): str(v or '').strip() for k, v in (data.get('resend') or {}).items()}
    others = [str(x).strip() for x in (data.get('other_documents') or []) if str(x).strip()]
    # Stored comma-separated, as in the previous system. Anything that would not fit or
    # would be split apart is refused, never cut short: the list was truncated to 500
    # characters while the document count still included what was lost (review N4).
    if any(',' in x for x in others):
        raise IntakeError('A document name cannot contain a comma; commas separate one document from the next')
    if not chosen and not others:
        raise IntakeError('Add at least one report or document to dispatch')
    reports, sent_before = [], set()
    for vid in chosen:
        valuation = m.Valuation.objects.filter(pk=vid).first() if re.fullmatch(r'[0-9a-f-]{36}', vid) else None
        report = current_report_of(valuation) if valuation else None     # checked again here, not only in the queue
        if report is None:
            raise IntakeError('Only an approved report with a current bank report can be dispatched')
        if dispatched_reports().filter(pk=report.pk).exists():
            # The same revision sent again. A corrected revision is not a resend.
            if not resend.get(vid):
                raise IntakeError(f'{valuation.report_number} has already been dispatched; give a reason to send it again', 409)
            sent_before.add(valuation.pk)
        reports.append((valuation, report))
    try:
        mode = int(data.get('mode'))
    except (TypeError, ValueError):
        mode = None
    if mode not in MODES:
        raise IntakeError('Choose how it is dispatched')
    courier = data.get('courier')
    courier = int(courier) if str(courier or '').isdigit() else None
    if mode == 1 and courier not in COURIERS:
        raise IntakeError('Choose the courier')
    if courier == 3 and not str(data.get('other_courier') or '').strip():
        raise IntakeError('Name the courier')
    try:
        status = int(data.get('status') or LYING)
    except ValueError:
        status = None
    if status not in STATUSES:
        raise IntakeError('Choose the dispatch status')
    outward = date_of(data, 'outward_date', 'outward date') or timezone.localdate()
    delivered = date_of(data, 'delivered_date', 'delivery date', not_before=outward)
    consignment = str(data.get('consignment_number') or '').strip()
    if status >= TRANSIT and mode in TRACKED and not consignment:
        raise IntakeError('Enter the consignment number once it is in transit')
    if status == DELIVERED and delivered is None:
        raise IntakeError('Enter the delivery date')
    if status != DELIVERED:
        delivered = None
    cost = money(data.get('cost'), 'Cost') if data.get('cost') not in (None, '') else None
    if cost is not None and cost < 0:
        raise IntakeError('Cost cannot be negative')

    for label, joined in (('The other documents', ','.join(others)), ('The report numbers', ','.join(v.report_number for v, _ in reports))):
        if len(joined) > 500:
            raise IntakeError(f'{label} come to {len(joined)} characters; the limit is 500. '
                              'Shorten the names, or send the rest in a second dispatch.')
    first = reports[0][0].case if reports else None
    account, name = actor(request.user)
    sequence = allocate('dispatch', m.Dispatch, 'number', 'D', within=m.Dispatch.objects.exclude(number__regex=OLD_SCHEME))
    d = m.Dispatch.objects.create(
        number=format_number('D', timezone.localdate(), sequence), local_sequence=sequence, request_key=key, request_hash=digest,
        client_name=(str(data.get('client_name') or '').strip() or (first.lead.office.name if first else ''))[:100],
        customer_name=(str(data.get('customer_name') or '').strip() or (first.borrower.name if first and first.borrower_id else ''))[:200],
        town=str(data.get('town') or '').strip()[:255], document_count=len(reports) + len(others),
        report_references=','.join(v.report_number for v, _ in reports), other_documents=','.join(others),
        mode=mode, status=status, courier=courier, other_courier=str(data.get('other_courier') or '').strip()[:500],
        consignment_number=consignment[:500], authorized_person=str(data.get('authorized_person') or '').strip()[:500],
        cost=cost, outward_date=outward, delivered_date=delivered, created_by=account, created_by_name=name[:200])
    m.DispatchItem.objects.bulk_create([
        m.DispatchItem(dispatch=d, position=n, reference=v.report_number, valuation=v, lead=v.case.lead, bank_report=r,
                       resolution=m.DispatchItem.CHOSEN, resend=v.pk in sent_before,
                       resend_reason=resend.get(str(v.pk), '')[:500] if v.pk in sent_before else '')
        for n, (v, r) in enumerate(reports)])
    record(request.user, d, action='create_dispatch')
    return JsonResponse(dispatch_json(d), status=201)


def dispatch_for(request, pk):
    head_office(request.user)
    return m.Dispatch.objects.select_for_update().get(pk=find(m.Dispatch, pk).pk)


@endpoint(['GET'])
def detail(request, pk):
    head_office(request.user)
    return JsonResponse(dispatch_json(find(m.Dispatch, pk)))


@endpoint(['POST'])
def advance(request, pk):
    d = dispatch_for(request, pk)
    if d.cancelled:
        raise IntakeError('This dispatch has been cancelled', 409)
    data = payload(request, ['status', 'consignment_number', 'delivered_date'])
    try:
        status = int(data.get('status'))
    except (TypeError, ValueError):
        status = None
    if status not in (TRANSIT, DELIVERED) or status <= (d.status or LYING):
        raise IntakeError(f'A dispatch {STATUSES.get(d.status, "")} can only move forward', 409)
    consignment = str(data.get('consignment_number') or '').strip() or d.consignment_number
    if d.mode in TRACKED and not consignment:
        raise IntakeError('Enter the consignment number')
    before = snapshot(d)
    if status == DELIVERED:
        d.delivered_date = date_of(data, 'delivered_date', 'delivery date', not_before=d.outward_date)
        if d.delivered_date is None:
            raise IntakeError('Enter the delivery date')
    d.status, d.consignment_number = status, consignment[:500]
    d.save(update_fields=['status', 'consignment_number', 'delivered_date'])
    record(request.user, d, before, action='advance_dispatch')
    return JsonResponse(dispatch_json(d))


@endpoint(['POST'])
def cancel(request, pk):
    d = dispatch_for(request, pk)
    if d.cancelled:
        raise IntakeError('This dispatch is already cancelled', 409)
    if d.status == DELIVERED:
        raise IntakeError('A delivered dispatch cannot be cancelled', 409)
    reason = str(payload(request, ['reason']).get('reason') or '').strip()
    if not reason:
        raise IntakeError('Enter why the dispatch is being cancelled')
    before = snapshot(d)
    d.cancelled, d.cancel_remark = True, reason[:4000]
    d.save(update_fields=['cancelled', 'cancel_remark'])
    record(request.user, d, before, action='cancel_dispatch')
    return JsonResponse(dispatch_json(d))


@endpoint(['GET'])
def history(request, pk):
    """Every dispatch that carried a report (legacy /dispatch_list/{reportNo})."""
    head_office(request.user)
    valuation = find(m.Valuation, pk)
    items = m.DispatchItem.objects.filter(valuation=valuation).select_related('dispatch').order_by('dispatch__outward_date')
    return JsonResponse({'valuation': valuation.pk, 'report_number': valuation.report_number,
                         'dispatches': [{**{k: v for k, v in dispatch_json(i.dispatch).items() if k != 'items'}, 'resend': i.resend,
                                         'resend_reason': i.resend_reason} for i in items]})
