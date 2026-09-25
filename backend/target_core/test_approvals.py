"""Final approval, the final revert and revisions, and hold, unhold and cancel."""
from django.test import override_settings

from . import models as m
from .test_bank_reports import MEDIA, BankReportTests

TRACKS = ('legal', 'technical', 'social', 'general')


@override_settings(MEDIA_ROOT=MEDIA)
class Approval(BankReportTests):
    def approve(self, v=None, **body):
        return self.client.post(f'/api/approvals/{v or self.v}/approve/', body, content_type='application/json')

    def final_revert(self, reason='Area recheck needed', v=None):
        return self.client.post(f'/api/approvals/{v or self.v}/revert/', {'reason': reason}, content_type='application/json')

    def standing(self, action, reason='Documents awaited', v=None):
        return self.client.post(f'/api/valuations/{v or self.v}/standing/{action}/', {'reason': reason},
                                content_type='application/json')

    def resubmit_and_verify(self):
        r = self.client.post(f'/api/valuations/{self.v}/submission/', {
            'eligible_loan_amount': '1', 'desired_loan_amount': '1', 'submitted_to': str(self.reviewer.pk),
            'dispatch_at': 1, 'dispatch_by': 1, 'report_category': 1}, content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        for track in TRACKS:
            self.client.post(f'/api/verifications/{self.v}/{track}/', {'remark': 'ok'}, content_type='application/json')
        return r.json()['report_number']


class ApproveTests(Approval):
    def test_approval_issues_the_report(self):
        self.generate()
        body = self.approve().json()
        self.assertTrue(body['approved'])
        self.assertEqual(body['approved_by'], 'Sanjeev')
        self.assertIsNotNone(m.BankReport.objects.get().approved_at)
        self.assertEqual(m.ValuationEvent.objects.get().kind, 'approve')
        self.assertEqual(m.Valuation.objects.get(pk=self.v).legacy_status, 'Submit')   # as in the legacy data

    def test_approval_needs_a_generated_report(self):
        """Regression: the legacy save checked nothing."""
        self.assertIn('Generate the bank report', self.approve().json()['error'])

    def test_approval_needs_all_four_verifications(self):
        self.generate()
        m.ValuationVerification.objects.filter(valuation_id=self.v).update(general_status='UnVerified')
        self.assertEqual(self.approve().status_code, 409)

    def test_a_report_is_approved_once(self):
        self.generate()
        self.approve()
        self.assertEqual(self.approve().status_code, 409)

    def test_the_queue_separates_pending_and_approved(self):
        self.generate()
        self.assertEqual(self.client.get('/api/approvals/').json()['counts'], {'pending': 1, 'approved': 0})
        self.approve()
        self.assertEqual(self.client.get('/api/approvals/').json()['counts'], {'pending': 0, 'approved': 1})


class FinalRevertTests(Approval):
    def test_an_issued_report_is_superseded_and_kept_not_deleted(self):
        """Regression: the legacy final revert deleted the bank report."""
        self.generate()
        self.approve()
        body = self.final_revert().json()
        self.assertEqual(body['status'], 'Revert')
        report = m.BankReport.objects.get()
        self.assertIsNotNone(report.superseded_at)
        self.assertIsNotNone(report.document_id)
        v = m.ValuationVerification.objects.get()
        self.assertEqual((v.legal_status, v.final_status), ('UnVerified', 'UnVerified'))
        self.assertEqual(v.legal_done_by_name, 'Sanjeev')                   # the verifier is kept
        self.assertEqual(m.Reversion.objects.get().stage, 'final')

    def test_the_full_revision_cycle(self):
        self.generate()
        number = m.Valuation.objects.get(pk=self.v).report_number
        self.approve()
        self.final_revert()
        self.assertEqual(self.resubmit_and_verify(), number)                # the report keeps its number
        self.assertEqual(self.generate().status_code, 200)
        self.assertEqual(sorted(m.BankReport.objects.values_list('revision', flat=True)), [0, 1])
        self.assertIn('Revision 1', self.document_text())
        self.assertEqual(self.approve().status_code, 200)
        body = self.client.get(f'/api/bank-reports/{self.v}/').json()
        self.assertEqual((body['report']['revision'], [s['revision'] for s in body['superseded']]), (1, [0]))

    def test_an_unissued_draft_is_revised_in_place(self):
        self.generate()
        self.final_revert()
        self.assertIsNone(m.BankReport.objects.get().superseded_at)
        self.resubmit_and_verify()
        self.generate()
        self.assertEqual(list(m.BankReport.objects.values_list('revision', flat=True)), [0])
        self.assertEqual(m.Reversion.objects.get().stage, 'bank report')

    def test_nothing_to_revert_before_a_report_exists(self):
        self.assertEqual(self.final_revert().status_code, 409)

    def test_a_reason_is_required(self):
        self.generate()
        self.assertEqual(self.final_revert(reason='').status_code, 400)


class StandingTests(Approval):
    def test_unholding_restores_the_status_it_was_held_from(self):
        """Regression: the legacy unhold always returned Pending."""
        self.assertEqual(self.standing('hold').json()['status'], 'Hold')
        self.assertEqual(self.standing('unhold', 'Documents received').json()['status'], 'Submit')

    def test_an_imported_hold_of_unknown_origin_returns_to_pending(self):
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Hold', held_from_status='')
        self.assertEqual(self.standing('unhold').json()['status'], 'Pending')

    def test_every_change_of_standing_is_kept(self):
        """Regression: the legacy reason field was overwritten each time."""
        self.standing('hold', 'First')
        self.standing('unhold', 'Second')
        self.standing('hold', 'Third')
        events = self.client.get(f'/api/valuations/{self.v}/standing/').json()['events']
        self.assertEqual([e['reason'] for e in events], ['Third', 'Second', 'First'])

    def test_a_reason_is_required(self):
        self.assertEqual(self.standing('hold', reason='').status_code, 400)

    def test_an_approved_valuation_cannot_be_held_or_cancelled(self):
        self.generate()
        self.approve()
        self.assertEqual(self.standing('hold').status_code, 409)
        self.assertEqual(self.standing('cancel').status_code, 409)

    def test_cancellation_is_final(self):
        self.assertEqual(self.standing('cancel', 'Double entry').json()['status'], 'Cancel')
        self.assertEqual(self.standing('hold').status_code, 409)
        self.assertEqual(self.standing('unhold').status_code, 409)

    def test_a_held_valuation_can_be_cancelled(self):
        self.standing('hold')
        self.assertEqual(self.standing('cancel').json()['status'], 'Cancel')

    def test_an_invoiced_valuation_cannot_be_cancelled(self):
        m.Invoice.objects.create(valuation_id=self.v, number='INV-1')
        response = self.standing('cancel')
        self.assertEqual(response.status_code, 409)
        self.assertIn('invoiced', response.json()['error'])

    def test_an_unknown_action_is_refused(self):
        self.assertEqual(self.standing('delete').status_code, 404)
