// simple-badges.spec.js — the battery warning and frost badge on the simple home.
//
//   npm run test:ui
//
// The battery icon sits above the room temperature when the controller's
// batteryLow flag is set; a reading at or below five per cent uses the empty
// artwork. The frost badge appears beside the outside temperature when the
// summary's rule says frost protection is active. Both are driven from a map
// built here so the result does not depend on the wall clock.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome } = require('./support/harness');
const MAP = require('./fixtures/map.json');

function room(name, battery) {
  return {
    name,
    sensor: `sensor-${name}`,
    relays: [`relay-${name}`],
    relay: 'off',
    linked: 'yes',
    status: 'good',
    temperature: 1900,
    battery,
    statusMessage: '',
    relaysTotal: 1,
    relaysFailed: 0,
  };
}

function badgeMap() {
  const map = JSON.parse(JSON.stringify(MAP));
  map.profile = 0;
  map.calendar = 'off';
  map.rooms = [
    room('Battery Low', 15),
    room('Battery Empty', 3),
    room('Battery Good', 80),
    {
      name: 'Outside',
      sensor: 'test-outside',
      relays: [],
      relay: 'off',
      linked: 'yes',
      status: 'good',
      temperature: 500,
      battery: 51,
      statusMessage: '',
      relaysTotal: 0,
      relaysFailed: 0,
      protect: 'yes',
      ptemp: 10,
    },
  ];
  map.profiles = [{
    name: 'Weekday',
    rooms: {
      'Battery Low': { mode: 'off', target: 0, periods: [] },
      'Battery Empty': { mode: 'off', target: 0, periods: [] },
      'Battery Good': { mode: 'off', target: 0, periods: [] },
      'Outside': { mode: 'off', target: 0, periods: [] },
    },
  }];
  return map;
}

test('the simple home shows battery warnings and frost protection', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, badgeMap());
  await waitForHome(page);
  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-view').click();
  await expect(page.locator('#simple-room-0')).toBeVisible();

  // Low: the low artwork, above the temperature.
  await expect(page.locator('#simple-room-0-battery')).toBeVisible();
  await expect.poll(() => page.locator('#simple-room-0-battery')
    .evaluate(el => getComputedStyle(el).backgroundImage)).toContain('battery-low.png');

  // Empty: the red/empty artwork.
  await expect(page.locator('#simple-room-1-battery')).toBeVisible();
  await expect.poll(() => page.locator('#simple-room-1-battery')
    .evaluate(el => getComputedStyle(el).backgroundImage)).toContain('battery-empty.png');

  // A healthy battery shows nothing.
  await expect(page.locator('#simple-room-2-battery')).toBeHidden();

  // Outside 5.0 C with a 10 C frost trigger and no room calling.
  await expect(page.locator('#simple-profile-outside')).toHaveText('5.0');
  await expect(page.locator('#simple-profile-frost')).toBeVisible();

  expect(pageErrors).toEqual([]);
});
