# Legacy MIS queries

The MIS in omen-lead-new (report/report_home.jsp) offers 24 reports:
month-wise leads, month-wise valuations, total amount, doer-wise, service-rendered-wise,
lead MIS by client, billing MIS by liable field assessor and by client, cancelled
valuations, offline billing, field assessors' financial targets; outstanding (recovery)
by area, liable FA, client customer, client, service rendered and client billing, and
pending recovery; and invoices by area, liable FA, client customer, client, service
rendered and division. All eleven recovery and invoice reports call one query,
InvoiceService.invoiceListReport, with different filter forms.

## Defects found by running the legacy queries against the restored source

Run on 2026-09-27 against omen-full-database-20260916 (the legacy MariaDB).

1. Invoice and recovery totals are multiplied by the number of charge lines.
   invoiceListReport inner-joins valuation_billing, producing 6.00 rows per invoice,
   and sums valuation-level amounts over those rows. Total after tax sums to
   Rs 34,62,92,167 against Rs 5,76,79,313 counted once (6.00x); remaining, the money
   still owed, to Rs 67,73,508 against Rs 11,28,918.
2. Invoice and recovery reports omit 43 of 11,927 invoices, through inner joins to
   valuation_verification and valuation_bank_report.
3. The cancelled valuations report groups by client while selecting individual
   valuations, so MySQL returns one arbitrary valuation per client: 277 rows of 700
   cancelled valuations; 423 never appear.
4. Assessor-wise billing appends its name search after GROUP BY, which is a SQL
   syntax error whenever a name is searched.
5. On report_home.jsp, 3.6 "Outstanding Client Wise Billing MIS" links to the same
   address as 3.5, the service-rendered report.
6. Service rendered joins charge lines too: it counted 71,592 invoices and summed
   Rs 34,80,77,928, against 11,926 invoices and Rs 5,79,79,672.
7. The lead reports have no deleted-lead filter and counted 757 deleted leads.
8. Pending recovery bands (0-60, 60-90, 90-120, over 120 days) use BETWEEN, so an
   invoice exactly 60 or 90 days old falls into two bands.
9. Offline billing selects from offline_invoice alone and groups by l.client_id, a
   table it never joins. It fails every time: "Unknown column 'l.client_id' in
   'GROUP BY'". Rs 14,01,827 owed on offline invoices was never reported.
10. The targets report groups by year and assessor; one assessor holds two targets
    for 2021-22, and both rows join the same invoices, doubling that achievement.

The new MIS reconciles with every legacy query that was correct, and differs from
the others by exactly these defects: manage.py reconcile_mis --settings=config.full_database.

## Extracted queries

Extracted from omen-lead-new by matching method braces. Conditional fragments are shown
as `[if <condition>] <sql>`.

## leadStatusCount  (service/LeadStatusCountService.java)
```
    SELECT l.lead_status
    ,count(l.lead_status) status_count
    FROM lead_mngt .lead l
    WHERE l.lead_id IS NOT NULL
[if searchParamDTO.getDateFrom() != null && !searchParamDTO.getDateFrom().equals("")]
[if searchParamDTO.getDateTo() != null && !searchParamDTO.getDateTo().equals("")]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND :DATE_TO
[else]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND SYSDATE()
    DATE_FROM
    GROUP BY l.lead_status
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(l.lead_status) LIKE :freeText
    status_count
```

## getLeadStatusCount  (service/LeadStatusCountService.java)
```
    SELECT COUNT(*)
    FROM lead_mngt .lead l
    JOIN lead_mngt .orderer_reg ord ON ord.orderer_reg_id = l.orderer_reg_id
    WHERE l.lead_status = :lead_status
[if searchParamDTO.getDateFrom() != null && !searchParamDTO.getDateFrom().equals("")]
[if searchParamDTO.getDateTo() != null && !searchParamDTO.getDateTo().equals("")]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND :DATE_TO
[else]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND SYSDATE()
    DATE_FROM
    GROUP BY l.lead_date, ord.mobile_no , ord.orderer_name, ord.orderer_reg_id, l.lead_no
```

