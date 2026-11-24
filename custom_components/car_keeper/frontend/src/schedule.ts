// The due rule: the same rule as `schedule.py`. The golden corpus
// `tests/fixtures/shared/schedule.json` holds the 2 copies together. The tab uses it
// to show the limits of a reading that the user types, before the server has it.
import { roundReading } from './units';

export type Status = 'ok' | 'soon' | 'overdue';
export const RANK: Record<Status, number> = { ok: 0, soon: 1, overdue: 2 };
const DAILY_WINDOW_DAYS = 90;
const DAILY_MIN_DAYS = 7;
const DAY = 86_400_000;

export interface Base {
  date?: string | null;
  reading?: number | null;
}

export interface Item {
  kind?: string;
  enabled?: boolean;
  interval_distance?: number | null;
  interval_months?: number | null;
  due_date?: string | null;
  start?: Base | null;
  last_done?: Base | null;
}

export interface Evaluation {
  status: Status;
  first: 'distance' | 'date' | null;
  distance_limit: number | null;
  distance_left: number | null;
  date_limit: string | null;
  days_left: number | null;
  eta_days: number | null;
}

/** The days since 1970 of a `YYYY-MM-DD` date, or of the date part of a timestamp. */
function dayNumber(value: string): number {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / DAY);
}

/** *value* plus *months*. A day past the end of the month moves to its last day. */
export function addMonths(value: string, months: number): string {
  const [y, m, d] = value.slice(0, 10).split('-').map(Number);
  const total = y * 12 + (m - 1) + months;
  const year = Math.floor(total / 12);
  const month = total - year * 12;
  const last = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const day = Math.min(d, last);
  return `${String(year).padStart(4, '0')}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/** The days from *start* to *end*. Negative when *end* is earlier. */
export function daysBetween(start: string, end: string): number {
  return dayNumber(end) - dayNumber(start);
}

/** The worst status, or `ok` for none. */
export function worst(statuses: Status[]): Status {
  return statuses.reduce<Status>((a, b) => (RANK[b] > RANK[a] ? b : a), 'ok');
}

/** The average distance a day over the last 90 days, or null. */
export function dailyDistance(readings: { ts: string; value: number }[], today: string): number | null {
  const start = dayNumber(today) - DAILY_WINDOW_DAYS;
  const points = readings
    .map((r) => [dayNumber(r.ts), Number(r.value)] as [number, number])
    .filter(([day]) => day >= start)
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (points.length < 2) return null;
  const span = points[points.length - 1][0] - points[0][0];
  if (span < DAILY_MIN_DAYS) return null;
  return Math.max(0, (points[points.length - 1][1] - points[0][1]) / span);
}

/** The next due date of a date item, or null when it is done for good. */
export function dateDue(item: Item, leadDays: number): string | null {
  const due = item.due_date;
  const done = item.last_done;
  if (!due || !done || !done.date) return due ?? null;
  const months = item.interval_months;
  let step = 0;
  let current = due;
  while (daysBetween(done.date, current) <= leadDays) {
    if (!months) return null;
    step += 1;
    current = addMonths(due, months * step);
  }
  return current;
}

function limitStatus(left: number, lead: number): Status {
  if (left <= 0) return 'overdue';
  if (left <= lead) return 'soon';
  return 'ok';
}

/** The limits and the status of 1 item. */
export function evaluate(
  item: Item,
  odometer: number | null,
  daily: number | null,
  today: string,
  leadDistance: number,
  leadDays: number,
): Evaluation {
  const base = item.last_done || item.start || {};
  const out: Evaluation = {
    status: 'ok',
    first: null,
    distance_limit: null,
    distance_left: null,
    date_limit: null,
    days_left: null,
    eta_days: null,
  };
  if (item.enabled === false) return out;
  const statuses: Status[] = [];
  let distanceDays: number | null = null;
  const interval = item.interval_distance;
  if (interval && base.reading != null && odometer != null) {
    const limit = roundReading(base.reading + interval);
    const left = roundReading(limit - odometer);
    out.distance_limit = limit;
    out.distance_left = left;
    statuses.push(limitStatus(left, leadDistance));
    if (daily) distanceDays = Math.max(0, left) / daily;
    else if (left <= 0) distanceDays = 0;
  }
  let dateLimit: string | null = null;
  if (item.kind === 'date') dateLimit = dateDue(item, leadDays);
  else if (item.interval_months && base.date) dateLimit = addMonths(base.date, item.interval_months);
  if (dateLimit) {
    const days = daysBetween(today, dateLimit);
    out.date_limit = dateLimit;
    out.days_left = days;
    statuses.push(limitStatus(days, leadDays));
  }
  if (dateLimit !== null && distanceDays !== null) {
    out.first = distanceDays < (out.days_left as number) ? 'distance' : 'date';
  } else if (dateLimit !== null) out.first = 'date';
  else if (out.distance_limit !== null) out.first = 'distance';
  const etas = [distanceDays, out.days_left].filter((d): d is number => d !== null);
  out.eta_days = etas.length ? Math.min(...etas) : null;
  out.status = worst(statuses);
  return out;
}
