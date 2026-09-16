# Validation evidence

Last updated 17 September 2026, after the review corrections.

## Scope imported

Nine business modules: crm, services, workorders, reference, leads, documents,
billing, valuations, organization. 61 source tables from `lead_mngt` and
`uam_user`. Attendance, identity, messaging, reports, leave, audit, all UAT
schemas and `uam_user.logtable` are deliberately out of scope.

| Measure | Value |
|---|---|
| Source tables | 61 |
| Source rows read | 2,537,219 |
| Accepted into target | 2,537,011 (99.992%) |
| Quarantined | 208 |
| Imported with issues | 11,950 |
| SourceRow payloads retained | 2,537,219 (every row, including rejects) |

## Checks performed

- **Full 61-table repeat import proposes 0 inserts and 0 updates**
  (`database/target-repeat-final.json`). This is the idempotency proof for the
  complete streaming pipeline, run after the corrections.
- 19 tests pass under both `config.settings` and `config.target`.
  `makemigrations --check` reports no drift. Frontend production build passes.
- Import reconciles against live MySQL. Every quarantine was traced to a
  dangling legacy foreign key; for the original 16, twelve were directly
  dangling and four cascaded from lead 435 whose `client_id` 1183 is absent.
- Storage classification follows the source system: 150,636 documents
  `legacy_lead_s3`, 50 `legacy_uam_local`, per `DEPLOYMENT_INVENTORY.md`.
- No answer references an option belonging to another question (was 2).
- No subtype remapping was ambiguous (0 rows), so every one of the 13
  remappings had exactly one candidate under the declared service.

## What these numbers do not establish

- Acceptance is not semantic correctness. 11,950 rows carry issues.
- Document **metadata** is migrated; no file bytes were copied or verified.
- Valuation answers are preserved in EAV form. Report rendering parity against
  the legacy JSP output has not been demonstrated.
- No browser session, login, CSRF or end-to-end UI test has been run.
- No production access, and no legacy MIS calculation has been reimplemented
  or compared.

## Operational note

No personal login is created by the importer. Use `Create Login.command` or
`manage.py createsuperuser`. Any temporary QA account should be removed after
testing.