## getLeadStatusList  (service/LeadStatusCountService.java)
```
    SELECT l.lead_no
    ,ord.orderer_name
    ,ord.orderer_reg_id
    FROM lead_mngt .lead l
    LEFT JOIN lead_mngt .orderer_reg ord ON ord.orderer_reg_id = l.orderer_reg_id
    WHERE l.lead_id IS NOT NULL
[if leadStatus != 0]
    AND l.lead_status = :lead_status
[if searchParamDTO.getDateFrom() != null && !searchParamDTO.getDateFrom().equals("")]
[if searchParamDTO.getDateTo() != null && !searchParamDTO.getDateTo().equals("")]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND :DATE_TO
[else]
    AND l.LEAD_DATE BETWEEN :DATE_FROM AND SYSDATE()
    DATE_FROM
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(l.lead_status) LIKE :freeText
[if rs.getObject("orderer_reg_id") != null]
    orderer_reg_id
    orderer_name
    status_count
```

## getDoerWise  (service/LeadStatusCountService.java)
```
    SELECT
    leadCount.totalLeadCounts,
    cccases.totalWoCounts,
    SUM(
    CASE WHEN valuation_status IS NOT NULL THEN 1 ELSE 0
    ) total_valuation,
    SUM(
    CASE WHEN valuation_status = 'Pending' THEN 1 ELSE 0
    ) pending_valuation,
    SUM(
    CASE WHEN valuation_status = 'Submit' THEN 1 ELSE 0
    ) submit_valuation,
    SUM(
    CASE WHEN valuation_status = 'Revert' THEN 1 ELSE 0
    ) revert_valuation,
    SUM(
    CASE WHEN valuation_status = 'Cancel' THEN 1 ELSE 0
    )cancel_valuation,
    SUM(
    CASE WHEN valuation_status = 'Hold' THEN 1 ELSE 0
    )hold_valuation
    FROM
    LEFT JOIN client_customer cc on cc.client_customer_id = v.client_customer_id
    LEFT JOIN lead_order lo on lo.lead_order_id = v.lead_order_id
    LEFT JOIN lead_borrower lb on lo.lead_borrower_id = lb.lead_borrower_id
    LEFT JOIN lead l on l.lead_id = lo.lead_id
    JOIN uam_user .employee e
    LEFT JOIN(
    SELECT
    COUNT(lb.lead_borrower_id) totalWoCounts ,
    FROM lead_mngt .lead_borrower lb
    JOIN lead_mngt .lead lead ON lead.lead_id = lb.lead_id
    WHERE lead.delete_status!= 1
    GROUP by lead.assigned_to
    ) cccases
    cccases.assigned_to = e.emp_id
    LEFT JOIN(
    SELECT
    COUNT(lead.lead_id) totalLeadCounts ,
    FROM lead_mngt .lead lead
    WHERE lead.delete_status!= 1
    GROUP by lead.assigned_to
    ) leadCount
    leadCount.assigned_to = e.emp_id
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    WHERE v.valuation_date BETWEEN :fromDate AND :toDate
    fromDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(v.valuation_status) LIKE :freeText
    GROUP By v.valuation_done_by
    totalWoCounts
    totalLeadCounts
[if rs.getObject("emp_id") != null]
```

