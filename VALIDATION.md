# First migration milestone — validation

Verified locally on 16 September 2026.

- Django system checks passed; initial schema migration applied to a separate SQLite database.
- Six automated tests passed: repeat imports/corrections/omitted-row retention and note preservation; dry-run rollback; duplicate rejection; orphan retention; financial-year date boundaries; session/CSRF/access and note validation.
- React production build passed with Vite 7.3.6. npm reported no known vulnerabilities at install time.
- Imported: 199 banks, 1,394 client offices, 2,049 contacts, 10,969 leads, 12,877 cases.
- Other exported business sheets were stored in source staging. Their operational models and workflows are not yet migrated.
- Repeating the full real-data import in dry-run mode proposed zero inserts and zero updates across all 16 business sheets.
- Browser checks passed: staff sign-in, overview counts, search narrowed to one lead, linked case visible, note saved through the React → Django API → database path, sign-out. Browser console had no errors during this check.
- The temporary QA account and its test note were removed after testing. No personal login was created for the user; use Create Login.command or manage.py createsuperuser.

The first-slice importer reports four rows with missing/unmatched modeled references: one contact, two leads and one case. This narrower check does not supersede the 1,842 review items in the broader Excel analysis. Further domain validation remains necessary.

Not tested or completed: PostgreSQL, deployment, complete operational workflow parity, external integrations, all-role permission parity, full legacy MIS calculations, XLSX upload UI, incremental sync, financial reconciliation, and mobile browser layout. See README for the remaining milestones and supported refresh process.
