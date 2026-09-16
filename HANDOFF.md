# Django and React migration: handoff to Claude / Devin

Status at handoff: 16 September 2026. This document supersedes older progress claims where they conflict. The migration is incomplete. The architecture correction is implemented but its new import and API paths are not yet validated end to end.

## Objective and boundaries

Build one Django + React monorepo with a consolidated business schema, prioritizing lead management. Do not reproduce all 982 legacy tables as application tables. Historical attendance is out of scope; payroll history and leave-opening-balance evidence remain in scope. Do not discard important tables merely because their names contain “backup”. Keep production and UAT separate.

Use the local restored database only. Do not connect to production, change source data, commit credentials, or copy database dumps into a public repository. Preserve the existing prototype database and its backups.

## Completed before this correction

- Restored the supplied SQL dump locally into MariaDB. Existing verification reports cover 982 tables and 7,998,004 rows, plus database objects. These are source-restoration results, not clean-target import results.
- Generated read-only legacy access: 905 unmanaged Django models and 77 keyless table readers.
- Reviewed all 982 source tables at disposition level and documented the 202 highlighted main-schema tables. The 202 outcomes were 140 retain, 25 preserve/reconcile, 33 attendance exclusions, two mapping reviews, and two archives. These are review outcomes, not completed implementations.
- Built a prototype React application with login, overview, office and lead search, lead details, linked cases and notes. Its old SQLite database holds 27,488 typed business rows plus 62,537 staged records from the JSON export.
- Designed 27 initial clean-target entities. The prototype and clean schema were initially disconnected; this was a real defect.

## Changes made in the current correction

- Moved the old Django `core` app into `archive/prototype_core`, outside active backend test discovery. Its code and tests remain available for reference.
- Made `target_core` the only active business-model app. Both `config.settings` and the compatibility alias `config.target` use `backend/target.sqlite3` and the same API routes.
- Adapted API views to target models, including UUID lead routes. React has not yet been browser-tested against these changes.
- Added `SourceRow` for source payload retention/quarantine and `LeadNote` for local notes. Added office geography fields. Generated and applied migration `0002`. The target now has 29 managed business/support models, excluding Django framework tables.
- Preserved `backend/db.sqlite3`; created SQLite backups with the `.before-unification` suffix. Existing prototype accounts and notes have NOT yet been copied into the target.
- Implemented `target_core/sync.py` and the `sync_legacy` management command: a direct read-only MySQL-to-target import with stable identities, repeat-update behavior, target transaction rollback, source payload preservation, issue records and per-table counts. This code has NOT yet been exercised against real MySQL or covered by dedicated pipeline tests.

## Current evidence and limitations

- `manage.py test`: eight tests pass after the correction.
- `manage.py test --settings=config.target`: eight tests pass after the correction.
- These eight tests cover target schema constraints and legacy access protections. They do NOT replace the archived prototype importer/API regression coverage or prove the new pipeline works.
- No successful real-data import into the clean target has been performed. Do not present the old prototype counts as target counts.
- The old `VALIDATION.md` six-test and browser claims describe the earlier prototype. They are not evidence for the current API/import implementation.
- README and other status documents still need reconciliation with the new architecture.

## Target entities and business purpose

| Area | Entities | Business purpose |
|---|---|---|
| Organizations | Bank, BankBranch, ClientType, ClientOffice | Separate the bank directory from actual client offices and their business relationships. |
| People | Employee, ContactDesignation, Contact | Staff ownership and client contacts; employees are not automatically login accounts. |
| Service catalogue | ServiceType, ServiceSubtype | Define requested services and their categories. |
| Lead operations | Lead, RequestedService, Borrower, Case, WorkOrder, Valuation | Track requests, parties, assets/cases, work authorization and valuation delivery. |
| Files | Document | Preserve file references and verification state; copying metadata does not retrieve files. |
| Finance | Invoice, InvoiceLine, Receipt, ReceiptAllocation | Billing and receipt allocation; allocation rules and financial reconciliation remain unfinished. |
| Payroll and leave | SalaryBaseline, SalaryBaselineComponent, SalaryResult, LeaveOpeningBalance | Preserve historical salary results and opening-balance evidence without historical attendance. |
| Migration traceability | ImportBatch, SourceIdentity, MigrationIssue, SourceRow | Explain each import, retain source identities and quarantine unresolved data. |
| Local collaboration | LeadNote | Keep application notes separate from source-owned imported fields. |

