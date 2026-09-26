"""One-way full refresh from the read-only source database into managed models.

No JSON-export dependency, no hard-coded snapshot dates, no attendance import.
Missing/invalid required references are quarantined with their original payload.
"""
import hashlib
import json
import re
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.db import connections, transaction, models
from django.utils import timezone
try:
    from zoneinfo import ZoneInfo
    LEGACY_TIMEZONE=ZoneInfo('Asia/Kolkata')   # legacy timestamps are wall-clock local time
except Exception:
    LEGACY_TIMEZONE=timezone.get_default_timezone()
from target_core import models as m

VERSION = 'mysql-target-v1'
# Rows read per page. Bounds peak memory on large tables such as the 1.95M-row
# valuation answer set, which cannot be held in memory in one piece.
CHUNK_SIZE = 100000
# Credential-bearing columns are dropped at the source reader, before payloads,
# fingerprints or reports are built, so no stage of the pipeline can retain them.
# Excluding a column from a spec's scalars is NOT sufficient: the reader selects
# whole rows and SourceRow stores the whole row.
EXCLUDED_COLUMNS = {'password','old_password','pin','pin_no','session_id','otp',
                    'security_answer','security_question','token','secret'}


def readable(columns):
    """Indices and names of the columns permitted to leave the source."""
    kept=[(i,c) for i,c in enumerate(columns) if c not in EXCLUDED_COLUMNS]
    return [i for i,_ in kept],[c for _,c in kept]
NS = uuid.UUID('9bd83976-1597-4f34-99cf-6ea542f97ebc')

