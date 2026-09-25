"""Final approval, the final revert, and hold, unhold and cancel.

Traced to BankReportController /final_bankReport_approval,
/saveFinalBankReportApproval, /final_revert_back and /saveFinalRevertBack, and to
ValuationController /update_valuation_status, /reason_valuationStatus_iframe and
/save_reason.

Final approval issues the report to the bank. The legacy save checked nothing; it
set the final status and a name. Here it requires a submitted valuation, all four
tracks verified, and a generated bank report, and records who approved and when.
A completed valuation stays Submit, as in the legacy data; approval is recorded
on the verification record and the report.

The final revert sends an approved or reported valuation back. The legacy code
deleted the bank report, so a report a bank had already received disappeared, and
overwrote each verifier with the reverter. Here an issued report is superseded and
kept, and the next version carries the following revision number; an unissued
draft is revised in place, since no bank has seen it. Verifiers are kept.

Hold, unhold and cancel each need a reason and are recorded as ValuationEvent,
where the legacy system kept one reason field and overwrote it. Imported data
bounds them: none of 24 holds or 700 cancellations happened after a bank report,
though 7 holds and 143 cancellations came after submission. So they are allowed
from Pending, Revert and Submit, but not after final approval. Unhold restores the
status the hold was placed from, where the legacy code always returned Pending;
the 24 imported holds do not record their origin and return to Pending. Cancel is
final, and is refused for an invoiced valuation: 21 imported cancellations left an
invoice standing against cancelled work, which belongs to invoicing to reverse.

The legacy /update_valuation_status endpoint set the status to any text unless
the valuation was on hold. It is not carried over.
"""
import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.reports.services import current as current_report
from apps.documents.storage import file_json
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.valuations.services import in_scope, scope_cases
from apps.valuations.verification import TRACKS, UNVERIFIED, VERIFIED, actor

PAGE_SIZE = 25
HOLDABLE = ('Pending', 'Revert', 'Submit')
CANCELLABLE = ('Pending', 'Revert', 'Hold', 'Submit')


def verification_of(valuation, lock=False):
    qs = m.ValuationVerification.objects.filter(valuation=valuation)
    return (qs.select_for_update() if lock else qs).first()


def all_verified(verification):
    return verification is not None and all(getattr(verification, f'{t}_status') == VERIFIED for t in TRACKS)


def is_approved(verification):
    return verification is not None and verification.final_status == VERIFIED


def reason_and_date(data, valuation, required=True):
    reason = str(data.get('reason') or data.get('remark') or '').strip()
    if required and not reason:
        raise IntakeError('Enter a reason')
    today = timezone.localdate()
    try:
        on = datetime.date.fromisoformat(data['date']) if data.get('date') else today
    except ValueError:
        raise IntakeError('Enter the date as YYYY-MM-DD')
    if on > today:
        raise IntakeError('The date cannot be in the future')
    return reason[:4000], on


def event(valuation, kind, before, reason, on, user):
    account, name = actor(user)
    m.ValuationEvent.objects.create(valuation=valuation, kind=kind, from_status=before, to_status=valuation.legacy_status,
                                    reason=reason, on=on, by=account, by_name=name[:200])


def approval_blockers(valuation, verification, report):
    reasons = []
    if valuation.legacy_status != 'Submit':
        reasons.append(f'The valuation is {valuation.legacy_status or "not submitted"}')
    if not all_verified(verification):
        reasons.append('All four verifications are required')
    if report is None or report.document_id is None:
        reasons.append('Generate the bank report first')
    if is_approved(verification):
        reasons.append('The report already has final approval')
    return reasons


def standing_json(valuation):
    verification = verification_of(valuation)
    report = current_report(valuation)
    approved = is_approved(verification)
    status = valuation.legacy_status
    invoiced = m.Invoice.objects.filter(valuation=valuation, cancelled_at__isnull=True).exists()
    return {'id': valuation.pk, 'status': status, 'report_number': valuation.report_number,
            'lead_number': valuation.case.lead.number,
            'borrower': valuation.case.borrower.name if valuation.case.borrower_id else '',
            'approved': approved, 'approved_by': (verification.final_done_by_name or '').strip() if verification else '',
            'report': None if report is None else {'revision': report.revision, 'document': file_json(report.document),
                                                   'approved_at': report.approved_at},
            'approval_blockers': approval_blockers(valuation, verification, report),
            'can_final_revert': status == 'Submit' and (approved or report is not None),
            'can_hold': status in HOLDABLE and not approved,
            'can_unhold': status == 'Hold',
            'unhold_to': (valuation.held_from_status or 'Pending') if status == 'Hold' else None,
            'can_cancel': status in CANCELLABLE and not approved and not invoiced,
            'cancel_blocked_by_invoice': status in CANCELLABLE and invoiced,
            'reason': valuation.status_reason,
            'events': [{'kind': e.get_kind_display(), 'from': e.from_status, 'to': e.to_status, 'reason': e.reason,
                        'on': e.on, 'by': e.by_name} for e in valuation.events.order_by('-created_at')],
            'reversions': [{'on': r.reverted_on, 'by': r.reverted_by_name, 'remark': r.remark, 'stage': r.stage or 'legacy'}
                           for r in valuation.reversions.order_by('-reverted_on', '-created_at')]}


# --- approval ------------------------------------------------------------

