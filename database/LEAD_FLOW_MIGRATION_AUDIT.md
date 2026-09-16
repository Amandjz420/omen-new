# Lead management: legacy-to-Django flow migration audit

Review date: 17 September 2026. Scope: the supplied `omen-lead-new` application, its main-schema data mappings, current Django backend and React preview. This is an execution-readiness review, not a claim that all business operations are implemented.

## Verdict

**The complete lead-management lifecycle cannot currently execute in Django.** The working product is an authenticated historical-data preview with lead notes. Most operational entities have import mappings, but their command APIs, workflow services, permissions and forms do not yet exist.

The first business blocker is creating a lead: `POST /api/leads/` returns 405. Starting with an already imported lead does not remove the blocker: services, borrowers, work orders, valuations, reports, billing and collections have no operational API routes.

This audit inventories 50 Java controller files containing 410 active method-level `RequestMapping` declarations. These include aliases, lookups, screen routes, exports and support endpoints; they are **not 410 distinct business workflows**, and static presence does not prove that every old endpoint ran successfully. All declarations and all 53 LEAD source tables are listed in [LEAD_FLOW_INVENTORY.md](LEAD_FLOW_INVENTORY.md).

There are seven current Django route patterns, implemented in `backend/config/urls.py` and `backend/target_core/views.py`. The importer's 61 sources include 41 of the 53 `lead_mngt` tables, with 20 shared UAM sources. Imported data and executable workflows are assessed separately below.

## Reading the status

- **Preview works:** checked API behavior and/or browser interaction exists. It does not imply legacy permission or reporting parity.
- **Partial:** only a subset, such as searching or displaying imported records, works.
- **Data only:** managed models and source mappings exist, but the operational action cannot be executed through Django/React.
- **Missing:** the required target representation and/or import path is absent.
- **Support pending:** an integration or shared control requires its own contract and verification.

Controller names in the following tables refer to files under `omen-lead-new/src/main/java/com/awzpact/lead/controller/`. Exact legacy routes and source links appear in the appendix. Target model names refer to `backend/target_core/models.py`; mappings refer to `backend/target_core/sync.py`.

## 1. Client setup and lead intake

