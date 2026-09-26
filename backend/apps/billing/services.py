"""Invoicing: issuing the tax invoice, recording payments, write-offs and credit notes.

Traced to InvoiceController /invoice_view, /saveInvoice, /update_payment and
/save_update_invoice, generateInvoiceNo, InvoiceDAOImpl.getMaxInvoiceNo,
invoice_view.jsp and InvoiceNewTestUtil.

Issuing. Allowed for a submitted valuation with a generated bank report and no
standing invoice; the legacy invoice reads the liable field assessor from the bank
report, so it always followed it. One standing invoice per valuation, as in all
11,927 imported. Numbered I- + MMYYDD + a counter continuing the online series
(11,946); offline invoices share the I- format but kept their own counter (to
15,556), so the seed reads online and locally issued invoices only.

GST. Each charge carries 18% GST. Intra-state supply splits it into CGST and SGST
of 9% each; inter-state puts it all into IGST. The legacy page computed this in
the browser and the server stored what it was sent, and its running totals were
never reset, so they grew on every recalculation; 342 imported invoices do not
match their own lines. Taxes are computed here in Decimal, to the paisa, per line.
The lines are snapshotted onto the invoice, since a tax invoice must not change
after issue. The place of supply is suggested by comparing the state code of
Omen's GSTIN with the billed party's, and may be overridden.

Whose GSTIN is billed follows GstEnum: the client, the client customer, or another
party with its GSTIN. Omen's own GSTIN is the firm's, 23AABFO1645E1ZS, not the
account's: one of the four imported accounts carries a different GSTIN
(23AAACP0165G1ZX, apparently the bank's own), which must not print as Omen's.

Balances. total = paid + remaining + bad debt - excess, the identity 11,122
imported invoices satisfy. Two legacy defects break it:
  * On issue, an advance above the total set remaining to zero and then recorded
    the excess as the remaining amount, now zero, so overpayments were lost.
  * On payment, remaining was computed as payment minus balance, the wrong way
    round, and the invoice date could be edited after issue.
805 imported invoices fail the identity. Here the balance is recomputed on every
change, and the invoice and its date never change once issued.

payment_status holds InvoicePaymentTypeEnum: 1 Fully Payment, 2 Partial Payment,
empty for no payment yet. The separate payment_type column is empty on every
imported invoice and is not used. 334 partial payments were closed by writing
off the remainder, which the write-off action supports.

Credit notes. The legacy system could not reverse an invoice: 21 valuations were
cancelled with their invoice still standing. An invoice is never edited or
deleted; it is reversed in full by a credit note (CN- + MMYYDD + counter), which
records any refund due. That releases the billing lock and allows cancellation.
"""
import datetime
import re
import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from django.conf import settings
from django.db.models import OuterRef, Q, Sum
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.reports.services import current as current_report
from apps.documents.storage import file_json, serve
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.common.numbering import allocate, format_number
from apps.billing.valuation import GST_RATE, PAISA, discount_id, money
from apps.valuations.services import in_scope, scope_cases, scoped_employee
from apps.valuations.verification import actor
from apps.common.words import amount_words

FIRM_GSTIN = getattr(settings, 'OMEN_GSTIN', '23AABFO1645E1ZS')
GSTIN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')
HALF_RATE = GST_RATE / 2
PAGE_SIZE = 25
ZERO = Decimal('0')


def q(value):
    return (value or ZERO).quantize(PAISA, ROUND_HALF_UP)


def standing(valuation):
    return m.Invoice.objects.filter(valuation=valuation, cancelled_at__isnull=True).order_by('-created_at').first()


def taxes(amount, place):
    if place == 'intra':
        half = q(amount * HALF_RATE)
        return half, half, ZERO
    return ZERO, ZERO, q(amount * GST_RATE)


def party_gstin(valuation, party, other=''):
    case = valuation.case
    if party == 1:
        return (case.lead.office.gstin or '').strip().upper()
    if party == 2:
        return (case.borrower.gst_number or '').strip().upper() if case.borrower_id else ''
    return (other or '').strip().upper()


def suggested_place(gstin):
    """Intra-state when the billed party's GSTIN is registered in Omen's state."""
    return 'intra' if not gstin or gstin[:2] == FIRM_GSTIN[:2] else 'inter'


