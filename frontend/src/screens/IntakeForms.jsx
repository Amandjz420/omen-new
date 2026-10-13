import {Alert, Anchor, Button, Group, MultiSelect, Paper, Radio, Select, SimpleGrid, Stack, Table, Text, TextInput, Textarea, Title} from '@mantine/core';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useEffect, useMemo, useState} from 'react';
import {Link, useNavigate} from 'react-router';
import {PageHeader} from '../components/PageHeader.jsx';
import {ErrorState, LoadingState} from '../components/States.jsx';
import {api, post} from '../lib/api.js';
import {uuid} from '../lib/uuid.js';

// The legacy intake forms (design/add_lead, add_feedback, add_client, add_case), field
// for field and in the same order, with everything the legacy forms filled in for the
// person, and more where the data allows.

export const useLookups = () => useQuery({queryKey: ['intake', 'lookups'], queryFn: () => api('intake/lookups/'), staleTime: 600_000});
export const useCatalog = () => useQuery({queryKey: ['intake', 'catalog'], queryFn: () => api('intake/catalog/'), staleTime: 600_000});
const options = (rows = [], label = 'name') => rows.map(r => ({value: String(r.id ?? r.code), label: String(r[label] ?? r.label ?? '').trim()}));
const codes = (rows = []) => rows.map(r => ({value: String(r.code), label: r.label}));
const digitsOf = v => String(v || '').replace(/\D/g, '').slice(-10);
const today = () => new Date().toISOString().slice(0, 10);

function ReadOnly({label, value}) {
  return <TextInput label={label} value={value || '—'} readOnly variant="filled"/>;
}

function Section({title, children}) {
  return <Paper withBorder p="md"><Title order={3} mb="sm">{title}</Title><Stack gap="sm">{children}</Stack></Paper>;
}

/** design/add_lead.jsp: the lead giver found by mobile number, else registered; the
 * requested services with their cases; who received the lead and who it is assigned to. */
