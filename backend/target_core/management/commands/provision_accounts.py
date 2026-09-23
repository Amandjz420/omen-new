"""Provision and reconcile Django accounts from the frozen legacy identity.

Separate from the data importer on purpose: the importer records what the legacy
system contained, this decides who may sign in. Idempotent.

The whole plan is computed before anything is written, and the same computation
backs both the dry run and the real run, so a preview cannot disagree with what
actually happens. Any account whose identity bindings do not resolve cleanly is
reported as a conflict and provisions nothing; a partial binding is never left
behind.

Decisions encoded, all reviewed rather than inferred:
  * Legacy credentials are never imported. Each account is issued its own login
    id as an initial password and flagged must_change_password; the API refuses
    everything but password setup and sign-out until that is changed.
  * Provisioned accounts receive NO business access. is_staff stays false until a
    business permission policy exists; the admin-site flag is not a role system.
  * A legacy Administrator or CEO role never becomes is_superuser.
  * Region and circle are recorded but are not access restrictions.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F as models_F
from django.utils import timezone

from target_core import models as m

LEAD_PROJECT = 'LEAD'

# Reviewed identity merges, keyed by login id. Confirmed with the data owner.
MERGES = {'9907360751': ('9826056729', 'Confirmed same person; duplicate legacy account, grants carried to the canonical account')}

# Approved adoptions of a pre-existing Django username by a legacy account.
# Empty by design: an unreviewed username collision is a conflict, never a match.
ADOPTIONS = {}


class Command(BaseCommand):
    help = 'Provision and reconcile Django accounts from imported legacy identity.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def canonical_of(self, account, by_login):
        """Follow the merge chain to its end, refusing cycles and dead ends."""
        seen, current = [account.login_id], account
        while current.login_id in MERGES:
            target = by_login.get(MERGES[current.login_id][0])
            if target is None:
                return None, f'merge target {MERGES[current.login_id][0]} not found'
            if target.login_id in seen:
                return None, f'merge cycle: {" -> ".join(seen + [target.login_id])}'
            seen.append(target.login_id)
            current = target
        return current, None

    def eligible_grants(self):
        """A grant only qualifies with a real, enabled role in its own project."""
        return (m.RoleAssignment.objects
                .filter(project__name=LEAD_PROJECT, legacy_status='1', legacy_deleted='0',
                        role__isnull=False, role__legacy_deleted='0', role__legacy_status='1')
                .exclude(role__project_id=None)
                .filter(role__project_id=models_F('project_id')))

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        dry = options['dry_run']
        accounts = list(m.LegacyAccount.objects.select_related('employee', 'user').order_by('login_id'))
        by_login = {a.login_id: a for a in accounts}
        conflicts, notes = [], {'merged': 0, 'created': 0, 'linked': 0, 'unchanged': 0,
                                'not_eligible': 0, 'revoked': 0, 'reactivated': 0, 'access_withdrawn': 0}

        # --- plan: merge graph first, then eligibility computed from it ---------
        canonical, merged_from = {}, {}
        for account in accounts:
            target, problem = self.canonical_of(account, by_login)
            if problem:
                conflicts.append(f'{account.login_id}: {problem}')
                continue
            canonical[account.login_id] = target
            if target.login_id != account.login_id:
                merged_from.setdefault(target.login_id, []).append(account)
                notes['merged'] += 1

        direct = set(self.eligible_grants().values_list('account__login_id', flat=True))
        eligible = set()
        for login, target in canonical.items():
            if login in direct:
                eligible.add(target.login_id)

        # --- apply -------------------------------------------------------------
        for account in accounts:
            target = canonical.get(account.login_id)
            if target is None or target.login_id != account.login_id:
                if target is not None and not dry:
                    reason = MERGES[account.login_id][1]
                    if account.merged_into_id != target.id or account.merge_reason != reason:
                        account.merged_into, account.merge_reason = target, reason
                        account.save(update_fields=['merged_into', 'merge_reason'])
                continue

            if account.login_id not in eligible:
                notes['not_eligible'] += 1
                if account.user_id and account.user.is_active:
                    # The authoritative grant is gone; provisioned access must not survive it.
                    notes['revoked'] += 1
                    if not dry:
                        account.user.is_active = False
                        account.user.save(update_fields=['is_active'])
                continue

            if account.employee is None:
                conflicts.append(f'{account.login_id}: eligible for LEAD but no employee link; not provisioned')
                continue

            existing = User.objects.filter(username=account.login_id).first()
            if existing is not None and account.user_id != existing.pk and account.login_id not in ADOPTIONS:
                conflicts.append(f'{account.login_id}: a Django user of that name already exists; '
                                 f'unreviewed adoption refused')
                continue
            employee_user = account.employee.user
            if employee_user is not None and existing is not None and employee_user.pk != existing.pk:
                conflicts.append(f'{account.login_id}: employee already linked to a different account; '
                                 f'left untouched')
                continue
            if employee_user is not None and existing is None:
                conflicts.append(f'{account.login_id}: employee already linked to another account; '
                                 f'refusing to create a second identity')
                continue

            active = account.legacy_status == '1'
            if existing is None:
                notes['created'] += 1
                if dry:
                    continue
                user = User(username=account.login_id, first_name=(account.name or '')[:150],
                            email=account.email or '', is_active=active,
                            # No business access. See the module docstring.
                            is_staff=False, is_superuser=False)
                user.set_password(account.login_id)
                user.save()
            else:
                user = existing
                notes['unchanged'] += 1
                changed = []
                if user.is_active != active:
                    notes['reactivated' if active else 'revoked'] += 1
                    user.is_active = active
                    changed.append('is_active')
                # Accounts provisioned before this policy carried the admin-site
                # flag, which the preview API treats as business access. Withdraw
                # it until a real permission policy exists.
                if user.is_staff or user.is_superuser:
                    notes['access_withdrawn'] += 1
                    user.is_staff = user.is_superuser = False
                    changed += ['is_staff', 'is_superuser']
                if changed and not dry:
                    user.save(update_fields=changed)

            if dry:
                continue
            if account.user_id != user.pk:
                account.user = user
                account.provisioned_at = account.provisioned_at or timezone.now()
                account.save(update_fields=['user', 'provisioned_at'])
            if account.employee.user_id != user.pk:
                account.employee.user = user
                account.employee.save(update_fields=['user'])
                notes['linked'] += 1

        for key in ('merged', 'created', 'unchanged', 'linked', 'not_eligible', 'revoked', 'reactivated', 'access_withdrawn'):
            self.stdout.write(f'{key:18s} {notes[key]}')
        for line in conflicts:
            self.stdout.write(self.style.ERROR(f'conflict: {line}'))
        if dry:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('dry run: rolled back'))
