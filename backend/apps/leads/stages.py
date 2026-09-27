"""Where each of a lead's cases stands, stage by stage.

The stages are intake, work order, valuation, verification, bank report, final
approval, invoice, payment and dispatch. Each is worked out from its own current
records and nothing else. They were once treated as a strict sequence, so a
completed later stage marked every earlier one done; but they are not one: a
report can be dispatched before it is paid for, and an invoice can predate
approval or outlive a reversion. On the real data 42 standing invoices sit on
valuations that are not approved, and the old rule showed their checks and
approval as done (review BF3). No inference is needed: every valuation has its
work order linked, and every approved valuation has all four checks recorded.

A held or cancelled valuation stops the track; a sent-back one is current. An
invoice issued before the current approval says so. The current stage is the
first that is not done, unless the work is stopped.

Read-only. A user restricted to their own leads sees only the cases in their scope.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from target_core import models as m
from apps.accounts.api import staff_api
from apps.reports.pdf import rupees
from apps.valuations.services import scope_cases, scope_leads

TRACKS = ('legal', 'technical', 'social', 'general')


def case_stages(case):
    lead = case.lead
    order = m.WorkOrder.objects.filter(borrower_id=case.borrower_id).order_by('created_at').first() if case.borrower_id else None
    v = m.Valuation.objects.filter(case=case).order_by('created_at').first()
    verification = m.ValuationVerification.objects.filter(valuation=v).first() if v else None
    report = (m.BankReport.objects.filter(valuation=v, superseded_at__isnull=True).order_by('-revision').first() if v else None)
    invoice = m.Invoice.objects.filter(valuation=v, cancelled_at__isnull=True).order_by('-created_at').first() if v else None
    # The dispatch of the current revision; an item from the previous system names no
    # revision and can only have sent revision 0.
    items = (m.DispatchItem.objects.filter(valuation=v, dispatch__cancelled=False).select_related('dispatch')
             .order_by('-dispatch__outward_date') if v and report else m.DispatchItem.objects.none())
    item = items.filter(bank_report=report).first() or (items.filter(bank_report__isnull=True).first() if report and report.revision == 0 else None)
    checked = sum(1 for t in TRACKS if verification and getattr(verification, f'{t}_status') == 'Verified')
    status = v.legacy_status if v else ''
    owed = (invoice.legacy_remaining_amount or 0) if invoice else None

    approved = bool(verification and verification.final_status == 'Verified')
    stopped = status in ('Hold', 'Cancel')
    rows = [
        ('intake', 'Intake', True, 'Received' if lead.received_date else ''),
        ('work_order', 'Work order', bool((v and v.work_order_id) or order), (v.work_order.number if v and v.work_order_id else order.number if order else '')),
        ('valuation', 'Valuation', status == 'Submit',
         {'Pending': 'Being filled in', 'Revert': 'Sent back for correction', 'Submit': 'Submitted'}.get(status, '')),
        ('verification', 'Verification', checked == 4, f'{checked} of 4 checks' if v and checked < 4 else ''),
        ('bank_report', 'Bank report', report is not None, f'Revision {report.revision}' if report and report.revision else ''),
        ('approval', 'Approval', approved, 'Withdrawn for correction' if status == 'Revert' and not approved and report is None and invoice else ''),
        ('invoice', 'Invoice', invoice is not None,
         (f'{invoice.number}, issued before the current approval' if not approved else invoice.number) if invoice else ''),
        ('payment', 'Payment', invoice is not None and owed <= 0,
         f'₹{rupees(owed)} outstanding' if invoice is not None and owed > 0 else ('Paid' if invoice is not None else '')),
        ('dispatch', 'Dispatch', bool(item and item.dispatch.status == 3),
         {1: 'Lying at head office', 2: 'In transit', 3: 'Delivered'}.get(item.dispatch.status, '') if item else ''),
    ]
    out, current_given = [], False
    for key, label, done, detail in rows:
        if key == 'valuation' and stopped:
            state, detail = 'stopped', 'On hold' if status == 'Hold' else 'Cancelled'
        elif done:
            state = 'done'
        elif stopped:
            state = 'skipped' if status == 'Cancel' else 'waiting'
        elif not current_given:
            state, current_given = 'current', True
        else:
            state = 'waiting'
        out.append({'key': key, 'label': label, 'state': state, 'detail': detail})
    return {'id': case.pk, 'borrower': case.borrower.name.strip() if case.borrower_id else '',
            'service': case.service.name if case.service_id else '', 'subtype': case.subtype.name if case.subtype_id else '',
            'report_number': v.report_number if v else '', 'stages': out}


@require_GET
@staff_api
def lead_stages(request, pk):
    lead = scope_leads(request.user, m.Lead.objects.filter(pk=pk)).first()      # not found, rather than an empty list
    if lead is None:
        return JsonResponse({'error': 'Lead not found'}, status=404)
    cases = (scope_cases(request.user, m.Case.objects.filter(lead=lead))
             .select_related('lead', 'borrower', 'service', 'subtype').order_by('created_at'))
    return JsonResponse({'lead': lead.pk, 'cases': [case_stages(c) for c in cases]})
