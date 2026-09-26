"""Review the 202 highlighted sources without dropping attendance-adjacent payroll history."""
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
data = json.loads((ROOT/'target-disposition.json').read_text())
selected = [r.copy() for r in data['tables'] if r['environment']=='main' and r['disposition'] in {'domain_candidate','archive_candidate','review'}]
assert len(selected)==202

# Purpose descriptions are design intent. This registry does not claim every workflow has been implemented.
PURPOSE = {
'billing.charge_type':'Defines billable heads so charges are classified consistently.',
'billing.invoice':'Records issued bills, due dates, tax/amount totals and billing status.',
'billing.invoice_follow_up':'Tracks collection calls, reminders and actions for an invoice.',
'billing.issuer_account':'Identifies OMEN billing and remittance details used on documents.',
'billing.legacy_receipt':'Retains the direct amount-received path until receipt identities and balances are reconciled.',
'billing.offline_invoice':'Preserves manually/offline issued invoices and their original numbering.',
'billing.offline_receipt':'Preserves collections recorded outside the normal invoice workflow.',
'billing.receipt':'Records a receipt and its maker/checker/verification lifecycle.',
'billing.valuation_charge':'Records fee and tax components associated with a valuation.',
'crm.client_office':'Identifies the office that commissions work; drives relationship and branch performance reporting.',
'crm.client_type':'Classifies banks and other commissioning client types.',
'crm.contact':'Records the person who gives work and their office, designation and contact details.',
'crm.contact_designation':'Provides role/designation choices for external contacts.',
'documents.document':'Stores file metadata and a storage reference for S3 or local files; source upload IDs remain namespaced.',
'documents.document_usage':'Defines how document types are used in a workflow.',
'documents.lead_attachment':'Connects uploaded documents to a lead.',
'documents.legacy_upload_configuration':'Preserves upload-system settings for storage migration review; secrets are reconfigured separately.',
'documents.scrutiny_requirement':'Defines documents needed during scrutiny or review.',
'documents.valuation_attachment':'Connects valuation photos/files to the relevant case or assessment.',
'hr.additional_assignment':'Records an employee holding additional responsibility.',
'hr.department':'Organizes employees by department.',
'hr.deputation_department':'Identifies departments involved in employee deputation.',
'hr.designation':'Defines internal employee positions, separately from bank-contact designations.',
'hr.employee':'Represents an employee and their employment identity, independent of login access.',
'hr.employee_bank_account':'Preserves salary-payment destination and account ownership information.',
'hr.employee_bank_account_revision':'Keeps the audit trail of changes to salary-payment details.',
'hr.employee_group':'Groups employees for applicable HR or pay rules.',
'hr.employee_identity':'Keeps employee identity/KYC references under restricted access.',
'hr.employee_revision':'Preserves historical employee changes and prior employment details.',
'hr.employee_type':'Classifies employment categories used by HR/payroll.',
'hr.section_assignment':'Connects employees to assigned organizational sections.',
'hr.transfer':'Records an employee-transfer process.',
'hr.transfer_employee':'Identifies employees and postings involved in a transfer.',
'hr.transfer_note':'Preserves transfer remarks and supporting decisions.',
'identity.legacy_login_state':'Retains legacy login-state evidence; does not reactivate sessions in Django.',
'identity.legacy_module':'Maps old application modules into the new permission catalogue.',
'identity.legacy_permission':'Preserves old user permissions and scopes for reviewed access mapping.',
'identity.legacy_project':'Identifies the legacy applications for role/resource mapping.',
'identity.legacy_resource':'Maps old URLs/actions into the new permission catalogue.',
'identity.legacy_role':'Maps old user types into explicitly configured Django groups/roles.',
'identity.legacy_submodule':'Preserves submodule groupings needed to understand old access rules.',
'identity.legacy_user':'Maps legacy user identity to new accounts; passwords and grants are not copied blindly.',
'identity.login_event':'Preserves historical authentication events.',
'identity.permission_revision':'Preserves prior permission changes for audit.',
'identity.resource_scope':'Maps location/organizational restrictions on a resource.',
'identity.user_revision':'Preserves changes to legacy account identity.',
'leads.borrower':'Groups borrower/party information and agreed commercial terms under a lead.',
'leads.case':'Represents a property/asset assignment with service, location and operational status.',
'leads.division':'Preserves lead-domain division classification until equivalence with organizational divisions is proven.',
'leads.employee_assignment':'Connects employees to work responsibility.',
'leads.employee_target':'Records assigned business targets for employee performance reporting.',
'leads.follow_up':'Records follow-up calls, dates, outcomes and remarks for leads.',
'leads.lead':'Represents the incoming work request and its commissioning office.',
'leads.party_type':'Defines party categories used by the lead workflow.',
'leads.requested_service':'Lists services/subtypes and requested volumes under a lead.',
'leads.subdivision':'Preserves lead subdivision classification and its parent relationship.',
'leave.approval':'Tracks decisions on leave requests.',
'leave.request':'Preserves employee leave requests independently of attendance punch history.',
'leave.request_revision':'Preserves corrections and prior states of leave requests.',
'leave.type':'Defines leave categories and the rules that affect leave balances.',
'messaging.delivery_log':'Keeps delivery history with source application and channel; not evidence of consent.',
'messaging.notification':'Represents an in-app notification.',
'messaging.notification_recipient':'Tracks notification recipients and delivery/read state.',
'payroll.approval':'Records salary review/approval decisions.',
'payroll.component_revision':'Preserves changes to pay components for historical reconstruction.',
'payroll.configuration_revision':'Preserves prior employee pay configurations.',
'payroll.da_schedule':'Defines dated dearness-allowance rules/rates.',
'payroll.deduction':'Records salary deduction configuration or entries.',
'payroll.employee_pay_head':'Records employee pay-head values associated with salary results.',
'payroll.grade_pay':'Defines grade-pay reference values.',
'payroll.grade_pay_schedule':'Preserves alternate/new grade-pay schedules until effective-date rules are verified.',
'payroll.hra_schedule':'Defines housing-rent allowance rules/rates.',
'payroll.pay_band':'Defines pay-band classification.',
'payroll.pay_code':'Defines earning/deduction codes and their classification.',
'payroll.pay_commission':'Identifies the pay-commission/rule regime.',
'payroll.pay_head':'Defines reusable pay-head classifications.',
'payroll.pay_run_sheet':'Groups salary results into a payroll sheet/run.',
'payroll.provident_fund':'Preserves provident-fund details used in pay calculations.',
'payroll.salary_component':'Records detailed components of an employee salary.',
'payroll.salary_configuration':'Records employee-level pay setup and processing state.',
'payroll.salary_record':'Preserves salary amounts by code and effective period.',
'payroll.salary_revision':'Preserves changes to effective salary records.',
'payroll.salary_summary':'Preserves issued salary results, totals, period, payment status and frozen day counts.',
'reference.bank':'Provides a shared bank organization directory.',
'reference.bank_branch':'Provides official branch, IFSC and location references; distinct from commissioning offices.',
'reference.legacy_ifsc':'Preserves alternate IFSC data until it is reconciled with the bank-branch directory.',
'reports.bank_report':'Records a generated bank report, valuation values, references and issued document.',
'reports.dispatch':'Tracks where and when a completed report was dispatched.',
'reports.heading':'Defines reusable report headings.',
'reports.report_usage':'Classifies the intended use of a report.',
'reports.template_question':'Places questions/sections into a report template in the required order.',
'reports.template_version':'Keeps report configurations by version instead of dated backup tables.',
'services.service_subtype':'Defines subservices/asset categories under a service.',
'services.service_type':'Defines services offered by OMEN.',
'valuations.answer':'Preserves responses, repeated groups and values entered for valuation questions.',
'valuations.question':'Defines valuation questions and expected input structure.',
'valuations.question_category':'Groups valuation questions into meaningful sections.',
'valuations.question_option':'Defines permitted option choices for valuation questions.',
'valuations.reversion':'Records returned/reverted assessments and the reasons for rework.',
'valuations.review':'Preserves legal, technical, social, general and final review decisions.',
'valuations.valuation':'Represents an assessment linked to a case and explicitly linked work order.',
'workorders.fee_rule':'Defines work-order fee calculation rules.',
'workorders.work_order':'Represents the work instruction/agreement; distinct from the lead and property case.',
'workorders.work_order_revision':'Preserves historical changes to work orders.',
'audit.application_deletion':'Preserves evidence of deleted employee applications.',
'audit.application_revision':'Preserves changes to employee applications.',
'audit.legacy_master_event':'Preserves source master-data audit events rather than discarding history.',
}

