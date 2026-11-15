// hero.spec.js — the marketing page's hero photo, which is one of three.
//
//   npm run test:ui
//
// index.html picks the photo with an inline script in <head>, before the
// stylesheet paints, so there is no flash of another one; styles.css carries
// the rules for the two non-default photos (`html[data-hero="mixed"] .hero`
// and `html[data-hero="alternate"] .hero`). The probability is overridden here,
// so the spec says which photo rather than hoping for it: one draw, with the
// default up to 0.4, mixed from 0.4 to 0.8, and the alternate above 0.8.
//
// What this guards is what a swap to a third file can break: a photo never
// being referenced (a rule and an inline script that drift), an asset 404ing
// (they have to be in assets/, the only directory of the page's own files that
// deploy.sh copies), the thresholds drifting away from 40/40/20, and the
// accessible name still describing the first couple.

const { test, expect } = require('@playwright/test');

const PHOTOS = {
  default: 'living-room-hero.jpg',
  mixed: 'mixed-ethnicity.jpg',
  alternate: 'alternate-ethnicity.jpg',
};

const LABELS = {
  default: 'A mature couple relaxing together in a bright, comfortable living room',
  mixed: 'A middle-aged couple relaxing together in a bright, comfortable living room',
  alternate: 'A mature Black couple relaxing together in a bright, comfortable living room',
};

// Load the page with Math.random pinned, and report what it did.
async function load(page, random) {
  const fetches = [];
  page.on('response', response => {
    const name = response.url().split('/').pop();
    if (Object.values(PHOTOS).includes(name)) fetches.push(`${name} ${response.status()}`);
  });
  await page.addInitScript(value => { Math.random = () => value; }, random);
  await page.goto('/index.html');
  await page.waitForLoadState('load');
  return {
    fetches,
    variant: await page.evaluate(() => document.documentElement.getAttribute('data-hero')),
    photo: await page.locator('.hero').evaluate(el => getComputedStyle(el).backgroundImage),
    label: await page.locator('.hero-photo').getAttribute('aria-label'),
  };
}

// Every variant fetches exactly its own photo, and describes it.
function expectOnly(seen, variant) {
  const others = Object.values(PHOTOS).filter(name => name !== PHOTOS[variant]);
  expect(seen.photo).toContain(PHOTOS[variant]);
  expect(seen.label).toBe(LABELS[variant]);
  expect(seen.fetches).toContain(`${PHOTOS[variant]} 200`);
  for (const other of others) expect(seen.fetches.join()).not.toContain(other);
}

test('the lower 40% is the default couple', async ({ page }) => {
  const seen = await load(page, 0.2);
  expect(seen.variant).toBeNull();
  expectOnly(seen, 'default');
});

test('the middle 40% is the mixed-ethnicity couple', async ({ page }) => {
  const seen = await load(page, 0.6);
  expect(seen.variant).toBe('mixed');
  expectOnly(seen, 'mixed');
});

test('the top 20% is the Black couple, framed like the other two', async ({ page }) => {
  const seen = await load(page, 0.9);
  expect(seen.variant).toBe('alternate');
  expectOnly(seen, 'alternate');
  // All three share the phone crop, which is what keeps the framing the same
  // whichever one a visit gets.
  await expect(page.locator('.hero')).toHaveCSS('background-size', 'auto 360px');
});
