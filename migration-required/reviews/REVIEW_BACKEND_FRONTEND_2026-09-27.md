# Backend and frontend readiness review — 27 September 2026

## Scope and decision

Review began at UI-foundation commit `1a44c1a`. Claude committed corrections during the review; the final backend checkpoint is **`fd52f72`**, including password correction `94378d0`. Final backend tests use an isolated archive so concurrent working-tree edits cannot affect the result. No application code or application data was changed by this review. Browser writes used a separate synthetic database and temporary servers.

**Not ready for operational sign-off.** The previous four findings N1–N4 are now addressed, but five confirmed issues remain. The new interface successfully hosts important existing workflows; it is a foundation and integration phase, not complete frontend or MIS parity.

## Findings

### BF1 — P1: Restricted assessors can read and annotate somebody else's leads

Locations: `backend/apps/leads/api.py:23`, `:35–43`, `:44–52`.

The lead list and detail endpoints use unscoped querysets. The staff gate does not enforce the assignment restriction already used by valuation and stage APIs. Note creation also happens before any object-level access check.

Synthetic reproduction: assign a lead to employee A and sign in as a different assessor with role 157. The lead list includes A's lead; its detail returns 200 with case information; a note POST returns 201 and persists. The same lead's stages endpoint returns no cases, demonstrating that the intended restriction exists but is applied inconsistently. Contact and note fields are also serialized by the unscoped detail path.

This is an existing unresolved access defect, not a request to design the deferred business-role policy. Apply the current shared scope policy consistently to listing, detail, and note writes. Test assigned, reassigned, unassigned, and revoked-access cases, preserving authorized head-office access.

### BF2 — P1: The HTTP-phone UUID fallback recurses indefinitely

Locations: `frontend/src/lib/uuid.js:5–6`, `:16`.

When native crypto.randomUUID is absent, module initialization assigns uuid itself to crypto.randomUUID. Calling uuid then sees that method and calls itself again. This is the environment the fallback specifically intends to support: phones opening an office server over HTTP rather than HTTPS/localhost.

Reproduction: evaluate the module in a JavaScript context with crypto.getRandomValues but no native randomUUID; invoke the installed method. It throws RangeError: Maximum call stack size exceeded. Workflow screens call this method for receipt creation, work-order requests, invoice operations, and dispatch. The existing test removes the native method after importing the module, missing the initialization path.

Fix: retain the original native function separately or install an independent fallback implementation that never calls the installed wrapper. Test initial module loading without native randomUUID and exercise a UUID-dependent workflow. Localhost browser checks do not reproduce this environment, so passing them does not close this finding.

### BF3 — P2: The stage track claims incomplete or reverted work is complete

Location: `backend/apps/leads/stages.py:52–59`.

The tracker marks every stage before the latest completed stage as done. These workflows are not a strict sequence: dispatch does not prove payment, invoices can exist before final approval, and historical invoices remain after a report is reverted.

Reproduced on `fd52f72`:

- A delivered dispatch with an unpaid invoice shows Payment as done while its detail says ₹1,180 outstanding.
- After final revert, an existing invoice makes valuation, verification and approval appear done despite 0 of 4 checks and withdrawn approval.
- Putting that reverted valuation on hold still shows the valuation done instead of stopped.

The new dispatch-revision correction is good, but does not fix this broader inference. Compute each stage from its current authoritative records; distinguish historical/inferred evidence from confirmed completion; give hold, cancellation and reversion precedence where appropriate. Tests should cover delivery before payment, invoice before approval, and post-invoice reversion/hold.

### BF4 — P2: Dashboard errors silently hide work queues

Locations: `frontend/src/screens/Home.jsx:29–37`, `:47`.

Every failed request is classified as missing and its row removed. A server error, lost connection or expired session therefore looks like an unavailable/empty workload rather than a failure to load it.

Component reproduction: make all ten queue requests return HTTP 500. Only the table header remains; there is no error, retry control or explanation. A partial failure silently removes only the affected work, understating what is waiting.

Fix: distinguish explicit access denial from operational errors. Keep the affected queue visible with an unavailable count and retry action; handle session expiry centrally. Test both complete and partial outages.

