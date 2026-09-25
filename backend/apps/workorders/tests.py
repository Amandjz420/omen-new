"""Work-order generation: numbering, the letter, closure and failure paths."""
import datetime
import shutil
import tempfile
import uuid
from unittest import mock

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from target_core import models as m
from target_core import workorders
from target_core.numbering import allocate, format_number

MEDIA = tempfile.mkdtemp(prefix='omen-test-media-')


@override_settings(MEDIA_ROOT=MEDIA)
class WorkOrderTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(self.user)
        office = m.ClientOffice.objects.create(name='SBI Main')
        self.contact = m.Contact.objects.create(name='R. Sharma', office=office, phone='9000000001')
        self.lead = m.Lead.objects.create(office=office, contact=self.contact, date_basis='actual_intake',
                                          legacy_status='2', legacy_deleted='0', number='L-0926240001',
                                          received_date=datetime.date(2026, 9, 20))
        self.service = m.ServiceType.objects.create(name='Valuation of asset')

    def borrower(self, name='Asha Verma', cases=1, **extra):
        b = m.Borrower.objects.create(lead=self.lead, name=name, legacy_deleted='0', **extra)
        for _ in range(cases):
            m.Case.objects.create(lead=self.lead, borrower=b, service=self.service, asset_address='Plot 4')
        return b

    def issue(self, borrower, key=None):
        return self.client.post('/api/work-orders/', {'request_id': str(key or uuid.uuid4()),
                                                      'borrower': str(borrower.pk)},
                                content_type='application/json')

    # --- numbering -------------------------------------------------------
    def test_number_continues_above_the_imported_maximum(self):
        m.WorkOrder.objects.create(lead=self.lead, borrower=self.borrower('Old'), number='O-09261012289')
        response = self.issue(self.borrower())
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['number'].endswith('12290'))
        self.assertRegex(response.json()['number'], r'^O-\d{6}12290$')

    def test_numbers_are_sequential_and_unique(self):
        a, b = self.borrower('A'), self.borrower('B')
        n1 = self.issue(a).json()['number']
        n2 = self.issue(b).json()['number']
        self.assertEqual(int(n2[8:]), int(n1[8:]) + 1)

    def test_format_matches_the_legacy_shape(self):
        self.assertEqual(format_number('O', datetime.date(2026, 9, 10), 12289), 'O-09261012289')
        self.assertEqual(format_number('O', datetime.date(2026, 1, 5), 7), 'O-0126050007')

    def test_allocation_outside_a_transaction_is_refused(self):
        outside = mock.Mock(in_atomic_block=False)
        with mock.patch('target_core.numbering.transaction.get_connection', return_value=outside):
            with self.assertRaises(RuntimeError):
                allocate('work_order', m.WorkOrder, 'number', 'O')

    # --- the letter ------------------------------------------------------
    def test_the_letter_is_generated_stored_and_retrievable(self):
        response = self.issue(self.borrower(payer=2, fee_basis=1, customer_payment_method=1))
        order = m.WorkOrder.objects.get(pk=response.json()['id'])
        self.assertEqual(order.document.media_type, 'application/pdf')
        pdf = self.client.get(f'/api/work-orders/{order.pk}/document/')
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF'))

    def test_the_letter_decodes_payment_responsibility(self):
        b = self.borrower(payer=2, fee_basis=1, customer_payment_method=3)
        self.assertEqual((b.get_payer_display(), b.get_fee_basis_display(), b.get_customer_payment_method_display()),
                         ('By Client Customer', 'By Circular', 'By Any Other'))

    def test_markup_in_free_text_cannot_break_the_letter(self):
        response = self.issue(self.borrower(name='<b>Malicious & "quoted"</b>'))
        self.assertEqual(response.status_code, 201)

    def test_a_render_failure_saves_nothing(self):
        b = self.borrower()
        with mock.patch.object(workorders, 'render', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.issue(b)
        self.assertFalse(m.WorkOrder.objects.exists())
        self.assertFalse(m.Document.objects.exists())
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.legacy_status, '2')

    # --- closure ---------------------------------------------------------
    def test_lead_stays_open_until_every_borrower_has_a_work_order(self):
        first, second = self.borrower('A'), self.borrower('B')
        self.assertFalse(self.issue(first).json()['lead_closed'])
        self.lead.refresh_from_db(); self.assertEqual(self.lead.legacy_status, '2')
        self.assertTrue(self.issue(second).json()['lead_closed'])
        self.lead.refresh_from_db(); self.assertEqual(self.lead.legacy_status, '4')

    def test_legacy_behaviour_closes_on_the_first_order_when_switched(self):
        first, _ = self.borrower('A'), self.borrower('B')
        with mock.patch.object(workorders, 'CLOSE_WHEN_EVERY_BORROWER_ORDERED', False):
            self.assertTrue(self.issue(first).json()['lead_closed'])

    def test_a_deleted_borrower_does_not_hold_closure_open(self):
        live = self.borrower('Live')
        m.Borrower.objects.create(lead=self.lead, name='Gone', legacy_deleted='1')
        self.assertTrue(self.issue(live).json()['lead_closed'])

    def test_closing_an_imported_lead_protects_it_from_reimport(self):
        self.issue(self.borrower())
        self.assertTrue(m.LocalRecord.objects.filter(target_model='target_core.Lead',
                                                     target_id=self.lead.pk).exists())
        self.assertTrue(m.IntakeAudit.objects.filter(action='close_on_work_order').exists())

    def test_a_half_ordered_closed_lead_can_complete_its_remaining_borrowers(self):
        done, pending = self.borrower('Done'), self.borrower('Pending')
        m.WorkOrder.objects.create(lead=self.lead, borrower=done, number='O-09261012289')
        m.Lead.objects.filter(pk=self.lead.pk).update(legacy_status='4')
        self.assertEqual(self.issue(pending).status_code, 201)

    # --- refusals --------------------------------------------------------
    def test_a_second_order_for_the_same_borrower_is_refused(self):
        b = self.borrower()
        self.assertEqual(self.issue(b).status_code, 201)
        response = self.issue(b)
        self.assertEqual(response.status_code, 409)
        self.assertIn('already has a work order', response.json()['error'])

    def test_a_borrower_with_no_case_is_refused(self):
        response = self.issue(self.borrower(cases=0))
        self.assertEqual(response.status_code, 409)
        self.assertIn('asset case', response.json()['error'])

    def test_a_cancelled_lead_is_refused(self):
        b = self.borrower()
        m.Lead.objects.filter(pk=self.lead.pk).update(legacy_status='3')
        self.assertIn('cancelled', self.issue(b).json()['error'])

    def test_a_deleted_borrower_is_refused(self):
        b = self.borrower()
        m.Borrower.objects.filter(pk=b.pk).update(legacy_deleted='1')
        self.assertEqual(self.issue(b).status_code, 409)

    def test_the_database_refuses_two_new_orders_for_one_borrower(self):
        b = self.borrower()
        m.WorkOrder.objects.create(lead=self.lead, borrower=b, number='O-1', local_sequence=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            m.WorkOrder.objects.create(lead=self.lead, borrower=b, number='O-2', local_sequence=2)

    # --- retries ---------------------------------------------------------
    def test_a_retried_request_returns_the_original_order(self):
        b, key = self.borrower(), uuid.uuid4()
        first = self.issue(b, key)
        again = self.issue(b, key)
        self.assertEqual(again.status_code, 200)
        self.assertTrue(again.json()['replayed'])
        self.assertEqual(again.json()['id'], first.json()['id'])
        self.assertEqual(m.WorkOrder.objects.count(), 1)

    def test_a_reused_request_id_with_different_data_is_refused(self):
        key = uuid.uuid4()
        self.issue(self.borrower('A'), key)
        self.assertEqual(self.issue(self.borrower('B'), key).status_code, 409)

    # --- visibility and access -------------------------------------------
    def test_the_lead_view_reports_outstanding_borrowers(self):
        done, pending, empty = self.borrower('Done'), self.borrower('Pending'), self.borrower('Empty', cases=0)
        self.issue(done)
        state = self.client.get(f'/api/work-orders/leads/{self.lead.pk}/').json()
        by_name = {b['name']: b for b in state['borrowers']}
        self.assertEqual((state['ordered'], state['outstanding']), (1, 2))
        self.assertTrue(by_name['Pending']['eligible'])
        self.assertFalse(by_name['Empty']['eligible'])
        self.assertTrue(by_name['Empty']['reasons'])

    def test_an_imported_letter_reports_that_it_is_not_yet_retrieved(self):
        doc = m.Document.objects.create(storage_provider='legacy_lead_s3', storage_key='x.pdf')
        order = m.WorkOrder.objects.create(lead=self.lead, borrower=self.borrower(), number='O-1', document=doc)
        response = self.client.get(f'/api/work-orders/{order.pk}/document/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('legacy storage', response.json()['error'])

    def test_signed_out_users_are_refused(self):
        self.client.logout()
        self.assertEqual(self.issue(self.borrower()).status_code, 401)

    def test_an_account_still_onboarding_is_refused(self):
        m.LegacyAccount.objects.create(name='x', login_id='staff', user=self.user, must_change_password=True)
        self.assertEqual(self.issue(self.borrower()).status_code, 403)


@override_settings(MEDIA_ROOT=MEDIA)
class WorkOrderLetterContentTests(TestCase):
    """Assert what the letter says, not only that a PDF was produced."""

    def test_the_letter_carries_every_section_with_real_values(self):
        import io
        from pypdf import PdfReader
        from target_core.workorder_pdf import render
        office = m.ClientOffice.objects.create(name='SBI Main')
        contact = m.Contact.objects.create(name='Mr. Abhinav Saxena', office=office, phone='8458997942')
        lead = m.Lead.objects.create(office=office, contact=contact, date_basis='actual_intake',
                                     received_date=datetime.date(2021, 8, 18))
        service = m.ServiceType.objects.create(name='Valuation of asset')
        b = m.Borrower.objects.create(lead=lead, name='M/s Fairy Land Hotel & Resorts', contact_number='8120800003',
                                      property_count=2, payer=1, fee_basis=1, customer_payment_method=1)
        m.Case.objects.create(lead=lead, borrower=b, service=service, asset_state='Madhya Pradesh',
                              asset_district='Bhopal', asset_pin_code='462016', asset_address='Kolar main road')
        text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(
            render(m.WorkOrder(lead=lead, borrower=b, number='O-0926240001')))).pages)
        for expected in ['Work Order', 'O-0926240001', '18-08-2021', 'Omen Assessors', 'Bhopal (M.P.) 462016',
                         'cited above', 'Mr. Abhinav Saxena', '8458997942', 'M/s Fairy Land Hotel & Resorts',
                         'By Client', 'By Circular', 'By Bank', 'Valuation of', 'Madhya Pradesh', '462016']:
            self.assertIn(expected, text)
        # The two legacy misspellings are corrected.
        self.assertNotIn('refernece', text)
        self.assertNotIn('citied', text)


