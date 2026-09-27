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
        self.assertEqual(s['invoice'], ('done', 'I-1, issued before the current approval'))   # this valuation is not approved
        self.assertEqual(s['payment'][1], '₹680 outstanding')
        self.assertNotEqual(s['payment'][0], 'done')              # earlier stages are unfinished, so it is not current

    def valued(self, status):
        """A valuation on its work order, as every real valuation has one."""
        order = m.WorkOrder.objects.create(lead=self.case.lead, borrower=self.case.borrower, number=f'O-{m.WorkOrder.objects.count() + 1}')
        return m.Valuation.objects.create(case=self.case, legacy_status=status, work_order=order)

    def approved_case(self, owed='0', delivered=True):
        """A case through every stage on its own records: submitted, all four checks,
        a current report, approval, an invoice and, if asked, delivery."""
        v = self.valued('Submit')
        m.ValuationVerification.objects.create(valuation=v, legal_status='Verified', technical_status='Verified',
                                               social_status='Verified', general_status='Verified', final_status='Verified')
        report = m.BankReport.objects.create(valuation=v, revision=0)
        invoice = m.Invoice.objects.create(valuation=v, origin='local_invoice', number='I-3', legacy_remaining_amount=Decimal(owed))
        if delivered:
            d = m.Dispatch.objects.create(number='D-3', status=3, outward_date=datetime.date(2026, 9, 1))
            m.DispatchItem.objects.create(dispatch=d, position=0, reference='R-1', valuation=v, bank_report=report, resolution='chosen')
        return v, invoice

    def test_delivery_does_not_mean_payment(self):
        """Review BF3: a delivered report with an unpaid invoice showed payment done."""
        self.approved_case(owed='1180')
        s = self.stages()
        self.assertEqual(s['dispatch'][0], 'done')
        self.assertEqual(s['payment'], ('current', '₹1,180 outstanding'))            # previously done

    def test_an_invoice_before_approval_does_not_approve_the_work(self):
        v = self.valued('Submit')
        m.ValuationVerification.objects.create(valuation=v, legal_status='Verified')
        m.Invoice.objects.create(valuation=v, origin='local_invoice', number='I-4', legacy_remaining_amount=Decimal('500'))
        s = self.stages()
        self.assertEqual(s['verification'], ('current', '1 of 4 checks'))
        self.assertEqual(s['approval'][0], 'waiting')
        self.assertEqual(s['invoice'], ('done', 'I-4, issued before the current approval'))

    def test_a_reverted_valuation_is_not_shown_as_verified_or_approved(self):
        """Review BF3: after a final revert, an existing invoice made the earlier stages look done."""
        v, _ = self.approved_case(delivered=False)
        m.Valuation.objects.filter(pk=v.pk).update(legacy_status='Revert')
        m.ValuationVerification.objects.filter(valuation=v).update(legal_status='', technical_status='', social_status='',
                                                                   general_status='', final_status='')
        m.BankReport.objects.filter(valuation=v).update(superseded_at=datetime.datetime(2026, 9, 2, tzinfo=datetime.timezone.utc))
        s = self.stages()
        self.assertEqual(s['valuation'], ('current', 'Sent back for correction'))
        self.assertEqual(s['verification'], ('waiting', '0 of 4 checks'))            # previously done
        self.assertEqual([s[k][0] for k in ('bank_report', 'approval')], ['waiting', 'waiting'])
        self.assertEqual(s['invoice'][0], 'done')                                    # a historical fact, labelled
        self.assertIn('before the current approval', s['invoice'][1])

    def test_a_reverted_valuation_put_on_hold_is_stopped(self):
        v, _ = self.approved_case(delivered=False)
        m.Valuation.objects.filter(pk=v.pk).update(legacy_status='Hold')
        m.ValuationVerification.objects.filter(valuation=v).update(final_status='')
        s = self.stages()
        self.assertEqual(s['valuation'], ('stopped', 'On hold'))                      # previously done
        self.assertNotIn('current', [state for state, _ in s.values()])

    def test_only_one_stage_is_current(self):
        self.valued('Pending')
        self.assertEqual([state for state, _ in self.stages().values()].count('current'), 1)

    def test_a_cancelled_valuation_stops_the_track(self):
        m.Valuation.objects.create(case=self.case, legacy_status='Cancel')
        s = self.stages()
        self.assertEqual(s['valuation'], ('stopped', 'Cancelled'))
        self.assertEqual({s[k][0] for k in ('verification', 'invoice', 'dispatch')}, {'skipped'})

    def test_a_case_complete_on_its_own_records_is_complete(self):
        self.approved_case()
        self.assertEqual(set(state for state, _ in self.stages().values()), {'done'})

    def test_a_dispatch_counts_only_for_the_current_revision(self):
        v = m.Valuation.objects.create(case=self.case, legacy_status='Submit')
        old = m.BankReport.objects.create(valuation=v, revision=0, superseded_at=datetime.datetime(2026, 9, 2, tzinfo=datetime.timezone.utc))
        m.BankReport.objects.create(valuation=v, revision=1)
        d = m.Dispatch.objects.create(number='D-2', status=3, outward_date=datetime.date(2026, 9, 1))
        m.DispatchItem.objects.create(dispatch=d, position=0, reference='R-1', valuation=v, bank_report=old, resolution='chosen')
        self.assertNotEqual(self.stages()['dispatch'][0], 'done')          # revision 1 has not been sent

    def test_a_restricted_user_sees_only_their_own_cases(self):
        me, other = m.Employee.objects.create(name='Assessor'), m.Employee.objects.create(name='Other')
        theirs = self.lead_with_case(assigned=other)
        self.client.force_login(user_with_role('157', me))
        # Not found, as for a lead that does not exist, rather than an empty list (review BF1).
        self.assertEqual(self.client.get(f'/api/leads/{theirs.lead_id}/stages/').status_code, 404)
