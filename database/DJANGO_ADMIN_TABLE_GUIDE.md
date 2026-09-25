# Django admin table guide

All 83 existing business and migration models have explicit list layouts. Database schema, domain grouping and existing write permissions are unchanged.

## Using the lists

- Click a column heading to sort. Related columns show business names/numbers instead of UUID object labels.
- Use the search box for the fields listed below. Fields marked `=` use exact, case-insensitive matching; other searches match contained text.
- Use the right-hand filters for status, dates and smaller reference lists. High-cardinality clients, documents and transactions use search instead of huge dropdowns.
- Relationship selectors on forms use permission-checked autocomplete with readable labels.
- Lists show 50 records per page. Extra full-result counts and filter facet counts are disabled; pagination still uses an exact result count.
- Large JSON evidence payloads stay on detail pages rather than being loaded into metadata-only lists. Long text in lists is shortened; full content remains on the record.
- Credential hashes are excluded. Migration/audit evidence remains read-only; this does not change the previously documented business workflow limitations.

## Model layouts

### Accounts

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| LegacyProject | `name`, `legacy_status` | `name` | `legacy_status` | `name` |
| RoleDefinition | `name`, `project__name`, `code`, `legacy_status`, `legacy_deleted` | `name`, `code`, `name_hindi`, `project__name` | `project`, `legacy_status`, `legacy_deleted` | `project__name`, `name` |
| LegacyAccount | `name`, `login_id`, `employee__name`, `user__username`, `legacy_status`, `must_change_password`, `provisioned_at` | `name`, `login_id`, `email`, `mobile`, `employee__employee_code` | `legacy_status`, `must_change_password`, `provisioned_at` | `name` |
| RoleAssignment | `account__login_id`, `role__name`, `project__name`, `legacy_status`, `scope_region`, `scope_circle` | `account__login_id`, `account__name`, `role__name`, `legacy_role_code` | `project`, `legacy_status`, `legacy_deleted` | `account__login_id` |
| LoginEvent | `account__login_id`, `login_at`, `logout_at`, `login_action`, `ip_address` | `account__login_id`, `account__name`, `ip_address`, `login_action` | `login_at` | `-login_at` |

### Organization

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Employee | `name`, `employee_code`, `user__username`, `legacy_status` | `name`, `employee_code`, `user__username` | `legacy_status`, `user__is_active` | `name` |
| SalaryBaseline | `employee__name`, `employee__employee_code`, `source_variant`, `legacy_status` | `employee__name`, `employee__employee_code`, `source_variant` | `source_variant`, `legacy_status` | `employee__name` |
| SalaryBaselineComponent | `baseline__employee__name`, `pay_code`, `amount`, `from_period`, `to_period`, `mode` | `baseline__employee__name`, `baseline__employee__employee_code`, `pay_code` | `mode` | `baseline__employee__name`, `pay_code` |
| SalaryResult | `employee__name`, `employee__employee_code`, `period`, `gross_earning`, `gross_deduction`, `net_salary`, `legacy_payment_status` | `employee__name`, `employee__employee_code`, `period` | `legacy_payment_status` | `-period`, `employee__name` |
| LeaveOpeningBalance | `employee__name`, `leave_type_code`, `as_of_date`, `days`, `reconciled` | `employee__name`, `employee__employee_code`, `leave_type_code` | `reconciled`, `as_of_date`, `leave_type_code` | `-as_of_date` |
| LeadDivision | `name`, `legacy_status`, `legacy_deleted` | `name` | `legacy_status`, `legacy_deleted` | `name` |
| LeadSubdivision | `name`, `division__name`, `legacy_status`, `legacy_deleted` | `name`, `division__name` | `division`, `legacy_status`, `legacy_deleted` | `name` |
| EmployeeTarget | `employee__name`, `financial_year`, `period_start`, `period_end`, `target_cases`, `target_amount`, `legacy_status` | `employee__name`, `employee__employee_code`, `financial_year` | `legacy_status`, `period_start` | `-period_start` |
| EmployeeAssignmentRule | `employee__name`, `client_type__name`, `service__name`, `subtype__name`, `report_usage__name`, `asset_value` | `employee__name`, `employee__employee_code`, `service__name`, `report_usage__name` | `client_type`, `service` | `employee__name` |

