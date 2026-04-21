/**
 * Helper functions for schedule/period editing in RBR Playwright tests.
 *
 * The period editor uses up/down arrow buttons:
 *   - Hour: ±1 per click (wraps 0-23, does NOT affect minutes)
 *   - Minute: ±5 per click (wraps 0-55, does NOT affect hours)
 *   - Temperature: ±0.5°C per click
 */

/**
 * Navigate to the timing schedule editor for a room.
 */
async function openScheduleEditor(page, roomIndex) {
    await page.locator(`#room-tools-${roomIndex}`).click();

    const editButton = page.locator('#button-edit');
    await editButton.waitFor({ state: 'visible', timeout: 5000 });
    await editButton.click();

    const timesButton = page.locator('#button-times');
    await timesButton.waitFor({ state: 'visible', timeout: 5000 });
    await timesButton.click();

    await page.locator('#edit-times').waitFor({ state: 'visible', timeout: 5000 });
}

/**
 * Click a button multiple times.
 */
async function clickN(locator, n) {
    for (let i = 0; i < n; i++) {
        await locator.click();
    }
}

/**
 * Delete all existing periods by repeatedly clicking the first one
 * and deleting it.
 */
async function deleteAllPeriods(page) {
    while (true) {
        const info = page.locator('#period-info-0');
        const visible = await info.isVisible().catch(() => false);
        if (!visible) break;

        // Click the period to open the editor
        await info.click();
        await page.locator('#period-delete').waitFor({ state: 'visible', timeout: 5000 });
        await page.locator('#period-delete').click();

        // Confirm deletion
        const yesButton = page.locator('#dialog-button1');
        await yesButton.waitFor({ state: 'visible', timeout: 5000 });
        await yesButton.click();

        await page.waitForTimeout(300);
    }
}

/**
 * Add a new period and set its values.
 * A new period starts at 00:00 with the inherited temperature (15.0°C default).
 *
 * @param {number} hour - target hour (0-23)
 * @param {number} minute - target minute (must be multiple of 5)
 * @param {number} temp - target temperature in tenths (e.g. 210 = 21.0°C)
 * @param {number} inheritedTemp - the starting temperature in tenths (default 150)
 */
async function addPeriod(page, hour, minute, temp, inheritedTemp = 150) {
    await page.locator('#edit-add-button').click();
    await page.waitForTimeout(300);

    // The new period is at 00:00 and sorted to index 0. Click it to edit.
    const periodInfo = page.locator('#period-info-0');
    await periodInfo.waitFor({ state: 'visible', timeout: 5000 });
    await periodInfo.click();
    await page.locator('#hour-text').waitFor({ state: 'visible', timeout: 5000 });

    // Set hour
    if (hour > 0) await clickN(page.locator('#hour-up'), hour);

    // Set minute
    const minuteClicks = minute / 5;
    if (minuteClicks > 0) await clickN(page.locator('#minute-up'), minuteClicks);

    // Set temperature
    const tempDiff = (temp - inheritedTemp) / 5;
    if (tempDiff > 0) await clickN(page.locator('#temp-up'), tempDiff);
    else if (tempDiff < 0) await clickN(page.locator('#temp-down'), -tempDiff);

    // Save this period
    await page.locator('#period-save').click();
    await page.waitForTimeout(300);
}

/**
 * Save the schedule and return to the main screen.
 */
async function saveSchedule(page) {
    await page.locator('#edit-save-button').click();
}

/**
 * Set a complete schedule for a room.
 * Deletes all existing periods, then adds new ones.
 * Each entry is [hour, minute, tempInTenths].
 */
async function setSchedule(page, roomIndex, schedule) {
    await openScheduleEditor(page, roomIndex);
    await deleteAllPeriods(page);

    // Add periods in time order (earliest first).
    // Each new period starts at 00:00 and sorts to index 0.
    // Adding in reverse order would put them in the right positions,
    // but since we always click index 0 to edit the just-added period,
    // adding in any order works — each period gets sorted after save.
    // Adding in forward order is simplest to read.
    const sorted = [...schedule].sort((a, b) => a[0] * 60 + a[1] - b[0] * 60 - b[1]);

    for (const [hour, minute, temp] of sorted) {
        await addPeriod(page, hour, minute, temp);
    }

    await saveSchedule(page);
}

/**
 * Set a room's mode to "timed" via the mode dialog.
 */
async function setTimedMode(page, roomIndex) {
    const modeButton = page.locator(`#room-${roomIndex}-mode-button`);
    await modeButton.scrollIntoViewIfNeeded();
    await modeButton.waitFor({ state: 'visible', timeout: 15000 });
    await modeButton.click();

    const timedButton = page.locator('#mode-timed');
    await timedButton.waitFor({ state: 'visible', timeout: 5000 });
    await timedButton.click();

    // Wait for the mode dialog to close and main screen to settle
    await page.waitForTimeout(1000);
    await page.locator(`#room-name-${roomIndex}`).waitFor({ state: 'visible', timeout: 15000 });
}

module.exports = { openScheduleEditor, addPeriod, deleteAllPeriods, saveSchedule, setSchedule, setTimedMode, clickN };
