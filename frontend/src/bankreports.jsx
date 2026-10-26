import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useState} from 'react';
import {dateTime, today} from './lib/format.js';
import {confirmAction} from './components/confirm.jsx';

const rupees = v => v === '' || v == null ? '' : Number(v).toLocaleString('en-IN', {maximumFractionDigits: 0});

export function BankReports({api}) {
  const [open, setOpen] = useState(null);
  return open ? <ReportForm api={api} id={open} onBack={() => setOpen(null)}/> : <Queue api={api} onOpen={setOpen}/>;
}

function Queue({api, onOpen}) {
  const [state, setState] = useState('pending');
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  useEffect(() => {
    const t = setTimeout(() => api(`bank-reports/?state=${state}&q=${encodeURIComponent(q)}&page=${page}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [state, q, page]);
  return <section className="panel">
    <div className="tabs">{[['pending', 'Ready for a report'], ['generated', 'Report generated']].map(([k, l]) =>
      <button key={k} className={k === state ? 'active' : ''} onClick={() => {setState(k); setPage(1);}}>{l}{list && <span className="count"> {list.counts[k]}</span>}</button>)}</div>
    <p className="muted">Only valuations with all four verifications appear here.</p>
    <div className="toolbar"><label className="search">Search<input placeholder="Report, lead or borrower" value={q} onChange={e => {setQ(e.target.value); setPage(1);}}/></label></div>
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <ResponsiveTable><table><thead><tr><th>Report</th><th>Lead</th><th>Borrower</th><th>Service</th><th>Submitted</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.id}><td><strong>{r.report_number}</strong></td><td>{r.lead_number}</td><td>{r.borrower}</td>
        <td>{r.service}</td><td>{r.submitted_at ? dateTime(r.submitted_at) : (r.submitted_on || '—')}</td><td><button className="link" onClick={() => onOpen(r.id)}>{state === 'pending' ? 'Prepare →' : 'Open →'}</button></td></tr>)}</tbody></table></ResponsiveTable>
      {list.total === 0 && <p>Nothing here.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

export function ReportForm({api, id, onBack}) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({});
  const [banks, setBanks] = useState([]);
  const [branches, setBranches] = useState([]);
  const [branchQuery, setBranchQuery] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const adopt = d => {setData(d); setForm({...d.values, report_date: d.values.report_date || today()});};
  useEffect(() => {api(`bank-reports/${id}/`).then(adopt).catch(e => setError(e.message));}, [id]);
  useEffect(() => {if (data?.bank_client) api('bank-reports/banks/').then(r => setBanks(r.banks)).catch(() => {});}, [data?.bank_client]);
  useEffect(() => {
    if (!form.bank) {setBranches([]); return;}
    const t = setTimeout(() => api(`bank-reports/branches/?bank=${form.bank}&q=${encodeURIComponent(branchQuery)}`)
      .then(r => setBranches(r.branches)).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [form.bank, branchQuery]);
  if (!data) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  const set = (k, v) => setForm(f => ({...f, [k]: v}));
  const blocked = data.blockers.length > 0;
  async function generate(e) {
    e.preventDefault();
    if (!(await confirmAction({title: 'Are you sure you want to submit the report?', confirmLabel: data.report ? 'Regenerate report' : 'Generate report',
      consequence: data.report ? 'The bank report is generated again from the values below, replacing the current version.' : 'The bank report is generated from the values below.'}))) return;
    setSaving(true); setError('');
    try {adopt(await api(`bank-reports/${id}/`, {method: 'PUT', body: JSON.stringify(form)}));}
    catch (err) {setError(err.message);} finally {setSaving(false);}
  }
  // The values are required for a property valuation only (values_required).
  const amount = (k, label, required = data.values_required !== false) => <label>{label}{required && <span className="required"> *</span>}
    <input inputMode="decimal" value={form[k] ?? ''} disabled={blocked} required={required} onChange={e => set(k, e.target.value)}/>
    {form[k] !== '' && form[k] != null && <small className="muted">Rs. {rupees(form[k])}</small>}</label>;
  const text = (k, label, required = false) => <label>{label}{required && <span className="required"> *</span>}
    <input value={form[k] || ''} disabled={blocked} required={required} maxLength={150} onChange={e => set(k, e.target.value)}/></label>;
  return <section className="panel">
    <button className="link" onClick={onBack}>← Back to bank reports</button>
    <h2>Bank report · {data.report_number}{data.report?.revision ? ` · Revision ${data.report.revision}` : ''}</h2>
    {data.blockers.map(b => <p key={b} className="notice">{b}</p>)}
    {data.report?.stale && <p className="notice">The valuation has changed since this report was generated, so it no longer matches. Regenerate it before approval.</p>}
    {data.template_error && <p className="error">{data.template_error}</p>}
    {data.template && <p className="muted">Using the report template with {data.template.lines} lines.</p>}
    {data.report?.document && <p>{data.report.document.available
      ? <a href={`/api/bank-reports/${id}/document/`} target="_blank" rel="noopener">View the report (PDF)</a>
      : <span className="muted">The report's file could not be found in storage.</span>}
      {data.report.generated_at && <small className="muted"> · generated {dateTime(data.report.generated_at)}{data.report.generated_by ? ` by ${data.report.generated_by}` : ''}</small>}</p>}
    {data.report && <Liable api={api} id={id} liable={data.report.liable} onChanged={adopt}/>}
    {error && <p role="alert" className="error">{error}</p>}
    <form onSubmit={generate}>
      <h3>Assessed values</h3>
      <div className="form-grid">{amount('market_fair_amount', 'Fair market value')}{amount('realisable_value_amount', 'Realisable value')}
        {amount('distress_value_amount', 'Distress value')}{amount('book_value_amount', 'Book value', false)}</div>
      {!data.report && Object.keys(data.prefilled_from || {}).length > 0 && <p className="notice">
        Filled in from the valuation form ({[...new Set(Object.values(data.prefilled_from))].join('; ')}). Check them before generating; they can be changed.</p>}
      <p className="muted">Values are written out in words on the report automatically.</p>
      <h3>References</h3>
      <div className="form-grid">{text('our_reference', 'Our reference', true)}{text('your_reference', "Bank's reference", true)}
        {text('unique_reference', 'Unique reference')}{text('omen_id', 'OMEN ID')}
        <label>Report date<input type="date" value={form.report_date || ''} max={today()} disabled={blocked} onChange={e => set('report_date', e.target.value)}/></label></div>
      {data.bank_client && <><h3>Addressed to</h3>
        <div className="form-grid">
          <label>Bank<span className="required"> *</span><select value={form.bank || ''} disabled={blocked} required onChange={e => {set('bank', e.target.value); set('branch', '');}}>
            <option value="">Choose…</option>{banks.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
          <label>Find branch<input value={branchQuery} disabled={blocked || !form.bank} placeholder="Name, IFSC or city" onChange={e => setBranchQuery(e.target.value)}/></label>
          <label>Branch<span className="required"> *</span><select value={form.branch || ''} disabled={blocked || !form.bank} required onChange={e => set('branch', e.target.value)}>
            {/* The branch filled in from the office is a real option. It was shown on the
                empty placeholder instead, so the form looked complete but sent no branch,
                and the browser refused it: "Please select an item in the list". */}
            <option value="">Choose…</option>
            {form.branch && !branches.some(b => String(b.id) === String(form.branch)) &&
              <option value={form.branch}>{data.branch_name || 'The chosen branch'}</option>}
            {branches.map(b => <option key={b.id} value={b.id}>{b.name}{b.ifsc ? ` · ${b.ifsc}` : ''}{b.city ? ` · ${b.city}` : ''}</option>)}</select></label>
          <label>IFSC code<input value={(branches.find(b => String(b.id) === String(form.branch))?.ifsc
            || (String(form.branch || '') === String(data.values.branch || '') ? data.ifsc : '') || '').toUpperCase()} readOnly disabled/></label>
        </div>
        <p className="muted">The report's bank chooses the template, and can differ from the office's bank.</p></>}
      <label>Certificate<textarea rows={3} value={form.certificate || ''} disabled={blocked} onChange={e => set('certificate', e.target.value)}/></label>
      {!blocked && <p className="actions"><button disabled={saving || !data.template}>{saving ? 'Generating…' : (data.report ? 'Regenerate report' : 'Generate report')}</button></p>}
    </form>
    {data.superseded.length > 0 && <><h3>Earlier versions</h3><ul>{data.superseded.map(s => <li key={s.revision}>
      Revision {s.revision} · superseded {new Date(s.superseded_at).toLocaleDateString('en-IN')}</li>)}</ul></>}
  </section>;
}

// Who the report's billing and recovery is credited to: the lead's assignee when it was
// generated; changed here, with a reason, as the legacy Change liable FA.
function Liable({api, id, liable, onChanged}) {
  const [open, setOpen] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [form, setForm] = useState({employee: '', reason: ''});
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => {if (open && !employees.length) api('intake/catalog/').then(c => setEmployees(c.employees || [])).catch(e => setError(e.message));}, [open]);
  async function save(e) {
    e.preventDefault(); setSaving(true); setError('');
    try {onChanged(await api(`bank-reports/${id}/liable/`, {method: 'POST', body: JSON.stringify(form)})); setOpen(false); setForm({employee: '', reason: ''});}
    catch (err) {setError(err.message);} finally {setSaving(false);}
  }
  return <div className="liable">
    <p>Liable assessor: <strong>{liable?.name || 'Not recorded'}</strong>{' '}
      {!open && <button type="button" className="link" onClick={() => setOpen(true)}>Change</button>}</p>
    {open && <form className="panel inset" onSubmit={save}>
      <h3>Change liable assessor</h3>
      <div className="form-grid">
        <label>New liable assessor<span className="required"> *</span>
          <select required value={form.employee} onChange={e => setForm(f => ({...f, employee: e.target.value}))}>
            <option value="">Select…</option>
            {employees.filter(x => String(x.id) !== String(liable?.id)).map(x => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select></label>
        <label>Reason<span className="required"> *</span>
          <textarea required value={form.reason} onChange={e => setForm(f => ({...f, reason: e.target.value}))}/></label>
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      <button disabled={saving || !form.employee || !form.reason.trim()}>Save</button>{' '}
      <button type="button" className="link" onClick={() => {setOpen(false); setError('');}}>Cancel</button>
    </form>}
  </div>;
}

