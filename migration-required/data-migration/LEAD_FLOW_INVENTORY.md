# Legacy lead flow source inventory

Generated from the current Java controllers and Django import specifications. See [LEAD_FLOW_MIGRATION_AUDIT.md](LEAD_FLOW_MIGRATION_AUDIT.md) for business meaning, execution checks and gaps.

Java mappings are static evidence. ANY means no HTTP method restriction is specified in the annotation; it does not authorize carrying that behavior into Django. Paths may have multiple class aliases.

## Every source controller and declared action

### AJAXController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/ajax/get_district_list`<br>`/ajax/get_district_list` | [AJAXController.java:49](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L49) |
| GET | `/user/ajax/get_city_list`<br>`/ajax/get_city_list` | [AJAXController.java:59](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L59) |
| POST | `/user/ajax/get_borrower_list`<br>`/ajax/get_borrower_list` | [AJAXController.java:69](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L69) |
| POST | `/user/ajax/get_invoice_list`<br>`/ajax/get_invoice_list` | [AJAXController.java:79](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L79) |
| POST | `/user/ajax/get_bankstate_list`<br>`/ajax/get_bankstate_list` | [AJAXController.java:89](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L89) |
| POST | `/user/ajax/get_bankdistrict_list`<br>`/ajax/get_bankdistrict_list` | [AJAXController.java:99](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L99) |
| POST | `/user/ajax/get_bankcity_list`<br>`/ajax/get_bankcity_list` | [AJAXController.java:110](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L110) |
| GET | `/user/ajax/get_serviceSubType_list`<br>`/ajax/get_serviceSubType_list` | [AJAXController.java:121](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L121) |
| POST | `/user/ajax/get_bankbranch_list`<br>`/ajax/get_bankbranch_list` | [AJAXController.java:131](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L131) |
| POST | `/user/ajax/get_bankbranch_new_list`<br>`/ajax/get_bankbranch_new_list` | [AJAXController.java:142](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L142) |
| POST | `/user/ajax/get_bankbranch_District_list`<br>`/ajax/get_bankbranch_District_list` | [AJAXController.java:153](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L153) |
| GET | `/user/ajax/get_usageOfReports_list`<br>`/ajax/get_usageOfReports_list` | [AJAXController.java:164](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L164) |
| GET | `/user/ajax/get_scrutinyDocument_list`<br>`/ajax/get_scrutinyDocument_list` | [AJAXController.java:175](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L175) |
| GET | `/user/ajax/get_serviceSubTypeNew_list`<br>`/ajax/get_serviceSubTypeNew_list` | [AJAXController.java:185](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L185) |
| GET | `/user/ajax/get_client_list`<br>`/ajax/get_client_list` | [AJAXController.java:195](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L195) |
| POST | `/user/ajax/get_client`<br>`/ajax/get_client` | [AJAXController.java:214](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L214) |
| GET | `/user/ajax/get_client_by_ifsc`<br>`/ajax/get_client_by_ifsc` | [AJAXController.java:224](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L224) |
| POST | `/user/ajax/get_subdivision`<br>`/ajax/get_subdivision` | [AJAXController.java:235](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L235) |
| GET | `/user/ajax/get_client_by_Id`<br>`/ajax/get_client_by_Id` | [AJAXController.java:245](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L245) |
| POST | `/user/ajax/reports`<br>`/ajax/reports` | [AJAXController.java:257](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AJAXController.java#L257) |

### AmountReceivedController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/amount_received/list`<br>`/user/amount_received1/list` | [AmountReceivedController.java:74](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L74) |
| GET | `/user/amount_received/bad_bebt_list`<br>`/user/amount_received1/bad_bebt_list` | [AmountReceivedController.java:102](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L102) |
| POST | `/user/amount_received/search`<br>`/user/amount_received1/search` | [AmountReceivedController.java:131](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L131) |
| ANY | `/user/amount_received/export_data`<br>`/user/amount_received1/export_data` | [AmountReceivedController.java:181](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L181) |
| GET | `/user/amount_received/update_bad_debt/{invoiceIdEnc}`<br>`/user/amount_received1/update_bad_debt/{invoiceIdEnc}` | [AmountReceivedController.java:275](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L275) |
| POST | `/user/amount_received/save_bad_debt`<br>`/user/amount_received1/save_bad_debt` | [AmountReceivedController.java:303](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L303) |
| GET | `/user/amount_received/update_invoice_status/{invoiceIdEnc}`<br>`/user/amount_received1/update_invoice_status/{invoiceIdEnc}` | [AmountReceivedController.java:343](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L343) |
| POST | `/user/amount_received/save_invoice_status`<br>`/user/amount_received1/save_invoice_status` | [AmountReceivedController.java:370](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L370) |
| GET | `/user/amount_received/update_payment/{invoiceIdEnc}`<br>`/user/amount_received1/update_payment/{invoiceIdEnc}` | [AmountReceivedController.java:407](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L407) |
| GET | `/user/amount_received/view_payment/{invoiceNo}`<br>`/user/amount_received1/view_payment/{invoiceNo}` | [AmountReceivedController.java:476](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L476) |
| GET | `/user/amount_received/history/{invoiceId}`<br>`/user/amount_received1/history/{invoiceId}` | [AmountReceivedController.java:501](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L501) |
| POST | `/user/amount_received/save_followup`<br>`/user/amount_received1/save_followup` | [AmountReceivedController.java:529](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L529) |
| POST | `/user/amount_received/save_update_amount`<br>`/user/amount_received1/save_update_amount` | [AmountReceivedController.java:568](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L568) |
| GET | `/user/amount_received/total_list`<br>`/user/amount_received1/total_list` | [AmountReceivedController.java:614](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L614) |
| POST | `/user/amount_received/received_amount_search`<br>`/user/amount_received1/received_amount_search` | [AmountReceivedController.java:626](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L626) |
| ANY | `/user/amount_received/update_status/{amountReceivedIdEnc}`<br>`/user/amount_received1/update_status/{amountReceivedIdEnc}` | [AmountReceivedController.java:652](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L652) |
| ANY | `/user/amount_received/delete/{amountReceivedIdEnc}`<br>`/user/amount_received1/delete/{amountReceivedIdEnc}` | [AmountReceivedController.java:677](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/AmountReceivedController.java#L677) |

### BankController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/bank/detail` | [BankController.java:31](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankController.java#L31) |
| ANY | `/user/bank/search` | [BankController.java:41](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankController.java#L41) |

### BankReportController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/valuation/bankReport/{valuationIdEnc}` | [BankReportController.java:61](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L61) |
| GET | `/user/valuation/report_question` | [BankReportController.java:101](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L101) |
| POST | `/user/valuation/savebankReport` | [BankReportController.java:119](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L119) |
| GET | `/user/valuation/revert_back/{valuationIdEnc}` | [BankReportController.java:209](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L209) |
| POST | `/user/valuation/saveRevertBack` | [BankReportController.java:251](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L251) |
| GET | `/user/valuation/final_bankReport_approval/{valuationIdEnc}` | [BankReportController.java:330](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L330) |
| POST | `/user/valuation/saveFinalBankReportApproval` | [BankReportController.java:368](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L368) |
| GET | `/user/valuation/final_revert_back/{valuationIdEnc}` | [BankReportController.java:396](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L396) |
| POST | `/user/valuation/saveFinalRevertBack` | [BankReportController.java:438](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportController.java#L438) |

### BankReportHeadingController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/bank_heading/detail` | [BankReportHeadingController.java:42](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L42) |
| GET | `/user/bank_heading/add` | [BankReportHeadingController.java:56](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L56) |
| POST | `/user/bank_heading/save` | [BankReportHeadingController.java:70](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L70) |
| GET | `/user/bank_heading/add_iframe` | [BankReportHeadingController.java:97](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L97) |
| GET | `/user/bank_heading/edit/{bankReportHeadingIdEnc}` | [BankReportHeadingController.java:110](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L110) |
| POST | `/user/bank_heading/search` | [BankReportHeadingController.java:131](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L131) |
| ANY | `/user/bank_heading/delete/{bankReportHeadingIdEnc}` | [BankReportHeadingController.java:160](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L160) |
| ANY | `/user/bank_heading/update_status/{bankReportHeadingIdEnc}` | [BankReportHeadingController.java:181](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L181) |
| POST | `/user/bank_heading/getBankReportHeading` | [BankReportHeadingController.java:203](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BankReportHeadingController.java#L203) |

### BillingHeadController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/billing_head/detail` | [BillingHeadController.java:40](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L40) |
| GET | `/user/billing_head/add` | [BillingHeadController.java:52](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L52) |
| POST | `/user/billing_head/save` | [BillingHeadController.java:64](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L64) |
| GET | `/user/billing_head/add_iframe` | [BillingHeadController.java:91](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L91) |
| GET | `/user/billing_head/edit/{detailCategoryIdEnc}` | [BillingHeadController.java:103](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L103) |
| ANY | `/user/billing_head/search` | [BillingHeadController.java:122](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L122) |
| ANY | `/user/billing_head/delete/{BillingHeadIdEnc}` | [BillingHeadController.java:147](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L147) |
| ANY | `/user/billing_head/update_status/{BillingHeadIdEnc}` | [BillingHeadController.java:168](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L168) |
| POST | `/user/billing_head/getBillingHead` | [BillingHeadController.java:190](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/BillingHeadController.java#L190) |

### CalculatorController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/calculator/view` | [CalculatorController.java:21](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CalculatorController.java#L21) |

### CashReceiptController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/case_receipt/list` | [CashReceiptController.java:108](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L108) |
| GET | `/user/case_receipt/checker_list` | [CashReceiptController.java:129](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L129) |
| GET | `/user/case_receipt/verify_list` | [CashReceiptController.java:151](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L151) |
| GET | `/user/case_receipt/add` | [CashReceiptController.java:172](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L172) |
| POST | `/user/case_receipt/save` | [CashReceiptController.java:195](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L195) |
| POST | `/user/case_receipt/verify/save` | [CashReceiptController.java:325](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L325) |
| GET | `/user/case_receipt/edit/{caseReceiptIdEnc}` | [CashReceiptController.java:386](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L386) |
| GET | `/user/case_receipt/edit_verify/{caseReceiptIdEnc}` | [CashReceiptController.java:428](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L428) |
| GET | `/user/case_receipt/view/{caseReceiptIdEnc}` | [CashReceiptController.java:465](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L465) |
| POST | `/user/case_receipt/dashboard/search` | [CashReceiptController.java:499](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L499) |
| ANY | `/user/case_receipt/delete/{caseReceiptIdEnc}` | [CashReceiptController.java:572](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CashReceiptController.java#L572) |

### ClientController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/clients/add` | [ClientController.java:56](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L56) |
| POST | `/user/clients/save` | [ClientController.java:74](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L74) |
| ANY | `/user/clients/bank_branch_list` | [ClientController.java:101](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L101) |
| ANY | `/user/clients/bank_branch_list_search` | [ClientController.java:116](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L116) |
| GET | `/user/clients/list` | [ClientController.java:152](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L152) |
| POST | `/user/clients/search` | [ClientController.java:171](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L171) |
| GET | `/user/clients/add_iframe` | [ClientController.java:246](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L246) |
| POST | `/user/clients/addClientIframe` | [ClientController.java:263](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L263) |
| GET | `/user/clients/edits/{clientIdEnc}` | [ClientController.java:339](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L339) |
| ANY | `/user/clients/delete/{clientIdEnc}` | [ClientController.java:372](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientController.java#L372) |

### ClientDesignationController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/client_designation/add` | [ClientDesignationController.java:43](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L43) |
| POST | `/user/client_designation/save` | [ClientDesignationController.java:54](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L54) |
| GET | `/user/client_designation/list` | [ClientDesignationController.java:81](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L81) |
| POST | `/user/client_designation/designation_search` | [ClientDesignationController.java:93](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L93) |
| GET | `/user/client_designation/edit/{clientDesignationIdEnc}` | [ClientDesignationController.java:123](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L123) |
| ANY | `/user/client_designation/delete/{clientDesignationIdEnc}` | [ClientDesignationController.java:141](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L141) |
| ANY | `/user/client_designation/update_status/{clientDesignationIdEnc}` | [ClientDesignationController.java:162](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientDesignationController.java#L162) |

### ClientTypeMasterController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/client_type/detail` | [ClientTypeMasterController.java:40](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L40) |
| GET | `/user/client_type/add` | [ClientTypeMasterController.java:52](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L52) |
| POST | `/user/client_type/save` | [ClientTypeMasterController.java:63](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L63) |
| GET | `/user/client_type/add_iframe` | [ClientTypeMasterController.java:90](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L90) |
| GET | `/user/client_type/edit/{clientTypeIdEnc}` | [ClientTypeMasterController.java:129](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L129) |
| ANY | `/user/client_type/search` | [ClientTypeMasterController.java:146](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L146) |
| ANY | `/user/client_type/delete/{clientTypeIdEnc}` | [ClientTypeMasterController.java:171](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L171) |
| ANY | `/user/client_type/update_status/{clientTypeIdEnc}` | [ClientTypeMasterController.java:192](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L192) |
| POST | `/user/client_type/getClientType` | [ClientTypeMasterController.java:214](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ClientTypeMasterController.java#L214) |

### CustomerController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/customer/add` | [CustomerController.java:94](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CustomerController.java#L94) |
| POST | `/user/customer/save` | [CustomerController.java:132](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CustomerController.java#L132) |
| GET | `/user/customer/edit/{leadIdEnc}` | [CustomerController.java:206](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/CustomerController.java#L206) |

### DashboardCountListController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/dashboard/work_order` | [DashboardCountListController.java:50](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L50) |
| ANY | `/user/dashboard/work_order_list` | [DashboardCountListController.java:78](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L78) |
| GET | `/user/dashboard/target` | [DashboardCountListController.java:120](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L120) |
| ANY | `/user/dashboard/target_list` | [DashboardCountListController.java:142](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L142) |
| GET | `/user/dashboard/client_list` | [DashboardCountListController.java:189](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L189) |
| POST | `/user/dashboard/client_search` | [DashboardCountListController.java:211](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DashboardCountListController.java#L211) |

### DesignController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/design/lead_list` | [DesignController.java:78](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L78) |
| GET | `/user/design/add_feedback/{leadIdEnc}` | [DesignController.java:100](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L100) |
| POST | `/user/design/save_call_status` | [DesignController.java:147](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L147) |
| GET | `/user/design/add_client/{leadIdEnc}` | [DesignController.java:190](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L190) |
| POST | `/user/design/save_borrower_detail` | [DesignController.java:223](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L223) |
| GET | `/user/design/view/{clientCustomerIdEnc}` | [DesignController.java:280](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L280) |
| GET | `/user/design/edit_client/{leadIdEnc}/{leadBorrowerIdEnc}` | [DesignController.java:294](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L294) |
| ANY | `/user/design/client_delete/{leadBorrowerId}` | [DesignController.java:328](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L328) |
| GET | `/user/design/add_case/{leadIdEnc}` | [DesignController.java:347](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L347) |
| POST | `/user/design/customer_detail_save` | [DesignController.java:405](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L405) |
| ANY | `/user/design/case_delete/{clientCustomerId}` | [DesignController.java:440](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L440) |
| GET | `/user/design/edit_case/{leadIdEnc}/{clientCustomerIdEnc}` | [DesignController.java:460](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L460) |
| GET | `/user/design/lead_info/{leadIdEnc}` | [DesignController.java:514](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DesignController.java#L514) |

### DetailCategoryController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/detail_category/detail` | [DetailCategoryController.java:40](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L40) |
| GET | `/user/detail_category/add` | [DetailCategoryController.java:53](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L53) |
| POST | `/user/detail_category/save` | [DetailCategoryController.java:65](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L65) |
| GET | `/user/detail_category/add_iframe` | [DetailCategoryController.java:92](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L92) |
| GET | `/user/detail_category/edit/{detailCategoryIdEnc}` | [DetailCategoryController.java:104](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L104) |
| POST | `/user/detail_category/search` | [DetailCategoryController.java:123](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L123) |
| ANY | `/user/detail_category/delete/{DetailCategoryIdEnc}` | [DetailCategoryController.java:147](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L147) |
| ANY | `/user/detail_category/update_status/{DetailCategoryIdEnc}` | [DetailCategoryController.java:168](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L168) |
| POST | `/user/detail_category/getDetailCategory` | [DetailCategoryController.java:190](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DetailCategoryController.java#L190) |

### DispatchController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/dispatch/list` | [DispatchController.java:103](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L103) |
| GET | `/user/dispatch/add` | [DispatchController.java:132](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L132) |
| POST | `/user/dispatch/save` | [DispatchController.java:153](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L153) |
| GET | `/user/dispatch/edit/{dispatchIdEnc}` | [DispatchController.java:282](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L282) |
| GET | `/user/dispatch/view_report/{dispatchIdEnc}` | [DispatchController.java:327](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L327) |
| GET | `/user/dispatch/dispatch_list/{reportNo}` | [DispatchController.java:345](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L345) |
| POST | `/user/dispatch/dashboard/search` | [DispatchController.java:357](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L357) |
| ANY | `/user/dispatch/delete/{dispatchIdEnc}` | [DispatchController.java:436](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DispatchController.java#L436) |

### DivisionController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/client_division/add` | [DivisionController.java:43](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L43) |
| POST | `/user/client_division/save` | [DivisionController.java:53](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L53) |
| GET | `/user/client_division/list` | [DivisionController.java:80](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L80) |
| POST | `/user/client_division/division_search` | [DivisionController.java:92](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L92) |
| GET | `/user/client_division/edit/{divisionIdEnc}` | [DivisionController.java:123](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L123) |
| ANY | `/user/client_division/delete/{divisionIdEnc}` | [DivisionController.java:142](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L142) |
| ANY | `/user/client_division/update_status/{divisionIdEnc}` | [DivisionController.java:166](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/DivisionController.java#L166) |

### EmpTaggingController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/emp_tagging/add` | [EmpTaggingController.java:48](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/EmpTaggingController.java#L48) |
| POST | `/user/emp_tagging/save` | [EmpTaggingController.java:65](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/EmpTaggingController.java#L65) |
| GET | `/user/emp_tagging/list` | [EmpTaggingController.java:92](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/EmpTaggingController.java#L92) |
| POST | `/user/emp_tagging/search` | [EmpTaggingController.java:104](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/EmpTaggingController.java#L104) |
| GET | `/user/emp_tagging/edit/{empTaggingIdEnc}` | [EmpTaggingController.java:135](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/EmpTaggingController.java#L135) |

### ErrorController

| HTTP | Full path(s) | Source |
|---|---|---|
| ANY | `/user/error_msg`<br>`/error_msg` | [ErrorController.java:20](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ErrorController.java#L20) |
| ANY | `/error_400`<br>`/error_400` | [ErrorController.java:27](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ErrorController.java#L27) |
| ANY | `/user/error_404`<br>`/error_404` | [ErrorController.java:33](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ErrorController.java#L33) |
| ANY | `/user/error_500`<br>`/error_500` | [ErrorController.java:40](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ErrorController.java#L40) |
| ANY | `/user/error_403`<br>`/error_403` | [ErrorController.java:48](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ErrorController.java#L48) |

### FaTargetController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/fa_target/detail` | [FaTargetController.java:42](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L42) |
| ANY | `/user/fa_target/search` | [FaTargetController.java:54](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L54) |
| GET | `/user/fa_target/add_target/{empIdEnc}` | [FaTargetController.java:81](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L81) |
| POST | `/user/fa_target/saveData` | [FaTargetController.java:100](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L100) |
| GET | `/user/fa_target/edit/{targetId}` | [FaTargetController.java:127](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L127) |
| GET | `/user/fa_target/fa_target_mis` | [FaTargetController.java:152](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L152) |
| ANY | `/user/fa_target/fa_target_mis_list` | [FaTargetController.java:162](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/FaTargetController.java#L162) |

### InvoiceChangeFAController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/invoice_change_fa/list` | [InvoiceChangeFAController.java:42](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceChangeFAController.java#L42) |
| POST | `/user/invoice_change_fa/search` | [InvoiceChangeFAController.java:59](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceChangeFAController.java#L59) |

### InvoiceController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/invoice/list` | [InvoiceController.java:108](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L108) |
| POST | `/user/invoice/search` | [InvoiceController.java:136](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L136) |
| GET | `/user/invoice/invoice_view/{valuationIdEnc}` | [InvoiceController.java:183](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L183) |
| POST | `/user/invoice/saveInvoice` | [InvoiceController.java:211](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L211) |
| GET | `/user/invoice/update_payment/{invoiceIdEnc}` | [InvoiceController.java:303](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L303) |
| POST | `/user/invoice/save_update_invoice` | [InvoiceController.java:324](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/InvoiceController.java#L324) |

### LeadBorrowerDetailController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET, POST | `/user/lead_borrower/list/{leadIdEnc}` | [LeadBorrowerDetailController.java:43](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadBorrowerDetailController.java#L43) |
| ANY | `/user/lead_borrower/search` | [LeadBorrowerDetailController.java:50](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadBorrowerDetailController.java#L50) |
| GET, POST | `/user/lead_borrower/cases_list/{leadIdEnc}` | [LeadBorrowerDetailController.java:73](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadBorrowerDetailController.java#L73) |
| ANY | `/user/lead_borrower/cases_search` | [LeadBorrowerDetailController.java:80](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadBorrowerDetailController.java#L80) |

### LeadController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/lead_detail/list` | [LeadController.java:102](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L102) |
| POST | `/user/lead_detail/dashboard/search` | [LeadController.java:137](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L137) |
| GET | `/user/lead_detail/view/{leadIdEnc}` | [LeadController.java:224](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L224) |
| ANY | `/user/lead_detail/export_data` | [LeadController.java:255](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L255) |
| GET | `/user/lead_detail/add_lead/{ordererRegistrationIdEnc}` | [LeadController.java:364](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L364) |
| GET | `/user/lead_detail/client_view/{clientIdEnc}` | [LeadController.java:412](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L412) |
| GET | `/user/lead_detail/view_call/{leadIdEnc}` | [LeadController.java:426](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L426) |
| GET | `/user/lead_detail/call_status_iframe/{leadIdEnc}` | [LeadController.java:444](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L444) |
| ANY | `/user/lead_detail/delete/{leadIdEnc}` | [LeadController.java:487](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadController.java#L487) |

### LeadCustomerDetailController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/lead_customer/add/{leadIdEnc}` | [LeadCustomerDetailController.java:55](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadCustomerDetailController.java#L55) |
| POST | `/user/lead_customer/customer_detail_save` | [LeadCustomerDetailController.java:89](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadCustomerDetailController.java#L89) |

### LeadOrderController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/lead_order/list` | [LeadOrderController.java:38](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadOrderController.java#L38) |
| POST | `/user/lead_order/search` | [LeadOrderController.java:53](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadOrderController.java#L53) |

### LeadServiceTypeController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET, POST | `/user/lead_service/list/{leadIdEnc}` | [LeadServiceTypeController.java:58](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L58) |
| ANY | `/user/lead_service/search` | [LeadServiceTypeController.java:68](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L68) |
| ANY | `/user/lead_service/export_data` | [LeadServiceTypeController.java:91](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L91) |
| GET | `/user/lead_service/service_type_add/{leadIdEnc}` | [LeadServiceTypeController.java:135](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L135) |
| POST | `/user/lead_service/save_service_type` | [LeadServiceTypeController.java:157](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L157) |
| ANY | `/user/lead_service/delete/{leadServiceIdEnc}` | [LeadServiceTypeController.java:187](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/LeadServiceTypeController.java#L187) |

### MonthWiseLeadReportController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/lead_status/month_wise` | [MonthWiseLeadReportController.java:66](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L66) |
| GET, POST | `/user/lead_status/status_wise_count` | [MonthWiseLeadReportController.java:93](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L93) |
| ANY | `/user/lead_status/search` | [MonthWiseLeadReportController.java:101](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L101) |
| ANY | `/user/lead_status/export_data` | [MonthWiseLeadReportController.java:134](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L134) |
| GET, POST | `/user/lead_status/lead_status_list/{leadStatus}` | [MonthWiseLeadReportController.java:182](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L182) |
| ANY | `/user/lead_status/search_emp_list` | [MonthWiseLeadReportController.java:208](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L208) |
| ANY | `/user/lead_status/export_data_lead_list` | [MonthWiseLeadReportController.java:246](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L246) |
| GET | `/user/lead_status/month_wise_val_report` | [MonthWiseLeadReportController.java:303](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L303) |
| GET | `/user/lead_status/recovery_list` | [MonthWiseLeadReportController.java:323](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L323) |
| ANY | `/user/lead_status/recovery_search` | [MonthWiseLeadReportController.java:362](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L362) |
| ANY | `/user/lead_status/invoice_search` | [MonthWiseLeadReportController.java:487](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L487) |
| ANY | `/user/lead_status/export_data_recovery_list` | [MonthWiseLeadReportController.java:618](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L618) |
| ANY | `/user/lead_status/export_data_invoice_list` | [MonthWiseLeadReportController.java:805](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L805) |
| GET | `/user/lead_status/report_recovery` | [MonthWiseLeadReportController.java:986](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L986) |
| GET | `/user/lead_status/report_invoice` | [MonthWiseLeadReportController.java:993](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L993) |
| GET | `/user/lead_status/total_amount` | [MonthWiseLeadReportController.java:1000](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1000) |
| ANY | `/user/lead_status/total_amount_list` | [MonthWiseLeadReportController.java:1014](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1014) |
| ANY | `/user/lead_status/export_data_total_amount` | [MonthWiseLeadReportController.java:1045](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1045) |
| GET | `/user/lead_status/recovery_list_period_wise` | [MonthWiseLeadReportController.java:1088](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1088) |
| GET | `/user/lead_status/recovery_list_area_wise` | [MonthWiseLeadReportController.java:1102](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1102) |
| GET | `/user/lead_status/invoice_list_area_wise` | [MonthWiseLeadReportController.java:1146](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1146) |
| GET | `/user/lead_status/recovery_list_client_wise` | [MonthWiseLeadReportController.java:1190](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1190) |
| GET | `/user/lead_status/invoice_list_client_wise` | [MonthWiseLeadReportController.java:1217](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1217) |
| GET | `/user/lead_status/recovery_list_responsibles_wise` | [MonthWiseLeadReportController.java:1244](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1244) |
| GET | `/user/lead_status/invoice_list_responsibles_wise` | [MonthWiseLeadReportController.java:1279](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1279) |
| GET | `/user/lead_status/recovery_list_service_rendered_wise` | [MonthWiseLeadReportController.java:1314](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1314) |
| GET | `/user/lead_status/invoice_list_service_rendered_wise` | [MonthWiseLeadReportController.java:1325](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1325) |
| GET | `/user/lead_status/recovery_list_client_customer_wise` | [MonthWiseLeadReportController.java:1336](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1336) |
| GET | `/user/lead_status/invoice_list_client_customer_wise` | [MonthWiseLeadReportController.java:1355](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1355) |
| GET | `/user/lead_status/invoice_list_division_wise` | [MonthWiseLeadReportController.java:1374](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1374) |
| GET | `/user/lead_status/invoice_list_invoice_head_wise` | [MonthWiseLeadReportController.java:1387](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1387) |
| GET | `/user/lead_status/recovery_list_id_wise` | [MonthWiseLeadReportController.java:1400](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1400) |
| GET | `/user/lead_status/recovery_list_contact_detail_wise` | [MonthWiseLeadReportController.java:1420](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1420) |
| GET | `/user/lead_status/client_wise_lead_mis` | [MonthWiseLeadReportController.java:1429](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1429) |
| ANY | `/user/lead_status/client_wise_lead_list` | [MonthWiseLeadReportController.java:1442](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1442) |
| ANY | `/user/lead_status/export_data_lead_wise` | [MonthWiseLeadReportController.java:1497](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1497) |
| GET | `/user/lead_status/offline_billing` | [MonthWiseLeadReportController.java:1582](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1582) |
| ANY | `/user/lead_status/offline_billing_list` | [MonthWiseLeadReportController.java:1592](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1592) |
| ANY | `/user/lead_status/export_data_offline_invoice` | [MonthWiseLeadReportController.java:1648](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1648) |
| GET | `/user/lead_status/assessor_wise_billing` | [MonthWiseLeadReportController.java:1727](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1727) |
| ANY | `/user/lead_status/assessor_wise_billing_list` | [MonthWiseLeadReportController.java:1738](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1738) |
| ANY | `/user/lead_status/export_data_assessor_wise` | [MonthWiseLeadReportController.java:1772](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1772) |
| GET | `/user/lead_status/cancel_valuation` | [MonthWiseLeadReportController.java:1814](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1814) |
| ANY | `/user/lead_status/cancel_valuation_list` | [MonthWiseLeadReportController.java:1827](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1827) |
| ANY | `/user/lead_status/export_data_cancel_valuation` | [MonthWiseLeadReportController.java:1858](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1858) |
| GET | `/user/lead_status/client_wise_billing` | [MonthWiseLeadReportController.java:1916](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1916) |
| ANY | `/user/lead_status/client_wise_billing_list` | [MonthWiseLeadReportController.java:1929](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1929) |
| ANY | `/user/lead_status/export_data_client_wise` | [MonthWiseLeadReportController.java:1988](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L1988) |
| GET | `/user/lead_status/doer_wise` | [MonthWiseLeadReportController.java:2069](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2069) |
| ANY | `/user/lead_status/doer_wise_list` | [MonthWiseLeadReportController.java:2076](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2076) |
| GET | `/user/lead_status/client_lead_mis/{clientId}` | [MonthWiseLeadReportController.java:2111](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2111) |
| ANY | `/user/lead_status/client_lead_mis_list` | [MonthWiseLeadReportController.java:2127](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2127) |
| GET | `/user/lead_status/doer_wise_valuation/{empId}` | [MonthWiseLeadReportController.java:2180](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2180) |
| ANY | `/user/lead_status/doer_wise_valuation_list` | [MonthWiseLeadReportController.java:2194](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2194) |
| ANY | `/user/lead_status/export_data_doer_wise_list/{empId}` | [MonthWiseLeadReportController.java:2238](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2238) |
| ANY | `/user/lead_status/export_data_doer_wise` | [MonthWiseLeadReportController.java:2289](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2289) |
| GET | `/user/lead_status/service_render_wise_list` | [MonthWiseLeadReportController.java:2337](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2337) |
| ANY | `/user/lead_status/render_wise_list` | [MonthWiseLeadReportController.java:2351](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2351) |
| ANY | `/user/lead_status/export_data_render_wise` | [MonthWiseLeadReportController.java:2411](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/MonthWiseLeadReportController.java#L2411) |

### NewLeadController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/lead/add` | [NewLeadController.java:63](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/NewLeadController.java#L63) |
| ANY | `/user/lead/orderer_list_By_clientId` | [NewLeadController.java:92](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/NewLeadController.java#L92) |
| ANY | `/user/lead/orderer_list_search` | [NewLeadController.java:107](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/NewLeadController.java#L107) |

### OfflineInvoiceController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/offline_invoice/add` | [OfflineInvoiceController.java:58](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L58) |
| POST | `/user/offline_invoice/save` | [OfflineInvoiceController.java:72](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L72) |
| GET | `/user/offline_invoice/list` | [OfflineInvoiceController.java:104](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L104) |
| POST | `/user/offline_invoice/offline_invoice_search` | [OfflineInvoiceController.java:116](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L116) |
| GET | `/user/offline_invoice/update_payment/{offlineInvoiceIdEnc}` | [OfflineInvoiceController.java:165](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L165) |
| POST | `/user/offline_invoice/save_offline_amount` | [OfflineInvoiceController.java:191](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L191) |
| GET | `/user/offline_invoice/view_offline_payment/{offlineinvoiceIdEnc}` | [OfflineInvoiceController.java:230](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L230) |
| GET | `/user/offline_invoice/edits/{offlineInvoiceIdEnc}` | [OfflineInvoiceController.java:255](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OfflineInvoiceController.java#L255) |

### OrdererRegistrationController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/orderer_registration/detail` | [OrdererRegistrationController.java:64](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L64) |
| GET | `/user/orderer_registration/add` | [OrdererRegistrationController.java:77](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L77) |
| POST | `/user/orderer_registration/save` | [OrdererRegistrationController.java:97](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L97) |
| ANY | `/user/orderer_registration/search` | [OrdererRegistrationController.java:137](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L137) |
| GET | `/user/orderer_registration/edit_iframe/{ordererRegistrationIdEnc}` | [OrdererRegistrationController.java:190](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L190) |
| POST | `/user/orderer_registration/edit` | [OrdererRegistrationController.java:216](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L216) |
| ANY | `/user/orderer_registration/delete/{ordererRegistrationIdEnc}` | [OrdererRegistrationController.java:248](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L248) |
| ANY | `/user/orderer_registration/update_status/{ordererRegistrationIdEnc}` | [OrdererRegistrationController.java:268](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L268) |
| GET | `/user/orderer_registration/get_orderer` | [OrdererRegistrationController.java:289](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L289) |
| GET | `/user/orderer_registration/get_orderer_alt_no` | [OrdererRegistrationController.java:346](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/OrdererRegistrationController.java#L346) |

### PublicController

| HTTP | Full path(s) | Source |
|---|---|---|
| ANY | `/user/check_schudler` | [PublicController.java:35](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/PublicController.java#L35) |
| ANY | `/user/download_file/{uploadIdEnc}` | [PublicController.java:46](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/PublicController.java#L46) |

### QuastionMasterController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/question_master/detail` | [QuastionMasterController.java:58](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L58) |
| POST | `/user/question_master/question_master_search` | [QuastionMasterController.java:74](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L74) |
| GET | `/user/question_master/add` | [QuastionMasterController.java:125](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L125) |
| POST | `/user/question_master/save` | [QuastionMasterController.java:142](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L142) |
| GET | `/user/question_master/edit/{questionIdEnc}` | [QuastionMasterController.java:199](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L199) |
| GET | `/user/question_master/question_option` | [QuastionMasterController.java:227](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L227) |
| ANY | `/user/question_master/update_status/{questionIdEnc}` | [QuastionMasterController.java:250](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L250) |
| ANY | `/user/question_master/delete/{questionIdEnc}` | [QuastionMasterController.java:273](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L273) |
| ANY | `/user/question_master/option_delete/{optionId}` | [QuastionMasterController.java:296](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L296) |
| GET | `/user/question_master/view/{questionIdEnc}` | [QuastionMasterController.java:320](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/QuastionMasterController.java#L320) |

### RecoveryReportStatus

| HTTP | Full path(s) | Source |
|---|---|---|
| GET, POST | `/user/pending_recovery/list/{duration}` | [RecoveryReportStatus.java:44](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/RecoveryReportStatus.java#L44) |
| ANY | `/user/pending_recovery/search_list` | [RecoveryReportStatus.java:57](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/RecoveryReportStatus.java#L57) |

### ReportController

| HTTP | Full path(s) | Source |
|---|---|---|
| ANY | `/user/report/home` | [ReportController.java:33](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportController.java#L33) |

### ReportSetupController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/report_setup/detail` | [ReportSetupController.java:69](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L69) |
| POST | `/user/report_setup/search` | [ReportSetupController.java:86](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L86) |
| GET | `/user/report_setup/add` | [ReportSetupController.java:135](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L135) |
| GET | `/user/report_setup/edit/{setupIdEnc}` | [ReportSetupController.java:153](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L153) |
| GET | `/user/report_setup/report_setup_question` | [ReportSetupController.java:183](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L183) |
| POST | `/user/report_setup/save` | [ReportSetupController.java:228](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L228) |
| ANY | `/user/report_setup/update_status/{setupIdEnc}` | [ReportSetupController.java:275](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L275) |
| ANY | `/user/report_setup/delete/{setupIdEnc}` | [ReportSetupController.java:298](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportSetupController.java#L298) |

### ReportValuationStatus

| HTTP | Full path(s) | Source |
|---|---|---|
| GET, POST | `/user/valuation_status/valuation_status_list/{valuationStatus}` | [ReportValuationStatus.java:133](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportValuationStatus.java#L133) |
| ANY | `/user/valuation_status/valuation_list` | [ReportValuationStatus.java:160](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportValuationStatus.java#L160) |
| ANY | `/user/valuation_status/export_data_valuation_list` | [ReportValuationStatus.java:199](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ReportValuationStatus.java#L199) |

### ScrutinyDocumentController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/scrutinyDocument/add` | [ScrutinyDocumentController.java:47](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L47) |
| POST | `/user/scrutinyDocument/save` | [ScrutinyDocumentController.java:61](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L61) |
| GET | `/user/scrutinyDocument/list` | [ScrutinyDocumentController.java:88](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L88) |
| POST | `/user/scrutinyDocument/scrutiny_document_search` | [ScrutinyDocumentController.java:104](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L104) |
| GET | `/user/scrutinyDocument/edit/{scrutinyDocumentIdEnc}` | [ScrutinyDocumentController.java:145](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L145) |
| ANY | `/user/scrutinyDocument/update_status/{scrutinyDocumentIdEnc}` | [ScrutinyDocumentController.java:169](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L169) |
| ANY | `/user/scrutinyDocument/delete/{scrutinyDocumentIdEnc}` | [ScrutinyDocumentController.java:192](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ScrutinyDocumentController.java#L192) |

### ServiceSubTypeController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/serviceSubType/add` | [ServiceSubTypeController.java:44](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L44) |
| POST | `/user/serviceSubType/save` | [ServiceSubTypeController.java:55](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L55) |
| GET | `/user/serviceSubType/list` | [ServiceSubTypeController.java:82](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L82) |
| POST | `/user/serviceSubType/service_sub_type_search` | [ServiceSubTypeController.java:94](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L94) |
| GET | `/user/serviceSubType/edit/{serviceSubTypeIdEnc}` | [ServiceSubTypeController.java:125](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L125) |
| ANY | `/user/serviceSubType/update_status/{serviceSubTypeIdEnc}` | [ServiceSubTypeController.java:144](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L144) |
| ANY | `/user/serviceSubType/delete/{serviceSubTypeIdEnc}` | [ServiceSubTypeController.java:167](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceSubTypeController.java#L167) |

### ServiceTypeController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/serviceType/add` | [ServiceTypeController.java:43](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L43) |
| POST | `/user/serviceType/save` | [ServiceTypeController.java:53](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L53) |
| GET | `/user/serviceType/list` | [ServiceTypeController.java:80](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L80) |
| POST | `/user/serviceType/service_type_search` | [ServiceTypeController.java:92](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L92) |
| GET | `/user/serviceType/edit/{serviceTypeIdEnc}` | [ServiceTypeController.java:123](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L123) |
| ANY | `/user/serviceType/update_status/{serviceTypeIdEnc}` | [ServiceTypeController.java:140](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L140) |
| ANY | `/user/serviceType/delete/{serviceTypeIdEnc}` | [ServiceTypeController.java:162](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L162) |
| GET | `/user/serviceType/service_list` | [ServiceTypeController.java:185](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L185) |
| POST | `/user/serviceType/service_search` | [ServiceTypeController.java:200](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ServiceTypeController.java#L200) |

### SubDivisionController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/client_subDivision/add` | [SubDivisionController.java:44](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L44) |
| POST | `/user/client_subDivision/save` | [SubDivisionController.java:55](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L55) |
| GET | `/user/client_subDivision/list` | [SubDivisionController.java:82](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L82) |
| POST | `/user/client_subDivision/sub_division_search` | [SubDivisionController.java:94](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L94) |
| GET | `/user/client_subDivision/edit/{subDivisionIdEnc}` | [SubDivisionController.java:125](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L125) |
| ANY | `/user/client_subDivision/delete/{subDivisionIdEnc}` | [SubDivisionController.java:143](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L143) |
| ANY | `/user/client_subDivision/update_status/{subDivisionIdEnc}` | [SubDivisionController.java:166](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/SubDivisionController.java#L166) |

### TestController

| HTTP | Full path(s) | Source |
|---|---|---|
| ANY | `/user/upload_data/cash_reciept` | [TestController.java:77](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/TestController.java#L77) |
| ANY | `/user/upload_data/sms_test` | [TestController.java:126](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/TestController.java#L126) |

### UsageOgReportsController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/usageOfReports/add` | [UsageOgReportsController.java:45](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L45) |
| POST | `/user/usageOfReports/save` | [UsageOgReportsController.java:57](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L57) |
| GET | `/user/usageOfReports/list` | [UsageOgReportsController.java:84](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L84) |
| POST | `/user/usageOfReports/usage_of_report_search` | [UsageOgReportsController.java:98](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L98) |
| GET | `/user/usageOfReports/edit/{usageOfReportsIdEnc}` | [UsageOgReportsController.java:139](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L139) |
| ANY | `/user/usageOfReports/update_status/{usageOfReportsIdEnc}` | [UsageOgReportsController.java:160](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L160) |
| ANY | `/user/usageOfReports/delete/{usageOfReportsIdEnc}` | [UsageOgReportsController.java:183](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/UsageOgReportsController.java#L183) |

### ValuationChangeFAController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/change_fa/list` | [ValuationChangeFAController.java:65](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationChangeFAController.java#L65) |
| POST | `/user/change_fa/search` | [ValuationChangeFAController.java:87](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationChangeFAController.java#L87) |
| GET | `/user/change_fa/update/{reportId}` | [ValuationChangeFAController.java:145](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationChangeFAController.java#L145) |
| POST | `/user/change_fa/update_fa` | [ValuationChangeFAController.java:163](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationChangeFAController.java#L163) |

### ValuationController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/valuation/list` | [ValuationController.java:132](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L132) |
| POST | `/user/valuation/search` | [ValuationController.java:164](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L164) |
| GET | `/user/valuation/case/{clientCustomerIdEnc}` | [ValuationController.java:221](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L221) |
| GET | `/user/valuation/detail/{valuationIdEnc}/{detailCategoryId}` | [ValuationController.java:267](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L267) |
| GET | `/user/valuation/multi_answer_list_old` | [ValuationController.java:303](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L303) |
| GET | `/user/valuation/multi_answer_list` | [ValuationController.java:320](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L320) |
| GET | `/user/valuation/multipleData/{valuationId}/{questionId}` | [ValuationController.java:339](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L339) |
| POST | `/user/valuation/saveMultiDetail` | [ValuationController.java:357](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L357) |
| POST | `/user/valuation/saveDetail` | [ValuationController.java:405](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L405) |
| GET | `/user/valuation/billing/{valuationIdEnc}` | [ValuationController.java:552](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L552) |
| POST | `/user/valuation/saveBilling` | [ValuationController.java:584](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L584) |
| GET | `/user/valuation/uploadPhoto/{valuationIdEnc}` | [ValuationController.java:634](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L634) |
| GET | `/user/valuation/imageDisplay` | [ValuationController.java:666](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L666) |
| POST | `/user/valuation/saveUploadPhoto` | [ValuationController.java:687](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L687) |
| GET | `/user/valuation/uploadDoc/{valuationIdEnc}` | [ValuationController.java:748](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L748) |
| POST | `/user/valuation/saveUploadDoc` | [ValuationController.java:777](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L777) |
| ANY | `/user/valuation/deleteUploadPhoto/{id}/{uploadId}` | [ValuationController.java:826](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L826) |
| GET | `/user/valuation/final/{valuationIdEnc}` | [ValuationController.java:845](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L845) |
| POST | `/user/valuation/saveFinal` | [ValuationController.java:879](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L879) |
| GET | `/user/valuation/verification/{valuationIdEnc}` | [ValuationController.java:922](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L922) |
| POST | `/user/valuation/saveVerification` | [ValuationController.java:963](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L963) |
| GET | `/user/valuation/view/{valuationIdEnc}` | [ValuationController.java:1013](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L1013) |
| ANY | `/user/valuation/update_valuation_status` | [ValuationController.java:1034](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L1034) |
| GET | `/user/valuation/reason_valuationStatus_iframe/{valuationId}/{valuationStatus}` | [ValuationController.java:1060](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L1060) |
| POST | `/user/valuation/save_reason` | [ValuationController.java:1078](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationController.java#L1078) |

### ValuationFullViewController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/valuation/case_view/{clientCustomerIdEnc}` | [ValuationFullViewController.java:59](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L59) |
| GET | `/user/valuation/valuation_view/{valuationIdEnc}/{detailCategoryId}` | [ValuationFullViewController.java:104](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L104) |
| GET | `/user/valuation/billing_view/{valuationIdEnc}` | [ValuationFullViewController.java:154](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L154) |
| GET | `/user/valuation/uploadDoc_view/{valuationIdEnc}` | [ValuationFullViewController.java:186](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L186) |
| GET | `/user/valuation/allDoc_view/{valuationIdEnc}` | [ValuationFullViewController.java:216](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L216) |
| GET | `/user/valuation/uploadDoc_view_new/{valuationIdEnc}` | [ValuationFullViewController.java:234](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L234) |
| GET | `/user/valuation/uploadPhoto_view/{valuationIdEnc}` | [ValuationFullViewController.java:263](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L263) |
| GET | `/user/valuation/uploadPhoto_view_new/{valuationIdEnc}` | [ValuationFullViewController.java:294](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L294) |
| GET | `/user/valuation/legalVerfication_view/{valuationIdEnc}` | [ValuationFullViewController.java:325](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L325) |
| GET | `/user/valuation/technicalVerfication_view/{valuationIdEnc}` | [ValuationFullViewController.java:366](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L366) |
| GET | `/user/valuation/socialVerfication_view/{valuationIdEnc}` | [ValuationFullViewController.java:407](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L407) |
| GET | `/user/valuation/generalVerfication_view/{valuationIdEnc}` | [ValuationFullViewController.java:448](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationFullViewController.java#L448) |

### ValuationListAllUserController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/valuation/legal_list` | [ValuationListAllUserController.java:56](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L56) |
| POST | `/user/valuation/leagal_search` | [ValuationListAllUserController.java:88](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L88) |
| GET | `/user/valuation/social_list` | [ValuationListAllUserController.java:149](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L149) |
| POST | `/user/valuation/social_search` | [ValuationListAllUserController.java:180](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L180) |
| GET | `/user/valuation/technical_list` | [ValuationListAllUserController.java:240](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L240) |
| POST | `/user/valuation/technical_search` | [ValuationListAllUserController.java:271](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L271) |
| GET | `/user/valuation/general_list` | [ValuationListAllUserController.java:331](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L331) |
| POST | `/user/valuation/general_search` | [ValuationListAllUserController.java:362](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L362) |
| GET | `/user/valuation/bank_report_list` | [ValuationListAllUserController.java:422](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L422) |
| POST | `/user/valuation/bank_report_search` | [ValuationListAllUserController.java:454](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L454) |
| GET | `/user/valuation/bank_report_approval_list` | [ValuationListAllUserController.java:521](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L521) |
| POST | `/user/valuation/bank_report_approval_search` | [ValuationListAllUserController.java:553](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L553) |
| GET | `/user/valuation/final_revert_back_list` | [ValuationListAllUserController.java:616](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L616) |
| POST | `/user/valuation/final_revert_back_search` | [ValuationListAllUserController.java:637](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationListAllUserController.java#L637) |

### ValuationMultiController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/valuation/multipleDataNew/{valuationId}/{questionId}` | [ValuationMultiController.java:50](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationMultiController.java#L50) |
| POST | `/user/valuation/saveMultiDetailNew` | [ValuationMultiController.java:80](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationMultiController.java#L80) |
| ANY | `/user/valuation/deleteMultiDetailNew/{valuationID}/{questionId}/{indexNo}` | [ValuationMultiController.java:140](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/ValuationMultiController.java#L140) |

### WoChargeCalculationMasterController

| HTTP | Full path(s) | Source |
|---|---|---|
| GET | `/user/wo_calculation/detail` | [WoChargeCalculationMasterController.java:41](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L41) |
| GET | `/user/wo_calculation/add` | [WoChargeCalculationMasterController.java:54](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L54) |
| POST | `/user/wo_calculation/save` | [WoChargeCalculationMasterController.java:67](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L67) |
| GET | `/user/wo_calculation/edit/{woFeesCalculationIdEnc}` | [WoChargeCalculationMasterController.java:132](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L132) |
| ANY | `/user/wo_calculation/search` | [WoChargeCalculationMasterController.java:150](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L150) |
| ANY | `/user/wo_calculation/delete/{woFeesCalculationIdEnc}` | [WoChargeCalculationMasterController.java:175](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WoChargeCalculationMasterController.java#L175) |

### WorkOrderGenerateController

| HTTP | Full path(s) | Source |
|---|---|---|
| ANY | `/user/work_order/view/{leadBorrowerIdEnc}` | [WorkOrderGenerateController.java:98](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WorkOrderGenerateController.java#L98) |
| POST | `/user/work_order/wo_save` | [WorkOrderGenerateController.java:128](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WorkOrderGenerateController.java#L128) |
| GET | `/user/work_order/add_client_list/{leadIdEnc}` | [WorkOrderGenerateController.java:180](../../../omen-lead-new/src/main/java/com/awzpact/lead/controller/WorkOrderGenerateController.java#L180) |

## Every lead_mngt source table

Counts below are from the preserved source inventory and last saved full import report, not a fresh import. A model/import mapping is not an operational API.

| Source table | Source rows | Target model | Imported-source outcomes (accepted / quarantine) |
|---|---:|---|---|
| `account_detail` | 4 | IssuerAccount | 4 / 0 |
| `amount_received` | 1,519 | Receipt | 1,519 / 0 |
| `bank_report_heading` | 478 | No current mapping | Not imported by current pipeline |
| `billing_head` | 6 | ChargeType | 6 / 0 |
| `cash_receipt` | 11,207 | Receipt | 11,207 / 0 |
| `client` | 1,394 | ClientOffice | 1,394 / 0 |
| `client_customer` | 12,877 | Case | 12,875 / 2 |
| `client_designation` | 26 | ContactDesignation | 26 / 0 |
| `client_type` | 7 | ClientType | 7 / 0 |
| `detail_category` | 73 | QuestionCategory | 73 / 0 |
| `dispatch` | 7,545 | No current mapping | Not imported by current pipeline |
| `division` | 9 | LeadDivision | 9 / 0 |
| `employee_tagging` | 3 | EmployeeAssignmentRule | 3 / 0 |
| `employee_target` | 36 | EmployeeTarget | 36 / 0 |
| `follow_up` | 2,021 | FollowUp | 2,021 / 0 |
| `ifsc` | 360 | IfscArea | 360 / 0 |
| `invoice` | 11,927 | Invoice | 11,926 / 1 |
| `invoice_follow_up` | 13 | InvoiceFollowUp | 13 / 0 |
| `lead` | 10,969 | Lead | 10,968 / 1 |
| `lead_borrower` | 12,756 | Borrower | 12,751 / 5 |
| `lead_order` | 12,285 | WorkOrder | 12,285 / 0 |
| `lead_order_history` | 1 | WorkOrderRevision | 1 / 0 |
| `lead_services` | 11,798 | RequestedService | 11,796 / 2 |
| `lead_upload` | 0 | LeadAttachment | 0 / 0 |
| `offline_amount_received` | 991 | Receipt | 991 / 0 |
| `offline_invoice` | 1,396 | Invoice | 1,396 / 0 |
| `orderer_reg` | 2,049 | Contact | 2,048 / 1 |
| `party` | 0 | LeadParty | 0 / 0 |
| `question` | 2,161 | Question | 2,161 / 0 |
| `question_options` | 5,382 | QuestionOption | 5,382 / 0 |
| `report_question` | 4,785 | No current mapping | Not imported by current pipeline |
| `report_question_backup` | 969 | No current mapping | Not imported by current pipeline |
| `report_question_backup_25_08` | 161 | No current mapping | Not imported by current pipeline |
| `report_question_backup_29_10` | 1,441 | No current mapping | Not imported by current pipeline |
| `report_setup` | 209 | No current mapping | Not imported by current pipeline |
| `report_setup_backup` | 40 | No current mapping | Not imported by current pipeline |
| `report_setup_backup_25_08` | 3 | No current mapping | Not imported by current pipeline |
| `revert_back` | 3,343 | Reversion | 3,343 / 0 |
| `scrutiny_document` | 153 | ScrutinyRequirement | 153 / 0 |
| `service_sub_type` | 50 | ServiceSubtype | 50 / 0 |
| `service_type` | 15 | ServiceType | 15 / 0 |
| `sms_log` | 5,169 | No current mapping | Not imported by current pipeline |
| `sub_division` | 12 | LeadSubdivision | 12 / 0 |
| `upload` | 150,636 | Document | 150,636 / 0 |
| `usage_documents` | 0 | DocumentUsage | 0 / 0 |
| `usage_of_reports` | 117 | No current mapping | Not imported by current pipeline |
| `valuation` | 12,651 | Valuation | 12,650 / 1 |
| `valuation_answer` | 1,947,362 | ValuationAnswer | 1,947,183 / 179 |
| `valuation_bank_report` | 11,898 | No current mapping | Not imported by current pipeline |
| `valuation_billing` | 72,852 | ValuationCharge | 72,846 / 6 |
| `valuation_photo` | 58,711 | ValuationAttachment | 58,705 / 6 |
| `valuation_verification` | 12,080 | ValuationVerification | 12,079 / 1 |
| `wo_fees_calculation` | 0 | FeeRule | 0 / 0 |

Coverage: 50 controller files, 410 active method mappings, 53 LEAD source tables, 41 mapped LEAD source tables.

## Target route source

```python
from django.urls import path
from target_core import views
urlpatterns = [
    path('api/session/', views.session), path('api/login/', views.sign_in), path('api/logout/', views.sign_out),
    path('api/offices/', views.offices), path('api/leads/', views.leads), path('api/leads/<uuid:pk>/', views.lead_detail),
    path('api/summary/', views.summary),
]
```
