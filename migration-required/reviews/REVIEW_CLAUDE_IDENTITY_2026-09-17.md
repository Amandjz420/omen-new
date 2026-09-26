# Review of Claude's valuation dependencies and identity migration

Reviewed 17 September 2026. Commits: `204659f` (valuation dependencies) and `2e3d984` (identity and provisioning), relative to `ead56d5`.

**Verdict: request changes before using the provisioned accounts for business work.** The new valuation imports reconcile with retained source payloads, and the existing tests pass. Identity evidence is imported, but account onboarding and authorization are incomplete and contain reproducible defects.

This review changed no application code, accounts or imported records. Target-data inspection used SQLite read-only mode. Behavioral reproductions ran against a separate in-memory database with synthetic users, employees and leads; CSRF checks were enabled for HTTP requests. Credential values were not printed, decrypted or included in this report. No production access was used.

## Findings

### R1 — P1: Initial-password change is never enforced

Location: `backend/target_core/management/commands/provision_accounts.py:79–85`; `backend/target_core/models.py:741`; `backend/target_core/views.py:38–46`.

Provisioning sets an account's initial password to its login ID and immediately activates it. `must_change_password` is stored but never read by the login handler, API guard or React application. There is no password-change endpoint in the URL configuration. The provisioning test checks the flag, not the promised restriction.

Reproduction: provision a synthetic assessor, sign in with its initial password, then read leads and post a note without changing the password. Login returns 200, lead reads return 200 and the note returns 201, while `must_change_password` remains true. All 23 currently provisioned accounts have the flag set and are active.

Required correction: implement the complete onboarding flow and enforce it on the backend before business access. Only password setup and logout should be available during onboarding; chosen passwords must pass validation, the flag must clear only after a successful change, and existing sessions must not bypass the restriction. Prefer invitation/reset credentials; if login-ID initial passwords remain an approved business decision, that does not remove the requirement to enforce first-use password change.

### R2 — P1: Every provisioned role receives the same unrestricted preview access

Location: `backend/target_core/management/commands/provision_accounts.py:79–83`; `backend/target_core/views.py:12–20` and the lead querysets.

Every new account gets `is_staff=True`. The existing API checks only that flag; it never consults role assignments or action permissions. Thus importing a Field Assessor role gives the same API capabilities as an administrator, including viewing all lead details and writing notes on any lead.

Reproduction: a synthetic Field Assessor can fetch a lead assigned to a different employee (200) and add a note to it (201). The test establishes the current behavior; the final assignment-access policy still needs to be expressed explicitly.

Required correction: keep onboarding accounts restricted until a business permission policy exists, or implement role/action checks for the current API before enabling them. Apply the policy consistently to lists, details, counts and writes. The recorded decision to remove region/circle restrictions does not by itself grant every role every action or remove assignment restrictions. Do not use the admin-site flag as the business role system.

### R3 — P1: Legacy credentials were copied into SourceRow despite the exclusion claim

Location: new `userdetail` import specification at `backend/target_core/sync.py:115`, full-row payload construction at `sync.py:277`, and subsequent SourceRow persistence.

Leaving passwords out of `LegacyAccount` scalar fields does not exclude them from staging. The source reader uses `SELECT *`, and the pipeline serializes the entire row into `SourceRow.payload`.

Read-only inspection confirms 51 staged `uam_user.userdetail` payloads contain non-empty `password` fields and 21 contain non-empty `old_password` fields. Only column names and counts were inspected for reporting; no values were displayed. These are legacy credential representations, not necessarily plaintext, but they contradict the explicit promise that credentials are never imported.

Required correction: introduce a credential-excluding source/payload allowlist, apply it before persistence and fingerprinting, and add a test that supplies extra credential columns and asserts their absence from every target payload. Sanitize already imported target staging credentials in a controlled remediation, including identifying affected copies/backups. Retain necessary non-secret identity evidence and source keys. Do not change or delete the source dump as part of that remediation.

### R4 — P1: Disabling a legacy account or revoking its grant leaves Django access active

Location: `backend/target_core/management/commands/provision_accounts.py:63–68,79–88`; API guard in `backend/target_core/views.py:12–20`.

The command sets `is_active` only when creating a user. If the source account becomes inactive, an existing Django user is treated as unchanged. If the LEAD grant is revoked, the command skips the account without changing its existing access. Requests do not check those legacy states either.

Reproduction: after provisioning, set the synthetic legacy account and its grant inactive and rerun provisioning. Django `is_active` remains true, an existing session still reads leads (200), and a fresh login succeeds (200).

Required correction: define who owns account activation after migration and implement an explicit revocation/reconciliation path. If legacy evidence is frozen, expose and enforce a new-system account/grant disable operation; if source status remains authoritative during transition, reconcile revocations safely. Never silently leave provisioned access enabled when the authoritative grant has been removed. Test both fresh and existing sessions.

### R5 — P1: Account adoption trusts username equality and can commit conflicting identity links

Location: `backend/target_core/management/commands/provision_accounts.py:74,90–105`.

When a username already exists, the command adopts it without proof that it belongs to the legacy person. It preserves its existing privilege flags. It also links `LegacyAccount.user` before checking whether `Employee.user` already belongs to someone else; that conflict merely emits a warning and commits the new active account.

Two synthetic reproductions:

- Pre-create a privileged Django account with the same username as an imported legacy login. Provisioning links that existing superuser to the legacy employee without a reviewed mapping. No password was changed by this reproduction; the defect is unverified identity adoption and retained privileges.
- Pre-link an employee to a different Django user. Provisioning creates an active staff account and links it to the legacy account, while leaving the employee linked to the original user. The two identity paths now disagree.