# schema, table, ID, target, scalar target->source, FK target->(parent table, source column, optional)
SPECS = [
 ('uam_user','bank','bank_id',m.Bank,{'name':'name','legacy_status':'status'},{}),
 ('uam_user','bank_branch','branch_id',m.BankBranch,{'name':'name','ifsc':'ifsc_code','micr':'micr_code','address':'branch_address','city':'city','district':'district','state':'state'}, {'bank':('bank','bank_id',False)}),
 ('uam_user','employee','emp_id',m.Employee,{'name':'name','employee_code':'emp_code'},{}),
 ('lead_mngt','client_type','client_type_id',m.ClientType,{'name':'client_type_name'},{}),
 ('lead_mngt','client_designation','client_designation_id',m.ContactDesignation,{'name':'name'},{}),
 ('lead_mngt','service_type','service_type_id',m.ServiceType,{'name':'name'},{}),
 ('lead_mngt','service_sub_type','service_sub_type_id',m.ServiceSubtype,{'name':'name'}, {'service':('service_type','service_type_id',False)}),
 ('lead_mngt','client','client_id',m.ClientOffice,{'name':'name','branch_name':'branch','address':'address','legacy_working_status':'working','gstin':'gst_no','ifsc':'ifsc'}, {'client_type':('client_type','client_type_id',True),'bank':('bank','bank_id',True),'directory_branch':('bank_branch','bank_branch_id',True)}),
 ('lead_mngt','orderer_reg','orderer_reg_id',m.Contact,{'name':'orderer_name','phone':'mobile_no','alternate_phone':'alt_contact_no'}, {'office':('client','client_id',False),'designation':('client_designation','client_designation_id',True)}),
 ('lead_mngt','lead','lead_id',m.Lead,{'number':'lead_no','received_date':'lead_date','legacy_status':'lead_status','legacy_deleted':'delete_status','enquiry_mode':'mode','party_count':'no_of_parties','case_count':'no_of_cases','legacy_number_old':'lead_no_old'}, {'office':('client','client_id',False),'contact':('orderer_reg','orderer_reg_id',True),'assigned_employee':('employee','assigned_to',True),'received_by':('employee','received_by',True),'client_type':('client_type','client_type_id',True)}),
 ('lead_mngt','lead_services','lead_service_id',m.RequestedService,{'party_count':'no_of_parties','case_count':'no_of_cases'}, {'lead':('lead','lead_id',False),'service':('service_type','service_type_id',False),'subtype':('service_sub_type','service_sub_type_id',True)}),
 ('lead_mngt','lead_borrower','lead_borrower_id',m.Borrower,{'name':'name_of_borrower','agreed_fee':'wo_amount','property_count':'no_of_properties','contact_number':'contact_no','email':'email_id','payer':'paid_by','fee_basis':'payment_by_mode','customer_payment_method':'cc_payment_mode','payer_name':'payment_by','payer_mobile':'payment_by_mobile','pay_by_date':'pay_by_date','gst_number':'cc_gst_no','payment_reference_number':'payment_res_no','payment_reference_name':'payment_res_name','legacy_deleted':'delete_status'}, {'lead':('lead','lead_id',False)}),
 ('lead_mngt','client_customer','client_customer_id',m.Case,{'asset_address':'address','legacy_status':'delete_status','asset_pin_code':'pin_code','asset_block_code':'block_id','asset_amount':'asset_amount','contact_person_name':'contact_person_name','contact_number':'contact_no','expected_report_date':'expect_date_report','remarks':'remarks','usage_of_report_code':'usage_of_reports_id','scrutiny_document_code':'scrutiny_document_id'}, {'lead':('lead','lead_id',False),'borrower':('lead_borrower','lead_borrower_id',False),'service':('service_type','service_type_id',False),'subtype':('service_sub_type','service_sub_type_id',True)}),
 ('lead_mngt','upload','upload_id',m.Document,{'storage_key':'doc_path','original_name':'doc_name','media_type':'doc_type_name','size_bytes':'doc_size'},{}),
 ('lead_mngt','lead_order','lead_order_id',m.WorkOrder,{'number':'lead_order_no','legacy_status':'status','legacy_number_old':'lead_order_no_old','legacy_deleted':'delete_status'}, {'lead':('lead','lead_id',False),'borrower':('lead_borrower','lead_borrower_id',False),'document':('upload','upload_id',True)}),
 ('lead_mngt','valuation','valuation_id',m.Valuation,{'valuation_date':'valuation_date','legacy_status':'valuation_status','report_number':'report_no','assessor_name':'valuation_done_by_name','eligible_loan_amount':'eligible_loan_amount','desired_loan_amount':'desire_loan_amount','total_billing_amount':'total_billing_amount','advance_collected':'advance_collected','remaining_amount':'remaining_amount','total_after_tax':'total_amount_after_tax','total_after_tax_words':'total_amount_after_tax_in_words','assessor_comment':'assessors_comment','non_cost_factor':'non_cost_factor','report_category':'report_category','dispatch_at_code':'to_be_dispatched_at','dispatch_by_code':'to_be_dispatched_by','status_reason':'reason','status_reason_date':'reason_date'}, {'case':('client_customer','client_customer_id',False),'work_order':('lead_order','lead_order_id',True),'submitted_to':('employee','submit_to',True),'liable_employee':('employee','liable_fa',True),'assessor':('employee','valuation_done_by',True)}),
 # Omen's own accounts load first, since each invoice names the one it is paid into.
 # account_detail.bank_id is the account's code, not a bank.
 ('lead_mngt','account_detail','account_detail_id',m.IssuerAccount,{'name':'name','code':'bank_id','branch_code':'branch_code','account_number':'account_no','ifsc_code':'ifsc_code','branch_address':'branch_address','gst_number':'gst_no'},{}),
 # invoice.bank_id joins account_detail.bank_id, which equals account_detail_id on
 # all four accounts, so it resolves through the account's source key.
 ('lead_mngt','invoice','invoice_id',m.Invoice,{'number':'invoice_no','issued_date':'invoice_date','due_date':'due_date','billed_amount':'total_invoice_amount','legacy_paid_amount':'total_pay_amount','legacy_remaining_amount':'total_remaining_amount','legacy_status':'payment_status','gstin_party':'gst_type','other_gstin':'other_gst','payer':'paid_by','payment_type':'payment_type','payment_date':'payment_date','bad_debt_amount':'bad_debt_amount','bad_debt_remark':'bad_debt_remark','excess_amount':'excess_amount','remaining_words':'total_remaining_amount_in_words','legacy_number_old':'invoice_no_old'}, {'valuation':('valuation','valuation_id',False),'issuer_account':('account_detail','bank_id',True),'document':('upload','upload_id',True)}),
 ('uam_user','employee_salary_main_backup','employee_salary_main_id',m.SalaryBaseline,{'legacy_status':'status'}, {'employee':('employee','emp_id',False)}),
 ('uam_user','employee_salary_backup','employee_salary_id',m.SalaryBaselineComponent,{'pay_code':'pay_code','amount':'amount','from_period':'from_year_month','to_period':'to_year_month','mode':'pay_mode'}, {'baseline':('employee_salary_main_backup','employee_salary_main_id',False)}),
 ('uam_user','employee_salary_summary','employee_salary_summary_id',m.SalaryResult,{'period':'year_months','gross_earning':'gross_earning','gross_deduction':'gross_deduction','net_salary':'net_salary','paid_days':'present_days','legacy_payment_status':'transaction_status'}, {'employee':('employee','employee_id',False)}),

 # --- Organization: administrative geography -------------------------------
 # Legacy stores these parent keys as varchar, so every link is optional and an
 # unresolved reference is reported rather than discarding the row.
 ('uam_user','state','state_id',m.State,{'name':'name','name_hindi':'name_hindi','census_code':'census_code','legacy_status':'status'},{}),
 ('uam_user','district','district_id',m.District,{'name':'name','name_hindi':'name_hindi','census_code':'census_code','legacy_status':'status'}, {'state':('state','state_id',True)}),
 ('uam_user','region','region_id',m.Region,{'name':'name','name_hindi':'name_hindi','legacy_status':'status'},{}),
 ('uam_user','circle','circle_id',m.Circle,{'name':'name','name_hindi':'name_hindi','legacy_status':'status'}, {'region':('region','region_id',True)}),
 ('uam_user','block','block_id',m.Block,{'name':'name','name_hindi':'name_hindi','census_code':'census_code','area_type':'area_type','legacy_status':'status'}, {'district':('district','district_id',True),'region':('region','region_id',True),'circle':('circle','circle_id',True)}),
 ('uam_user','panchayat','panchayat_id',m.Panchayat,{'name':'name','name_hindi':'name_hindi','legacy_status':'status'}, {'block':('block','block_id',True)}),
 ('uam_user','village','village_id',m.Village,{'name':'name','name_hindi':'name_hindi','census_code':'census_code','pincode':'pincode','area_type':'area_type','legacy_status':'status','legacy_panchayat_code':'panchayat_id'},{}),
 ('uam_user','city','city_id',m.City,{'name':'name','name_hindi':'name_hindi','code':'code','legacy_status':'status'},{}),
 ('uam_user','location','location_id',m.Location,{'name':'name','name_hindi':'name_hindi','code':'code','legacy_status':'status'}, {'city':('city','city_id',True)}),
 ('uam_user','sublocation','sublocation_id',m.SubLocation,{'name':'name','name_hindi':'name_hindi','code':'code','legacy_status':'status'}, {'location':('location','location_id',True)}),
 ('uam_user','official_location','official_location_id',m.OfficialLocation,{'name':'name','name_hindi':'name_hindi','kind':'type','code':'code','legacy_status':'status'}, {'city':('city','city_id',True)}),
 ('lead_mngt','ifsc','ifsc',m.IfscArea,{'ifsc':'ifsc'}, {'state':('state','state_id',True),'district':('district','district_id',True),'block':('block','block_id',True)}),

 # Report purpose lookup. Several tables store this id as a bare code, so it
 # loads before them and their codes become real links.
 ('lead_mngt','usage_of_reports','usage_of_reports_id',m.ReportUsage,{'name':'name','legacy_status':'status','legacy_deleted':'delete_status'}, {'service':('service_type','service_type_id',True),'subtype':('service_sub_type','service_sub_type_id',True)}),

 # --- Lead operations: territory, follow-up, targets, assignment -----------
 ('lead_mngt','division','division_id',m.LeadDivision,{'name':'name','legacy_status':'status','legacy_deleted':'delete_status'},{}),
 ('lead_mngt','sub_division','sub_division_id',m.LeadSubdivision,{'name':'name','legacy_status':'status','legacy_deleted':'delete_status'}, {'division':('division','division_id',True)}),
 ('lead_mngt','follow_up','follow_up_id',m.FollowUp,{'call_status':'call_status_id','logged_date_text':'date','logged_time_text':'time','remark':'remark','legacy_update_date':'update_date'}, {'lead':('lead','lead_id',False)}),
 ('lead_mngt','employee_target','target_id',m.EmployeeTarget,{'financial_year':'fin_year','period_start':'fy_start_date','period_end':'fy_end_date','target_cases':'target_cases','target_amount':'target_amount','legacy_status':'status'}, {'employee':('employee','emp_id',False)}),
 ('lead_mngt','employee_tagging','emp_tagging_id',m.EmployeeAssignmentRule,{'usage_of_report_code':'usage_of_report','asset_value':'asset_value'}, {'report_usage':('usage_of_reports','usage_of_report',True),'employee':('employee','emp_id',True),'client_type':('client_type','client_type_id',True),'service':('service_type','service_type_id',True),'subtype':('service_sub_type','service_sub_type_id',True)}),
 ('lead_mngt','party','party_id',m.LeadParty,{'borrower_name':'name_of_borrower','contact_person_name':'contact_person_name','contact_number':'contact_no'}, {'lead':('lead','lead_id',True)}),

 # --- Identity: frozen legacy evidence -------------------------------------
 # Credentials are never imported. Scope columns are recorded, not enforced.
 ('uam_user','project','project_id',m.LegacyProject,{'name':'name','legacy_status':'status'},{}),
 ('uam_user','usertype','utype_id',m.RoleDefinition,{'name':'name','name_hindi':'name_hindi','code':'code','legacy_status':'status','legacy_deleted':'delete_status'}, {'project':('project','project_id',True)}),
 ('uam_user','userdetail','user_id',m.LegacyAccount,{'name':'name','login_id':'login_id','email':'email_id','mobile':'mobile_no','legacy_status':'status'}, {'employee':('employee','user_id',True)}),
 ('uam_user','userdetail_per','user_per_id',m.RoleAssignment,{'legacy_role_code':'usertype_id','legacy_status':'status','legacy_deleted':'delete_status','remark':'remark','scope_region':'region_id','scope_circle':'circle_id','scope_division':'division_id','scope_subdivision':'subdivision_id'}, {'account':('userdetail','user_id',False),'role':('usertype','usertype_id',True),'project':('project','project_id',True)}),
 ('uam_user','login_history','history_id',m.LoginEvent,{'login_at':'login_date','logout_at':'logout_date','ip_address':'ip_address','mac_address':'mac_address','login_action':'login_action'}, {'account':('userdetail','user_id',True)}),

 # Receipts load after identity so maker, checker and verifier resolve to accounts.
 # Legacy receipts do carry a settlement reference: cash_receipt names the invoice
 # directly, amount_received names the valuation. Both are recorded so billing
 # reconciliation has a starting point; neither is a posted allocation.
 ('lead_mngt','cash_receipt','cash_receipt_id',m.Receipt,{'number':'cash_receipt_no','received_date':'date','amount':'ammount','legacy_status':'payment_status','payer_name':'payee_details_name','mode':'mode','remark':'remark','received_as':'received_as','payment_mode':'mode','mobile':'mobile_no','amount_received_on':'ammount_receive_date','cheque_draft_number':'check_draft_no','cheque_draft_bank':'check_draft_issue_bank','issue_date':'issue_date','in_favour_of':'issue_favour_of','proforma_invoice_number':'p_invoice_no','received_against_code':'received_against','receivable_bank_code':'receivable_bank','description':'description','checked_at':'checked_date','verified_at':'verified_date'}, {'invoice':('invoice','invoice_id',True),'office':('client','client_id',True),'borrower':('lead_borrower','lead_borrower_id',True),'document':('upload','upload_id',True),'maker':('userdetail','maker',True),'checked_by':('userdetail','checked_by',True),'verified_by':('userdetail','verified_by',True)}),
 ('lead_mngt','amount_received','amount_received_id',m.Receipt,{'number':'invoice_no','received_date':'payment_date','amount':'amount_received','legacy_status':'verify_status'}, {'valuation':('valuation','valuation_id',True)}),

 # --- Valuations: the report form ------------------------------------------
 ('lead_mngt','detail_category','detail_category_id',m.QuestionCategory,{'name':'detail_category_name','legacy_status':'status','legacy_deleted':'delete_status','source_sequence':'detail_category_id'},{}),
 ('lead_mngt','question','question_id',m.Question,{'text':'question','answer_type':'answer_type','question_type':'question_type','is_document':'is_document','is_mandatory':'is_mandatory','display_order':'is_order','legacy_status':'status','legacy_deleted':'delete_status','source_sequence':'question_id'}, {'service':('service_type','service_type',True),'subtype':('service_sub_type','service_sub_type',True),'category':('detail_category','detail_category',True)}),
 ('lead_mngt','question_options','option_id',m.QuestionOption,{'value':'value','value_type':'value_type','legacy_deleted':'delete_status','source_sequence':'option_id'}, {'question':('question','question_id',False)}),
 # The valuation form itself: 1.95M answer cells, read in pages. answer_group is
 # the repeating-row index for grid questions and is never collapsed. No uniqueness
 # is asserted over (valuation, question, answer_group, option): the legacy data
 # repeats even that combination.
 ('lead_mngt','valuation_answer','answer_id',m.ValuationAnswer,{'answer_group':'answer_group','value':'value'}, {'valuation':('valuation','valuation_id',False),'question':('question','question_id',False),'option':('question_options','option_id',True),'document':('upload','upload_id',True)}),
 ('lead_mngt','valuation_bank_report','report_id',m.BankReport,{'report_number':'report_no','report_date':'report_date','our_reference':'our_reference','your_reference':'your_reference','omen_id':'omen_id','unique_reference':'unique_ref_id','market_fair_amount':'market_fair_amount','realisable_value_amount':'realisable_value_amount','book_value_amount':'book_value_amount','distress_value_amount':'distress_value_amount','market_fair_amount_word':'market_fair_amount_word','realisable_value_amount_word':'realisable_value_amount_word','book_value_amount_word':'book_value_amount_word','distress_value_amount_word':'distress_value_amount_word','bank_certificate':'bank_certificate','legacy_liable_fa':'liable_fa'}, {'valuation':('valuation','valuation_id',False),'bank':('bank','bank_id',True),'branch':('bank_branch','bank_branch_id',True),'document':('upload','upload_id',True)}),
 ('lead_mngt','valuation_verification','verification_id',m.ValuationVerification,{'legal_done_by_name':'legal_verification_done_name','legal_date':'legal_verification_date','legal_status':'legal_verification_status','legal_remark':'legal_verification_remark','technical_done_by_name':'tech_verification_done_name','technical_date':'tech_verification_date','technical_status':'tech_verification_status','technical_remark':'tech_verification_remark','social_done_by_name':'social_verification_done_name','social_date':'social_verification_date','social_status':'social_verification_status','social_remark':'social_verification_remark','general_done_by_name':'general_verification_done_name','general_date':'general_verification_date','general_status':'general_verification_status','general_remark':'general_verification_remark','final_done_by_name':'final_verification_done_name','final_status':'final_verification_status'}, {'valuation':('valuation','valuation_id',False),'legal_done_by':('userdetail','legal_verification_done_by',True),'technical_done_by':('userdetail','tech_verification_done_by',True),'social_done_by':('userdetail','social_verification_done_by',True),'general_done_by':('userdetail','general_verification_done_by',True),'final_done_by':('userdetail','final_verification_done_by',True)}),
 ('lead_mngt','revert_back','revert_id',m.Reversion,{'remark':'revert_remark','reverted_on':'revert_date','reverted_by_name':'revert_by_name'}, {'valuation':('valuation','valuation_id',False),'reverted_by':('userdetail','revert_by',True)}),
 ('lead_mngt','valuation_photo','id',m.ValuationAttachment,{'name':'name','attachment_type':'photo_type'}, {'valuation':('valuation','valuation_id',False),'document':('upload','upload_id',True)}),

 # --- Bank report templates -------------------------------------------------
 # Every link is optional: a template line lost over a lookup would silently
 # change every report built from it. report_setup carries 3 subtype and 1 bank
 # reference that do not resolve; those rows import with the link unset.
 ('lead_mngt','report_setup','report_setup_id',m.ReportTemplate,{'legacy_status':'status','legacy_deleted':'delete_status'}, {'client_type':('client_type','client_type_id',True),'service':('service_type','service_type',True),'subtype':('service_sub_type','service_sub_type',True),'bank':('bank','bank_id',True)}),
 ('lead_mngt','bank_report_heading','bank_report_heading_id',m.ReportHeading,{'name':'bank_report_heading_name','display_order':'is_order','legacy_status':'status','legacy_deleted':'delete_status'}, {'client_type':('client_type','client_type_id',True),'bank':('bank','bank_id',True)}),
 ('lead_mngt','report_question','id',m.ReportTemplateLine,{'output_label':'question_output','content_before':'content_before','content_after':'content_after','sequence':'question_sequence_id','indexing':'report_indexing'}, {'template':('report_setup','setup_id',False),'question':('question','question_id',True),'heading':('bank_report_heading','bank_report_heading_id',True)}),

 # --- Dispatch and notifications --------------------------------------------
 # dispatch has no foreign key; its report references are resolved afterwards by
 # link_dispatch_items. sms_log is the notification history dispatch produced.
 ('lead_mngt','dispatch','dispatch_id',m.Dispatch,{'number':'dispatch_no','client_name':'client_name','customer_name':'client_customer_name','town':'dispatch_town','document_count':'no_of_doc','report_references':'nature_of_docs','other_documents':'other_docs','mode':'mode_of_dispatch','status':'status','courier':'courier_by','other_courier':'other_courier','consignment_number':'consignment_number','authorized_person':'authorized_person','cost':'cost','outward_date':'outward_date','filter_date':'filter_date','delivered_date':'delivered_date','cancelled':'cancle_status','cancel_remark':'cancle_remark'},{}),
 ('lead_mngt','sms_log','sms_log_id',m.SmsMessage,{'reference_client_id':'reference_client_id','record_id':'record_id','mobile':'mobile_no','message':'message','client_type':'client_type','template_id':'template_id','sender_id':'senderid','response_code':'responce_code','response_message':'responce_message','delivery_report':'delivery_report','request_reference':'request_ref_id','gateway_transaction':'reftxid','sent_at':'send_date','server_ip_address':'server_ip_address'},{}),

 # --- Billing ---------------------------------------------------------------
 ('lead_mngt','billing_head','billing_head_id',m.ChargeType,{'name':'billing_head_name','charge_kind':'type','legacy_status':'status','legacy_deleted':'delete_status','source_sequence':'billing_head_id'},{}),
 ('lead_mngt','valuation_billing','billing_id',m.ValuationCharge,{'amount':'amount','cgst':'cgst','sgst':'sgst','igst':'igst','total_amount':'total_amount'}, {'valuation':('valuation','valuation_id',False),'charge_type':('billing_head','billing_head_id',True)}),
 ('lead_mngt','offline_invoice','offline_invoice_id',m.Invoice,{'number':'invoice_no','issued_date':'invoice_date','billed_amount':'total_amount','legacy_status':'payment_status','advance_amount':'advance_amount','reference_lead':'lead_no','reference_work_order':'work_order_no','reference_report':'report_no','billed_to_name':'client_name','billed_customer_name':'client_customer_name','billed_branch_name':'branch_name','billed_branch_code':'branch_code'},{'service':('service_type','service_type',True),'subtype':('service_sub_type','sub_service_type',True),'liable_employee':('employee','liable_fa',True),'doer_employee':('employee','doer_fa',True)}),
 ('lead_mngt','offline_amount_received','offline_amount_received_id',m.Receipt,{'number':'invoice_no','received_date':'payment_date','amount':'amount_received','legacy_status':'payment_status','remark':'remark'}, {'invoice':('offline_invoice','offline_invoice_id',True)}),
 ('lead_mngt','invoice_follow_up','invoice_follow_up_id',m.InvoiceFollowUp,{'call_status':'call_status_id','logged_date_text':'date','logged_time_text':'time','remark':'remark','legacy_update_date':'update_date'}, {'invoice':('invoice','invoice_id',True)}),

 # --- Documents -------------------------------------------------------------
 ('lead_mngt','scrutiny_document','scrutiny_document_id',m.ScrutinyRequirement,{'name':'name','usage_of_report_code':'usage_of_reports_id','legacy_status':'status','legacy_deleted':'delete_status'}, {'report_usage':('usage_of_reports','usage_of_reports_id',True),'service':('service_type','service_type_id',True),'subtype':('service_sub_type','service_sub_type_id',True),'client_type':('client_type','client_type_id',True)}),
 ('uam_user','upload_sys','upload_id',m.UploadConfiguration,{'document_number':'doc_no','document_type':'doc_type','storage_key':'doc_path','size_text':'doc_size','original_name':'doc_name','public_path':'public_path','uploaded_by_name':'upload_by_name'},{}),
 ('lead_mngt','lead_upload','lead_upload_id',m.LeadAttachment,{'attachment_type':'type','remark':'remark','proposal_amount':'proposal_amount','legacy_status':'status'}, {'lead':('lead','lead_id',True),'document':('upload','upload_id',True)}),
 ('lead_mngt','usage_documents','usage_documents_id',m.DocumentUsage,{'usage_of_report_code':'usage_of_reports_id','remarks':'remarks'}, {'report_usage':('usage_of_reports','usage_of_reports_id',True),'lead':('lead','lead_id',True),'document':('upload','doc_upload_id',True)}),

 # --- Work orders -----------------------------------------------------------
 ('lead_mngt','lead_order_history','lead_order_id',m.WorkOrderRevision,{'number':'lead_order_no','legacy_status':'status'}, {'lead':('lead','lead_id',True),'document':('upload','upload_id',True)}),
 ('lead_mngt','wo_fees_calculation','wo_fees_calculation_id',m.FeeRule,{'fmv_category':'fmv_category','fmv_range_min':'fmv_range_min','fmv_range_max':'fmv_range_max','per_lac_amount':'per_lac_amount','additional_charge':'additional_charge','min_fee':'min_fees','max_fee':'max_fees','legacy_deleted':'delete_status'}, {'bank':('bank','bank_id',True)}),

 # --- Sequenced last: these two table names collide with lead_mngt tables ----
 # `maps` is keyed by bare table name, so uam_user.division and uam_user.upload
 # must run after every spec that resolves against lead_mngt.division/upload.
 ('uam_user','division','division_id',m.AdministrativeDivision,{'name':'name','name_hindi':'name_hindi','legacy_status':'status'}, {'circle':('circle','circle_id',True)}),
 ('uam_user','upload','upload_id',m.Document,{'storage_key':'doc_path','original_name':'doc_name','media_type':'doc_type','size_bytes':'doc_size'},{}),
]
ALLOWED = {(s,t) for s,t,*_ in SPECS} | {('uam_user','state'),('uam_user','district')}
# Tables that a later spec resolves a foreign key against. Everything else can be
# discarded once imported instead of being held for the rest of the run.
PARENT_TABLES = {link[0] for spec in SPECS for link in spec[5].values()}
# Source values confirmed wrong, corrected on every import so a fresh import at
# cutover is as correct as this one. Keyed by (schema, table, source id, column);
# applied only while the source still holds the stated wrong value, so a fix made
# at source is never overwritten. The original remains in the staged SourceRow
# payload and each application is recorded as an issue on the row.
# Two-digit years confirmed by the record's own number. 11 offline invoices carry
# dates like 0021-03-04; the invoice number I-MMYYDD... states month and year, and
# on all 11 agrees with 2021 and the month. The year is corrected only when the
# number confirms both; the original remains in the staged payload.
CENTURY_CORRECTIONS = {('lead_mngt', 'offline_invoice', 'invoice_date'): 'invoice_no'}

