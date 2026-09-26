import uuid
"""Invoicing: issue, GST, numbering, balances, payments, write-offs and credit notes."""
import io
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from pypdf import PdfReader

from target_core import models as m
from target_core.sync import source_key
from apps.reports.test_approvals import Approval
from apps.reports.test_reports import MEDIA


@override_settings(MEDIA_ROOT=MEDIA)
class Invoicing(Approval):
    def setUp(self):
        super().setUp()
        batch = m.ImportBatch.objects.create()
        self.professional = m.ChargeType.objects.create(name='Professional charges', legacy_status='1', legacy_deleted='0', source_sequence=1)
        self.discount = m.ChargeType.objects.create(name='Discount (if any)', legacy_status='1', legacy_deleted='0', source_sequence=2)
        self.courier = m.ChargeType.objects.create(name='Delivery / Courier Charges', legacy_status='1', legacy_deleted='0', source_sequence=6)
        m.SourceIdentity.objects.create(batch=batch, environment='main', schema='lead_mngt', table='billing_head',
                                        key=source_key('2'), target_model='target_core.ChargeType', target_id=self.discount.pk)
        for head, amount in ((self.professional, '1000'), (self.discount, '-100'), (self.courier, '100')):
            m.ValuationCharge.objects.create(valuation_id=self.v, charge_type=head, amount=Decimal(amount))
        m.Valuation.objects.filter(pk=self.v).update(advance_collected=Decimal('0'))
        self.sbi_account = m.IssuerAccount.objects.create(name='State Bank of india', code=2, account_number='000009684', ifsc_code='SBIN0005793')
        office = m.Valuation.objects.get(pk=self.v).case.lead.office
        m.ClientOffice.objects.filter(pk=office.pk).update(gstin='23ABCDE1234F1Z5')
        self.generate()

    def issue(self, **overrides):
        body = {'place': 'intra', 'party': 1, 'account': str(self.sbi_account.pk), **overrides}
        return self.client.post(f'/api/invoices/valuations/{self.v}/', body, content_type='application/json')

    def pay(self, invoice, amount, operation_id=None, **extra):
        body = {'operation_id': str(operation_id or uuid.uuid4()), 'amount': amount, **extra}
        return self.client.post(f'/api/invoices/{invoice}/payments/', body, content_type='application/json')

    def pdf(self, url):
        r = self.client.get(url)
        return ' '.join(''.join(p.extract_text() for p in PdfReader(io.BytesIO(b''.join(r.streaming_content))).pages).split())


