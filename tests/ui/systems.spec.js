// systems.spec.js — the About sheet's Systems list and the Manual link.
//
//   npm run test:ui
//
// One PWA can manage several installations; the list is local to the device and
// a system is identified by its MAC. This drives the real shell with a scripted
// controller, adds a second system through the same dialog flow a person uses,
// selects between them, and removes one. The server is not involved in removal:
// the spec proves the stored list changes and the installation is untouched.
//
// The Manual control is not a tab. It is an anchor to /docs/, opened in a new
// tab, so the browser can show the documentation outside the installed app.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome } = require('./support/harness');
const MAP = require('./fixtures/map.json');

const FIRST_MAC = '00:11:22:33:44:55';
const SECOND_MAC = 'aa:bb:cc:dd:ee:ff';

async function openSystems(page) {
  await page.locator('#top-bar-mark').click();
  await expect(page.locator('#about-sheet')).toBeVisible();
  await page.locator('#about-tab-systems').click();
  await expect(page.locator('#about-body-systems')).toBeVisible();
}

async function boot(page) {
  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
}

async function storedSystems(page) {
  return page.evaluate(() => JSON.parse(localStorage.getItem('rbr-systems') || '[]'));
}

test('the About sheet links to the manual and lists the current system', async ({ page }) => {
  await boot(page);
  await page.locator('#top-bar-mark').click();
  await expect(page.locator('#about-sheet')).toBeVisible();

  const manual = page.locator('#about-tab-manual');
  await expect(manual).toHaveAttribute('href', '/docs/#operation/01-the-interface');
  await expect(manual).toHaveAttribute('target', '_blank');

  await page.locator('#about-tab-systems').click();
  await expect(page.locator('#about-body-systems')).toBeVisible();
  await expect(page.locator('#about-systems-list > div')).toHaveCount(1);
  await expect(page.locator('#system-row-0-name')).toHaveText('My system');
  await expect(page.locator('#system-row-0-mac')).toHaveText(FIRST_MAC);
  await expect(page.locator('#system-row-0-select')).toHaveText('Current');
  await expect(page.locator('#system-row-0-select')).toBeDisabled();
});

test('a system can be added, selected and removed', async ({ page }) => {
  await boot(page);
  await openSystems(page);

  const answers = ['Second home', SECOND_MAC, '123456'];
  page.on('dialog', dialog => dialog.accept(answers.shift() || 'yes'));
  await page.route('**/verify', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, token: 'token-second' }),
  }));

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'load' }),
    page.locator('#about-systems-add').click(),
  ]);
  await page.waitForFunction(() => window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);

  let systems = await storedSystems(page);
  expect(systems).toHaveLength(2);
  expect(systems[1]).toMatchObject({ name: 'Second home', mac: SECOND_MAC, token: 'token-second' });
  expect(await page.evaluate(() => localStorage.getItem('rbr-current-mac'))).toBe(SECOND_MAC);

  await openSystems(page);
  await expect(page.locator('#about-systems-list > div')).toHaveCount(2);
  await expect(page.locator('#system-row-1-select')).toHaveText('Current');
  await expect(page.locator('#system-row-0-select')).toHaveText('Select');

  // Selecting the first system rewrites the current MAC and reloads.
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'load' }),
    page.locator('#system-row-0-select').click(),
  ]);
  await page.waitForFunction(() => window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);
  expect(await page.evaluate(() => localStorage.getItem('rbr-current-mac'))).toBe(FIRST_MAC);

  // Rename the non-current second system in this device's list. The MAC,
  // token and identity are untouched; only the label changes.
  await openSystems(page);
  answers.push('Renamed home');
  await page.locator('#system-row-1-rename').click();
  await expect(page.locator('#system-row-1-name')).toHaveText('Renamed home');
  systems = await storedSystems(page);
  expect(systems[1].name).toBe('Renamed home');
  expect(systems[1].mac).toBe(SECOND_MAC);
  expect(systems[1].token).toBe('token-second');

  // Remove the now non-current second system. It disappears from storage and
  // from the list, and the current system does not change. The dialog handler
  // installed above accepts the confirmation; the sheet is still open, so the
  // row is clicked where it stands.
  await expect(page.locator('#system-row-1-name')).toHaveText('Renamed home');
  await page.locator('#system-row-1-delete').click();
  await expect(page.locator('#about-systems-list > div')).toHaveCount(1);
  await expect(page.locator('#system-row-0-name')).toHaveText('My system');
  await expect(page.locator('#system-row-0-select')).toHaveText('Current');
  systems = await storedSystems(page);
  expect(systems).toHaveLength(1);
  expect(systems[0].mac).toBe(FIRST_MAC);
});
