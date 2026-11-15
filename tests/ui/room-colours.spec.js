// room-colours.spec.js — the colour, border and icon of a room on the reduced home.
//
//   npm run test:ui
//
// The rule is a state readout, not decoration: blue means the radiator is off,
// orange means it is on, and a Timed room is black between periods even if its
// relay is still on. The pill border adopts the text colour, or stays neutral
// grey when the text is black; the background is a three-quarters-of-the-way-
// to-white tint of the same colour, except the neutral default (a Timed gap),
// which mixes that grey only half-way so the pill still reads as grey.
// An Off room is told apart by its fainter text alone: it wears exactly the
// neutral pill a Timed room wears between periods — same border, same
// background — because a tint of its own, paler or darker, only drew the eye.
// The icon carries
// the finer mode: clock for Timed outside a period, running man inside one, A
// for Advance, and a plus for Boost and On. The map below is built so the
// result does not depend on the wall clock (the Timed rooms use a zero-length
// period, which the schedule projection treats as always active).

const { test, expect } = require('@playwright/test');
const { openApp, pushMap, waitForHome, chooseView } = require('./support/harness');
const MAP = require('./fixtures/map.json');

const BLACK = 'rgb(18, 52, 90)';   // the navy the site uses, not black
const BLUE = 'rgb(47, 117, 181)';
const ORANGE = 'rgb(232, 106, 51)';
const GREY = 'rgb(153, 153, 153)';
const DEFAULT_GREY = 'rgb(187, 187, 187)';
const BG_BLUE = 'rgb(203, 220, 236)';
const BG_ORANGE = 'rgb(249, 218, 204)';
const BG_DEFAULT = 'rgb(221, 221, 221)';

function room(name, relay) {
  return {
    name,
    sensor: `sensor-${name}`,
    relays: [`relay-${name}`],
    relay,
    linked: 'yes',
    status: 'good',
    temperature: 1900,
    battery: 80,
    statusMessage: '',
    relaysTotal: 1,
    relaysFailed: 0,
  };
}

function colourMap() {
  const map = JSON.parse(JSON.stringify(MAP));
  map.profile = 0;
  map.calendar = 'off';
  map.rooms = [
    room('Off Room', 'off'),
    room('On Off', 'off'),
    room('On Heat', 'on'),
    room('Timed Gap', 'on'),
    room('Timed Cool', 'off'),
    room('Timed Heat', 'on'),
    room('Timed Advance', 'on'),
    room('Boost Room', 'on'),
    {
      name: 'Outside',
      sensor: 'test-outside',
      relays: [],
      relay: 'off',
      linked: 'yes',
      status: 'good',
      temperature: 500,
      battery: 51,
      statusMessage: '',
      relaysTotal: 0,
      relaysFailed: 0,
    },
  ];
  map.profiles = [{
    name: 'Weekday',
    rooms: {
      'Off Room': { mode: 'off', target: 0, periods: [] },
      'On Off': { mode: 'on', target: 21, periods: [] },
      'On Heat': { mode: 'on', target: 22, periods: [] },
      'Timed Gap': { mode: 'timed', target: 21, periods: [] },
      'Timed Cool': { mode: 'timed', target: 21, periods: [{ on: '00:00', off: '00:00', temp: '21.0' }] },
      'Timed Heat': { mode: 'timed', target: 23, periods: [{ on: '00:00', off: '00:00', temp: '23.0' }] },
      'Timed Advance': { mode: 'timed', target: 23, advance: 'A', periods: [{ on: '00:00', off: '00:00', temp: '23.0' }] },
      'Boost Room': { mode: 'boost', target: 22, periods: [] },
      'Outside': { mode: 'off', target: 0, periods: [] },
    },
  }];
  return map;
}

