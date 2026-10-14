import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useState} from 'react';
import {FollowUpForm, useLookups} from './screens/IntakeForms.jsx';
import {uuid} from './lib/uuid.js';
import {today} from './lib/format.js';

const BUCKETS = [['to_invoice', 'To invoice'], ['unpaid', 'Unpaid'], ['paid', 'Paid'], ['cancelled', 'Cancelled'], ['offline', 'Offline']];
const rs = v => `₹ ${Number(v || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

export function Invoices({api}) {
  const [view, setView] = useState(null);       // {issue: valuationId} or {invoice: id}
  if (view?.issue) return <Issue api={api} valuation={view.issue} onBack={() => setView(null)} onIssued={id => setView({invoice: id})}/>;
  if (view?.invoice) return <Invoice api={api} id={view.invoice} onBack={() => setView(null)}/>;
  return <Queue api={api} onIssue={v => setView({issue: v})} onOpen={id => setView({invoice: id})}/>;
}

function Queue({api, onIssue, onOpen}) {
  const [state, setState] = useState('to_invoice');
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [due, setDue] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => api(`invoices/?state=${state}&q=${encodeURIComponent(q)}&page=${page}${state === 'offline' && due ? '&due=1' : ''}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [state, q, page, due]);
  const issuing = state === 'to_invoice', offline = state === 'offline';
  return <section className="panel">
    <div className="tabs">{BUCKETS.map(([k, l]) => <button key={k} className={k === state ? 'active' : ''} onClick={() => {setState(k); setPage(1);}}>
      {l}{list && <span className="count"> {list.counts[k].toLocaleString('en-IN')}</span>}</button>)}</div>
    <div className="toolbar"><label className="search">Search<input placeholder={issuing ? 'Report, lead or borrower' : offline ? 'Invoice, client, customer or reference' : 'Invoice, report or borrower'} value={q} onChange={e => {setQ(e.target.value); setPage(1);}}/></label>
      {offline && <label className="choice"><input type="checkbox" checked={due} onChange={e => {setDue(e.target.checked); setPage(1);}}/>Outstanding only{list && ` (${list.counts.offline_due.toLocaleString('en-IN')})`}</label>}</div>
    {offline && <p className="muted">Invoices raised outside the system in 2020–21 and recorded afterwards. They belong to no valuation; their lead and report numbers are kept as references.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <ResponsiveTable><table><thead><tr>{offline
        ? <><th>Invoice</th><th>Date</th><th>Billed to</th><th>Customer</th><th>Reference</th><th>Total</th><th>Outstanding</th><th></th></>
        : issuing
        ? <><th>Report</th><th>Lead</th><th>Borrower</th><th>Billed</th><th></th></>
        : <><th>Invoice</th><th>Date</th><th>Report</th><th>Borrower</th><th>Total</th><th>Outstanding</th><th></th></>}</tr></thead>
      <tbody>{list.results.map(r => offline
        ? <tr key={r.id}><td><strong>{r.number}</strong></td><td>{r.issued_on || '—'}</td><td>{r.billed_to}</td><td>{r.customer}</td>
            <td>{r.report_number || '—'}</td><td>{rs(r.total)}</td><td>{rs(r.remaining)}</td><td><button className="link" onClick={() => onOpen(r.id)}>Open →</button></td></tr>
        : issuing
        ? <tr key={r.valuation}><td><strong>{r.report_number}</strong></td><td>{r.lead_number}</td><td>{r.borrower}</td><td>{rs(r.total)}</td>
            <td><button className="link" onClick={() => onIssue(r.valuation)}>Invoice →</button></td></tr>
        : <tr key={r.id}><td><strong>{r.number}</strong></td><td>{r.issued_on || '—'}</td><td>{r.report_number}</td><td>{r.borrower}</td>
            <td>{rs(r.total)}</td><td>{rs(r.remaining)}</td><td><button className="link" onClick={() => onOpen(r.id)}>Open →</button></td></tr>)}</tbody></table></ResponsiveTable>
      {list.total === 0 && <p>Nothing here.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function Lines({lines, place}) {
  return <div className="table-wrap"><table><thead><tr><th>Particulars</th><th>Taxable</th>
    {place !== 'inter' && <><th>CGST 9%</th><th>SGST 9%</th></>}{place !== 'intra' && <th>IGST 18%</th>}<th>Total</th></tr></thead>
    <tbody>{lines.map((l, i) => <tr key={i}><td>{l.description}</td><td>{rs(l.amount)}</td>
      {place !== 'inter' && <><td>{rs(l.cgst)}</td><td>{rs(l.sgst)}</td></>}{place !== 'intra' && <td>{rs(l.igst)}</td>}<td>{rs(l.total)}</td></tr>)}</tbody></table></div>;
}

function Issue({api, valuation, onBack, onIssued}) {
  const [form, setForm] = useState({party: 1, place: '', other_gstin: '', account: '', due_date: '', payer: ''});
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const qs = `party=${form.party}&other_gstin=${encodeURIComponent(form.other_gstin)}${form.place ? `&place=${form.place}` : ''}`;
    api(`invoices/valuations/${valuation}/?${qs}`).then(d => {
      setDraft(d);
      setForm(f => ({...f, place: f.place || d.place, account: f.account || (d.accounts.find(a => a.code === 2)?.id ?? d.accounts[0]?.id ?? ''),
                     payer: f.payer || (d.default_payer ? String(d.default_payer) : '')}));
    }).catch(e => setError(e.message));
  }, [valuation, form.party, form.place, form.other_gstin]);
  if (!draft) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  const set = (k, v) => setForm(f => ({...f, [k]: v}));
  async function issue() {
    if (!window.confirm(`Issue a tax invoice for ${rs(draft.total)}? An issued invoice cannot be edited; it can only be reversed by a credit note.`)) return;
    setBusy(true); setError('');
    try {onIssued((await api(`invoices/valuations/${valuation}/`, {method: 'POST', body: JSON.stringify(form)})).id);}
    catch (e) {setError(e.message);} finally {setBusy(false);}
  }
  const blocked = draft.blockers.length > 0;
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to invoices</button>
    <h2>Invoice {draft.report_number}</h2>
    {draft.blockers.map(b => <p key={b} className="notice">{b}</p>)}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="form-grid">
      <label>Bill GSTIN of<select value={form.party} disabled={blocked} onChange={e => set('party', Number(e.target.value))}>
        <option value={1}>Client (bank)</option><option value={2}>Client customer (borrower)</option><option value={3}>Other party</option></select></label>
      {form.party === 3 && <label>Other GSTIN<input value={form.other_gstin} maxLength={15} onChange={e => set('other_gstin', e.target.value.toUpperCase())}/></label>}
      <label>Place of supply<select value={form.place} disabled={blocked} onChange={e => set('place', e.target.value)}>
        <option value="intra">Intra state (CGST + SGST)</option><option value="inter">Inter state (IGST)</option></select>
        <small className="muted">Suggested: {draft.suggested_place === 'intra' ? 'intra state' : 'inter state'}{draft.gstin ? ` (GSTIN ${draft.gstin})` : ' (no GSTIN on file)'}</small></label>
      <label>Paid into<select value={form.account} disabled={blocked} onChange={e => set('account', e.target.value)}>
        {draft.accounts.map(a => <option key={a.id} value={a.id}>{a.name} · {a.ifsc}</option>)}</select></label>
      <label>Due date<input type="date" value={form.due_date} min={today()} disabled={blocked} onChange={e => set('due_date', e.target.value)}/><small className="muted">Defaults to 15 days</small></label>
      <label>Paid by<select value={form.payer} disabled={blocked} onChange={e => set('payer', e.target.value)}>
        <option value="">—</option><option value="1">By Client</option><option value="2">By Client Customer</option></select></label>
    </div>
    <Lines lines={draft.lines} place={form.place}/>
    <table className="totals"><tbody>
      <tr><td>Taxable value</td><td>{rs(draft.taxable)}</td></tr><tr><td>GST</td><td>{rs(draft.tax)}</td></tr>
      <tr><td><strong>Invoice total</strong></td><td><strong>{rs(draft.total)}</strong></td></tr>
      <tr><td>Advance received</td><td>{rs(draft.advance)}</td></tr>
      <tr><td><strong>Balance due</strong></td><td><strong>{rs(draft.remaining)}</strong></td></tr>
      {Number(draft.excess) > 0 && <tr><td>Received in excess</td><td>{rs(draft.excess)}</td></tr>}
    </tbody></table>
    {!blocked && <p className="actions"><button disabled={busy} onClick={issue}>{busy ? 'Issuing…' : 'Issue invoice'}</button></p>}
  </section>;
}