These 29 entities are the implemented foundation, not a claim that every retained legacy business domain has been implemented.

## Direct import scope implemented in code

- `uam_user`: bank, bank_branch, employee, employee_salary_main_backup, employee_salary_backup, employee_salary_summary.
- `lead_mngt`: client_type, client_designation, service_type, service_sub_type, client, orderer_reg, lead, lead_services, lead_borrower, client_customer, upload, lead_order, valuation, invoice, cash_receipt, amount_received.
- `uam_user.state` and `district` are additional geography lookups.

That is 22 entity source tables plus two lookups. Invoice lines, receipt allocations and leave opening balances have models but no import mapping yet. Other retained domains also need implementation. Attendance and UAT are intentionally excluded from this importer.

## Next phase — Claude / Devin implementation

1. Read this handoff, existing schema documentation, source mappings and code. Finish the current correction before adding features. Do not restore a second active business schema.
2. Add meaningful pipeline tests: first import, repeat import, corrections, omitted-source retention, optional and required missing parents, quarantine recovery, conflicting relationships, duplicate-key rollback, failed-source rollback and dry-run rollback. Assert local notes and office ownership survive updates.
3. Review importer correctness before real execution. Include geography inputs in its fingerprint; verify source-identity model labels; validate required lookup columns; examine decimal precision, duplicate identities, memory use and concurrent-run protection. Verify snapshot guarantees for source storage engines rather than assuming every table is transactional.
4. Add a read-only prototype adoption command for local Django accounts and notes. Preserve password hashes safely, map notes through legacy lead IDs to target UUIDs, reject conflicting identities, report unresolved notes and prove repeatability. Do not import HR password fields as login credentials.
5. Run the direct importer against the local restored MySQL database, retain a per-table reconciliation report, investigate quarantined rows, then repeat with dry-run. Do not silently drop rows or invent financial links. Distinguish unchanged accepted records from unresolved records.
6. Test all existing API behavior against the target: session login/logout, CSRF, staff access, search, pagination, lead detail, notes and overview counts. Update React labels/counts to distinguish accepted records from quarantined source rows. Run a production frontend build and browser smoke test.
7. Rerun full tests under both documented settings, check migration drift, and update README/VALIDATION with the exact current evidence. Keep historical prototype validation clearly marked as historical.
8. Produce a completion report listing changed files, exact commands/results, target counts, quarantine counts/reasons, preserved prototype data, remaining domain gaps and known risks. No production deployment or deletion of the old database.

Suggested execution, from `omen-next/backend`, after reviewing and testing the importer:

```sh
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test
.venv/bin/python manage.py test --settings=config.target
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py sync_legacy --settings=config.full_database --dry-run --report ../database/target-dry-run.json
.venv/bin/python manage.py sync_legacy --settings=config.full_database --report ../database/target-import.json
.venv/bin/python manage.py sync_legacy --settings=config.full_database --dry-run --report ../database/target-repeat.json
```

The MySQL source configuration is local to `database/.local/connection.json`; do not include its contents in handoff reports. The ordinary web application uses the target database and does not need source access to serve imported data.

## Codex review gate

Return the changed project plus the completion report to Codex. Codex will independently inspect the diff/code and rerun relevant checks, focusing on data loss, relationship correctness, repeatability, source protection, access control and UI/API behavior. A passing test count alone is insufficient. Outstanding issues must be fixed or explicitly documented before proceeding.