### Directory

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Bank | `name`, `legacy_status` | `name` | `legacy_status` | `name` |
| BankBranch | `name`, `bank__name`, `ifsc`, `city`, `district`, `state` | `name`, `=ifsc`, `=micr`, `bank__name`, `city`, `district` | `bank` | `name` |
| ClientType | `name`, `created_at` | `name` | `created_at` | `name` |
| ClientOffice | `name`, `branch_name`, `bank__name`, `client_type__name`, `owner__name`, `state`, `district`, `legacy_working_status` | `name`, `branch_name`, `bank__name`, `ifsc`, `gstin`, `district` | `client_type`, `legacy_working_status` | `name` |
| ContactDesignation | `name`, `created_at` | `name` | `created_at` | `name` |
| Contact | `name`, `office__name`, `designation__name`, `phone`, `alternate_phone` | `name`, `phone`, `alternate_phone`, `office__name` | `designation` | `name` |

### Catalog

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| ServiceType | `name`, `created_at` | `name` | `created_at` | `name` |
| ServiceSubtype | `name`, `service__name` | `name`, `service__name` | `service` | `service__name`, `name` |
| State | `name`, `name_hindi`, `census_code`, `legacy_status` | `name`, `name_hindi`, `census_code` | `legacy_status` | `name` |
| District | `name`, `state__name`, `name_hindi`, `census_code`, `legacy_status` | `name`, `name_hindi`, `census_code`, `state__name` | `state`, `legacy_status` | `name` |
| Region | `name`, `name_hindi`, `legacy_status` | `name`, `name_hindi` | `legacy_status` | `name` |
| Circle | `name`, `region__name`, `name_hindi`, `legacy_status` | `name`, `name_hindi`, `region__name` | `region`, `legacy_status` | `name` |
| Block | `name`, `district__name`, `region__name`, `circle__name`, `census_code`, `area_type`, `legacy_status` | `name`, `name_hindi`, `census_code`, `district__name` | `region`, `area_type`, `legacy_status` | `name` |
| Panchayat | `name`, `block__name`, `name_hindi`, `legacy_status` | `name`, `name_hindi`, `block__name` | `legacy_status` | `name` |
| Village | `name`, `panchayat__name`, `legacy_panchayat_code`, `census_code`, `pincode`, `area_type`, `legacy_status` | `name`, `name_hindi`, `census_code`, `pincode`, `legacy_panchayat_code` | `area_type`, `legacy_status` | `name` |
| City | `name`, `name_hindi`, `code`, `legacy_status` | `name`, `name_hindi`, `code` | `legacy_status` | `name` |
| Location | `name`, `city__name`, `code`, `legacy_status` | `name`, `name_hindi`, `code`, `city__name` | `legacy_status` | `name` |
| SubLocation | `name`, `location__name`, `code`, `legacy_status` | `name`, `name_hindi`, `code`, `location__name` | `legacy_status` | `name` |
| AdministrativeDivision | `name`, `circle__name`, `name_hindi`, `legacy_status` | `name`, `name_hindi`, `circle__name` | `legacy_status` | `name` |
| OfficialLocation | `name`, `city__name`, `kind`, `code`, `legacy_status` | `name`, `name_hindi`, `code`, `city__name` | `kind`, `legacy_status` | `name` |
| IfscArea | `ifsc`, `state__name`, `district__name`, `block__name` | `=ifsc`, `state__name`, `district__name`, `block__name` | `state` | `ifsc` |
| ScrutinyRequirement | `name`, `service__name`, `subtype__name`, `client_type__name`, `report_usage__name`, `legacy_status` | `name`, `report_usage__name`, `usage_of_report_code` | `service`, `client_type`, `legacy_status`, `legacy_deleted` | `name` |
| ReportUsage | `name`, `service__name`, `subtype__name`, `legacy_status`, `legacy_deleted` | `name`, `service__name` | `service`, `legacy_status`, `legacy_deleted` | `name` |

