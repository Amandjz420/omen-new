# Legacy workflow and forms: working notes

Source: omen-lead-new (JSP views, Spring controllers) and the legacy uam_user menu.
Working notes for the form-by-form study; the finished write-up follows.

## The live menu (uam_user.uam_module / submodule, project LEAD, active)

- Lead Manager: Lead List /lead_detail/list (Add lead -> /user/customer/add);
  Orderer List /orderer_registration/detail; Work Order List /lead_order/list
- Service Manager: Service List /valuation/list; Change Liable FA /change_fa/list;
  Bank Report Generation /valuation/bank_report_list
- CIF Verification: Legal /valuation/legal_list; Social; Technical; General;
  Final Approval /valuation/bank_report_approval_list; Final Revert Back
- Invoice Manager: Invoice Generation /invoice/list; Recovery Follow-up
  /amount_received/list; Bad Debts /amount_received/bad_bebt_list; Offline Invoice
- Dispatch Module /dispatch/list
- Pay in Receipt: maker /case_receipt/list; checker /case_receipt/checker_list;
  verify /case_receipt/verify_list
- MIS Reports /report/home
- Masters: service type, asset type / service subtype, employee FY target,
  usage of reports, scrutiny documents, billing heads; client type, client
  division, client designation, client master; detail category, question bank,
  bank report heading, report setup

## 1. Add lead (design/add_lead.jsp; CustomerController /user/customer/add, /save)

Live form. master/lead_form.jsp (LeadController) is an older version, not in any
menu; add_lead's script still fills its addressee/dispatch/payment fields.

LEAD GIVER INFORMATION
- Mode * (select)
- Lead Giver Mobile No. * (10 digits). On 10 digits: GET /user/orderer_registration/get_orderer
  - known orderer: read-only, filled: Lead Giver Name, Designation, City, Client
    Type, Client Name, Client Branch, Division, Address, GST No.
  - new orderer: Client Type * -> Client Name * (filtered by type; getClientListNew)
    -> IFSC Code * (findClientByIFSC fills the client) -> Lead Giver Name * ->
    Division * -> Sub Division * (by division) -> Lead Giver Designation *;
    read-only from the client: Branch, Address, State, District, Block.
    Add client type / add client open in an iframe from the form.
- Alternate Contact Number (exclude 0 prefix)
LEAD INFORMATION
- Services table, rows: Type of service -> Type of sub service (loaded for the
  service) -> No. of Case/Property *; add/delete rows. Total cases summed.
- No Of Clients
OTHER DETAILS (internal)
- Lead Received By * (employee); Lead Assigned To * (employee)
Save -> redirect to /lead_detail/list.

Older master/lead_form also had: Source *, Reference, Lead Received On *, Report
Expected by *, Number of Parties *, Addressee (designation, name, address,
city) *, Dispatch (designation, name, address, city) *, Payment by (name,
contact) *.

## 2. Lead list (master/lead_list.jsp; rows built by resources/js/master/lead_list.js)

Columns: No, Lead Id (-> design/lead_info, read-only view of the add-lead
sections), Client (short name; branch [IFSC] -> client view), Lead Giver (name
[mobile]), Lead Date, Services and Sub Services counts (-> /lead_service/list),
Parties "recorded/expected" (-> /lead_borrower/list), Cases "recorded/expected"
(-> /lead_borrower/cases_list), Status, Follow Up Action (call status iframe),
Action: view; edit (/customer/edit) and delete hidden once Closed (4); Generate
Work Order (/work_order/add_client_list/{lead}).

Lead statuses (LeadStatusEnum): 1 New Lead, 2 Lead in Process, 3 Cancel Lead,
4 Closed Lead; the same four as the new app. lead_list.js also tests 5-7, 15, 16:
dead branches. Legacy data: 220 in process, 9,992 closed, 757 cancelled (all
deleted).

Progress against the numbers declared at intake (parties x/y, cases x/y) is how
the old list showed what intake still needed.