SOURCE_CORRECTIONS = {
    ('lead_mngt', 'account_detail', '4', 'gst_no'): (
        '23AAACP0165G1ZX', '23AABFO1645E1ZS',
        "Omen's Punjab National Bank account carried 23AAACP0165G1ZX, not Omen's GSTIN; "
        "Omen's other three accounts carry the firm's 23AABFO1645E1ZS. Corrected on the data owner's instruction."),
}
# Children owned by their parent. Once a valuation is edited in this system it is
# locally owned, and its answers belong to that edit: the importer stages their
# source rows as evidence but neither compares them nor requires them to exist,
# since the local edit may have replaced them. Without this, one answer removed by
# an edit leaves a source identity pointing at nothing, which aborts the import.
PARENT_OWNED = {m.ValuationAnswer: ('valuation', 'valuation_id', m.Valuation),
                m.ValuationCharge: ('valuation', 'valuation_id', m.Valuation),
                m.ValuationAttachment: ('valuation', 'valuation_id', m.Valuation)}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), default=str)


def fetch_map(queryset, field, values, keyfunc, size=500):
    """Chunked `__in` lookup. SQLite binds one host parameter per value, so a
    single large `__in` fails outright on a table of any size."""
    found={}
    for start in range(0,len(values),size):
        for record in queryset.filter(**{field+'__in':values[start:start+size]}):
            found[keyfunc(record)]=record
    return found


