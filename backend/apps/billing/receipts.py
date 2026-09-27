"""Cash receipts: maker, checker and verifier.

Traced to CashReceiptController (/add, /save, /checker_list, /edit, /verify_list,
/edit_verify, /verify/save, /view, /delete) and the enums CashRecieptRecievedEnum,
CaseReceiptPaymentModeEnum and ReceivedAgainstEnum.

A receipt passes three steps before it counts. The maker records it as an advance,
a recovery against an invoice, or other; the checker confirms it; the verifier
confirms it again, and only then does a recovery settle its invoice. Numbered C- +
MMYYDD + a counter continuing the legacy cash receipt series.

Legacy defects not carried over:
  * Verifying a recovery set the invoice's remaining amount to zero and then
    recorded the whole receipt as the excess (the 6,508-on-6,390 invoice). The
    balance is recomputed here from total, paid and write-offs.
  * A receipt could be verified, and so settle its invoice, more than once. The
    receipt's own id is the key of the payment it books, so it settles at most once.
  * Delete removed any receipt, even a verified recovery, while its invoice kept
    the payment. Receipts are voided with a reason, and only before verification.
  * Editing after checking left the check standing. A corrected receipt must be
    checked again.
  * Creation was not retry-safe; a repeated submission made a second receipt.

The legacy system also sent the payer an SMS on receipt. No SMS gateway is
configured here, so none is sent.

Roles overlap in the imported data (in about a quarter of verified receipts one
person performed two of the three steps). Under the interim access policy that is
allowed and shown, not refused.
"""
import datetime
import hashlib
import json
import uuid

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.audit.services import record, snapshot
from apps.billing.services import (ZERO, balances, check_scope, invoice_json, locked, paid_of, q, settle)
from apps.billing.valuation import money
from apps.common.http import IntakeError, endpoint, find, payload
from apps.documents.storage import file_json, serve
from apps.common.numbering import allocate, format_number
from apps.valuations.services import NOBODY, scoped_employee
from apps.valuations.verification import actor

ORIGINS = ('legacy_cash_receipt', 'local_cash_receipt')
RECEIVED_AS = dict(m.Receipt.RECEIVED_AS)
MODES = dict(m.Receipt.MODES)
INSTRUMENT = (2, 3)                     # cheque, draft
# The write contract: exactly the fields a maker or checker may send, for creation
# and correction alike. The screen builds its request from this same list; it
# previously sent the arrival date, which was missing here, and on correction
# spread response-only fields into the request, so both were refused (review R1).
FIELDS = ('received_as', 'invoice', 'amount', 'received_date', 'amount_received_on', 'payment_mode',
          'cheque_draft_number', 'cheque_draft_bank', 'issue_date', 'in_favour_of', 'payer_name', 'mobile',
          'remark', 'description')
PAGE_SIZE = 25


def visible(user):
    rows = m.Receipt.objects.filter(origin__in=ORIGINS)
    who = scoped_employee(user)
    if who is None:
        return rows
    if who is NOBODY:
        return rows.none()
    # A recovery is scoped only through its current invoice; any other receipt only
    # through its borrower. A recovery moved to another invoice once stayed visible
    # through its old borrower while showing the new invoice (review R2).
    return rows.filter(Q(received_as=2, invoice__valuation__case__lead__assigned_employee=who)
                       | (~Q(received_as=2) & Q(borrower__lead__assigned_employee=who)))


VERIFIED = Q(verified_by__isnull=False) | Q(verified_at__isnull=False)
LIVE = Q(voided_at__isnull=True)
STAGES = {'to_check': LIVE & ~VERIFIED & Q(checked_by__isnull=True, checked_at__isnull=True),
          'to_verify': LIVE & ~VERIFIED & (Q(checked_by__isnull=False) | Q(checked_at__isnull=False)),
          'verified': VERIFIED, 'voided': Q(voided_at__isnull=False)}


def stage_of(r):
    if r.voided_at:
        return 'voided'
    if r.verified_by_id or r.verified_at:
        return 'verified'
    return 'to_verify' if (r.checked_by_id or r.checked_at) else 'to_check'


