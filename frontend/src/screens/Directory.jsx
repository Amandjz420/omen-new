import {Accordion, Alert, Anchor, Badge, Button, Group, Pagination, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput, Textarea, Title} from '@mantine/core';
import {useDebouncedValue} from '@mantine/hooks';
import {notifications} from '@mantine/notifications';
import {keepPreviousData, useQuery, useQueryClient} from '@tanstack/react-query';
import {Fragment, useEffect, useState} from 'react';
import {useSearchParams} from 'react-router';
import {PageHeader} from '../components/PageHeader.jsx';
import {EmptyState, ErrorState, LoadingState} from '../components/States.jsx';
import {api, post} from '../lib/api.js';
import {count, date} from '../lib/format.js';
import {NewClientPanel, useLookups} from './IntakeForms.jsx';

// Client review 2026-11-25: about 1,400 organisations and 2,000 clients did not fit the
// old screen's 30-item dropdown. They are shown as a tree: bank -> branch -> clients,
// with Corporate and Individual organisations grouped by type. Whoever gave work most
// recently comes first. Search skips the tree.

const FILTERS = ['q', 'type', 'bank', 'state', 'district', 'active'];
const ACTIVE = [{value: '', label: 'Any time'}, {value: '3', label: 'Last 3 months'}, {value: '6', label: 'Last 6 months'}, {value: '12', label: 'Last 12 months'}];
const SORTS = [{value: 'last_lead', label: 'Most recent lead'}, {value: 'name', label: 'Name'}, {value: 'leads', label: 'Most leads'},
               {value: 'clients', label: 'Most clients'}, {value: 'district', label: 'District'}];
const FI = 'Financial Institution';
const query = (filters, extra = {}) => new URLSearchParams(Object.entries({...filters, ...extra}).filter(([, v]) => v)).toString();
const last = d => (d ? date(d) : 'No leads');

export function Directory() {
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(FILTERS.map(k => [k, params.get(k) ?? '']));
  const set = next => setParams(p => {Object.entries(next).forEach(([k, v]) => v ? p.set(k, v) : p.delete(k)); return p;}, {replace: true});
  const [typed, setTyped] = useState(filters.q);
  const [q] = useDebouncedValue(typed.trim(), 300);
  useEffect(() => { if (q !== filters.q && (q.length >= 2 || !q)) set({q}); }, [q]);   // eslint-disable-line react-hooks/exhaustive-deps
  const {q: _q, ...narrow} = filters;
  const groups = useQuery({queryKey: ['directory', 'groups', narrow], queryFn: () => api(`directory/groups/?${query(narrow)}`), placeholderData: keepPreviousData});
  const [adding, setAdding] = useState(false);
  const f = groups.data?.filters;
  const districts = f?.states.find(s => s.name === filters.state)?.districts || [];
  return <Stack>
    <PageHeader title="Organisations & clients"
                description="Banks and their branches, corporates and individuals, and the clients at each. Whoever gave work most recently comes first."
                actions={<Button onClick={() => setAdding(a => !a)}>New organisation</Button>}/>
    {adding && <NewOrganisation onDone={() => setAdding(false)}/>}
    <Paper withBorder p="sm">
      <Stack gap="xs">
        <TextInput label="Search" placeholder="Branch, IFSC, place, client name or mobile" value={typed} onChange={e => setTyped(e.currentTarget.value)}/>
        <SimpleGrid cols={{base: 2, sm: 5}}>
          <Select label="Type" placeholder="All types" clearable data={f?.types || []} value={filters.type || null} onChange={v => set({type: v || ''})}/>
          <Select label="Bank" placeholder="All banks" clearable searchable data={f?.banks || []} value={filters.bank || null} onChange={v => set({bank: v || ''})}/>
          <Select label="State" placeholder="All states" clearable searchable data={(f?.states || []).map(s => s.name)} value={filters.state || null}
                  onChange={v => set({state: v || '', district: ''})}/>
          <Select label="District" placeholder={filters.state ? 'All districts' : 'Choose a state first'} clearable searchable data={districts}
                  value={filters.district || null} onChange={v => set({district: v || ''})} disabled={!filters.state}/>
          <Select label="Active" data={ACTIVE} value={filters.active} onChange={v => set({active: v || ''})} allowDeselect={false}/>
        </SimpleGrid>
      </Stack>
    </Paper>
    {filters.q ? <SearchResults filters={filters}/>
      : groups.isError ? <ErrorState error={groups.error} onRetry={groups.refetch}/>
      : !groups.data ? <LoadingState label="Loading organisations"/>
      : groups.data.groups.length === 0 ? <EmptyState title="No organisations match" description="Clear a filter, or widen the active period."/>
      : <>
        <Text size="sm" c="dimmed">{count(groups.data.totals.organisations)} organisations · {count(groups.data.totals.clients)} clients</Text>
        <Groups groups={groups.data.groups} filters={narrow}/>
      </>}
  </Stack>;
}