| Flow | Legacy implementation and behavior | Current Django/data mapping | Execution outcome and work needed |
|---|---|---|---|
| Sign in, session and access | Legacy controllers depend on `loginUser` and UAM/user context; authorization also depends on shared configuration | Django auth sessions, staff check, CSRF; session/login/logout APIs | **Preview works.** Legacy roles, user-to-employee identity, branch/client scope and reviewer duties are not migrated. Prototype account adoption remains separate. |
| Bank directory lookup | `BankController`, `AJAXController`; select bank and branch/location | `uam_user.bank → Bank`, `bank_branch → BankBranch`, `ifsc → IfscArea` | **Data only** for directory workflows. Office responses show a bank name, but no dedicated branch/IFSC lookup API exists. |
| Create/edit client offices | `ClientController`; client identity, branch, address, type and status | `client → ClientOffice`; `/api/offices/` GET | **Partial.** Search/list works; creation, editing, status changes and deletion are unavailable. |
| Create/edit contact people | `OrdererRegistrationController`; client-linked contact and alternate number | `orderer_reg → Contact`, `client_designation → ContactDesignation` | **Partial.** One contact is shown in lead detail. No contact creation, editing or lookup workflow. |
| Maintain client types/designations | `ClientTypeMasterController`, `ClientDesignationController` | `ClientType`, `ContactDesignation` | **Data only.** Add guarded maintenance APIs and forms. |
| Maintain territory and service catalogues | `DivisionController`, `SubDivisionController`, `ServiceTypeController`, `ServiceSubTypeController` | `LeadDivision`, `LeadSubdivision`, `ServiceType`, `ServiceSubtype` | **Data only.** Add controlled maintenance and dependency validation. Territory links on all relevant business entities need field-level mapping. |
| Create or edit a lead | `NewLeadController`, `CustomerController`; select/create contact, associate office, generate lead number, save lead and requested services transactionally | `lead → Lead` | **Unavailable.** `POST /api/leads/` is 405. `PATCH /api/leads/{uuid}/` is 405. Add a service with numbering, contact/office consistency, required fields and transaction rollback. |
| Search/view leads | `LeadController`, `DesignController`, `NewLeadController`; list, filters and detailed views | `/api/leads/`, `/api/leads/{uuid}/`; imported office/contact/cases | **Preview works** for current filters and fields. Legacy lead-detail breadth, permissions and exports are not equivalent. |
| Add/change requested services | `LeadServiceTypeController`, `CustomerController`; service/subtype, party and case counts | `lead_services → RequestedService` | **Data only.** No service-edit API/form. Validate subtype ownership and count semantics before enabling writes. |
| Add/edit/remove borrowers | `LeadBorrowerDetailController`, `DesignController`; borrowers grouped under a lead | `lead_borrower → Borrower` | **Data only.** Add borrower API and links to cases/fees; do not confuse a borrower with the commissioning office. |
| Add/edit/remove cases | `LeadCustomerDetailController`, `DesignController`; borrower, lead, service, asset data | `client_customer → Case`; subset displayed in lead detail | **Partial.** Read subset only. Case creation, editing, location completion and protected removal are missing. |
| Lead call follow-ups | `DesignController.save_call_status`; call status, date, time and remarks | `follow_up → FollowUp` | **Data only.** Current `LeadNote` is a separate free-text workspace note; it does not execute the old call-follow-up workflow. |
| Add a workspace note | New preview function | `LeadNote`; POST to lead detail with `{body}` | **Preview works.** Stored author/body/time, reload and CSRF checked. No claim of legacy follow-up equivalence. |
| Lead status, cancellation and removal | `LeadController`, `CustomerController`, work-order generation, legacy enums | `Lead.legacy_status`, `legacy_deleted`; UI filter only | **Data only for mutations.** No transition service or delete endpoint. Establish allowed transitions and preserve historical flags. |
| Staff assignment and targets | `EmpTaggingController`, `FaTargetController` | `employee → Employee`, `EmployeeAssignmentRule`, `EmployeeTarget`, optional lead assignee | **Data only.** Rule execution, scope enforcement and target-vs-actual calculations are missing. |

## 2. Work orders and valuation execution

| Flow | Legacy implementation and behavior | Current Django/data mapping | Execution outcome and work needed |
|---|---|---|---|
| Work-order queue and generation | `LeadOrderController`, `WorkOrderGenerateController`; borrower-level order, number and generated PDF | `lead_order → WorkOrder`, `lead_order_history → WorkOrderRevision` | **Data only.** No order-create/revision API, numbering service or PDF generator. |
| Fee calculation setup | `WoChargeCalculationMasterController`; bank/range-based fee rules | `wo_fees_calculation → FeeRule` (empty in saved source snapshot) | **Data only.** Empty data is not proof the feature is unnecessary. Implement range, rounding and boundary tests. |
| Start/reopen valuation | `ValuationController.case`; load case, create Pending valuation if absent, record current user | `valuation → Valuation` | **Data only.** No create/open/reopen API. Implement explicit POST creation rather than copying a GET with write side effects. Resolve user-to-assessor identity. |
| Configure form sections/questions | `DetailCategoryController`, `QuastionMasterController`; questions/options, service/subtype/category/type, required/document flags | `detail_category → QuestionCategory`, `question → Question`, `question_options → QuestionOption` | **Data only.** No configuration screens/API; historical version semantics need a design. |
| Load the correct valuation form | `ValuationService.questionList`; filter by service, subtype, category, deletion and review type | Question and option models | **Data only.** No form-definition API or React renderer. A subtype correction can change which questions load, so remapping needs review. |
| Save scalar/option answers | `ValuationController.saveDetail`; question/option/value/document links | `valuation_answer → ValuationAnswer` | **Data only.** Add typed input validation, mandatory-field policy, ownership checks and transactional save. |
| Add/edit/delete repeating grid rows | `ValuationMultiController`, older multi handlers; group index identifies a row | `ValuationAnswer.answer_group`, optional option/column | **Data only.** No repeating-row API/UI. Preserve group and source answer identities; do not collapse repeated historical cells. |
| Numeric attribute totals | `valuation_detail.jsp` answer type 5 and other service-specific forms | Answer values retained | **Data only.** Port validated calculation rules to backend services and compare examples. Frontend totals alone are insufficient. |
| Photos, evidence and attachments | `ValuationController` photo/document uploads, `PublicController` download | `Document`, `ValuationAttachment`, `LeadAttachment`, `DocumentUsage`, `ScrutinyRequirement` | **Data only.** No upload/download API, object access, file-byte transfer, signed-link policy or content verification. |
| Record charges before invoicing | `ValuationController.saveBilling` | `billing_head → ChargeType`, `valuation_billing → ValuationCharge` | **Data only.** No billing-line edit API or calculation service. |
| Submit completed assessment | `ValuationController.saveFinal`; date, desired/eligible loan, comments, non-cost factors, submit-to employee, dispatch instructions and report number | `Valuation` holds only case/order/assessor/date/status/report number | **Incomplete model and no workflow.** Several submission fields remain only in SourceRow payload; add typed fields and submission checks. |
| Legal/technical/social/general verification | `ValuationController.saveVerification`, `ValuationListAllUserController` queues | `valuation_verification → ValuationVerification` | **Data only.** Add reviewer permissions, per-track actions, actor identities, audit events and required-review policy. |
| Hold/cancel/revert/resume assessment | `ValuationController` status/reason actions; `BankReportController` return actions | Legacy valuation status and `revert_back → Reversion` | **Data only.** Reason validation, transition rules, reviewer-state reset and notifications are absent. |
| Reassign valuation/invoice responsibility | `ValuationChangeFAController`, `InvoiceChangeFAController` and related update actions | Some employee references; no complete operational assignment history | **Data only/partial fields.** Need role checks, reassignment endpoints and history. |
| Read full valuation and review queues | `ValuationFullViewController`, `ValuationListAllUserController` | Imported valuation-related entities | **Data only.** Lead detail does not include answers, reviews, photos or reports. |