def source_key(value):
    if value is None or str(value)=='':
        raise ValueError('Missing source ID')
    return canonical([['id',str(value)]])


class MySQLSource:
    """One read-only connection reads both main schemas. Never writes to the source."""
    @contextmanager
    def snapshot(self):
        if 'lead_mngt' not in connections:
            raise ValueError('Use --settings=config.full_database to configure the MySQL source')
        self.connection = connections['lead_mngt']
        if self.connection.vendor != 'mysql':
            raise ValueError('The legacy connection must use MySQL/MariaDB')
        with self.connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
        try:
            yield self
        finally:
            self.connection.rollback()

    def rows(self, schema, table):
        if (schema,table) not in ALLOWED:
            raise ValueError('Table outside import contract')
        with self.connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM `{schema}`.`{table}`')
            keep,columns=readable([c[0].lower() for c in cursor.description])
            return [dict(zip(columns,[row[i] for i in keep])) for row in cursor.fetchall()]

    def chunks(self, schema, table, keycol, size=CHUNK_SIZE):
        """Read in primary-key order, one page at a time.

        Keyset pagination rather than OFFSET: the snapshot is stable, so paging
        on the key is both correct and cheap. Reading in key order also makes the
        batch fingerprint independent of storage order, which the previous
        in-memory sort provided.
        """
        if (schema,table) not in ALLOWED:
            raise ValueError('Table outside import contract')
        last=None
        while True:
            with self.connection.cursor() as cursor:
                if last is None:
                    cursor.execute(f'SELECT * FROM `{schema}`.`{table}` ORDER BY `{keycol}` LIMIT {int(size)}')
                else:
                    cursor.execute(f'SELECT * FROM `{schema}`.`{table}` WHERE `{keycol}`>%s ORDER BY `{keycol}` LIMIT {int(size)}',[last])
                keep,columns=readable([c[0].lower() for c in cursor.description])
                page=[dict(zip(columns,[row[i] for i in keep])) for row in cursor.fetchall()]
            if not page:
                return
            yield page
            if len(page)<size:
                return
            last=page[-1][keycol]


