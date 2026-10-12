import {Alert, Badge, Button, Drawer, Group, Paper, Stack, Text, Title} from '@mantine/core';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useEffect, useRef, useState} from 'react';
import {api, post} from '../lib/api.js';
import {listDrafts} from '../lib/drafts.js';

export function SiteChecklist({id, onQuestion, unsaved = false}) {
  const client = useQueryClient();
  const [opened, setOpened] = useState(false);
  const [follow, setFollow] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const picker = useRef(null), photoType = useRef(null);
  const check = useQuery({queryKey: ['valuation', id, 'checklist'], queryFn: () => api(`valuations/${id}/checklist/`), enabled: opened});
  const data = check.data;
  const missing = data?.missing_required || [];
  const drafts = listDrafts().filter(d => d.key.startsWith(`valuation:${id}:`));
  const pendingSave = unsaved || drafts.length > 0;
  useEffect(() => {
    if (follow && data && !missing.some(q => String(q.question) === String(follow.question))) setFollow(null);
  }, [data, follow]); // A saved answer must not leave an obsolete follow-up on screen.

  async function ask(question) {
    setBusy(true); setError(''); setFollow(null);
    try {
      const body = await post(`valuations/${id}/checklist/follow-up/`, question ? {question} : {});
      setFollow(body.follow_up);
      await check.refetch();
    } catch (e) { setError(e.message); check.refetch(); }
    finally { setBusy(false); }
  }
  async function upload(file) {
    if (!file || !photoType.current) return;
    const body = new FormData();
    body.append('type', String(photoType.current)); body.append('file', file);
    setUploading(true); setError('');
    try {
      await api(`valuations/${id}/photos/`, {method: 'POST', body});
      await client.invalidateQueries({queryKey: ['valuation', id]});
    } catch (e) { setError(e.message); }
    finally { setUploading(false); }
  }
  function answer(q) { setOpened(false); onQuestion(q); }

  return <>
    <Button variant="light" fullWidth onClick={() => {setOpened(true); setFollow(null); setError(''); if (data) check.refetch();}}>Before leaving the site</Button>
    <Drawer opened={opened} onClose={() => setOpened(false)} position="bottom" size="90%" title="Before leaving the site">
      <Stack gap="md" maw={900} mx="auto" pb="xl">
        <Text size="sm" c="dimmed">Check the remaining required information and expected photographs before you leave.</Text>
        {pendingSave && <Alert color="orange" title="Some answers are not saved to the server">Save or sync your answers first. This checklist counts saved answers only.</Alert>}
        {check.isError && <Alert color="red" title="Checklist unavailable">{check.error.message}<Button variant="subtle" onClick={() => check.refetch()}>Retry checklist</Button></Alert>}
        {check.isFetching && <Text role="status" size="sm">Checking saved information…</Text>}
        {error && <Alert color="red">{error}</Alert>}
        {data && !check.isError && <>
          <Group gap="xs"><Badge color={data.remaining_questions ? 'orange' : 'green'}>{data.remaining_questions} required questions remaining</Badge>
            <Badge color={data.remaining_photos ? 'orange' : 'green'}>{data.remaining_photos} photo categories to check</Badge></Group>
          {!pendingSave && !check.isFetching && data.remaining_questions === 0 && data.remaining_photos === 0 && <Alert color="green">All required questions have saved answers and expected photo categories have file records. Review the evidence before leaving; this is not report approval.</Alert>}
          <Title order={3}>Required information</Title>
          {!missing.length && <Text size="sm">No unanswered required questions.</Text>}
          {missing.length > 0 && <>
            <Button loading={busy} disabled={!data.editable || uploading || pendingSave} onClick={() => ask()}>Ask a focused follow-up</Button>
            {follow && <Paper withBorder p="md" aria-live="polite">
              <Text size="xs" c="dimmed">{follow.ai_generated ? 'AI follow-up — check against the original question' : 'Original question — AI wording unavailable'}</Text>
              <Text fw={600} my="xs">{follow.prompt}</Text>
              <Text size="sm" c="dimmed">Original: {follow.text}</Text>
              <Button mt="sm" onClick={() => answer(follow)}>Answer this question</Button>
              <Text size="xs" mt="xs">Type or select an answer in the form, or use Record and review the suggested answer.</Text>
            </Paper>}
            {missing.map(q => <Paper withBorder p="sm" key={q.question}>
              <Text size="xs" c="dimmed">{q.section}</Text><Text size="sm" fw={600}>{q.text}</Text>
              <Group gap="xs" mt="xs"><Button size="xs" variant="light" onClick={() => answer(q)}>Open question</Button>
                <Button size="xs" variant="subtle" disabled={busy || !data.editable || pendingSave} onClick={() => ask(q.question)}>Help me answer</Button></Group>
            </Paper>)}
          </>}
          <Title order={3}>Photographs and plans</Title>
          <Text size="sm" c="dimmed">{data.photo_policy}</Text>
          <input ref={picker} type="file" accept="image/jpeg,image/png,image/webp,image/bmp" capture="environment" hidden aria-label="Add checklist photograph"
            onChange={e => {const file = e.currentTarget.files?.[0]; e.currentTarget.value = ''; upload(file);}}/>
          {data.photos.map(p => <Paper withBorder p="sm" key={p.code}>
            <Group justify="space-between" wrap="wrap"><Text fw={600} size="sm">{p.label}</Text>
              <Badge color={p.status === 'recorded' ? 'green' : 'orange'}>{p.status === 'recorded' ? 'File recorded' : p.status === 'unavailable' ? 'File unavailable' : 'Missing'}</Badge>
              {p.status !== 'recorded' && data.editable && <Button size="xs" disabled={uploading} onClick={() => {photoType.current = p.code; picker.current?.click();}}>Add {p.label}</Button>}
            </Group>
          </Paper>)}
          {uploading && <Text role="status">Saving photograph…</Text>}
          <Text size="xs" c="dimmed">{data.photo_check}</Text>
          <Button variant="default" disabled={check.isFetching || uploading} onClick={() => check.refetch()}>Refresh checklist</Button>
        </>}
      </Stack>
    </Drawer>
  </>;
}
