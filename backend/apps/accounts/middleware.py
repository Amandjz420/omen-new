"""Enforce first-login password setup everywhere, not only on the JSON API.

The API guard in views.py covers /api/. The admin site is a second front door to
the same data, so the same restriction has to apply there or the requirement is
trivially bypassed by signing into /admin/ instead.
"""
from django.shortcuts import redirect

from apps.accounts.api import onboarding_pending

# Reachable while a password change is outstanding.
PERMITTED = ('/admin/password_change/', '/admin/logout/', '/admin/jsi18n/',
             '/api/password/', '/api/logout/', '/api/session/', '/static/')


class RequirePasswordChange:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (user is not None and user.is_authenticated
                and request.path.startswith('/admin/')
                and not request.path.startswith(PERMITTED)
                and onboarding_pending(user)):
            return redirect('admin:password_change')
        return self.get_response(request)
