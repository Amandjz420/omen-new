import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {renderApp} from './test/render.jsx';
import {api} from './lib/api.js';
import {Invoice} from './invoices.jsx';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const INVOICE = {id: 'i1', number: 'I-1', cancelled: false, remaining: '5000', total: '5000', paid: '0', bad_debt: '0', lines: [], payments: [], credit_notes: [],
  references: {lead: 'L-1', report: 'R-1'}, billed_to: {name: 'State Bank of India', branch: 'Itarsi', customer: false}, place_of_supply: '23-Madhya Pradesh',
  document: {available: true}, issued_on: '2026-10-01', due_on: null, advance: '0', excess: '0', offline: false, borrower: 'Asha Verma',
  report_number: 'R-1', payment_status: '', recorded_remaining: '5000', recorded_excess: '0', bad_debt_remark: '', number_shared: false, follow_ups: [{id: 'f1', call_status: '4', remark: 'First call', logged_date_text: '2026-10-15 00:00:00', logged_time_text: '11:30'}]};

describe("an invoice's recovery follow-ups", () => {
  it('lists earlier calls and records a new one', async () => {
    const calls = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
      const path = String(url).replace('/api/', ''), method = options.method || 'GET';
      calls.push({path, method, body: options.body ? JSON.parse(options.body) : null});
      const body = path.startsWith('intake/lookups') ? {follow_up_statuses: [{code: '4', label: 'Call back'}, {code: '6', label: 'Meeting has been scheduled'}]}
        : path === 'invoices/i1/follow-ups/' ? {follow_ups: [{id: 'f2', call_status: '6', remark: 'Meeting fixed', logged_date_text: '2026-10-20', logged_time_text: '10:00'}, ...INVOICE.follow_ups]}
        : path === 'invoices/i1/' ? INVOICE : {};
      return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
    });
    renderApp(<Invoice api={api} id="i1" onBack={() => {}}/>);
    expect(await screen.findByText(/call back 2026-10-15 11:30 · First call/)).toBeTruthy();
    const status = (await screen.findAllByLabelText('Follow up status', {exact: false})).find(el => el.tagName === 'INPUT' && el.type !== 'hidden');
    fireEvent.click(status);
    fireEvent.click(await screen.findByRole('option', {name: 'Meeting has been scheduled'}));
    fireEvent.change(screen.getByRole('textbox', {name: 'Please specify the remark if any'}), {target: {value: 'Meeting fixed'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save follow-up'}));
    expect(await screen.findByText(/Meeting fixed/, {selector: 'li'})).toBeTruthy();
    expect(calls.find(c => c.method === 'POST' && c.path === 'invoices/i1/follow-ups/').body).toMatchObject({status: '6', remark: 'Meeting fixed'});
  });

  it('opens on a page without crypto.randomUUID, as on a phone over plain http', async () => {
    vi.stubGlobal('crypto', {getRandomValues: a => globalThis.Array.from(a, () => 7) && a});
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => new Response(JSON.stringify(String(url).includes('invoices/i1/') ? INVOICE : {}),
      {status: 200, headers: {'Content-Type': 'application/json'}}));
    renderApp(<Invoice api={api} id="i1" onBack={() => {}}/>);
    await waitFor(() => expect(screen.getByText(/First call/)).toBeTruthy());              // previously: crypto.randomUUID is not a function
  });
});