## 3. Reports, dispatch, billing and recovery

| Flow | Legacy implementation and behavior | Current Django/data mapping | Execution outcome and work needed |
|---|---|---|---|
| Configure report usage and templates | `UsageOgReportsController`, `ReportSetupController`, `BankReportHeadingController`; ordered template questions/headings and usage | `usage_of_reports`, `report_setup`, `report_question`, `bank_report_heading` have no current mappings | **Missing.** Model versioned report templates and map active and historical definitions. |
| Prepare bank valuation report | `BankReportController.savebankReport`; market/fair, realizable, distress and book values, references, certificate and report date | `valuation_bank_report` has no current mapping | **Missing.** These assessed values are not replaced by invoice totals or generic valuation answers. |
| Generate/review bank report output | `BankReportController`, report services/utilities | No managed issued-report model or renderer | **Missing.** Map templates and report data; reproduce approved outputs and record generated artifacts. |
| Final report approval and correction return | `BankReportController.saveFinalBankReportApproval`, `saveFinalRevertBack` | Final status/name fields exist in `ValuationVerification`; report model absent | **Incomplete.** Approval API, permissions, review invalidation and issued-version controls are absent. |
| Dispatch report and inspect history | `DispatchController`; dispatch record, report association, view/edit/delete | `dispatch` has no current mapping | **Missing.** Import historical dispatch and implement authorized delivery tracking. |
| Create invoice/PDF | `InvoiceController.saveInvoice`; save charges/taxes/totals, invoice number/due date and generated file | `invoice → Invoice`; `ValuationCharge`, `IssuerAccount`, `Document`; `InvoiceLine` model exists | **Data only.** No invoice command API, posting rules, numbering, line generation or PDF service. |
| Edit invoice/payment status | `InvoiceController`, `AmountReceivedController` | Original invoice totals/status retained | **Data only.** Add controlled corrections/reversals and derived outstanding balance logic. |
| Enter/check/verify cash receipt | `CashReceiptController`; separate add/checker/verify screens/actions | `cash_receipt → Receipt` with invoice/client/borrower/document references | **Data only.** No maker/checker workflow or verified posting API. `Receipt.verified` does not derive automatically from a legacy text status. |
| Record amount received and history | `AmountReceivedController`; update payment, receipt status, lists, history, delete | `amount_received → Receipt` with valuation reference | **Data only.** Reconcile identities across receipt sources before aggregating payments. |
| Invoice follow-up and bad debt | `AmountReceivedController`; follow-up date/time/status and bad-debt actions | `InvoiceFollowUp` imported; no complete bad-debt workflow | **Data only/incomplete.** Add collection tasks and reviewed write-off/adjustment semantics. |
| Offline invoices and collections | `OfflineInvoiceController` | `offline_invoice → Invoice(origin)`, `offline_amount_received → Receipt(origin)` | **Data only.** Preserve origin and implement separate input/numbering/reconciliation rules. |
| Allocate receipt to invoice | New target accounting control; source links provide evidence, not posted allocations | `ReceiptAllocation` exists with positive amount and unique posting key | **Model only.** No service enforces aggregate limits, currency, verification, concurrent posting or reversals. |
| Lead/valuation/recovery MIS and exports | `MonthWiseLeadReportController`, `ReportValuationStatus`, `RecoveryReportStatus`, `DashboardCountListController`, `ReportController` | `/api/summary/` counts cases/services with optional financial-year filter | **Partial preview only.** Legacy month/status/client/area/assessor/responsible-person/service/ageing/invoice/recovery/export reports are missing. |
| File download, lookups and auxiliary screens | `AJAXController`, `PublicController`, `CalculatorController`, `ErrorController`, `TestController` | No equivalent lookup/download suite; Django handles errors generically | **Support pending.** Port needed lookup dependencies and reviewed calculations; test/demo routes do not need automatic production replicas. Messaging/scheduler behavior requires separate evidence. |

