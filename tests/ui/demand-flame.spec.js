// demand-flame.spec.js — the flame beside the heartbeat dot.
//
//   npm run test:ui
//
// The map names the demand relay (`request`) but does not say whether it is
// firing, so the UI derives the state from what the controller fires it for:
// any room calling for heat, or frost protection with no room calling. A
// system with no request relay shows nothing. The flame lives in the top bar,
// which both home screens share, so this drives it from the full home and the
// spec below also checks the simple home keeps it.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome } = require('./support/harness');
const MAP = require('./fixtures/map.json');

function demandMap({ request, heating, frost }) {
  const map = JSON.parse(JSON.stringify(MAP));
  map.profile = 0;
  map.calendar = 'off';
  if (request) map.request = 'test-demand';
  else delete map.request;

  // `calling` is taken straight from the controller's relay field.
  map.rooms[0].relay = heating ? 'on' : 'off';
  map.rooms[1].relay = 'off';

  const outside = map.rooms[2];
  outside.temperature = 500;
  if (frost) {
    outside.protect = 'yes';
    outside.ptemp = 10;
  } else {
    delete outside.protect;
    delete outside.ptemp;
  }
  return map;
}

test('the flame appears beside the heartbeat dot only while the demand relay is on', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, demandMap({ request: true, heating: true, frost: false }));
  await waitForHome(page);

  const flame = page.locator('#top-bar-demand-flame');
  const dot = page.locator('#top-bar-heartbeat-dot');

  // A room calling: the controller fires the demand relay.
  await expect(flame).toBeVisible();

  // Idle: the relay is off, the dot is still there.
  await pushMap(page, demandMap({ request: true, heating: false, frost: false }));
  await expect(flame).toBeHidden();
  await expect(dot).toBeVisible();

  // No request relay configured: rooms can heat on their own valves, but
  // there is no demand relay to report, so no flame.
  await pushMap(page, demandMap({ request: false, heating: true, frost: false }));
  await expect(flame).toBeHidden();

  // Frost protection fires the demand relay with no room calling.
  await pushMap(page, demandMap({ request: true, heating: false, frost: true }));
  await expect(flame).toBeVisible();

  expect(pageErrors).toEqual([]);
});

test('the simple home keeps the flame current', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, demandMap({ request: true, heating: true, frost: false }));
  await waitForHome(page);
  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-view').click();
  await expect(page.locator('#simple-room-0')).toBeVisible();

  const flame = page.locator('#top-bar-demand-flame');
  await expect(flame).toBeVisible();

  await pushMap(page, demandMap({ request: true, heating: false, frost: false }));
  await expect(flame).toBeHidden();

  expect(pageErrors).toEqual([]);
});
