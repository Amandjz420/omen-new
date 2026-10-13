"""Restore each valuation's earlier documents from the previous system.

The legacy "All uploaded docs history" (ValuationFullViewController /allDoc_view,
ValuationService.allUploadDoc) listed every upload whose doc_no reads
"<user>-<valuation>-<option>" (ValuationController sets it for an answer's
document). Uploads still linked to an answer or a photo are current; the rest are
earlier versions, replaced or removed. Each becomes a DocumentVersion of its
valuation, with its question (through the option) and upload date.

Run after every import, with the legacy database:
    manage.py link_document_history --settings=config.full_database
Safe to repeat: a document already recorded is left as it is.
"""
import datetime
import json

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone

from target_core import models as m


def targets(table):
    out = {}
    for key, target in m.SourceIdentity.objects.filter(environment='main', schema='lead_mngt', table=table).values_list('key', 'target_id'):
        try:
            out[str(json.loads(key)[0][1])] = target
        except (ValueError, IndexError, TypeError):
            pass
    return out


class Command(BaseCommand):
    help = "Record each valuation's earlier documents from the previous system."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, dry_run=False, **options):
        legacy = connections['lead_mngt'].cursor()
        legacy.execute('SELECT upload_id FROM valuation_answer WHERE upload_id IS NOT NULL')
        linked = {str(r[0]) for r in legacy.fetchall()}
        legacy.execute('SELECT upload_id FROM valuation_photo WHERE upload_id IS NOT NULL')
        linked |= {str(r[0]) for r in legacy.fetchall()}
        legacy.execute('SELECT upload_id, doc_no, doc_name, upload_date FROM upload')
        uploads = legacy.fetchall()
        documents, valuations, options = targets('upload'), targets('valuation'), targets('question_options')
        questions = dict(m.QuestionOption.objects.values_list('id', 'question_id'))
        known = set(str(x) for x in m.DocumentVersion.objects.values_list('document_id', flat=True))
        counts = {'earlier': 0, 'recorded': 0, 'already': 0, 'no file': 0, 'no valuation': 0}
        rows = []
        for upload_id, doc_no, name, uploaded in uploads:
            parts = str(doc_no or '').split('-')
            if len(parts) != 3 or str(upload_id) in linked:
                continue                                          # not an answer's document, or still current
            counts['earlier'] += 1
            document, valuation = documents.get(str(upload_id)), valuations.get(parts[1])
            if valuation is None:
                counts['no valuation'] += 1; continue
            if document is None:
                counts['no file'] += 1; continue
            if str(document) in known:
                counts['already'] += 1; continue
            option = options.get(parts[2])
            when = uploaded if isinstance(uploaded, datetime.datetime) else (
                datetime.datetime.combine(uploaded, datetime.time()) if isinstance(uploaded, datetime.date) else None)
            if when is not None and timezone.is_naive(when):
                when = timezone.make_aware(when)
            rows.append(m.DocumentVersion(valuation_id=valuation, document_id=document, question_id=questions.get(option),
                                          name=str(name or '')[:500], source=m.DocumentVersion.LEGACY, replaced_at=when))
            known.add(str(document))
        counts['recorded'] = len(rows)
        if not dry_run:
            with transaction.atomic():
                m.DocumentVersion.objects.bulk_create(rows, batch_size=1000)
        self.stdout.write(('Would record' if dry_run else 'Recorded') + f": {counts}")
