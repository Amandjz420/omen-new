import {ResponsiveTable} from '../components/ResponsiveTable.jsx';
import {Group, Pagination, Stack, Table, Text, TextInput} from '@mantine/core';
import {useDebouncedValue} from '@mantine/hooks';
import {keepPreviousData, useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {PageHeader} from '../components/PageHeader.jsx';
import {EmptyState, ErrorState, LoadingState} from '../components/States.jsx';
import {api} from '../lib/api.js';
import {count} from '../lib/format.js';

export function Offices() {
  const [typed, setTyped] = useState('');
  const [q] = useDebouncedValue(typed, 250);
  const [page, setPage] = useState(1);
  const list = useQuery({queryKey: ['offices', q, page], queryFn: () => api(`offices/?q=${encodeURIComponent(q)}&page=${page}`), placeholderData: keepPreviousData});
  return <Stack>
    <PageHeader title="Client offices" description="The bank branches and other clients that commission work."/>
    <TextInput label="Search" placeholder="Office, branch or source ID" value={typed} onChange={e => {setTyped(e.currentTarget.value); setPage(1);}} maw={480}/>
    {list.isError ? <ErrorState error={list.error} onRetry={list.refetch}/> : !list.data ? <LoadingState label="Loading offices"/> : <>
      <ResponsiveTable><Table>
        <Table.Thead><Table.Tr><Table.Th>Office</Table.Th><Table.Th>Branch</Table.Th><Table.Th>Bank</Table.Th><Table.Th>District</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{list.data.results.map(r => <Table.Tr key={r.id}>
          <Table.Td><Text size="sm" fw={600}>{r.name}</Text><Text size="xs" c="dimmed">{r.source_id ? `Source ${r.source_id}` : 'Recorded here'}</Text></Table.Td>
          <Table.Td>{r.branch || '—'}</Table.Td><Table.Td>{r.bank || 'Not a bank'}</Table.Td><Table.Td>{r.district || 'Unknown'}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></ResponsiveTable>
      {list.data.count === 0 ? <EmptyState title="No offices match" description="Try a shorter search."/>
        : <Group justify="space-between"><Text size="sm" c="dimmed">{count(list.data.count)} offices</Text>
            <Pagination total={Math.ceil(list.data.count / 30)} value={page} onChange={setPage} size="sm"/></Group>}
    </>}
  </Stack>;
}
