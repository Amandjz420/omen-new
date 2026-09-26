import React, {useEffect, useState} from 'react';

const STAGES = [['to_check', 'To check'], ['to_verify', 'To verify'], ['verified', 'Verified'], ['voided', 'Voided']];
const AS = [[2, 'Recovery against an invoice'], [1, 'Advance'], [3, 'Other']];
const MODES = [[4, 'Netbanking'], [5, 'UPI'], [1, 'Cash'], [2, 'Cheque'], [3, 'Draft']];
const rs = v => `₹ ${Number(v || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
const today = () => new Date().toISOString().slice(0, 10);
const blank = () => ({operation_id: crypto.randomUUID(), received_as: 2, invoice: '', amount: '', received_date: today(),
  amount_received_on: '', payment_mode: 4, cheque_draft_number: '', cheque_draft_bank: '', issue_date: '', in_favour_of: '',
  payer_name: '', mobile: '', remark: '', description: ''});

export function Receipts({api}) {
  const [view, setView] = useState(null);           // 'new' or a receipt id
  if (view === 'new') return <ReceiptForm api={api} onBack={() => setView(null)} onSaved={id => setView(id)}/>;
  if (view) return <Receipt api={api} id={view} onBack={() => setView(null)}/>;
  return <Queue api={api} onOpen={setView} onNew={() => setView('new')}/>;
}

function Queue({api, onOpen, onNew}) {
  const [stage, setStage] = useState('to_check');
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  useEffect(() => {
    const t = setTimeout(() => api(`receipts/?stage=${stage}&q=${encodeURIComponent(q)}&page=${page}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [stage, q, page]);
  return <section className="panel">
    <div className="tabs">{STAGES.map(([k, l]) => <button key={k} className={k === stage ? 'active' : ''} onClick={() => {setStage(k); setPage(1);}}>
      {l}{list && <span className="count"> {list.counts[k].toLocaleString('en-IN')}</span>}</button>)}</div>
    <div className="toolbar"><label className="search">Search<input placeholder="Receipt, payer, invoice or cheque number" value={q} onChange={e => {setQ(e.target.value); setPage(1);}}/></label>
      <button onClick={onNew}>New receipt</button></div>
    <p className="muted">A receipt counts only once it has been made, checked and verified. A recovery settles its invoice at verification.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <div className="table-wrap"><table><thead><tr><th>Receipt</th><th>Date</th><th>Type</th><th>Payer</th><th>Invoice</th><th>Mode</th><th>Amount</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.id}><td><strong>{r.number}</strong></td><td>{r.received_date || '—'}</td><td>{r.received_as}</td>
        <td>{r.payer}</td><td>{r.invoice || '—'}</td><td>{r.mode}</td><td>{rs(r.amount)}</td>
        <td><button className="link" onClick={() => onOpen(r.id)}>Open →</button></td></tr>)}</tbody></table></div>
      {list.total === 0 && <p>Nothing here.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function InvoicePicker({api, value, onPick}) {
  const [q, setQ] = useState('');
  const [found, setFound] = useState([]);
  useEffect(() => {
    if (q.trim().length < 3) {setFound([]); return;}
    const t = setTimeout(() => Promise.all(['unpaid', 'offline'].map(s => api(`invoices/?state=${s}&q=${encodeURIComponent(q)}`)))
      .then(([a, b]) => setFound([...a.results, ...b.results].slice(0, 12))).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [q]);
  return <label>Invoice<span className="required"> *</span>
    <input placeholder="Type 3+ characters of the invoice number or borrower" value={q} onChange={e => setQ(e.target.value)}/>
    {value?.number && <small>Chosen: {value.number}{value.remaining ? ` · ${rs(value.remaining)} outstanding` : ''}</small>}
    {found.length > 0 && <ul className="picker">{found.map(i => <li key={i.id}><button type="button" className="link"
      onClick={() => {onPick(i); setQ(''); setFound([]);}}>{i.number} · {i.borrower || i.billed_to || ''} · {rs(i.remaining)} outstanding</button></li>)}</ul>}
  </label>;
}

function ReceiptForm({api, id, initial, onBack, onSaved}) {
  const [form, setForm] = useState(initial || blank());
  const [chosen, setChosen] = useState(initial?.invoiceInfo || null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm(f => ({...f, [k]: v}));
  const recovery = Number(form.received_as) === 2, instrument = [2, 3].includes(Number(form.payment_mode));
  async function save(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      // The operation ID stays the same if this fails, so resubmitting is a safe retry.
      const body = JSON.stringify({...form, invoice: recovery ? form.invoice : ''});
      const r = await api(id ? `receipts/${id}/` : 'receipts/', {method: id ? 'PUT' : 'POST', body});
      onSaved(r.id);
    } catch (err) {setError(err.message);} finally {setBusy(false);}
  }
  return <section className="panel"><form onSubmit={save}>
    <button type="button" className="link" onClick={onBack}>← Back</button>
    <h2>{id ? 'Correct receipt' : 'New receipt'}</h2>
    {id && <p className="notice">A corrected receipt must be checked again.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="form-grid">
      <label>Received as<select value={form.received_as} onChange={e => set('received_as', Number(e.target.value))}>{AS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      {recovery && <InvoicePicker api={api} value={chosen} onPick={i => {setChosen(i); set('invoice', i.id);}}/>}
      <label>Amount<span className="required"> *</span><input inputMode="decimal" value={form.amount} required onChange={e => set('amount', e.target.value)}/></label>
      <label>Receipt date<input type="date" value={form.received_date || ''} max={today()} onChange={e => set('received_date', e.target.value)}/></label>
      <label>Money arrived on<input type="date" value={form.amount_received_on || ''} max={today()} onChange={e => set('amount_received_on', e.target.value)}/></label>
      <label>Paid by<select value={form.payment_mode} onChange={e => set('payment_mode', Number(e.target.value))}>{MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      {instrument && <><label>Cheque / draft number<span className="required"> *</span><input value={form.cheque_draft_number} required onChange={e => set('cheque_draft_number', e.target.value)}/></label>
        <label>Drawn on bank<span className="required"> *</span><input value={form.cheque_draft_bank} required onChange={e => set('cheque_draft_bank', e.target.value)}/></label>
        <label>Cheque / draft date<input type="date" value={form.issue_date || ''} max={today()} onChange={e => set('issue_date', e.target.value)}/></label>
        <label>In favour of<input value={form.in_favour_of} onChange={e => set('in_favour_of', e.target.value)}/></label></>}
      <label>Payer<span className="required"> *</span><input value={form.payer_name} required maxLength={300} onChange={e => set('payer_name', e.target.value)}/></label>
      <label>Payer's mobile<input value={form.mobile} maxLength={20} onChange={e => set('mobile', e.target.value)}/></label>
    </div>
    <label>Description<input value={form.description} maxLength={500} onChange={e => set('description', e.target.value)}/></label>
    <label>Remark<textarea rows={2} value={form.remark} onChange={e => set('remark', e.target.value)}/></label>
    <p className="actions"><button disabled={busy || (recovery && !form.invoice)}>{busy ? 'Saving…' : id ? 'Save correction' : 'Record receipt'}</button></p>
  </form></section>;
}

function Receipt({api, id, onBack}) {
  const [r, setR] = useState(null);
  const [reason, setReason] = useState('');
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const load = () => api(`receipts/${id}/`).then(setR).catch(e => setError(e.message));
  useEffect(() => {load();}, [id]);
  async function act(action, body = {}) {
    setBusy(action); setError('');
    try {setR(await api(`receipts/${id}/${action}/`, {method: 'POST', body: JSON.stringify(body)}));}
    catch (e) {
      // An overpayment is allowed, but only when confirmed.
      if (action === 'verify' && !body.confirm_overpayment && /outstanding/.test(e.message) && window.confirm(`${e.message}\n\nVerify anyway?`)) {
        setBusy(''); return act('verify', {confirm_overpayment: true});
      }
      setError(e.message);
    } finally {setBusy('');}
  }
  if (!r) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  if (editing) return <ReceiptForm api={api} id={id} onBack={() => setEditing(false)} onSaved={() => {setEditing(false); load();}}
    initial={{...r, invoice: r.invoice?.id || '', invoiceInfo: r.invoice, operation_id: crypto.randomUUID()}}/>;
  const open = ['to_check', 'to_verify'].includes(r.stage);
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to receipts</button>
    <h2>{r.number} · {rs(r.amount)}</h2>
    <p>{r.received_as_label} · {r.payment_mode_label}{r.cheque_draft_number ? ` ${r.cheque_draft_number} (${r.cheque_draft_bank})` : ''} · from {r.payer_name || '—'} · {r.received_date || '—'}
      <span className="status"> {STAGES.find(([k]) => k === r.stage)[1]}</span></p>
    {r.invoice && <p>Against invoice <strong>{r.invoice.number}</strong> · total {rs(r.invoice.total)} · paid so far {rs(r.invoice.paid)}{r.invoice.cancelled ? ' · cancelled' : ''}</p>}
    <div className="track-status">
      <div className="done"><strong>Made</strong><small>{r.maker || '—'}</small></div>
      <div className={r.checked_by || r.checked_at ? 'done' : ''}><strong>Checked</strong><small>{r.checked_by || (r.checked_at ? 'yes' : 'pending')}</small></div>
      <div className={r.verified_by || r.verified_at ? 'done' : ''}><strong>Verified</strong><small>{r.verified_by || (r.verified_at ? 'yes' : 'pending')}</small></div>
    </div>
    {r.same_person.length > 0 && <p className="muted">The same person was {r.same_person.join(', ')}.</p>}
    {r.stage === 'voided' && <p className="notice">Voided{r.voided_by ? ` by ${r.voided_by}` : ''}: {r.void_reason}</p>}
    {r.absorbs_legacy_entries > 0 && <p className="muted">This receipt also appears in the previous system's amount-received records; that copy is not counted.</p>}
    {r.remark && <p className="muted">Remark: {r.remark}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {open && <p className="actions">
      {r.stage === 'to_check' && <button disabled={!!busy} onClick={() => act('check')}>Check</button>}
      {r.stage === 'to_verify' && <button disabled={!!busy} onClick={() => act('verify')}>{r.received_as === 2 ? 'Verify and settle invoice' : 'Verify'}</button>}
      <button className="link" onClick={() => setEditing(true)}>Correct details</button></p>}
    {open && <form className="panel inset" onSubmit={e => {e.preventDefault(); if (window.confirm('Void this receipt? It stays on record but never counts.')) act('void', {reason});}}>
      <h3>Void</h3><label>Reason<span className="required"> *</span><input value={reason} required onChange={e => setReason(e.target.value)}/></label>
      <button disabled={busy === 'void' || !reason.trim()}>Void receipt</button></form>}
  </section>;
}
