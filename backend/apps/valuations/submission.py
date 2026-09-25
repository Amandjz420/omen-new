"""Submitting a valuation for verification.

Traced to ValuationController /final and /saveFinal, generateReportNo and
valuation_final.jsp.

Submission records the assessor's conclusions (eligible and desired loan amounts,
comment, non-cost factors, Safe/Risky category), who the report is submitted to,
where and how it is to be dispatched, and the valuation date. It assigns the
report number R- + MMYYDD + a global counter, and moves the valuation to Submit.

Required questions. The legacy saveFinal checked nothing, but the page withheld
the form while any required question was unanswered ("Enter All Required Question
after that you can continue"). The check now runs on the server, so a direct post
cannot skip it. A required question counts as answered when it has a non-empty
answer; the legacy count accepted an empty row too, which affects only 4 required
questions in the whole imported dataset, and this form never stores empty rows.

Three legacy defects are not carried over:
  * Every submission generated a new report number, including resubmission after
    a revert, discarding the old one. The counter reached 16,331 while only 11,945
    valuations hold a number: 4,386 numbers were burned, and 3,116 of 3,119
    reverted-then-resubmitted valuations carry a number dated after their revert.
    Renumbering orphans every letter and dispatch that cited the report, so a
    report now keeps its number through corrections.
    RENUMBER_ON_RESUBMIT = True restores the legacy behaviour.
  * "Submit to" was required on the form but never stored: saveFinal copied it to
    a transient field while the update read another, so 11,895 of 11,896 submitted
    valuations have none. It is stored here.
  * The number allocator read the maximum and wrote maximum + 1 without a lock.

Dispatch intent uses AddToBeDispatchedatEnum and ToBeDispatchedByEnum. The
dispatch record uses ModeOfDispatchEnum, whose codes for Speed Post and Courier
are swapped relative to ToBeDispatchedByEnum, so the two are decoded separately and
never compared by code.
"""
import datetime

from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.common.numbering import allocate, format_number
from apps.billing.valuation import money
from apps.valuations.services import EDITABLE, LIVE, filled, form_questions, in_scope, section_key, valuation_json

RENUMBER_ON_RESUBMIT = False
DISPATCH_AT = [(1, 'Addressee'), (2, 'Extension Office'), (3, 'Other'),
               (4, 'Client Customer will pick up')]                          # AddToBeDispatchedatEnum
DISPATCH_BY = [(1, 'Speed post'), (2, 'Courier'), (3, 'Deliver by hand')]    # ToBeDispatchedByEnum
CATEGORIES = [(1, 'Safe'), (2, 'Risky')]                                     # ReportCategoryEnum


def unanswered_required(valuation):
    answered = {a.question_id for a in m.ValuationAnswer.objects.filter(valuation=valuation) if filled(a)}
    return [{'section': q.category.name if q.category else 'Other', 'section_key': section_key(q),
             'question': q.pk, 'text': q.text.strip()}
            for q in form_questions(valuation)
            if q.is_mandatory and q.legacy_deleted in LIVE and q.legacy_status == '1' and q.pk not in answered]


def employees():
    return list(m.Employee.objects.filter(legacy_status__in=('1', '')).order_by('name').values('id', 'name'))


def choice(value, options, label, required=True):
    if value in (None, ''):
        if required:
            raise IntakeError(f'Choose {label}')
        return None
    try:
        code = int(value)
    except (TypeError, ValueError):
        raise IntakeError(f'Choose a valid {label}')
    if code not in dict(options):
        raise IntakeError(f'Choose a valid {label}')
    return code


