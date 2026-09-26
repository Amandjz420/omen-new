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