def receipt_json(r):
    who = lambda account: account.name.strip() if account else ''
    steps = {'maker': r.maker_id, 'checker': r.checked_by_id, 'verifier': r.verified_by_id}
    same = [f'{a} and {b}' for a, b in (('maker', 'checker'), ('checker', 'verifier'), ('maker', 'verifier'))
            if steps[a] and steps[a] == steps[b]]
    invoice = r.invoice
    return {'id': r.pk, 'number': r.number, 'origin': 'local' if r.origin == 'local_cash_receipt' else 'legacy',
            'document': file_json(r.document) if r.document_id else None,
            'stage': stage_of(r), 'received_as': r.received_as, 'received_as_label': RECEIVED_AS.get(r.received_as, ''),
            'amount': str(q(r.amount)), 'received_date': r.received_date, 'amount_received_on': r.amount_received_on,
            'payment_mode': r.payment_mode, 'payment_mode_label': MODES.get(r.payment_mode, r.mode or ''),
            'cheque_draft_number': r.cheque_draft_number, 'cheque_draft_bank': r.cheque_draft_bank,
            'issue_date': r.issue_date, 'in_favour_of': r.in_favour_of, 'payer_name': r.payer_name, 'mobile': r.mobile,
            'remark': r.remark, 'description': r.description,
            'invoice': None if invoice is None else {'id': invoice.pk, 'number': invoice.number, 'total': str(q(invoice.billed_amount)),
                                                     'paid': str(paid_of(invoice)), 'cancelled': invoice.cancelled_at is not None},
            'maker': who(r.maker), 'checked_by': who(r.checked_by), 'checked_at': r.checked_at,
            'verified_by': who(r.verified_by), 'verified_at': r.verified_at,
            'voided_at': r.voided_at, 'void_reason': r.void_reason, 'voided_by': who(r.voided_by),
            'same_person': same, 'absorbs_legacy_entries': r.duplicates.count()}


def clean(data, user, existing=None):
    """Validate the maker's or checker's fields; returns the values to store."""
    try:
        received_as = int(data.get('received_as'))
    except (TypeError, ValueError):
        received_as = None
    if received_as not in RECEIVED_AS:
        raise IntakeError('Choose whether this is an advance, a recovery or other')
    invoice = None
    if received_as == 2:
        if not data.get('invoice'):
            raise IntakeError('A recovery must name the invoice it settles')
        invoice = find(m.Invoice, data['invoice'])
        check_scope(user, invoice)
        if invoice.cancelled_at:
            raise IntakeError('That invoice has been cancelled by a credit note', 409)
    amount = money(data.get('amount'), 'Amount')
    if amount <= 0:
        raise IntakeError('Enter the amount received')
    today = timezone.localdate()

    def day(field, label, required=False):
        if not data.get(field):
            if required:
                raise IntakeError(f'Enter the {label}')
            return None
        try:
            value = datetime.date.fromisoformat(str(data[field]))
        except ValueError:
            raise IntakeError(f'Enter the {label} as YYYY-MM-DD')
        if value > today:
            raise IntakeError(f'The {label} cannot be in the future')
        return value

    try:
        mode = int(data.get('payment_mode'))
    except (TypeError, ValueError):
        mode = None
    if mode not in MODES:
        raise IntakeError('Choose how the money was paid')
    number, bank = str(data.get('cheque_draft_number') or '').strip(), str(data.get('cheque_draft_bank') or '').strip()
    if mode in INSTRUMENT and not (number and bank):
        raise IntakeError(f'Enter the {MODES[mode].lower()} number and the bank it is drawn on')
    values = {'received_as': received_as, 'invoice': invoice, 'amount': amount,
              'received_date': day('received_date', 'receipt date') or today,
              'amount_received_on': day('amount_received_on', 'date the money arrived'),
              'payment_mode': mode, 'mode': str(mode), 'cheque_draft_number': number[:200], 'cheque_draft_bank': bank[:200],
              'issue_date': day('issue_date', 'cheque or draft date'), 'in_favour_of': str(data.get('in_favour_of') or '')[:500],
              'payer_name': str(data.get('payer_name') or '').strip()[:300], 'mobile': str(data.get('mobile') or '')[:500],
              'remark': str(data.get('remark') or '')[:2000], 'description': str(data.get('description') or '')[:500]}
    if not values['payer_name']:
        raise IntakeError('Enter who paid')
    # Every link derived from the invoice is recomputed, never left over. A recovery
    # takes its valuation, office and borrower from its current invoice, or none for
    # an offline invoice; an advance or other receipt has no invoice or valuation,
    # and keeps the office and borrower it was recorded against.
    if invoice is not None:
        case = invoice.valuation.case if invoice.valuation_id else None
        values['valuation'] = invoice.valuation if case else None
        values['office'] = case.lead.office if case else invoice.office
        values['borrower'] = case.borrower if case else None
    else:
        values['valuation'] = None
    return values


