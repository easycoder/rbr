// system.spec.js — the System sheet: the system-wide On cap and the heating type.
//
//   npm run test:ui
//
// Both are map-root settings (`onmax`, `systemType`). This drives the real sheet
// with a scripted controller: the fixture has no cap, so the sheet must show
// Always On; choosing eight hours and saving must carry `onmax: "8"` in the
// System Name request. The heating type has to be both shown from the map and
// sent back on Save — the controller used to drop it on the floor, which is
// covered by tests/unit/system_type_test.py; here the page's half is what the
// request and the reopened sheet can prove.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, lastRequest } = require('./support/harness');
const MAP = require('./fixtures/map.json');

test('the System sheet sets the system-wide On cap', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);

  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-system').click();
  await expect(page.locator('#system-sheet')).toBeVisible();

  // The fixture predates the setting, so the actual behaviour is Always On.
  await expect(page.locator('#system-sheet-max-on')).toHaveValue('always');

  await page.selectOption('#system-sheet-max-on', '8');
  await page.locator('#system-sheet-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(async () => {
    const request = await lastRequest(page, 'System Name');
    return request && request.onmax;
  }).toBe('8');

  expect(pageErrors).toEqual([]);
});

test('the System sheet reopens on the saved On cap', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  // The controller's map is the only place the setting lives, so a page that
  // loads one with a cap must show that cap, not the Always On default.
  await pushMap(page, Object.assign({}, MAP, { onmax: '8' }));
  await waitForHome(page);

  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-system').click();
  await expect(page.locator('#system-sheet')).toBeVisible();
  await expect(page.locator('#system-sheet-max-on')).toHaveValue('8');

  // Change it, save, and reopen: the sheet is rebuilt from the map each time,
  // so a selection that is written to the map but not read back looks saved
  // and then quietly reverts on the next Save.
  await page.selectOption('#system-sheet-max-on', '10');
  await page.locator('#system-sheet-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-system').click();
  await expect(page.locator('#system-sheet-max-on')).toHaveValue('10');

  expect(pageErrors).toEqual([]);
});

test('the System sheet shows and sends the heating type', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  // A system already set to Heat Pump: the sheet must come up on that pill,
  // not on the Boiler default it would show if the field arrived empty.
  await pushMap(page, Object.assign({}, MAP, { systemType: 'Heat Pump' }));
  await waitForHome(page);

  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-system').click();
  await expect(page.locator('#system-sheet')).toBeVisible();
  await expect(page.locator('#system-sheet-type-heatpump')).toHaveCSS('background-color', 'rgb(255, 255, 255)');

  // Choosing Boiler and saving ships the label the controller stores.
  await page.locator('#system-sheet-type-boiler').click();
  await expect(page.locator('#system-sheet-type-boiler')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await page.locator('#system-sheet-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(async () => {
    const request = await lastRequest(page, 'System Name');
    return request && request.systemType;
  }).toBe('Boiler');

  // The controller's reply carries the stored type back; reopening shows it.
  await pushMap(page, Object.assign({}, MAP, { systemType: 'Boiler' }));
  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-system').click();
  await expect(page.locator('#system-sheet-type-boiler')).toHaveCSS('background-color', 'rgb(255, 255, 255)');

  expect(pageErrors).toEqual([]);
});
