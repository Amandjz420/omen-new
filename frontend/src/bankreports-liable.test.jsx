import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {renderApp} from './test/render.jsx';
import {api} from './lib/api.js';
import {ReportForm} from './bankreports.jsx';

afterEach(() => vi.restoreAllMocks());
const REPORT = {report_number: 'R-1', bank_client: false, blockers: [], values: {}, template: {lines: 3},
                report: {id: 'r1', revision: 0, document: {available: true}, liable: {id: 'e1', name: 'Rahul Patidar'}}, superseded: []};

describe('the liable assessor', () => {
  it('is shown on the report and changed with a reason', async () => {
    const calls = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
      const path = String(url).replace('/api/', ''), method = options.method || 'GET';
      calls.push({path, method, body: options.body ? JSON.parse(options.body) : null});
      const body = path.startsWith('bank-reports/?') ? {count: 1, page: 1, pages: 1, results: [{id: 'v1', report_number: 'R-1', lead_number: 'L-1', borrower: 'Asha Verma', service: 'L & B', submitted_on: '2026-10-10'}]}
        : path.endsWith('/liable/') ? {...REPORT, report: {...REPORT.report, liable: {id: 'e2', name: 'Vijay Galphate'}}}
        : path.startsWith('intake/catalog') ? {employees: [{id: 'e1', name: 'Rahul Patidar'}, {id: 'e2', name: 'Vijay Galphate'}]}
        : path.startsWith('bank-reports/v1') ? REPORT : {};
      return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
    });
    renderApp(<ReportForm api={api} id="v1" onBack={() => {}}/>);
    expect(await screen.findByText('Rahul Patidar')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', {name: 'Change'}));
    const select = await screen.findByLabelText(/New liable assessor/);
    await waitFor(() => expect(select.querySelectorAll('option').length).toBe(2));        // not the current one
    fireEvent.change(select, {target: {value: 'e2'}});
    expect(screen.getByRole('button', {name: 'Save'}).disabled).toBe(true);                 // a reason is needed
    fireEvent.change(screen.getByLabelText(/Reason/), {target: {value: 'Branch reassigned'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save'}));
    expect(await screen.findByText('Vijay Galphate')).toBeTruthy();
    expect(calls.find(c => c.path === 'bank-reports/v1/liable/').body).toEqual({employee: 'e2', reason: 'Branch reassigned'});
  });
});
