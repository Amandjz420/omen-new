"""Valuation photographs, and documents attached to answers.

Traced to ValuationController /uploadPhoto, /saveUploadPhoto, /deleteUploadPhoto,
/uploadDoc and /saveUploadDoc.

Photos are their own records, each of one PhotoTypeEnum type. The imported data
shows the working pattern: about six per valuation, one each of Front, Inside,
Right View, Left View, Location Plan and Site Plan, with Other rarely used.

Documents are not free-standing. On a document question such as "List of
documents produced for perusal", each chosen option may carry its own file, so
a document attaches to an existing answer row: 35,284 imported answers across
8,034 valuations carry one. An option must be chosen before its document can be
attached, as in the legacy form.

The legacy delete removed the photo row outright. On an imported valuation that
leaves a source identity pointing at nothing, which aborts the next import, so
photos of an edited valuation are owned by it (PARENT_OWNED in sync.py). The file
itself is kept as evidence; only the link is removed.
"""
from django.http import JsonResponse

from target_core import models as m
from apps.documents.storage import file_json, serve, store
from apps.common.http import IntakeError, endpoint, find
from apps.audit.services import record, snapshot
from apps.valuations.services import EDITABLE, in_scope

PHOTO_TYPES = [(1, 'Front'), (2, 'Inside'), (3, 'Right View'), (4, 'Left View'),
               (5, 'Location Plan'), (6, 'Site Plan'), (7, 'Other')]          # PhotoTypeEnum
PHOTO_LABELS = dict(PHOTO_TYPES)
EXPECTED = [1, 2, 3, 4, 5, 6]


def editable(valuation):
    if valuation.legacy_status not in EDITABLE:
        raise IntakeError(f'A {valuation.legacy_status or "closed"} valuation cannot be edited', 409)


def photo_json(photo):
    code = int(photo.attachment_type) if (photo.attachment_type or '').isdigit() else None
    return {'id': photo.pk, 'type': code, 'type_label': PHOTO_LABELS.get(code, 'Unclassified'),
            'caption': photo.name, 'file': file_json(photo.document)}


def photos_json(valuation):
    photos = list(m.ValuationAttachment.objects.filter(valuation=valuation).select_related('document')
                  .order_by('attachment_type', 'created_at'))
    have = {int(p.attachment_type) for p in photos if (p.attachment_type or '').isdigit()}
    return {'valuation': valuation.pk, 'editable': valuation.legacy_status in EDITABLE,
            'types': [{'code': c, 'label': l} for c, l in PHOTO_TYPES],
            'missing': [PHOTO_LABELS[c] for c in EXPECTED if c not in have],
            'photos': [photo_json(p) for p in photos]}


@endpoint(['GET', 'POST'])
def photos(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    if request.method == 'POST':
        valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
        editable(valuation)
        try:
            code = int(request.POST.get('type', ''))
        except ValueError:
            code = None
        if code not in PHOTO_LABELS:
            raise IntakeError('Choose what the photo shows')
        caption = (request.POST.get('caption') or '').strip()[:500]
        before = snapshot(valuation)
        record(request.user, valuation, before, action='add_valuation_photo')
        document = store(request.FILES.get('file'), 'photo', f'valuations/{valuation.pk}/photos')
        m.ValuationAttachment.objects.create(valuation=valuation, document=document, name=caption,
                                             attachment_type=str(code))
        return JsonResponse(photos_json(valuation), status=201)
    return JsonResponse(photos_json(valuation))


@endpoint(['DELETE'])
def photo(request, pk, photo_pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    editable(valuation)
    item = find(m.ValuationAttachment, photo_pk)
    if item.valuation_id != valuation.pk:
        raise IntakeError('Photo not found', 404)
    record(request.user, valuation, snapshot(valuation), action='remove_valuation_photo')
    item.delete()          # the Document and its file are kept as evidence
    return JsonResponse(photos_json(valuation))


@endpoint(['GET'])
def photo_file(request, pk, photo_pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    item = find(m.ValuationAttachment, photo_pk)
    if item.valuation_id != valuation.pk:
        raise IntakeError('Photo not found', 404)
    return serve(item.document)


def answer_for(valuation, data):
    """The answer row a document attaches to: question, option and row group."""
    question = find(m.Question, data.get('question'))
    if not question.is_document:
        raise IntakeError('Documents can be attached only to document questions')
    option = data.get('option') or None
    try:
        group = int(data.get('group') or 0)
    except ValueError:
        raise IntakeError('group must be a whole number')
    answer = (m.ValuationAnswer.objects.select_for_update()
              .filter(valuation=valuation, question=question, option_id=option, answer_group=group)
              .order_by('id').first())
    if answer is None:
        raise IntakeError('Choose the option and save the section before attaching its document', 409)
    return answer


@endpoint(['POST', 'DELETE'])
def answer_document(request, pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    valuation = m.Valuation.objects.select_for_update().get(pk=valuation.pk)
    editable(valuation)
    data = request.POST if request.method == 'POST' else request.GET
    answer = answer_for(valuation, data)
    record(request.user, valuation, snapshot(valuation),
           action='attach_answer_document' if request.method == 'POST' else 'detach_answer_document')
    if request.method == 'POST':
        answer.document = store(request.FILES.get('file'), 'document', f'valuations/{valuation.pk}/documents')
    else:
        answer.document = None          # the Document and its file are kept as evidence
    answer.save(update_fields=['document'])
    return JsonResponse({'answer': answer.pk, 'question': answer.question_id, 'option': answer.option_id,
                         'group': answer.answer_group, 'file': file_json(answer.document)},
                        status=201 if request.method == 'POST' else 200)


@endpoint(['GET'])
def document_file(request, pk, document_pk):
    valuation = find(m.Valuation, pk)
    in_scope(request.user, valuation.case)
    # Serve only a document that belongs to this valuation's answers.
    if not m.ValuationAnswer.objects.filter(valuation=valuation, document_id=document_pk).exists():
        raise IntakeError('File not found', 404)
    return serve(find(m.Document, document_pk))
