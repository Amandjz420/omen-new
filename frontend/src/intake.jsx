import {uuid} from './lib/uuid.js';  // crypto.randomUUID exists only on secure pages
import {BorrowerForm, CaseForm, FollowUpForm, formsFor, ifscBank, ownForm, useLookups} from './screens/IntakeForms.jsx';
import {confirmAction} from './components/confirm.jsx';
import React, {useEffect, useState} from 'react';

const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0,10);
const option = (name, label, options, required = true) => ({name, label, options, required});
const input = (name, label, type = 'text', required = true) => ({name, label, type, required});

function Form({title, fields, initial = {}, save, button = 'Save', children, lead}) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const form = event.currentTarget;
    // An edit form keeps what was saved; resetting it showed the old values again.
    try {await save(Object.fromEntries(new FormData(form))); if (!Object.keys(initial).length) form.reset();}
    catch (e) {setError(e.message);} finally {setBusy(false);}
  }
  return <form onSubmit={submit} className="intake-form"><h3>{title}</h3><div className="intake-fields">
    {lead}
    {fields.map(f => <label key={f.name}>{f.label}{f.options ?
      <select name={f.name} required={f.required} defaultValue={initial[f.name] ?? ''}>
        <option value="">Select…</option>{f.options.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
      </select> : <input name={f.name} type={f.type} required={f.required} defaultValue={initial[f.name] ?? ''}
        min={f.type === 'number' ? 0 : undefined} step={f.type === 'number' ? 'any' : undefined}/>}</label>)}
    {children}</div>{error && <p className="error" role="alert">{error}</p>}
    <button disabled={busy}>{busy ? 'Saving…' : button}</button></form>;
}

function OfficePicker({api, selected, onSelect, catalog}) {
  const [q, setQ] = useState('');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('');
  const [office, setOffice] = useState(null);
  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => api(`offices/?q=${encodeURIComponent(q)}`).then(x => {
      if(active) {setRows(x.results); setError('');}
    }).catch(e => active && setError(e.message)), 200);
    return () => {active = false; clearTimeout(timer);};
  }, [q]);
  async function edit() {
    try {setOffice(await api(`intake/offices/${selected}/`)); setMode('edit');}
    catch(e) {setError(e.message);}
  }
  const fields = [input('name','Client office name'),input('branch_name','Branch','text',false),
    input('address','Address','text',false),option('bank','Bank',catalog.banks,false),
    option('client_type','Client type',catalog.client_types,false),input('state','State','text',false),input('district','District','text',false)];
  return <section className="panel"><h2>Client office</h2>
    <label>Search client offices<input value={q} onChange={e => setQ(e.target.value)} placeholder="Office name, branch or source ID"/></label>
    <label>Select client office<select value={selected || ''} onChange={e => onSelect(e.target.value)}>
      <option value="">Select…</option>{selected && !rows.some(o => o.id === selected) && <option value={selected}>Selected client office</option>}
      {rows.map(o => <option value={o.id} key={o.id}>{o.name} {o.branch ? `· ${o.branch}` : ''}</option>)}
    </select></label><p className="muted">Showing up to 30 matches. Refine your search to find another office.</p>
    <button type="button" onClick={() => {setOffice(null); setMode(mode === 'new' ? '' : 'new');}}>New client office</button>{' '}
    <button type="button" disabled={!selected} onClick={edit}>Edit selected office</button>
    {error && <p role="alert" className="error">{error}</p>}
    {mode && <Form key={mode+(office?.id || '')} title={mode === 'new' ? 'Create client office' : 'Edit client office'} fields={fields} initial={office || {}}
      save={async data => {
        const saved = await api(`intake/offices/${mode === 'edit' ? `${office.id}/` : ''}`, {method: mode === 'edit' ? 'PATCH' : 'POST',body: JSON.stringify(data)});
        setRows(rows => [{...saved, branch:saved.branch_name},...rows.filter(o => o.id !== saved.id)]);
        onSelect(saved.id); setMode('');
      }}/>}</section>;
}

function Contacts({api, office, catalog, value, onSelect}) {
  const [rows,setRows] = useState([]);
  const [mode,setMode] = useState('');
  const [error,setError] = useState('');
  async function load() {
    const x = await api(`intake/contacts/?office=${office}`); setRows(x.results);
  }
  useEffect(() => {
    let active = true; setRows([]); setMode('');
    if (office) api(`intake/contacts/?office=${office}`).then(x => active && setRows(x.results)).catch(e => active && setError(e.message));
    return () => {active = false;};
  },[office]);
  const selected = rows.find(r => r.id === value);
  return <section className="panel"><h2>Client contact</h2><label>Select contact<select disabled={!office} value={value || ''} onChange={e => onSelect(e.target.value)}>
    <option value="">No contact selected</option>{rows.map(r => <option key={r.id} value={r.id}>{r.name} · {r.phone}</option>)}</select></label>
    <button type="button" disabled={!office} onClick={() => setMode(mode === 'new' ? '' : 'new')}>New contact</button>{' '}
    <button type="button" disabled={!selected} onClick={() => setMode('edit')}>Edit selected contact</button>
    {error && <p role="alert" className="error">{error}</p>}
    {mode && <Form key={mode+(selected?.id || '')} title={mode === 'new' ? 'Create contact' : 'Edit contact'}
      fields={[input('name','Contact name'),input('phone','Phone','tel',false),input('alternate_phone','Alternate phone','tel',false),option('designation','Designation',catalog.designations,false)]}
      initial={mode === 'edit' ? {...selected,designation:selected?.designation_id} : {}}
      save={async data => {
        const x = await api(`intake/contacts/${mode === 'edit' ? `${selected.id}/` : ''}`, {method: mode === 'edit' ? 'PATCH':'POST',body:JSON.stringify({...data,office})});
        await load(); onSelect(x.id);setMode('');
      }}/>}</section>;
}

