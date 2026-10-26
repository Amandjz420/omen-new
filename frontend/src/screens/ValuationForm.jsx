import {Alert, Anchor, Badge, Button, Drawer, Group, Loader, NativeSelect, Paper, Progress, Radio, Stack, Text, TextInput, Textarea, Title} from '@mantine/core';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useEffect, useRef, useState} from 'react';
import {Link, useParams, useSearchParams} from 'react-router';
import {ErrorState, LoadingState} from '../components/States.jsx';
import {ApiError, api, post} from '../lib/api.js';
import {clearDraft, listDrafts, saveDraft} from '../lib/drafts.js';
import classes from './ValuationForm.module.css';
import {SiteChecklist} from './SiteChecklist.jsx';

// The valuation form on a phone: answer by tapping an option or writing your own,
// by recording what you see at the site, or by photographing a document. Recording
// and reading only suggest; nothing reaches the form until you accept it.

const KIND_LABEL = {single: 'Pick one', multiple: 'Pick any', text: 'Text', grid: 'Table', sum: 'Amounts', formula: 'Calculated'};
const SOURCE_LABEL = {recording: 'Accepted from your recording', document: 'Accepted from a document'};
const draftKey = (id, qid) => `valuation:${id}:${qid}`;

export function ValuationForm() {
  const {id} = useParams();
  const [params, setParams] = useSearchParams();
  const client = useQueryClient();
  const detail = useQuery({queryKey: ['valuation', id], queryFn: () => api(`valuations/${id}/`)});
  const key = params.get('section') || detail.data?.sections?.[0]?.key;
  const section = useQuery({queryKey: ['valuation', id, 'section', key], queryFn: () => api(`valuations/${id}/sections/${key}/`), enabled: !!key});
  const assist = useQuery({queryKey: ['valuation', id, 'assist'], queryFn: () => api(`valuations/${id}/assist/`)});
  const [status, setStatus] = useState({});            // per question: saving, saved, device, or an error
  const [review, setReview] = useState(null);           // {suggestions, source, error}
  const [busy, setBusy] = useState('');
  const [deciding, setDeciding] = useState(false);
  useEffect(() => {
    const question = params.get('question');
    if (!question || !section.data) return;
    const element = document.getElementById(`question-${question}`);
    element?.scrollIntoView?.({behavior: 'smooth', block: 'center'});
    element?.focus({preventScroll: true});
  }, [params, section.data]);

  const refresh = () => {
    client.invalidateQueries({queryKey: ['valuation', id]});
    client.invalidateQueries({queryKey: ['home']});
  };

  // An answer is kept on the phone first, then sent; a dropped signal leaves it waiting there.
  async function save(q, answer, sectionKey = key) {
    saveDraft(draftKey(id, q.id), {section: sectionKey, question: q.id, answer});
    setStatus(s => ({...s, [q.id]: 'saving'}));
    try {
      const body = await api(`valuations/${id}/sections/${sectionKey}/`, {method: 'PUT', body: JSON.stringify({answers: [{question: q.id, ...answer}]})});
      clearDraft(draftKey(id, q.id));
      client.setQueryData(['valuation', id, 'section', sectionKey], body);
      setStatus(s => ({...s, [q.id]: 'saved'}));
      client.invalidateQueries({queryKey: ['valuation', id, 'checklist']});
    } catch (e) {
      if (!(e instanceof ApiError) || e.status === 0) setStatus(s => ({...s, [q.id]: 'device'}));
      else { clearDraft(draftKey(id, q.id)); setStatus(s => ({...s, [q.id]: e.message})); }
    }
  }
  useEffect(() => {                                      // back online: send what is waiting on the phone
    const resend = () => listDrafts().filter(d => d.key.startsWith(`valuation:${id}:`))
      .forEach(d => save({id: d.value.question}, d.value.answer, d.value.section));
    window.addEventListener('online', resend);
    return () => window.removeEventListener('online', resend);
  }, [id]);                                              // eslint-disable-line react-hooks/exhaustive-deps

  async function decide(s, accept, resolution = 'use_source', ownAnswer) {
    setDeciding(true);
    try {
      await post(`valuations/${id}/assist/suggestions/${s.id}/${accept ? 'accept' : 'dismiss'}/`, accept ? {resolution, expected_answer: s.current_answer, ...(resolution === 'write_own' ? {own_answer: ownAnswer} : {})} : {});
      setReview(r => r && {...r, suggestions: r.suggestions.map(x => (x.id === s.id ? {...x, status: accept ? 'accepted' : 'dismissed'} : x))});
      refresh();
    } catch (e) {
      setReview(r => ({...(r || {suggestions: []}), error: e.message}));
      refresh();
    } finally { setDeciding(false); }
  }

  async function send(path, form) {
    setBusy(path === 'recordings' ? 'Transcribing and matching your recording' : 'Reading the pages');
    try {
      const body = await api(`valuations/${id}/assist/${path}/`, {method: 'POST', body: form});
      setReview({suggestions: body.suggestions, source: body.source});
      refresh();
      return true;
    } catch (e) {
      setReview({suggestions: [], error: e.message, source: e.data?.source});
      refresh();
      return !!e.data?.source; // stored even if transcription failed
    } finally { setBusy(''); }
  }
  async function retry(source) {
    setBusy('Trying again');
    try {
      const body = await post(`valuations/${id}/assist/sources/${source.id}/retry/`);
      setReview({suggestions: body.suggestions, source: body.source});
      refresh();
    } catch (e) { setReview({suggestions: [], error: e.message, source: e.data?.source}); }
    finally { setBusy(''); }
  }

  if (detail.isError) return <ErrorState error={detail.error} onRetry={detail.refetch}/>;
  if (!detail.data) return <LoadingState label="Opening the valuation"/>;
  const v = detail.data, editable = v.editable && section.data?.editable !== false;
  const current = v.sections.find(s => s.key === key);
  const pending = (section.data?.suggestions || []);
  const configured = assist.data?.configured;
  const sources = assist.data?.sources || [];
  const openSource = (source, located = '') => setReview({source, located, error: source.error || '', suggestions: (assist.data?.suggestions || []).filter(s => String(s.source) === String(source.id))});

  return <Stack gap="md" className={classes.page}>
    <div>
      <Anchor component={Link} to="/valuations" size="sm">All valuations</Anchor>
      <Title order={1} className={classes.title}>{v.report_number || v.lead_number}</Title>
      <Text size="sm" c="dimmed">{[v.borrower, v.subtype || v.service, v.bank].filter(Boolean).join(' · ')}</Text>
    </div>

    <Paper withBorder p="sm" className={classes.bar}>
      <Progress value={current?.questions ? current.answered / current.questions * 100 : 0} aria-label="Section completion"/>
      <NativeSelect disabled={!!busy} label="Section" value={key || ''} onChange={e => setParams({section: e.currentTarget.value})}
                    data={v.sections.map(s => ({value: s.key, label: `${s.name.trim()} (${s.answered} of ${s.questions})`}))}/>
      {editable && <div className={classes.assist}>
        <Recorder disabled={!configured || !!busy} onRecorded={(blob, name) => { const f = new FormData(); f.append('audio', blob, name); return send('recordings', f); }}/>
        <PagePicker disabled={!configured || !!busy} onPicked={files => { const f = new FormData(); files.forEach(x => f.append('pages', x)); send('documents', f); }}/>
      </div>}
      {assist.isError && <Text size="xs" c="red">Unable to load saved recordings. <button className={classes.link} onClick={() => assist.refetch()}>Retry</button></Text>}
      {editable && assist.data && !configured && <Text size="xs" c="dimmed">Voice and documents are not set up on this server yet.</Text>}
      {!editable && <Text size="sm" c="dimmed">This valuation is {v.status?.toLowerCase() || 'closed'} and cannot be edited.</Text>}
      {busy && <Group gap="xs"><Loader size="xs"/><Text size="sm">{busy}…</Text></Group>}
      {pending.length > 0 && <Button variant="subtle" color="orange" size="compact-sm" onClick={() => setReview({suggestions: pending})}>
        {pending.length} suggestion{pending.length === 1 ? '' : 's'} to review in this section</Button>}
    </Paper>

    <SiteChecklist id={id} unsaved={Object.values(status).some(s => s === 'saving' || s === 'device')}
      onQuestion={q => setParams({section: q.section_key, question: String(q.question)})}/>

    {sources.length > 0 && <details className={classes.history}><summary>Saved recordings and documents · {sources.length}</summary><Stack gap="xs" mt="sm">{sources.map(source => <Paper key={source.id} withBorder p="sm"><Group justify="space-between"><Text size="sm" fw={600}>{source.kind === 'recording' ? 'Site recording' : 'Document pages'} · {new Date(source.created_at).toLocaleString('en-IN', {hour12: false})}</Text><Button size="xs" variant="light" onClick={() => openSource(source)}>Review source</Button></Group>{source.kind === 'recording' && <SourceAudio source={source}/>}<Text size="xs" c="dimmed">{source.files?.[0]?.storage === 's3' ? 'Saved in S3' : 'Saved on server'}{source.status === 'failed' ? ' · Processing failed; source kept' : ''}</Text></Paper>)}</Stack></details>}

    {section.isError ? <ErrorState error={section.error} onRetry={section.refetch}/> : !section.data ? <LoadingState label="Loading the questions"/> :
      <Stack gap="sm">
        {current && <Text size="sm" c="dimmed">{current.answered} of {current.questions} answered{current.required ? ` · ${current.required_answered} of ${current.required} required` : ''}</Text>}
        {section.data.questions.filter(q => !q.retired || hasAnswer(q)).map(q => <Question key={q.id} q={q} editable={editable && status[q.id] !== 'saving' && !deciding}
          status={status[q.id]} suggestions={pending.filter(s => String(s.question) === String(q.id))}
          onSave={answer => save(q, answer)} onDecide={decide} onSource={source => { const found = sources.find(s => String(s.id) === String(source.id)); if (found) openSource(found, source.located); }}/>)}
      </Stack>}

    <Drawer opened={!!review} onClose={() => setReview(null)} position="bottom" size="95%" title="Suggested answers" classNames={{body: classes.sheet}}>
      {review && <Review review={review} sources={sources} onDecide={decide} onRetry={retry} busy={!!busy || deciding} editable={editable}/>}
    </Drawer>
  </Stack>;
}

