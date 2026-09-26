# migration-required

Everything here supported the migration from the legacy Java system and its review.
**None of it is needed for the application to run.** It is kept for evidence,
audit and the final cutover import.

| Folder | Contents |
| --- | --- |
| `handoff/` | `HANDOFF.md`, the running record of the migration and its run order, and `VALIDATION.md`. |
| `reviews/` | Codex's reviews of Claude's work and the gap reviews, with their reproduced findings. |
| `app-reference/` | Design and reference documents for the new application: domain architecture, the admin table guide, target schema, user roles, lead intake, deployment inventory. Still accurate; kept here because the app does not read them. |
| `data-migration/` | The tools that restored, catalogued, mapped and verified the legacy databases, together with the data they read and write (`mapping-catalog.json`, `verification.json`, `target-disposition.json`, `entity-review.json`, `object-verification.json`) and the documents they generate (`SOURCE_TO_TARGET.md`, `BUSINESS_ENTITIES.md`, `LEAD_FLOW_INVENTORY.md`, and others). Tools and data stay together so their relative paths hold. |
| `import-runs/` | Reports from every import: `dry-runs/`, `imports/` and `repeat-proofs/` (the zero-change evidence after each change). |
| `archive/` | `prototype_core`, an early prototype app that is not installed. |
| `database-backups/` | Superseded SQLite databases from earlier phases. **Git-ignored and never to be committed: they may hold legacy personal data.** |

## What stays in the application, and why

- `database/.local/` holds local, git-ignored configuration the application reads:
  the PostgreSQL connection (`postgres.json`), the legacy source connection used by
  the importer (`connection.json`), and generated admin credentials.
- `backend/target.sqlite3` is the fallback database when `DATABASE_ENGINE=sqlite`
  and the source for `transfer_sqlite_to_postgres`: the rollback path.
- The import pipeline itself (`backend/apps/migration_pipeline`, the `legacy`
  schema models, `sync_legacy` and the linking commands) is application code. It
  runs the final cutover import and is covered by the test suite.
- `backend/apps/migration_pipeline/fixtures/pre_split_contract.json` is read by the
  architecture tests and `amend_schema_contract`.

## Using the tools

The tools in `data-migration/` compute the repository root from their own location
(two levels up) and still read `database/.local/` for credentials. Only the
`legacy` app's tests depend on this folder, for `mapping-catalog.json`.

After each import, write its report into `import-runs/`, for example:

    manage.py sync_legacy --settings=config.full_database --report ../migration-required/import-runs/imports/<name>.json
    manage.py sync_legacy --settings=config.full_database --dry-run --report ../migration-required/import-runs/repeat-proofs/<name>.json
