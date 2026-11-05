// smoke.spec.js — the page boots from a controller map and renders it.
//
//   npm run test:ui
//
// This is the harness check, not a feature test: it proves the things every
// later spec depends on — that the real runtime and the real shell load, that
// the stubbed MQTT client takes the place of the broker without falling into
// demo mode, that the UI asks the controller for a full map, and that a map in
// the controller's own shape reaches the room list. It deliberately asserts
// only the first row and the summary: adding more rooms to the fixture should
// not require editing this spec.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, sentText } = require('./support/harness');
const MAP = require('./fixtures/map.json');

test('boots from a controller map and renders its rooms', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);

  // On connect the shell sends `action: first`, which is what makes the
  // controller reply with a full map rather than a heartbeat. Seeing it proves
  // the scripted client is the one the shell is talking to.
  await expect.poll(() => sentText(page), { timeout: 15000 }).toContain('first');

  // No controller here: the fixture is the reply.
  await pushMap(page, MAP);

  // One room is calling, so the summary names it; the outdoor sensor entry is
  // not a room and must not appear in the list.
  await expect(page.locator('#summary-title')).toHaveText('Kitchen is calling for heat');
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen');
  await expect(page.locator('#room-1-name')).toHaveText('Bedroom');
  await expect(page.locator('#room-2-name')).toHaveCount(0);

  // The row is interactive chrome, not just text: this is the element every
  // room spec will click.
  await expect(page.locator('#room-0-rest')).toBeVisible();
  await expect(page.locator('#room-0-heating-tag')).toBeVisible();

  expect(pageErrors).toEqual([]);
});