def convert(field, value, warnings, source_column):
    if isinstance(field, (models.CharField,models.TextField)):
        return '' if value is None else str(value)
    if isinstance(field,models.BooleanField):
        # These columns are NOT NULL in the target. A null or unparseable source
        # flag must fall back to False, not abort the run on a NOT NULL violation.
        if value in (None,''): return False
        if isinstance(value,str): return value.strip().lower() not in ('0','false','n','no')
        return bool(value)
    if value in (None,''):
        return None
    if isinstance(field,models.DateTimeField):
        try:
            moment=value if hasattr(value,'year') else datetime.fromisoformat(str(value).replace('T',' ')[:19])
            if isinstance(moment,date) and not isinstance(moment,datetime):
                moment=datetime(moment.year,moment.month,moment.day)
            # Legacy timestamps are wall-clock in the operating timezone.
            return moment if timezone.is_aware(moment) else timezone.make_aware(moment, LEGACY_TIMEZONE)
        except (ValueError,TypeError):
            warnings.append(f'{source_column}: unparseable timestamp retained in source payload only')
            return None
    if isinstance(field,models.DateField):
        try:
            parsed=date.fromisoformat(str(value)[:10])
            if parsed.year < 1900: raise ValueError()
            return parsed
        except ValueError:
            warnings.append(f'Invalid date in {source_column}; raw value retained')
            return None
    if isinstance(field,models.DecimalField):
        result=Decimal(str(value))
        if not result.is_finite(): raise ValueError(f'Invalid decimal in {source_column}')
        return result
    if isinstance(field,models.IntegerField):
        number=Decimal(str(value))
        if not number.is_finite() or number!=number.to_integral_value() or number<0:
            raise ValueError(f'Invalid count in {source_column}')
        return int(number)
    return value