RESOLVE = {
'action_permission_java':('identity.action_scope','Controls which actions a role/department can use within projects and modules.'),
'adv_mapping':('hr.external_reference','Preserves employee-to-reference mappings. Meaning of ref_no must be traced before downstream use.'),
'correction_dates':('payroll.processing_window','Defines permitted application/correction, sheet-generation and voucher windows by period.'),
'designation_senctioned_detail':('hr.sanctioned_position','Tracks sanctioned, filled/vacant posts by designation and official location.'),
'emp_bank_acc_verification':('hr.bank_account_verification','Records account-validation outcome and verification evidence for salary payments.'),
'emp_bank_acc_verification_his':('hr.bank_verification_revision','Preserves revisions to bank-account verification.'),
'emp_function':('hr.employee_function','Assigns employee responsibilities/functions.'),
'emp_salary_summary_history':('payroll.summary_revision','Preserves revisions to salary summaries.'),
'function':('hr.function','Defines employee function/responsibility categories.'),
'house_type':('hr.housing_type','Defines allotted housing categories and associated amounts.'),
'invoice_follow_up':('billing.legacy_uam_invoice_follow_up','Preserves UAM invoice-follow-up identity until its invoice database relationship is established.'),
'joining_batch':('hr.joining_batch','Groups employees by joining batch.'),
'link_officer':('hr.delegated_officer','Maps an officer to a linked/delegated officer.'),
'logtable':('archive.operational_log','Retains source operational diagnostics outside the active business tables; not a financial ledger.'),
'nullday':('attendance.non_working_period','Fresh-start configuration for exceptional non-working periods; legacy rows stay in source.'),
'org_structure_data':('hr.structure_submission','Tracks organizational staffing submissions and review metadata.'),
'org_structure_tagging':('hr.organizational_assignment','Records employee department/designation/posting and approval state.'),
'payroll_1018_gwalior':('payroll.legacy_pay_sheet','Preserves regional historical salary-sheet format for pay-result reconciliation.'),
'payroll_data_indore':('payroll.legacy_pay_sheet','Preserves regional historical salary-sheet format for pay-result reconciliation.'),
'visitors':('archive.usage_statistics','Preserves legacy website counter data; not an external customer-contact register.'),
'what_new':('messaging.announcement','Displays application-specific announcements and release information.'),
}
BACKUPS = {
'report_question_backup':'reports.template_question_snapshot','report_question_backup_25_08':'reports.template_question_snapshot',
'report_question_backup_29_10':'reports.template_question_snapshot','report_setup_backup':'reports.template_snapshot',
'report_setup_backup_25_08':'reports.template_snapshot','bank_branch_old':'reference.branch_snapshot','bank_old':'reference.bank_snapshot',
'designation_senctioned_dtl_bk':'hr.position_snapshot','emp_salary_backup_history_del':'payroll.deleted_salary_revision',
'employee_291118':'hr.employee_snapshot','employee_del':'hr.deleted_employee_snapshot',
'employee_salary_backup':'payroll.salary_baseline_component','employee_salary_backup_history':'payroll.baseline_revision',
'employee_salary_del':'payroll.deleted_salary_revision','employee_salary_main_backup':'payroll.salary_baseline',
'employee_salary_pay_head7623':'payroll.pay_head_snapshot','employee_salary_summary7623':'payroll.summary_snapshot',
'hql_permission_082019':'leave.legacy_permission_snapshot','leaveday_backup':'leave.balance_evidence',
'pay_code_bak7623':'payroll.pay_code_snapshot','userdetail_del':'identity.deleted_user_snapshot',
'userdetail_per_temp':'identity.permission_snapshot',
}
PURPOSE.update({target: purpose for target,purpose in RESOLVE.values()})
PURPOSE.update({
'reports.template_question_snapshot':'Retains old report question ordering/content so historical templates can be reconstructed.',
'reports.template_snapshot':'Retains old report configurations; source version labels remain intact.',
'reference.branch_snapshot':'Retains old branch-directory rows for identity and IFSC reconciliation.',
'reference.bank_snapshot':'Retains old bank-directory identities for comparison before consolidation.',
'hr.position_snapshot':'Preserves prior sanctioned-post data.',
'hr.employee_snapshot':'Preserves a dated employee snapshot without recreating active duplicate employees.',
'hr.deleted_employee_snapshot':'Retains deleted employee history without reactivating employment.',
'payroll.salary_baseline_component':'Preserves baseline pay components read and written by payroll code despite the backup table name.',
'payroll.salary_baseline':'Preserves the employee salary baseline used by payroll queries and corrections.',
'payroll.baseline_revision':'Preserves changes to baseline salary components.',
'payroll.deleted_salary_revision':'Preserves removed salary components and deletion history.',
'payroll.pay_head_snapshot':'Preserves a dated salary pay-head snapshot for comparison with issued pay.',
'payroll.summary_snapshot':'Preserves a dated salary summary including payment status and totals.',
'payroll.pay_code_snapshot':'Preserves the pay-code definitions used by a historical salary snapshot.',
'leave.legacy_permission_snapshot':'Preserves old leave-related permission evidence pending rule verification.',
'leave.balance_evidence':'Retains leave-day evidence needed to establish opening balances after the attendance reset.',
'identity.deleted_user_snapshot':'Preserves deleted account audit evidence without enabling login.',
'identity.permission_snapshot':'Retains temporary/old permission mappings for review; grants are rebuilt explicitly.',
})
for r in selected:
    schema,name=r['source_schema'],r['source_table']
    target=r['proposed_target']
    disposition='retain_for_target'
    if schema=='ebioserver':
        target='attendance.fresh_setup'
        disposition='skip_attendance_history'
    elif r['disposition']=='archive_candidate':
        if name.startswith(('attendance_', 'attendance_status_')):
            target='attendance.fresh_setup'; disposition='skip_attendance_history'
        else:
            target=BACKUPS[name]; disposition='preserve_and_reconcile'
    elif r['disposition']=='review':
        target,purpose=RESOLVE[name]
        if target.startswith('archive.'):
            disposition='retain_in_archive'
        elif name in {'adv_mapping','invoice_follow_up'}:
            disposition='retain_mapping_review'
    if target and target.startswith('attendance.'):
        # Approved sheets can be required to explain paid salaries; retain as payroll evidence, not replayed punches.
        if target in {'attendance.approved_sheet','attendance.sheet_item','attendance.sheet_leave'}:
            target='payroll.attendance_evidence'; disposition='preserve_and_reconcile'
        else:
            disposition='skip_attendance_history'
    r.update(target_entity=target,decision=disposition)
    if target.startswith('organization.'):
        PURPOSE[target]=f"Defines {target.split('.')[1].replace('_',' ')} references used for organizational/geographic scope; retain hierarchy until equivalence is proven."
    if target.startswith('attendance.'):
        PURPOSE[target]='Build fresh attendance configuration/events; do not import historical attendance rows. Keep the legacy source copy for reference.'
    r['business_usecase']=PURPOSE.get(target)
    if not r['business_usecase']:
        if target=='payroll.attendance_evidence':
            r['business_usecase']='Preserves approved attendance-sheet evidence underlying historical pay, without reconstructing the old punch system.'
        else:
            raise ValueError('Missing business purpose: '+str(target))