function Groups({groups, filters}) {
  const [open, setOpen] = useState(groups.length === 1 ? [groups[0].key] : []);
  return <Accordion multiple variant="separated" value={open} onChange={setOpen}>
    {groups.map(g => <Accordion.Item key={g.key} value={g.key}>
      <Accordion.Control aria-label={g.name}>
        <Group justify="space-between" wrap="wrap" gap="xs" pr="sm">
          <Text fw={600}>{g.name}</Text>
          <Group gap="xs">
            <Badge variant="light">{count(g.branches)} {g.kind === 'bank' || g.key === 'none' ? 'branches' : 'organisations'}</Badge>
            <Badge variant="light" color="gray">{count(g.clients)} clients</Badge>
            <Badge variant="light" color="gray">{count(g.leads)} leads</Badge>
            <Text size="xs" c="dimmed">Last lead {last(g.last_lead)}</Text>
          </Group>
        </Group>
      </Accordion.Control>
      <Accordion.Panel>{open.includes(g.key) && <Branches group={g} filters={filters}/>}</Accordion.Panel>
    </Accordion.Item>)}
  </Accordion>;
}

function Branches({group, filters}) {
  const [sort, setSort] = useState('last_lead');
  const [page, setPage] = useState(1);
  const list = useQuery({queryKey: ['directory', 'branches', group.key, filters, sort, page], placeholderData: keepPreviousData,
                         queryFn: () => api(`directory/branches/?${query(filters, {group: group.key, sort, page})}`)});
  if (list.isError) return <ErrorState error={list.error} onRetry={list.refetch}/>;
  if (!list.data) return <LoadingState label={`Loading ${group.name}`}/>;
  return <Stack gap="xs">
    <Group justify="space-between">
      <Text size="sm" c="dimmed">{count(list.data.count)} {group.kind === 'bank' ? 'branches' : 'organisations'}</Text>
      <Select aria-label="Sort by" size="xs" w={190} data={SORTS} value={sort} onChange={v => {setSort(v); setPage(1);}} allowDeselect={false}/>
    </Group>
    <BranchTable rows={list.data.results} bank={group.kind === 'bank'}/>
    {list.data.count > list.data.page_size && <Pagination size="sm" total={Math.ceil(list.data.count / list.data.page_size)} value={page} onChange={setPage}/>}
  </Stack>;
}

