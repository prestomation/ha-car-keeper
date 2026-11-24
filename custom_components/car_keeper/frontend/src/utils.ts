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
export type View = 'garage' | 'settings';

export interface Route {
  view: View;
  params: Record<string, string>;
}

const VIEWS: readonly View[] = ['garage', 'settings'];

/**
 * Read the tab path ("" or "/settings;key=value"). The filters of a view are
 * `;key=value` parameters on the last segment, because the Home Keeper host
 * gives the tab only the path. An unknown path opens the garage.
 */
export function parseRoute(path: string): Route {
  const clean = (path || '').split('?')[0].replace(/^\/+|\/+$/g, '');
  const [head, ...pairs] = clean.split(';');
  const params: Record<string, string> = {};
  for (const pair of pairs) {
    const at = pair.indexOf('=');
    if (at <= 0) continue;
    params[decodeURIComponent(pair.slice(0, at))] = decodeURIComponent(pair.slice(at + 1));
  }
  const view = (VIEWS as readonly string[]).includes(head) ? (head as View) : 'garage';
  return { view, params };
}

/** Build the tab path of a route. A parameter with no value is left out. */
export function buildPath(route: Route): string {
  const pairs = Object.keys(route.params)
    .sort()
    .filter((key) => route.params[key] !== '')
    .map((key) => `;${encodeURIComponent(key)}=${encodeURIComponent(route.params[key])}`);
  return `/${route.view}${pairs.join('')}`;
}
