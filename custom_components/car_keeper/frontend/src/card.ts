// The garage card: 1 row for each car. Every user can add it to a dashboard.
import { getState, subscribe, type Hass, type State } from './api';
import { setLanguage, t } from './i18n';
import { CARD_STYLES } from './styles';
import { escapeHTML } from './utils';

export const GARAGE_CARD_TAG = 'car-keeper-garage-card';

export interface GarageCardConfig {
  type: string;
  title?: string;
}

export class CarKeeperGarageCard extends HTMLElement {
  private _hass?: Hass;
  private _config: GarageCardConfig = { type: `custom:${GARAGE_CARD_TAG}` };
  private _state?: State;
  private _unsub?: () => void;

  setConfig(config: GarageCardConfig): void {
    if (!config) throw new Error(t('card.invalid_config'));
    this._config = { ...config };
    this._render();
  }

  set hass(hass: Hass) {
    const first = !this._hass;
    this._hass = hass;
    setLanguage(hass.language);
    if (first) void this._load(true);
  }

  getCardSize(): number {
    return 2;
  }

  static getStubConfig(): GarageCardConfig {
    return { type: `custom:${GARAGE_CARD_TAG}` };
  }

  connectedCallback(): void {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._render();
  }

  disconnectedCallback(): void {
    this._unsub?.();
    this._unsub = undefined;
  }

  private async _load(withSubscribe: boolean): Promise<void> {
    if (!this._hass) return;
    this._state = await getState(this._hass);
    if (withSubscribe && !this._unsub) {
      this._unsub = await subscribe(this._hass, () => void this._load(false));
    }
    this._render();
  }

  private _render(): void {
    const root = this.shadowRoot;
    if (!root) return;
    const title = this._config.title ?? t('card.garage_title');
    const cars = this._state ? Object.keys(this._state.cars).length : 0;
    const body = cars === 0 ? `<div class="ck-empty">${escapeHTML(t('card.no_cars'))}</div>` : '';
    root.innerHTML = `<style>${CARD_STYLES}</style><ha-card>
      <h2 class="ck-title">${escapeHTML(title)}</h2>${body}</ha-card>`;
  }
}
