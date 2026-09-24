import React, {useEffect, useState} from 'react';

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
      <div className="table-wrap"><table><thead><tr><th>Lead</th><th>Borrower</th><th>Work order</th><th>Service</th><th>District</th><th>Valuation</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.case}>
        <td><strong>{r.lead_number}</strong></td><td>{r.borrower}</td><td>{r.work_order || '—'}</td>
        <td>{r.service}<small>{r.subtype}</small></td><td>{r.district || '—'}</td>
        <td>{r.valuation ? <><span className="status">{LABELS[r.valuation.status] || r.valuation.status}</span>{r.valuation.report_number && <small>{r.valuation.report_number}</small>}</> : <span className="muted">Not started</span>}</td>
        <td>{r.valuation
          ? <button className="link" onClick={() => onOpen(r.valuation.id)}>Open →</button>
          : <button disabled={busy === r.case} onClick={() => start(r)}>{busy === r.case ? 'Starting…' : 'Start valuation'}</button>}</td>
      </tr>)}</tbody></table></div>
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
    if (!key) return;
    setSection(null); setSaved('');
    api(`valuations/${id}/sections/${key}/`).then(s => {
      setSection(s); setDirty(false);
      setDraft(Object.fromEntries(s.questions.map(q => [q.id, structuredClone(q.answer)])));
    }).catch(e => setError(e.message));
  }, [key]);

  function choose(next) {
    if (dirty && !window.confirm('Leave this section without saving your changes?')) return;
    setKey(next);
  }
  const edit = (qid, answer) => {setDraft(d => ({...d, [qid]: answer})); setDirty(true); setSaved('');};

  async function save() {
    setSaving(true); setError('');
    try {
      const answers = section.questions.map(q => ({question: q.id, ...draft[q.id]}));
      const result = await api(`valuations/${id}/sections/${key}/`, {method: 'PUT', body: JSON.stringify({answers})});
      setSection(result); setDirty(false);
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
    <p>{head.lead_number} · {head.borrower} · {head.work_order}</p>
    <p className="muted">{head.service}{head.subtype ? ` / ${head.subtype}` : ''}{head.bank ? ` · ${head.bank}` : ''}{head.asset ? ` · ${head.asset}` : ''}</p>
    <p><span className="status">{LABELS[head.status] || head.status}</span></p>
    {readOnly && <p className="notice">This valuation is {(LABELS[head.status] || head.status).toLowerCase()} and cannot be edited.</p>}
    {head.status === 'Revert' && <p className="notice">This valuation was sent back for correction. Update the answers, then resubmit.</p>}
    <p className="muted">Some forms include a section for each bank. Complete the common parts and the section for {head.bank || 'this case\u2019s bank'} only.</p>
    <div className="valuation-layout">
      <nav className="sections">{head.sections.map(s => <button key={s.key} className={s.key === key ? 'active' : ''} onClick={() => choose(s.key)}>
        <span>{s.name}</span>
        <small>{s.answered}/{s.questions}{s.required ? ` · required ${s.required_answered}/${s.required}` : ''}</small>
      </button>)}</nav>
      <div className="section-body">
        {error && <p role="alert" className="error">{error}</p>}
        {!section ? <p>Loading section…</p> : <>
          {section.questions.map(q => <Question key={q.id} q={q} value={draft[q.id]} readOnly={readOnly} onChange={a => edit(q.id, a)}/>)}
          {!readOnly && <p className="actions"><button disabled={saving || !dirty} onClick={save}>{saving ? 'Saving…' : 'Save section'}</button>
            {saved && <span className="muted">{saved}</span>}{dirty && <span className="muted">Unsaved changes</span>}</p>}
        </>}
      </div>
    </div>
  </section>;
}

function Question({q, value, readOnly, onChange}) {
  const title = <legend>{q.text}{q.mandatory && <span className="required"> *</span>}{q.retired && <small className="muted"> (retired question)</small>}</legend>;
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
        checked={selected.has(o.id)} onChange={() => toggle(o.id)}/>{o.label}</label>)}</fieldset>;
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
