// Pure helpers of the tab and the cards. Nothing here reads the DOM, so the unit
// tests and the mutation gate cover each function.

/** Escape text for `innerHTML`. Every user value goes through this function. */
export function escapeHTML(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** The views of the tab. */
export type View = 'garage' | 'car' | 'add' | 'settings';

export interface Route {
  view: View;
  /** The car of the `car` view. */
  id: string;
  /** The Log service dialog of the car is open (`/car/<id>/log`). */
  log: boolean;
  params: Record<string, string>;
}

function readParams(pairs: string[]): Record<string, string> {
  const params: Record<string, string> = {};
  for (const pair of pairs) {
    const at = pair.indexOf('=');
    if (at <= 0) continue;
    params[decodeURIComponent(pair.slice(0, at))] = decodeURIComponent(pair.slice(at + 1));
  }
  return params;
}

/**
 * Read the tab path: "", "/add", "/settings", "/car/<id>" or "/car/<id>/log".
 * The filters of a view are `;key=value` parameters on the last segment, because
 * the Home Keeper host gives the tab only the path. An unknown path opens the
 * garage.
 */
export function parseRoute(path: string): Route {
  const clean = (path || '').split('?')[0].replace(/^\/+|\/+$/g, '');
  const [segments, ...pairs] = clean.split(';');
  const parts = segments.split('/').filter(Boolean).map(decodeURIComponent);
  const params = readParams(pairs);
  const route: Route = { view: 'garage', id: '', log: false, params };
  if (parts[0] === 'car' && parts[1] && parts.length <= 3) {
    route.view = 'car';
    route.id = parts[1];
    route.log = parts[2] === 'log';
  } else if (parts.length === 1 && (parts[0] === 'add' || parts[0] === 'settings')) {
    route.view = parts[0];
  }
  return route;
}

/** Build the tab path of a route. A parameter with no value is left out. */
export function buildPath(route: Route): string {
  const pairs = Object.keys(route.params)
    .sort()
    .filter((key) => route.params[key] !== '')
    .map((key) => `;${encodeURIComponent(key)}=${encodeURIComponent(route.params[key])}`)
    .join('');
  if (route.view === 'car') {
    return `/car/${encodeURIComponent(route.id)}${route.log ? '/log' : ''}${pairs}`;
  }
  if (route.view === 'garage') return `/${pairs}`;
  return `/${route.view}${pairs}`;
}

/** A route with no parameters. */
export function routeTo(view: View, id = '', log = false): Route {
  return { view, id, log, params: {} };
}