### Leads

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Lead | `number`, `office__name`, `contact__name`, `assigned_employee__name`, `received_date`, `legacy_status`, `enquiry_mode`, `party_count` | `number`, `office__name`, `contact__name`, `contact__phone`, `assigned_employee__name`, `legacy_number_old` | `legacy_status`, `legacy_deleted`, `enquiry_mode`, `received_date`, `date_basis` | `-received_date` |
| RequestedService | `lead__number`, `service__name`, `subtype__name`, `party_count`, `case_count` | `lead__number`, `lead__office__name`, `service__name`, `subtype__name` | `service` | `-created_at` |
| Borrower | `name`, `lead__number`, `contact_number`, `agreed_fee`, `property_count`, `payer`, `pay_by_date`, `legacy_deleted` | `name`, `lead__number`, `contact_number`, `email`, `gst_number` | `payer`, `fee_basis`, `legacy_deleted`, `pay_by_date` | `name` |
| Case | `lead__number`, `borrower__name`, `service__name`, `subtype__name`, `asset_district`, `asset_amount`, `expected_report_date`, `legacy_status` | `lead__number`, `borrower__name`, `asset_address`, `asset_district`, `contact_number` | `service`, `legacy_status`, `expected_report_date` | `-created_at` |
| LeadNote | `lead__number`, `author__username`, `body`, `created_at` | `lead__number`, `author__username`, `body` | `created_at` | `-created_at` |
| FollowUp | `lead__number`, `call_status`, `logged_date_text`, `logged_time_text`, `remark` | `lead__number`, `remark`, `logged_date_text` | `call_status` | `-created_at` |
| LeadParty | `lead__number`, `borrower_name`, `contact_person_name`, `contact_number` | `lead__number`, `borrower_name`, `contact_person_name`, `contact_number` | `created_at` | `-created_at` |
| LeadAttachment | `lead__number`, `document__original_name`, `attachment_type`, `proposal_amount`, `legacy_status` | `lead__number`, `document__original_name`, `remark` | `attachment_type`, `legacy_status` | `-created_at` |

### Workorders

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| WorkOrder | `number`, `lead__number`, `borrower__name`, `issued_at`, `issued_by__username`, `legacy_status`, `document__original_name` | `number`, `lead__number`, `borrower__name`, `legacy_number_old` | `legacy_status`, `legacy_deleted`, `issued_at` | `-created_at` |
| WorkOrderRevision | `number`, `lead__number`, `document__original_name`, `legacy_status`, `created_at` | `number`, `lead__number`, `document__original_name` | `legacy_status`, `created_at` | `-created_at` |

### Valuations

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Valuation | `report_number`, `case__lead__number`, `case__borrower__name`, `case__service__name`, `assessor_name`, `valuation_date`, `legacy_status`, `total_after_tax` | `report_number`, `case__lead__number`, `case__borrower__name`, `assessor_name` | `legacy_status`, `case__service`, `report_category`, `valuation_date` | `-valuation_date` |
| QuestionCategory | `name`, `source_sequence`, `legacy_status`, `legacy_deleted` | `name` | `legacy_status`, `legacy_deleted` | `source_sequence`, `name` |
| Question | `text`, `service__name`, `subtype__name`, `category__name`, `answer_type`, `question_type`, `is_mandatory`, `is_document`, `source_sequence` | `text`, `category__name`, `service__name` | `service`, `answer_type`, `question_type`, `is_mandatory`, `is_document`, `legacy_status`, `legacy_deleted` | `source_sequence` |
| QuestionOption | `question__text`, `value`, `value_type`, `source_sequence`, `legacy_deleted` | `question__text`, `value`, `value_type` | `legacy_deleted` | `source_sequence` |
| ValuationAnswer | `valuation__report_number`, `question__text`, `option__value`, `answer_group`, `value`, `document__original_name` | `valuation__report_number`, `valuation__case__lead__number`, `question__text`, `value` | `question__answer_type` | `id` |
| ValuationVerification | `valuation__report_number`, `legal_status`, `technical_status`, `social_status`, `general_status`, `final_status`, `final_done_by_name` | `valuation__report_number`, `valuation__case__lead__number`, `final_done_by_name`, `legal_done_by_name`, `technical_done_by_name` | `legal_status`, `technical_status`, `social_status`, `general_status`, `final_status` | `-created_at` |
| Reversion | `valuation__report_number`, `stage`, `reverted_on`, `reverted_by_name`, `remark` | `valuation__report_number`, `reverted_by_name`, `remark` | `stage`, `reverted_on` | `-reverted_on` |
| ValuationAttachment | `valuation__report_number`, `name`, `attachment_type`, `document__original_name` | `valuation__report_number`, `valuation__case__lead__number`, `name`, `document__original_name` | `attachment_type` | `-created_at` |
| ValuationEvent | `valuation__report_number`, `kind`, `from_status`, `to_status`, `on`, `by_name`, `reason` | `valuation__report_number`, `by_name`, `reason` | `kind`, `on` | `-on` |

