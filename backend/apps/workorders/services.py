"""Work-order generation, the stage that closes a lead.

Traced to WorkOrderGenerateController.saveLeadCustomerDetail and
LeadOrderService.leadOrderPdf in omen-lead-new:

  * A work order is issued per borrower, not per lead.
  * Its number is O- + MMYYDD (issue date) + a global counter padded to four
    digits, continuing above the imported maximum.
  * The letter is generated with the order; if it cannot be produced, nothing is
    saved. The letter's date is the lead's date, not the issue date.
  * Generating a work order closes the lead (status 4, LeadStatusEnum.Close).

One deliberate departure, switchable below. The legacy code reads:

      if (lead.getNoOfParties() == leadViewDTO.getUploadCount()) {
      }
      lead.setLeadStatus(LeadStatusEnum.Close.getValue());

The comparison was plainly meant to hold closure until every party had a work
order, but its body is empty, so the lead closes on the first borrower's order.
112 imported leads are closed while some of their borrowers still have none.
This module follows the evident intent: the lead closes when every active
borrower holds a work order. Set CLOSE_WHEN_EVERY_BORROWER_ORDERED = False to
reproduce the legacy behaviour exactly.

Closure means the work has been ordered. It is not valuation approval and not
payment completion.
"""
import hashlib
import json
import uuid
from apps.valuations.services import require_lead
from apps.documents.storage import available
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.common.numbering import allocate, format_number
from apps.workorders.pdf import render

CLOSE_WHEN_EVERY_BORROWER_ORDERED = True
LIVE = ('', '0')                    # legacy delete_status values meaning "not deleted"
OPEN_STATUSES = ('1', '2', '4')     # New, In process, Closed. Closed stays open for the
                                    # remaining borrowers of the 112 half-ordered leads.
CANCELLED = '3'


def active_borrowers(lead):
    return m.Borrower.objects.filter(lead=lead, legacy_deleted__in=LIVE)


def live_cases(borrower):
    """A borrower's cases not deleted (a case's legacy_status carries its delete flag).
    Deleted ones once counted, so a borrower whose only case was deleted could still
    be ordered."""
    return m.Case.objects.filter(borrower=borrower, legacy_status__in=LIVE)


def eligibility(borrower):
    """Reasons a work order cannot be issued for this borrower; empty if it can."""
    lead, reasons = borrower.lead, []
    if lead.legacy_deleted not in LIVE:
        reasons.append('The lead has been deleted')
    if lead.legacy_status == CANCELLED:
        reasons.append('The lead is cancelled')
    elif lead.legacy_status not in OPEN_STATUSES:
        reasons.append('The lead has an unrecognised status')
    if borrower.legacy_deleted not in LIVE:
        reasons.append('The borrower has been deleted')
    if borrower.work_orders.exists():
        reasons.append('This borrower already has a work order')
    # Every one of the 12,285 legacy orders was issued for a borrower with a case.
    if not live_cases(borrower).exists():
        reasons.append('Add at least one asset case before issuing a work order')
    return reasons


def order_json(order):
    return {'id': order.pk, 'number': order.number, 'lead': order.lead_id, 'borrower': order.borrower_id,
            'borrower_name': order.borrower.name,
            'issued_at': order.issued_at, 'issued_by': order.issued_by.get_username() if order.issued_by else None,
            'document': order.document_id is not None,
            'document_available': available(order.document) if order.document_id else False,
            'origin': 'local' if order.local_sequence else 'imported'}


def lead_state(lead):
    borrowers = []
    for b in active_borrowers(lead).order_by('created_at', 'id'):
        order = b.work_orders.order_by('created_at').first()
        reasons = [] if order else eligibility(b)
        borrowers.append({'id': b.pk, 'name': b.name, 'cases': live_cases(b).count(), 'contact_number': b.contact_number,
                          'email': b.email, 'payer': b.payer, 'fee_basis': b.fee_basis, 'agreed_fee': b.agreed_fee,
                          'customer_payment_method': b.customer_payment_method, 'declared_cases': b.property_count,
                          'work_order': order_json(order) if order else None,
                          'eligible': order is None and not reasons, 'reasons': reasons})
    ordered = sum(1 for b in borrowers if b['work_order'])
    return {'lead': lead.pk, 'number': lead.number, 'status': lead.legacy_status,
            'closed': lead.legacy_status == '4', 'borrowers': borrowers,
            'ordered': ordered, 'outstanding': len(borrowers) - ordered}


