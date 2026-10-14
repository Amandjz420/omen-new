import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useState} from 'react';
import {Standing} from './approvals.jsx';
import {SiteChecklist} from './screens/SiteChecklist.jsx';

const FILTERS = [['', 'Active work'], ['not_started', 'Not started'], ['Pending', 'Pending'], ['Revert', 'Reverted'],
                 ['Hold', 'On hold'], ['Submit', 'Submitted'], ['Cancel', 'Cancelled']];
const LABELS = {Pending: 'Pending', Revert: 'Reverted — needs correction', Hold: 'On hold', Submit: 'Submitted', Cancel: 'Cancelled'};

// Mirrors number() and js_round() on the server: strip non-numeric characters,
// then parse; the formula rounds halves up, as the legacy page's Math.round did.
// The server recomputes on save, so this is a preview, not the stored value.
const num = v => {const n = parseFloat(String(v ?? '').replace(/[^0-9.\-]/g, '')); return Number.isFinite(n) ? n : null;};
function withFormula(cells, columns) {
  const [a, b, c] = ['A', 'B', 'C'].map(x => num(cells[columns[x]]));
  if (a === null || b === null || c === null || !columns.D) return cells;
  return {...cells, [columns.D]: String(Math.round((a * b) * (1 - c / 100)))};
}

export function Valuations({api}) {
  const [open, setOpen] = useState(null);
  return open ? <ValuationForm api={api} id={open} onBack={() => setOpen(null)}/> : <Queue api={api} onOpen={setOpen}/>;
}

