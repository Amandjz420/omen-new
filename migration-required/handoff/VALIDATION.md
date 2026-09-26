# Validation evidence

## Current checkpoint — business-app refactor, 25 September 2026

Admin list follow-up: all 83 models have reviewed columns, related-field search,
business filters and ordering. Sixteen focused tests pass on both SQLite and
PostgreSQL, including rendering/searching every model list, filter behavior,
related-column query counts, domain navigation and autocomplete permissions.
System checks and migration-drift checks pass. The existing receipt migration
0020 was confirmed applied on the local database; this admin change applied no
migration. See [the admin table guide](../app-reference/DJANGO_ADMIN_TABLE_GUIDE.md).

Admin navigation follow-up: the home page and sidebar now display business-domain
groups. Nine focused admin/architecture tests pass on SQLite, covering domain
landing pages, existing model URLs, unknown domains, anonymous access and a
view-only user seeing only their permitted model. Schema drift remains zero.
This UI grouping does not change the earlier business permissions or workflow policy.

The backend model definitions and workflows are organized under `backend/apps/`.
See [the architecture guide](../app-reference/DJANGO_APP_ARCHITECTURE.md). This checkpoint
validates structural compatibility, not resolution of the separately reported
business-workflow defects.

- **265 tests pass on PostgreSQL under `config.settings`; 265 pass under `config.target`.**
- All 83 model definitions match the pre-refactor field, relationship, constraint,
  table and persistent-label contract. All 54 API patterns remain present once.
- Django system checks and `makemigrations --check --dry-run` pass with no drift.
- Existing migration files, including the pre-existing uncommitted receipt migration
  0020, are byte-for-byte unchanged. No application-data migration or import was run.
- Compatibility tests cover model/admin identity, management-command discovery,
  credential output location and the bundled PDF letterhead. Domain tests include
  the existing import/reimport, auth, lead, valuation, report and finance checks.
- The React source and API URLs did not change. No additional browser acceptance
  or production cutover was performed for this refactor.

The dated checkpoints below are historical and should not be read as the current
feature inventory. See the [expanded gap review](../reviews/MIGRATION_GAP_REVIEW_2026-09-25.md)
for outstanding business functionality and defects.

## Historical checkpoint — 24 September 2026

Lead intake is now implemented behind the existing admin/staff gate; business roles are deferred by the owner. See [the current implementation report](../app-reference/LEAD_INTAKE_IMPLEMENTATION.md) for APIs, source rules, limitations and evidence. Migration 0009 is applied locally after a consistent database backup. All 72 tests pass under both settings; frontend build and migration-drift checks pass. A disposable-database browser test covered office/contact creation, lead numbering and assignment, services, borrowers, cases and follow-ups. Existing target lead, case, office, contact and account counts were preserved.

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
| Source tables | 73 |
| Source rows read | 2,641,787 |
| Accepted into target | 2,641,578 (99.992%) |
| Quarantined | 209 |
| Imported with issues | 11,970 |
| SourceRow payloads retained | 2,641,787 (every row, including rejects) |

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

- **Fresh 73-table repeat import proposes 0 inserts and 0 updates**
  (`migration-required/import-runs/repeat-proofs/target-repeat-73.json`), run against PostgreSQL.
- 90 tests pass, on PostgreSQL, under both `config.settings` and `config.target`.
  `makemigrations --check` reports no drift. Frontend production build passes.
- Every quarantine traced to a dangling legacy foreign key.
- 11,896 of 12,650 valuations carry assessed values; 150 of 153 scrutiny
  requirements resolve to a report usage.
- Login timestamps retain time of day: 74,164 events, none truncated.

## Bank report templates and dispatch

All 53 `lead_mngt` tables are now accounted for: 48 imported, 5 old backups
deliberately excluded (`report_question_backup*`, `report_setup_backup*`).

- **Templates** — `report_setup` (209), `bank_report_heading` (478) and
  `report_question` (4,785) import with every reference resolving except 3
  subtypes and 1 bank on `report_setup`. Those templates are kept with the link
  unset, because a lost template line would silently alter every report built
  from it.
- **Dispatch** (7,545) carries no foreign key. Its reports are listed as
  comma-separated report numbers in `nature_of_docs`, which the legacy controller
  joins to `valuation.report_no`. `link_dispatch_items` reproduces that join:
  10,752 references, 10,037 (93.35%) linked to a valuation, 17 of them after
  correcting a missing hyphen, space or `R-` prefix; 5 are lead numbers keyed
  into the report field; 710 name no valuation and are kept as unresolved.
  `report_no` is unique, so no reference is ambiguous. The unresolved share is
  spread evenly across 2021-2026, so it is not an old purge.
- **SMS** (5,169) is the notification history the dispatch controller produced.
  It runs from August 2023 to August 2024 and then stops. No row is flagged as a
  one-time password.

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
