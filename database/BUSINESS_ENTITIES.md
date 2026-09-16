# Business entities and source coverage

Historical attendance is excluded from the import by owner direction. Payroll results, salary baselines, leave records and opening-balance evidence remain in scope. This is a logical entity plan; snapshot concepts may share version/archive infrastructure instead of each creating a physical table. Existing Django compatibility models are not these redesigned entities.

All **202 highlighted main-schema source tables** are represented (142 domain candidates, 28 backup candidates, 32 previously unclear). No source rows are deleted by this plan.

## Important findings

- Payroll SQL explicitly reads and writes salary backup/main-backup tables: retain them as salary baselines.
- Preserve leave-day backup evidence for opening balances.
- Dated report backups retain historical template content.
- Old bank directories need identity reconciliation; a matching display name is insufficient.
- `logtable` has 2,031,252 rows and is operational diagnostics, not core business transactions; retain separately.
- Empty tables can still describe supported workflows; zero rows is not grounds to remove an entity.
- Employee external references and UAM invoice follow-ups remain mapping-review items; records are retained rather than assigned guessed meanings.

## Entities by business area

### Archive

| Proposed entity | Business use | Source tables |
|---|---|---|
| archive.operational_log | Retains source operational diagnostics outside the active business tables; not a financial ledger. | uam_user.logtable |
| archive.usage_statistics | Preserves legacy website counter data; not an external customer-contact register. | uam_user.visitors |

### Audit

| Proposed entity | Business use | Source tables |
|---|---|---|
| audit.application_deletion | Preserves evidence of deleted employee applications. | uam_user.application_delete_history |
| audit.application_revision | Preserves changes to employee applications. | uam_user.application_update_history |
| audit.legacy_master_event | Preserves source master-data audit events rather than discarding history. | uam_user.master_history |

### Billing

| Proposed entity | Business use | Source tables |
|---|---|---|
| billing.charge_type | Defines billable heads so charges are classified consistently. | lead_mngt.billing_head |
| billing.invoice | Records issued bills, due dates, tax/amount totals and billing status. | lead_mngt.invoice |
| billing.invoice_follow_up | Tracks collection calls, reminders and actions for an invoice. | lead_mngt.invoice_follow_up |
| billing.issuer_account | Identifies OMEN billing and remittance details used on documents. | lead_mngt.account_detail |
| billing.legacy_receipt | Retains the direct amount-received path until receipt identities and balances are reconciled. | lead_mngt.amount_received |
| billing.legacy_uam_invoice_follow_up | Preserves UAM invoice-follow-up identity until its invoice database relationship is established. | uam_user.invoice_follow_up |
| billing.offline_invoice | Preserves manually/offline issued invoices and their original numbering. | lead_mngt.offline_invoice |
| billing.offline_receipt | Preserves collections recorded outside the normal invoice workflow. | lead_mngt.offline_amount_received |
| billing.receipt | Records a receipt and its maker/checker/verification lifecycle. | lead_mngt.cash_receipt |
| billing.valuation_charge | Records fee and tax components associated with a valuation. | lead_mngt.valuation_billing |

### Crm

| Proposed entity | Business use | Source tables |
|---|---|---|
| crm.client_office | Identifies the office that commissions work; drives relationship and branch performance reporting. | lead_mngt.client |
| crm.client_type | Classifies banks and other commissioning client types. | lead_mngt.client_type |
| crm.contact | Records the person who gives work and their office, designation and contact details. | lead_mngt.orderer_reg |
| crm.contact_designation | Provides role/designation choices for external contacts. | lead_mngt.client_designation |

### Documents

| Proposed entity | Business use | Source tables |
|---|---|---|
| documents.document | Stores file metadata and a storage reference for S3 or local files; source upload IDs remain namespaced. | lead_mngt.upload<br>uam_user.upload |
| documents.document_usage | Defines how document types are used in a workflow. | lead_mngt.usage_documents |
| documents.lead_attachment | Connects uploaded documents to a lead. | lead_mngt.lead_upload |
| documents.legacy_upload_configuration | Preserves upload-system settings for storage migration review; secrets are reconfigured separately. | uam_user.upload_sys |
| documents.scrutiny_requirement | Defines documents needed during scrutiny or review. | lead_mngt.scrutiny_document |
| documents.valuation_attachment | Connects valuation photos/files to the relevant case or assessment. | lead_mngt.valuation_photo |

### Hr

