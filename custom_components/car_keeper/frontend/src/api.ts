// The websocket calls of the tab and the cards.

export interface HassConnection {
  sendMessagePromise<T>(msg: Record<string, unknown>): Promise<T>;
  subscribeMessage(cb: (msg: unknown) => void, msg: Record<string, unknown>): Promise<() => void>;
}

export interface Hass {
  language?: string;
  connection: HassConnection;
}

// The records stay loose: the reply holds each stored field, and a new field must
// not break an old tab.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Rec = Record<string, any>;

export interface State {
  cars: Record<string, Rec>;
  items: Record<string, Rec>;
  services: Record<string, Rec>;
  readings: Record<string, Rec[]>;
  settings: { unit: string; templates?: Rec };
  starter_jobs?: Rec[];
  presets?: Presets;
  tab: boolean;
  revision: number;
  today?: string;
}

/** The car presets in Home Keeper (`presets.project` on the server). */
export interface Presets {
  status?: 'registered' | 'no_service' | 'failed' | 'waiting';
  preset_ids?: string[];
  error?: string | null;
  rows?: { domain: string; brand: string; duties: string[] }[];
}

export const DOMAIN = 'car_keeper';

export function getState(hass: Hass): Promise<State> {
  return hass.connection.sendMessagePromise<State>({ type: `${DOMAIN}/get_state` });
}

/** Call `onChange` after each store change. The promise gives the unsubscribe. */
export function subscribe(hass: Hass, onChange: () => void): Promise<() => void> {
  return hass.connection.subscribeMessage(() => onChange(), { type: `${DOMAIN}/subscribe` });
}

/**
 * Call a Car Keeper service through its websocket twin. The server checks the
 * admin rule with the user of the connection. A refused call rejects with the
 * translated message of the server.
 */
export function call<T = Rec>(hass: Hass, service: string, data: Rec = {}): Promise<T> {
  return hass.connection.sendMessagePromise<T>({ type: `${DOMAIN}/${service}`, ...data });
}