def close_if_complete(lead, actor):
    """Close the lead once the closure rule is satisfied. Returns True on closure."""
    if lead.legacy_status == '4':
        return False
    if CLOSE_WHEN_EVERY_BORROWER_ORDERED:
        borrowers = list(active_borrowers(lead))
        if not borrowers or any(not b.work_orders.exists() for b in borrowers):
            return False
    before = snapshot(lead)
    lead.legacy_status = '4'
    lead.save(update_fields=['legacy_status'])
    # An edit to an imported lead makes it locally owned, so a later import does
    # not revert this closure to the legacy status.
    record(actor, lead, before, action='close_on_work_order')
    return True


@endpoint(['GET'])
def lead_work_orders(request, pk):
    return JsonResponse(lead_state(require_lead(request.user, find(m.Lead, pk))))


@endpoint(['POST'])
def create_work_order(request):
    data = payload(request, ['request_id', 'borrower'])
    try:
        key = uuid.UUID(str(data.get('request_id')))
    except ValueError:
        raise IntakeError('request_id must be a UUID, reused when retrying the same order')
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    prior = m.WorkOrder.objects.filter(request_key=key).first()
    if prior is not None:
        require_lead(request.user, prior.lead)                  # a replay is checked now, as in review R3
    if prior:
        if prior.request_hash != digest:
            raise IntakeError('This request ID was already used for a different work order', 409)
        return JsonResponse({**order_json(prior), 'replayed': True, 'lead_state': lead_state(prior.lead)})

    borrower = find(m.Borrower, data.get('borrower'))
    require_lead(request.user, borrower.lead)
    # Lock the borrower and its lead so concurrent requests for the same borrower
    # serialise; the partial unique constraint is the final backstop.
    borrower = m.Borrower.objects.select_for_update().get(pk=borrower.pk)
    lead = m.Lead.objects.select_for_update().get(pk=borrower.lead_id)
    reasons = eligibility(borrower)
    if reasons:
        raise IntakeError('; '.join(reasons), 409)

    issued = timezone.now()
    sequence = allocate('work_order', m.WorkOrder, 'number', 'O')
    order = m.WorkOrder(lead=lead, borrower=borrower,
                        number=format_number('O', timezone.localdate(issued), sequence),
                        request_key=key, request_hash=digest, local_sequence=sequence,
                        issued_by=request.user, issued_at=issued)
    content = render(order)                  # raises before anything is written
    relative = f'work_orders/{issued:%Y/%m}/{order.number}.pdf'
    order.document = m.Document.objects.create(
        storage_provider='local', storage_key=relative, original_name=f'{order.number}.pdf',
        media_type='application/pdf', size_bytes=len(content))
    order.save()
    record(request.user, order)
    closed = close_if_complete(lead, request.user)

    # Written last, inside the transaction: if the file cannot be stored, the
    # order, its document record and any closure all roll back together.
    path = Path(settings.MEDIA_ROOT) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    lead.refresh_from_db()
    return JsonResponse({**order_json(order), 'replayed': False, 'lead_closed': closed,
                         'lead_state': lead_state(lead)}, status=201)


@endpoint(['GET'])
def work_order_detail(request, pk):
    order = find(m.WorkOrder, pk)
    require_lead(request.user, order.lead)
    return JsonResponse({**order_json(order), 'lead_state': lead_state(order.lead)})


@endpoint(['GET'])
def work_order_document(request, pk):
    order = find(m.WorkOrder, pk)
    require_lead(request.user, order.lead)
    document = order.document
    if document is None:
        raise IntakeError('This work order has no document', 404)
    # Letters issued here and imported ones in the previous system's bucket alike.
    from apps.documents.storage import serve
    return serve(document)