## 4. Rules that change the migration design

### A closed lead is not a completed or paid valuation

`WorkOrderGenerateController.java:163` sets lead status to Closed **after successful work-order PDF creation**. `CustomerController` creates a New Lead and can set In Process when services are saved. Therefore an exact replica of the old status labels cannot serve as a single new lifecycle for lead, assessment, approval, dispatch and payment.

Retain the legacy status for history. Define separate operational states for work order, valuation, review, report, invoice and receipt. Establish closure criteria deliberately rather than inferring them from `legacy_status=4`.

### Bank-report data is essential valuation data

`BankReportController.java:133–148` records distress, realizable, book and market/fair values and their word representations. `valuation_bank_report` contains 11,898 source rows in the preserved baseline. The importer does not map this table. An answer import alone cannot reproduce a complete bank report.

### Final valuation fields need active target representation

`ValuationController.saveFinal` stores desired/eligible loan amounts, comments, non-cost factors, submit-to employee and dispatch/report-category fields. Current `Valuation` has no equivalent typed fields for most of these. Their source payload may be retained, but no API uses it for execution. Promote required values with explicit types and provenance; do not silently recalculate historical conclusions.

### Legacy side effects need explicit new commands

Some legacy GET actions create valuation/verification records or delete/change state. Do not replicate unsafe method semantics. Use authenticated POST/PATCH/DELETE commands, CSRF protection, transactions, idempotency where necessary, and explicit permission checks. Read-only detail routes must remain read-only.

### Missing relationships can affect behavior even when counts match

The importer resolves optional relationships and preserves warnings. A remapped service subtype can select a different questionnaire. An unresolved option can obscure the meaning of a grid column. Required fields must be validated by answer type before enabling submission. Inspect historical examples, not only import totals.

### Imported fields are only a subset

`Case` has `asset_district` and `asset_state`, but the current case spec does not populate them. Lead detail renders the district field, so a blank value can appear as Unknown even when source data exists elsewhere. Extend mappings based on verified source columns/lookups before geographic MIS validation.

## 5. The 12 LEAD tables still outside the importer

| Table(s) | Baseline rows | Why they matter |
|---|---:|---|
| `valuation_bank_report` | 11,898 | Assessed values, bank report details and issuance context. |
| `dispatch` | 7,545 | Delivery/dispatch history. |
| `report_setup` | 209 | Report configuration/version candidates. |
| `report_question` | 4,785 | Report content/ordering. |
| `bank_report_heading` | 478 | Report headings/layout structure. |
| `usage_of_reports` | 117 | Usage classification and dependent lookups/rules. |
| `sms_log` | 5,169 | Historical notification evidence; does not prove an active sending service. |
| `report_question_backup`, `report_question_backup_25_08`, `report_question_backup_29_10` | 969 / 161 / 1,441 | Reconcile historical template differences before archival. |
| `report_setup_backup`, `report_setup_backup_25_08` | 40 / 3 | Potential historical report configuration evidence. |

