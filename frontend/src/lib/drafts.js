// Drafts kept on the device, so work entered at a site with poor signal is never
// lost to a dropped connection. Each draft carries a schema version and the time it
// was saved; the valuation form will write answers here first and send them when
// the connection allows.
const PREFIX = 'omen:draft:';
const VERSION = 1;

const storage = () => {
  try { return globalThis.localStorage ?? null; } catch { return null; }   // private mode can refuse access
};

export function saveDraft(key, value) {
  const store = storage();
  if (!store) return false;
  try {
    store.setItem(PREFIX + key, JSON.stringify({version: VERSION, savedAt: new Date().toISOString(), value}));
    return true;
  } catch {
    return false;                                                         // storage full: the caller keeps working online
  }
}

export function loadDraft(key) {
  const store = storage();
  const raw = store?.getItem(PREFIX + key);
  if (!raw) return null;
  try {
    const draft = JSON.parse(raw);
    return draft.version === VERSION ? draft : null;                      // an old shape is ignored, never misread
  } catch {
    return null;
  }
}

export function clearDraft(key) {
  storage()?.removeItem(PREFIX + key);
}

export function listDrafts() {
  const store = storage();
  if (!store) return [];
  return Object.keys(store).filter(k => k.startsWith(PREFIX)).map(k => ({key: k.slice(PREFIX.length), ...loadDraft(k.slice(PREFIX.length))}))
    .filter(d => d.savedAt).sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}