def draft_lines(valuation, place):
    discount = discount_id()
    lines = []
    for n, charge in enumerate(m.ValuationCharge.objects.filter(valuation=valuation).select_related('charge_type')
                               .order_by('charge_type__source_sequence', 'charge_type__name')):
        amount = q(charge.amount)
        if charge.charge_type_id == discount:
            amount = -abs(amount)          # a discount always reduces the bill
        if amount == ZERO:
            continue
        cgst, sgst, igst = taxes(amount, place)
        lines.append({'charge_type': charge.charge_type_id, 'description': charge.charge_type.name.strip() if charge.charge_type else 'Charge',
                      'amount': amount, 'cgst': cgst, 'sgst': sgst, 'igst': igst, 'total': amount + cgst + sgst + igst,
                      'position': n})
    taxable = sum((l['amount'] for l in lines), ZERO)
    tax = sum((l['cgst'] + l['sgst'] + l['igst'] for l in lines), ZERO)
    return lines, taxable, tax, taxable + tax


def balances(total, paid, bad_debt):
    # Quantized after max(): max(ZERO, x) returns the bare ZERO, which prints as
    # '0' where every other amount prints to the paisa.
    remaining = q(max(ZERO, q(total) - q(bad_debt) - q(paid)))
    excess = q(max(ZERO, q(paid) + q(bad_debt) - q(total)))
    return remaining, excess


OFFLINE = 'legacy_offline_invoice'
PAYMENT_ORIGINS = ('local_invoice_payment', 'legacy_offline_amount_received')


def is_offline(invoice):
    return invoice.origin == OFFLINE


def paid_of(invoice):
    """What has been paid against an invoice. An untouched offline invoice stored
    no paid amount, so it is the advance plus its recorded payments; once an
    operation is applied here that figure is stored and added to."""
    if is_offline(invoice) and invoice.legacy_paid_amount is None:
        recorded = (invoice.receipts.filter(origin='legacy_offline_amount_received', duplicate_of__isnull=True)
                    .aggregate(s=Sum('amount'))['s'])
        return q(invoice.advance_amount) + q(recorded)
    return q(invoice.legacy_paid_amount)


def check_scope(user, invoice):
    """An invoice on a valuation follows that case's scope. An offline invoice
    belongs to no case, so there is no assignment to restrict by: only an
    unrestricted user may see it. Scope was previously checked only when an
    invoice had a valuation, so an offline one opened by id was unchecked."""
    if invoice.valuation_id:
        in_scope(user, invoice.valuation.case)
    elif scoped_employee(user) is not None:
        raise IntakeError('Invoice not found', 404)


