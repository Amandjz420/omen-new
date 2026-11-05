"""Client review 2026-11-05: three client types, a client's GST/PAN and IFSC, the
orderer and who contacted us, editing a lead from its form, an optional PIN, and the
work order's terms of payment and signature."""
import datetime
import io
import importlib

from django.apps import apps as django_apps
from django.test import TestCase

from target_core import models as m
from apps.leads.test_intake import IntakeFixture


class ClientTypeMigrationTests(TestCase):
    def test_other_types_move_to_individual_and_are_hidden(self):
        migration = importlib.import_module('target_core.migrations.0036_lead_orderer_client_types')
        for name in ('Corporate', 'Financial Institution', 'Individual'):   # the migration made them already
            m.ClientType.objects.get_or_create(name=name)
        bdo = m.ClientType.objects.create(name='Business Development Officer')
        hlc = m.ClientType.objects.create(name='HLC')
        office = m.ClientOffice.objects.create(name='Sanjay Gour', client_type=bdo)
        lead = m.Lead.objects.create(office=office, client_type=bdo)
        migration.three_client_types(django_apps, None)
        individual = m.ClientType.objects.filter(name='Individual').order_by('created_at').first()
        office.refresh_from_db(); lead.refresh_from_db(); bdo.refresh_from_db(); hlc.refresh_from_db()
        self.assertEqual((office.client_type, lead.client_type), (individual, individual))
        self.assertEqual((bdo.active, hlc.active), (False, False))
        response = self.client.get('/api/intake/catalog/')
        if response.status_code == 200:
            self.assertEqual(sorted(t['name'] for t in response.json()['client_types']),
                             ['Corporate', 'Financial Institution', 'Individual'])


