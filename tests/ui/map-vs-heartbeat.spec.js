// map-vs-heartbeat.spec.js — a heartbeat that lands while a map is being
// acknowledged must not swallow the map.
//
// OnMapReceived tints the heartbeat dot and used to wait 500 ms there, before
// reading the payload. ReceivedMessage is one variable, so a poll's empty reply
// arriving inside that window overwrote the map; the handler then took the
// empty payload for a heartbeat and the map was never applied. On a journal run
// the visible result is a room card one reading behind the controller — the
// 2026-11-11 report, where s909 and s975 failed in Show but not in Run because
// the pacing changed which poll landed in the window. The tint is now held by a
// forked task, so the payload is read before anything can wait.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, pushRaw, waitForHome } = require('./support/harness');
const MAP = require('./fixtures/map.json');

function withKitchenTemperature(map, value) {
  const next = JSON.parse(JSON.stringify(map));
  for (const room of next.rooms) {
    if (room.name === 'Kitchen') room.temperature = value;
  }
  return next;
}

test('a heartbeat arriving during the reply pulse does not swallow a map', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await expect(page.locator('#room-0-temp')).toHaveText('20.0');

  // The map is applied only after the heartbeat tint; the empty payload lands
  // inside that window, as a poll's reply does on a busy run.
  await pushMap(page, withKitchenTemperature(MAP, 1950));
  await page.waitForTimeout(100);
  await pushRaw(page, '');

  await expect(page.locator('#room-0-temp')).toHaveText('19.5');
  expect(pageErrors).toEqual([]);
});
