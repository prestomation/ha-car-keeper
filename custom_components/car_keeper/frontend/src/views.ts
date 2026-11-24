// The markup of each view of the tab. Each function is pure: it takes the state
// and the form state and returns HTML. Every user value goes through `escapeHTML`.
// Each control has a `data-k`, so a render keeps the focus and the typed text.
import type { Presets, State } from './api';
import { formatDate, t, tn } from './i18n';
import {
  ADD_STEPS,
  carRows,
  distance,
  itemRows,
  money,
  nextItem,
  serviceRows,
  starterJobs,
  type AddForm,
  type LogForm,
  type Rec,
} from './model';
import { escapeHTML as e } from './utils';

export interface DetailUi {
  odometer: string;
  odometerError: string;
  editCar: boolean;
  editItem: string;
  addItem: boolean;
}

const FUELS = ['petrol', 'diesel', 'hybrid', 'plug_in_hybrid', 'electric', 'other'];

function chip(status: string): string {
  const key = ['ok', 'soon', 'overdue'].includes(status) ? status : 'ok';
  return `<span class="ck-chip ${key}" data-status="${key}">${e(t(`status.${key}`))}</span>`;
}

function field(
  key: string,
  label: string,
  value: unknown,
  type = 'text',
  extra = '',
): string {
  return `<label class="ck-field"><span>${e(label)}</span>
    <input data-k="${e(key)}" name="${e(key)}" type="${type}" value="${e(value ?? '')}" ${extra}></label>`;
}

const OPTION_TEXT: Record<string, (o: string) => string> = {
  fuel: (o) => t(`fuel.${o}`),
  unit: (o) => t(`unit.${o}`),
  source: (o) => t(`source.${o}`),
};

function select(key: string, label: string, value: string, options: string[], kind: string): string {
  const opts = options
    .map((o) => `<option value="${e(o)}" ${o === value ? 'selected' : ''}>${e(OPTION_TEXT[kind](o))}</option>`)
    .join('');
  return `<label class="ck-field"><span>${e(label)}</span>
    <select data-k="${e(key)}" name="${e(key)}">${opts}</select></label>`;
}

/** The text of the next limit of a job: "in 1,200 km or 45 days". */
export function limitText(item: Rec, unit: string): string {
  const due = item.due ?? {};
  if (item.enabled === false) return t('item.off');
  const parts: string[] = [];
  if (typeof due.distance_left === 'number') {
    parts.push(
      due.distance_left <= 0
        ? t('item.over_distance', { distance: distance(-due.distance_left, unit) })
        : t('item.in_distance', { distance: distance(due.distance_left, unit) }),
    );
  }
  if (typeof due.days_left === 'number') {
    parts.push(
      due.days_left <= 0
        ? tn('item.over_days', Math.max(-due.days_left, 0))
        : tn('item.in_days', due.days_left),
    );
  }
  return parts.length ? parts.join(` ${t('item.or')} `) : t('item.no_limit');
}

/** Only a path in Home Assistant is a link: never a scheme such as `javascript:`. */
export function safeLink(url: string): boolean {
  return /^\/(?!\/)/.test(url);
}

// ── Garage ──────────────────────────────────────────────────────────────────

export function garageView(state: State): string {
  const cars = carRows(state);
  const head = `<div class="ck-head"><h1>${e(t('garage.title'))}</h1>
    <div class="ck-head-actions">
      <button class="ck-btn text" data-act="go" data-path="/settings" data-k="to-settings">${e(
        t('settings.title'),
      )}</button>
      <button class="ck-btn primary" data-act="go" data-path="/add" data-k="to-add">${e(
        t('add.title'),
      )}</button></div></div>`;
  if (cars.length === 0) {
    return `${head}<div class="ck-empty" data-view="garage"><h2>${e(t('garage.empty_title'))}</h2>
      <p>${e(t('garage.empty_text'))}</p></div>`;
  }
  const tiles = cars
    .map((car) => {
      const next = nextItem(state, car);
      const status = car.summary?.status ?? 'ok';
      const sub = [car.make, car.model, car.year].filter(Boolean).join(' ');
      return `<button class="ck-car ${e(status)}" data-act="go" data-path="/car/${encodeURIComponent(
        car.id,
      )}" data-k="car-${e(car.id)}" data-car="${e(car.id)}">
        <span class="ck-car-top"><span class="ck-car-name">${e(car.name)}</span>${chip(status)}</span>
        <span class="ck-muted">${e(sub)}</span>
        <span class="ck-car-odo">${e(distance(car.odometer?.value, car.unit) || t('car.no_reading'))}</span>
        <span class="ck-muted">${
          next ? `${e(next.name)}: ${e(limitText(next, car.unit))}` : e(t('car.no_jobs'))
        }</span></button>`;
    })
    .join('');
  return `${head}<div class="ck-grid" data-view="garage">${tiles}</div>`;
}