const hasAnswer = q => {
  const a = q.answer || {};
  return Boolean((a.selected || []).length || a.custom || a.value === 0 || a.value || (a.rows || []).length || Object.keys(a.values || {}).length);
};

function Question({q, editable, status, suggestions, onSave, onDecide, onSource}) {
  return <Paper withBorder p="md" id={`question-${q.id}`} tabIndex={-1} className={classes.question} data-suggested={suggestions.length > 0 || undefined}>
    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
      <Text fw={600} size="sm" className={classes.questionText}>{q.text}{q.mandatory && <span className={classes.required} aria-label="required"> *</span>}</Text>
      <Text size="xs" c="dimmed" className={classes.kind}>{KIND_LABEL[q.kind]}</Text>
    </Group>
    {suggestions.map(s => <SuggestionCard key={s.id} s={s} onDecide={onDecide} disabled={!editable} inline/>)}
    {(q.kind === 'single' || q.kind === 'multiple') && <Choice q={q} editable={editable} onSave={onSave}/>}
    {q.kind === 'text' && <FreeText q={q} editable={editable} onSave={onSave}/>}
    {q.kind === 'grid' && <Grid q={q} editable={editable} onSave={onSave}/>}
    {q.kind === 'sum' && <Sum q={q} editable={editable} onSave={onSave}/>}
    {q.kind === 'formula' && <Formula q={q}/>}
    {q.comparisons?.map(c => <details className={classes.comparison} key={c.id}>
      <summary>Answer review history</summary>
      <Text size="sm">Current form answer: {c.current_display || 'Empty'}</Text>
      <Text size="sm">Previous form answer: {c.previous_display || 'Empty'}</Text>
      <Text size="sm">Suggested answer: {c.display}</Text>
      <Text size="xs" c="dimmed">{c.kind === 'document' ? 'Document' : 'Recording'} · {c.located} · {({use_source: 'Used the suggestion', keep_site: 'Kept the current answer', keep_both: 'Kept the current answer and evidence', write_own: 'Wrote an own answer'})[c.resolution]}</Text>
    </details>)}
    <Footnote q={q} status={status} onSource={onSource}/>
  </Paper>;
}

