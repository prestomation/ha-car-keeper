// The dashboard cards. Every user can add them. The garage card shows each car with
// its odometer and its next job. The car card shows 1 car: it types a reading and
// marks a job done, and has no other control. With `max_height` (pixels) the list
// scrolls inside the card; with no `max_height` the card grows with its content.
import { call, getState, subscribe, type Hass, type State } from './api';
import { setLanguage, t } from './i18n';
import { carRows, distance, itemRows, nextItem, type Rec } from './model';
import { CARD_STYLES } from './styles';
import { escapeHTML as e } from './utils';
import { limitText } from './views';

export const GARAGE_CARD_TAG = 'car-keeper-garage-card';
export const CAR_CARD_TAG = 'car-keeper-car-card';

export interface CardConfig {
  type: string;
  title?: string;
  car_id?: string;
  max_height?: number;
}

/** The checked config of a card. A bad `max_height` throws. */
export function cleanConfig(config: CardConfig | undefined, needsCar: boolean): CardConfig {
  if (!config || typeof config !== 'object') throw new Error(t('card.invalid_config'));
  const out: CardConfig = { ...config };
  if (out.max_height !== undefined) {
    const h = Number(out.max_height);
    if (!Number.isFinite(h) || h <= 0) throw new Error(t('card.invalid_max_height'));
    out.max_height = h;
  }
  if (needsCar && !out.car_id) throw new Error(t('card.need_car'));
  return out;
}

function chip(status: string): string {
  const key = ['ok', 'soon', 'overdue'].includes(status) ? status : 'ok';
  return `<span class="ck-chip ${key}" data-status="${key}">${e(t(`status.${key}`))}</span>`;
}

abstract class BaseCard extends HTMLElement {
  protected _hass?: Hass;
  protected _config: CardConfig = { type: '' };
  protected _state?: State;
  protected _message = '';
  private _unsub?: () => void;

  set hass(hass: Hass) {
    const first = !this._hass;
    this._hass = hass;
    setLanguage(hass.language);
    if (first) void this._load(true);
  }

  getCardSize(): number {
    return 3;
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      const root = this.attachShadow({ mode: 'open' });
      root.addEventListener('click', (ev) => void this._onClick(ev));
    }
    this._render();
  }

  disconnectedCallback(): void {
    this._unsub?.();
    this._unsub = undefined;
  }

  protected async _load(withSubscribe: boolean): Promise<void> {
    if (!this._hass) return;
    try {
      this._state = await getState(this._hass);
      if (withSubscribe && !this._unsub) {
        this._unsub = await subscribe(this._hass, () => void this._load(false));
      }
    } catch (err) {
      this._message = String((err as { message?: string })?.message ?? err);
    }
    this._render();
  }

  protected _scroll(inner: string): string {
    const h = this._config.max_height;
    return h ? `<div class="ck-scroll" style="max-height:${h}px">${inner}</div>` : inner;
  }

  protected async _onClick(_ev: Event): Promise<void> {
    /* the garage card has no control */
  }

  protected abstract _body(): string;

  protected _render(): void {
    const root = this.shadowRoot;
    if (!root) return;
    const focusKey = (root.activeElement as HTMLElement | null)?.dataset?.k;
    const typed = root.querySelector<HTMLInputElement>('[data-k="odometer"]')?.value ?? '';
    root.innerHTML = `<style>${CARD_STYLES}</style><ha-card>${this._body()}</ha-card>`;
    const input = root.querySelector<HTMLInputElement>('[data-k="odometer"]');
    if (input && typed) input.value = typed;
    if (focusKey) root.querySelector<HTMLElement>(`[data-k="${focusKey}"]`)?.focus();
  }
}

export class CarKeeperGarageCard extends BaseCard {
  setConfig(config: CardConfig): void {
    this._config = cleanConfig(config, false);
    this._render();
  }

  static getStubConfig(): CardConfig {
    return { type: `custom:${GARAGE_CARD_TAG}` };
  }

