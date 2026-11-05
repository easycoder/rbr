// devices.spec.js — a room rename keeps that room's own wiring.
//
// The original failure renamed the selected room and then wrote another room's
// relays and thermometer over it, because the scratch record used for the
// rename was left on the last room scanned. The jsdom check catches it at the
// module boundary; this drives the same picker and prompt in the real shell
// and compares the whole identity list and both profiles in the request.

const { test, expect } = require('@playwright/test');
const {
  openApp, pushMap, waitForHome, openDeviceEditor, lastRequest, answerDialogs,
} = require('./support/harness');
const MAP = require('./fixtures/map.json');

function wiring(rooms) {
  return rooms.map(room => ({
    name: room.name,
    sensor: room.sensor,
    relays: room.relays,
  }));
}

test('renaming the second room keeps its own wiring and moves only its state', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const answers = answerDialogs(page);
  answers.prompt = 'Bedroom 2';

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openDeviceEditor(page);

  await expect(page.locator('#sheet-title')).toHaveText('Rooms and Devices');

  // The sheet loads with the first room selected; rename the *second* row, so
  // the rename must not borrow the form's wiring.
  await page.locator('#device-editor-room-pill').click();
  await page.locator('#device-room-edit-1-edit').click();
  await expect(page.locator('#device-room-edit-1-name')).toHaveText('Bedroom 2');

  await page.locator('#device-editor-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(() => lastRequest(page, 'Update Profiles')).not.toBeNull();
  const request = await lastRequest(page, 'Update Profiles');

  // The identity list keeps order and wiring; only the one name changes.
  expect(wiring(request.rooms)).toEqual([
    { name: 'Kitchen', sensor: 'test-kitchen', relays: ['test-relay-kitchen'] },
    { name: 'Bedroom 2', sensor: 'test-bedroom', relays: ['test-relay-bedroom'] },
    { name: 'Outside', sensor: 'test-outside', relays: [] },
  ]);

  // Every profile's state key moved with the room, and the state itself is
  // the one that room already had.
  const weekday = request.profiles[0].rooms;
  expect(weekday.Bedroom).toBeUndefined();
  expect(weekday['Bedroom 2'].periods).toEqual([
    { on: '07:00', off: '09:00', temp: '18.0' },
    { on: '20:00', off: '22:30', temp: '18.0' },
  ]);

  const weekend = request.profiles[1].rooms;
  expect(weekend.Bedroom).toBeUndefined();
  expect(weekend['Bedroom 2']).toEqual({ mode: 'off', target: 0, periods: [] });

  expect(pageErrors).toEqual([]);
});
