// crypto.randomUUID exists only in secure contexts (https, or localhost). A phone
// on the office network opening http://<server>:5173 has none, and every retry-safe
// action needs an operation ID, so a version-4 UUID is built from getRandomValues,
// which browsers provide everywhere.
//
// The browser's own function, if any, is kept separately. The fallback installed
// for screens that call crypto.randomUUID directly is independent of uuid(): it
// once installed uuid() itself, which then found and called itself for ever
// (review BF2).
const native = typeof globalThis.crypto?.randomUUID === 'function' ? globalThis.crypto.randomUUID.bind(globalThis.crypto) : null;

function fromRandomValues() {
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map(x => x.toString(16).padStart(2, '0'));
  return `${h.slice(0, 4).join('')}-${h.slice(4, 6).join('')}-${h.slice(6, 8).join('')}-${h.slice(8, 10).join('')}-${h.slice(10).join('')}`;
}

export function uuid() {
  return native ? native() : fromRandomValues();
}

if (globalThis.crypto && !native) globalThis.crypto.randomUUID = fromRandomValues;
