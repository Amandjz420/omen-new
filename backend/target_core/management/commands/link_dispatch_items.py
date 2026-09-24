"""Resolve each dispatch's report references into DispatchItem links.

Legacy dispatch rows carry no foreign key. The reports a dispatch delivered are
listed as comma-separated report numbers in nature_of_docs (imported verbatim as
Dispatch.report_references), which the legacy DispatchController splits and joins
to valuation.report_no. This command reproduces that join as real relations.

Every reference is recorded, whether or not it resolves, so the raw evidence is
never reduced to only what matched:
  exact        the token is a report number of exactly one valuation
  normalized   it matches once spacing, a missing hyphen or a missing "R-"
               prefix is corrected ("R0522116328" -> "R-0522116328")
  lead_number  a lead number keyed into the report field; linked to the lead
  unresolved   no valuation carries it. Recorded, never discarded.

valuation.report_no is unique across all valuations, so no reference can match
more than one. Ids are deterministic, so rerunning changes nothing, and a
dispatch whose reference list shrinks on re-import loses the surplus items.
"""
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from target_core import models as m

NAMESPACE = uuid.UUID('6f1f4b8e-2a5c-4c1a-9d8e-0b7a3e5d2c11')


def tokens(text):
    return [t.strip() for t in (text or '').split(',') if t.strip()]


def candidates(token):
    """Correction forms tried, in order, after the exact match fails."""
    s = token.replace(' ', '').upper()
    forms = [s]
    if s.startswith('R') and not s.startswith('R-'):
        forms.append('R-' + s[1:])
    if s.isdigit():
        forms.append('R-' + s)
    return forms


class Command(BaseCommand):
    help = 'Link dispatch report references to valuations.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        valuations = dict(m.Valuation.objects.exclude(report_number='')
                          .values_list('report_number', 'id'))
        leads = dict(m.Lead.objects.exclude(number='').values_list('number', 'id'))
        existing = {(i.dispatch_id, i.position): i for i in m.DispatchItem.objects.all()}
        counts = {k: 0 for k, _ in m.DispatchItem.RESOLUTIONS}
        creates, updates, keep = [], [], set()

        for dispatch in m.Dispatch.objects.only('id', 'report_references').iterator(chunk_size=2000):
            for position, token in enumerate(tokens(dispatch.report_references)):
                valuation_id = lead_id = None
                if token in valuations:
                    resolution, valuation_id = m.DispatchItem.EXACT, valuations[token]
                else:
                    form = next((f for f in candidates(token) if f in valuations), None)
                    if form:
                        resolution, valuation_id = m.DispatchItem.NORMALIZED, valuations[form]
                    elif token in leads or token.replace(' ', '').upper() in leads:
                        resolution = m.DispatchItem.LEAD_NUMBER
                        lead_id = leads.get(token) or leads.get(token.replace(' ', '').upper())
                    else:
                        resolution = m.DispatchItem.UNRESOLVED
                counts[resolution] += 1
                key = (dispatch.id, position)
                keep.add(key)
                values = dict(reference=token[:100], valuation_id=valuation_id,
                              lead_id=lead_id, resolution=resolution)
                prior = existing.get(key)
                if prior is None:
                    creates.append(m.DispatchItem(
                        id=uuid.uuid5(NAMESPACE, f'{dispatch.id}:{position}'),
                        dispatch_id=dispatch.id, position=position, **values))
                elif any(getattr(prior, f) != v for f, v in values.items()):
                    for f, v in values.items():
                        setattr(prior, f, v)
                    updates.append(prior)

        stale = [i.id for k, i in existing.items() if k not in keep]
        if not options['dry_run']:
            m.DispatchItem.objects.bulk_create(creates, batch_size=1000)
            m.DispatchItem.objects.bulk_update(updates, ['reference', 'valuation', 'lead', 'resolution'], batch_size=500)
            m.DispatchItem.objects.filter(id__in=stale).delete()

        total = sum(counts.values())
        for key, label in m.DispatchItem.RESOLUTIONS:
            self.stdout.write(f'{key:12s} {counts[key]:7,}  {label}')
        linked = counts['exact'] + counts['normalized']
        self.stdout.write(f'{"total":12s} {total:7,}  linked to a valuation: {linked:,} '
                          f'({linked / total * 100 if total else 0:.2f}%)')
        self.stdout.write(f'created {len(creates):,}  updated {len(updates):,}  removed {len(stale):,}')
        if options['dry_run']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('dry run: rolled back'))
