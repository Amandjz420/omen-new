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

/** Call the backend. Adds the CSRF token, lets FormData set its own boundary,
 * and throws ApiError with the server's own message. The screens moved across
 * from the previous interface receive this same function as their `api` prop. */
export async function api(path, options = {}) {
  const json = !(options.body instanceof FormData);
  let response;
  try {
    response = await fetch(`/api/${path}`, {
      credentials: 'same-origin', ...options,
      headers: {...(json ? {'Content-Type': 'application/json'} : {}), 'X-CSRFToken': csrf, ...options.headers},
    });
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0, null);
  }
  const data = await response.json().catch(() => ({error: 'The server could not complete the request'}));
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
