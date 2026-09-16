# Full OMEN database baseline for the Django monorepo

**Clean target update:** [CLEAN_TARGET_STATUS.md](CLEAN_TARGET_STATUS.md) describes the new managed schema and attendance exclusion. [BUSINESS_ENTITIES.md](BUSINESS_ENTITIES.md) lists entity purposes and coverage of all 202 highlighted tables. This page documents the unchanged, full restored source baseline.

Verified locally on 16 September 2026. This is the full SQL-dump baseline, replacing the marketing-export-only approach as the basis of the whole-system migration.

## Completed and verified

| Original schema | Tables | Restored rows | Purpose |
|---|---:|---:|---|
| ebioserver | 104 | 46,377 | ESSL / iclock attendance |
| lead_mngt | 53 | 2,391,950 | Lead, valuation, reports, invoicing, collections |
| smldb | 2 | 20 | Email / SMS logs |
| uam_user | 421 | 2,632,993 | UAM / HRMS and shared operational data |
| uam_user_uat | 347 | 1,285,996 | UAM / HRMS UAT |
| lead_mngt_uat | 53 | 1,635,543 | Lead UAT |
| smldb_uat | 2 | 5,125 | Messaging UAT |
| **Total** | **982** | **7,998,004** | All supplied schemas kept separate |

All 982 per-table row counts, ordered column names and index-name/column mappings match the reviewed dump metadata. Every table was queried through Django, including materializing one row where available to exercise field mappings. All eight views compiled successfully through SELECT. All 86 triggers, four procedures and 18 foreign-key constraints were found by schema/name identity. No failed tables were reported.

This verification establishes structural/row-count parity, not a cell-by-cell checksum comparison or Java/database-program behavioral parity. Exact routine execution, all default/collation semantics and every financial/workflow outcome remain to be tested. The original native dump was restored without rewriting its data or routines.

Evidence: `verification.json`, `object-verification.json`, `mapping-catalog.json`. These contain counts and schema metadata, not customer row values. Private restore logs and local credentials are under ignored `.local/`.

## Architecture and monorepo scope

```
omen-next/
  backend/
    config/full_database.py      # opt-in seven-schema Django connections
    legacy/
      ebioserver/               # attendance source mappings
      lead_mngt/                # full lead database mappings
      smldb/                    # messaging mappings
      uam_user/                 # full shared UAM/HR database mappings
      *_uat/                    # separate UAT mappings
      base.py                   # read-only access and database router
      catalog.py                # lookup by original schema/table
  frontend/                     # earlier limited React preview
  database/                     # full restore, generation, verification, deployment inventory
```

The target remains one Django + React monorepo for the whole system. Schema boundaries are preserved in this first database phase; a monorepo does not require merging all schemas or conflating UAT IDs with production IDs. Backend business modules can be introduced independently of the legacy physical schema boundaries.

The earlier five-entity SQLite preview remains a separate prototype. Its screens do not yet use this full database. Do not treat its import command, record counts or UI as the whole-system migration.

## Django coverage and identity

There are **905 Django table models**, including **106 composite-primary-key models**, and **77 dedicated table readers** for tables without a primary key. No fake unique ID was chosen for keyless tables. All original source columns are accessible. Actual declared foreign keys are represented where present; application-only relationships are not silently turned into database constraints.

`database/generate_models.py` creates deterministic mappings from the reviewed metadata. Each schema has a generated Django migration file recording unmanaged-model state. These are compatibility/state migrations: they **do not create the native source tables**. `database/restore.py` provisions the physical schema, indexes, defaults, views and routines from the original dump. Running Django migrate alone is not a replacement for the native restore.

The models use `managed=False`. The first goal is complete, faithful, readable data access before enabling ported business writes. Django model/queryset writes and routing are blocked, and the dedicated DB account has SELECT/SHOW VIEW privileges only. Existing legacy employee credentials do not create Django login accounts.

