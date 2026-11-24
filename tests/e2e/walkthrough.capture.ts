/**
 * The video walkthrough of the Cars tab, for the PR comment (not committed).
 *
 *   KEEP_UP=1 NO_TESTS=1 bash ci/e2e-up.sh
 *   bash ci/capture-video.sh        # writes docs/videos/walkthrough.{webm,mp4,gif}
 *
 * The tour: open the Cars tab in Home Keeper, see the garage, open a car, type a
 * reading, log a service, see the Home Keeper presets in the settings, look at Add car,
 * and open the cards on a dashboard. `BEAT` pauses let each step read in the video.
 *
 * The recording needs its own context: `recordVideo` is set when a context is made.
 */
import { test, type Page } from '@playwright/test';
import { resolve } from 'node:path';
import { carsTab, noServiceWorker, odometer, openCarCard, openTab } from './tests/helpers';
import { DESKTOP } from './viewports';

const OUT = process.env.VIDEO_DIR || '/tmp/car-keeper-video';
const BEAT = 900;

async function beat(page: Page, n = 1): Promise<void> {
  await page.waitForTimeout(BEAT * n);
}

test('record the Car Keeper walkthrough', async ({ browser }) => {
  const context = await browser.newContext({
    storageState: './.auth/state.json',
    viewport: DESKTOP,
    recordVideo: { dir: OUT, size: DESKTOP },
  });
  await noServiceWorker(context);
  const page = await context.newPage();

  try {
    // 1. The garage in the Cars tab of Home Keeper.
    await openTab(page);
    await beat(page, 2);
    // 2. A car: its odometer, its jobs and its history.
    const tab = carsTab(page);
    await tab.locator('[data-car="civic"]').click();
    await beat(page, 2);
    // 3. Type a new reading.
    await tab.locator('[data-k="odometer"]').fill(String((await odometer('civic')) + 300));
    await beat(page);
    await tab.locator('[data-k="save-odometer"]').click();
    await beat(page, 2);
    // 4. Log a service for 2 jobs.
    await tab.locator('[data-k="done-civic-tyre_rotation"]').click();
    await tab.locator('[data-k="log-item-civic-engine_oil"]').check();
    await tab.locator('[data-k="log-cost"]').fill('95');
    await tab.locator('[data-k="log-shop"]').fill('Main Street Garage');
    await beat(page, 2);
    await tab.locator('[data-k="log-save"]').click();
    await beat(page, 2);
    // 5. Add car offers the starter jobs of the fuel type.
    await openTab(page, '/settings');
    await tab.locator('[data-view="presets"]').evaluate((el) => el.scrollIntoView({ block: 'start', behavior: 'smooth' }));
    await beat(page, 2);

    await openTab(page, '/add');
    await tab.locator('[data-k="add-name"]').fill('Fit');
    await tab.locator('[data-k="add-next"]').click();
    await tab.locator('[data-k="add-next"]').click();
    await beat(page, 2);
    // 6. The garage card and the car card on a dashboard.
    await openCarCard(page);
    await beat(page, 2);
  } finally {
    const video = page.video();
    await context.close();
    if (video) await video.saveAs(resolve(OUT, 'walkthrough.webm'));
  }
});