class IssueTests(Invoicing):
    def test_intra_state_splits_gst_into_cgst_and_sgst(self):
        body = self.issue().json()
        # taxable 1000 - 100 + 100 = 1000; 9% + 9% on each line
        self.assertEqual((body['total'], body['remaining']), ('1180.00', '1180.00'))
        pro = next(l for l in body['lines'] if l['description'] == 'Professional charges')
        self.assertEqual((pro['cgst'], pro['sgst'], pro['igst'], pro['total']), ('90.00', '90.00', '0.00', '1180.00'))
        disc = next(l for l in body['lines'] if l['description'].startswith('Discount'))
        self.assertEqual((disc['amount'], disc['cgst']), ('-100.00', '-9.00'))

    def test_inter_state_puts_all_gst_into_igst(self):
        body = self.issue(place='inter').json()
        pro = next(l for l in body['lines'] if l['description'] == 'Professional charges')
        self.assertEqual((pro['cgst'], pro['igst']), ('0.00', '180.00'))
        self.assertEqual(body['total'], '1180.00')

    def test_the_number_continues_the_online_series_not_the_offline_one(self):
        m.Invoice.objects.create(origin='legacy_invoice', number='I-09260911946')
        m.Invoice.objects.create(origin='legacy_offline_invoice', number='I-11200315556')
        self.assertTrue(self.issue().json()['number'].endswith('11947'))

    def test_the_lines_are_snapshotted_and_the_billing_updated(self):
        self.issue()
        invoice = m.Invoice.objects.get(local_sequence__isnull=False)
        self.assertEqual(invoice.lines.count(), 3)
        charge = m.ValuationCharge.objects.get(valuation_id=self.v, charge_type=self.professional)
        self.assertEqual((charge.cgst, charge.sgst), (Decimal('90.00'), Decimal('90.00')))
        v = m.Valuation.objects.get(pk=self.v)
        self.assertEqual((v.total_after_tax, v.total_after_tax_words), (Decimal('1180.00'), 'One Thousand One Hundred Eighty'))

    def test_an_advance_above_the_total_is_recorded_as_excess(self):
        """Regression: the legacy code zeroed remaining and then read it as the excess."""
        m.Valuation.objects.filter(pk=self.v).update(advance_collected=Decimal('1500'))
        body = self.issue().json()
        self.assertEqual((body['remaining'], body['excess']), ('0.00', '320.00'))

    def test_a_valuation_is_invoiced_once(self):
        self.issue()
        self.assertIn('already has an invoice', self.issue().json()['error'])

    def test_an_invoice_needs_the_bank_report(self):
        m.BankReport.objects.update(superseded_at=timezone.now())
        self.assertIn('bank report', self.issue().json()['error'])

    def test_another_partys_gstin_is_required_and_validated(self):
        self.assertEqual(self.issue(party=3).status_code, 400)
        self.assertEqual(self.issue(party=3, other_gstin='NOT-A-GSTIN').status_code, 400)
        self.assertEqual(self.issue(party=3, other_gstin='27AABCU9603R1ZM').status_code, 201)

    def test_the_place_of_supply_is_suggested_from_the_gstin_state(self):
        draft = self.client.get(f'/api/invoices/valuations/{self.v}/').json()
        self.assertEqual(draft['suggested_place'], 'intra')                    # 23 = Madhya Pradesh
        office = m.Valuation.objects.get(pk=self.v).case.lead.office
        m.ClientOffice.objects.filter(pk=office.pk).update(gstin='27ABCDE1234F1Z5')
        self.assertEqual(self.client.get(f'/api/invoices/valuations/{self.v}/').json()['suggested_place'], 'inter')

    def test_the_document_is_a_tax_invoice(self):
        invoice = self.issue().json()
        text = self.pdf(f"/api/invoices/{invoice['id']}/document/")
        for expected in ('TAX INVOICE', '23AABFO1645E1ZS', invoice['number'], 'Professional charges', '1,180.00',
                         'One Thousand One Hundred Eighty', 'SBIN0005793', 'Intra State'):
            self.assertIn(expected, text)


class PaymentTests(Invoicing):
    def test_partial_then_full_payment(self):
        invoice = self.issue().json()['id']
        partial = self.pay(invoice, '500').json()
        self.assertEqual((partial['remaining'], partial['payment_status']), ('680.00', 'Partly paid'))
        full = self.pay(invoice, '680').json()
        self.assertEqual((full['remaining'], full['payment_status']), ('0.00', 'Fully paid'))
        self.assertEqual(len(full['payments']), 2)
        self.assertEqual(m.Receipt.objects.filter(invoice_id=invoice).count(), 2)

    def test_an_overpayment_is_recorded_as_excess(self):
        invoice = self.issue().json()['id']
        body = self.pay(invoice, '1200').json()
        self.assertEqual((body['remaining'], body['excess']), ('0.00', '20.00'))

    def test_a_payment_needs_an_amount_and_a_real_date(self):
        invoice = self.issue().json()['id']
        self.assertEqual(self.pay(invoice, '0').status_code, 400)
        future = (timezone.localdate() + timezone.timedelta(days=1)).isoformat()
        self.assertEqual(self.pay(invoice, '10', date=future).status_code, 400)

    def test_writing_off_the_remainder_closes_the_invoice(self):
        invoice = self.issue().json()['id']
        self.pay(invoice, '1000')
        wo = lambda a, r='Bank will not pay': self.client.post(f'/api/invoices/{invoice}/write-off/',
                                                                 {'operation_id': str(uuid.uuid4()), 'amount': a, 'remark': r},
                                                                 content_type='application/json')
        self.assertEqual(wo('500').status_code, 400)                           # more than is owed
        self.assertEqual(wo('180', r='').status_code, 400)                     # no reason
        body = wo('180').json()
        self.assertEqual((body['remaining'], body['bad_debt'], body['payment_status']), ('0.00', '180.00', 'Fully paid'))


