"""Independent API workflow checks. Only Django's disposable test DB is written.

The missing-write checks describe migration gaps, not business-flow acceptance.
"""
from datetime import date
import uuid
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from target_core import models as m
from target_core.sync import source_key


def seed_flow_example():
    bank = m.Bank.objects.create(name='Audit Example Bank')
    office = m.ClientOffice.objects.create(name='Audit Example Office', bank=bank, branch_name='Sample Branch')
    contact = m.Contact.objects.create(name='Audit Contact', office=office, phone='TEST-NOT-A-PHONE')
    service = m.ServiceType.objects.create(name='Audit Valuation Service')
    subtype = m.ServiceSubtype.objects.create(name='Audit Building', service=service)
    lead = m.Lead.objects.create(number='AUDIT-LEAD-001', office=office, contact=contact,
                                 received_date=date(2026, 4, 1), legacy_status='1')
    borrower = m.Borrower.objects.create(name='Audit Borrower', lead=lead)
    case = m.Case.objects.create(lead=lead, borrower=borrower, service=service, subtype=subtype)
    batch = m.ImportBatch.objects.create(snapshot_checksum='a'*64, conversion_version='mysql-target-audit',
        source_environment='main', status='completed_with_issues', summary={
            'lead_mngt.lead': dict(source_rows=1, inserted=1, updated=0, unchanged=0, quarantined=0, rows_with_issues=0)})
    for table, instance, legacy_id, problems in [
        ('lead', lead, 1001, []), ('client', office, 1002, []),
        ('client_customer', case, 1003, ['Synthetic subtype correction for workflow audit'])]:
        key = source_key(legacy_id)
        m.SourceIdentity.objects.create(batch=batch, environment='main', schema='lead_mngt', table=table,
            key=key, target_model=instance._meta.label, target_id=instance.id)
        m.SourceRow.objects.create(schema='lead_mngt', table=table, key=key,
            payload={}, payload_hash='a'*64, batch=batch, outcome='imported', problems=problems)
    m.SourceRow.objects.create(schema='lead_mngt', table='lead', key=source_key(9999),
        payload={}, payload_hash='b'*64, batch=batch, outcome='quarantined', problems=['Synthetic missing office'])
    return lead, office, case


class FlowContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user('flow-reviewer', password='test-only-Audit-984!', is_staff=True)
        cls.member = get_user_model().objects.create_user('flow-member', password='test-only-Audit-984!')
        cls.lead, cls.office, cls.case = seed_flow_example()

    def login_csrf(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/session/').json()['csrf']
        response = client.post('/api/login/', {'username':'flow-reviewer','password':'test-only-Audit-984!'},
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        return client, response.json()['csrf']

    def test_session_login_note_reload_logout_with_csrf(self):
        client, token = self.login_csrf()
        path = f'/api/leads/{self.lead.id}/'
        self.assertEqual(client.get(path).status_code, 200)
        response = client.post(path, {'body':'Audit note'}, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(client.get(path).json()['notes'][0]['body'], 'Audit note')
        self.assertEqual(client.post('/api/logout/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get(path).status_code, 401)

    def test_unauthenticated_and_nonstaff_access_denied(self):
        for path in ['/api/leads/', '/api/offices/', '/api/summary/', f'/api/leads/{self.lead.id}/']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get('/api/leads/').status_code, 403)

    def test_csrf_required_for_login_and_note(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/login/', {}, content_type='application/json').status_code, 403)
        client, _ = self.login_csrf()
        self.assertEqual(client.post(f'/api/leads/{self.lead.id}/', {'body':'No token'},
                                    content_type='application/json').status_code, 403)
        self.assertFalse(m.LeadNote.objects.exists())

    def test_notes_validate_blank_length_and_keep_business_fields(self):
        self.client.force_login(self.staff)
        path = f'/api/leads/{self.lead.id}/'
        for body in ['', '  ', 'x'*4001, 12]:
            self.assertEqual(self.client.post(path, {'body':body}, content_type='application/json').status_code, 400)
        self.assertFalse(m.LeadNote.objects.exists())
        response = self.client.post(path, {'body':'Allowed note', 'legacy_status':'4'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.legacy_status, '1')

    def test_search_by_number_legacy_id_office_and_status(self):
        self.client.force_login(self.staff)
        for q in ['AUDIT-LEAD', '1001', 'Audit Example Office']:
            self.assertEqual(self.client.get('/api/leads/', {'q':q}).json()['count'], 1)
        self.assertEqual(self.client.get('/api/leads/', {'status':'4'}).json()['count'], 0)
        self.assertEqual(self.client.get('/api/offices/', {'q':'1002'}).json()['count'], 1)
        self.assertEqual(self.client.get('/api/offices/', {'q':'Sample Branch'}).json()['count'], 1)

    def test_pagination_and_invalid_page(self):
        self.client.force_login(self.staff)
        m.Lead.objects.bulk_create([m.Lead(office=self.office, number=f'AUDIT-{n:03}') for n in range(34)])
        first = self.client.get('/api/leads/').json()
        second = self.client.get('/api/leads/', {'page':2}).json()
        self.assertEqual((first['count'], len(first['results']), len(second['results'])), (35,30,5))
        self.assertFalse({r['id'] for r in first['results']} & {r['id'] for r in second['results']})
        self.assertEqual(self.client.get('/api/leads/', {'page':'bad'}).status_code, 400)

    def test_case_warning_contact_and_source_identity_visible(self):
        self.client.force_login(self.staff)
        detail = self.client.get(f'/api/leads/{self.lead.id}/').json()
        self.assertEqual(detail['source_id'], '1001')
        self.assertEqual(detail['contact']['name'], 'Audit Contact')
        self.assertEqual(detail['cases'][0]['source_id'], '1003')
        self.assertIn('Synthetic subtype correction', detail['cases'][0]['issues'][0])

    def test_summary_reconciliation_and_financial_year_boundary(self):
        self.client.force_login(self.staff)
        summary = self.client.get('/api/summary/').json()
        self.assertEqual((summary['source_rows'], summary['quarantined_source_rows'], summary['rows_with_issues']), (4,1,1))
        self.assertEqual(self.client.get('/api/summary/', {'year':2026}).json()['cases'], 1)
        self.assertEqual(self.client.get('/api/summary/', {'year':2025}).json()['cases'], 0)
        self.assertEqual(self.client.get('/api/summary/', {'year':'invalid'}).status_code, 400)

    def test_unknown_lead_and_invalid_login(self):
        self.assertEqual(self.client.post('/api/login/', {'username':'flow-reviewer','password':'wrong'},
                                         content_type='application/json').status_code, 401)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/api/leads/{uuid.uuid4()}/').status_code, 404)

    def test_characterize_missing_business_write_flows(self):
        # Passing means these gaps are reproduced, NOT that the flows work.
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post('/api/leads/', {}, content_type='application/json').status_code, 405)
        self.assertEqual(self.client.post('/api/offices/', {}, content_type='application/json').status_code, 405)
        self.assertEqual(self.client.patch(f'/api/leads/{self.lead.id}/', {}, content_type='application/json').status_code, 405)
        # Work orders, the valuation form, invoicing, receipts and dispatch are implemented.
        for path in ['/api/reports/']:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(m.Lead.objects.count(), 1)
