import dayjs from 'dayjs';

/** Rupees with Indian digit grouping: 3850000 -> "₹38,50,000.00". */
export function rupees(value, {paise = true} = {}) {
  const n = Number(value || 0);
  return `₹${n.toLocaleString('en-IN', {minimumFractionDigits: paise ? 2 : 0, maximumFractionDigits: paise ? 2 : 0})}`;
}

/** A plain count with Indian grouping: 1234567 -> "12,34,567". */
export const count = value => Number(value || 0).toLocaleString('en-IN');

/** A calendar date: "2026-09-27" -> "27 Sep 2026". Empty stays empty. */
export const date = value => (value ? dayjs(value).format('D MMM YYYY') : '');
export const dateTime = value => (value ? dayjs(value).format('D MMM YYYY, h:mm a') : '');