function BranchTable({rows, bank, showGroup = false}) {
  const [open, setOpen] = useState(null);
  return <Table.ScrollContainer minWidth={720}><Table highlightOnHover verticalSpacing="xs">
    <Table.Thead><Table.Tr>
      <Table.Th>{bank ? 'Branch' : 'Organisation'}</Table.Th>{showGroup && <Table.Th>Bank / type</Table.Th>}<Table.Th>IFSC</Table.Th>
      <Table.Th>District</Table.Th><Table.Th>Clients</Table.Th><Table.Th>Leads</Table.Th><Table.Th>Last lead</Table.Th><Table.Th/>
    </Table.Tr></Table.Thead>
    <Table.Tbody>{rows.map(r => <Fragment key={r.id}>
      <Table.Tr>
        <Table.Td><Text size="sm" fw={600}>{bank ? r.branch || r.name : r.name}</Text>
          <Text size="xs" c="dimmed">{bank ? (r.branch ? r.name : '') : r.branch}</Text></Table.Td>
        {showGroup && <Table.Td>{r.group_name}</Table.Td>}
        <Table.Td>{r.ifsc || '—'}</Table.Td><Table.Td>{r.district || '—'}</Table.Td>
        <Table.Td className="num">{r.clients}</Table.Td><Table.Td className="num">{r.leads}</Table.Td><Table.Td>{last(r.last_lead)}</Table.Td>
        <Table.Td><Button size="compact-xs" variant={open === r.id ? 'filled' : 'light'} onClick={() => setOpen(open === r.id ? null : r.id)}
                          aria-expanded={open === r.id} aria-label={`Clients at ${[r.name, r.branch].filter(Boolean).join(', ')}`}>
          {open === r.id ? 'Close' : `Clients (${r.clients})`}</Button></Table.Td>
      </Table.Tr>
      {open === r.id && <Table.Tr><Table.Td colSpan={showGroup ? 8 : 7} p={0}><BranchPanel office={r}/></Table.Td></Table.Tr>}
    </Fragment>)}</Table.Tbody>
  </Table></Table.ScrollContainer>;
}

const invalidate = client => client.invalidateQueries({queryKey: ['directory']});

/** A branch opened: its details, its clients, and editing both. */
function BranchPanel({office}) {
  const client = useQueryClient();
  const clients = useQuery({queryKey: ['directory', 'clients', office.id], queryFn: () => api(`directory/clients/?office=${office.id}`)});
  const [editing, setEditing] = useState(null);           // 'office', 'new', or a client
  return <Paper bg="gray.0" p="sm" radius={0} aria-label={`Organisation ${[office.name, office.branch].filter(Boolean).join(', ')}`}>
    <Stack gap="xs">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <Text size="sm">{[office.address, office.district, office.state].filter(Boolean).join(', ') || 'No address recorded'}
          {office.gstin && ` · GST ${office.gstin}`}{office.pan && ` · PAN ${office.pan}`}</Text>
        <Group gap="xs">
          <Button size="compact-sm" variant="light" onClick={() => setEditing(editing === 'office' ? null : 'office')}>Edit organisation</Button>
          <Button size="compact-sm" onClick={() => setEditing(editing === 'new' ? null : 'new')}>Add client</Button>
        </Group>
      </Group>
      {editing === 'office' && <OrganisationForm office={office} onDone={() => {setEditing(null); invalidate(client);}}/>}
      {editing === 'new' && <ClientForm office={office} onDone={() => {setEditing(null); invalidate(client);}}/>}
      {clients.isError ? <ErrorState error={clients.error} onRetry={clients.refetch}/> : !clients.data ? <LoadingState label="Loading clients"/>
        : clients.data.results.length === 0 ? <Text size="sm" c="dimmed">No clients recorded at this organisation yet.</Text>
        : <Table verticalSpacing={4}><Table.Thead><Table.Tr><Table.Th>Client</Table.Th><Table.Th>Designation</Table.Th><Table.Th>Mobile</Table.Th>
            <Table.Th>Leads</Table.Th><Table.Th>Last lead</Table.Th><Table.Th/></Table.Tr></Table.Thead>
          <Table.Tbody>{clients.data.results.map(c => <Fragment key={c.id}>
            <Table.Tr><Table.Td>{c.name}</Table.Td><Table.Td>{c.designation || '—'}</Table.Td>
              <Table.Td>{[c.phone, c.alternate_phone].filter(Boolean).join(' / ') || '—'}</Table.Td>
              <Table.Td className="num">{c.leads}</Table.Td><Table.Td>{last(c.last_lead)}</Table.Td>
              <Table.Td><Anchor component="button" size="sm" onClick={() => setEditing(editing?.id === c.id ? null : c)}>Edit</Anchor></Table.Td></Table.Tr>
            {editing?.id === c.id && <Table.Tr><Table.Td colSpan={6}>
              <ClientForm office={office} initial={c} onDone={() => {setEditing(null); invalidate(client);}}/></Table.Td></Table.Tr>}
          </Fragment>)}</Table.Tbody></Table>}
    </Stack>
  </Paper>;
}

