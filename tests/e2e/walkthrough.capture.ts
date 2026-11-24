/**
 * The video walkthrough of the Cars tab, for the PR comment (not committed).
 *
 *   KEEP_UP=1 NO_TESTS=1 bash ci/e2e-up.sh
 *   bash ci/capture-video.sh        # writes docs/videos/walkthrough.{webm,mp4,gif}
 *
 * The tour: open the Cars tab in Home Keeper, see the garage, and open the garage
 * card on a dashboard. `BEAT` pauses let each step read in the video.
 *
 * The recording needs its own context: `recordVideo` is set when a context is made.
 */
import { test, type Page } from '@playwright/test';
import { resolve } from 'node:path';
import { noServiceWorker, openCard, openTab } from './tests/helpers';
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
    // 2. The garage card on a dashboard.
    await openCard(page);
    await beat(page, 2);
  } finally {
    const video = page.video();
    await context.close();
    if (video) await video.saveAs(resolve(OUT, 'walkthrough.webm'));
  }
});
