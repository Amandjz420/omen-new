# Response to the backend and frontend readiness review — 27 September 2026

Response by Claude to `REVIEW_BACKEND_FRONTEND_2026-09-27.md`. All five findings are
confirmed and fixed. Each fix has regression tests that fail against the reviewed
code and pass now.

| Finding | Commit | Fix | Regression evidence |
| --- | --- | --- | --- |
| BF1 (P1) restricted assessors read and annotate others' leads | `3fa2c96` | `scope_leads` and `require_lead` beside `scope_cases`, on the same `scoped_employee` decision, applied before any read or write | 7 tests; 5 fail on the reviewed code |
| BF2 (P1) HTTP-phone UUID fallback recurses | `3fa2c96` | The native function is kept separately; the installed fallback is independent of `uuid()` | Unit and browser tests remove `randomUUID` before load; both reproduce the `RangeError` on the reviewed code |
| BF3 (P2) stage track claims incomplete or reverted work complete | `c237ab6` | Each stage from its own current records; hold and cancellation take precedence; a pre-approval invoice is labelled | Your three scenarios plus one more fail on the reviewed logic |
| BF4 (P2) dashboard errors hide queues | this commit | Denials (403, 404) hide a queue; other failures keep it visible as unavailable, with retry and a notice; a 401 anywhere returns to sign-in centrally | 4 tests; complete outage, partial outage and session expiry fail on the reviewed code |
| BF5 (P2) lead header and stage track stale after nested edits | `c237ab6` | Both workspace panels report changes; the lead page refetches the lead, stages, lead list, dashboard and MIS | Real `WorkOrders` issuance test and an intake-save test; both fail on the reviewed code |

## Beyond the reported findings

- **BF1 was wider than reported.** The intake lead detail and children and all four
  work-order endpoints had no scope check, so an assessor could also add a borrower
  to another's lead and issue a work order on it (the reviewed code answered 201).
  All are scoped now. A lead outside scope answers exactly as a missing one, and the
  stages endpoint returns 404 instead of an empty list. A replayed work-order
  request is re-checked.
- **BF3 needs no inference on the real data.** All 12,650 valuations have their work
  order linked and all 11,896 approved valuations have four checks recorded; the old
  rule only misreported the 42 standing invoices on valuations that are not approved.
- **The intake chunk warning** you noted is resolved: the lead workspace loads lazily.

## Correction to the review's limits

The review was taken at `fd52f72`. Since then the MIS has been built (`01e6ce8`,
`d4db9f8`, `22a3334`): all 24 legacy reports on one engine, with Excel export, a
Reports workspace, and `manage.py reconcile_mis --settings=config.full_database`,
which matches every legacy query that was correct and documents ten legacy defects
in `migration-required/data-migration/MIS_LEGACY_QUERIES.md`.

## Still open, as the review says

- Browser acceptance with restricted users, a phone over plain HTTP, network
  failures, and the report-to-invoice-to-dispatch lifecycle.
- The device-draft store and `confirmAction` are not yet used by the operational
  forms; offline data entry is not established.
- Carried-over workflow records do not yet have their own addresses.
