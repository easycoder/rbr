// appearance.spec.js — the Appearance sheet: the view style and the page colour.
//
//   npm run test:ui
//
// Both choices are device-local and live: a tap on the view pill rebuilds the
// home behind the sheet, and a swatch or the time checkbox repaints the page
// gradient at once. Nothing in this sheet reaches the controller, so every
// assertion is about the page and about what is left in browser storage for the
// next load.
//
// The background is one colour mixed towards white for each hour bucket, so the
// fixed gradient (time-based changes off) is checked against the stops computed
// here from the same colour — that is the colour maths as much as the storage.

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome } = require('./support/harness');
const MAP = require('./fixtures/map.json');

const DEFAULT_COLOUR = '#E86A33';
const OLIVE = '#808000';

// The three stops with time-based changes off: 14%, 36% and 64% of the colour
// towards white — the afternoon set — as shell.allspeak's PaintAfternoonStops
// mixes them. The browser serialises the inline gradient's colours as rgb(...),
// so that is the form to look for.
function fixedStops(hex) {
  const rgb = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
  return [14, 36, 64].map(share => 'rgb(' + rgb
    .map(channel => Math.floor((channel * share + 255 * (100 - share)) / 100))
    .join(', ') + ')');
}

async function openAppearance(page) {
  await page.locator('#top-bar-menu-btn').click();
  await page.locator('#menu-row-appearance').click();
  await expect(page.locator('#appearance-sheet')).toBeVisible();
}

// Webson gives the layout template its own id to the container it renders
// into, so the page's background lives on #layout-frame, not #app.
async function background(page) {
  return page.evaluate(() => document.getElementById('layout-frame').style.background);
}

test('a fresh install starts simplified, and the sheet switches view and keeps up', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  // No stored view choice: this is what a new installation gets.
  await openApp(page, { freshView: true });
  await pushMap(page, MAP);
  await waitForHome(page);
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect(page.locator('#summary-title')).toHaveCount(0);

  // Appearance is the hamburger's top row, and says what it is for.
  await page.locator('#top-bar-menu-btn').click();
  await expect(page.locator('#menu-sheet-card > button').first()).toHaveAttribute('id', 'menu-row-appearance');
  await expect(page.locator('#menu-row-appearance-sub')).toHaveText('The look and feel of this app');
  await page.locator('#menu-row-appearance').click();
  await expect(page.locator('#appearance-sheet')).toBeVisible();

  // The sheet says which view is in force, and switching is live: the home
  // behind it is rebuilt while the sheet stays up.
  await expect(page.locator('#appearance-sheet-view-simplified')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await page.locator('#appearance-sheet-view-detailed').click();
  await expect(page.locator('#appearance-sheet')).toBeVisible();
  await expect(page.locator('#summary-title')).toBeVisible();
  await expect(page.locator('#simple-room-0')).toHaveCount(0);
  await expect(page.locator('#appearance-sheet-view-detailed')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-simple-view'))).toBe('off');

  // Back to simplified, then Done: the choice outlives the sheet.
  await page.locator('#appearance-sheet-view-simplified').click();
  await page.locator('#appearance-sheet-done-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-simple-view'))).toBe('on');

  // ...and the next load.
  await page.reload();
  await page.waitForFunction(() => !!window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);
  await expect(page.locator('#simple-room-0')).toBeVisible();
  await expect(page.locator('#simple-room-1-name')).toHaveText('Bedroom');

  expect(pageErrors).toEqual([]);
});

test('the background colour is a device choice: swatch, hex and the time checkbox', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openAppearance(page);

  // The app's own orange is the colour until one is picked, and the stored
  // choice is what the field shows.
  await expect(page.locator('#appearance-sheet-hex')).toHaveValue(DEFAULT_COLOUR);
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-colour'))).toBeNull();

  // The olive swatch (third in the palette) is applied as the page gradient.
  const before = await background(page);
  await page.locator('#appearance-sheet-swatch-2').click();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-colour'))).toBe(OLIVE);
  const olive = await background(page);
  expect(olive).not.toBe(before);
  expect(olive).toContain('gradient');
  await expect(page.locator('#appearance-sheet-hex')).toHaveValue(OLIVE);

  // The choice is remembered across a reload, with the swatch still ringed.
  await page.reload();
  await page.waitForFunction(() => !!window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);
  expect(await background(page)).toBe(olive);
  await openAppearance(page);
  await expect(page.locator('#appearance-sheet-hex')).toHaveValue(OLIVE);
  await expect(page.locator('#appearance-sheet-swatch-2')).toHaveCSS('box-shadow', /rgb\(18, 52, 90\)/);

  // A value that is not a colour is refused without changing anything: the
  // note says why, and the saved colour is still the olive.
  await page.locator('#appearance-sheet-hex').fill('olive');
  await page.locator('#appearance-sheet-hex').blur();
  await expect(page.locator('#appearance-sheet-note')).toHaveText('That is not a hex colour. Use six digits, such as #808000.');
  expect(await background(page)).toBe(olive);
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-colour'))).toBe(OLIVE);

  // Any six-digit value works, and is normalised to upper case with the hash.
  await page.locator('#appearance-sheet-hex').fill('5c7a99');
  await page.locator('#appearance-sheet-hex').blur();
  await expect(page.locator('#appearance-sheet-hex')).toHaveValue('#5C7A99');
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-colour'))).toBe('#5C7A99');

  // Turning the time-based changes off leaves one fixed gradient: the afternoon
  // stops for the chosen colour, at whatever hour the run happens. They are the
  // stops with the most colour in them, so a frozen background still reads as
  // the chosen shade rather than as a near-white wash.
  await page.locator('#appearance-sheet-time').uncheck();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-time'))).toBe('off');
  const fixed = await background(page);
  const [top, mid, bottom] = fixedStops('#5C7A99');
  expect(fixed).toContain(top);
  expect(fixed).toContain(mid);
  expect(fixed).toContain(bottom);

  // It survives a reload, and the checkbox comes back unticked.
  await page.reload();
  await page.waitForFunction(() => !!window.__rbr && window.__rbr.connected === true, null, { timeout: 30000 });
  await pushMap(page, MAP);
  await waitForHome(page);
  expect(await background(page)).toBe(fixed);
  await openAppearance(page);
  await expect(page.locator('#appearance-sheet-time')).not.toBeChecked();

  // Ticking it again restores the time-of-day behaviour.
  await page.locator('#appearance-sheet-time').check();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('rbr-bg-time'))).toBe('on');

  expect(pageErrors).toEqual([]);
});