function OrganisationForm({office, onDone}) {
  const [f, setF] = useState({name: office.name || '', branch_name: office.branch || '', address: office.address || '', ifsc: office.ifsc || '',
                              gstin: office.gstin || '', pan: office.pan || ''});
  const [error, setError] = useState('');
  const set = (k, v) => setF(x => ({...x, [k]: v}));
  const fi = !office.type || office.type === FI;
  async function save(e) {
    e.preventDefault(); setError('');
    try {
      await api(`intake/offices/${office.id}/`, {method: 'PATCH', body: JSON.stringify(fi ? f : {...f, ifsc: ''})});
      notifications.show({message: 'Organisation saved'}); onDone();
    } catch (err) { setError(err.message); }
  }
  return <form onSubmit={save}><Paper withBorder p="sm"><Stack gap="xs">
    <Title order={4}>Edit organisation</Title>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 3}}>
      <TextInput label="Organisation name" required value={f.name} onChange={e => set('name', e.currentTarget.value)}/>
      <TextInput label="Branch" value={f.branch_name} onChange={e => set('branch_name', e.currentTarget.value)}/>
      {fi && <TextInput label="IFSC code" maxLength={11} value={f.ifsc} onChange={e => set('ifsc', e.currentTarget.value.toUpperCase())}/>}
      <TextInput label="GST no." maxLength={15} value={f.gstin} onChange={e => set('gstin', e.currentTarget.value.toUpperCase())}/>
      <TextInput label="PAN" maxLength={10} value={f.pan} onChange={e => set('pan', e.currentTarget.value.toUpperCase())}/>
    </SimpleGrid>
    <Textarea label="Address" autosize minRows={2} value={f.address} onChange={e => set('address', e.currentTarget.value)}/>
    <Group><Button type="submit" size="xs">Save organisation</Button><Button size="xs" variant="subtle" onClick={onDone}>Cancel</Button></Group>
  </Stack></Paper></form>;
}

function ClientForm({office, initial = null, onDone}) {
  const lookups = useLookups();
  const [f, setF] = useState({name: initial?.name || '', phone: initial?.phone || '', alternate_phone: initial?.alternate_phone || '',
                              designation: initial?.designation_id ? String(initial.designation_id) : null});
  const [error, setError] = useState('');
  const set = (k, v) => setF(x => ({...x, [k]: v}));
  async function save(e) {
    e.preventDefault(); setError('');
    const body = {...f, office: office.id, designation: f.designation || null};
    try {
      if (initial) await api(`intake/contacts/${initial.id}/`, {method: 'PATCH', body: JSON.stringify(body)});
      else await post('intake/contacts/', body);
      notifications.show({message: initial ? 'Client saved' : 'Client added'}); onDone();
    } catch (err) { setError(err.message); }
  }
  return <form onSubmit={save}><Paper withBorder p="sm"><Stack gap="xs">
    <Title order={4}>{initial ? `Edit ${initial.name}` : 'Add a client'}</Title>
    {error && <Alert color="red" variant="light" role="alert">{error}</Alert>}
    <SimpleGrid cols={{base: 1, sm: 4}}>
      <TextInput label="Client name" required value={f.name} onChange={e => set('name', e.currentTarget.value)}/>
      <TextInput label="Mobile no." inputMode="numeric" value={f.phone} onChange={e => set('phone', e.currentTarget.value)}/>
      <TextInput label="Alternate no." inputMode="numeric" value={f.alternate_phone} onChange={e => set('alternate_phone', e.currentTarget.value)}/>
      <Select label="Designation" searchable clearable data={(lookups.data?.designations || []).map(d => ({value: String(d.id), label: d.name}))}
              value={f.designation} onChange={v => set('designation', v)}/>
    </SimpleGrid>
    <Group><Button type="submit" size="xs">{initial ? 'Save client' : 'Add client'}</Button><Button size="xs" variant="subtle" onClick={onDone}>Cancel</Button></Group>
  </Stack></Paper></form>;
}

