"""Remove credential-bearing keys from already-imported source staging.

The reader now drops these columns before anything is persisted, so new imports
cannot reintroduce them. This command repairs staging written before that fix.

It rewrites SourceRow payloads only. It never touches the source database or the
SQL dump, and it removes no non-secret identity evidence or source keys.
"""
import json

from django.core.management.base import BaseCommand
from django.db import transaction

from target_core.models import SourceRow
from target_core.sync import EXCLUDED_COLUMNS


class Command(BaseCommand):
    help = 'Strip credential columns from previously staged source payloads.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        affected, removed = 0, {}
        pending = []
        for row in SourceRow.objects.iterator(chunk_size=2000):
            present = [key for key in row.payload if key in EXCLUDED_COLUMNS]
            if not present:
                continue
            affected += 1
            for key in present:
                removed[key] = removed.get(key, 0) + 1
                del row.payload[key]
            pending.append(row)
            if len(pending) >= 500 and not options['dry_run']:
                SourceRow.objects.bulk_update(pending, ['payload'], batch_size=250)
                pending = []
        if pending and not options['dry_run']:
            SourceRow.objects.bulk_update(pending, ['payload'], batch_size=250)

        self.stdout.write(f'payloads affected {affected}')
        for key in sorted(removed):
            self.stdout.write(f'  removed {key:20s} {removed[key]}')
        if options['dry_run']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('dry run: rolled back'))
