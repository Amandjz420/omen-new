# User, Employee and Role Design for the Django LEAD System

**Status:** design recommendation for review (not yet implemented)  
**Prepared:** 17 September 2026  
**Scope:** LEAD application identity, roles, permissions, data scope and employee assignment

## 1. Decision in one page

The Django system should keep three concepts separate:

1. **User account** – a person or service identity that can authenticate. It owns the login, password, sessions, MFA and account status.
2. **Employee** – an HR/business record used for assignment, responsibility, reporting and historical attribution. An employee may have no login account.
3. **Role assignment** – a time-bound grant that says what an authenticated user may do, and over which data scope. A job title is not a permission.

The relationship should be:

```text
User account (authentication)
        0..1
        |
        v
Employee (business identity and assignment)
        ^
        |
Role assignment -> role definition + actions + data scope + validity
```

Use Django's built-in `User` as the authentication identity and add a nullable, protected one-to-one link from `Employee` to `User`. Do not make `Employee` a login table, do not add a single `user.role` field, and do not equate a user's display name or job title with authorization.

Every request should be authorized by the following rule:

```text
active account
AND active role assignment
AND requested action
AND matching record scope
AND valid workflow state
AND separation-of-duties check
```

This gives the LEAD application a predictable policy for intake, assessment, verification, approval, billing, dispatch and reporting, while allowing HR and payroll to be added later without giving those users access to LEAD cases by accident.

## 2. What the legacy database actually contains

The findings below are from the restored local MySQL source database and the Java source, not assumptions based on table names.

### 2.1 Account and employee linkage

In the `uam_user` schema there are 51 `userdetail` rows and 51 `employee` rows. The legacy login SQL joins `userdetail.user_id` to `employee.emp_id`; that join produces 49 matches. There are two accounts with no matching employee on that join and two employees with no matching account. The explicit `employee.user_id` column is non-nullable in practice for **zero** of the 51 employees, so it cannot be used as the current source of truth.

This means IDs are correlated in the old application but are not a safe universal identity contract for the new system. The migration must create a reviewed mapping and retain the original IDs for audit and reconciliation.

The LEAD database has 10,969 populated `lead.assigned_to` values. All of them currently match both an `employee.emp_id` and a `userdetail.user_id`, which explains why the old application can treat those values as interchangeable. The new code must still store assignment as an explicit `Employee` foreign key and use `User -> Employee` only when an actor needs to be identified.

### 2.2 Status and account lifecycle

Of the 51 legacy accounts, 30 have status `1` and 21 have status `0`. A legacy status is evidence for migration review; it is not a complete security policy. The new system needs explicit states such as active, suspended, locked and deactivated, with session/token revocation on access removal.

Do not import the legacy reversible password representation as a Django password hash. Create accounts in an onboarding state and require a password reset (and MFA where required). Existing sessions, login tokens and failed-password data must not be copied as active credentials.

### 2.3 Projects, roles and grants

The current LEAD project uses project ID **14**. It has 22 role definitions. The role names and active grantee counts are:

| Legacy role | Active users | Recommended treatment |
|---|---:|---|
| Administrator | 4 | Map to Access Administrator only after reviewing actual actions |
| Employee | 2 | Map by job function; it is not a permission role by itself |
| LMS Admin | 1 | Access Administrator plus approved operational permissions |
| Field Assessors | 7 | Valuation Assessor |
| Sr. Manager (operation and marketing) | 0 | Operations Manager / Lead Coordinator, confirm scope |
| LMS Valuator | 0 | Valuation Assessor |
| Manager (QC - 2 & FA) | 1 | Reviewer with the relevant review track |
| Social Verifier | 0 | Reviewer: social track |
| Technical Verifer | 0 | Reviewer: technical track |
| General Verifier | 0 | Reviewer: general track |
| Executive Operation | 2 | Lead Coordinator or Operations Manager, confirm duties |
| LMS Manager | 0 | Operations Manager, confirm duties |
| Final Approver & CEO | 1 | Final Approver; CEO is a title, not a global bypass |
| Asst. Manager (QC1) | 0 | Reviewer: QC1 track |
| Opration Head | 1 | Operations Manager |
| Checker | 0 | Finance Approver or Reviewer, depending on the transaction |
| Sr. Manager Accounts & Finance | 1 | Finance Approver |
| Sr. Executive Admin | 1 | Access Administrator or Lead Coordinator, confirm duties |
| Executive | 0 | Map by actual work, not this generic title |
| Customer Care Head | 1 | Lead Coordinator with customer-care actions |
| OPRN MGR | 0 | Operations Manager, confirm duties |

There are 24 active LEAD grants, all attached to users whose account status is active. The grants contain `region_id` for all 24 users and `circle_id` for 21, while division and subdivision are empty. Non-empty legacy scope fields do not automatically prove a valid geographic restriction; their values need business confirmation before being activated as data scopes.

Five grants in the wider `uam_user` data reference missing role definitions. None is an active LEAD project grant. They should be preserved as migration exceptions, not silently converted into access.

