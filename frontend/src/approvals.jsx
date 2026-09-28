import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useState} from 'react';

export function Approvals({api}) {
  const [open, setOpen] = useState(null);
  return open ? <Review api={api} id={open} onBack={() => setOpen(null)}/> : <Queue api={api} onOpen={setOpen}/>;
}

function Queue({api, onOpen}) {
  const [state, setState] = useState('pending');
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  useEffect(() => {
    const t = setTimeout(() => api(`approvals/?state=${state}&q=${encodeURIComponent(q)}&page=${page}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [state, q, page]);
  return <section className="panel">
    <div className="tabs">{[['pending', 'Awaiting approval'], ['approved', 'Approved']].map(([k, l]) =>
      <button key={k} className={k === state ? 'active' : ''} onClick={() => {setState(k); setPage(1);}}>{l}{list && <span className="count"> {list.counts[k]}</span>}</button>)}</div>
    <div className="toolbar"><label className="search">Search<input placeholder="Report, lead or borrower" value={q} onChange={e => {setQ(e.target.value); setPage(1);}}/></label></div>
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <ResponsiveTable><table><thead><tr><th>Report</th><th>Lead</th><th>Borrower</th><th>Service</th><th>Submitted</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.id}><td><strong>{r.report_number}</strong></td><td>{r.lead_number}</td><td>{r.borrower}</td>
        <td>{r.service}</td><td>{r.submitted_on || '—'}</td><td><button className="link" onClick={() => onOpen(r.id)}>Review →</button></td></tr>)}</tbody></table></ResponsiveTable>
      {list.total === 0 && <p>Nothing here.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function Review({api, id, onBack}) {
  const [data, setData] = useState(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const load = () => api(`approvals/${id}/`).then(setData).catch(e => setError(e.message));
  useEffect(() => {load();}, [id]);
  async function act(path, body, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(path); setError('');
    try {setData(await api(`approvals/${id}/${path}/`, {method: 'POST', body: JSON.stringify(body)})); setReason('');}
    catch (e) {setError(e.message);} finally {setBusy('');}
  }
  if (!data) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  const doc = data.report?.document;
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to approvals</button>
    <h2>{data.report_number}{data.report?.revision ? ` · Revision ${data.report.revision}` : ''}</h2>
    <p>{data.lead_number} · {data.borrower} · <span className="status">{data.approved ? `Approved by ${data.approved_by}` : data.status}</span></p>
    {doc && (doc.available ? <p><a href={`/api/bank-reports/${id}/document/`} target="_blank" rel="noopener">Read the bank report (PDF)</a></p>
      : <p className="muted">The bank report's file could not be found in storage.</p>)}
    {error && <p role="alert" className="error">{error}</p>}
    {data.approval_blockers.length === 0
      ? <p><button disabled={busy === 'approve'} onClick={() => act('approve', {}, 'Give final approval? This issues the report to the bank.')}>
          {busy === 'approve' ? 'Approving…' : 'Give final approval'}</button></p>
      : !data.approved && data.approval_blockers.map(b => <p key={b} className="notice">{b}</p>)}
    {data.can_final_revert && <form className="panel inset" onSubmit={e => {e.preventDefault(); act('revert', {reason},
        data.approved ? 'Send back an approved report? It will be kept as a superseded version, and the corrected report will be issued as the next revision.'
                      : 'Send this report back for correction?');}}>
      <h3>Send back for correction</h3>
      <p className="muted">{data.approved ? 'This report has been issued. It will be kept, and the corrected report will carry the next revision number.'
                                          : 'This report has not been issued, so it will simply be revised.'}</p>
      <label>Reason<span className="required"> *</span><textarea rows={2} value={reason} required onChange={e => setReason(e.target.value)}/></label>
      <button disabled={busy === 'revert' || !reason.trim()}>{busy === 'revert' ? 'Sending…' : 'Send back'}</button></form>}
    <History data={data}/>
  </section>;
}

export function History({data}) {
  if (!data.events.length && !data.reversions.length) return null;
  return <><h3>History</h3><ul>
    {data.events.map((e, i) => <li key={`e${i}`}>{e.on || '—'} · {e.kind} by {e.by || '—'}{e.reason ? `: ${e.reason}` : ''}</li>)}
    {data.reversions.map((r, i) => <li key={`r${i}`}>{r.on || '—'} · Sent back ({r.stage}) by {r.by || '—'}: {r.remark}</li>)}
  </ul></>;
}

// Hold, unhold and cancel, shown on the valuation itself.
export function Standing({api, id, onChange}) {
  const [data, setData] = useState(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  useEffect(() => {api(`valuations/${id}/standing/`).then(setData).catch(e => setError(e.message));}, [id]);
  if (!data) return null;
  async function act(action, confirmText) {
    if (!reason.trim()) {setError('Enter a reason first'); return;}
    if (!window.confirm(confirmText)) return;
    setBusy(action); setError('');
    try {const next = await api(`valuations/${id}/standing/${action}/`, {method: 'POST', body: JSON.stringify({reason})}); setData(next); setReason(''); onChange?.(next);}
    catch (e) {setError(e.message);} finally {setBusy('');}
  }
  const any = data.can_hold || data.can_unhold || data.can_cancel;
  return <div className="standing">
    {data.status === 'Hold' && <p className="notice">On hold: {data.reason}</p>}
    {data.status === 'Cancel' && <p className="notice">Cancelled: {data.reason}</p>}
    {data.cancel_blocked_by_invoice && <p className="muted">This valuation has been invoiced, so it can only be cancelled by reversing the invoice.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {any && <div className="toolbar">
      <label className="search">Reason<input value={reason} maxLength={500} onChange={e => setReason(e.target.value)} placeholder="Why?"/></label>
      {data.can_hold && <button disabled={!!busy} onClick={() => act('hold', 'Put this valuation on hold?')}>Put on hold</button>}
      {data.can_unhold && <button disabled={!!busy} onClick={() => act('unhold', `Take this valuation off hold? It returns to ${data.unhold_to}.`)}>Take off hold</button>}
      {data.can_cancel && <button disabled={!!busy} onClick={() => act('cancel', 'Cancel this valuation? This cannot be undone.')}>Cancel valuation</button>}
    </div>}
  </div>;
}
