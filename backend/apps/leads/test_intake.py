import json
import uuid
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from target_core import models as m
from target_core.sync import synchronize
from apps.migration_pipeline.tests import FakeSource, dataset


class IntakeFixture:
    """Everything a complete legacy intake needs; holds no tests."""
    def setUp(self):
        self.user = get_user_model().objects.create_user('intake-admin',password='Only-for-tests-984!',is_staff=True)
        self.client.force_login(self.user)
        self.office = m.ClientOffice.objects.create(name='Test bank office')
        self.contact = m.Contact.objects.create(name='Test contact',office=self.office)
        self.employee = m.Employee.objects.create(name='Test assessor')
        self.service = m.ServiceType.objects.create(name='Valuation')
        self.subtype = m.ServiceSubtype.objects.create(name='Land',service=self.service)
        self.usage = m.ReportUsage.objects.create(name='Loan purpose',service=self.service,subtype=self.subtype)
        self.document = m.ScrutinyRequirement.objects.create(name='Sale deed',service=self.service,subtype=self.subtype,report_usage=self.usage)
        self.state = m.State.objects.create(name='Madhya Pradesh')
        self.district = m.District.objects.create(name='Bhopal',state=self.state)
        self.block = m.Block.objects.create(name='Huzur',district=self.district)
        self.contact.phone = '9826012345'; self.contact.save()
        batch = m.ImportBatch.objects.create()
        for schema, table, obj, code in (('lead_mngt', 'usage_of_reports', self.usage, '148'), ('lead_mngt', 'scrutiny_document', self.document, '114'),
                                         ('uam_user', 'block', self.block, '305')):
            m.SourceIdentity.objects.create(batch=batch, environment='main', schema=schema, table=table, key=json.dumps([['id', code]]),
                                            target_model=obj._meta.label, target_id=obj.pk)

    def send(self, path, data, method='post'):
        return getattr(self.client,method)(path,json.dumps(data,default=str),content_type='application/json')

    def data(self, **extra):
        return {'request_id':str(uuid.uuid4()),'contact':str(self.contact.pk),'enquiry_mode':1,
                'received_by':str(self.employee.pk),'received_date':'2026-09-24','assigned_employee':str(self.employee.pk),
                'services':[{'service':str(self.service.pk),'subtype':str(self.subtype.pk),'case_count':1}],**extra}

    def borrower(self, **extra):
        return {'name':'Asha Verma','contact_number':'9826054321','property_count':1,'payer':1,'fee_basis':1,
                'payment_reference_name':'R. K. Sharma','payment_reference_number':'9893012345','pay_by_date':'2026-10-31',
                'customer_payment_method':1,**extra}

    def case(self, borrower, **extra):
        return {'borrower':borrower,'service':str(self.service.pk),'subtype':str(self.subtype.pk),'report_usages':[str(self.usage.pk)],
                'scrutiny_documents':[str(self.document.pk)],'expected_report_date':'2026-10-20','asset_amount':'3850000',
                'asset_address':'Plot 47, Ward 12','state':str(self.state.pk),'district':str(self.district.pk),
                'block':str(self.block.pk),'asset_pin_code':'462042',**extra}

    def follow_up(self, **extra):
        return {'status':'4','notify_date':'2026-10-15','notify_time':'11:30','remark':'Call back after site visit',**extra}

    def create(self, **extra):
        r = self.send('/api/intake/leads/',self.data(**extra))
        self.assertEqual(r.status_code,201,r.content)
        return m.Lead.objects.get(pk=r.json()['id'])