## 3. The live intake sequence (DesignController, /user/design)

After add-lead, the lead is completed through a sequence of pages, each saving
and moving on or repeating:
  add_feedback/{lead} --save_call_status--> add_client/{lead} (repeat per
  borrower) ; add_case/{lead} (repeat per case) ; then Generate Work Order.
master/lead_borrower, master/lead_parties, services/customer_party_cases_form_
and master/customer_form are older versions: no controller shows them.

### 3a. Follow up for lead (design/add_feedback.jsp)
- Follow Up Status * (select; onchange getcall...)
- Date to be notified *; Hour *; Minute *
- Remark * ("Please specify the remark if any")
- List of follow ups below.

### 3b. Client's customer = borrower (design/add_client.jsp; save_borrower_detail)
- Name of Client's Customer *; Email Id; Contact No *; CC GST No.
- No. of cases *
- Paid By * (radio): By Client / By Client Customer
- Payment by mode (radio): By Circular / By Fixed
- Client Name * (read-only, filled); Contact Number * (read-only, filled)
- Client Payment Responsible Name *; Client Payment Responsible No *
- Pay by Date *; Work Order Amount *
- Payment By Mode * (radio): By Bank / By Cash / By Any Other
(conditional display to confirm in the page script)

### 3c. Case (design/add_case.jsp; customer_detail_save)
- Client's Customer Name * (select, the lead's borrowers)
- Service Type * -> Service Sub Type * (onchange getUsageOfReportsList)
- Usage of Report * (multi; by subtype; onchange getScrutinyDocumentList)
- Scrutiny Documents * (multi; by usage of report)
- Expect date of report *; Output Amount *; Remark
- Contact Person Name; Contact Person No
- Property Address *; State * -> District * (by state) -> City * (by district); Pin *

Borrower form conditions (add_client.jsp script): Paid By = By Client shows the
client's name and number (filled); By Client Customer hides them. Payment By Mode
= By Circular hides Work Order Amount (the fee follows the bank's circular); By
Fixed shows it. Then the customer's payment method: bank, cash or other.

## GAP: the new intake records far less than the legacy intake did

The database models hold every legacy field (imported), but the intake API
(apps/leads/services.py) accepts only:
- Lead: office, contact, assigned_employee, received_date.
  Missing: Mode *, Lead Received By *, alternate contact number, and the lead
  giver mobile-number lookup that fills the lead giver and client.
- Borrower: name, agreed_fee, property_count.
  Missing: contact number *, email, GST no., Paid By *, circular/fixed *,
  payment method, payer name and mobile, Pay by Date *, payment responsible
  name * and number *.
- Case: borrower, service, subtype, asset_address, asset_district, asset_state
  (free text). Missing: Usage of Report *, Scrutiny Documents *, Expected date of
  report *, Output Amount *, remark, contact person name and number, Pin *,
  city; state/district/city were cascading selects.
- Follow-up: outcome, remark. Missing: date to be notified *, hour, minute.

## 4. Work order (design/add_client_list.jsp; WorkOrderGenerateController /wo_save)

add_client_list lists the lead's borrowers: Name of Customer/Owner, Email, No. of
Cases, Entered No. of Cases, Paid By, Paid By Mode, Payment Mode; per row view or
download its work order. Generating one (per borrower) numbers it, renders the
PDF letter, attaches it, and sets the lead Closed.
Legacy defects, not carried over (the new work orders close the lead after the
last borrower and refuse a second order): the lead closed after the first
borrower's order (the all-parties check has an empty body); nothing prevented a
second order for the same borrower (the existing order is looked up, unused).

## 5. Valuation onward

valuation/valuation_detail.jsp renders each question category from the question
bank with each question's options; no fixed fields. Dispatch at/by, liable
assessor and the other final fields are taken at submission. Verification, bank
report, approval, invoicing, receipts, dispatch and MIS were traced from the
legacy code when they were built (see their commits).