function Choice({q, editable, onSave}) {
  const answer = q.answer || {selected: [], custom: ''};
  // An option with no label is the written-in answer's slot, not a choice to show.
  const options = q.options.filter(o => (o.label || '').trim());
  const [writing, setWriting] = useState(!!answer.custom || !options.length);
  const [custom, setCustom] = useState(answer.custom || '');
  useEffect(() => { setCustom(answer.custom || ''); if (answer.custom) setWriting(true); }, [answer.custom]);
  const selected = new Set((answer.selected || []).map(String));
  const pick = id => {
    const next = new Set(selected);
    if (q.kind === 'single') { next.clear(); if (!selected.has(id)) next.add(id); } else if (next.has(id)) next.delete(id); else next.add(id);
    onSave({selected: [...next], custom: q.kind === 'single' && next.size ? '' : custom});
    if (q.kind === 'single' && next.size) { setCustom(''); setWriting(false); }
  };
  return <>
    <div className={classes.options} role="group" aria-label={q.text}>
      {options.map(o => <button key={o.id} type="button" className={classes.option} aria-pressed={selected.has(String(o.id))}
                                  disabled={!editable} onClick={() => pick(String(o.id))}>{o.label}</button>)}
    </div>
    {writing && <TextInput label="Your own answer" value={custom} disabled={!editable} placeholder="What you found"
      onChange={e => setCustom(e.currentTarget.value)}
      onBlur={() => custom !== (answer.custom || '') && onSave({selected: q.kind === 'single' && custom ? [] : [...selected], custom})}/>}
    {editable && options.length > 0 && <button type="button" className={classes.link} onClick={() => {
      if (writing && answer.custom) onSave({selected: [...selected], custom: ''});
      setWriting(!writing); if (writing) setCustom('');
    }}>{writing ? 'Use the options instead' : 'Write your own answer'}</button>}
  </>;
}

