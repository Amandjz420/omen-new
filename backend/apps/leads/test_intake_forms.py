"""The intake forms as the legacy forms were (design/add_lead, add_feedback, add_client,
add_case), with their auto-fill."""
import json
import uuid
from datetime import date

from django.test import TestCase

from target_core import models as m
from apps.leads.test_intake import IntakeFixture


class LeadFormTests(IntakeFixture, TestCase):
    def test_a_lead_needs_its_mode_who_received_it_and_a_service(self):
        for missing in ('enquiry_mode', 'received_by', 'assigned_employee'):
            self.assertEqual(self.send('/api/intake/leads/', self.data(**{missing: None})).status_code, 400, missing)
        self.assertEqual(self.send('/api/intake/leads/', self.data(services=[])).status_code, 400)
        self.assertEqual(self.send('/api/intake/leads/', self.data(enquiry_mode=9)).status_code, 400)

    def test_the_client_type_and_total_cases_fill_in(self):
        self.office.client_type = m.ClientType.objects.create(name='Financial Institution'); self.office.save()
        flat = m.ServiceSubtype.objects.create(name='Flat', service=self.service)
        body = self.data(services=[{'service': str(self.service.pk), 'subtype': str(self.subtype.pk), 'case_count': 2},
                                   {'service': str(self.service.pk), 'subtype': str(flat.pk), 'case_count': 3}])
        del body['received_date']                                       # the live legacy form had no date field
        r = self.send('/api/intake/leads/', body)
        self.assertEqual(r.status_code, 201, r.content)
        lead = m.Lead.objects.get(pk=r.json()['id'])
        self.assertEqual((lead.office, lead.client_type.name, lead.case_count), (self.office, 'Financial Institution', 5))
        self.assertEqual(lead.legacy_status, '2')                     # in process once its services are saved, as before
        self.assertEqual(lead.received_date, date.today())              # the legacy form dated a lead today

    def test_a_new_lead_giver_is_registered_with_the_lead(self):
        division = m.LeadDivision.objects.create(name='Retail / PB')
        sub = m.LeadSubdivision.objects.create(name='PBD', division=division)
        designation = m.ContactDesignation.objects.create(name='Field Officer')
        new = {'name': 'Poonam Salve', 'phone': '98260 77777', 'office': str(self.office.pk), 'designation': str(designation.pk),
               'division': str(division.pk), 'subdivision': str(sub.pk)}
        lead = self.create(contact=None, new_contact=new)
        self.assertEqual((lead.contact.name, lead.contact.phone, lead.contact.subdivision), ('Poonam Salve', '9826077777', sub))
        self.assertEqual(self.send('/api/intake/leads/', self.data(contact=None, new_contact=new)).status_code, 409)   # now known
        other = m.LeadSubdivision.objects.create(name='SME', division=m.LeadDivision.objects.create(name='SME'))
        response = self.send('/api/intake/leads/', self.data(contact=None, new_contact={**new, 'phone': '9826088888', 'subdivision': str(other.pk)}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.send('/api/intake/leads/', self.data(contact=None, new_contact={**new, 'phone': '12345'})).status_code, 400)

    def test_an_alternate_number_is_kept_on_the_lead_giver(self):
        self.create(alternate_phone='9993011111')
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.alternate_phone, '9993011111')

    def test_an_imported_lead_without_a_mode_can_still_be_edited(self):
        lead = self.create()
        m.Lead.objects.filter(pk=lead.pk).update(enquiry_mode=None, received_by=None)
        response = self.send(f'/api/intake/leads/{lead.pk}/', {'assigned_employee': str(self.employee.pk)}, 'patch')
        self.assertEqual(response.status_code, 200, response.content)


