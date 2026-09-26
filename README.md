# OMEN — Django + React migration

The local application now supports **lead intake** alongside imported history. Business roles are deferred at the owner's request; the current application remains restricted to the existing staff/admin accounts.

See [lead intake implementation and API contract](migration-required/app-reference/LEAD_INTAKE_IMPLEMENTATION.md) for behavior, migration protection, validation and remaining scope. This is a working local migration phase, not whole-system parity or production cutover.

## What works

- Session login, CSRF protection and required first-login password change.
- Office and lead search, imported cases, notes and reconciliation overview.
- Client office/contact creation and editing.
- Numbered lead creation, employee assignment and received-date entry.
- Requested services, borrowers, asset cases, follow-ups and reasoned cancellation.
- Audit records for intake writes and protection of locally edited records during source refreshes.
- Direct, one-way read-only MySQL source import into the managed Django target.

Work-order generation, valuation execution/review, report output, finance workflows, dispatch, MIS parity, file retrieval and business roles remain future work. Historical attendance is excluded.

## Run locally

Backend:

```sh
cd "/Users/aman/Desktop/OMEN Source Code/omen-next/backend"
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Frontend, in another terminal:

```sh
cd "/Users/aman/Desktop/OMEN Source Code/omen-next/frontend"
npm run dev
```

Open http://127.0.0.1:5173. Sign in with an existing admin account, complete password setup when requested, then choose **New lead / client**. Reopen a saved lead through **Leads**. The Data Atlas at port 4173 is a separate application.

The shared local accounts were configured deliberately. Their initial credentials are stored privately under `database/.local/`, never in this README. Do not rerun setup with `--rotate` unless you intend to reset their passwords. Imported employee accounts are not granted business access automatically.

For a fresh environment, install `backend/requirements.txt` into a Python virtual environment, run migrations, create a local administrator with `manage.py createsuperuser`, and run `npm ci` in frontend. Python 3.12 and Node 22 were used for this workspace. The new database will be empty until imported.

## Database and refresh

`backend/target.sqlite3` is the active local target. Both `config.settings` and `config.target` use the same model set and API. The ordinary application does not need MySQL access.

The source is the locally restored dump, configured privately in `database/.local/connection.json`. No production source access is needed.

From backend:

```sh
.venv/bin/python manage.py sync_legacy --settings=config.full_database --dry-run --report ../database/new-dry-run.json
.venv/bin/python manage.py sync_legacy --settings=config.full_database --report ../database/new-import.json
```

Review the dry-run report before committing a new import. Preserve production/UAT boundaries. Imported source identities remain stable; unresolved rows are retained in staging. Credentials are excluded from staged identity payloads.

Locally edited offices, contacts and leads are marked as locally managed: later source changes are retained in staging rather than overwriting those target records. New local records and follow-ups survive imports. This is whole-record ownership, not an automatic per-field merge; see the implementation guide before reconciliation or cutover.

The old Excel/JSON prototype and its importer are archived. They are not the current migration path.

## Validation

```sh
cd backend
.venv/bin/python manage.py test
.venv/bin/python manage.py test --settings=config.target
.venv/bin/python manage.py makemigrations --check --dry-run
cd ../frontend
npm run build
```

At the lead-intake checkpoint, 72 tests pass under both settings; browser verification used synthetic data in a disposable database. The recorded 68-table source repeat covers 2,623,601 rows with zero inserts/updates. This report does not imply that every business workflow has been implemented.

## Documentation

- [Current lead intake implementation](migration-required/app-reference/LEAD_INTAKE_IMPLEMENTATION.md)
- [Migration method](migration-required/data-migration/MIGRATION_METHOD.md)
- [Legacy lead flow inventory](migration-required/data-migration/LEAD_FLOW_INVENTORY.md)
- [Legacy-to-Django flow audit](migration-required/data-migration/LEAD_FLOW_MIGRATION_AUDIT.md)
- [User/employee and role design proposal](migration-required/app-reference/USER_ROLES_AND_EMPLOYEE_DESIGN.md)
- [Identity review findings](migration-required/reviews/REVIEW_CLAUDE_IDENTITY_2026-09-17.md)
- [Business entities and source disposition](migration-required/data-migration/BUSINESS_ENTITIES.md)
- [Validation history](migration-required/handoff/VALIDATION.md)
- [Handoff history](migration-required/handoff/HANDOFF.md)

Older reports describe their dated checkpoints and must not override the current implementation guide. SQL dumps, SQLite databases, credentials and salary/contact payloads must not be committed or included in general-purpose handoffs.

## Code organization

The backend is organized into business apps under `backend/apps/`. See [the Django architecture guide](migration-required/app-reference/DJANGO_APP_ARCHITECTURE.md) for model ownership, workflow locations, domain tests and migration compatibility. Existing database labels and API URLs are preserved.

## Migration material

Documents, reviews, mapping data, tools and import reports from the migration are in
[`migration-required/`](migration-required/README.md). None of it is needed for the
application to run.
