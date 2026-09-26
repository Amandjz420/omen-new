# Full source-to-target disposition register

Design candidates only; no source records have been deleted or consolidated. Every source table has one entry. Target names are proposed logical entities, not final migrations. UAT entries describe a separate environment.

## ebioserver

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| attendancestates | 6 | attendance.device_state | domain_candidate |
| devicecommands | 34 | attendance.device_command | domain_candidate |
| deviceerrormessages | 0 | attendance.device_error | domain_candidate |
| devicelogs | 0 | attendance.device_event | domain_candidate |
| devicelogs_01_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_02_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_03_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_04_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2019 | 943 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2020 | 664 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2021 | 712 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2022 | 516 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2023 | 597 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2024 | 500 | attendance.device_event | consolidate_candidate |
| devicelogs_10_2025 | 383 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2019 | 4,971 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2020 | 593 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2021 | 569 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2022 | 584 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2023 | 535 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2024 | 487 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2025 | 366 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2019 | 910 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2020 | 638 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2021 | 601 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2022 | 502 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2023 | 556 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2024 | 425 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2025 | 393 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2020 | 1,014 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2021 | 608 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2022 | 541 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2023 | 471 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2024 | 649 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2025 | 435 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2026 | 401 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2020 | 958 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2021 | 598 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2022 | 565 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2023 | 448 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2024 | 538 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2025 | 393 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2026 | 344 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2020 | 791 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2021 | 552 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2022 | 599 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2023 | 468 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2024 | 531 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2025 | 402 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2026 | 366 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2020 | 2 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2021 | 183 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2022 | 509 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2023 | 507 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2024 | 449 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2025 | 364 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2026 | 94 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2020 | 40 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2022 | 612 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2023 | 564 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2024 | 588 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2025 | 313 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2020 | 30 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2021 | 543 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2022 | 632 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2023 | 553 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2024 | 533 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2025 | 334 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2020 | 614 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2021 | 756 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2022 | 615 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2023 | 676 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2024 | 528 | attendance.device_event | consolidate_candidate |
| devicelogs_7_2025 | 440 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2019 | 166 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2020 | 540 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2021 | 672 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2022 | 563 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2023 | 574 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2024 | 476 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2025 | 355 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2019 | 732 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2020 | 663 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2021 | 677 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2022 | 581 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2023 | 563 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2024 | 477 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2025 | 370 | attendance.device_event | consolidate_candidate |
| deviceoperationlogtypes | 0 | Review required | review |
| devices | 4 | attendance.device | domain_candidate |
| devicesstatus | 0 | Review required | review |
| employees | 54 | attendance.device_person | domain_candidate |
| employees_110522 | 50 | Review required | archive_candidate |
| employeesbio | 145 | attendance.biometric_reference | domain_candidate |
| fetch_attendance_log | 0 | Review required | review |
| mastersettings | 1 | Review required | review |
| parallelattlogexportdetails | 0 | Review required | review |
| paralleldatabasedetails | 0 | Review required | review |
| permissions | 8 | Review required | review |
| transactionsdump | 0 | Review required | review |
| userpermissions | 45 | Review required | review |
| users | 2 | Review required | review |
| usersdump | 0 | Review required | review |
| verificationmode | 23 | attendance.verification_mode | domain_candidate |

## lead_mngt

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| account_detail | 4 | billing.issuer_account | domain_candidate |
| amount_received | 1,519 | billing.legacy_receipt | domain_candidate |
| bank_report_heading | 478 | reports.heading | domain_candidate |
| billing_head | 6 | billing.charge_type | domain_candidate |
| cash_receipt | 11,207 | billing.receipt | domain_candidate |
| client | 1,394 | crm.client_office | domain_candidate |
| client_customer | 12,877 | leads.case | domain_candidate |
| client_designation | 26 | crm.contact_designation | domain_candidate |
| client_type | 7 | crm.client_type | domain_candidate |
| detail_category | 73 | valuations.question_category | domain_candidate |
| dispatch | 7,545 | reports.dispatch | domain_candidate |
| division | 9 | leads.division | domain_candidate |
| employee_tagging | 3 | leads.employee_assignment | domain_candidate |
| employee_target | 36 | leads.employee_target | domain_candidate |
| follow_up | 2,021 | leads.follow_up | domain_candidate |
| ifsc | 360 | reference.legacy_ifsc | domain_candidate |
| invoice | 11,927 | billing.invoice | domain_candidate |
| invoice_follow_up | 13 | billing.invoice_follow_up | domain_candidate |
| lead | 10,969 | leads.lead | domain_candidate |
| lead_borrower | 12,756 | leads.borrower | domain_candidate |
| lead_order | 12,285 | workorders.work_order | domain_candidate |
| lead_order_history | 1 | workorders.work_order_revision | domain_candidate |
| lead_services | 11,798 | leads.requested_service | domain_candidate |
| lead_upload | 0 | documents.lead_attachment | domain_candidate |
| offline_amount_received | 991 | billing.offline_receipt | domain_candidate |
| offline_invoice | 1,396 | billing.offline_invoice | domain_candidate |
| orderer_reg | 2,049 | crm.contact | domain_candidate |
| party | 0 | leads.party_type | domain_candidate |
| question | 2,161 | valuations.question | domain_candidate |
| question_options | 5,382 | valuations.question_option | domain_candidate |
| report_question | 4,785 | reports.template_question | domain_candidate |
| report_question_backup | 969 | Review required | archive_candidate |
| report_question_backup_25_08 | 161 | Review required | archive_candidate |
| report_question_backup_29_10 | 1,441 | Review required | archive_candidate |
| report_setup | 209 | reports.template_version | domain_candidate |
| report_setup_backup | 40 | Review required | archive_candidate |
| report_setup_backup_25_08 | 3 | Review required | archive_candidate |
| revert_back | 3,343 | valuations.reversion | domain_candidate |
| scrutiny_document | 153 | documents.scrutiny_requirement | domain_candidate |
| service_sub_type | 50 | services.service_subtype | domain_candidate |
| service_type | 15 | services.service_type | domain_candidate |
| sms_log | 5,169 | messaging.delivery_log | domain_candidate |
| sub_division | 12 | leads.subdivision | domain_candidate |
| upload | 150,636 | documents.document | domain_candidate |
| usage_documents | 0 | documents.document_usage | domain_candidate |
| usage_of_reports | 117 | reports.report_usage | domain_candidate |
| valuation | 12,651 | valuations.valuation | domain_candidate |
| valuation_answer | 1,947,362 | valuations.answer | domain_candidate |
| valuation_bank_report | 11,898 | reports.bank_report | domain_candidate |
| valuation_billing | 72,852 | billing.valuation_charge | domain_candidate |
| valuation_photo | 58,711 | documents.valuation_attachment | domain_candidate |
| valuation_verification | 12,080 | valuations.review | domain_candidate |
| wo_fees_calculation | 0 | workorders.fee_rule | domain_candidate |

