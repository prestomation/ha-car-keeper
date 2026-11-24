// Pure helpers of the tab and the cards: the rows that a view shows, the labels of a
// value, and the 2 form state machines (Log service and Add car). Nothing here reads
// the DOM, so the unit tests, the model tests and the mutation gate cover it.
import type { State } from './api';
import { groupDigits } from './units';

export type Rec = Record<string, any>;

export const STATUS_RANK: Record<string, number> = { ok: 0, soon: 1, overdue: 2 };

/** The cars, by name. */
export function carRows(state: State): Rec[] {
  return Object.values(state.cars).sort((a, b) =>
    String(a.name).localeCompare(String(b.name)),
  );
}

/**
 * The jobs of a car. An enabled job comes first, then the worst status, then the
 * nearest limit (`eta_days`), then the name.
 */
export function itemRows(state: State, carId: string): Rec[] {
  const rows = Object.values(state.items).filter((i) => i.car_id === carId);
  return rows.sort((a, b) => {
    const on = Number(b.enabled !== false) - Number(a.enabled !== false);
    if (on) return on;
    const rank = (STATUS_RANK[b.due?.status] ?? 0) - (STATUS_RANK[a.due?.status] ?? 0);
    if (rank) return rank;
    const ea = a.due?.eta_days ?? Number.POSITIVE_INFINITY;
    const eb = b.due?.eta_days ?? Number.POSITIVE_INFINITY;
    if (ea !== eb) return ea < eb ? -1 : 1;
    return String(a.name).localeCompare(String(b.name));
  });
}

/** The service records of a car, the newest first. */
export function serviceRows(state: State, carId: string): Rec[] {
  return Object.values(state.services)
    .filter((s) => s.car_id === carId)
    .sort((a, b) =>
      a.date === b.date ? String(b.logged).localeCompare(String(a.logged)) : a.date < b.date ? 1 : -1,
    );
}

/** A distance with its unit: "15,000 km". An empty value gives "". */
export function distance(value: unknown, unit: string): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '';
  return `${groupDigits(value)} ${unit}`;
}

/** A cost with 2 decimals, or "" for no cost. */
export function money(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '';
}

/** The next job of a car, or undefined. */
export function nextItem(state: State, car: Rec): Rec | undefined {
  const id = car.summary?.next_item_id;
  return id ? state.items[id] : undefined;
}

/** The starter jobs that a car with *fuel* can take, enabled first. */
export function starterJobs(state: State, fuel: string): Rec[] {
  return ((state as Rec).starter_jobs ?? []).filter(
    (job: Rec) => job.enabled && (job.fuels as string[]).includes(fuel),
  );
}

// ── Log service ─────────────────────────────────────────────────────────────

export interface LogForm {
  items: string[];
  date: string;
  reading: string;
  cost: string;
  shop: string;
  notes: string;
}

export type LogAction =
  | { type: 'toggle'; id: string }
  | { type: 'set'; field: Exclude<keyof LogForm, 'items'>; value: string };

/** A new Log service form, with the given jobs selected and today. */
export function logStart(items: string[], today: string, reading: number | null): LogForm {
  return {
    items: [...new Set(items)],
    date: today,
    reading: reading == null ? '' : String(reading),
    cost: '',
    shop: '',
    notes: '',
  };
}

/** The next form after *action*. A job toggles in or out, in the order of the clicks. */
export function logReduce(form: LogForm, action: LogAction): LogForm {
  if (action.type === 'toggle') {
    const items = form.items.includes(action.id)
      ? form.items.filter((id) => id !== action.id)
      : [...form.items, action.id];
    return { ...form, items };
  }
  return { ...form, [action.field]: action.value };
}

function numberOrNull(text: string): number | null | undefined {
  const clean = text.trim();
  if (!clean) return null;
  const value = Number(clean);
  return Number.isFinite(value) && value >= 0 ? value : undefined;
}

/** The error of the form (a key under `log.`), or "" when the form can be saved. */
export function logError(form: LogForm): string {
  if (form.items.length === 0) return 'need_job';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.date)) return 'bad_date';
  if (numberOrNull(form.reading) === undefined) return 'bad_reading';
  if (numberOrNull(form.cost) === undefined) return 'bad_cost';
  return '';
}

/** The `log_service` data of a form that has no error. */
export function logData(form: LogForm, carId: string): Rec {
  const data: Rec = { car_id: carId, items: form.items, date: form.date };
  const reading = numberOrNull(form.reading);
  const cost = numberOrNull(form.cost);
  if (reading != null) data.reading = reading;
  if (cost != null) data.cost = cost;
  if (form.shop.trim()) data.shop = form.shop.trim();
  if (form.notes.trim()) data.notes = form.notes.trim();
  return data;
}

// ── Add car ─────────────────────────────────────────────────────────────────

export const ADD_STEPS = 3;

export interface AddForm {
  step: number;
  name: string;
  make: string;
  model: string;
  year: string;
  fuel: string;
  unit: string;
  vin: string;
  plate: string;
  odometer: string;
  jobs: string[];
}

export type AddAction =
  | { type: 'next' }
  | { type: 'back' }
  | { type: 'set'; field: Exclude<keyof AddForm, 'step' | 'jobs'>; value: string }
  | { type: 'toggle'; id: string }
  | { type: 'jobs'; ids: string[] };

export function addStart(unit: string, jobs: string[]): AddForm {
  return {
    step: 1,
    name: '',
    make: '',
    model: '',
    year: '',
    fuel: 'petrol',
    unit,
    vin: '',
    plate: '',
    odometer: '',
    jobs: [...new Set(jobs)],
  };
}

/** The error of the current step (a key under `add.`), or "". */
export function addError(form: AddForm): string {
  if (form.step === 1) {
    if (!form.name.trim()) return 'need_name';
    if (form.year.trim() && !/^\d{4}$/.test(form.year.trim())) return 'bad_year';
  }
  if (form.step === 2 && numberOrNull(form.odometer) === undefined) return 'bad_odometer';
  return '';
}

/**
 * The next form after *action*. Next moves on only from a step with no error, and
 * never past the last step. Back never goes before the first step.
 */
export function addReduce(form: AddForm, action: AddAction): AddForm {
  switch (action.type) {
    case 'next':
      return addError(form) || form.step >= ADD_STEPS ? form : { ...form, step: form.step + 1 };
    case 'back':
      return form.step > 1 ? { ...form, step: form.step - 1 } : form;
    case 'toggle': {
      const jobs = form.jobs.includes(action.id)
        ? form.jobs.filter((id) => id !== action.id)
        : [...form.jobs, action.id];
      return { ...form, jobs };
    }
    case 'jobs':
      return { ...form, jobs: [...new Set(action.ids)] };
    default:
      return { ...form, [action.field]: action.value };
  }
}

/** The `add_car` data of a form on its last step. */
export function addData(form: AddForm): Rec {
  const data: Rec = {
    name: form.name.trim(),
    fuel: form.fuel,
    unit: form.unit,
    starter_jobs: form.jobs,
  };
  for (const key of ['make', 'model', 'vin', 'plate'] as const) {
    if (form[key].trim()) data[key] = form[key].trim();
  }
  if (form.year.trim()) data.year = Number(form.year.trim());
  const odometer = numberOrNull(form.odometer);
  if (odometer != null) data.odometer = odometer;
  return data;
}
