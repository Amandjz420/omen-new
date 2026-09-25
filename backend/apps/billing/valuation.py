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

from target_core import models as m
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.migration_pipeline.services import source_key
from apps.valuations.services import EDITABLE, LIVE, in_scope

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


def stored_lines(valuation):
    """Every stored charge line, grouped by head, current or retired. Totals are
    always the sum of all of them, as the legacy total was: the save used to total
    only the submitted lines, so a line omitted from a request stayed stored but
    was left out of the total (review finding G5). 42 heads across 7 imported
    valuations hold more than one legacy line, which a per-head lookup hid."""
    grouped = {}
    for charge in m.ValuationCharge.objects.filter(valuation=valuation).select_related('charge_type').order_by('id'):
        grouped.setdefault(charge.charge_type_id, []).append(charge)
    return grouped


def line_amount(charges, discount):
    total = sum((c.amount or Decimal('0') for c in charges), Decimal('0'))
    return -abs(total) if charges and charges[0].charge_type_id == discount else total


def invoiced(valuation):
    """A standing invoice locks billing; one reversed by a credit note does not."""
    return m.Invoice.objects.filter(valuation=valuation, cancelled_at__isnull=True).exists()


def billing_json(valuation):
    discount = discount_id()
    stored = stored_lines(valuation)
    current = heads()
    retired = [charges[0].charge_type for head_id, charges in stored.items()
               if head_id not in {h.pk for h in current} and charges[0].charge_type is not None]
    shown = current + sorted(retired, key=lambda h: (h.source_sequence or 0, h.name))
    lines = {h.pk: line_amount(stored.get(h.pk, []), discount) for h in shown}
    advance = valuation.advance_collected or Decimal('0')
    computed = totals(lines, advance, discount)
    locked = invoiced(valuation)
    as_str = lambda d: str(d.quantize(PAISA))
    return {'valuation': valuation.pk,
            'editable': valuation.legacy_status in EDITABLE and not locked,
            'locked_reason': 'This valuation has been invoiced; change its charges through invoicing.' if locked else '',
            'gst_rate': str(GST_RATE),
            'lines': [{'charge_type': h.pk, 'name': h.name.strip(), 'discount': h.pk == discount,
                       'amount': as_str(abs(lines[h.pk])), 'retired': h not in current,
                       'stored_lines': len(stored.get(h.pk, []))} for h in shown],
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
    discount = discount_id()
    stored = stored_lines(valuation)
    known = {str(h.pk): h for h in heads()}
    # A retired head that still holds lines on this valuation can be corrected.
    known.update({str(head_id): charges[0].charge_type for head_id, charges in stored.items()
                  if charges[0].charge_type is not None})
    amounts = {}
    for item in data['lines']:
        head = known.get(str((item or {}).get('charge_type')))
        if head is None:
            raise IntakeError('Every line must name a current charge head')
        if len(stored.get(head.pk, [])) > 1:
            existing_total = abs(line_amount(stored[head.pk], discount))
            if money(item.get('amount'), head.name.strip()).copy_abs() != existing_total:
                raise IntakeError(f'{head.name.strip()} holds {len(stored[head.pk])} lines from the previous system; '
                                  'review them before changing the amount', 409)
            continue                                    # unchanged: its stored lines stay as they are
        amount = money(item.get('amount'), head.name.strip())
        if head.pk != discount and amount < 0:
            raise IntakeError(f'{head.name.strip()} cannot be negative; enter reductions as a discount')
        # A discount is a reduction however it is typed.
        amounts[head.pk] = -abs(amount) if head.pk == discount else amount
    advance = money(data.get('advance'), 'Advance paid')
    if advance < 0:
        raise IntakeError('Advance paid cannot be negative')
    # Partial update: submitted heads change, every other stored line stays, and the
    # totals come from the final stored set rather than the request alone.
    final = {head_id: line_amount(charges, discount) for head_id, charges in stored.items()}
    final.update(amounts)
    computed = totals(final, advance, discount)
    if computed['total'] < 0:
        raise IntakeError('The discount is larger than the charges')

    before = snapshot(valuation)
    for head_id, amount in amounts.items():
        lines = stored.get(head_id, [])
        if not lines:
            m.ValuationCharge.objects.create(valuation=valuation, charge_type_id=head_id, amount=amount)
        elif lines[0].amount != amount:
            lines[0].amount = amount
            lines[0].save(update_fields=['amount'])
    valuation.total_billing_amount = computed['total']
    valuation.advance_collected = advance
    valuation.total_after_tax = computed['after_tax']
    valuation.remaining_amount = computed['remaining']
    valuation.save(update_fields=['total_billing_amount', 'advance_collected', 'total_after_tax', 'remaining_amount'])
    record(request.user, valuation, before, action='save_valuation_billing')