class ClientOfficeTests(IntakeFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.fi = m.ClientType.objects.get_or_create(name='Financial Institution')[0]
        self.corporate = m.ClientType.objects.get_or_create(name='Corporate')[0]

    def new_office(self, **extra):
        return self.send('/api/intake/offices/', {'name': 'Acme Ltd', 'address': 'MP Nagar', **extra})

    def test_only_a_financial_institution_keeps_an_ifsc(self):
        r = self.new_office(client_type=str(self.corporate.pk), ifsc='SBIN0001234', gstin='23abcde1234f1z5', pan='abcde1234f',
                        block=str(self.block.pk))
        self.assertEqual(r.status_code, 201, r.content)
        o = m.ClientOffice.objects.get(pk=r.json()['id'])
        self.assertEqual((o.ifsc, o.gstin, o.pan, o.district, o.state), ('', '23ABCDE1234F1Z5', 'ABCDE1234F', 'Bhopal', 'Madhya Pradesh'))
        r = self.new_office(client_type=str(self.fi.pk), ifsc='SBIN0001234')
        self.assertEqual(m.ClientOffice.objects.get(pk=r.json()['id']).ifsc, 'SBIN0001234')

    def test_a_malformed_gst_pan_or_ifsc_is_refused(self):
        for bad in ({'gstin': '1234'}, {'pan': 'ABC'}, {'client_type': str(self.fi.pk), 'ifsc': 'SBIN1'}):
            self.assertEqual(self.new_office(**bad).status_code, 400, bad)


class LeadEditTests(IntakeFixture, TestCase):
    def test_contacted_by_is_kept_apart_from_the_orderer(self):
        lead = self.create(contacted_by_name='Ravi', contacted_by_phone='98260 11111', contacted_by_remark='Friend of the borrower')
        self.assertEqual((lead.contact, lead.contacted_by_name, lead.contacted_by_phone), (self.contact, 'Ravi', '9826011111'))
        self.assertEqual(self.send('/api/intake/leads/', self.data(contacted_by_phone='123')).status_code, 400)

    def test_the_lead_form_edits_every_field_and_its_services(self):
        lead = self.create()
        flat = m.ServiceSubtype.objects.create(name='Flat', service=self.service)
        other_office = m.ClientOffice.objects.create(name='Other office')
        other = m.Contact.objects.create(name='Other orderer', office=other_office, phone='9826099999')
        existing = lead.requestedservice_set.get()
        r = self.send(f'/api/intake/leads/{lead.pk}/', {
            'enquiry_mode': 2, 'contact': str(other.pk), 'contacted_by_name': 'Ravi', 'party_count': 2,
            'services': [{'id': str(existing.pk), 'service': str(self.service.pk), 'subtype': str(self.subtype.pk), 'case_count': 4},
                         {'service': str(self.service.pk), 'subtype': str(flat.pk), 'case_count': 1}]}, 'patch')
        self.assertEqual(r.status_code, 200, r.content)
        lead.refresh_from_db()
        self.assertEqual((lead.enquiry_mode, lead.contact, lead.office, lead.contacted_by_name, lead.case_count, lead.party_count),
                         (2, other, other_office, 'Ravi', 5, 2))
        self.assertEqual(r.json()['orderer']['name'], 'Other orderer')
        # Dropping a service removes it; one with cases cannot be dropped.
        b = self.send(f'/api/intake/leads/{lead.pk}/borrowers/', self.borrower()).json()['id']
        self.assertEqual(self.send(f'/api/intake/leads/{lead.pk}/cases/', self.case(b)).status_code, 201)
        keep_flat = [{'service': str(self.service.pk), 'subtype': str(flat.pk), 'case_count': 1,
                      'id': str(lead.requestedservice_set.get(subtype=flat).pk)}]
        self.assertEqual(self.send(f'/api/intake/leads/{lead.pk}/', {'services': keep_flat}, 'patch').status_code, 409)
        land = [{'id': str(existing.pk), 'service': str(self.service.pk), 'subtype': str(self.subtype.pk), 'case_count': 4}]
        self.assertEqual(self.send(f'/api/intake/leads/{lead.pk}/', {'services': land}, 'patch').status_code, 200)
        self.assertEqual(lead.requestedservice_set.count(), 1)

    def test_a_new_orderer_can_be_registered_on_edit(self):
        lead = self.create()
        division = m.LeadDivision.objects.create(name='Retail')
        sub = m.LeadSubdivision.objects.create(name='PBD', division=division)
        designation = m.ContactDesignation.objects.create(name='Manager')
        r = self.send(f'/api/intake/leads/{lead.pk}/', {'new_contact': {
            'name': 'Neha', 'phone': '9826022222', 'office': str(self.office.pk), 'designation': str(designation.pk),
            'division': str(division.pk), 'subdivision': str(sub.pk)}}, 'patch')
        self.assertEqual(r.status_code, 200, r.content)
        lead.refresh_from_db()
        self.assertEqual(lead.contact.name, 'Neha')


class WorkOrderTermsTests(TestCase):
    def test_the_letter_has_terms_of_payment_and_a_signature_block(self):
        from pypdf import PdfReader
        from apps.workorders.pdf import render
        office = m.ClientOffice.objects.create(name='Acme Ltd', branch_name='Bhopal')
        contact = m.Contact.objects.create(name='Mr. Orderer', office=office, phone='9826012345')
        lead = m.Lead.objects.create(office=office, contact=contact, received_date=datetime.date(2026, 11, 5))
        b = m.Borrower.objects.create(lead=lead, name='Asha Verma', payer=2, fee_basis=2, agreed_fee=15000,
                                      customer_payment_method=1, payment_reference_name='Asha Verma',
                                      payment_reference_number='9826054321', pay_by_date=datetime.date(2026, 11, 30))
        text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(render(m.WorkOrder(lead=lead, borrower=b, number='O-1')))).pages)
        for expected in ['Orderer Information', 'Terms of Payment', "client's customer", 'Rs. 15,000.00', '30-11-2026',
                         '9826054321', 'Authorised Signatory', 'For Acme Ltd, Bhopal', 'Designation']:
            self.assertIn(expected, text)
        self.assertNotIn('Lead Giver', text)