def invoice_json(invoice):
    total, paid, bad = q(invoice.billed_amount), paid_of(invoice), q(invoice.bad_debt_amount)
    remaining, excess = balances(total, paid, bad)
    local = invoice.local_sequence is not None
    lines = [{'description': l.description, 'amount': str(q(l.net_amount)), 'cgst': str(q(l.cgst)), 'sgst': str(q(l.sgst)),
              'igst': str(q(l.igst)), 'total': str(q(l.total_amount))} for l in invoice.lines.order_by('position')]
    if not lines and invoice.valuation_id:
        lines = [{'description': c.charge_type.name.strip() if c.charge_type else 'Charge', 'amount': str(q(c.amount)),
                  'cgst': str(q(c.cgst)), 'sgst': str(q(c.sgst)), 'igst': str(q(c.igst)), 'total': str(q(c.total_amount))}
                 for c in m.ValuationCharge.objects.filter(valuation=invoice.valuation).select_related('charge_type')
                 .order_by('charge_type__source_sequence') if c.amount]
    v = invoice.valuation
    status = {'1': 'Fully paid', '2': 'Partly paid'}.get(invoice.legacy_status, 'Unpaid')
    return {'id': invoice.pk, 'number': invoice.number, 'origin': 'local' if local else invoice.origin,
            'issued_on': invoice.issued_date, 'due_on': invoice.due_date,
            'valuation': invoice.valuation_id, 'report_number': v.report_number if v else '',
            'lead_number': v.case.lead.number if v else '', 'borrower': v.case.borrower.name if v and v.case.borrower_id else '',
            'place_of_supply': invoice.get_place_of_supply_display() if invoice.place_of_supply else '',
            'gstin_party': invoice.get_gstin_party_display() if invoice.gstin_party else '',
            'account': invoice.issuer_account.name.strip() if invoice.issuer_account_id else '',
            'lines': lines, 'total': str(total), 'paid': str(paid), 'bad_debt': str(bad), 'bad_debt_remark': invoice.bad_debt_remark,
            'remaining': str(remaining), 'excess': str(excess),
            'recorded_remaining': str(q(invoice.legacy_remaining_amount)), 'recorded_excess': str(q(invoice.excess_amount)),
            'payment_status': status, 'cancelled': invoice.cancelled_at is not None, 'cancel_reason': invoice.cancel_reason,
            'document': file_json(invoice.document),
            'payments': [{'on': r.received_date, 'amount': str(q(r.amount)), 'by': r.payer_name, 'mode': r.mode, 'remark': r.remark,
                          'recorded': 'previous system' if r.origin.startswith('legacy') else 'here'}
                         for r in invoice.receipts.filter(origin__in=PAYMENT_ORIGINS, duplicate_of__isnull=True)
                         .order_by('received_date', 'created_at')],
            'offline': is_offline(invoice),
            'advance': str(q(invoice.advance_amount)) if is_offline(invoice) else None,
            'billed_to': {'name': invoice.billed_to_name, 'customer': invoice.billed_customer_name,
                          'branch': invoice.billed_branch_name, 'branch_code': invoice.billed_branch_code} if is_offline(invoice) else None,
            'references': {'lead': invoice.reference_lead, 'work_order': invoice.reference_work_order,
                           'report': invoice.reference_report,
                           'service': invoice.service.name if invoice.service_id else '',
                           'subtype': invoice.subtype.name if invoice.subtype_id else '',
                           'liable': invoice.liable_employee.name if invoice.liable_employee_id else '',
                           'doer': invoice.doer_employee.name if invoice.doer_employee_id else ''} if is_offline(invoice) else None,
            'number_shared': (m.Invoice.objects.filter(origin=invoice.origin, number=invoice.number).exclude(pk=invoice.pk).count()
                              if invoice.number else 0),
            'credit_notes': [{'id': c.pk, 'number': c.number, 'on': c.issued_on, 'total': str(q(c.total_amount)),
                              'refund_due': str(q(c.refund_due)), 'reason': c.reason, 'document': file_json(c.document)}
                             for c in invoice.credit_notes.order_by('created_at')]}


def issue_blockers(valuation):
    reasons = []
    if valuation.legacy_status != 'Submit':
        reasons.append(f'The valuation is {valuation.legacy_status or "not submitted"}')
    if current_report(valuation) is None:
        reasons.append('Generate the bank report first')
    if standing(valuation) is not None:
        reasons.append('This valuation already has an invoice; issue a credit note to replace it')
    if not m.ValuationCharge.objects.filter(valuation=valuation).exclude(amount=None).exclude(amount=0).exists():
        reasons.append('Enter the billing first')
    return reasons


