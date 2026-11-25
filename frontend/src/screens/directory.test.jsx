import {fireEvent, screen, waitFor, within} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';
import {Directory} from './Directory.jsx';

// Client review 2026-11-25: organisations as a bank -> branch -> client tree.
const GROUPS = {groups: [
  {key: 'bank:sbi', name: 'State Bank of India', kind: 'bank', branches: 412, clients: 980, leads: 5000, last_lead: '2026-11-20'},
  {key: 'type:Corporate', name: 'Corporate', kind: 'type', branches: 26, clients: 30, leads: 40, last_lead: '2026-10-01'}],
  totals: {organisations: 438, clients: 1010},
  filters: {types: ['Corporate', 'Financial Institution', 'Individual'], banks: [{value: 'bank:sbi', label: 'State Bank of India'}],
            states: [{name: 'Madhya Pradesh', districts: ['Bhopal', 'Hoshangabad']}]}};
const BRANCH = {id: 'o1', name: 'State Bank of India', branch: 'Hoshangabad', ifsc: 'SBIN0000383', district: 'Hoshangabad', state: 'Madhya Pradesh',
                address: 'Main road', gstin: '', pan: '', type: 'Financial Institution', group: 'bank:sbi', group_name: 'State Bank of India',
                clients: 1, leads: 127, last_lead: '2026-11-20'};
const CLIENTS = {results: [{id: 'c1', name: 'Poonam Salve', phone: '9826012345', alternate_phone: '', designation: 'Field Officer', designation_id: 'fo',
                            office: 'o1', office_name: 'State Bank of India, Hoshangabad', leads: 127, last_lead: '2026-11-20'}]};
afterEach(() => vi.restoreAllMocks());

function backend() {
  const calls = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = String(url).replace('/api/', ''), method = options.method || 'GET';
    calls.push({path, method, body: options.body ? JSON.parse(options.body) : null});
    const body = path.startsWith('directory/groups') ? GROUPS
      : path.startsWith('directory/branches') ? {count: 1, page: 1, page_size: 25, results: [BRANCH]}
      : path.startsWith('directory/clients') ? CLIENTS
      : path.startsWith('directory/search') ? {branches: [], branch_count: 0, clients: CLIENTS.results}
      : path.startsWith('intake/offices/o1') ? {id: 'o1', name: 'State Bank of India', branch_name: 'Hoshangabad', address: 'Main road'}
      : path.startsWith('intake/lookups') ? {designations: [{id: 'fo', name: 'Field Officer'}], client_types: []} : {};
    return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
  });
  return calls;
}
const open = (route = '/leads/clients') => renderApp(<Routes><Route path="/leads/clients" element={<Directory/>}/></Routes>, {route});

describe('organisations and clients', () => {
  it('lists banks, then a bank’s branches, then a branch’s clients', async () => {
    const calls = backend();
    open();
    expect(await screen.findByText('438 organisations · 1,010 clients')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', {name: 'State Bank of India'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Clients at State Bank of India, Hoshangabad'}));
    const panel = await screen.findByLabelText('Organisation State Bank of India, Hoshangabad');
    expect(await within(panel).findByText('Poonam Salve')).toBeTruthy();
    expect(calls.some(c => c.path.startsWith('directory/branches/?') && c.path.includes('group=bank%3Asbi'))).toBe(true);
  });

  it('sends the filters to the server', async () => {
    const calls = backend();
    open('/leads/clients?type=Corporate&active=6&state=Madhya+Pradesh&district=Bhopal');
    await screen.findByText('438 organisations · 1,010 clients');
    const groups = calls.find(c => c.path.startsWith('directory/groups')).path;
    for (const part of ['type=Corporate', 'active=6', 'state=Madhya+Pradesh', 'district=Bhopal']) expect(groups).toContain(part);
  });

  it('searches clients by mobile, and edits one', async () => {
    const calls = backend();
    open('/leads/clients?q=9826012345');
    expect(await screen.findByText('Poonam Salve')).toBeTruthy();
    expect(calls.some(c => c.path.startsWith('directory/search/?') && c.path.includes('q=9826012345'))).toBe(true);
    fireEvent.click(screen.getByRole('button', {name: 'Open organisation'}));
    const panel = await screen.findByLabelText('Organisation State Bank of India, Hoshangabad');
    fireEvent.click(await within(panel).findByRole('button', {name: 'Edit'}));
    fireEvent.change(within(panel).getByRole('textbox', {name: 'Mobile no.'}), {target: {value: '9826099999'}});
    fireEvent.click(within(panel).getByRole('button', {name: 'Save client'}));
    await waitFor(() => expect(calls.find(c => c.method === 'PATCH')).toMatchObject(
      {path: 'intake/contacts/c1/', body: {name: 'Poonam Salve', phone: '9826099999', office: 'o1', designation: 'fo'}}));
  });
});
