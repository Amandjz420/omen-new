import json
"""The bank report: the gate, template choice, values, versions and the document."""
import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from pypdf import PdfReader

from target_core import models as m
from target_core.sync import source_key
from apps.valuations.test_forms import Form

MEDIA = tempfile.mkdtemp(prefix='omen-test-media-')


@override_settings(MEDIA_ROOT=MEDIA)
class BankReportTests(Form, TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.build()
        batch = m.ImportBatch.objects.create()
        self.fi = m.ClientType.objects.create(name='Financial Institution')
        m.SourceIdentity.objects.create(batch=batch, environment='main', schema='lead_mngt', table='client_type',
                                        key=source_key('1'), target_model='target_core.ClientType', target_id=self.fi.pk)
        self.sbi = m.Bank.objects.create(name='State Bank of India')
        self.pnb = m.Bank.objects.create(name='Punjab National Bank')
        self.itarsi = m.BankBranch.objects.create(bank=self.sbi, name='Main Branch Itarsi', address='Station Road', district='Hoshangabad', state='MP')
        self.pnb_branch = m.BankBranch.objects.create(bank=self.pnb, name='PNB Bhopal')
        self.template = self.template_for(self.sbi)
        self.user = User.objects.create_user('staff', password='x', is_staff=True, first_name='Sanjeev')
        self.client.force_login(self.user)
        self.reviewer = m.Employee.objects.create(name='Reviewer', legacy_status='1')
        self.v = self.ready()

    def template_for(self, bank, client_type=None):
        template = m.ReportTemplate.objects.create(client_type=client_type or self.fi, service=self.service,
                                                   subtype=self.subtype, bank=bank, legacy_deleted='0')
        general = m.ReportHeading.objects.create(name='I - GENERAL', display_order=1, legacy_deleted='0')
        gone = m.ReportHeading.objects.create(name='RETIRED HEADING', display_order=2, legacy_deleted='1')
        m.ReportTemplateLine.objects.create(template=template, question=self.text, heading=general, sequence=1,
                                            indexing='1.', output_label='Year of construction', content_after='AD')
        m.ReportTemplateLine.objects.create(template=template, question=self.grid, heading=general, sequence=2,
                                            indexing='2.', output_label='Owners')
        m.ReportTemplateLine.objects.create(template=template, question=self.radio, heading=gone, sequence=1,
                                            output_label='Must not print')
        return template

    def ready(self, bank_client=True):
        office = m.ClientOffice.objects.create(name='SBI Itarsi', client_type=self.fi if bank_client else None,
                                               bank=self.sbi, directory_branch=self.itarsi)
        lead = m.Lead.objects.create(office=office, date_basis='actual_intake', legacy_status='4', legacy_deleted='0', number='L-1')
        borrower = m.Borrower.objects.create(lead=lead, name='M/s Bhola Warehouse', legacy_deleted='0')
        case = m.Case.objects.create(lead=lead, borrower=borrower, service=self.service, subtype=self.subtype)
        m.WorkOrder.objects.create(lead=lead, borrower=borrower, number='O-1')
        v = self.client.post(f'/api/valuations/cases/{case.pk}/', {}, content_type='application/json').json()['id']
        self.client.put(f'/api/valuations/{v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]},
            {'question': str(self.text.pk), 'value': '1999'},
            {'question': str(self.grid.pk), 'rows': [{'cells': {str(self.grid_opts[0].pk): 'Mr. Tiwari', str(self.grid_opts[1].pk): '100%'}}]}]},
            content_type='application/json')
        self.client.post(f'/api/valuations/{v}/submission/', {
            'eligible_loan_amount': '1', 'desired_loan_amount': '1', 'submitted_to': str(self.reviewer.pk),
            'dispatch_at': 1, 'dispatch_by': 1, 'report_category': 1}, content_type='application/json')
        for track in ('legal', 'technical', 'social', 'general'):
            self.client.post(f'/api/verifications/{v}/{track}/', {'remark': 'ok'}, content_type='application/json')
        return v

    def generate(self, v=None, **overrides):
        body = {'market_fair_amount': '3850000', 'realisable_value_amount': '3500000', 'distress_value_amount': '3000000',
                'our_reference': 'OA/2026/1', 'your_reference': 'SBIN0000389', 'bank': str(self.sbi.pk),
                'branch': str(self.itarsi.pk), **overrides}
        return self.client.put(f'/api/bank-reports/{v or self.v}/', body, content_type='application/json')

    def document_text(self, v=None):
        pdf = self.client.get(f'/api/bank-reports/{v or self.v}/document/')
        text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(b''.join(pdf.streaming_content))).pages)
        return ' '.join(text.split())          # a PDF wraps lines wherever the page width falls


