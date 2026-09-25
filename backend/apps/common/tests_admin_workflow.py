"""Review finding G6: the admin must not bypass workflow rules."""
from django.contrib.auth.models import User
from django.test import TestCase

from target_core import models as m


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser('root', 'r@x.test', 'x'))

    def test_codex_reproduction_a_lead_cannot_be_added_through_admin(self):
        office = m.ClientOffice.objects.create(name='SBI Main')
        response = self.client.post('/admin/target_core/lead/add/', {'office': office.pk, 'number': ''})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(m.Lead.objects.exists())

    def test_an_invoice_cannot_be_edited_through_admin(self):
        invoice = m.Invoice.objects.create(origin='local_invoice', number='I-0926250001')
        response = self.client.post(f'/admin/target_core/invoice/{invoice.pk}/change/', {'number': 'I-TAMPERED'})
        self.assertEqual(response.status_code, 403)
        invoice.refresh_from_db()
        self.assertEqual(invoice.number, 'I-0926250001')

    def test_workflow_records_remain_browsable(self):
        self.assertEqual(self.client.get('/admin/target_core/lead/').status_code, 200)
        self.assertEqual(self.client.get('/admin/target_core/invoice/').status_code, 200)

    def test_reference_data_stays_editable(self):
        bank = m.Bank.objects.create(name='State Bank of India')
        page = self.client.get(f'/admin/target_core/bank/{bank.pk}/change/')
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'name="_save"')
