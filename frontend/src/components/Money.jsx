import {Text} from '@mantine/core';
import {rupees} from '../lib/format.js';

/** An amount in rupees, with fixed-width figures so columns line up. */
export function Money({value, paise = true, ...props}) {
  return <Text component="span" className="num" inherit {...props}>{rupees(value, {paise})}</Text>;
}