function NewOrganisation({onDone}) {
  const lookups = useLookups();
  const client = useQueryClient();
  const [type, setType] = useState(null);
  if (!lookups.data) return <LoadingState label="Opening the form"/>;
  const typeLabel = lookups.data.client_types.find(t => String(t.id) === type)?.name || '';
  return <Paper withBorder p="sm"><Stack gap="xs">
    <Select label="Organisation type" required maw={320} data={lookups.data.client_types.map(t => ({value: String(t.id), label: t.name}))}
            value={type} onChange={setType} placeholder="Select…"/>
    {type ? <NewClientPanel key={type} clientType={type} typeLabel={typeLabel} lookups={lookups.data} onCancel={onDone}
                            onCreated={async () => {notifications.show({message: 'Organisation added'}); await invalidate(client); onDone();}}/>
      : <Button size="xs" variant="subtle" onClick={onDone} w="fit-content">Cancel</Button>}
  </Stack></Paper>;
}

function SearchResults({filters}) {
  const {q, ...narrow} = filters;
  const found = useQuery({queryKey: ['directory', 'search', filters], queryFn: () => api(`directory/search/?${query(narrow, {q})}`), placeholderData: keepPreviousData});
  const [open, setOpen] = useState(null);
  if (found.isError) return <ErrorState error={found.error} onRetry={found.refetch}/>;
  if (!found.data) return <LoadingState label="Searching"/>;
  const {branches, clients, branch_count} = found.data;
  if (!branches.length && !clients.length) return <EmptyState title="Nothing matches" description="Try part of the branch name, the IFSC, or the client's mobile number."/>;
  return <Stack>
    {branches.length > 0 && <section>
      <Title order={3} mb="xs">Organisations{branch_count > branches.length ? ` (first ${branches.length} of ${count(branch_count)})` : ''}</Title>
      <BranchTable rows={branches} bank={false} showGroup/>
    </section>}
    {clients.length > 0 && <section>
      <Title order={3} mb="xs">Clients</Title>
      <Table.ScrollContainer minWidth={640}><Table verticalSpacing="xs">
        <Table.Thead><Table.Tr><Table.Th>Client</Table.Th><Table.Th>Mobile</Table.Th><Table.Th>Organisation</Table.Th><Table.Th>Leads</Table.Th>
          <Table.Th>Last lead</Table.Th><Table.Th/></Table.Tr></Table.Thead>
        <Table.Tbody>{clients.map(c => <Fragment key={c.id}>
          <Table.Tr><Table.Td>{c.name}<Text size="xs" c="dimmed">{c.designation}</Text></Table.Td>
            <Table.Td>{[c.phone, c.alternate_phone].filter(Boolean).join(' / ') || '—'}</Table.Td><Table.Td>{c.office_name}</Table.Td>
            <Table.Td className="num">{c.leads}</Table.Td><Table.Td>{last(c.last_lead)}</Table.Td>
            <Table.Td><Button size="compact-xs" variant="light" onClick={() => setOpen(open === c.id ? null : c.id)}>
              {open === c.id ? 'Close' : 'Open organisation'}</Button></Table.Td></Table.Tr>
          {open === c.id && <Table.Tr><Table.Td colSpan={6} p={0}><OfficeById id={c.office}/></Table.Td></Table.Tr>}
        </Fragment>)}</Table.Tbody>
      </Table></Table.ScrollContainer>
    </section>}
  </Stack>;
}

function OfficeById({id}) {
  const office = useQuery({queryKey: ['directory', 'office', id], queryFn: () => api(`intake/offices/${id}/`)});
  if (office.isError) return <ErrorState error={office.error}/>;
  if (!office.data) return <LoadingState/>;
  const o = office.data;
  return <BranchPanel office={{id, name: o.name, branch: o.branch_name, address: o.address, ifsc: o.ifsc, gstin: o.gstin, pan: o.pan,
                               district: o.district, state: o.state, type: ''}}/>;
}
