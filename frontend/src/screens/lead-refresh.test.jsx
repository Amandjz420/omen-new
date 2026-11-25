import {fireEvent, screen, waitFor, within} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';
import {LeadDetail} from './Leads.jsx';

// Review BF5: issuing the last borrower's work order on a lead page left the page's
// header and stage track stale. The real WorkOrders component is used.
const L = '3f1c2a9e-5b7d-4e21-9c3a-6d8e0f1a2b3c';
afterEach(() => vi.restoreAllMocks());

function backend() {
  let issued = false;
  const calls = {lead: 0, stages: 0};
  const stage = (label, state) => ({key: label, label, state, detail: ''});
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = String(url).replace('/api/', '');
    let body;
    if (path === 'work-orders/' && options.method === 'POST') { issued = true; body = {id: 'w1', number: 'ORDER-1'}; }
    else if (path.startsWith(`work-orders/leads/${L}/`)) {
      body = {ordered: issued ? 1 : 0, outstanding: issued ? 0 : 1, closed: issued,
              borrowers: [{id: 'b1', name: 'Asha Verma', cases: 1, eligible: !issued, can_issue: !issued, reasons: [],
                           work_order: issued ? {id: 'w1', number: 'ORDER-1', origin: 'local'} : null}]};
    } else if (path.startsWith(`leads/${L}/stages/`)) {
      calls.stages += 1;
      body = {cases: [{id: 'c1', borrower: 'Asha Verma', service: 'Valuation', stages: [stage('Intake', 'done'), stage('Work order', issued ? 'done' : 'current'), stage('Valuation', issued ? 'current' : 'waiting')]}]};
    } else if (path.startsWith(`leads/${L}/`)) {
      calls.lead += 1;
      body = {id: L, number: 'L-0926271001', status_label: issued ? 'Closed' : 'In process', date_basis: 'actual_intake',
              received_date: '2026-09-26', office: {name: 'State Bank of India'}, contact: null, issues: [], notes: [], cases: []};
    } else if (path.startsWith('intake/')) {
      // The carried-over intake panel reads these fields; missing ones crash it, and with it the page.
      body = path.startsWith('intake/catalog')
        ? {services: [], subtypes: [], employees: [], banks: [], client_types: [], designations: []}
        : {id: L, number: 'L-0926271001', legacy_status: issued ? '4' : '2', editable: true, received_date: '2026-09-26',
           office: null, office_name: 'State Bank of India', assigned_employee: null, contact: '', updated_at: '2026-09-26T10:00:00Z',
           borrowers: [], services: [], cases: [], follow_ups: [], audit: []};
    } else body = {};
    return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
  });
  return calls;
}

describe('the lead page after a change inside it', () => {
  it('refreshes its header and stage track when a work order is issued', async () => {
    const calls = backend();
    renderApp(<Routes><Route path="/leads/:id" element={<LeadDetail/>}/></Routes>, {route: `/leads/${L}`});
    expect(await screen.findByText('In process')).toBeTruthy();
    const track = await screen.findByRole('list', {name: 'Stages for Asha Verma'});
    expect(within(track).getAllByRole('listitem')[1].getAttribute('aria-current')).toBe('step');       // work order current

    fireEvent.click(await screen.findByRole('tab', {name: /Work orders/}));                              // orders sit in their own tab
    fireEvent.click(await screen.findByRole('button', {name: 'Issue work order'}));
    expect(await screen.findByText('ORDER-1')).toBeTruthy();                                             // the panel itself

    await waitFor(() => expect(screen.getByText('Closed')).toBeTruthy());                               // the header: previously stale
    await waitFor(() => {
      const items = within(screen.getByRole('list', {name: 'Stages for Asha Verma'})).getAllByRole('listitem');
      expect(items[1].getAttribute('data-state')).toBe('done');                                          // the track: previously stale
      expect(items[2].getAttribute('aria-current')).toBe('step');
    });
    expect(calls.lead).toBeGreaterThan(1);
    expect(calls.stages).toBeGreaterThan(1);
  });
});

// Client review 2026-11-25: a new lead waits unassigned until someone picks it up.
describe('picking up a lead', () => {
  it('assigns it to the person who picks it up, and a manager can reassign it', async () => {
    let assigned = null;
    const posts = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
      const path = String(url).replace('/api/', ''), method = options.method || 'GET';
      if (method === 'POST') posts.push({path, body: JSON.parse(options.body || '{}')});
      let body = {};
      if (path === `intake/leads/${L}/pick-up/`) { assigned = {id: 'e2', name: 'Vijay Galphate'}; body = {}; }
      else if (path === `intake/leads/${L}/reassign/`) { assigned = {id: 'e1', name: 'Rahul Patidar'}; body = {}; }
      else if (path.startsWith(`leads/${L}/stages/`)) body = {cases: []};
      else if (path.startsWith('work-orders/')) body = {ordered: 0, outstanding: 0, closed: false, borrowers: []};
      else if (path.startsWith(`leads/${L}/`)) {
        body = {id: L, number: 'L-1125261001', status_label: assigned ? 'In process' : 'New lead', date_basis: 'actual_intake', received_date: '2026-11-25',
                office: {name: 'State Bank of India'}, contact: null, issues: [], notes: [], cases: [], received_by: 'Rahul Patidar',
                assigned_to: assigned, can_pick_up: !assigned, can_reassign: true};
      } else if (path.startsWith('intake/catalog')) {
        body = {services: [], subtypes: [], employees: [{id: 'e1', name: 'Rahul Patidar'}, {id: 'e2', name: 'Vijay Galphate'}], banks: [], client_types: [], designations: []};
      } else if (path.startsWith('intake/')) {
        body = {id: L, number: 'L-1125261001', legacy_status: '1', editable: true, received_date: '2026-11-25', office: null, office_name: 'State Bank of India',
                assigned_employee: null, contact: '', updated_at: '2026-11-25T10:00:00Z', borrowers: [], services: [], cases: [], follow_ups: [], audit: []};
      }
      return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
    });
    renderApp(<Routes><Route path="/leads/:id" element={<LeadDetail/>}/></Routes>, {route: `/leads/${L}`});
    const box = await screen.findByLabelText('Assignment');
    expect(box.textContent).toContain('Assigned to nobody yet');
    fireEvent.click(within(box).getByRole('button', {name: 'Pick up this lead'}));
    await waitFor(() => expect(screen.getByLabelText('Assignment').textContent).toContain('Assigned to Vijay Galphate'));
    expect(posts[0].path).toBe(`intake/leads/${L}/pick-up/`);
    expect(screen.queryByRole('button', {name: 'Pick up this lead'})).toBeNull();

    fireEvent.click(screen.getAllByLabelText('Reassign to').find(el => el.tagName === 'INPUT' && el.type !== 'hidden'));
    fireEvent.click(await screen.findByRole('option', {name: 'Rahul Patidar'}));
    fireEvent.click(within(screen.getByLabelText('Assignment')).getByRole('button', {name: 'Reassign'}));
    await waitFor(() => expect(posts.some(p => p.path === `intake/leads/${L}/reassign/` && p.body.employee === 'e1')).toBe(true));
  });
});