### 2.4 How permissions work in the old application

The Java application obtains a user's role/project permission from `userdetail_per` and `usertype`, then maps `action_permission_java` to modules, submodules and URL actions. Actions include add, edit, delete, view, import, export and print. The URL interceptor checks the logged-in role before allowing a request.

This is a useful source of historical intent, but it is not a sufficient target design. The URL/menu mapping does not fully express object ownership, workflow state, maker-checker controls or field-level data sensitivity. The Django application should use explicit action permissions plus querysets and workflow checks.

## 3. Employee versus user account

| Question | User account | Employee |
|---|---|---|
| Purpose | Authentication and authorization actor | Business/HR identity and work assignment |
| Can exist without the other? | Yes: an external auditor or technical admin may not be an employee | Yes: an employee may have no application login |
| Main data | Username/email, password hash, MFA, status, last login | Employee code, name, department, manager, employment status |
| Used by | `created_by`, `approved_by`, audit events, sessions | `assigned_to`, assessor, reviewer, office ownership, payroll |
| Deletion | Disable and retain history; do not delete an audit actor | Retain historical employment and assignments; mark inactive |
| Naming | Stable account identifier | HR/business identifier; names can change |

Example: a field assessor has one Django user account and one employee record. A valuation is assigned to the employee. When the assessor submits it, the audit event records the user account. If the assessor leaves, the account is disabled and new work is reassigned, while old valuations still show the original employee and actor.

An employee who only appears in historic attendance or payroll data does not need a login. Conversely, a support or integration account must not be fabricated as an employee merely to satisfy a foreign key.

## 4. Proposed Django role model

Use a small set of stable business roles and add scope and workflow rules around them. Do not create a role for every legacy title.

| Proposed role | Main capabilities | Explicit boundaries |
|---|---|---|
| Access Administrator | Manage accounts, role definitions, role assignments and lookup configuration | Cannot approve valuations, receipts or their own access request by default |
| Operations Manager | Allocate leads/cases, manage teams/offices, monitor queues and operational SLAs | Cannot alter submitted evidence or approve a transaction solely because of title |
| Lead Coordinator | Create/edit clients, contacts, leads, requested services, borrowers, follow-ups and intake documents | Limited to assigned office/team/scope; cannot finalize a valuation or approve own financial work |
| Valuation Assessor | Work assigned valuations, enter answers/evidence, save drafts and submit for review | Cannot assess unassigned cases unless explicitly delegated; cannot approve own valuation |
| Reviewer | Perform an assigned technical, social, general or QC review and return/accept work | Track-specific; cannot skip required earlier review stages or approve own work |
| Final Approver | Review completed checks, approve/reject/finalize a valuation and controlled reverts | Cannot rewrite assessor evidence or approve a record they created or reviewed where policy forbids it |
| Billing & Collections Executive | Prepare invoices, receipts, allocations and customer follow-up | Cannot verify/approve their own receipt or alter valuation results |
| Finance Approver | Check, verify, reverse or approve finance transactions within policy limits | Maker-checker required; no self-approval; amount limits are configurable business policy |
| Dispatch Coordinator | Generate approved work-order/report packages, send/track dispatch and delivery | Can use only approved versions; cannot edit valuation facts |
| Management/Auditor Viewer | Read dashboards, case history and approved reports; export where separately granted | Read-only; export and sensitive-field access are separate permissions |

HR/payroll roles should be separate extensions (HR Officer, Payroll Preparer, Payroll Approver, Employee Self-Service). They should not receive LEAD case access merely because the same person has an HR role.

One user may have multiple roles, for example Lead Coordinator plus Reviewer. Each role assignment keeps its own scope. Permissions must not be combined into a broader accidental scope: a user who is a viewer for one office and an editor for another is still an editor only in the second office.

## 5. Recommended target data model

The existing target `Employee` model should gain a nullable one-to-one link to Django's user model:

```python
class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="employee_profile",
    )
```

The account remains Django's built-in `User`; changing `AUTH_USER_MODEL` during the current migration would create unnecessary migration risk. Django groups are useful for reusable role permissions, but built-in group permissions are additive and do not provide object-level scope by themselves. The application therefore needs a project model similar to:

```text
RoleDefinition
  name, code, domain, description, enabled

RolePermission
  role, action, resource, field (optional), enabled

RoleAssignment
  user, role, scope_kind, organization_unit/team/client_office (nullable),
  valid_from, valid_to, status, approved_by, reason, source_legacy_id

AuditEvent
  actor_user, action, resource_type, resource_id, role_at_time,
  before_snapshot, after_snapshot, reason, occurred_at
```

`scope_kind` must be constrained so that its subject is unambiguous: global, organization unit, team, client office, assigned records, or explicit record set. A centralized `can(user, action, obj)` service and matching visible querysets must be used by every API endpoint, export and background job. Frontend hiding is only a convenience; the API is the security boundary.

