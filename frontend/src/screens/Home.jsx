import {Anchor, Paper, Stack, Table, Text, Title} from '@mantine/core';
import {useQueries} from '@tanstack/react-query';
import {Link} from 'react-router';
import {PageHeader} from '../components/PageHeader.jsx';
import {StageTrack} from '../components/StageTrack.jsx';
import {api} from '../lib/api.js';
import {count} from '../lib/format.js';

// What is waiting at each stage. A queue the person may not open (dispatch, for an
// assessor restricted to their own leads) simply does not appear.
const SOURCES = [
  ['valuations', 'valuations/?status=not_started', d => d.total, 'Valuation', 'Valuations not started', '/valuations'],
  ['pending', 'valuations/?status=Pending', d => d.total, 'Valuation', 'Valuations in progress', '/valuations'],
  ['reverted', 'valuations/?status=Revert', d => d.total, 'Valuation', 'Sent back for correction', '/valuations'],
  ['verification', 'verifications/?track=legal', d => Object.values(d.counts).reduce((a, b) => a + b, 0), 'Verification', 'Verifications waiting, across the four tracks', '/verification'],
  ['bank', 'bank-reports/', d => d.counts.pending, 'Bank report', 'Ready for a bank report', '/bank-reports'],
  ['approval', 'approvals/', d => d.counts.pending, 'Approval', 'Awaiting final approval', '/approval'],
  ['invoice', 'invoices/', d => d.counts.to_invoice, 'Invoice', 'Approved work to invoice', '/invoices'],
  ['unpaid', 'invoices/?state=unpaid', d => d.counts.unpaid, 'Invoice', 'Invoices with money outstanding', '/invoices'],
  ['receipts', 'receipts/', d => d.counts.to_check + d.counts.to_verify, 'Receipts', 'Receipts to check or verify', '/receipts'],
  ['dispatch', 'dispatch/awaiting/', d => d.total, 'Dispatch', 'Approved reports not yet sent', '/dispatch'],
];
const STAGES = [['Valuation', '/valuations'], ['Verification', '/verification'], ['Bank report', '/bank-reports'],
  ['Approval', '/approval'], ['Invoice', '/invoices'], ['Receipts', '/receipts'], ['Dispatch', '/dispatch']];

export function Home() {
  const results = useQueries({queries: SOURCES.map(([key, path]) => ({queryKey: ['home', key], queryFn: () => api(path), retry: 0}))});
  const rows = SOURCES.map(([key, , pick, stage, label, to], i) => {
    const r = results[i];
    return {key, stage, label, to, loading: r.isPending, missing: r.isError, value: r.data ? pick(r.data) : null};
  });
  const stages = STAGES.map(([label, to]) => {
    const own = rows.filter(r => r.stage === label && !r.missing);
    const known = own.filter(r => r.value !== null);
    const n = known.reduce((a, r) => a + r.value, 0);
    return {key: label, label, to, count: own.length && known.length === own.length ? n : undefined,
            state: !own.length ? 'skipped' : n > 0 ? 'current' : 'waiting'};
  });
  return <Stack gap="xl">
    <PageHeader title="My work" description="What is waiting at each stage, from a valuation to the report reaching the bank."/>
    <Paper withBorder p={{base: 'md', sm: 'xl'}}><StageTrack stages={stages} label="Work waiting at each stage"/></Paper>
    <div>
      <Title order={2} mb="sm">Queues</Title>
      <Table.ScrollContainer minWidth={420}>
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Stage</Table.Th><Table.Th>Queue</Table.Th><Table.Th ta="right">Waiting</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{rows.filter(r => !r.missing).map(r => <Table.Tr key={r.key}>
            <Table.Td><Text size="sm" c="dimmed">{r.stage}</Text></Table.Td>
            <Table.Td><Anchor component={Link} to={r.to} size="sm">{r.label}</Anchor></Table.Td>
            <Table.Td ta="right" className="num">{r.loading ? '…' : count(r.value)}</Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </div>
  </Stack>;
}
