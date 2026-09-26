import {Badge} from '@mantine/core';

const TONES = {approved: 'green', refused: 'red', waiting: 'yellow', active: 'omen', neutral: 'gray'};

/** A status in plain words; the tone carries the meaning, never the colour alone. */
export function StatusBadge({tone = 'neutral', children}) {
  return <Badge variant="light" color={TONES[tone] ?? 'gray'} radius="sm" tt="none" fw={600}>{children}</Badge>;
}
