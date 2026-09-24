"""The four verification queues, verifying a track, and sending work back."""
import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from . import models as m
from .sync import synchronize
from .test_valuations import Form
from .tests import FakeSource, dataset, row

TRACKS = ('legal', 'technical', 'social', 'general')


class Verification(Form, TestCase):
    def setUp(self):
        self.build()
        # spread the questions across tracks; one belongs to none
        m.Question.objects.filter(pk=self.text.pk).update(question_type=2)
        m.Question.objects.filter(pk=self.total.pk).update(question_type=3)
        m.Question.objects.filter(pk=self.calc.pk).update(question_type=None)
        self.user = User.objects.create_user('staff', password='x', is_staff=True, first_name='Udaybhan')
        self.client.force_login(self.user)
        self.reviewer = m.Employee.objects.create(name='Reviewer', legacy_status='1')
        self.v = self.submitted()

    def submitted(self, case=None):
        case = case or self.lead_with_case()
        v = self.client.post(f'/api/valuations/cases/{case.pk}/', {}, content_type='application/json').json()['id']
        self.client.put(f'/api/valuations/{v}/sections/{self.site.pk}/', {'answers': [
            {'question': str(self.radio.pk), 'selected': [str(self.radio_opts[0].pk)]},
            {'question': str(self.text.pk), 'value': '1999'}]}, content_type='application/json')
        r = self.client.post(f'/api/valuations/{v}/submission/', {
            'eligible_loan_amount': '1', 'desired_loan_amount': '1', 'submitted_to': str(self.reviewer.pk),
            'dispatch_at': 1, 'dispatch_by': 1, 'report_category': 1}, content_type='application/json')
        assert r.status_code == 200, r.content
        return v

    def queue(self, track):
        return self.client.get(f'/api/verifications/?track={track}').json()

    def verify(self, track, remark='Verified', v=None, **extra):
        return self.client.post(f'/api/verifications/{v or self.v}/{track}/', {'remark': remark, **extra},
                                content_type='application/json')

    def revert(self, remark='Photos missing', v=None):
        return self.client.post(f'/api/verifications/{v or self.v}/revert/', {'remark': remark},
                                content_type='application/json')


class QueueTests(Verification):
    def test_a_submitted_valuation_waits_in_all_four_queues(self):
        counts = self.queue('legal')['counts']
        self.assertEqual(counts, {t: 1 for t in TRACKS})

    def test_verifying_a_track_clears_only_that_queue(self):
        self.assertEqual(self.verify('legal').status_code, 200)
        counts = self.queue('legal')['counts']
        self.assertEqual(counts, {'legal': 0, 'technical': 1, 'social': 1, 'general': 1})

    def test_tracks_may_be_verified_in_any_order(self):
        for track in ('general', 'social', 'legal', 'technical'):
            self.assertEqual(self.verify(track).status_code, 200)
        self.assertEqual(self.queue('legal')['counts'], {t: 0 for t in TRACKS})

    def test_a_pending_valuation_is_in_no_queue(self):
        self.lead_with_case()
        self.client.post(f'/api/valuations/cases/{self.lead_with_case().pk}/', {}, content_type='application/json')
        self.assertEqual(self.queue('legal')['total'], 1)


class TrackViewTests(Verification):
    def ids(self, body):
        return {q['id'] for s in body['sections'] for q in s['questions']}

    def test_each_track_sees_only_its_own_questions(self):
        legal = self.client.get(f'/api/verifications/{self.v}/?track=legal').json()
        technical = self.client.get(f'/api/verifications/{self.v}/?track=technical').json()
        self.assertIn(str(self.radio.pk), self.ids(legal))
        self.assertNotIn(str(self.text.pk), self.ids(legal))
        self.assertEqual(self.ids(technical), {str(self.text.pk)})

    def test_questions_in_no_track_are_shown_to_every_track(self):
        for track in TRACKS:
            body = self.client.get(f'/api/verifications/{self.v}/?track={track}').json()
            self.assertEqual([q['id'] for q in body['unassigned']], [str(self.calc.pk)])

    def test_the_verifier_sees_the_recorded_answers(self):
        body = self.client.get(f'/api/verifications/{self.v}/?track=technical').json()
        self.assertEqual(body['sections'][0]['questions'][0]['answer']['value'], '1999')

    def test_viewing_does_not_create_a_verification_record(self):
        """Regression: the legacy page created the record on a read."""
        self.client.get(f'/api/verifications/{self.v}/?track=legal')
        self.assertFalse(m.ValuationVerification.objects.exists())


class VerifyTests(Verification):
    def test_verifying_records_remark_date_and_verifier(self):
        self.verify('legal', remark='Title chain checked')
        v = m.ValuationVerification.objects.get()
        self.assertEqual((v.legal_status, v.legal_remark, v.legal_date), ('Verified', 'Title chain checked', timezone.localdate()))
        self.assertEqual(v.legal_done_by_name, 'Udaybhan')

    def test_a_remark_is_required(self):
        self.assertEqual(self.verify('legal', remark='  ').status_code, 400)

    def test_the_date_cannot_be_in_the_future(self):
        tomorrow = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.verify('legal', date=tomorrow).status_code, 400)

    def test_a_track_cannot_be_verified_twice(self):
        self.verify('legal')
        again = self.verify('legal')
        self.assertEqual(again.status_code, 409)
        self.assertIn('Udaybhan', again.json()['error'])

    def test_only_a_submitted_valuation_can_be_verified(self):
        """Regression: the legacy save never checked the status."""
        m.Valuation.objects.filter(pk=self.v).update(legacy_status='Pending')
        self.assertEqual(self.verify('legal').status_code, 409)

    def test_an_unknown_track_is_refused(self):
        self.assertEqual(self.verify('financial').status_code, 404)