@override_settings(MEDIA_ROOT=MEDIA)
class LeadLifecycleTests(TestCase):
    """Intake and work orders together, driven only through the public API."""

    def setUp(self):
        self.user = User.objects.create_user('operator', password='x', is_staff=True)
        self.client.force_login(self.user)
        self.service = m.ServiceType.objects.create(name='Valuation of asset')
        self.subtype = m.ServiceSubtype.objects.create(name='L & B', service=self.service)

    def post(self, path, data, expect=201):
        response = self.client.post(f'/api/{path}', data, content_type='application/json')
        self.assertEqual(response.status_code, expect, response.content)
        return response.json()

    def test_a_lead_runs_from_intake_to_closure_through_the_api(self):
        office = self.post('intake/offices/', {'name': 'SBI Main Branch', 'branch_name': 'Main', 'address': 'MP Nagar'})
        contact = self.post('intake/contacts/', {'name': 'R. Sharma', 'office': office['id'], 'phone': '9000000001'})
        lead = self.post('intake/leads/', {
            'request_id': str(uuid.uuid4()), 'office': office['id'], 'contact': contact['id'],
            'received_date': '2026-09-24',
            'services': [{'service': str(self.service.pk), 'subtype': str(self.subtype.pk)}],
            'borrowers': [{'name': 'Asha Verma'}, {'name': 'Ravi Verma'}]})
        detail = self.client.get(f"/api/intake/leads/{lead['id']}/").json()
        self.assertEqual(detail['legacy_status'], '2')          # services recorded -> In process
        borrowers = {b['name']: b['id'] for b in detail['borrowers']}

        # Nothing can be ordered until each borrower has a case.
        state = self.client.get(f"/api/work-orders/leads/{lead['id']}/").json()
        self.assertTrue(all(not b['eligible'] for b in state['borrowers']))

        for name in borrowers:
            self.post(f"intake/leads/{lead['id']}/cases/", {
                'borrower': borrowers[name], 'service': str(self.service.pk), 'subtype': str(self.subtype.pk),
                'asset_address': f'Plot for {name}', 'asset_district': 'Bhopal', 'asset_state': 'Madhya Pradesh'})

        first = self.post('work-orders/', {'request_id': str(uuid.uuid4()), 'borrower': borrowers['Asha Verma']})
        self.assertFalse(first['lead_closed'])
        # Intake locks as soon as any work order exists.
        self.assertFalse(self.client.get(f"/api/intake/leads/{lead['id']}/").json()['editable'])

        second = self.post('work-orders/', {'request_id': str(uuid.uuid4()), 'borrower': borrowers['Ravi Verma']})
        self.assertTrue(second['lead_closed'])
        self.assertEqual(self.client.get(f"/api/intake/leads/{lead['id']}/").json()['legacy_status'], '4')

        # Both letters are retrievable and the numbers are consecutive.
        for order in (first, second):
            pdf = self.client.get(f"/api/work-orders/{order['id']}/document/")
            self.assertEqual(pdf.status_code, 200)
        self.assertEqual(int(second['number'][8:]), int(first['number'][8:]) + 1)
        # The audit trail records the orders and the closure.
        actions = set(m.IntakeAudit.objects.values_list('action', flat=True))
        self.assertIn('close_on_work_order', actions)
