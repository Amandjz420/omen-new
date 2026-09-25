"""Give the shared administrative logins real credentials.

`superadmin` and `admin` are shared generic accounts, not personal identities.
The username-as-password rule agreed for personal accounts is unsafe for these:
their usernames are published in the legacy application, so the password would be
public knowledge, and they are the two accounts that carry the most authority.

This command issues each a generated password, writes it once to a gitignored
local file readable only by its owner, and requires a change at first sign-in.
Passwords are never printed to the console or committed.
"""
import os
import secrets
import string
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from target_core.models import LegacyAccount

ACCOUNTS = {'superadmin': {'is_staff': True, 'is_superuser': True},
            'admin': {'is_staff': True, 'is_superuser': False}}
ALPHABET = string.ascii_letters + string.digits + '!@#$%^&*-_=+'
# backend/.local-secret is Django's SECRET_KEY file, not a directory. Credentials
# go beside the MySQL connection file, which is already gitignored.
from django.conf import settings

SECRET_DIR = settings.BASE_DIR.parent / 'database' / '.local'


class Command(BaseCommand):
    help = 'Issue credentials for the shared administrative accounts.'

    def add_arguments(self, parser):
        parser.add_argument('--rotate', action='store_true',
                            help='Reissue passwords even if the accounts are already set up.')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        issued, skipped = {}, []
        for username, flags in ACCOUNTS.items():
            account = LegacyAccount.objects.filter(login_id=username).first()
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User(username=username, first_name=account.name if account else username,
                            is_active=True)
            # A password equal to the username counts as unset: it is the very
            # thing this command exists to replace.
            already_safe = (user.pk is not None and user.has_usable_password()
                            and not user.check_password(username))
            if already_safe and not options['rotate']:
                skipped.append(username)
                continue
            password = ''.join(secrets.choice(ALPHABET) for _ in range(24))
            user.set_password(password)
            user.is_active = True
            user.is_staff = flags['is_staff']
            user.is_superuser = flags['is_superuser']
            user.save()
            issued[username] = password
            if account is not None:
                # Still forced to change at first sign-in: a generated password is
                # strong but nobody has chosen it.
                account.must_change_password = True
                account.issued_password_hash = user.password
                account.user = user
                account.provisioned_at = account.provisioned_at or timezone.now()
                account.save(update_fields=['must_change_password', 'issued_password_hash',
                                            'user', 'provisioned_at'])

        # `admin` is staff but not a superuser, so without explicit permissions the
        # admin site would show it nothing. Grant the target_core models through a
        # group, which keeps the grant visible and revocable.
        group, _ = Group.objects.get_or_create(name='OMEN administrators')
        group.permissions.set(Permission.objects.filter(content_type__app_label='target_core'))
        for username in ACCOUNTS:
            user = User.objects.filter(username=username).first()
            if user is not None and not user.is_superuser:
                user.groups.add(group)

        for username in skipped:
            self.stdout.write(f'{username}: already has a usable password; use --rotate to reissue')

        if issued:
            SECRET_DIR.mkdir(parents=True, exist_ok=True)
            path = SECRET_DIR / 'admin-credentials.txt'
            lines = [f'Issued {timezone.now().isoformat(timespec="seconds")}',
                     'Change these at first sign-in. Delete this file afterwards.', '']
            lines += [f'{name}\t{value}' for name, value in issued.items()]
            path.write_text('\n'.join(lines) + '\n')
            os.chmod(path, 0o600)
            self.stdout.write(self.style.SUCCESS(f'issued {len(issued)} password(s) -> {path}'))
            self.stdout.write('passwords were not printed; read the file, then delete it')