### Reports

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| BankReport | `report_number`, `valuation__case__borrower__name`, `bank__name`, `report_date`, `revision`, `market_fair_amount`, `generated_at`, `approved_at`, `superseded_at` | `report_number`, `valuation__case__borrower__name`, `our_reference`, `your_reference`, `unique_reference` | `bank`, `report_date`, `approved_at`, `superseded_at` | `-report_date` |
| ReportTemplate | `client_type__name`, `bank__name`, `service__name`, `subtype__name`, `legacy_status`, `legacy_deleted` | `client_type__name`, `bank__name`, `service__name`, `subtype__name` | `client_type`, `bank`, `service`, `legacy_status`, `legacy_deleted` | `service__name`, `bank__name` |
| ReportHeading | `name`, `client_type__name`, `bank__name`, `display_order`, `legacy_status`, `legacy_deleted` | `name`, `bank__name` | `client_type`, `legacy_status`, `legacy_deleted` | `display_order`, `name` |
| ReportTemplateLine | `template__bank__name`, `template__service__name`, `heading__name`, `sequence`, `indexing`, `output_label`, `question__text` | `output_label`, `question__text`, `template__bank__name`, `heading__name` | `template__client_type`, `template__service` | `sequence` |

### Billing

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| ChargeType | `name`, `charge_kind`, `source_sequence`, `legacy_status`, `legacy_deleted` | `name`, `charge_kind` | `charge_kind`, `legacy_status`, `legacy_deleted` | `source_sequence`, `name` |
| ValuationCharge | `valuation__report_number`, `charge_type__name`, `amount`, `cgst`, `sgst`, `igst`, `total_amount` | `valuation__report_number`, `valuation__case__lead__number`, `charge_type__name` | `charge_type` | `-created_at` |
| Invoice | `number`, `valuation__report_number`, `office__name`, `origin`, `issued_date`, `due_date`, `billed_amount`, `legacy_paid_amount`, `legacy_remaining_amount`, `legacy_status`, `cancelled_at` | `number`, `valuation__report_number`, `valuation__case__borrower__name`, `office__name`, `legacy_number_old` | `origin`, `legacy_status`, `issued_date`, `due_date`, `cancelled_at`, `place_of_supply` | `-issued_date` |
| InvoiceLine | `invoice__number`, `description`, `net_amount`, `tax_amount`, `total_amount`, `position` | `invoice__number`, `description`, `charge_type__name` | `charge_type` | `invoice__number`, `position` |
| Receipt | `number`, `invoice__number`, `valuation__report_number`, `payer_name`, `received_date`, `amount`, `origin`, `legacy_status`, `verified` | `number`, `invoice__number`, `valuation__report_number`, `payer_name`, `mobile`, `cheque_draft_number` | `origin`, `verified`, `legacy_status`, `received_as`, `payment_mode`, `received_date` | `-received_date` |
| ReceiptAllocation | `receipt__number`, `invoice__number`, `amount`, `posting_key`, `created_at` | `receipt__number`, `invoice__number`, `=posting_key` | `created_at` | `-created_at` |
| InvoiceFollowUp | `invoice__number`, `call_status`, `logged_date_text`, `logged_time_text`, `remark` | `invoice__number`, `remark`, `logged_date_text` | `call_status` | `-created_at` |
| IssuerAccount | `name`, `code`, `account_number`, `ifsc_code`, `branch_code`, `gst_number` | `name`, `account_number`, `ifsc_code`, `gst_number` | `created_at` | `code` |
| FeeRule | `bank__name`, `fmv_category`, `fmv_range_min`, `fmv_range_max`, `per_lac_amount`, `min_fee`, `max_fee`, `legacy_deleted` | `bank__name`, `fmv_category` | `bank`, `fmv_category`, `legacy_deleted` | `bank__name`, `fmv_range_min` |
| CreditNote | `number`, `invoice__number`, `issued_on`, `total_amount`, `refund_due`, `issued_by_name`, `reason` | `number`, `invoice__number`, `issued_by_name`, `reason` | `issued_on` | `-issued_on` |

