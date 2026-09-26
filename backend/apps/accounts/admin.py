from apps.common.admin import register_models
from . import models

register_models(getattr(models, name) for name in models.__all__)


# The admin site's own-password page is where RequirePasswordChange sends an admin
# user to complete onboarding. It is rebuilt here as Django builds it, with one
# difference: its form refuses the password the user already has. Django's form
# accepts a new password equal to the current one, so the issued password could be
# "changed" to itself and onboarding completed without a new password being chosen
# (review N1). The rule matches the password endpoint. Onboarding completes only
# after a genuinely new password is saved. Resetting another user's password is a
# separate page and does not complete that person's onboarding.
from django import forms
from django.contrib import admin as _admin
from django.contrib.admin.forms import AdminPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse

from apps.accounts.api import complete_onboarding


class OwnPasswordChangeForm(AdminPasswordChangeForm):
    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password1')
        if new and self.user.check_password(new):
            # On the field: the admin's password template shows field errors only, so a
            # form-wide error would say "correct the error below" and not say which.
            self.add_error('new_password1', forms.ValidationError('Choose a password you have not used here before.',
                                                                  code='password_reused'))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            complete_onboarding(user)
        return user


def change_own_password(request, extra_context=None):
    site = _admin.site
    defaults = {'form_class': OwnPasswordChangeForm,
                'success_url': reverse('admin:password_change_done', current_app=site.name),
                'extra_context': {**site.each_context(request), **(extra_context or {})}}
    if site.password_change_template is not None:
        defaults['template_name'] = site.password_change_template
    request.current_app = site.name
    return PasswordChangeView.as_view(**defaults)(request)


_admin.site.password_change = change_own_password
