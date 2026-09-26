# Claude review — non-MIS changes, 26 September 2026

## Scope and conclusion

Reviewed committed code through `8275971`, using an isolated archive of that commit. This covers the eight earlier corrections, offline invoicing, duplicate receipt linking, and the maker/checker/verifier receipt workflow. MIS and concurrent, uncommitted dispatch changes are excluded. Application code and application data were not changed during this review.

The earlier corrections are substantial, but this revision is not ready for operational sign-off. Seven defects below were reproduced using synthetic records. In particular, the actual receipt form cannot save and some receipt reads bypass the intended scope.

Source locations below refer to commit `8275971`; later edits may move lines.

## Confirmed findings

### R1 — P1: Receipt creation and correction reject the React request

Locations: `frontend/src/receipts.jsx:9`, `:76`, `:129`; `backend/apps/billing/receipts.py:53`, `:194`, `:229`.

The new form always sends `amount_received_on`, including when blank, but the backend's permitted FIELDS omit it. Creation therefore returns HTTP 400, `Unexpected fields in request`. Correction spreads the receipt response into form state and sends response-only fields, including invoiceInfo, along with an operation_id that the correction endpoint does not permit. Its request also returns 400.

Required correction: define an explicit write payload for creation/correction; permit and validate the arrival date; include it in the idempotency fingerprint. Add contract tests using the complete payloads React actually sends. Acceptance: create with and without an arrival date, then correct an unchecked receipt through the UI.

### R2 — P1: Reassigning a receipt preserves old ownership and exposes the new invoice

Locations: `backend/apps/billing/receipts.py:65`, `:147–158`.

Cleaning a recovery fills valuation, office, and borrower only when the selected invoice has a valuation. Changing an online recovery to an offline invoice leaves the old valuation and borrower attached. The visibility query still admits the old borrower's assigned assessor, while receipt serialization includes the newly selected invoice's details.

Reproduction: correction to an offline invoice returned 200 and retained the previous valuation and borrower. The old assessor received 404 for the offline invoice itself but 200 for the receipt containing its invoice details.

Required correction: explicitly recompute or clear all derived links on every reassignment; scope recovery access through its current invoice. Define ownership deliberately for advances and other receipts. Acceptance: test online-to-offline, online-to-other, and online-to-online changes against both the previous and new staff scopes.

### R3 — P2: Receipt retry returns data after access has been revoked

Location: `backend/apps/billing/receipts.py:193–207`.

The cached operation lookup returns receipt_json before checking current visibility. A user can reuse their own known operation ID after losing their grant. In the reproduction, the direct receipt read returned 404 after revocation, but replaying the original creation request returned 200 with the receipt.

Required correction: authorize access to the existing receipt before returning a cached success. Preserve legitimate retry behavior without duplicating the receipt. Acceptance: a retry after revocation or reassignment cannot disclose the record, while an authorized identical retry remains idempotent.

### R4 — P1: Changing one's password in Django admin leaves onboarding blocked

Locations: `backend/apps/accounts/api.py:12–24`; `backend/apps/accounts/middleware.py`; Django admin's own password-change route.

The new explicit onboarding flag correctly prevents a password-hash upgrade from completing onboarding. However, the built-in admin self-password-change flow does not clear that flag. A successful password change was reproduced: the new password worked, but must_change_password stayed true and the next admin-home request redirected back to `/admin/password_change/`.

Required correction: connect successful authenticated self-password changes to the onboarding policy, or route onboarding through the existing explicit password endpoint. Do not reintroduce hash comparison; an administrator resetting somebody else's password should not silently complete their onboarding. Acceptance: test API self-change, admin self-change, automatic hash upgrade, and another administrator's reset separately.

### R5 — P2: Verified receipts settle an invoice but are absent from its payment history

Locations: `backend/apps/billing/services.py:133`, `:187–190`.

Invoice payment serialization allows only local_invoice_payment and legacy_offline_amount_received. New local_cash_receipt recoveries are excluded. Reproduction: verifying a receipt increased the invoice's paid amount to 500.00, while its payments array remained empty.

