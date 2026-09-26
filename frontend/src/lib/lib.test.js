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
  it('makes a version-4 UUID without crypto.randomUUID, as on a phone over plain http', () => {
    const original = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', {value: undefined, configurable: true});
    expect(uuid()).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    Object.defineProperty(crypto, 'randomUUID', {value: original, configurable: true});
  });
});
