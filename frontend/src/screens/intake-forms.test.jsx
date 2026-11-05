import {fireEvent, screen, waitFor, within} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';
import {BorrowerForm, CaseForm, FollowUpForm, NewLeadForm} from './IntakeForms.jsx';

// The legacy intake forms, driven as a person would, against a stand-in backend.
const LOOKUPS = {
  modes: [{code: 1, label: 'Phone'}, {code: 2, label: 'Email'}],
  follow_up_statuses: [{code: '4', label: 'Call back'}, {code: '6', label: 'Meeting has been scheduled'}],
  payers: [{code: 1, label: 'By client'}, {code: 2, label: 'By client customer'}],
  fee_bases: [{code: 1, label: 'By circular'}, {code: 2, label: 'Fixed amount'}],
  payment_methods: [{code: 1, label: 'By bank'}, {code: 2, label: 'By cash'}],
  client_types: [{id: 'ct', name: 'Financial Institution'}], designations: [{id: 'fo', name: 'Field Officer'}],
  divisions: [{id: 'retail', name: 'Retail / PB'}, {id: 'sme', name: 'SME'}],
  subdivisions: [{id: 'pbd', name: 'PBD', division_id: 'retail'}, {id: 'sme1', name: 'SME Hub', division_id: 'sme'}],
  states: [{id: 'mp', name: 'Madhya Pradesh'}], districts: [{id: 'bpl', name: 'Bhopal', state_id: 'mp'}, {id: 'ind', name: 'Indore', state_id: 'mp'}],
  blocks: [{id: 'huzur', name: 'Huzur', district_id: 'bpl', code: '305'}, {id: 'mhow', name: 'Mhow', district_id: 'ind', code: '410'}],
  report_usages: [{id: 'loan', name: 'Loan purpose', subtype_id: 'lb', code: '148'}, {id: 'flatuse', name: 'Flat purpose', subtype_id: 'flat', code: '70'}],
  scrutiny_documents: [{id: 'deed', name: 'Sale deed', report_usage_id: 'loan', code: '114'}, {id: 'nocdoc', name: 'Society NOC', report_usage_id: 'flatuse', code: '9'}],
};
const CATALOG = {services: [{id: 'val', name: 'Valuation of asset'}], subtypes: [{id: 'lb', name: 'L & B', service_id: 'val'}, {id: 'flat', name: 'Flat', service_id: 'val'}],
                 employees: [{id: 'e1', name: 'Rahul Patidar'}, {id: 'e2', name: 'Vijay Galphate'}]};
const OFFICE = {id: 'o1', name: 'State Bank of India', branch: 'Main Branch Hoshangabad', client_type: 'Financial Institution', client_type_id: 'ct',
                address: 'Hoshangabad', ifsc: 'SBIN0000383', gstin: '23AAACS', state: 'Madhya Pradesh', district: 'Bhopal', city: 'Huzur', block_id: 'huzur'};
const POONAM = {id: 'c1', name: 'Poonam Salve', phone: '9826012345', designation: 'Field Officer', division: 'Retail / PB', subdivision: 'PBD', office: OFFICE, leads: 127};
afterEach(() => vi.restoreAllMocks());

function backend(routes = {}) {
  const calls = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = String(url).replace('/api/', ''), method = options.method || 'GET';
    calls.push({path, method, body: options.body ? JSON.parse(options.body) : null});
    const key = Object.keys(routes).find(k => path.startsWith(k));
    const body = key ? (typeof routes[key] === 'function' ? routes[key](path, method) : routes[key])
      : path.startsWith('intake/lookups/') && !path.startsWith('intake/lookups/orderer') ? LOOKUPS
      : path.startsWith('intake/catalog') ? CATALOG : {};
    return new Response(JSON.stringify(body), {status: method === 'POST' ? 201 : 200, headers: {'Content-Type': 'application/json'}});
  });
  return calls;
}
// Mantine's selects label both their input and their option list; this finds the input.
const field = label => screen.getAllByLabelText(label, {exact: false}).find(el => el.tagName === 'INPUT' && el.type !== 'hidden');
async function choose(label, option) {
  fireEvent.click(field(label));
  fireEvent.click(await screen.findByRole('option', {name: option}));
}
const posted = (calls, path) => calls.filter(c => c.method === 'POST' && c.path === path).map(c => c.body);