Keyless readers accept validated column filters and bounded limits; offsets do not guarantee stable ordering on a keyless table. Composite-key foreign-key support has limitations in Django 5.2. Preserve the physical keys and port service-level relationships deliberately; do not remove composite keys to simplify the ORM.

## Use the full database locally

The dedicated local Docker container is `omen-full-database-20260916`, bound to **127.0.0.1:3307**, with a named volume of the same name. It uses the official MariaDB 10.11 image; downloaded digest: `sha256:07c0aaff7396b74cb7975cba78257178d188e30f531a5db2b617c48beef13c41`. The source server was MySQL 5.6.51. MariaDB compatibility behavior must be included in later runtime tests.

`lower_case_table_names=1` permits the dump's mixed-case schema/table references to resolve. This is a documented local compatibility setting, not proof of the original server setting. Native engines and source object definitions are retained. UAT triggers that reference the main schema still do so **inside this isolated copy**; do not enable UAT writes until that source behavior has been addressed.

Start an existing stopped database:

```sh
docker start omen-full-database-20260916
```

From `omen-next/backend`:

```sh
.venv/bin/python manage.py check --settings=config.full_database
.venv/bin/python manage.py shell --settings=config.full_database
```

Examples in the Django shell (read only):

```python
from legacy.catalog import table
Lead = table('lead_mngt', 'lead')
Lead.objects.count()
Lead.objects.filter(lead_status=1).count()

# Bank has no primary key in the original database.
Bank = table('uam_user', 'bank')
Bank.count()
rows = Bank.rows(limit=10)
```

Generated Python column names are catalogued in `mapping-catalog.json`. They are normalized identifiers with original `db_column` preserved. For the actual declared ForeignKey fields, Django's scalar-ID attribute follows its normal `<field>_id` convention; some generated names therefore end in `_id_id`.

The migration settings are opt-in. The existing React dev server still uses the earlier SQLite preview. Never point this baseline at the production server by replacing the local credentials casually.

## Reproduce and verify

Dependencies: Docker, Python 3.12, and `backend/requirements-database.txt`. On this Mac, mysqlclient is linked using the Homebrew `mariadb-connector-c` library. Install with:

```sh
PKG_CONFIG_PATH=/opt/homebrew/opt/mariadb-connector-c/lib/pkgconfig backend/.venv/bin/pip install -r backend/requirements-database.txt
```

From `omen-next`, for a **new empty local environment only**:

```sh
backend/.venv/bin/python database/bootstrap.py
backend/.venv/bin/python database/restore.py
backend/.venv/bin/python database/generate_models.py
backend/.venv/bin/python database/verify_full_database.py
backend/.venv/bin/python database/verify_objects.py
```

Bootstrap refuses an existing container/configuration; restore refuses existing source tables. The scripts are tied to the exact supplied snapshot checksum. They do not drop/rebuild an existing DB, support incremental updates, or automatically recover a partial restore. For a newer dump, create a separately reviewed baseline with updated metadata/checksum and compare it before any cutover. Preserve the original SQL dump.

## Remaining migration work

1. Port complete business services and permissions into Django modules: lead workflow, work orders, valuation, verification, documents, billing, collections, MIS, HRMS, payroll, accounts and integrations. Generated models are not a substitute for those services.
2. Validate inferred relationships, orphan rows, status rules, amount precision, audit triggers and attendance procedures with transaction tests and reconciliation. Decide which database routines remain native and which are replaced in Django.
3. Migrate lead S3 files and UAM local uploads separately, reconcile file references, and account for the deployed iclock attendance application. See `DEPLOYMENT_INVENTORY.md`.
4. Connect React to the complete Django services after database/workflow verification. Preserve login, permission and user provisioning boundaries.
5. Add production-grade deploy configuration, backup/restore tests, incremental/cutover strategy and signed-off behavior parity before replacing any deployed service.

No production server was contacted and no uploaded files were copied. Server credentials supplied in chat were not written to this repository.

Reference: https://docs.djangoproject.com/en/5.2/topics/composite-primary-key/ and https://docs.djangoproject.com/en/5.2/ref/databases/.