# Search SQL-shaped references across all supplied Java projects; evidence is static, not proof of runtime reachability.
names={r['source_table'].lower() for r in selected}
pattern=re.compile(r'\b(?:from|join|update|into|delete\s+from)\s+(?:`?\w+`?\.)?`?('+ '|'.join(sorted(map(re.escape,names),key=len,reverse=True))+r')\b', re.I)
evidence=collections.defaultdict(list)
for project in sorted(WORKSPACE.glob('omen-*')):
    if project.name in {'omen-next','omen-data-explorer'}:
        continue
    for file in project.rglob('*.java'):
        text=file.read_text(errors='replace')
        found=set()
        for match in pattern.finditer(text):
            name=match[1].lower()
            if name not in found:
                found.add(name)
                evidence[name].append({'file':str(file.relative_to(WORKSPACE)),'line':text.count('\n',0,match.start())+1})
for r in selected:
    refs=evidence[r['source_table'].lower()]
    r['sql_reference_files']=len(refs)
    r['evidence']=refs[:5]

summary=dict(collections.Counter(r['decision'] for r in selected))
groups=collections.defaultdict(list)
for r in selected:
    if r['decision']!='skip_attendance_history': groups[r['target_entity']].append(r)
result={'status':'reviewed_entity_plan_not_all_implemented','attendance_policy':'Do not migrate historical attendance; retain salary results and leave/payroll evidence.',
        'reviewed_sources':len(selected),'original_groups':dict(collections.Counter(r['disposition'] for r in selected)),
        'decisions':summary,'proposed_entity_concepts':len(groups),'sources':selected}
