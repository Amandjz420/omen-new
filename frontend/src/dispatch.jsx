import React, {useEffect, useState} from 'react';

const TABS = [['awaiting', 'Awaiting dispatch'], ['lying', 'Lying at HO'], ['transit', 'In transit'], ['delivered', 'Delivered'], ['cancelled', 'Cancelled']];
const MODES = [[2, 'Speed Post'], [1, 'Courier'], [3, 'By Hand'], [4, 'Pick up from HO'], [5, 'By E-Mail'], [6, 'Normal Post']];
const COURIERS = [[1, 'Madhur Courier Services'], [2, 'India Post Services'], [3, 'Other']];
const today = () => new Date().toISOString().slice(0, 10);

export function Dispatch({api}) {
  const [view, setView] = useState(null);       // {send: [reports], resend?} or {dispatch: id}
  if (view?.send) return <SendForm api={api} reports={view.send} resend={view.resend} onBack={() => setView(null)} onSent={id => setView({dispatch: id})}/>;
  if (view?.dispatch) return <DispatchPage api={api} id={view.dispatch} onBack={() => setView(null)}
    onResend={r => setView({send: [r], resend: true})}/>;
  return <Lists api={api} onSend={reports => setView({send: reports})} onOpen={id => setView({dispatch: id})}/>;
}

