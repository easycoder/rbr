// profiles.spec.js — renaming a profile through the real sheet.
//
// The calendar stores profile *names*, not references. A rename that updated
// only profiles[].name would leave every day pointing at a profile that no
// longer exists, and the page and controller would both fall back to the
// selected profile in silence. The check is therefore the whole request: the
// profile, every day that named it, and the profile that was not touched.

const { test, expect } = require('@playwright/test');
const {
  openApp, pushMap, waitForHome, openProfileSheet, lastRequest, answerDialogs,
} = require('./support/harness');
const MAP = require('./fixtures/map.json');

function dayNames(calendar) {
  return calendar.map((entry, i) => entry[`day${i}-profile`]);
}

test('renaming a profile renames the days that name it in the same request', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  const answers = answerDialogs(page);
  answers.prompt = 'Weekday 2';

  await openApp(page);
  await pushMap(page, MAP);
  await waitForHome(page);
  await openProfileSheet(page);

  await page.locator('#profile-row-0-rename').click();
  await expect(page.locator('#profile-row-0-label')).toHaveText('Weekday 2');

  await page.locator('#profile-save-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  await expect.poll(() => lastRequest(page, 'Update Profiles')).not.toBeNull();
  const request = await lastRequest(page, 'Update Profiles');

  expect(request.profiles.map(profile => profile.name)).toEqual(['Weekday 2', 'Weekend']);
  expect(dayNames(request['calendar-data']).slice(0, 5)).toEqual(Array(5).fill('Weekday 2'));
  expect(dayNames(request['calendar-data']).slice(5)).toEqual(['Weekend', 'Weekend']);

  // The calendar's mapping is unchanged apart from the name it now uses, and
  // the profile that was not renamed is untouched.
  expect(request.profile).toBe(0);
  expect(request.profiles[1]).toEqual(MAP.profiles[1]);

  expect(pageErrors).toEqual([]);
});
