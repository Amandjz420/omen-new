# Independent migration review

Reviewed 16 September 2026. Verdict: substantial data-import progress, but the handoff acceptance gate is not passed. This review did not modify application code or imported business data.

## Verified evidence

- The final import committed. Its report matches the latest database ImportBatch summary.
- 61 source tables; 2,537,219 SourceRow records; 2,537,011 SourceIdentity records; 208 quarantined rows. The reported 99.992% acceptance is numerically accurate.
- 1,947,183 valuation answers are in the target. The EAV model retains answer_group and does not impose the proposed composite uniqueness constraint.
- Quarantine reasons in the target are missing/quarantined required parents. This review did not independently re-query MySQL to prove that every such failure is a direct dangling source FK rather than a cascade.
- Eight tests pass under each of config.settings and config.target. Migration generation reports no changes. Frontend production build passes.
- Cash receipts retain 8,837 invoice references out of 11,207 receipts; all 1,519 amount_received records retain valuation references. These links are not posted receipt allocations or financial reconciliation.
- The final report records 11,948 rows with issues, including quarantines. Acceptance alone is not a measure of semantic correctness.

## Findings requiring correction

### P1 — Valuation answer relationships are not fully validated

Two imported ValuationAnswer rows reference a QuestionOption whose question differs from the answer's question. The generic importer checks existence but never checks this relationship. A renderer can therefore associate an answer with an option/column from another question. Preserve the original source evidence, flag these conflicts, and resolve or leave the optional link unset according to documented rules. Add a regression test.

Additionally, 11,567 source rows have the sole warning `Unmatched optional parent: option_id`. This is not automatically data loss: original payloads remain. It does require profiling by answer type and tracing legacy rendering rules before claiming the reconstructed forms are complete. Record whether each unresolved option is irrelevant to its answer type or prevents interpretation of an option/grid cell.

Location: backend/target_core/sync.py, generic relationship resolution around lines 269–283 and semantic checks around 294–312; valuation_answer spec.

### P1 — The zero-padding fix is bypassed by later relationship checks

The generic FK resolver accepts zero-padded numeric references, but Case/WorkOrder validation then indexes the borrower map using the original unnormalized string. Valuation checks do the same for order and case. A valid padded reference can pass initial resolution and then raise an uncaught KeyError, rolling back the entire import. Office/subtype checks can instead silently skip validation when their unnormalized lookup misses. Reuse the resolved objects for all later checks. Test padded borrower, order, case, branch and subtype IDs, not only geography.

Location: backend/target_core/sync.py:286, 295, 307–310.

### P2 — UAM files receive the wrong storage classification

All 50 imported uam_user.upload documents currently have storage_provider=legacy_lead_storage. The importer applies that value to every Document, regardless of source schema. The supplied deployment inventory says UAM uses local server storage while LEAD uses S3. Select the provider by source and keep unknown container details explicit. This is a metadata defect; no file retrieval was tested.

Location: backend/target_core/sync.py:290.

### P1 — Required importer/API regression coverage is still absent

The eight tests are the existing model/access-protection checks. There are no new pipeline tests, no prototype adoption command, and no replacement for the archived API/auth/CSRF/note regression coverage. Passing these tests does not establish correction handling, rollback, duplicate rejection across page boundaries, account/note preservation or end-to-end UI behavior.

The saved zero-change repeat report covers 60 tables and 589,857 rows. The saved 61-table dry run predates the answer import and proposes 1,947,183 inserts. It is not evidence for idempotency of the full streaming pipeline. Run and retain a full 61-table post-import repeat report after fixing the defects.

Locations: backend/target_core/tests.py; backend/target_core/management/commands/; database/target-repeat-2.json; database/target-dry-run-4.json.

### P2 — The UI hides corrected and unresolved case classifications

Case serialization always emits an empty issues list, even when the importer remaps or clears a subtype. The UI consequently presents the inferred subtype without its warning. Overview labels say all retained source records while displaying accepted target rows, and the quarantine total returned by the API is not displayed. Surface case-level issues and distinguish source, accepted, warned and quarantined counts.

Locations: backend/target_core/views.py, lead_detail case serialization; frontend/src/main.jsx:62–65.

## Other review decisions

- Subtype remapping is by trimmed, case-insensitive name, not literal exact name. The current target has no duplicate normalized names within a service, but the implementation silently selects one if future data introduces duplicates. Keep business rows, preserve original IDs, and treat remapping as an explicit reviewed rule with ambiguity handling. Do not treat matching names alone as proof of business equivalence.
- The report now uses schema-qualified names correctly. Parent maps still use bare table names and rely on ordering the UAM collisions last. Namespace parent references before extending mappings; the current ordering avoids the known collisions but is fragile.
- Source payload retention proves availability of raw data, not correct application interpretation or complete operational modules. Current routes remain the lead-preview API; the additional imported entities do not yet have full workflows.
- The current working tree has uncommitted sync.py changes and untracked final/dry-run reports. Commit the reviewed implementation and non-sensitive evidence together when fixed.
- HANDOFF.md and VALIDATION.md remain stale. Update both with current scope and evidence, including remaining account/note adoption and workflow gaps.

## Acceptance checklist for the implementation agent

1. Fix the semantic relationship checks, normalization reuse and source-specific document storage labels.
2. Profile unresolved valuation options and document answer-type handling with source-code evidence.
3. Add meaningful importer and API tests, including failure, repeat, pagination-boundary and local-data preservation cases.
4. Implement and verify safe prototype account/note adoption.
5. Rerun import as appropriate, reconcile changes, then retain a full 61-table repeat report with zero unintended inserts/updates.
6. Validate real browser login, searches, lead details, notes and issue visibility; verify financial links without assuming settlement or double-counting receipt sources.
7. Update documentation and commit code plus non-sensitive validation reports. Return for independent review before starting the next business-feature phase.

Limits: no production access, no fresh full MySQL comparison, no complete 15-minute repeat import, no browser session/CSRF test and no independent verification of all JSP answer-type semantics were performed in this review. Those remain acceptance work, not implied by the confirmed row counts.
