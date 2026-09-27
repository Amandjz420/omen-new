import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';

// Review BF5, intake half: a save in the intake panel must refresh the page around it.
// The panel is replaced by one that reports a save exactly as IntakeLead does, through onChange.
vi.mock('../intake.jsx', () => ({
  IntakeLead: ({onChange}) => <button type="button" onClick={() => onChange?.()}>Save intake change</button>,
  default: () => null,
}));

const L = '3f1c2a9e-5b7d-4e21-9c3a-6d8e0f1a2b3c';
afterEach(() => vi.restoreAllMocks());

describe('the lead page after an intake change', () => {
  it('refetches the lead and its stages', async () => {
    let saved = false;
    const counts = {lead: 0, stages: 0};
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
      const path = String(url).replace('/api/', '');
      let body = {};
      if (path.startsWith(`leads/${L}/stages/`)) { counts.stages += 1; body = {cases: []}; }
      else if (path.startsWith(`leads/${L}/`)) {
        counts.lead += 1;
        body = {id: L, number: 'L-1', status_label: saved ? 'Cancelled' : 'In process', date_basis: 'actual_intake',
                received_date: '2026-09-26', office: null, contact: null, issues: [], notes: [], cases: []};
      } else if (path.startsWith('work-orders/leads/')) body = {ordered: 0, outstanding: 0, closed: false, borrowers: []};
      return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
    });
    const {LeadDetail} = await import('./Leads.jsx');
    renderApp(<Routes><Route path="/leads/:id" element={<LeadDetail/>}/></Routes>, {route: `/leads/${L}`});
    expect(await screen.findByText('In process')).toBeTruthy();
    saved = true;
    fireEvent.click(await screen.findByRole('button', {name: 'Save intake change'}));   // the workspace loads with the lead
    await waitFor(() => expect(screen.getByText('Cancelled')).toBeTruthy());
    expect(counts.lead).toBe(2);
    expect(counts.stages).toBe(2);
  });
});
