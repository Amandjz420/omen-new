# OMEN — Django + React monorepo migration

**Current target work:** [Clean target status and created entities](database/CLEAN_TARGET_STATUS.md) · [Business purpose and complete 202-table coverage](database/BUSINESS_ENTITIES.md). Historical attendance is excluded; payroll and leave evidence remain in scope. The first 27 managed tables exist in a separate target database, with legacy-data imports still pending.

**Scope correction, 16 September 2026:** The full-system database baseline is now under [database/README.md](database/README.md). It contains all seven supplied schemas: 982 tables and 7,998,004 rows, with Django mappings and reconciliation evidence. The sections below describe the earlier limited SQLite/React prototype only; that prototype is not the whole-system migration and has not yet been connected to the full baseline.

This is the first runnable slice of the migration, in a new directory alongside the original Java applications. It uses Django 5.2, React 19 and Vite. A local SQLite database supports development; PostgreSQL deployment and production operations remain future work.

## What works

- Staff sign-in with Django sessions and CSRF protection.
- Searchable, paginated offices and leads; legacy status filters.
- Lead detail with commissioning office, contact and linked property cases.
- Follow-up notes stored separately from imported source data.
- Recorded-case overview by service, and latest import reconciliation.
- Atomic, repeatable import from the JSON projection used to build the Excel files. Original IDs and raw fields are preserved. Missing relationships are flagged; rows are retained. Dry runs execute the import and roll it back.

## Run on this machine

The dependencies and database have been set up locally. Create your own staff account first:

```sh
cd "/Users/aman/Desktop/OMEN Source Code/omen-next/backend"
.venv/bin/python manage.py createsuperuser
```

Run the backend in one terminal:

```sh
cd "/Users/aman/Desktop/OMEN Source Code/omen-next/backend"
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Run the frontend in another terminal:

```sh
cd "/Users/aman/Desktop/OMEN Source Code/omen-next/frontend"
npm run dev
```

Open http://127.0.0.1:5173 and sign in. There is no shared/default password. The earlier Data Atlas on port 4173 is a separate application.

## Set up on another machine

Use Python 3.12+ and Node 22.12+ (Node 22.22 was used here). In backend, create `.venv`, install `requirements.txt`, run `manage.py migrate` and `manage.py createsuperuser`. In frontend, run `npm ci`. Then follow the two start commands above.

## Import or refresh the local dataset

From backend:

```sh
.venv/bin/python manage.py import_legacy "../../outputs/01a08c3d-marketing-export/work/workbooks.json" --dry-run
.venv/bin/python manage.py import_legacy "../../outputs/01a08c3d-marketing-export/work/workbooks.json"
```

This command accepts the JSON intermediate containing sheets, columns and rows, not XLSX or arbitrary SQL. It imports the main-schema projection previously generated from the 10 September 2026 dump. For a future dump, extraction must produce the same contract with refreshed source values. The old extraction scripts contain snapshot-specific paths and dates; update/parameterize them before reusing for a new snapshot. An Excel upload UI, extraction automation, and scheduled sync are not implemented yet.

Each typed model has a unique original source ID within its fixed source-table identity. Reimport updates imported fields and foreign keys while preserving new local notes. Missing rows in later input are retained. Other exported sheets are retained in `SourceRecord` staging, unique by sheet and source ID. Staging is not completed domain migration.

The importer validates shape, required source IDs, duplicate IDs and the first-slice foreign keys. It does not yet replicate all checks from the Excel review workbook. Null links retain the unresolved source reference in `raw`. Counters for rows with issues overlap inserted/updated/unchanged; do not sum them as additional records. The entire import is one transaction; it is intended for the present local dataset, not concurrent production synchronization. Successful batch counts/checksum are recorded. Persistent per-row version history, failed-job history and undo of a previously committed import are not implemented; back up the local DB before refreshing important work.

## Frontend / API / database

React sends `/api/...` requests to Vite, which proxies them to Django on port 8000. Django uses its ORM to read/write SQLite. The browser receives JSON. Session cookies identify users, and a CSRF token protects writes. Source JSON and the SQLite file are outside the frontend public folder.

| Endpoint | Method / input | Output / behavior |
|---|---|---|
| `/api/session/` | GET | Username, staff status, CSRF token |
| `/api/login/` | POST `{username,password}` | Staff session and rotated CSRF token |
| `/api/logout/` | POST | Ends session |
| `/api/offices/` | GET `q`, `page` | 30 offices/page, bank/location labels |
| `/api/leads/` | GET `q`, `page`, `status` | 30 leads/page and commissioning office |
| `/api/leads/<id>/` | GET | Contact, cases and local notes; ID is target DB ID |
| `/api/leads/<id>/` | POST `{body}` | Creates a local note of 1–4,000 characters and returns detail |
| `/api/summary/` | GET optional `year=2026` | Recorded cases/services for April 2026–March 2027; office/lead/contact counts remain all-history |

Business endpoints require staff login. Ordinary accounts receive 403; anonymous users receive 401. All staff can view all imported records in this local preview. Fine-grained roles/territories and production login throttling remain deployment prerequisites.

## Data and workflow boundaries

The normalized slice is Bank → Office → Lead → Case, with Contact → Office and Lead → Contact. Other export fields are retained as JSON. Source ID mappings: bank.bank_id, client.client_id, orderer_reg.orderer_reg_id, lead.lead_id, client_customer.client_customer_id. Bank is from uam_user; the other four are from lead_mngt.

Lead-entry dates are work-received proxies. All statuses/deletion flags are retained. Recorded cases are not accepted assignments. Closed leads do not establish completed valuation or payment. The current overview is not validated legacy MIS parity, and no monetary figures are summed.

Next milestones:

1. Move staged services, official branches, borrower commercial groups and work orders into typed domain models; complete reference validation and review UI.
2. Port lead creation/editing, assignment and follow-up workflows with documented permissions and accepted status rules.
3. Port valuation forms, document storage, work-order generation, review/approval and dispatch with workflow tests.
4. Port invoice and collection rules with reconciliation and repeat-payment protection; verify MIS definitions against the Java reports.
5. Migrate HRMS/payroll/accounts/integrations independently. Test PostgreSQL, permissions, backups, deployment and cutover reconciliation before replacing the original system.

## Checks

```sh
cd backend
.venv/bin/python manage.py check
.venv/bin/python manage.py test
cd ../frontend
npm run build
```

Tests cover repeat imports, corrections, omitted-row retention, note preservation, leading-zero IDs, orphan references, dry-run rollback, duplicate rejection, date boundaries, staff access, CSRF, login and notes.

Implementation references: Django https://docs.djangoproject.com/en/5.2/ and Vite https://vite.dev/guide/. Project business-rule evidence: `../reports/project-understanding/03-lead-business-workflows.md`; export contract: `../outputs/01a08c3d-marketing-export/Lovable_Import_and_Relationship_Guide.md`.