function FreeText({q, editable, onSave}) {
  const saved = q.answer?.value || '';
  const [value, setValue] = useState(saved);
  useEffect(() => setValue(saved), [saved]);
  return <Textarea aria-label={q.text} value={value} disabled={!editable} autosize minRows={1} placeholder="Type the answer"
                   onChange={e => setValue(e.currentTarget.value)} onBlur={() => value !== saved && onSave({value})}/>;
}

function Grid({q, editable, onSave}) {
  const saved = q.answer?.rows || [];
  const [rows, setRows] = useState(saved);
  useEffect(() => setRows(saved), [JSON.stringify(saved)]);     // eslint-disable-line react-hooks/exhaustive-deps
  const set = (i, optionId, value) => setRows(rs => rs.map((r, n) => (n === i ? {...r, cells: {...r.cells, [optionId]: value}} : r)));
  const commit = () => JSON.stringify(rows) !== JSON.stringify(saved) && onSave({rows});
  return <Stack gap="xs">
    {rows.map((r, i) => <div key={r.group ?? `new-${i}`} className={classes.gridRow}>
      {rows.length > 1 && <Text size="xs" c="dimmed">Row {i + 1}</Text>}
      {q.options.map(o => <TextInput key={o.id} label={o.label} size="sm" disabled={!editable} value={r.cells?.[o.id] || ''}
                                     onChange={e => set(i, String(o.id), e.currentTarget.value)} onBlur={commit}/>)}
    </div>)}
    {editable && <button type="button" className={classes.link} onClick={() => setRows(rs => [...rs, {cells: {}}])}>{rows.length ? 'Add a row' : 'Fill in the table'}</button>}
  </Stack>;
}

