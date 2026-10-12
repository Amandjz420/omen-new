import {fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {renderApp} from '../test/render.jsx';
import {SiteChecklist} from './SiteChecklist.jsx';
import {saveDraft} from '../lib/drafts.js';

const question = {question: 'q1', text: 'Year of construction', section: 'Inspection', section_key: 'site'};
const initial = {editable: true, missing_required: [question], remaining_questions: 1, remaining_photos: 1,
  photos: [{code: 1, label: 'Front', status: 'missing'}], photo_policy: 'Expected coverage', photo_check: 'Records only'};
afterEach(() => {vi.restoreAllMocks(); localStorage.clear();});

function server(data = initial) {
  let current = structuredClone(data);
  const calls = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
    calls.push({url, ...options});
    let body = current;
    if (String(url).endsWith('/follow-up/')) body = {follow_up: {...question, ai_generated: true, prompt: 'When was the property built?'}};
    if (String(url).endsWith('/photos/')) {
      current = {...current, remaining_photos: 0, photos: [{code: 1, label: 'Front', status: 'recorded'}]};
      body = {};
    }
    return new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
  });
  return calls;
}

describe('site completion checklist', () => {
  it('shows missing information, asks a focused follow-up and opens the original question', async () => {
    const calls = server(), onQuestion = vi.fn();
    renderApp(<SiteChecklist id="v1" onQuestion={onQuestion}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Before leaving the site'}));
    expect(await screen.findByText('1 required questions remaining')).toBeTruthy();
    expect(screen.getByText('Year of construction')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', {name: 'Ask a focused follow-up'}));
    expect(await screen.findByText('When was the property built?')).toBeTruthy();
    expect(screen.getByText('Original: Year of construction')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', {name: 'Answer this question'}));
    expect(onQuestion).toHaveBeenCalledWith(expect.objectContaining({question: 'q1', section_key: 'site'}));
    expect(calls.filter(c => c.method === 'POST')).toHaveLength(1);
  });

  it('uploads a photograph to the selected category and refreshes its status', async () => {
    const calls = server();
    renderApp(<SiteChecklist id="v1" onQuestion={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Before leaving the site'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Add Front'}));
    fireEvent.change(screen.getByLabelText('Add checklist photograph'), {target: {files: [new File(['photo'], 'front.jpg', {type: 'image/jpeg'})]}});
    expect(await screen.findByText('File recorded')).toBeTruthy();
    const upload = calls.find(c => String(c.url).endsWith('/photos/'));
    expect(upload.body.get('type')).toBe('1');
    expect(upload.body.get('file').name).toBe('front.jpg');
    expect(screen.queryByRole('button', {name: 'Add Front'})).toBeNull();
  });

  it('does not claim completion while an answer remains on the device', async () => {
    server({...initial, missing_required: [], remaining_questions: 0, remaining_photos: 0, photos: []});
    saveDraft('valuation:v1:q1', {answer: {value: '2000'}});
    renderApp(<SiteChecklist id="v1" onQuestion={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Before leaving the site'}));
    expect(await screen.findByText('No unanswered required questions.')).toBeTruthy();
    expect(screen.getByText('Some answers are not saved to the server')).toBeTruthy();
    expect(screen.queryByText(/All required questions have saved answers/)).toBeNull();
  });

  it('shows a failure instead of an empty checklist when the server cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Offline'));
    renderApp(<SiteChecklist id="v1" onQuestion={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Before leaving the site'}));
    expect(await screen.findByText('Checklist unavailable')).toBeTruthy();
    expect(screen.queryByText('No unanswered required questions.')).toBeNull();
  });

  it('does not offer uploads or AI prompting for a submitted valuation', async () => {
    server({...initial, editable: false});
    renderApp(<SiteChecklist id="v1" onQuestion={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Before leaving the site'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Ask a focused follow-up'}).disabled).toBe(true));
    expect(screen.queryByRole('button', {name: 'Add Front'})).toBeNull();
  });
});