export function NewLeadForm() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const lookups = useLookups(), catalog = useCatalog();
  const [requestId] = useState(uuid);
  const [mode, setMode] = useState(null);
  const [mobile, setMobile] = useState('');
  const [alternate, setAlternate] = useState('');
  const [chosen, setChosen] = useState(null);
  const [giver, setGiver] = useState({client_type: null, office: null, name: '', division: null, subdivision: null, designation: null});
  const [ifsc, setIfsc] = useState('');
  const [ifscResult, setIfscResult] = useState(null);
  const [rows, setRows] = useState([{service: null, subtype: null, case_count: '1'}]);
  const [parties, setParties] = useState('');
  const [receivedBy, setReceivedBy] = useState(null);
  const [assigned, setAssigned] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const digits = digitsOf(mobile);
  const found = useQuery({queryKey: ['intake', 'orderer', digits], queryFn: () => api(`intake/lookups/orderer/?mobile=${digits}`),
                          enabled: digits.length === 10, retry: false});
  const matches = digits.length === 10 ? found.data?.matches || [] : [];
  useEffect(() => { setChosen(matches.length ? String(matches[0].id) : null); }, [found.data, digits]);   // eslint-disable-line react-hooks/exhaustive-deps
  const known = matches.find(m => String(m.id) === chosen);
  const isNew = digits.length === 10 && found.isSuccess && !known;
  const offices = useQuery({queryKey: ['intake', 'offices', giver.client_type], enabled: isNew && !!giver.client_type,
                            queryFn: () => api(`intake/lookups/offices/?client_type=${giver.client_type}`)});
  const office = (offices.data?.results || []).find(o => String(o.id) === giver.office) || ifscResult?.office || null;
  const setG = (key, value) => setGiver(g => ({...g, [key]: value, ...(key === 'client_type' ? {office: null} : {}), ...(key === 'division' ? {subdivision: null} : {})}));

  async function findIfsc() {
    setError('');
    try {
      const r = await api(`intake/lookups/ifsc/?code=${encodeURIComponent(ifsc.trim())}`);
      const first = r.offices[0];
      setIfscResult({office: first || null, directory: first ? null : r.directory});
      if (first) setGiver(g => ({...g, client_type: first.client_type_id ? String(first.client_type_id) : g.client_type, office: String(first.id)}));
      if (!first && !r.directory) setError('No client or bank branch has this IFSC.');
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

  const total = rows.reduce((n, r) => n + (Number(r.case_count) || 0), 0);
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true);
    const body = {request_id: requestId, enquiry_mode: Number(mode), received_by: receivedBy, assigned_employee: assigned,
      services: rows.filter(r => r.service).map(r => ({service: r.service, subtype: r.subtype || null, case_count: Number(r.case_count)})),
      ...(alternate ? {alternate_phone: alternate} : {}), ...(parties ? {party_count: Number(parties)} : {}),
      ...(known ? {contact: known.id} : {new_contact: {name: giver.name, phone: digits, office: office?.id, designation: giver.designation,
                                                       division: giver.division, subdivision: giver.subdivision}})};
    try {
      const lead = await post('intake/leads/', body);
      client.invalidateQueries({queryKey: ['leads']}); client.invalidateQueries({queryKey: ['home']});
      navigate(`/leads/${lead.id}`);
    } catch (e) { setError(e.message); setBusy(false); }
  }

  useEffect(() => { const me = lookups.data?.me?.employee_id; if (me && !receivedBy) setReceivedBy(String(me)); }, [lookups.data]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (lookups.isError || catalog.isError) return <ErrorState error={lookups.error || catalog.error}/>;
  if (!lookups.data || !catalog.data) return <LoadingState label="Opening the lead form"/>;
  const L = lookups.data, C = catalog.data;
  const subdivisions = L.subdivisions.filter(s => String(s.division_id) === String(giver.division));

  return <form onSubmit={submit}><Stack gap="md" maw={900}>
    <PageHeader title="New lead" description="Enter the lead giver's mobile number: a known lead giver's details fill in."/>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}

    <Section title="Lead giver information">
      <SimpleGrid cols={{base: 1, sm: 3}}>
        <Select label="Mode" required data={codes(L.modes)} value={mode} onChange={setMode} placeholder="Select…"/>
        <TextInput label="Lead giver mobile no." required value={mobile} onChange={e => setMobile(e.currentTarget.value)}
                   inputMode="numeric" maxLength={14} placeholder="10 digits" description={found.isFetching ? 'Looking up…' : undefined}/>
        <TextInput label="Alternate contact number" value={alternate} onChange={e => setAlternate(e.currentTarget.value)} inputMode="numeric"
                   placeholder="Without the 0 prefix"/>
      </SimpleGrid>

      {matches.length > 1 && <Radio.Group label="This number belongs to more than one lead giver" value={chosen} onChange={setChosen}>
        <Stack gap={4} mt={4}>{matches.map(m => <Radio key={m.id} value={String(m.id)}
          label={`${m.name}, ${m.office?.name || ''} ${m.office?.branch || ''} (${m.leads} leads)`}/>)}<Radio value="" label="Someone else: register a new lead giver"/></Stack>
      </Radio.Group>}

      {known && <SimpleGrid cols={{base: 1, sm: 3}} aria-label="The lead giver's details">
        <ReadOnly label="Lead giver name" value={known.name}/><ReadOnly label="Designation" value={known.designation}/>
        <ReadOnly label="City" value={known.office?.city}/><ReadOnly label="Client type" value={known.office?.client_type}/>
        <ReadOnly label="Client name" value={known.office?.name}/><ReadOnly label="Client branch" value={known.office?.branch}/>
        <ReadOnly label="Division" value={[known.division, known.subdivision].filter(Boolean).join(' / ')}/>
        <ReadOnly label="Address" value={known.office?.address}/><ReadOnly label="GST No." value={known.office?.gstin}/>
      </SimpleGrid>}

      {isNew && <>
        <Text size="sm" c="dimmed">No lead giver has this number. Register them with the lead.</Text>
        <SimpleGrid cols={{base: 1, sm: 3}}>
          <Select label="Client type" required data={options(L.client_types)} value={giver.client_type} onChange={v => setG('client_type', v)} placeholder="Select…"/>
          <Select label="Client name" required searchable data={(offices.data?.results || []).map(o => ({value: String(o.id), label: `${o.name}${o.branch ? ', ' + o.branch : ''}`}))}
                  value={giver.office} onChange={v => { setG('office', v); setIfscResult(null); }} disabled={!giver.client_type}
                  placeholder={giver.client_type ? 'Select…' : 'Choose a client type first'}/>
          <Group align="flex-end" gap="xs" wrap="nowrap">
            <TextInput label="IFSC code" value={ifsc} onChange={e => setIfsc(e.currentTarget.value.toUpperCase())} maxLength={11} style={{flex: 1}}/>
            <Button variant="light" onClick={findIfsc} disabled={ifsc.trim().length !== 11}>Find</Button>
          </Group>
        </SimpleGrid>
        {ifscResult?.directory && <Alert variant="light" color="blue" title="Not yet a client: found in the bank directory">
          <Text size="sm">{ifscResult.directory.bank}, {ifscResult.directory.branch} — {ifscResult.directory.address}, {ifscResult.directory.district}, {ifscResult.directory.state}</Text>
          <Button mt="xs" size="xs" onClick={addFromDirectory} disabled={!giver.client_type}>{giver.client_type ? 'Add this branch as a client' : 'Choose its client type first'}</Button>
        </Alert>}
        <SimpleGrid cols={{base: 1, sm: 3}}>
          <TextInput label="Lead giver name" required value={giver.name} onChange={e => setG('name', e.currentTarget.value)}/>
          <Select label="Division" required data={options(L.divisions)} value={giver.division} onChange={v => setG('division', v)} placeholder="Select…"/>
          <Select label="Sub division" required data={options(subdivisions)} value={giver.subdivision} onChange={v => setG('subdivision', v)}
                  disabled={!giver.division} placeholder={giver.division ? 'Select…' : 'Choose a division first'}/>
          <Select label="Lead giver designation" required data={options(L.designations)} value={giver.designation} onChange={v => setG('designation', v)} placeholder="Select…"/>
          <ReadOnly label="Client branch" value={office?.branch}/><ReadOnly label="Client address" value={office?.address}/>
          <ReadOnly label="Client state" value={office?.state}/><ReadOnly label="Client district" value={office?.district}/>
          <ReadOnly label="Client city" value={office?.city}/>
        </SimpleGrid>
        <Anchor component={Link} to="/leads/clients" size="sm">Add or edit a client office</Anchor>
      </>}
    </Section>

    <Section title="Lead information">
      <Table.ScrollContainer minWidth={520}><Table>
        <Table.Thead><Table.Tr><Table.Th>Type of service</Table.Th><Table.Th>Type of sub service</Table.Th><Table.Th>No. of case / property</Table.Th><Table.Th/></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((r, i) => {
          const subtypes = C.subtypes.filter(s => String(s.service_id) === String(r.service));
          const set = patch => setRows(rs => rs.map((x, n) => (n === i ? {...x, ...patch} : x)));
          return <Table.Tr key={i}>
            <Table.Td><Select aria-label={`Service ${i + 1}`} required={i === 0} data={options(C.services)} value={r.service} onChange={v => set({service: v, subtype: null})} placeholder="Select…"/></Table.Td>
            <Table.Td><Select aria-label={`Sub service ${i + 1}`} data={options(subtypes)} value={r.subtype} onChange={v => set({subtype: v})} disabled={!r.service || !subtypes.length}
                              placeholder={!r.service ? 'Choose a service first' : subtypes.length ? 'Select…' : 'No sub services'}/></Table.Td>
            <Table.Td><TextInput aria-label={`Cases ${i + 1}`} required inputMode="numeric" value={r.case_count} onChange={e => set({case_count: e.currentTarget.value})}/></Table.Td>
            <Table.Td>{rows.length > 1 && <Button variant="subtle" color="red" size="xs" onClick={() => setRows(rs => rs.filter((_, n) => n !== i))}>Remove</Button>}</Table.Td>
          </Table.Tr>;
        })}</Table.Tbody>
      </Table></Table.ScrollContainer>
      <Group justify="space-between">
        <Button variant="light" size="xs" onClick={() => setRows(rs => [...rs, {service: null, subtype: null, case_count: '1'}])}>Add a service</Button>
        <Text size="sm">No. of cases / properties: <strong className="num">{total}</strong></Text>
      </Group>
      <TextInput label="No. of clients" inputMode="numeric" value={parties} onChange={e => setParties(e.currentTarget.value)} maw={220}/>
    </Section>

    <Section title="Other details (for internal use only)">
      <SimpleGrid cols={{base: 1, sm: 2}}>
        <Select label="Lead received by" required searchable data={options(C.employees)} value={receivedBy} onChange={setReceivedBy} placeholder="Select…"/>
        <Select label="Lead assigned to" required searchable data={options(C.employees)} value={assigned} onChange={setAssigned} placeholder="Select…"/>
      </SimpleGrid>
    </Section>
    <Group><Button type="submit" loading={busy} disabled={digits.length !== 10 || !mode}>Save the lead</Button></Group>
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

