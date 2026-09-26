"""Mark legacy amount-received entries that duplicate a cash receipt.

The amount_received table (2019-2022) was superseded by cash receipts, and its
history was copied across: an entry and a cash receipt on the same valuation's
invoice, with the same amount and date, record the same money once. Both are
imported, so without this each copied payment would count twice. The older entry
is kept as evidence and points at the cash receipt it duplicates; totals never
count a receipt with duplicate_of set.

Pairing is one-to-one, so no cash receipt absorbs two entries, and deterministic
(earliest first). Run after every import, like link_dispatch_items; it is
idempotent and never unlinks. An entry with no match is reported, not guessed.

    manage.py link_duplicate_receipts [--dry-run]
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from target_core import models as m


class Command(BaseCommand):
    help = 'Link amount-received entries to the cash receipts that duplicate them.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        taken = set(m.Receipt.objects.exclude(duplicate_of=None).values_list('duplicate_of_id', flat=True))
        candidates = defaultdict(list)
        for receipt in (m.Receipt.objects.filter(origin='legacy_cash_receipt', invoice__valuation__isnull=False)
                        .exclude(pk__in=taken).order_by('created_at', 'id')
                        .values('id', 'invoice__valuation_id', 'amount', 'received_date', 'amount_received_on')):
            for day in {receipt['received_date'], receipt['amount_received_on']} - {None}:
                candidates[(receipt['invoice__valuation_id'], receipt['amount'], day)].append(receipt['id'])
        linked, unmatched, updates = 0, [], []
        for entry in (m.Receipt.objects.filter(origin='legacy_amount_received', duplicate_of__isnull=True)
                      .order_by('created_at', 'id')):
            pool = candidates.get((entry.valuation_id, entry.amount, entry.received_date), [])
            match = next((c for c in pool if c not in taken), None)
            if match is None:
                unmatched.append(entry.pk)
                continue
            taken.add(match)
            entry.duplicate_of_id = match
            updates.append(entry)
            linked += 1
        if not options['dry_run']:
            m.Receipt.objects.bulk_update(updates, ['duplicate_of'], batch_size=500)
        if options['verbosity'] == 0:
            return
        already = m.Receipt.objects.filter(origin='legacy_amount_received').exclude(duplicate_of=None).count()
        self.stdout.write(f'{"Would link" if options["dry_run"] else "Linked"} {linked}; '
                          f'{len(unmatched)} without a matching cash receipt; '
                          f'{already if not options["dry_run"] else already + linked} now marked as duplicates.')
        if unmatched:
            self.stdout.write(f'Unmatched: {", ".join(str(u) for u in unmatched[:10])}')