class CreditNoteTests(Invoicing):
    def credit(self, invoice, reason='Double entry'):
        return self.client.post(f'/api/invoices/{invoice}/credit-note/', {'reason': reason}, content_type='application/json')

    def test_a_credit_note_reverses_the_invoice_without_deleting_it(self):
        invoice = self.issue().json()['id']
        self.pay(invoice, '300')
        body = self.credit(invoice).json()
        self.assertTrue(body['cancelled'])
        note = body['credit_notes'][0]
        self.assertRegex(note['number'], r'^CN-\d{6}0001$')
        self.assertEqual((note['total'], note['refund_due']), ('1180.00', '300.00'))
        self.assertTrue(m.Invoice.objects.filter(pk=invoice).exists())

    def test_a_credited_invoice_takes_no_further_payments(self):
        invoice = self.issue().json()['id']
        self.credit(invoice)
        self.assertEqual(self.pay(invoice, '10').status_code, 409)

    def test_a_credit_note_releases_billing_and_cancellation(self):
        invoice = self.issue().json()['id']
        self.assertEqual(self.standing('cancel').status_code, 409)
        self.credit(invoice)
        self.assertEqual(self.standing('cancel').json()['status'], 'Cancel')

    def test_a_credited_valuation_can_be_invoiced_again(self):
        first = self.issue().json()
        self.credit(first['id'])
        second = self.issue().json()
        self.assertNotEqual(first['number'], second['number'])

    def test_a_reason_is_required(self):
        invoice = self.issue().json()['id']
        self.assertEqual(self.credit(invoice, reason='').status_code, 400)

    def test_the_credit_note_document(self):
        invoice = self.issue().json()
        note = self.credit(invoice['id']).json()['credit_notes'][0]
        text = self.pdf(f"/api/invoices/credit-notes/{note['id']}/document/")
        for expected in ('CREDIT NOTE', note['number'], invoice['number'], 'Double entry'):
            self.assertIn(expected, text)


class QueueTests(Invoicing):
    def test_the_buckets_follow_the_invoice_through_its_life(self):
        counts = lambda: self.client.get('/api/invoices/').json()['counts']
        self.assertEqual(counts()['to_invoice'], 1)
        invoice = self.issue().json()['id']
        self.assertEqual((counts()['to_invoice'], counts()['unpaid']), (0, 1))
        self.pay(invoice, '1180')
        self.assertEqual((counts()['unpaid'], counts()['paid']), (0, 1))


class CreditNoteNumberTests(Invoicing):
    def test_credit_notes_never_share_a_number_with_a_cash_receipt(self):
        """Legacy cash receipts use C- + MMYYDD + counter."""
        from django.utils import timezone as tz
        receipt_number = f"C-{tz.localdate():%m%y%d}0001"
        m.Receipt.objects.create(origin='legacy_cash_receipt', number=receipt_number)
        invoice = self.issue().json()['id']
        note = self.client.post(f'/api/invoices/{invoice}/credit-note/', {'reason': 'x'},
                                content_type='application/json').json()['credit_notes'][0]
        self.assertNotEqual(note['number'], receipt_number)
        self.assertTrue(note['number'].startswith('CN-'))

    def test_longer_prefixes_read_the_counter_from_the_right_place(self):
        import datetime
        from target_core.numbering import format_number, legacy_maximum
        m.CreditNote.objects.create(invoice=m.Invoice.objects.create(origin='x', number='I-1'),
                                    number=format_number('CN', datetime.date(2026, 9, 25), 42), local_sequence=42,
                                    issued_on=datetime.date(2026, 9, 25), taxable_amount=1, tax_amount=0, total_amount=1, reason='r')
        self.assertEqual(legacy_maximum(m.CreditNote, 'number', 'CN'), 42)
        self.assertEqual(format_number('CN', datetime.date(2026, 9, 25), 42), 'CN-0926250042')


