"""Build a reviewable source-disposition inventory, not a destructive migration."""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
catalog = json.loads((ROOT / 'mapping-catalog.json').read_text())
verified = json.loads((ROOT / 'verification.json').read_text())
counts = {(t['schema'], t['table']): t['restored_rows'] for t in verified['tables']}
lead_targets = {
 'account_detail':'billing.issuer_account', 'amount_received':'billing.legacy_receipt',
 'bank_report_heading':'reports.heading', 'billing_head':'billing.charge_type',
 'cash_receipt':'billing.receipt', 'client':'crm.client_office', 'client_customer':'leads.case',
 'client_designation':'crm.contact_designation', 'client_type':'crm.client_type',
 'detail_category':'valuations.question_category', 'dispatch':'reports.dispatch',
 'division':'leads.division', 'employee_tagging':'leads.employee_assignment', 'employee_target':'leads.employee_target',
 'follow_up':'leads.follow_up', 'ifsc':'reference.legacy_ifsc', 'invoice':'billing.invoice',
 'invoice_follow_up':'billing.invoice_follow_up', 'lead':'leads.lead', 'lead_borrower':'leads.borrower',
 'lead_order':'workorders.work_order', 'lead_order_history':'workorders.work_order_revision',
 'lead_services':'leads.requested_service', 'lead_upload':'documents.lead_attachment',
 'offline_amount_received':'billing.offline_receipt', 'offline_invoice':'billing.offline_invoice',
 'orderer_reg':'crm.contact', 'party':'leads.party_type', 'question':'valuations.question',
 'question_options':'valuations.question_option', 'report_question':'reports.template_question',
 'report_setup':'reports.template_version', 'revert_back':'valuations.reversion',
 'scrutiny_document':'documents.scrutiny_requirement', 'service_sub_type':'services.service_subtype',
 'service_type':'services.service_type', 'sms_log':'messaging.delivery_log',
 'sub_division':'leads.subdivision', 'upload':'documents.document',
 'usage_documents':'documents.document_usage', 'usage_of_reports':'reports.report_usage',
 'valuation':'valuations.valuation', 'valuation_answer':'valuations.answer',
 'valuation_bank_report':'reports.bank_report', 'valuation_billing':'billing.valuation_charge',
 'valuation_photo':'documents.valuation_attachment', 'valuation_verification':'valuations.review',
 'wo_fees_calculation':'workorders.fee_rule',
}
uam_targets = {
 'bank':'reference.bank', 'bank_branch':'reference.bank_branch',
 'employee':'hr.employee', 'department':'hr.department', 'deputation_department':'hr.deputation_department',
 'designation':'hr.designation', 'employee_type':'hr.employee_type', 'employee_group':'hr.employee_group',
 'employee_history':'hr.employee_revision', 'emp_bankdetail':'hr.employee_bank_account',
 'emp_bankdetail_history':'hr.employee_bank_account_revision', 'kyc_details':'hr.employee_identity',
 'emp_device':'attendance.employee_device_identity', 'device_location':'attendance.device_location',
 'attendance_sheet':'attendance.approved_sheet', 'attendance_sheet_list':'attendance.sheet_item',
 'att_sheet_leave':'attendance.sheet_leave', 'leave_manage':'leave.request',
 'leave_manage_history':'leave.request_revision', 'leave_type':'leave.type',
 'leave_verification_detail':'leave.approval', 'shift_schedule':'attendance.shift',
 'shift_tours':'attendance.shift_assignment', 'shift_tour_history':'attendance.shift_assignment_revision',
 'week_off_detail':'attendance.weekly_rest_rule', 'calender':'attendance.calendar',
 'transfer':'hr.transfer', 'transfer_emp':'hr.transfer_employee', 'transfer_remark':'hr.transfer_note',
 'emp_additional_charge':'hr.additional_assignment', 'emp_assigned_section':'hr.section_assignment',
 'employee_salary':'payroll.salary_record', 'employee_salary_main':'payroll.salary_configuration',
 'employee_salary_detail':'payroll.salary_component', 'employee_salary_pay_head':'payroll.employee_pay_head',
 'employee_salary_summary':'payroll.salary_summary', 'employee_salary_history':'payroll.salary_revision',
 'employee_salary_detail_history':'payroll.component_revision', 'employee_salary_main_history':'payroll.configuration_revision',
 'salary_deduction':'payroll.deduction', 'salary_sheet':'payroll.pay_run_sheet', 'verify_emp_salary':'payroll.approval',
 'emp_pay_head':'payroll.pay_head', 'pay_code':'payroll.pay_code', 'pay_band':'payroll.pay_band',
 'pay_commission':'payroll.pay_commission', 'grade_pay':'payroll.grade_pay', 'grade_pay_new':'payroll.grade_pay_schedule',
 'gpf_detail':'payroll.provident_fund', 'da_details':'payroll.da_schedule', 'hra_details':'payroll.hra_schedule',
 'userdetail':'identity.legacy_user', 'usertype':'identity.legacy_role', 'userdetail_per':'identity.legacy_permission',
 'userdetail_history':'identity.user_revision', 'userdetail_per_history':'identity.permission_revision',
 'login_history':'identity.login_event', 'userdetail_login':'identity.legacy_login_state',
 'project':'identity.legacy_project', 'project_url':'identity.legacy_resource', 'project_url_loc':'identity.resource_scope',
 'submodule':'identity.legacy_submodule', 'uam_module':'identity.legacy_module',
 'upload':'documents.document', 'upload_sys':'documents.legacy_upload_configuration',
 'email_log':'messaging.delivery_log', 'sms_log':'messaging.delivery_log',
 'notification':'messaging.notification', 'notification_detail':'messaging.notification_recipient',
 'master_history':'audit.legacy_master_event', 'application_delete_history':'audit.application_deletion',
 'application_update_history':'audit.application_revision',
}
for location in ['state','district','block','city','village','panchayat','region','circle','division','location','sublocation','official_location']:
    uam_targets[location] = 'organization.' + location

