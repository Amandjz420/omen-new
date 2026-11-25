"""Client review 2026-11-25: the lead form asks for no service and no assignee; the lead
is received by whoever records it, waits unassigned, and is picked up by someone with a
pickup role (LEAD_PICKUP_ROLES) or reassigned by a manager. The person who received a
lead keeps seeing it."""
from django.test import TestCase, override_settings

from target_core import models as m
from apps.leads.test_intake import IntakeFixture
from apps.valuations.test_forms import user_with_role


class ReceivedByTests(IntakeFixture, TestCase):
    def test_the_person_recording_the_lead_received_it(self):
        m.LegacyAccount.objects.create(name='Intake admin', login_id='intake-admin', user=self.user, employee=self.employee,
                                       must_change_password=False)
        other = m.Employee.objects.create(name='Someone else')
        lead = self.create(received_by=str(other.pk))                    # what the browser sends is not trusted
        self.assertEqual((lead.received_by, lead.assigned_employee, lead.legacy_status), (self.employee, None, '1'))
        self.assertEqual(self.client.get('/api/intake/lookups/').json()['me'],
                         {'employee_id': str(self.employee.pk), 'name': 'Test assessor'})

    def test_an_account_with_no_employee_names_who_received_it(self):
        body = self.data(); del body['received_by']
        self.assertEqual(self.send('/api/intake/leads/', body).status_code, 400)
        self.assertEqual(self.create().received_by, self.employee)


class PickUpTests(IntakeFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.lead = self.create()
        self.lead.legacy_deleted = '0'; self.lead.save()
        self.url = f'/api/intake/leads/{self.lead.pk}/'
        self.picker = m.Employee.objects.create(name='Operations executive')

    def as_role(self, source_id, employee, role_name=None):
        user = user_with_role(source_id, employee)
        if role_name:
            m.RoleDefinition.objects.filter(roleassignment__account__user=user).update(name=role_name)
        self.client.force_login(user)
        return user

    def listed(self, **query):
        return [r['id'] for r in self.client.get('/api/leads/', query).json()['results']]

    def test_a_manager_picks_up_a_lead_and_it_is_in_process(self):
        self.as_role('1', self.picker)                                     # an unrestricted role: a manager
        self.assertEqual(self.listed(assignment='unassigned'), [str(self.lead.pk)])
        detail = self.client.get(f'/api/leads/{self.lead.pk}/').json()
        self.assertEqual((detail['can_pick_up'], detail['can_reassign'], detail['assigned_to']), (True, True, None))
        r = self.send(self.url + 'pick-up/', {})
        self.assertEqual(r.status_code, 200, r.content)
        self.lead.refresh_from_db()
        self.assertEqual((self.lead.assigned_employee, self.lead.legacy_status), (self.picker, '2'))
        self.assertTrue(m.IntakeAudit.objects.filter(action='lead.pickup', target_id=self.lead.pk).exists())
        self.assertEqual(self.send(self.url + 'pick-up/', {}).status_code, 409)          # already picked up
        self.assertEqual(self.listed(assignment='unassigned'), [])
        self.assertEqual(self.listed(assignment='mine'), [str(self.lead.pk)])
        self.assertFalse(self.client.get(f'/api/leads/{self.lead.pk}/').json()['can_pick_up'])

    def test_an_account_with_no_employee_cannot_pick_up_but_can_reassign(self):
        self.assertEqual(self.send(self.url + 'pick-up/', {}).status_code, 403)
        self.assertEqual(self.send(self.url + 'reassign/', {}).status_code, 400)
        r = self.send(self.url + 'reassign/', {'employee': str(self.picker.pk)})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['assigned_name'], 'Operations executive')
        self.assertTrue(m.IntakeAudit.objects.filter(action='lead.reassign', target_id=self.lead.pk).exists())

    def test_until_pickup_roles_are_set_a_restricted_user_cannot_pick_up(self):
        self.as_role('157', self.picker)
        self.assertNotIn(str(self.lead.pk), self.listed())
        self.assertEqual(self.send(self.url + 'pick-up/', {}).status_code, 404)

    @override_settings(LEAD_PICKUP_ROLES=['Lead Desk'])
    def test_a_pickup_role_sees_the_queue_and_picks_up_but_cannot_reassign(self):
        self.as_role('157', self.picker, role_name='Lead desk')               # names match whatever their case
        self.assertIn(str(self.lead.pk), self.listed(assignment='unassigned'))
        detail = self.client.get(f'/api/leads/{self.lead.pk}/').json()
        self.assertEqual((detail['can_pick_up'], detail['can_reassign']), (True, False))
        self.assertEqual(self.send(self.url + 'pick-up/', {}).status_code, 200)
        self.assertEqual(self.send(self.url + 'reassign/', {'employee': str(self.employee.pk)}).status_code, 403)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_employee, self.picker)

    def test_the_person_who_received_a_lead_keeps_seeing_and_editing_it(self):
        receiver = m.Employee.objects.create(name='Receptionist')
        m.Lead.objects.filter(pk=self.lead.pk).update(received_by=receiver, assigned_employee=self.picker)
        self.as_role('157', receiver)
        self.assertIn(str(self.lead.pk), self.listed())
        self.assertEqual(self.send(self.url, {'case_count': 3}, 'patch').status_code, 200)
        self.as_role('157', m.Employee.objects.create(name='Unrelated'))
        self.assertNotIn(str(self.lead.pk), self.listed())

    def test_a_closed_or_cancelled_lead_is_not_picked_up(self):
        m.Lead.objects.filter(pk=self.lead.pk).update(legacy_status='3')
        self.assertEqual(self.send(self.url + 'reassign/', {'employee': str(self.picker.pk)}).status_code, 409)