@endpoint(['GET'])
def queue(request):
    ready = m.Valuation.objects.filter(legacy_status='Submit', case__in=scope_cases(request.user, m.Case.objects.all()))
    for track in TRACKS:
        ready = ready.filter(**{f'verifications__{track}_status': VERIFIED})
    reported = m.BankReport.objects.filter(superseded_at__isnull=True, document__isnull=False).values('valuation')
    ready = ready.filter(pk__in=reported)
    pending, approved = ready.exclude(verifications__final_status=VERIFIED), ready.filter(verifications__final_status=VERIFIED)
    state = request.GET.get('state', 'pending')
    rows = pending if state == 'pending' else approved
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(report_number__icontains=text) | Q(case__lead__number__icontains=text)
                           | Q(case__borrower__name__icontains=text))
    rows = rows.select_related('case__lead', 'case__borrower', 'case__service').order_by('-valuation_date', '-report_number')
    total = rows.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    return JsonResponse({'state': state, 'total': total, 'page': page, 'page_size': PAGE_SIZE,
                         'counts': {'pending': pending.count(), 'approved': approved.count()},
                         'results': [{'id': v.pk, 'report_number': v.report_number, 'lead_number': v.case.lead.number,
                                      'borrower': v.case.borrower.name if v.case.borrower_id else '',
                                      'service': v.case.service.name, 'submitted_on': v.valuation_date}
                                     for v in rows[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]]})


@endpoint(['GET'])
def detail(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    return JsonResponse(standing_json(valuation))


@endpoint(['POST'])
def approve(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    verification = verification_of(valuation, lock=True)
    report = current_report(valuation)
    reasons = approval_blockers(valuation, verification, report)
    if reasons:
        raise IntakeError('; '.join(reasons), 409)
    remark, on = reason_and_date(payload(request, ['remark', 'date']), valuation, required=False)
    account, name = actor(request.user)
    before = snapshot(verification)
    verification.final_status, verification.final_done_by, verification.final_done_by_name = VERIFIED, account, name[:200]
    verification.save(update_fields=['final_status', 'final_done_by', 'final_done_by_name'])
    record(request.user, verification, before, action='final_approval')
    before = snapshot(report)
    report.approved_at = timezone.now()
    report.save(update_fields=['approved_at'])
    record(request.user, report, before, action='issue_bank_report')
    event(valuation, m.ValuationEvent.APPROVE, 'Submit', remark, on, request.user)
    return JsonResponse(standing_json(valuation))


@endpoint(['POST'])
def final_revert(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    verification = verification_of(valuation, lock=True)
    report = current_report(valuation)
    approved = is_approved(verification)
    if valuation.legacy_status != 'Submit' or not (approved or report is not None):
        raise IntakeError('Only a reported or approved valuation is sent back from here; '
                          'use verification to send back earlier work', 409)
    reason, on = reason_and_date(payload(request, ['reason', 'date']), valuation)
    account, name = actor(request.user)
    if report is not None and approved:
        # Issued to the bank: keep it as a superseded version, never delete it.
        before = snapshot(report)
        report.superseded_at = timezone.now()
        report.save(update_fields=['superseded_at'])
        record(request.user, report, before, action='supersede_bank_report')
    if verification is not None:
        before = snapshot(verification)
        for track in TRACKS:
            if getattr(verification, f'{track}_status'):
                setattr(verification, f'{track}_status', UNVERIFIED)      # verifier names are kept
        if verification.final_status:
            verification.final_status = UNVERIFIED
        verification.save()
        record(request.user, verification, before, action='final_revert_verifications')
    before = snapshot(valuation)
    valuation.legacy_status = 'Revert'
    valuation.status_reason, valuation.status_reason_date = reason[:500], on
    valuation.save(update_fields=['legacy_status', 'status_reason', 'status_reason_date'])
    record(request.user, valuation, before, action='final_revert_valuation')
    m.Reversion.objects.create(valuation=valuation, remark=reason[:300], reverted_on=on, reverted_by=account,
                               reverted_by_name=name[:200], stage='final' if approved else 'bank report')
    return JsonResponse(standing_json(valuation))


# --- standing: hold, unhold, cancel --------------------------------------

@endpoint(['POST'])
def standing(request, pk, action):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    approved = is_approved(verification_of(valuation))
    reason, on = reason_and_date(payload(request, ['reason', 'date']), valuation)
    was = valuation.legacy_status
    before = snapshot(valuation)
    if action == 'hold':
        if was not in HOLDABLE or approved:
            raise IntakeError(f'A {was or "closed"}{" approved" if approved else ""} valuation cannot be put on hold', 409)
        valuation.held_from_status, valuation.legacy_status, kind = was, 'Hold', m.ValuationEvent.HOLD
    elif action == 'unhold':
        if was != 'Hold':
            raise IntakeError('Only a valuation on hold can be taken off hold', 409)
        valuation.legacy_status, valuation.held_from_status = valuation.held_from_status or 'Pending', ''
        kind = m.ValuationEvent.UNHOLD
    elif action == 'cancel':
        if was not in CANCELLABLE or approved:
            raise IntakeError(f'A {was or "closed"}{" approved" if approved else ""} valuation cannot be cancelled', 409)
        if m.Invoice.objects.filter(valuation=valuation, cancelled_at__isnull=True).exists():
            raise IntakeError('This valuation has a standing invoice; issue a credit note first', 409)
        valuation.legacy_status, valuation.held_from_status, kind = 'Cancel', '', m.ValuationEvent.CANCEL
    else:
        raise IntakeError('Unknown action', 404)
    valuation.status_reason, valuation.status_reason_date = reason[:500], on
    valuation.save(update_fields=['legacy_status', 'held_from_status', 'status_reason', 'status_reason_date'])
    record(request.user, valuation, before, action=f'{action}_valuation')
    event(valuation, kind, was, reason, on, request.user)
    return JsonResponse(standing_json(valuation))


@endpoint(['GET'])
def standing_detail(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    return JsonResponse(standing_json(valuation))