## Following phase — Codex implementation

After the review gate, continue the remaining business migration in dependency order: resolve remaining entity mappings; implement lead/work-order/valuation workflows and permissions; reconcile invoice and receipt relationships; complete payroll and opening-balance imports without attendance history; implement and compare legacy MIS calculations; integrate file access; then prepare production database configuration, deployment and cutover. Sequence the exact work using the reviewed gaps. Do not claim whole-system parity until each retained domain has mapping, implementation and validation evidence.

## Files to start with

- `backend/target_core/models.py`, `sync.py`, `views.py`, `tests.py`, `migrations/`
- `backend/config/settings.py`, `target.py`, `full_database.py`, `urls.py`
- `frontend/src/` and `archive/prototype_core/`
- `database/BUSINESS_ENTITIES.md`, `TARGET_SCHEMA_DESIGN.md`, `entity-review.json`, `target-disposition.json`
- `database/mapping-catalog.json`, `verification.json`, `object-verification.json`

Do not distribute the SQL dump, credentials, salary/contact payloads or SQLite databases with a general-purpose handoff summary. Give implementation agents access only through the authorized project environment.

---

# Addendum — 17 September 2026

## The valuation form (EAV)

The legacy valuation report is entity-attribute-value and is **preserved in that
shape rather than pivoted**, because the question set varies by service and
changes over time; pivoting would freeze the current form and lose history.

| Legacy table | Rows | Target | Role |
|---|---|---|---|
| `detail_category` | 73 | `QuestionCategory` | form sections |
| `question` | 2,161 | `Question` | the attribute, scoped by service + subtype + category |
| `question_options` | 5,382 | `QuestionOption` | permitted values |
| `valuation_answer` | 1,947,362 | `ValuationAnswer` | one stored cell |
| `valuation_verification` | 12,080 | `ValuationVerification` | five review tracks, kept flat |
| `revert_back` | 3,343 | `Reversion` | sent back for correction |

`question.answer_type` governs grouping. Semantics were read from the legacy
renderers `report_question.jsp` and `valuation_full_view.jsp`:

- **1, 2** — option list; one answer row per option
- **3** — free text; a single answer row
- **4, 6** — repeating grid; `answer_group` is the row index, options are columns
- **5** — attribute/value table whose numeric values are totalled

Consequences for the model: `answer_group` is significant and is never
collapsed; and **no uniqueness is asserted** over
`(valuation, question, answer_group, option)` because 281,335 combinations
repeat in the source and 30 repeat even including the option.

Known unresolved links: 11,567 answers reference an option id absent from
`question_options`. Payloads are retained. Profiling these by `answer_type` to
determine which are interpretable remains open work.

## Review corrections applied

1. Later relationship checks reuse the objects resolved by the FK resolver.
   Previously they re-indexed the parent maps with the raw string, bypassing
   zero-pad normalization; the bracket forms raised an uncaught `KeyError` that
   would roll back an entire import.
2. An answer whose option belongs to another question keeps its value and
   clears only the unusable link (2 rows).
3. `storage_provider` follows the source system rather than being hardcoded.
4. Subtype remapping is by **normalized** name (trimmed, case-insensitive) and
   refuses to guess when more than one candidate matches.
5. `BooleanField` conversion handles null rather than failing NOT NULL.
6. The API surfaces importer issues on offices, leads and cases; the overview
   distinguishes source, accepted, flagged and quarantined counts.

## Still open

- Pipeline tests exist (19), but there is no browser login/CSRF/session test.
- Prototype account and note adoption is **not applicable**: the prototype
  database holds 0 `auth_user` and 0 `core_leadnote` rows. Verified empty.
- Parent maps are still keyed by bare table name and rely on ordering the two
  `uam_user` collisions last. Namespace them before extending mappings.
- Document bytes, legacy MIS parity, identity/permissions, messaging and
  attendance remain unmigrated.
