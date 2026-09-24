# Lead intake implementation — 24 September 2026

## Delivered scope

The local Django/React application supports client office and contact creation/editing, lead creation, requested services, borrowers, asset cases, employee assignment, follow-ups and cancellation. Business roles are deferred at the owner's request. The existing staff/admin gate and first-login password requirement remain enforced on every intake endpoint. Ordinary provisioned accounts do not receive business access.

The first usable path is: sign in and complete password setup, choose **New lead / client**, choose/create an office and contact, create the lead, then add services, borrowers and cases. The lead also appears under **Leads**; opening it exposes the same intake controls and the existing notes/history view.

This is a local intake slice, not completed whole-system parity or production cutover. Work-order generation, valuation execution/review, document upload/retrieval, report generation, invoicing, receipts, dispatch and MIS remain subsequent phases. Existing child rows can be viewed and new services/borrowers/cases added; editing or removing existing service/borrower/case rows is not part of this slice. No SMS/email is sent.

## Business rules traced to Java

- `omen-lead-new/src/main/java/com/awzpact/lead/controller/CustomerController.java`, `generateLeadNo()`: `L-` + two-digit month + two-digit year + two-digit day + a global numeric suffix. The current creation date is used, not the received date selected by the operator.
- `omen-lead-new/src/main/java/com/awzpact/lead/dao/LeadDAOImpl.java`, `getMaxLeadNewNo()`: the suffix continues from the maximum existing sequence and does not reset with the financial year. The new allocator considers existing numeric-format lead numbers and uses a transactional counter, with uniqueness on locally allocated sequences. Concurrent database conflicts return HTTP 409 for retry instead of committing partial records.
- `CustomerController`: creates status 1 (New), then sets status 2 (In process) when requested services are recorded. The new API follows this transition and does not interpret assignment alone as completion.
- `lead/enums/LeadStatusEnum.java`: 1 New, 2 In process, 3 Cancelled, 4 Closed. This phase only creates 1, advances to 2 and cancels with a recorded reason. It never sets Closed as a shortcut to valuation or payment completion.
- `WorkOrderGenerateController`: closure is tied to work-order generation in the old application. Work-order generation is not implemented here.

Additional explicit rules in this slice: a contact must belong to the selected office; a subtype must belong to its service; a case borrower must belong to the same lead; a case must use a requested service/subtype; negative fees, nonpositive supplied counts and blank names are rejected. An employee without a login can be assigned, but an employee whose linked account is disabled cannot receive new assignments. Cancelled, closed, unknown/deleted-status and already-work-ordered leads are locked against intake mutations. The receipt/invoice approval policy is not involved.

The legacy call-status codes remain unchanged in imported follow-ups. New follow-ups use the explicit local outcomes Contacted, No answer and Callback requested; they are not presented as verified mappings of legacy numeric codes.

## Schema changes

Migration `target_core.0009_lead_intake` adds:

| Entity / field | Purpose |
|---|---|
| LeadCounter | Serial allocation of local lead numbers above the imported maximum |
| Lead.intake_key / intake_hash | Retry-safe lead creation and conflict detection when a token is reused with different data |
| Lead.local_sequence | Unique sequence allocated to each locally created lead |
| IntakeAudit | Actor, action, target, before/after business data and timestamps for intake writes |
| LocalRecord | Marks a record as locally managed after an edit, so the importer preserves it |

No new user roles or permissions tables were added. Existing business tables continue to hold offices, contacts, services, borrowers, cases and follow-ups.

## Import ownership and repeat behavior

New UUID records are not assigned a legacy SourceIdentity, so source refreshes do not target them. An edit to an imported office/contact/lead creates a LocalRecord marker in the same transaction as its audit event. A later import preserves that entire target record, still records the newest sanitized source payload in SourceRow, and reports `Locally managed record; source changes retained in staging only`.

This is deliberately whole-record ownership, not a per-field merge. After an imported office is locally edited, other source changes to that office also remain in staging. Reconciliation should compare that evidence before handing ownership back; this phase provides no automatic ownership reset. Source refresh is not a two-way synchronization protocol. Production and legacy systems must not independently allocate new lead numbers during cutover without a coordinated writer policy.

Tests import source fixtures, locally edit an imported office and lead, add a local lead and follow-up, change the source, then import twice. Target edits, local records and follow-ups survive, while the changed source data is retained in staging.

## API contract

All requests require the existing authenticated staff/admin session, completed onboarding and CSRF for writes. JSON responses use the existing error convention `{ "error": "..." }`. Invalid values return 400, missing resources 404, unauthenticated access 401, denied access 403, and locked records/retry conflicts 409. Browser forms display these errors.