class RetryTests(Invoicing):
    """Review finding G3: a retried payment must not book the money twice."""

    def test_a_retried_payment_is_booked_once(self):
        invoice = self.issue().json()['id']
        op = uuid.uuid4()
        first = self.pay(invoice, '100', operation_id=op).json()
        again = self.pay(invoice, '100', operation_id=op).json()
        self.assertEqual((first['paid'], again['paid']), ('100.00', '100.00'))      # previously 200.00
        self.assertTrue(again['replayed'])
        self.assertEqual(m.Receipt.objects.filter(invoice_id=invoice).count(), 1)

    def test_two_separate_equal_payments_both_count(self):
        invoice = self.issue().json()['id']
        self.pay(invoice, '100')
        self.assertEqual(self.pay(invoice, '100').json()['paid'], '200.00')

    def test_an_operation_id_cannot_be_reused_for_a_different_payment(self):
        invoice = self.issue().json()['id']
        op = uuid.uuid4()
        self.pay(invoice, '100', operation_id=op)
        self.assertEqual(self.pay(invoice, '250', operation_id=op).status_code, 409)

    def test_a_payment_needs_an_operation_id(self):
        invoice = self.issue().json()['id']
        response = self.client.post(f'/api/invoices/{invoice}/payments/', {'amount': '100'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_a_retried_write_off_is_applied_once(self):
        invoice = self.issue().json()['id']
        body = {'operation_id': str(uuid.uuid4()), 'amount': '180', 'remark': 'Unrecoverable'}
        post = lambda: self.client.post(f'/api/invoices/{invoice}/write-off/', body, content_type='application/json').json()
        self.assertEqual(post()['bad_debt'], '180.00')
        self.assertEqual(post()['bad_debt'], '180.00')
        self.assertEqual(m.FinancialOperation.objects.filter(kind='write_off').count(), 1)


class OfflineInvoiceTests(Invoicing):
    """Review finding G4: offline invoices must be visible and settle correctly."""

    def setUp(self):
        super().setUp()
        import datetime
        self.offline = m.Invoice.objects.create(origin='legacy_offline_invoice', number='I-1120251794',
                                                issued_date=datetime.date(2020, 11, 25), billed_amount=Decimal('1000'),
                                                advance_amount=Decimal('200'), billed_to_name='State Bank of India',
                                                billed_customer_name='M/s Offline Traders', reference_report='R-OFF-1')
        m.Receipt.objects.create(origin='legacy_offline_amount_received', invoice=self.offline, amount=Decimal('300'),
                                 received_date=datetime.date(2020, 12, 1))

    def offline_queue(self, due=False):
        return self.client.get(f"/api/invoices/?state=offline{'&due=1' if due else ''}").json()

    def test_codex_reproduction_offline_invoices_appear_in_their_own_queue(self):
        body = self.offline_queue()
        self.assertEqual(body['counts']['offline'], 1)                                  # previously invisible
        row = body['results'][0]
        self.assertEqual((row['number'], row['billed_to'], row['remaining']), ('I-1120251794', 'State Bank of India', '500.00'))

    def test_the_balance_is_total_less_advance_and_recorded_payments(self):
        body = self.client.get(f'/api/invoices/{self.offline.pk}/').json()
        self.assertEqual((body['paid'], body['remaining'], body['advance']), ('500.00', '500.00', '200.00'))
        self.assertTrue(body['offline'])
        self.assertEqual(body['references']['report'], 'R-OFF-1')
        self.assertEqual(body['payments'][0]['recorded'], 'previous system')

    def test_a_payment_here_adds_to_the_advance_and_recorded_payments(self):
        body = self.pay(self.offline.pk, '400').json()
        self.assertEqual((body['paid'], body['remaining']), ('900.00', '100.00'))
        body = self.pay(self.offline.pk, '100').json()
        self.assertEqual((body['remaining'], body['payment_status']), ('0.00', 'Fully paid'))

    def test_the_outstanding_filter(self):
        self.assertEqual(self.offline_queue(due=True)['total'], 1)
        self.pay(self.offline.pk, '500')
        self.assertEqual(self.offline_queue(due=True)['total'], 0)
        self.assertEqual(self.offline_queue()['total'], 1)

    def test_a_restricted_user_cannot_see_offline_invoices(self):
        from apps.valuations.test_forms import user_with_role
        self.client.force_login(user_with_role('157', m.Employee.objects.create(name='Assessor')))
        self.assertEqual(self.offline_queue()['total'], 0)
        self.assertEqual(self.client.get(f'/api/invoices/{self.offline.pk}/').status_code, 404)


class DuplicateReceiptTests(Invoicing):
    """amount_received entries copied into cash receipts must count once."""

    def run_link(self):
        from django.core.management import call_command
        call_command('link_duplicate_receipts', verbosity=0)

    def test_a_copied_entry_is_linked_to_its_cash_receipt(self):
        import datetime
        invoice = m.Invoice.objects.create(origin='legacy_invoice', number='I-0322010001', valuation_id=self.v)
        day = datetime.date(2022, 3, 1)
        receipt = m.Receipt.objects.create(origin='legacy_cash_receipt', invoice=invoice, amount=Decimal('500'), received_date=day)
        copy = m.Receipt.objects.create(origin='legacy_amount_received', valuation_id=self.v, amount=Decimal('500'), received_date=day)
        other = m.Receipt.objects.create(origin='legacy_amount_received', valuation_id=self.v, amount=Decimal('999'), received_date=day)
        self.run_link()
        copy.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(copy.duplicate_of_id, receipt.pk)
        self.assertIsNone(other.duplicate_of_id)                           # no match: reported, not guessed
        self.run_link()                                                    # idempotent
        self.assertEqual(m.Receipt.objects.exclude(duplicate_of=None).count(), 1)

    def test_one_cash_receipt_absorbs_only_one_entry(self):
        import datetime
        invoice = m.Invoice.objects.create(origin='legacy_invoice', number='I-0322010002', valuation_id=self.v)
        day = datetime.date(2022, 3, 2)
        m.Receipt.objects.create(origin='legacy_cash_receipt', invoice=invoice, amount=Decimal('500'), received_date=day)
        for _ in range(2):
            m.Receipt.objects.create(origin='legacy_amount_received', valuation_id=self.v, amount=Decimal('500'), received_date=day)
        self.run_link()
        self.assertEqual(m.Receipt.objects.filter(origin='legacy_amount_received').exclude(duplicate_of=None).count(), 1)


class CashReceiptTests(Invoicing):
    """Maker, checker and verifier."""

    def setUp(self):
        super().setUp()
        self.invoice = self.issue().json()['id']                        # total 1180.00

    def make(self, operation_id=None, **overrides):
        body = {'operation_id': str(operation_id or uuid.uuid4()), 'received_as': 2, 'invoice': self.invoice,
                'amount': '500', 'payment_mode': 4, 'payer_name': 'State Bank of India', **overrides}
        return self.client.post('/api/receipts/', body, content_type='application/json')

    def step(self, receipt, action, **body):
        return self.client.post(f'/api/receipts/{receipt}/{action}/', body, content_type='application/json')

    def paid(self):
        return self.client.get(f'/api/invoices/{self.invoice}/').json()

    def test_a_receipt_continues_the_legacy_series(self):
        m.Receipt.objects.create(origin='legacy_cash_receipt', number='C-09261011210')
        body = self.make().json()
        self.assertTrue(body['number'].endswith('11211'))
        self.assertEqual(body['stage'], 'to_check')

    def test_a_recovery_settles_its_invoice_only_when_verified(self):
        receipt = self.make().json()['id']
        self.assertEqual(self.paid()['paid'], '0.00')
        self.step(receipt, 'check')
        self.assertEqual(self.paid()['paid'], '0.00')
        self.assertEqual(self.step(receipt, 'verify').json()['stage'], 'verified')
        body = self.paid()
        self.assertEqual((body['paid'], body['remaining'], body['payment_status']), ('500.00', '680.00', 'Partly paid'))
        self.assertEqual(m.Valuation.objects.get(pk=self.v).remaining_amount, Decimal('680.00'))

    def test_an_overpayment_records_the_true_excess(self):
        """Regression: legacy verification recorded the whole receipt as the excess."""
        receipt = self.make(amount='1500').json()['id']
        self.step(receipt, 'check')
        self.step(receipt, 'verify', confirm_overpayment=True)
        body = self.paid()
        self.assertEqual((body['remaining'], body['excess']), ('0.00', '320.00'))

    def test_a_receipt_settles_its_invoice_once(self):
        receipt = self.make().json()['id']
        self.step(receipt, 'check')
        self.step(receipt, 'verify')
        self.assertEqual(self.step(receipt, 'verify').status_code, 409)
        self.assertEqual(self.paid()['paid'], '500.00')

    def test_the_steps_run_in_order(self):
        receipt = self.make().json()['id']
        self.assertEqual(self.step(receipt, 'verify').status_code, 409)       # not yet checked
        self.step(receipt, 'check')
        self.assertEqual(self.step(receipt, 'check').status_code, 409)

    def test_correcting_a_checked_receipt_needs_a_new_check(self):
        receipt = self.make().json()['id']
        self.step(receipt, 'check')
        body = {'received_as': 2, 'invoice': self.invoice, 'amount': '600', 'payment_mode': 4, 'payer_name': 'SBI'}
        corrected = self.client.put(f'/api/receipts/{receipt}/', body, content_type='application/json').json()
        self.assertEqual((corrected['stage'], corrected['amount']), ('to_check', '600.00'))

    def test_creation_is_retry_safe(self):
        op = uuid.uuid4()
        self.make(operation_id=op)
        self.assertTrue(self.make(operation_id=op).json()['replayed'])
        self.assertEqual(m.Receipt.objects.filter(origin='local_cash_receipt').count(), 1)
        self.assertEqual(self.make(operation_id=op, amount='999').status_code, 409)

    def test_a_receipt_is_voided_not_deleted_and_only_before_verification(self):
        first = self.make().json()['id']
        self.assertEqual(self.step(first, 'void', reason='Entered twice').json()['stage'], 'voided')
        self.assertEqual(self.step(first, 'check').status_code, 409)
        second = self.make().json()['id']
        self.step(second, 'check'); self.step(second, 'verify')
        self.assertEqual(self.step(second, 'void', reason='x').status_code, 409)
        self.assertEqual(m.Receipt.objects.filter(origin='local_cash_receipt').count(), 2)

    def test_the_maker_must_give_complete_details(self):
        self.assertEqual(self.make(invoice='').status_code, 400)               # a recovery names its invoice
        self.assertEqual(self.make(payment_mode=2).status_code, 400)           # a cheque needs number and bank
        self.assertEqual(self.make(payment_mode=2, cheque_draft_number='001234', cheque_draft_bank='SBI').status_code, 201)
        self.assertEqual(self.make(amount='0').status_code, 400)
        self.assertEqual(self.make(payer_name='').status_code, 400)
        future = (timezone.localdate() + timezone.timedelta(days=1)).isoformat()
        self.assertEqual(self.make(received_date=future).status_code, 400)

    def test_an_advance_touches_no_invoice(self):
        receipt = self.make(received_as=1, invoice='').json()['id']
        self.step(receipt, 'check'); self.step(receipt, 'verify')
        self.assertEqual(self.paid()['paid'], '0.00')

    def test_a_recovery_against_a_credited_invoice_cannot_be_verified(self):
        receipt = self.make().json()['id']
        self.step(receipt, 'check')
        self.client.post(f'/api/invoices/{self.invoice}/credit-note/', {'reason': 'Wrong party'}, content_type='application/json')
        self.assertEqual(self.step(receipt, 'verify').status_code, 409)

    def test_the_queue_follows_the_stages(self):
        receipt = self.make().json()['id']
        counts = lambda: self.client.get('/api/receipts/').json()['counts']
        self.assertEqual((counts()['to_check'], counts()['to_verify']), (1, 0))
        self.step(receipt, 'check')
        self.assertEqual((counts()['to_check'], counts()['to_verify']), (0, 1))
        self.step(receipt, 'verify')
        self.assertEqual(counts()['verified'], 1)

    def test_overpaying_an_invoice_needs_confirmation(self):
        self.pay(self.invoice, '1180')                                         # already fully paid
        receipt = self.make(amount='500').json()['id']
        self.step(receipt, 'check')
        refused = self.step(receipt, 'verify')
        self.assertEqual(refused.status_code, 409)
        self.assertIn('Rs 0.00 outstanding', refused.json()['error'])
        self.assertEqual(self.client.get(f'/api/receipts/{receipt}/').json()['stage'], 'to_verify')   # nothing marked
        self.assertEqual(self.step(receipt, 'verify', confirm_overpayment=True).status_code, 200)
        self.assertEqual(self.paid()['excess'], '500.00')