export function Invoice({api, id, onBack}) {
  const [inv, setInv] = useState(null);
  // One operation ID per intended payment or write-off. It is kept when a request
  // fails, so resubmitting after a lost response is a safe retry the server
  // answers without booking the money again, and renewed only after success.
  // crypto.randomUUID exists only on secure pages; a phone on the office network over
  // plain http has none, and the invoice screen failed to open there.
  const newId = () => uuid();
  const [pay, setPay] = useState({amount: '', date: today(), mode: '', payer_name: '', operation_id: newId()});
  const [wo, setWo] = useState({amount: '', remark: '', operation_id: newId()});
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  useEffect(() => {api(`invoices/${id}/`).then(setInv).catch(e => setError(e.message));}, [id]);
  async function act(path, body, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(path); setError('');
    try {
      setInv(await api(`invoices/${id}/${path}/`, {method: 'POST', body: JSON.stringify(body)}));
      if (path === 'payments') setPay(p => ({...p, amount: '', operation_id: newId()}));
      if (path === 'write-off') setWo({amount: '', remark: '', operation_id: newId()});
      setReason('');
    }
    catch (e) {setError(e.message);} finally {setBusy('');}
  }
  if (!inv) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  const open = !inv.cancelled, owed = Number(inv.remaining) > 0;
  const disagrees = inv.recorded_excess !== inv.excess || inv.recorded_remaining !== inv.remaining;
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to invoices</button>
    <h2>{inv.number}{inv.cancelled ? ' · Cancelled' : ''}</h2>
    <p>{inv.report_number} · {inv.borrower} · issued {inv.issued_on || '—'}{inv.due_on ? ` · due ${inv.due_on}` : ''} · <span className="status">{inv.payment_status}</span></p>
    {inv.document && (inv.document.available ? <p><a href={`/api/invoices/${id}/document/`} target="_blank" rel="noopener">View the invoice (PDF)</a></p>
      : <p className="muted">The invoice's file could not be found in storage.</p>)}
    {inv.offline && <div className="notice">
      <p>Offline invoice, recorded from outside the system. Billed to <strong>{inv.billed_to.name}</strong>{inv.billed_to.branch ? `, ${inv.billed_to.branch}` : ''}{inv.billed_to.customer ? ` · customer ${inv.billed_to.customer}` : ''}.</p>
      <p className="muted">References (not linked to any record here): lead {inv.references.lead || '—'} · work order {inv.references.work_order || '—'} · report {inv.references.report || '—'}
        {inv.references.service ? ` · ${inv.references.service}${inv.references.subtype ? ' / ' + inv.references.subtype : ''}` : ''}{inv.references.liable ? ` · liable ${inv.references.liable}` : ''}</p>
      {inv.advance && Number(inv.advance) > 0 && <p className="muted">Advance received when raised: {rs(inv.advance)}</p>}
    </div>}
    {inv.number_shared > 0 && <p className="notice">Another offline invoice carries the same number, {inv.number}.</p>}
    {inv.cancelled && <p className="notice">Cancelled by credit note: {inv.cancel_reason}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <Lines lines={inv.lines} place={inv.place_of_supply.startsWith('Inter') ? 'inter' : inv.place_of_supply.startsWith('Intra') ? 'intra' : ''}/>
    <table className="totals"><tbody>
      <tr><td><strong>Invoice total</strong></td><td><strong>{rs(inv.total)}</strong></td></tr>
      <tr><td>Received</td><td>{rs(inv.paid)}</td></tr>
      {Number(inv.bad_debt) > 0 && <tr><td>Written off</td><td>{rs(inv.bad_debt)}{inv.bad_debt_remark && <small> · {inv.bad_debt_remark}</small>}</td></tr>}
      <tr><td><strong>Outstanding</strong></td><td><strong>{rs(inv.remaining)}</strong></td></tr>
      {Number(inv.excess) > 0 && <tr><td>Received in excess</td><td>{rs(inv.excess)}</td></tr>}
    </tbody></table>
    {disagrees && <p className="muted">The previous system recorded {rs(inv.recorded_remaining)} outstanding and {rs(inv.recorded_excess)} in excess. The figures above are recomputed from the total, receipts and write-offs.</p>}
    {open && owed && <form className="panel inset" onSubmit={e => {e.preventDefault(); act('payments', pay);}}>
      <h3>Record a payment</h3><div className="form-grid">
        <label>Amount<span className="required"> *</span><input inputMode="decimal" value={pay.amount} required onChange={e => setPay({...pay, amount: e.target.value})}/></label>
        <label>Date<input type="date" value={pay.date} max={today()} onChange={e => setPay({...pay, date: e.target.value})}/></label>
        <label>Mode<input value={pay.mode} placeholder="NEFT, cheque…" maxLength={40} onChange={e => setPay({...pay, mode: e.target.value})}/></label>
        <label>Paid by<input value={pay.payer_name} maxLength={300} onChange={e => setPay({...pay, payer_name: e.target.value})}/></label></div>
      <button disabled={busy === 'payments' || !pay.amount}>{busy === 'payments' ? 'Saving…' : 'Record payment'}</button></form>}
    {open && owed && <form className="panel inset" onSubmit={e => {e.preventDefault(); act('write-off', wo, `Write off ${rs(wo.amount)} as bad debt?`);}}>
      <h3>Write off as bad debt</h3><div className="form-grid">
        <label>Amount<input inputMode="decimal" value={wo.amount} required onChange={e => setWo({...wo, amount: e.target.value})}/></label>
        <label>Reason<input value={wo.remark} required onChange={e => setWo({...wo, remark: e.target.value})}/></label></div>
      <button disabled={busy === 'write-off' || !wo.amount || !wo.remark.trim()}>Write off</button></form>}
    {open && <form className="panel inset" onSubmit={e => {e.preventDefault(); act('credit-note', {reason}, 'Cancel this invoice with a credit note? The invoice stays on record and cannot be reinstated.');}}>
      <h3>Cancel with a credit note</h3>
      <label>Reason<span className="required"> *</span><input value={reason} required onChange={e => setReason(e.target.value)}/></label>
      <button disabled={busy === 'credit-note' || !reason.trim()}>Issue credit note</button></form>}
    <RecoveryFollowUps api={api} id={id} rows={inv.follow_ups || []} owed={owed}/>
    {inv.payments.length > 0 && <><h3>Payments</h3><ul>{inv.payments.map((p, i) => <li key={i}>{p.on || '—'} · {rs(p.amount)}{p.mode ? ` · ${p.mode}` : ''}{p.by ? ` · ${p.by}` : ''}{p.recorded === 'previous system' && <small className="muted"> · recorded in the previous system</small>}</li>)}</ul></>}
    {inv.credit_notes.length > 0 && <><h3>Credit notes</h3><ul>{inv.credit_notes.map(c => <li key={c.id}>{c.number} · {c.on} · {rs(c.total)}
      {Number(c.refund_due) > 0 && ` · ${rs(c.refund_due)} to refund`} · {c.reason}
      {c.document?.available && <> · <a href={`/api/invoices/credit-notes/${c.id}/document/`} target="_blank" rel="noopener">PDF</a></>}</li>)}</ul></>}
  </section>;
}

// Recovery follow-up (legacy /amount_received, design/payment_info): calls chasing the
// invoice's payment, on the same form as a lead's follow-up.
function RecoveryFollowUps({api, id, rows: initial, owed}) {
  const {data: lookups} = useLookups();
  const [rows, setRows] = useState(initial);
  useEffect(() => setRows(initial), [initial]);
  const label = code => (lookups?.follow_up_statuses || []).find(s => String(s.code) === String(code))?.label || code;
  return <section className="recovery">
    {owed && <FollowUpForm onSave={async data => setRows((await api(`invoices/${id}/follow-ups/`, {method: 'POST', body: JSON.stringify(data)})).follow_ups)}/>}
    {rows.length > 0 && <><h3>Recovery follow-ups</h3><ul>{rows.map(f => <li key={f.id}><strong>{label(f.call_status)}</strong>
      {(f.logged_date_text || '').slice(0, 10) && ` · call back ${(f.logged_date_text || '').slice(0, 10)} ${f.logged_time_text || ''}`} · {f.remark}</li>)}</ul></>}
  </section>;
}