class IntakeTests(IntakeFixture, TestCase):
    def test_complete_intake_and_audit(self):
        lead = self.create()
        base=f'/api/intake/leads/{lead.pk}/'
        borrower=self.send(base+'borrowers/',self.borrower(fee_basis=2,agreed_fee='1234.50'))
        self.assertEqual(borrower.status_code,201,borrower.content)
        case=self.send(base+'cases/',self.case(borrower.json()['id']))
        self.assertEqual(case.status_code,201,case.content)
        follow=self.send(base+'follow-ups/',self.follow_up())
        self.assertEqual(follow.status_code,201,follow.content)
        detail=self.client.get(base).json()
        self.assertEqual(detail['legacy_status'],'2')
        self.assertEqual(len(detail['cases']),1)
        self.assertEqual(len(detail['follow_ups']),1)
        self.assertEqual(m.IntakeAudit.objects.filter(actor=self.user).count(),6)

    def test_number_continues_imported_global_sequence_without_year_reset(self):
        m.Lead.objects.create(office=self.office,number='L-03252012000')
        with patch('target_core.intake.timezone.localdate',return_value=date(2026,9,24)):
            lead=self.create()
        self.assertEqual(lead.number,'L-09262412001')

    def test_retry_same_payload_returns_same_lead_and_changed_payload_conflicts(self):
        data=self.data()
        first=self.send('/api/intake/leads/',data)
        second=self.send('/api/intake/leads/',data)
        self.assertEqual(first.status_code,201,first.content)
        self.assertEqual(second.status_code,200,second.content)
        self.assertEqual(first.json()['id'],second.json()['id'])
        data['received_date']='2026-09-23'
        self.assertEqual(self.send('/api/intake/leads/',data).status_code,409)
        self.assertEqual(m.Lead.objects.count(),1)

    def test_bad_nested_data_rolls_back_lead_and_sequence(self):
        other=m.ServiceType.objects.create(name='Other')
        wrong=m.ServiceSubtype.objects.create(name='Wrong',service=other)
        r=self.send('/api/intake/leads/',self.data(services=[{'service':self.service.pk,'subtype':wrong.pk}]))
        self.assertEqual(r.status_code,400,r.content)
        self.assertEqual(m.Lead.objects.count(),0)
        self.assertEqual(m.LeadCounter.objects.count(),0)
        self.assertEqual(m.IntakeAudit.objects.count(),0)

    def test_the_office_is_the_lead_givers_and_an_unknown_contact_is_refused(self):
        # As on the legacy form, the lead's client is the lead giver's: a contact from
        # another office brings that office, and an office sent alongside is ignored.
        other=m.ClientOffice.objects.create(name='Other office')
        contact=m.Contact.objects.create(name='Other contact',office=other,phone='9826011111')
        lead=self.create(contact=contact.pk,office=str(self.office.pk))
        self.assertEqual(lead.office,other)
        self.assertEqual(self.send('/api/intake/leads/',self.data(contact=uuid.uuid4())).status_code,404)

    def test_assignment_edit_cancellation_and_lock(self):
        lead=self.create();base=f'/api/intake/leads/{lead.pk}/'
        second=m.Employee.objects.create(name='Second employee')
        self.assertEqual(self.send(base,{'assigned_employee':second.pk},'patch').status_code,200)
        lead.refresh_from_db();self.assertEqual(lead.assigned_employee,second)
        self.assertEqual(self.send(base,{'cancel_reason':'No longer required'},'patch').status_code,200)
        self.assertEqual(self.send(base,{'assigned_employee':self.employee.pk},'patch').status_code,409)
        self.assertEqual(self.send(base+'services/',{'service':self.service.pk}).status_code,409)
        self.assertEqual(lead.notes.count(),1)

    def test_work_order_blocks_intake_changes(self):
        lead=self.create();b=m.Borrower.objects.create(lead=lead,name='Borrower')
        m.WorkOrder.objects.create(lead=lead,borrower=b,number='W-1')
        r=self.send(f'/api/intake/leads/{lead.pk}/',{'cancel_reason':'Not allowed'},'patch')
        self.assertEqual(r.status_code,409)

    def test_case_requires_same_lead_borrower_and_requested_service(self):
        lead=self.create();other=self.create()
        b=m.Borrower.objects.create(lead=other,name='Wrong borrower')
        base=f'/api/intake/leads/{lead.pk}/cases/'
        self.assertEqual(self.send(base,self.case(str(b.pk))).status_code,400)                 # another lead's borrower
        b.lead=lead;b.save()
        unrequested=m.ServiceSubtype.objects.create(name='Flat',service=self.service)
        self.assertEqual(self.send(base,self.case(str(b.pk),subtype=str(unrequested.pk))).status_code,400)   # not requested
        self.assertEqual(self.send(base,self.case(str(b.pk))).status_code,201)

    def test_service_duplicates_and_negative_fees_are_rejected(self):
        lead=self.create();base=f'/api/intake/leads/{lead.pk}/'
        for status in [201,409]:
            self.assertEqual(self.send(base+'services/',{'service':self.service.pk}).status_code,status)
        self.assertEqual(self.send(base+'borrowers/',self.borrower(fee_basis=2,agreed_fee='-1')).status_code,400)

    def test_client_and_contact_create_edit(self):
        r=self.send('/api/intake/offices/',{'name':'Created office','branch_name':'Branch'})
        self.assertEqual(r.status_code,201,r.content)
        office_id=r.json()['id']
        r=self.send('/api/intake/contacts/',{'name':'Created contact','office':office_id,'phone':'123'})
        self.assertEqual(r.status_code,201,r.content)
        cid=r.json()['id']
        r=self.send(f'/api/intake/contacts/{cid}/',{'phone':'456'},'patch')
        self.assertEqual(r.status_code,200,r.content)
        self.assertEqual(r.json()['phone'],'456')
        self.assertEqual(self.send(f'/api/intake/contacts/{cid}/',{'office':self.office.pk},'patch').status_code,400)

    def test_auth_onboarding_and_csrf_protect_writes(self):
        path='/api/intake/leads/'
        self.client.logout();self.assertEqual(self.send(path,self.data()).status_code,401)
        member=get_user_model().objects.create_user('ordinary')
        self.client.force_login(member);self.assertEqual(self.send(path,self.data()).status_code,403)
        self.client.force_login(self.user)
        m.LegacyAccount.objects.create(name='Pending',user=self.user,must_change_password=True)
        self.assertEqual(self.send(path,self.data()).status_code,403)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.user)
        self.assertEqual(secure.post(path,self.data(),content_type='application/json').status_code,403)

    def test_local_records_and_source_edits_survive_repeat_import(self):
        source=dataset();synchronize(FakeSource(source))
        imported=m.Lead.objects.get(number='L-1')
        imported.legacy_status='1';imported.save()
        base=f'/api/intake/leads/{imported.pk}/'
        self.assertEqual(self.send(base,{'assigned_employee':self.employee.pk,'received_date':'2026-09-24'},'patch').status_code,200)
        self.assertEqual(self.send(f'/api/intake/offices/{imported.office_id}/',{'name':'Locally edited office'},'patch').status_code,200)
        local=self.create()
        self.assertEqual(self.send(base+'follow-ups/',self.follow_up(status='3')).status_code,201)
        source[('lead_mngt','lead')][0]['lead_status']='4'
        source[('lead_mngt','client')][0]['name']='Changed in source'
        synchronize(FakeSource(source));synchronize(FakeSource(source))
        imported.refresh_from_db()
        self.assertEqual(imported.legacy_status,'1')
        self.assertEqual(imported.assigned_employee,self.employee)
        self.assertEqual(imported.office.name,'Locally edited office')
        self.assertTrue(m.Lead.objects.filter(pk=local.pk).exists())
        self.assertEqual(imported.follow_ups.count(),1)
        self.assertEqual(m.SourceRow.objects.get(table='lead').payload['lead_status'],'4')