class GateTests(BankReportTests):
    def test_all_four_verifications_are_required(self):
        m.ValuationVerification.objects.filter(valuation_id=self.v).update(social_status='UnVerified')
        response = self.generate()
        self.assertEqual(response.status_code, 409)
        self.assertIn('Social', response.json()['error'])

    def test_a_finally_approved_report_cannot_be_regenerated(self):
        m.ValuationVerification.objects.filter(valuation_id=self.v).update(final_status='Verified')
        self.assertEqual(self.generate().status_code, 409)

    def test_a_reverted_valuation_cannot_be_reported(self):
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Revert')
        self.assertEqual(self.generate().status_code, 409)


class GenerationTests(BankReportTests):
    def test_a_report_is_generated_with_its_values_in_words(self):
        body = self.generate().json()
        self.assertIsNotNone(body['report']['document'])
        r = m.BankReport.objects.get()
        self.assertEqual(r.market_fair_amount, Decimal('3850000.00'))
        self.assertEqual(r.market_fair_amount_word, 'Thirty Eight Lakh Fifty Thousand')
        self.assertEqual(r.report_number, m.Valuation.objects.get(pk=self.v).report_number)
        self.assertEqual(r.template, self.template)

    def test_the_document_says_what_a_bank_receives(self):
        self.generate()
        text = self.document_text()
        for expected in ('State Bank of India', 'Main Branch Itarsi', 'M/s Bhola Warehouse', 'I - GENERAL',
                         'Year of construction', '1999 AD', 'Mr. Tiwari', 'Rs. 38,50,000',
                         'Rupees Thirty Eight Lakh Fifty Thousand only', 'Approved Valuer', 'Branch Manager',
                         'Annexure V', 'Sales comparison approach'):
            self.assertIn(expected, text)
        self.assertNotIn('Must not print', text)        # a retired heading's lines are omitted

    def test_the_report_is_laid_out_as_the_previous_system_printed_it(self):
        """The page banks know: room for the pre-printed letterhead (no banner image),
        references at the top, the labelled addressee rows, the service as a title,
        the valuer's guidance paragraph, and "n of N" at each page's foot; on A4."""
        self.generate()
        pdf = self.client.get(f'/api/bank-reports/{self.v}/document/')
        reader = PdfReader(io.BytesIO(b''.join(pdf.streaming_content)))
        text = self.document_text()
        for expected in ('OUR REFERENCE : OA/2026/1', 'YOUR REFERENCE : SBIN0000389', 'Name & Address of Branch : To,',
                         'Name of Customer (s)/ Borrower unit : (for which valuation report is sought): M/s Bhola Warehouse',
                         'Valuation of asset- (L & B)', 'Here the approved valuer should discuss',
                         'Screen shot of longitude/latitude', f'1 of {len(reader.pages)}'):
            self.assertIn(expected, text)
        self.assertNotIn('OMEN ID', text)                          # an empty reference is left out, not printed blank
        self.assertEqual([round(x) for x in reader.pages[0].mediabox[2:]], [595, 842])    # A4, not the legacy US Letter
        self.assertFalse(any(page.images for page in reader.pages))                       # no banner: no photos were taken

    def test_zero_values_are_allowed_and_book_value_is_optional(self):
        self.assertEqual(self.generate(market_fair_amount='0').status_code, 200)
        self.assertEqual(m.BankReport.objects.get().book_value_amount, Decimal('0.00'))

    def test_a_missing_or_negative_value_is_refused(self):
        self.assertEqual(self.generate(distress_value_amount='').status_code, 400)
        self.assertEqual(self.generate(realisable_value_amount='-1').status_code, 400)

    def test_both_references_are_required(self):
        self.assertEqual(self.generate(our_reference='').status_code, 400)
        self.assertEqual(self.generate(your_reference='  ').status_code, 400)

    def test_regenerating_before_approval_updates_the_same_report(self):
        self.generate()
        self.generate(market_fair_amount='4000000')
        self.assertEqual(m.BankReport.objects.count(), 1)
        self.assertEqual(m.BankReport.objects.get().market_fair_amount_word, 'Forty Lakh')