## doerMisList  (service/LeadStatusCountService.java)
```
    SELECT
    lo.lead_order_id
    , lo.lead_order_no
    , cc.address case_address
    FROM lead_order lo
    LEFT JOIN client_customer cc ON cc.lead_borrower_id = lo.lead_borrower_id
    LEFT JOIN lead l ON lo.lead_id = l.lead_id
    LEFT JOIN client c ON l.client_id = c.client_id
    LEFT JOIN lead_borrower lb ON cc.lead_borrower_id = lb.lead_borrower_id
    LEFT JOIN service_type st ON st.service_type_id=cc.service_type_id
    JOIN valuation v ON v.client_customer_id=cc.client_customer_id
    LEFT JOIN service_sub_type sst ON sst.service_sub_type_id=cc.service_sub_type_id
    WHERE v.valuation_done_by = :empId
[if searchParamDTO.getValuationStatus() != null && !searchParamDTO.getValuationStatus().trim().equals("") && !sear]
[if searchParamDTO.getValuationStatus().equals("Pending") && !searchParamDTO.getValuationStatus().equals("") && !s]
    AND v.valuation_status='Pending'
[if searchParamDTO.getValuationStatus().equals("Submit") && !searchParamDTO.getValuationStatus().equals("") && !se]
    AND v.valuation_status='Submit'
[if searchParamDTO.getValuationStatus().equals("Revert") && !searchParamDTO.getValuationStatus().equals("") && !se]
    AND v.valuation_status='Revert'
[if searchParamDTO.getValuationStatus().equals("Cancel") && !searchParamDTO.getValuationStatus().equals("") && !se]
    AND v.valuation_status='Cancel'
[if searchParamDTO.getValuationStatus().equals("Hold") && !searchParamDTO.getValuationStatus().equals("") && !sear]
    AND v.valuation_status='Hold'
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND v.valuation_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().toUpperCase().equals("") && !searchParam]
    AND CONCAT(v.valuation_id ) LIKE :freeText
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
    lead_order_id
    lead_order_no
[if rs.getObject("lead_id") != null]
[if rs.getObject("lead_id") != null]
[if rs.getObject("client_customer_id") != null]
[if rs.getObject("borrower_name") != null]
    case_address
[if rs.getObject("service_type_id") != null]
[if rs.getObject("service_sub_type_id") != null]
[if rs.getObject("valuation_id") != null]
```

## getClientWiseBilling  (service/LeadStatusCountService.java)
```
    SELECT
    SUM(i.total_invoice_amount) total_invoice_amount,
    FROM
    lead_order lo
    LEFT JOIN lead l ON lo.lead_id = l.lead_id
    LEFT JOIN client c ON l.client_id = c.client_id
    LEFT JOIN uam_user .state s ON c.state_id = s.state_id
    LEFT JOIN uam_user .district divi ON c.district_id = divi.district_id
    LEFT JOIN uam_user .block b ON c.block_id = b.block_id
    LEFT JOIN valuation v ON v.lead_order_id = lo.lead_order_id
    LEFT JOIN uam_user .employee e ON e.emp_id = v.valuation_done_by
    LEFT JOIN invoice i ON i.valuation_id = v.valuation_id
    Where (c.delete_status = 0 OR c.delete_status is null)
    GROUP BY l.client_id
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND i.invoice_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(c.ifsc) LIKE :freeText
[if searchParamDTO.getClientName() != null && !searchParamDTO.getClientName().trim().equals("") && !searchParamDTO]
    AND c.name LIKE :clientName
[if searchParamDTO.getBranchCode() != null && !searchParamDTO.getBranchCode().trim().equals("") && !searchParamDTO]
    AND c.ifsc LIKE :branchCode
[if searchParamDTO.getBranchName() != null && !searchParamDTO.getBranchName().trim().equals("") && !searchParamDTO]
    AND c.branch = :branchName
[if searchParamDTO.getEmpId() != null && !searchParamDTO.getEmpId().trim().equals("") && !searchParamDTO.getEmpId(]
    AND v.valuation_done_by = :empId
[if searchParamDTO.getDistrictId() != null && !searchParamDTO.getDistrictId().trim().equals("") && !searchParamDTO]
    AND divi.district_id = :districtId
[if searchParamDTO.getCityId() != null && !searchParamDTO.getCityId().trim().equals("") && !searchParamDTO.getCity]
    AND b.block_id = :blockId
    GROUP BY l.client_id
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
    lead_order_id
    lead_order_no
[if rs.getObject("valuation_id") != null]
[if rs.getObject("invoice_id") != null]
[if rs.getObject("lead_id") != null]
[if rs.getObject("ifsc") != null]
[if rs.getObject("district_id") != null]
[if rs.getObject("block_id") != null]
```

