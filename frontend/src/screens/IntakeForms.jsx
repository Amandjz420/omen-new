import {Alert, Anchor, Button, Group, MultiSelect, Paper, Radio, Select, SimpleGrid, Stack, Table, Text, TextInput, Textarea, Title} from '@mantine/core';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useEffect, useMemo, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import {PageHeader} from '../components/PageHeader.jsx';
import {ErrorState, LoadingState} from '../components/States.jsx';
import {api, post} from '../lib/api.js';
import {uuid} from '../lib/uuid.js';
import {today} from '../lib/format.js';

// The legacy intake forms (design/add_lead, add_feedback, add_client, add_case), field
// for field and in the same order, with everything the legacy forms filled in for the
// person, and more where the data allows.

export const useLookups = () => useQuery({queryKey: ['intake', 'lookups'], queryFn: () => api('intake/lookups/'), staleTime: 600_000});
export const useCatalog = () => useQuery({queryKey: ['intake', 'catalog'], queryFn: () => api('intake/catalog/'), staleTime: 600_000});
const options = (rows = [], label = 'name') => rows.map(r => ({value: String(r.id ?? r.code), label: String(r[label] ?? r.label ?? '').trim()}));
const codes = (rows = []) => rows.map(r => ({value: String(r.code), label: r.label}));
const digitsOf = v => String(v || '').replace(/\D/g, '').slice(-10);

// A bank's own valuation form is its own subtype, named with its IFSC prefix, as in
// L & B ( SBIN); a client office's bank is its IFSC's prefix (apps/catalog/banks.py).
export const formBank = name => (String(name || '').match(/\(\s*([A-Z]{4})\s*\)\s*$/) || [])[1] || null;
export const ifscBank = ifsc => (String(ifsc || '').trim().toUpperCase().match(/^([A-Z]{4})0[A-Z0-9]{6}$/) || [])[1] || null;
/** The forms this bank's leads may use: the general ones and the bank's own. */
export const formsFor = (subtypes, bank) => subtypes.filter(s => !bank || !formBank(s.name) || formBank(s.name) === bank);
export const ownForm = (subtypes, bank) => (bank && subtypes.find(s => formBank(s.name) === bank)) || null;

function ReadOnly({label, value}) {
  return <TextInput label={label} value={value || '—'} readOnly variant="filled"/>;
}

function Section({title, children}) {
  return <Paper withBorder p="md"><Title order={3} mb="sm">{title}</Title><Stack gap="sm">{children}</Stack></Paper>;
}

const FI = 'Financial Institution';
const typeName = (types, id) => (types || []).find(t => String(t.id) === String(id))?.name || '';

/** Client review 2026-11-05: an organisation (a client office) is added on the lead form
 * itself. Every organisation has a name, address, place and GST/PAN; only a Financial
 * Institution has an IFSC. Since client review 2026-11-25 the "client" is the person who
 * orders the work, and the body they work for is the "organisation". */
