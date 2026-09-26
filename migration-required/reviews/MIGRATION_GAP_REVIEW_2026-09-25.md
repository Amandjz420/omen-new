# Expanded migration gap review — 25 September 2026

## Verdict

The main LEAD journey now has substantial Django and React implementation: intake → work order → valuation → submission → four verification tracks → bank report → approval → invoice/payment. This is substantially beyond the previous intake checkpoint. It is not yet a complete, reliable replacement for the legacy LEAD application.

The remaining work comprises defects in implemented workflows, imported data that cannot yet be operated on, missing workflows, and cutover validation. Table-import acceptance alone cannot measure completion.

## Reviewed checkpoint and evidence

- Stable code reviewed: `ebaf68b`, including the valuation, verification, bank-report, approval and invoicing commits after `c9482e6`.
- Reproductions ran against a separate archive of that commit with synthetic records in an in-memory database. Existing application data was not modified.
- Full suite on a separate PostgreSQL test database: **260 tests passed under `config.settings` and 260 under `config.target`**.
- Committed snapshot migration drift check: **no changes detected**. Frontend production build: **passed**.
- Receipt fields, importer edits and migration `0020_receipt_amount_received_on_receipt_checked_at_and_more.py` were uncommitted during review. They are in progress, not counted as finished workflows. No application code was changed by this review.
- Examined legacy controllers for dispatch, cash receipts, offline invoicing and MIS, alongside the Django route map, importer and React screens. This is a focused migration review, not a claim to have verified every legacy method or every imported row.

Stored evidence in `target-repeat-invoicing.json` reports **73 source tables, 2,641,787 rows, 2,641,578 unchanged accepted rows, 209 quarantined rows and 11,971 rows with issues**, with zero inserts/updates proposed. These are Claude's retained reconciliation results, read during this review; I did not rerun the multi-million-row import. Investigate the issues and quarantines as a tracked exception register rather than equating acceptance with business correctness.

## Confirmed defects in implemented features

### G1 — P1: An outdated bank report can receive final approval

Code: `backend/target_core/approvals.py`, `final_revert` and `approval_blockers`; `verifications.py`, `revert`.

An unapproved report is left current when a valuation is sent back. After answers are corrected, resubmission and verification restore eligibility for approval without requiring PDF regeneration. Approval checks that a document exists, not whether it represents the current answers.

**Reproduced:** generate a report containing construction year 1999 → send it back → change the answer to 2025 → resubmit → verify all four tracks → approve without generating another report. All writes return HTTP 200. Approval retains the same document; its extracted text contains 1999 and not 2025.

**Fix:** invalidate the draft on either revert path and bind report generation/approval to a valuation revision or content fingerprint. Block approval until the report represents the latest submitted and verified revision. Cover both verification-stage and final-stage send-backs.

### G2 — P1: Valuation read/save still destroys historical answer distinctions

Code: `backend/target_core/valuations.py`, `answer_of`, `save_section`, `reconcile`; `frontend/src/valuations.jsx`, section save.

**Reproduced again at the latest commit:** two stored answers for the same grid cell in group 7 become one answer in group 1 after GET and PUT of the section, without an intended change. The serializer collapses duplicates, the frontend submits every question, and saving renumbers groups.

The newer reconciliation code improves document preservation for matching keys, but explicitly collapses duplicate answers. Renumbered groups also cease to match their existing answers and attachments. This only partially addresses the previous review finding.

**Fix:** preserve answer identities, groups and documents; explicitly handle ambiguous historical values; submit intentional edits and retain answer-level before/after evidence. Add unchanged-round-trip tests using realistic duplicate cells and non-contiguous groups.

### G3 — P1: Payment retries book money twice

Code: `backend/target_core/invoices.py`, `payment` (receipt creation and paid-total increment).

There is no payment operation identifier or deduplication key. An identical retry creates another receipt and increments the paid total again. Row locking serializes the writes but does not deduplicate them.

**Reproduced:** the same 100 payment request sent twice changes paid from 100.00 to 200.00 and produces two receipts. This matters when a successful response is lost and a user retries. Two genuinely separate equal payments must remain supported.

**Fix:** introduce a client-generated operation ID with a database uniqueness rule, bind it to the request payload, and return the original result for a retry. Apply the same reasoning to write-offs and other additive financial operations. Test response-loss retries.