def fingerprint(data):
    return hashlib.sha256(json.dumps({f: str(data.get(f) or '').strip() for f in FIELDS}, sort_keys=True).encode()).hexdigest()


@endpoint(['GET', 'POST'])
def receipts(request):
    if request.method == 'POST':
        return create(request)
    stage = request.GET.get('stage', 'to_check')
    rows = visible(request.user)
    counts = {k: rows.filter(v).count() for k, v in STAGES.items()}
    rows = rows.filter(STAGES.get(stage, STAGES['to_check']))
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(number__icontains=text) | Q(payer_name__icontains=text) | Q(invoice__number__icontains=text)
                           | Q(cheque_draft_number__icontains=text))
    total = rows.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    items = rows.select_related('invoice', 'maker', 'checked_by', 'verified_by').order_by('-received_date', '-number')
    return JsonResponse({'stage': stage, 'total': total, 'page': page, 'page_size': PAGE_SIZE, 'counts': counts,
                         'results': [{'id': r.pk, 'number': r.number, 'received_date': r.received_date,
                                      'received_as': RECEIVED_AS.get(r.received_as, ''), 'payer': r.payer_name,
                                      'amount': str(q(r.amount)), 'mode': MODES.get(r.payment_mode, r.mode or ''),
                                      'invoice': r.invoice.number if r.invoice_id else '',
                                      'maker': r.maker.name.strip() if r.maker_id else ''}
                                     for r in items[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]]})


def create(request):
    data = payload(request, ['operation_id', *FIELDS])
    try:
        key = uuid.UUID(str(data.get('operation_id')))
    except (TypeError, ValueError):
        raise IntakeError('operation_id is required: a new UUID for each receipt')
    digest = fingerprint(data)
    done = m.Receipt.objects.filter(request_key=key).first()
    if done is not None:
        # Access is checked now, not as it was when the receipt was created: a replay
        # once returned the receipt after the user's grant was removed (review R3).
        if not visible(request.user).filter(pk=done.pk).exists():
            raise IntakeError('Receipt not found', 404)
        if done.request_hash != digest:
            raise IntakeError('This operation_id was already used for a different receipt', 409)
        return JsonResponse({**receipt_json(done), 'replayed': True})
    values = clean(data, request.user)
    account, _ = actor(request.user)
    series = m.Receipt.objects.filter(origin__in=ORIGINS)
    sequence = allocate('cash_receipt', m.Receipt, 'number', 'C', within=series)
    receipt = m.Receipt.objects.create(origin='local_cash_receipt', number=format_number('C', timezone.localdate(), sequence),
                                       request_key=key, request_hash=digest, maker=account, **values)
    record(request.user, receipt, action='make_cash_receipt')
    return JsonResponse(receipt_json(receipt), status=201)


def receipt_for(request, pk, lock=True):
    receipt = find(m.Receipt, pk)
    if not visible(request.user).filter(pk=receipt.pk).exists():
        raise IntakeError('Receipt not found', 404)
    return m.Receipt.objects.select_for_update().get(pk=receipt.pk) if lock else receipt


@endpoint(['GET', 'PUT'])
def receipt(request, pk):
    if request.method == 'GET':
        return JsonResponse(receipt_json(receipt_for(request, pk, lock=False)))
    r = receipt_for(request, pk)
    if stage_of(r) not in ('to_check', 'to_verify'):
        raise IntakeError(f'A {stage_of(r).replace("_", " ")} receipt cannot be changed', 409)
    values = clean(payload(request, list(FIELDS)), request.user, r)
    before = snapshot(r)
    for field, value in values.items():
        setattr(r, field, value)
    r.checked_by, r.checked_at = None, None             # a corrected receipt is checked again
    r.save()
    record(request.user, r, before, action='correct_cash_receipt')
    return JsonResponse(receipt_json(r))


