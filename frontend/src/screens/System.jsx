import {Alert, Paper, SimpleGrid, Stack, Table, Text, Title} from '@mantine/core';
import {useQuery} from '@tanstack/react-query';
import {PageHeader} from '../components/PageHeader.jsx';
import {ErrorState, LoadingState} from '../components/States.jsx';
import {api} from '../lib/api.js';
import {count, dateTime} from '../lib/format.js';

const useSummary = () => useQuery({queryKey: ['summary'], queryFn: () => api('summary/')});

function Figure({label, value, note}) {
  return <div><Text size="sm" c="dimmed">{label}</Text><Text fz={28} fw={650} className="num" lh={1.2}>{count(value)}</Text>
    {note && <Text size="xs" c="dimmed">{note}</Text>}</div>;
}

export function MigrationStatus() {
  const s = useSummary();
  if (s.isError) return <ErrorState error={s.error} onRetry={s.refetch}/>;
  if (!s.data) return <LoadingState/>;
  const d = s.data, top = Math.max(1, ...d.services.map(v => v.count));
  return <Stack gap="xl">
    <PageHeader title="Migration status" description="What was brought across from the previous system, and how it was handled."/>
    <Paper withBorder p="lg"><SimpleGrid cols={{base: 2, sm: 4}} spacing="lg">
      <Figure label="Client offices" value={d.offices}/><Figure label="Leads" value={d.leads}/>
      <Figure label="Cases" value={d.cases}/><Figure label="Contacts" value={d.contacts}/>
    </SimpleGrid></Paper>
    <Paper withBorder p="lg"><SimpleGrid cols={{base: 2, sm: 4}} spacing="lg">
      <Figure label="Source rows read" value={d.source_rows} note="Every row, including rejects"/>
      <Figure label="Imported" value={d.source_rows - d.quarantined_source_rows}/>
      <Figure label="Imported with corrections" value={d.rows_with_issues}/>
      <Figure label="Held back" value={d.quarantined_source_rows} note="Not imported; the original is kept"/>
    </SimpleGrid></Paper>
    <section><Title order={2} mb="sm">Recorded work by service</Title>
      <Stack gap={10}>{d.services.map(v => <div key={v.service}>
        <Text size="sm" mb={2}>{v.service || 'Unclassified'} <Text span c="dimmed" className="num">{count(v.count)}</Text></Text>
        <div style={{height: 8, background: 'var(--mantine-color-gray-2)', borderRadius: 4}}><div style={{height: 8, borderRadius: 4, width: `${100 * v.count / top}%`, background: 'var(--mantine-color-omen-6)'}}/></div>
      </div>)}</Stack></section>
    <Alert color="yellow" variant="light">Closed is a status from the previous system. It does not by itself mean the valuation was completed or paid.</Alert>
  </Stack>;
}

export function ImportHistory() {
  const s = useSummary();
  if (s.isError) return <ErrorState error={s.error} onRetry={s.refetch}/>;
  if (!s.data) return <LoadingState/>;
  const last = s.data.latest_import;
  return <Stack>
    <PageHeader title="Import history" description="The most recent import from the previous system. Records are matched by their source IDs, and nothing missing from a later import is deleted."/>
    {!last ? <Text>No import has been recorded.</Text> : <>
      <Text size="sm">Imported {dateTime(last.created_at)}</Text>
      <Table.ScrollContainer minWidth={560}><Table>
        <Table.Thead><Table.Tr><Table.Th>Source</Table.Th><Table.Th ta="right">Added</Table.Th><Table.Th ta="right">Updated</Table.Th><Table.Th ta="right">Unchanged</Table.Th><Table.Th>Handling</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{Object.entries(last.summary).map(([sheet, x]) => <Table.Tr key={sheet}>
          <Table.Td>{sheet}</Table.Td><Table.Td ta="right" className="num">{count(x.inserted ?? x.staged_inserted)}</Table.Td>
          <Table.Td ta="right" className="num">{count(x.updated ?? x.staged_updated)}</Table.Td><Table.Td ta="right" className="num">{count(x.unchanged)}</Table.Td>
          <Table.Td>{x.staged_inserted !== undefined ? 'Staged only' : `${count(x.rows_with_issues)} rows corrected`}</Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer></>}
  </Stack>;
}
