# Django business-app organization

## What changed

The Python definitions of all 83 concrete target models now live under `backend/apps/`, grouped into 11 business apps and three supporting apps. Workflow modules, URL definitions, admin registrations, management commands and tests have moved with their responsibilities. One Django project, one database and one React frontend remain.

This is a structural refactor, not implementation of the defects or missing workflows listed in `MIGRATION_GAP_REVIEW_2026-09-25.md`. Existing behavior, including known limitations, is retained. Dispatch and analytics packages organize the code/data already present; their existence does not mean the missing dispatch and MIS workflows are implemented.

## App responsibilities

| App | Responsibility | Main implementation |
|---|---|---|
| accounts | Login, onboarding, identity evidence, provisioning | `api.py`, `middleware.py`, `management/commands/` |
| organization | Employees and organizational assignment; retained salary/leave baseline models | `models.py` |
| directory | Banks, branches, client offices and contacts | `api.py`, `services.py` |
| catalog | Services, geography and shared reference choices | `models.py`, `api.py` |
| leads | Intake, requested services, borrowers, cases, follow-ups and notes | `services.py`, `api.py` |
| workorders | Work-order issuance and letters | `services.py`, `pdf.py` |
| valuations | Assessment answers, submissions, verification and attachment workflows | `services.py`, `submission.py`, `verification.py`, `files.py` |
| reports | Bank templates, generated reports, revisions, approval and standing transitions | `services.py`, `approvals.py`, `pdf.py`, `assets/` |
| billing | Charge entry, invoices, collections, credit notes and financial documents | `valuation.py`, `services.py`, `pdf.py` |
| documents | Shared document metadata, local upload validation and retrieval | `storage.py` |
| dispatch | Dispatch/SMS history and report-link reconciliation | `models.py`, `management/commands/link_dispatch_items.py` |
| migration_pipeline | Import specifications, reader/conversion/reconciliation and evidence | `services.py`, `management/commands/` |
| audit | Audit entries, local ownership and shared sequence ledger | `models.py`, `services.py` |
| analytics | Existing overview read API; future MIS ownership | `api.py` |

`apps/common/` is a shared Python package, not another installed model app: abstract models, request/transaction helpers, form validation, numbering, number-to-words conversion, read pagination and common admin policy. Business decisions belong in the domain services, not in common.

The exact model-to-domain inventory is in `backend/apps/model_ownership.json`. Each domain README lists its models.

Admin list columns, searches, filters and ordering are documented for every model
in [the admin table guide](DJANGO_ADMIN_TABLE_GUIDE.md). Their presentation settings
live in `apps/common/admin_options.py`; domain registrations apply those settings
with shared permission and query-loading behavior.

## Database identity is intentionally retained

Model **Python location** and persistent Django **app label** are different concerns. For example:

```python
from apps.leads.models import Lead

Lead.__module__       # apps.leads.models
Lead._meta.label     # target_core.Lead
Lead._meta.db_table  # target_core_lead
```

All existing models explicitly retain `Meta.app_label = 'target_core'`. The installed domain AppConfigs use distinct `omen_*` labels, but their existing model definitions retain the historical persistence label. `target_core/models.py` is a small compatibility registry importing those same classes; it no longer contains business model definitions.

Consequently:

- Existing table names, UUIDs, relationships and migration dependencies do not change.
- Content types, permissions, admin URLs and model labels stored in SourceIdentity, LocalRecord and audit entries remain valid.
- Existing migration files remain under `target_core/migrations/`. No table move, reimport, content-type rewrite or production migration was performed for this split.
- Admin registrations are owned by domain `admin.py` files. A custom `DomainAdminSite` groups the home page and sidebar by business domain after Django filters model permissions. Existing `target_core` model URLs and permission identities remain unchanged. Domain landing pages use `/admin/domains/<domain>/`; domains without registered models are not shown.
- `apps.get_app_config('target_core').get_models()` still provides the complete persisted model set. Domain `models.__all__` and `model_ownership.json` provide the logical domain inventories. Do not use a domain AppConfig's `get_models()` to discover these legacy-label models.

This is a deliberate stable-label architecture, not a completed rename of database app identities. Moving persistent labels later would be a separate migration requiring permission, content-type, generic-reference and import-ledger reconciliation. It is not required to maintain code in smaller apps.

## Where to put changes

1. Edit a model in its domain's `models.py`, never the compatibility registry.
2. Put workflow changes in the owning domain service module and expose routes through that domain's `urls.py`.
3. Keep the existing JSON contract unless a deliberate API change is being made. React's API paths did not change in this refactor.
4. Put regression tests in the owning domain. The historical combined importer/identity suite lives in `apps/migration_pipeline/tests.py`; existing test fixtures remain importable through compatibility modules.
5. Use shared `apps.common.http` for API transaction/error boundaries and `apps.audit.services` for audit/ownership recording.
6. For an added persisted model under this architecture, explicitly retain the intended persistence label, include it in the registry/inventory and generate the migration under that label. Existing-model changes continue to generate `target_core` migrations.

Standard commands from `backend/` remain:

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations target_core
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test
.venv/bin/python manage.py test --settings=config.target
```

Run a domain suite with, for example, `manage.py test apps.billing` or `manage.py test apps.valuations`. Default discovery runs all domain suites. The old `manage.py test target_core` package discovery is no longer the full suite: legacy test modules only provide explicit-import compatibility.

Public commands remain `sync_legacy`, `provision_accounts`, `setup_admin_accounts`, `sanitize_staged_credentials`, `transfer_sqlite_to_postgres` and `link_dispatch_items`. Added since the split: `link_duplicate_receipts` (billing; run after every import, after `link_dispatch_items`) and `amend_schema_contract` (migration_pipeline; records a deliberate model or API-route change in the pre-split contract, and refuses unless the changes are exactly those named). Their implementations now live under the appropriate domain's management package. Credential output still goes to the original project `database/.local/` location.

## Compatibility imports

Old workflow imports such as `target_core.invoices` and `target_core.sync` alias the actual domain module, preserving callers and existing monkeypatches without maintaining two implementations. `target_core.views` re-exports the account/directory/lead/analytics API functions. New code should use the new domain paths directly.

The importer and some cross-domain workflows still use the model registry as a compatibility facade. This does not create duplicate models or tables. A later cleanup can replace those imports with explicit domain imports without changing persistence identity.

## Preservation and validation

The uncommitted receipt additions and migration 0020 present before the refactor were preserved. They remain work in progress; this refactor does not approve or apply that migration to the application database.

`apps/migration_pipeline/fixtures/pre_split_contract.json` records the model schema and API routes captured from the actual pre-refactor files, including those receipt additions. It contains schema metadata only, no customer data. Architecture tests compare all model fields/options/tables and every API pattern, verify old/new imports resolve to the same model classes, check admin registrations, command identity, credential output location and the report letterhead asset.

The application database was not imported, migrated or rewritten during the split. Validation uses disposable test databases. See `VALIDATION.md` for the final run results.
