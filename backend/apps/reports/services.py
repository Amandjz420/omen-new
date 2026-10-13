"""The bank report: the assessed values and the document a bank receives.

Traced to BankReportController /bankReport, /report_question and /savebankReport,
BankReportService.questionList, findQuestions and bankReportPDF, and
ValuationBankReportUtil.

Gate. A report may be generated only for a submitted valuation whose four tracks
are all verified and which has no final approval yet. The legacy queue checked
none of this, but all 11,898 imported bank reports had all four tracks verified,
so the gate enforces what was always practised (the data owner's decision).

Template. Chosen by the office's client type, the case's service and subtype, and
for bank clients (client type 1, Financial Institution) the bank chosen on the
report. That bank can differ from the office's bank, and does on 523 imported
reports; matched on the report's bank, every one of the 11,579 bank-client
reports has a live template. For other clients the legacy query ignored the bank,
so several templates for one combination would have had their lines merged into
one report; none does today, and here more than one is refused as ambiguous.

Values. Market/fair, realisable and distress are required and may be zero (2,161
imported reports state a zero market value); book value is optional, set on only 2
of 11,897. Words are generated, never typed: the converter reproduces all 47,592
stored legacy figures in words exactly.

Versions. The legacy system kept one report per valuation, updated it in place and
deleted it on a final revert, so a report a bank had received could disappear.
Until final approval the current version is updated in place, as before. A final
revert (the approval stage) supersedes it instead of deleting it, and the next
version carries the following revision number, printed beside the report number.
"""
import datetime
import uuid
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.reports.pdf import render, template_lines
from apps.documents.storage import file_json, serve
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.migration_pipeline.services import source_key
from apps.billing.valuation import money
from apps.valuations.services import LIVE, in_scope, scope_cases
from apps.valuations.verification import TRACKS, VERIFIED, actor
from apps.common.words import amount_words

BANK_CLIENT_SOURCE_ID = '1'          # client_type 1, "Financial Institution"
PAGE_SIZE = 25


def bank_client_type_id():
    return (m.SourceIdentity.objects.filter(environment='main', schema='lead_mngt', table='client_type',
                                            key=source_key(BANK_CLIENT_SOURCE_ID))
            .values_list('target_id', flat=True).first())


def is_bank_client(valuation):
    office = valuation.case.lead.office
    return office.client_type_id is not None and office.client_type_id == bank_client_type_id()


