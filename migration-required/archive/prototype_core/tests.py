import io
import json
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, Client
from core.management.commands.import_legacy import KEYS
from core.models import Bank, Office, Lead, Case, LeadNote, ImportBatch


class MigrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('reviewer', password='Local-test-password-937', is_staff=True)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'export.json'
        self.rows = {name: [] for name in KEYS}
        self.rows.update({'Banks': [{'bank_id': '001', 'name': 'Example bank'}],
                         'Client Offices': [{'client_id': '1', 'name': 'Example office', 'branch': 'Main', 'bank_id': '001'}],
                         'Contacts': [{'orderer_reg_id': '1', 'client_id': '1', 'orderer_name': 'Example contact'}],
                         'Leads': [{'lead_id': '1', 'client_id': '1', 'orderer_reg_id': '1', 'lead_no': 'L1', 'lead_status': '4', 'lead_date': '2026-04-01'}],
                         'Cases': [{'client_customer_id': '1', 'lead_id': '1', 'service_name': 'Valuation'}]})

    def run_import(self, **options):
        sheets = []
        for name, rows in self.rows.items():
            columns = list(rows[0]) if rows else [KEYS[name]]
            sheets.append({'name': name, 'columns': columns, 'rows': [[r.get(k) for k in columns] for r in rows]})
        self.path.write_text(json.dumps([{'sheets': sheets}]))
        call_command('import_legacy', self.path, stdout=io.StringIO(), **options)

    def test_repeat_refresh_preserves_ids_notes_and_omitted_rows(self):
        self.run_import()
        lead = Lead.objects.get()
        LeadNote.objects.create(lead=lead, author=self.user, body='Keep this local note')
        self.run_import()
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.get().pk, lead.pk)
        self.assertEqual(Bank.objects.get().source_id, '001')
        self.rows['Client Offices'][0]['name'] = 'Corrected office'
        self.run_import()
        self.assertEqual(Office.objects.get().name, 'Corrected office')
        self.assertEqual(LeadNote.objects.get().body, 'Keep this local note')
        self.rows['Cases'] = []
        self.run_import()
        self.assertEqual(Case.objects.count(), 1)

    def test_full_dry_run_rolls_back(self):
        self.run_import(dry_run=True)
        self.assertFalse(Bank.objects.exists())
        self.assertFalse(ImportBatch.objects.exists())

    def test_duplicate_key_rejected_before_writing(self):
        self.rows['Cases'] *= 2
        with self.assertRaises(CommandError):
            self.run_import()
        self.assertFalse(Bank.objects.exists())

    def test_orphan_is_retained_and_flagged(self):
        self.rows['Cases'][0]['lead_id'] = 'missing'
        self.run_import()
        case = Case.objects.get()
        self.assertIsNone(case.lead)
        self.assertEqual(case.raw['lead_id'], 'missing')
        self.assertTrue(case.issues)

    def test_dates_and_summary_boundaries(self):
        self.run_import()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/summary/?year=2026').json()['cases'], 1)
        self.assertEqual(self.client.get('/api/summary/?year=2025').json()['cases'], 0)
        self.assertEqual(self.client.get('/api/summary/?year=bad').status_code, 400)

    def test_login_csrf_access_and_note_validation(self):
        self.run_import()
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get('/api/leads/').status_code, 401)
        self.assertEqual(client.post('/api/login/', {}, content_type='application/json').status_code, 403)
        token = client.get('/api/session/').json()['csrf']
        response = client.post('/api/login/', {'username': 'reviewer', 'password': 'Local-test-password-937'},
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        token = response.json()['csrf']
        self.assertEqual(client.get('/api/leads/').json()['count'], 1)
        url = f'/api/leads/{Lead.objects.get().pk}/'
        self.assertEqual(client.post(url, {'body': ''}, content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(client.post(url, {'body': 'Call next week'}, content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assertEqual(client.get(url).json()['notes'][0]['body'], 'Call next week')
        outsider = get_user_model().objects.create_user('outsider', password='another-long-password')
        client.force_login(outsider)
        self.assertEqual(client.get(url).status_code, 403)