// ── Car detail ──────────────────────────────────────────────────────────────

function odometerCard(car: Rec, ui: DetailUi): string {
  const odo = car.odometer ?? {};
  const fromSensor = odo.source === 'entity';
  return `<section class="ck-card" data-section="odometer"><h2>${e(t('car.odometer'))}</h2>
    <div class="ck-big">${e(distance(odo.value, car.unit) || t('car.no_reading'))}</div>
    <p class="ck-muted">${e(
      fromSensor ? t('car.from_sensor', { entity: odo.entity_id ?? '' }) : t('car.typed'),
    )}</p>
    <div class="ck-row">
      ${field('odometer', t('car.new_reading', { unit: car.unit }), ui.odometer, 'number', 'min="0" step="0.1" inputmode="decimal"')}
      <button class="ck-btn primary" data-act="odometer" data-k="save-odometer">${e(t('action.save'))}</button>
    </div>
    ${ui.odometerError ? `<p class="ck-error" role="alert">${e(ui.odometerError)}</p>` : ''}
  </section>`;
}

function itemForm(item: Rec | null, unit: string): string {
  const v = item ?? { kind: 'job', add_task: true, enabled: true };
  const key = item ? `item-${item.id}` : 'item-new';
  return `<div class="ck-form" data-form="${e(key)}">
    ${field(`${key}-name`, t('item.name'), v.name)}
    ${field(`${key}-distance`, t('item.interval_distance', { unit }), v.interval_distance, 'number', 'min="1"')}
    ${field(`${key}-months`, t('item.interval_months'), v.interval_months, 'number', 'min="1"')}
    ${field(`${key}-notes`, t('item.notes'), v.notes)}
    <label class="ck-check"><input type="checkbox" data-k="${key}-task" ${v.add_task ? 'checked' : ''}>
      ${e(t('item.add_task'))}</label>
    <label class="ck-check"><input type="checkbox" data-k="${key}-enabled" ${v.enabled !== false ? 'checked' : ''}>
      ${e(t('item.enabled'))}</label>
    <div class="ck-actions">
      <button class="ck-btn" data-act="item-cancel" data-k="${key}-cancel">${e(t('action.cancel'))}</button>
      <button class="ck-btn primary" data-act="item-save" data-id="${e(item?.id ?? '')}" data-k="${key}-save">${e(
        t('action.save'),
      )}</button></div></div>`;
}

function itemsCard(state: State, car: Rec, ui: DetailUi): string {
  const rows = itemRows(state, car.id)
    .map((item) => {
      if (ui.editItem === item.id) return `<li class="ck-item">${itemForm(item, car.unit)}</li>`;
      const status = item.enabled === false ? 'ok' : (item.due?.status ?? 'ok');
      return `<li class="ck-item ${item.enabled === false ? 'off' : ''}" data-item="${e(item.id)}">
        <div class="ck-item-main"><span class="ck-item-name">${e(item.name)}</span>${
          item.enabled === false ? '' : chip(status)
        }</div>
        <div class="ck-muted">${e(limitText(item, car.unit))}</div>
        <div class="ck-actions">
          <button class="ck-btn text" data-act="edit-item" data-id="${e(item.id)}" data-k="edit-${e(item.id)}">${e(
            t('action.edit'),
          )}</button>
          <button class="ck-btn text danger" data-act="delete-item" data-id="${e(item.id)}" data-k="delete-${e(item.id)}">${e(
            t('action.delete'),
          )}</button>
          <button class="ck-btn" data-act="log" data-id="${e(item.id)}" data-k="done-${e(item.id)}">${e(
            t('item.done'),
          )}</button></div></li>`;
    })
    .join('');
  return `<section class="ck-card" data-section="jobs"><div class="ck-card-head"><h2>${e(t('car.jobs'))}</h2>
      <button class="ck-btn text" data-act="add-item" data-k="add-item">${e(t('item.add'))}</button></div>
    ${ui.addItem ? itemForm(null, car.unit) : ''}
    ${rows ? `<ul class="ck-list">${rows}</ul>` : `<p class="ck-muted">${e(t('car.no_jobs'))}</p>`}
    <p class="ck-note">${e(t('car.manual_note'))}</p></section>`;
}