function Sum({q, editable, onSave}) {
  const saved = q.answer?.values || {};
  const [values, setValues] = useState(saved);
  useEffect(() => setValues(saved), [JSON.stringify(saved)]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <Stack gap="xs">
    {q.options.map(o => <TextInput key={o.id} label={o.label} size="sm" inputMode="decimal" disabled={!editable} value={values[o.id] || ''}
      onChange={e => setValues(v => ({...v, [o.id]: e.currentTarget.value}))}
      onBlur={() => JSON.stringify(values) !== JSON.stringify(saved) && onSave({values})}/>)}
    <Text size="sm" fw={600} className="num">Total: ₹{Number(q.answer?.total || 0).toLocaleString('en-IN')}</Text>
  </Stack>;
}

function Formula({q}) {
  const rows = q.answer?.rows || [];
  return rows.length === 0 ? <Text size="sm" c="dimmed">Calculated from the table on the full form.</Text> :
    <Stack gap={4}>{rows.map((r, i) => <Text key={i} size="sm" className="num">
      {q.options.map(o => r.cells?.[o.id]).filter(Boolean).join(' · ')}</Text>)}</Stack>;
}

function Footnote({q, status, onSource}) {
  const text = status === 'saving' ? 'Saving…' : status === 'saved' ? (q.source ? null : 'Saved')
    : status === 'device' ? 'Saved on this phone. It will be sent when you are back online.' : status;
  return <>
    {q.source && <button className={classes.link} onClick={() => onSource?.(q.source)}>{SOURCE_LABEL[q.source.kind]}{q.source.located ? ` · ${q.source.located}` : ''} · Review source</button>}
    {!q.source && hasAnswer(q) && <Text size="xs" c="dimmed">Answered by you</Text>}
    {text && <Text size="xs" c={status && !['saving', 'saved', 'device'].includes(status) ? 'red' : 'dimmed'} role={status === 'device' ? 'status' : undefined}>{text}</Text>}
    {q.conflicts?.length > 0 && <Text size="xs" c="orange.8">This question holds conflicting answers from the previous system; use the full form to resolve them.</Text>}
  </>;
}

function SuggestionCard({s, onDecide, inline = false, disabled = false, onEvidence}) {
  const filled = !!hasAnswer({answer: s.current_answer}) || !!s.current_display;
  const [resolution, setResolution] = useState(filled ? 'keep_site' : 'use_source');
  const [own, setOwn] = useState({});
  const [copied, setCopied] = useState('');
  const kind = s.answer_kind || 'text';
  const ownQuestion = {text: 'Your answer', kind, options: s.options || [], answer: own};
  async function copy() {
    try { await navigator.clipboard.writeText(s.display); setCopied('Copied'); }
    catch { setCopied('Select the suggestion text to copy it.'); }
  }
  const done = s.status && s.status !== 'pending';
  return <div className={classes.suggestion}>
    <Group gap={6} className={classes.suggestionHead}>
      <Text span size="xs" fw={700}>{s.kind === 'recording' ? 'Suggested from your recording' : 'Suggested from a document'}</Text>
      {s.located && <button className={classes.link} onClick={() => onEvidence?.(s)}>· {s.located}</button>}
      {s.confidence === 'check' && <Badge size="xs" color="orange" variant="light" tt="none">Please check</Badge>}
    </Group>
    {!inline && <Text size="xs" c="dimmed">{s.question_text}</Text>}
    <Text fw={650} size="sm" className={classes.value}>{s.display}</Text>
    <Text size="xs" c="dimmed" fs="italic" lang="hi">“{s.quote}”</Text>
    <Group gap="xs"><Button size="xs" variant="subtle" onClick={copy}>Copy suggestion</Button>{copied && <Text size="xs" role="status">{copied}</Text>}</Group>
    <div className={classes.comparison}>
      {filled && <Text size="sm" fw={600}>Current answer: {s.current_display || 'Already answered'}</Text>}
      <Radio.Group label="Choose the answer for the form" value={resolution} onChange={setResolution}>
        <Stack gap="xs" mt="xs">
          {filled && <Radio value="keep_site" label="Keep the current answer" disabled={disabled || done}/>}
          <Radio value="use_source" label="Use the suggestion" disabled={disabled || done}/>
          <Radio value="write_own" label="Write my own answer" disabled={disabled || done}/>
        </Stack>
      </Radio.Group>
      {resolution === 'write_own' && <Stack gap="xs" mt="sm">
        {['text', 'single', 'multiple'].includes(kind) && <Textarea label="Your answer" value={own.value || own.custom || ''} disabled={disabled || done}
          onChange={e => setOwn(kind === 'text' ? {value: e.currentTarget.value} : {selected: [], custom: e.currentTarget.value})}/>}
        {kind === 'grid' && <Grid q={ownQuestion} editable={!disabled && !done} onSave={setOwn}/>}
        {kind === 'sum' && <Sum q={ownQuestion} editable={!disabled && !done} onSave={setOwn}/>}
      </Stack>}
      <Text size="xs" c="dimmed" mt="xs">Only your chosen answer goes on the form. The suggestion and previous answer are retained in the review history.</Text>
    </div>
    {done ? <Text size="xs" fw={600} c={s.status === 'accepted' ? 'green.8' : 'dimmed'}>{s.status === 'accepted' ? 'Accepted' : 'Dismissed'}</Text> :
      <Group gap="xs">
        <Button size="sm" className={classes.accept} disabled={disabled || (resolution === 'write_own' && !hasAnswer({answer: own}))} onClick={() => onDecide(s, true, resolution, own)}>Accept</Button>
        <Button size="sm" variant="subtle" color="orange" disabled={disabled} onClick={() => onDecide(s, false)}>Dismiss</Button>
      </Group>}
  </div>;
}

function SourceAudio({source, located = ''}) {
  const player = useRef(null);
  const [failed, setFailed] = useState(false);
  const [version, setVersion] = useState(0);
  const file = source?.files?.[0];
  const seek = () => {
    const match = /^(\d+):(\d+)$/.exec(located);
    if (match && player.current) player.current.currentTime = Number(match[1]) * 60 + Number(match[2]);
  };
  useEffect(seek, [located]);
  if (!file) return <Text size="xs" c="dimmed">Recording file unavailable.</Text>;
  return <div className={classes.audio}><audio key={version} ref={player} controls preload="none" aria-label="Saved site recording"
    src={file.url + (version ? `?retry=${version}` : '')} onLoadedMetadata={seek} onError={() => setFailed(true)}/>
    {failed && <Button variant="subtle" size="xs" onClick={() => { setFailed(false); setVersion(v => v + 1); }}>Reload recording</Button>}
    <Anchor href={file.url} target="_blank" size="xs">Open recording</Anchor></div>;
}

function Review({review, sources, onDecide, onRetry, busy, editable}) {
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const [batch, setBatch] = useState(false);
  const source = sources.find(x => String(x.id) === String(selected?.source)) || review.source;
  const files = source?.files || [];
  const waiting = review.suggestions.filter(s => !s.status || s.status === 'pending');
  const clear = waiting.filter(s => s.confidence === 'clear' && !hasAnswer({answer: s.current_answer}) && !s.current_display);
  const evidence = s => { setSelected(s); const n = /page (\d+)/i.exec(s.located || ''); if (n) setPage(Number(n[1])); };
  useEffect(() => { setSelected(null); setPage(Number(/page (\d+)/i.exec(review.located || '')?.[1] || 1)); }, [review.source?.id]);
  const file = files.find(f => f.page === page) || files[0];
  return <div className={classes.reviewLayout}>
    {source && <div className={classes.documentViewer}>
      <Text fw={600}>{source.kind === 'recording' ? 'Your saved recording' : 'Source pages'}</Text>
      {source.kind === 'recording' ? <SourceAudio source={source} located={selected?.located || review.located}/> : <>
        <Group justify="space-between" my="sm"><Button variant="default" size="xs" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous page</Button><Text size="sm">Page {page} of {files.length}</Text><Button variant="default" size="xs" disabled={page >= files.length} onClick={() => setPage(p => p + 1)}>Next page</Button></Group>
        {file && <a href={file.url} target="_blank" rel="noreferrer"><img className={classes.sourcePage} src={file.url} alt={`Document page ${page}`}/></a>}
        {selected?.quote && <blockquote className={classes.quote}><Text size="xs">Evidence from {selected.located}</Text><mark>{selected.quote}</mark></blockquote>}
      </>}
      {source.text && <details className={classes.transcript}><summary>{source.kind === 'recording' ? 'What you said' : 'What was read'}</summary><Text size="sm" lang="hi" style={{whiteSpace: 'pre-wrap'}}>{source.text}</Text></details>}
    </div>}
    <Stack gap="sm" className={classes.reviewAnswers}>
      <Text size="sm" c="dimmed">Nothing changes on the form until you accept it.</Text>
      {review.error && <Alert color="red" title="This could not be finished"><Text size="sm">{review.error}</Text>
        {review.source?.status === 'failed' && <><Button mt="xs" disabled={busy || !editable} onClick={() => onRetry(review.source)}>Try again</Button><Text size="xs">Your source is saved. You do not need to record or upload it again.</Text></>}
      </Alert>}
      {!review.error && <Text size="sm">{review.suggestions.length ? `${review.suggestions.length} suggested answers` : 'No pending suggestions from this source.'}</Text>}
      {clear.length > 1 && <Button className={classes.accept} disabled={busy || batch || !editable} onClick={async () => { setBatch(true); try { for (const s of clear) await onDecide(s, true); } finally { setBatch(false); } }}>Accept {clear.length} clear answers</Button>}
      {review.suggestions.map(s => <SuggestionCard key={s.id} s={s} disabled={busy || batch || !editable} onDecide={onDecide} onEvidence={evidence}/>)}
    </Stack>
  </div>;
}

// The live microphone needs a secure page (https or localhost). Elsewhere, such as a
// phone opening the office server over http, the phone's own recorder is used instead.
function Recorder({disabled, onRecorded}) {
  const live = typeof window !== 'undefined' && window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder;
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const [unsent, setUnsent] = useState(null);
  const [preview, setPreview] = useState('');
  const alive = useRef(true);
  useEffect(() => { if (!unsent) { setPreview(''); return; } const url = URL.createObjectURL(unsent.blob); setPreview(url); return () => URL.revokeObjectURL(url); }, [unsent]);
  const deliver = async (blob, name) => { setUnsent({blob, name}); if (await onRecorded(blob, name)) setUnsent(null); };
  const media = useRef(null), timer = useRef(null), fallback = useRef(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; clearInterval(timer.current); if (media.current) { media.current.onstop = null; if (media.current.state !== 'inactive') media.current.stop(); media.current.stream?.getTracks().forEach(t => t.stop()); } }; }, []);

  async function start() {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      if (!alive.current) { stream.getTracks().forEach(t => t.stop()); return; }
      const type = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(t => MediaRecorder.isTypeSupported?.(t)) || '';
      const recorder = new MediaRecorder(stream, type ? {mimeType: type} : undefined);
      const chunks = [];
      recorder.ondataavailable = e => e.data.size && chunks.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, {type: recorder.mimeType || type || 'audio/webm'});
        deliver(blob, (recorder.mimeType || type).includes('mp4') ? 'site-recording.m4a' : 'site-recording.webm');
      };
      media.current = recorder;
      recorder.start(1000);
      setSeconds(0); setRecording(true);
      timer.current = setInterval(() => setSeconds(s => { if (s >= 599) { clearInterval(timer.current); setRecording(false); if (recorder.state !== 'inactive') recorder.stop(); } return s + 1; }), 1000);
    } catch {
      setError('The microphone could not be used. Allow it for this site, or use the phone’s recorder.');
    }
  }
  function stop() { clearInterval(timer.current); setRecording(false); if (media.current?.state !== 'inactive') media.current?.stop(); }

  if (recording) return <Button color="red" onClick={stop} className={classes.assistButton}>
    Stop · {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</Button>;
  return <>
    <Button onClick={() => (live ? start() : fallback.current?.click())} disabled={disabled} className={classes.assistButton}>Record</Button>
    <input ref={fallback} type="file" accept="audio/*" capture hidden aria-label="Record with the phone’s recorder"
           onChange={e => { const f = e.currentTarget.files?.[0]; if (f) deliver(f, f.name); e.currentTarget.value = ''; }}/>
    {unsent && <div className={classes.assistNote}><Text size="xs">Recording kept in this page until the server confirms it is saved. Do not close this page during upload.</Text><audio controls src={preview || undefined} aria-label="Recording waiting to upload"/><Button size="xs" disabled={disabled} onClick={() => deliver(unsent.blob, unsent.name)}>Retry upload</Button></div>}
    {error && <Text size="xs" c="red" className={classes.assistNote}>{error} <button className={classes.link} onClick={() => fallback.current?.click()}>Choose a recording</button></Text>}
  </>;
}

function PagePicker({disabled, onPicked}) {
  const input = useRef(null);
  return <>
    <Button variant="light" onClick={() => input.current?.click()} disabled={disabled} className={classes.assistButton}>Read a document</Button>
    <input ref={input} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" multiple hidden aria-label="Photograph the document’s pages"
           onChange={e => { const files = [...(e.currentTarget.files || [])]; if (files.length) onPicked(files.slice(0, 10)); e.currentTarget.value = ''; }}/>
  </>;
}