// The subtype list depends on the service, so the service comes first. It had come
// after the subtype, which then showed an empty list before any service was chosen.
export function ServiceForm({catalog, save, ifsc = ''}) {
  const [service,setService] = useState('');
  // The bank decides the form: its own pre-chosen, another bank's not offered.
  const bank = ifscBank(ifsc);
  const subtypes = formsFor(catalog.subtypes.filter(s => s.service_id === service), bank);
  const own = ownForm(subtypes, bank);
  const hint = !service ? 'Choose a service first' : subtypes.length ? 'Select…' : 'This service has no subtypes';
  return <Form title="Add requested service" save={save}
    fields={[input('party_count','Expected parties','number',false),input('case_count','Expected cases','number',false)]}
    lead={<>
      <label>Service<select name="service" required value={service} onChange={e => setService(e.target.value)}>
        <option value="">Select…</option>{catalog.services.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}
      </select></label>
      <label>Asset subtype<select name="subtype" key={`${service}-${own?.id || ''}`} defaultValue={own ? own.id : ''} disabled={!service || !subtypes.length}>
        <option value="">{hint}</option>{subtypes.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}
      </select></label>
    </>}/>;
}

const label = (rows, code) => (rows || []).find(r => String(r.code) === String(code))?.label;

export function IntakeLead({api, leadId, catalog: supplied, onChange}) {
  const {data: lookups} = useLookups();
  const [catalog,setCatalog] = useState(supplied);
  const [lead,setLead] = useState(null);
  const [error,setError] = useState('');
  const [contact,setContact] = useState('');
  async function reload() {
    const x = await api(`intake/leads/${leadId}/`);setLead(x);setContact(x.contact || '');
    onChange?.();
  }
  useEffect(() => {
    let active = true;
    Promise.all([supplied ? Promise.resolve(supplied) : api('intake/catalog/'),api(`intake/leads/${leadId}/`)]).then(([c,l]) => {
      if(active) {setCatalog(c);setLead(l);setContact(l.contact || '');setError('');}
    }).catch(e => active && setError(e.message));
    return () => {active = false;};
  },[leadId]);
  async function add(kind, data) {
    const created = await api(`intake/leads/${leadId}/${kind}/`,{method:'POST',body:JSON.stringify(data)});await reload();
    return created;                                     // the form keeps editing the record it created
  }
  const [editing,setEditing] = useState(null);          // {kind, record}
  async function change(kind, id, data) {
    await api(`intake/leads/${leadId}/${kind}/${id}/`,{method:'PATCH',body:JSON.stringify(data)});await reload();   // the form stays open with what was saved
  }
  async function remove(kind, record, what) {
    const ok = await confirmAction({title: `Delete ${what}?`, danger: true, confirmLabel: 'Delete',
      consequence: kind === 'borrowers' ? `${record.name} is removed from this lead. A customer with cases keeps them until those are deleted first.`
        : 'This case is removed from the lead. It is kept in the history, not erased.'});
    if (!ok) return;
    try {await api(`intake/leads/${leadId}/${kind}/${record.id}/`,{method:'DELETE'});await reload();} catch (e) {setError(e.message);}
  }
  const named = (list,id) => list.find(x => x.id === id)?.name || 'Not specified';
  if(error) return <p role="alert" className="error">{error}</p>;
  if(!lead || !catalog) return <p>Loading lead intake…</p>;
  return <div className="intake"><section className="panel"><h2>{lead.number} · {lead.office_name}</h2>
    <p>Status: {{'1':'New','2':'In process','3':'Cancelled','4':'Closed'}[lead.legacy_status] || 'Unknown'}</p>
    {!lead.editable && <p className="notice">Intake is locked because this lead is cancelled, closed, has an unknown status, or already has a work order.</p>}
    <h3>Requested services</h3><ul>{lead.services.map(s => <li key={s.id}>{named(catalog.services,s.service_id)} · {named(catalog.subtypes,s.subtype_id)}</li>)}</ul>
    <h3>Client's customers</h3><ul>{lead.borrowers.map(b => <li key={b.id}>{lead.editable && <span className="row-actions"><button type="button" className="link" onClick={() => setEditing({kind: 'borrowers', record: b})}>Edit</button> · <button type="button" className="link" onClick={() => remove('borrowers', b, b.name)}>Delete</button> · </span>}{b.name}{b.contact_number ? ` · ${b.contact_number}` : ''} · {b.property_count || 0} case(s) · {label(lookups?.payers, b.payer) || 'Payer not recorded'} · {b.fee_basis === 2 ? `Fixed ₹${Number(b.agreed_fee || 0).toLocaleString('en-IN')}` : label(lookups?.fee_bases, b.fee_basis) || ''}</li>)}</ul>
    <h3>Cases</h3><ul>{lead.cases.map(c => <li key={c.id}>{lead.editable && <span className="row-actions"><button type="button" className="link" onClick={() => setEditing({kind: 'cases', record: c})}>Edit</button> · <button type="button" className="link" onClick={() => remove('cases', c, 'this case')}>Delete</button> · </span>}{named(lead.borrowers,c.borrower_id)} · {c.asset_address}{c.asset_district ? `, ${c.asset_district}` : ''}{c.asset_state ? `, ${c.asset_state}` : ''}{c.asset_pin_code ? ` ${c.asset_pin_code}` : ''}{c.expected_report_date ? ` · report by ${c.expected_report_date}` : ''}</li>)}</ul>
    <h3>Follow-ups</h3>{lead.follow_ups.map(f => <article className="note" key={f.id}><strong>{label(lookups?.follow_up_statuses, f.call_status) || f.call_status}</strong><p>{f.remark}</p><small>{(f.logged_date_text || '').slice(0, 10) ? `Call back ${(f.logged_date_text || '').slice(0, 10)} ${f.logged_time_text || ''}` : ''}</small></article>)}
  </section>{lead.editable && <>
    <Contacts api={api} office={lead.office} catalog={catalog} value={contact} onSelect={setContact}/>
    <section className="panel"><Form key={lead.updated_at || lead.id} title="Assignment and intake date" initial={{assigned_employee:lead.assigned_employee,received_date:lead.received_date}}
      fields={[option('assigned_employee','Assigned employee',catalog.employees,false),input('received_date','Received date','date')]}
      save={async data => {await api(`intake/leads/${leadId}/`,{method:'PATCH',body:JSON.stringify({...data,contact})});await reload();}}/>
    <ServiceForm catalog={catalog} ifsc={lead.office_detail?.ifsc} save={data => add('services',data)}/>
    {editing?.kind === 'borrowers' && <BorrowerForm key={editing.record.id} lead={lead} initial={editing.record} onCancel={() => setEditing(null)}
      onUpdate={(id, data) => change('borrowers', id, data)}/>}
    {editing?.kind === 'cases' && <CaseForm key={editing.record.id} lead={lead} catalog={catalog} initial={editing.record} onCancel={() => setEditing(null)}
      onUpdate={(id, data) => change('cases', id, data)}/>}
    {/* The legacy intake sequence: follow-up, then each client's customer, then each case. */}
    <FollowUpForm onSave={data => add('follow-ups', data)}/>
    <BorrowerForm lead={lead} onSave={data => add('borrowers', data)} onUpdate={(id, data) => change('borrowers', id, data)}/>
    {lead.borrowers.length > 0 && <CaseForm lead={lead} catalog={catalog} onSave={data => add('cases', data)} onUpdate={(id, data) => change('cases', id, data)}/>}
    <Form title="Cancel lead" button="Cancel lead" fields={[input('cancel_reason','Reason for cancellation')]}
      save={async data => {await api(`intake/leads/${leadId}/`,{method:'PATCH',body:JSON.stringify(data)});await reload();}}/>
    </section></>}
    <section className="panel"><h3>Lead change history</h3>{lead.audit.map((a,i) => <p key={i}>{a.action} · {a.actor__username} · {new Date(a.created_at).toLocaleString()}</p>)}</section>
  </div>;
}

export default function IntakeWorkspace({api}) {
  const [catalog,setCatalog] = useState(null);
  const [office,setOffice] = useState('');
  const [contact,setContact] = useState('');
  const [leadId,setLeadId] = useState(null);
  const [error,setError] = useState('');
  const [key,setKey] = useState(() => uuid());
  useEffect(() => {let active=true;api('intake/catalog/').then(x => active && setCatalog(x)).catch(e => active && setError(e.message));return () => {active=false;};},[]);
  if(error) return <p role="alert" className="error">{error}</p>;
  if(!catalog) return <p>Loading intake options…</p>;
  if(leadId) return <><button onClick={() => {setLeadId(null);setKey(uuid());}}>Create another lead</button><IntakeLead api={api} leadId={leadId} catalog={catalog}/></>;
  return <div className="intake"><p className="intro">Add or edit client offices and their lead givers. Record new leads on the New lead form, which finds a lead giver by mobile number.</p>
    <OfficePicker api={api} selected={office} onSelect={id => {setOffice(id);setContact('');}} catalog={catalog}/>
    <Contacts api={api} office={office} catalog={catalog} value={contact} onSelect={setContact}/>
  </div>;
}