function historyCard(state: State, car: Rec): string {
  const rows = serviceRows(state, car.id)
    .map((s) => {
      const names = (s.items as string[])
        .map((id) => state.items[id]?.name)
        .filter(Boolean)
        .join(', ');
      const facts = [distance(s.reading, car.unit), s.shop, money(s.cost)].filter(Boolean).join(' · ');
      return `<li class="ck-item" data-service="${e(s.id)}"><div class="ck-item-main">
        <span class="ck-item-name">${e(formatDate(s.date) || s.date)}</span><span class="ck-muted">${e(facts)}</span></div>
        <div>${e(names || t('history.no_jobs'))}</div>
        ${s.notes ? `<div class="ck-muted">${e(s.notes)}</div>` : ''}
        <div class="ck-actions"><button class="ck-btn text danger" data-act="delete-service" data-id="${e(
          s.id,
        )}" data-k="delete-service-${e(s.id)}">${e(t('action.delete'))}</button></div></li>`;
    })
    .join('');
  const total = car.summary?.cost_total;
  return `<section class="ck-card" data-section="history"><div class="ck-card-head"><h2>${e(
    t('car.history'),
  )}</h2><span class="ck-muted">${e(t('history.total', { cost: money(total ?? 0) }))}</span></div>
    ${rows ? `<ul class="ck-list">${rows}</ul>` : `<p class="ck-muted">${e(t('history.empty'))}</p>`}</section>`;
}

function carCard(car: Rec, ui: DetailUi, applianceLink: string): string {
  if (ui.editCar) {
    return `<section class="ck-card" data-section="car"><h2>${e(t('car.edit'))}</h2><div class="ck-form" data-form="car">
      ${field('car-name', t('add.name'), car.name)}
      ${field('car-make', t('add.make'), car.make)}
      ${field('car-model', t('add.model'), car.model)}
      ${field('car-year', t('add.year'), car.year, 'number', 'min="1886" max="2200"')}
      ${select('car-fuel', t('add.fuel'), car.fuel, FUELS, 'fuel')}
      ${select('car-unit', t('add.unit'), car.unit, ['km', 'mi'], 'unit')}
      ${field('car-vin', t('car.vin'), car.vin)}
      ${field('car-plate', t('car.plate'), car.plate)}
      ${field('car-engine', t('car.engine_code'), car.engine_code)}
      ${field('car-transmission', t('car.transmission_code'), car.transmission_code)}
      ${field('car-registered', t('car.first_registered'), car.first_registered, 'date')}
      ${select('car-source', t('car.source'), car.odometer?.source ?? 'manual', ['manual', 'entity'], 'source')}
      ${field('car-entity', t('car.entity'), car.odometer?.entity_id, 'text', 'placeholder="sensor.my_car_odometer"')}
      <div class="ck-actions">
        <button class="ck-btn" data-act="car-cancel" data-k="car-cancel">${e(t('action.cancel'))}</button>
        <button class="ck-btn primary" data-act="car-save" data-k="car-save">${e(t('action.save'))}</button>
      </div></div></section>`;
  }
  const facts: [string, unknown][] = [
    [t('add.fuel'), t(`fuel.${car.fuel}`)],
    [t('car.vin'), car.vin],
    [t('car.plate'), car.plate],
    [t('car.engine_code'), car.engine_code],
    [t('car.transmission_code'), car.transmission_code],
    [t('car.first_registered'), car.first_registered],
  ];
  const list = facts
    .filter(([, v]) => v)
    .map(([k, v]) => `<div class="ck-kv"><span class="ck-muted">${e(k)}</span><span>${e(v)}</span></div>`)
    .join('');
  return `<section class="ck-card" data-section="car"><h2>${e(t('car.details'))}</h2>${list}
    <div class="ck-actions">
      ${safeLink(applianceLink) ? `<a class="ck-btn text" href="${e(applianceLink)}" data-k="appliance">${e(t('car.in_home_keeper'))}</a>` : ''}
      <button class="ck-btn text danger" data-act="delete-car" data-k="delete-car">${e(t('car.delete'))}</button>
      <button class="ck-btn" data-act="edit-car" data-k="edit-car">${e(t('action.edit'))}</button>
    </div></section>`;
}