(ROOT/'entity-review.json').write_text(json.dumps(result,indent=2))
lines=['# Business entities and source coverage\n\n',
'Historical attendance is excluded from the import by owner direction. Payroll results, salary baselines, leave records and opening-balance evidence remain in scope. This is a logical entity plan; snapshot concepts may share version/archive infrastructure instead of each creating a physical table. Existing Django compatibility models are not these redesigned entities.\n\n',
f"All **{len(selected)} highlighted main-schema source tables** are represented (142 domain candidates, 28 backup candidates, 32 previously unclear). No source rows are deleted by this plan.\n\n",
'## Important findings\n\n- Payroll SQL explicitly reads and writes salary backup/main-backup tables: retain them as salary baselines.\n- Preserve leave-day backup evidence for opening balances.\n- Dated report backups retain historical template content.\n- Old bank directories need identity reconciliation; a matching display name is insufficient.\n- `logtable` has 2,031,252 rows and is operational diagnostics, not core business transactions; retain separately.\n- Empty tables can still describe supported workflows; zero rows is not grounds to remove an entity.\n- Employee external references and UAM invoice follow-ups remain mapping-review items; records are retained rather than assigned guessed meanings.\n\n',
'## Entities by business area\n\n']
for area in sorted({k.split('.')[0] for k in groups}):
    lines += [f'### {area.title()}\n\n','| Proposed entity | Business use | Source tables |\n|---|---|---|\n']
    for target,rs in sorted(groups.items()):
        if target.split('.')[0]!=area:continue
        lines.append(f"| {target} | {rs[0]['business_usecase']} | "+'<br>'.join(r['source_schema']+'.'+r['source_table'] for r in rs)+' |\n')
    lines.append('\n')
