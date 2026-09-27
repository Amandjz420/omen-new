"""Record where each of the previous system's files is.

Lists the bucket's LeadUpload/ and UAMUpload/ folders and checks the local copy of
the user-management uploads, then records on each legacy document its exact
location: the stored key if it exists, otherwise the key with doubled slashes
collapsed, otherwise nothing, meaning not found. Idempotent; run after each import:

    manage.py locate_legacy_files
"""
import html
import re
import urllib.request
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from target_core import models as m
from apps.documents import s3
from apps.documents.storage import LOCAL_MARK, PREFIX, contained


def listing(prefix):
    keys, token = set(), None
    while True:
        query = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        if token:
            query['continuation-token'] = token
        with urllib.request.urlopen(s3.presign('', query=query), timeout=60) as r:
            body = r.read().decode()
        keys.update(html.unescape(k) for k in re.findall(r'<Key>([^<]*)</Key>', body))
        token = (re.findall(r'<NextContinuationToken>([^<]*)', body) or [None])[0]
        if not token:
            return keys


class Command(BaseCommand):
    help = "Record where each of the previous system's files is: in the bucket or the local uploads folder."

    def handle(self, *args, **options):
        if not s3.configured():
            raise CommandError('The S3 credentials are not configured (AWS_* in the repository .env).')
        self.stdout.write('Listing the bucket…')
        found = {p: listing(p) for p in PREFIX.values()}
        self.stdout.write(f"  LeadUpload/ {len(found['LeadUpload/']):,} objects, UAMUpload/ {len(found['UAMUpload/']):,}")
        now, outcome, changed = timezone.now(), Counter(), []
        for doc in m.Document.objects.filter(storage_provider__in=PREFIX).only('id', 'storage_provider', 'storage_key',
                                                                               'legacy_location', 'legacy_checked_at').iterator(2000):
            prefix, key = PREFIX[doc.storage_provider], doc.storage_key.lstrip('/')
            location, how = '', 'not found'
            if doc.storage_provider == 'legacy_uam_local' and contained(settings.LEGACY_UAM_ROOT, key):
                location, how = LOCAL_MARK + key, 'local uploads folder'
            elif prefix + key in found[prefix]:
                location, how = prefix + key, 'bucket, as stored'
            elif prefix + re.sub('/+', '/', key) in found[prefix]:
                location, how = prefix + re.sub('/+', '/', key), 'bucket, doubled slash collapsed'
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