  protected _body(): string {
    const title = this._config.title ?? t('card.garage_title');
    const state = this._state;
    const cars = state ? carRows(state) : [];
    const rows = cars
      .map((car) => {
        const next = state ? nextItem(state, car) : undefined;
        return `<li class="ck-row-card" data-car="${e(car.id)}"><div class="ck-line">
          <span class="ck-name">${e(car.name)}</span>${chip(car.summary?.status ?? 'ok')}</div>
          <div class="ck-muted">${e(distance(car.odometer?.value, car.unit) || t('car.no_reading'))}${
            next ? ` · ${e(next.name)}: ${e(limitText(next, car.unit))}` : ''
          }</div></li>`;
      })
      .join('');
    const body = rows
      ? this._scroll(`<ul class="ck-list">${rows}</ul>`)
      : `<div class="ck-empty">${e(t('card.no_cars'))}</div>`;
    return `<h2 class="ck-title">${e(title)}</h2>${body}`;
  }
}

export class CarKeeperCarCard extends BaseCard {
  setConfig(config: CardConfig): void {
    this._config = cleanConfig(config, true);
    this._render();
  }

  static getStubConfig(): CardConfig {
    return { type: `custom:${CAR_CARD_TAG}`, car_id: '' };
  }

  private _car(): Rec | undefined {
    return this._state?.cars[this._config.car_id ?? ''];
  }

  protected async _onClick(ev: Event): Promise<void> {
    const target = (ev.target as HTMLElement).closest<HTMLElement>('[data-act]');
    const car = this._car();
    if (!target || !car || !this._hass) return;
    try {
      if (target.dataset.act === 'odometer') {
        const raw = this.shadowRoot?.querySelector<HTMLInputElement>('[data-k="odometer"]')?.value ?? '';
        const value = Number(raw);
        if (!raw.trim() || !Number.isFinite(value) || value < 0) {
          this._message = t('car.bad_reading');
        } else {
          await call(this._hass, 'set_odometer', { car_id: car.id, value });
          const input = this.shadowRoot?.querySelector<HTMLInputElement>('[data-k="odometer"]');
          if (input) input.value = '';
          this._message = t('toast.reading_saved');
        }
      } else if (target.dataset.act === 'done') {
        await call(this._hass, 'log_service', { car_id: car.id, items: [target.dataset.id] });
        this._message = t('toast.logged');
      }
    } catch (err) {
      this._message = String((err as { message?: string })?.message ?? err);
    }
    await this._load(false);
  }

  protected _body(): string {
    const car = this._car();
    if (!this._state) return `<div class="ck-empty">${e(t('state.loading'))}</div>`;
    if (!car) return `<div class="ck-empty">${e(t('card.car_gone'))}</div>`;
    const title = this._config.title ?? car.name;
    const jobs = itemRows(this._state, car.id)
      .filter((item) => item.enabled !== false)
      .map(
        (item) => `<li class="ck-row-card" data-item="${e(item.id)}"><div class="ck-line">
          <span class="ck-name">${e(item.name)}</span>${chip(item.due?.status ?? 'ok')}</div>
          <div class="ck-line"><span class="ck-muted">${e(limitText(item, car.unit))}</span>
          <button class="ck-btn" data-act="done" data-id="${e(item.id)}" data-k="done-${e(item.id)}">${e(
            t('item.done'),
          )}</button></div></li>`,
      )
      .join('');
    return `<div class="ck-line"><h2 class="ck-title">${e(title)}</h2>${chip(car.summary?.status ?? 'ok')}</div>
      <div class="ck-big">${e(distance(car.odometer?.value, car.unit) || t('car.no_reading'))}</div>
      <div class="ck-line">
        <input data-k="odometer" type="number" min="0" step="0.1" inputmode="decimal"
          aria-label="${e(t('car.new_reading', { unit: car.unit }))}" placeholder="${e(
            t('car.new_reading', { unit: car.unit }),
          )}">
        <button class="ck-btn primary" data-act="odometer" data-k="save-odometer">${e(t('action.save'))}</button>
      </div>
      ${this._message ? `<p class="ck-muted" role="status">${e(this._message)}</p>` : ''}
      ${jobs ? this._scroll(`<ul class="ck-list">${jobs}</ul>`) : `<div class="ck-empty">${e(t('car.no_jobs'))}</div>`}`;
  }
}
