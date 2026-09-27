"""Review BF1: every endpoint that starts from a lead applies the assessor scope."""
import uuid

from django.contrib.auth.models import User
from django.test import TestCase

from target_core import models as m
from apps.valuations.test_forms import Form, user_with_role


class LeadScopeTests(Form, TestCase):
    def setUp(self):
        self.build()
        self.a, self.b = m.Employee.objects.create(name='Assessor A'), m.Employee.objects.create(name='Assessor B')
        self.case = self.lead_with_case(assigned=self.a)
        self.lead = self.case.lead
        self.order = m.WorkOrder.objects.get(lead=self.lead)            # lead_with_case issues one

    def as_(self, employee):
        user = user_with_role('157', employee)
        self.client.force_login(user)
        return user

    def reads(self):
        """Every lead-scoped read, and whether each answered 200."""
        L, W = self.lead.pk, self.order.pk
        return {path: self.client.get(path).status_code == 200 for path in (
            f'/api/leads/{L}/', f'/api/leads/{L}/stages/', f'/api/intake/leads/{L}/',
            f'/api/work-orders/leads/{L}/', f'/api/work-orders/{W}/', f'/api/work-orders/{W}/document/')}

    def listed(self):
        return str(self.lead.pk) in [r['id'] for r in self.client.get('/api/leads/').json()['results']]

    def test_the_assigned_assessor_reaches_their_lead(self):
        self.as_(self.a)
        self.assertTrue(self.listed())
        closed = [p for p, ok in self.reads().items() if not ok and not p.endswith('/document/')]
        self.assertEqual(closed, [])

    def test_another_assessor_reaches_none_of_it(self):
        """Codex's reproduction: the list, detail and a note were all open to assessor B."""
        self.as_(self.b)
        self.assertFalse(self.listed())                                              # previously listed
        self.assertEqual([p for p, ok in self.reads().items() if ok], [])            # previously 200 for several
        note = self.client.post(f'/api/leads/{self.lead.pk}/', {'body': 'Not mine'}, content_type='application/json')
        self.assertEqual(note.status_code, 404)                                       # previously 201
        self.assertFalse(m.LeadNote.objects.exists())                                 # and nothing was saved
        before = m.Borrower.objects.count()
        added = self.client.post(f'/api/intake/leads/{self.lead.pk}/borrowers/', {'name': 'Someone'}, content_type='application/json')
        self.assertEqual((added.status_code, m.Borrower.objects.count()), (404, before))   # nor a borrower added

    def test_a_work_order_cannot_be_issued_on_someone_elses_lead(self):
        waiting = self.lead_with_case(assigned=self.a, ordered=False)
        before = m.WorkOrder.objects.count()
        self.as_(self.b)
        response = self.client.post('/api/work-orders/', {'request_id': str(uuid.uuid4()), 'borrower': str(waiting.borrower.pk)},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(m.WorkOrder.objects.count(), before)                  # nothing was issued

    def test_reassigning_moves_access(self):
        m.Lead.objects.filter(pk=self.lead.pk).update(assigned_employee=self.b)
        self.as_(self.a)
        self.assertFalse(self.listed())
        self.assertEqual([p for p, ok in self.reads().items() if ok], [])
        self.as_(self.b)
        self.assertTrue(self.listed())

    def test_an_unassigned_lead_is_head_office_work(self):
        m.Lead.objects.filter(pk=self.lead.pk).update(assigned_employee=None)
        self.as_(self.a)
        self.assertFalse(self.listed())

    def test_revoked_access_closes_everything_including_a_replay(self):
        user = self.as_(self.a)
        body = {'request_id': str(uuid.uuid4()), 'borrower': str(self.lead_with_case(assigned=self.a, ordered=False).borrower.pk)}
        self.assertEqual(self.client.post('/api/work-orders/', body, content_type='application/json').status_code, 201)
        m.RoleAssignment.objects.filter(account__user=user).update(legacy_status='0')
        self.assertFalse(self.listed())
        self.assertEqual([p for p, ok in self.reads().items() if ok], [])
        self.assertEqual(self.client.post('/api/work-orders/', body, content_type='application/json').status_code, 404)

    def test_head_office_keeps_full_access(self):
        self.client.force_login(User.objects.create_user('office', password='x', is_staff=True))
        self.assertTrue(self.listed())
        closed = [p for p, ok in self.reads().items() if not ok and not p.endswith('/document/')]
        self.assertEqual(closed, [])
        note = self.client.post(f'/api/leads/{self.lead.pk}/', {'body': 'Called the branch'}, content_type='application/json')
        self.assertEqual(note.status_code, 201)
