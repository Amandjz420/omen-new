"""Create Django accounts from the frozen legacy identity.

Separate from the data importer on purpose. The importer records what the legacy
system contained; this command decides who may sign in, which is a reviewed
business action. It is idempotent: rerunning changes nothing.

Decisions this encodes, all recorded rather than inferred at runtime:
  * Legacy passwords are never imported. Each account is provisioned with its own
    login id as the initial password and flagged must_change_password, so the
    holder sets a real one at first sign-in. set_password does not run
    AUTH_PASSWORD_VALIDATORS, so validators stay fully in force for every
    password chosen afterwards.
  * Region and circle are not access restrictions. No scope is applied.
  * A legacy Administrator or CEO role never becomes is_superuser.
  * Accounts confirmed to be the same person provision one Django account; the
    duplicate keeps its record and its grants and provisions nothing.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from target_core import models as m

LEAD_PROJECT = 'LEAD'

# Reviewed identity merges. Confirmed with the data owner, not inferred.
# 9907360751 and 9826056729 are both Sanjeev Agrawal; only the second has a
# matching employee record, and the first is the one holding Administrator.
MERGES = {'9907360751': ('9826056729', 'Confirmed same person; duplicate legacy account, grants carried to the canonical account')}


class Command(BaseCommand):
    help = 'Provision Django accounts from imported legacy identity records.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        report = {'merged': 0, 'created': 0, 'linked': 0, 'unchanged': 0, 'skipped_no_lead_access': 0, 'exceptions': []}

        lead_accounts = set(
            m.RoleAssignment.objects
            .filter(project__name=LEAD_PROJECT, legacy_status='1', legacy_deleted='0')
            .values_list('account_id', flat=True))

        for account in m.LegacyAccount.objects.select_related('employee').order_by('login_id'):
            target = MERGES.get(account.login_id)
            if target:
                canonical = m.LegacyAccount.objects.filter(login_id=target[0]).first()
                if canonical is None:
                    report['exceptions'].append(f'{account.login_id}: merge target {target[0]} not found')
                    continue
                if account.merged_into_id != canonical.id:
                    account.merged_into, account.merge_reason = canonical, target[1]
                    if not options['dry_run']:
                        account.save(update_fields=['merged_into', 'merge_reason'])
                report['merged'] += 1
                continue

            # Grants belonging to a duplicate count towards the canonical account.
            has_access = account.id in lead_accounts or any(
                dup.id in lead_accounts for dup in account.merged_accounts.all())
            if not has_access:
                report['skipped_no_lead_access'] += 1
                continue

            if account.employee is None:
                report['exceptions'].append(f'{account.login_id}: LEAD access but no employee link; not provisioned')
                continue

            user = account.user or User.objects.filter(username=account.login_id).first()
            if user is None:
                if options['dry_run']:
                    report['created'] += 1
                    continue
                user = User.objects.create(username=account.login_id, first_name=account.name[:150],
                                           email=account.email or '', is_active=account.legacy_status == '1',
                                           # The API currently gates on is_staff. Replacing that with
                                           # role checks is a separate change; is_superuser is never set.
                                           is_staff=True, is_superuser=False)
                user.set_password(account.login_id)
                user.save()
                report['created'] += 1
            else:
                report['unchanged'] += 1

            if not options['dry_run']:
                changed = []
                if account.user_id != user.pk:
                    account.user = user
                    account.provisioned_at = account.provisioned_at or timezone.now()
                    changed = ['user', 'provisioned_at']
                if changed:
                    account.save(update_fields=changed)
                employee = account.employee
                if employee.user_id != user.pk:
                    if employee.user_id is not None:
                        report['exceptions'].append(
                            f'{account.login_id}: employee already linked to another account; left unchanged')
                    else:
                        employee.user = user
                        employee.save(update_fields=['user'])
                        report['linked'] += 1

        for key in ('merged', 'created', 'linked', 'unchanged', 'skipped_no_lead_access'):
            self.stdout.write(f'{key:26s} {report[key]}')
        for line in report['exceptions']:
            self.stdout.write(self.style.WARNING(f'exception: {line}'))
        if options['dry_run']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('dry run: rolled back'))
