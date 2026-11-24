import { expect, odometer, openCard, openCarCard, test, trackErrors } from './helpers';

test.describe('cards', () => {
  test('the garage card shows each car @responsive', async ({ page }) => {
    const errors = trackErrors(page);
    const card = await openCard(page);
    await expect(card.locator('.ck-title')).toHaveText('Garage');
    await expect(card.locator('[data-car]')).toHaveCount(2);
    expect(errors).toEqual([]);
  });

  test('the car card scrolls inside its max_height @responsive', async ({ page }) => {
    const card = await openCarCard(page);
    await expect(card.locator('.ck-scroll')).toHaveCSS('max-height', '320px');
    await expect(card.locator('[data-item]')).not.toHaveCount(0);
  });

  test('a user who is not an admin types a reading on the car card', async ({ browser }) => {
    const before = await odometer('civic');
    const context = await browser.newContext({ storageState: './.auth/sam.json' });
    const page = await context.newPage();
    const card = await openCarCard(page);
    await card.locator('[data-k="odometer"]').fill(String(before + 5));
    await card.locator('[data-k="save-odometer"]').click();
    await expect(card.locator('[role="status"]')).toHaveText('Reading saved');
    expect(await odometer('civic')).toBe(before + 5);
    await context.close();
  });
});