### BF5 — P2: Lead header and stage track stay stale after successful nested edits

Locations: `frontend/src/screens/Leads.jsx:60–61`, `:94`; `frontend/src/workorders.jsx:63–67`.

LeadDetail caches its lead and stage responses, but its embedded workspace does not notify those queries when intake or work-order operations succeed. The workspace refreshes only its own intake child.

Component reproduction using the real WorkOrders component: issue the last borrower's work order successfully. ORDER-1 appears and the lower panel says the lead closed, while the top header still says In process and the stage track still shows Work order as current. Both parent endpoints were fetched only once.

Fix: propagate successful mutations out of the embedded workspace and invalidate/refetch the lead, its stages, and relevant lead-list/dashboard queries. Test the entire visible page after issuance and intake changes, not only the mutated child panel.

## Previous findings: now corrected

| Previous finding | Fresh reproduction after the fixes |
| --- | --- |
| N1: unchanged issued password completes admin onboarding | Same-password submission is rejected; flag stays pending and admin home remains gated. |
| N2: dispatch without a bank report | Missing report is absent from awaiting and dispatch POST returns 400. |
| N3: corrected revision hidden by the earlier dispatch | Revision 1 appears in awaiting; revision 0's item retains its BankReport relationship. |
| N4: document-list truncation | Oversized list returns 400 and creates no dispatch. |

These results close the specific earlier reproductions. They do not certify attachment availability, all possible dispatch concurrency scenarios, or full legacy parity.

## What was exercised

- Frontend unit/component suite: **13 tests passed**; production build passed. The only build warning observed was that intake is both statically and dynamically imported, so it is not a separate lazy chunk.
- Two additional temporary component reproductions confirmed BF4 and BF5. A separate module-initialization reproduction confirmed BF2.
- Synthetic backend reproductions confirmed BF1 and BF3 and rechecked N1–N4.
- Manual in-app browser checks against an isolated backend: sign-in, dashboard loading, valuation list, opening a valuation, saving required answers, phone navigation, receipt creation and correction. The saved valuation showed required 2/2 and Saved; receipt amount changed from 10 to 12 after correction.
- At a 390-pixel viewport, the inspected valuation and receipt screens settled to document width 390 with no page-level horizontal overflow; the phone menu opened and navigated successfully. No browser console errors were captured in that exercise.
- Final fixed snapshot `fd52f72`: **408 tests passed under config.settings on SQLite** (74.060 seconds) and **408 under config.target on PostgreSQL** (122.812 seconds). Migration drift check reported no changes. Tests used disposable databases.
- A lead opened at its individual address and retained its detail page after refresh. Temporary review servers were stopped and the temporary browser tab closed after testing.
- An intermediate PostgreSQL run overlapped Claude's model/contract edits and failed an architecture comparison. That mixed-working-tree run is not evidence against a committed revision; it was replaced by fixed-snapshot validation.

## Completeness and limits

- No new MIS screen, route or full MIS implementation exists at this checkpoint. Analytics still exposes the earlier summary API.
- The new shell, authentication screens, lead views and stage display are implemented. Valuation, verification, bank reports, approvals, finance and dispatch still use the carried-over workflow components inside the shell.
- Device-draft storage and the shared confirmation component exist but are not connected to the operational forms. Offline data-entry recovery is therefore not established by this change.
- Most carried-over record details still live in component state rather than individual routes. Lead record URLs are implemented; the same guarantee does not yet apply to every workflow record.
- No fresh full source import, production deployment, real customer-data mutation, complete browser journey through every module, or external file-store audit was performed.

## Recommended order

1. Fix BF1 access checks and BF2 UUID initialization before allowing assessor usage.
2. Correct BF3 stage semantics and BF5 refresh behavior together so the displayed state is both accurate and current.
3. Add BF4 explicit dashboard failure handling.
4. Run browser acceptance with restricted users, HTTP-phone conditions, network failures, and the report-to-invoice-to-dispatch lifecycle.
5. Define and implement the remaining MIS and offline-form scope before describing the whole frontend/backend migration as ready.