class TemplateChoiceTests(BankReportTests):
    def test_the_template_follows_the_report_bank_not_the_office_bank(self):
        pnb = self.template_for(self.pnb)
        self.generate(bank=str(self.pnb.pk), branch=str(self.pnb_branch.pk))
        self.assertEqual(m.BankReport.objects.get().template, pnb)

    def test_a_bank_client_must_choose_bank_and_branch(self):
        self.assertEqual(self.generate(bank='').status_code, 400)
        self.assertEqual(self.generate(branch='').status_code, 400)

    def test_the_branch_must_belong_to_the_bank(self):
        self.assertEqual(self.generate(branch=str(self.pnb_branch.pk)).status_code, 400)

    def test_no_matching_template_is_refused(self):
        response = self.generate(bank=str(self.pnb.pk), branch=str(self.pnb_branch.pk))
        self.assertEqual(response.status_code, 409)
        self.assertIn('No report template', response.json()['error'])

    def test_two_matching_templates_are_refused_as_ambiguous(self):
        self.template_for(self.sbi)
        self.assertIn('Several', self.generate().json()['error'])


class VersionTests(BankReportTests):
    def test_after_a_superseded_version_the_next_carries_a_revision(self):
        self.generate()
        m.BankReport.objects.update(superseded_at=timezone.now())
        self.assertEqual(self.generate().status_code, 200)
        self.assertEqual(sorted(m.BankReport.objects.values_list('revision', flat=True)), [0, 1])
        self.assertIn('Revision 1', self.document_text())
        body = self.client.get(f'/api/bank-reports/{self.v}/').json()
        self.assertEqual([s['revision'] for s in body['superseded']], [0])


class QueueTests(BankReportTests):
    def test_the_queue_separates_pending_and_generated(self):
        counts = self.client.get('/api/bank-reports/').json()['counts']
        self.assertEqual(counts, {'pending': 1, 'generated': 0})
        self.generate()
        self.assertEqual(self.client.get('/api/bank-reports/').json()['counts'], {'pending': 0, 'generated': 1})

    def test_branches_are_searchable_within_a_bank(self):
        rows = self.client.get(f'/api/bank-reports/branches/?bank={self.sbi.pk}&q=itarsi').json()['branches']
        self.assertEqual([r['name'] for r in rows], ['Main Branch Itarsi'])


