import {Anchor, Button, Group, Pagination, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput, Title} from '@mantine/core';
import {DatePickerInput} from '@mantine/dates';
import {useDebouncedValue} from '@mantine/hooks';
import {keepPreviousData, useQuery} from '@tanstack/react-query';
import dayjs from 'dayjs';
import {useEffect, useState} from 'react';
import {Link, useParams, useSearchParams} from 'react-router';
import {Money} from '../components/Money.jsx';
import {PageHeader} from '../components/PageHeader.jsx';
import {EmptyState, ErrorState, LoadingState} from '../components/States.jsx';
import {api} from '../lib/api.js';
import {count, date} from '../lib/format.js';
import classes from './Reports.module.css';

/** The report list, under the numbers staff know from the previous system. */
export function ReportList() {
  const list = useQuery({queryKey: ['mis'], queryFn: () => api('mis/')});
  if (list.isError) return <ErrorState error={list.error} onRetry={list.refetch}/>;
  if (!list.data) return <LoadingState label="Loading reports"/>;
  const sections = Object.entries(list.data.reports.reduce((acc, r) => ({...acc, [r.section]: [...(acc[r.section] ?? []), r]}), {}));
  return <Stack gap="xl">
    <PageHeader title="Reports" description="The management reports, with money counted once per invoice. Every report exports to Excel."/>
    {sections.map(([section, reports]) => <section key={section}>
      <Title order={2} mb="sm">{section}</Title>
      <SimpleGrid cols={{base: 1, sm: 2}} spacing="sm">{reports.map(r => <Paper key={r.key} withBorder p="md" component={Link} to={`/reports/${r.key}`} className={classes.card}>
        <Text fw={650}>{r.title} <Text span c="dimmed" size="sm" fw={400}>{r.number}</Text></Text>
        <Text size="sm" c="dimmed">{r.description}</Text>
      </Paper>)}</SimpleGrid>
    </section>)}
  </Stack>;
}

const iso = d => (d ? dayjs(d).format('YYYY-MM-DD') : '');

