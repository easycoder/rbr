// system.spec.js — the system-wide On cap in the System sheet.
//
//   npm run test:ui
//
// The cap is a map-root setting (`onmax`). This drives the real sheet with a
// scripted controller: the fixture has no setting, so the sheet must show
// Always On; choosing eight hours and saving must carry `onmax: "8"` in the
// System Name request. The controller is not in the loop, so the request is
// the contract this test can prove.

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