## getOfflineBilling  (service/LeadStatusCountService.java)
```
    SELECT
    of.work_order_no,
    FROM
    WHERE of.offline_invoice_id is not null
    GROUP BY l.client_id
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND of.invoice_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(of.work_order_no,of.lead_no) LIKE :freeText
[if searchParamDTO.getClientName() != null && !searchParamDTO.getClientName().trim().equals("") && !searchParamDTO]
    AND of.client_name LIKE :clientName
[if searchParamDTO.getBranchCode() != null && !searchParamDTO.getBranchCode().trim().equals("") && !searchParamDTO]
    AND of.branch_code LIKE :branchCode
[if searchParamDTO.getBranchName() != null && !searchParamDTO.getBranchName().trim().equals("") && !searchParamDTO]
    AND of.branch_name = :branchName
[if searchParamDTO.getLiableFa() != null && !searchParamDTO.getLiableFa().trim().equals("") && !searchParamDTO.get]
    AND of.liable_fa = :liableFa
    searchParamDTO.getEmpId()
[if searchParamDTO.getDoerFa() != null && !searchParamDTO.getDoerFa().trim().equals("") && !searchParamDTO.getDoer]
    AND of.doer_fa = :doerFa
[if searchParamDTO.getClientCustomerName()!= null && !searchParamDTO.getClientCustomerName().trim().equals("") && ]
    AND of.client_customer_name LIKE :clientCustomerName
    GROUP BY l.client_id
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
    work_order_no
    lead_order_no
```

## getCancelValuationList  (service/LeadStatusCountService.java)
```
    SELECT
    lo.lead_order_no,
    FROM `valuation` v
    JOIN lead_order lo on v.lead_order_id = lo.lead_order_id
    JOIN lead l on l.lead_id = lo.lead_id
    JOIN client c on c.client_id = l.client_id
    JOIN uam_user .employee e on e.emp_id = v.valuation_done_by
    where valuation_status='Cancel'
    GROUP BY l.client_id
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(c.ifsc) LIKE :freeText
[if searchParamDTO.getEmpId() != null && !searchParamDTO.getEmpId().trim().equals("") && !searchParamDTO.getEmpId(]
    AND e.emp_id LIKE :empId
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
[if rs.getObject("emp_id") != null]
[if rs.getObject("lead_order_no") != null]
[if rs.getObject("lead_no") != null]
[if rs.getObject("ifsc") != null]
    lead_order_no
    lead_order_id
    lead_order_no
```

## getAssessorWiseBilling  (service/LeadStatusCountService.java)
```
    SELECT
    SUM(i.total_invoice_amount) total_invoice_amount,
    FROM lead_order lo
    LEFT JOIN lead l ON lo.lead_id = l.lead_id
    LEFT JOIN client c ON l.client_id = c.client_id
    LEFT JOIN uam_user .state s ON c.state_id = s.state_id
    LEFT JOIN uam_user .district divi ON c.district_id = divi.district_id
    LEFT JOIN uam_user .block b ON c.block_id = b.block_id
    LEFT JOIN valuation v ON v.lead_order_id = lo.lead_order_id
    LEFT JOIN valuation_bank_report vbr ON v.valuation_id = vbr.valuation_id
    LEFT JOIN uam_user .employee e ON e.emp_id = vbr.liable_fa
    LEFT JOIN invoice i ON i.valuation_id = vbr.valuation_id
    Where v.valuation_id is not null
    AND vbr.liable_fa is not null
    AND e.emp_id is not null
    SELECT
    COUNT(*) totalBankReport,
    SUM(i.total_invoice_amount) AS total_invoice_amount
    FROM
    LEFT JOIN invoice i on i.valuation_id = vbr.valuation_id
    LEFT JOIN uam_user .employee e ON e.emp_id = vbr.liable_fa
    Where vbr.liable_fa IS NOT NULL
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND i.invoice_date BETWEEN :fromDate AND :toDate
    fromDate
    GROUP BY v.liable_fa
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(e.name) LIKE :freeText
    GROUP BY vbr.liable_fa
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
    lead_order_id
    lead_order_no
[if rs.getObject("emp_id") != null]
```

