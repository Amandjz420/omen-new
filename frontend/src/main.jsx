import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

let csrf = '';
async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, {...options, headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...options.headers}});
  const data = await response.json().catch(() => ({error: 'The server could not complete the request'}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  if (data.csrf) csrf = data.csrf;
  return data;
}
const fmt = n => Number(n || 0).toLocaleString('en-IN');

function App() {
  const [user, setUser] = useState(undefined);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('Overview');
  const [summary, setSummary] = useState(null);
  const [list, setList] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [detail, setDetail] = useState(null);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {api('session/').then(x => setUser(x.staff ? x.username : null)).catch(e => {setError(e.message); setUser(null);});}, []);
  useEffect(() => {
    if (!user) return;
    let active = true;
    api('summary/').then(x => active && setSummary(x)).catch(e => active && setError(e.message));
    return () => {active = false;};
  }, [user]);
  useEffect(() => {
    if (!user || !['Leads', 'Offices'].includes(tab)) return;
    let active = true;
    setList(null);
    const timer = setTimeout(() => api(`${tab.toLowerCase()}/?q=${encodeURIComponent(search)}&page=${page}&status=${status}`)
      .then(x => active && setList(x)).catch(e => active && setError(e.message)), 200);
    return () => {active = false; clearTimeout(timer);};
  }, [tab, page, search, status, user]);
  async function signIn(event) {
    event.preventDefault(); setError(''); setSaving(true);
    const fields = new FormData(event.target);
    try {const x = await api('login/', {method: 'POST', body: JSON.stringify(Object.fromEntries(fields))}); setUser(x.username);}
    catch (e) {setError(e.message);} finally {setSaving(false);}
  }
  async function openLead(id) {
    setError('');
    try {setDetail(await api(`leads/${id}/`)); setNote('');} catch (e) {setError(e.message);}
  }
  async function saveNote(event) {
    event.preventDefault(); setSaving(true); setError('');
    try {setDetail(await api(`leads/${detail.id}/`, {method: 'POST', body: JSON.stringify({body: note})})); setNote('');}
    catch(e) {setError(e.message);} finally {setSaving(false);}
  }
  if (user === undefined) return <main className="login"><p>Connecting to your workspace…</p></main>;
  if (!user) return <main className="login"><form onSubmit={signIn} className="login-card"><div className="logo">O<span>MEN</span></div><p className="eyebrow">LEAD WORKSPACE / MIGRATION PREVIEW</p><h1>Your relationships.<br/>A clearer picture.</h1><p>Sign in with a Django staff account to explore the imported records.</p><label>Username<input name="username" autoComplete="username" required/></label><label>Password<input name="password" type="password" autoComplete="current-password" required/></label><button disabled={saving}>{saving ? 'Signing in…' : 'Open workspace →'}</button>{error && <p role="alert" className="error">{error}</p>}</form></main>;
  return <div className="shell"><aside><div className="logo">O<span>MEN</span></div><p className="eyebrow">RELATIONSHIP WORKSPACE</p><nav>{['Overview', 'Leads', 'Offices', 'Import history'].map(t => <button className={tab === t ? 'active' : ''} key={t} onClick={() => {setTab(t); setPage(1); setSearch(''); setDetail(null); setError('');}}>{t}</button>)}</nav><div className="aside-foot"><span>Migration preview · Phase 1</span><button onClick={async () => {try {await api('logout/', {method: 'POST'}); setUser(null); setDetail(null); setSummary(null); setList(null); await api('session/');} catch(e) {setError(e.message);}}}>Sign out · {user}</button></div></aside>
  <main><header><div><p className="eyebrow">OMEN / {tab.toUpperCase()}</p><h1>{tab === 'Overview' ? 'The work behind every relationship.' : tab}</h1></div><span className="pill">Local migration workspace</span></header>
  {error && <p role="alert" className="error">{error}</p>}
  {tab === 'Overview' && (summary ? <><p className="intro">A first view of your imported lead history, with the original relationships preserved.</p><section className="stats">{[['Client offices', summary.offices], ['Leads', summary.leads], ['Recorded cases', summary.cases], ['Contacts', summary.contacts]].map(([label, value]) => <article key={label}><span>{label}</span><strong>{fmt(value)}</strong><small>All retained source records</small></article>)}</section><section className="panel"><div className="section-title"><h2>Recorded work by service</h2><span>All available history</span></div><p className="muted">{summary.policy}</p>{summary.services.length ? summary.services.map(s => <div className="service" key={s.service}><span>{s.service || 'Unclassified'}</span><div className="track"><div style={{width: `${100*s.count/Math.max(...summary.services.map(v => v.count))}%`}}/></div><strong>{fmt(s.count)}</strong></div>) : <p>Import your source data to populate this workspace.</p>}</section><div className="notice">Closed is a legacy lead status. It does not establish completed valuation or payment. Operational MIS parity is still being migrated.</div></> : <p>Loading overview…</p>)}
  {['Leads', 'Offices'].includes(tab) && !detail && <section className="panel"><div className="toolbar"><label className="search">Search {tab.toLowerCase()}<input placeholder={tab === 'Leads' ? 'Lead number, source ID or office name' : 'Office name, branch or source ID'} value={search} onChange={e => {setSearch(e.target.value); setPage(1);}}/></label>{tab === 'Leads' && <label>Legacy status<select value={status} onChange={e => {setStatus(e.target.value); setPage(1);}}><option value="">All statuses</option><option value="1">New lead</option><option value="2">In process</option><option value="3">Cancelled</option><option value="4">Closed (legacy)</option></select></label>}</div>{!list ? <p>Loading records…</p> : <><div className="table-wrap"><table><thead><tr>{(tab === 'Leads' ? ['Lead / source ID', 'Commissioning office', 'Lead-entry date', 'Status', ''] : ['Office / source ID', 'Branch', 'Bank', 'District']).map((h, i) => <th key={i}>{h}</th>)}</tr></thead><tbody>{list.results.map(r => tab === 'Leads' ? <tr key={r.id}><td><strong>{r.number || 'No number'}</strong><small>Source {r.source_id}</small></td><td>{r.office?.name || 'Unresolved office'}<small>{r.office?.branch}</small></td><td>{r.received_date || 'Unknown'}</td><td><span className="status">{r.status_label}</span></td><td><button className="link" onClick={() => openLead(r.id)}>Open →</button></td></tr> : <tr key={r.id}><td><strong>{r.name}</strong><small>Source {r.source_id}</small></td><td>{r.branch || '—'}</td><td>{r.bank || 'Unlinked / non-bank'}</td><td>{r.district || 'Unknown'}</td></tr>)}</tbody></table></div>{list.count === 0 && <p>No matching records.</p>}<div className="pagination"><span>{fmt(list.count)} records · Page {page}</span><button disabled={page <= 1} onClick={() => setPage(page-1)}>Previous</button><button disabled={page*30 >= list.count} onClick={() => setPage(page+1)}>Next</button></div></>}</section>}
  {detail && tab === 'Leads' && <section className="panel"><button className="link" onClick={() => setDetail(null)}>← Back to leads</button><h2>{detail.number || `Lead ${detail.source_id}`}</h2><p>{detail.office?.name || 'Unresolved office'} · {detail.office?.branch} · {detail.status_label}</p><p className="muted">Lead-entry proxy: {detail.received_date || 'Unknown'} · Contact: {detail.contact?.name || 'Unknown'} {detail.contact?.phone || ''}</p>{detail.issues.length > 0 && <p className="notice">{detail.issues.join('; ')}</p>}<h3>Linked cases ({detail.cases.length})</h3><div className="table-wrap"><table><thead><tr><th>Source case</th><th>Service</th><th>Asset subtype</th><th>Asset district</th></tr></thead><tbody>{detail.cases.map(c => <tr key={c.source_id}><td>{c.source_id}</td><td>{c.service || 'Unknown'}</td><td>{c.subtype || 'Unknown'}</td><td>{c.district || 'Unknown'}</td></tr>)}</tbody></table></div><h3>Follow-up notes</h3><p className="muted">Notes belong to this workspace and survive source-data refreshes.</p><form onSubmit={saveNote}><label>Add a note<textarea value={note} maxLength={4000} onChange={e => setNote(e.target.value)} required/></label><button disabled={saving || !note.trim()}>{saving ? 'Saving…' : 'Save note'}</button></form>{detail.notes.map(n => <article className="note" key={n.id}><p>{n.body}</p><small>{n.author__username} · {new Date(n.created_at).toLocaleString()}</small></article>)}</section>}
  {tab === 'Import history' && <section className="panel"><h2>Latest committed import</h2><p className="muted">Source IDs drive updates. Missing records are retained. Additional exported entities are staged for later migration phases.</p>{summary?.latest_import ? <><p>{new Date(summary.latest_import.created_at).toLocaleString()}</p><div className="table-wrap"><table><thead><tr><th>Source sheet</th><th>Inserted</th><th>Updated</th><th>Unchanged</th><th>Handling</th></tr></thead><tbody>{Object.entries(summary.latest_import.summary).map(([sheet, s]) => <tr key={sheet}><td>{sheet}</td><td>{fmt(s.inserted ?? s.staged_inserted)}</td><td>{fmt(s.updated ?? s.staged_updated)}</td><td>{fmt(s.unchanged)}</td><td>{s.staged_inserted !== undefined ? 'Staging only' : `${s.rows_with_issues} rows flagged`}</td></tr>)}</tbody></table></div></> : <p>No import has been committed.</p>}</section>}
  </main></div>;
}
createRoot(document.getElementById('root')).render(<App/>);
