// map-mid-edit.spec.js — a map pushed while a sheet editor is open must be
// held, not applied behind the editor's reply.
//
// A sheet editor is opened with `send … and assign reply`, which parks the
// shell on the runtime's ONE reply slot per program. Applying a controller map
// calls MapToRooms with another blocking send; if that runs while the editor
// holds the slot, the editor's reply is dropped and the sheet chrome stays up
// over hidden content. The jsdom check reads the shell's log; this proves the
// user-visible consequences in a real browser: the room list does not change
// underneath the sheet, Save still closes it and ships the request, and the
// held map is applied afterwards.

const { test, expect } = require('@playwright/test');
const {
  openApp, pushMap, waitForHome, openSchedule, lastRequest,
} = require('./support/harness');
const MAP = require('./fixtures/map.json');

function renamedMap(map, from, to) {
  const next = JSON.parse(JSON.stringify(map));
  for (const room of next.rooms) {
    if (room.name === from) room.name = to;
  }
  for (const profile of next.profiles) {
    profile.rooms[to] = profile.rooms[from];
    delete profile.rooms[from];
  }
  return next;
}

test('a map pushed mid-edit is held, then applied after Save closes the sheet', async ({ page }) => {
  const pageErrors = [];
  const consoleLines = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => consoleLines.push(message.text()));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openSchedule(page, 0);
  await expect(page.locator('#sheet-title')).toHaveText('Schedule for Kitchen');

  // A controller push lands while the editor is open.
  const next = renamedMap(MAP, 'Kitchen', 'Kitchen B');
  await pushMap(page, next);

  // The shell must say it held the map, and the list must still show the old
  // name — applying it here would be the bug, not a feature.
  await expect.poll(
    () => consoleLines.some(line => /map held while a sheet module is open/.test(line)),
    { timeout: 15000 },
  ).toBe(true);
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen');

  await page.locator('#schedule-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  // Save still shipped its request while the map was held.
  await expect.poll(() => lastRequest(page, 'Update Profiles')).not.toBeNull();
  const request = await lastRequest(page, 'Update Profiles');
  expect(request.profiles[0].rooms.Kitchen.periods[0].on).toBe('06:00');

  // Once the sheet has released the reply slot, the held map is applied.
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen B');

  expect(pageErrors).toEqual([]);
});
