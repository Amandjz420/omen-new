import {afterEach, describe, expect, it, vi} from 'vitest';
import {count, date, rupees} from './format.js';
import {clearDraft, listDrafts, loadDraft, saveDraft} from './drafts.js';
import {uuid} from './uuid.js';

describe('format', () => {
  it('groups rupees the Indian way', () => {
    expect(rupees(3850000)).toBe('₹38,50,000.00');
    expect(rupees(12345678, {paise: false})).toBe('₹1,23,45,678');
    expect(count(1234567)).toBe('12,34,567');
  });
  it('writes dates plainly and leaves empty ones empty', () => {
    expect(date('2026-09-27')).toBe('27 Sep 2026');
    expect(date(null)).toBe('');
  });
});

describe('drafts', () => {
  afterEach(() => localStorage.clear());
  it('keeps a draft with the time it was saved', () => {
    saveDraft('valuation:1:site', {q1: '1999'});
    const d = loadDraft('valuation:1:site');
    expect(d.value).toEqual({q1: '1999'});
    expect(d.savedAt).toMatch(/^\d{4}-/);
    expect(listDrafts().map(x => x.key)).toEqual(['valuation:1:site']);
    clearDraft('valuation:1:site');
    expect(loadDraft('valuation:1:site')).toBeNull();
  });
  it('ignores a draft saved in an older shape rather than misreading it', () => {
    localStorage.setItem('omen:draft:old', JSON.stringify({version: 0, value: 'x'}));
    expect(loadDraft('old')).toBeNull();
  });
  it('reports failure instead of throwing when storage is full', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {throw new Error('QuotaExceededError');});
    expect(saveDraft('k', 1)).toBe(false);
    spy.mockRestore();
  });
});

describe('uuid', () => {
  const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

  it('works when the page loads without crypto.randomUUID, as on a phone over plain http', async () => {
    // Removed before the module loads: the path that once recursed (review BF2).
    const original = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', {value: undefined, configurable: true, writable: true});
    try {
      vi.resetModules();
      const {uuid: fresh} = await import('./uuid.js?http-phone');
      const ids = new Set(Array.from({length: 200}, () => crypto.randomUUID()));  // the screens call this directly
      expect(ids.size).toBe(200);
      [...ids].forEach(id => expect(id).toMatch(V4));
      expect(fresh()).toMatch(V4);
    } finally {
      Object.defineProperty(crypto, 'randomUUID', {value: original, configurable: true, writable: true});
    }
  });

  it('uses the browser\'s own function where it exists', () => {
    expect(uuid()).toMatch(V4);
  });
});

describe('today', () => {
  it('is the date on the local calendar, not in UTC', async () => {
    const {today} = await import('./format.js');
    // 1:18 in the morning in India is still the previous day in UTC.
    expect(today(new Date(2026, 9, 15, 1, 18))).toBe('2026-10-15');
    expect(today(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05');
  });
});
