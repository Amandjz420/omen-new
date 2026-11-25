# Client review 2026-11-25: lead flow, step 1 (naming and the new lead form)

From the "Lead to Case" flowchart (Lead Giver Info → Work Order Info → Case Details → send work order → documents → case allotment), agreed with Aman.

## Naming (labels only; models, fields and API names unchanged)
- Orderer → **Client** (the person who orders the work).
- The client office → **Organisation** (Organisation type, Organisation name, Branch).
- Client's customer / client customer / borrower → **Applicant**.
- Applied to the lead and case screens, the work-order letter, invoices and payer options, MIS reports and search placeholders, and the list screens. Model choice labels changed: `Borrower.payer` and `Invoice.payer` are now "By Client" / "By Applicant", and `Invoice.gstin_party` is now "Organisation" / "Applicant" / "Other" (migration 0037, labels only). The bank report PDF keeps the bank's prescribed wording.
- Individual leads: the client is the applicant, so the applicant form starts with the client's name and mobile and is titled "Client (applicant)".

## New lead form
- It asks for **No. of applicants** and **No. of cases** (both required, at least 1) and **no service type**. Each case now picks its own service and sub-type from the whole catalog, with a bank's own form pre-chosen for that bank's leads. Services requested on older leads still show, read-only.
- **Lead received by** is the signed-in person's employee record, set by the server. An account with no employee record chooses it.
- **Lead assigned to** is not on the form. A new lead is unassigned and stays "New lead".

## Pickup and reassignment (`apps/leads/assignment.py`)
- `POST /api/intake/leads/<id>/pick-up/` assigns the lead to the caller and moves it to "In process". It requires the caller's employee record, and either an unrestricted user or a role named in `LEAD_PICKUP_ROLES` (comma-separated env var; **not decided yet**, so empty means managers/admins only).
- `POST /api/intake/leads/<id>/reassign/ {employee}` is for unrestricted users (managers) only. Both actions are audited.
- Restricted users see leads assigned to them **or received by them**. Users who may pick up also see the unassigned queue. The lead list gains an "Assigned to" column and filter (Unassigned / Assigned to me). The lead page shows who received it, who has it, and Pick up / Reassign.
- Fix found on the way: the bank's-own-form check on a case now runs against the case's lead. It was skipped while the lead-level service check covered it.

Tests: backend 585 OK, frontend 74 OK.
