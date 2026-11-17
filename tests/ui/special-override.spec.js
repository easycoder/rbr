// special-override.spec.js — the morning start override and its off-time choice.
//
//   npm run test:ui
//
// Special actions → "Change the morning start time" opens a time popup with a
// checkbox: "Move the off time too". Ticked (the default), the controller moves
// the morning stop by the same amount as the start, so the period keeps its
// interval; unticked, the stop stays where the schedule put it. The controller's
// side of that is tests/unit/unit-10-overrides.allspeak; this spec proves what
// the page sends and that the choice is remembered per room.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, lastRequest } = require('./support/harness');
const MAP = require('./fixtures/map.json');

async function openMorningTime(page) {
  // The expansion may already be open (it survives the popup), and clicking the
  // rest row would then close it, so only open it when it is shut.
  if (!(await page.locator('#room-0-special-btn').isVisible())) {
    await page.locator('#room-0-rest').click();
  }
  await page.locator('#room-0-special-btn').click();
  await expect(page.locator('#special-sheet')).toBeVisible();
  await page.locator('#special-action-start').click();
  await expect(page.locator('#special-time-sheet')).toBeVisible();
}

test('the off time follows the start by default', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openMorningTime(page);

  // Pre-filled with the room's scheduled morning start, and the box is ticked:
  // shifting a warm-up half an hour usually means keeping its length.
  await expect(page.locator('#special-time-input')).toHaveValue('06:00');
  await expect(page.locator('#special-time-track')).toBeChecked();

  await page.locator('#special-time-input').fill('07:15');
  await page.locator('#special-time-input').blur();
  await page.locator('#special-time-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(async () => {
    const request = await lastRequest(page, 'Room Override');
    return request && request.time + ' ' + request.keepoff;
  }).toBe('07:15 yes');

  expect(pageErrors).toEqual([]);
});

test('unticking it keeps the schedule’s own off time, and the choice is remembered', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openMorningTime(page);

  await page.locator('#special-time-track').uncheck();
  await page.locator('#special-time-input').fill('05:45');
  await page.locator('#special-time-input').blur();
  await page.locator('#special-time-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(async () => {
    const request = await lastRequest(page, 'Room Override');
    return request && request.time + ' ' + request.keepoff;
  }).toBe('05:45 no');

  // Re-opening the popup shows what this phone chose last time for this room.
  await openMorningTime(page);
  await expect(page.locator('#special-time-track')).not.toBeChecked();
  await expect(page.locator('#special-time-input')).toHaveValue('05:45');

  expect(pageErrors).toEqual([]);
});