| Proposed entity | Business use | Source tables |
|---|---|---|
| hr.additional_assignment | Records an employee holding additional responsibility. | uam_user.emp_additional_charge |
| hr.bank_account_verification | Records account-validation outcome and verification evidence for salary payments. | uam_user.emp_bank_acc_verification |
| hr.bank_verification_revision | Preserves revisions to bank-account verification. | uam_user.emp_bank_acc_verification_his |
| hr.delegated_officer | Maps an officer to a linked/delegated officer. | uam_user.link_officer |
| hr.deleted_employee_snapshot | Retains deleted employee history without reactivating employment. | uam_user.employee_del |
| hr.department | Organizes employees by department. | uam_user.department |
| hr.deputation_department | Identifies departments involved in employee deputation. | uam_user.deputation_department |
| hr.designation | Defines internal employee positions, separately from bank-contact designations. | uam_user.designation |
| hr.employee | Represents an employee and their employment identity, independent of login access. | uam_user.employee |
| hr.employee_bank_account | Preserves salary-payment destination and account ownership information. | uam_user.emp_bankdetail |
| hr.employee_bank_account_revision | Keeps the audit trail of changes to salary-payment details. | uam_user.emp_bankdetail_history |
| hr.employee_function | Assigns employee responsibilities/functions. | uam_user.emp_function |
| hr.employee_group | Groups employees for applicable HR or pay rules. | uam_user.employee_group |
| hr.employee_identity | Keeps employee identity/KYC references under restricted access. | uam_user.kyc_details |
| hr.employee_revision | Preserves historical employee changes and prior employment details. | uam_user.employee_history |
| hr.employee_snapshot | Preserves a dated employee snapshot without recreating active duplicate employees. | uam_user.employee_291118 |
| hr.employee_type | Classifies employment categories used by HR/payroll. | uam_user.employee_type |
| hr.external_reference | Preserves employee-to-reference mappings. Meaning of ref_no must be traced before downstream use. | uam_user.adv_mapping |
| hr.function | Defines employee function/responsibility categories. | uam_user.function |
| hr.housing_type | Defines allotted housing categories and associated amounts. | uam_user.house_type |
| hr.joining_batch | Groups employees by joining batch. | uam_user.joining_batch |
| hr.organizational_assignment | Records employee department/designation/posting and approval state. | uam_user.org_structure_tagging |
| hr.position_snapshot | Preserves prior sanctioned-post data. | uam_user.designation_senctioned_dtl_bk |
| hr.sanctioned_position | Tracks sanctioned, filled/vacant posts by designation and official location. | uam_user.designation_senctioned_detail |
| hr.section_assignment | Connects employees to assigned organizational sections. | uam_user.emp_assigned_section |
| hr.structure_submission | Tracks organizational staffing submissions and review metadata. | uam_user.org_structure_data |
| hr.transfer | Records an employee-transfer process. | uam_user.transfer |
| hr.transfer_employee | Identifies employees and postings involved in a transfer. | uam_user.transfer_emp |
| hr.transfer_note | Preserves transfer remarks and supporting decisions. | uam_user.transfer_remark |

### Identity

| Proposed entity | Business use | Source tables |
|---|---|---|
| identity.action_scope | Controls which actions a role/department can use within projects and modules. | uam_user.action_permission_java |
| identity.deleted_user_snapshot | Preserves deleted account audit evidence without enabling login. | uam_user.userdetail_del |
| identity.legacy_login_state | Retains legacy login-state evidence; does not reactivate sessions in Django. | uam_user.userdetail_login |
| identity.legacy_module | Maps old application modules into the new permission catalogue. | uam_user.uam_module |
| identity.legacy_permission | Preserves old user permissions and scopes for reviewed access mapping. | uam_user.userdetail_per |
| identity.legacy_project | Identifies the legacy applications for role/resource mapping. | uam_user.project |
| identity.legacy_resource | Maps old URLs/actions into the new permission catalogue. | uam_user.project_url |
| identity.legacy_role | Maps old user types into explicitly configured Django groups/roles. | uam_user.usertype |
| identity.legacy_submodule | Preserves submodule groupings needed to understand old access rules. | uam_user.submodule |
| identity.legacy_user | Maps legacy user identity to new accounts; passwords and grants are not copied blindly. | uam_user.userdetail |
| identity.login_event | Preserves historical authentication events. | uam_user.login_history |
| identity.permission_revision | Preserves prior permission changes for audit. | uam_user.userdetail_per_history |
| identity.permission_snapshot | Retains temporary/old permission mappings for review; grants are rebuilt explicitly. | uam_user.userdetail_per_temp |
| identity.resource_scope | Maps location/organizational restrictions on a resource. | uam_user.project_url_loc |
| identity.user_revision | Preserves changes to legacy account identity. | uam_user.userdetail_history |

### Leads

| Proposed entity | Business use | Source tables |
|---|---|---|
| leads.borrower | Groups borrower/party information and agreed commercial terms under a lead. | lead_mngt.lead_borrower |
| leads.case | Represents a property/asset assignment with service, location and operational status. | lead_mngt.client_customer |
| leads.division | Preserves lead-domain division classification until equivalence with organizational divisions is proven. | lead_mngt.division |
| leads.employee_assignment | Connects employees to work responsibility. | lead_mngt.employee_tagging |
| leads.employee_target | Records assigned business targets for employee performance reporting. | lead_mngt.employee_target |
| leads.follow_up | Records follow-up calls, dates, outcomes and remarks for leads. | lead_mngt.follow_up |
| leads.lead | Represents the incoming work request and its commissioning office. | lead_mngt.lead |
| leads.party_type | Defines party categories used by the lead workflow. | lead_mngt.party |
| leads.requested_service | Lists services/subtypes and requested volumes under a lead. | lead_mngt.lead_services |
| leads.subdivision | Preserves lead subdivision classification and its parent relationship. | lead_mngt.sub_division |

### Leave

