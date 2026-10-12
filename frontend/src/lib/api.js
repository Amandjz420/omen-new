import './uuid.js';

let csrf = '';
export const SIGNED_OUT = 'omen:signed-out';

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// The CSRF token is read from Django's cookie on every request. A copy kept in
// memory went stale whenever Django issued a new token, as it does at every sign-in,
// including in another tab or on the admin site at :8000 (browsers share cookies
// across ports), and sign-in then failed with "CSRF token incorrect".
function token() {
  const match = (globalThis.document?.cookie || '').match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : csrf;
}

async function send(path, options, json) {
  try {
    return await fetch(`/api/${path}`, {
      credentials: 'same-origin', ...options,
      headers: {...(json ? {'Content-Type': 'application/json'} : {}), 'X-CSRFToken': token(), ...options.headers},
    });
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0, null);
  }
}

/** Call the backend. Adds the CSRF token, lets FormData set its own boundary,
 * and throws ApiError with the server's own message. The screens moved across
 * from the previous interface receive this same function as their `api` prop. */
export async function api(path, options = {}, retried = false) {
  const json = !(options.body instanceof FormData);
  const response = await send(path, options, json);
  const text = await response.text().catch(() => '');
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = null; }
  // Django's CSRF refusal is an HTML page, before the view runs, so nothing was done:
  // fetch a fresh token and try once more. Other refusals are never retried.
  if (response.status === 403 && data === null && /csrf/i.test(text)) {
    if (!retried && path !== 'session/') {
      await send('session/', {}, true).then(r => r.json()).then(d => { if (d?.csrf) csrf = d.csrf; }).catch(() => {});
      return api(path, options, true);
    }
    throw new ApiError('The security check failed. Reload the page and try again.', 403, null);
  }
  data = data || {error: 'The server could not complete the request'};
  // An expired session is handled once, for every screen: the session gate hears of
  // it and returns the person to sign-in (review BF4).
  if (response.status === 401) globalThis.dispatchEvent?.(new CustomEvent(SIGNED_OUT));
  if (!response.ok) {
    const message = data.problems?.length ? data.problems.join(' ') : data.error || `Request failed (${response.status})`;
    throw new ApiError(message, response.status, data);
  }
  if (data.csrf) csrf = data.csrf;
  return data;
}

export const post = (path, body) => api(path, {method: 'POST', body: JSON.stringify(body ?? {})});
export const put = (path, body) => api(path, {method: 'PUT', body: JSON.stringify(body ?? {})});
