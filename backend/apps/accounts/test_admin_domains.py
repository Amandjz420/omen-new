from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from apps.common.admin_site import DOMAINS


class AdminDomainNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('domain-review', password='test-only-password')
        self.client.force_login(self.user)

    def test_home_renders_each_domain_and_preserves_model_links(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        groups = response.context['app_list']
        self.assertEqual([g['app_label'] for g in groups if g['app_label'].startswith('omen_')],
                         [f'omen_{domain}' for domain in DOMAINS])
        entries = [entry for group in groups for entry in group['models']]
        self.assertEqual(len(entries), len(admin.site._registry))
        self.assertEqual(len({entry['model'] for entry in entries}), len(entries))
        self.assertContains(response, 'Lead management')
        self.assertContains(response, reverse('admin:target_core_lead_changelist'))

    def test_domain_page_and_sidebar_work_without_changing_model_urls(self):
        response = self.client.get(reverse('admin:domain_index', args=['leads']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([g['app_label'] for g in response.context['app_list']], ['omen_leads'])
        response = self.client.get(reverse('admin:target_core_lead_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin:domain_index', args=['billing']))
        self.assertEqual(self.client.get('/admin/domains/unknown/').status_code, 404)
        self.assertEqual(self.client.get('/admin/target_core/').status_code, 200)

    def test_only_permitted_models_and_domains_are_shown(self):
        user = User.objects.create_user('limited-domain', is_staff=True)
        user.user_permissions.add(Permission.objects.get(content_type__app_label='target_core', codename='view_lead'))
        self.client.force_login(user)
        response = self.client.get(reverse('admin:index'))
        groups = response.context['app_list']
        self.assertEqual([g['app_label'] for g in groups], ['omen_leads'])
        self.assertEqual([e['object_name'] for e in groups[0]['models']], ['Lead'])
        self.assertFalse(groups[0]['models'][0]['perms']['add'])
        self.assertEqual(self.client.get('/admin/domains/billing/').status_code, 404)

    def test_anonymous_domain_access_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get('/admin/domains/leads/').status_code, 302)
