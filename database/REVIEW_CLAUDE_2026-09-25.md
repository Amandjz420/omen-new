# Independent review of Claude's changes — 25 September 2026

## Decision

Do not sign off on operational use yet. Four reproducible defects remain despite the passing automated suite. No application fixes were made during this review.

## Scope and reproducibility

Reviewed commits from the Django admin addition (`5c3ec9b`) through valuation forms (`c9482e6beefcf17ee5ab5f2e898d3ecffa99894a`), following lead intake (`a12bced`). This includes PostgreSQL configuration/transfer code, additional import mappings, work orders, and valuation workflows. This is not a fresh reconciliation of every imported production row.

The working tree began changing during review. To avoid mixing revisions, defect reproductions used a `git archive` snapshot of `c9482e6` and a disposable in-memory database with all migrations applied. They used synthetic data and Django's test client, except the admin check, which exercised the actual registered admin form and save hook. Source line numbers below refer to that committed snapshot. Uncommitted changes require a separate review after completion.

## R1 — P1: Saving a section loses valuation answers and grid identities

Locations: `backend/target_core/valuations.py`, `answer_of`, `save_section`; `frontend/src/valuations.jsx`, section save.

The read representation reduces repeated answers to a single value per grid cell, text question, or sum option. The frontend submits every question in the section. Saving then rebuilds the answers and numbers grid rows from 1, ignoring the returned `group` identifier. Consequently even a read/save with no intended edits changes migrated data.

Reproduction: create two answers for the same valuation, grid question and option with `answer_group=7`, values `first` and `second`. GET the section and PUT back its returned answers in the frontend's format. Response is HTTP 200; two stored answers become one, and group 7 becomes group 1. Which duplicate survives depends on answer ordering. In the committed implementation, deleting and recreating answers also discards attached document links.

An in-progress `reconcile()` change was observed during review. It attempts to preserve document links for matching keys, but explicitly collapses duplicates and still receives renumbered groups. It therefore does not resolve the underlying preservation defect.

Required correction: preserve stable answer identities, group identifiers, and attached documents. Treat ambiguous historical duplicates explicitly rather than silently normalizing them. Submit only intentional changes and retain answer-level before/after evidence. Test unchanged round trips with duplicates, non-contiguous groups, documents and retired options.

## R2 — P1: Generic admin writes bypass business workflows

Location: `backend/target_core/admin.py:42–45`, generic `OwnedAdmin` registration.

The admin saves workflow models directly. The lead creation path does not call the intake service, allocate a number, or create an IntakeAudit entry. Generic forms similarly do not enforce the service-layer cross-record checks and workflow transitions for cases, work orders or valuations.

Reproduction: supply all required fields to the actual registered Lead admin form, leave the optional number blank, and invoke its save hook. Validation succeeds; the stored lead has `number=''`, `local_sequence=None`, and zero IntakeAudit records. This is a supported UI entry point, not a direct ORM-only bypass.

Required correction: route workflow edits through shared business services, or make those admin models read-only until specialized forms/actions exist. Keep ordinary directory maintenance separate. Add tests for admin lead creation, closed-record edits and work-order issuance, alongside equivalent API tests.

## R3 — P1: Revoking a scoped role broadens valuation access

Location: `backend/target_core/valuations.py:73–79`, `scoped_employee`.

An empty set of active LEAD assignments returns `None`, which means unrestricted access. This is unsafe for an existing authenticated, active staff user between a role change/import and account reconciliation. The role query also omits the role-definition validity checks used during provisioning.

Reproduction: create a linked Field Assessor account with source role 157 and request another employee's valuation. It returns HTTP 404. Set the assignment status to inactive and repeat the request in the same session. It returns HTTP 200. The request has gained access because its grant was removed.

Required correction: deny access for linked accounts with no eligible grants. Validate the role and project as well as the assignment. Grant unrestricted scope only through an explicit eligible role or administrative policy. Regression tests must exercise existing sessions after revocation, invalid definitions and mixed grants. This is enforcement of the current scoped-role promise; it does not require designing the final role matrix now.

## R4 — P2: Password hash upgrades count as password changes

Location: `backend/target_core/views.py:24–27`, `onboarding_pending`.

The onboarding gate treats a different encoded password hash as proof that the password changed. Django automatically upgrades an older hash during successful authentication, even when the user supplied the unchanged issued password.

Reproduction: create an account requiring a password change, with a valid low-iteration PBKDF2 hash also stored as `issued_password_hash`. Authenticate with that same password using the current hasher. Django upgrades the hash and `onboarding_pending` changes from True to False without a password change.

Required correction: clear onboarding through an explicit successful password-change path, including the approved admin reset/change flow. Do not infer a password change from encoded hash inequality. Test automatic rehashing and actual password changes separately.

## Verification and limits

- Local PostgreSQL test run under `config.settings`: **139 tests passed**. The command began before concurrent working-tree edits were noticed; this is evidence for that run, not a certification of the final changing tree.
- Frontend production build: **passed**.
- Isolated `c9482e6` snapshot under `config.target`, using SQLite's disposable test database: **139 tests passed**. This confirms the committed suite also passes; it does not substitute for PostgreSQL-specific verification under that setting.
- All four reproductions above ran against the isolated committed snapshot. They did not write to the application database or rerun the legacy import.
- The PostgreSQL transfer totals, full source-to-target reconciliation, real file availability, rendered work-order documents, production concurrency and complete browser journeys were not independently re-certified in this review.

## Recommended next handoff

1. Finish the current in-progress changes and provide a stable commit.
2. Fix R1 and R2 before allowing business users to edit migrated records.
3. Fix R3 and R4 before relying on the current access and onboarding rules.
4. Add regression tests for the four reproductions, then rerun both settings on PostgreSQL and rebuild the frontend.
5. Review the resulting commit and exercise one complete synthetic journey: intake → borrower/service/case → work order → valuation edit → repeat import, checking numbering, document links, answer preservation and audit evidence.

Final role design can remain deferred, as requested. Data preservation and enforcement of existing restrictions cannot safely be deferred with it.
