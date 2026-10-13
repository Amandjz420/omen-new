"""Copy the local copy of the previous user-management uploads to the bucket.

Every file under LEGACY_UAM_ROOT is uploaded, privately, to OMEN/uamupload/ plus its
path in the folder, then downloaded again and compared byte for byte. Files already
in the bucket are re-verified rather than uploaded again, so the command can be
re-run. The local folder is never changed. Dry run by default:

    manage.py upload_uam_files            # what would be uploaded
    manage.py upload_uam_files --apply    # upload and verify
    manage.py locate_legacy_files         # then point the documents at the copies
"""
import hashlib
import mimetypes
from pathlib import Path
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.documents import s3
from apps.documents.storage import UAM_COPY


def fetch(key):
    try:
        with urlopen(s3.presign(key), timeout=90) as response:
            return response.read()
    except OSError:
        return None


def same(key, data):
    copied = fetch(key)
    return copied is not None and hashlib.sha256(copied).digest() == hashlib.sha256(data).digest()


class Command(BaseCommand):
    help = 'Upload the local user-management uploads folder to the bucket, verified. Dry run by default.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        root = Path(settings.LEGACY_UAM_ROOT)
        if not root.is_dir():
            raise CommandError(f'The uploads folder {root} does not exist. Set OMEN_UAM_ROOT.')
        if not s3.configured():
            raise CommandError('The S3 credentials are not configured (AWS_* in the repository .env).')
        from apps.documents.management.commands.locate_legacy_files import listing
        files = sorted(p for p in root.rglob('*') if p.is_file() and p.name != '.DS_Store')
        present = listing(UAM_COPY)
        key_of = {p: UAM_COPY + p.relative_to(root).as_posix() for p in files}
        todo = [p for p in files if key_of[p] not in present]
        self.stdout.write(f'{len(files):,} files in {root}; {len(files) - len(todo):,} already in the bucket; '
                          f'{len(todo):,} to upload ({sum(p.stat().st_size for p in todo) / 1e6:.1f} MB).')
        if not options['apply']:
            return
        failed = []
        for n, path in enumerate(files, 1):
            data = path.read_bytes()
            if path in todo:
                try:
                    s3.upload(key_of[path], data, mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
                except Exception:
                    failed.append(key_of[path])
                    continue
            if not same(key_of[path], data):          # every file, uploaded now or before, is proven
                failed.append(key_of[path])
            if n % 200 == 0:
                self.stdout.write(f'  {n:,} of {len(files):,}')
        if failed:
            for key in failed[:20]:
                self.stdout.write(f'  failed: {key}')
            raise CommandError(f'{len(failed):,} files did not upload or verify. Re-run to retry them.')
        self.stdout.write(self.style.SUCCESS(f'All {len(files):,} files are in the bucket under {UAM_COPY}, verified.'))
