// The Cars tab of the Home Keeper panel. The panel sets `hass`, `narrow`, `route`
// and `host`. The tab moves only with `host.navigate`. The `route` setter is the
// only place that changes the view.
import { call, getState, subscribe, type Hass, type State } from './api';
import { confirmDestructive } from './dialog';
import { formatDate, setLanguage, t } from './i18n';
import {
  addData,
  addError,
  addReduce,
  addStart,
  logData,
  logError,
  logReduce,
  logStart,
  starterJobs,
  type AddForm,
  type LogForm,
  type Rec,
} from './model';
import { TAB_STYLES } from './styles';
import { addView, detailView, garageView, logDialog, settingsView, type DetailUi } from './views';
import { buildPath, escapeHTML, parseRoute, routeTo, type Route } from './utils';

interface Host {
  apiVersion: number;
  navigate(path: string, opts?: { replace?: boolean }): void;
  showToast(text: string): void;
  applianceLink?(assetId: string): string;
}

function emptyUi(): DetailUi {
  return { odometer: '', odometerError: '', editCar: false, editItem: '', addItem: false };
}

function errorText(err: unknown): string {
  return String((err as { message?: string })?.message ?? err);
}

export class HomeKeeperCarsTab extends HTMLElement {
  private _hass?: Hass;
  private _route: Route = parseRoute('');
  private _state?: State;
  private _error = '';
  private _unsub?: () => void;
  private _ui: DetailUi = emptyUi();
  private _log?: LogForm;
  private _logError = '';
  private _add?: AddForm;
  private _addError = '';
  host?: Host;
  narrow = false;

  set hass(hass: Hass) {
    const first = !this._hass;
    this._hass = hass;
    setLanguage(hass.language);
    if (first) void this._load(true);
  }

