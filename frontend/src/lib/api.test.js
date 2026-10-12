import {afterEach, describe, expect, it, vi} from 'vitest';
import {api, post} from './api.js';

// Sign-in failed with "CSRF token incorrect" after a sign-in on the admin site at :8000
// replaced the token the app held in memory.
const html403 = () => new Response('<h1>Forbidden (403)</h1><p>CSRF verification failed. Request aborted.</p>', {status: 403, headers: {'Content-Type': 'text/html'}});
const ok = body => new Response(JSON.stringify(body), {status: 200, headers: {'Content-Type': 'application/json'}});
afterEach(() => { vi.restoreAllMocks(); document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'; });

describe('the CSRF token', () => {
  it('is read from the current cookie, not a stale copy', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(ok({csrf: 'stale-token'})).mockResolvedValueOnce(ok({username: 'aman'}));
    await api('session/');                                         // the app remembers stale-token
    document.cookie = 'csrftoken=fresh-token';                     // a sign-in elsewhere issues a new one
    await post('login/', {username: 'aman', password: 'x'});
    expect(fetch.mock.calls[1][1].headers['X-CSRFToken']).toBe('fresh-token');   // previously stale-token: 403
  });

  it('recovers once from a CSRF refusal, which the server rejects before doing anything', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(html403()).mockResolvedValueOnce(ok({csrf: 'new'})).mockResolvedValueOnce(ok({username: 'aman'}));
    expect(await post('login/', {username: 'aman', password: 'x'})).toEqual({username: 'aman'});
    expect(fetch.mock.calls.map(c => c[0])).toEqual(['/api/login/', '/api/session/', '/api/login/']);
  });

  it('retries only once, then says to reload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(html403()).mockResolvedValueOnce(ok({csrf: 'new'})).mockResolvedValueOnce(html403());
    await expect(post('login/', {})).rejects.toThrow('The security check failed. Reload the page and try again.');
  });

  it('never retries any other refusal', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response(JSON.stringify({error: 'Staff access is required'}), {status: 403}));
    await expect(post('receipts/', {})).rejects.toThrow('Staff access is required');
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