function NewClientPanel({clientType, typeLabel, lookups, onCreated, onCancel}) {
  const blank = {name: '', branch_name: '', address: '', state: null, district: null, block: null, gstin: '', pan: '', ifsc: ''};
  const [f, setF] = useState(blank);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setF(x => ({...x, [k]: v, ...(k === 'state' ? {district: null, block: null} : {}), ...(k === 'district' ? {block: null} : {})}));
  const named = (rows, id) => rows.find(r => String(r.id) === String(id))?.name || '';
  async function save() {
    setError('');
    if (!f.name.trim() || !f.address.trim()) { setError('Enter the organisation name and address'); return; }
    setBusy(true);
    try {
      const created = await post('intake/offices/', {name: f.name, branch_name: f.branch_name, address: f.address, client_type: clientType,
        gstin: f.gstin, pan: f.pan, ifsc: typeLabel === FI ? f.ifsc : '', block: f.block || null,
        state: named(lookups.states, f.state), district: named(lookups.districts, f.district)});
      await onCreated(created);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  // Not a nested form: the panel sits inside the lead form, so it saves on its own button.
  return <Paper withBorder p="md" bg="gray.0" aria-label="New organisation">
    <Title order={4} mb="xs">New organisation{typeLabel ? ` (${typeLabel})` : ''}</Title>
    {error && <Alert color="red" variant="light" role="alert" mb="xs">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <TextInput label={typeLabel === 'Individual' ? 'Name (person)' : 'Organisation name'} required value={f.name} onChange={e => set('name', e.currentTarget.value)}/>
      <TextInput label="Branch / unit" value={f.branch_name} onChange={e => set('branch_name', e.currentTarget.value)}/>
      {typeLabel === FI && <TextInput label="IFSC code" value={f.ifsc} maxLength={11} onChange={e => set('ifsc', e.currentTarget.value.toUpperCase())}/>}
      <TextInput label="GST no." value={f.gstin} maxLength={15} onChange={e => set('gstin', e.currentTarget.value.toUpperCase())}/>
      <TextInput label="PAN" value={f.pan} maxLength={10} onChange={e => set('pan', e.currentTarget.value.toUpperCase())}/>
    </SimpleGrid>
    <Textarea label="Address" required mt="sm" value={f.address} onChange={e => set('address', e.currentTarget.value)} autosize minRows={2}/>
    <SimpleGrid cols={{base: 1, sm: 3}} mt="sm">
      <Select label="State" searchable data={options(lookups.states)} value={f.state} onChange={v => set('state', v)} placeholder="Select…"/>
      <Select label="District" searchable data={options(lookups.districts.filter(d => String(d.state_id) === String(f.state)))} value={f.district}
              onChange={v => set('district', v)} disabled={!f.state} placeholder={f.state ? 'Select…' : 'Choose a state first'}/>
      <Select label="City" searchable data={options(lookups.blocks.filter(b => String(b.district_id) === String(f.district)))} value={f.block}
              onChange={v => set('block', v)} disabled={!f.district} placeholder={f.district ? 'Select…' : 'Choose a district first'}/>
    </SimpleGrid>
    <Group mt="sm"><Button onClick={save} loading={busy}>Save organisation</Button><Button variant="subtle" onClick={onCancel}>Cancel</Button></Group>
  </Paper>;
}

/** design/add_lead.jsp: the client (who orders the work; the "orderer" until client review
 * 2026-11-25) found by mobile number, else registered; who contacted us, if someone else;
 * how many applicants and cases to expect. No service is chosen here: each case names
 * its own. The lead is received by the person recording it and assigned later, when
 * someone picks it up. With editId the same form edits a saved lead, filled with what
 * was entered (client review 2026-11-05). */
export function NewLeadForm() {
  const {id: editId} = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const lookups = useLookups(), catalog = useCatalog();
  const me = lookups.data?.me?.employee_id || null;
  const saved = useQuery({queryKey: ['intake', 'lead', editId], queryFn: () => api(`intake/leads/${editId}/`), enabled: !!editId});
  const [requestId] = useState(uuid);
  const [mode, setMode] = useState(null);
  const [mobile, setMobile] = useState('');
  const [alternate, setAlternate] = useState('');
  const [chosen, setChosen] = useState(null);
  const [giver, setGiver] = useState({client_type: null, office: null, name: '', division: null, subdivision: null, designation: null});
  const [ifsc, setIfsc] = useState('');
  const [ifscResult, setIfscResult] = useState(null);
  const [addingClient, setAddingClient] = useState(false);
  const [contactedBy, setContactedBy] = useState({name: '', phone: '', remark: ''});
  const [parties, setParties] = useState('');
  const [cases, setCases] = useState('');
  const [receivedBy, setReceivedBy] = useState(null);
  const [receivedDate, setReceivedDate] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filled, setFilled] = useState(false);

  // Editing: the form opens with what was saved.
  useEffect(() => {
    const l = saved.data;
    if (!l || filled) return;
    setMode(l.enquiry_mode ? String(l.enquiry_mode) : null);
    setMobile(l.orderer?.phone || ''); setAlternate(l.orderer?.alternate_phone || '');
    setContactedBy({name: l.contacted_by_name || '', phone: l.contacted_by_phone || '', remark: l.contacted_by_remark || ''});
    setParties(l.party_count ? String(l.party_count) : '');
    setCases(l.case_count ? String(l.case_count) : '');
    setReceivedDate(l.received_date || '');
    setFilled(true);
  }, [saved.data]);   // eslint-disable-line react-hooks/exhaustive-deps

  const digits = digitsOf(mobile);
  const found = useQuery({queryKey: ['intake', 'orderer', digits], queryFn: () => api(`intake/lookups/orderer/?mobile=${digits}`),
                          enabled: digits.length === 10, retry: false});
  const matches = digits.length === 10 ? found.data?.matches || [] : [];
  useEffect(() => {
    const current = saved.data?.orderer?.id;
    setChosen(current && matches.some(m => String(m.id) === String(current)) ? String(current) : matches.length ? String(matches[0].id) : null);
  }, [found.data, digits]);   // eslint-disable-line react-hooks/exhaustive-deps
  const known = matches.find(m => String(m.id) === chosen);
  const isNew = digits.length === 10 && found.isSuccess && !known;
  const offices = useQuery({queryKey: ['intake', 'offices', giver.client_type], enabled: isNew && !!giver.client_type,
                            queryFn: () => api(`intake/lookups/offices/?client_type=${giver.client_type}`)});
  const office = (offices.data?.results || []).find(o => String(o.id) === giver.office) || ifscResult?.office || null;
  const setG = (key, value) => setGiver(g => ({...g, [key]: value, ...(key === 'client_type' ? {office: null} : {}), ...(key === 'division' ? {subdivision: null} : {})}));
  const chosenType = typeName(lookups.data?.client_types, giver.client_type);
  const isFI = chosenType === FI;
  useEffect(() => { if (!isFI) { setIfsc(''); setIfscResult(null); } }, [isFI]);

  async function findIfsc() {
    setError('');
    try {
      const r = await api(`intake/lookups/ifsc/?code=${encodeURIComponent(ifsc.trim())}`);
      const first = r.offices[0];
      setIfscResult({office: first || null, directory: first ? null : r.directory});
      if (first) setGiver(g => ({...g, client_type: first.client_type_id ? String(first.client_type_id) : g.client_type, office: String(first.id)}));
      if (!first && !r.directory) setError('No organisation or bank branch has this IFSC.');
    } catch (e) { setError(e.message); }
  }
  async function addFromDirectory() {
    const d = ifscResult.directory;
    try {
      const created = await post('intake/offices/', {name: d.bank, branch_name: d.branch, address: d.address, bank: d.bank_id,
                                                    state: d.state, district: d.district, ifsc: d.ifsc, client_type: giver.client_type});
      const r = await api(`intake/lookups/ifsc/?code=${d.ifsc}`);
      setIfscResult({office: r.offices.find(o => String(o.id) === String(created.id)) || r.offices[0], directory: null});
      setGiver(g => ({...g, office: String(created.id)}));
    } catch (e) { setError(e.message); }
  }
  async function clientCreated(created) {
    await client.invalidateQueries({queryKey: ['intake', 'offices']});
    await offices.refetch();
    setIfscResult(null);
    setGiver(g => ({...g, office: String(created.id)}));
    setAddingClient(false);
  }

  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true);
    const orderer = known ? {contact: known.id} : {new_contact: {name: giver.name, phone: digits, office: office?.id, designation: giver.designation,
                                                                 division: giver.division, subdivision: giver.subdivision}};
    const common = {enquiry_mode: Number(mode), ...orderer, party_count: Number(parties), case_count: Number(cases),
      contacted_by_name: contactedBy.name, contacted_by_phone: contactedBy.phone, contacted_by_remark: contactedBy.remark,
      ...(alternate ? {alternate_phone: alternate} : {})};
    try {
      if (editId) {
        // An unchanged client is not sent again, so their record is not touched.
        const body = {...common, ...(receivedDate ? {received_date: receivedDate} : {})};
        if (known && String(known.id) === String(saved.data?.orderer?.id)) delete body.contact;
        await api(`intake/leads/${editId}/`, {method: 'PATCH', body: JSON.stringify(body)});
        for (const queryKey of [['leads'], ['home'], ['lead', editId], ['intake', 'lead', editId]]) client.invalidateQueries({queryKey});
        navigate(`/leads/${editId}?tab=details`);
      } else {
        // Received by the person signed in; only an account with no employee record names who.
        const lead = await post('intake/leads/', {request_id: requestId, ...common, ...(me ? {} : {received_by: receivedBy})});
        client.invalidateQueries({queryKey: ['leads']}); client.invalidateQueries({queryKey: ['home']});
        navigate(`/leads/${lead.id}`);
      }
    } catch (e) { setError(e.message); setBusy(false); }
  }

  if (lookups.isError || catalog.isError || saved.isError) return <ErrorState error={lookups.error || catalog.error || saved.error}/>;
  if (!lookups.data || !catalog.data || (editId && !filled)) return <LoadingState label="Opening the lead form"/>;
  const L = lookups.data, C = catalog.data;
  const named = (rows, id) => (rows || []).find(r => String(r.id) === String(id))?.name || '';
  const subdivisions = L.subdivisions.filter(s => String(s.division_id) === String(giver.division));
  const locked = editId && !saved.data.editable;

  return <form onSubmit={submit}><Stack gap="md" maw={900}>
    {editId && <Anchor component={Link} to={`/leads/${editId}?tab=details`} size="sm">Back to the lead</Anchor>}
    <PageHeader title={editId ? `Edit lead ${saved.data.number || ''}` : 'New lead'}
                description={editId ? 'Change what was entered when the lead was created.' : "Enter the client's mobile number: a known client's details fill in."}/>
    {locked && <Alert color="yellow" variant="light">This lead is cancelled, closed or already has a work order, so it can no longer be edited.</Alert>}
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}

    <Section title="Client information">
      <SimpleGrid cols={{base: 1, sm: 3}}>
        <Select label="Mode" required data={codes(L.modes)} value={mode} onChange={setMode} placeholder="Select…"/>
        <TextInput label="Client mobile no." required value={mobile} onChange={e => setMobile(e.currentTarget.value)}
                   inputMode="numeric" maxLength={14} placeholder="10 digits" description={found.isFetching ? 'Looking up…' : undefined}/>
        <TextInput label="Alternate contact number" value={alternate} onChange={e => setAlternate(e.currentTarget.value)} inputMode="numeric"
                   placeholder="Without the 0 prefix"/>
      </SimpleGrid>

      {matches.length > 1 && <Radio.Group label="This number belongs to more than one client" value={chosen} onChange={setChosen}>
        <Stack gap={4} mt={4}>{matches.map(m => <Radio key={m.id} value={String(m.id)}
          label={`${m.name}, ${m.office?.name || ''} ${m.office?.branch || ''} (${m.leads} leads)`}/>)}<Radio value="" label="Someone else: register a new client"/></Stack>
      </Radio.Group>}

      {known && <SimpleGrid cols={{base: 1, sm: 3}} aria-label="The client's details">
        <ReadOnly label="Client name" value={known.name}/><ReadOnly label="Designation" value={known.designation}/>
        <ReadOnly label="City" value={known.office?.city}/><ReadOnly label="Organisation type" value={known.office?.client_type}/>
        <ReadOnly label="Organisation name" value={known.office?.name}/><ReadOnly label="Branch" value={known.office?.branch}/>
        <ReadOnly label="Division" value={[known.division, known.subdivision].filter(Boolean).join(' / ')}/>
        <ReadOnly label="Address" value={known.office?.address}/><ReadOnly label="GST No." value={known.office?.gstin}/>
        <ReadOnly label="PAN" value={known.office?.pan}/>
        {known.office?.ifsc && <ReadOnly label="IFSC" value={known.office.ifsc}/>}
      </SimpleGrid>}

      {isNew && <>
        <Text size="sm" c="dimmed">No client has this number. Register them with the lead.</Text>
        <SimpleGrid cols={{base: 1, sm: 3}}>
          <Select label="Organisation type" required data={options(L.client_types)} value={giver.client_type} onChange={v => { setG('client_type', v); setAddingClient(false); }} placeholder="Select…"/>
          <Select label="Organisation name" required searchable data={(offices.data?.results || []).map(o => ({value: String(o.id), label: `${o.name}${o.branch ? ', ' + o.branch : ''}`}))}
                  value={giver.office} onChange={v => { setG('office', v); setIfscResult(null); }} disabled={!giver.client_type}
                  placeholder={giver.client_type ? 'Select…' : 'Choose an organisation type first'}/>
          {isFI ? <Group align="flex-end" gap="xs" wrap="nowrap">
            <TextInput label="IFSC code" value={ifsc} onChange={e => setIfsc(e.currentTarget.value.toUpperCase())} maxLength={11} style={{flex: 1}}/>
            <Button variant="light" onClick={findIfsc} disabled={ifsc.trim().length !== 11}>Find</Button>
          </Group> : <Group align="flex-end"><Button variant="light" onClick={() => setAddingClient(a => !a)} disabled={!giver.client_type}>New organisation</Button></Group>}
        </SimpleGrid>
        {isFI && <Group><Button variant="subtle" size="xs" onClick={() => setAddingClient(a => !a)}>Not listed? Add a new organisation</Button></Group>}
        {addingClient && giver.client_type && <NewClientPanel clientType={giver.client_type} typeLabel={chosenType} lookups={L}
          onCreated={clientCreated} onCancel={() => setAddingClient(false)}/>}
        {isFI && ifscResult?.directory && <Alert variant="light" color="blue" title="Not yet an organisation: found in the bank directory">
          <Text size="sm">{ifscResult.directory.bank}, {ifscResult.directory.branch} — {ifscResult.directory.address}, {ifscResult.directory.district}, {ifscResult.directory.state}</Text>
          <Button mt="xs" size="xs" onClick={addFromDirectory}>Add this branch as an organisation</Button>
        </Alert>}
        <SimpleGrid cols={{base: 1, sm: 3}}>
          <TextInput label="Client name" required value={giver.name} onChange={e => setG('name', e.currentTarget.value)}/>
          <Select label="Division" required data={options(L.divisions)} value={giver.division} onChange={v => setG('division', v)} placeholder="Select…"/>
          <Select label="Sub division" required data={options(subdivisions)} value={giver.subdivision} onChange={v => setG('subdivision', v)}
                  disabled={!giver.division} placeholder={giver.division ? 'Select…' : 'Choose a division first'}/>
          <Select label="Client designation" required data={options(L.designations)} value={giver.designation} onChange={v => setG('designation', v)} placeholder="Select…"/>
          <ReadOnly label="Branch" value={office?.branch}/><ReadOnly label="Organisation address" value={office?.address}/>
          <ReadOnly label="Organisation state" value={office?.state}/><ReadOnly label="Organisation district" value={office?.district}/>
          <ReadOnly label="Organisation city" value={office?.city}/>
          <ReadOnly label="GST No." value={office?.gstin}/><ReadOnly label="PAN" value={office?.pan}/>
        </SimpleGrid>
      </>}
    </Section>

    <Section title="Contacted by (optional)">
      <Text size="sm" c="dimmed">The person who passed on the lead, when it is not the client. Kept for reference; not printed on the work order.</Text>
      <SimpleGrid cols={{base: 1, sm: 3}}>
        <TextInput label="Name" value={contactedBy.name} onChange={e => { const v = e.currentTarget.value; setContactedBy(c => ({...c, name: v})); }}/>
        <TextInput label="Mobile no." inputMode="numeric" maxLength={14} value={contactedBy.phone} onChange={e => { const v = e.currentTarget.value; setContactedBy(c => ({...c, phone: v})); }}/>
        <TextInput label="Remark" value={contactedBy.remark} onChange={e => { const v = e.currentTarget.value; setContactedBy(c => ({...c, remark: v})); }}/>
      </SimpleGrid>
    </Section>

    <Section title="Lead information">
      <SimpleGrid cols={{base: 1, sm: 3}}>
        <TextInput label="No. of applicants" required inputMode="numeric" value={parties} onChange={e => setParties(e.currentTarget.value)}/>
        <TextInput label="No. of cases" required inputMode="numeric" value={cases} onChange={e => setCases(e.currentTarget.value)}
                   description="The service for each case is chosen when the case is entered."/>
      </SimpleGrid>
    </Section>

    <Section title="Other details (for internal use only)">
      <SimpleGrid cols={{base: 1, sm: editId ? 3 : 2}}>
        {editId ? <ReadOnly label="Lead received by" value={saved.data.received_by_name}/>
          : me ? <ReadOnly label="Lead received by" value={L.me?.name || named(C.employees, me)}/>
          : <Select label="Lead received by" required searchable data={options(C.employees)} value={receivedBy} onChange={setReceivedBy} placeholder="Select…"
                    description="Your login has no employee record, so choose who received the lead."/>}
        {editId ? <ReadOnly label="Lead assigned to" value={saved.data.assigned_name || 'Not picked up yet'}/>
          : <ReadOnly label="Lead assigned to" value="Assigned when someone picks up the lead"/>}
        {editId && <TextInput label="Received date" type="date" required value={receivedDate} onChange={e => setReceivedDate(e.currentTarget.value)}/>}
      </SimpleGrid>
    </Section>
    <Group><Button type="submit" loading={busy} disabled={digits.length !== 10 || !mode || locked}>{editId ? 'Save changes' : 'Save the lead'}</Button>
      {editId && <Button variant="subtle" component={Link} to={`/leads/${editId}?tab=details`}>Cancel</Button>}</Group>
  </Stack></form>;
}