export function detailView(state: State, carId: string, ui: DetailUi, applianceLink: string): string {
  const car = state.cars[carId];
  if (!car) {
    return `<div class="ck-empty" data-view="gone"><h2>${e(t('car.gone_title'))}</h2>
      <p>${e(t('car.gone_text'))}</p><button class="ck-btn" data-act="go" data-path="/" data-k="back">${e(
        t('action.back'),
      )}</button></div>`;
  }
  const sub = [car.make, car.model, car.year, car.plate].filter(Boolean).join(' · ');
  return `<div class="ck-head"><button class="ck-btn text" data-act="go" data-path="/" data-k="back">${e(
    t('action.back'),
  )}</button><h1>${e(car.name)}</h1>${chip(car.summary?.status ?? 'ok')}</div>
    <p class="ck-muted ck-sub">${e(sub)}</p>
    <div class="ck-columns" data-view="car">
      <div>${odometerCard(car, ui)}${itemsCard(state, car, ui)}</div>
      <div>${historyCard(state, car)}${carCard(car, ui, applianceLink)}</div>
    </div>`;
}

// ── Log service ─────────────────────────────────────────────────────────────

export function logDialog(state: State, car: Rec, form: LogForm, error: string): string {
  const jobs = itemRows(state, car.id)
    .map(
      (item) => `<label class="ck-check"><input type="checkbox" data-act="log-toggle" data-id="${e(
        item.id,
      )}" data-k="log-item-${e(item.id)}" ${form.items.includes(item.id) ? 'checked' : ''}>${e(item.name)}</label>`,
    )
    .join('');
  return `<div class="ck-modal" data-log><div class="ck-dialog" role="dialog" aria-modal="true" aria-labelledby="ck-log-title">
    <h3 id="ck-log-title">${e(t('log.title', { car: car.name }))}</h3>
    <fieldset class="ck-jobs"><legend>${e(t('log.jobs'))}</legend>${jobs || e(t('car.no_jobs'))}</fieldset>
    ${field('log-date', t('log.date'), form.date, 'date')}
    ${field('log-reading', t('log.reading', { unit: car.unit }), form.reading, 'number', 'min="0" step="0.1" inputmode="decimal"')}
    ${field('log-cost', t('log.cost'), form.cost, 'number', 'min="0" step="0.01" inputmode="decimal"')}
    ${field('log-shop', t('log.shop'), form.shop)}
    ${field('log-notes', t('log.notes'), form.notes)}
    ${error ? `<p class="ck-error" role="alert">${e(t(`log.${error}`))}</p>` : ''}
    <div class="ck-actions">
      <button class="ck-btn" data-act="log-cancel" data-k="log-cancel">${e(t('action.cancel'))}</button>
      <button class="ck-btn primary" data-act="log-save" data-k="log-save">${e(t('action.save'))}</button>
    </div></div></div>`;
}

// ── Add car ─────────────────────────────────────────────────────────────────

export function addView(state: State, form: AddForm, error: string): string {
  let body = '';
  if (form.step === 1) {
    body = `${field('add-name', t('add.name'), form.name, 'text', 'required')}
      ${field('add-make', t('add.make'), form.make)}
      ${field('add-model', t('add.model'), form.model)}
      ${field('add-year', t('add.year'), form.year, 'number', 'min="1886" max="2200"')}
      ${select('add-fuel', t('add.fuel'), form.fuel, FUELS, 'fuel')}
      ${select('add-unit', t('add.unit'), form.unit, ['km', 'mi'], 'unit')}
      ${field('add-vin', t('car.vin'), form.vin)}
      ${field('add-plate', t('car.plate'), form.plate)}`;
  } else if (form.step === 2) {
    body = `${field('add-odometer', t('car.new_reading', { unit: form.unit }), form.odometer, 'number', 'min="0" step="0.1" inputmode="decimal"')}
      <p class="ck-muted">${e(t('add.odometer_help'))}</p>`;
  } else {
    const jobs = starterJobs(state, form.fuel)
      .map(
        (job) => `<label class="ck-check"><input type="checkbox" data-act="add-toggle" data-id="${e(
          job.id,
        )}" data-k="add-job-${e(job.id)}" ${form.jobs.includes(job.id) ? 'checked' : ''}>${e(
          t(`template.${job.id}`),
        )}</label>`,
      )
      .join('');
    body = `<p class="ck-note">${e(t('car.manual_note'))}</p><fieldset class="ck-jobs"><legend>${e(
      t('add.jobs'),
    )}</legend>${jobs}</fieldset>`;
  }
  const last = form.step >= ADD_STEPS;
  return `<div class="ck-head"><button class="ck-btn text" data-act="go" data-path="/" data-k="back">${e(
    t('action.back'),
  )}</button><h1>${e(t('add.title'))}</h1></div>
    <section class="ck-card" data-view="add" data-step="${form.step}">
      <p class="ck-muted">${e(t('add.step', { step: form.step, steps: ADD_STEPS }))}</p>
      <div class="ck-form">${body}</div>
      ${error ? `<p class="ck-error" role="alert">${e(t(`add.${error}`))}</p>` : ''}
      <div class="ck-actions">
        ${form.step > 1 ? `<button class="ck-btn" data-act="add-back" data-k="add-back">${e(t('action.previous'))}</button>` : ''}
        <button class="ck-btn primary" data-act="${last ? 'add-save' : 'add-next'}" data-k="add-next">${e(
          last ? t('add.save') : t('action.next'),
        )}</button>
      </div></section>`;
}