### G4 — P2: Offline invoices are invisible in the invoice queues

Code: `backend/target_core/invoices.py`, `queue`, especially `Invoice.objects.filter(valuation__case__in=cases)`; `sync.py`, offline mappings.

Offline invoices are imported without a valuation relationship. Every invoice queue requires that relationship, so the offline population is excluded. The stored import report accounts for **1,396 offline invoices and 991 offline payment rows**; operational import completeness therefore differs from UI completeness.

**Reproduced:** an existing offline invoice with an outstanding balance is absent from the unpaid queue. This happens for an unrestricted staff user as well.

**Fix:** provide a deliberate offline invoice workflow and scope based on its own client/ownership relationships. Preserve and expose its payment history, numbering and reconciliation rules. Do not invent a valuation to force it into the online flow.

### G5 — P2: Billing totals can disagree with the lines retained in the database

Code: `backend/target_core/valuation_billing.py`, `save`.

Totals are computed from the submitted lines, while existing lines omitted from the request remain stored. The API accepts this inconsistent combination.

**Reproduced:** stored lines of 1000 and 100; submit only the first line changed to 2000. The API returns HTTP 200 and stores total 2000, while the stored lines sum to 2100. Invoicing subsequently reads all stored lines. A retired head omitted by the current-head form presents a related risk even when the frontend submits its full visible form.

**Fix:** choose and enforce replace-all or partial-update semantics. Compute totals from the final persisted set. Preserve/review retired historical charges explicitly rather than making them disappear from the form.

### G6 — P1: Generic admin still bypasses business services

Code: `backend/target_core/admin.py`, `OwnedAdmin.save_model` and generic registrations.

**Reproduced again:** the registered Lead admin form accepts a lead with an empty number, no local sequence and no IntakeAudit entry. Work orders, answers, reports and invoices also retain generic model editing rather than the API's workflow enforcement. This undermines assumptions such as invoice immutability and approval locks.

**Fix:** use shared services for workflow actions or make workflow models read-only in admin pending specialized forms/actions. Keep safe directory maintenance available. This is needed even when only trusted administrators use the site.

### G7 — P1: Removing an assessor grant expands access

Code: `backend/target_core/valuations.py`, `scoped_employee`.

**Reproduced again:** requesting another employee's valuation returns 404; deactivating the user's sole assessor assignment makes the same session receive 200. An empty grant set is interpreted as unrestricted access. Eligibility checks also need the role-definition and project validity conditions used in provisioning.

**Fix:** deny linked accounts with no eligible grants, reserve unrestricted access for an explicit valid administrative/broad role, and test existing sessions after grant changes. Final business-role design can remain deferred; this existing restriction must still fail safely.

### G8 — P2: Automatic password rehash bypasses onboarding

Code: `backend/target_core/views.py`, `onboarding_pending`.

**Reproduced again:** authenticating with the unchanged issued password upgrades an older PBKDF2 hash; the different encoded string clears the password-change requirement. A hash upgrade is not a password change.

**Fix:** clear onboarding through explicit successful password-change/reset flows rather than encoded-hash inequality. Include an automatic-rehash regression test.

## Remaining business coverage

