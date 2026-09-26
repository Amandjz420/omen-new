"""Review finding G8: a password-hash upgrade is not a password change."""
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.contrib.auth.models import User
from django.test import TestCase

from target_core import models as m

ISSUED = 'Issued-Password-2026!'


class OnboardingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('asha', is_staff=True)
        # An older hash: fewer PBKDF2 iterations than Django now uses, so signing in
        # makes Django rewrite the stored hash for the same password.
        self.user.password = PBKDF2PasswordHasher().encode(ISSUED, 'legacysalt', iterations=1000)
        self.user.save()
        m.LegacyAccount.objects.create(name='Asha', login_id='asha', user=self.user, legacy_status='1',
                                       must_change_password=True, issued_password_hash=self.user.password)

    def login(self, password=ISSUED):
        return self.client.post('/api/login/', {'username': 'asha', 'password': password}, content_type='application/json')

    def test_codex_reproduction_signing_in_with_the_issued_password_keeps_onboarding(self):
        before = self.user.password
        self.assertTrue(self.login().json()['password_change_required'])
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, before)                  # Django did upgrade the hash
        self.assertTrue(self.client.get('/api/session/').json()['password_change_required'])   # previously False

    def test_a_password_set_by_someone_else_does_not_complete_onboarding(self):
        self.user.set_password('Chosen-By-Admin-9')
        self.user.save()
        self.client.force_login(self.user)
        self.assertTrue(self.client.get('/api/session/').json()['password_change_required'])

    def test_changing_the_password_through_the_endpoint_completes_onboarding(self):
        self.login()
        response = self.client.post('/api/password/', {'current_password': ISSUED, 'new_password': 'My-Own-Choice-2026'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(self.client.get('/api/session/').json()['password_change_required'])


class AdminPasswordPageTests(TestCase):
    """Review R4: the admin's own-password page completes onboarding; a reset of
    someone else's password does not."""

    def setUp(self):
        self.user = User.objects.create_user('asha', password=ISSUED, is_staff=True)
        self.account = m.LegacyAccount.objects.create(name='Asha', login_id='asha', user=self.user, legacy_status='1',
                                                      must_change_password=True, issued_password_hash=self.user.password)

    def test_changing_your_own_password_in_admin_completes_onboarding(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get('/admin/'), '/admin/password_change/', fetch_redirect_response=False)
        response = self.client.post('/admin/password_change/', {'old_password': ISSUED, 'new_password1': 'My-Own-Admin-Choice-26',
                                                                'new_password2': 'My-Own-Admin-Choice-26'})
        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertFalse(self.account.must_change_password)                 # previously stayed True
        self.assertEqual(self.client.get('/admin/').status_code, 200)       # previously redirected again

    def test_a_failed_change_leaves_onboarding_outstanding(self):
        self.client.force_login(self.user)
        self.client.post('/admin/password_change/', {'old_password': 'wrong', 'new_password1': 'My-Own-Admin-Choice-26',
                                                     'new_password2': 'My-Own-Admin-Choice-26'})
        self.account.refresh_from_db()
        self.assertTrue(self.account.must_change_password)

    def test_another_administrators_reset_does_not_complete_onboarding(self):
        self.client.force_login(User.objects.create_superuser('root', 'r@x.test', 'Root-Password-2026!'))
        response = self.client.post(f'/admin/auth/user/{self.user.pk}/password/',
                                    {'password1': 'Set-By-Someone-Else-26', 'password2': 'Set-By-Someone-Else-26', 'usable_password': 'true'})
        self.assertEqual(response.status_code, 302, response.content[:300])
        self.account.refresh_from_db()
        self.assertTrue(self.account.must_change_password)
