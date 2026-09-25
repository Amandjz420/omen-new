"""The valuation form: the assessor's queue, opening a case, and filling the form.

Traced to ValuationController (/list, /case, /detail, /saveDetail,
/multipleDataNew, /saveMultiDetailNew, /deleteMultiDetailNew),
ValuationService.findAllQuesValuation, ValuationAllUserService, and the JSPs
report_question.jsp and valuation_multi_answer.jsp in omen-lead-new.

Structure
  * One valuation per case, created when the case is first opened, status Pending.
    The queue is built from work orders, so only cases whose borrower has a work
    order can be valued.
  * The form is every live question for the case's service and subtype, grouped
    into sections by question category. Questions already answered stay visible
    even if later retired, so an imported valuation shows what was recorded.
  * Sections, questions and grid columns keep the legacy source order.

Answer types (AnswerTypeEnum)
  1 Single/Radio, 2 Multiple/Checkbox: one stored row per chosen option, its value
    the option's text. The legacy form also stored unchosen options with an empty
    value, so a chosen option is one whose value is not empty.
  3 Text: a single value.
  4 Tabular: a grid; answer_group numbers the rows, options are the columns.
  5 Sum of Attribute: a value per option; the total is derived, not stored.
  6 Formula: a grid whose column D is (A x B) x (1 - C/100), rounded. The legacy
    page computed this only in the browser; it is computed here on save, which
    reproduces all 9,086 imported rows that carry numeric inputs.

question_type (QuestionTypeEnum) is the verification track: 1 Legal,
2 Technical, 3 Social, 4 General. It does not affect how a question is filled.

Access. Field Assessors and LMS Valuators (legacy user types 157 and 159) see only
leads assigned to them, as in the legacy queue. The legacy system filtered only
its lists, so an assessor could still open another's case by URL; here the same
scope also governs opening and saving. Everyone else keeps full access under the
interim policy.

Editing. Only Pending and Revert valuations are editable. Editing an imported
valuation makes it locally owned, so a later import stages its answers as
evidence instead of reverting the edit (see PARENT_OWNED in sync.py).
"""
import math
import re

from django.db.models import OuterRef, Q, Subquery
from django.http import JsonResponse

from target_core import models as m
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.migration_pipeline.services import source_key

LIVE = ('', '0')
EDITABLE = ('Pending', 'Revert')
KINDS = {1: 'single', 2: 'multiple', 3: 'text', 4: 'grid', 5: 'sum', 6: 'formula'}
TRACKS = {1: 'legal', 2: 'technical', 3: 'social', 4: 'general'}
SCOPED_ROLE_SOURCE_IDS = ('157', '159')          # Field Assessors, LMS Valuator
PAGE_SIZE = 25
NOBODY = object()                                # scoped, but linked to no employee


# --- access ------------------------------------------------------------------

def scoped_employee(user):
    """None: unrestricted. An Employee: restricted to leads assigned to them.
    NOBODY: restricted, and sees nothing.

    It fails safe. A linked account with no eligible grant sees nothing: an empty
    grant set used to be read as unrestricted, so deactivating an assessor's only
    role widened their access (review finding G7). Unrestricted access needs an
    eligible role other than the two scoped ones. Grants qualify by the shared
    rule in apps.accounts.grants, the one provisioning uses. The check runs on
    every request, so a grant change applies to an existing session at once.

    A user with no linked legacy account (a Django-only superuser, say) is governed
    by the interim staff policy alone and is not scoped here."""
    from apps.accounts.grants import eligible_lead_grants
    account = getattr(user, 'legacy_account', None)
    if account is None:
        return None
    accounts = [account, *account.merged_accounts.all()]
    roles = set(eligible_lead_grants().filter(account__in=accounts).values_list('role_id', flat=True))
    if not roles:
        return NOBODY
    scoped = set(m.SourceIdentity.objects.filter(environment='main', schema='uam_user', table='usertype',
                                                 key__in=[source_key(i) for i in SCOPED_ROLE_SOURCE_IDS])
                 .values_list('target_id', flat=True))
    if not roles <= scoped:
        return None
    return account.employee or NOBODY


def scope_cases(user, cases):
    who = scoped_employee(user)
    if who is None:
        return cases
    if who is NOBODY:
        return cases.none()
    return cases.filter(lead__assigned_employee=who)


def in_scope(user, case):
    # 404 rather than 403, so a scoped user cannot probe which cases exist.
    if not scope_cases(user, m.Case.objects.filter(pk=case.pk)).exists():
        raise IntakeError('Case not found', 404)


