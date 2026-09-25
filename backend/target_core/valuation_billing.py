"""Valuation billing: the charge lines and the provisional totals.

Traced to ValuationController /billing and /saveBilling and valuation_billing.jsp.

Every valuation carries one line per charge head (professional charges, discount,
photo charges, visit expenses, additional work, courier). The legacy page computed
every total in the browser and the server stored whatever it was sent:

    total      = sum of line amounts
    after tax  = total x 1.18                 (a flat 18% GST)
    remaining  = after tax - advance paid

Three legacy defects are not carried over, and totals are now computed here:
  * After-tax was recalculated on keypress, which fires before the typed
    character lands, while the total updated on blur, so after-tax could lag one
    keystroke behind. 288 imported valuations have a stale or zero after-tax.
  * The discount line was summed like any other charge, so it only reduced the
    bill if typed as a negative number. 993 were; 15 were typed positive and
    increased the bill. The discount is now always a reduction, stored negative
    as 993 legacy lines already are.
  * Money was JavaScript floating point. It is Decimal here, to the paisa.

Totals at this stage are provisional. Invoicing rewrites each line's CGST, SGST
and IGST and resets the remaining amount (InvoiceController), which is why
11,022 imported valuations show zero remaining. So this stage never writes
line-level GST, and billing is locked once a valuation has been invoiced:
19 of the 27 reverted valuations already carry an invoice, and editing their
charges would make the invoice silently disagree with the valuation.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.http import JsonResponse

from . import models as m
from .intake import IntakeError, endpoint, find, payload, record, snapshot
from .sync import source_key
from .valuations import EDITABLE, LIVE, in_scope

GST_RATE = Decimal('0.18')
DISCOUNT_SOURCE_ID = '2'            # billing_head 2, "Discount (if any)"
PAISA = Decimal('0.01')


def money(value, label):
    if value in (None, ''):
        return Decimal('0')
    try:
        amount = Decimal(str(value).replace(',', '').strip())
    except InvalidOperation:
        raise IntakeError(f'{label} must be a number')
    if not amount.is_finite():
        raise IntakeError(f'{label} must be a number')
    return amount.quantize(PAISA, ROUND_HALF_UP)


def heads():
    return list(m.ChargeType.objects.filter(legacy_deleted__in=LIVE, legacy_status__in=('1', ''))
                .order_by('source_sequence', 'name'))


def discount_id():
    target = (m.SourceIdentity.objects.filter(environment='main', schema='lead_mngt', table='billing_head',
                                              key=source_key(DISCOUNT_SOURCE_ID))
              .values_list('target_id', flat=True).first())
    return target


def totals(lines, advance, discount):
    charges = sum((a for h, a in lines.items() if h != discount), Decimal('0'))
    reduction = sum((abs(a) for h, a in lines.items() if h == discount), Decimal('0'))
    total = charges - reduction
    after_tax = (total * (1 + GST_RATE)).quantize(PAISA, ROUND_HALF_UP)
    return {'charges': charges, 'discount': reduction, 'total': total, 'gst': after_tax - total,
            'after_tax': after_tax, 'advance': advance, 'remaining': after_tax - advance}


def invoiced(valuation):
    """A standing invoice locks billing; one reversed by a credit note does not."""
    return m.Invoice.objects.filter(valuation=valuation, cancelled_at__isnull=True).exists()


def billing_json(valuation):
    discount = discount_id()
    stored = {c.charge_type_id: c for c in m.ValuationCharge.objects.filter(valuation=valuation)}
    lines = {h.pk: (stored[h.pk].amount if h.pk in stored and stored[h.pk].amount is not None else Decimal('0'))
             for h in heads()}
    advance = valuation.advance_collected or Decimal('0')
    computed = totals(lines, advance, discount)
    locked = invoiced(valuation)
    as_str = lambda d: str(d.quantize(PAISA))
    return {'valuation': valuation.pk,
            'editable': valuation.legacy_status in EDITABLE and not locked,
            'locked_reason': 'This valuation has been invoiced; change its charges through invoicing.' if locked else '',
            'gst_rate': str(GST_RATE),
            'lines': [{'charge_type': h.pk, 'name': h.name.strip(), 'discount': h.pk == discount,
                       'amount': as_str(abs(lines[h.pk]))} for h in heads()],
            'totals': {k: as_str(v) for k, v in computed.items()},
            # What the legacy system stored, so a discrepancy with the computed
            # figures stays visible rather than being silently replaced.
            'stored': {'total': str(valuation.total_billing_amount) if valuation.total_billing_amount is not None else None,
                       'after_tax': str(valuation.total_after_tax) if valuation.total_after_tax is not None else None,
                       'remaining': str(valuation.remaining_amount) if valuation.remaining_amount is not None else None}}


@endpoint(['GET', 'PUT'])
def billing(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    if request.method == 'PUT':
        save(request, valuation)
        valuation.refresh_from_db()
    return JsonResponse(billing_json(valuation))


def save(request, valuation):
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    if valuation.legacy_status not in EDITABLE:
        raise IntakeError(f'A {valuation.legacy_status or "closed"} valuation cannot be edited', 409)
    if invoiced(valuation):
        raise IntakeError('This valuation has been invoiced; change its charges through invoicing', 409)
    data = payload(request, ['lines', 'advance'])
    if not isinstance(data.get('lines'), list):
        raise IntakeError('lines must be a list')
    known = {str(h.pk): h for h in heads()}
    discount = discount_id()
    amounts = {}
    for item in data['lines']:
        head = known.get(str((item or {}).get('charge_type')))
        if head is None:
            raise IntakeError('Every line must name a current charge head')
        amount = money(item.get('amount'), head.name.strip())
        if head.pk != discount and amount < 0:
            raise IntakeError(f'{head.name.strip()} cannot be negative; enter reductions as a discount')
        # A discount is a reduction however it is typed.
        amounts[head.pk] = -abs(amount) if head.pk == discount else amount
    advance = money(data.get('advance'), 'Advance paid')
    if advance < 0:
        raise IntakeError('Advance paid cannot be negative')
    computed = totals(amounts, advance, discount)
    if computed['total'] < 0:
        raise IntakeError('The discount is larger than the charges')

    before = snapshot(valuation)
    existing = {c.charge_type_id: c for c in m.ValuationCharge.objects.filter(valuation=valuation)}
    for head_id, amount in amounts.items():
        line = existing.get(head_id)
        if line is None:
            m.ValuationCharge.objects.create(valuation=valuation, charge_type_id=head_id, amount=amount)
        elif line.amount != amount:
            line.amount = amount
            line.save(update_fields=['amount'])
    valuation.total_billing_amount = computed['total']
    valuation.advance_collected = advance
    valuation.total_after_tax = computed['after_tax']
    valuation.remaining_amount = computed['remaining']
    valuation.save(update_fields=['total_billing_amount', 'advance_collected', 'total_after_tax', 'remaining_amount'])
    record(request.user, valuation, before, action='save_valuation_billing')
