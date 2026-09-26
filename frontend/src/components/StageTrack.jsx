import {Box, Text, UnstyledButton} from '@mantine/core';
import {Link} from 'react-router';
import classes from './StageTrack.module.css';

/** Where a case, or the whole firm's work, stands across the stages of a valuation.
 * The stages are a true sequence, so they are numbered. Each stage is done, current,
 * waiting, stopped, or not applicable; with `count` it shows how much is waiting there. */
export function StageTrack({stages, compact = false, label = 'Stages'}) {
  return <Box component="ol" className={classes.track} data-compact={compact || undefined} aria-label={label}>
    {stages.map((s, i) => {
      const body = <>
        <span className={classes.node} aria-hidden="true">{s.state === 'done' ? '✓' : i + 1}</span>
        <span className={classes.text}>
          <Text component="span" className={classes.name}>{s.label}</Text>
          {s.count !== undefined && <Text component="span" className={`${classes.count} num`}>{s.count.toLocaleString('en-IN')}</Text>}
          {s.detail && <Text component="span" className={classes.detail}>{s.detail}</Text>}
        </span>
      </>;
      return <li key={s.key} className={classes.stage} data-state={s.state} aria-current={s.state === 'current' ? 'step' : undefined}>
        {s.to ? <UnstyledButton component={Link} to={s.to} className={classes.link}>{body}</UnstyledButton> : <div className={classes.link}>{body}</div>}
      </li>;
    })}
  </Box>;
}
