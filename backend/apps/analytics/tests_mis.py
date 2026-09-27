"""The MIS engine and the money reports."""
import datetime
import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook

from target_core import models as m
from apps.migration_pipeline.services import source_key
from apps.valuations.test_forms import Form, user_with_role


class MisTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.client.force_login(User.objects.create_user('staff', password='x', is_staff=True))
        self.today = timezone.localdate()

    def invoice(self, billed, remaining=0, days_ago=10, status='Submit', assigned=None, report=True, cancelled=False, **case):
        c = self.lead_with_case(assigned=assigned)
        for k, v in case.items():
            setattr(c, k, v)
        c.save()
        v = m.Valuation.objects.create(case=c, legacy_status=status, report_number=f'R-{m.Valuation.objects.count() + 1}')
        if report:
            m.BankReport.objects.create(valuation=v, revision=0)
        for head in range(6):                                              # six charge lines, as legacy invoices carry
            m.ValuationCharge.objects.create(valuation=v, amount=Decimal(billed) / 6)
        return m.Invoice.objects.create(valuation=v, origin='legacy_invoice', number=f'I-{m.Invoice.objects.count() + 1}',
                                        issued_date=self.today - datetime.timedelta(days=days_ago), billed_amount=Decimal(billed),
                                        legacy_paid_amount=Decimal(billed) - Decimal(remaining), legacy_remaining_amount=Decimal(remaining),
                                        cancelled_at=timezone.now() if cancelled else None)

    def get(self, key, **params):
        return self.client.get(f'/api/mis/{key}/', params)

    def test_money_is_counted_once_per_invoice_whatever_its_charge_lines(self):
        """Regression: the legacy query summed across six charge lines per invoice."""
        self.invoice('1180', remaining='680')
        t = self.get('invoices').json()['totals']
        self.assertEqual((t['invoices'], t['billed'], t['outstanding']), (1, '1180.00', '680.00'))

    def test_every_standing_invoice_counts_and_a_credited_one_does_not(self):
        self.invoice('100', report=False)                                   # the legacy inner join dropped this
        self.invoice('200', cancelled=True)                                 # reversed by a credit note
        self.assertEqual(self.get('invoices').json()['totals']['billed'], '100.00')

    def test_outstanding_is_money_owed_on_work_not_cancelled(self):
        self.invoice('100', remaining='40')
        self.invoice('100', remaining='0')
        self.invoice('100', remaining='30', status='Cancel')
        t = self.get('outstanding').json()['totals']
        self.assertEqual((t['invoices'], t['outstanding']), (1, '40.00'))

    def test_each_invoice_falls_into_exactly_one_age_band(self):
        """Regression: the legacy bands overlapped at 60 and 90 days."""
        for days in (60, 61, 90, 91, 121):
            self.invoice('100', remaining='10', days_ago=days)
        bands = {g['label']: g['values']['invoices'] for g in self.get('pending-recovery').json()['groups']}
        self.assertEqual(bands, {'0 to 60 days': 1, '61 to 90 days': 2, '91 to 120 days': 1, 'Over 120 days': 1})

    def test_the_six_invoice_groupings(self):
        a, b = m.Employee.objects.create(name='Asha'), m.Employee.objects.create(name='Vivek')
        self.invoice('100', assigned=a, asset_district='Bhopal', asset_state='Madhya Pradesh')
        self.invoice('300', assigned=b, asset_district='Itarsi', asset_state='Madhya Pradesh')
        for group in ('area', 'assessor', 'customer', 'client', 'service', 'division'):
            body = self.get('invoices', group=group).json()
            self.assertEqual(body['group'], group)
            self.assertEqual(sum(g['values']['invoices'] for g in body['groups']), 2, group)
        by_assessor = {g['label']: g['values']['billed'] for g in self.get('invoices', group='assessor').json()['groups']}
        self.assertEqual(by_assessor, {'Vivek': '300.00', 'Asha': '100.00'})
        self.assertEqual([g['label'] for g in self.get('invoices', group='area').json()['groups']][0], 'Itarsi, Madhya Pradesh')

    def test_the_date_filter_uses_the_invoice_date(self):
        self.invoice('100', days_ago=5)
        self.invoice('200', days_ago=40)
        since = (self.today - datetime.timedelta(days=10)).isoformat()
        self.assertEqual(self.get('invoices', **{'from': since}).json()['totals']['billed'], '100.00')
        self.assertEqual(self.get('invoices', **{'from': self.today.isoformat(), 'to': since}).status_code, 400)

    def test_the_records_behind_a_group(self):
        inv = self.invoice('100', remaining='25')
        group = self.get('outstanding', group='client').json()['groups'][0]['key']
        detail = self.get('outstanding', group='client', within=group).json()['detail']
        self.assertEqual((detail['total'], detail['rows'][0]['invoice'], detail['rows'][0]['outstanding']), (1, inv.number, '25.00'))

    def test_excel_export_has_a_summary_and_the_details(self):
        self.invoice('3850000', remaining='50000')
        response = self.client.get('/api/mis/outstanding/export/', {'group': 'client'})
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        wb = load_workbook(io.BytesIO(response.content))
        self.assertEqual(wb.sheetnames, ['Summary', 'Details'])
        summary = [c.value for row in wb['Summary'].iter_rows() for c in row if c.value is not None]
        self.assertIn('Omen Assessors: Outstanding', summary)
        self.assertIn(50000.0, summary)
        money_cell = next(c for row in wb['Details'].iter_rows(min_row=2) for c in row if c.value == 3850000.0)
        self.assertIn('##\\,##', money_cell.number_format)                    # Indian digit grouping

    def test_billing_by_liable_assessor_resolves_legacy_employee_ids(self):
        fa = m.Employee.objects.create(name='Ravi Liable')
        m.SourceIdentity.objects.create(batch=m.ImportBatch.objects.create(), environment='main', schema='uam_user',
                                        table='employee', key=source_key('57'), target_model='target_core.Employee', target_id=fa.pk)
        inv = self.invoice('500')
        m.BankReport.objects.filter(valuation=inv.valuation).update(legacy_liable_fa='57')
        groups = self.get('billing-by-assessor').json()['groups']
        self.assertEqual([(g['label'], g['values']['reports'], g['values']['billed']) for g in groups], [('Ravi Liable', 1, '500.00')])

    def test_a_restricted_user_sees_only_their_own_figures(self):
        me = m.Employee.objects.create(name='Assessor')
        self.invoice('100', assigned=me)
        self.invoice('900', assigned=m.Employee.objects.create(name='Other'))
        self.client.force_login(user_with_role('157', me))
        self.assertEqual(self.get('invoices').json()['totals']['billed'], '100.00')

    def test_the_catalogue_and_an_unknown_report(self):
        keys = [r['key'] for r in self.client.get('/api/mis/').json()['reports']]
        self.assertEqual(keys, ['invoices', 'outstanding', 'pending-recovery', 'total-amount', 'billing-by-client', 'billing-by-assessor'])
        self.assertEqual(self.get('no-such-report').status_code, 404)
