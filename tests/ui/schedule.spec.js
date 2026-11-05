// schedule.spec.js — the schedule editor through the real shell.
//
// Covers the interaction the jsdom check cannot see: two native <select>
// dropdowns, a real change event, and the payload the page puts on the wire.
// A loaded period keeps its duration when its start moves; Save must carry the
// shifted stop into the controller's `periods[]` and must not leak the
// editing-only `offAuto` flag.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, openSchedule, lastRequest } = require('./support/harness');
const MAP = require('./fixtures/map.json');

test('moving a period start carries its stop into the saved request', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);

  await openSchedule(page, 0);
  await expect(page.locator('#sheet-title')).toHaveText('Schedule for Kitchen');

  const start = page.locator('#schedule-period-0-start-select');
  const stop = page.locator('#schedule-period-0-off-select');
  await expect(start).toHaveValue('06:00');
  await expect(stop).toHaveValue('08:00');

  // The fixture's first period is 06:00–08:00. Moving the start must keep the
  // two-hour duration until the user picks a stop of their own.
  await start.selectOption('06:30');
  await expect(stop).toHaveValue('08:30');

  await page.locator('#schedule-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(() => lastRequest(page, 'Update Profiles')).not.toBeNull();
  const request = await lastRequest(page, 'Update Profiles');

  const kitchen = request.profiles[0].rooms.Kitchen;
  expect(kitchen.periods).toEqual([
    { on: '06:30', off: '08:30', temp: '21.0', enabled: true },
    { on: '18:00', off: '23:00', temp: '22.0', enabled: true },
  ]);
  expect(JSON.stringify(kitchen.periods)).not.toContain('offAuto');

  // The request carries identity as well as schedule state; the controller
  // writes the six UI-owned fields back from it.
  expect(request.rooms.find(room => room.name === 'Kitchen')).toMatchObject({
    sensor: 'test-kitchen',
    relays: ['test-relay-kitchen'],
  });

  expect(pageErrors).toEqual([]);
});
