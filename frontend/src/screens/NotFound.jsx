import {Anchor, Stack, Text, Title} from '@mantine/core';
import {Link} from 'react-router';

export function NotFound() {
  return <Stack py="xl" gap="xs"><Title order={1}>There is no page at this address</Title>
    <Text c="dimmed">It may have moved in the new layout. <Anchor component={Link} to="/">Go to My work</Anchor>.</Text></Stack>;
}
