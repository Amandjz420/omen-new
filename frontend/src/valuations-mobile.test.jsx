import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {renderApp} from './test/render.jsx';
import {Valuations} from './valuations.jsx';

vi.mock('./approvals.jsx', () => ({Standing: () => null}));
afterEach(() => vi.restoreAllMocks());

it('keeps unsaved answers when a phone section change is cancelled, and switches only when confirmed', async () => {
  const sections = [{key: 'a', name: 'Property', answered: 0, questions: 1}, {key: 'b', name: 'Inspection', answered: 0, questions: 1}];
  const api = vi.fn(async path => {
    if (path.startsWith('valuations/?')) return {total: 1, page_size: 25, results: [{case_id: 'case1', lead_number: 'L-1', borrower: 'Sample borrower', valuation: {id: 'v1', status: 'Pending'}}]};
    if (path === 'valuations/v1/') return {editable: true, status: 'Pending', sections};
    if (path.includes('/sections/')) return {questions: [{id: path.includes('/a/') ? 'q1' : 'q2', text: 'Observations', kind: 'text', answer: {value: ''}}]};
    throw new Error(`Unexpected request: ${path}`);
  });
  renderApp(<Valuations api={api}/>);
  fireEvent.click(await screen.findByRole('button', {name: 'Open →'}));
  const picker = await screen.findByRole('combobox', {name: 'Valuation section'});
  const answer = await screen.findByRole('textbox');
  fireEvent.change(answer, {target: {value: 'Unsaved inspection note'}});
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  fireEvent.change(picker, {target: {value: 'b'}});
  expect(picker.value).toBe('a');
  expect(answer.value).toBe('Unsaved inspection note');
  expect(api.mock.calls.some(([path]) => path === 'valuations/v1/sections/b/')).toBe(false);
  confirm.mockReturnValue(true);
  fireEvent.change(picker, {target: {value: 'b'}});
  await waitFor(() => expect(api).toHaveBeenCalledWith('valuations/v1/sections/b/'));
  expect(picker.value).toBe('b');
  expect(api.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});
