"""Submitting a valuation: required questions, the report number, and the fields."""
import datetime
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from target_core import models as m
from target_core import valuation_submit
from apps.valuations.test_forms import Form


class SubmissionTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.user = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(self.user)
        self.reviewer = m.Employee.objects.create(name='Udaybhan Singh', legacy_status='1')
        self.case = self.lead_with_case()
        self.v = self.client.post(f'/api/valuations/cases/{self.case.pk}/', {}, content_type='application/json').json()['id']

    def answer_required(self):
        self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]},
            {'question': str(self.text.pk), 'value': '1999'}]}, content_type='application/json')

    def submit(self, **overrides):
        body = {'eligible_loan_amount': '2500000', 'desired_loan_amount': '2000000',
                'assessor_comment': 'Clear title', 'non_cost_factor': '', 'submitted_to': str(self.reviewer.pk),
                'dispatch_at': 1, 'dispatch_by': 2, 'report_category': 1, **overrides}
        return self.client.post(f'/api/valuations/{self.v}/submission/', body, content_type='application/json')

    # --- the gate ----------------------------------------------------------
    def test_unanswered_required_questions_block_submission(self):
        response = self.submit()
        self.assertEqual(response.status_code, 409)
        self.assertIn('required question', response.json()['error'])
        missing = self.client.get(f'/api/valuations/{self.v}/submission/').json()['missing_required']
        self.assertEqual(len(missing), 2)
        self.assertEqual(m.Valuation.objects.get(pk=self.v).legacy_status, 'Pending')

    def test_an_empty_answer_does_not_satisfy_a_required_question(self):
        self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]},
            {'question': str(self.text.pk), 'value': '   '}]}, content_type='application/json')
        self.assertEqual(self.submit().status_code, 409)

    # --- the report number -------------------------------------------------
    def test_submission_assigns_a_report_number_above_the_imported_maximum(self):
        other = self.lead_with_case()
        m.Valuation.objects.create(case=other, legacy_status='Submit', report_number='R-0926100001')
        m.Valuation.objects.create(case=self.lead_with_case(), legacy_status='Submit', report_number='R-09261116331')          # R- + 092611 + counter 16331
        self.answer_required()
        body = self.submit().json()
        self.assertEqual(body['status'], 'Submit')
        self.assertRegex(body['report_number'], r'^R-\d{6}16332$')
        self.assertTrue(body['report_number'].startswith(f"R-{timezone.localdate():%m%y%d}"))

    def test_a_resubmitted_revert_keeps_its_report_number(self):
        self.answer_required()
        first = self.submit().json()['report_number']
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Revert')
        second = self.submit().json()['report_number']
        self.assertEqual(first, second)
        self.assertEqual(m.LeadCounter.objects.get(name='report').value, int(first[8:]))

    def test_legacy_renumbering_can_be_restored(self):
        self.answer_required()
        first = self.submit().json()['report_number']
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Revert')
        with mock.patch.object(valuation_submit, 'RENUMBER_ON_RESUBMIT', True):
            second = self.submit().json()['report_number']
        self.assertNotEqual(first, second)

    def test_a_second_click_never_issues_a_second_number(self):
        self.answer_required()
        self.assertEqual(self.submit().status_code, 200)
        again = self.submit()
        self.assertEqual(again.status_code, 409)
        self.assertIn('already submitted', again.json()['error'])
        self.assertEqual(m.LeadCounter.objects.get(name='report').value, 1)

    # --- the fields --------------------------------------------------------
    def test_submitted_to_is_stored(self):
        """Regression: the legacy form required it but never saved it."""
        self.answer_required()
        self.submit()
        v = m.Valuation.objects.get(pk=self.v)
        self.assertEqual(v.submitted_to, self.reviewer)
        self.assertEqual((v.eligible_loan_amount, v.desired_loan_amount), (Decimal('2500000.00'), Decimal('2000000.00')))
        self.assertEqual((v.dispatch_at_code, v.dispatch_by_code, v.report_category), (1, 2, 1))

    def test_every_required_field_is_enforced(self):
        self.answer_required()
        for field in ('submitted_to', 'dispatch_at', 'dispatch_by', 'report_category'):
            self.assertEqual(self.submit(**{field: ''}).status_code, 400, field)
        self.assertEqual(m.Valuation.objects.get(pk=self.v).legacy_status, 'Pending')

    def test_the_loan_amounts_are_optional(self):
        """Review 2026-10: not mandatory at final submission; blank is stored as not given."""
        self.answer_required()
        self.assertEqual(self.submit(eligible_loan_amount='', desired_loan_amount='').status_code, 200)
        v = m.Valuation.objects.get(pk=self.v)
        self.assertEqual((v.eligible_loan_amount, v.desired_loan_amount, v.legacy_status), (None, None, 'Submit'))

    def test_the_moment_of_submission_is_recorded(self):
        self.answer_required()
        before = timezone.now()
        body = self.submit().json()
        v = m.Valuation.objects.get(pk=self.v)
        self.assertTrue(before <= v.submitted_at <= timezone.now())
        self.assertIsNotNone(body['submission']['submitted_at'])

    def test_codes_outside_their_enum_are_refused(self):
        self.answer_required()
        self.assertEqual(self.submit(dispatch_by=9).status_code, 400)
        self.assertEqual(self.submit(report_category=0).status_code, 400)

    def test_the_valuation_date_defaults_to_today_and_cannot_be_in_the_future(self):
        self.answer_required()
        tomorrow = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.submit(valuation_date=tomorrow).status_code, 400)
        self.submit()
        self.assertEqual(m.Valuation.objects.get(pk=self.v).valuation_date, timezone.localdate())

    def test_a_submitted_valuation_is_locked_against_edits(self):
        self.answer_required()
        self.submit()
        edit = self.client.put(f'/api/valuations/{self.v}/sections/{self.site.pk}/',
                               {'answers': [{'question': str(self.text.pk), 'value': '2001'}]}, content_type='application/json')
        self.assertEqual(edit.status_code, 409)

    def test_a_held_valuation_cannot_be_submitted(self):
        self.answer_required()
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Hold')
        self.assertEqual(self.submit().status_code, 409)

    def test_submission_is_audited_and_makes_an_imported_valuation_local(self):
        self.answer_required()
        self.submit()
        self.assertTrue(m.IntakeAudit.objects.filter(action='submit_valuation', target_id=self.v).exists())
        self.assertTrue(m.LocalRecord.objects.filter(target_id=self.v).exists())