describe('the new lead form', () => {
  const open = () => renderApp(<Routes><Route path="/leads/new" element={<NewLeadForm/>}/><Route path="/leads/:id" element={<p>Lead page</p>}/></Routes>, {route: '/leads/new'});

  it('fills in a known lead giver from their mobile number and saves with them', async () => {
    const calls = backend({'intake/lookups/orderer': {matches: [POONAM]}, 'intake/leads/': {id: 'L1', number: 'L-1'}});
    open();
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '98260 12345'}});
    const details = await screen.findByLabelText("The orderer's details");
    expect(within(details).getByDisplayValue('Poonam Salve')).toBeTruthy();
    expect(within(details).getByDisplayValue('Main Branch Hoshangabad')).toBeTruthy();
    expect(within(details).getByDisplayValue('Retail / PB / PBD')).toBeTruthy();
    await choose('Mode', 'Phone');
    await choose('Service 1', 'Valuation of asset');
    await choose('Sub service 1', 'L & B');                                 // the sub services are the service's
    fireEvent.change(screen.getByRole('textbox', {name: 'Cases 1'}), {target: {value: '3'}});
    expect(screen.getByText('3')).toBeTruthy();                               // the total adds itself up
    await choose('Lead received by', 'Rahul Patidar');
    await choose('Lead assigned to', 'Vijay Galphate');
    fireEvent.click(screen.getByRole('button', {name: 'Save the lead'}));
    await screen.findByText('Lead page');
    expect(posted(calls, 'intake/leads/')[0]).toMatchObject({contact: 'c1', enquiry_mode: 1, received_by: 'e1', assigned_employee: 'e2',
                                                             services: [{service: 'val', subtype: 'lb', case_count: 3}]});
  });

  it('registers a new lead giver, with the sub-division following the division', async () => {
    const calls = backend({'intake/lookups/orderer': {matches: []}, 'intake/lookups/offices': {results: [OFFICE]}, 'intake/leads/': {id: 'L2'}});
    open();
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '9826077777'}});
    await screen.findByText('No orderer has this number. Register them with the lead.');
    await choose('Client type', 'Financial Institution');
    await choose('Client name', 'State Bank of India, Main Branch Hoshangabad');
    expect(screen.getByDisplayValue('Huzur')).toBeTruthy();                  // the client's city fills in
    await choose('Division', 'SME');
    fireEvent.click(field('Sub division'));
    expect(screen.queryByRole('option', {name: 'PBD'})).toBeNull();          // only the division's sub-divisions
    fireEvent.click(await screen.findByRole('option', {name: 'SME Hub'}));
    fireEvent.change(screen.getByRole('textbox', {name: 'Orderer name'}), {target: {value: 'Anil Rao'}});
    await choose('Orderer designation', 'Field Officer');
    await choose('Mode', 'Email');
    await choose('Service 1', 'Valuation of asset');
    await choose('Lead received by', 'Rahul Patidar');
    await choose('Lead assigned to', 'Rahul Patidar');
    fireEvent.click(screen.getByRole('button', {name: 'Save the lead'}));
    await screen.findByText('Lead page');
    expect(posted(calls, 'intake/leads/')[0].new_contact).toEqual({name: 'Anil Rao', phone: '9826077777', office: 'o1', designation: 'fo',
                                                                   division: 'sme', subdivision: 'sme1'});
  });

  it('adds a branch found only in the bank directory as a client, in one step', async () => {
    const directory = {bank: 'Indian Bank', bank_id: 'b9', branch: 'JHAJJAR', address: 'Rohtak Road', city: 'JHAJJAR', district: 'JHAJJAR', state: 'HARYANA', ifsc: 'IDIB000J031'};
    let added = false;
    const calls = backend({'intake/lookups/orderer': {matches: []}, 'intake/lookups/offices': {results: []},
      'intake/lookups/ifsc': () => (added ? {offices: [{...OFFICE, id: 'new', name: 'Indian Bank', branch: 'JHAJJAR'}], directory} : {offices: [], directory}),
      'intake/offices/': () => { added = true; return {id: 'new'}; }});
    open();
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '9826077777'}});
    await screen.findByText('No orderer has this number. Register them with the lead.');
    await choose('Client type', 'Financial Institution');
    fireEvent.change(screen.getByRole('textbox', {name: 'IFSC code'}), {target: {value: 'idib000j031'}});
    fireEvent.click(screen.getByRole('button', {name: 'Find'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Add this branch as a client'}));
    await waitFor(() => expect(posted(calls, 'intake/offices/')[0]).toMatchObject({name: 'Indian Bank', branch_name: 'JHAJJAR', bank: 'b9', ifsc: 'IDIB000J031', client_type: 'ct'}));
    expect(await screen.findByDisplayValue('JHAJJAR')).toBeTruthy();
  });
});