## getClientWiseLead  (service/LeadStatusCountService.java)
```
    SELECT c.name client_name,
    Sum(CASE WHEN lead_status IS NOT NULL THEN 1 ELSE 0 END) total_lead,
    Sum(CASE WHEN lead_status=1 THEN 1 ELSE 0 END) pending_lead,
    Sum(CASE WHEN lead_status=2 THEN 1 ELSE 0 END) inprogress_lead,
    Sum(CASE WHEN lead_status=3 THEN 1 ELSE 0 END) rejected_lead,
    Sum(CASE WHEN lead_status=4 THEN 1 ELSE 0 END) closed_lead
    FROM lead_mngt .lead l
    LEFT JOIN client c ON c.client_id = l.client_id
    LEFT JOIN uam_user .district d ON d.district_id = c.district_id
    LEFT JOIN uam_user .block b ON b.block_id = c.block_id
    where l.client_id is not null
    GROUP BY l.client_id
    GROUP BY v.liable_fa
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND l.lead_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(c.ifsc) LIKE :freeText
[if searchParamDTO.getClientName() != null && !searchParamDTO.getClientName().trim().equals("") && !searchParamDTO]
    AND c.name LIKE :clientName
[if searchParamDTO.getBranchCode() != null && !searchParamDTO.getBranchCode().trim().equals("") && !searchParamDTO]
    AND c.ifsc LIKE :branchCode
[if searchParamDTO.getBranchName() != null && !searchParamDTO.getBranchName().trim().equals("") && !searchParamDTO]
    AND c.branch = :branchName
[if searchParamDTO.getDistrictId() != null && !searchParamDTO.getDistrictId().trim().equals("") && !searchParamDTO]
    AND d.district_id = :districtId
[if searchParamDTO.getCityId() != null && !searchParamDTO.getCityId().trim().equals("") && !searchParamDTO.getCity]
    AND b.block_id = :blockId
    GROUP BY l.client_id
    ORDER BY
[if rs.getObject("client_id") != null]
[if rs.getObject("district_id") != null]
[if rs.getObject("block_id") != null]
    lead_order_id
    lead_order_no
```

## leadMisList  (service/LeadStatusCountService.java)
```
    SELECT
    ord.orderer_reg_id,
    ord.orderer_name,
    FROM lead_mngt .lead l
    LEFT JOIN client c ON c.client_id = l.client_id
    LEFT JOIN orderer_reg ord ON ord.orderer_reg_id = l.orderer_reg_id
    LEFT JOIN uam_user .district d ON d.district_id = c.district_id
    LEFT JOIN uam_user .block b ON b.block_id = c.block_id
    WHERE c.client_id = :clientId
[if searchParamDTO.getLeadStatus() != null && !searchParamDTO.getLeadStatus().trim().equals("") && !searchParamDTO]
[if searchParamDTO.getLeadStatus().equals("PendingLead") && !searchParamDTO.getLeadStatus().equals("") && !searchP]
    AND l.lead_status=1
[if searchParamDTO.getLeadStatus().equals("InprogressLead") && !searchParamDTO.getLeadStatus().equals("") && !sear]
    AND l.lead_status=2
[if searchParamDTO.getLeadStatus().equals("CansilLead") && !searchParamDTO.getLeadStatus().equals("") && !searchPa]
    AND l.lead_status=3
[if searchParamDTO.getLeadStatus().equals("CloseLead") && !searchParamDTO.getLeadStatus().equals("") && !searchPar]
    AND l.lead_status=4
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND l.lead_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().toUpperCase().equals("") && !searchParam]
    AND CONCAT(v.valuation_id ) LIKE :freeText
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
[if rs.getObject("client_id") != null]
[if rs.getObject("orderer_reg_id") != null]
    orderer_reg_id
    orderer_name
```