def submission_json(valuation):
    keeps = bool(valuation.report_number) and not RENUMBER_ON_RESUBMIT
    return {'valuation': valuation.pk, 'status': valuation.legacy_status,
            'editable': valuation.legacy_status in EDITABLE,
            'report_number': valuation.report_number,
            'keeps_report_number': keeps,
            'missing_required': unanswered_required(valuation),
            'values': {'valuation_date': valuation.valuation_date,
                       'eligible_loan_amount': str(valuation.eligible_loan_amount or ''),
                       'desired_loan_amount': str(valuation.desired_loan_amount or ''),
                       'assessor_comment': valuation.assessor_comment,
                       'non_cost_factor': valuation.non_cost_factor,
                       'submitted_to': valuation.submitted_to_id,
                       'dispatch_at': valuation.dispatch_at_code or None,
                       'dispatch_by': valuation.dispatch_by_code or None,
                       'report_category': valuation.report_category or None},
            'options': {'employees': employees(),
                        'dispatch_at': [{'code': c, 'label': l} for c, l in DISPATCH_AT],
                        'dispatch_by': [{'code': c, 'label': l} for c, l in DISPATCH_BY],
                        'report_category': [{'code': c, 'label': l} for c, l in CATEGORIES]}}


@endpoint(['GET', 'POST'])
def submission(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    if request.method == 'POST':
        valuation = submit(request, valuation)
        return JsonResponse({**valuation_json(valuation, request.user), 'submission': submission_json(valuation)})
    return JsonResponse(submission_json(valuation))


def submit(request, valuation):
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    if valuation.legacy_status == 'Submit':
        # A second click, or a retry after a lost response: never a second number.
        raise IntakeError(f'This valuation is already submitted as {valuation.report_number}', 409)
    if valuation.legacy_status not in EDITABLE:
        raise IntakeError(f'A {valuation.legacy_status or "closed"} valuation cannot be submitted', 409)
    missing = unanswered_required(valuation)
    if missing:
        names = '; '.join(f"{q['section']}: {q['text'][:60]}" for q in missing[:5])
        more = f' and {len(missing) - 5} more' if len(missing) > 5 else ''
        raise IntakeError(f'Answer every required question before submitting. Missing: {names}{more}', 409)

    data = payload(request, ['valuation_date', 'eligible_loan_amount', 'desired_loan_amount', 'assessor_comment',
                             'non_cost_factor', 'submitted_to', 'dispatch_at', 'dispatch_by', 'report_category'])
    for field, label in (('eligible_loan_amount', 'the eligible loan amount'), ('desired_loan_amount', 'the desired loan amount')):
        if data.get(field) in (None, ''):
            raise IntakeError(f'Enter {label}')
    eligible = money(data.get('eligible_loan_amount'), 'Eligible loan amount')
    desired = money(data.get('desired_loan_amount'), 'Desired loan amount')
    if eligible < 0 or desired < 0:
        raise IntakeError('Loan amounts cannot be negative')
    if not data.get('submitted_to'):
        raise IntakeError('Choose who the valuation is submitted to')
    recipient = find(m.Employee, data['submitted_to'])
    today = timezone.localdate()
    try:
        valued_on = datetime.date.fromisoformat(data['valuation_date']) if data.get('valuation_date') else today
    except ValueError:
        raise IntakeError('Enter the valuation date as YYYY-MM-DD')
    if valued_on > today:
        raise IntakeError('The valuation date cannot be in the future')

    before = snapshot(valuation)
    if not valuation.report_number or RENUMBER_ON_RESUBMIT:
        sequence = allocate('report', m.Valuation, 'report_number', 'R')
        valuation.report_number = format_number('R', today, sequence)
    valuation.valuation_date = valued_on
    valuation.eligible_loan_amount, valuation.desired_loan_amount = eligible, desired
    valuation.assessor_comment = str(data.get('assessor_comment') or '').strip()
    valuation.non_cost_factor = str(data.get('non_cost_factor') or '').strip()
    valuation.submitted_to = recipient
    valuation.dispatch_at_code = choice(data.get('dispatch_at'), DISPATCH_AT, 'where the report is dispatched')
    valuation.dispatch_by_code = choice(data.get('dispatch_by'), DISPATCH_BY, 'how the report is dispatched')
    valuation.report_category = choice(data.get('report_category'), CATEGORIES, 'the report category')
    valuation.legacy_status = 'Submit'
    valuation.status_reason = ''
    valuation.save()
    record(request.user, valuation, before, action='submit_valuation')
    return valuation