def synchronize(source, *, dry_run=False, progress=lambda message: None):
    """All target rows commit atomically; one failed batch record survives failure.

    Rows invalid under target constraints remain in SourceRow quarantine. An existing
    good target is not overwritten with a now-invalid source correction.
    """
    batch=m.ImportBatch.objects.create(snapshot_checksum='',conversion_version=VERSION,source_environment='main',status='running')
    report={}
    digest=hashlib.sha256()
    try:
        with source.snapshot(), transaction.atomic():
            maps={}
            geo={name:{str(r[name+'_id']):r['name'] or '' for r in source.rows('uam_user',name)} for name in ('state','district')}
            for schema,table,keycol,model,scalars,links in SPECS:
                progress(f'Reading {schema}.{table}')
                counts={'source_rows':0,'inserted':0,'updated':0,'unchanged':0,'quarantined':0,'rows_with_issues':0}
                current={}
                seen=set()
                # Only tables a later spec resolves against are kept in memory.
                retain=table in PARENT_TABLES
                owned_parents=set()
                if model in PARENT_OWNED:
                    owned_parents=set(m.LocalRecord.objects.filter(target_model=PARENT_OWNED[model][2]._meta.label)
                                      .values_list('target_id',flat=True))
                # Legacy service_sub_type duplicates the same subtype name under each service.
                # Index by (normalized name, service) so a row whose subtype FK points at an
                # equivalently named subtype filed under another service can be resolved.
                subtype_by_name={}
                if model in (m.RequestedService,m.Case):
                    for o in maps['service_sub_type'].values():
                        subtype_by_name.setdefault((o.name.strip().lower(),o.service_id),[]).append(o)
                for rows in source.chunks(schema,table,keycol):
                    counts['source_rows']+=len(rows)
                    # Prefetch only what this page needs; a whole-table prefetch does not
                    # survive a repeat run of a multi-million-row table.
                    page_keys=[source_key(r[keycol]) for r in rows]
                    identities=fetch_map(m.SourceIdentity.objects.filter(environment='main',schema=schema,table=table),'key',page_keys,lambda r:r.key)
                    existing=fetch_map(model.objects.all(),'id',[r.target_id for r in identities.values()],lambda r:r.id)
                    locally_owned = set(m.LocalRecord.objects.filter(target_model=model._meta.label).values_list('target_id', flat=True))
                    stages=fetch_map(m.SourceRow.objects.filter(schema=schema,table=table),'key',page_keys,lambda r:r.key)
                    creates,updates,identity_creates,stage_creates,stage_updates,issues=[],[],[],[],[],[]
                    for row in rows:
                        required={keycol,*scalars.values(),*(link[1] for link in links.values())}
                        # Geography is read straight off the row below, so it belongs to
                        # the contract too; otherwise a missing column raises KeyError.
                        if model in (m.ClientOffice,m.Case): required|={'state_id','district_id'}
                        if required-set(row):
                            raise ValueError(f'Source contract missing columns in {schema}.{table}: {sorted(required-set(row))}')
                        key=source_key(row[keycol])
                        if key in seen: raise ValueError(f'Duplicate source key in {schema}.{table}; no arbitrary match selected')
                        seen.add(key)
                        # Defence in depth: the reader already drops these, but the
                        # payload and its fingerprint are the things that persist.
                        payload={k:v for k,v in json.loads(canonical(row)).items() if k not in EXCLUDED_COLUMNS}
                        fingerprint=hashlib.sha256(canonical(payload).encode()).hexdigest()
                        digest.update(canonical([schema,table,key,fingerprint]).encode())
                        warnings=[]; values={}; problem=None; resolved={}
                        ident=identities.get(key)
                        if owned_parents:
                            parent_table,parent_column,_=PARENT_OWNED[model]
                            owner=maps[parent_table].get(str(row.get(parent_column)))
                            if owner is not None and owner.id in owned_parents:
                                # Checked before the missing-target test below, which
                                # sits outside the row's try and would abort the run.
                                counts['unchanged']+=1
                                m.SourceRow.objects.update_or_create(schema=schema,table=table,key=key,
                                    defaults=dict(payload=payload,payload_hash=fingerprint,batch=batch,outcome='imported',
                                                  problems=['Parent record is locally managed; source retained in staging only']))
                                continue
                        obj=existing.get(ident.target_id) if ident else None
                        if ident and obj is None: raise ValueError('Source identity refers to a missing target; repair before import')
                        if obj is not None and obj.id in locally_owned:
                            # Keep current source evidence while preserving the whole
                            # locally edited record and the relationships it owns.
                            warnings.append('Locally managed record; source changes retained in staging only')
                            counts['unchanged'] += 1
                            counts['rows_with_issues'] += 1
                            if retain: current[str(row[keycol])] = obj
                            m.SourceRow.objects.update_or_create(schema=schema, table=table, key=key,
                                defaults=dict(payload=payload, payload_hash=fingerprint, batch=batch,
                                              outcome='imported', problems=warnings))
                            issues.append(m.MigrationIssue(batch=batch, source_identity={'schema':schema,'table':table,'key':key}, reason=warnings[0]))
                            continue
                        try:
                            for field,column in scalars.items():
                                f=model._meta.get_field(field)
                                raw=row[column]
                                witness=CENTURY_CORRECTIONS.get((schema,table,column))
                                if witness and hasattr(raw,'year') and raw.year<100:
                                    number=str(row.get(witness) or '')
                                    if re.fullmatch(r'[A-Z]-\d{7,}',number) and int(number[4:6])==raw.year and int(number[2:4])==raw.month:
                                        warnings.append(f'{column} year corrected from {raw.year:04d} to {2000+raw.year}, as stated by {witness} {number}')
                                        raw=raw.replace(year=2000+raw.year)
                                fix=SOURCE_CORRECTIONS.get((schema,table,str(row[keycol]),column))
                                if fix and str(raw or '').strip()==fix[0]:
                                    raw=fix[1]
                                    warnings.append(f'{column} corrected from {fix[0]} to {fix[1]}: {fix[2]}')
                                value=convert(f,raw,warnings,column)
                                f.run_validators(value)
                                values[field]=value
                            for field,(parent,column,optional) in links.items():
                                source_id=row[column]
                                linked=maps[parent].get(str(source_id))
                                if linked is None and source_id is not None:
                                    # Legacy stores some parent keys as zero-padded varchar
                                    # ('010101' for block 10101). MySQL compares these
                                    # numerically; a string lookup does not.
                                    text=str(source_id).strip()
                                    if text.isdigit():
                                        linked=maps[parent].get(str(int(text)))
                                resolved[field]=linked
                                values[field+'_id']=linked.id if linked else None
                                if linked is None and not optional:
                                    raise ValueError(f'Missing or quarantined required parent: {column}')
                                if linked is None and source_id not in (None,'',0,'0'):
                                    warnings.append(f'Unmatched optional parent: {column}')
                            if model is m.ClientOffice:
                                values.update(state=geo['state'].get(str(row['state_id']),''),district=geo['district'].get(str(row['district_id']),''))
                                directory=resolved.get('directory_branch')
                                if directory and values['bank_id'] and directory.bank_id!=values['bank_id']:
                                    raise ValueError('Office bank disagrees with directory branch bank')
                            if model is m.Case:
                                values.update(asset_state=geo['state'].get(str(row['state_id']),''),
                                              asset_district=geo['district'].get(str(row['district_id']),''))
                            if model is m.Lead: values['date_basis']='lead_entry_proxy'
                            # DEPLOYMENT_INVENTORY: the lead application stores uploads in S3,
                            # UAM/HRMS on a local server path. Neither set of bytes is migrated.
                            if model is m.Document:
                                values['storage_provider']='legacy_lead_s3' if schema=='lead_mngt' else 'legacy_uam_local'
                            if model is m.Invoice: values['origin']='legacy_'+table
                            if model is m.Receipt: values['origin']='legacy_'+table
                            if model is m.SalaryBaseline: values['source_variant']=table
                            if model in (m.RequestedService,m.Case):
                                subtype=resolved.get('subtype')
                                if subtype and subtype.service_id!=values['service_id']:
                                    # Subtype is an optional classification. A mismatch is a legacy
                                    # referential defect, not grounds for discarding the business row.
                                    # Matching names are evidence, not proof of equivalence, so an
                                    # ambiguous match is never resolved by picking one arbitrarily.
                                    siblings=subtype_by_name.get((subtype.name.strip().lower(),values['service_id']),[])
                                    if len(siblings)==1:
                                        values['subtype_id']=siblings[0].id
                                        warnings.append(f"Subtype {row['service_sub_type_id']} is filed under a different service; remapped by normalized name (trimmed, case-insensitive) to the one matching subtype of the declared service")
                                    elif len(siblings)>1:
                                        values['subtype_id']=None
                                        warnings.append(f"Subtype {row['service_sub_type_id']} is filed under a different service and its name matches {len(siblings)} subtypes of the declared service; ambiguous, subtype cleared")
                                    else:
                                        values['subtype_id']=None
                                        warnings.append(f"Subtype {row['service_sub_type_id']} is filed under a different service with no equivalent under the declared service; subtype cleared")
                            if model is m.ValuationAnswer:
                                option=resolved.get('option')
                                if option is not None and option.question_id!=values['question_id']:
                                    # The option is a column of a different question and cannot label
                                    # this cell. Keep the answer and its raw value; drop only the
                                    # unusable link. SourceRow still holds the original option id.
                                    values['option_id']=None
                                    warnings.append(f"Option {row['option_id']} belongs to a different question; option link cleared")
                            if model in (m.Case,m.WorkOrder):
                                borrower=resolved['borrower']
                                if borrower.lead_id!=values['lead_id']: raise ValueError('Borrower belongs to a different lead')
                            if model is m.Valuation and values['work_order_id']:
                                order=resolved['work_order']; case=resolved['case']
                                if order.lead_id!=case.lead_id or order.borrower_id!=case.borrower_id:
                                    raise ValueError('Valuation case and order refer to different lead/borrower')
                            if obj is None:
                                obj=model(id=uuid.uuid5(NS,f'{schema}.{table}:{key}'),**values)
                                creates.append(obj); counts['inserted']+=1
                                identity_creates.append(m.SourceIdentity(batch=batch,environment='main',schema=schema,table=table,key=key,target_model=model._meta.label,target_id=obj.id))
                            elif any(getattr(obj,k)!=v for k,v in values.items()):
                                for k,v in values.items(): setattr(obj,k,v)
                                obj.updated_at=datetime.now().astimezone(); updates.append(obj); counts['updated']+=1
                            else: counts['unchanged']+=1
                            if retain: current[str(row[keycol])]=obj
                        except (ValueError,InvalidOperation,ValidationError) as exc:
                            problem=str(exc) if not isinstance(exc,ValidationError) else 'Value violates target field limits'
                            warnings.append(problem); counts['quarantined']+=1
                        if warnings:
                            counts['rows_with_issues']+=1
                            issues.append(m.MigrationIssue(batch=batch,source_identity={'schema':schema,'table':table,'key':key},reason='; '.join(warnings)))
                        outcome='quarantined' if problem else 'imported'
                        prior=stages.get(key)
                        values_stage=dict(payload=payload,payload_hash=fingerprint,batch=batch,outcome=outcome,problems=warnings)
                        if prior is None: stage_creates.append(m.SourceRow(schema=schema,table=table,key=key,**values_stage))
                        elif prior.payload_hash!=fingerprint or prior.outcome!=outcome or prior.problems!=warnings:
                            for k,v in values_stage.items():setattr(prior,k,v)
                            stage_updates.append(prior)
                    model.objects.bulk_create(creates,batch_size=400)
                    # Only import-owned fields are updated: local office owner and note rows are untouched.
                    update_fields=[*scalars,*links]
                    extra={m.ClientOffice:['state','district'],m.Case:['asset_state','asset_district'],m.Lead:['date_basis'],m.Document:['storage_provider'],m.Invoice:['origin'],m.Receipt:['origin'],m.SalaryBaseline:['source_variant']}.get(model,[])
                    model.objects.bulk_update(updates,update_fields+extra+['updated_at'],batch_size=300)
                    m.SourceIdentity.objects.bulk_create(identity_creates,batch_size=400)
                    m.SourceRow.objects.bulk_create(stage_creates,batch_size=300)
                    m.SourceRow.objects.bulk_update(stage_updates,['payload','payload_hash','batch','outcome','problems'],batch_size=250)
                    m.MigrationIssue.objects.bulk_create(issues,batch_size=400)
                maps[table]=current if retain else {}
                assert sum(counts[k] for k in ('inserted','updated','unchanged','quarantined'))==counts['source_rows']
                report[f'{schema}.{table}']=counts
                progress(f'{table}: {counts}')
            batch.snapshot_checksum=digest.hexdigest(); batch.summary=report
            batch.status='completed_with_issues' if any(r['rows_with_issues'] for r in report.values()) else 'completed'
            batch.save()
            if dry_run: transaction.set_rollback(True)
        if dry_run: batch.delete()
        return report
    except Exception:
        if dry_run: batch.delete()
        else:
            batch.status='failed'; batch.summary={'error':'Import rolled back; inspect command error and correct input before retrying'}; batch.save()
        raise
