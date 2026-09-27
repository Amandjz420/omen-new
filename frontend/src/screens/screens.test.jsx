import {screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {SessionProvider} from '../app/session.jsx';
import {Shell} from '../app/Shell.jsx';
import {renderApp} from '../test/render.jsx';
import {Gate} from './Gate.jsx';

const respond = (routes) => vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
  const key = Object.keys(routes).find(k => String(url).includes(k));
  return new Response(JSON.stringify(routes[key] ?? {}), {status: key ? 200 : 404, headers: {'Content-Type': 'application/json'}});
});
afterEach(() => vi.restoreAllMocks());
const app = ui => renderApp(<SessionProvider><Gate>{ui}</Gate></SessionProvider>);

describe('the sign-in gate', () => {
  it('asks a signed-out person to sign in', async () => {
    respond({'session/': {username: null}});
    app(<p>workspace</p>);
    expect(await screen.findByRole('heading', {name: 'Sign in'})).toBeTruthy();
    expect(screen.queryByText('workspace')).toBeNull();
  });
  it('holds a person with a temporary password until they choose their own', async () => {
    respond({'session/': {username: 'asha', staff: true, password_change_required: true}});
    app(<p>workspace</p>);
    expect(await screen.findByRole('heading', {name: 'Choose your password'})).toBeTruthy();
  });
  it('tells a person without access to ask for a role', async () => {
    respond({'session/': {username: 'asha', staff: false}});
    app(<p>workspace</p>);
    expect(await screen.findByText(/no workspace access yet/)).toBeTruthy();
  });
  it('opens the workspace for a signed-in member of staff, with every workspace in the menu', async () => {
    respond({'session/': {username: 'asha', staff: true}});
    app(<Shell/>);
    await waitFor(() => expect(screen.getByRole('navigation', {name: 'Main'})).toBeTruthy());
    for (const name of ['My work', 'Leads', 'Valuations', 'Verification', 'Invoices', 'Receipts', 'Dispatch']) {
      expect(screen.getAllByRole('link', {name}).length).toBeGreaterThan(0);
    }
  });
});

describe('reports', () => {
  const REPORT = {key: 'outstanding', number: '3', title: 'Outstanding', section: 'Recovery', description: 'Money still owed.',
    date_label: 'Invoice date', groupings: [{key: 'client', label: 'Client'}, {key: 'area', label: 'Area'}], default_group: 'client',
    measures: [{key: 'invoices', label: 'Invoices', kind: 'count'}, {key: 'outstanding', label: 'Outstanding', kind: 'money'}],
    columns: [{key: 'invoice', label: 'Invoice', kind: 'text'}, {key: 'outstanding', label: 'Outstanding', kind: 'money'}],
    group: 'client', group_label: 'Client', totals: {invoices: 3, outstanding: '1238879.00'},
    groups: [{key: 'a', label: 'State Bank of India, Itarsi', values: {invoices: 2, outstanding: '850000.00'}},
             {key: 'b', label: 'Punjab National Bank', values: {invoices: 1, outstanding: '388879.00'}}]};

  it('shows the totals in rupees with Indian grouping, and offers every grouping', async () => {
    respond({'mis/outstanding/': REPORT});
    const {ReportView} = await import('./Reports.jsx');
    const {Route, Routes} = await import('react-router');
    renderApp(<Routes><Route path="/reports/:key" element={<ReportView/>}/></Routes>, {route: '/reports/outstanding'});
    expect(await screen.findByRole('heading', {name: 'Outstanding'})).toBeTruthy();
    expect(screen.getAllByText('₹12,38,879.00').length).toBeGreaterThan(0);
    const grouping = screen.getAllByLabelText('Group by').find(el => el.tagName === 'INPUT' && el.type !== 'hidden');
    expect(grouping.value).toBe('Client');                                 // the current grouping, with the others offered
    expect(screen.getByRole('link', {name: 'Export to Excel'}).getAttribute('href')).toBe('/api/mis/outstanding/export/?');
  });
});