rows = []
for t in catalog['tables']:
    schema, name = t['schema'], t['table']
    base = schema.removesuffix('_uat')
    env = 'uat' if schema.endswith('_uat') else 'main'
    target, decision, note = None, 'review', 'Keep source intact; domain mapping requires code/usage review.'
    monthly = re.fullmatch(r'(devicelogs)_(\d{1,2})_(\d{4})', name)
    period = re.fullmatch(r'(att_status_history|attendance_status|attendance|emp_application)_(\d{2})(\d{4})', name)
    if monthly or period:
        match = monthly or period
        month = int(match[2])
        target = {'devicelogs':'attendance.device_event','attendance':'attendance.daily_record',
                  'attendance_status':'attendance.daily_status','att_status_history':'attendance.status_revision',
                  'emp_application':'attendance.employee_application'}[match[1]]
        if 1 <= month <= 12:
            decision = 'consolidate_candidate'
            note = f'Monthly family; source period {match[3]}-{month:02d}. Compare layouts, date semantics and overlapping records before combining.'
        else:
            decision = 'review_invalid_period'
            note = 'Invalid month in table name; do not infer or rewrite dates.'
    elif re.search(r'backup|_old$|_bak|_bk$|_del$|_temp$|_\d{6}$|7623$', name):
        decision = 'archive_candidate'
        note = 'Name suggests snapshot/backup; preserve all rows. Prove usage and reconcile unique records before excluding from active tables.'
    elif base == 'lead_mngt':
        target = lead_targets.get(name)
    elif base == 'uam_user':
        target = uam_targets.get(name)
    elif base == 'smldb':
        target = 'messaging.delivery_log'
    elif base == 'ebioserver':
        target = {'devicelogs':'attendance.device_event','devices':'attendance.device',
                  'devicecommands':'attendance.device_command','deviceerrormessages':'attendance.device_error',
                  'employees':'attendance.device_person','employeesbio':'attendance.biometric_reference',
                  'attendancestates':'attendance.device_state','verificationmode':'attendance.verification_mode'}.get(name)
    if target and decision == 'review':
        decision = 'domain_candidate'
        note = 'Proposed domain entity; column conversion and business-rule parity still required.'
    if target == 'messaging.delivery_log':
        note += ' Retain source application and channel; do not deduplicate by message text.'
    if target == 'documents.document':
        note += ' Preserve storage provider and source identity; equal upload IDs across schemas are different documents.'
    if env == 'uat':
        note += ' UAT remains a separate target environment; never combine its rows into production.'
    signature = [(c['name'].lower(), c['sqlType'].lower(), c['nullable']) for c in t['columns']]
    rows.append({'source_schema':schema,'source_table':name,'source_rows':counts[schema,name],
                 'environment':env,'proposed_target':target,'disposition':decision,'reason':note,
                 'source_primary_key':t['primary_key'],'layout':signature})

stats = collections.Counter(r['disposition'] for r in rows if r['environment']=='main')
groups = collections.defaultdict(list)
for row in rows:
    if row['environment']=='main' and row['disposition']=='consolidate_candidate':
        groups[row['proposed_target']].append(row)
families = []
for target, members in sorted(groups.items()):
    variants = collections.Counter(json.dumps(r['layout']) for r in members)
    families.append({'target':target,'source_tables':len(members),'source_rows':sum(r['source_rows'] for r in members),
                     'column_layout_variants':len(variants)})
output = {'status':'design_candidates_not_applied','total_source_tables':len(rows),
          'main_tables':sum(r['environment']=='main' for r in rows),'uat_tables':sum(r['environment']=='uat' for r in rows),
          'main_dispositions':dict(stats),'monthly_families':families,
          'tables':[{k:v for k,v in row.items() if k!='layout'} for row in rows]}
(ROOT/'target-disposition.json').write_text(json.dumps(output,indent=2))
lines=['# Full source-to-target disposition register\n\nDesign candidates only; no source records have been deleted or consolidated. Every source table has one entry. Target names are proposed logical entities, not final migrations. UAT entries describe a separate environment.\n\n']
for schema in catalog['schemas']:
    lines += [f'## {schema}\n\n','| Source table | Rows | Proposed target | Disposition |\n|---|---:|---|---|\n']
    for row in rows:
        if row['source_schema']==schema:
            lines.append(f"| {row['source_table']} | {row['source_rows']:,} | {row['proposed_target'] or 'Review required'} | {row['disposition']} |\n")
    lines.append('\n')
(ROOT/'SOURCE_TO_TARGET.md').write_text(''.join(lines))
print(json.dumps({k:v for k,v in output.items() if k!='tables'},indent=2))
