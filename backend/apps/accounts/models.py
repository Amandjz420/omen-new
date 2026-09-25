"""accounts model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class LegacyProject(NamedEntity):
    """uam_user.project: the applications sharing the legacy sign-on server."""
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class RoleDefinition(NamedEntity):
    """uam_user.usertype. A legacy job title, preserved for audit. Mapping these
    onto the new business roles is a separate reviewed decision."""
    project = models.ForeignKey('target_core.LegacyProject', null=True, on_delete=models.PROTECT)
    code = models.CharField(max_length=20, blank=True)
    name_hindi = models.CharField(max_length=500, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class LegacyAccount(NamedEntity):
    """uam_user.userdetail. Credentials are deliberately not imported: the legacy
    representation is not a Django-compatible hash and sits beside an
    old_password column suggesting reversible storage."""
    login_id = models.CharField(max_length=50, blank=True, db_index=True)
    email = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=12, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    # The legacy application treats userdetail.user_id and employee.emp_id as the
    # same number. That holds for 49 of 51 accounts, and on all 49 the names agree
    # as well, so the link is recorded where it resolves and left unset otherwise.
    employee = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT, related_name='legacy_accounts')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.PROTECT, related_name='legacy_account')
    # Set when two legacy accounts are the same person. The duplicate keeps its
    # own record and its role grants, but provisions no second Django account.
    merged_into = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='merged_accounts')
    merge_reason = models.CharField(max_length=300, blank=True)
    must_change_password = models.BooleanField(default=True)
    # The hash of the password this account was issued. Onboarding is complete
    # once the stored hash differs, whoever changed it and wherever from.
    issued_password_hash = models.CharField(max_length=128, blank=True, editable=False)
    provisioned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "target_core"


class RoleAssignment(Entity):
    """uam_user.userdetail_per: which role a legacy account held, in which project."""
    account = models.ForeignKey('target_core.LegacyAccount', on_delete=models.PROTECT, related_name='role_assignments')
    role = models.ForeignKey('target_core.RoleDefinition', null=True, on_delete=models.PROTECT)
    project = models.ForeignKey('target_core.LegacyProject', null=True, on_delete=models.PROTECT)
    legacy_role_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)
    remark = models.CharField(max_length=250, blank=True)
    # Recorded, never enforced. See the module note above.
    scope_region = models.CharField(max_length=10, blank=True)
    scope_circle = models.CharField(max_length=10, blank=True)
    scope_division = models.CharField(max_length=10, blank=True)
    scope_subdivision = models.CharField(max_length=10, blank=True)

    class Meta:
        app_label = "target_core"


class LoginEvent(Entity):
    """uam_user.login_history. Historical evidence only; never a live session."""
    account = models.ForeignKey('target_core.LegacyAccount', null=True, on_delete=models.PROTECT, related_name='login_events')
    # Source columns are datetimes. Every retained login timestamp and almost
    # every logout timestamp has a non-midnight time, so dates cannot represent
    # session ordering or duration.
    login_at = models.DateTimeField(null=True, db_index=True)
    logout_at = models.DateTimeField(null=True)
    ip_address = models.CharField(max_length=100, blank=True)
    mac_address = models.CharField(max_length=100, blank=True)
    login_action = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['LegacyProject', 'RoleDefinition', 'LegacyAccount', 'RoleAssignment', 'LoginEvent']
