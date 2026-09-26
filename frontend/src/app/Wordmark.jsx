import classes from './Shell.module.css';

/** The Omen Assessors wordmark, set as on the previous site: bold, widely spaced. */
export function Wordmark({size = 'md'}) {
  return <span className={classes.wordmark} data-size={size}>
    <span className={classes.omen}>OMEN</span>
    <span className={classes.assessors}>ASSESSORS</span>
  </span>;
}