/** design/add_client.jsp: the client's customer and the fee agreement. Paid by the client:
 * the payer is the lead's client and lead giver, and payment responsibility defaults to
 * the lead giver. Fixed fee: the work order amount. */
export function BorrowerForm({lead, onSave, onUpdate, initial = null, onCancel}) {
  const lookups = useLookups();
  const fromRecord = b => b && ({name: b.name || '', contact_number: b.contact_number || '', email: b.email || '', gst_number: b.gst_number || '',
    property_count: String(b.property_count ?? 1), payer: String(b.payer ?? 1), fee_basis: String(b.fee_basis ?? 1),
    agreed_fee: b.agreed_fee != null ? String(Number(b.agreed_fee)) : '', payment_reference_name: b.payment_reference_name || '',
    payment_reference_number: b.payment_reference_number || '', pay_by_date: b.pay_by_date || '', customer_payment_method: String(b.customer_payment_method ?? 1)});
  const blank = {name: '', contact_number: '', email: '', gst_number: '', property_count: '1', payer: '1', fee_basis: '1', agreed_fee: '',
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
  return <form onSubmit={submit}><Section title={recordId ? `Edit ${f.name || initial?.name || "client's customer"}` : "Client's customer"}>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <TextInput label="Name of client's customer" required value={f.name} onChange={e => set('name', e.currentTarget.value)}/>
      <TextInput label="Email ID" type="email" value={f.email} onChange={e => set('email', e.currentTarget.value)}/>
      <TextInput label="Contact no." required inputMode="numeric" value={f.contact_number} onChange={e => set('contact_number', e.currentTarget.value)}/>
      <TextInput label="CC GST no." value={f.gst_number} onChange={e => set('gst_number', e.currentTarget.value.toUpperCase())}/>
      <TextInput label="No. of cases" required inputMode="numeric" value={f.property_count} onChange={e => set('property_count', e.currentTarget.value)}/>
    </SimpleGrid>
    <Radio.Group label="Paid by" required value={f.payer} onChange={v => set('payer', v)}>
      <Group mt={4}>{codes(L.payers).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <Radio.Group label="Payment by mode" required value={f.fee_basis} onChange={v => set('fee_basis', v)}>
      <Group mt={4}>{codes(L.fee_bases).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <SimpleGrid cols={{base: 1, sm: 3}}>
      {f.payer === '1' && <><ReadOnly label="Client name" value={[lead.office_name, lead.office_detail?.branch].filter(Boolean).join(', ')}/>
        <ReadOnly label="Contact number" value={lead.contact?.phone}/></>}
      <TextInput label="Client payment responsible name" required value={f.payment_reference_name} onChange={e => set('payment_reference_name', e.currentTarget.value)}/>
      <TextInput label="Client payment responsible no." required inputMode="numeric" value={f.payment_reference_number} onChange={e => set('payment_reference_number', e.currentTarget.value)}/>
      <TextInput label="Pay by date" required type="date" value={f.pay_by_date} onChange={e => set('pay_by_date', e.currentTarget.value)}/>
      {f.fee_basis === '2' && <TextInput label="Work order amount" required inputMode="decimal" value={f.agreed_fee} onChange={e => set('agreed_fee', e.currentTarget.value)}/>}
    </SimpleGrid>
    <Radio.Group label="Payment by mode (client's customer)" required value={f.customer_payment_method} onChange={v => set('customer_payment_method', v)}>
      <Group mt={4}>{codes(L.payment_methods).map(o => <Radio key={o.value} value={o.value} label={o.label}/>)}</Group></Radio.Group>
    <Group><Button type="submit">{recordId ? 'Save changes' : "Save client's customer"}</Button>
      {saved && <Text size="sm" c="green.8" role="status">Saved.</Text>}
      {recordId && !initial && <Button variant="light" onClick={() => { setF(blank); setRecordId(null); setSaved(false); }}>Add another customer</Button>}
      {onCancel && <Button variant="subtle" onClick={onCancel}>{saved ? 'Close' : 'Cancel'}</Button>}</Group>
  </Section></form>;
}

/** design/add_case.jsp: each choice narrows the next. The contact person defaults to the
 * customer, and the place to the client office's, as most properties are near it. */
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
  const blank = () => ({borrower: null, requested: lead.services.length === 1 ? String(lead.services[0].id) : null, report_usages: [], scrutiny_documents: [],
                        expected_report_date: '', asset_amount: '', remarks: '', contact_person_name: '', contact_number: '', asset_address: '',
                        state: placeDefaults.state || null, district: placeDefaults.district || null, block: placeDefaults.block || null, asset_pin_code: ''});
  const fromRecord = c => {
    if (!c || !L) return null;
    const byCode = (rows, codes) => String(codes || '').split(',').map(x => x.trim()).filter(Boolean)
      .map(code => rows.find(r => String(r.code) === code)).filter(Boolean).map(r => String(r.id));
    const state = L.states.find(x => x.name.trim().toLowerCase() === (c.asset_state || '').trim().toLowerCase());
    const district = state && L.districts.find(d => String(d.state_id) === String(state.id) && d.name.trim().toLowerCase() === (c.asset_district || '').trim().toLowerCase());
    const block = L.blocks.find(b => String(b.code) === String(c.asset_block_code));
    const requested = lead.services.find(s => String(s.service_id) === String(c.service_id) && String(s.subtype_id ?? '') === String(c.subtype_id ?? ''));
    return {borrower: String(c.borrower_id), requested: requested ? String(requested.id) : null, report_usages: byCode(L.report_usages, c.usage_of_report_code),
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
    if (k === 'borrower') {                                  // the contact person defaults to the customer
      const b = lead.borrowers.find(b => String(b.id) === v);
      if (b && !x.contact_person_name) Object.assign(next, {contact_person_name: b.name, contact_number: b.contact_number || ''});
    }
    if (k === 'requested') Object.assign(next, {report_usages: [], scrutiny_documents: []});
    if (k === 'report_usages') next.scrutiny_documents = x.scrutiny_documents.filter(id => documentsFor(v).some(d => String(d.id) === id));
    if (k === 'state') Object.assign(next, {district: null, block: null});
    if (k === 'district') next.block = null;
    return next;
  }); };
  if (!L) return null;
  const service = lead.services.find(s => String(s.id) === f.requested);
  const usages = L.report_usages.filter(u => service && String(u.subtype_id) === String(service.subtype_id));
  function documentsFor(chosen) { return L.scrutiny_documents.filter(d => chosen.includes(String(d.report_usage_id))); }
  const named = (rows, id) => rows.find(x => String(x.id) === String(id))?.name || '';
  async function submit(e) {
    e.preventDefault(); setError('');
    const {requested, ...rest} = f;
    const body = {...rest, service: service?.service_id, subtype: service?.subtype_id};
    try {
      if (recordId) await onUpdate(recordId, body);
      else setRecordId((await onSave(body))?.id || null);
      setSaved(true);
    } catch (err) { setError(err.message); }
  }
  return <form onSubmit={submit}><Section title={recordId ? 'Edit case' : 'Cases detail'}>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <Select label="Client's customer name" required data={options(lead.borrowers)} value={f.borrower} onChange={v => set('borrower', v)} placeholder="Select…"/>
      <Select label="Service type and sub type" required value={f.requested} onChange={v => set('requested', v)} placeholder="Select…"
              data={lead.services.map(s => ({value: String(s.id), label: [named(catalog.services, s.service_id), named(catalog.subtypes, s.subtype_id)].filter(Boolean).join(' · ')}))}/>
      <TextInput label="Expected date of report" required type="date" value={f.expected_report_date} onChange={e => set('expected_report_date', e.currentTarget.value)}/>
    </SimpleGrid>
    <MultiSelect label="Usage of report" required searchable data={options(usages)} value={f.report_usages} onChange={v => set('report_usages', v)}
                 disabled={!service} placeholder={service ? 'Select one or more' : 'Choose the service first'}/>
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
      <TextInput label="PIN" required inputMode="numeric" maxLength={6} value={f.asset_pin_code} onChange={e => set('asset_pin_code', e.currentTarget.value)}/>
    </SimpleGrid>
    <Group><Button type="submit">{recordId ? 'Save changes' : 'Save case'}</Button>
      {saved && <Text size="sm" c="green.8" role="status">Saved.</Text>}
      {recordId && !initial && <Button variant="light" onClick={() => { setF(blank()); setRecordId(null); setSaved(false); }}>Add another case</Button>}
      {onCancel && <Button variant="subtle" onClick={onCancel}>{saved ? 'Close' : 'Cancel'}</Button>}</Group>
  </Section></form>;
}