def content_fingerprint(valuation):
    """A hash of the valuation content a bank report prints: every answer with its
    option, row group, value and attached document; every photo; the report
    number; and the borrower, service and subtype in the subject line. It changes
    whenever any of those do, by whatever route: a send-back and correction, a
    photo added, or an edit made outside the workflow."""
    import hashlib
    import json
    case = valuation.case
    content = {
        'report_number': valuation.report_number,
        'borrower': case.borrower.name if case.borrower_id else '',
        'service': str(case.service_id), 'subtype': str(case.subtype_id or ''),
        'answers': sorted([str(a['question_id']), str(a['option_id'] or ''), a['answer_group'], a['value'] or '',
                           str(a['document_id'] or '')]
                          for a in m.ValuationAnswer.objects.filter(valuation=valuation)
                          .values('question_id', 'option_id', 'answer_group', 'value', 'document_id')),
        'photos': sorted([str(p['id']), p['attachment_type'] or '', p['name'] or '', str(p['document_id'] or '')]
                         for p in m.ValuationAttachment.objects.filter(valuation=valuation)
                         .values('id', 'attachment_type', 'name', 'document_id')),
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def is_stale(report, valuation):
    """True when the report no longer reflects the valuation it was made from."""
    return not report.content_fingerprint or report.content_fingerprint != content_fingerprint(valuation)


def current(valuation):
    return (m.BankReport.objects.filter(valuation=valuation, superseded_at__isnull=True)
            .select_related('bank', 'branch', 'document').order_by('-revision', '-created_at').first())


def blockers(valuation):
    reasons = []
    if valuation.legacy_status != 'Submit':
        reasons.append(f'The valuation is {valuation.legacy_status or "not submitted"}, not submitted')
    verification = m.ValuationVerification.objects.filter(valuation=valuation).first()
    missing = [label for t, (_, label) in TRACKS.items()
               if not verification or getattr(verification, f'{t}_status') != VERIFIED]
    if missing:
        reasons.append('Awaiting verification: ' + ', '.join(missing))
    if verification and verification.final_status == VERIFIED:
        reasons.append('The report has final approval; a change needs a final revert first')
    return reasons


def office_bank(office):
    """The office's bank: as recorded, or else from its IFSC in the bank directory (131
    of 140 bank offices without one have an IFSC the directory knows)."""
    if office.bank_id:
        return office.bank
    branch = m.BankBranch.objects.filter(ifsc__iexact=(office.ifsc or '').strip()).select_related('bank').first() if office.ifsc else None
    return branch.bank if branch and branch.bank_id else None


def values_required(valuation):
    """Whether the report must state market, realisable and distress values: for a
    property valuation, yes. Legacy reports since 2024 show the values absent from
    nearly every other kind: cost incurred (191 of 191), chartered engineer
    certificates (156 of 157), estimate vetting (110 of 110), estimates, rent
    assessments, revisits, fitness, and plant and machinery valuations (105 of 109);
    requiring them refused about 28% of the reports staff produce. Book value was
    never given (3,383 of 3,383) and stays optional."""
    case = valuation.case
    service = (case.service.name if case.service_id else '').strip().lower()
    subtype = (case.subtype.name if case.subtype_id else '').strip().lower()
    return service == 'valuation of asset' and not subtype.startswith('plant')


def liable_for(valuation, report):
    """Who a report's billing and recovery is credited to: a previous revision's (with
    any correction), an imported report's legacy assessor, the liable assessor chosen
    at submission, or the lead's assignee."""
    earlier = (m.BankReport.objects.filter(valuation=valuation, liable_employee__isnull=False)
               .exclude(pk=report.pk).order_by('-revision').first())
    if earlier:
        return earlier.liable_employee
    if report.legacy_liable_fa:
        from apps.analytics.mis import liable_assessors
        found = liable_assessors()(report.legacy_liable_fa)
        if found:
            return m.Employee.objects.filter(pk=found[0]).first()
    # The liable assessor chosen at submission (the legacy form's "Liable FA"), else
    # the lead's assignee.
    return valuation.submitted_to or valuation.case.lead.assigned_employee


def resolve_template(valuation, bank):
    case = valuation.case
    office = case.lead.office
    templates = m.ReportTemplate.objects.filter(client_type=office.client_type, service=case.service,
                                                subtype=case.subtype, legacy_deleted__in=LIVE)
    if is_bank_client(valuation):
        if bank is None:
            raise IntakeError('Choose the bank this report is for')
        templates = templates.filter(bank=bank)
    templates = list(templates)
    if not templates:
        raise IntakeError('No report template matches this client type, service, subtype'
                          + (' and bank' if is_bank_client(valuation) else ''), 409)
    if len(templates) > 1:
        raise IntakeError('Several report templates match; resolve the duplicate in report setup', 409)
    return templates[0]


def report_json(valuation):
    report = current(valuation)
    office = valuation.case.lead.office
    bank_client = is_bank_client(valuation)
    template = error = None
    bank = report.bank if report and report.bank_id else (office_bank(office) if bank_client else None)
    try:
        chosen = resolve_template(valuation, bank) if (bank or not bank_client) else None
        if chosen:
            template = {'id': chosen.pk, 'lines': template_lines(chosen).count()}
    except IntakeError as exc:
        error = exc.message
    value = lambda f: str(getattr(report, f)) if report and getattr(report, f) is not None else ''
    return {'valuation': valuation.pk, 'report_number': valuation.report_number,
            'blockers': blockers(valuation), 'bank_client': bank_client, 'values_required': values_required(valuation),
            'template': template, 'template_error': error,
            'report': None if report is None else {
                'id': report.pk, 'revision': report.revision, 'document': file_json(report.document), 'liable': liable_json(report),
                'stale': is_stale(report, valuation),
                'generated_at': report.generated_at, 'generated_by': report.generated_by_name},
            'values': {'market_fair_amount': value('market_fair_amount'), 'realisable_value_amount': value('realisable_value_amount'),
                       'book_value_amount': value('book_value_amount'), 'distress_value_amount': value('distress_value_amount'),
                       'our_reference': report.our_reference if report else '', 'your_reference': report.your_reference if report else '',
                       'unique_reference': report.unique_reference if report else '', 'omen_id': report.omen_id if report else '',
                       'report_date': report.report_date if report else None,
                       'bank': str(bank.pk) if bank else None,
                       'branch': str((report.branch_id if report and report.branch_id else office.directory_branch_id) or '') or None,
                       'certificate': report.bank_certificate if report else ''},
            'bank_name': bank.name if bank else '',
            'branch_name': (report.branch.name if report and report.branch_id else
                            (office.directory_branch.name if office.directory_branch_id else '')),
            'superseded': [{'revision': r.revision, 'superseded_at': r.superseded_at, 'document': file_json(r.document)}
                           for r in m.BankReport.objects.filter(valuation=valuation, superseded_at__isnull=False)
                           .order_by('revision')]}


def liable_json(report):
    if report is None:
        return None
    employee = report.liable_employee
    if employee is None and report.legacy_liable_fa:
        from apps.analytics.mis import liable_assessors
        found = liable_assessors()(report.legacy_liable_fa)
        return found and {'id': found[0], 'name': found[1]}
    return employee and {'id': employee.pk, 'name': employee.name}


@endpoint(['POST'])
def change_liable(request, pk):
    """Change liable assessor (legacy /change_fa/update_fa): who a report's billing
    and recovery is credited to. Recorded, with its reason, in the valuation's history."""
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    data = payload(request, ['employee', 'reason'])
    report = current(valuation)
    if report is None:
        raise IntakeError('Generate the bank report first', 409)
    employee = find(m.Employee, data.get('employee'))
    reason = str(data.get('reason') or '').strip()
    if not reason:
        raise IntakeError('Enter why the liable assessor is changing')
    previous = liable_json(report)
    if previous and str(previous['id']) == str(employee.pk):
        raise IntakeError(f'{employee.name} is already the liable assessor')
    before = snapshot(report)
    report.liable_employee = employee
    report.save(update_fields=['liable_employee', 'updated_at'])
    account, name = actor(request.user)
    m.ValuationEvent.objects.create(valuation=valuation, kind=m.ValuationEvent.LIABLE, on=timezone.localdate(),
                                    from_status=(previous or {}).get('name', '')[:80], to_status=employee.name[:80],
                                    reason=reason[:4000], by=account, by_name=name[:200])
    record(request.user, report, before, action='change_liable_assessor')
    return JsonResponse(report_json(valuation))


@endpoint(['GET', 'PUT'])
def report(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    if request.method == 'PUT':
        generate(request, valuation)
        valuation.refresh_from_db()
    return JsonResponse(report_json(valuation))


def generate(request, valuation):
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    reasons = blockers(valuation)
    if reasons:
        raise IntakeError('; '.join(reasons), 409)
    data = payload(request, ['market_fair_amount', 'realisable_value_amount', 'book_value_amount',
                             'distress_value_amount', 'our_reference', 'your_reference', 'unique_reference',
                             'omen_id', 'report_date', 'bank', 'branch', 'certificate'])
    amounts = {}
    needed = values_required(valuation)
    for field, label, required in (('market_fair_amount', 'Fair market value', needed),
                                   ('realisable_value_amount', 'Realisable value', needed),
                                   ('distress_value_amount', 'Distress value', needed),
                                   ('book_value_amount', 'Book value', False)):
        if required and data.get(field) in (None, ''):
            raise IntakeError(f'Enter the {label.lower()}')
        amounts[field] = money(data.get(field), label)
        if amounts[field] < 0:
            raise IntakeError(f'{label} cannot be negative')
    for field, label in (('our_reference', 'our reference'), ('your_reference', "the bank's reference")):
        if not str(data.get(field) or '').strip():
            raise IntakeError(f'Enter {label}')
    today = timezone.localdate()
    try:
        dated = datetime.date.fromisoformat(data['report_date']) if data.get('report_date') else today
    except ValueError:
        raise IntakeError('Enter the report date as YYYY-MM-DD')
    if dated > today:
        raise IntakeError('The report date cannot be in the future')
    if valuation.valuation_date and dated < valuation.valuation_date:
        raise IntakeError('The report date cannot be before the valuation date')

    bank = branch = None
    if is_bank_client(valuation):
        bank = find(m.Bank, data.get('bank')) if data.get('bank') else None
        if bank is None:
            raise IntakeError('Choose the bank this report is for')
        if data.get('branch'):
            branch = find(m.BankBranch, data['branch'])
            if branch.bank_id != bank.pk:
                raise IntakeError('The branch belongs to a different bank')
        else:
            raise IntakeError('Choose the bank branch this report is for')
    template = resolve_template(valuation, bank)

    report = current(valuation)
    before = snapshot(report) if report else None
    if report is None:
        report = m.BankReport(valuation=valuation, revision=m.BankReport.objects.filter(
            valuation=valuation, superseded_at__isnull=False).count())
    account, name = actor(request.user)
    report.report_number = valuation.report_number
    report.report_date, report.bank, report.branch, report.template = dated, bank, branch, template
    for field, amount in amounts.items():
        setattr(report, field, amount)
        setattr(report, f'{field}_word', amount_words(round(amount)))
    for field in ('our_reference', 'your_reference', 'unique_reference', 'omen_id'):
        setattr(report, field, str(data.get(field) or '').strip()[:150])
    report.bank_certificate = str(data.get('certificate') or '').strip()
    report.generated_by, report.generated_by_name, report.generated_at = account, name[:200], timezone.now()
    if report.liable_employee_id is None:
        report.liable_employee = liable_for(valuation, report)
    report.save()

    report.content_fingerprint = content_fingerprint(valuation)
    report.save(update_fields=['content_fingerprint'])
    content = render(report, template, bank is not None)          # raises before any file is written
    relative = f'bank_reports/{valuation.pk}/rev{report.revision}-{uuid.uuid4().hex}.pdf'
    report.document = m.Document.objects.create(storage_provider='local', storage_key=relative,
                                                original_name=f'{valuation.report_number}'
                                                              f'{"-rev" + str(report.revision) if report.revision else ""}.pdf',
                                                media_type='application/pdf', size_bytes=len(content))
    report.save(update_fields=['document'])
    record(request.user, report, before, action='generate_bank_report')
    path = Path(settings.MEDIA_ROOT) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@endpoint(['GET'])
def document(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    report = current(valuation)
    if report is None:
        raise IntakeError('No bank report has been generated', 404)
    return serve(report.document)


@endpoint(['GET'])
def queue(request):
    ready = (m.Valuation.objects.filter(legacy_status='Submit', case__in=scope_cases(request.user, m.Case.objects.all()))
             .exclude(verifications__final_status=VERIFIED))
    for track in TRACKS:
        ready = ready.filter(**{f'verifications__{track}_status': VERIFIED})
    with_report = m.BankReport.objects.filter(superseded_at__isnull=True).values('valuation')
    state = request.GET.get('state', 'pending')
    rows = ready.exclude(pk__in=with_report) if state == 'pending' else ready.filter(pk__in=with_report)
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
                         'counts': {'pending': ready.exclude(pk__in=with_report).count(),
                                    'generated': ready.filter(pk__in=with_report).count()},
                         'results': [{'id': v.pk, 'report_number': v.report_number, 'lead_number': v.case.lead.number,
                                      'borrower': v.case.borrower.name if v.case.borrower_id else '',
                                      'service': v.case.service.name, 'submitted_on': v.valuation_date}
                                     for v in rows[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]]})


@endpoint(['GET'])
def banks(request):
    return JsonResponse({'banks': list(m.Bank.objects.order_by('name').values('id', 'name'))})


@endpoint(['GET'])
def branches(request):
    bank = request.GET.get('bank')
    if not bank:
        raise IntakeError('Choose a bank')
    rows = m.BankBranch.objects.filter(bank_id=bank)
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(name__icontains=text) | Q(ifsc__icontains=text) | Q(city__icontains=text))
    return JsonResponse({'branches': list(rows.order_by('name').values('id', 'name', 'ifsc', 'city', 'district')[:50])})
