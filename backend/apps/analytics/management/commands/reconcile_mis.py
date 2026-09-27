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
        self.lead_reports()
        self.valuation_reports()
        self.service_rendered()
        self.cancelled_valuations()
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

    def held(self, table):
        return m.SourceRow.objects.filter(schema='lead_mngt', table=table, outcome='quarantined').count()

    def mapped(self, schema, table):
        return {k: str(v) for k, v in m.SourceIdentity.objects.filter(environment='main', schema=schema, table=table)
                .values_list('key', 'target_id')}

    def lead_reports(self):
        self.stdout.write('\nMonth-wise leads and Lead MIS (legacy counted deleted leads)')
        deleted = self.one('SELECT COUNT(*) FROM lead WHERE delete_status = 1')[0]
        self.cur.execute('SELECT lead_status, COUNT(*) FROM lead WHERE delete_status <> 1 OR delete_status IS NULL GROUP BY lead_status')
        legacy = {str(k): n for k, n in self.cur.fetchall()}
        _, _, groups, t = engine('leads', 'status')
        codes = {'New lead': '1', 'In process': '2', 'Cancelled': '3', 'Closed': '4'}
        ours = {codes.get(g['label'], g['label']): g['values']['leads'] for g in groups}
        # Quarantined leads count only if they were live; leads recorded here are added.
        held = sum(1 for r in m.SourceRow.objects.filter(schema='lead_mngt', table='lead', outcome='quarantined')
                   if str(r.payload.get('delete_status')) != '1')
        local = m.Lead.objects.exclude(legacy_deleted='1').filter(local_sequence__isnull=False)
        self.compare('leads, deleted ones left out', sum(legacy.values()) - held + local.count(), t['leads'],
                     f'the legacy report also counted {deleted} deleted leads'
                     + (f'; {local.count()} recorded here' if local.exists() else '') + (f'; {held} quarantined' if held else ''))
        for lead in local.values('legacy_status'):
            legacy[lead['legacy_status']] = legacy.get(lead['legacy_status'], 0) + 1
        differ = [k for k in set(legacy) | set(ours) if legacy.get(k, 0) != ours.get(k, 0)]
        self.compare('statuses whose count differs', 0, len(differ))
        self.cur.execute('SELECT client_id, COUNT(*) FROM lead WHERE (delete_status <> 1 OR delete_status IS NULL) AND client_id IS NOT NULL GROUP BY client_id')
        legacy_clients = dict(self.cur.fetchall())
        office = self.mapped('lead_mngt', 'client')
        _, _, groups, _ = engine('lead-mis', 'client')
        ours = {g['key']: g['values']['leads'] for g in groups}
        mismatched = [c for c, n in legacy_clients.items() if ours.get(office.get(source_key(c)), 0) != n]
        self.compare('clients whose lead count differs', 0, len(mismatched), f'of {len(legacy_clients)} clients')

    def valuation_reports(self):
        self.stdout.write('\nMonth-wise and doer-wise valuations')
        self.cur.execute('SELECT valuation_status, COUNT(*) FROM valuation GROUP BY valuation_status')
        legacy = dict(self.cur.fetchall())
        held = self.held('valuation')
        _, _, _, t = engine('doer-wise')
        self.compare('valuations', sum(legacy.values()) - held, t['valuations'], f'({held} quarantined on import)' if held else '')
        for code, key in (('Submit', 'submitted'), ('Pending', 'pending'), ('Revert', 'reverted'), ('Hold', 'held')):
            self.compare(f'  of which {code}', legacy.get(code, 0), t[key])
        self.cur.execute('SELECT valuation_done_by, COUNT(*) FROM valuation WHERE valuation_done_by IS NOT NULL GROUP BY valuation_done_by')
        legacy_doers = dict(self.cur.fetchall())
        for r in m.SourceRow.objects.filter(schema='lead_mngt', table='valuation', outcome='quarantined'):
            doer = r.payload.get('valuation_done_by')
            if doer in legacy_doers:
                legacy_doers[doer] -= 1                             # a quarantined valuation is not reported
        employee = self.mapped('uam_user', 'employee')
        _, _, groups, _ = engine('doer-wise', 'doer')
        ours = {g['key']: g['values']['valuations'] for g in groups}
        mismatched = [d for d, n in legacy_doers.items() if ours.get(employee.get(source_key(d)), 0) != n]
        self.compare('people whose valuation count differs', 0, len(mismatched), f'of {len(legacy_doers)} people')

    def service_rendered(self):
        self.stdout.write('\nService rendered (legacy defect: counted across charge lines)')
        joined = self.one("""SELECT COUNT(i.invoice_id), SUM(i.total_invoice_amount) FROM valuation v
                             JOIN valuation_billing vb ON vb.valuation_id = v.valuation_id JOIN invoice i ON i.valuation_id = v.valuation_id""")
        once = self.one('SELECT COUNT(*), SUM(total_invoice_amount) FROM invoice')
        _, _, _, t = engine('service-rendered')
        held_billed = self.one("SELECT COALESCE(SUM(total_invoice_amount),0) FROM invoice WHERE invoice_id IN (%s)" % (','.join(
            k.split('"')[3] for k in self.quarantined_invoices()) or 'NULL'))[0]
        self.compare('invoices, counted once', once[0] - len(self.quarantined_invoices()), t['invoices'],
                     f'the legacy query counted {joined[0]:,}')
        self.compare('invoiced, counted once', round(once[1] - held_billed), round(t['billed']),
                     f'the legacy query summed Rs {round(joined[1]):,}')

    def cancelled_valuations(self):
        self.stdout.write('\nCancelled valuations (legacy defect: one per client)')
        total = self.one("SELECT COUNT(*) FROM valuation WHERE valuation_status = 'Cancel'")[0]
        shown = self.one("""SELECT COUNT(*) FROM (SELECT l.client_id FROM valuation v JOIN lead_order lo ON v.lead_order_id = lo.lead_order_id
                            JOIN lead l ON l.lead_id = lo.lead_id WHERE v.valuation_status = 'Cancel' GROUP BY l.client_id) x""")[0]
        held = m.SourceRow.objects.filter(schema='lead_mngt', table='valuation', outcome='quarantined', payload__valuation_status='Cancel').count()
        _, _, _, t = engine('cancelled-valuations')
        self.compare('cancelled valuations listed', total - held, t['cancelled'],
                     f'the legacy report showed {shown}' + (f'; {held} quarantined' if held else ''))