These are seven active/log source tables plus five backup candidates. Backup status is not a deletion decision. Main LEAD coverage is 41 mapped tables out of 53; the other 20 imported sources are UAM shared/payroll/geography data.

## 6. API contracts that execute today

| API | Input | Output/effect | Verified scope |
|---|---|---|---|
| GET `/api/session/` | Existing session cookie, if any | `csrf`, `username`, `staff` | Session bootstrap. |
| POST `/api/login/` | JSON username/password and CSRF token | Authenticated session; refreshed CSRF and username | Staff login; invalid login rejected. |
| POST `/api/logout/` | CSRF token | `{ok: true}` and session logout | Subsequent protected read returns 401. |
| GET `/api/offices/` | `q`, `page` | `count`, `page`, `page_size`, office results | Name/branch/source-ID search; 30-row pagination. |
| GET `/api/leads/` | `q`, `status`, `page` | Lead results with office, date and legacy status | Number/source-ID/office search and status filter. |
| GET `/api/leads/{uuid}/` | Existing lead UUID | Lead, office, contact, cases, issues and notes | Linked case/source identity and warning exposure. No complete valuation detail. |
| POST `/api/leads/{uuid}/` | JSON `{body: "note"}`, CSRF | 201 and refreshed detail | Adds a note only; cannot update status, service, borrower or valuation. |
| GET `/api/summary/` | Optional financial-year start `year` | Counts, service breakdown, source/issue/quarantine counts, latest import summary | Case count filter uses April 1 to following April 1. Other headline entity counts remain global. |

All operational APIs use a broad staff gate. This is suitable for the migration preview; it does not implement per-employee/client/branch or maker/checker authorization.

React calls relative `/api/` URLs with JSON and an `X-CSRFToken` header. During ordinary development Vite proxies these requests to Django. The server, not React, controls authentication and persistence. The four current navigation screens are Overview, Leads, Offices and Import history.

## 7. Execution checks in this review

### Automated

Added `backend/target_core/test_flow_contracts.py`, isolated from other ongoing edits. Its ten tests exercise:

1. Session → staff login → read lead → save note → reread → logout, with CSRF enforcement.
2. Anonymous and nonstaff access rejection.
3. Missing-CSRF rejection on login and note creation.
4. Blank/oversized/non-string note rejection and protection of lead status.
5. Lead and office searches by supported identifiers/fields; status filtering.
6. Multi-page results without overlap and invalid-page rejection.
7. Contact, case source identity and case-level import-warning visibility.
8. Source/accepted-warning/quarantine counts and financial-year boundaries.
9. Invalid login and nonexistent lead handling.
10. Characterization of absent business writes: lead/office creation and lead PATCH rejected; no valuation/order/invoice/receipt/report/dispatch endpoints.

The final test passing means those **gaps were reproduced**, not that those business operations work. Synthetic ORM fixture creation is test setup, not evidence of an operational create API.

The other current tests include schema/access protections and newly added importer regressions for paging, repeat import, required orphans, padded keys, subtype ambiguity, question-option mismatch, storage classification, note preservation and dry-run rollback. These are useful checks but do not execute the missing business APIs or prove complete MySQL refresh parity.

### Browser

The current production React build is tested with a temporary synthetic SQLite database and a loopback-only test server. `database/serve_flow_audit.py` builds that disposable environment and never opens the imported target database. This separates screen behavior from historical-data correctness.

Results: staff sign-in, overview reconciliation counts, lead search by source ID, linked case display, case-level warning display, note creation, session persistence after reload, note persistence after reload, office listing, import-history display and sign-out all passed in the browser. A browser success on this fixture is not evidence of every imported record's correctness, production deployment readiness or full-scale performance.

### Validation note — 17 September 2026

