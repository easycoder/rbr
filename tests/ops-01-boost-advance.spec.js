const { test, expect } = require('@playwright/test');
const { setSchedule } = require('./helpers/schedule');
// NOTE: run-ops-tests.sh patches the test-copy of controller.as so the boost
// duration is interpreted in seconds rather than minutes. Clicking "1 hr"
// therefore expires in 60 real seconds, which is what makes this test viable.

const LR_IDX = 1;
const LR_NAME = 'Living Room';

// Observing state via map-sim.json doesn't work: the controller only writes
// that file every 60s (controller.as:363-370). Instead these tests observe
// UI state through the DOM — the controller pushes MapHasChanged updates to
// UIs over MQTT within ~1s of a change, so the mode button's text / info
// reflect controller state quickly.

/**
 * Two periods both strictly in the past relative to wall-clock time, so
 * FindCurrentPeriod hits the wrap branch (PeriodNow==EventCount → 0).
 * That's the "overnight / cross-day" path the user flagged as historically
 * fragile.
 */
function pastWrapSchedule() {
    const d = new Date();
    const nowMin = d.getHours() * 60 + d.getMinutes();
    let u1 = nowMin - 120;
    let u2 = nowMin - 60;
    if (u1 < 5) u1 = 5;
    if (u2 <= u1) u2 = u1 + 5;
    u1 = Math.floor(u1 / 5) * 5;
    u2 = Math.floor(u2 / 5) * 5;
    return [
        [Math.floor(u1 / 60), u1 % 60, 180],
        [Math.floor(u2 / 60), u2 % 60, 200],
    ];
}

async function openMode(page, roomIdx) {
    await page.locator(`#room-${roomIdx}-mode-button`).click();
}

async function setTimed(page, roomIdx) {
    await openMode(page, roomIdx);
    await page.locator('#mode-timed').click();
    await expect(page.locator(`#room-${roomIdx}-mode-text`))
        .toHaveText('Timed', { timeout: 30000 });
}

test.describe('Living Room — Advance & Boost', () => {
    test.setTimeout(180000);

    test.beforeEach(async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });
    });

    test('advance toggles Timed↔Advance (cross-day wrap schedule)', async ({ page }) => {
        await page.goto('/index.html');
        await expect(page.locator(`#room-name-${LR_IDX}`)).toHaveText(LR_NAME, { timeout: 20000 });

        await setSchedule(page, LR_IDX, pastWrapSchedule());
        await setTimed(page, LR_IDX);

        // Click Advance → mode text becomes "Advance"
        await openMode(page, LR_IDX);
        await page.locator('#timed-advance').click();
        await expect(page.locator(`#room-${LR_IDX}-mode-text`))
            .toHaveText('Advance', { timeout: 30000 });

        // Click Advance again → toggles back to Timed
        await openMode(page, LR_IDX);
        await page.locator('#timed-advance').click();
        await expect(page.locator(`#room-${LR_IDX}-mode-text`))
            .toHaveText('Timed', { timeout: 30000 });
    });

    test('boost: 1-minute compressed round-trip', async ({ page }) => {
        await page.goto('/index.html');
        await expect(page.locator(`#room-name-${LR_IDX}`)).toHaveText(LR_NAME, { timeout: 20000 });

        await setSchedule(page, LR_IDX, pastWrapSchedule());
        await setTimed(page, LR_IDX);

        // Click Mode → "1 hr" boost. The patched controller treats 60 "minutes"
        // as 60 seconds, so the boost expires in ~1 min of real time.
        await openMode(page, LR_IDX);
        await page.locator('#boost-3').click();

        // Countdown should show 1-2 mins (since `until - now` is ~60000ms
        // right after the click; UI does `(until - now)/60000 + 1`).
        const info = page.locator(`#room-${LR_IDX}-mode-info`);
        await expect(info).toHaveText(/^[1-3]\s*mins?$/, { timeout: 30000 });
        await expect(page.locator(`#room-${LR_IDX}-mode-text`))
            .toHaveText('Boost', { timeout: 5000 });

        // Wait for boost to expire; controller reverts to timed.
        await expect(page.locator(`#room-${LR_IDX}-mode-text`))
            .toHaveText('Timed', { timeout: 120000 });
    });
});
