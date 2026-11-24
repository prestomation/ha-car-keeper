// The websocket calls of the tab and the cards.

export interface HassConnection {
  sendMessagePromise<T>(msg: Record<string, unknown>): Promise<T>;
  subscribeMessage(cb: (msg: unknown) => void, msg: Record<string, unknown>): Promise<() => void>;
}

export interface Hass {
  language?: string;
  connection: HassConnection;
}

export interface State {
  cars: Record<string, Record<string, unknown>>;
  items: Record<string, Record<string, unknown>>;
  services: Record<string, Record<string, unknown>>;
  documents: Record<string, Record<string, unknown>>;
  settings: { unit: string };
  tab: boolean;
  revision: number;
}

export const DOMAIN = 'car_keeper';

export function getState(hass: Hass): Promise<State> {
  return hass.connection.sendMessagePromise<State>({ type: `${DOMAIN}/get_state` });
}

/** Call `onChange` after each store change. The promise gives the unsubscribe. */
export function subscribe(hass: Hass, onChange: () => void): Promise<() => void> {
  return hass.connection.subscribeMessage(() => onChange(), { type: `${DOMAIN}/subscribe` });
}
