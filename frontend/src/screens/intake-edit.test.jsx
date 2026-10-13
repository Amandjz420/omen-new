import {fireEvent, screen, waitFor, within} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';
import {IntakeLead} from '../intake.jsx';
import {WorkOrders} from '../workorders.jsx';
import {api} from '../lib/api.js';
import {BorrowerForm, CaseForm, FollowUpForm, NewLeadForm} from './IntakeForms.jsx';
import {Leads} from './Leads.jsx';

const LOOKUPS = {me: {employee_id: 'e2'}, modes: [], follow_up_statuses: [{code: '4', label: 'Call back'}],
  payers: [{code: 1, label: 'By client'}, {code: 2, label: 'By client customer'}], fee_bases: [{code: 1, label: 'By circular'}, {code: 2, label: 'Fixed amount'}],
  payment_methods: [{code: 1, label: 'By bank'}, {code: 3, label: 'By any other'}], client_types: [], designations: [], divisions: [], subdivisions: [],
  states: [{id: 'mp', name: 'Madhya Pradesh'}], districts: [{id: 'bpl', name: 'Bhopal', state_id: 'mp'}], blocks: [{id: 'huzur', name: 'Huzur', district_id: 'bpl', code: '305'}],
  report_usages: [{id: 'loan', name: 'Loan purpose', subtype_id: 'lb', code: '148'}, {id: 'sale', name: 'Sale purpose', subtype_id: 'lb', code: '70'}],
  scrutiny_documents: [{id: 'deed', name: 'Sale deed', report_usage_id: 'loan', code: '114'}]};
const CATALOG = {services: [{id: 'val', name: 'Valuation of asset'}], subtypes: [{id: 'lb', name: 'L & B', service_id: 'val'}],
                 employees: [{id: 'e1', name: 'Rahul Patidar'}, {id: 'e2', name: 'Vijay Galphate'}]};
const BORROWER = {id: 'b1', name: 'Asha Verma', contact_number: '9826054321', email: '', gst_number: '', property_count: 2, payer: 2, fee_basis: 2,
                  agreed_fee: '7500.000000', payment_reference_name: 'Asha Verma', payment_reference_number: '9826054321', pay_by_date: '2026-10-31', customer_payment_method: 3};
const CASE = {id: 'k1', borrower_id: 'b1', service_id: 'val', subtype_id: 'lb', usage_of_report_code: '148,70', scrutiny_document_code: '114',
              expected_report_date: '2026-10-20', asset_amount: '3850000.00', asset_address: 'Plot 47', asset_state: 'Madhya Pradesh', asset_district: 'Bhopal',
              asset_block_code: '305', asset_pin_code: '462042', remarks: '', contact_person_name: 'Asha Verma', contact_number: '9826054321'};
const LEAD = {id: 'L1', number: 'L-1', office_name: 'State Bank of India', office: 'o1', legacy_status: '2', editable: true, updated_at: 'x',
              contact: {name: 'Poonam Salve', phone: '9826012345'}, office_detail: {state: 'Madhya Pradesh', district: 'Bhopal', block_id: 'huzur'},
              services: [{id: 'rs1', service_id: 'val', subtype_id: 'lb'}], borrowers: [BORROWER], cases: [CASE], follow_ups: [], audit: []};
afterEach(() => vi.restoreAllMocks());

function backend(extra = {}) {
  const calls = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = String(url).replace('/api/', ''), method = options.method || 'GET';
    calls.push({path, method, body: options.body && typeof options.body === 'string' ? JSON.parse(options.body) : null});
    const key = Object.keys(extra).find(k => path.startsWith(k));
    const body = key ? extra[key] : path.startsWith('intake/lookups') ? LOOKUPS : path.startsWith('intake/catalog') ? CATALOG
      : path.startsWith('intake/leads/L1') ? LEAD : path.startsWith('intake/contacts') ? {results: []} : {};
    return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
  });
  return calls;
}
const list = heading => screen.getByText(heading).nextElementSibling;
const field = label => screen.getAllByLabelText(label, {exact: false}).find(el => el.tagName === 'INPUT' && el.type !== 'hidden');

describe('the lead list', () => {
  it('shows parties and cases entered against those declared, marked while short', async () => {
    backend({'leads/': {count: 1, results: [{id: 'L1', number: 'L-1', status_label: 'In process', office: {name: 'SBI'},
      lead_giver: {name: 'Poonam Salve', phone: '9826012345'}, parties: {recorded: 1, declared: 2}, cases: {recorded: 2, declared: 2}}]}});
    renderApp(<Routes><Route path="/leads" element={<Leads/>}/></Routes>, {route: '/leads'});
    const parties = await screen.findByLabelText('1 of 2 parties entered');
    expect(parties.textContent).toBe('1/2');
    expect(screen.getByLabelText('2 of 2 cases entered').textContent).toBe('2/2');
    expect(screen.getByText('Poonam Salve')).toBeTruthy();
  });
});

