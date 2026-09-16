# Clean target: entities, business use and current implementation

## Current status

The owner has excluded historical attendance from the new-system import. The complete restored database remains available as source evidence. Salary results, payroll baselines, leave requests and opening-balance evidence remain in scope.

The first **27 managed Django tables** are created in a separate local `backend/target.sqlite3`. These are new target tables, not the 905 unmanaged source mappings. No legacy business rows have yet been imported into this clean target. The original UI still uses the separate earlier prototype.

Implementation: `backend/target_core/models.py`, `backend/target_core/migrations/0001_initial.py`. Use `--settings=config.target`. Current models are a foundation, not the full fields/workflows for every domain; additional domain entities and conversion logic remain required. SQLite is for local schema/tests, not a validated production financial-storage choice.

## Created entities

| Entity | Business use |
|---|---|
| Bank | Shared bank organization directory |
| BankBranch | Official branch and IFSC/location reference |
| ClientType | Bank/non-bank client classification |
| ClientOffice | The commissioning office that gives OMEN work |
| ContactDesignation | External contact roles |
| Contact | Lead-giver/contact person linked to their office |
| Employee | Employee identity, separate from login accounts |
| ServiceType | Services offered by OMEN |
| ServiceSubtype | Subservice/asset classification under a service |
| Lead | Incoming work request from a client office |
| RequestedService | Services and requested counts within a lead |
| Borrower | Party grouping and agreed borrower-level fee |
| Case | Property/asset assignment linked to a lead and borrower |
| WorkOrder | Work instruction/agreement with explicit borrower/lead links |
| Valuation | Assessment linked to a case and, where established, a work order |
| Document | File metadata/storage location; file existence is separately verified |
| Invoice | Issued bill with original totals/status and source origin |
| InvoiceLine | Itemized invoiced charges |
| Receipt | Money received and verification state |
| ReceiptAllocation | Explicit assignment of received money to invoices, with a posting key to prevent duplicate posting |
| SalaryBaseline | Employee pay setup including the legacy salary-main-backup concept |
| SalaryBaselineComponent | Effective pay-code amounts in the salary baseline |
| SalaryResult | Historical salary totals/payment status and frozen paid-day values, independent of attendance history |
| LeaveOpeningBalance | Reconciled starting leave balance supported by source evidence |
| ImportBatch | Records migration snapshot, conversion version and outcome |
| SourceIdentity | Links original environment/schema/table/key to a target identity |
| MigrationIssue | Retains unresolved mapping/validation issues and their resolution |

Invoice/receipt imports do not automatically post allocations. Legacy paid totals remain separate from reconciled receipts. A later transaction service must check cumulative allocations, currency and receipt verification. Related lead/borrower/case/service consistency must be checked during conversion and business writes, beyond simple database foreign keys.

## Coverage of the 202 highlighted source tables

| Outcome | Tables | Treatment |
|---|---:|---|
| Retain for target | 140 | Covered by proposed business entities; many are still planned, not yet created |
| Preserve and reconcile | 25 | Keep salary baseline/history, template versions, old directory identities and other evidence |
| Retain pending precise mapping | 2 | Employee external reference and UAM invoice follow-up linkage need more investigation |
| Retain separately as archive | 2 | Operational logs and website counters |
| Skip attendance history | 33 | No import into the fresh attendance system; source data remains preserved |
| **Total** | **202** | No highlighted table omitted from the review register |

The [business-entity guide](BUSINESS_ENTITIES.md) lists every proposed entity and business use, followed by a complete 202-table checklist. The 157 retained logical concepts in that guide are not 157 implemented physical tables: snapshots and legacy role/resource mappings may share version/archive/migration infrastructure. Their final representation must preserve meaning and evidence rather than follow a target count.

## Findings that change the earlier backup classification

- `employee_salary_backup` and `employee_salary_main_backup` have explicit payroll SELECT/INSERT/UPDATE paths. They are modeled as salary baselines, not discarded as backups. Examples: `omen-payroll/src/main/java/com/awzpact/payroll/dao/EmployeeSalaryBackupDAOImpl.java:33`, `EmployeeSalaryMainBackupDAOImpl.java:19`, and `service/EmployeeSalaryService.java:760`.
- `leaveday_backup` has a DAO INSERT path (`omen-uam-hrms/src/java/com/awzpact/uam/dao/LeaveDayBackupDAOImpl.java:27`). Preserve it as leave-balance evidence; do not assume it independently supplies a correct opening balance.
- `correction_dates` contains voucher-generation windows as well as attendance/application windows. Retain it for payroll/processing rules despite the attendance reset.
- Salary summary snapshots and deletion history must not be dropped solely because of a date or backup suffix.
- `logtable` contains 2,031,252 operational-log rows. Keeping these out of active business tables reduces volume without erasing the preserved source archive.
- Table purpose reviews are based on source columns and static SQL evidence, not execution of every deployed workflow. Tables with no rows are still accounted for.

## Next database work

1. Finish field conversions and source-identity rules for the 27 managed entities; import validated records from the full source into the clean target with unresolved rows recorded as issues.
2. Add remaining managed entities for valuation questionnaires/answers, template versions, reviews, dispatch, work revisions, invoice follow-ups and document attachments.
3. Add HR, leave, payroll, permissions, organizational references and history entities covered by the guide. Trace accounts code and database routines before declaring accounting/workflow parity.
4. Reconcile backups and legacy variants before combining them. Preserve historic payroll results and leave opening evidence without importing punches.
5. Build fresh attendance configuration/events later, independently of the historical-data migration.

## Checks completed

- Managed initial migration applied to the separate target database.
- Django system checks and migration-drift check passed.
- Four automated tests passed: distinct branch/office identities and deletion protection; namespaced source keys and duplicate rejection; historical salary precision/day values without attendance; positive allocations and duplicate posting-key rejection.
- Entity-review coverage reconciles to 142 + 28 + 32 = 202 original sources, with no duplicate source entries.

Run checks from `backend`:

```sh
.venv/bin/python manage.py check --settings=config.target
.venv/bin/python manage.py test target_core --settings=config.target
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.target
```
