"""Dispatch: awaiting reports, numbering, resends, status and cancellation."""
import uuid

from django.test import override_settings
from django.utils import timezone

from target_core import models as m
from apps.reports.test_approvals import Approval
from apps.reports.test_reports import MEDIA


@override_settings(MEDIA_ROOT=MEDIA)
class DispatchTests(Approval):
    def setUp(self):
        super().setUp()
        self.generate()
        self.approve()

    def send(self, operation_id=None, **overrides):
        body = {'operation_id': str(operation_id or uuid.uuid4()), 'reports': [str(self.v)], 'mode': 2,
                'status': 1, **overrides}
        return self.client.post('/api/dispatch/', body, content_type='application/json')

    def awaiting(self):
        return self.client.get('/api/dispatch/awaiting/').json()

    def step(self, d, **body):
        return self.client.post(f'/api/dispatch/{d}/advance/', body, content_type='application/json')

    def test_an_approved_report_awaits_dispatch_until_sent(self):
        self.assertEqual([r['valuation'] for r in self.awaiting()['results']], [str(self.v)])
        body = self.send().json()
        self.assertEqual((body['document_count'], body['items'][0]['valuation']), (1, str(self.v)))
        self.assertEqual(self.awaiting()['total'], 0)

    def test_the_number_continues_the_legacy_series_skipping_the_old_scheme(self):
        m.Dispatch.objects.create(number='D-0926106707')
        m.Dispatch.objects.create(number='D-022117820280002')             # the 17-character 2021 scheme
        self.assertTrue(self.send().json()['number'].endswith('6708'))

    def test_the_counter_continues_past_9999(self):
        """The legacy query skipped numbers of 13+ characters, so it would repeat 10000."""
        m.Dispatch.objects.create(number='D-0926109999')
        first = self.send(other_documents=['Title deed copy'], reports=[]).json()['number']
        second = self.send(other_documents=['Map copy'], reports=[]).json()['number']
        self.assertEqual((first[8:], second[8:]), ('10000', '10001'))

    def test_a_resend_needs_a_reason(self):
        self.send()
        refused = self.send()
        self.assertEqual(refused.status_code, 409)
        self.assertIn('already been dispatched', refused.json()['error'])
        again = self.send(resend={str(self.v): 'Bank lost the first copy'}).json()
        self.assertTrue(again['items'][0]['resend'])

    def test_status_moves_forward_and_delivery_needs_a_date(self):
        d = self.send().json()['id']
        self.assertEqual(self.step(d, status=2).status_code, 400)          # speed post needs a consignment number
        self.assertEqual(self.step(d, status=2, consignment_number='EM123456789IN').status_code, 200)
        self.assertEqual(self.step(d, status=3).status_code, 400)          # no delivery date
        today = timezone.localdate().isoformat()
        self.assertEqual(self.step(d, status=3, delivered_date=today).json()['status_label'], 'Delivered')
        self.assertEqual(self.step(d, status=2).status_code, 409)          # never backwards

    def test_a_delivery_date_cannot_precede_the_outward_date(self):
        d = self.send(outward_date=timezone.localdate().isoformat()).json()['id']
        earlier = (timezone.localdate() - timezone.timedelta(days=3)).isoformat()
        self.assertEqual(self.step(d, status=3, delivered_date=earlier).status_code, 400)

    def test_cancelling_returns_the_report_to_the_queue_but_not_once_delivered(self):
        d = self.send().json()['id']
        cancel = lambda x, r='Wrong address': self.client.post(f'/api/dispatch/{x}/cancel/', {'reason': r}, content_type='application/json')
        self.assertEqual(cancel(d).status_code, 200)
        self.assertEqual(self.awaiting()['total'], 1)
        delivered = self.send(status=3, consignment_number='EM1', delivered_date=timezone.localdate().isoformat()).json()['id']
        self.assertEqual(cancel(delivered).status_code, 409)

    def test_a_courier_must_be_named(self):
        self.assertEqual(self.send(mode=1).status_code, 400)
        self.assertEqual(self.send(mode=1, courier=3).status_code, 400)
        self.assertEqual(self.send(mode=1, courier=3, other_courier='Blue Dart').status_code, 201)

    def test_only_an_approved_report_can_be_dispatched(self):
        self.assertEqual(self.send(reports=[str(uuid.uuid4())]).status_code, 400)
        self.assertEqual(self.send(reports=[]).status_code, 400)            # nothing to send

    def test_creation_is_retry_safe(self):
        op = uuid.uuid4()
        self.send(operation_id=op)
        self.assertTrue(self.send(operation_id=op).json()['replayed'])
        self.assertEqual(m.Dispatch.objects.count(), 1)

    def test_a_reports_dispatch_history(self):
        self.send()
        history = self.client.get(f'/api/dispatch/reports/{self.v}/').json()
        self.assertEqual(len(history['dispatches']), 1)

    def test_dispatch_is_a_head_office_function(self):
        from apps.valuations.test_forms import user_with_role
        self.client.force_login(user_with_role('157', m.Employee.objects.create(name='Assessor')))
        self.assertEqual(self.client.get('/api/dispatch/awaiting/').status_code, 404)