# --- the form ----------------------------------------------------------------

def live_questions(case):
    return m.Question.objects.filter(service=case.service, subtype=case.subtype,
                                     legacy_deleted__in=LIVE, legacy_status='1')


def form_questions(valuation):
    answered = m.ValuationAnswer.objects.filter(valuation=valuation).values('question')
    return (m.Question.objects.filter(Q(pk__in=live_questions(valuation.case).values('pk')) | Q(pk__in=answered))
            .select_related('category').order_by('display_order', 'source_sequence', 'id'))


def section_key(question):
    return str(question.category_id) if question.category_id else 'none'


def filled(answer):
    return (answer.value or '').strip() != ''


def sections(valuation):
    questions = list(form_questions(valuation))
    answered = set(m.ValuationAnswer.objects.filter(valuation=valuation).exclude(value='')
                   .values_list('question_id', flat=True))
    grouped = {}
    for q in questions:
        key = section_key(q)
        entry = grouped.setdefault(key, {'key': key, 'name': q.category.name if q.category else 'Other',
                                         'order': q.category.source_sequence if q.category else 10 ** 9,
                                         'questions': 0, 'answered': 0, 'required': 0, 'required_answered': 0})
        entry['questions'] += 1
        entry['answered'] += q.pk in answered
        if q.is_mandatory:
            entry['required'] += 1
            entry['required_answered'] += q.pk in answered
    return sorted(grouped.values(), key=lambda s: (s['order'] or 0, s['name']))


def options_of(question):
    return list(m.QuestionOption.objects.filter(question=question)
                .filter(Q(legacy_deleted__in=LIVE)).order_by('source_sequence', 'id'))


def number(value):
    text = re.sub(r'[^0-9.\-]', '', str(value or ''))
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def js_round(value):
    """JavaScript's Math.round, which the legacy page used: halves round up.
    Python's round() rounds halves to even, so 2.5 would give 2 instead of 3."""
    return math.floor(value + 0.5)


def formula(cells, columns):
    """Column D = Math.round((A x B) x (1 - C/100)), when A, B and C are numeric."""
    a, b, c = (number(cells.get(columns.get(x))) for x in 'ABC')
    if None in (a, b, c) or 'D' not in columns:
        return cells
    return {**cells, columns['D']: str(js_round((a * b) * (1 - c / 100)))}


def answer_of(question, answers, options):
    kind = KINDS.get(question.answer_type, 'text')
    if kind in ('single', 'multiple'):
        return {'selected': [str(a.option_id) for a in answers if a.option_id and filled(a)]}
    if kind == 'text':
        chosen = next((a for a in answers if not a.option_id), answers[0] if answers else None)
        return {'value': chosen.value if chosen else ''}
    if kind == 'sum':
        values = {str(a.option_id): a.value for a in answers if a.option_id}
        total = sum(n for n in (number(v) for v in values.values()) if n is not None)
        return {'values': values, 'total': total}
    rows = {}
    for a in answers:
        if a.option_id:
            rows.setdefault(a.answer_group, {})[str(a.option_id)] = a.value
    return {'rows': [{'group': g, 'cells': cells} for g, cells in sorted(rows.items())]}


def attached(answers):
    from apps.documents.storage import file_json
    return [{'option': str(a.option_id) if a.option_id else None, 'group': a.answer_group,
             'file': file_json(a.document)} for a in answers if a.document_id]


def question_json(question, answers):
    options = options_of(question)
    return {'id': question.pk, 'text': question.text.strip(), 'kind': KINDS.get(question.answer_type, 'text'),
            'answer_type': question.answer_type, 'track': TRACKS.get(question.question_type),
            'mandatory': question.is_mandatory, 'document': question.is_document,
            'retired': question.legacy_deleted not in LIVE or question.legacy_status != '1',
            'options': [{'id': o.pk, 'label': o.value.strip(), 'column': o.value_type or ''} for o in options],
            'answer': answer_of(question, answers, options),
            'documents': attached(answers) if question.is_document else []}