## smldb

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| email_log | 0 | messaging.delivery_log | domain_candidate |
| sms_log | 20 | messaging.delivery_log | domain_candidate |

## uam_user

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| action_permission_java | 491 | Review required | review |
| adv_mapping | 5 | Review required | review |
| application_delete_history | 2 | audit.application_deletion | domain_candidate |
| application_update_history | 1 | audit.application_revision | domain_candidate |
| att_sheet_leave | 7,728 | attendance.sheet_leave | domain_candidate |
| att_status_history_012020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012025 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022025 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032025 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112018 | 4 | attendance.status_revision | consolidate_candidate |
| att_status_history_112019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112024 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122024 | 0 | attendance.status_revision | consolidate_candidate |
| attendance_012020 | 1,015 | attendance.daily_record | consolidate_candidate |
| attendance_012021 | 603 | attendance.daily_record | consolidate_candidate |
| attendance_012022 | 536 | attendance.daily_record | consolidate_candidate |
| attendance_012023 | 465 | attendance.daily_record | consolidate_candidate |
| attendance_012024 | 647 | attendance.daily_record | consolidate_candidate |
| attendance_012025 | 437 | attendance.daily_record | consolidate_candidate |
| attendance_022020 | 1,015 | attendance.daily_record | consolidate_candidate |
| attendance_022021 | 595 | attendance.daily_record | consolidate_candidate |
| attendance_022022 | 737 | attendance.daily_record | consolidate_candidate |
| attendance_022023 | 428 | attendance.daily_record | consolidate_candidate |
| attendance_022024 | 534 | attendance.daily_record | consolidate_candidate |
| attendance_022025 | 393 | attendance.daily_record | consolidate_candidate |
| attendance_032020 | 791 | attendance.daily_record | consolidate_candidate |
| attendance_032021 | 549 | attendance.daily_record | consolidate_candidate |
| attendance_032022 | 597 | attendance.daily_record | consolidate_candidate |
| attendance_032023 | 462 | attendance.daily_record | consolidate_candidate |
| attendance_032024 | 525 | attendance.daily_record | consolidate_candidate |
| attendance_032025 | 402 | attendance.daily_record | consolidate_candidate |
| attendance_042019 | 246 | attendance.daily_record | consolidate_candidate |
| attendance_042021 | 182 | attendance.daily_record | consolidate_candidate |
| attendance_042022 | 506 | attendance.daily_record | consolidate_candidate |
| attendance_042023 | 501 | attendance.daily_record | consolidate_candidate |
| attendance_042024 | 449 | attendance.daily_record | consolidate_candidate |
| attendance_052019 | 88 | attendance.daily_record | consolidate_candidate |
| attendance_052021 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_052022 | 647 | attendance.daily_record | consolidate_candidate |
| attendance_052023 | 560 | attendance.daily_record | consolidate_candidate |
| attendance_052024 | 588 | attendance.daily_record | consolidate_candidate |
| attendance_062020 | 30 | attendance.daily_record | consolidate_candidate |
| attendance_062020_backup | 30 | Review required | archive_candidate |
| attendance_062021 | 543 | attendance.daily_record | consolidate_candidate |
| attendance_062021_backup | 538 | Review required | archive_candidate |
| attendance_062022 | 630 | attendance.daily_record | consolidate_candidate |
| attendance_062023 | 548 | attendance.daily_record | consolidate_candidate |
| attendance_062024 | 533 | attendance.daily_record | consolidate_candidate |
| attendance_072019 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_072020 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_072021 | 903 | attendance.daily_record | consolidate_candidate |
| attendance_072021_backup | 109 | Review required | archive_candidate |
| attendance_072022 | 610 | attendance.daily_record | consolidate_candidate |
| attendance_072023 | 673 | attendance.daily_record | consolidate_candidate |
| attendance_072024 | 528 | attendance.daily_record | consolidate_candidate |
| attendance_082019 | 1,489 | attendance.daily_record | consolidate_candidate |
| attendance_082020 | 184 | attendance.daily_record | consolidate_candidate |
| attendance_082021 | 664 | attendance.daily_record | consolidate_candidate |
| attendance_082022 | 561 | attendance.daily_record | consolidate_candidate |
| attendance_082023 | 569 | attendance.daily_record | consolidate_candidate |
| attendance_082024 | 476 | attendance.daily_record | consolidate_candidate |
| attendance_092019 | 3,601 | attendance.daily_record | consolidate_candidate |
| attendance_092020 | 30,826 | attendance.daily_record | consolidate_candidate |
| attendance_092021 | 672 | attendance.daily_record | consolidate_candidate |
| attendance_092022 | 577 | attendance.daily_record | consolidate_candidate |
| attendance_092023 | 558 | attendance.daily_record | consolidate_candidate |
| attendance_092024 | 477 | attendance.daily_record | consolidate_candidate |
| attendance_102019 | 943 | attendance.daily_record | consolidate_candidate |
| attendance_102020 | 664 | attendance.daily_record | consolidate_candidate |
| attendance_102021 | 710 | attendance.daily_record | consolidate_candidate |
| attendance_102022 | 487 | attendance.daily_record | consolidate_candidate |
| attendance_102023 | 592 | attendance.daily_record | consolidate_candidate |
| attendance_102024 | 500 | attendance.daily_record | consolidate_candidate |
| attendance_112019 | 921 | attendance.daily_record | consolidate_candidate |
| attendance_112020 | 585 | attendance.daily_record | consolidate_candidate |
| attendance_112021 | 565 | attendance.daily_record | consolidate_candidate |
| attendance_112022 | 582 | attendance.daily_record | consolidate_candidate |
| attendance_112023 | 528 | attendance.daily_record | consolidate_candidate |
| attendance_112024 | 487 | attendance.daily_record | consolidate_candidate |
| attendance_122019 | 910 | attendance.daily_record | consolidate_candidate |
| attendance_122020 | 638 | attendance.daily_record | consolidate_candidate |
| attendance_122021 | 598 | attendance.daily_record | consolidate_candidate |
| attendance_122022 | 497 | attendance.daily_record | consolidate_candidate |
| attendance_122023 | 550 | attendance.daily_record | consolidate_candidate |
| attendance_122024 | 425 | attendance.daily_record | consolidate_candidate |
| attendance_132021 | 0 | attendance.daily_record | review_invalid_period |
| attendance_sheet | 52 | attendance.approved_sheet | domain_candidate |
| attendance_sheet_list | 786 | attendance.sheet_item | domain_candidate |
| attendance_status_012019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_012020 | 584 | attendance.daily_status | consolidate_candidate |
| attendance_status_012021 | 424 | attendance.daily_status | consolidate_candidate |
| attendance_status_012022 | 529 | attendance.daily_status | consolidate_candidate |
| attendance_status_012023 | 475 | attendance.daily_status | consolidate_candidate |
| attendance_status_012024 | 520 | attendance.daily_status | consolidate_candidate |
| attendance_status_012025 | 377 | attendance.daily_status | consolidate_candidate |
| attendance_status_022019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_022020 | 594 | attendance.daily_status | consolidate_candidate |
| attendance_status_022021 | 409 | attendance.daily_status | consolidate_candidate |
| attendance_status_022022 | 523 | attendance.daily_status | consolidate_candidate |
| attendance_status_022023 | 441 | attendance.daily_status | consolidate_candidate |
| attendance_status_022024 | 485 | attendance.daily_status | consolidate_candidate |
| attendance_status_022025 | 346 | attendance.daily_status | consolidate_candidate |
| attendance_status_032019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_032020 | 432 | attendance.daily_status | consolidate_candidate |
| attendance_status_032021 | 378 | attendance.daily_status | consolidate_candidate |
| attendance_status_032022 | 519 | attendance.daily_status | consolidate_candidate |
| attendance_status_032023 | 455 | attendance.daily_status | consolidate_candidate |
| attendance_status_032024 | 454 | attendance.daily_status | consolidate_candidate |
| attendance_status_032025 | 352 | attendance.daily_status | consolidate_candidate |
| attendance_status_042019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_042021 | 193 | attendance.daily_status | consolidate_candidate |
| attendance_status_042022 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_042023 | 479 | attendance.daily_status | consolidate_candidate |
| attendance_status_042024 | 452 | attendance.daily_status | consolidate_candidate |
| attendance_status_052019 | 499 | attendance.daily_status | consolidate_candidate |
| attendance_status_052021 | 135 | attendance.daily_status | consolidate_candidate |
| attendance_status_052022 | 637 | attendance.daily_status | consolidate_candidate |
| attendance_status_052023 | 473 | attendance.daily_status | consolidate_candidate |
| attendance_status_052024 | 481 | attendance.daily_status | consolidate_candidate |
| attendance_status_062019 | 894 | attendance.daily_status | consolidate_candidate |
| attendance_status_062020 | 79 | attendance.daily_status | consolidate_candidate |
| attendance_status_062021 | 274 | attendance.daily_status | consolidate_candidate |
| attendance_status_062021_backup | 274 | Review required | archive_candidate |
| attendance_status_062022 | 558 | attendance.daily_status | consolidate_candidate |
| attendance_status_062023 | 494 | attendance.daily_status | consolidate_candidate |
| attendance_status_062024 | 460 | attendance.daily_status | consolidate_candidate |
| attendance_status_072019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_072020 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_072021 | 460 | attendance.daily_status | consolidate_candidate |
| attendance_status_072021_backup | 62 | Review required | archive_candidate |
| attendance_status_072022 | 570 | attendance.daily_status | consolidate_candidate |
| attendance_status_072023 | 569 | attendance.daily_status | consolidate_candidate |
| attendance_status_072024 | 438 | attendance.daily_status | consolidate_candidate |
| attendance_status_082019 | 64 | attendance.daily_status | consolidate_candidate |
| attendance_status_082020 | 160 | attendance.daily_status | consolidate_candidate |
| attendance_status_082021 | 505 | attendance.daily_status | consolidate_candidate |
| attendance_status_082022 | 495 | attendance.daily_status | consolidate_candidate |
| attendance_status_082023 | 525 | attendance.daily_status | consolidate_candidate |
| attendance_status_082024 | 405 | attendance.daily_status | consolidate_candidate |
| attendance_status_092019 | 600 | attendance.daily_status | consolidate_candidate |
| attendance_status_092020 | 6,039 | attendance.daily_status | consolidate_candidate |
| attendance_status_092021 | 543 | attendance.daily_status | consolidate_candidate |
| attendance_status_092022 | 508 | attendance.daily_status | consolidate_candidate |
| attendance_status_092023 | 513 | attendance.daily_status | consolidate_candidate |
| attendance_status_092024 | 442 | attendance.daily_status | consolidate_candidate |
| attendance_status_102019 | 525 | attendance.daily_status | consolidate_candidate |
| attendance_status_102020 | 525 | attendance.daily_status | consolidate_candidate |
| attendance_status_102021 | 622 | attendance.daily_status | consolidate_candidate |
| attendance_status_102022 | 505 | attendance.daily_status | consolidate_candidate |
| attendance_status_102023 | 527 | attendance.daily_status | consolidate_candidate |
| attendance_status_102024 | 404 | attendance.daily_status | consolidate_candidate |
| attendance_status_112019 | 555 | attendance.daily_status | consolidate_candidate |
| attendance_status_112020 | 448 | attendance.daily_status | consolidate_candidate |
| attendance_status_112021 | 524 | attendance.daily_status | consolidate_candidate |
| attendance_status_112022 | 541 | attendance.daily_status | consolidate_candidate |
| attendance_status_112023 | 502 | attendance.daily_status | consolidate_candidate |
| attendance_status_112024 | 412 | attendance.daily_status | consolidate_candidate |
| attendance_status_122019 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_122020 | 374 | attendance.daily_status | consolidate_candidate |
| attendance_status_122021 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_122022 | 518 | attendance.daily_status | consolidate_candidate |
| attendance_status_122023 | 530 | attendance.daily_status | consolidate_candidate |
| attendance_status_122024 | 371 | attendance.daily_status | consolidate_candidate |
| bank | 199 | reference.bank | domain_candidate |
| bank_branch | 143,702 | reference.bank_branch | domain_candidate |
| bank_branch_old | 143,521 | Review required | archive_candidate |
| bank_old | 200 | Review required | archive_candidate |
| block | 585 | organization.block | domain_candidate |
| calender | 33 | attendance.calendar | domain_candidate |
| circle | 11 | organization.circle | domain_candidate |
| city | 2 | organization.city | domain_candidate |
| correction_dates | 34 | Review required | review |
| da_details | 0 | payroll.da_schedule | domain_candidate |
| department | 5 | hr.department | domain_candidate |
| deputation_department | 0 | hr.deputation_department | domain_candidate |
| designation | 19 | hr.designation | domain_candidate |
| designation_senctioned_detail | 0 | Review required | review |
| designation_senctioned_dtl_bk | 0 | Review required | archive_candidate |
| device_location | 0 | attendance.device_location | domain_candidate |
| devicelogs_10_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_11_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_12_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_1_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_2_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2022 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_3_2025 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_4_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_5_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_6_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_8_2024 | 0 | attendance.device_event | consolidate_candidate |
| devicelogs_9_2024 | 0 | attendance.device_event | consolidate_candidate |
| district | 79 | organization.district | domain_candidate |
| division | 0 | organization.division | domain_candidate |
| email_log | 0 | messaging.delivery_log | domain_candidate |
| emp_additional_charge | 0 | hr.additional_assignment | domain_candidate |
| emp_application_012020 | 318 | attendance.employee_application | consolidate_candidate |
| emp_application_012021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_012022 | 280 | attendance.employee_application | consolidate_candidate |
| emp_application_012023 | 167 | attendance.employee_application | consolidate_candidate |
| emp_application_012024 | 276 | attendance.employee_application | consolidate_candidate |
| emp_application_012025 | 124 | attendance.employee_application | consolidate_candidate |
| emp_application_022020 | 333 | attendance.employee_application | consolidate_candidate |
| emp_application_022021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_022022 | 275 | attendance.employee_application | consolidate_candidate |
| emp_application_022023 | 165 | attendance.employee_application | consolidate_candidate |
| emp_application_022024 | 254 | attendance.employee_application | consolidate_candidate |
| emp_application_022025 | 139 | attendance.employee_application | consolidate_candidate |
| emp_application_032020 | 180 | attendance.employee_application | consolidate_candidate |
| emp_application_032021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_032022 | 277 | attendance.employee_application | consolidate_candidate |
| emp_application_032023 | 174 | attendance.employee_application | consolidate_candidate |
| emp_application_032024 | 245 | attendance.employee_application | consolidate_candidate |
| emp_application_032025 | 112 | attendance.employee_application | consolidate_candidate |
| emp_application_042021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_042022 | 301 | attendance.employee_application | consolidate_candidate |
| emp_application_042023 | 151 | attendance.employee_application | consolidate_candidate |
| emp_application_042024 | 203 | attendance.employee_application | consolidate_candidate |
| emp_application_052019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_052021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_052022 | 336 | attendance.employee_application | consolidate_candidate |
| emp_application_052023 | 179 | attendance.employee_application | consolidate_candidate |
| emp_application_052024 | 231 | attendance.employee_application | consolidate_candidate |
| emp_application_062019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_062020 | 181 | attendance.employee_application | consolidate_candidate |
| emp_application_062021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_062022 | 282 | attendance.employee_application | consolidate_candidate |
| emp_application_062023 | 221 | attendance.employee_application | consolidate_candidate |
| emp_application_062024 | 199 | attendance.employee_application | consolidate_candidate |
| emp_application_072019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_072020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_072021 | 95 | attendance.employee_application | consolidate_candidate |
| emp_application_072022 | 271 | attendance.employee_application | consolidate_candidate |
| emp_application_072023 | 295 | attendance.employee_application | consolidate_candidate |
| emp_application_072024 | 206 | attendance.employee_application | consolidate_candidate |
| emp_application_082019 | 2 | attendance.employee_application | consolidate_candidate |
| emp_application_082020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_082021 | 80 | attendance.employee_application | consolidate_candidate |
| emp_application_082022 | 213 | attendance.employee_application | consolidate_candidate |
| emp_application_082023 | 289 | attendance.employee_application | consolidate_candidate |
| emp_application_082024 | 140 | attendance.employee_application | consolidate_candidate |
| emp_application_092019 | 196 | attendance.employee_application | consolidate_candidate |
| emp_application_092020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_092021 | 174 | attendance.employee_application | consolidate_candidate |
| emp_application_092022 | 195 | attendance.employee_application | consolidate_candidate |
| emp_application_092023 | 264 | attendance.employee_application | consolidate_candidate |
| emp_application_092024 | 192 | attendance.employee_application | consolidate_candidate |
| emp_application_102019 | 284 | attendance.employee_application | consolidate_candidate |
| emp_application_102020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_102021 | 258 | attendance.employee_application | consolidate_candidate |
| emp_application_102022 | 180 | attendance.employee_application | consolidate_candidate |
| emp_application_102023 | 291 | attendance.employee_application | consolidate_candidate |
| emp_application_102024 | 156 | attendance.employee_application | consolidate_candidate |
| emp_application_112019 | 308 | attendance.employee_application | consolidate_candidate |
| emp_application_112020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_112021 | 293 | attendance.employee_application | consolidate_candidate |
| emp_application_112022 | 204 | attendance.employee_application | consolidate_candidate |
| emp_application_112023 | 283 | attendance.employee_application | consolidate_candidate |
| emp_application_112024 | 174 | attendance.employee_application | consolidate_candidate |
| emp_application_122019 | 246 | attendance.employee_application | consolidate_candidate |
| emp_application_122020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_122021 | 306 | attendance.employee_application | consolidate_candidate |
| emp_application_122022 | 191 | attendance.employee_application | consolidate_candidate |
| emp_application_122023 | 279 | attendance.employee_application | consolidate_candidate |
| emp_application_122024 | 145 | attendance.employee_application | consolidate_candidate |
| emp_assigned_section | 80 | hr.section_assignment | domain_candidate |
| emp_bank_acc_verification | 0 | Review required | review |
| emp_bank_acc_verification_his | 0 | Review required | review |
| emp_bankdetail | 55 | hr.employee_bank_account | domain_candidate |
| emp_bankdetail_history | 0 | hr.employee_bank_account_revision | domain_candidate |
| emp_device | 113 | attendance.employee_device_identity | domain_candidate |
| emp_function | 59 | Review required | review |
| emp_pay_head | 0 | payroll.pay_head | domain_candidate |
| emp_salary_backup_history_del | 316 | Review required | archive_candidate |
| emp_salary_summary_history | 0 | Review required | review |
| employee | 51 | hr.employee | domain_candidate |
| employee_291118 | 0 | Review required | archive_candidate |
| employee_del | 0 | Review required | archive_candidate |
| employee_group | 0 | hr.employee_group | domain_candidate |
| employee_history | 0 | hr.employee_revision | domain_candidate |
| employee_salary | 515 | payroll.salary_record | domain_candidate |
| employee_salary_backup | 312 | Review required | archive_candidate |
| employee_salary_backup_history | 3,487 | Review required | archive_candidate |
| employee_salary_del | 12,554 | Review required | archive_candidate |
| employee_salary_detail | 48 | payroll.salary_component | domain_candidate |
| employee_salary_detail_history | 0 | payroll.component_revision | domain_candidate |
| employee_salary_history | 0 | payroll.salary_revision | domain_candidate |
| employee_salary_main | 36 | payroll.salary_configuration | domain_candidate |
| employee_salary_main_backup | 38 | Review required | archive_candidate |
| employee_salary_main_history | 1,399 | payroll.configuration_revision | domain_candidate |
| employee_salary_pay_head | 5,693 | payroll.employee_pay_head | domain_candidate |
| employee_salary_pay_head7623 | 2,472 | Review required | archive_candidate |
| employee_salary_summary | 597 | payroll.salary_summary | domain_candidate |
| employee_salary_summary7623 | 254 | Review required | archive_candidate |
| employee_type | 4 | hr.employee_type | domain_candidate |
| function | 5 | Review required | review |
| gpf_detail | 0 | payroll.provident_fund | domain_candidate |
| grade_pay | 2 | payroll.grade_pay | domain_candidate |
| grade_pay_new | 1 | payroll.grade_pay_schedule | domain_candidate |
| house_type | 0 | Review required | review |
| hql_permission_082019 | 0 | Review required | archive_candidate |
| hra_details | 0 | payroll.hra_schedule | domain_candidate |
| invoice_follow_up | 0 | Review required | review |
| joining_batch | 0 | Review required | review |
| kyc_details | 0 | hr.employee_identity | domain_candidate |
| leave_manage | 189 | leave.request | domain_candidate |
| leave_manage_history | 0 | leave.request_revision | domain_candidate |
| leave_type | 10 | leave.type | domain_candidate |
| leave_verification_detail | 39 | leave.approval | domain_candidate |
| leaveday_backup | 7 | Review required | archive_candidate |
| link_officer | 0 | Review required | review |
| location | 0 | organization.location | domain_candidate |
| login_history | 74,164 | identity.login_event | domain_candidate |
| logtable | 2,031,252 | Review required | review |
| master_history | 1,234 | audit.legacy_master_event | domain_candidate |
| notification | 22,013 | messaging.notification | domain_candidate |
| notification_detail | 22,013 | messaging.notification_recipient | domain_candidate |
| nullday | 0 | Review required | review |
| official_location | 12 | organization.official_location | domain_candidate |
| org_structure_data | 0 | Review required | review |
| org_structure_tagging | 0 | Review required | review |
| panchayat | 8,210 | organization.panchayat | domain_candidate |
| pay_band | 0 | payroll.pay_band | domain_candidate |
| pay_code | 35 | payroll.pay_code | domain_candidate |
| pay_code_bak7623 | 32 | Review required | archive_candidate |
| pay_commission | 0 | payroll.pay_commission | domain_candidate |
| payroll_1018_gwalior | 0 | Review required | review |
| payroll_data_indore | 0 | Review required | review |
| project | 3 | identity.legacy_project | domain_candidate |
| project_url | 3 | identity.legacy_resource | domain_candidate |
| project_url_loc | 3 | identity.resource_scope | domain_candidate |
| region | 1 | organization.region | domain_candidate |
| salary_deduction | 0 | payroll.deduction | domain_candidate |
| salary_sheet | 1,420 | payroll.pay_run_sheet | domain_candidate |
| shift_schedule | 3 | attendance.shift | domain_candidate |
| shift_tour_history | 0 | attendance.shift_assignment_revision | domain_candidate |
| shift_tours | 84 | attendance.shift_assignment | domain_candidate |
| sms_log | 0 | messaging.delivery_log | domain_candidate |
| state | 13 | organization.state | domain_candidate |
| sublocation | 0 | organization.sublocation | domain_candidate |
| submodule | 593 | identity.legacy_submodule | domain_candidate |
| transfer | 0 | hr.transfer | domain_candidate |
| transfer_emp | 0 | hr.transfer_employee | domain_candidate |
| transfer_remark | 0 | hr.transfer_note | domain_candidate |
| uam_module | 56 | identity.legacy_module | domain_candidate |
| upload | 50 | documents.document | domain_candidate |
| upload_sys | 429 | documents.legacy_upload_configuration | domain_candidate |
| userdetail | 51 | identity.legacy_user | domain_candidate |
| userdetail_del | 0 | Review required | archive_candidate |
| userdetail_history | 0 | identity.user_revision | domain_candidate |
| userdetail_login | 51 | identity.legacy_login_state | domain_candidate |
| userdetail_per | 114 | identity.legacy_permission | domain_candidate |
| userdetail_per_history | 0 | identity.permission_revision | domain_candidate |
| userdetail_per_temp | 0 | Review required | archive_candidate |
| usertype | 35 | identity.legacy_role | domain_candidate |
| verify_emp_salary | 601 | payroll.approval | domain_candidate |
| village | 23,793 | organization.village | domain_candidate |
| visitors | 0 | Review required | review |
| week_off_detail | 0 | attendance.weekly_rest_rule | domain_candidate |
| what_new | 1 | Review required | review |

