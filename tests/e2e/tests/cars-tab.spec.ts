import { carKeeper } from '../ha-ws';
import { adminState, carsTab, expect, odometer, openTab, test, trackErrors, userState } from './helpers';

test.describe('Cars tab', () => {
  test('shows the garage with each car and its status @responsive', async ({ page }) => {
    const errors = trackErrors(page);
    const tab = await openTab(page);
    await expect(tab.locator('.ck-car')).toHaveCount(2);
    await expect(tab.locator('[data-car="civic"] .ck-car-name')).toHaveText('Civic');
    await expect(tab.locator('[data-car="model3"] .ck-chip')).toHaveAttribute('data-status', 'overdue');
    expect(errors).toEqual([]);
  });

  test('an unknown path opens the garage', async ({ page }) => {
    const tab = await openTab(page, '/nope');
    await expect(tab.locator('[data-view="garage"]')).toBeVisible();
  });

  test('opens a car, and Back goes to the garage', async ({ page }) => {
    const tab = await openTab(page);
    await tab.locator('[data-car="civic"]').click();
    await expect(page).toHaveURL(/\/home-keeper\/cars\/car\/civic$/);
    await expect(tab.locator('h1')).toHaveText('Civic');
    await expect(tab.locator('[data-section="history"]')).toContainText('Main Street Garage');
    await tab.locator('[data-k="back"]').first().click();
    await expect(tab.locator('[data-view="garage"]')).toBeVisible();
  });

  test('saves a typed reading, and refuses a lower one @responsive', async ({ page }) => {
    const before = await odometer('civic');
    const tab = await openTab(page, '/car/civic');
    await tab.locator('[data-k="odometer"]').fill(String(before - 100));
    await tab.locator('[data-k="save-odometer"]').click();
    await expect(tab.locator('.ck-error')).toBeVisible();
    await tab.locator('[data-k="odometer"]').fill(String(before + 25));
    await tab.locator('[data-k="save-odometer"]').click();
    await expect(tab.locator('[data-section="odometer"] .ck-big')).toContainText(
      (before + 25).toLocaleString('en-US'),
    );
    expect(await odometer('civic')).toBe(before + 25);
  });

  test('logs a service with 2 jobs, and the delete asks first', async ({ page }) => {
    const tab = await openTab(page, '/car/civic');
    await tab.locator('[data-k="done-civic-tyre_rotation"]').click();
    await expect(page).toHaveURL(/\/car\/civic\/log$/);
    await tab.locator('[data-k="log-item-civic-engine_oil"]').check();
    await tab.locator('[data-k="log-cost"]').fill('61');
    await tab.locator('[data-k="log-shop"]').fill('E2E Shop');
    await tab.locator('[data-k="log-save"]').click();
    await expect(tab.locator('[data-log]')).toHaveCount(0);
    await expect(tab.locator('[data-section="history"]')).toContainText('E2E Shop');
    const state = await adminState();
    const logged = Object.values<Record<string, any>>(state.services).find((s) => s.shop === 'E2E Shop')!;
    expect(logged.items.sort()).toEqual(['civic-engine_oil', 'civic-tyre_rotation']);
    await tab.locator(`[data-k="delete-service-${logged.id}"]`).click();
    await expect(tab.locator('[data-confirm]')).toBeVisible();
    await tab.locator('[data-confirm-act="ok"]').click();
    await expect(tab.locator('[data-section="history"]')).not.toContainText('E2E Shop');
  });

  test('adds a car in 3 steps and deletes it after a question', async ({ page }) => {
    const tab = await openTab(page, '/add');
    await tab.locator('[data-k="add-name"]').fill('E2E Fit');
    await tab.locator('[data-k="add-next"]').click();
    await tab.locator('[data-k="add-odometer"]').fill('1000');
    await tab.locator('[data-k="add-next"]').click();
    await expect(tab.locator('[data-k="add-job-engine_oil"]')).toBeChecked();
    await tab.locator('[data-k="add-next"]').click();
    await expect(tab.locator('h1')).toHaveText('E2E Fit');
    await expect(tab.locator('[data-item]')).not.toHaveCount(0);
    await tab.locator('[data-k="delete-car"]').click();
    await tab.locator('[data-confirm-act="ok"]').click();
    await expect(tab.locator('[data-view="garage"]')).toBeVisible();
    await expect(tab.locator('.ck-car')).toHaveCount(2);
  });

  test('shows the settings with the starter jobs', async ({ page }) => {
    const tab = await openTab(page, '/settings');
    await expect(tab.locator('[data-job="timing_belt"]')).toBeVisible();
  });

  test('lists the car presets and their status in Home Keeper', async ({ page }) => {
    const tab = await openTab(page, '/settings');
    const section = tab.locator('[data-section="presets"]');
    await expect(section.locator('[data-preset="volvo"]')).toContainText('Volvo Cars');
    const status = section.locator('[data-k="presets-status"]');
    // The lanes with the Home Keeper presets pin (CK_EXPECT_PRESETS=1) must register.
    const word = process.env.CK_EXPECT_PRESETS === '1' ? 'registered' : /registered|no_service/;
    await expect(status).toHaveAttribute('data-status', word);
    const state = await userState();
    if (state.presets.status === 'registered') {
      await expect(status).toHaveText(`${state.presets.preset_ids.length} presets are in Home Keeper.`);
      const picker = await import('../ha-ws').then(({ withWs }) =>
        withWs('admin', (ws) =>
          ws.call<{ presets: { id: string }[] }>({ type: 'home_keeper/list_declarative_presets' }),
        ),
      );
      const ours = picker.presets.filter((p) => p.id.startsWith('car_keeper/'));
      expect(ours.map((p) => p.id)).toEqual(state.presets.preset_ids);
    }
  });

  test('a user who is not an admin reads the same state', async () => {
    const state = await userState();
    const admin = await adminState();
    expect(state.tab).toBe(true);
    expect(state.settings).toEqual({ unit: 'km', templates: {} });
    expect(state.cars.civic.vin).toBe(admin.cars.civic.vin);
    expect(Object.keys(state.cars.civic).sort()).toEqual(Object.keys(admin.cars.civic).sort());
  });

  test('a user who is not an admin cannot delete a car', async () => {
    await expect(
      import('../ha-ws').then(({ withWs }) =>
        withWs('user', (ws) => ws.call({ type: 'car_keeper/delete_car', car_id: 'civic' })),
      ),
    ).rejects.toThrow();
    expect(Object.keys((await carKeeper<Record<string, any>>('get_state')).cars)).toContain('civic');
  });

  test('the tab element is the only Car Keeper element in the panel', async ({ page }) => {
    await openTab(page);
    await expect(carsTab(page)).toHaveCount(1);
  });
});