Required correction: expose actual settlements in invoice history, including verified recoveries, while honoring duplicate links and excluding unverified receipts. Acceptance: verification adds one visible settlement; retry adds none; duplicate representations do not inflate either the history or balance.

### R6 — P2: Verification leaves conflicting states on the receipt

Location: `backend/apps/billing/receipts.py:270–271`.

Verification sets verified_by and verified_at but leaves the existing verified Boolean false. The reproduced receipt was at stage verified and had settled its invoice, yet verified was false. Admin columns and filters using that Boolean consequently disagree with the operational workflow.

Required correction: establish a consistent verification state across the workflow and admin. If retaining the Boolean, update it atomically and reconcile existing records with explicit treatment of imported provenance. Acceptance: a newly verified receipt is consistently classified in its API response, detail page, admin list, and filters.

### R7 — P2: Credited offline invoices disappear from the finance queues

Locations: `backend/apps/billing/services.py:503`, `:523–528`.

The offline queue excludes cancelled invoices, while the cancelled queue starts from invoices linked to valuation cases. Offline invoices have no such link. After crediting an offline invoice, the reproduction found it in neither queue, although the record still existed.

Required correction: include permitted offline invoices in cancelled/credited history and retain clear labels and document access. Acceptance: an offline invoice can be found from the finance interface after crediting without knowing its UUID in advance.

## Earlier findings: what now works

| Earlier finding | Review result |
| --- | --- |
| G1: stale bank-report approval | The original answer-change scenario is addressed by report fingerprints and approval validation. This does not certify every possible report dependency. |
| G2: historical answer rewriting | Group preservation, unchanged-cell handling, explicit conflict resolution, and dirty-question submission address the original behavior. |
| G3: duplicate financial retries | FinancialOperation keys, payload checks, and invoice locking address the original payment/write-off issue. R3 above is a separate authorization gap in the new receipt retry path. |
| G4: offline invoice handling | Active offline invoices have their own queue and balance/payment handling. Credited history remains incomplete: R7. |
| G5: billing line totals | Totals are recalculated from stored lines, including retired heads; conflicting duplicate changes are rejected. |
| G6: admin workflow bypass | Workflow records are now view-only in admin; reference data remains separately editable. |
| G7: removed assessor grant | The shared scope resolver no longer broadens access when no eligible grant remains. New receipt paths still need R2/R3. |
| G8: password rehash bypass | Automatic rehash no longer completes onboarding. Admin self-password change requires R4. |

These statements concern the original scenarios and reviewed code paths, not a guarantee that every business workflow is complete.

## Validation evidence and limits

- 325 tests passed under config.settings in an isolated PostgreSQL test database.
- 325 tests passed under config.target in the same separately managed test environment.
- Frontend production build passed from the committed snapshot.
- Migration drift check reported no changes, using SQLite settings against the snapshot.
- Separate synthetic, migrated in-memory database reproductions confirmed all seven findings. React-shaped requests were exercised through Django's test client; a browser acceptance pass was not performed.
- No fresh full legacy import, source-to-target reconciliation, real attachment retrieval, or production deployment was performed. Existing import counts and deployment readiness are not newly certified by this review.
- Duplicate-linking code was inspected; existing links were not reconciled against a fresh source snapshot. Future source corrections and ambiguous matches need their own reconciliation coverage.

The standalone review runner and reproduction logs were kept under `/tmp/omen_review26*` and `/tmp/omen-review26*`; temporary files are not durable project artifacts. The source locations and reproduction descriptions above are the durable handoff.

## Recommended next sequence

1. Fix the receipt write contract, scope on reassignment, and scope on retries before operational use.
2. Fix admin self-password onboarding without weakening the explicit onboarding gate.
3. Reconcile invoice payment history, verification state, and credited offline visibility.
4. Add the acceptance scenarios above to the suite and execute the complete receipt journey in React: create, correct, check, verify, view invoice settlement, and retry.
5. Review MIS and dispatch separately once their current changes are committed, then perform a broader cross-module acceptance pass and fresh migration reconciliation.