@endpoint(['GET', 'POST'])
def for_valuation(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    if request.method == 'POST':
        invoice = issue(request, valuation)
        return JsonResponse(invoice_json(invoice), status=201)
    party = int(request.GET.get('party') or 1)
    gstin = party_gstin(valuation, party, request.GET.get('other_gstin', ''))
    place = request.GET.get('place') or suggested_place(gstin)
    lines, taxable, tax, total = draft_lines(valuation, place)
    advance = q(valuation.advance_collected)
    remaining, excess = balances(total, advance, ZERO)
    borrower = valuation.case.borrower if valuation.case.borrower_id else None
    return JsonResponse({'valuation': valuation.pk, 'report_number': valuation.report_number,
                         'blockers': issue_blockers(valuation), 'standing': invoice_json(standing(valuation)) if standing(valuation) else None,
                         'party': party, 'gstin': gstin, 'place': place, 'suggested_place': suggested_place(gstin),
                         'firm_gstin': FIRM_GSTIN,
                         'lines': [{**l, **{k: str(l[k]) for k in ('amount', 'cgst', 'sgst', 'igst', 'total')}} for l in lines],
                         'taxable': str(taxable), 'tax': str(tax), 'total': str(total), 'advance': str(advance),
                         'remaining': str(remaining), 'excess': str(excess),
                         'accounts': [{'id': a.pk, 'name': a.name.strip(), 'ifsc': a.ifsc_code, 'code': a.code}
                                      for a in m.IssuerAccount.objects.order_by('code')],
                         'default_payer': borrower.payer if borrower else None})


def issue(request, valuation):
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    reasons = issue_blockers(valuation)
    if reasons:
        raise IntakeError('; '.join(reasons), 409)
    data = payload(request, ['place', 'party', 'other_gstin', 'account', 'due_date', 'payer'])
    if data.get('place') not in ('intra', 'inter'):
        raise IntakeError('Choose intra-state or inter-state supply')
    try:
        party = int(data.get('party'))
    except (TypeError, ValueError):
        party = None
    if party not in (1, 2, 3):
        raise IntakeError('Choose whose GSTIN is billed')
    other = str(data.get('other_gstin') or '').strip().upper()
    if party == 3:
        if not GSTIN.match(other):
            raise IntakeError('Enter a valid 15-character GSTIN')
    else:
        other = ''
    if not data.get('account'):
        raise IntakeError("Choose the Omen account the invoice is paid into")
    account = find(m.IssuerAccount, data['account'])
    today = timezone.localdate()
    try:
        due = datetime.date.fromisoformat(data['due_date']) if data.get('due_date') else today + datetime.timedelta(days=15)
    except ValueError:
        raise IntakeError('Enter the due date as YYYY-MM-DD')
    if due < today:
        raise IntakeError('The due date cannot be before the invoice date')
    payer = data.get('payer')
    payer = int(payer) if str(payer or '').isdigit() and int(payer) in (1, 2) else None

    lines, taxable, tax, total = draft_lines(valuation, data['place'])
    if total < 0:
        raise IntakeError('The invoice total cannot be negative')
    advance = q(valuation.advance_collected)
    remaining, excess = balances(total, advance, ZERO)
    online = m.Invoice.objects.filter(Q(origin='legacy_invoice') | Q(local_sequence__isnull=False))
    sequence = allocate('invoice', m.Invoice, 'number', 'I', within=online)
    account_person, name = actor(request.user)
    invoice = m.Invoice.objects.create(
        valuation=valuation, office=valuation.case.lead.office, origin='local_invoice',
        number=format_number('I', today, sequence), local_sequence=sequence, issued_date=today, due_date=due,
        billed_amount=total, legacy_paid_amount=advance, legacy_remaining_amount=remaining, excess_amount=excess,
        bad_debt_amount=ZERO, remaining_words=amount_words(round(remaining)),
        legacy_status='1' if remaining == 0 and total > 0 else ('2' if advance > 0 else ''),
        place_of_supply=data['place'], gstin_party=party, other_gstin=other, payer=payer, issuer_account=account,
        issued_by=account_person, issued_by_name=name[:200])
    m.InvoiceLine.objects.bulk_create([m.InvoiceLine(
        invoice=invoice, charge_type_id=l['charge_type'], description=l['description'], net_amount=l['amount'],
        tax_amount=l['cgst'] + l['sgst'] + l['igst'], cgst=l['cgst'], sgst=l['sgst'], igst=l['igst'],
        total_amount=l['total'], position=l['position']) for l in lines])
    # Keep the valuation's billing consistent with what was invoiced.
    before = snapshot(valuation)
    for charge in m.ValuationCharge.objects.filter(valuation=valuation):
        match = next((l for l in lines if l['charge_type'] == charge.charge_type_id), None)
        if match:
            charge.cgst, charge.sgst, charge.igst, charge.total_amount = match['cgst'], match['sgst'], match['igst'], match['total']
            charge.save(update_fields=['cgst', 'sgst', 'igst', 'total_amount'])
    valuation.total_billing_amount, valuation.total_after_tax = taxable, total
    valuation.total_after_tax_words, valuation.remaining_amount = amount_words(round(total)), remaining
    valuation.save(update_fields=['total_billing_amount', 'total_after_tax', 'total_after_tax_words', 'remaining_amount'])
    record(request.user, valuation, before, action='invoice_valuation')
    record(request.user, invoice, action='issue_invoice')
    attach_document(invoice)
    return invoice


def attach_document(invoice, credit=None):
    from apps.billing.pdf import render
    content = render(invoice, credit)
    folder = f'invoices/{invoice.pk}'
    name = f'{credit.number if credit else invoice.number}.pdf'
    relative = f'{folder}/{uuid.uuid4().hex}.pdf'
    document = m.Document.objects.create(storage_provider='local', storage_key=relative, original_name=name,
                                         media_type='application/pdf', size_bytes=len(content))
    target = credit or invoice
    target.document = document
    target.save(update_fields=['document'])
    path = Path(settings.MEDIA_ROOT) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def locked(pk, user):
    invoice = find(m.Invoice, pk)
    check_scope(user, invoice)
    invoice = m.Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.cancelled_at:
        raise IntakeError('This invoice has been cancelled by a credit note', 409)
    if is_offline(invoice) and invoice.legacy_paid_amount is None:
        # Fix the derived paid amount before the first operation adds to it.
        invoice.legacy_paid_amount = paid_of(invoice)
    return invoice


def settle(invoice):
    remaining, excess = balances(invoice.billed_amount, invoice.legacy_paid_amount, invoice.bad_debt_amount)
    invoice.legacy_remaining_amount, invoice.excess_amount = remaining, excess
    invoice.remaining_words = amount_words(round(remaining))
    paid = q(invoice.legacy_paid_amount)
    invoice.legacy_status = '1' if remaining == 0 else ('2' if paid > 0 or q(invoice.bad_debt_amount) > 0 else '')
    invoice.payment_type = int(invoice.legacy_status) if invoice.legacy_status else None



def operation(request_data, kind, invoice, fields):
    """Replay an already-applied operation, or return (key, payload hash) for a
    new one. Called with the invoice row locked, so identical concurrent retries
    queue and the later one finds the first; the unique key is the backstop."""
    import hashlib, json as _json
    raw = request_data.get('operation_id')
    try:
        key = uuid.UUID(str(raw))
    except (TypeError, ValueError):
        raise IntakeError('operation_id is required: a new UUID for each intended operation')
    canonical = _json.dumps({'kind': kind, 'invoice': str(invoice.pk),
                             **{f: str(request_data.get(f) or '').strip() for f in fields}}, sort_keys=True)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    done = m.FinancialOperation.objects.filter(key=key).first()
    if done is None:
        return key, digest, None
    if done.payload_hash != digest:
        raise IntakeError('This operation_id was already used for a different request', 409)
    return key, digest, done

@endpoint(['POST'])
def payment(request, pk):
    invoice = locked(pk, request.user)
    data = payload(request, ['operation_id', 'amount', 'date', 'mode', 'payer_name', 'remark'])
    key, digest, done = operation(data, m.FinancialOperation.PAYMENT, invoice, ['amount', 'date', 'mode', 'payer_name', 'remark'])
    if done:
        return JsonResponse({**invoice_json(invoice), 'replayed': True})
    amount = money(data.get('amount'), 'Amount received')
    if amount <= 0:
        raise IntakeError('Enter the amount received')
    today = timezone.localdate()
    try:
        on = datetime.date.fromisoformat(data['date']) if data.get('date') else today
    except ValueError:
        raise IntakeError('Enter the date as YYYY-MM-DD')
    if on > today:
        raise IntakeError('The payment date cannot be in the future')
    if invoice.issued_date and on < invoice.issued_date and invoice.local_sequence:
        raise IntakeError('The payment date cannot be before the invoice date')
    before = snapshot(invoice)
    receipt = m.Receipt.objects.create(origin='local_invoice_payment', invoice=invoice, valuation=invoice.valuation,
                                       office=invoice.office, received_date=on, amount=amount,
                                       mode=str(data.get('mode') or '')[:40], payer_name=str(data.get('payer_name') or '')[:300],
                                       remark=str(data.get('remark') or '')[:2000])
    account, name = actor(request.user)
    m.FinancialOperation.objects.create(key=key, kind=m.FinancialOperation.PAYMENT, invoice=invoice, payload_hash=digest,
                                        amount=amount, receipt=receipt, by=account, by_name=name[:200])
    invoice.legacy_paid_amount = q(invoice.legacy_paid_amount) + amount
    invoice.payment_date = on
    settle(invoice)
    invoice.save()
    record(request.user, invoice, before, action='record_invoice_payment')
    return JsonResponse(invoice_json(invoice))


@endpoint(['POST'])
def write_off(request, pk):
    invoice = locked(pk, request.user)
    data = payload(request, ['operation_id', 'amount', 'remark'])
    key, digest, done = operation(data, m.FinancialOperation.WRITE_OFF, invoice, ['amount', 'remark'])
    if done:
        return JsonResponse({**invoice_json(invoice), 'replayed': True})
    amount = money(data.get('amount'), 'Write-off')
    remark = str(data.get('remark') or '').strip()
    remaining, _ = balances(invoice.billed_amount, invoice.legacy_paid_amount, invoice.bad_debt_amount)
    if amount <= 0:
        raise IntakeError('Enter the amount to write off')
    if amount > remaining:
        raise IntakeError(f'Only {remaining} is outstanding')
    if not remark:
        raise IntakeError('Enter why it is being written off')
    before = snapshot(invoice)
    account, name = actor(request.user)
    m.FinancialOperation.objects.create(key=key, kind=m.FinancialOperation.WRITE_OFF, invoice=invoice, payload_hash=digest,
                                        amount=amount, remark=remark[:4000], by=account, by_name=name[:200])
    invoice.bad_debt_amount = q(invoice.bad_debt_amount) + amount
    invoice.bad_debt_remark = remark[:4000]
    settle(invoice)
    invoice.save()
    record(request.user, invoice, before, action='write_off_invoice')
    return JsonResponse(invoice_json(invoice))


@endpoint(['POST'])
def credit_note(request, pk):
    invoice = locked(pk, request.user)
    reason = str(payload(request, ['reason']).get('reason') or '').strip()
    if not reason:
        raise IntakeError('Enter why the invoice is being cancelled')
    lines = list(invoice.lines.all())
    if lines:
        taxable = sum((q(l.net_amount) for l in lines), ZERO)
        tax = sum((q(l.cgst) + q(l.sgst) + q(l.igst) for l in lines), ZERO)
    else:            # an imported invoice keeps its taxes on the valuation's billing
        charges = m.ValuationCharge.objects.filter(valuation=invoice.valuation) if invoice.valuation_id else m.ValuationCharge.objects.none()
        taxable = q(charges.aggregate(s=Sum('amount'))['s'])
        tax = q(sum((q(c.cgst) + q(c.sgst) + q(c.igst) for c in charges), ZERO))
    total = q(invoice.billed_amount)
    today = timezone.localdate()
    # CN-, not C-: legacy cash receipts are numbered C- + MMYYDD + counter, so a C-
    # credit note could carry the same number as a cash receipt issued that day.
    sequence = allocate('credit_note', m.CreditNote, 'number', 'CN')
    account, name = actor(request.user)
    before = snapshot(invoice)
    credit = m.CreditNote.objects.create(invoice=invoice, number=format_number('CN', today, sequence), local_sequence=sequence,
                                         issued_on=today, taxable_amount=taxable, tax_amount=tax, total_amount=total,
                                         reason=reason[:4000], refund_due=paid_of(invoice),
                                         issued_by=account, issued_by_name=name[:200])
    invoice.cancelled_at, invoice.cancel_reason = timezone.now(), reason[:4000]
    invoice.save(update_fields=['cancelled_at', 'cancel_reason'])
    record(request.user, invoice, before, action='credit_note_invoice')
    attach_document(invoice, credit)
    return JsonResponse(invoice_json(invoice))


@endpoint(['GET'])
def detail(request, pk):
    invoice = find(m.Invoice, pk)
    check_scope(request.user, invoice)
    return JsonResponse(invoice_json(invoice))


@endpoint(['GET'])
def document(request, pk):
    invoice = find(m.Invoice, pk)
    check_scope(request.user, invoice)
    return serve(invoice.document)


@endpoint(['GET'])
def credit_document(request, pk):
    credit = find(m.CreditNote, pk)
    check_scope(request.user, credit.invoice)
    return serve(credit.document)


def offline_queryset(user):
    """Offline invoices with their outstanding balance, visible only to an
    unrestricted user (see check_scope)."""
    from django.db.models import Case, DecimalField, ExpressionWrapper, F, Subquery, Value, When
    from django.db.models.functions import Coalesce
    money_field = DecimalField(max_digits=24, decimal_places=6)
    recorded = (m.Receipt.objects.filter(invoice=OuterRef('pk'), origin='legacy_offline_amount_received',
                                         duplicate_of__isnull=True)
                .values('invoice').annotate(s=Sum('amount')).values('s'))
    nought = Value(ZERO, output_field=money_field)
    paid = Case(When(legacy_paid_amount__isnull=False, then=F('legacy_paid_amount')),
                default=Coalesce(F('advance_amount'), nought) + Coalesce(Subquery(recorded, output_field=money_field), nought),
                output_field=money_field)
    rows = (m.Invoice.objects.filter(origin=OFFLINE, cancelled_at__isnull=True)
            .annotate(outstanding=ExpressionWrapper(Coalesce(F('billed_amount'), nought) - paid
                                                    - Coalesce(F('bad_debt_amount'), nought), output_field=money_field)))
    # Emptied after annotating, so a restricted user's empty queue can still be
    # filtered by balance.
    return rows.none() if scoped_employee(user) is not None else rows


@endpoint(['GET'])
def queue(request):
    state = request.GET.get('state', 'to_invoice')
    cases = scope_cases(request.user, m.Case.objects.all())
    text = request.GET.get('q', '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    reported = m.BankReport.objects.filter(superseded_at__isnull=True).values('valuation')
    standing_ids = m.Invoice.objects.filter(cancelled_at__isnull=True, valuation__isnull=False).values('valuation')
    to_invoice = m.Valuation.objects.filter(legacy_status='Submit', case__in=cases, pk__in=reported).exclude(pk__in=standing_ids)
    invoices = m.Invoice.objects.filter(valuation__case__in=cases)
    active = invoices.filter(cancelled_at__isnull=True)
    buckets = {'to_invoice': to_invoice,
               'unpaid': active.filter(legacy_remaining_amount__gt=0),
               'paid': active.filter(Q(legacy_remaining_amount__lte=0) | Q(legacy_remaining_amount__isnull=True)),
               'cancelled': invoices.filter(cancelled_at__isnull=False),
               'offline': offline_queryset(request.user)}
    rows = buckets.get(state, to_invoice)
    if state == 'offline' and request.GET.get('due') == '1':
        rows = rows.filter(outstanding__gt=Decimal('0.5'))
    if text:
        if state == 'offline':
            rows = rows.filter(Q(number__icontains=text) | Q(billed_to_name__icontains=text) | Q(billed_customer_name__icontains=text)
                               | Q(reference_report__icontains=text) | Q(reference_lead__icontains=text))
        elif state == 'to_invoice':
            rows = rows.filter(Q(report_number__icontains=text) | Q(case__lead__number__icontains=text) | Q(case__borrower__name__icontains=text))
        else:
            rows = rows.filter(Q(number__icontains=text) | Q(valuation__report_number__icontains=text) | Q(valuation__case__borrower__name__icontains=text))
    total = rows.count()
    if state == 'offline':
        items = rows.order_by('-outstanding', '-issued_date')[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        results = [{'id': i.pk, 'number': i.number, 'issued_on': i.issued_date, 'billed_to': i.billed_to_name,
                    'customer': i.billed_customer_name, 'report_number': i.reference_report,
                    'total': str(q(i.billed_amount)), 'remaining': str(q(max(i.outstanding, ZERO)))} for i in items]
    elif state == 'to_invoice':
        items = rows.select_related('case__lead', 'case__borrower').order_by('-valuation_date')[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        results = [{'valuation': v.pk, 'report_number': v.report_number, 'lead_number': v.case.lead.number,
                    'borrower': v.case.borrower.name if v.case.borrower_id else '', 'total': str(q(v.total_after_tax))} for v in items]
    else:
        items = rows.select_related('valuation__case__borrower').order_by('-issued_date', '-number')[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        results = [{'id': i.pk, 'number': i.number, 'issued_on': i.issued_date, 'report_number': i.valuation.report_number if i.valuation_id else '',
                    'borrower': i.valuation.case.borrower.name if i.valuation_id and i.valuation.case.borrower_id else '',
                    'total': str(q(i.billed_amount)), 'remaining': str(q(i.legacy_remaining_amount))} for i in items]
    return JsonResponse({'state': state, 'total': total, 'page': page, 'page_size': PAGE_SIZE,
                         'counts': {**{k: v.count() for k, v in buckets.items()},
                                    'offline_due': buckets['offline'].filter(outstanding__gt=Decimal('0.5')).count()},
                         'results': results})