Use `Employee` on business ownership fields (`Lead.assigned_employee`, `Valuation.assessor`, reviewer assignment, office owner). Use `User` on actor/audit fields (`created_by`, `submitted_by`, `approved_by`, `LeadNote.author`). At approval time, store both the actor ID and a display snapshot so that later name or role changes do not rewrite historical evidence.

## 6. Workflow and separation of duties

The minimum LEAD policy should be:

1. Lead Coordinator creates intake and submits a case for assessment.
2. Operations Manager assigns an employee and service workflow.
3. Valuation Assessor works only assigned cases, saves drafts and submits.
4. Reviewer performs the required track (technical/social/general/QC) and either accepts or returns it with a reason.
5. Final Approver finalizes the valuation after all required reviews.
6. Billing & Collections prepares the invoice/receipt; Finance Approver checks or approves it.
7. Dispatch Coordinator produces and sends only the approved report/work-order package.

The system must reject a transition when the record is closed/locked, a required prior stage is missing, the actor is outside the record scope, or the actor is the prohibited maker of the same transaction. Combining roles must not bypass self-approval. A break-glass technical administrator, if required, should be separately logged and audited rather than treated as an ordinary CEO or Administrator privilege.

## 7. Migration and activation plan

1. **Freeze source evidence.** Import legacy users, employees, role definitions, grants and original IDs into staging/source-identity tables. Keep exceptions and raw payloads.
2. **Review the 51 account/employee candidates.** Automatically propose the 49 ID-join matches, then manually review the two unmatched accounts and two unmatched employees. Prefer an approved mapping based on employee code and HR evidence; never rely on names alone.
3. **Create Django accounts safely.** Create inactive/onboarding accounts with new password-reset tokens. Never convert the legacy reversible password string into a Django hash or log it.
4. **Map the 22 LEAD roles.** Preserve each legacy role/grant for audit, map to the proposed role only after comparing effective module actions, and record the reviewer, reason and source role ID.
5. **Convert scope fields.** Treat legacy region/circle values as proposed scope only. Validate whether they mean a real office/territory or a wildcard before activating them.
6. **Backfill business relationships.** Store lead, valuation, review and finance assignments against `Employee`; store creation/submission/approval actors against `User`.
7. **Activate in stages.** Start with read-only viewer access, then intake, assessment, review, approval, finance and dispatch. Do not activate all migrated grants in one switch.
8. **Reconcile and test.** Compare user-to-employee links, role grants, visible lead counts and workflow transitions against the legacy system and signed-off business examples.

The import must be idempotent: rerunning it updates the same source identity instead of duplicating accounts or role assignments. Revoking a role or disabling an account must immediately block new API requests while retaining historical records.

## 8. Current Django gap to close

The current prototype gates the API and sign-in flow with `is_staff`. Django documents `is_staff` as access to the Django admin site; it is not the LEAD job-role model. This currently means an ordinary employee can be blocked even when they should have a business role, while a staff flag can grant access without the required case scope or workflow check.

The target implementation should replace that gate with active-account and role-assignment checks. `is_superuser` should remain a tightly controlled technical emergency flag and should not be assigned automatically to legacy Administrator, Super Administrator or CEO accounts.

## 9. Acceptance tests before enabling production work

- An employee without a login can remain assigned to historic leads and valuations.
- A user without an employee link can authenticate only into explicitly allowed external/admin functions.
- A disabled user cannot sign in, use an existing token, or call an API.
- A user with a role for Office A cannot read or edit Office B records.
- A revoked or expired role stops access without deleting history.
- Field Assessor can edit an assigned draft but cannot submit an unassigned case or approve it.
- Reviewer can act only on the configured review track; required stages cannot be skipped.
- A maker cannot approve their own valuation, review or receipt even when they hold multiple roles.
- Exports and sensitive client/financial fields require separate permissions.
- Role and employee changes leave an audit event with actor, reason, before/after values and timestamp.
- Re-running the migration produces the same counts and no duplicate account, employee link or role assignment.

## 10. Source references

- Legacy login and project permission logic: `omen-lead-new/src/main/java/com/awzpact/uam/service/LoginService.java`, `uam/controller/LoginController.java`, `uam/util/ExecuteTimeInterceptor.java`, `uam/service/URLRequestValidatorService.java`.
- Legacy generated identity models: `omen-next/backend/legacy/uam_user/models.py` (`TUserdetail`, `TUserdetailLogin`, `TUserdetailPer`, `TUsertype`, `TEmployee`).
- LEAD assignment and role-specific valuation restrictions: `omen-lead-new/src/main/java/com/awzpact/lead/service/ValuationService.java` and `ValuationAllUserService.java`.
- Current target identity model and API guard: `omen-next/backend/target_core/models.py` and `target_core/views.py`.
- Django permissions and groups: [Django authentication documentation](https://docs.djangoproject.com/en/5.2/topics/auth/default/#permissions-and-authorization).
- Django user/profile and object-permission guidance: [Django authentication customization documentation](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#handling-object-permissions).
- Meaning of the admin flag: [Django User reference](https://docs.djangoproject.com/en/5.2/ref/contrib/auth/#django.contrib.auth.models.User.is_staff).

