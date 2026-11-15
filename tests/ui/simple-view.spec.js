// simple-view.spec.js — the reduced home screen for a resident who should not
// have to read the full room list.
//
//   npm run test:ui
//
// It drives the real shell in the real runtime with a scripted controller. The
// important contract is not just that the large buttons appear, but that the
// single-room page is wired to the same element IDs as a compact room row:
// tapping a mode button there must produce the same Operating Mode request,
// and Home must return to the room list. The choice is stored per device, so
// the last section reloads the page and proves it survived.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, lastRequest, chooseView } = require('./support/harness');
const MAP = require('./fixtures/map.json');

// The harness marks this device as one that chose Detailed, so the assertions
// that click full-view rows keep working; chooseView switches through the
// Appearance sheet.

test('simple view: toggle, one-room page, action and Home', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);

  // This device has stored the detailed view, which is what every other spec
  // sees; a fresh install starts simplified and is covered by appearance.spec.js.
  await expect(page.locator('#summary-title')).toBeVisible();
  await expect(page.locator('#simple-room-0')).toHaveCount(0);

  await chooseView(page, 'simplified');

  // Reduced home: name and temperature only, one button per room, no summary.
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect(page.locator('#simple-room-0-name')).toHaveText('Kitchen');
  await expect(page.locator('#simple-room-0-temp')).toHaveText('20.0');
  await expect(page.locator('#simple-room-1-name')).toHaveText('Bedroom');
  await expect(page.locator('#summary-title')).toHaveCount(0);
  await expect(page.locator('#room-0-name')).toHaveCount(0);

  // The banner's second row carries the date and time, the Profile button
  // and — because the fixture has an outside thermometer — its reading.
  await expect(page.locator('#top-bar-info')).toBeVisible();
  await expect(page.locator('#top-bar-date')).not.toBeEmpty();
  await expect(page.locator('#top-bar-profile')).toBeVisible();
  await expect(page.locator('#top-bar-profile-name')).toHaveText('Weekday');
  await expect(page.locator('#top-bar-outside')).toHaveText('5.0');

  // The banner is compact — it leaves most of the screen to the rooms — and
  // the last room pill runs to the bottom border below it.
  const bannerHeight = await page.locator('#top-bar').evaluate(el => el.getBoundingClientRect().height);
  expect(bannerHeight).toBeLessThan(140);
  const roomHeights = await page.evaluate(() => ['simple-room-0', 'simple-room-1']
    .map(id => Math.round(document.getElementById(id).getBoundingClientRect().height)));
  expect(Math.max(...roomHeights) - Math.min(...roomHeights)).toBeLessThan(3);
  expect(roomHeights[0]).toBeGreaterThan(250);

  // Pills are 90% of the list width and centred, so the gradient frames each
  // room on both sides instead of the pills forming one solid column.
  const pillBox = await page.locator('#simple-room-0').evaluate(el => {
    const box = el.getBoundingClientRect();
    const parent = el.parentElement.getBoundingClientRect();
    return {
      width: box.width,
      available: parent.width - parseFloat(getComputedStyle(el.parentElement).paddingLeft)
        - parseFloat(getComputedStyle(el.parentElement).paddingRight),
      left: box.left - parent.left,
      right: parent.right - box.right,
    };
  });
  expect(pillBox.width / pillBox.available).toBeCloseTo(0.9, 2);
  expect(Math.abs(pillBox.left - pillBox.right)).toBeLessThan(2);

  // Every space in the column is the same height — above the first pill,
  // between the pills and below the last — and each is a quarter of a pill.
  const shares = await page.evaluate(() => {
    const main = document.getElementById('layout-main');
    const cs = getComputedStyle(main);
    const box = main.getBoundingClientRect();
    const top = box.top + parseFloat(cs.paddingTop);
    const bottom = box.bottom - parseFloat(cs.paddingBottom);
    const a = document.getElementById('simple-room-0').getBoundingClientRect();
    const b = document.getElementById('simple-room-1').getBoundingClientRect();
    return {
      above: a.top - top,
      between: b.top - a.bottom,
      below: bottom - b.bottom,
      height: a.height,
    };
  });
  expect(Math.abs(shares.above - shares.between)).toBeLessThan(2);
  expect(Math.abs(shares.below - shares.between)).toBeLessThan(2);
  expect(shares.between / shares.height).toBeCloseTo(0.25, 1);

  // The Profile button opens the profile editor and Cancel returns to the
  // room list.
  await page.locator('#top-bar-profile').click();
  await expect(page.locator('#profile-sheet')).toBeVisible();
  await page.locator('#profile-cancel-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  // A device-level preference, not system state.
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-simple-view'))).toBe('on');

  // The single-room page keeps the compact row's IDs, so the existing render
  // and action code works unchanged.
  await page.locator('#simple-room-0').click();
  await expect(page.locator('#room-0-card')).toBeVisible();
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen');
  await expect(page.locator('#room-0-temp')).toHaveText('20.0');
  await expect(page.locator('#room-0-mode-timed')).toBeVisible();
  await expect(page.locator('#room-0-target-block')).toBeHidden();
  await expect(page.locator('#simple-room-home')).toBeVisible();

  // The card fills the screen below the banner, with the action row above
  // the Home button. The banner drops its date/profile/outside row here —
  // those belong to the room list — which is what keeps the card on one
  // screen.
  await expect(page.locator('#top-bar-info')).toBeHidden();
  const cardBox = await page.locator('#room-0-card').evaluate(el => {
    const box = el.getBoundingClientRect();
    return { top: Math.round(box.top), bottom: Math.round(box.bottom), height: Math.round(box.height) };
  });
  expect(cardBox.bottom).toBe(844 - 8);
  expect(cardBox.height).toBeGreaterThan(700);

  // Edit schedule, Special actions and Room details are one row of equal
  // width, with two-line labels, on the light-grey/mid-grey button face.
  const actionBoxes = await page.evaluate(() => ['room-0-edit-schedule', 'room-0-special-btn', 'room-0-info-btn']
    .map(id => {
      const box = document.getElementById(id).getBoundingClientRect();
      return { top: Math.round(box.top), width: Math.round(box.width), height: Math.round(box.height) };
    }));
  expect(new Set(actionBoxes.map(box => box.top)).size).toBe(1);
  expect(Math.max(...actionBoxes.map(box => box.width)) - Math.min(...actionBoxes.map(box => box.width))).toBeLessThan(3);
  expect(Math.max(...actionBoxes.map(box => box.height)) - Math.min(...actionBoxes.map(box => box.height))).toBeLessThan(3);
  expect(Math.abs(actionBoxes[0].width - actionBoxes[0].height)).toBeLessThan(3);
  await expect(page.locator('#room-0-edit-schedule')).toHaveCSS('white-space', 'pre-line');
  await expect(page.locator('#room-0-edit-schedule')).toHaveCSS('background-color', 'rgb(244, 245, 247)');
  await expect(page.locator('#room-0-edit-schedule')).toHaveCSS('border-top-color', 'rgb(187, 187, 187)');
  await expect(page.locator('#room-0-advance-btn')).toHaveCSS('background-color', 'rgb(244, 245, 247)');
  await expect(page.locator('#room-0-advance-btn')).toHaveCSS('border-top-color', 'rgb(187, 187, 187)');

  // Advance is a large square centred in the remaining space.
  const advanceBox = await page.locator('#room-0-advance-btn').evaluate(el => {
    const box = el.getBoundingClientRect();
    return { left: Math.round(box.left), top: Math.round(box.top), width: Math.round(box.width), height: Math.round(box.height) };
  });
  expect(Math.abs(advanceBox.width - advanceBox.height)).toBeLessThan(3);
  expect(advanceBox.width).toBeGreaterThan(180);
  const expansionBox = await page.locator('#room-0-expansion').evaluate(el => {
    const box = el.getBoundingClientRect();
    return { left: Math.round(box.left), width: Math.round(box.width) };
  });
  expect(Math.abs((advanceBox.left + advanceBox.width / 2) - (expansionBox.left + expansionBox.width / 2))).toBeLessThan(3);
  const advanceBlockBox = await page.locator('#room-0-advance-block').evaluate(el => {
    const box = el.getBoundingClientRect();
    return { top: Math.round(box.top), bottom: Math.round(box.bottom) };
  });
  const advanceAbove = advanceBox.top - advanceBlockBox.top;
  const advanceBelow = advanceBlockBox.bottom - (advanceBox.top + advanceBox.height);
  expect(Math.abs(advanceAbove - advanceBelow)).toBeLessThan(3);
  await expect(page.locator('#room-0-advance-btn')).toContainText('Advance');

  // The label is set at twice the compact row's size so it reads across a
  // room, and the widest line still fits inside the padding box.
  await expect(page.locator('#room-0-advance-btn')).toHaveCSS('font-size', '40px');
  const advanceLabelFits = await page.locator('#room-0-advance-btn').evaluate(el => {
    const cs = getComputedStyle(el);
    const inner = el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const widest = (el.textContent || '').split('\n')
      .reduce((a, b) => (b.length > a.length ? b : a), '');
    const probe = document.createElement('span');
    probe.style.font = cs.font;
    probe.style.whiteSpace = 'pre';
    probe.textContent = widest;
    el.appendChild(probe);
    const width = probe.getBoundingClientRect().width;
    probe.remove();
    return width <= inner;
  });
  expect(advanceLabelFits).toBe(true);

  // The 2x2 mode grid's On button is the real ChangeMode path.
  await page.locator('#room-0-mode-on').click();
  await expect.poll(async () => {
    const request = await lastRequest(page, 'Operating Mode');
    return request && request.Mode;
  }).toBe('on');
  await expect(page.locator('#room-0-target-block')).toBeVisible();

  // The target stepper and the boost duration buttons use the same paths.
  await page.locator('#room-0-target-plus').click();
  await expect(page.locator('#room-0-target-value')).toHaveText('21.5');
  await expect.poll(async () => {
    const request = await lastRequest(page, 'Operating Mode');
    return request && request.target;
  }).toBe('21.5');

  await page.locator('#room-0-mode-boost').click();
  await expect(page.locator('#room-0-boost-block')).toBeVisible();
  await page.locator('#room-0-boost-30').click();
  await expect.poll(async () => {
    const request = await lastRequest(page, 'Operating Mode');
    return request && request.Mode + ':' + request.boost;
  }).toBe('boost:B30');

  // Home returns to the room list, not the full view.
  await page.locator('#simple-room-home').click();
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect(page.locator('#simple-room-home')).toHaveCount(0);
  await expect(page.locator('#top-bar-profile')).toBeVisible();
  await expect(page.locator('#top-bar-info')).toBeVisible();

  // Switching back rebuilds the full view and restores its own page padding.
  await chooseView(page, 'detailed');
  await expect(page.locator('#summary-title')).toBeVisible();
  await expect(page.locator('#top-bar-info')).toBeHidden();
  expect(await page.locator('#layout-main').evaluate(el => getComputedStyle(el).paddingTop)).toBe('14px');

  // Return to the simple view for the reload check.
  await chooseView(page, 'simplified');
  await expect(page.locator('#simple-room-0')).toBeVisible();

  // Reload proves the choice is remembered on this device.
  await page.reload();
  await page.waitForFunction(() => !!window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect(page.locator('#summary-title')).toHaveCount(0);

  expect(pageErrors).toEqual([]);
});

test('simple view: the bottom pill omits the outside reading without a sensor', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  // No outdoor slot at all: the profile half must still be present.
  const noOutside = JSON.parse(JSON.stringify(MAP));
  noOutside.rooms = noOutside.rooms.filter(room => room.name !== 'Outside');

  await openApp(page);
  await pushMap(page, noOutside);
  await waitForHome(page);
  await chooseView(page, 'simplified');

  await expect(page.locator('#top-bar-profile')).toBeVisible();
  await expect(page.locator('#top-bar-profile-name')).toHaveText('Weekday');
  await expect(page.locator('#top-bar-outside-block')).toBeHidden();

  expect(pageErrors).toEqual([]);
});
