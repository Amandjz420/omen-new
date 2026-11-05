# Client review 2026-11-05: lead intake

| # | Request | Done |
|---|---------|------|
| 1 | Client type: Corporate, Financial Institution, Individual | Only these three are offered. Migration 0036 moves the clients of Business Development Officer/Agent (3 on production) to Individual and marks those types and both HLC rows inactive. They are kept so a source refresh still resolves their identities, but nothing points at them. |
| 2 | No IFSC for Individual / Corporate | The IFSC field and Find button appear only for Financial Institution. The server clears the IFSC and bank of any other client type. |
| 3 | Add the client on the lead form | A **New client** panel on the lead form, for every type, takes name, branch, address, state/district/city, GST no. and PAN, plus the IFSC for an FI. The new client is selected straight away. GST and PAN are validated when given. |
| 4 | Lead giver → Orderer, plus "Contacted by" | Renamed on the form, the list, the lead page, the nav and the work-order letter. The new optional fields are `contacted_by_name`, `contacted_by_phone` (must be a mobile number) and `contacted_by_remark`. They are internal and not printed. |
| 5 | Lead details read-only; Edit reopens the lead form filled in | The details tab shows a read-only summary. **Edit lead** opens `/leads/:id/edit`, the same form, prefilled. It saves via `PATCH /api/intake/leads/:id/` with any form field, the orderer (found or newly registered, with the office following), and the services (added, changed or removed). A service with live cases can't be removed or changed. Editing is allowed until a work order exists, the same rule as before. |
| 6 | PIN optional | The PIN is optional on the case form. If one is given it must still be six digits. |
| 7 | Work order: terms of payment and signature | New section (6) Terms of Payment is built from the customer's fee agreement: who pays, the fee, payment mode, the person responsible, the due date and the GST no. It is followed by a blank block for the client's authorised signatory: name, designation, date and seal. |

Also fixed: a case's scrutiny-document codes are now stored in the order chosen. A test had been order-dependent.

Tests: backend 577 OK (sqlite), frontend 75 OK.
