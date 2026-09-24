# Validation evidence

## Current checkpoint — 24 September 2026

Lead intake is now implemented behind the existing admin/staff gate; business roles are deferred by the owner. See [the current implementation report](database/LEAD_INTAKE_IMPLEMENTATION.md) for APIs, source rules, limitations and evidence. Migration 0009 is applied locally after a consistent database backup. All 72 tests pass under both settings; frontend build and migration-drift checks pass. A disposable-database browser test covered office/contact creation, lead numbering and assignment, services, borrowers, cases and follow-ups. Existing target lead, case, office, contact and account counts were preserved.

The sections below record the earlier identity-import checkpoint. Its source import totals remain relevant, but its test count and operational scope are historical.

Last updated 17 September 2026, after closing the identity review findings R1-R8.

## Scope imported

Nine business modules — crm, services, workorders, reference, leads, documents,
billing, valuations, organization — plus LEAD identity. 68 source tables from
`lead_mngt` and `uam_user`. PRAYAS and PAYROLL are out of scope by decision:
they continue to run against the legacy UAM, which this migration does not
change. Attendance, messaging, reports, leave, HR and all UAT schemas remain
excluded.

| Measure | Value |
|---|---|
| Source tables | 68 |
| Source rows read | 2,623,601 |
| Accepted into target | 2,623,392 (99.992%) |
| Quarantined | 209 |
| Imported with issues | 11,966 |
| SourceRow payloads retained | 2,623,601 (every row, including rejects) |

## Identity

23 Django accounts provisioned from 24 active LEAD grants (two legacy accounts
are one reviewed person). 51 legacy accounts, 35 role definitions, 114 historical
grants and 74,164 login events are retained as evidence.

- **No credential value is imported at any stage.** The source reader drops
  `password`, `old_password`, `pin_no`, `session_id` and related columns before
  payloads or fingerprints are built, and payload construction filters them
  again. Staging written before this fix was remediated: 74,215 payloads
  sanitized, zero credentials remain. The source database and dump were not
  altered.
- **Provisioned accounts hold no business access.** `is_staff` is false and
  `is_superuser` is never set. The admin-site flag is not used as a role system;
  a business permission policy is still outstanding.
- **Onboarding is enforced server-side.** An account issued an initial password
  reaches only password setup and sign-out, for new and existing sessions alike.
  Chosen passwords are validated in full.
- **Revocation is reconciled.** Disabling a legacy account or withdrawing its
  LEAD grant deactivates the Django account on the next run.
- Region and circle are recorded but are **not** access restrictions, by decision.

## Checks performed

- **Fresh 68-table repeat import proposes 0 inserts and 0 updates**
  (`database/target-repeat-68.json`), run after all importer changes.
- 54 tests pass under both `config.settings` and `config.target`.
  `makemigrations --check` reports no drift. Frontend production build passes.
- Every quarantine traced to a dangling legacy foreign key.
- 11,896 of 12,650 valuations carry assessed values; 150 of 153 scrutiny
  requirements resolve to a report usage.
- Login timestamps retain time of day: 74,164 events, none truncated.

## What these numbers do not establish

- Acceptance is not semantic correctness. 11,966 rows carry issues.
- Document **metadata** is migrated; no file bytes were copied or verified.
- Valuation answers are preserved in EAV form. Report rendering parity against
  the legacy output has not been demonstrated.
- No business permission policy exists yet, so no account can do business work.
- No browser-based user acceptance testing. No PostgreSQL or deployment testing.
- No operational write API beyond lead notes and password change.

## Operational note

Personal accounts are issued their own login id as an initial password and must
change it at first sign-in.

The shared generic logins `superadmin` and `admin` are carved out of that rule,
because their usernames are published in the legacy application. `manage.py
setup_admin_accounts` issues each a generated 24-character password, writes it
once to `database/.local/admin-credentials.txt` (mode 600, gitignored) and still
requires a change at first sign-in. Passwords are never printed or committed.
`superadmin` holds `is_superuser`; `admin` holds staff access only. Provisioning
never issues these two a login-id password and never withdraws their access.

Read that file, sign in, change both passwords, then delete it.