test('room state colours and icons follow the radiator and mode', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openApp(page);
  await pushMap(page, colourMap());
  await waitForHome(page);
  await chooseView(page, 'simplified');
  await expect(page.locator('#simple-room-0')).toBeVisible();

  const name = index => page.locator(`#simple-room-${index}-name`);
  const temp = index => page.locator(`#simple-room-${index}-temp`);

  // Off mode: the fainter grey, and nothing else about the pill says Off.
  await expect(name(0)).toHaveCSS('color', GREY);
  await expect(temp(0)).toHaveCSS('color', GREY);

  // On, radiator off: blue.
  await expect(name(1)).toHaveCSS('color', BLUE);
  await expect(temp(1)).toHaveCSS('color', BLUE);

  // On, radiator on: orange.
  await expect(name(2)).toHaveCSS('color', ORANGE);
  await expect(temp(2)).toHaveCSS('color', ORANGE);

  // Timed between periods, even with the relay on: black.
  await expect(name(3)).toHaveCSS('color', BLACK);
  await expect(temp(3)).toHaveCSS('color', BLACK);

  // Timed inside a period: blue when off, orange when on.
  await expect(name(4)).toHaveCSS('color', BLUE);
  await expect(temp(4)).toHaveCSS('color', BLUE);
  await expect(name(5)).toHaveCSS('color', ORANGE);
  await expect(temp(5)).toHaveCSS('color', ORANGE);

  // The pill border adopts the text colour; the navy text of a Timed gap and
  // the faint grey of an Off room both keep the neutral border.
  const pill = index => page.locator(`#simple-room-${index}`);
  await expect(pill(0)).toHaveCSS('border-top-color', DEFAULT_GREY);
  await expect(pill(1)).toHaveCSS('border-top-color', BLUE);
  await expect(pill(2)).toHaveCSS('border-top-color', ORANGE);
  await expect(pill(3)).toHaveCSS('border-top-color', DEFAULT_GREY);
  await expect(pill(4)).toHaveCSS('border-top-color', BLUE);
  await expect(pill(5)).toHaveCSS('border-top-color', ORANGE);
  await expect(pill(7)).toHaveCSS('border-top-color', ORANGE);

  // Backgrounds are the same hue, three-quarters of the way to white — but
  // the neutral default under black text (a Timed gap) is mixed half-way, so
  // the grey still shows against the page gradient.
  await expect(pill(0)).toHaveCSS('background-color', BG_DEFAULT);

  // Off and a Timed gap are the same pill: the faint text is the only
  // difference, which is what keeps an out-of-system room from shouting.
  for (const edge of ['border-top-color', 'background-color']) {
    expect(await pill(0).evaluate((el, prop) => getComputedStyle(el)[prop], edge))
      .toBe(await pill(3).evaluate((el, prop) => getComputedStyle(el)[prop], edge));
  }
  await expect(pill(1)).toHaveCSS('background-color', BG_BLUE);
  await expect(pill(2)).toHaveCSS('background-color', BG_ORANGE);
  await expect(pill(3)).toHaveCSS('background-color', BG_DEFAULT);
  await expect(pill(4)).toHaveCSS('background-color', BG_BLUE);
  await expect(pill(5)).toHaveCSS('background-color', BG_ORANGE);
  await expect(pill(7)).toHaveCSS('background-color', BG_ORANGE);

  // The banner is not a room either: one card inset from the page edges,
  // with the room pills below it.
  await expect(page.locator('#top-bar')).toHaveCSS('border-radius', '18px');
  await expect(page.locator('#top-bar')).toHaveCSS('background-color', 'rgba(255, 255, 255, 0.96)');
  const bannerBox = await page.locator('#top-bar').evaluate(el => {
    const box = el.getBoundingClientRect();
    return { left: Math.round(box.left), width: Math.round(box.width) };
  });
  expect(bannerBox).toEqual({ left: 8, width: 374 });

  // Icons: Off kept, the plus for On and Boost, the clock between Timed
  // periods, the running man inside one, and the A for Advance.
  const iconMask = index => page.locator(`#simple-room-${index}-chip-icon`)
    .evaluate(el => el.style.mask || el.style.webkitMask || '');
  await expect.poll(() => iconMask(0)).toContain('off.svg');
  await expect.poll(() => iconMask(1)).toContain('plus.svg');
  await expect.poll(() => iconMask(2)).toContain('plus.svg');
  await expect.poll(() => iconMask(3)).toContain('clock.svg');
  await expect.poll(() => iconMask(4)).toContain('run.png');
  await expect.poll(() => iconMask(5)).toContain('run.png');
  await expect.poll(() => iconMask(6)).toContain('advance.svg');
  await expect.poll(() => iconMask(7)).toContain('plus.svg');
  await expect(page.locator('#simple-room-5-chip-icon')).toHaveCSS('background-color', ORANGE);
  await expect(page.locator('#simple-room-7-chip-icon')).toHaveCSS('background-color', ORANGE);
  // The Off glyph keeps the neutral grey of the pill it sits on.
  await expect(page.locator('#simple-room-0-chip-icon')).toHaveCSS('background-color', GREY);
  await expect(page.locator('#simple-room-0-chip')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await expect(page.locator('#simple-room-2-chip')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');

  // The single-room page uses the same rule through RenderRoom.
  await page.locator('#simple-room-2').click();
  await expect(page.locator('#room-2-name')).toHaveCSS('color', ORANGE);
  await expect(page.locator('#room-2-temp')).toHaveCSS('color', ORANGE);
  await expect.poll(() => page.locator('#room-2-chip-icon')
    .evaluate(el => el.style.mask || el.style.webkitMask || '')).toContain('plus.svg');
  await expect(page.locator('#room-2-chip-icon')).toHaveCSS('background-color', ORANGE);
  await page.locator('#simple-room-home').click();
  await expect(page.locator('#simple-room-0')).toBeVisible();

  expect(pageErrors).toEqual([]);
});