const LEAD = {id: 'L1', office_name: 'State Bank of India', office_detail: OFFICE, contact: {name: 'Poonam Salve', phone: '9826012345'},
              services: [{id: 'rs1', service_id: 'val', subtype_id: 'lb'}], borrowers: [{id: 'b1', name: 'Asha Verma', contact_number: '9826054321'}]};

describe("the client's customer form", () => {
  it('fills in the payer and payment responsibility when the bank pays, and asks for a fixed fee', async () => {
    backend();
    const save = vi.fn().mockResolvedValue({});
    renderApp(<BorrowerForm lead={LEAD} onSave={save}/>);
    expect(await screen.findByDisplayValue('State Bank of India, Main Branch Hoshangabad')).toBeTruthy();   // the payer
    expect(screen.getByRole('textbox', {name: 'Client payment responsible name'}).value).toBe('Poonam Salve');
    expect(screen.queryByRole('textbox', {name: 'Work order amount'})).toBeNull();                          // by circular
    fireEvent.click(screen.getByRole('radio', {name: 'Fixed amount'}));
    fireEvent.change(screen.getByRole('textbox', {name: 'Work order amount'}), {target: {value: '5000'}});
    fireEvent.change(screen.getByRole('textbox', {name: "Name of client's customer"}), {target: {value: 'Asha Verma'}});
    fireEvent.change(screen.getByRole('textbox', {name: 'Contact no.'}), {target: {value: '9826054321'}});
    fireEvent.change(screen.getByLabelText(/Pay by date/), {target: {value: '2026-10-31'}});
    fireEvent.click(screen.getByRole('button', {name: "Save client's customer"}));
    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(save.mock.calls[0][0]).toMatchObject({payer: 1, fee_basis: 2, agreed_fee: '5000', customer_payment_method: 1, property_count: 1,
                                                 payment_reference_name: 'Poonam Salve', payment_reference_number: '9826012345'});
  });
});

