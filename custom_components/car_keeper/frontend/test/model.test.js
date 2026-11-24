// Unit tests and model tests of `model.ts`. The 2 form state machines (Log service
// and Add car) get fast-check model tests: a random list of actions runs against the
// reducer and against a small model, and the 2 must agree after each step.
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import {
  ADD_STEPS,
  addData,
  addError,
  addReduce,
  addStart,
  carRows,
  distance,
  itemRows,
  logData,
  logError,
  logReduce,
  logStart,
  money,
  nextItem,
  serviceRows,
  starterJobs,
} from '../src/model.ts';
import GARAGE from './fixtures/garage.json';

const RUNS = Number(process.env.CK_STATEFUL_EXAMPLES || 200);

describe('rows', () => {
  it('orders the cars by name', () => {
    expect(carRows(GARAGE).map((c) => c.id)).toEqual(['civic', 'model3']);
  });

  it('orders the jobs: on first, then the worst status, then the nearest limit, then the name', () => {
    expect(itemRows(GARAGE, 'civic').map((i) => i.id)).toEqual([
      'civic-registration',
      'civic-tyre_rotation',
      'civic-engine_oil',
    ]);
    const state = structuredClone(GARAGE);
    state.items['civic-registration'].enabled = false;
    expect(itemRows(state, 'civic').at(-1).id).toBe('civic-registration');
    state.items['civic-tyre_rotation'].due = { status: 'soon', eta_days: null };
    state.items['civic-engine_oil'].due = { status: 'soon', eta_days: 3 };
    expect(itemRows(state, 'civic').map((i) => i.id).slice(0, 2)).toEqual([
      'civic-engine_oil',
      'civic-tyre_rotation',
    ]);
    state.items['civic-engine_oil'].due = { status: 'soon', eta_days: null };
    state.items['civic-engine_oil'].name = 'Z';
    state.items['civic-tyre_rotation'].name = 'A';
    expect(itemRows(state, 'civic')[0].id).toBe('civic-tyre_rotation');
  });

  it('orders the services, the newest first', () => {
    const state = structuredClone(GARAGE);
    state.services.s2 = { ...state.services.s1, id: 's2', date: '2026-05-01' };
    state.services.s3 = { ...state.services.s1, id: 's3', logged: '2026-04-02T11:00:00+00:00' };
    expect(serviceRows(state, 'civic').map((s) => s.id)).toEqual(['s2', 's3', 's1']);
    expect(serviceRows(state, 'model3')).toEqual([]);
  });

  it('finds the next job and the starter jobs of a fuel', () => {
    expect(nextItem(GARAGE, GARAGE.cars.civic).id).toBe('civic-registration');
    expect(nextItem(GARAGE, { summary: {} })).toBeUndefined();
    const electric = starterJobs(GARAGE, 'electric').map((j) => j.id);
    expect(electric).toContain('tyre_rotation');
    expect(electric).not.toContain('engine_oil');
    const off = structuredClone(GARAGE);
    off.starter_jobs.find((j) => j.id === 'tyre_rotation').enabled = false;
    expect(starterJobs(off, 'electric').map((j) => j.id)).not.toContain('tyre_rotation');
    expect(starterJobs({}, 'petrol')).toEqual([]);
  });

  it('writes a distance and a cost', () => {
    expect(distance(15000, 'km')).toBe('15,000 km');
    expect(distance(null, 'km')).toBe('');
    expect(distance(Number.NaN, 'mi')).toBe('');
    expect(money(84.5)).toBe('84.50');
    expect(money(undefined)).toBe('');
  });
});