// ── Settings ────────────────────────────────────────────────────────────────

export function settingsView(state: State): string {
  const rows = (state.starter_jobs ?? [])
    .map(
      (job) => `<tr data-job="${e(job.id)}"><td><label class="ck-check"><input type="checkbox" data-k="tpl-${e(
        job.id,
      )}-on" ${job.enabled ? 'checked' : ''}>${e(t(`template.${job.id}`))}</label></td>
      <td>${job.kind === 'date' ? '' : `<input type="number" min="1" data-k="tpl-${e(job.id)}-km" value="${e(job.km ?? '')}" aria-label="${e(t('settings.km'))}">`}</td>
      <td><input type="number" min="1" data-k="tpl-${e(job.id)}-months" value="${e(job.months ?? '')}" aria-label="${e(
        t('settings.months'),
      )}"></td></tr>`,
    )
    .join('');
  return `<div class="ck-head"><button class="ck-btn text" data-act="go" data-path="/" data-k="back">${e(
    t('action.back'),
  )}</button><h1>${e(t('settings.title'))}</h1></div>
    <section class="ck-card" data-view="settings">
      ${select('set-unit', t('settings.unit'), state.settings.unit, ['km', 'mi'], 'unit')}
      <h2>${e(t('settings.starter_jobs'))}</h2><p class="ck-note">${e(t('car.manual_note'))}</p>
      <div class="ck-table-wrap"><table class="ck-table"><thead><tr><th>${e(t('settings.job'))}</th>
        <th>${e(t('settings.km'))}</th><th>${e(t('settings.months'))}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="ck-actions"><button class="ck-btn primary" data-act="settings-save" data-k="settings-save">${e(
        t('action.save'),
      )}</button></div></section>
    ${presetsSection(state.presets ?? {})}`;
}

/** The line that says if Home Keeper holds the car presets. */
export function presetStatus(presets: Presets): string {
  const known = ['registered', 'no_service', 'failed', 'waiting'];
  // A status that this tab does not know yet shows the waiting text, not a raw key.
  const status = known.includes(presets.status ?? '') ? presets.status : 'waiting';
  if (status === 'registered') return tn('presets.status.registered', presets.preset_ids?.length ?? 0);
  if (status === 'failed') return t('presets.status.failed', { error: presets.error ?? '' });
  return t(`presets.status.${status}`);
}

/** The car integrations that have Home Keeper presets, and the tasks of each. */
export function presetsSection(presets: Presets): string {
  const rows = (presets.rows ?? [])
    .map(
      (row) => `<li data-preset="${e(row.domain)}"><span class="ck-preset-brand">${e(row.brand)}</span>
      <span class="ck-muted">${e(row.duties.map((duty) => t(`duty.${duty}`)).join(', '))}</span></li>`,
    )
    .join('');
  return `<section class="ck-card" data-section="presets">
      <h2>${e(t('presets.title'))}</h2>
      <p>${e(t('presets.intro'))}</p>
      <p class="ck-note" data-k="presets-status" data-status="${e(presets.status ?? 'waiting')}">${e(
        presetStatus(presets),
      )}</p>
      <ul class="ck-presets" aria-label="${e(t('presets.title'))}">${rows}</ul>
    </section>`;
}
