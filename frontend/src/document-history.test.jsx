import {fireEvent, screen} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {render} from '@testing-library/react';
import {DocumentHistory} from './valuations.jsx';

afterEach(() => vi.restoreAllMocks());

describe("a valuation's uploaded documents", () => {
  it('lists the current and earlier ones, each opening its file', async () => {
    const api = vi.fn().mockResolvedValue({documents: [
      {document: 'd2', name: 'deed-v2.pdf', status: 'current', question: 'Documents produced', on: '2026-10-12T10:00:00Z', by: ''},
      {document: 'd1', name: 'deed-v1.pdf', status: 'legacy', question: 'Documents produced', on: '2024-05-02T10:00:00Z', by: ''}]});
    render(<DocumentHistory api={api} id="v1"/>);
    fireEvent.click(screen.getByRole('button', {name: /Show all uploaded documents/}));
    const earlier = await screen.findByRole('link', {name: 'deed-v1.pdf'});
    expect(earlier.getAttribute('href')).toBe('/api/valuations/v1/documents/d1/file/');
    expect(screen.getByText(/Earlier upload \(previous system\) · Documents produced/)).toBeTruthy();
    expect(api).toHaveBeenCalledWith('valuations/v1/documents/history/');
  });
});