describe('Log service form', () => {
  it('starts with the jobs and the reading', () => {
    expect(logStart(['a', 'a', 'b'], '2026-10-15', 41800)).toEqual({
      items: ['a', 'b'],
      date: '2026-10-15',
      reading: '41800',
      cost: '',
      shop: '',
      notes: '',
    });
    expect(logStart([], 'x', null).reading).toBe('');
  });

  it('finds each error', () => {
    const ok = logStart(['a'], '2026-10-15', 1);
    expect(logError(ok)).toBe('');
    expect(logError({ ...ok, items: [] })).toBe('need_job');
    expect(logError({ ...ok, date: '15.10.2026' })).toBe('bad_date');
    expect(logError({ ...ok, reading: '-1' })).toBe('bad_reading');
    expect(logError({ ...ok, reading: 'x' })).toBe('bad_reading');
    expect(logError({ ...ok, cost: '-2' })).toBe('bad_cost');
    expect(logError({ ...ok, reading: '  ', cost: '' })).toBe('');
  });

  it('gives the service data', () => {
    const form = { ...logStart(['a'], '2026-10-15', 1), cost: '12.5', shop: ' Shop ', notes: ' n ' };
    expect(logData(form, 'c')).toEqual({
      car_id: 'c',
      items: ['a'],
      date: '2026-10-15',
      reading: 1,
      cost: 12.5,
      shop: 'Shop',
      notes: 'n',
    });
    expect(logData({ ...form, reading: '', cost: '', shop: ' ', notes: '' }, 'c')).toEqual({
      car_id: 'c',
      items: ['a'],
      date: '2026-10-15',
    });
  });

  it('matches its model for each list of actions', () => {
    const ids = fc.constantFrom('a', 'b', 'c');
    const action = fc.oneof(
      ids.map((id) => ({ type: 'toggle', id })),
      fc.record({
        type: fc.constant('set'),
        field: fc.constantFrom('date', 'reading', 'cost', 'shop', 'notes'),
        value: fc.string({ maxLength: 6 }),
      }),
    );
    fc.assert(
      fc.property(fc.array(action, { maxLength: 30 }), (actions) => {
        let form = logStart([], '2026-01-01', null);
        const model = { items: new Set(), fields: { date: '2026-01-01', reading: '', cost: '', shop: '', notes: '' } };
        for (const a of actions) {
          form = logReduce(form, a);
          if (a.type === 'toggle') {
            if (model.items.has(a.id)) model.items.delete(a.id);
            else model.items.add(a.id);
          } else {
            model.fields[a.field] = a.value;
          }
          // The selected jobs are the model set, with no repeat.
          expect(new Set(form.items)).toEqual(model.items);
          expect(form.items.length).toBe(model.items.size);
          for (const key of Object.keys(model.fields)) expect(form[key]).toBe(model.fields[key]);
          // A form with no error always gives data with its jobs.
          if (!logError(form)) expect(logData(form, 'c').items).toEqual(form.items);
        }
      }),
      { numRuns: RUNS },
    );
  });
});

describe('Add car form', () => {
  it('steps only from a step with no error', () => {
    let form = addStart('km', ['engine_oil', 'engine_oil']);
    expect(form.jobs).toEqual(['engine_oil']);
    expect(addError(form)).toBe('need_name');
    expect(addReduce(form, { type: 'next' }).step).toBe(1);
    form = addReduce(form, { type: 'set', field: 'name', value: 'Civic' });
    form = addReduce(form, { type: 'set', field: 'year', value: '18' });
    expect(addError(form)).toBe('bad_year');
    form = addReduce(form, { type: 'set', field: 'year', value: '2018' });
    form = addReduce(form, { type: 'next' });
    expect(form.step).toBe(2);
    form = addReduce(form, { type: 'set', field: 'odometer', value: '-5' });
    expect(addError(form)).toBe('bad_odometer');
    expect(addReduce(form, { type: 'next' }).step).toBe(2);
    form = addReduce(form, { type: 'set', field: 'odometer', value: '1200' });
    form = addReduce(addReduce(form, { type: 'next' }), { type: 'next' });
    expect(form.step).toBe(ADD_STEPS);
    expect(addReduce(addStart('km', []), { type: 'back' }).step).toBe(1);
  });

  it('gives the car data', () => {
    const form = {
      ...addStart('mi', ['a']),
      name: ' Civic ',
      make: 'Honda',
      model: '',
      year: '2018',
      vin: ' v ',
      plate: '',
      odometer: '12',
    };
    expect(addData(form)).toEqual({
      name: 'Civic',
      fuel: 'petrol',
      unit: 'mi',
      starter_jobs: ['a'],
      make: 'Honda',
      vin: 'v',
      year: 2018,
      odometer: 12,
    });
    expect(addData({ ...form, year: '', odometer: '' })).not.toHaveProperty('year');
  });

  it('matches its model for each list of actions', () => {
    const action = fc.oneof(
      fc.constant({ type: 'next' }),
      fc.constant({ type: 'back' }),
      fc.constantFrom('x', 'y').map((id) => ({ type: 'toggle', id })),
      fc.record({
        type: fc.constant('set'),
        field: fc.constantFrom('name', 'year', 'odometer', 'make'),
        value: fc.constantFrom('', 'Civic', '2018', '18', '-1', '500'),
      }),
    );
    fc.assert(
      fc.property(fc.array(action, { maxLength: 40 }), (actions) => {
        let form = addStart('km', []);
        let step = 1;
        for (const a of actions) {
          const before = form;
          form = addReduce(form, a);
          if (a.type === 'next' && !addError(before) && step < ADD_STEPS) step += 1;
          if (a.type === 'back' && step > 1) step -= 1;
          expect(form.step).toBe(step);
          // The step stays in range, and a move past the first step needs a name.
          expect(form.step >= 1 && form.step <= ADD_STEPS).toBe(true);
          if (before.step === 1 && form.step === 2) expect(before.name.trim()).not.toBe('');
          expect(new Set(form.jobs).size).toBe(form.jobs.length);
        }
      }),
      { numRuns: RUNS },
    );
  });
});