class BorrowerFormTests(IntakeFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.lead = self.create()
        self.base = f'/api/intake/leads/{self.lead.pk}/borrowers/'

    def test_the_legacy_required_fields(self):
        for missing in ('contact_number', 'property_count', 'payer', 'fee_basis', 'payment_reference_name',
                        'payment_reference_number', 'pay_by_date', 'customer_payment_method'):
            self.assertEqual(self.send(self.base, self.borrower(**{missing: None})).status_code, 400, missing)
        self.assertEqual(self.send(self.base, self.borrower(contact_number='12345')).status_code, 400)

    def test_paid_by_the_client_fills_in_the_payer(self):
        self.office.branch_name = 'Main Branch'; self.office.save()
        b = m.Borrower.objects.get(pk=self.send(self.base, self.borrower(payer=1)).json()['id'])
        self.assertEqual((b.payer_name, b.payer_mobile), ('Test bank office, Main Branch', '9826012345'))
        b = m.Borrower.objects.get(pk=self.send(self.base, self.borrower(name='Second', payer=2)).json()['id'])
        self.assertEqual((b.payer_name, b.payer_mobile), ('', ''))

    def test_a_fixed_fee_needs_the_amount_and_a_circular_takes_none(self):
        self.assertEqual(self.send(self.base, self.borrower(fee_basis=2)).status_code, 400)
        fixed = m.Borrower.objects.get(pk=self.send(self.base, self.borrower(fee_basis=2, agreed_fee='5000')).json()['id'])
        circular = m.Borrower.objects.get(pk=self.send(self.base, self.borrower(name='Other', fee_basis=1, agreed_fee='5000')).json()['id'])
        self.assertEqual((fixed.agreed_fee, circular.agreed_fee), (5000, None))


class CaseFormTests(IntakeFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.lead = self.create()
        self.b = self.send(f'/api/intake/leads/{self.lead.pk}/borrowers/', self.borrower()).json()['id']
        self.base = f'/api/intake/leads/{self.lead.pk}/cases/'

    def coded(self, obj, table, code, schema='lead_mngt'):
        m.SourceIdentity.objects.create(batch=m.ImportBatch.objects.create(), environment='main', schema=schema, table=table,
                                        key=json.dumps([['id', code]]), target_model=obj._meta.label, target_id=obj.pk)
        return obj

    def test_stored_as_imported_cases_store_it(self):
        second = self.coded(m.ReportUsage.objects.create(name='Sale purpose', service=self.service, subtype=self.subtype), 'usage_of_reports', '70')
        map_ = self.coded(m.ScrutinyRequirement.objects.create(name='Approved map', subtype=self.subtype, report_usage=second), 'scrutiny_document', '8')
        r = self.send(self.base, self.case(self.b, report_usages=[str(self.usage.pk), str(second.pk)],
                                           scrutiny_documents=[str(self.document.pk), str(map_.pk)]))
        self.assertEqual(r.status_code, 201, r.content)
        c = m.Case.objects.get(pk=r.json()['id'])
        self.assertEqual((c.usage_of_report_code, c.scrutiny_document_code), ('148,70', '114,8'))
        self.assertEqual((c.asset_state, c.asset_district, c.asset_block_code, c.asset_pin_code), ('Madhya Pradesh', 'Bhopal', '305', '462042'))

    def test_each_choice_must_belong_to_the_one_before(self):
        flat = m.ServiceSubtype.objects.create(name='Flat', service=self.service)
        stray = m.ReportUsage.objects.create(name='Other subtype', service=self.service, subtype=flat)
        unchosen = m.ScrutinyRequirement.objects.create(name='Other usage', report_usage=m.ReportUsage.objects.create(name='U', subtype=self.subtype))
        far = m.District.objects.create(name='Indore', state=m.State.objects.create(name='Other state'))
        elsewhere = m.Block.objects.create(name='Mhow', district=far)
        for bad in ({'report_usages': [str(stray.pk)]}, {'scrutiny_documents': [str(unchosen.pk)]},
                    {'district': str(far.pk)}, {'block': str(elsewhere.pk)}, {'asset_pin_code': '46204'}):
            self.assertEqual(self.send(self.base, self.case(self.b, **bad)).status_code, 400, bad)

    def test_the_legacy_required_fields(self):
        for missing in ('report_usages', 'scrutiny_documents', 'expected_report_date', 'asset_amount', 'asset_address',
                        'state', 'district', 'block', 'asset_pin_code'):
            self.assertEqual(self.send(self.base, self.case(self.b, **{missing: None})).status_code, 400, missing)

    def test_deleted_and_uncoded_choices_are_refused(self):
        m.ReportUsage.objects.filter(pk=self.usage.pk).update(legacy_deleted='1')
        self.assertEqual(self.send(self.base, self.case(self.b)).status_code, 400)
        m.ReportUsage.objects.filter(pk=self.usage.pk).update(legacy_deleted='0')
        m.SourceIdentity.objects.filter(target_id=self.block.pk).delete()
        self.assertIn('no code', self.send(self.base, self.case(self.b)).json()['error'])


class FollowUpFormTests(IntakeFixture, TestCase):
    def test_a_follow_up_keeps_its_legacy_status_and_when_to_call_back(self):
        lead = self.create()
        base = f'/api/intake/leads/{lead.pk}/follow-ups/'
        self.assertEqual(self.send(base, self.follow_up()).status_code, 201)
        f = lead.follow_ups.get()
        self.assertEqual((f.call_status, f.logged_date_text, f.logged_time_text), ('4', '2026-10-15', '11:30'))
        for bad in ({'status': 'Contacted'}, {'notify_date': 'tomorrow'}, {'notify_time': '25:00'}, {'remark': ' '}):
            self.assertEqual(self.send(base, self.follow_up(**bad)).status_code, 400, bad)


class LookupTests(IntakeFixture, TestCase):
    def test_the_lead_giver_is_found_by_mobile_with_everything_the_form_shows(self):
        quiet = m.Contact.objects.create(name='Rarely gives leads', office=self.office, alternate_phone='9826012345')
        self.create()
        body = self.client.get('/api/intake/lookups/orderer/', {'mobile': '+91 98260 12345'}).json()
        self.assertEqual([x['name'] for x in body['matches']], ['Test contact', 'Rarely gives leads'])   # the busier one first
        self.assertEqual(body['matches'][0]['office']['name'], 'Test bank office')
        self.assertEqual(self.client.get('/api/intake/lookups/orderer/', {'mobile': '123'}).status_code, 400)
        self.assertTrue(quiet)

    def test_a_client_is_found_by_ifsc_or_filled_from_the_bank_directory(self):
        self.office.ifsc = 'SBIN0000383'; self.office.save()
        self.assertEqual(len(self.client.get('/api/intake/lookups/ifsc/', {'code': 'sbin0000383'}).json()['offices']), 1)
        bank = m.Bank.objects.create(name='Indian Bank')
        m.BankBranch.objects.create(name='JHAJJAR', bank=bank, ifsc='IDIB000J031', address='Rohtak Road', city='JHAJJAR', district='JHAJJAR', state='HARYANA')
        body = self.client.get('/api/intake/lookups/ifsc/', {'code': 'IDIB000J031'}).json()
        self.assertEqual((body['offices'], body['directory']['bank'], body['directory']['state']), ([], 'Indian Bank', 'HARYANA'))
        self.assertEqual(self.client.get('/api/intake/lookups/ifsc/', {'code': 'SBIN12'}).status_code, 400)

    def test_the_lists_leave_out_what_was_deleted_and_carry_legacy_codes(self):
        m.ReportUsage.objects.create(name='Deleted usage', subtype=self.subtype, legacy_deleted='1')
        body = self.client.get('/api/intake/lookups/').json()
        self.assertEqual([u['name'] for u in body['report_usages']], ['Loan purpose'])
        self.assertEqual((body['report_usages'][0]['code'], body['blocks'][0]['code']), ('148', '305'))
        self.assertEqual([s['code'] for s in body['follow_up_statuses']], ['1', '3', '4', '5', '6', '7'])

    def test_a_client_added_from_the_bank_directory_keeps_its_ifsc(self):
        bank = m.Bank.objects.create(name='Indian Bank')
        m.BankBranch.objects.create(name='JHAJJAR', bank=bank, ifsc='IDIB000J031', address='Rohtak Road', city='JHAJJAR', district='JHAJJAR', state='HARYANA')
        found = self.client.get('/api/intake/lookups/ifsc/', {'code': 'IDIB000J031'}).json()['directory']
        r = self.send('/api/intake/offices/', {'name': found['bank'], 'branch_name': found['branch'], 'address': found['address'],
                                               'bank': found['bank_id'], 'state': found['state'], 'district': found['district'], 'ifsc': found['ifsc']})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(self.client.get('/api/intake/lookups/ifsc/', {'code': 'IDIB000J031'}).json()['offices']), 1)

    def test_the_lead_carries_its_offices_place_for_the_case_form(self):
        self.office.state, self.office.district, self.office.block = 'Madhya Pradesh', 'Bhopal', self.block; self.office.save()
        detail = self.client.get(f'/api/intake/leads/{self.create().pk}/').json()['office_detail']
        self.assertEqual((detail['state'], detail['district'], detail['city']), ('Madhya Pradesh', 'Bhopal', 'Huzur'))