| Route | Method | Input / output |
|---|---|---|
| `/api/intake/catalog/` | GET | Services, service-linked subtypes, assignable employees, client types, designations, banks |
| `/api/offices/?q=...` | GET | Existing paginated office search; used to choose an office |
| `/api/intake/offices/` | POST | name, branch_name, address, bank, client_type, state, district → created ID and fields |
| `/api/intake/offices/<id>/` | GET / PATCH | Read/update allowed office fields; an existing linked directory branch must remain consistent with the bank |
| `/api/intake/contacts/?office=<id>` | GET | Contacts belonging to that office |
| `/api/intake/contacts/` | POST | name, office, designation, phone, alternate_phone → created ID and fields |
| `/api/intake/contacts/<id>/` | PATCH | Update contact fields; moving a contact between offices is refused |
| `/api/intake/leads/` | POST | request_id UUID, office, contact, assigned_employee, received_date; optional services/borrowers arrays → id, generated number, replayed flag |
| `/api/intake/leads/<id>/` | GET | Lead fields, services, borrowers, cases, follow-ups, editable flag, lead audit entries |
| `/api/intake/leads/<id>/` | PATCH | contact, assigned_employee, received_date, or nonblank cancel_reason → updated lead detail |
| `/api/intake/leads/<id>/services/` | POST | service, subtype, party_count, case_count → new ID; advances New to In process |
| `/api/intake/leads/<id>/borrowers/` | POST | name, agreed_fee, property_count → new ID; local currency INR |
| `/api/intake/leads/<id>/cases/` | POST | borrower, service, subtype, asset_address, asset_district, asset_state → new ID |
| `/api/intake/leads/<id>/follow-ups/` | POST | outcome, remark → new ID; timestamp assigned by server |

Example lead creation (replace placeholders with catalogue/directory UUIDs):

```json
{
  "request_id": "bd34b48b-1808-4806-95ad-62f63b2d6a99",
  "office": "<office UUID>",
  "contact": "<contact UUID>",
  "assigned_employee": "<employee UUID>",
  "received_date": "2026-09-24",
  "services": [{"service": "<service UUID>", "subtype": "<subtype UUID>"}],
  "borrowers": [{"name": "Example borrower", "agreed_fee": "2500.00", "property_count": 1}]
}
```

A repeated creation request with the same key and same JSON data returns the existing lead (200); a changed payload with that key returns 409. The first creation returns 201. Invalid nested services/borrowers roll back the complete request, including counter changes and audit entries. Retry deduplication currently applies to lead creation; other POST operations are individual transactions, and clients should check the record before resubmitting after an ambiguous network failure.

## Correction re-review and validation evidence

- Existing identity regression tests cover onboarding restrictions, credential exclusion, timestamp conversion, grant eligibility, source-status/grant revocation, refused username adoption, employee-binding conflicts and merge ordering. Those regressions pass together with the new intake tests.
- Read-only inspection of 74,215 target identity payloads found zero keys from the credential exclusion list.
- Compared all 74,164 login timestamps to retained source timestamps interpreted as Asia/Kolkata: zero mismatches. The timezone interpretation remains an explicit assumption; it was not independently confirmed from production server configuration.
- The saved 68-table repeat report records 2,623,601 source rows, zero inserts and zero updates. It is existing evidence from Claude, not a new full MySQL execution during this phase.
- All 72 tests pass under both `config.settings` and `config.target`; the new intake test class contains 12 workflow/data-protection tests.
- Frontend production build passes. No migration drift.
- Browser smoke test used an isolated in-memory database and synthetic data: created an office and contact, generated and assigned a lead, added service/subtype, borrower, case and follow-up, then verified the lead in the existing list. No smoke-test business data was written to the real target database.

The earlier role-access finding is contained by the admin-only gate, not resolved by a finished business role policy. The owner's instruction defers that policy. Shared admin setup, first-login UI and test-output isolation from the preceding phase are retained.

## Local rollout

The local database was backed up using SQLite's consistent backup API to `database/.local/target-before-intake-2026-09-24.sqlite3` with owner-only permissions, then migration 0009 was applied. The source dump and MySQL database were untouched. The backup is ignored by Git and contains sensitive application data; do not distribute it as documentation.

Start/restart the existing backend on port 8000 and frontend on port 5173. Log in with the existing admin account and choose **New lead / client**. The separate Data Atlas on port 4173 does not serve these forms.

Next implementation phase: work-order creation for the collected borrowers/cases, with numbering, fee rules, document output and transition tests. Then proceed to valuation, review/reporting, finance, dispatch and MIS. Business roles remain deferred, and this local preview must not be treated as a production deployment.
