import {fireEvent, screen, waitFor, within} from '@testing-library/react';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {Route, Routes} from 'react-router';
import {renderApp} from '../test/render.jsx';
import {ValuationForm} from './ValuationForm.jsx';

const V = 'v1', S = 's1';
const road = {id: 'q-road', text: 'Type of road available at present', kind: 'single', mandatory: false, retired: false,
  options: [{id: 'o-cem', label: 'Cemented'}, {id: 'o-tar', label: 'Tar'}], answer: {selected: [], custom: ''}, conflicts: [], source: null};
const year = {id: 'q-year', text: 'Year of first construction', kind: 'text', options: [], answer: {value: ''}, conflicts: [], source: null};
const suggestion = {id: 'sg1', question: 'q-road', question_text: road.text, section: S, kind: 'recording', display: 'Cemented',
  quote: 'सामने सीमेंट की road है', located: '0:06', confidence: 'clear', differs: false, status: 'pending'};
beforeEach(() => { URL.createObjectURL = vi.fn(() => 'blob:test-recording'); URL.revokeObjectURL = vi.fn(); });
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

function backend({configured = true, pending = [], failSave = false} = {}) {
  const calls = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    const path = String(url).replace('/api/', ''), method = options.method || 'GET';
    calls.push({path, method, body: options.body});
    const json = (body, status = 200) => new Response(JSON.stringify(body), {status, headers: {'Content-Type': 'application/json'}});
    if (path === `valuations/${V}/`) return json({id: V, report_number: 'R-0926100001', borrower: 'Asha Verma', subtype: 'L & B', editable: true,
      status: 'Pending', sections: [{key: S, name: 'PART C - ONSITE', questions: 77, answered: 11, required: 0, required_answered: 0}]});
    if (path === `valuations/${V}/assist/`) return json({configured, suggestions: pending, sources: []});
    if (path.startsWith(`valuations/${V}/sections/${S}/`)) {
      if (method === 'PUT' && failSave) throw new TypeError('Failed to fetch');
      return json({editable: true, questions: [road, year], suggestions: pending, sections: []});
    }
    if (path.endsWith('/accept/') || path.endsWith('/dismiss/')) return json({...suggestion, status: 'accepted'});
    if (path === `valuations/${V}/assist/recordings/`) return json({source: {id: 'src1', kind: 'recording', status: 'ready', text: 'सामने सीमेंट की road है', counts: {}},
      suggestions: [suggestion]}, 201);
    return json({}, 404);
  });
  return calls;
}
const open = () => renderApp(<Routes><Route path="/valuations/:id/form" element={<ValuationForm/>}/></Routes>, {route: `/valuations/${V}/form`});
const puts = calls => calls.filter(c => c.method === 'PUT').map(c => JSON.parse(c.body).answers[0]);

describe('the phone form', () => {
  it('does not render a stray zero below unanswered questions', async () => {
    backend();
    open();
    await screen.findByRole('button', {name: 'Cemented'});
    expect(screen.queryByText('0', {exact: true})).toBeNull();
    expect(screen.queryByText('Answered by you')).toBeNull();
  });

  it('saves an option the moment it is tapped', async () => {
    const calls = backend();
    open();
    fireEvent.click(await screen.findByRole('button', {name: 'Cemented'}));
    await waitFor(() => expect(puts(calls)).toEqual([{question: 'q-road', selected: ['o-cem'], custom: ''}]));
    expect(await screen.findByText('Saved')).toBeTruthy();
  });

  it('saves a written-in answer when no option fits', async () => {
    const calls = backend();
    open();
    fireEvent.click(await screen.findByRole('button', {name: 'Write your own answer'}));
    const input = screen.getByLabelText('Your own answer');
    fireEvent.change(input, {target: {value: 'Paver block road'}});
    fireEvent.blur(input);
    await waitFor(() => expect(puts(calls)).toEqual([{question: 'q-road', selected: [], custom: 'Paver block road'}]));
  });

  it('keeps an answer on the phone when the signal drops', async () => {
    backend({failSave: true});
    open();
    fireEvent.click(await screen.findByRole('button', {name: 'Tar'}));
    expect(await screen.findByText('Saved on this phone. It will be sent when you are back online.')).toBeTruthy();
    expect(Object.keys(localStorage).some(k => k.includes('valuation:v1:q-road'))).toBe(true);
  });

  it('shows a suggestion beside its question, with its evidence, and accepts it', async () => {
    const calls = backend({pending: [suggestion]});
    open();
    expect(await screen.findByText('“सामने सीमेंट की road है”')).toBeTruthy();
    expect(screen.getByText('· 0:06')).toBeTruthy();
    fireEvent.click(screen.getAllByRole('button', {name: 'Accept'})[0]);
    await waitFor(() => expect(calls.some(c => c.path === `valuations/${V}/assist/suggestions/sg1/accept/` && c.method === 'POST')).toBe(true));
  });

  it('only offers the current answer when the field is filled', async () => {
    backend({pending: [{...suggestion, current_answer: {selected: ['o-tar']}, current_display: 'Tar', differs: true}]});
    open();
    expect(await screen.findByRole('radio', {name: 'Keep the current answer'})).toBeTruthy();
    expect(screen.queryByText(/Keep both:/)).toBeNull();
  });

  it('saves an own answer for an empty field without accepting the suggested text', async () => {
    const calls = backend({pending: [{...suggestion, answer_kind: 'single', current_answer: {selected: [], custom: ''}}]});
    open();
    fireEvent.click(await screen.findByRole('radio', {name: 'Write my own answer'}));
    expect(screen.queryByRole('radio', {name: 'Keep the current answer'})).toBeNull();
    fireEvent.change(screen.getByLabelText('Your answer'), {target: {value: 'Gravel'}});
    fireEvent.click(screen.getByRole('button', {name: 'Accept'}));
    await waitFor(() => expect(calls.some(c => c.path.endsWith('/accept/') && JSON.parse(c.body).own_answer.custom === 'Gravel')).toBe(true));
  });

  it('copies the suggestion without changing the form', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText}});
    const calls = backend({pending: [suggestion]});
    open();
    fireEvent.click(await screen.findByRole('button', {name: 'Copy suggestion'}));
    expect(writeText).toHaveBeenCalledWith('Cemented');
    expect(await screen.findByText('Copied')).toBeTruthy();
    expect(puts(calls)).toEqual([]);
  });

  it('sends a recording and opens the review of what it suggested', async () => {
    const calls = backend();
    open();
    await screen.findByRole('button', {name: 'Record'});
    const recorder = screen.getByLabelText('Record with the phone’s recorder');       // no live microphone off a secure page
    fireEvent.change(recorder, {target: {files: [new File(['audio'], 'site.m4a', {type: 'audio/mp4'})]}});
    await waitFor(() => expect(calls.some(c => c.path === `valuations/${V}/assist/recordings/` && c.body instanceof FormData)).toBe(true));
    const sheet = await screen.findByRole('dialog', {name: 'Suggested answers'});
    expect(within(sheet).getByText('Cemented')).toBeTruthy();
    expect(within(sheet).getByText('What you said')).toBeTruthy();
  });

  it('says so when voice and documents are not set up', async () => {
    backend({configured: false});
    open();
    expect(await screen.findByText('Voice and documents are not set up on this server yet.')).toBeTruthy();
    expect(screen.getByRole('button', {name: 'Record'}).disabled).toBe(true);
    expect(screen.getByRole('button', {name: 'Read a document'}).disabled).toBe(true);
  });
});