def valuation_json(valuation, user):
    case = valuation.case
    order = valuation.work_order
    return {'id': valuation.pk, 'status': valuation.legacy_status, 'report_number': valuation.report_number,
            'editable': valuation.legacy_status in EDITABLE,
            'case': case.pk, 'lead': case.lead_id, 'lead_number': case.lead.number,
            'borrower': case.borrower.name if case.borrower_id else '',
            'work_order': order.number if order else '',
            'service': case.service.name, 'subtype': case.subtype.name if case.subtype else '',
            'bank': case.lead.office.bank.name if case.lead.office.bank_id else '',
            'asset': ', '.join(x for x in (case.asset_address, case.asset_district, case.asset_state) if x),
            'origin': 'imported' if m.SourceIdentity.objects.filter(target_id=valuation.pk).exists() else 'local',
            'sections': sections(valuation)}


# --- endpoints ---------------------------------------------------------------

@endpoint(['GET'])
def queue(request):
    cases = scope_cases(request.user, m.Case.objects.filter(borrower__work_orders__isnull=False).distinct())
    latest = m.Valuation.objects.filter(case=OuterRef('pk')).order_by('-created_at')
    cases = cases.annotate(valuation_id=Subquery(latest.values('pk')[:1]),
                           valuation_status=Subquery(latest.values('legacy_status')[:1]),
                           valuation_report=Subquery(latest.values('report_number')[:1]))
    status = request.GET.get('status', '')
    if status == 'not_started':
        cases = cases.filter(valuation_id__isnull=True)
    elif status:
        cases = cases.filter(valuation_status=status)
    else:
        # Cancelled work leaves the default view. The legacy assessor queue
        # skipped this filter, which surfaced cancelled valuations to assessors.
        # The IS NULL branch is required: a case not yet started has no status,
        # and NULL <> 'Cancel' is unknown in SQL, so a bare exclude() drops every
        # unstarted case, which is exactly the work an assessor needs to see.
        cases = cases.filter(Q(valuation_status__isnull=True) | ~Q(valuation_status='Cancel'))
    text = request.GET.get('q', '').strip()
    if text:
        cases = cases.filter(Q(lead__number__icontains=text) | Q(borrower__name__icontains=text)
                             | Q(borrower__work_orders__number__icontains=text) | Q(valuation_report__icontains=text))
    cases = cases.select_related('lead', 'borrower', 'service', 'subtype').order_by('-lead__received_date', '-id')
    total = cases.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    rows = cases[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
    orders = dict(m.WorkOrder.objects.filter(borrower__in=[c.borrower_id for c in rows])
                  .order_by('borrower', 'created_at').values_list('borrower', 'number'))
    return JsonResponse({'total': total, 'page': page, 'page_size': PAGE_SIZE,
                         'scoped': scoped_employee(request.user) is not None,
                         'results': [{'case': c.pk, 'lead': c.lead_id, 'lead_number': c.lead.number,
                                      'borrower': c.borrower.name if c.borrower_id else '',
                                      'work_order': orders.get(c.borrower_id, ''),
                                      'service': c.service.name, 'subtype': c.subtype.name if c.subtype else '',
                                      'district': c.asset_district,
                                      'valuation': ({'id': c.valuation_id, 'status': c.valuation_status,
                                                     'report_number': c.valuation_report}
                                                    if c.valuation_id else None)} for c in rows]})


@endpoint(['POST'])
def open_case(request, pk):
    case = find(m.Case, pk)
    in_scope(request.user, case)
    # Serialise concurrent opens of the same case so it gains exactly one valuation.
    case = m.Case.objects.select_for_update().get(pk=case.pk)
    existing = m.Valuation.objects.filter(case=case).order_by('created_at').first()
    if existing:
        return JsonResponse({**valuation_json(existing, request.user), 'created': False})
    order = m.WorkOrder.objects.filter(borrower_id=case.borrower_id).order_by('created_at').first()
    if order is None:
        raise IntakeError('Issue a work order for this borrower before starting the valuation', 409)
    if case.lead.legacy_status == '3':
        raise IntakeError('The lead is cancelled', 409)
    employee = getattr(request.user, 'employee_profile', None)
    valuation = m.Valuation.objects.create(case=case, work_order=order, legacy_status='Pending',
                                           assessor=employee,
                                           assessor_name=(employee.name if employee else request.user.get_username()))
    record(request.user, valuation)
    return JsonResponse({**valuation_json(valuation, request.user), 'created': True}, status=201)


@endpoint(['GET'])
def detail(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    return JsonResponse(valuation_json(valuation, request.user))


def section_questions(valuation, key):
    questions = [q for q in form_questions(valuation) if section_key(q) == key]
    if not questions:
        raise IntakeError('Section not found', 404)
    return questions


@endpoint(['GET', 'PUT'])
def section(request, pk, key):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    questions = section_questions(valuation, key)
    if request.method == 'PUT':
        save_section(request, valuation, questions)
    answers = {}
    for a in (m.ValuationAnswer.objects.filter(valuation=valuation, question__in=questions)
              .select_related('document').order_by('answer_group', 'id')):
        answers.setdefault(a.question_id, []).append(a)
    return JsonResponse({'valuation': valuation.pk, 'key': key, 'editable': valuation.legacy_status in EDITABLE,
                         'questions': [question_json(q, answers.get(q.pk, [])) for q in questions],
                         'sections': sections(valuation)})


def save_section(request, valuation, questions):
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    if valuation.legacy_status not in EDITABLE:
        raise IntakeError(f'A {valuation.legacy_status or "closed"} valuation cannot be edited', 409)
    data = payload(request, ['answers'])
    submitted = data.get('answers')
    if not isinstance(submitted, list):
        raise IntakeError('answers must be a list')
    by_id = {str(q.pk): q for q in questions}
    rows, touched = [], []
    for item in submitted:
        if not isinstance(item, dict) or str(item.get('question')) not in by_id:
            raise IntakeError('Every answer must name a question in this section')
        question = by_id[str(item['question'])]
        options = {str(o.pk): o for o in options_of(question)}
        kind = KINDS.get(question.answer_type, 'text')
        touched.append(question)

        def cell(option_id, value, group=0):
            if option_id not in options:
                raise IntakeError(f'An option does not belong to the question "{question.text.strip()[:60]}"')
            rows.append(m.ValuationAnswer(valuation=valuation, question=question, option=options[option_id],
                                          answer_group=group, value=str(value)[:100000]))

        if kind in ('single', 'multiple'):
            chosen = [str(o) for o in item.get('selected') or []]
            if kind == 'single' and len(chosen) > 1:
                raise IntakeError(f'Choose one option for "{question.text.strip()[:60]}"')
            for option_id in dict.fromkeys(chosen):
                cell(option_id, options[option_id].value if option_id in options else '')
        elif kind == 'text':
            value = str(item.get('value') or '')
            if value.strip():
                rows.append(m.ValuationAnswer(valuation=valuation, question=question, answer_group=0, value=value))
        elif kind == 'sum':
            for option_id, value in (item.get('values') or {}).items():
                if str(value).strip():
                    cell(str(option_id), value)
        else:
            columns = {o.value_type: str(o.pk) for o in options.values() if o.value_type}
            for group, entry in enumerate(item.get('rows') or [], 1):
                cells = {str(k): v for k, v in ((entry or {}).get('cells') or {}).items()}
                if kind == 'formula':
                    cells = formula(cells, columns)
                if any(str(v).strip() for v in cells.values()):
                    for option_id, value in cells.items():
                        cell(option_id, value, group)

    before = snapshot(valuation)
    # Local ownership first: once an imported valuation is edited, its answers are
    # this edit's to replace, and the importer no longer compares them.
    record(request.user, valuation, before, action='save_valuation_section')
    reconcile(valuation, touched, rows)


def reconcile(valuation, questions, rows):
    """Bring the stored answers for these questions into line with `rows`.

    Rows are matched on (question, option, row group) and updated in place rather
    than deleted and recreated. That keeps each answer's attached document: 35,284
    imported answers carry one, and recreating the row would silently drop the
    link. An answer that is no longer given is removed, and its document link with
    it. Legacy rows that duplicate a key are collapsed, keeping any document."""
    existing = {}
    for answer in m.ValuationAnswer.objects.filter(valuation=valuation, question__in=questions).order_by('id'):
        existing.setdefault((answer.question_id, answer.option_id, answer.answer_group), []).append(answer)
    keep, creates, updates = set(), [], []
    for wanted in rows:
        key = (wanted.question_id, wanted.option_id, wanted.answer_group)
        matches = existing.get(key) or []
        if key in keep:
            continue
        keep.add(key)
        if not matches:
            creates.append(wanted)
            continue
        survivor = next((a for a in matches if a.document_id), matches[0])
        if survivor.value != wanted.value:
            survivor.value = wanted.value
            updates.append(survivor)
    obsolete = [a.pk for key, answers in existing.items() for a in answers
                if key not in keep or a is not next((x for x in answers if x.document_id), answers[0])]
    m.ValuationAnswer.objects.filter(pk__in=obsolete).delete()
    m.ValuationAnswer.objects.bulk_update(updates, ['value'], batch_size=500)
    m.ValuationAnswer.objects.bulk_create(creates, batch_size=500)
