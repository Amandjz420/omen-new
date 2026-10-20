import {ResponsiveTable} from '../components/ResponsiveTable.jsx';
import {Anchor, Badge, Button, Group, Pagination, Paper, Select, Stack, Table, Tabs, Text, Textarea, TextInput, Title} from '@mantine/core';
import {useDebouncedValue} from '@mantine/hooks';
import {notifications} from '@mantine/notifications';
import {keepPreviousData, useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {lazy, Suspense, useEffect, useState} from 'react';
import {Link, useParams, useSearchParams} from 'react-router';
import {PageHeader} from '../components/PageHeader.jsx';
import {StageTrack} from '../components/StageTrack.jsx';
import {EmptyState, ErrorState, LoadingState} from '../components/States.jsx';
import {StatusBadge} from '../components/StatusBadge.jsx';
// Loaded when a lead is opened: it brings in the intake screens, which would
// otherwise be bundled into every page load.
const LeadWorkspace = lazy(() => import('../workorders.jsx').then(module => ({default: module.LeadWorkspace})));
import {api, post} from '../lib/api.js';
import {count, date, dateTime} from '../lib/format.js';

const PAGE = 30;
const TABS = ['details', 'customers', 'followups', 'orders'];
const STATUSES = [{value: '', label: 'All statuses'}, {value: '1', label: 'New lead'}, {value: '2', label: 'In process'},
                  {value: '3', label: 'Cancelled'}, {value: '4', label: 'Closed (previous system)'}];
const tone = s => ({'Cancelled': 'refused', 'New lead': 'active', 'In process': 'waiting'}[s] ?? 'neutral');

// Recorded against declared, as the legacy list showed it ("1/3"), marked while
// intake still has some to enter.
function Progress({recorded, declared, label}) {
  if (recorded == null) return '—';
  const short = declared != null && recorded < declared;
  return <Text size="sm" className="num" c={short ? 'orange.8' : undefined} fw={short ? 600 : undefined}
               aria-label={`${recorded} of ${declared ?? 'unknown'} ${label} entered`}>{recorded}/{declared ?? '?'}</Text>;
}

export function Leads() {
  // Search, status and page live in the address, so a filtered list can be shared or bookmarked.
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '', status = params.get('status') ?? '', page = Number(params.get('page') ?? 1);
  const [typed, setTyped] = useState(q);
  const [search] = useDebouncedValue(typed, 250);
  const set = (next) => setParams(p => {Object.entries(next).forEach(([k, v]) => v ? p.set(k, v) : p.delete(k)); return p;}, {replace: true});
  useEffect(() => {if (search !== q) set({q: search, page: ''});}, [search]);      // eslint-disable-line react-hooks/exhaustive-deps
  const list = useQuery({queryKey: ['leads', q, status, page], queryFn: () => api(`leads/?q=${encodeURIComponent(q)}&page=${page}&status=${status}`),
                         placeholderData: keepPreviousData});
  return <Stack>
    <PageHeader title="Leads" description="Every lead, imported or recorded here."
                actions={<Button component={Link} to="/leads/new">New lead</Button>}/>
    <Group align="flex-end" wrap="wrap" className="responsive-filters">
      <TextInput label="Search" placeholder="Lead number, source ID or office" value={typed} onChange={e => setTyped(e.currentTarget.value)} style={{flex: 1, minWidth: 240}}/>
      <Select label="Status" data={STATUSES} value={status} onChange={v => set({status: v, page: ''})} allowDeselect={false} w={220}/>
    </Group>
    {list.isError ? <ErrorState error={list.error} onRetry={list.refetch}/> : !list.data ? <LoadingState label="Loading leads"/> : <>
      <ResponsiveTable>
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Lead</Table.Th><Table.Th>Commissioning office</Table.Th><Table.Th>Lead giver</Table.Th><Table.Th>Received</Table.Th><Table.Th>Parties</Table.Th><Table.Th>Cases</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{list.data.results.map(r => <Table.Tr key={r.id}>
            <Table.Td><Anchor component={Link} to={`/leads/${r.id}`} fw={600}>{r.number || 'No number'}</Anchor>
              <Text size="xs" c="dimmed">{r.source_id ? `Source ${r.source_id}` : 'Recorded here'}</Text></Table.Td>
            <Table.Td>{r.office?.name || 'Office not resolved'}<Text size="xs" c="dimmed">{r.office?.branch}</Text></Table.Td>
            <Table.Td>{r.lead_giver?.name || '—'}<Text size="xs" c="dimmed">{r.lead_giver?.phone}</Text></Table.Td>
            <Table.Td>{date(r.received_date) || 'Unknown'}</Table.Td>
            <Table.Td><Progress {...r.parties} label="parties"/></Table.Td>
            <Table.Td><Progress {...r.cases} label="cases"/></Table.Td>
            <Table.Td><StatusBadge tone={tone(r.status_label)}>{r.status_label}</StatusBadge></Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table>
      </ResponsiveTable>
      {list.data.count === 0 ? <EmptyState title="No leads match" description="Try a shorter search, or another status."/>
        : <Group justify="space-between"><Text size="sm" c="dimmed">{count(list.data.count)} leads</Text>
            <Pagination total={Math.ceil(list.data.count / PAGE)} value={page} onChange={p => set({page: String(p)})} size="sm"/></Group>}
    </>}
  </Stack>;
}

export function LeadDetail() {
  const {id} = useParams();
  const client = useQueryClient();
  // The open tab lives in the address, so a refresh or a shared link reopens it.
  const [params, setParams] = useSearchParams();
  const tab = TABS.includes(params.get('tab')) ? params.get('tab') : TABS[0];
  const openTab = value => setParams(p => {const next = new URLSearchParams(p); next.set('tab', value); return next;}, {replace: true});
  const lead = useQuery({queryKey: ['lead', id], queryFn: () => api(`leads/${id}/`)});
  const stages = useQuery({queryKey: ['lead', id, 'stages'], queryFn: () => api(`leads/${id}/stages/`)});
  const [note, setNote] = useState('');
  const save = useMutation({
    mutationFn: body => post(`leads/${id}/`, {body}),
    onSuccess: data => {client.setQueryData(['lead', id], data); setNote(''); notifications.show({message: 'Note saved'});},
    onError: e => notifications.show({color: 'red', title: 'The note was not saved', message: e.message}),
  });
  // After a change inside the workspace: this lead, its stage track (a nested key),
  // the lead list and the dashboard counts are all refetched.
  const refreshLead = () => {
    for (const queryKey of [['lead', id], ['leads'], ['home'], ['mis']]) client.invalidateQueries({queryKey});
  };
  if (lead.isError) return <ErrorState error={lead.error} onRetry={lead.refetch}/>;
  if (!lead.data) return <LoadingState label="Loading the lead"/>;
  const d = lead.data;
  const notes = <section>
      <Title order={2} mb={4}>Follow-up notes</Title>
      <Text size="sm" c="dimmed" mb="sm">Notes are kept here and survive refreshes from the previous system.</Text>
      <form onSubmit={e => {e.preventDefault(); save.mutate(note);}}><Stack gap="xs" maw={640}>
        <Textarea label="Add a note" value={note} maxLength={4000} autosize minRows={3} onChange={e => setNote(e.currentTarget.value)} required/>
        <Group><Button type="submit" loading={save.isPending} disabled={!note.trim()}>Save note</Button></Group>
      </Stack></form>
      <Stack gap="sm" mt="lg">{d.notes.map(n => <Paper key={n.id} withBorder p="sm">
        <Text size="sm" style={{whiteSpace: 'pre-wrap'}}>{n.body}</Text>
        <Text size="xs" c="dimmed" mt={4}>{n.author__username}, {dateTime(n.created_at)}</Text></Paper>)}</Stack>
    </section>;
  return <Stack gap="xl">
    <div>
      <Anchor component={Link} to="/leads" size="sm">Back to leads</Anchor>
      <PageHeader title={d.number || `Lead ${d.source_id}`}
                  description={[d.office?.name || 'Office not resolved', d.office?.branch].filter(Boolean).join(', ')}
                  actions={<StatusBadge tone={tone(d.status_label)}>{d.status_label}</StatusBadge>}/>
      <Text size="sm">{d.date_basis === 'actual_intake' ? 'Received' : 'Entered in the previous system'} {date(d.received_date) || 'on an unknown date'}.
        {d.contact?.name && ` Contact: ${d.contact.name}${d.contact.phone ? `, ${d.contact.phone}` : ''}.`}</Text>
      {d.issues.length > 0 && <Text size="sm" c="orange.8" mt="xs">{d.issues.join('; ')}</Text>}
    </div>

    <section>
      <Title order={2} mb="sm">Where each case stands</Title>
      {stages.isError ? <ErrorState error={stages.error} onRetry={stages.refetch}/> : !stages.data ? <LoadingState/>
        : stages.data.cases.length === 0 ? <EmptyState title="No cases yet" description="Cases appear once a service is recorded against a borrower."/>
        : <Stack>{stages.data.cases.map(c => <Paper withBorder p="md" key={c.id}>
            <Group justify="space-between" mb="md" wrap="wrap"><div><Text fw={600}>{c.borrower || 'Borrower not recorded'}</Text>
              <Text size="sm" c="dimmed">{[c.service, c.subtype].filter(Boolean).join(', ')}</Text></div>
              {c.report_number && <Text size="sm" className="num">{c.report_number}</Text>}</Group>
            <StageTrack stages={c.stages} compact label={`Stages for ${c.borrower || 'this case'}`}/>
          </Paper>)}</Stack>}
    </section>

    <Suspense fallback={<LoadingState label="Loading the lead workspace"/>}>
      <LeadWorkspace key={d.id} api={api} leadId={d.id} onChanged={refreshLead} layout={parts => <Tabs value={tab} onChange={openTab} keepMounted>
        <Tabs.List>
          <Tabs.Tab value="details">Lead details</Tabs.Tab>
          <Tabs.Tab value="customers" rightSection={parts.lead && <Badge size="sm" variant="light" title={`${parts.lead.borrowers.length} customers, ${parts.lead.cases.length} cases`}>{parts.lead.borrowers.length} · {parts.lead.cases.length}</Badge>}>Client's customers &amp; cases</Tabs.Tab>
          <Tabs.Tab value="followups" rightSection={<Badge size="sm" variant="light" title="Follow-ups and notes">{d.notes.length + (parts.lead?.follow_ups.length || 0)}</Badge>}>Follow-ups &amp; notes</Tabs.Tab>
          <Tabs.Tab value="orders">Work orders &amp; history</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="details" pt="md"><div className="legacy-screen">{parts.details}</div></Tabs.Panel>
        <Tabs.Panel value="customers" pt="md"><div className="legacy-screen">{parts.customers}</div></Tabs.Panel>
        <Tabs.Panel value="followups" pt="md"><Stack gap="xl">
          {parts.followUps && <div className="legacy-screen">{parts.followUps}</div>}
          {notes}</Stack></Tabs.Panel>
        <Tabs.Panel value="orders" pt="md"><div className="legacy-screen"><div className="intake">{parts.workOrders}{parts.history}</div></div></Tabs.Panel>
      </Tabs>}/></Suspense>
  </Stack>;
}