/** design/add_feedback.jsp: the follow-up status, when to call back, and a remark. */
export function FollowUpForm({onSave}) {
  const lookups = useLookups();
  const [f, setF] = useState({status: null, date: today(), hour: '10', minute: '00', remark: ''});
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);              // what was saved stays on screen; Save waits for a change
  const set = (k, v) => { setSaved(false); setF(x => ({...x, [k]: v})); };
  const hours = Array.from({length: 24}, (_, i) => String(i).padStart(2, '0'));
  const minutes = ['00', '05', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'];
  async function submit(e) {
    e.preventDefault(); setError('');
    try { await onSave({status: f.status, notify_date: f.date, notify_time: `${f.hour}:${f.minute}`, remark: f.remark});
      setSaved(true); } catch (err) { setError(err.message); }
  }
  if (!lookups.data) return null;
  return <form onSubmit={submit}><Section title="Follow up for lead">
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 2, sm: 4}}>
      <Select label="Follow up status" required data={codes(lookups.data.follow_up_statuses)} value={f.status} onChange={v => set('status', v)} placeholder="Select…"/>
      <TextInput label="Date to be notified" required type="date" value={f.date} onChange={e => set('date', e.currentTarget.value)}/>
      <Select label="Hour" required data={hours} value={f.hour} onChange={v => set('hour', v)} allowDeselect={false}/>
      <Select label="Minute" required data={minutes} value={f.minute} onChange={v => set('minute', v)} allowDeselect={false}/>
    </SimpleGrid>
    <Textarea label="Please specify the remark if any" required value={f.remark} onChange={e => set('remark', e.currentTarget.value)} autosize minRows={2}/>
    <Group><Button type="submit" disabled={saved}>Save follow-up</Button>{saved && <Text size="sm" c="green.8" role="status">Saved. Change anything to record another follow-up.</Text>}</Group>
  </Section></form>;
}