### Documents

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Document | `original_name`, `storage_provider`, `media_type`, `size_bytes`, `content_verified`, `created_at` | `original_name`, `=storage_key`, `=checksum` | `storage_provider`, `content_verified` | `id` |
| UploadConfiguration | `document_number`, `document_type`, `original_name`, `size_text`, `uploaded_by_name` | `document_number`, `original_name`, `uploaded_by_name`, `=storage_key` | `document_type` | `-created_at` |
| DocumentUsage | `lead__number`, `document__original_name`, `report_usage__name`, `usage_of_report_code`, `remarks` | `lead__number`, `document__original_name`, `report_usage__name`, `remarks` | `created_at` | `-created_at` |

### Dispatch

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| Dispatch | `number`, `client_name`, `customer_name`, `mode`, `status`, `consignment_number`, `outward_date`, `delivered_date`, `cancelled` | `number`, `client_name`, `customer_name`, `report_references`, `consignment_number` | `mode`, `status`, `cancelled`, `outward_date`, `delivered_date` | `-outward_date` |
| DispatchItem | `dispatch__number`, `position`, `reference`, `valuation__report_number`, `lead__number`, `resolution` | `dispatch__number`, `reference`, `valuation__report_number`, `lead__number` | `resolution` | `dispatch__number`, `position` |
| SmsMessage | `mobile`, `sent_at`, `client_type`, `template_id`, `response_code`, `delivery_report` | `=mobile`, `=request_reference`, `=gateway_transaction`, `message` | `client_type`, `sent_at` | `-sent_at` |

### Migration Pipeline

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| ImportBatch | `id`, `source_environment`, `conversion_version`, `status`, `created_at` | `=id`, `snapshot_checksum`, `conversion_version` | `source_environment`, `status`, `created_at` | `-created_at` |
| SourceIdentity | `schema`, `table`, `key`, `environment`, `target_model`, `target_id` | `=key`, `=target_id`, `target_model` | `environment`, `schema`, `table` | `id` |
| MigrationIssue | `id`, `reason`, `resolved`, `resolution`, `batch__created_at` | `reason`, `resolution` | `resolved`, `created_at` | `-created_at` |
| SourceRow | `schema`, `table`, `key`, `outcome`, `batch__created_at` | `=key` | `schema`, `table`, `outcome` | `id` |

### Audit

| Model | Columns | Search | Filters | Default order |
|---|---|---|---|---|
| LocalRecord | `target_model`, `target_id`, `created_at`, `updated_at` | `target_model`, `=target_id` | `created_at` | `-created_at` |
| IntakeAudit | `action`, `target_model`, `target_id`, `actor__username`, `created_at` | `action`, `target_model`, `=target_id`, `actor__username` | `created_at` | `-created_at` |
| LeadCounter | `name`, `value` | `name` | None needed | `name` |

## Maintaining the configuration

Edit `backend/apps/common/admin_options.py` to adjust a model’s reviewed layout. Double underscores follow relationships, for example `valuation__case__borrower__name`. Django system checks and `apps.accounts.test_admin_lists` validate the lookup paths and render/search all 83 model pages. No model migration is needed for presentation-only changes.
