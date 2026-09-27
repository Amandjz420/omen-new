import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {SessionProvider} from '../app/session.jsx';
import {renderApp} from '../test/render.jsx';
import {Gate} from './Gate.jsx';
import {Home} from './Home.jsx';

// Review BF4: failures on My work must be visible, not read as an empty workload.
const QUEUES = {'valuations/?status=not_started': {total: 42}, 'valuations/?status=Pending': {total: 17}, 'valuations/?status=Revert': {total: 5},
  'verifications/': {counts: {legal: 1, technical: 1, social: 1, general: 1}}, 'bank-reports/': {counts: {pending: 11}},
  'approvals/': {counts: {pending: 8}}, 'invoices/?state=unpaid': {counts: {unpaid: 249}}, 'invoices/': {counts: {to_invoice: 14}},
  'receipts/': {counts: {to_check: 26, to_verify: 22}}, 'dispatch/awaiting/': {total: 65}};
afterEach(() => vi.restoreAllMocks());

function serve(status = () => 200) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
    const path = String(url).replace('/api/', '');
    if (path === 'session/') return new Response(JSON.stringify({username: 'asha', staff: true}), {status: 200});
    const key = Object.keys(QUEUES).sort((a, b) => b.length - a.length).find(k => path.startsWith(k.split('?')[0]) && (!k.includes('?') || path.includes(k.split('?')[1])));
    const code = status(key);
    return new Response(JSON.stringify(code === 200 ? QUEUES[key] : {error: 'failed'}), {status: code, headers: {'Content-Type': 'application/json'}});
  });
}
const home = () => renderApp(<SessionProvider><Gate><Home/></Gate></SessionProvider>);

describe('My work when requests fail', () => {
  it('keeps every queue in view and says so when all of them fail', async () => {
    serve(() => 500);
    home();
    expect(await screen.findByText('The queues could not be loaded')).toBeTruthy();
    expect(screen.getAllByRole('button', {name: /unavailable, try again/}).length).toBe(10);        // previously: only a header
  });

  it('marks only the queue that failed, and retries it', async () => {
    let broken = true;
    serve(key => (key === 'receipts/' && broken ? 500 : 200));
    home();
    const retry = await screen.findByRole('button', {name: 'Receipts to check or verify: unavailable, try again'});
    expect(screen.getByText('42')).toBeTruthy();                                                   // the others still count
    expect(screen.getByRole('alert').textContent).toContain('Receipts to check or verify');
    broken = false;
    fireEvent.click(retry);
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
    expect(screen.getByRole('row', {name: /Receipts to check or verify/}).textContent).toContain('48');   // table row, not the track
  });

  it('leaves out a queue the person may not open', async () => {
    serve(key => (key === 'dispatch/awaiting/' ? 404 : 200));
    home();
    await screen.findByText('42');
    expect(screen.queryByRole('link', {name: 'Approved reports not yet sent'})).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('returns the person to sign-in when their session has ended', async () => {
    serve(() => 401);
    home();
    expect(await screen.findByRole('heading', {name: 'Sign in'})).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('Your session has ended');
  });
});