## uam_user_uat

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| action_permission_java | 471 | Review required | review |
| adv_mapping | 5 | Review required | review |
| application_delete_history | 2 | audit.application_deletion | domain_candidate |
| application_update_history | 1 | audit.application_revision | domain_candidate |
| att_sheet_leave | 4,828 | attendance.sheet_leave | domain_candidate |
| att_status_history_012020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_012023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_022023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_032023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_042023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_052023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_062023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_072023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_082023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_092023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_102023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112018 | 4 | attendance.status_revision | consolidate_candidate |
| att_status_history_112019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_112023 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122019 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122020 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122021 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122022 | 0 | attendance.status_revision | consolidate_candidate |
| att_status_history_122023 | 0 | attendance.status_revision | consolidate_candidate |
| attendance_012020 | 1,015 | attendance.daily_record | consolidate_candidate |
| attendance_012021 | 603 | attendance.daily_record | consolidate_candidate |
| attendance_012022 | 536 | attendance.daily_record | consolidate_candidate |
| attendance_012023 | 465 | attendance.daily_record | consolidate_candidate |
| attendance_022020 | 1,015 | attendance.daily_record | consolidate_candidate |
| attendance_022021 | 595 | attendance.daily_record | consolidate_candidate |
| attendance_022022 | 737 | attendance.daily_record | consolidate_candidate |
| attendance_022023 | 428 | attendance.daily_record | consolidate_candidate |
| attendance_032020 | 791 | attendance.daily_record | consolidate_candidate |
| attendance_032021 | 549 | attendance.daily_record | consolidate_candidate |
| attendance_032022 | 597 | attendance.daily_record | consolidate_candidate |
| attendance_032023 | 462 | attendance.daily_record | consolidate_candidate |
| attendance_042019 | 246 | attendance.daily_record | consolidate_candidate |
| attendance_042021 | 182 | attendance.daily_record | consolidate_candidate |
| attendance_042022 | 506 | attendance.daily_record | consolidate_candidate |
| attendance_042023 | 501 | attendance.daily_record | consolidate_candidate |
| attendance_052019 | 88 | attendance.daily_record | consolidate_candidate |
| attendance_052021 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_052022 | 647 | attendance.daily_record | consolidate_candidate |
| attendance_052023 | 560 | attendance.daily_record | consolidate_candidate |
| attendance_062020 | 30 | attendance.daily_record | consolidate_candidate |
| attendance_062020_backup | 30 | Review required | archive_candidate |
| attendance_062021 | 543 | attendance.daily_record | consolidate_candidate |
| attendance_062021_backup | 538 | Review required | archive_candidate |
| attendance_062022 | 630 | attendance.daily_record | consolidate_candidate |
| attendance_062023 | 548 | attendance.daily_record | consolidate_candidate |
| attendance_072019 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_072020 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_072021 | 903 | attendance.daily_record | consolidate_candidate |
| attendance_072021_backup | 109 | Review required | archive_candidate |
| attendance_072022 | 610 | attendance.daily_record | consolidate_candidate |
| attendance_072023 | 673 | attendance.daily_record | consolidate_candidate |
| attendance_082019 | 1,489 | attendance.daily_record | consolidate_candidate |
| attendance_082020 | 184 | attendance.daily_record | consolidate_candidate |
| attendance_082021 | 664 | attendance.daily_record | consolidate_candidate |
| attendance_082022 | 561 | attendance.daily_record | consolidate_candidate |
| attendance_082023 | 165 | attendance.daily_record | consolidate_candidate |
| attendance_092019 | 3,601 | attendance.daily_record | consolidate_candidate |
| attendance_092020 | 30,826 | attendance.daily_record | consolidate_candidate |
| attendance_092021 | 672 | attendance.daily_record | consolidate_candidate |
| attendance_092022 | 577 | attendance.daily_record | consolidate_candidate |
| attendance_092023 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_102019 | 943 | attendance.daily_record | consolidate_candidate |
| attendance_102020 | 664 | attendance.daily_record | consolidate_candidate |
| attendance_102021 | 710 | attendance.daily_record | consolidate_candidate |
| attendance_102022 | 487 | attendance.daily_record | consolidate_candidate |
| attendance_102023 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_112019 | 921 | attendance.daily_record | consolidate_candidate |
| attendance_112020 | 585 | attendance.daily_record | consolidate_candidate |
| attendance_112021 | 565 | attendance.daily_record | consolidate_candidate |
| attendance_112022 | 582 | attendance.daily_record | consolidate_candidate |
| attendance_112023 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_122019 | 910 | attendance.daily_record | consolidate_candidate |
| attendance_122020 | 638 | attendance.daily_record | consolidate_candidate |
| attendance_122021 | 598 | attendance.daily_record | consolidate_candidate |
| attendance_122022 | 497 | attendance.daily_record | consolidate_candidate |
| attendance_122023 | 0 | attendance.daily_record | consolidate_candidate |
| attendance_132021 | 0 | attendance.daily_record | review_invalid_period |
| attendance_sheet | 31 | attendance.approved_sheet | domain_candidate |
| attendance_sheet_list | 496 | attendance.sheet_item | domain_candidate |
| attendance_status_012019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_012020 | 584 | attendance.daily_status | consolidate_candidate |
| attendance_status_012021 | 424 | attendance.daily_status | consolidate_candidate |
| attendance_status_012022 | 529 | attendance.daily_status | consolidate_candidate |
| attendance_status_012023 | 475 | attendance.daily_status | consolidate_candidate |
| attendance_status_022019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_022020 | 594 | attendance.daily_status | consolidate_candidate |
| attendance_status_022021 | 409 | attendance.daily_status | consolidate_candidate |
| attendance_status_022022 | 523 | attendance.daily_status | consolidate_candidate |
| attendance_status_022023 | 441 | attendance.daily_status | consolidate_candidate |
| attendance_status_032019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_032020 | 432 | attendance.daily_status | consolidate_candidate |
| attendance_status_032021 | 378 | attendance.daily_status | consolidate_candidate |
| attendance_status_032022 | 519 | attendance.daily_status | consolidate_candidate |
| attendance_status_032023 | 455 | attendance.daily_status | consolidate_candidate |
| attendance_status_042019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_042021 | 193 | attendance.daily_status | consolidate_candidate |
| attendance_status_042022 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_042023 | 479 | attendance.daily_status | consolidate_candidate |
| attendance_status_052019 | 499 | attendance.daily_status | consolidate_candidate |
| attendance_status_052021 | 135 | attendance.daily_status | consolidate_candidate |
| attendance_status_052022 | 637 | attendance.daily_status | consolidate_candidate |
| attendance_status_052023 | 473 | attendance.daily_status | consolidate_candidate |
| attendance_status_062019 | 894 | attendance.daily_status | consolidate_candidate |
| attendance_status_062020 | 79 | attendance.daily_status | consolidate_candidate |
| attendance_status_062021 | 274 | attendance.daily_status | consolidate_candidate |
| attendance_status_062021_backup | 274 | Review required | archive_candidate |
| attendance_status_062022 | 558 | attendance.daily_status | consolidate_candidate |
| attendance_status_062023 | 494 | attendance.daily_status | consolidate_candidate |
| attendance_status_072019 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_072020 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_072021 | 460 | attendance.daily_status | consolidate_candidate |
| attendance_status_072021_backup | 62 | Review required | archive_candidate |
| attendance_status_072022 | 570 | attendance.daily_status | consolidate_candidate |
| attendance_status_072023 | 569 | attendance.daily_status | consolidate_candidate |
| attendance_status_082019 | 64 | attendance.daily_status | consolidate_candidate |
| attendance_status_082020 | 160 | attendance.daily_status | consolidate_candidate |
| attendance_status_082021 | 505 | attendance.daily_status | consolidate_candidate |
| attendance_status_082022 | 495 | attendance.daily_status | consolidate_candidate |
| attendance_status_082023 | 146 | attendance.daily_status | consolidate_candidate |
| attendance_status_092019 | 600 | attendance.daily_status | consolidate_candidate |
| attendance_status_092020 | 6,039 | attendance.daily_status | consolidate_candidate |
| attendance_status_092021 | 543 | attendance.daily_status | consolidate_candidate |
| attendance_status_092022 | 508 | attendance.daily_status | consolidate_candidate |
| attendance_status_092023 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_102019 | 525 | attendance.daily_status | consolidate_candidate |
| attendance_status_102020 | 525 | attendance.daily_status | consolidate_candidate |
| attendance_status_102021 | 622 | attendance.daily_status | consolidate_candidate |
| attendance_status_102022 | 505 | attendance.daily_status | consolidate_candidate |
| attendance_status_102023 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_112019 | 555 | attendance.daily_status | consolidate_candidate |
| attendance_status_112020 | 448 | attendance.daily_status | consolidate_candidate |
| attendance_status_112021 | 524 | attendance.daily_status | consolidate_candidate |
| attendance_status_112022 | 541 | attendance.daily_status | consolidate_candidate |
| attendance_status_112023 | 0 | attendance.daily_status | consolidate_candidate |
| attendance_status_122019 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_122020 | 374 | attendance.daily_status | consolidate_candidate |
| attendance_status_122021 | 549 | attendance.daily_status | consolidate_candidate |
| attendance_status_122022 | 518 | attendance.daily_status | consolidate_candidate |
| attendance_status_122023 | 0 | attendance.daily_status | consolidate_candidate |
| bank | 199 | reference.bank | domain_candidate |
| bank_branch | 143,635 | reference.bank_branch | domain_candidate |
| bank_branch_old | 143,521 | Review required | archive_candidate |
| bank_old | 200 | Review required | archive_candidate |
| block | 510 | organization.block | domain_candidate |
| calender | 24 | attendance.calendar | domain_candidate |
| circle | 11 | organization.circle | domain_candidate |
| city | 2 | organization.city | domain_candidate |
| correction_dates | 34 | Review required | review |
| da_details | 0 | payroll.da_schedule | domain_candidate |
| department | 5 | hr.department | domain_candidate |
| deputation_department | 0 | hr.deputation_department | domain_candidate |
| designation | 19 | hr.designation | domain_candidate |
| designation_senctioned_detail | 0 | Review required | review |
| designation_senctioned_dtl_bk | 0 | Review required | archive_candidate |
| device_location | 0 | attendance.device_location | domain_candidate |
| devicelogs_3_2022 | 0 | attendance.device_event | consolidate_candidate |
| district | 68 | organization.district | domain_candidate |
| division | 0 | organization.division | domain_candidate |
| email_log | 0 | messaging.delivery_log | domain_candidate |
| emp_additional_charge | 0 | hr.additional_assignment | domain_candidate |
| emp_application_012020 | 318 | attendance.employee_application | consolidate_candidate |
| emp_application_012021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_012022 | 280 | attendance.employee_application | consolidate_candidate |
| emp_application_012023 | 167 | attendance.employee_application | consolidate_candidate |
| emp_application_022020 | 333 | attendance.employee_application | consolidate_candidate |
| emp_application_022021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_022022 | 275 | attendance.employee_application | consolidate_candidate |
| emp_application_022023 | 165 | attendance.employee_application | consolidate_candidate |
| emp_application_032020 | 180 | attendance.employee_application | consolidate_candidate |
| emp_application_032021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_032022 | 277 | attendance.employee_application | consolidate_candidate |
| emp_application_032023 | 174 | attendance.employee_application | consolidate_candidate |
| emp_application_042021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_042022 | 301 | attendance.employee_application | consolidate_candidate |
| emp_application_042023 | 151 | attendance.employee_application | consolidate_candidate |
| emp_application_052019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_052021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_052022 | 336 | attendance.employee_application | consolidate_candidate |
| emp_application_052023 | 179 | attendance.employee_application | consolidate_candidate |
| emp_application_062019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_062020 | 181 | attendance.employee_application | consolidate_candidate |
| emp_application_062021 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_062022 | 282 | attendance.employee_application | consolidate_candidate |
| emp_application_062023 | 221 | attendance.employee_application | consolidate_candidate |
| emp_application_072019 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_072020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_072021 | 95 | attendance.employee_application | consolidate_candidate |
| emp_application_072022 | 271 | attendance.employee_application | consolidate_candidate |
| emp_application_072023 | 295 | attendance.employee_application | consolidate_candidate |
| emp_application_082019 | 2 | attendance.employee_application | consolidate_candidate |
| emp_application_082020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_082021 | 80 | attendance.employee_application | consolidate_candidate |
| emp_application_082022 | 213 | attendance.employee_application | consolidate_candidate |
| emp_application_082023 | 88 | attendance.employee_application | consolidate_candidate |
| emp_application_092019 | 196 | attendance.employee_application | consolidate_candidate |
| emp_application_092020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_092021 | 174 | attendance.employee_application | consolidate_candidate |
| emp_application_092022 | 195 | attendance.employee_application | consolidate_candidate |
| emp_application_092023 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_102019 | 284 | attendance.employee_application | consolidate_candidate |
| emp_application_102020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_102021 | 258 | attendance.employee_application | consolidate_candidate |
| emp_application_102022 | 180 | attendance.employee_application | consolidate_candidate |
| emp_application_102023 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_112019 | 308 | attendance.employee_application | consolidate_candidate |
| emp_application_112020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_112021 | 293 | attendance.employee_application | consolidate_candidate |
| emp_application_112022 | 204 | attendance.employee_application | consolidate_candidate |
| emp_application_112023 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_122019 | 246 | attendance.employee_application | consolidate_candidate |
| emp_application_122020 | 0 | attendance.employee_application | consolidate_candidate |
| emp_application_122021 | 306 | attendance.employee_application | consolidate_candidate |
| emp_application_122022 | 191 | attendance.employee_application | consolidate_candidate |
| emp_application_122023 | 0 | attendance.employee_application | consolidate_candidate |
| emp_assigned_section | 78 | hr.section_assignment | domain_candidate |
| emp_bank_acc_verification | 0 | Review required | review |
| emp_bank_acc_verification_his | 0 | Review required | review |
| emp_bankdetail | 54 | hr.employee_bank_account | domain_candidate |
| emp_bankdetail_history | 0 | hr.employee_bank_account_revision | domain_candidate |
| emp_device | 112 | attendance.employee_device_identity | domain_candidate |
| emp_function | 58 | Review required | review |
| emp_pay_head | 0 | payroll.pay_head | domain_candidate |
| emp_salary_backup_history_del | 311 | Review required | archive_candidate |
| emp_salary_summary_history | 0 | Review required | review |
| employee | 49 | hr.employee | domain_candidate |
| employee_291118 | 0 | Review required | archive_candidate |
| employee_del | 0 | Review required | archive_candidate |
| employee_group | 0 | hr.employee_group | domain_candidate |
| employee_history | 0 | hr.employee_revision | domain_candidate |
| employee_salary | 471 | payroll.salary_record | domain_candidate |
| employee_salary_backup | 268 | Review required | archive_candidate |
| employee_salary_backup_history | 1,716 | Review required | archive_candidate |
| employee_salary_del | 5,414 | Review required | archive_candidate |
| employee_salary_detail | 47 | payroll.salary_component | domain_candidate |
| employee_salary_detail_history | 0 | payroll.component_revision | domain_candidate |
| employee_salary_history | 0 | payroll.salary_revision | domain_candidate |
| employee_salary_main | 36 | payroll.salary_configuration | domain_candidate |
| employee_salary_main_backup | 38 | Review required | archive_candidate |
| employee_salary_main_history | 820 | payroll.configuration_revision | domain_candidate |
| employee_salary_pay_head | 2,808 | payroll.employee_pay_head | domain_candidate |
| employee_salary_pay_head7623 | 2,472 | Review required | archive_candidate |
| employee_salary_summary | 296 | payroll.salary_summary | domain_candidate |
| employee_salary_summary7623 | 254 | Review required | archive_candidate |
| employee_type | 4 | hr.employee_type | domain_candidate |
| function | 5 | Review required | review |
| gpf_detail | 0 | payroll.provident_fund | domain_candidate |
| grade_pay | 2 | payroll.grade_pay | domain_candidate |
| grade_pay_new | 1 | payroll.grade_pay_schedule | domain_candidate |
| house_type | 0 | Review required | review |
| hql_permission_082019 | 0 | Review required | archive_candidate |
| hra_details | 0 | payroll.hra_schedule | domain_candidate |
| invoice_follow_up | 0 | Review required | review |
| joining_batch | 0 | Review required | review |
| kyc_details | 0 | hr.employee_identity | domain_candidate |
| leave_manage | 184 | leave.request | domain_candidate |
| leave_manage_history | 0 | leave.request_revision | domain_candidate |
| leave_type | 10 | leave.type | domain_candidate |
| leave_verification_detail | 37 | leave.approval | domain_candidate |
| leaveday_backup | 4 | Review required | archive_candidate |
| link_officer | 0 | Review required | review |
| location | 0 | organization.location | domain_candidate |
| login_history | 45,316 | identity.login_event | domain_candidate |
| logtable | 770,068 | Review required | review |
| master_history | 1,171 | audit.legacy_master_event | domain_candidate |
| notification | 13,699 | messaging.notification | domain_candidate |
| notification_detail | 13,699 | messaging.notification_recipient | domain_candidate |
| nullday | 0 | Review required | review |
| official_location | 12 | organization.official_location | domain_candidate |
| org_structure_data | 0 | Review required | review |
| org_structure_tagging | 0 | Review required | review |
| panchayat | 8,206 | organization.panchayat | domain_candidate |
| pay_band | 0 | payroll.pay_band | domain_candidate |
| pay_code | 35 | payroll.pay_code | domain_candidate |
| pay_code_bak7623 | 32 | Review required | archive_candidate |
| pay_commission | 0 | payroll.pay_commission | domain_candidate |
| payroll_1018_gwalior | 0 | Review required | review |
| payroll_data_indore | 0 | Review required | review |
| project | 3 | identity.legacy_project | domain_candidate |
| project_url | 3 | identity.legacy_resource | domain_candidate |
| project_url_loc | 3 | identity.resource_scope | domain_candidate |
| region | 1 | organization.region | domain_candidate |
| salary_deduction | 0 | payroll.deduction | domain_candidate |
| salary_sheet | 799 | payroll.pay_run_sheet | domain_candidate |
| shift_schedule | 3 | attendance.shift | domain_candidate |
| shift_tour_history | 0 | attendance.shift_assignment_revision | domain_candidate |
| shift_tours | 37 | attendance.shift_assignment | domain_candidate |
| sms_log | 0 | messaging.delivery_log | domain_candidate |
| state | 8 | organization.state | domain_candidate |
| sublocation | 0 | organization.sublocation | domain_candidate |
| submodule | 593 | identity.legacy_submodule | domain_candidate |
| transfer | 0 | hr.transfer | domain_candidate |
| transfer_emp | 0 | hr.transfer_employee | domain_candidate |
| transfer_remark | 0 | hr.transfer_note | domain_candidate |
| uam_module | 56 | identity.legacy_module | domain_candidate |
| upload | 48 | documents.document | domain_candidate |
| upload_sys | 214 | documents.legacy_upload_configuration | domain_candidate |
| userdetail | 50 | identity.legacy_user | domain_candidate |
| userdetail_del | 0 | Review required | archive_candidate |
| userdetail_history | 0 | identity.user_revision | domain_candidate |
| userdetail_login | 50 | identity.legacy_login_state | domain_candidate |
| userdetail_per | 111 | identity.legacy_permission | domain_candidate |
| userdetail_per_history | 0 | identity.permission_revision | domain_candidate |
| userdetail_per_temp | 0 | Review required | archive_candidate |
| usertype | 34 | identity.legacy_role | domain_candidate |
| verify_emp_salary | 404 | payroll.approval | domain_candidate |
| village | 23,793 | organization.village | domain_candidate |
| visitors | 0 | Review required | review |
| week_off_detail | 0 | attendance.weekly_rest_rule | domain_candidate |
| what_new | 1 | Review required | review |