function Queue({api, onOpen}) {
  const [list, setList] = useState(null);
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => api(`valuations/?status=${status}&q=${encodeURIComponent(q)}&page=${page}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(timer);
  }, [status, q, page]);

  async function start(row) {
    setBusy(row.case); setError('');
    try {onOpen((await api(`valuations/cases/${row.case}/`, {method: 'POST', body: '{}'})).id);}
    catch (e) {setError(e.message);} finally {setBusy('');}
  }

  return <section className="panel">
    <div className="toolbar">
      <label className="search">Search<input placeholder="Lead, borrower, work order or report number" value={q}
        onChange={e => {setQ(e.target.value); setPage(1);}}/></label>
      <label>Show<select value={status} onChange={e => {setStatus(e.target.value); setPage(1);}}>
        {FILTERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
    </div>
    {list?.scoped && <p className="notice">Showing only the leads assigned to you.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading valuations…</p> : <>
      <ResponsiveTable><table><thead><tr><th>Lead</th><th>Borrower</th><th>Work order</th><th>Service</th><th>District</th><th>Valuation</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.case}>
        <td><strong>{r.lead_number}</strong></td><td>{r.borrower}</td><td>{r.work_order || '—'}</td>
        <td>{r.service}<small>{r.subtype}</small></td><td>{r.district || '—'}</td>
        <td>{r.valuation ? <><span className="status">{LABELS[r.valuation.status] || r.valuation.status}</span>{r.valuation.report_number && <small>{r.valuation.report_number}</small>}</> : <span className="muted">Not started</span>}</td>
        <td>{r.valuation
          ? <button className="link" onClick={() => onOpen(r.valuation.id)}>Open →</button>
          : <button disabled={busy === r.case} onClick={() => start(r)}>{busy === r.case ? 'Starting…' : 'Start valuation'}</button>}</td>
      </tr>)}</tbody></table></ResponsiveTable>
      {list.total === 0 && <p>No matching valuations.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} cases · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function ValuationForm({api, id, onBack}) {
  const [head, setHead] = useState(null);
  const [key, setKey] = useState(null);
  const [section, setSection] = useState(null);
  const [draft, setDraft] = useState({});
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {api(`valuations/${id}/`).then(v => {setHead(v); setKey(v.sections[0]?.key || null);}).catch(e => setError(e.message));}, [id]);
  useEffect(() => {
    if (!key || key.startsWith('__')) {setDirty(false); return;}
    setSection(null); setSaved('');
    api(`valuations/${id}/sections/${key}/`).then(s => {
      setSection(s); setDirty(false); setChanged(new Set());
      setDraft(Object.fromEntries(s.questions.map(q => [q.id, structuredClone(q.answer)])));
    }).catch(e => setError(e.message));
  }, [key]);

  function choose(next) {
    if (dirty && !window.confirm('Leave this section without saving your changes?')) return;
    setKey(next);
    // On a phone the questions start a screen below the picker, and on desktop a long
    // section leaves the page scrolled far down: bring the chosen section's start into
    // view whenever it is off screen.
    requestAnimationFrame(() => {
      const body = document.querySelector('.section-body');
      const top = body?.getBoundingClientRect().top;
      if (body && (top < 0 || top > window.innerHeight * 0.6)) body.scrollIntoView({block: 'start'});
    });
  }
  // Only questions the user changed are sent; an untouched question is never
  // rewritten, so opening and saving a section cannot alter historical answers.
  const [changed, setChanged] = useState(new Set());
  const edit = (qid, answer) => {setDraft(d => ({...d, [qid]: answer})); setChanged(c => new Set(c).add(qid)); setDirty(true); setSaved('');};

  async function save() {
    const edited = section.questions.filter(q => changed.has(q.id));
    const conflicting = edited.filter(q => q.conflicts?.length);
    if (conflicting.length && !window.confirm(`${conflicting.map(q => `"${q.text}"`).join(', ')} ${conflicting.length > 1 ? 'hold' : 'holds'} conflicting answers from the previous system. Saving replaces them with what you entered. Continue?`)) return;
    setSaving(true); setError('');
    try {
      const answers = edited.map(q => ({question: q.id, ...draft[q.id], ...(q.conflicts?.length ? {resolve: true} : {})}));
      const result = await api(`valuations/${id}/sections/${key}/`, {method: 'PUT', body: JSON.stringify({answers})});
      setSection(result); setDirty(false); setChanged(new Set());
      setDraft(Object.fromEntries(result.questions.map(q => [q.id, structuredClone(q.answer)])));
      setHead(h => ({...h, sections: result.sections}));
      setSaved('Saved');
    } catch (e) {setError(e.message);} finally {setSaving(false);}
  }

  if (!head) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading valuation…</p>}</section>;
  const readOnly = !head.editable;
  return <section className="panel">
    <button className="link" onClick={() => {if (!dirty || window.confirm('Leave without saving?')) onBack();}}>← Back to valuations</button>
    <h2>{head.report_number || 'Valuation in progress'}</h2>
    {head.editable && <p><a href={`/valuations/${head.id}/form`}>Answer on a phone, by voice or from documents</a></p>}
    <p>{head.lead_number} · {head.borrower} · {head.work_order}</p>
    <p className="muted">{head.service}{head.subtype ? ` / ${head.subtype}` : ''}{head.bank ? ` · ${head.bank}` : ''}{head.asset ? ` · ${head.asset}` : ''}</p>
    <p><span className="status">{LABELS[head.status] || head.status}</span></p>
    <Standing api={api} id={id} onChange={next => setHead(h => ({...h, status: next.status, editable: ['Pending', 'Revert'].includes(next.status)}))}/>
    {readOnly && <p className="notice">This valuation is {(LABELS[head.status] || head.status).toLowerCase()} and cannot be edited.</p>}
    {head.status === 'Revert' && <p className="notice">This valuation was sent back for correction. Update the answers, then resubmit.</p>}
    <p className="muted">Some forms include a section for each bank. Complete the common parts and the section for {head.bank || 'this case\u2019s bank'} only.</p>
    <SiteChecklist id={id} unsaved={dirty} onQuestion={q => choose(q.section_key)}/>
    <div className="valuation-layout">
      <label className="mobile-section-picker">Valuation section
        <select value={key || ''} onChange={e => choose(e.target.value)}>
          {!key && <option value="" disabled>Choose a section</option>}
          {head.sections.map(s => <option key={s.key} value={s.key}>{s.name} ({s.answered}/{s.questions})</option>)}
          <option value="__billing">Billing</option><option value="__photos">Photos</option>
          <option value="__submit">{head.status === 'Submit' ? 'Submission' : 'Submit'}</option>
        </select>
      </label>
      <nav className="sections" aria-label="Valuation sections">{head.sections.map(s => <button key={s.key} className={s.key === key ? 'active' : ''} onClick={() => choose(s.key)}>
        <span>{s.name}</span>
        <small>{s.answered}/{s.questions}{s.required ? ` · required ${s.required_answered}/${s.required}` : ''}</small>
      </button>)}
        {[['__billing', 'Billing'], ['__photos', 'Photos'], ['__submit', head.status === 'Submit' ? 'Submission' : 'Submit']].map(([k, label]) => <button key={k} className={k === key ? 'active' : ''} onClick={() => choose(k)}><span>{label}</span></button>)}
      </nav>
      <div className="section-body">
        {error && <p role="alert" className="error">{error}</p>}
        {key === '__billing' ? <Billing api={api} id={id}/> : key === '__photos' ? <><Photos api={api} id={id}/><DocumentHistory api={api} id={id}/></> :
        key === '__submit' ? <Submission api={api} id={id} onJump={choose} onDone={setHead}/> :
        !section ? <p>Loading section…</p> : <>
          {section.questions.map(q => <Question key={q.id} q={q} value={draft[q.id]} readOnly={readOnly} onChange={a => edit(q.id, a)}
            files={q.document ? {api, id, dirty, reload: () => api(`valuations/${id}/sections/${key}/`).then(setSection)} : null}/>)}
          {!readOnly && <p className="actions"><button disabled={saving || !dirty} onClick={save}>{saving ? 'Saving…' : 'Save section'}</button>
            {saved && <span className="muted">{saved}</span>}{dirty && <span className="muted">Unsaved changes</span>}</p>}
        </>}
      </div>
    </div>
  </section>;
}

function Documents({q, selected, readOnly, files}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const byOption = Object.fromEntries((q.documents || []).map(d => [d.option, d.file]));
  async function attach(optionId, file) {
    setBusy(optionId); setError('');
    const form = new FormData();
    form.append('question', q.id); form.append('option', optionId); form.append('file', file);
    try {await files.api(`valuations/${files.id}/documents/`, {method: 'POST', body: form}); await files.reload();}
    catch (e) {setError(e.message);} finally {setBusy('');}
  }
  async function detach(optionId) {
    setBusy(optionId); setError('');
    try {await files.api(`valuations/${files.id}/documents/?question=${q.id}&option=${optionId}`, {method: 'DELETE'}); await files.reload();}
    catch (e) {setError(e.message);} finally {setBusy('');}
  }
  const chosen = q.options.filter(o => selected.has(o.id));
  if (!chosen.length) return null;
  return <div className="documents">
    <small className="muted">Attach a document for each chosen item{files.dirty ? ' — save the section first' : ''}.</small>
    {error && <p role="alert" className="error">{error}</p>}
    {chosen.map(o => {const file = byOption[o.id]; return <div key={o.id} className="document-row">
      <span>{o.label}</span>
      {file ? (file.available
        ? <a href={`/api/valuations/${files.id}/documents/${file.id}/file/`} target="_blank" rel="noopener">{file.name || 'Document'}</a>
        : <small className="muted">{file.name || 'Document'} (file not found)</small>) : <small className="muted">No document</small>}
      {!readOnly && <>
        <label className="link">{file ? 'Replace' : 'Attach'}<input type="file" hidden disabled={files.dirty || busy === o.id}
          accept=".pdf,.doc,.docx,image/jpeg,image/png,image/webp" onChange={e => e.target.files[0] && attach(o.id, e.target.files[0])}/></label>
        {file && <button className="link" disabled={busy === o.id} onClick={() => detach(o.id)}>Remove</button>}</>}
    </div>;})}
  </div>;
}

export function Question({q, value, readOnly, onChange, files}) {
  const title = <><legend>{q.text}{q.mandatory && <span className="required"> *</span>}{q.retired && <small className="muted"> (retired question)</small>}</legend>
    {q.conflicts?.length > 0 && <p className="notice">The previous system stored conflicting answers here: {q.conflicts.map(c => c.values.join(' / ')).join('; ')}. The first is shown. Changing this question replaces them.</p>}</>;
  if (!value) return null;
  if (q.kind === 'single' || q.kind === 'multiple') {
    const selected = new Set(value.selected);
    const toggle = id => {
      if (q.kind === 'single') return onChange({selected: selected.has(id) ? [] : [id]});
      const next = new Set(selected); next.has(id) ? next.delete(id) : next.add(id);
      onChange({selected: [...next]});
    };
    return <fieldset className="question">{title}{q.options.map(o => <label key={o.id} className="choice">
      <input type={q.kind === 'single' ? 'radio' : 'checkbox'} name={q.id} disabled={readOnly}
        checked={selected.has(o.id)} onChange={() => toggle(o.id)}/>{o.label}</label>)}
      {files && <Documents q={q} selected={selected} readOnly={readOnly} files={files}/>}</fieldset>;
  }
  if (q.kind === 'text') {
    return <fieldset className="question">{title}<textarea rows={2} value={value.value} disabled={readOnly}
      onChange={e => onChange({value: e.target.value})}/></fieldset>;
  }
  if (q.kind === 'sum') {
    const total = q.options.reduce((t, o) => t + (num(value.values[o.id]) ?? 0), 0);
    return <fieldset className="question">{title}<div className="table-wrap"><table><tbody>
      {q.options.map(o => <tr key={o.id}><td>{o.label}</td><td><input value={value.values[o.id] ?? ''} disabled={readOnly}
        onChange={e => onChange({values: {...value.values, [o.id]: e.target.value}})}/></td></tr>)}
      <tr><td><strong>Total</strong></td><td><strong>{total.toLocaleString('en-IN')}</strong></td></tr>
    </tbody></table></div></fieldset>;
  }
  // grid and formula
  const columns = Object.fromEntries(q.options.filter(o => o.column).map(o => [o.column, o.id]));
  const rows = value.rows.length ? value.rows : [{cells: {}}];
  const setRows = next => onChange({rows: next});
  const setCell = (i, optionId, v) => {
    let cells = {...rows[i].cells, [optionId]: v};
    if (q.kind === 'formula') cells = withFormula(cells, columns);
    setRows(rows.map((r, n) => n === i ? {...r, cells} : r));
  };
  return <fieldset className="question">{title}
    {q.kind === 'formula' && <p className="muted">Net value is calculated as (A × B) × (1 − C / 100).</p>}
    <div className="table-wrap"><table><thead><tr>{q.options.map(o => <th key={o.id}>{o.label}{o.column && <small> {o.column}</small>}</th>)}{!readOnly && <th></th>}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{q.options.map(o => {
      const computed = q.kind === 'formula' && o.column === 'D';
      return <td key={o.id}><input value={r.cells[o.id] ?? ''} disabled={readOnly || computed} title={computed ? 'Calculated' : ''}
        onChange={e => setCell(i, o.id, e.target.value)}/></td>;})}
      {!readOnly && <td><button className="link" onClick={() => setRows(rows.filter((_, n) => n !== i))}>Remove</button></td>}</tr>)}
    </tbody></table></div>
    {!readOnly && <button className="link" onClick={() => setRows([...rows, {cells: {}}])}>+ Add row</button>}
  </fieldset>;
}

const rupees = v => Number(v || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});

function Billing({api, id}) {
  const [data, setData] = useState(null);
  const [lines, setLines] = useState({});
  const [advance, setAdvance] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const adopt = d => {setData(d); setLines(Object.fromEntries(d.lines.map(l => [l.charge_type, l.amount === '0.00' ? '' : l.amount]))); setAdvance(d.totals.advance === '0.00' ? '' : d.totals.advance);};
  useEffect(() => {api(`valuations/${id}/billing/`).then(adopt).catch(e => setError(e.message));}, [id]);
  if (!data) return error ? <p role="alert" className="error">{error}</p> : <p>Loading billing…</p>;
  // Preview only; the server recomputes in exact decimal arithmetic on save.
  const charges = data.lines.filter(l => !l.discount).reduce((t, l) => t + (Number(lines[l.charge_type]) || 0), 0);
  const discount = data.lines.filter(l => l.discount).reduce((t, l) => t + Math.abs(Number(lines[l.charge_type]) || 0), 0);
  const total = charges - discount, afterTax = total * (1 + Number(data.gst_rate)), remaining = afterTax - (Number(advance) || 0);
  async function save() {
    setSaving(true); setError('');
    try {adopt(await api(`valuations/${id}/billing/`, {method: 'PUT', body: JSON.stringify({
      advance, lines: data.lines.map(l => ({charge_type: l.charge_type, amount: lines[l.charge_type] || '0'}))})}));}
    catch (e) {setError(e.message);} finally {setSaving(false);}
  }
  const stored = data.stored, differs = stored.after_tax !== null && Number(stored.after_tax).toFixed(2) !== data.totals.after_tax;
  return <div>
    <h3>Billing</h3>
    {data.locked_reason && <p className="notice">{data.locked_reason}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="table-wrap"><table><tbody>
      {data.lines.map(l => <tr key={l.charge_type}><td>{l.name}{l.discount && <small> (reduces the bill)</small>}
        {l.retired && <small className="muted"> (retired charge; set to 0 to remove)</small>}
        {l.stored_lines > 1 && <small className="muted"> ({l.stored_lines} lines from the previous system; shown as their total)</small>}</td>
        <td><input inputMode="decimal" value={lines[l.charge_type] ?? ''} disabled={!data.editable || l.stored_lines > 1}
          onChange={e => setLines({...lines, [l.charge_type]: e.target.value})}/></td></tr>)}
      <tr><td><strong>Total</strong></td><td><strong>₹ {rupees(total)}</strong></td></tr>
      <tr><td>GST at {Number(data.gst_rate) * 100}%</td><td>₹ {rupees(afterTax - total)}</td></tr>
      <tr><td><strong>Total after GST</strong></td><td><strong>₹ {rupees(afterTax)}</strong></td></tr>
      <tr><td>Advance paid by party</td><td><input inputMode="decimal" value={advance} disabled={!data.editable} onChange={e => setAdvance(e.target.value)}/></td></tr>
      <tr><td><strong>Remaining</strong></td><td><strong>₹ {rupees(remaining)}</strong></td></tr>
    </tbody></table></div>
    {differs && <p className="muted">The previous system recorded a total after GST of ₹ {rupees(stored.after_tax)}. Saving will replace it with the correctly computed figure.</p>}
    <p className="muted">These totals are provisional; invoicing sets the final GST split.</p>
    {data.editable && <button disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save billing'}</button>}
  </div>;
}

function Photos({api, id}) {
  const [data, setData] = useState(null);
  const [type, setType] = useState('1');
  const [caption, setCaption] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {api(`valuations/${id}/photos/`).then(setData).catch(e => setError(e.message));}, [id]);
  async function upload(file) {
    setBusy(true); setError('');
    const form = new FormData();
    form.append('type', type); form.append('caption', caption); form.append('file', file);
    try {setData(await api(`valuations/${id}/photos/`, {method: 'POST', body: form})); setCaption('');}
    catch (e) {setError(e.message);} finally {setBusy(false);}
  }
  async function remove(photo) {
    if (!window.confirm(`Remove the ${photo.type_label} photo?`)) return;
    try {setData(await api(`valuations/${id}/photos/${photo.id}/`, {method: 'DELETE'}));} catch (e) {setError(e.message);}
  }
  if (!data) return error ? <p role="alert" className="error">{error}</p> : <p>Loading photos…</p>;
  return <div>
    <h3>Photos</h3>
    {data.missing.length > 0 && <p className="notice">Usually taken but not yet added: {data.missing.join(', ')}.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {data.editable && <div className="toolbar">
      <label>Shows<select value={type} onChange={e => setType(e.target.value)}>{data.types.map(t => <option key={t.code} value={t.code}>{t.label}</option>)}</select></label>
      <label>Caption<input value={caption} maxLength={500} onChange={e => setCaption(e.target.value)}/></label>
      <label className="link">{busy ? 'Uploading…' : 'Choose photo'}<input type="file" hidden disabled={busy} accept="image/jpeg,image/png,image/webp,image/bmp"
        onChange={e => e.target.files[0] && upload(e.target.files[0])}/></label>
    </div>}
    <div className="photo-grid">{data.photos.map(p => <figure key={p.id}>
      {p.file?.available ? <a href={`/api/valuations/${id}/photos/${p.id}/file/`} target="_blank" rel="noopener">
          <img src={`/api/valuations/${id}/photos/${p.id}/file/`} alt={`${p.type_label} photo`} loading="lazy" decoding="async"/></a>
        : <div className="photo-placeholder">Photo not found</div>}
      <figcaption><strong>{p.type_label}</strong>{p.caption && <small> · {p.caption}</small>}
        {data.editable && <button className="link" onClick={() => remove(p)}>Remove</button>}</figcaption>
    </figure>)}</div>
    {data.photos.length === 0 && <p>No photos yet.</p>}
  </div>;
}

function Submission({api, id, onJump, onDone}) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({});
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const adopt = d => {setData(d); setForm({...d.values, valuation_date: d.values.valuation_date || ''});};
  useEffect(() => {api(`valuations/${id}/submission/`).then(adopt).catch(e => setError(e.message));}, [id]);
  if (!data) return error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>;
  const set = (k, v) => setForm(f => ({...f, [k]: v}));
  const locked = !data.editable;
  async function submit(e) {
    e.preventDefault();
    const note = data.keeps_report_number ? `It keeps report number ${data.report_number}.` : 'A report number will be assigned.';
    if (!window.confirm(`Submit this valuation for verification? ${note}\n\nIt can no longer be edited unless it is sent back.`)) return;
    setSaving(true); setError('');
    try {const result = await api(`valuations/${id}/submission/`, {method: 'POST', body: JSON.stringify(form)}); adopt(result.submission); onDone(result);}
    catch (e) {setError(e.message);} finally {setSaving(false);}
  }
  const select = (k, label, options, required = true) => <label>{label}{required && <span className="required"> *</span>}
    <select value={form[k] ?? ''} disabled={locked} onChange={e => set(k, e.target.value)} required={required}>
      <option value="">Choose…</option>{options.map(o => <option key={o.code ?? o.id} value={o.code ?? o.id}>{o.label ?? o.name}</option>)}</select></label>;
  return <form onSubmit={submit}>
    <h3>{data.status === 'Submit' ? `Submitted as ${data.report_number}` : 'Submit for verification'}</h3>
    {error && <p role="alert" className="error">{error}</p>}
    {!locked && data.missing_required.length > 0 && <div className="notice">
      <p>Answer these required questions before submitting:</p>
      <ul>{data.missing_required.map(q => <li key={q.question}><button type="button" className="link" onClick={() => onJump(q.section_key)}>{q.section}</button>: {q.text}</li>)}</ul>
    </div>}
    {!locked && data.keeps_report_number && <p className="muted">This valuation was sent back. Resubmitting keeps its report number, {data.report_number}.</p>}
    <div className="form-grid">
      <label>Valuation date<input type="date" value={form.valuation_date || ''} disabled={locked} max={new Date().toISOString().slice(0, 10)} onChange={e => set('valuation_date', e.target.value)}/><small className="muted">Defaults to today</small></label>
      <label>Eligible loan amount<span className="required"> *</span><input inputMode="decimal" value={form.eligible_loan_amount || ''} disabled={locked} required onChange={e => set('eligible_loan_amount', e.target.value)}/></label>
      <label>Desired loan amount<span className="required"> *</span><input inputMode="decimal" value={form.desired_loan_amount || ''} disabled={locked} required onChange={e => set('desired_loan_amount', e.target.value)}/></label>
      {select('submitted_to', 'Liable assessor (FA)', data.options.employees)}
      <small className="muted form-note">Who this report's billing and recovery is credited to. It starts as the lead's assignee.</small>
      {select('dispatch_at', 'To be dispatched at', data.options.dispatch_at)}
      {select('dispatch_by', 'To be dispatched by', data.options.dispatch_by)}
      {select('report_category', 'Report category', data.options.report_category)}
    </div>
    <label>Assessor's comment<textarea rows={3} value={form.assessor_comment || ''} disabled={locked} onChange={e => set('assessor_comment', e.target.value)}/></label>
    <label>Non-cost factors<textarea rows={2} value={form.non_cost_factor || ''} disabled={locked} onChange={e => set('non_cost_factor', e.target.value)}/></label>
    {!locked && <p className="actions"><button disabled={saving || data.missing_required.length > 0}>{saving ? 'Submitting…' : 'Submit valuation'}</button></p>}
  </form>;
}

// Every document of the valuation's answers, current and earlier, as the legacy
// "All uploaded docs history": a replaced or removed document stays listed and opens.
const VERSION_LABEL = {current: 'In place', replaced: 'Replaced', removed: 'Removed', legacy: 'Earlier upload (previous system)'};
export function DocumentHistory({api, id}) {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {if (open && rows === null) api(`valuations/${id}/documents/history/`).then(r => setRows(r.documents)).catch(() => setRows([]));}, [open]);
  return <section className="document-history">
    <button type="button" className="link" onClick={() => setOpen(!open)} aria-expanded={open}>
      {open ? 'Hide' : 'Show'} all uploaded documents{rows ? ` (${rows.length})` : ''}</button>
    {open && rows === null && <p className="muted">Loading…</p>}
    {open && rows?.length === 0 && <p className="muted">No documents have been uploaded for this valuation.</p>}
    {open && rows?.length > 0 && <ul>{rows.map(r => <li key={r.document}>
      <a href={`/api/valuations/${id}/documents/${r.document}/file/`} target="_blank" rel="noopener">{r.name || 'Document'}</a>
      {' · '}{VERSION_LABEL[r.status] || r.status}{r.question ? ` · ${r.question}` : ''}
      {r.on ? ` · ${new Date(r.on).toLocaleDateString('en-IN')}` : ''}{r.by ? ` · ${r.by}` : ''}</li>)}</ul>}
  </section>;
}