## getRenderWiseList  (service/LeadStatusCountService.java)
```
    SELECT
    SUM(i.total_invoice_amount) total_invoice_amount,
    COUNT(i.invoice_id) total_invoice_count
    FROM lead_order lo
    LEFT JOIN client_customer cc ON cc.lead_borrower_id = lo.lead_borrower_id
    LEFT JOIN uam_user .state s ON cc.state_id = s.state_id
    LEFT JOIN uam_user .district divi ON cc.district_id = divi.district_id
    LEFT JOIN uam_user .block b ON cc.block_id = b.block_id
    LEFT JOIN client_customer cc ON cc.lead_borrower_id = lo.lead_borrower_id
    LEFT JOIN lead l ON lo.lead_id = l.lead_id
    LEFT JOIN orderer_reg ord ON l.orderer_reg_id = ord.orderer_reg_id
    LEFT JOIN division d ON ord.division_id = d.division_id
    LEFT JOIN uam_user .employee e ON e.emp_id = l.assigned_to
    LEFT JOIN client c ON l.client_id = c.client_id
    LEFT JOIN uam_user .bank_branch bb ON bb.branch_id = c.bank_branch_id
    LEFT JOIN uam_user .district dis ON c.district_id = dis.district_id
    LEFT JOIN lead_mngt .client_type ct ON ct.client_type_id = l.client_type_id
    LEFT JOIN lead_borrower lb ON cc.lead_borrower_id = lb.lead_borrower_id
    LEFT JOIN service_type st ON st.service_type_id=cc.service_type_id
    JOIN valuation v ON v.client_customer_id=cc.client_customer_id
    JOIN valuation_billing vb ON vb.valuation_id=v.valuation_id
    JOIN invoice i ON i.valuation_id =v.valuation_id
    LEFT JOIN upload u ON i.upload_id =u.upload_id
    JOIN valuation_verification vv ON vv.valuation_id = v.valuation_id
    JOIN valuation_bank_report br ON br.valuation_id = v.valuation_id
    LEFT JOIN service_sub_type sst ON sst.service_sub_type_id=cc.service_sub_type_id
    Where (c.delete_status = 0 OR c.delete_status is null)
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND i.invoice_date BETWEEN :fromDate AND :toDate
    fromDate
[if searchParamDTO.getFreeText() != null && !searchParamDTO.getFreeText().trim().equals("") && !searchParamDTO.get]
    AND CONCAT(c.ifsc) LIKE :freeText
[if searchParamDTO.getClientName() != null && !searchParamDTO.getClientName().trim().equals("") && !searchParamDTO]
    AND c.name LIKE :clientName
[if searchParamDTO.getBranchCode() != null && !searchParamDTO.getBranchCode().trim().equals("") && !searchParamDTO]
    AND c.ifsc LIKE :branchCode
[if searchParamDTO.getBranchName() != null && !searchParamDTO.getBranchName().trim().equals("") && !searchParamDTO]
    AND c.branch = :branchName
[if searchParamDTO.getDistrictId() != null && !searchParamDTO.getDistrictId().trim().equals("") && !searchParamDTO]
    AND divi.district_id = :districtId
[if searchParamDTO.getCityId() != null && !searchParamDTO.getCityId().trim().equals("") && !searchParamDTO.getCity]
    AND b.block_id = :blockId
[if searchParamDTO.getServiceTypeName() != null && !searchParamDTO.getServiceTypeName().trim().equals("") && !sear]
    AND st.service_type_id = :serviceTypeName
    GROUP BY l.client_id
[if searchParamDTO.getOrderByBean() != null]
    ORDER BY
    lead_order_id
    lead_order_no
[if rs.getObject("valuation_id") != null]
[if rs.getObject("invoice_id") != null]
    total_invoice_count
[if rs.getObject("lead_id") != null]
[if rs.getObject("client_customer_id") != null]
[if rs.getObject("service_type_id") != null]
[if rs.getObject("ifsc") != null]
[if rs.getObject("district_id") != null]
[if rs.getObject("block_id") != null]
```