/** One report. Its dates, grouping and search live in the address, so it can be bookmarked or shared. */
export function ReportView() {
  const {key} = useParams();
  const [params, setParams] = useSearchParams();
  const get = name => params.get(name) ?? '';
  const set = next => setParams(p => {Object.entries(next).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k))); return p;}, {replace: true});
  const [typed, setTyped] = useState(get('q'));
  const [search] = useDebouncedValue(typed, 300);
  useEffect(() => {if (search !== get('q')) set({q: search, within: '', page: ''});}, [search]);   // eslint-disable-line react-hooks/exhaustive-deps

  const query = ['from', 'to', 'group', 'q'].map(k => get(k) && `${k}=${encodeURIComponent(get(k))}`).filter(Boolean).join('&');
  const within = params.has('within') ? get('within') : null;
  const detailQuery = within !== null ? `&within=${encodeURIComponent(within)}&page=${get('page') || 1}` : '';
  const data = useQuery({queryKey: ['mis', key, query, detailQuery], queryFn: () => api(`mis/${key}/?${query}${detailQuery}`), placeholderData: keepPreviousData});

  if (data.isError) return <ErrorState error={data.error} onRetry={data.refetch}/>;
  if (!data.data) return <LoadingState label="Running the report"/>;
  const r = data.data, lead = r.measures.find(x => x.kind === 'money') ?? r.measures.find(x => x.kind !== 'percent') ?? r.measures[0];
  const top = Math.max(1, ...r.groups.map(g => Number(g.values[lead.key])));
  // Money in rupees; percentages to one place, or a dash where there is no target to measure against.
  const cell = (m, v) => (m.kind === 'money' ? <Money value={v}/>
    : m.kind === 'percent' ? <span className="num">{v === null || v === undefined ? '—' : `${Number(v).toLocaleString('en-IN', {minimumFractionDigits: 1, maximumFractionDigits: 1})}%`}</span>
    : <span className="num">{count(v)}</span>);
  const range = [get('from') ? dayjs(get('from')).toDate() : null, get('to') ? dayjs(get('to')).toDate() : null];

  return <Stack gap="lg">
    <div>
      <Anchor component={Link} to="/reports" size="sm">All reports</Anchor>
      <PageHeader title={r.title} description={r.description}
                  actions={<Button component="a" href={`/api/mis/${key}/export/?${query}`} download variant="light">Export to Excel</Button>}/>
    </div>
    <Group align="flex-end" wrap="wrap">
      <DatePickerInput type="range" label={r.date_label} placeholder="All dates" clearable value={range} valueFormat="D MMM YYYY"
                       onChange={([a, b]) => set({from: iso(a), to: iso(b), within: '', page: ''})} w={260}/>
      {r.groupings.length > 1 && <Select label="Group by" data={r.groupings.map(g => ({value: g.key, label: g.label}))} value={r.group}
                                         allowDeselect={false} onChange={v => set({group: v, within: '', page: ''})} w={220}/>}
      <TextInput label="Search" placeholder="Lead number, client or client customer" value={typed}
                 onChange={e => setTyped(e.currentTarget.value)} style={{flex: 1, minWidth: 220}}/>
    </Group>

    <Paper withBorder p="md">
      <SimpleGrid cols={{base: 2, sm: r.measures.length}} spacing="md">
        {r.measures.map(m => <div key={m.key}><Text size="sm" c="dimmed">{m.label}</Text>
          <Text fz={22} fw={650} lh={1.2}>{cell(m, r.totals[m.key])}</Text></div>)}
      </SimpleGrid>
    </Paper>

    {r.groups.length === 0 ? <EmptyState title="Nothing in this report" description="Try a wider date range, or clear the search."/> :
      <Table.ScrollContainer minWidth={560}>
        <Table>
          <Table.Thead><Table.Tr><Table.Th>{r.group_label}</Table.Th>{r.measures.map(m => <Table.Th key={m.key} ta="right">{m.label}</Table.Th>)}</Table.Tr></Table.Thead>
          <Table.Tbody>
            {r.groups.map(g => <Table.Tr key={g.key} className={within === g.key ? classes.chosen : undefined}>
              <Table.Td>
                <Anchor component="button" type="button" size="sm" onClick={() => set({within: within === g.key ? '' : g.key, page: ''})}
                        aria-expanded={within === g.key}>{g.label}</Anchor>
                <div className={classes.bar} aria-hidden="true"><span style={{width: `${100 * Number(g.values[lead.key]) / top}%`}}/></div>
              </Table.Td>
              {r.measures.map(m => <Table.Td key={m.key} ta="right">{cell(m, g.values[m.key])}</Table.Td>)}
            </Table.Tr>)}
          </Table.Tbody>
          <Table.Tfoot><Table.Tr><Table.Th>Total</Table.Th>{r.measures.map(m => <Table.Th key={m.key} ta="right">{cell(m, r.totals[m.key])}</Table.Th>)}</Table.Tr></Table.Tfoot>
        </Table>
      </Table.ScrollContainer>}

    {r.detail && <section aria-label={`Records for ${r.detail.label}`}>
      <Title order={2} mb="sm">{r.detail.label}</Title>
      <Table.ScrollContainer minWidth={900}>
        <Table striped>
          <Table.Thead><Table.Tr>{r.columns.map(c => <Table.Th key={c.key} ta={['money', 'number', 'percent'].includes(c.kind) ? 'right' : undefined}>{c.label}</Table.Th>)}</Table.Tr></Table.Thead>
          <Table.Tbody>{r.detail.rows.map((row, i) => <Table.Tr key={i}>{r.columns.map(c => <Table.Td key={c.key} ta={['money', 'number', 'percent'].includes(c.kind) ? 'right' : undefined}>
            {['money', 'number', 'percent'].includes(c.kind) ? cell(c, row[c.key]) : c.kind === 'date' ? date(row[c.key]) : row[c.key] || '—'}</Table.Td>)}</Table.Tr>)}</Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      {r.detail.total > r.detail.page_size && <Group justify="space-between" mt="sm">
        <Text size="sm" c="dimmed">{count(r.detail.total)} records</Text>
        <Pagination total={Math.ceil(r.detail.total / r.detail.page_size)} value={r.detail.page} onChange={p => set({page: String(p)})} size="sm"/>
      </Group>}
    </section>}
  </Stack>;
}

