"""Verification: four independent tracks, each worked from its own queue.

Traced to ValuationController /verification and /saveVerification,
BankReportController /revert_back and /saveRevertBack, the legal, technical,
social and general lists in ValuationAllUserService, and valuation_verification.jsp.

Each question belongs to one track through question_type (QuestionTypeEnum: 1
Legal, 2 Technical, 3 Social, 4 General). A track's queue holds submitted
valuations whose track is not yet verified, and its verifier sees only that
track's questions, read-only. Verifying records the remark, date and verifier.
The tracks are independent and may be verified in any order.

Verification is one-way. Rejection is a send-back to the assessor: every track and
the final approval return to UnVerified, the valuation to Revert, and the reason
is recorded.

Legacy defects not carried over:
  * Viewing the verification page created the verification record; a read had a
    side effect. The record is created on the first verification instead.
  * Verification never checked the valuation was submitted, so a direct post could
    verify one still being filled in.
  * A revert overwrote each track's verifier with the reverter's name, destroying
    the record of who had checked it. Verifiers are kept; the reverter is recorded
    on the reversion.
  * revert_back had one row per valuation and overwrote it, so only the latest of
    several reverts survives in the imported data. Every revert is kept here.
  * 36 live questions, 14 of them mandatory, belong to no track, so no legacy
    queue ever showed them to a verifier. They are shown in the General track,
    labelled as unassigned, rather than left unseen. (They were first shown in every
    track, which repeated questions such as Date of inspection in each one; the
    review of October 2026 asked for them once.)

Corrections. A verifier may correct the answers of their own track (the General
verifier also the unassigned ones) while the valuation is submitted and that track
is not yet verified. The change goes through the assessor's own save, with its
validation and answer-level audit, recorded as a verifier correction.

After verifying, the screen moves on to the same valuation's next unverified track,
in the order Legal, Social, Technical, General (next_track).

Scope: a verifier restricted to their own leads (Field Assessors, LMS Valuators)
sees only those, as in the legacy lists; everyone else sees all.
"""
import datetime

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.common.http import IntakeError, endpoint, find, payload
from apps.audit.services import record, snapshot
from apps.valuations.services import form_questions, in_scope, question_json, save_section, scope_cases, section_key

TRACKS = {'legal': (1, 'Legal'), 'technical': (2, 'Technical'), 'social': (3, 'Social'), 'general': (4, 'General')}
VERIFIED, UNVERIFIED = 'Verified', 'UnVerified'
SEQUENCE = ('legal', 'social', 'technical', 'general')     # the order the screen moves through
UNASSIGNED_TRACK = 'general'                               # where questions of no track are shown
PAGE_SIZE = 25


def track_named(name):
    if name not in TRACKS:
        raise IntakeError('Unknown verification track', 404)
    return name


def actor(user):
    account = getattr(user, 'legacy_account', None)
    name = (account.name if account else '') or user.get_full_name() or user.get_username()
    return account, name.strip()


def state(verification, track):
    if verification is None:
        return {'status': '', 'verified': False, 'by': '', 'date': None, 'remark': ''}
    status = getattr(verification, f'{track}_status') or ''
    return {'status': status, 'verified': status == VERIFIED,
            'by': (getattr(verification, f'{track}_done_by_name') or '').strip(),
            'date': getattr(verification, f'{track}_date'), 'remark': getattr(verification, f'{track}_remark') or ''}


def tracks_json(verification):
    out = {t: {'label': label, **state(verification, t)} for t, (_, label) in TRACKS.items()}
    final = (verification.final_status or '') if verification else ''
    out['final'] = {'label': 'Final approval', 'status': final, 'verified': final == VERIFIED,
                    'by': (verification.final_done_by_name or '').strip() if verification else ''}
    return out


def approved(verification):
    return verification is not None and verification.final_status == VERIFIED


def pending(track, user):
    submitted = m.Valuation.objects.filter(legacy_status='Submit')
    submitted = submitted.filter(case__in=scope_cases(user, m.Case.objects.all()))
    return submitted.exclude(**{f'verifications__{track}_status': VERIFIED})


