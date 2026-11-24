// The Cars tab of the Home Keeper panel. The panel sets `hass`, `narrow`, `route`
// and `host`. The tab moves only with `host.navigate`.
import { getState, subscribe, type Hass, type State } from './api';
import { setLanguage, t } from './i18n';
import { TAB_STYLES } from './styles';
import { escapeHTML, parseRoute, type Route } from './utils';

interface Host {
  apiVersion: number;
  navigate(path: string, opts?: { replace?: boolean }): void;
  showToast(text: string): void;
}

export class HomeKeeperCarsTab extends HTMLElement {
  private _hass?: Hass;
  private _route: Route = parseRoute('');
  private _state?: State;
  private _error = '';
  private _unsub?: () => void;
  host?: Host;
  narrow = false;

  set hass(hass: Hass) {
    const first = !this._hass;
    this._hass = hass;
    setLanguage(hass.language);
    if (first) void this._load(true);
  }

  set route(route: { path: string }) {
    this._route = parseRoute(route?.path ?? '');
    this._render();
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
    try {
      this._state = await getState(this._hass);
      this._error = '';
      if (withSubscribe && !this._unsub) {
        this._unsub = await subscribe(this._hass, () => void this._load(false));
      }
    } catch (err) {
      this._error = String((err as { message?: string })?.message ?? err);
    }
    this._render();
  }

  private _render(): void {
    const root = this.shadowRoot;
    if (!root) return;
    let body: string;
    if (this._error) {
      body = `<div class="ck-empty" role="alert"><h2>${escapeHTML(t('error.title'))}</h2>
        <p>${escapeHTML(this._error)}</p></div>`;
    } else if (!this._state) {
      body = `<div class="ck-empty">${escapeHTML(t('state.loading'))}</div>`;
    } else if (Object.keys(this._state.cars).length === 0) {
      body = `<div class="ck-empty" data-view="${this._route.view}"><h2>${escapeHTML(
        t('garage.empty_title'),
      )}</h2><p>${escapeHTML(t('garage.empty_text'))}</p></div>`;
    } else {
      body = `<div data-view="${this._route.view}"></div>`;
    }
    root.innerHTML = `<style>${TAB_STYLES}</style><div class="ck-page">${body}</div>`;
  }
}