@endpoint(['POST'])
def check(request, pk):
    r = receipt_for(request, pk)
    if stage_of(r) != 'to_check':
        raise IntakeError(f'This receipt is {stage_of(r).replace("_", " ")}, not awaiting a check', 409)
    account, _ = actor(request.user)
    before = snapshot(r)
    r.checked_by, r.checked_at = account, timezone.now()
    r.save(update_fields=['checked_by', 'checked_at'])
    record(request.user, r, before, action='check_cash_receipt')
    return JsonResponse(receipt_json(r))


@endpoint(['POST'])
def verify(request, pk):
    r = receipt_for(request, pk)
    if stage_of(r) != 'to_verify':
        raise IntakeError(f'This receipt is {stage_of(r).replace("_", " ")}, not awaiting verification', 409)
    account, name = actor(request.user)
    invoice = None
    if r.received_as == 2 and r.invoice_id:
        invoice = locked(r.invoice_id, request.user)            # refuses a credited invoice
        owed, _ = balances(invoice.billed_amount, paid_of(invoice), invoice.bad_debt_amount)
        # Of the 29 legacy recoveries left unverified, 27 are against invoices
        # already fully paid: verifying them would overpay. Genuine overpayments do
        # happen, so it is allowed, but only when confirmed.
        confirmed = payload(request, ['confirm_overpayment']).get('confirm_overpayment') is True
        if q(r.amount) > owed and not confirmed:
            raise IntakeError(f'Invoice {invoice.number} has Rs {owed} outstanding and this receipt is Rs {q(r.amount)}. '
                              f'Confirm to record Rs {q(r.amount) - owed} as received in excess, or void the receipt.', 409)
    before = snapshot(r)
    # The Boolean is kept in step with the workflow; it had stayed False, so admin
    # lists and filters disagreed with the stage (review R6).
    r.verified_by, r.verified_at, r.verified = account, timezone.now(), True
    r.save(update_fields=['verified_by', 'verified_at', 'verified'])
    record(request.user, r, before, action='verify_cash_receipt')
    if invoice is not None:
        before = snapshot(invoice)
        # The receipt's id keys the payment, so a receipt settles its invoice once.
        m.FinancialOperation.objects.create(key=r.pk, kind=m.FinancialOperation.PAYMENT, invoice=invoice,
                                            payload_hash='cash_receipt', amount=r.amount, receipt=r, by=account,
                                            by_name=name[:200])
        invoice.legacy_paid_amount = paid_of(invoice) + q(r.amount)
        invoice.payment_date = r.amount_received_on or r.received_date
        settle(invoice)
        invoice.save()
        record(request.user, invoice, before, action='settle_invoice_by_receipt')
        if invoice.valuation_id:
            v = invoice.valuation
            before = snapshot(v)
            v.advance_collected, v.remaining_amount = invoice.legacy_paid_amount, invoice.legacy_remaining_amount
            v.save(update_fields=['advance_collected', 'remaining_amount'])
            record(request.user, v, before, action='settle_valuation_by_receipt')
    return JsonResponse(receipt_json(r))


@endpoint(['POST'])
def void(request, pk):
    r = receipt_for(request, pk)
    if stage_of(r) not in ('to_check', 'to_verify'):
        raise IntakeError('Only an unverified receipt can be voided; a verified receipt stays on record', 409)
    reason = str(payload(request, ['reason']).get('reason') or '').strip()
    if not reason:
        raise IntakeError('Enter why the receipt is being voided')
    account, _ = actor(request.user)
    before = snapshot(r)
    r.voided_at, r.void_reason, r.voided_by = timezone.now(), reason[:4000], account
    r.save(update_fields=['voided_at', 'void_reason', 'voided_by'])
    record(request.user, r, before, action='void_cash_receipt')
    return JsonResponse(receipt_json(r))


@endpoint(['GET'])
def document(request, pk):
    """A receipt's scanned document. 9,641 legacy receipts carry one, which no screen
    could open. Visible to exactly those who may see the receipt."""
    r = visible(request.user).filter(pk=pk).select_related('document').first()
    if r is None or r.document_id is None:
        raise IntakeError('Document not found', 404)
    return serve(r.document)