Required correction: reject unreviewed username collisions and validate the complete User/LegacyAccount/Employee relationship before creating or activating anything. Apply each approved binding atomically. Report conflicts without leaving partially provisioned access. An explicit adoption mapping must verify account ownership and privileged status.

### R6 — P2: A grant with a missing, disabled or deleted role can qualify for provisioning

Location: `backend/target_core/management/commands/provision_accounts.py:44–47`.

Eligibility filters only the grant's project name, status and deletion flag. It does not require an existing enabled role or validate the role's project against the grant's project. A nullable missing role therefore still grants staff access.

Reproduction: create an active LEAD grant with `role=None`. Provisioning creates an active staff user. The target contains five missing-role historical grants, but this review does not claim any of those currently grants LEAD access; this reproduction tests the command's unsafe eligibility rule.

Required correction: validate role existence, status, deletion state and project consistency before eligibility. Preserve invalid grants as evidence/exceptions, without provisioning access from them. Add equivalent checks for canonical accounts receiving merged grants.

### R7 — P2: Merge provisioning depends on login sort order and can require a second run

Location: `backend/target_core/management/commands/provision_accounts.py:49–65`.

Merges are saved while iterating accounts in login order. When the canonical account sorts first and only the later duplicate holds a LEAD grant, the canonical account is skipped before its duplicate is linked. A second run sees the link and creates a user, contradicting the command's repeatability claim. The dry run never saves merge links, so it cannot reliably preview this case either.

Reproduction with a patched synthetic merge map: first run creates no canonical user; second run creates it. The currently provisioned real canonical account may have its own eligible grant, so this is a demonstrated command defect rather than a claim that one of the current 23 accounts is missing.

Required correction: resolve and validate the full merge graph first, compute canonical eligibility from that graph, then provision. Use the same computation for dry run and real run. Test duplicate-only grants, sort orders, missing targets and cycles.

### R8 — P2: Login event migration drops time-of-day from the typed history

Location: `backend/target_core/models.py:764–765`; `backend/target_core/sync.py:117` and date conversion.

The legacy `login_history.login_date` and `logout_date` are datetime fields. The new model uses DateField, and the converter takes only the first ten characters. All 74,164 retained source login timestamps have a non-midnight time; 72,558 logout timestamps do as well. The typed event history cannot represent their ordering or session durations accurately. The raw payload still retains the original timestamps, so recovery is possible.

Required correction: use datetime fields, determine the source timezone and date/time column semantics, and backfill from retained evidence. The generic date conversion also needs an explicit DateTimeField branch so a model change alone does not continue truncating values. Add timestamp round-trip tests.

## What passed

Independent checks in this review:

- `manage.py test --verbosity 0`: 35 tests passed.
- `manage.py test --settings=config.target --verbosity 0`: 35 tests passed.
- `manage.py makemigrations --check --dry-run`: no drift.
- `npm run build`: passed.
- Target holds 11,897 BankReport records covering 11,896 valuations and 117 ReportUsage records.
- Compared all four assessed-amount fields on all 11,897 imported BankReport rows with retained source payloads at the source currency precision: zero mismatches.
- ReportUsage links resolve for 150 of 153 scrutiny requirements. Employee assignment rules have 0 of 3 links resolved; those unresolved references remain documented. DocumentUsage currently has zero rows.
- Target holds 51 legacy accounts, 35 role definitions, 114 historical role assignments and 74,164 login events.
- Target holds 23 Django users and 23 linked employees. All 23 users are active staff accounts; none is a superuser. The collision reproduction above used only a synthetic pre-existing superuser.

The committed identity import report covers 68 tables and 2,623,601 source rows: 74,367 newly inserted, 2,549,025 unchanged, 209 quarantined. These are report totals, not a fresh MySQL import performed by this review. The saved full repeat proof covers the previous 63-table scope; this review did not rerun the full 68-table source import.

## Why the passing tests missed the defects

The six provisioning tests cover straightforward creation, no duplicate users on a simple repeat, password/flag assignment, no newly created superusers, preservation of employees without accounts, and a direct password-validator call. They do not exercise password-change enforcement, role-specific API access, revocation, existing-user conflicts, rejected role grants, merges, or credential exclusion from source payloads.

The existing API tests intentionally assert the old preview's staff-only behavior. They prove that preview contract works, not that the new identity policy works. Add behavioral tests for R1–R8 rather than relying on the existing count.

## Documentation and remaining scope

`VALIDATION.md` still says identity is excluded, reports 63 source tables and 29 tests, and says no personal login is created. Those statements are stale after `2e3d984`. Its claim that no session/login/CSRF test exists also overlooks the existing backend FlowContractTests; browser testing is a separate claim. `HANDOFF.md` retains outdated identity status in its addendum.

`USER_ROLES_AND_EMPLOYEE_DESIGN.md` is a proposal, not evidence of implementation. The imported RoleDefinition and RoleAssignment models currently store historical roles/grants; they do not implement its ten proposed business roles, action permissions, approval rules or audit trail. Update the decision record to distinguish the reported owner decisions (no geographic restrictions, approved identity merge, initial-password choice) from recommendations and completed functionality.

Lead creation, work orders, valuation execution/review, finance approval and dispatch remain future operational API work. The existing routes still provide authentication, reads and lead notes.

## Recommended correction order and review gate

1. Close credential staging and onboarding defects before routine account use.
2. Implement current-API role/action authorization and account/grant revocation.
3. Make identity binding, grant eligibility and merge provisioning fail safely and agree with dry-run output.
4. Restore timestamp precision and cover the new imports with dedicated tests.
5. Update validation/handoff documents; rerun both suites and migration checks. Produce a fresh 68-table repeat reconciliation after importer changes.

Return the corrected diff and the new evidence for review before building the lead-intake write workflow on these accounts.