@endpoint(['GET'])
def queue(request):
    track = track_named(request.GET.get('track', 'legal'))
    rows = pending(track, request.user)
    text = request.GET.get('q', '').strip()
    if text:
        rows = rows.filter(Q(report_number__icontains=text) | Q(case__lead__number__icontains=text)
                           | Q(case__borrower__name__icontains=text))
    rows = rows.select_related('case__lead', 'case__borrower', 'case__service', 'case__subtype').order_by('-valuation_date', '-report_number')
    total = rows.count()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    items = list(rows[(page - 1) * PAGE_SIZE:page * PAGE_SIZE])
    records = {v.valuation_id: v for v in m.ValuationVerification.objects.filter(valuation__in=items)}
    return JsonResponse({'track': track, 'total': total, 'page': page, 'page_size': PAGE_SIZE,
                         'counts': {t: pending(t, request.user).count() for t in TRACKS},
                         'results': [{'id': v.pk, 'report_number': v.report_number, 'lead_number': v.case.lead.number,
                                      'borrower': v.case.borrower.name if v.case.borrower_id else '',
                                      'service': v.case.service.name, 'subtype': v.case.subtype.name if v.case.subtype else '',
                                      'submitted_on': v.valuation_date, 'submitted_at': v.submitted_at, 'assessor': v.assessor_name,
                                      'tracks': {t: state(records.get(v.pk), t)['verified'] for t in TRACKS}}
                                     for v in items]})


def next_track(verification, after):
    """The next track of this valuation still to verify, following SEQUENCE from
    `after` and wrapping round; None when every track is verified."""
    start = SEQUENCE.index(after) + 1
    for t in SEQUENCE[start:] + SEQUENCE[:start]:
        if t != after and not state(verification, t)['verified']:
            return t
    return None


def owns(question, track):
    """Whether this track's verifier sees, and may correct, this question."""
    if question.question_type in (None, 0):
        return track == UNASSIGNED_TRACK
    return question.question_type == TRACKS[track][0]


def track_questions(valuation, code):
    """Sections of this track's questions, plus, for the General track, those
    assigned to no track."""
    show_unassigned = code == TRACKS[UNASSIGNED_TRACK][0]
    answers = {}
    for a in m.ValuationAnswer.objects.filter(valuation=valuation).select_related('document').order_by('answer_group', 'id'):
        answers.setdefault(a.question_id, []).append(a)
    sections, unassigned = {}, []
    for q in form_questions(valuation):
        if q.question_type == code:
            entry = sections.setdefault(section_key(q), {'key': section_key(q), 'name': q.category.name if q.category else 'Other',
                                                          'order': q.category.source_sequence if q.category else 10 ** 9,
                                                          'questions': []})
            entry['questions'].append(question_json(q, answers.get(q.pk, [])))
        elif q.question_type in (None, 0) and show_unassigned:
            unassigned.append(question_json(q, answers.get(q.pk, [])))
    return sorted(sections.values(), key=lambda s: (s['order'] or 0, s['name'])), unassigned


