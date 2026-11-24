import { type Page } from '@playwright/test';
import { auditOutlines } from '../outline-audit';
import { carsTab, expect, openCard, test } from './helpers';

/**
 * Every outline is whole, as in Home Keeper.
 *
 * A border, a ring or an outline of a control must show all of it, on every view, at
 * the desktop and the phone width. `outline-audit.ts` finds a control that an ancestor
 * clips, and a border with a gap. Each view below is opened by a URL and a few clicks,
 * then audited. A view that fails names the control and the box that cuts it.
 *
 * Add the view to `VIEWS` when you add a surface that has bordered controls. A control
 * that is cut on purpose carries `data-ck-cut`.
 */
type View = {
  name: string;
  url: string;
  /** What shows that the view is ready. Defaults to the tab. */
  ready?: (page: Page) => Promise<void>;
  /** Open a dialog, a menu or a state. */
  before?: (page: Page) => Promise<void>;
  /** Put back what `before` changed. */
  after?: (page: Page) => Promise<void>;
};

const tabReady = async (page: Page): Promise<void> => {
  await expect(carsTab(page).locator('[data-view]')).toBeVisible({ timeout: 45_000 });
};

const VIEWS: View[] = [
  { name: 'Garage', url: '/home-keeper/cars' },
  {
    name: 'Garage card',
    url: '/car-keeper-e2e/cars',
    ready: async (page) => {
      await openCard(page);
    },
  },
];

test.describe('Car Keeper: outlines are whole', () => {
  for (const view of VIEWS) {
    test(`${view.name} @responsive`, async ({ page }) => {
      await page.goto(view.url, { waitUntil: 'domcontentloaded' });
      await (view.ready ?? tabReady)(page);
      try {
        if (view.before) await view.before(page);
        expect(await auditOutlines(page), 'controls with a cut or open outline').toEqual([]);
      } finally {
        if (view.after) await view.after(page);
      }
    });
  }
});
