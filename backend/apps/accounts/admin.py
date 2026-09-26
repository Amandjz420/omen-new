from apps.common.admin import register_models
from . import models

register_models(getattr(models, name) for name in models.__all__)


# The admin site's password page is where RequirePasswordChange sends an admin user
# to complete onboarding, but a successful change there never cleared the
# requirement, so the user was sent back to it indefinitely (review R4). That page
# is always the signed-in user changing their own password, with their current one;
# resetting someone else's is a separate page (auth/user/<id>/password/), which
# deliberately does not complete that person's onboarding. A successful change
# redirects, so onboarding is completed on the redirect.
from django.contrib import admin as _admin

from apps.accounts.api import complete_onboarding

_change_own_password = _admin.site.password_change


def change_own_password(request, extra_context=None):
    response = _change_own_password(request, extra_context)
    if request.method == 'POST' and response.status_code == 302 and request.user.is_authenticated:
        complete_onboarding(request.user)
    return response


_admin.site.password_change = change_own_password
