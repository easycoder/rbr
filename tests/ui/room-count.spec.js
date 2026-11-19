// room-count.spec.js — the home when the controller's room list changes size,
// and a room card that has to survive a map push.
//
//   npm run test:ui
//
// What it exists for, 2026-11-19. The page had been built from a smaller map;
// the next push carried eight rooms. RefreshHomeScreen looped to the new
// RoomCount, Attach waited for a `room-3-name` that had never been rendered,
// and the push ended in "Runtime error in 'Shell': No such element". The home
// never caught up, and a tap then reached PaintExpansion with handle arrays
// whose slots nobody had attached ("ModeTimedBtn is not attached to a DOM
// element"). A changed count now rebuilds the shape.
//
// The reduced view has the same failure in its room card: OpenSimpleRoom
// clears MainHolder and reallocates the row handles before the card exists,
// and a card whose template never arrives used to leave SimpleRoomIndex set,
// so every later push tried to paint a page that was not there. It now falls
// back to the room list. The last test proves the ordinary case the report
// also depended on: a map landing while the card is open leaves it wired.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, lastRequest } = require('./support/harness');
const MAP = require('./fixtures/map.json');

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

test('a map with more rooms rebuilds the detailed home', async ({ page }) => {
  const pageErrors = [];
  const dialogs = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('dialog', async dialog => { dialogs.push(dialog.message()); await dialog.dismiss(); });

  const small = clone(MAP);
  const big = clone(require('../../map.json'));

  await openApp(page);
  await pushMap(page, small);
  await waitForHome(page);
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen');
  await expect(page.locator('#room-2-name')).toHaveCount(0);

  await pushMap(page, big);
  await expect(page.locator('#room-6-name')).toHaveText('Office', { timeout: 10000 });
  await expect(page.locator('#room-6-name')).toBeVisible();

  // No runtime error and, in particular, none of the "No such element" dialogs
  // that came from Attach waiting on rows the old home never rendered.
  expect(dialogs).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test('a map while the room card is open leaves it wired', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page, { freshView: true });
  await pushMap(page, MAP);
  await waitForHome(page);

  await page.locator('#simple-room-1').click();
  await expect(page.locator('#room-1-card')).toBeVisible();
  await expect(page.locator('#room-1-name')).toHaveText('Bedroom');

  await pushMap(page, MAP);
  await expect(page.locator('#room-1-card')).toBeVisible();

  // The controls still answer: their handles survived the push.
  await page.locator('#room-1-mode-off').click();
  await expect.poll(async () => {
    const request = await lastRequest(page, 'Operating Mode');
    return request && request.Room + ' ' + request.Mode;
  }).toBe('Bedroom off');

  expect(pageErrors).toEqual([]);
});

test('a card whose template never arrives falls back to the list', async ({ page }) => {
  const pageErrors = [];
  const dialogs = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('dialog', async dialog => { dialogs.push(dialog.message()); await dialog.dismiss(); });

  await openApp(page, { freshView: true });
  await pushMap(page, MAP);
  await waitForHome(page);

  // The one fetch this tap makes is the card template. Refusing it is the
  // failure the guard exists for: SimpleRoomIndex is already set and
  // MainHolder is already empty when LoadFailed stops the click handler.
  await page.route('**/webson/simple-room.json*', route => route.abort());
  await page.locator('#simple-room-1').click();
  await expect.poll(() => dialogs.length).toBeGreaterThan(0);
  expect(dialogs[0]).toContain('Failed to load UI template');

  // The next map push must not spend the rest of the session reporting a card
  // that is not there; it puts the room list back instead.
  await pushMap(page, MAP);
  await expect(page.locator('#simple-room-1')).toBeVisible();
  await expect(page.locator('#simple-room-1-name')).toHaveText('Bedroom');

  expect(pageErrors).toEqual([]);
});
