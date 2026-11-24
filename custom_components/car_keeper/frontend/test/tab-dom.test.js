import { describe, expect, it } from 'vitest';
import '../src/tab-index.ts';
import { fakeHass, fixture, flush } from './fake-hass.js';
import GARAGE from './fixtures/garage.json';

// The host moves the tab the same way as the Home Keeper panel: `navigate` sets the
// route of the element.
function mount(opts = {}, path = '') {
  const fake = fakeHass(opts);
  const el = document.createElement('home-keeper-cars-tab');
  document.body.appendChild(el);
  const nav = [];
  const toasts = [];
  el.host = {
    apiVersion: 1,
    navigate: (p, o) => {
      nav.push([p, Boolean(o?.replace)]);
      el.route = { path: p };
    },
    showToast: (text) => toasts.push(text),
    applianceLink: (id) => `/home-keeper/appliances/${id}`,
  };
  el.route = { path };
  el.hass = fake.hass;
  const $ = (sel) => el.shadowRoot.querySelector(sel);
  const $$ = (sel) => [...el.shadowRoot.querySelectorAll(sel)];
  const click = async (sel) => {
    $(sel).click();
    await flush();
  };
  const type = (key, value) => {
    const input = $(`[data-k="${key}"]`);
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  };
  return { el, fake, nav, toasts, $, $$, click, type };
}

const garage = () => structuredClone(GARAGE);