## invoiceListReport  (service/InvoiceService.java)
```
    SELECT
    lo.lead_order_id
    , lo.lead_order_no
    , cc.address case_address
    , SUM(v.total_amount_after_tax) totalAmountAfterTaxExcel
    , SUM(v.remaining_amount) totalRemainingAmountExcel
    , SUM(v.advance_collected) totalAdvanceAmountExcel
    , DATE_FORMAT(i.invoice_date, \ )
    , ord.orderer_reg_id
    , DATEDIFF(CURDATE(), i.invoice_date) pendingDays
    FROM lead_order lo
    LEFT JOIN client_customer cc ON cc.lead_borrower_id = lo.lead_borrower_id
    LEFT JOIN uam_user .state s ON cc.state_id = s.state_id
    LEFT JOIN uam_user .district divi ON cc.district_id = divi.district_id
    LEFT JOIN uam_user .block b ON cc.block_id = b.block_id
    LEFT JOIN client_customer cc ON cc.lead_borrower_id = lo.lead_borrower_id
    LEFT JOIN lead l ON lo.lead_id = l.lead_id
    LEFT JOIN orderer_reg ord ON l.orderer_reg_id = ord.orderer_reg_id
    LEFT JOIN division d ON ord.division_id = d.division_id
    LEFT JOIN uam_user .employee e ON e.emp_id = l.assigned_to
    LEFT JOIN client c ON l.client_id = c.client_id
    LEFT JOIN uam_user .bank_branch bb ON bb.branch_id = c.bank_branch_id
    LEFT JOIN uam_user .district dis ON c.district_id = dis.district_id
    LEFT JOIN lead_mngt .client_type ct ON ct.client_type_id = l.client_type_id
    LEFT JOIN lead_borrower lb ON cc.lead_borrower_id = lb.lead_borrower_id
    LEFT JOIN service_type st ON st.service_type_id=cc.service_type_id
    JOIN valuation v ON v.client_customer_id=cc.client_customer_id
    JOIN valuation_billing vb ON vb.valuation_id=v.valuation_id
    JOIN invoice i ON i.valuation_id =v.valuation_id
    LEFT JOIN upload u ON i.upload_id =u.upload_id
    JOIN valuation_verification vv ON vv.valuation_id = v.valuation_id
    JOIN valuation_bank_report br ON br.valuation_id = v.valuation_id
    LEFT JOIN service_sub_type sst ON sst.service_sub_type_id=cc.service_sub_type_id
    Where lo.lead_order_id IS NOT NULL
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    AND i.invoice_date BETWEEN :fromDate AND :toDate
    fromDate
    fromDate
[if searchParamDTO.getClientTypeId() != null && !searchParamDTO.getClientTypeId().trim().equals("") && !searchPara]
    AND c.client_type_id LIKE :client_type_id
[if searchParamDTO.getClientId() != null && !searchParamDTO.getClientId().trim().equals("") && !searchParamDTO.get]
    AND c.client_id LIKE :client_id
    AND CONCAT(lo.lead_order_no,l.lead_no,c.name,st.name,sst.name) LIKE :freeText
    AND l.lead_no LIKE :leadNo
    AND lo.lead_order_no LIKE :leadOrderNo
    leadOrderNo % %
[if searchParamDTO.getClientCustomerName() != null && !searchParamDTO.getClientCustomerName().trim().equals("") &&]
    AND lb.name_of_borrower LIKE :clientCustomerName
[if searchParamDTO.getServiceTypeName() != null && !searchParamDTO.getServiceTypeName().trim().equals("") && !sear]
    AND st.service_type_id LIKE :serviceTypeName
[if searchParamDTO.getReportNo() != null && !searchParamDTO.getReportNo().trim().equals("") && !searchParamDTO.get]
    AND br.report_no LIKE :reportNo
[if searchParamDTO.getStateId() != null && !searchParamDTO.getStateId().trim().equals("") && !searchParamDTO.getSt]
    AND s.state_id LIKE :stateId
[if searchParamDTO.getDistrictId() != null && !searchParamDTO.getDistrictId().trim().equals("") && !searchParamDTO]
    AND divi.district_id LIKE :districtId
[if searchParamDTO.getCityId() != null && !searchParamDTO.getCityId().trim().equals("") && !searchParamDTO.getCity]
    AND b.block_id LIKE :blockId
[if searchParamDTO.getOrdererRegistrationId() != null && !searchParamDTO.getOrdererRegistrationId().trim().equals(]
    AND ord.orderer_reg_id LIKE :ordererRegistrationId
    ordererRegistrationId % %
[if searchParamDTO.getLeadBorrowerId() != null && !searchParamDTO.getLeadBorrowerId().trim().equals("") && !search]
    AND lb.lead_borrower_id LIKE :leadBorrowerId
[if searchParamDTO.getEmpId() != null && !searchParamDTO.getEmpId().trim().equals("") && !searchParamDTO.getEmpId(]
    AND e.emp_id LIKE :empId
[if searchParamDTO.getPinCode() != null && !searchParamDTO.getPinCode().trim().equals("") && !searchParamDTO.getPi]
    AND cc.pin_code LIKE :pinCode
[if searchParamDTO.getMobileNo() != null && !searchParamDTO.getMobileNo().trim().equals("") && !searchParamDTO.get]
    AND lb.contact_no LIKE :mobileNo
[if searchParamDTO.getEmailId() != null && !searchParamDTO.getEmailId().trim().equals("") && !searchParamDTO.getEm]
    AND lb.email_id LIKE :emailId
[if searchParamDTO.getDivisionId() != null && !searchParamDTO.getDivisionId().trim().equals("") && !searchParamDTO]
    AND d.division_id LIKE :divisionId
    AND vb.billing_head_id LIKE :invoiceHeadId
    AND v.valuation_date LIKE :valuationDate
    AND br.report_date LIKE :reportDate
    AND i.invoice_date LIKE :invoiceDate
    query for mis
    lead_order_id
    lead_order_no
[if rs.getObject("lead_id") != null]
[if rs.getObject("orderer_reg_id") != null]
    orderer_reg_id
[if rs.getObject("emp_id") != null]
[if rs.getObject("client_id") != null]
[if rs.getObject("bank_branch_id") != null]
[if rs.getObject("client_customer_id") != null]
[if rs.getObject("district_id") != null]
[if rs.getObject("block_id") != null]
[if rs.getObject("state_id") != null]
    case_address
[if rs.getObject("name_of_borrower") != null]
[if rs.getObject("service_type_id") != null]
[if rs.getObject("service_sub_type_id") != null]
[if rs.getObject("valuation_id") != null]
[if rs.getObject("invoice_id") != null]
[if rs.getObject("report_id") != null]
```

## totalAmountListReport  (service/InvoiceService.java)
```
    SELECT
    SUM(i.total_invoice_amount) totalInvoiceSumamount
    , SUM(i.total_pay_amount) totalPaySumamount
    , SUM(i.total_remaining_amount) totalRemainingSumAmount
    FROM invoice i
[if searchParamDTO.getDateTo() != null && searchParamDTO.getDateTo() != null]
    WHERE invoice_date BETWEEN :fromDate AND :toDate
    fromDate
    fromDate
    totalInvoiceSumamount
    totalPaySumamount
    totalRemainingSumAmount
```