| Proposed entity | Business use | Source tables |
|---|---|---|
| leave.approval | Tracks decisions on leave requests. | uam_user.leave_verification_detail |
| leave.balance_evidence | Retains leave-day evidence needed to establish opening balances after the attendance reset. | uam_user.leaveday_backup |
| leave.legacy_permission_snapshot | Preserves old leave-related permission evidence pending rule verification. | uam_user.hql_permission_082019 |
| leave.request | Preserves employee leave requests independently of attendance punch history. | uam_user.leave_manage |
| leave.request_revision | Preserves corrections and prior states of leave requests. | uam_user.leave_manage_history |
| leave.type | Defines leave categories and the rules that affect leave balances. | uam_user.leave_type |

### Messaging

| Proposed entity | Business use | Source tables |
|---|---|---|
| messaging.announcement | Displays application-specific announcements and release information. | uam_user.what_new |
| messaging.delivery_log | Keeps delivery history with source application and channel; not evidence of consent. | lead_mngt.sms_log<br>smldb.email_log<br>smldb.sms_log<br>uam_user.email_log<br>uam_user.sms_log |
| messaging.notification | Represents an in-app notification. | uam_user.notification |
| messaging.notification_recipient | Tracks notification recipients and delivery/read state. | uam_user.notification_detail |

### Organization

| Proposed entity | Business use | Source tables |
|---|---|---|
| organization.block | Defines block references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.block |
| organization.circle | Defines circle references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.circle |
| organization.city | Defines city references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.city |
| organization.district | Defines district references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.district |
| organization.division | Defines division references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.division |
| organization.location | Defines location references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.location |
| organization.official_location | Defines official location references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.official_location |
| organization.panchayat | Defines panchayat references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.panchayat |
| organization.region | Defines region references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.region |
| organization.state | Defines state references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.state |
| organization.sublocation | Defines sublocation references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.sublocation |
| organization.village | Defines village references used for organizational/geographic scope; retain hierarchy until equivalence is proven. | uam_user.village |

### Payroll

| Proposed entity | Business use | Source tables |
|---|---|---|
| payroll.approval | Records salary review/approval decisions. | uam_user.verify_emp_salary |
| payroll.attendance_evidence | Preserves approved attendance-sheet evidence underlying historical pay, without reconstructing the old punch system. | uam_user.att_sheet_leave<br>uam_user.attendance_sheet<br>uam_user.attendance_sheet_list |
| payroll.baseline_revision | Preserves changes to baseline salary components. | uam_user.employee_salary_backup_history |
| payroll.component_revision | Preserves changes to pay components for historical reconstruction. | uam_user.employee_salary_detail_history |
| payroll.configuration_revision | Preserves prior employee pay configurations. | uam_user.employee_salary_main_history |
| payroll.da_schedule | Defines dated dearness-allowance rules/rates. | uam_user.da_details |
| payroll.deduction | Records salary deduction configuration or entries. | uam_user.salary_deduction |
| payroll.deleted_salary_revision | Preserves removed salary components and deletion history. | uam_user.emp_salary_backup_history_del<br>uam_user.employee_salary_del |
| payroll.employee_pay_head | Records employee pay-head values associated with salary results. | uam_user.employee_salary_pay_head |
| payroll.grade_pay | Defines grade-pay reference values. | uam_user.grade_pay |
| payroll.grade_pay_schedule | Preserves alternate/new grade-pay schedules until effective-date rules are verified. | uam_user.grade_pay_new |
| payroll.hra_schedule | Defines housing-rent allowance rules/rates. | uam_user.hra_details |
| payroll.legacy_pay_sheet | Preserves regional historical salary-sheet format for pay-result reconciliation. | uam_user.payroll_1018_gwalior<br>uam_user.payroll_data_indore |
| payroll.pay_band | Defines pay-band classification. | uam_user.pay_band |
| payroll.pay_code | Defines earning/deduction codes and their classification. | uam_user.pay_code |
| payroll.pay_code_snapshot | Preserves the pay-code definitions used by a historical salary snapshot. | uam_user.pay_code_bak7623 |
| payroll.pay_commission | Identifies the pay-commission/rule regime. | uam_user.pay_commission |
| payroll.pay_head | Defines reusable pay-head classifications. | uam_user.emp_pay_head |
| payroll.pay_head_snapshot | Preserves a dated salary pay-head snapshot for comparison with issued pay. | uam_user.employee_salary_pay_head7623 |
| payroll.pay_run_sheet | Groups salary results into a payroll sheet/run. | uam_user.salary_sheet |
| payroll.processing_window | Defines permitted application/correction, sheet-generation and voucher windows by period. | uam_user.correction_dates |
| payroll.provident_fund | Preserves provident-fund details used in pay calculations. | uam_user.gpf_detail |
| payroll.salary_baseline | Preserves the employee salary baseline used by payroll queries and corrections. | uam_user.employee_salary_main_backup |
| payroll.salary_baseline_component | Preserves baseline pay components read and written by payroll code despite the backup table name. | uam_user.employee_salary_backup |
| payroll.salary_component | Records detailed components of an employee salary. | uam_user.employee_salary_detail |
| payroll.salary_configuration | Records employee-level pay setup and processing state. | uam_user.employee_salary_main |
| payroll.salary_record | Preserves salary amounts by code and effective period. | uam_user.employee_salary |
| payroll.salary_revision | Preserves changes to effective salary records. | uam_user.employee_salary_history |
| payroll.salary_summary | Preserves issued salary results, totals, period, payment status and frozen day counts. | uam_user.employee_salary_summary |
| payroll.summary_revision | Preserves revisions to salary summaries. | uam_user.emp_salary_summary_history |
| payroll.summary_snapshot | Preserves a dated salary summary including payment status and totals. | uam_user.employee_salary_summary7623 |

