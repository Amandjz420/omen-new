"""Record where each of the previous system's files is.

Lists the bucket's LeadUpload/ and UAMUpload/ folders and the copy of the
user-management uploads in OMEN/uamupload/, then records on each legacy document its
exact location: for a user-management upload its copy first; then the stored key if
it exists, otherwise the key with doubled slashes collapsed; for a user-management
upload, last, the local folder if this machine has it; otherwise nothing, meaning not
found. Idempotent; run after each import and after upload_uam_files:

    manage.py locate_legacy_files
    manage.py locate_legacy_files --only uam    # just the user-management uploads
"""
import html
import re
import time
import urllib.request
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from target_core import models as m
from apps.documents import s3
from apps.documents.storage import LOCAL_MARK, PREFIX, UAM_COPY, contained


def page(query, attempts=4):
    """One page of a listing. Listing LeadUpload/ takes some 150 requests, and a slow
    connection times out on one of them now and then; each page is retried, freshly
    signed, rather than losing the whole run."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(s3.presign('', query=query), timeout=120) as r:
                return r.read().decode()
        except OSError:                                  # TimeoutError and URLError included
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def listing(prefix):
    keys, token = set(), None
    while True:
        query = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        if token:
            query['continuation-token'] = token
        body = page(query)
        keys.update(html.unescape(k) for k in re.findall(r'<Key>([^<]*)</Key>', body))
        token = (re.findall(r'<NextContinuationToken>([^<]*)', body) or [None])[0]
        if not token:
            return keys


class Command(BaseCommand):
    help = "Record where each of the previous system's files is: in the bucket or the local uploads folder."

    def add_arguments(self, parser):
        # Listing LeadUpload/ is ~150 requests; the user-management uploads need two.
        parser.add_argument('--only', choices=['lead', 'uam'],
                            help='Locate only the lead documents or only the user-management uploads.')

    def handle(self, *args, **options):
        if not s3.configured():
            raise CommandError('The S3 credentials are not configured (AWS_* in the repository .env).')
        self.stdout.write('Listing the bucket…')
        providers = {'lead': ['legacy_lead_s3'], 'uam': ['legacy_uam_local']}.get(options.get('only'), list(PREFIX))
        prefixes = [PREFIX[p] for p in providers] + ([UAM_COPY] if 'legacy_uam_local' in providers else [])
        found = {p: listing(p) for p in prefixes}
        self.stdout.write('  ' + ', '.join(f'{p} {len(keys):,} objects' for p, keys in found.items()))
        now, outcome, changed = timezone.now(), Counter(), []
        for doc in m.Document.objects.filter(storage_provider__in=providers).only('id', 'storage_provider', 'storage_key',
                                                                               'legacy_location', 'legacy_checked_at').iterator(2000):
            prefix, key = PREFIX[doc.storage_provider], doc.storage_key.lstrip('/')
            location, how = '', 'not found'
            uam = doc.storage_provider == 'legacy_uam_local'
            if uam and UAM_COPY + key in found[UAM_COPY]:
                location, how = UAM_COPY + key, 'bucket, uploads folder copy'
            elif prefix + key in found[prefix]:
                location, how = prefix + key, 'bucket, as stored'
            elif prefix + re.sub('/+', '/', key) in found[prefix]:
                location, how = prefix + re.sub('/+', '/', key), 'bucket, doubled slash collapsed'
            elif uam and contained(settings.LEGACY_UAM_ROOT, key):
                location, how = LOCAL_MARK + key, 'local uploads folder'
            outcome[(doc.storage_provider, how)] += 1
            if doc.legacy_location != location or doc.legacy_checked_at is None:
                doc.legacy_location, doc.legacy_checked_at = location, now
                changed.append(doc)
            if len(changed) >= 2000:
                m.Document.objects.bulk_update(changed, ['legacy_location', 'legacy_checked_at'])
                changed = []
        if changed:
            m.Document.objects.bulk_update(changed, ['legacy_location', 'legacy_checked_at'])
        for (provider, how), n in sorted(outcome.items()):
            self.stdout.write(f'  {provider:18s} {how:34s} {n:>9,}')
        missing = sum(n for (_, how), n in outcome.items() if how == 'not found')
        self.stdout.write(self.style.SUCCESS('Every legacy file was found.') if not missing
                          else self.style.WARNING(f'{missing:,} legacy files were not found; they are shown as unavailable.'))
