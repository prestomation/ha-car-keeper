import { carsTab, expect, openTab, test, trackErrors, userState } from './helpers';

test.describe('Cars tab', () => {
  test('opens in the Home Keeper panel and shows the empty garage @responsive', async ({ page }) => {
    const errors = trackErrors(page);
    const tab = await openTab(page);
    await expect(tab.locator('.ck-empty h2')).toHaveText('No cars');
    expect(errors).toEqual([]);
  });

  test('an unknown path opens the garage', async ({ page }) => {
    const tab = await openTab(page, '/nope');
    await expect(tab.locator('[data-view="garage"]')).toBeVisible();
  });

  test('a user who is not an admin reads the same state', async () => {
    const state = await userState();
    expect(state.tab).toBe(true);
    expect(state.settings).toEqual({ unit: 'km' });
  });

  test('the tab element is the only Car Keeper element in the panel', async ({ page }) => {
    await openTab(page);
    await expect(carsTab(page)).toHaveCount(1);
  });
});
