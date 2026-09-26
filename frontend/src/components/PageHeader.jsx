import {Group, Stack, Text, Title} from '@mantine/core';

export function PageHeader({title, description, actions}) {
  return <Group justify="space-between" align="flex-end" wrap="wrap" gap="md" mb="lg">
    <Stack gap={4} maw={720}>
      <Title order={1}>{title}</Title>
      {description && <Text c="dimmed" size="sm">{description}</Text>}
    </Stack>
    {actions && <Group gap="sm">{actions}</Group>}
  </Group>;
}
