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
/** A moment, on the 24-hour clock: "27 Sep 2026, 14:05". */
export const dateTime = value => (value ? dayjs(value).format('D MMM YYYY, HH:mm') : '');

/** Today's date as YYYY-MM-DD on the user's own calendar. toISOString() gives the UTC
 *  date, which in India is still yesterday from midnight until 5:30 in the morning:
 *  every date field then defaulted to yesterday, and the server, which keeps Indian
 *  time, refused a verification as dated before the valuation. */
export function today(date = new Date()) {
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
