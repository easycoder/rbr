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
const { openApp, pushMap, waitForHome, lastRequest, chooseView } = require('./support/harness');
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

// The pill and the subline have to agree with what the controller is actually
// doing. The controller applies today's armed override to the morning period
// before it decides anything; the page's own projection used to play the stored
// schedule instead, so a room warmed an hour early showed black text and
// "Off until 07:30" while its flame was lit.
test('the room reads as heating inside the moved morning', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const ORANGE = 'rgb(232, 106, 51)';
  const pad = n => (n < 10 ? '0' + n : '' + n);
  // Every time below comes from one instant. Recomputing "now" at assertion
  // time is how a minute boundary turns a passing run into a failing one.
  const base = new Date();
  const hhmm = offset => {
    const d = new Date(base.getTime());
    d.setHours(d.getHours(), d.getMinutes() + offset, 0, 0);
    return pad(d.getHours()) + ':' + pad(d.getMinutes());
  };
  const todayKey = base.getFullYear() + '-' + pad(base.getMonth() + 1) + '-' + pad(base.getDate());

  const map = JSON.parse(JSON.stringify(MAP));
  // A morning an hour ahead of the clock, with the off time tracking it: the
  // scheduled stop is two hours out, the moved one an hour out.
  map.profiles[0].rooms.Kitchen.periods = [{ on: hhmm(60), off: hhmm(120), temp: '21.0' }];
  map.rooms[0].relay = 'on';
  map.overrides = {
    Kitchen: { kind: 'start', on: hhmm(-30), date: todayKey, keepoff: 'yes' },
  };

  await openApp(page);
  await pushMap(page, map);
  await waitForHome(page);

  // Inside the moved morning: the radiator is calling, so orange, not the
  // black of a gap between periods.
  await expect(page.locator('#room-0-name')).toHaveCSS('color', ORANGE);
  await expect(page.locator('#room-0-subline')).toContainText('21.0°→' + hhmm(30));
  await expect(page.locator('#room-0-override-text')).toHaveText('Today from ' + hhmm(-30));

  // The time popup still offers the room's own scheduled start for the next
  // request, not the override already in force.
  if (!(await page.locator('#room-0-special-btn').isVisible())) {
    await page.locator('#room-0-rest').click();
  }
  await page.locator('#room-0-special-btn').click();
  await page.locator('#special-action-start').click();
  await expect(page.locator('#special-time-input')).toHaveValue(hhmm(60));
  await page.locator('#special-time-cancel-btn').click();
  await page.locator('#special-sheet-close-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  // Same projection on the reduced home's pill.
  await chooseView(page, 'simplified');
  await expect(page.locator('#simple-room-0-name')).toHaveCSS('color', ORANGE);

  expect(pageErrors).toEqual([]);
});
