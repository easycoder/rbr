// demo-mode.spec.js — the no-credentials path, which is what a first-time
// visitor gets.
//
// demo-map.json is disk-shaped: the controller strips the derived relay counts
// before writing map.json, so the demo file has no relaysTotal. The renderer
// used to read an absent total as 0, which marked every room unwired: each
// card said "No radiator assigned" and nothing called for heat, even though
// the map sets relay "on" for four rooms. That became visible on 2026-10-26
// when `unwired` started gating `calling`; the live path was never affected
// because the controller's reply carries the field.
//
// The renderer now counts the room's own relays when the total is absent.
// This spec pins the demo page a visitor actually sees, including the About
// sheet that demo mode opens over it.

const { test, expect } = require('@playwright/test');
const { openDemo } = require('./support/harness');

test('demo mode renders the baked map with its rooms calling', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));

  await openDemo(page);

  // Demo mode opens the About sheet so a first-time visitor sees what RBR is.
  // Closing it is a real gesture on the sheet chrome, not a direct style poke.
  await expect(page.locator('#sheet-title')).toHaveText('About');
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'auto');
  await page.locator('#sheet-close-btn').click();
  await expect(page.locator('#sheet-root')).toHaveCSS('pointer-events', 'none');

  // Four demo rooms have relay "on" and none of them carries relaysTotal.
  await expect(page.locator('#summary-title')).toHaveText('4 rooms calling for heat');
  await expect(page.locator('#room-0-name')).toHaveText('Kitchen');
  await expect(page.locator('#room-0-heating-tag')).toBeVisible();
  await expect(page.locator('#room-3-heating-tag')).toBeHidden();

  // The regression's visible symptom: no card may claim it has no radiator.
  const warnings = await page.locator('[id$="-warn-text"]').allTextContents();
  expect(warnings).not.toContain('No radiator assigned');

  expect(pageErrors).toEqual([]);
});