### Reference

| Proposed entity | Business use | Source tables |
|---|---|---|
| reference.bank | Provides a shared bank organization directory. | uam_user.bank |
| reference.bank_branch | Provides official branch, IFSC and location references; distinct from commissioning offices. | uam_user.bank_branch |
| reference.bank_snapshot | Retains old bank-directory identities for comparison before consolidation. | uam_user.bank_old |
| reference.branch_snapshot | Retains old branch-directory rows for identity and IFSC reconciliation. | uam_user.bank_branch_old |
| reference.legacy_ifsc | Preserves alternate IFSC data until it is reconciled with the bank-branch directory. | lead_mngt.ifsc |

### Reports

| Proposed entity | Business use | Source tables |
|---|---|---|
| reports.bank_report | Records a generated bank report, valuation values, references and issued document. | lead_mngt.valuation_bank_report |
| reports.dispatch | Tracks where and when a completed report was dispatched. | lead_mngt.dispatch |
| reports.heading | Defines reusable report headings. | lead_mngt.bank_report_heading |
| reports.report_usage | Classifies the intended use of a report. | lead_mngt.usage_of_reports |
| reports.template_question | Places questions/sections into a report template in the required order. | lead_mngt.report_question |
| reports.template_question_snapshot | Retains old report question ordering/content so historical templates can be reconstructed. | lead_mngt.report_question_backup<br>lead_mngt.report_question_backup_25_08<br>lead_mngt.report_question_backup_29_10 |
| reports.template_snapshot | Retains old report configurations; source version labels remain intact. | lead_mngt.report_setup_backup<br>lead_mngt.report_setup_backup_25_08 |
| reports.template_version | Keeps report configurations by version instead of dated backup tables. | lead_mngt.report_setup |

### Services

| Proposed entity | Business use | Source tables |
|---|---|---|
| services.service_subtype | Defines subservices/asset categories under a service. | lead_mngt.service_sub_type |
| services.service_type | Defines services offered by OMEN. | lead_mngt.service_type |

### Valuations

| Proposed entity | Business use | Source tables |
|---|---|---|
| valuations.answer | Preserves responses, repeated groups and values entered for valuation questions. | lead_mngt.valuation_answer |
| valuations.question | Defines valuation questions and expected input structure. | lead_mngt.question |
| valuations.question_category | Groups valuation questions into meaningful sections. | lead_mngt.detail_category |
| valuations.question_option | Defines permitted option choices for valuation questions. | lead_mngt.question_options |
| valuations.reversion | Records returned/reverted assessments and the reasons for rework. | lead_mngt.revert_back |
| valuations.review | Preserves legal, technical, social, general and final review decisions. | lead_mngt.valuation_verification |
| valuations.valuation | Represents an assessment linked to a case and explicitly linked work order. | lead_mngt.valuation |

### Workorders

| Proposed entity | Business use | Source tables |
|---|---|---|
| workorders.fee_rule | Defines work-order fee calculation rules. | lead_mngt.wo_fees_calculation |
| workorders.work_order | Represents the work instruction/agreement; distinct from the lead and property case. | lead_mngt.lead_order |
| workorders.work_order_revision | Preserves historical changes to work orders. | lead_mngt.lead_order_history |

## Complete 202-table checklist