describe("the lead's page", () => {
  it('edits a customer in a form filled with their current details', async () => {
    const calls = backend();
    renderApp(<IntakeLead api={api} leadId="L1"/>);
    await screen.findByText("Client's customers");
    fireEvent.click(within(list("Client's customers")).getByRole('button', {name: 'Edit'}));
    // The page also shows the empty form for a new customer; look only in the one being edited.
    const form = within((await screen.findByText('Edit Asha Verma')).closest('form'));
    expect(form.getByRole('textbox', {name: 'Work order amount'}).value).toBe('7500');              // fixed fee, kept
    expect(form.getByRole('radio', {name: 'By any other'}).checked).toBe(true);
    fireEvent.change(form.getByRole('textbox', {name: 'Work order amount'}), {target: {value: '8000'}});
    fireEvent.click(form.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => expect(calls.find(c => c.method === 'PATCH')).toBeTruthy());
    const patch = calls.find(c => c.method === 'PATCH');
    expect(patch.path).toBe('intake/leads/L1/borrowers/b1/');
    expect(patch.body).toMatchObject({agreed_fee: '8000', payer: 2, fee_basis: 2, customer_payment_method: 3});
    expect(await form.findByText('Saved.')).toBeTruthy();                                              // the form stays, holding what was saved
    expect(form.getByRole('textbox', {name: 'Work order amount'}).value).toBe('8000');
  });

  it('asks before deleting, and says what happens', async () => {
    const calls = backend();
    renderApp(<IntakeLead api={api} leadId="L1"/>);
    await screen.findByText('Cases');
    fireEvent.click(within(list('Cases')).getByRole('button', {name: 'Delete'}));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/kept in the history, not erased/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', {name: 'Delete'}));
    await waitFor(() => expect(calls.some(c => c.method === 'DELETE' && c.path === 'intake/leads/L1/cases/k1/')).toBe(true));
  });
});

describe('editing a case', () => {
  it('turns its stored codes and place names back into the form’s choices', async () => {
    backend();
    renderApp(<CaseForm lead={LEAD} catalog={CATALOG} initial={CASE} onSave={vi.fn()}/>);
    await screen.findByText('Edit case');
    await waitFor(() => expect(field('City').value).toBe('Huzur'));
    expect(field('State').value).toBe('Madhya Pradesh');
    for (const chosen of ['Loan purpose', 'Sale purpose', 'Sale deed']) {                           // both usages, from "148,70"
      expect(screen.getAllByText(chosen).length).toBeGreaterThan(0);
    }
  });
});

describe('the new lead form', () => {
  it('puts the signed-in person as the one who received the lead', async () => {
    backend();
    renderApp(<Routes><Route path="/leads/new" element={<NewLeadForm/>}/></Routes>, {route: '/leads/new'});
    await screen.findByText('Lead giver information');
    await waitFor(() => expect(field('Lead received by').value).toBe('Vijay Galphate'));
  });
});

describe('the work order page', () => {
  it("shows each customer's payment terms, as the legacy list did", async () => {
    backend({'work-orders/leads/L1/': {ordered: 0, outstanding: 1, closed: false, borrowers: [{id: 'b1', name: 'Asha Verma', contact_number: '9826054321',
      email: 'asha@example.in', cases: 1, declared_cases: 2, payer: 1, fee_basis: 2, agreed_fee: '7500.000000', customer_payment_method: 1,
      eligible: true, reasons: [], work_order: null}]}});
    renderApp(<WorkOrders api={api} leadId="L1"/>);
    const row = (await screen.findByText('Asha Verma')).closest('tr');
    for (const text of ['1/2', 'By client', 'Fixed ₹7,500', 'By bank']) expect(within(row).getByText(text)).toBeTruthy();
    expect(within(row).getByText('9826054321 · asha@example.in')).toBeTruthy();
  });
});

describe('after saving', () => {
  it("keeps a new customer's values, and saving again updates that customer", async () => {
    backend();
    const save = vi.fn().mockResolvedValue({id: 'new-b'}), update = vi.fn().mockResolvedValue({});
    renderApp(<BorrowerForm lead={LEAD} onSave={save} onUpdate={update}/>);
    fireEvent.change(await screen.findByRole('textbox', {name: "Name of client's customer"}), {target: {value: 'Ravi Verma'}});
    fireEvent.change(screen.getByRole('textbox', {name: 'Contact no.'}), {target: {value: '9826054322'}});
    fireEvent.change(screen.getByLabelText(/Pay by date/), {target: {value: '2026-10-31'}});
    fireEvent.click(screen.getByRole('button', {name: "Save client's customer"}));
    expect(await screen.findByText('Saved.')).toBeTruthy();
    expect(screen.getByRole('textbox', {name: "Name of client's customer"}).value).toBe('Ravi Verma');   // previously cleared
    fireEvent.change(screen.getByRole('textbox', {name: 'Contact no.'}), {target: {value: '9826054399'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => expect(update).toHaveBeenCalled());
    expect(update.mock.calls[0][0]).toBe('new-b');                                                  // the same customer, not a second one
    expect(save).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', {name: 'Add another customer'}));
    expect(screen.getByRole('textbox', {name: "Name of client's customer"}).value).toBe('');
  });

  it('keeps a follow-up on screen, and will not save the same one twice', async () => {
    backend();
    const save = vi.fn().mockResolvedValue({id: 'f1'});
    renderApp(<FollowUpForm onSave={save}/>);
    await screen.findByText('Follow up for lead');
    fireEvent.click(field('Follow up status'));
    fireEvent.click(await screen.findByRole('option', {name: 'Call back'}));
    const remark = screen.getByRole('textbox', {name: 'Please specify the remark if any'});
    fireEvent.change(remark, {target: {value: 'After the site visit'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save follow-up'}));
    expect(await screen.findByText(/Saved\. Change anything/)).toBeTruthy();
    expect(remark.value).toBe('After the site visit');                                              // previously cleared
    expect(screen.getByRole('button', {name: 'Save follow-up'}).disabled).toBe(true);
    fireEvent.change(remark, {target: {value: 'Customer asked to call on Monday'}});
    expect(screen.getByRole('button', {name: 'Save follow-up'}).disabled).toBe(false);
  });
});