class LiableAssessorTests(BankReportTests):
    """Who a report's billing and recovery is credited to: the lead's assignee when it is
    generated (as legacy reports were, 98.7-100% from 2024), kept across revisions, and
    changeable with a reason, as the legacy Change liable FA."""

    def setUp(self):
        super().setUp()
        self.assignee = m.Employee.objects.create(name='Rahul Patidar', legacy_status='1')
        m.Lead.objects.filter(case__valuation__pk=self.v).update(assigned_employee=self.assignee)
        # Nothing chosen at submission: the lead's assignee is the fallback these test.
        m.Valuation.objects.filter(pk=self.v).update(submitted_to=None)

    def change(self, employee, reason='Branch reassigned'):
        return self.client.post(f'/api/bank-reports/{self.v}/liable/', {'employee': str(employee.pk), 'reason': reason},
                                content_type='application/json')

    def test_a_generated_report_is_credited_to_the_leads_assignee(self):
        body = self.generate().json()
        self.assertEqual(body['report']['liable'], {'id': str(self.assignee.pk), 'name': 'Rahul Patidar'})
        self.assertEqual(m.BankReport.objects.get().liable_employee, self.assignee)

    def test_the_billing_report_includes_a_report_generated_here(self):
        """Regression: reports generated here named no liable assessor, so the MIS skipped them."""
        self.generate()
        rows = self.client.get('/api/mis/billing-by-assessor/').json()
        self.assertIn('Rahul Patidar', json.dumps(rows))

    def test_a_change_needs_a_reason_and_is_kept_in_the_history(self):
        self.generate()
        other = m.Employee.objects.create(name='Vijay Galphate', legacy_status='1')
        self.assertEqual(self.change(other, reason=' ').status_code, 400)
        self.assertEqual(self.change(self.assignee).status_code, 400)                  # already liable
        r = self.change(other)
        self.assertEqual((r.status_code, r.json()['report']['liable']['name']), (200, 'Vijay Galphate'))
        event = m.ValuationEvent.objects.get(kind=m.ValuationEvent.LIABLE)
        self.assertEqual((event.from_status, event.to_status, event.reason), ('Rahul Patidar', 'Vijay Galphate', 'Branch reassigned'))

    def test_a_new_revision_keeps_a_correction(self):
        self.generate()
        other = m.Employee.objects.create(name='Vijay Galphate', legacy_status='1')
        self.change(other)
        from django.utils import timezone
        m.BankReport.objects.update(superseded_at=timezone.now())                       # a corrected revision is due
        self.generate()
        current = m.BankReport.objects.get(superseded_at__isnull=True)
        self.assertEqual((current.revision, current.liable_employee), (1, other))      # not back to the assignee

    def test_there_is_nothing_to_change_before_a_report(self):
        self.assertEqual(self.change(self.assignee).status_code, 409)


class SubmissionLiableTests(BankReportTests):
    """The submission's "Liable FA" (submitted_to): the lead's assignee unless chosen,
    and the one the bank report is credited to."""

    def setUp(self):
        super().setUp()
        self.assignee = m.Employee.objects.create(name='Rahul Patidar', legacy_status='1')
        m.Lead.objects.filter(case__valuation__pk=self.v).update(assigned_employee=self.assignee)

    def test_the_submission_offers_the_leads_assignee(self):
        m.Valuation.objects.filter(pk=self.v).update(submitted_to=None)
        body = self.client.get(f'/api/valuations/{self.v}/submission/').json()
        self.assertEqual(str(body['values']['submitted_to']), str(self.assignee.pk))

    def test_the_report_is_credited_to_the_one_chosen_at_submission(self):
        chosen = m.Employee.objects.create(name='Chosen at submission', legacy_status='1')
        m.Valuation.objects.filter(pk=self.v).update(submitted_to=chosen)
        self.assertEqual(self.generate().json()['report']['liable']['name'], 'Chosen at submission')


class ValuesRequiredTests(BankReportTests):
    """Market, realisable and distress values are required for a property valuation
    only; legacy reports of other kinds almost never gave them."""

    def without_values(self):
        return self.generate(market_fair_amount='', realisable_value_amount='', distress_value_amount='')

    def test_a_property_valuation_needs_its_values(self):
        self.service.name, self.subtype.name = 'Valuation of asset', 'L & B ( SBIN)'
        self.service.save(); self.subtype.save()
        self.assertEqual(self.without_values().status_code, 400)
        self.assertTrue(self.client.get(f'/api/bank-reports/{self.v}/').json()['values_required'])

    def test_a_certificate_or_a_plant_valuation_does_not(self):
        """Regression: values were required for every report, refusing about 28% of them."""
        self.service.name = 'Chartered Engineer Certificate'; self.service.save()
        self.assertEqual(self.without_values().status_code, 200, self.without_values().content)
        self.assertFalse(self.client.get(f'/api/bank-reports/{self.v}/').json()['values_required'])
        self.service.name, self.subtype.name = 'Valuation of asset', 'Plant & Machinery'
        self.service.save(); self.subtype.save()
        self.assertFalse(self.client.get(f'/api/bank-reports/{self.v}/').json()['values_required'])