describe('Cars tab', () => {
  it('shows the empty garage', async () => {
    const { $ } = mount();
    await flush();
    expect($('.ck-empty h2').textContent).toBe('No cars');
  });

  it('loads again after a change message', async () => {
    const { fake } = mount();
    await flush();
    fake.push();
    await flush();
    expect(fake.calls('get_state').length).toBe(2);
  });

  it('shows the error of a failed read', async () => {
    const { $ } = mount({ replies: { get_state: () => Promise.reject(new Error('boom <b>')) } });
    await flush();
    const alert = $('[role="alert"]');
    expect(alert.textContent).toContain('boom <b>');
    expect(alert.querySelector('b')).toBeNull();
  });

  it('shows each car of the garage with its status and its next job', async () => {
    const { $$, $, click, nav } = mount({ state: garage() });
    await flush();
    const tiles = $$('.ck-car');
    expect(tiles.map((b) => b.dataset.car)).toEqual(['civic', 'model3']);
    expect(tiles[1].querySelector('.ck-chip').dataset.status).toBe('overdue');
    expect(tiles[0].textContent).toContain('41,800 km');
    expect(tiles[0].textContent).toContain('Registration');
    await click('[data-car="model3"]');
    expect(nav.at(-1)).toEqual(['/car/model3', false]);
    expect($('[data-view="car"]')).not.toBeNull();
  });

  it('escapes the name of a car', async () => {
    const state = garage();
    state.cars.civic.name = '<img src=x onerror=alert(1)>';
    const { $ } = mount({ state });
    await flush();
    expect($('.ck-car img')).toBeNull();
    expect($('.ck-car-name').textContent).toBe('<img src=x onerror=alert(1)>');
  });

  it('shows a car with its jobs, its history and its details', async () => {
    const { $, $$ } = mount({ state: garage() }, '/car/civic');
    await flush();
    expect($('h1').textContent).toBe('Civic');
    expect($$('[data-item]').map((li) => li.dataset.item)).toEqual([
      'civic-registration',
      'civic-tyre_rotation',
      'civic-engine_oil',
    ]);
    expect($('[data-item="civic-engine_oil"]').textContent).toContain('in 8,200 km or in 169 days');
    expect($('[data-section="history"]').textContent).toContain('Total cost: 84.50');
    expect($('[data-section="car"]').textContent).toContain('1HGFC2F59JA000000');
    expect($('[data-k="appliance"]')).toBeNull();
  });

  it('links the appliance of a car in Home Keeper', async () => {
    const state = garage();
    state.cars.civic.hk_asset_id = 'a1';
    const { $ } = mount({ state }, '/car/civic');
    await flush();
    expect($('[data-k="appliance"]').getAttribute('href')).toBe('/home-keeper/appliances/a1');
  });

  it('links only a path of Home Assistant', async () => {
    const state = garage();
    state.cars.civic.hk_asset_id = 'a1';
    const { el, $ } = mount({ state }, '/car/civic');
    el.host.applianceLink = () => 'javascript:alert(1)';
    el.route = { path: '/car/civic' };
    await flush();
    expect($('[data-k="appliance"]')).toBeNull();
    el.host.applianceLink = () => '//evil.example/x';
    el.route = { path: '/car/civic' };
    expect($('[data-k="appliance"]')).toBeNull();
  });

  it('closes a question on Escape, and stops listening when the tab is gone', async () => {
    const { el, $, click, fake } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="delete-car"]');
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect($('[data-confirm]')).toBeNull();
    await click('[data-k="delete-car"]');
    const dialog = $('[data-confirm]');
    dialog.remove();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    el.shadowRoot.appendChild(dialog);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect($('[data-confirm]')).not.toBeNull();
    expect(fake.calls('delete_car')).toEqual([]);
  });

  it('shows the gone notice for a car that is not there', async () => {
    const { $, click, nav } = mount({ state: garage() }, '/car/nope');
    await flush();
    expect($('[data-view="gone"]')).not.toBeNull();
    await click('[data-k="back"]');
    expect(nav.at(-1)).toEqual(['/', false]);
  });

  it('saves a reading, and shows the error of a bad one', async () => {
    const { $, click, type, fake, toasts } = mount({ state: garage() }, '/car/civic');
    await flush();
    type('odometer', '-3');
    await click('[data-k="save-odometer"]');
    expect($('.ck-error').textContent).toBe('Type a number that is 0 or more.');
    expect(fake.calls('set_odometer')).toEqual([]);
    type('odometer', '42000');
    await click('[data-k="save-odometer"]');
    expect(fake.calls('set_odometer')[0]).toMatchObject({ car_id: 'civic', value: 42000 });
    expect(toasts).toContain('Reading saved');
    expect($('.ck-error')).toBeNull();
  });

  it('shows the error of the server for a lower reading', async () => {
    const { $, click, type } = mount(
      {
        state: garage(),
        replies: { set_odometer: () => Promise.reject(new Error('The reading is below the last reading.')) },
      },
      '/car/civic',
    );
    await flush();
    type('odometer', '10');
    await click('[data-k="save-odometer"]');
    expect($('.ck-error').textContent).toBe('The reading is below the last reading.');
  });

  it('logs a service with the jobs of the dialog', async () => {
    const { $, click, type, fake, nav } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="done-civic-engine_oil"]');
    expect(nav.at(-1)).toEqual(['/car/civic/log', false]);
    expect($('[data-log]')).not.toBeNull();
    expect($('[data-k="log-item-civic-engine_oil"]').checked).toBe(true);
    await click('[data-k="log-item-civic-tyre_rotation"]');
    type('log-cost', '120');
    type('log-shop', 'Main Street Garage');
    await click('[data-k="log-save"]');
    expect(fake.calls('log_service')[0]).toMatchObject({
      car_id: 'civic',
      items: ['civic-engine_oil', 'civic-tyre_rotation'],
      cost: 120,
      shop: 'Main Street Garage',
      reading: 41800,
    });
    expect(nav.at(-1)).toEqual(['/car/civic', true]);
    expect($('[data-log]')).toBeNull();
  });

  it('keeps the Log dialog open with the error of a form with no job', async () => {
    const { $, click, fake } = mount({ state: garage() }, '/car/civic/log');
    await flush();
    await click('[data-k="log-save"]');
    expect($('[data-log] .ck-error').textContent).toBe('Select 1 job or more.');
    expect(fake.calls('log_service')).toEqual([]);
    await click('[data-k="log-cancel"]');
    expect($('[data-log]')).toBeNull();
  });

  it('asks before it deletes a job, a service or a car', async () => {
    const { $, click, fake, nav } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="delete-civic-engine_oil"]');
    expect($('[data-confirm] h3').textContent).toBe('Delete Engine oil?');
    await click('[data-confirm-act="cancel"]');
    expect($('[data-confirm]')).toBeNull();
    expect(fake.calls('delete_item')).toEqual([]);
    await click('[data-k="delete-civic-engine_oil"]');
    await click('[data-confirm-act="ok"]');
    expect(fake.calls('delete_item')[0]).toMatchObject({ item_id: 'civic-engine_oil' });
    await click('[data-k="delete-service-s1"]');
    await click('[data-confirm-act="ok"]');
    expect(fake.calls('delete_service')[0]).toMatchObject({ service_id: 's1' });
    await click('[data-k="delete-car"]');
    expect($('[data-confirm] p').textContent).toContain('appliance stays');
    await click('[data-confirm-act="ok"]');
    expect(fake.calls('delete_car')[0]).toMatchObject({ car_id: 'civic' });
    expect(nav.at(-1)).toEqual(['/', true]);
  });

  it('keeps an open question when the store changes', async () => {
    const { $, click, fake } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="delete-car"]');
    fake.push();
    await flush();
    expect($('[data-confirm]')).not.toBeNull();
  });

  it('edits and adds a job', async () => {
    const { $, click, type, fake } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="edit-civic-engine_oil"]');
    type('item-civic-engine_oil-distance', '10000');
    await click('[data-k="item-civic-engine_oil-save"]');
    expect(fake.calls('update_item')[0]).toMatchObject({
      item_id: 'civic-engine_oil',
      interval_distance: 10000,
      interval_months: 12,
      add_task: true,
      enabled: true,
    });
    await click('[data-k="add-item"]');
    type('item-new-name', 'Wax');
    type('item-new-months', '6');
    await click('[data-k="item-new-save"]');
    expect(fake.calls('add_item')[0]).toMatchObject({
      car_id: 'civic',
      name: 'Wax',
      interval_distance: null,
      interval_months: 6,
    });
    await click('[data-k="add-item"]');
    await click('[data-k="item-new-cancel"]');
    expect($('[data-form="item-new"]')).toBeNull();
  });

  it('edits a car', async () => {
    const { click, type, fake } = mount({ state: garage() }, '/car/civic');
    await flush();
    await click('[data-k="edit-car"]');
    type('car-engine', 'K20C');
    type('car-registered', '2018-03-01');
    await click('[data-k="car-save"]');
    expect(fake.calls('update_car')[0]).toMatchObject({
      car_id: 'civic',
      name: 'Civic',
      engine_code: 'K20C',
      first_registered: '2018-03-01',
      odometer_source: 'manual',
      year: 2018,
    });
  });

  it('adds a car in 3 steps', async () => {
    const { $, click, type, fake, nav } = mount(
      { state: garage(), replies: { add_car: { car: { id: 'fit' } } } },
      '/add',
    );
    await flush();
    await click('[data-k="add-next"]');
    expect($('.ck-error').textContent).toBe('Type a name.');
    type('add-name', 'Fit');
    await click('[data-k="add-next"]');
    expect($('[data-step]').dataset.step).toBe('2');
    type('add-odometer', '5000');
    await click('[data-k="add-next"]');
    expect($('[data-step]').dataset.step).toBe('3');
    expect($('[data-k="add-job-engine_oil"]').checked).toBe(true);
    await click('[data-k="add-job-engine_oil"]');
    await click('[data-k="add-next"]');
    const sent = fake.calls('add_car')[0];
    expect(sent).toMatchObject({ name: 'Fit', odometer: 5000, unit: 'km' });
    expect(sent.starter_jobs).not.toContain('engine_oil');
    expect(nav.at(-1)).toEqual(['/car/fit', true]);
  });

  it('changes the starter jobs with the fuel', async () => {
    const { $, $$, click, type } = mount({ state: garage() }, '/add');
    await flush();
    type('add-name', 'EV');
    const fuel = $('[data-k="add-fuel"]');
    fuel.value = 'electric';
    fuel.dispatchEvent(new Event('change', { bubbles: true }));
    await click('[data-k="add-next"]');
    await click('[data-k="add-next"]');
    const jobs = $$('[data-act="add-toggle"]').map((i) => i.dataset.id);
    expect(jobs).not.toContain('engine_oil');
    expect(jobs).toContain('tyre_rotation');
  });

  it('saves the settings with the starter job overrides', async () => {
    const { $, click, fake } = mount({ state: garage() }, '/settings');
    await flush();
    $('[data-k="tpl-wipers-on"]').click();
    $('[data-k="tpl-engine_oil-km"]').value = '12000';
    await click('[data-k="settings-save"]');
    const call = fake.calls('set_settings')[0];
    expect(call.unit).toBe('km');
    expect(call.templates.wipers).toMatchObject({ enabled: false });
    expect(call.templates.engine_oil).toMatchObject({ km: 12000, months: 12, enabled: true });
    expect(call.templates.registration).not.toHaveProperty('km');
  });

  it('lists the car presets and says that Home Keeper holds them', async () => {
    const state = garage();
    state.presets = {
      status: 'registered',
      preset_ids: ['car_keeper/volvo_life_low', 'car_keeper/volvo_alert_binary_sensor_on'],
      error: null,
      rows: [{ domain: 'volvo', brand: 'Volvo <Cars>', duties: ['annual_service', 'check_tyres'] }],
    };
    const { $, $$ } = mount({ state }, '/settings');
    await flush();
    expect($('[data-k="presets-status"]').textContent).toBe('2 presets are in Home Keeper.');
    expect($('[data-k="presets-status"]').dataset.status).toBe('registered');
    const row = $$('[data-preset]')[0];
    expect(row.dataset.preset).toBe('volvo');
    expect(row.textContent).toContain('Volvo <Cars>');
    expect(row.innerHTML).not.toContain('<Cars>');
    expect(row.textContent).toContain('Annual service, Check the tyres');
  });

  it.each([
    [{ status: 'registered', preset_ids: ['a'] }, '1 preset is in Home Keeper.'],
    [{ status: 'no_service' }, 'Your Home Keeper cannot take presets from a companion.'],
    [{ status: 'failed', error: 'rows[0]: bad' }, 'Home Keeper refused the presets: rows[0]: bad'],
    [{ status: 'waiting' }, 'Car Keeper is sending the presets to Home Keeper.'],
    [{}, 'Car Keeper is sending the presets to Home Keeper.'],
    [{ status: 'paused' }, 'Car Keeper is sending the presets to Home Keeper.'],
  ])('says the preset status %o', async (presets, text) => {
    const state = garage();
    state.presets = presets;
    const { $ } = mount({ state }, '/settings');
    await flush();
    expect($('[data-k="presets-status"]').textContent).toContain(text);
  });

  it('shows the error of a refused call as a toast', async () => {
    const { click, toasts } = mount(
      { state: garage(), replies: { delete_item: () => Promise.reject(new Error('Only an admin can do this.')) } },
      '/car/civic',
    );
    await flush();
    await click('[data-k="delete-civic-engine_oil"]');
    await click('[data-confirm-act="ok"]');
    expect(toasts).toContain('Only an admin can do this.');
  });

  it('opens the garage of an old fixture with no car', async () => {
    const { $ } = mount({ state: fixture() }, '/car/x');
    await flush();
    expect($('[data-view="gone"]')).not.toBeNull();
  });
});