function Lists({api, onSend, onOpen}) {
  const [tab, setTab] = useState('awaiting');
  const [list, setList] = useState(null);
  const [counts, setCounts] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [picked, setPicked] = useState({});
  const [error, setError] = useState('');
  useEffect(() => {
    const t = setTimeout(() => {
      const path = tab === 'awaiting' ? `dispatch/awaiting/?q=${encodeURIComponent(q)}&page=${page}` : `dispatch/?state=${tab}&q=${encodeURIComponent(q)}&page=${page}`;
      Promise.all([api(path), api('dispatch/?state=lying')]).then(([r, c]) => {setList(r); setCounts(c.counts); setError('');}).catch(e => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [tab, q, page]);
  const awaiting = tab === 'awaiting', chosen = Object.values(picked);
  return <section className="panel">
    <div className="tabs">{TABS.map(([k, l]) => <button key={k} className={k === tab ? 'active' : ''} onClick={() => {setTab(k); setPage(1);}}>
      {l}{counts && k !== 'awaiting' && <span className="count"> {counts[k].toLocaleString('en-IN')}</span>}</button>)}</div>
    <div className="toolbar"><label className="search">Search<input placeholder={awaiting ? 'Report, lead, borrower or office' : 'Dispatch, report, consignment or client'} value={q} onChange={e => {setQ(e.target.value); setPage(1);}}/></label>
      {awaiting && <button disabled={!chosen.length} onClick={() => onSend(chosen)}>Dispatch {chosen.length || ''} selected</button>}</div>
    {awaiting && <p className="muted">Approved reports not yet in any dispatch, newest first. Dispatch tracking began in 2021, so older reports appear here without having been lost.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <div className="table-wrap"><table>{awaiting
        ? <><thead><tr><th></th><th>Report</th><th>Borrower</th><th>Office</th><th>Valued</th><th>Assessor's instruction</th></tr></thead>
          <tbody>{list.results.map(r => <tr key={r.valuation}><td><input type="checkbox" checked={!!picked[r.valuation]}
            onChange={e => setPicked(p => {const n = {...p}; e.target.checked ? n[r.valuation] = r : delete n[r.valuation]; return n;})}/></td>
            <td><strong>{r.report_number}</strong></td><td>{r.borrower}</td><td>{r.office}</td><td>{r.valued_on || '—'}</td>
            <td>{[r.to_be_dispatched_at, r.to_be_dispatched_by].filter(Boolean).join(' · ') || '—'}</td></tr>)}</tbody></>
        : <><thead><tr><th>Dispatch</th><th>Outward</th><th>Reports</th><th>Client</th><th>Mode</th><th>Consignment</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.results.map(d => <tr key={d.id}><td><strong>{d.number}</strong></td><td>{d.outward_date || '—'}</td><td>{d.reports || '—'}</td>
            <td>{d.client}</td><td>{d.mode}</td><td>{d.consignment || '—'}</td><td>{d.status}{d.delivered_date ? ` · ${d.delivered_date}` : ''}</td>
            <td><button className="link" onClick={() => onOpen(d.id)}>Open →</button></td></tr>)}</tbody></>}
      </table></div>
      {list.total === 0 && <p>Nothing here.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function SendForm({api, reports, resend, onBack, onSent}) {
  const [form, setForm] = useState({operation_id: crypto.randomUUID(), mode: 2, courier: '', other_courier: '', consignment_number: '',
    authorized_person: '', cost: '', outward_date: today(), town: '', status: 1, delivered_date: '', others: ''});
  const [reasons, setReasons] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm(f => ({...f, [k]: v}));
  const tracked = [1, 2, 6].includes(Number(form.mode));
  async function send(e) {
    e.preventDefault(); setBusy(true); setError('');
    const {others, ...rest} = form;
    try {
      const d = await api('dispatch/', {method: 'POST', body: JSON.stringify({...rest, reports: reports.map(r => r.valuation),
        other_documents: others.split(',').map(x => x.trim()).filter(Boolean), resend: resend ? reasons : {}})});
      onSent(d.id);
    } catch (err) {setError(err.message);} finally {setBusy(false);}
  }
  return <section className="panel"><form onSubmit={send}>
    <button type="button" className="link" onClick={onBack}>← Back</button>
    <h2>{resend ? 'Send again' : 'New dispatch'}</h2>
    <p>{reports.map(r => r.report_number).join(', ')}</p>
    {resend && reports.map(r => <label key={r.valuation}>Why is {r.report_number} being sent again?<span className="required"> *</span>
      <input value={reasons[r.valuation] || ''} required onChange={e => setReasons({...reasons, [r.valuation]: e.target.value})}/></label>)}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="form-grid">
      <label>Mode<select value={form.mode} onChange={e => set('mode', Number(e.target.value))}>{MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      {Number(form.mode) === 1 && <label>Courier<span className="required"> *</span><select value={form.courier} required onChange={e => set('courier', e.target.value)}>
        <option value="">Choose…</option>{COURIERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>}
      {Number(form.courier) === 3 && <label>Courier name<span className="required"> *</span><input value={form.other_courier} required onChange={e => set('other_courier', e.target.value)}/></label>}
      {tracked && <label>Consignment number<input value={form.consignment_number} onChange={e => set('consignment_number', e.target.value)}/><small className="muted">Required once in transit</small></label>}
      <label>Outward date<input type="date" value={form.outward_date} max={today()} onChange={e => set('outward_date', e.target.value)}/></label>
      <label>Status<select value={form.status} onChange={e => set('status', Number(e.target.value))}><option value={1}>Lying at HO</option><option value={2}>Under Transit</option><option value={3}>Delivered</option></select></label>
      {Number(form.status) === 3 && <label>Delivered on<span className="required"> *</span><input type="date" value={form.delivered_date} required max={today()} onChange={e => set('delivered_date', e.target.value)}/></label>}
      <label>Authorised person<input value={form.authorized_person} onChange={e => set('authorized_person', e.target.value)}/></label>
      <label>Cost<input inputMode="decimal" value={form.cost} onChange={e => set('cost', e.target.value)}/></label>
      <label>Town<input value={form.town} onChange={e => set('town', e.target.value)}/></label>
    </div>
    <label>Other documents (comma-separated)<input value={form.others} onChange={e => set('others', e.target.value)}/></label>
    <p className="actions"><button disabled={busy}>{busy ? 'Saving…' : 'Create dispatch'}</button></p>
  </form></section>;
}

function DispatchPage({api, id, onBack, onResend}) {
  const [d, setD] = useState(null);
  const [consignment, setConsignment] = useState('');
  const [delivered, setDelivered] = useState(today());
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {api(`dispatch/${id}/`).then(x => {setD(x); setConsignment(x.consignment_number);}).catch(e => setError(e.message));}, [id]);
  async function post(path, body) {
    setError('');
    try {setD(await api(`dispatch/${id}/${path}/`, {method: 'POST', body: JSON.stringify(body)}));} catch (e) {setError(e.message);}
  }
  if (!d) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to dispatch</button>
    <h2>{d.number} · {d.cancelled ? 'Cancelled' : d.status_label}</h2>
    <p>{d.mode_label}{d.courier_label ? ` · ${d.courier_label}` : ''}{d.other_courier ? ` (${d.other_courier})` : ''}{d.consignment_number ? ` · ${d.consignment_number}` : ''} · out {d.outward_date || '—'}{d.delivered_date ? ` · delivered ${d.delivered_date}` : ''}</p>
    <p>{d.client_name}{d.customer_name ? ` · ${d.customer_name}` : ''}{d.town ? ` · ${d.town}` : ''} · {d.document_count} document{d.document_count === 1 ? '' : 's'}</p>
    {d.cancelled && <p className="notice">Cancelled: {d.cancel_remark}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <h3>Reports</h3><ul>{d.items.map((i, n) => <li key={n}>{i.reference}{i.resend ? ` · sent again: ${i.resend_reason}` : ''}
      {d.status === 3 && i.valuation && <> · <button className="link" onClick={() => onResend({valuation: i.valuation, report_number: i.reference})}>Send again</button></>}</li>)}</ul>
    {d.other_documents.length > 0 && <p className="muted">Other documents: {d.other_documents.join(', ')}</p>}
    {d.next_statuses.length > 0 && <div className="panel inset"><h3>Update</h3><div className="form-grid">
      <label>Consignment number<input value={consignment} onChange={e => setConsignment(e.target.value)}/></label>
      {d.next_statuses.includes(3) && <label>Delivered on<input type="date" value={delivered} max={today()} onChange={e => setDelivered(e.target.value)}/></label>}</div>
      <p className="actions">{d.next_statuses.includes(2) && <button onClick={() => post('advance', {status: 2, consignment_number: consignment})}>Mark in transit</button>}
        {d.next_statuses.includes(3) && <button onClick={() => post('advance', {status: 3, consignment_number: consignment, delivered_date: delivered})}>Mark delivered</button>}</p></div>}
    {!d.cancelled && d.status !== 3 && <form className="panel inset" onSubmit={e => {e.preventDefault(); if (window.confirm('Cancel this dispatch? Its reports return to the awaiting list.')) post('cancel', {reason});}}>
      <h3>Cancel</h3><label>Reason<input value={reason} required onChange={e => setReason(e.target.value)}/></label><button disabled={!reason.trim()}>Cancel dispatch</button></form>}
  </section>;
}