  set route(route: { path: string }) {
    const next = parseRoute(route?.path ?? '');
    if (next.view !== this._route.view || next.id !== this._route.id) this._ui = emptyUi();
    if (!next.log) this._log = undefined;
    if (next.view !== 'add') this._add = undefined;
    this._route = next;
    this._render();
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      const root = this.attachShadow({ mode: 'open' });
      root.addEventListener('click', (ev) => this._onClick(ev));
      root.addEventListener('input', (ev) => this._onInput(ev));
      root.addEventListener('change', (ev) => this._onInput(ev));
    }
    this._render();
  }

  disconnectedCallback(): void {
    this._unsub?.();
    this._unsub = undefined;
  }

  private async _load(withSubscribe: boolean): Promise<void> {
    if (!this._hass) return;
    try {
      this._state = await getState(this._hass);
      this._error = '';
      if (withSubscribe && !this._unsub) {
        this._unsub = await subscribe(this._hass, () => void this._load(false));
      }
    } catch (err) {
      this._error = errorText(err);
    }
    this._render();
  }

  private _go(route: Route, replace = false): void {
    this.host?.navigate(buildPath(route), { replace });
  }

  private async _run(service: string, data: Rec, done?: string): Promise<Rec | undefined> {
    if (!this._hass) return undefined;
    try {
      const reply = await call(this._hass, service, data);
      if (done) this.host?.showToast(done);
      await this._load(false);
      return reply ?? {};
    } catch (err) {
      this.host?.showToast(errorText(err));
      return undefined;
    }
  }

  private _value(key: string): string {
    const el = this.shadowRoot?.querySelector<HTMLInputElement>(`[data-k="${key}"]`);
    return el ? el.value.trim() : '';
  }

  private _checked(key: string): boolean {
    return Boolean(this.shadowRoot?.querySelector<HTMLInputElement>(`[data-k="${key}"]`)?.checked);
  }

  private _onInput(ev: Event): void {
    const el = ev.target as HTMLInputElement;
    const key = el.dataset?.k ?? '';
    if (key === 'odometer') this._ui.odometer = el.value;
    if (key.startsWith('log-') && this._log && el.type !== 'checkbox') {
      const fieldName = key.slice(4) as 'date' | 'reading' | 'cost' | 'shop' | 'notes';
      this._log = logReduce(this._log, { type: 'set', field: fieldName, value: el.value });
    }
    if (key.startsWith('add-') && this._add && el.type !== 'checkbox') {
      const fieldName = key.slice(4) as Exclude<keyof AddForm, 'step' | 'jobs'>;
      this._add = addReduce(this._add, { type: 'set', field: fieldName, value: el.value });
      if (fieldName === 'fuel' && this._state) {
        this._add = addReduce(this._add, {
          type: 'jobs',
          ids: starterJobs(this._state, el.value).map((j) => j.id),
        });
      }
      if (ev.type === 'change' && (fieldName === 'fuel' || fieldName === 'unit')) this._render();
    }
  }

  private _onClick(ev: Event): void {
    const target = (ev.target as HTMLElement).closest<HTMLElement>('[data-act]');
    if (!target || !this._state) return;
    const act = target.dataset.act ?? '';
    const id = target.dataset.id ?? '';
    const car = this._state.cars[this._route.id];
    switch (act) {
      case 'go':
        this._go(parseRoute(target.dataset.path ?? '/'));
        return;
      case 'odometer':
        void this._saveOdometer();
        return;
      case 'log':
        this._log = logStart(id ? [id] : [], this._state.today ?? '', car?.odometer?.value ?? null);
        this._logError = '';
        this._go(routeTo('car', this._route.id, true));
        return;
      case 'log-toggle':
        if (this._log) this._log = logReduce(this._log, { type: 'toggle', id });
        return;
      case 'log-cancel':
        this._go(routeTo('car', this._route.id), true);
        return;
      case 'log-save':
        void this._saveLog();
        return;
      case 'edit-car':
        this._ui.editCar = true;
        break;
      case 'car-cancel':
        this._ui.editCar = false;
        break;
      case 'car-save':
        void this._saveCar();
        return;
      case 'add-item':
        this._ui.addItem = true;
        this._ui.editItem = '';
        break;
      case 'edit-item':
        this._ui.editItem = id;
        this._ui.addItem = false;
        break;
      case 'item-cancel':
        this._ui.editItem = '';
        this._ui.addItem = false;
        break;
      case 'item-save':
        void this._saveItem(id);
        return;
      case 'delete-item':
        this._confirmDelete('item', id);
        return;
      case 'delete-service':
        this._confirmDelete('service', id);
        return;
      case 'delete-car':
        this._confirmDelete('car', this._route.id);
        return;
      case 'add-next':
      case 'add-back':
        if (this._add) {
          this._add = addReduce(this._add, { type: act === 'add-next' ? 'next' : 'back' });
          this._addError = act === 'add-next' ? addError(this._add) : '';
        }
        break;
      case 'add-toggle':
        if (this._add) this._add = addReduce(this._add, { type: 'toggle', id });
        return;
      case 'add-save':
        void this._saveAdd();
        return;
      case 'settings-save':
        void this._saveSettings();
        return;
      default:
        return;
    }
    this._render();
  }

  private _confirmDelete(kind: 'car' | 'item' | 'service', id: string): void {
    const root = this.shadowRoot;
    const state = this._state;
    if (!root || !state) return;
    if (kind === 'car') {
      const car = state.cars[id];
      confirmDestructive(root, {
        title: t('confirm.car_title', { name: car?.name ?? '' }),
        text: t('confirm.car_text'),
        onConfirm: async () => {
          if (await this._run('delete_car', { car_id: id }, t('toast.car_deleted'))) {
            this._go(routeTo('garage'), true);
          }
        },
      });
    } else if (kind === 'item') {
      confirmDestructive(root, {
        title: t('confirm.item_title', { name: state.items[id]?.name ?? '' }),
        text: t('confirm.item_text'),
        onConfirm: () => void this._run('delete_item', { item_id: id }, t('toast.deleted')),
      });
    } else {
      confirmDestructive(root, {
        title: t('confirm.service_title', { date: formatDate(state.services[id]?.date) }),
        text: t('confirm.service_text'),
        onConfirm: () => void this._run('delete_service', { service_id: id }, t('toast.deleted')),
      });
    }
  }

  private async _saveOdometer(): Promise<void> {
    const value = Number(this._ui.odometer);
    if (!this._ui.odometer.trim() || !Number.isFinite(value) || value < 0) {
      this._ui.odometerError = t('car.bad_reading');
      this._render();
      return;
    }
    try {
      await call(this._hass!, 'set_odometer', { car_id: this._route.id, value });
      this._ui.odometer = '';
      this._ui.odometerError = '';
      this.host?.showToast(t('toast.reading_saved'));
      await this._load(false);
    } catch (err) {
      this._ui.odometerError = errorText(err);
      this._render();
    }
  }

  private async _saveLog(): Promise<void> {
    if (!this._log) return;
    this._logError = logError(this._log);
    if (this._logError) {
      this._render();
      return;
    }
    if (await this._run('log_service', logData(this._log, this._route.id), t('toast.logged'))) {
      this._go(routeTo('car', this._route.id), true);
    }
  }

  private async _saveCar(): Promise<void> {
    const year = this._value('car-year');
    const data: Rec = {
      car_id: this._route.id,
      name: this._value('car-name'),
      make: this._value('car-make'),
      model: this._value('car-model'),
      year: year ? Number(year) : null,
      fuel: this._value('car-fuel'),
      unit: this._value('car-unit'),
      vin: this._value('car-vin'),
      plate: this._value('car-plate'),
      engine_code: this._value('car-engine'),
      transmission_code: this._value('car-transmission'),
      first_registered: this._value('car-registered') || null,
      odometer_source: this._value('car-source'),
    };
    const entity = this._value('car-entity');
    if (data.odometer_source === 'entity' || entity) data.odometer_entity_id = entity || null;
    if (await this._run('update_car', data, t('toast.saved'))) {
      this._ui.editCar = false;
      this._render();
    }
  }

  private async _saveItem(id: string): Promise<void> {
    const key = id ? `item-${id}` : 'item-new';
    const distance = this._value(`${key}-distance`);
    const months = this._value(`${key}-months`);
    const data: Rec = {
      name: this._value(`${key}-name`),
      interval_distance: distance ? Number(distance) : null,
      interval_months: months ? Number(months) : null,
      notes: this._value(`${key}-notes`),
      add_task: this._checked(`${key}-task`),
      enabled: this._checked(`${key}-enabled`),
    };
    const reply = id
      ? await this._run('update_item', { item_id: id, ...data }, t('toast.saved'))
      : await this._run('add_item', { car_id: this._route.id, ...data }, t('toast.saved'));
    if (reply) {
      this._ui.editItem = '';
      this._ui.addItem = false;
      this._render();
    }
  }

  private async _saveAdd(): Promise<void> {
    if (!this._add) return;
    this._addError = addError(this._add);
    if (this._addError) {
      this._render();
      return;
    }
    const reply = await this._run('add_car', addData(this._add), t('toast.car_added'));
    const carId = (reply?.car as Rec | undefined)?.id;
    if (carId) this._go(routeTo('car', String(carId)), true);
  }

  private async _saveSettings(): Promise<void> {
    const templates: Rec = {};
    for (const job of this._state?.starter_jobs ?? []) {
      const km = this._value(`tpl-${job.id}-km`);
      const months = this._value(`tpl-${job.id}-months`);
      const override: Rec = { enabled: this._checked(`tpl-${job.id}-on`) };
      if (job.kind !== 'date') override.km = km ? Number(km) : null;
      override.months = months ? Number(months) : null;
      templates[job.id] = override;
    }
    await this._run('set_settings', { unit: this._value('set-unit'), templates }, t('toast.saved'));
  }

  private _render(): void {
    const root = this.shadowRoot;
    if (!root) return;
    // Keep the focus, the caret and the scroll of the control that has them.
    const active = root.activeElement as HTMLInputElement | null;
    const focusKey = active?.dataset?.k;
    let caret: number | null = null;
    try {
      caret = active?.selectionStart ?? null;
    } catch {
      caret = null;
    }
    // An open question stays open when a store change renders the view again.
    const confirm = root.querySelector('.ck-modal[data-confirm]');
    root.innerHTML = `<style>${TAB_STYLES}</style><div class="ck-page ${this.narrow ? 'narrow' : ''}">${this._body()}</div>`;
    if (confirm) root.appendChild(confirm);
    if (focusKey) {
      const el = root.querySelector<HTMLInputElement>(`[data-k="${focusKey}"]`);
      el?.focus();
      try {
        if (caret != null) el?.setSelectionRange(caret, caret);
      } catch {
        /* a number input has no caret */
      }
    }
  }

  private _body(): string {
    if (this._error) {
      return `<div class="ck-empty" role="alert"><h2>${escapeHTML(t('error.title'))}</h2>
        <p>${escapeHTML(this._error)}</p></div>`;
    }
    const state = this._state;
    if (!state) return `<div class="ck-empty">${escapeHTML(t('state.loading'))}</div>`;
    const route = this._route;
    if (route.view === 'add') {
      if (!this._add) {
        this._add = addStart(
          state.settings.unit,
          starterJobs(state, 'petrol').map((j) => j.id),
        );
      }
      return addView(state, this._add, this._addError);
    }
    if (route.view === 'settings') return settingsView(state);
    if (route.view === 'car') {
      const car = state.cars[route.id];
      const asset = car?.hk_asset_id ? String(car.hk_asset_id) : '';
      const link = asset && this.host?.applianceLink ? this.host.applianceLink(asset) : '';
      let html = detailView(state, route.id, this._ui, link);
      if (car && route.log) {
        if (!this._log) this._log = logStart([], state.today ?? '', car.odometer?.value ?? null);
        html += logDialog(state, car, this._log, this._logError);
      }
      return html;
    }
    return garageView(state);
  }
}