@endpoint(['GET'])
def detail(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    track = track_named(request.GET.get('track', 'legal'))
    verification = m.ValuationVerification.objects.filter(valuation=valuation).first()
    sections, unassigned = track_questions(valuation, TRACKS[track][0])
    case = valuation.case
    return JsonResponse({
        'id': valuation.pk, 'track': track, 'status': valuation.legacy_status, 'report_number': valuation.report_number,
        'lead_number': case.lead.number, 'borrower': case.borrower.name if case.borrower_id else '',
        'service': case.service.name, 'subtype': case.subtype.name if case.subtype else '',
        'assessor': valuation.assessor_name, 'submitted_on': valuation.valuation_date,
        'submitted_at': valuation.submitted_at,
        'tracks': tracks_json(verification),
        'can_verify': valuation.legacy_status == 'Submit' and not state(verification, track)['verified'],
        'can_edit': valuation.legacy_status == 'Submit' and not state(verification, track)['verified'],
        'next_track': next_track(verification, track),
        'can_revert': valuation.legacy_status == 'Submit' and not approved(verification),
        'sections': sections, 'unassigned': unassigned,
        'reversions': [{'on': r.reverted_on, 'by': r.reverted_by_name, 'remark': r.remark, 'stage': r.stage or 'legacy'}
                       for r in m.Reversion.objects.filter(valuation=valuation).order_by('-reverted_on', '-created_at')]})


def remark_and_date(data, valuation):
    remark = str(data.get('remark') or '').strip()
    if not remark:
        raise IntakeError('Enter a remark')
    today = timezone.localdate()
    try:
        on = datetime.date.fromisoformat(data['date']) if data.get('date') else today
    except ValueError:
        raise IntakeError('Enter the date as YYYY-MM-DD')
    if on > today:
        raise IntakeError('The date cannot be in the future')
    if valuation.valuation_date and on < valuation.valuation_date:
        raise IntakeError('The date cannot be before the valuation date')
    return remark[:4000], on


@endpoint(['POST'])
def verify(request, pk, track):
    track = track_named(track)
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    if valuation.legacy_status != 'Submit':
        raise IntakeError('Only a submitted valuation can be verified', 409)
    verification = m.ValuationVerification.objects.select_for_update().filter(valuation=valuation).first()
    current = state(verification, track)
    if current['verified']:
        raise IntakeError(f"{TRACKS[track][1]} verification was already given by {current['by'] or 'another user'}"
                          f"{' on ' + str(current['date']) if current['date'] else ''}", 409)
    remark, on = remark_and_date(payload(request, ['remark', 'date']), valuation)
    account, name = actor(request.user)
    before = snapshot(verification) if verification else None
    if verification is None:
        verification = m.ValuationVerification(valuation=valuation)
    for field, value in ((f'{track}_status', VERIFIED), (f'{track}_remark', remark), (f'{track}_date', on),
                         (f'{track}_done_by_name', name), (f'{track}_done_by', account)):
        setattr(verification, field, value)
    verification.save()
    # Recorded with a before-snapshot when the record already existed, so an
    # imported verification becomes locally owned and a re-import keeps this.
    record(request.user, verification, before, action=f'verify_{track}')
    return JsonResponse({'id': valuation.pk, 'track': track, 'tracks': tracks_json(verification),
                         'next_track': next_track(verification, track)})


@endpoint(['PUT'])
def correct(request, pk, track):
    """A verifier's correction of their own track's answers, before verifying it."""
    track = track_named(track)
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    verification = m.ValuationVerification.objects.filter(valuation=valuation).first()
    if valuation.legacy_status != 'Submit':
        raise IntakeError('Only a submitted valuation can be corrected in verification', 409)
    if state(verification, track)['verified']:
        raise IntakeError(f'{TRACKS[track][1]} verification is already given; its answers can no longer be changed here', 409)
    questions = [q for q in form_questions(valuation) if owns(q, track)]
    save_section(request, valuation, questions, statuses=('Submit',), action=f'verifier_correct_{track}')
    sections, unassigned = track_questions(valuation, TRACKS[track][0])
    return JsonResponse({'id': valuation.pk, 'track': track, 'sections': sections, 'unassigned': unassigned})


@endpoint(['POST'])
def revert(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    if valuation.legacy_status != 'Submit':
        raise IntakeError('Only a submitted valuation can be sent back', 409)
    verification = m.ValuationVerification.objects.select_for_update().filter(valuation=valuation).first()
    if approved(verification):
        raise IntakeError('This valuation has final approval; it is sent back from the bank report stage', 409)
    remark, on = remark_and_date(payload(request, ['remark', 'date']), valuation)
    account, name = actor(request.user)
    if verification is not None:
        before = snapshot(verification)
        for track in TRACKS:
            if getattr(verification, f'{track}_status'):
                setattr(verification, f'{track}_status', UNVERIFIED)   # the verifier's name is kept
        if verification.final_status:
            verification.final_status = UNVERIFIED
        verification.save()
        record(request.user, verification, before, action='revert_verifications')
    before = snapshot(valuation)
    valuation.legacy_status = 'Revert'
    valuation.status_reason, valuation.status_reason_date = remark[:500], on
    valuation.save(update_fields=['legacy_status', 'status_reason', 'status_reason_date'])
    record(request.user, valuation, before, action='revert_valuation')
    m.Reversion.objects.create(valuation=valuation, remark=remark[:300], reverted_on=on, reverted_by=account,
                               reverted_by_name=name[:200], stage='verification')
    return JsonResponse({'id': valuation.pk, 'status': valuation.legacy_status, 'tracks': tracks_json(verification)})
