import {ResponsiveTable} from './components/ResponsiveTable.jsx';
import React, {useEffect, useState} from 'react';
import {Question} from './valuations.jsx';
import {dateTime, today} from './lib/format.js';

const TRACKS = [['legal', 'Legal'], ['technical', 'Technical'], ['social', 'Social'], ['general', 'General']];

export function Verifications({api}) {
  const [track, setTrack] = useState('legal');
  const [open, setOpen] = useState(null);
  const [flash, setFlash] = useState('');
  // After a track is verified, the same valuation's next unverified track opens in
  // its place (Legal, Social, Technical, General); after the last, the queue returns.
  const advance = (done, next) => {
    const label = k => TRACKS.find(([t]) => t === k)[1];
    if (next) {setFlash(`${label(done)} verification saved. Now showing ${label(next).toLowerCase()} verification.`); setTrack(next);}
    else {setFlash(`${label(done)} verification saved. Every track of this valuation is verified.`); setOpen(null);}
  };
  if (open) return <Review api={api} id={open} track={track} flash={flash} onVerified={advance}
    onBack={() => {setOpen(null); setFlash('');}}/>;
  return <>{flash && <p className="notice" role="status">{flash}</p>}
    <Queue api={api} track={track} setTrack={t => {setTrack(t); setFlash('');}} onOpen={id => {setOpen(id); setFlash('');}}/></>;
}

