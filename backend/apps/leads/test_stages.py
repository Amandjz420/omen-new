"""Where each case stands: the stage track on the lead page."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from target_core import models as m
from apps.valuations.test_forms import Form, user_with_role


class StageTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.client.force_login(User.objects.create_user('staff', password='x', is_staff=True))
        self.case = self.lead_with_case(ordered=False)

    def stages(self, case=None):
        case = case or self.case
        body = self.client.get(f'/api/leads/{case.lead_id}/stages/').json()
        return {s['key']: (s['state'], s['detail']) for s in body['cases'][0]['stages']}

    def test_a_new_case_waits_for_its_work_order(self):
        s = self.stages()
        self.assertEqual(s['intake'][0], 'done')
        self.assertEqual(s['work_order'][0], 'current')
        self.assertEqual(s['dispatch'][0], 'waiting')

    def test_a_valuation_in_progress_is_the_current_stage(self):
        m.WorkOrder.objects.create(lead=self.case.lead, borrower=self.case.borrower, number='O-1')
        m.Valuation.objects.create(case=self.case, legacy_status='Revert')
        s = self.stages()
        self.assertEqual(s['work_order'], ('done', 'O-1'))
        self.assertEqual(s['valuation'], ('current', 'Sent back for correction'))

    def test_verification_counts_its_checks(self):
        m.WorkOrder.objects.create(lead=self.case.lead, borrower=self.case.borrower, number='O-1')
        v = m.Valuation.objects.create(case=self.case, legacy_status='Submit')
        m.ValuationVerification.objects.create(valuation=v, legal_status='Verified', social_status='Verified')
        self.assertEqual(self.stages()['verification'], ('current', '2 of 4 checks'))

    def test_an_outstanding_invoice_shows_what_is_owed(self):
        v = m.Valuation.objects.create(case=self.case, legacy_status='Submit')
        m.Invoice.objects.create(valuation=v, origin='local_invoice', number='I-1', legacy_remaining_amount=Decimal('680'))
        s = self.stages()
        self.assertEqual(s['invoice'], ('done', 'I-1'))
        self.assertEqual(s['payment'], ('current', '₹680 outstanding'))

    def test_a_later_stage_implies_the_earlier_ones(self):
        """Imported cases do not always carry every intermediate record."""
        v = m.Valuation.objects.create(case=self.case, legacy_status='Submit')
        m.ValuationVerification.objects.create(valuation=v, final_status='Verified')
        s = self.stages()
        self.assertEqual([s[k][0] for k in ('work_order', 'valuation', 'verification', 'bank_report', 'approval')], ['done'] * 5)
        self.assertEqual(s['invoice'][0], 'current')

    def test_a_cancelled_valuation_stops_the_track(self):
        m.Valuation.objects.create(case=self.case, legacy_status='Cancel')
        s = self.stages()
        self.assertEqual(s['valuation'], ('stopped', 'Cancelled'))
        self.assertEqual({s[k][0] for k in ('verification', 'invoice', 'dispatch')}, {'skipped'})

    def test_a_delivered_dispatch_completes_the_track(self):
        v = m.Valuation.objects.create(case=self.case, legacy_status='Submit')
        m.Invoice.objects.create(valuation=v, origin='local_invoice', number='I-2', legacy_remaining_amount=Decimal('0'))
        d = m.Dispatch.objects.create(number='D-1', status=3, outward_date=datetime.date(2026, 9, 1))
        m.DispatchItem.objects.create(dispatch=d, position=0, reference='R-1', valuation=v, resolution='chosen')
        self.assertEqual(set(state for state, _ in self.stages().values()), {'done'})

    def test_a_restricted_user_sees_only_their_own_cases(self):
        me, other = m.Employee.objects.create(name='Assessor'), m.Employee.objects.create(name='Other')
        theirs = self.lead_with_case(assigned=other)
        self.client.force_login(user_with_role('157', me))
        self.assertEqual(self.client.get(f'/api/leads/{theirs.lead_id}/stages/').json()['cases'], [])