describe('the case form', () => {
  it('narrows each choice by the one before, and fills in the place and contact', async () => {
    backend();
    const save = vi.fn().mockResolvedValue({});
    renderApp(<CaseForm lead={LEAD} catalog={CATALOG} onSave={save}/>);
    await screen.findByText('Cases detail');
    expect(field('City').value).toBe('Huzur');                                  // the branch's place
    await choose("Client's customer name", 'Asha Verma');
    expect(screen.getByRole('textbox', {name: 'Contact person name'}).value).toBe('Asha Verma');            // the customer
    fireEvent.click(field('Usage of report'));
    expect(screen.queryByRole('option', {name: 'Flat purpose'})).toBeNull();                                 // only L & B usages
    fireEvent.click(await screen.findByRole('option', {name: 'Loan purpose'}));
    fireEvent.click(field('Scrutiny documents'));
    expect(screen.queryByRole('option', {name: 'Society NOC'})).toBeNull();                                  // only the usage's documents
    fireEvent.click(await screen.findByRole('option', {name: 'Sale deed'}));
    fireEvent.change(screen.getByLabelText(/Expected date of report/), {target: {value: '2026-10-20'}});
    fireEvent.change(screen.getByRole('textbox', {name: 'Output amount'}), {target: {value: '3850000'}});
    fireEvent.change(screen.getByRole('textbox', {name: 'Property address'}), {target: {value: 'Plot 47'}});
    fireEvent.change(screen.getByRole('textbox', {name: 'PIN (optional)'}), {target: {value: '462042'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save case'}));
    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(save.mock.calls[0][0]).toMatchObject({borrower: 'b1', service: 'val', subtype: 'lb', report_usages: ['loan'], scrutiny_documents: ['deed'],
                                                 state: 'mp', district: 'bpl', block: 'huzur', asset_pin_code: '462042'});
  });
});

describe('the follow-up form', () => {
  it('sends the legacy status and the call-back time', async () => {
    backend();
    const save = vi.fn().mockResolvedValue({});
    renderApp(<FollowUpForm onSave={save}/>);
    await screen.findByText('Follow up for lead');
    await choose('Follow up status', 'Call back');
    fireEvent.change(screen.getByRole('textbox', {name: 'Please specify the remark if any'}), {target: {value: 'After the site visit'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save follow-up'}));
    await waitFor(() => expect(save).toHaveBeenCalled());
    expect(save.mock.calls[0][0]).toMatchObject({status: '4', notify_time: '10:00', remark: 'After the site visit'});
  });
});

describe("a bank's own form", () => {
  const SUBTYPES = [...CATALOG.subtypes, {id: 'sbin', name: 'L & B ( SBIN)', service_id: 'val'}, {id: 'cnrb', name: 'L & B ( CNRB)', service_id: 'val'}];

  it("is chosen for that bank's leads, and another bank's is not offered", async () => {
    backend({'intake/lookups/orderer': {matches: [POONAM]}, 'intake/catalog': {...CATALOG, subtypes: SUBTYPES}});
    renderApp(<Routes><Route path="/leads/new" element={<NewLeadForm/>}/></Routes>, {route: '/leads/new'});
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '9826012345'}});    // an SBI branch
    await screen.findByLabelText("The orderer's details");
    await choose('Service 1', 'Valuation of asset');
    expect(field('Sub service 1').value).toBe('L & B ( SBIN)');
    expect(screen.getByText("SBIN's own form is chosen; the general form is also allowed.")).toBeTruthy();
    fireEvent.click(field('Sub service 1'));
    expect(screen.getByRole('option', {name: 'L & B'})).toBeTruthy();
    expect(screen.queryByRole('option', {name: 'L & B ( CNRB)'})).toBeNull();
  });
});

describe('client review 2026-11-05', () => {
  const TYPES = [{id: 'corp', name: 'Corporate'}, {id: 'ct', name: 'Financial Institution'}, {id: 'ind', name: 'Individual'}];
  const open = () => renderApp(<Routes><Route path="/leads/new" element={<NewLeadForm/>}/></Routes>, {route: '/leads/new'});

  it('asks for an IFSC only for a financial institution, and adds a client on the form itself', async () => {
    let created = false;
    const calls = backend({'intake/lookups/orderer': {matches: []},
      'intake/lookups/offices': () => ({results: created ? [{...OFFICE, id: 'acme', name: 'Acme Ltd', branch: '', client_type: 'Corporate', ifsc: '', gstin: '23ABCDE1234F1Z5'}] : []}),
      'intake/lookups/': {...LOOKUPS, client_types: TYPES}, 'intake/offices/': () => { created = true; return {id: 'acme'}; }});
    open();
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '9826077777'}});
    await screen.findByText('No orderer has this number. Register them with the lead.');
    await choose('Client type', 'Financial Institution');
    expect(screen.getByRole('textbox', {name: 'IFSC code'})).toBeTruthy();
    await choose('Client type', 'Corporate');
    expect(screen.queryByRole('textbox', {name: 'IFSC code'})).toBeNull();
    fireEvent.click(screen.getByRole('button', {name: 'New client'}));
    const panel = await screen.findByLabelText('New client');
    expect(within(panel).queryByRole('textbox', {name: 'IFSC code'})).toBeNull();
    fireEvent.change(within(panel).getByRole('textbox', {name: 'Client name'}), {target: {value: 'Acme Ltd'}});
    fireEvent.change(within(panel).getByRole('textbox', {name: 'Address'}), {target: {value: 'MP Nagar'}});
    fireEvent.change(within(panel).getByRole('textbox', {name: 'GST no.'}), {target: {value: '23abcde1234f1z5'}});
    fireEvent.click(within(panel).getByRole('button', {name: 'Save client'}));
    await waitFor(() => expect(posted(calls, 'intake/offices/')[0]).toMatchObject({name: 'Acme Ltd', address: 'MP Nagar', client_type: 'corp', gstin: '23ABCDE1234F1Z5', ifsc: ''}));
    await waitFor(() => expect(field('Client name').value).toBe('Acme Ltd'));
    expect(screen.queryByLabelText('New client')).toBeNull();
  });

  it('records who contacted us apart from the orderer', async () => {
    const calls = backend({'intake/lookups/orderer': {matches: [POONAM]}, 'intake/leads/': {id: 'L9'}});
    open();
    fireEvent.change(await screen.findByLabelText(/Orderer mobile no/), {target: {value: '9826012345'}});
    await screen.findByLabelText("The orderer's details");
    await choose('Mode', 'Phone');
    await choose('Service 1', 'Valuation of asset');
    await choose('Lead received by', 'Vijay Galphate');
    await choose('Lead assigned to', 'Rahul Patidar');
    const section = screen.getByText('Contacted by (optional)').closest('div');
    fireEvent.change(within(section).getByRole('textbox', {name: 'Name'}), {target: {value: 'Ravi'}});
    fireEvent.change(within(section).getByRole('textbox', {name: 'Mobile no.'}), {target: {value: '9826011111'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save the lead'}));
    await waitFor(() => expect(posted(calls, 'intake/leads/')[0]).toMatchObject({contact: 'c1', contacted_by_name: 'Ravi', contacted_by_phone: '9826011111'}));
  });

  it('edits a saved lead on the same form, filled with what was entered', async () => {
    const SAVED = {id: 'L1', number: 'L-1', editable: true, enquiry_mode: 2, orderer: POONAM, contacted_by_name: 'Ravi', contacted_by_phone: '', contacted_by_remark: '',
                   services: [{id: 'rs1', service_id: 'val', subtype_id: 'lb', case_count: 3}], party_count: 2, received_by: 'e2', assigned_employee: 'e1',
                   received_date: '2026-11-01'};
    const calls = backend({'intake/lookups/orderer': {matches: [POONAM]}, 'intake/leads/L1/': SAVED});
    renderApp(<Routes><Route path="/leads/:id/edit" element={<NewLeadForm/>}/><Route path="/leads/:id" element={<p>Lead page</p>}/></Routes>, {route: '/leads/L1/edit'});
    await screen.findByText('Edit lead L-1');
    expect(screen.getByRole('textbox', {name: /Orderer mobile no/}).value).toBe('9826012345');
    await screen.findByLabelText("The orderer's details");
    expect(field('Mode').value).toBe('Email');
    expect(screen.getByRole('textbox', {name: 'Cases 1'}).value).toBe('3');
    fireEvent.change(screen.getByRole('textbox', {name: 'Cases 1'}), {target: {value: '4'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => expect(calls.find(c => c.method === 'PATCH')?.body).toMatchObject(
      {enquiry_mode: 2, contacted_by_name: 'Ravi', services: [{id: 'rs1', service: 'val', subtype: 'lb', case_count: 4}], received_date: '2026-11-01'}));
    expect(calls.find(c => c.method === 'PATCH').body.contact).toBeUndefined();     // the same orderer is not sent again
    await screen.findByText('Lead page');
  });
});
