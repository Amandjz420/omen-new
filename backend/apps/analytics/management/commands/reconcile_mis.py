"""Reconcile the MIS with the legacy queries, run against the restored source.

Where the legacy query was correct the figures must match exactly. Where it was
wrong (MIS_LEGACY_QUERIES.md), the difference must be the documented defect and
nothing else. Needs the import settings, which carry the legacy connection:

    manage.py reconcile_mis --settings=config.full_database
"""
from collections import Counter, defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

from target_core import models as m
from apps.analytics.mis import REPORTS, ZERO, filters_from, run
from apps.migration_pipeline.services import source_key


class Everyone:                      # unrestricted, as a head-office user
    legacy_account = None


class Query(dict):
    GET = property(lambda self: self)


def engine(key, group=None, **f):
    spec = REPORTS[key]
    filters = filters_from(Query(**{k: str(v) for k, v in f.items()}))
    return run(spec, Everyone(), filters, group or spec['default_group'])


class Command(BaseCommand):
    help = 'Compare each MIS report with the legacy query it replaces.'

    def handle(self, *args, **options):
        self.cur = connections['lead_mngt'].cursor()
        self.failed = 0
        self.total_amount()
        self.invoices()
        self.outstanding()
        self.billing_by_client()
        self.billing_by_assessor()
        self.pending_recovery()
        self.stdout.write(self.style.SUCCESS('All reports reconcile.') if not self.failed
                          else self.style.ERROR(f'{self.failed} check(s) did not reconcile.'))

    def one(self, sql):
        self.cur.execute(sql)
        return self.cur.fetchone()

    def compare(self, label, legacy, ours, note=''):
        same = abs(Decimal(str(legacy or 0)) - Decimal(str(ours or 0))) < Decimal('0.5')
        self.failed += not same
        mark = 'matches' if same else 'DIFFERS'
        self.stdout.write(f'  {label:44s} legacy {legacy!s:>16}  ours {ours!s:>16}  {mark}{"  " + note if note else ""}')

    def quarantined_invoices(self):
        return set(m.SourceRow.objects.filter(schema='lead_mngt', table='invoice', outcome='quarantined').values_list('key', flat=True))

    def total_amount(self):
        self.stdout.write('\nTotal amount (legacy query correct: plain sums over invoices)')
        billed, paid, owed = self.one('SELECT SUM(total_invoice_amount), SUM(total_pay_amount), SUM(total_remaining_amount) FROM invoice')
        skipped = self.one("SELECT COUNT(*) FROM invoice WHERE invoice_id IN (%s)" % (','.join(
            k.split('"')[3] for k in self.quarantined_invoices()) or 'NULL'))[0]
        _, _, _, t = engine('total-amount')
        note = f'({skipped} quarantined invoice excluded on import)' if skipped else ''
        q_billed = self.one("SELECT COALESCE(SUM(total_invoice_amount),0) FROM invoice WHERE invoice_id IN (%s)" % (','.join(
            k.split('"')[3] for k in self.quarantined_invoices()) or 'NULL'))[0]
        self.compare('invoiced', round(billed - q_billed), round(t['billed']), note)
        self.compare('received', round(paid - self.one("SELECT COALESCE(SUM(total_pay_amount),0) FROM invoice WHERE invoice_id IN (%s)" % (','.join(
            k.split('"')[3] for k in self.quarantined_invoices()) or 'NULL'))[0]), round(t['paid']))

    def invoices(self):
        self.stdout.write('\nInvoices (legacy defect: summed across charge lines, and dropped invoices without a report)')
        n = self.one('SELECT COUNT(*) FROM invoice')[0]
        _, _, groups, t = engine('invoices')
        self.compare('invoices counted', n - len(self.quarantined_invoices()), t['invoices'], 'every standing invoice, once')

    def outstanding(self):
        self.stdout.write('\nOutstanding (counted once per invoice)')
        owed = self.one("""SELECT SUM(i.total_remaining_amount) FROM invoice i JOIN valuation v ON v.valuation_id=i.valuation_id
                           WHERE i.total_remaining_amount > 0 AND v.valuation_status <> 'Cancel'""")[0]
        _, _, _, t = engine('outstanding')
        self.compare('money still owed', round(owed), round(t['outstanding']), 'legacy report showed 6x this')

    def billing_by_client(self):
        self.stdout.write('\nBilling by client (legacy grouping by client, compared client by client)')
        self.cur.execute("""SELECT l.client_id, COUNT(i.invoice_id), SUM(i.total_invoice_amount) FROM invoice i
                            JOIN valuation v ON v.valuation_id=i.valuation_id JOIN lead_order lo ON lo.lead_order_id=v.lead_order_id
                            JOIN lead l ON l.lead_id=lo.lead_id GROUP BY l.client_id""")
        legacy = {r[0]: (r[1], r[2]) for r in self.cur.fetchall()}
        office = dict(m.SourceIdentity.objects.filter(environment='main', schema='lead_mngt', table='client').values_list('key', 'target_id'))
        _, _, groups, _ = engine('billing-by-client')
        ours = {g['key']: g['values'] for g in groups}
        mismatched = [c for c, (n, s) in legacy.items()
                      if (ours.get(str(office.get(source_key(c)))) or {}).get('invoices') != n]
        self.compare('clients whose invoice count differs', 0, len(mismatched), f'of {len(legacy)} clients')

    def billing_by_assessor(self):
        self.stdout.write('\nBilling by liable field assessor (bank reports per assessor)')
        self.cur.execute("SELECT liable_fa, COUNT(*) FROM valuation_bank_report WHERE liable_fa IS NOT NULL AND liable_fa <> '' GROUP BY liable_fa")
        legacy = dict(self.cur.fetchall())
        held = [r.payload for r in m.SourceRow.objects.filter(schema='lead_mngt', table='valuation_bank_report', outcome='quarantined')]
        held = sum(1 for r in held if r.get('liable_fa') not in (None, '', 0, '0'))
        _, _, groups, t = engine('billing-by-assessor')
        self.compare('bank reports with a liable assessor', sum(legacy.values()) - held, t['reports'],
                     f'({held} quarantined bank report excluded on import)' if held else '')

    def pending_recovery(self):
        self.stdout.write('\nPending recovery (legacy bands overlapped at 60 and 90 days)')
        _, _, groups, t = engine('pending-recovery')
        ours = {g['label']: g['values']['invoices'] for g in groups}
        self.cur.execute("""SELECT DATEDIFF(CURDATE(), i.invoice_date) FROM invoice i JOIN valuation v ON v.valuation_id=i.valuation_id
                            WHERE i.total_remaining_amount > 0 AND v.valuation_status <> 'Cancel'""")
        days = [d for (d,) in self.cur.fetchall()]
        legacy = {'0 to 60': sum(1 for d in days if 0 <= d <= 60), '60 to 90': sum(1 for d in days if 60 <= d <= 90),
                  '90 to 120': sum(1 for d in days if 90 <= d <= 120), 'over 120': sum(1 for d in days if d > 120)}
        double = sum(1 for d in days if d in (60, 90))
        self.compare('invoices outstanding', len(days), t['invoices'])
        self.stdout.write(f'  legacy bands {legacy} (sum {sum(legacy.values())}; {double} counted twice at a boundary)')
        self.stdout.write(f'  our bands    {ours} (sum {sum(ours.values())}; each invoice once)')
