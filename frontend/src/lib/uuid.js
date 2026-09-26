// crypto.randomUUID exists only in secure contexts (https, or localhost). A phone
// on the office network opening http://<server>:5173 has none, and every retry-safe
// action needs an operation ID, so a version-4 UUID is built from getRandomValues,
// which browsers provide everywhere.
export function uuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map(x => x.toString(16).padStart(2, '0'));
  return `${h.slice(0, 4).join('')}-${h.slice(4, 6).join('')}-${h.slice(6, 8).join('')}-${h.slice(8, 10).join('')}-${h.slice(10).join('')}`;
}

// The screens moved across from the previous interface call crypto.randomUUID
// directly; give them the same fallback until each is rebuilt on uuid().
if (globalThis.crypto && !globalThis.crypto.randomUUID) globalThis.crypto.randomUUID = uuid;