| Source | Rows | Previous category | Decision | Entity | SQL reference files |
|---|---:|---|---|---|---:|
| ebioserver.attendancestates | 6 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.devicecommands | 34 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.deviceerrormessages | 0 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.devicelogs | 0 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 2 |
| ebioserver.deviceoperationlogtypes | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.devices | 4 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 1 |
| ebioserver.devicesstatus | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.employees | 54 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 1 |
| ebioserver.employees_110522 | 50 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.employeesbio | 145 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.fetch_attendance_log | 0 | review | skip_attendance_history | attendance.fresh_setup | 1 |
| ebioserver.mastersettings | 1 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.parallelattlogexportdetails | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.paralleldatabasedetails | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.permissions | 8 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.transactionsdump | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.userpermissions | 45 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.users | 2 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.usersdump | 0 | review | skip_attendance_history | attendance.fresh_setup | 0 |
| ebioserver.verificationmode | 23 | domain_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| lead_mngt.account_detail | 4 | domain_candidate | retain_for_target | billing.issuer_account | 0 |
| lead_mngt.amount_received | 1,519 | domain_candidate | retain_for_target | billing.legacy_receipt | 1 |
| lead_mngt.bank_report_heading | 478 | domain_candidate | retain_for_target | reports.heading | 2 |
| lead_mngt.billing_head | 6 | domain_candidate | retain_for_target | billing.charge_type | 2 |
| lead_mngt.cash_receipt | 11,207 | domain_candidate | retain_for_target | billing.receipt | 2 |
| lead_mngt.client | 1,394 | domain_candidate | retain_for_target | crm.client_office | 13 |
| lead_mngt.client_customer | 12,877 | domain_candidate | retain_for_target | leads.case | 12 |
| lead_mngt.client_designation | 26 | domain_candidate | retain_for_target | crm.contact_designation | 0 |
| lead_mngt.client_type | 7 | domain_candidate | retain_for_target | crm.client_type | 2 |
| lead_mngt.detail_category | 73 | domain_candidate | retain_for_target | valuations.question_category | 3 |
| lead_mngt.dispatch | 7,545 | domain_candidate | retain_for_target | reports.dispatch | 3 |
| lead_mngt.division | 9 | domain_candidate | retain_for_target | leads.division | 93 |
| lead_mngt.employee_tagging | 3 | domain_candidate | retain_for_target | leads.employee_assignment | 0 |
| lead_mngt.employee_target | 36 | domain_candidate | retain_for_target | leads.employee_target | 1 |
| lead_mngt.follow_up | 2,021 | domain_candidate | retain_for_target | leads.follow_up | 0 |
| lead_mngt.ifsc | 360 | domain_candidate | retain_for_target | reference.legacy_ifsc | 0 |
| lead_mngt.invoice | 11,927 | domain_candidate | retain_for_target | billing.invoice | 6 |
| lead_mngt.invoice_follow_up | 13 | domain_candidate | retain_for_target | billing.invoice_follow_up | 0 |
| lead_mngt.lead | 10,969 | domain_candidate | retain_for_target | leads.lead | 12 |
| lead_mngt.lead_borrower | 12,756 | domain_candidate | retain_for_target | leads.borrower | 16 |
| lead_mngt.lead_order | 12,285 | domain_candidate | retain_for_target | workorders.work_order | 8 |
| lead_mngt.lead_order_history | 1 | domain_candidate | retain_for_target | workorders.work_order_revision | 0 |
| lead_mngt.lead_services | 11,798 | domain_candidate | retain_for_target | leads.requested_service | 3 |
| lead_mngt.lead_upload | 0 | domain_candidate | retain_for_target | documents.lead_attachment | 0 |
| lead_mngt.offline_amount_received | 991 | domain_candidate | retain_for_target | billing.offline_receipt | 0 |
| lead_mngt.offline_invoice | 1,396 | domain_candidate | retain_for_target | billing.offline_invoice | 0 |
| lead_mngt.orderer_reg | 2,049 | domain_candidate | retain_for_target | crm.contact | 2 |
| lead_mngt.party | 0 | domain_candidate | retain_for_target | leads.party_type | 0 |
| lead_mngt.question | 2,161 | domain_candidate | retain_for_target | valuations.question | 4 |
| lead_mngt.question_options | 5,382 | domain_candidate | retain_for_target | valuations.question_option | 2 |
| lead_mngt.report_question | 4,785 | domain_candidate | retain_for_target | reports.template_question | 2 |
| lead_mngt.report_question_backup | 969 | archive_candidate | preserve_and_reconcile | reports.template_question_snapshot | 0 |
| lead_mngt.report_question_backup_25_08 | 161 | archive_candidate | preserve_and_reconcile | reports.template_question_snapshot | 0 |
| lead_mngt.report_question_backup_29_10 | 1,441 | archive_candidate | preserve_and_reconcile | reports.template_question_snapshot | 0 |
| lead_mngt.report_setup | 209 | domain_candidate | retain_for_target | reports.template_version | 2 |
| lead_mngt.report_setup_backup | 40 | archive_candidate | preserve_and_reconcile | reports.template_snapshot | 0 |
| lead_mngt.report_setup_backup_25_08 | 3 | archive_candidate | preserve_and_reconcile | reports.template_snapshot | 0 |
| lead_mngt.revert_back | 3,343 | domain_candidate | retain_for_target | valuations.reversion | 1 |
| lead_mngt.scrutiny_document | 153 | domain_candidate | retain_for_target | documents.scrutiny_requirement | 0 |
| lead_mngt.service_sub_type | 50 | domain_candidate | retain_for_target | services.service_subtype | 10 |
| lead_mngt.service_type | 15 | domain_candidate | retain_for_target | services.service_type | 10 |
| lead_mngt.sms_log | 5,169 | domain_candidate | retain_for_target | messaging.delivery_log | 9 |
| lead_mngt.sub_division | 12 | domain_candidate | retain_for_target | leads.subdivision | 78 |
| lead_mngt.upload | 150,636 | domain_candidate | retain_for_target | documents.document | 9 |
| lead_mngt.usage_documents | 0 | domain_candidate | retain_for_target | documents.document_usage | 0 |
| lead_mngt.usage_of_reports | 117 | domain_candidate | retain_for_target | reports.report_usage | 0 |
| lead_mngt.valuation | 12,651 | domain_candidate | retain_for_target | valuations.valuation | 11 |
| lead_mngt.valuation_answer | 1,947,362 | domain_candidate | retain_for_target | valuations.answer | 2 |
| lead_mngt.valuation_bank_report | 11,898 | domain_candidate | retain_for_target | reports.bank_report | 8 |
| lead_mngt.valuation_billing | 72,852 | domain_candidate | retain_for_target | billing.valuation_charge | 3 |
| lead_mngt.valuation_photo | 58,711 | domain_candidate | retain_for_target | documents.valuation_attachment | 2 |
| lead_mngt.valuation_verification | 12,080 | domain_candidate | retain_for_target | valuations.review | 6 |
| lead_mngt.wo_fees_calculation | 0 | domain_candidate | retain_for_target | workorders.fee_rule | 0 |
| smldb.email_log | 0 | domain_candidate | retain_for_target | messaging.delivery_log | 1 |
| smldb.sms_log | 20 | domain_candidate | retain_for_target | messaging.delivery_log | 9 |
| uam_user.action_permission_java | 491 | review | retain_for_target | identity.action_scope | 13 |
| uam_user.adv_mapping | 5 | review | retain_mapping_review | hr.external_reference | 0 |
| uam_user.application_delete_history | 2 | domain_candidate | retain_for_target | audit.application_deletion | 1 |
| uam_user.application_update_history | 1 | domain_candidate | retain_for_target | audit.application_revision | 0 |
| uam_user.att_sheet_leave | 7,728 | domain_candidate | preserve_and_reconcile | payroll.attendance_evidence | 10 |
| uam_user.attendance_062020_backup | 30 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| uam_user.attendance_062021_backup | 538 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| uam_user.attendance_072021_backup | 109 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| uam_user.attendance_sheet | 52 | domain_candidate | preserve_and_reconcile | payroll.attendance_evidence | 23 |
| uam_user.attendance_sheet_list | 786 | domain_candidate | preserve_and_reconcile | payroll.attendance_evidence | 20 |
| uam_user.attendance_status_062021_backup | 274 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| uam_user.attendance_status_072021_backup | 62 | archive_candidate | skip_attendance_history | attendance.fresh_setup | 0 |
| uam_user.bank | 199 | domain_candidate | retain_for_target | reference.bank | 27 |
| uam_user.bank_branch | 143,702 | domain_candidate | retain_for_target | reference.bank_branch | 11 |
| uam_user.bank_branch_old | 143,521 | archive_candidate | preserve_and_reconcile | reference.branch_snapshot | 0 |
| uam_user.bank_old | 200 | archive_candidate | preserve_and_reconcile | reference.bank_snapshot | 0 |
| uam_user.block | 585 | domain_candidate | retain_for_target | organization.block | 14 |
| uam_user.calender | 33 | domain_candidate | skip_attendance_history | attendance.calendar | 28 |
| uam_user.circle | 11 | domain_candidate | retain_for_target | organization.circle | 127 |
| uam_user.city | 2 | domain_candidate | retain_for_target | organization.city | 75 |
| uam_user.correction_dates | 34 | review | retain_for_target | payroll.processing_window | 12 |
| uam_user.da_details | 0 | domain_candidate | retain_for_target | payroll.da_schedule | 1 |
| uam_user.department | 5 | domain_candidate | retain_for_target | hr.department | 143 |
| uam_user.deputation_department | 0 | domain_candidate | retain_for_target | hr.deputation_department | 17 |
| uam_user.designation | 19 | domain_candidate | retain_for_target | hr.designation | 183 |
| uam_user.designation_senctioned_detail | 0 | review | retain_for_target | hr.sanctioned_position | 2 |
| uam_user.designation_senctioned_dtl_bk | 0 | archive_candidate | preserve_and_reconcile | hr.position_snapshot | 0 |
| uam_user.device_location | 0 | domain_candidate | skip_attendance_history | attendance.device_location | 1 |
| uam_user.district | 79 | domain_candidate | retain_for_target | organization.district | 17 |
| uam_user.division | 0 | domain_candidate | retain_for_target | organization.division | 93 |
| uam_user.email_log | 0 | domain_candidate | retain_for_target | messaging.delivery_log | 1 |
| uam_user.emp_additional_charge | 0 | domain_candidate | retain_for_target | hr.additional_assignment | 0 |
| uam_user.emp_assigned_section | 80 | domain_candidate | retain_for_target | hr.section_assignment | 3 |
| uam_user.emp_bank_acc_verification | 0 | review | retain_for_target | hr.bank_account_verification | 2 |
| uam_user.emp_bank_acc_verification_his | 0 | review | retain_for_target | hr.bank_verification_revision | 0 |
| uam_user.emp_bankdetail | 55 | domain_candidate | retain_for_target | hr.employee_bank_account | 29 |
| uam_user.emp_bankdetail_history | 0 | domain_candidate | retain_for_target | hr.employee_bank_account_revision | 0 |
| uam_user.emp_device | 113 | domain_candidate | skip_attendance_history | attendance.employee_device_identity | 1 |
| uam_user.emp_function | 59 | review | retain_for_target | hr.employee_function | 3 |
| uam_user.emp_pay_head | 0 | domain_candidate | retain_for_target | payroll.pay_head | 1 |
| uam_user.emp_salary_backup_history_del | 316 | archive_candidate | preserve_and_reconcile | payroll.deleted_salary_revision | 0 |
| uam_user.emp_salary_summary_history | 0 | review | retain_for_target | payroll.summary_revision | 0 |
| uam_user.employee | 51 | domain_candidate | retain_for_target | hr.employee | 348 |
| uam_user.employee_291118 | 0 | archive_candidate | preserve_and_reconcile | hr.employee_snapshot | 0 |
| uam_user.employee_del | 0 | archive_candidate | preserve_and_reconcile | hr.deleted_employee_snapshot | 0 |
| uam_user.employee_group | 0 | domain_candidate | retain_for_target | hr.employee_group | 2 |
| uam_user.employee_history | 0 | domain_candidate | retain_for_target | hr.employee_revision | 3 |
| uam_user.employee_salary | 515 | domain_candidate | retain_for_target | payroll.salary_record | 5 |
| uam_user.employee_salary_backup | 312 | archive_candidate | preserve_and_reconcile | payroll.salary_baseline_component | 4 |
| uam_user.employee_salary_backup_history | 3,487 | archive_candidate | preserve_and_reconcile | payroll.baseline_revision | 0 |
| uam_user.employee_salary_del | 12,554 | archive_candidate | preserve_and_reconcile | payroll.deleted_salary_revision | 0 |
| uam_user.employee_salary_detail | 48 | domain_candidate | retain_for_target | payroll.salary_component | 11 |
| uam_user.employee_salary_detail_history | 0 | domain_candidate | retain_for_target | payroll.component_revision | 0 |
| uam_user.employee_salary_history | 0 | domain_candidate | retain_for_target | payroll.salary_revision | 0 |
| uam_user.employee_salary_main | 36 | domain_candidate | retain_for_target | payroll.salary_configuration | 5 |
| uam_user.employee_salary_main_backup | 38 | archive_candidate | preserve_and_reconcile | payroll.salary_baseline | 6 |
| uam_user.employee_salary_main_history | 1,399 | domain_candidate | retain_for_target | payroll.configuration_revision | 0 |
| uam_user.employee_salary_pay_head | 5,693 | domain_candidate | retain_for_target | payroll.employee_pay_head | 8 |
| uam_user.employee_salary_pay_head7623 | 2,472 | archive_candidate | preserve_and_reconcile | payroll.pay_head_snapshot | 0 |
| uam_user.employee_salary_summary | 597 | domain_candidate | retain_for_target | payroll.salary_summary | 17 |
| uam_user.employee_salary_summary7623 | 254 | archive_candidate | preserve_and_reconcile | payroll.summary_snapshot | 0 |
| uam_user.employee_type | 4 | domain_candidate | retain_for_target | hr.employee_type | 110 |
| uam_user.function | 5 | review | retain_for_target | hr.function | 78 |
| uam_user.gpf_detail | 0 | domain_candidate | retain_for_target | payroll.provident_fund | 2 |
| uam_user.grade_pay | 2 | domain_candidate | retain_for_target | payroll.grade_pay | 23 |
| uam_user.grade_pay_new | 1 | domain_candidate | retain_for_target | payroll.grade_pay_schedule | 5 |
| uam_user.house_type | 0 | review | retain_for_target | hr.housing_type | 3 |
| uam_user.hql_permission_082019 | 0 | archive_candidate | preserve_and_reconcile | leave.legacy_permission_snapshot | 0 |
| uam_user.hra_details | 0 | domain_candidate | retain_for_target | payroll.hra_schedule | 1 |
| uam_user.invoice_follow_up | 0 | review | retain_mapping_review | billing.legacy_uam_invoice_follow_up | 0 |
| uam_user.joining_batch | 0 | review | retain_for_target | hr.joining_batch | 16 |
| uam_user.kyc_details | 0 | domain_candidate | retain_for_target | hr.employee_identity | 2 |
| uam_user.leave_manage | 189 | domain_candidate | retain_for_target | leave.request | 24 |
| uam_user.leave_manage_history | 0 | domain_candidate | retain_for_target | leave.request_revision | 3 |
| uam_user.leave_type | 10 | domain_candidate | retain_for_target | leave.type | 56 |
| uam_user.leave_verification_detail | 39 | domain_candidate | retain_for_target | leave.approval | 2 |
| uam_user.leaveday_backup | 7 | archive_candidate | preserve_and_reconcile | leave.balance_evidence | 3 |
| uam_user.link_officer | 0 | review | retain_for_target | hr.delegated_officer | 10 |
| uam_user.location | 0 | domain_candidate | retain_for_target | organization.location | 75 |
| uam_user.login_history | 74,164 | domain_candidate | retain_for_target | identity.login_event | 14 |
| uam_user.logtable | 2,031,252 | review | retain_in_archive | archive.operational_log | 0 |
| uam_user.master_history | 1,234 | domain_candidate | retain_for_target | audit.legacy_master_event | 3 |
| uam_user.notification | 22,013 | domain_candidate | retain_for_target | messaging.notification | 11 |
| uam_user.notification_detail | 22,013 | domain_candidate | retain_for_target | messaging.notification_recipient | 11 |
| uam_user.nullday | 0 | review | skip_attendance_history | attendance.non_working_period | 6 |
| uam_user.official_location | 12 | domain_candidate | retain_for_target | organization.official_location | 6 |
| uam_user.org_structure_data | 0 | review | retain_for_target | hr.structure_submission | 0 |
| uam_user.org_structure_tagging | 0 | review | retain_for_target | hr.organizational_assignment | 0 |
| uam_user.panchayat | 8,210 | domain_candidate | retain_for_target | organization.panchayat | 8 |
| uam_user.pay_band | 0 | domain_candidate | retain_for_target | payroll.pay_band | 6 |
| uam_user.pay_code | 35 | domain_candidate | retain_for_target | payroll.pay_code | 11 |
| uam_user.pay_code_bak7623 | 32 | archive_candidate | preserve_and_reconcile | payroll.pay_code_snapshot | 0 |
| uam_user.pay_commission | 0 | domain_candidate | retain_for_target | payroll.pay_commission | 10 |
| uam_user.payroll_1018_gwalior | 0 | review | retain_for_target | payroll.legacy_pay_sheet | 0 |
| uam_user.payroll_data_indore | 0 | review | retain_for_target | payroll.legacy_pay_sheet | 0 |
| uam_user.project | 3 | domain_candidate | retain_for_target | identity.legacy_project | 54 |
| uam_user.project_url | 3 | domain_candidate | retain_for_target | identity.legacy_resource | 1 |
| uam_user.project_url_loc | 3 | domain_candidate | retain_for_target | identity.resource_scope | 0 |
| uam_user.region | 1 | domain_candidate | retain_for_target | organization.region | 135 |
| uam_user.salary_deduction | 0 | domain_candidate | retain_for_target | payroll.deduction | 8 |
| uam_user.salary_sheet | 1,420 | domain_candidate | retain_for_target | payroll.pay_run_sheet | 1 |
| uam_user.shift_schedule | 3 | domain_candidate | skip_attendance_history | attendance.shift | 47 |
| uam_user.shift_tour_history | 0 | domain_candidate | skip_attendance_history | attendance.shift_assignment_revision | 0 |
| uam_user.shift_tours | 84 | domain_candidate | skip_attendance_history | attendance.shift_assignment | 17 |
| uam_user.sms_log | 0 | domain_candidate | retain_for_target | messaging.delivery_log | 9 |
| uam_user.state | 13 | domain_candidate | retain_for_target | organization.state | 57 |
| uam_user.sublocation | 0 | domain_candidate | retain_for_target | organization.sublocation | 91 |
| uam_user.submodule | 593 | domain_candidate | retain_for_target | identity.legacy_submodule | 14 |
| uam_user.transfer | 0 | domain_candidate | retain_for_target | hr.transfer | 28 |
| uam_user.transfer_emp | 0 | domain_candidate | retain_for_target | hr.transfer_employee | 29 |
| uam_user.transfer_remark | 0 | domain_candidate | retain_for_target | hr.transfer_note | 7 |
| uam_user.uam_module | 56 | domain_candidate | retain_for_target | identity.legacy_module | 11 |
| uam_user.upload | 50 | domain_candidate | retain_for_target | documents.document | 9 |
| uam_user.upload_sys | 429 | domain_candidate | retain_for_target | documents.legacy_upload_configuration | 4 |
| uam_user.userdetail | 51 | domain_candidate | retain_for_target | identity.legacy_user | 269 |
| uam_user.userdetail_del | 0 | archive_candidate | preserve_and_reconcile | identity.deleted_user_snapshot | 0 |
| uam_user.userdetail_history | 0 | domain_candidate | retain_for_target | identity.user_revision | 0 |
| uam_user.userdetail_login | 51 | domain_candidate | retain_for_target | identity.legacy_login_state | 24 |
| uam_user.userdetail_per | 114 | domain_candidate | retain_for_target | identity.legacy_permission | 30 |
| uam_user.userdetail_per_history | 0 | domain_candidate | retain_for_target | identity.permission_revision | 0 |
| uam_user.userdetail_per_temp | 0 | archive_candidate | preserve_and_reconcile | identity.permission_snapshot | 1 |
| uam_user.usertype | 35 | domain_candidate | retain_for_target | identity.legacy_role | 32 |
| uam_user.verify_emp_salary | 601 | domain_candidate | retain_for_target | payroll.approval | 1 |
| uam_user.village | 23,793 | domain_candidate | retain_for_target | organization.village | 9 |
| uam_user.visitors | 0 | review | retain_in_archive | archive.usage_statistics | 2 |
| uam_user.week_off_detail | 0 | domain_candidate | skip_attendance_history | attendance.weekly_rest_rule | 7 |
| uam_user.what_new | 1 | review | retain_for_target | messaging.announcement | 1 |

## Meaning of decisions

- **retain_for_target:** covered by a business entity; conversion and workflow tests still required.
- **preserve_and_reconcile:** retain history/baseline/evidence; do not merge it into current rows blindly.
- **retain_mapping_review:** retain rows while a precise meaning or foreign relationship is resolved.
- **retain_in_archive:** preserve source evidence outside active transaction tables.
- **skip_attendance_history:** no historical import; old data remains in the restored source copy.

SQL reference counts are static search evidence across supplied projects, may include commented/unreachable code or same-name tables in different schemas, and cannot establish live deployment usage. `entity-review.json` supplies file/line evidence for follow-up. Sources without a match are not automatically unused.
