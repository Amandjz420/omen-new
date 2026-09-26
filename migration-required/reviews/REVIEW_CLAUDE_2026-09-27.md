# Re-review of Claude's changes — 27 September 2026

Reviewed through `37ac554`: dispatch (`4855377`), receipt corrections (`abd2afb`), onboarding/finance corrections (`30d60cf`), and the migration-document relocation. The working tree was clean at review start. No application code or application data was changed. MIS has no new implementation in this commit range and is not certified here.

## Decision

The seven previously reported scenarios are addressed, with regression coverage. Receipt submission, reassignment scope, replay authorization, payment history, verification flags, and credited offline visibility have targeted corrections. Admin password changes no longer loop, but an additional onboarding bypass remains. The new dispatch workflow has correctness gaps. Do not treat this review as production sign-off.

## Confirmed findings

### N1 — P1: Admin onboarding accepts the unchanged issued password

Location: `backend/apps/accounts/admin.py:21–24`.

The wrapper clears must_change_password after the built-in form returns a successful redirect. That form permits the new password to equal the current password. Unlike the API password endpoint, this path never rejects reuse of the issued credential.

Reproduction: create a staff account with must_change_password=True; submit its current issued password as old_password, new_password1, and new_password2. Response: 302; must_change_password becomes False; the admin home returns 200. The account holder has not chosen a different password, yet onboarding is complete.

Fix: enforce the same current/issued-password reuse policy in the admin self-change form as the API before saving and clearing onboarding. Keep another administrator's reset separate. Acceptance: identical-password submission fails and leaves the flag true; a genuinely different valid password completes onboarding.

### N2 — P1: Dispatch accepts an approved valuation without any bank report

Location: `backend/apps/dispatch/services.py:71–73`, reused at `:188`.

The reverse-relation filter bank_reports__superseded_at__isnull=True also matches valuations with no related report: the outer join supplies NULL. Thus it does not establish that a current report exists. The gate also does not require a document link.

Reproduction: use an approved valuation fixture, remove its BankReport record to represent inconsistent/missing report data, then read awaiting dispatch and create a dispatch. Awaiting contains the valuation (total 1), and creation returns 201 with a report item despite there being no BankReport.

Fix: select an actual current approved report and require its dispatchable document, with a deliberate policy for historical records lacking retrievable files. Check again when creating the dispatch. Acceptance: no report, superseded-only reports, and missing-document reports cannot be dispatched as current approved reports.

### N3 — P2: A corrected report revision is hidden by the older revision's dispatch

Locations: `backend/apps/dispatch/services.py:76–77`, `:101`, `:238–240`; `backend/apps/dispatch/models.py`, DispatchItem.

Items reference only a valuation and report-number string, not the BankReport revision or document. The awaiting queue excludes a valuation if any non-cancelled dispatch item references it. Report numbers remain the same across revisions.

Reproduction using workflow APIs: generate and approve revision 0; create its dispatch; final-revert the report; resubmit and verify; generate and approve revision 1. Every transition succeeds, revision 1 is current, but awaiting dispatch returns total 0. The existing item contains no revision/document link to establish which version was sent.

Fix: bind newly created items to the immutable report revision/document sent. Determine awaiting status by the current revision, and distinguish sending a corrected revision from resending an already dispatched copy. Preserve uncertainty for legacy items rather than inventing a historical revision. Acceptance: revision 1 awaits dispatch while revision 0's dispatch history retains its original document reference.

### N4 — P2: Dispatch silently truncates its other-document list

Location: `backend/apps/dispatch/services.py:233–234`.

The document count is computed from the complete submitted list, but other_documents is joined and sliced to 500 characters without rejecting overflow. These documents have no separate DispatchItem rows, so the removed text is lost from the dispatch record and returned detail.

Reproduction: send one report and two other-document labels of 300 characters each. Creation succeeds, document_count is 3, but the returned labels have lengths 300 and 199. Longer lists can lose complete document names while the count still includes them. The React text field imposes no corresponding limit.

Fix: store each document entry structurally, or reject requests exceeding the supported total length with an actionable validation error. Acceptance: all submitted names survive exactly, or the whole request is refused before creating the dispatch.

## Previous review closure

| Finding from 26 September | Current result |
| --- | --- |
| R1 receipt request mismatch | Explicit frontend write fields agree with backend; arrival date accepted and fingerprinted. Creation/correction contract tests pass. |
| R2 stale receipt ownership | Recovery visibility follows its current invoice; offline reassignment clears the old valuation/borrower. Non-recovery ownership retention is now explicit and tested. |
| R3 unauthorized replay | Cached receipt responses now check current visibility before returning. Revoked-grant test passes. |
| R4 admin onboarding loop | Successful self-change clears the flag; failed change and another administrator's reset do not. New same-password bypass remains as N1. |
| R5 missing receipt history | Verified, non-voided recoveries appear in invoice history; unverified and duplicate representations are excluded by tests. |
| R6 verification flag | New verification updates the flag atomically. Import mapping and tests cover historical verification flags; full historical reconciliation was not rerun in this review. |
| R7 credited offline visibility | Credited offline invoices remain in the cancelled queue for permitted users. Scoped-user exclusion is tested. |

## Evidence and limits

- Full suite under config.settings on SQLite: **352 tests passed**, 36.870 seconds.
- Frontend production build passed (32 modules).
- Migration drift check: no changes detected.
- Four additional defects above reproduced against a separately migrated in-memory database with synthetic fixtures. Temporary reproduction script: `/tmp/omen_review27_repro.py`.
- Full suite under config.target on a disposable PostgreSQL test database: **352 tests passed**. The application database was not modified.
- No browser acceptance pass, fresh full source import, application-data reconciliation, deployment, or attachment-storage audit was performed. Existing import evidence was not treated as a fresh independently verified run.
- No business-role redesign was undertaken; that remains deferred by the owner. This review concerns current behavior under the existing access model.

## Next steps

1. Close N1 and require an actual dispatchable report for N2.
2. Bind dispatch history and its awaiting queue to report revisions (N3).
3. Eliminate silent document-list truncation (N4).
4. Add these negative and cross-workflow cases to automated coverage, then browser-test receipt creation/correction/verification and report revision-to-dispatch end to end.
5. Review MIS separately when its implementation is available.
