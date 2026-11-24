import { describe, expect, it } from 'vitest';
import '../src/card-index.ts';
import { cleanConfig } from '../src/card.ts';
import { fakeHass, flush } from './fake-hass.js';
import GARAGE from './fixtures/garage.json';

function mount(tag, config, opts = {}) {
  const fake = fakeHass(opts);
  const el = document.createElement(tag);
  el.setConfig(config);
  document.body.appendChild(el);
  el.hass = fake.hass;
  const $ = (sel) => el.shadowRoot.querySelector(sel);
  return { el, fake, $ };
}

describe('cards', () => {
  it('are in the card picker', () => {
    const types = window.customCards.map((c) => c.type);
    expect(types).toContain('car-keeper-garage-card');
    expect(types).toContain('car-keeper-car-card');
  });

  it('check the config', () => {
    expect(() => cleanConfig(undefined, false)).toThrow('The card configuration is not valid.');
    expect(() => cleanConfig({ type: 'x', max_height: 0 }, false)).toThrow('max_height');
    expect(() => cleanConfig({ type: 'x', max_height: 'tall' }, false)).toThrow('max_height');
    expect(cleanConfig({ type: 'x', max_height: '240' }, false).max_height).toBe(240);
    expect(() => cleanConfig({ type: 'x' }, true)).toThrow('car_id');
    expect(cleanConfig({ type: 'x', car_id: 'c' }, true).car_id).toBe('c');
  });
});

describe('garage card', () => {
  it('shows the title and the empty state', async () => {
    const { $ } = mount('car-keeper-garage-card', { type: 'custom:car-keeper-garage-card' });
    await flush();
    expect($('.ck-title').textContent).toBe('Garage');
    expect($('.ck-empty').textContent).toBe('No cars');
  });

  it('shows each car with its status and grows with no max_height', async () => {
    const { $, el } = mount(
      'car-keeper-garage-card',
      { type: 'custom:car-keeper-garage-card', title: 'Our cars' },
      { state: structuredClone(GARAGE) },
    );
    await flush();
    expect($('.ck-title').textContent).toBe('Our cars');
    const rows = [...el.shadowRoot.querySelectorAll('[data-car]')];
    expect(rows.map((r) => r.dataset.car)).toEqual(['civic', 'model3']);
    expect(rows[1].querySelector('.ck-chip').dataset.status).toBe('overdue');
    expect(rows[1].textContent).toContain('18,250 mi');
    expect($('.ck-scroll')).toBeNull();
  });

  it('scrolls inside the card with a max_height', async () => {
    const { $ } = mount(
      'car-keeper-garage-card',
      { type: 'custom:car-keeper-garage-card', max_height: 120 },
      { state: structuredClone(GARAGE) },
    );
    await flush();
    expect($('.ck-scroll').style.maxHeight).toBe('120px');
  });
});

describe('car card', () => {
  const config = { type: 'custom:car-keeper-car-card', car_id: 'civic' };

  it('shows the car, its odometer and its jobs', async () => {
    const { $, el } = mount('car-keeper-car-card', config, { state: structuredClone(GARAGE) });
    await flush();
    expect($('.ck-title').textContent).toBe('Civic');
    expect($('.ck-big').textContent).toBe('41,800 km');
    const jobs = [...el.shadowRoot.querySelectorAll('[data-item]')].map((li) => li.dataset.item);
    expect(jobs[0]).toBe('civic-registration');
  });

  it('types a reading and marks a job done', async () => {
    const { $, fake } = mount('car-keeper-car-card', config, { state: structuredClone(GARAGE) });
    await flush();
    $('[data-k="odometer"]').value = '-1';
    $('[data-k="save-odometer"]').click();
    await flush();
    expect($('[role="status"]').textContent).toBe('Type a number that is 0 or more.');
    expect(fake.calls('set_odometer')).toEqual([]);
    $('[data-k="odometer"]').value = '42000';
    $('[data-k="save-odometer"]').click();
    await flush();
    expect(fake.calls('set_odometer')[0]).toMatchObject({ car_id: 'civic', value: 42000 });
    $('[data-k="done-civic-engine_oil"]').click();
    await flush();
    expect(fake.calls('log_service')[0]).toMatchObject({ car_id: 'civic', items: ['civic-engine_oil'] });
    expect($('[role="status"]').textContent).toBe('Service logged');
  });

  it('shows the error of the server', async () => {
    const { $ } = mount('car-keeper-car-card', config, {
      state: structuredClone(GARAGE),
      replies: { set_odometer: () => Promise.reject(new Error('The reading is below the last reading.')) },
    });
    await flush();
    $('[data-k="odometer"]').value = '5';
    $('[data-k="save-odometer"]').click();
    await flush();
    expect($('[role="status"]').textContent).toBe('The reading is below the last reading.');
  });

  it('shows a notice for a car that is gone', async () => {
    const { $ } = mount('car-keeper-car-card', { ...config, car_id: 'nope' }, { state: structuredClone(GARAGE) });
    await flush();
    expect($('.ck-empty').textContent).toBe('This car is gone.');
  });
});