/** design/add_client.jsp: the applicant (the client's customer) and the fee agreement. Paid
 * by the client: the payer is the lead's organisation and client, and payment
 * responsibility defaults to the client. Fixed fee: the work order amount. For an
 * Individual lead the client is the applicant, so a new one starts with the client's
 * name and mobile (client review 2026-11-25). */
export function BorrowerForm({lead, onSave, onUpdate, initial = null, onCancel}) {
  const lookups = useLookups();
  const individual = lead.office_detail?.client_type === 'Individual';
  const who = individual ? 'client' : 'applicant';
  const fromRecord = b => b && ({name: b.name || '', contact_number: b.contact_number || '', email: b.email || '', gst_number: b.gst_number || '',
    property_count: String(b.property_count ?? 1), payer: String(b.payer ?? 1), fee_basis: String(b.fee_basis ?? 1),
    agreed_fee: b.agreed_fee != null ? String(Number(b.agreed_fee)) : '', payment_reference_name: b.payment_reference_name || '',
    payment_reference_number: b.payment_reference_number || '', pay_by_date: b.pay_by_date || '', customer_payment_method: String(b.customer_payment_method ?? 1)});
  const blank = {name: individual ? lead.contact?.name || '' : '', contact_number: individual ? lead.contact?.phone || '' : '', email: '', gst_number: '', property_count: '1', payer: '1', fee_basis: '1', agreed_fee: '',
                 payment_reference_name: lead.contact?.name || '', payment_reference_number: lead.contact?.phone || '', pay_by_date: '',
                 customer_payment_method: '1'};
  const [f, setF] = useState(() => fromRecord(initial) || blank);
  const [error, setError] = useState('');
  // Once saved, the form keeps the values and edits that same record, so saving again
  // updates it instead of adding a duplicate.
  const [recordId, setRecordId] = useState(initial?.id || null);
  const [saved, setSaved] = useState(false);
  const set = (k, v) => { setSaved(false); setF(x => {
    const next = {...x, [k]: v};
    if (k === 'payer') {                                   // the payment responsibility follows who pays, until edited
      const giver = {name: lead.contact?.name || '', phone: lead.contact?.phone || ''};
      if (v === '1' && !x.payment_reference_name) Object.assign(next, {payment_reference_name: giver.name, payment_reference_number: giver.phone});
      if (v === '2' && x.payment_reference_name === giver.name) Object.assign(next, {payment_reference_name: x.name, payment_reference_number: x.contact_number});
    }
    return next;
  }); };
  async function submit(e) {
    e.preventDefault(); setError('');
    const body = {...f, property_count: Number(f.property_count), payer: Number(f.payer), fee_basis: Number(f.fee_basis),
                  customer_payment_method: Number(f.customer_payment_method), agreed_fee: f.fee_basis === '2' ? f.agreed_fee : null,
                  email: f.email || '', gst_number: f.gst_number || ''};
    try {
      if (recordId) await onUpdate(recordId, body);
      else setRecordId((await onSave(body))?.id || null);
      setSaved(true);
    } catch (err) { setError(err.message); }
  }
  if (!lookups.data) return null;
  const L = lookups.data;
  return <form onSubmit={submit}><Section title={recordId ? `Edit ${f.name || initial?.name || who}` : individual ? 'Client (applicant)' : 'Applicant'}>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    {individual && !recordId && <Text size="sm" c="dimmed">For an Individual the client is the applicant: the name and mobile are taken from the client.</Text>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <TextInput label={individual ? 'Client name' : 'Applicant name'} required value={f.name} onChange={e => set('name', e.currentTarget.value)}/>
      <TextInput label="Email ID" type="email" value={f.email} onChange={e => set('email', e.currentTarget.value)}/>
      <TextInput label="Contact no." required inputMode="numeric" value={f.contact_number} onChange={e => set('contact_number', e.currentTarget.value)}/>
      <TextInput label={individual ? 'Client GST no.' : 'Applicant GST no.'} value={f.gst_number} onChange={e => set('gst_number', e.currentTarget.value.toUpperCase())}/>
      <TextInput label="No. of cases" required inputMode="numeric" value={f.property_count} onChange={e => set('property_count', e.currentTarget.value)}/>
    </SimpleGrid>
    <Radio.Group label="Paid by" required value={f.payer} onChange={v => set('payer', v)}>
      <Group mt={4}>{codes(L.payers).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <Radio.Group label="Payment by mode" required value={f.fee_basis} onChange={v => set('fee_basis', v)}>
      <Group mt={4}>{codes(L.fee_bases).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <SimpleGrid cols={{base: 1, sm: 3}}>
      {f.payer === '1' && <><ReadOnly label="Organisation" value={[lead.office_name, lead.office_detail?.branch].filter(Boolean).join(', ')}/>
        <ReadOnly label="Client mobile no." value={lead.contact?.phone}/></>}
      <TextInput label="Payment responsible name" required value={f.payment_reference_name} onChange={e => set('payment_reference_name', e.currentTarget.value)}/>
      <TextInput label="Payment responsible no." required inputMode="numeric" value={f.payment_reference_number} onChange={e => set('payment_reference_number', e.currentTarget.value)}/>
      <TextInput label="Pay by date" required type="date" value={f.pay_by_date} onChange={e => set('pay_by_date', e.currentTarget.value)}/>
      {f.fee_basis === '2' && <TextInput label="Work order amount" required inputMode="decimal" value={f.agreed_fee} onChange={e => set('agreed_fee', e.currentTarget.value)}/>}
    </SimpleGrid>
    <Radio.Group label={`Payment by mode (${who})`} required value={f.customer_payment_method} onChange={v => set('customer_payment_method', v)}>
      <Group mt={4}>{codes(L.payment_methods).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <Group><Button type="submit">{recordId ? 'Save changes' : `Save ${who}`}</Button>
      {saved && <Text size="sm" c="green.8" role="status">Saved.</Text>}
      {recordId && !initial && <Button variant="light" onClick={() => { setF(blank); setRecordId(null); setSaved(false); }}>Add another applicant</Button>}
      {onCancel && <Button variant="subtle" onClick={onCancel}>{saved ? 'Close' : 'Cancel'}</Button>}</Group>
  </Section></form>;
}

/** design/add_case.jsp: each choice narrows the next. The contact person defaults to the
 * applicant, and the place to the organisation's, as most properties are near it. The
 * service and sub type are chosen here, from the whole catalog, since the lead no longer
 * requests services (client review 2026-11-25); a bank's own form is pre-chosen for that
 * bank's leads and another bank's is not offered. */
export function CaseForm({lead, catalog, onSave, onUpdate, initial = null, onCancel}) {
  const lookups = useLookups();
  const L = lookups.data;
  const placeDefaults = useMemo(() => {
    if (!L) return {};
    const state = L.states.find(s => s.name.trim().toLowerCase() === (lead.office_detail?.state || '').trim().toLowerCase());
    const district = state && L.districts.find(d => String(d.state_id) === String(state.id) && d.name.trim().toLowerCase() === (lead.office_detail?.district || '').trim().toLowerCase());
    const block = district && L.blocks.find(b => String(b.id) === String(lead.office_detail?.block_id) && String(b.district_id) === String(district.id));
    return {state: state ? String(state.id) : null, district: district ? String(district.id) : null, block: block ? String(block.id) : null};
  }, [L, lead.office_detail]);
  const bank = ifscBank(lead.office_detail?.ifsc);
  const formsOf = service => formsFor((catalog.subtypes || []).filter(x => String(x.service_id) === String(service)), bank);
  const blank = () => ({borrower: null, service: null, subtype: null, report_usages: [], scrutiny_documents: [],
                        expected_report_date: '', asset_amount: '', remarks: '', contact_person_name: '', contact_number: '', asset_address: '',
                        state: placeDefaults.state || null, district: placeDefaults.district || null, block: placeDefaults.block || null, asset_pin_code: ''});
  const fromRecord = c => {
    if (!c || !L) return null;
    const byCode = (rows, codes) => String(codes || '').split(',').map(x => x.trim()).filter(Boolean)
      .map(code => rows.find(r => String(r.code) === code)).filter(Boolean).map(r => String(r.id));
    const state = L.states.find(x => x.name.trim().toLowerCase() === (c.asset_state || '').trim().toLowerCase());
    const district = state && L.districts.find(d => String(d.state_id) === String(state.id) && d.name.trim().toLowerCase() === (c.asset_district || '').trim().toLowerCase());
    const block = L.blocks.find(b => String(b.code) === String(c.asset_block_code));
    return {borrower: String(c.borrower_id), service: c.service_id ? String(c.service_id) : null, subtype: c.subtype_id ? String(c.subtype_id) : null, report_usages: byCode(L.report_usages, c.usage_of_report_code),
            scrutiny_documents: byCode(L.scrutiny_documents, c.scrutiny_document_code), expected_report_date: c.expected_report_date || '',
            asset_amount: c.asset_amount != null ? String(Number(c.asset_amount)) : '', remarks: c.remarks || '', contact_person_name: c.contact_person_name || '',
            contact_number: c.contact_number || '', asset_address: c.asset_address || '', state: state ? String(state.id) : null,
            district: district ? String(district.id) : null, block: block ? String(block.id) : null, asset_pin_code: c.asset_pin_code || ''};
  };
  const [f, setF] = useState(() => fromRecord(initial) || blank());
  useEffect(() => setF(fromRecord(initial) || blank()), [placeDefaults.state, L]);   // eslint-disable-line react-hooks/exhaustive-deps       // eslint-disable-line react-hooks/exhaustive-deps
  const [error, setError] = useState('');
  const [recordId, setRecordId] = useState(initial?.id || null);   // once saved, edits that same case
  const [saved, setSaved] = useState(false);
  const set = (k, v) => { setSaved(false); setF(x => {
    const next = {...x, [k]: v};
    if (k === 'borrower') {                                  // the contact person defaults to the applicant
      const b = lead.borrowers.find(b => String(b.id) === v);
      if (b && !x.contact_person_name) Object.assign(next, {contact_person_name: b.name, contact_number: b.contact_number || ''});
    }
    if (k === 'service') { const own = ownForm(formsOf(v), bank); Object.assign(next, {subtype: own ? String(own.id) : null, report_usages: [], scrutiny_documents: []}); }
    if (k === 'subtype') Object.assign(next, {report_usages: [], scrutiny_documents: []});
    if (k === 'report_usages') next.scrutiny_documents = x.scrutiny_documents.filter(id => documentsFor(v).some(d => String(d.id) === id));
    if (k === 'state') Object.assign(next, {district: null, block: null});
    if (k === 'district') next.block = null;
    return next;
  }); };
  if (!L) return null;
  const subtypes = f.service ? formsOf(f.service) : [];
  const usages = L.report_usages.filter(u => f.service && String(u.subtype_id) === String(f.subtype));
  function documentsFor(chosen) { return L.scrutiny_documents.filter(d => chosen.includes(String(d.report_usage_id))); }
  async function submit(e) {
    e.preventDefault(); setError('');
    const body = {...f};
    try {
      if (recordId) await onUpdate(recordId, body);
      else setRecordId((await onSave(body))?.id || null);
      setSaved(true);
    } catch (err) { setError(err.message); }
  }
  return <form onSubmit={submit}><Section title={recordId ? 'Edit case' : 'Cases detail'}>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <Select label="Applicant name" required data={options(lead.borrowers)} value={f.borrower} onChange={v => set('borrower', v)} placeholder="Select…"/>
      <Select label="Service type" required searchable data={options(catalog.services)} value={f.service} onChange={v => set('service', v)} placeholder="Select…"/>
      <Select label="Service sub type" required={subtypes.length > 0} searchable data={options(subtypes)} value={f.subtype} onChange={v => set('subtype', v)}
              disabled={!f.service || !subtypes.length} placeholder={!f.service ? 'Choose a service first' : subtypes.length ? 'Select…' : 'No sub types'}/>
      <TextInput label="Expected date of report" required type="date" value={f.expected_report_date} onChange={e => set('expected_report_date', e.currentTarget.value)}/>
    </SimpleGrid>
    <MultiSelect label="Usage of report" required searchable data={options(usages)} value={f.report_usages} onChange={v => set('report_usages', v)}
                 disabled={!f.subtype} placeholder={f.subtype ? 'Select one or more' : 'Choose the service sub type first'}/>
    <MultiSelect label="Scrutiny documents" required searchable data={options(documentsFor(f.report_usages))} value={f.scrutiny_documents}
                 onChange={v => set('scrutiny_documents', v)} disabled={!f.report_usages.length} placeholder={f.report_usages.length ? 'Select one or more' : 'Choose the usage of report first'}/>
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <TextInput label="Output amount" required inputMode="decimal" value={f.asset_amount} onChange={e => set('asset_amount', e.currentTarget.value)}/>
      <TextInput label="Contact person name" value={f.contact_person_name} onChange={e => set('contact_person_name', e.currentTarget.value)}/>
      <TextInput label="Contact person no." inputMode="numeric" value={f.contact_number} onChange={e => set('contact_number', e.currentTarget.value)}/>
    </SimpleGrid>
    <TextInput label="Remark" value={f.remarks} onChange={e => set('remarks', e.currentTarget.value)}/>
    <Textarea label="Property address" required value={f.asset_address} onChange={e => set('asset_address', e.currentTarget.value)} autosize minRows={2}/>
    <SimpleGrid cols={{base: 2, sm: 4}}>
      <Select label="State" required searchable data={options(L.states)} value={f.state} onChange={v => set('state', v)} placeholder="Select…"/>
      <Select label="District" required searchable data={options(L.districts.filter(d => String(d.state_id) === String(f.state)))} value={f.district}
              onChange={v => set('district', v)} disabled={!f.state} placeholder={f.state ? 'Select…' : 'Choose a state first'}/>
      <Select label="City" required searchable data={options(L.blocks.filter(b => String(b.district_id) === String(f.district)))} value={f.block}
              onChange={v => set('block', v)} disabled={!f.district} placeholder={f.district ? 'Select…' : 'Choose a district first'}/>
      <TextInput label="PIN (optional)" inputMode="numeric" maxLength={6} value={f.asset_pin_code} onChange={e => set('asset_pin_code', e.currentTarget.value)}/>
    </SimpleGrid>
    <Group><Button type="submit">{recordId ? 'Save changes' : 'Save case'}</Button>
      {saved && <Text size="sm" c="green.8" role="status">Saved.</Text>}
      {recordId && !initial && <Button variant="light" onClick={() => { setF(blank()); setRecordId(null); setSaved(false); }}>Add another case</Button>}
      {onCancel && <Button variant="subtle" onClick={onCancel}>{saved ? 'Close' : 'Cancel'}</Button>}</Group>
  </Section></form>;
}
