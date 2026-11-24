import { test as base, expect, type BrowserContext, type Locator, type Page } from '@playwright/test';
import { carKeeper, withWs } from '../ha-ws';

/**
 * Keep Home Assistant from installing its service worker.
 *
 * In a new browser context the worker takes control about 14 s after the first
 * load, and Home Assistant then reloads the page. A reload in the middle of a test
 * resets the tab. Playwright's `serviceWorkers: 'block'` removes
 * `navigator.serviceWorker`, which breaks the start of the Home Assistant frontend,
 * so the init script only makes `register` wait forever.
 */
export async function noServiceWorker(context: BrowserContext): Promise<void> {
  await context.addInitScript(() => {
    const sw = navigator.serviceWorker;
    if (sw) Object.defineProperty(sw, 'register', { value: () => new Promise(() => undefined) });
  });
}

/** The Playwright `test` with no Home Assistant service worker in each context. */
export const test = base.extend({
  context: async ({ context }, use) => {
    await noServiceWorker(context);
    await use(context);
  },
});

export { expect };

/** The panel URL of the Cars tab in Home Keeper. */
export const TAB_URL = '/home-keeper/cars';

/** The seeded dashboard with the cards (tests/integration/ha_config). */
export const DASHBOARD_URL = '/car-keeper-e2e/cars';

/** The tab element inside the Home Keeper panel. */
export function carsTab(page: Page): Locator {
  return page.locator('home-keeper-panel home-keeper-cars-tab');
}

/** Open a tab path (after `/home-keeper/cars`) and wait for the Car Keeper data. */
export async function openTab(page: Page, path = ''): Promise<Locator> {
  await page.goto(`${TAB_URL}${path}`, { waitUntil: 'domcontentloaded' });
  const tab = carsTab(page);
  // `data-view` is set once the Car Keeper data is there.
  await expect(tab.locator('[data-view]')).toBeVisible({ timeout: 45_000 });
  return tab;
}

/**
 * Open the seeded dashboard and wait for the garage card to show its data. On a
 * cold frontend the card element can upgrade after the dashboard renders, so the
 * helper loads the page again once if the card is not there.
 */
export async function openCard(page: Page): Promise<Locator> {
  const card = page.locator('car-keeper-garage-card');
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded' });
    try {
      await expect(card.locator('.ck-title')).toBeVisible({ timeout: 30_000 });
      return card;
    } catch (err) {
      if (attempt === 1) throw err;
    }
  }
  return card;
}

/** Open the seeded dashboard and wait for the car card of the Civic. */
export async function openCarCard(page: Page): Promise<Locator> {
  await openCard(page);
  const card = page.locator('car-keeper-car-card');
  await expect(card.locator('.ck-big')).toBeVisible({ timeout: 30_000 });
  return card;
}

/** The current odometer value of a seeded car. */
export async function odometer(carId: string): Promise<number> {
  const state = await adminState();
  return Number(state.cars[carId].odometer.value);
}

/** The whole `get_state` reply as Alex. */
export function adminState(): Promise<Record<string, any>> {
  return carKeeper('get_state');
}

/** The whole `get_state` reply as Sam, who is not an admin. */
export function userState(): Promise<Record<string, any>> {
  return withWs('user', (ws) => ws.call({ type: 'car_keeper/get_state' }));
}

/** Collect the uncaught page errors and the console errors of the Car Keeper code. */
export function trackErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error' && /car[-_]keeper|ck-/i.test(msg.text())) errors.push(msg.text());
  });
  return errors;
}
