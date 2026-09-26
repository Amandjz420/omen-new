import {Alert, Button, Center, Loader, Stack, Text, Title} from '@mantine/core';

export function LoadingState({label = 'Loading'}) {
  return <Center py="xl"><Stack align="center" gap="xs"><Loader size="sm"/><Text size="sm" c="dimmed">{label}</Text></Stack></Center>;
}

/** An empty list says what would appear here, and offers the next step. */
export function EmptyState({title, description, action}) {
  return <Stack align="flex-start" gap="xs" py="lg">
    <Title order={3}>{title}</Title>
    {description && <Text size="sm" c="dimmed">{description}</Text>}
    {action}
  </Stack>;
}

/** An error says what went wrong and how to recover. */
export function ErrorState({error, onRetry}) {
  return <Alert color="red" variant="light" title="This could not be loaded" role="alert">
    <Stack gap="xs" align="flex-start">
      <Text size="sm">{error?.message || String(error)}</Text>
      {onRetry && <Button size="xs" variant="light" color="red" onClick={onRetry}>Try again</Button>}
    </Stack>
  </Alert>;
}
