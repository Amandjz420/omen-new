import {fireEvent, screen, waitFor} from '@testing-library/react';
import {expect, it, vi} from 'vitest';
import {renderApp} from './test/render.jsx';
import {Verifications} from './verifications.jsx';

// Review 2026-10: a verifier corrects answers, and verifying moves on to the next track.
const tracks = done => Object.fromEntries(['legal', 'technical', 'social', 'general', 'final'].map(k =>
  [k, {label: k, status: done.includes(k) ? 'Verified' : '', verified: done.includes(k), by: '', date: null}]));
const detail = (track, done, next) => ({id: 'v1', track, status: 'Submit', report_number: 'R-1', lead_number: 'L-1', borrower: 'B',
  service: 'Valuation', subtype: '', assessor: 'A', submitted_on: '2026-10-26', submitted_at: '2026-10-26T08:35:00Z',
  tracks: tracks(done), can_verify: true, can_edit: true, can_revert: true, next_track: next, reversions: [], unassigned: [],
  sections: [{key: 's', name: 'Site', questions: [{id: `q-${track}`, text: `${track} question`, kind: 'text', options: [], answer: {value: 'old'}}]}]});

function fakeApi() {
  const done = [];
  return vi.fn(async (path, init = {}) => {
    if (path.startsWith('verifications/?')) return {track: 'legal', total: 1, page: 1, page_size: 25,
      counts: {legal: 1, technical: 1, social: 1, general: 1},
      results: [{id: 'v1', report_number: 'R-1', lead_number: 'L-1', borrower: 'B', service: 'Valuation', subtype: '',
                 submitted_on: '2026-10-26', submitted_at: '2026-10-26T08:35:00Z', assessor: 'A', tracks: {}}]};
    const view = path.match(/^verifications\/v1\/\?track=(\w+)/);
    if (view) return detail(view[1], done, ['legal', 'social', 'technical', 'general'].find(t => t !== view[1] && !done.includes(t)) || null);
    const answers = path.match(/^verifications\/v1\/(\w+)\/answers\/$/);
    if (answers) {const d = detail(answers[1], done, null); d.sections[0].questions[0].answer = JSON.parse(init.body).answers[0]; return d;}
    const verify = path.match(/^verifications\/v1\/(\w+)\/$/);
    if (verify) {done.push(verify[1]); return {next_track: ['legal', 'social', 'technical', 'general'].find(t => !done.includes(t)) || null};}
    throw new Error(`unexpected ${path}`);
  });
}

it('a verifier corrects an answer and the next track opens after verifying', async () => {
  const api = fakeApi();
  renderApp(<Verifications api={api}/>);
  fireEvent.click(await screen.findByText('Review →'));
  const answer = await screen.findByDisplayValue('old');
  expect(answer.disabled).toBe(false);
  fireEvent.change(answer, {target: {value: 'corrected'}});
  fireEvent.click(screen.getByText('Save corrections'));
  await waitFor(() => expect(api).toHaveBeenCalledWith('verifications/v1/legal/answers/', expect.objectContaining({method: 'PUT'})));
  expect(JSON.parse(api.mock.calls.find(c => c[0].endsWith('answers/'))[1].body).answers).toEqual([{question: 'q-legal', value: 'corrected'}]);

  fireEvent.change(screen.getByLabelText(/Remark/), {target: {value: 'Title checked'}});
  fireEvent.click(screen.getByText('Verify legal'));
  expect(await screen.findByRole('heading', {name: 'R-1 · Social verification'})).toBeTruthy();
  expect(screen.getByText(/Legal verification saved/)).toBeTruthy();
  expect(screen.getByText(/26 Oct 2026, \d\d:\d\d/)).toBeTruthy();          // the submission time on the 24-hour clock
});