| Area | What exists | Remaining gap / acceptance condition |
|---|---|---|
| Lead intake and work orders | API, React forms, numbering, generated work-order PDF and lead closure | Cross-check editable fields and correction routes against the legacy flow; eliminate admin bypass; exercise simultaneous number allocation and the full journey. |
| Valuation capture | Six answer types, billing, photos/documents, required-question submission | G2 and G5; realistic historical answer/attachment round trips; validate all needed source values are usable, not only staged. |
| Verification | Four queues, named reviewers, dates/remarks, reversion history | Final separation of duties is deferred. Test correction cycles and report invalidation across all four tracks, not just independent happy paths. |
| Bank report and approval | Templates, PDF generation, assessed values, revisions, approval/hold/cancel | G1; compare representative actual legacy outputs. Superseded document metadata is returned, but the committed download route selects only the current report; provide access to preserved historical revisions. |
| Online invoices | Issue, calculated tax lines, PDF, payments, write-offs, full credit notes | G3; reconcile historical balance/line disagreements; make refund/adjustment follow-through explicit. A credit note records refund due but is not a refund settlement workflow. |
| Historical payments | Receipt records imported | `invoice_json` lists only `origin='local_invoice_payment'`. Existing receipts and valuation-linked amount-received records need an intelligible payment history and reviewed matching, without double-counting different legacy representations of one payment. |
| Cash receipt checking and verification | Legacy receipt data; additional fields/mapping in progress | No committed equivalent of the legacy maker/checker/verification queues and commands. Define which status changes affect invoice balances, add audit/reversal and duplicate-settlement protection. |
| Offline invoicing | Invoice and payment imports | G4; operational create/view/payment/collection flow, source field coverage and dedicated reconciliation. |
| Dispatch | Historical Dispatch/DispatchItem and linking command | No committed dispatch API or React workflow. Implement creation, report-version association, delivery mode/reference, history and corrections. Imported dispatch history is not delivery capability. |
| SMS/email | Imported SMS history | No operational notification sender/retry/delivery tracking found. Decide the required legacy side effects, then implement or explicitly retire them. Never send messages merely as a side effect of migration replay. |
| MIS / recovery / exports | Summary counts and operational queues | Legacy monthly leads, valuation status, recovery/ageing, invoice reports, filters and exports need their own implementation and period-by-period comparison. Queue counts are not MIS parity. |
| Existing file bytes | Document metadata; local upload/download works | `files.serve` rejects non-local storage. Retrieve and verify the LEAD S3 files and any retained UAM local files; inventory missing objects and reconcile links/checksums. A successful database import does not establish that reports/photos can be opened. |
| Master data and report setup | Generic Django admin over models | Validate template completeness/ambiguity, service/subtype links, ordering and retired options. Changes must not silently alter historical report meaning. |
| Identity and access | Accounts, password setup and interim access | G7/G8 now; final role matrix and separation of duties later as requested, before wider user rollout. |
| Migration repeat / cutover | Direct importer, SourceRow/SourceIdentity, ownership protection and saved repeat reports | Fresh reconciliation at a stable checkpoint; exceptions resolved or accepted individually; one complete edited-record replay; file backup/restore and PostgreSQL recovery rehearsal; controlled switch from legacy writes. |

The legacy evidence for missing operational areas is concrete: `CashReceiptController` has checker/verify lists and `/verify/save`; `OfflineInvoiceController` has offline payment entry/history; `DispatchController` has save, edit and report-specific history; `MonthWiseLeadReportController` and recovery controllers have monthly/status/recovery searches and exports. Those do not have equivalent committed Django routes yet.

Attendance history remains deliberately excluded. Documentation also records PRAYAS/PAYROLL continuing in legacy UAM; they are outside this LEAD review, not certified as migrated. If the eventual goal remains replacing all of UAM too, that needs a separate explicit scope and acceptance matrix.

## Documentation and validation gaps

README still says work orders, valuation, finance and report output are future work. VALIDATION mixes 72-, 90-test and earlier access checkpoints and ends with limitations contradicted by newer implementation. The old flow audit is likewise historical. Rewrite the current-state sections around a single commit, retain dated history separately, and link each claimed capability to a regression or acceptance test.

The current passing suite is useful evidence, but did not catch the eight reproductions above. This review did not run a production cutover, fetch legacy file bytes, certify tax rules, perform real-user browser acceptance, or reconcile every source payload to a typed field. Avoid describing these as completed based on build/test success.

## Recommended order for Claude's next work

1. **Stabilize and correct existing features:** G1/G2/G3/G6 first, then G4/G5/G7/G8. Keep final role design deferred but repair existing access/onboarding behavior.
2. **Finish finance:** receipt lifecycle and verified allocations, imported payment history, offline invoices, correction/refund/adjustment handling and retry safety. Reconcile balances across all representations.
3. **Finish delivery and files:** legacy object retrieval, historical report downloads, dispatch linked to the issued version, and required notifications.
4. **Implement MIS:** enumerate each retained legacy report, its inputs/formula/filters/output, and compare selected historical periods and edge cases.
5. **Prove the integrated migration:** create a synthetic lead through payment/dispatch, correct it, repeat the import, and verify preserved answers/documents, unique numbers, audit records and balances. Then validate concurrency, permissions, backup restoration and cutover.

Use a stable commit and updated evidence for the next independent review. Do not use a percentage-complete estimate until every retained flow has an agreed acceptance test.