class RevertTests(Verification):
    def test_sending_back_resets_every_track_and_keeps_who_verified(self):
        self.verify('legal')
        self.verify('social')
        body = self.revert('Photos missing').json()
        self.assertEqual(body['status'], 'Revert')
        v = m.ValuationVerification.objects.get()
        self.assertEqual((v.legal_status, v.social_status), ('UnVerified', 'UnVerified'))
        self.assertEqual(v.legal_done_by_name, 'Udaybhan')         # not overwritten by the reverter
        r = m.Reversion.objects.get()
        self.assertEqual((r.remark, r.stage, r.reverted_by_name), ('Photos missing', 'verification', 'Udaybhan'))

    def test_every_revert_is_kept(self):
        """Regression: the legacy table kept one revert per valuation."""
        self.revert('First problem')
        self._resubmit()
        self.revert('Second problem')
        remarks = [r['remark'] for r in self.client.get(f'/api/verifications/{self.v}/').json()['reversions']]
        self.assertEqual(sorted(remarks), ['First problem', 'Second problem'])

    def _resubmit(self):
        r = self.client.post(f'/api/valuations/{self.v}/submission/', {
            'eligible_loan_amount': '1', 'desired_loan_amount': '1', 'submitted_to': str(self.reviewer.pk),
            'dispatch_at': 1, 'dispatch_by': 1, 'report_category': 1}, content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()['report_number']

    def test_a_resubmitted_valuation_returns_to_the_queues_with_its_number(self):
        number = m.Valuation.objects.get(pk=self.v).report_number
        self.verify('legal')
        self.revert()
        self.assertEqual(self.queue('legal')['total'], 0)
        self.assertEqual(self._resubmit(), number)
        self.assertEqual(self.queue('legal')['counts'], {t: 1 for t in TRACKS})

    def test_a_finally_approved_valuation_is_not_sent_back_from_here(self):
        m.ValuationVerification.objects.create(valuation_id=self.v, final_status='Verified')
        self.assertEqual(self.revert().status_code, 409)

    def test_a_reason_is_required(self):
        self.assertEqual(self.revert(remark='').status_code, 400)


class ScopeTests(Form, TestCase):
    def test_a_field_assessor_verifies_only_their_own_leads(self):
        from .test_valuations import user_with_role
        self.build()
        me = m.Employee.objects.create(name='Assessor')
        other = m.Employee.objects.create(name='Other')
        mine, theirs = self.lead_with_case(assigned=me), self.lead_with_case(assigned=other)
        for case in (mine, theirs):
            m.Valuation.objects.create(case=case, legacy_status='Submit', report_number=f'R-{case.pk.hex[:8]}')
        user = user_with_role('157', me)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/api/verifications/?track=legal').json()['total'], 1)
        target = m.Valuation.objects.get(case=theirs)
        response = self.client.post(f'/api/verifications/{target.pk}/legal/', {'remark': 'x'}, content_type='application/json')
        self.assertEqual(response.status_code, 404)


class ImportedVerificationTests(TestCase):
    def test_a_local_verification_of_an_imported_record_survives_reimport(self):
        data = dataset({
            ('lead_mngt', 'lead_order'): [row('lead_mngt', 'lead_order', lead_order_id=1, lead_id=1, lead_borrower_id=1)],
            ('lead_mngt', 'valuation'): [row('lead_mngt', 'valuation', valuation_id=1, client_customer_id=1,
                                             lead_order_id=1, valuation_status='Submit', report_no='R-0926010001')],
            ('lead_mngt', 'valuation_verification'): [row('lead_mngt', 'valuation_verification', verification_id=1,
                                                          valuation_id=1, legal_verification_status='Verified',
                                                          legal_verification_done_name='Old Verifier')]})
        synchronize(FakeSource(data))
        valuation = m.Valuation.objects.get()
        self.client.force_login(User.objects.create_user('staff', password='x', is_staff=True, first_name='New'))
        self.assertEqual(self.client.post(f'/api/verifications/{valuation.pk}/legal/', {'remark': 'x'},
                                          content_type='application/json').status_code, 409)   # already verified
        self.assertEqual(self.client.post(f'/api/verifications/{valuation.pk}/social/', {'remark': 'Checked'},
                                          content_type='application/json').status_code, 200)
        synchronize(FakeSource(data))
        v = m.ValuationVerification.objects.get()
        self.assertEqual((v.social_status, v.social_remark), ('Verified', 'Checked'))    # not reverted by the import
        self.assertEqual(v.legal_done_by_name, 'Old Verifier')
