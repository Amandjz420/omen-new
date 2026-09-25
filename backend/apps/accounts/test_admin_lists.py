"""Exercise every configured search/filter, plus real transaction list rendering."""
import json
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.common.admin_options import LAYOUTS
from target_core import models as m


class AdminListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('list-review', password='test-password')
        cls.office = m.ClientOffice.objects.create(name='Review Bank Office')
        cls.employee = m.Employee.objects.create(name='Review Assessor')
        cls.lead = m.Lead.objects.create(number='L-REVIEW-001', office=cls.office,
                                       assigned_employee=cls.employee, legacy_status='2')
        cls.service = m.ServiceType.objects.create(name='Review Service')
        cls.borrower = m.Borrower.objects.create(name='Review Borrower', lead=cls.lead)
        cls.case = m.Case.objects.create(lead=cls.lead, borrower=cls.borrower, service=cls.service)
        cls.valuation = m.Valuation.objects.create(case=cls.case, report_number='R-REVIEW-001', legacy_status='Pending')
        cls.invoice = m.Invoice.objects.create(valuation=cls.valuation, number='I-REVIEW-001', billed_amount=Decimal('1180'))
        cls.question = m.Question.objects.create(text='Review question', answer_type=3)
        m.ValuationAnswer.objects.create(valuation=cls.valuation, question=cls.question, value='A' * 250)
        cls.batch = m.ImportBatch.objects.create()
        m.SourceRow.objects.create(schema='lead_mngt', table='lead', key='review-key', batch=cls.batch,
                                   outcome='quarantined', payload={'review': 'payload-not-a-list-column'})

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_model_has_a_valid_renderable_searchable_filterable_list(self):
        models = list(apps.get_app_config('target_core').get_models())
        self.assertEqual({model.__name__ for model in models}, set(LAYOUTS))
        factory = RequestFactory()
        for model in models:
            with self.subTest(model=model.__name__):
                registered = admin.site._registry[model]
                url = reverse(f'admin:target_core_{model._meta.model_name}_changelist')
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                # Build filter specs and validate search lookup paths against the DB.
                response = self.client.get(url, {'q': 'review'})
                self.assertEqual(response.status_code, 200)
                request = factory.get(url); request.user = self.user
                qs, _ = registered.get_search_results(request, registered.get_queryset(request), 'review')
                list(qs[:1])

    def test_lead_columns_show_business_values_and_filter_status(self):
        url = reverse('admin:target_core_lead_changelist')
        response = self.client.get(url, {'q': 'Review Assessor'})
        for text in ('L-REVIEW-001', 'Review Bank Office', 'Review Assessor', 'In process'):
            self.assertContains(response, text)
        self.assertEqual(response.context['cl'].result_count, 1)
        self.assertEqual(self.client.get(url, {'legacy_status': '3'}).context['cl'].result_count, 0)

    def test_invoice_search_follows_report_and_borrower(self):
        url = reverse('admin:target_core_invoice_changelist')
        for search in ('R-REVIEW-001', 'Review Borrower'):
            response = self.client.get(url, {'q': search})
            self.assertEqual(response.context['cl'].result_count, 1)
            self.assertContains(response, 'I-REVIEW-001')

    def test_source_filters_and_exact_key_search(self):
        response = self.client.get(reverse('admin:target_core_sourcerow_changelist'),
                                   {'schema': 'lead_mngt', 'table': 'lead', 'outcome': 'quarantined', 'q': 'review-key'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cl'].result_count, 1)
        self.assertNotContains(response, 'payload-not-a-list-column')

    def test_related_column_rendering_does_not_query_per_row(self):
        m.ValuationAnswer.objects.create(valuation=self.valuation, question=self.question, value='Second')
        model_admin = admin.site._registry[m.ValuationAnswer]
        request = RequestFactory().get('/admin/'); request.user = self.user
        with CaptureQueriesContext(connection) as captured:
            for obj in model_admin.get_queryset(request):
                for column in model_admin.list_display:
                    column(obj)
        self.assertEqual(len(captured), 1)

    def test_evidence_permissions_and_sensitive_hash_exclusion(self):
        request = RequestFactory().get('/admin/'); request.user = self.user
        for model in (m.SourceRow, m.SourceIdentity, m.IntakeAudit, m.LegacyAccount):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))
        self.assertNotIn('issued_password_hash', admin.site._registry[m.LegacyAccount].get_form(request).base_fields)

    def test_relationship_autocomplete_uses_names_and_respects_permissions(self):
        url = reverse('admin:autocomplete')
        params = {'app_label': 'target_core', 'model_name': 'lead', 'field_name': 'office', 'term': 'Review Bank'}
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'][0]['id'], str(self.office.pk))
        self.assertIn('Review Bank Office', response.json()['results'][0]['text'])
        from django.contrib.auth.models import Permission
        user = User.objects.create_user('lead-only', is_staff=True)
        user.user_permissions.add(Permission.objects.get(content_type__app_label='target_core', codename='view_lead'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(url, params).status_code, 403)