## lead_mngt_uat

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| account_detail | 4 | billing.issuer_account | domain_candidate |
| amount_received | 1,519 | billing.legacy_receipt | domain_candidate |
| bank_report_heading | 465 | reports.heading | domain_candidate |
| billing_head | 6 | billing.charge_type | domain_candidate |
| cash_receipt | 6,787 | billing.receipt | domain_candidate |
| client | 1,090 | crm.client_office | domain_candidate |
| client_customer | 8,315 | leads.case | domain_candidate |
| client_designation | 17 | crm.contact_designation | domain_candidate |
| client_type | 7 | crm.client_type | domain_candidate |
| detail_category | 73 | valuations.question_category | domain_candidate |
| dispatch | 4,484 | reports.dispatch | domain_candidate |
| division | 9 | leads.division | domain_candidate |
| employee_tagging | 3 | leads.employee_assignment | domain_candidate |
| employee_target | 23 | leads.employee_target | domain_candidate |
| follow_up | 1,038 | leads.follow_up | domain_candidate |
| ifsc | 360 | reference.legacy_ifsc | domain_candidate |
| invoice | 7,656 | billing.invoice | domain_candidate |
| invoice_follow_up | 13 | billing.invoice_follow_up | domain_candidate |
| lead | 6,761 | leads.lead | domain_candidate |
| lead_borrower | 8,235 | leads.borrower | domain_candidate |
| lead_order | 7,878 | workorders.work_order | domain_candidate |
| lead_order_history | 1 | workorders.work_order_revision | domain_candidate |
| lead_services | 7,395 | leads.requested_service | domain_candidate |
| lead_upload | 0 | documents.lead_attachment | domain_candidate |
| offline_amount_received | 991 | billing.offline_receipt | domain_candidate |
| offline_invoice | 1,396 | billing.offline_invoice | domain_candidate |
| orderer_reg | 1,247 | crm.contact | domain_candidate |
| party | 0 | leads.party_type | domain_candidate |
| question | 1,504 | valuations.question | domain_candidate |
| question_options | 3,894 | valuations.question_option | domain_candidate |
| report_question | 4,114 | reports.template_question | domain_candidate |
| report_question_backup | 969 | Review required | archive_candidate |
| report_question_backup_25_08 | 161 | Review required | archive_candidate |
| report_question_backup_29_10 | 1,441 | Review required | archive_candidate |
| report_setup | 152 | reports.template_version | domain_candidate |
| report_setup_backup | 40 | Review required | archive_candidate |
| report_setup_backup_25_08 | 3 | Review required | archive_candidate |
| revert_back | 2,139 | valuations.reversion | domain_candidate |
| scrutiny_document | 130 | documents.scrutiny_requirement | domain_candidate |
| service_sub_type | 42 | services.service_subtype | domain_candidate |
| service_type | 15 | services.service_type | domain_candidate |
| sms_log | 55 | messaging.delivery_log | domain_candidate |
| sub_division | 12 | leads.subdivision | domain_candidate |
| upload | 92,895 | documents.document | domain_candidate |
| usage_documents | 0 | documents.document_usage | domain_candidate |
| usage_of_reports | 93 | reports.report_usage | domain_candidate |
| valuation | 8,132 | valuations.valuation | domain_candidate |
| valuation_answer | 1,351,410 | valuations.answer | domain_candidate |
| valuation_bank_report | 7,647 | reports.bank_report | domain_candidate |
| valuation_billing | 46,848 | billing.valuation_charge | domain_candidate |
| valuation_photo | 40,317 | documents.valuation_attachment | domain_candidate |
| valuation_verification | 7,757 | valuations.review | domain_candidate |
| wo_fees_calculation | 0 | workorders.fee_rule | domain_candidate |

## smldb_uat

| Source table | Rows | Proposed target | Disposition |
|---|---:|---|---|
| email_log | 0 | messaging.delivery_log | domain_candidate |
| sms_log | 5,125 | messaging.delivery_log | domain_candidate |

