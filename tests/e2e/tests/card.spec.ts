import { expect, openCard, test, trackErrors } from './helpers';

test.describe('garage card', () => {
  test('shows its title and the empty state @responsive', async ({ page }) => {
    const errors = trackErrors(page);
    const card = await openCard(page);
    await expect(card.locator('.ck-title')).toHaveText('Garage');
    await expect(card.locator('.ck-empty')).toHaveText('No cars');
    expect(errors).toEqual([]);
  });

  test('works for a user who is not an admin', async ({ browser }) => {
    const context = await browser.newContext({ storageState: './.auth/sam.json' });
    const page = await context.newPage();
    const card = await openCard(page);
    await expect(card.locator('.ck-empty')).toHaveText('No cars');
    await context.close();
  });
});