lines += ['## Complete 202-table checklist\n\n','| Source | Rows | Previous category | Decision | Entity | SQL reference files |\n|---|---:|---|---|---|---:|\n']
for r in selected:
    lines.append(f"| {r['source_schema']}.{r['source_table']} | {r['source_rows']:,} | {r['disposition']} | {r['decision']} | {r['target_entity']} | {r['sql_reference_files']} |\n")
lines += ['\n## Meaning of decisions\n\n- **retain_for_target:** covered by a business entity; conversion and workflow tests still required.\n- **preserve_and_reconcile:** retain history/baseline/evidence; do not merge it into current rows blindly.\n- **retain_mapping_review:** retain rows while a precise meaning or foreign relationship is resolved.\n- **retain_in_archive:** preserve source evidence outside active transaction tables.\n- **skip_attendance_history:** no historical import; old data remains in the restored source copy.\n\nSQL reference counts are static search evidence across supplied projects, may include commented/unreachable code or same-name tables in different schemas, and cannot establish live deployment usage. `entity-review.json` supplies file/line evidence for follow-up. Sources without a match are not automatically unused.\n']
(ROOT/'BUSINESS_ENTITIES.md').write_text(''.join(lines))
assert len({(r['source_schema'],r['source_table']) for r in selected})==202
print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