- Full Django suite: **29 tests passed** under `config.settings` and **29 passed** under `config.target`.
- Ten of those are the separate flow-contract checks added in this review; nineteen are the existing/current model, access and importer checks.
- Migration model-state check: no changes detected. The final rerun warned that consistency of the imported database's migration history could not be checked because it was locked. Fresh test-database migrations did apply successfully.
- React production build: passed.
- Browser console: no warning/error entries returned during the checked interaction sequence.
- The temporary browser server was stopped after sign-out, and its synthetic database/account/notes were removed by normal cleanup. Imported business data was not modified by this audit. The test server logged a missing favicon request; it did not affect the checked workflows.
- Browser test used the actual built React code and Django API/middleware with synthetic data. API tests explicitly enforced CSRF for login and note writes.
- These results establish the preview behavior described above, not execution of missing operational flows.

### Limits

The imported `target.sqlite3` returned `database is locked` during two read-only attempts in this review. No process was stopped and no import was interrupted. Import quantities in the inventory come from the saved final report and preserved baseline; they are not fresh database counts for 17 September. During the review, `target-import-corrected.json` appeared: it reports a non-dry-run over 61 tables, 2,537,219 source rows, zero inserts, 150,688 updates, 2,386,323 unchanged, 208 quarantined and 11,950 rows with issues. Those are artifact contents, not an independently confirmed database reconciliation. The current code includes normalization reuse, source-specific storage labels, wrong-question option clearing and visible case warnings; importer tests cover these rules. An unlocked database inspection and full repeat evidence must establish the resulting real-data state.

No production service, original Java runtime, file store, email/SMS provider or bank integration was exercised. Every old endpoint is inventoried, but only the current Django routes can be executed as Django flows.

## 8. Implementation order and acceptance scenarios

| Phase | Implement | Acceptance scenario before proceeding |
|---|---|---|
| A. Finish migration correctness | Reconcile importer fixes, remaining source mappings, source-to-user identities, prototype notes/accounts and full repeat report | Same snapshot reruns without unintended inserts/updates; all repairs visible; notes/accounts preserved. |
| B. Lead operations | Catalogue lookups, clients/contacts, lead create/edit, requested services, borrowers, cases, structured follow-ups, staff scope | Create one lead with two borrowers/multiple cases; edit permitted fields; reject cross-lead links; verify numbering, permissions and rollback. |
| C. Work orders | Fees, numbers, PDF/document generation and revisions | Generate borrower-specific order; verify case membership, retry behavior, document access, history and status semantics. |
| D. Valuation | Dynamic forms, typed answers, repeating rows, photos, submission fields, reviews and returns | Enter/reload all answer formats; preserve separate grid rows; reject wrong-question options; submit, return, correct and re-review with actor history. |
| E. Reports and dispatch | Import/version templates and bank reports; generate approved reports; record dispatch | Reproduce selected historical report values/layout; approve correct version; trace delivered file and dispatch history. |
| F. Finance | Charge calculations, invoice lines/numbers/PDF, receipts, verification, allocations, adjustments and offline flow | Create invoice, receive partial payments, verify/allocate, reverse a correction; prevent double allocation and reconcile outstanding balances. |
| G. MIS and deployment | Legacy report comparisons, role/data scopes, storage, concurrency, backups and cutover | Compare period/client/service/assessor/recovery totals; verify permissions and restore/cutover rehearsal. |

Do not use a single aggregate “migration percent” as permission to enable the next phase. Each flow needs its own input contract, transaction service, permissions, output contract, audit trail, error handling, tests and user-visible result.

## 9. Reproduce this audit

From `omen-next/backend`:

```sh
.venv/bin/python manage.py test
.venv/bin/python manage.py test --settings=config.target
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python ../database/build_flow_inventory.py
```

From `omen-next/frontend`: `npm run build`.

For a synthetic browser check, run `backend/.venv/bin/python database/serve_flow_audit.py` from `omen-next`, use the temporary account it prints at `http://127.0.0.1:8187/`, then stop that test server. It removes its temporary database on normal shutdown. Do not use this test harness as deployment configuration.

Generated appendix: [LEAD_FLOW_INVENTORY.md](LEAD_FLOW_INVENTORY.md). Migration method: [MIGRATION_METHOD.md](MIGRATION_METHOD.md). Prior review: [REVIEW_CLAUDE_DEVIN.md](../REVIEW_CLAUDE_DEVIN.md).