function Queue({api, track, setTrack, onOpen}) {
  const [list, setList] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  useEffect(() => {
    const t = setTimeout(() => api(`verifications/?track=${track}&q=${encodeURIComponent(q)}&page=${page}`)
      .then(r => {setList(r); setError('');}).catch(e => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [track, q, page]);
  return <section className="panel">
    <div className="tabs">{TRACKS.map(([k, label]) => <button key={k} className={k === track ? 'active' : ''}
      onClick={() => {setTrack(k); setPage(1);}}>{label}{list && <span className="count"> {list.counts[k]}</span>}</button>)}</div>
    <div className="toolbar"><label className="search">Search<input placeholder="Report, lead or borrower" value={q}
      onChange={e => {setQ(e.target.value); setPage(1);}}/></label></div>
    {error && <p role="alert" className="error">{error}</p>}
    {!list ? <p>Loading…</p> : <>
      <ResponsiveTable><table><thead><tr><th>Report</th><th>Lead</th><th>Borrower</th><th>Service</th><th>Submitted</th><th>Tracks done</th><th></th></tr></thead>
      <tbody>{list.results.map(r => <tr key={r.id}>
        <td><strong>{r.report_number}</strong></td><td>{r.lead_number}</td><td>{r.borrower}</td>
        <td>{r.service}<small>{r.subtype}</small></td><td>{r.submitted_at ? dateTime(r.submitted_at) : (r.submitted_on || '—')}<small>{r.assessor}</small></td>
        <td>{TRACKS.filter(([k]) => r.tracks[k]).map(([, l]) => l).join(', ') || 'None yet'}</td>
        <td><button className="link" onClick={() => onOpen(r.id)}>Review →</button></td></tr>)}</tbody></table></ResponsiveTable>
      {list.total === 0 && <p>Nothing waiting for {TRACKS.find(([k]) => k === track)[1].toLowerCase()} verification.</p>}
      <div className="pagination"><span>{list.total.toLocaleString('en-IN')} waiting · Page {page}</span>
        <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button disabled={page * list.page_size >= list.total} onClick={() => setPage(page + 1)}>Next</button></div>
    </>}
  </section>;
}

function Review({api, id, track, flash, onVerified, onBack}) {
  const [data, setData] = useState(null);
  const [remark, setRemark] = useState('');
  const [date, setDate] = useState(today());
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [draft, setDraft] = useState({});
  const [changed, setChanged] = useState(new Set());
  const [saved, setSaved] = useState('');
  const adoptQuestions = d => {
    const all = [...d.sections.flatMap(s => s.questions), ...d.unassigned];
    setDraft(Object.fromEntries(all.map(q => [q.id, structuredClone(q.answer)]))); setChanged(new Set());
  };
  const load = () => api(`verifications/${id}/?track=${track}`).then(d => {setData(d); adoptQuestions(d);}).catch(e => setError(e.message));
  useEffect(() => {setData(null); setRemark(''); setSaved(''); setError(''); load(); document.querySelector('main')?.scrollIntoView?.({block: 'start'});}, [id, track]);
  const label = TRACKS.find(([k]) => k === track)[1];
  const dirty = changed.size > 0;

  async function saveAnswers() {
    const all = [...data.sections.flatMap(s => s.questions), ...data.unassigned];
    const answers = all.filter(q => changed.has(q.id)).map(q => ({question: q.id, ...draft[q.id], ...(q.conflicts?.length ? {resolve: true} : {})}));
    setBusy('save'); setError(''); setSaved('');
    try {
      const r = await api(`verifications/${id}/${track}/answers/`, {method: 'PUT', body: JSON.stringify({answers})});
      const next = {...data, sections: r.sections, unassigned: r.unassigned};
      setData(next); adoptQuestions(next); setSaved('Corrections saved');
      return true;
    } catch (err) {setError(err.message); return false;} finally {setBusy('');}
  }
  async function verify(e) {
    e.preventDefault();
    if (dirty && !window.confirm('Your corrections are not saved yet. Save them and verify?')) return;
    if (dirty && !(await saveAnswers())) return;
    setBusy('verify'); setError('');
    try {
      const r = await api(`verifications/${id}/${track}/`, {method: 'POST', body: JSON.stringify({remark, date})});
      setRemark(''); onVerified(track, r.next_track);
    }
    catch (err) {setError(err.message);} finally {setBusy('');}
  }
  async function sendBack(e) {
    e.preventDefault();
    if (!window.confirm('Send this valuation back to the assessor? Every verification will need to be given again.')) return;
    setBusy('revert'); setError('');
    try {await api(`verifications/${id}/revert/`, {method: 'POST', body: JSON.stringify({remark: reason})}); setReason(''); await load();}
    catch (err) {setError(err.message);} finally {setBusy('');}
  }
  if (!data) return <section className="panel">{error ? <p role="alert" className="error">{error}</p> : <p>Loading…</p>}</section>;
  const editable = !!data.can_edit;
  const files = {api, id, dirty: false, reload: load, readOnly: true};
  const edit = (qid, answer) => {setDraft(d => ({...d, [qid]: answer})); setChanged(c => new Set(c).add(qid)); setSaved('');};
  const show = q => <Question key={q.id} q={q} value={draft[q.id]} readOnly={!editable} onChange={a => edit(q.id, a)} files={q.document ? files : null}/>;
  return <section className="panel">
    <button className="link" onClick={() => {if (!dirty || window.confirm('Leave without saving your corrections?')) onBack();}}>← Back to the {label.toLowerCase()} queue</button>
    {flash && <p className="notice" role="status">{flash}</p>}
    <h2>{data.report_number} · {label} verification</h2>
    <p>{data.lead_number} · {data.borrower} · {data.service}{data.subtype ? ` / ${data.subtype}` : ''}</p>
    <p className="muted">Assessor: {data.assessor || '—'} · Submitted {data.submitted_at ? dateTime(data.submitted_at) : (data.submitted_on || '—')} · Status {data.status}</p>
    <div className="track-status">{[...TRACKS, ['final', 'Final approval']].map(([k, l]) => {const t = data.tracks[k]; return <div key={k} className={t.verified ? 'done' : ''}>
      <strong>{l}</strong><small>{t.verified ? `Verified${t.by ? ' by ' + t.by : ''}${t.date ? ' · ' + t.date : ''}` : (t.status === 'UnVerified' ? `Sent back${t.by ? ' (was ' + t.by + ')' : ''}` : 'Pending')}</small></div>;})}</div>
    {error && <p role="alert" className="error">{error}</p>}

    <h3>{label} questions</h3>
    {editable && <p className="muted">You can correct any answer below before verifying. Corrections are recorded against your name.</p>}
    {data.sections.length === 0 && data.unassigned.length === 0 && <p className="muted">This form has no {label.toLowerCase()} questions.</p>}
    {data.sections.map(s => <div key={s.key}><h4>{s.name}</h4>{s.questions.map(show)}</div>)}
    {data.unassigned.length > 0 && <div><h4>Not assigned to any track</h4>
      <p className="muted">These questions belong to no verification track. They are checked here, in the general verification.</p>
      {data.unassigned.map(show)}</div>}
    {editable && <p className="actions"><button type="button" disabled={busy === 'save' || !dirty} onClick={saveAnswers}>{busy === 'save' ? 'Saving…' : 'Save corrections'}</button>
      {saved && <span className="muted">{saved}</span>}{dirty && <span className="muted">Unsaved corrections</span>}</p>}

    {data.can_verify && <form onSubmit={verify} className="panel inset"><h3>Give {label.toLowerCase()} verification</h3>
      <label>Remark<span className="required"> *</span><textarea rows={2} value={remark} required onChange={e => setRemark(e.target.value)}/></label>
      <label>Date<input type="date" value={date} max={today()} onChange={e => setDate(e.target.value)}/></label>
      <button disabled={busy === 'verify' || !remark.trim()}>{busy === 'verify' ? 'Saving…' : `Verify ${label.toLowerCase()}`}</button>
      {data.next_track && <small className="muted"> The {TRACKS.find(([k]) => k === data.next_track)[1].toLowerCase()} verification opens next.</small>}</form>}
    {!data.can_verify && data.tracks[track].verified && <p className="notice">{label} verification is complete.</p>}

    {data.can_revert && <form onSubmit={sendBack} className="panel inset"><h3>Send back to the assessor</h3>
      <label>Reason<span className="required"> *</span><textarea rows={2} value={reason} required onChange={e => setReason(e.target.value)}/></label>
      <button disabled={busy === 'revert' || !reason.trim()}>{busy === 'revert' ? 'Sending…' : 'Send back'}</button></form>}

    {data.reversions.length > 0 && <><h3>Sent back before</h3><ul>{data.reversions.map((r, i) =>
      <li key={i}>{r.on || '—'} · {r.by || '—'}: {r.remark}{r.stage === 'legacy' && <small className="muted"> (previous system; earlier reverts were not kept)</small>}</li>)}</ul></>}
  </section>;
}
