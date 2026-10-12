"""Copy existing local recordings to S3, verify bytes, then switch their location."""
import hashlib
from urllib.request import urlopen
from django.core.management.base import BaseCommand, CommandError
from target_core import models as m
from apps.documents import s3, storage


class Command(BaseCommand):
    help = 'Archive saved recordings to S3. Dry run by default; original local files are retained.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        ids = set()
        for source in m.AssistSource.objects.filter(kind='recording').only('document_ids'):
            ids.update(source.document_ids)
        documents = m.Document.objects.filter(pk__in=ids, storage_provider='local')
        self.stdout.write(f'{documents.count()} local recording(s) to archive.')
        if not options['apply']:
            return
        if not s3.configured():
            raise CommandError('Configure S3 before archiving recordings.')
        for document in documents:
            data = storage.read_bytes(document, limit=storage.MAX_BYTES)
            if not data:
                raise CommandError(f'Recording {document.pk} is missing or too large. Nothing changed for this recording.')
            key = f'OMEN/onsite/{document.storage_key}'
            s3.upload(key, data, document.media_type)
            try:
                with urlopen(s3.presign(key), timeout=90) as response:
                    copied = response.read(len(data) + 1)
            except OSError:
                raise CommandError('S3 verification failed. The local recording remains active.') from None
            if hashlib.sha256(copied).digest() != hashlib.sha256(data).digest():
                raise CommandError('S3 verification did not match. The local recording remains active.')
            m.Document.objects.filter(pk=document.pk, storage_provider='local').update(
                storage_provider='s3', storage_key=key, checksum=hashlib.sha256(data).hexdigest(), content_verified=True)
            self.stdout.write(f'Archived and verified recording {document.pk}. Local backup retained.')
