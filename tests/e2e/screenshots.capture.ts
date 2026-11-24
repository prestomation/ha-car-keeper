/**
 * The screenshots of the Cars tab and the cards, for docs/images/ and the PR.
 *
 *   KEEP_UP=1 NO_TESTS=1 bash ci/e2e-up.sh
 *   cd tests/e2e && SHOT_DIR=../../docs/images npx playwright test --config=screenshots.config.ts
 *
 * Desktop shots are 1280 px wide and phone shots 390 px wide (`viewports.ts`). The
 * phone shots come last, in 1 `setViewportSize(PHONE)` block, and have `-mobile` in
 * the name. A spec under tests/ asserts on each surface here.
 */
import { test, type Page } from '@playwright/test';
import { resolve } from 'node:path';
import { carsTab, noServiceWorker, openCarCard, openTab } from './tests/helpers';
import { PHONE } from './viewports';

const SHOT_DIR = resolve(__dirname, process.env.SHOT_DIR || '../../docs/images');
const DESKTOP_SHOT = { width: 1280, height: 900 };

async function shot(page: Page, name: string): Promise<void> {
  await page.mouse.move(0, 0);
  await page.waitForTimeout(600);
  await page.screenshot({ path: resolve(SHOT_DIR, `${name}.png`) });
}

/** Each surface, in the same order for the desktop and the phone. */
async function surfaces(page: Page, suffix: string): Promise<void> {
  await openTab(page);
  await shot(page, `garage-${suffix}`);
  await openTab(page, '/car/civic');
  await shot(page, `car-detail-${suffix}`);
  await openTab(page, '/car/civic/log');
  const tab = carsTab(page);
  await tab.locator('[data-k="log-item-civic-engine_oil"]').check();
  await shot(page, `log-service-${suffix}`);
  await openTab(page, '/add');
  await tab.locator('[data-k="add-name"]').fill('Fit');
  await tab.locator('[data-k="add-next"]').click();
  await tab.locator('[data-k="add-next"]').click();
  await shot(page, `add-car-${suffix}`);
  await openTab(page, '/settings');
  await shot(page, `settings-${suffix}`);
  await openCarCard(page);
  await shot(page, `cards-${suffix}`);
}

test('capture the screenshots', async ({ browser }) => {
  const context = await browser.newContext({ storageState: './.auth/state.json', deviceScaleFactor: 1 });
  await noServiceWorker(context);
  const page = await context.newPage();
  await page.setViewportSize(DESKTOP_SHOT);
  await surfaces(page, 'desktop');

  await page.setViewportSize(PHONE);
  await surfaces(page, 'mobile');
  await context.close();
});
