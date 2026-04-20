const { test, expect } = require('@playwright/test');
const { setSchedule, setTimedMode } = require('./helpers/schedule');

test.describe('Room Schedules', () => {
    test.setTimeout(120000);

    test('set timing schedules and timed mode for all rooms', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for all 4 rooms
        await expect(page.locator('#room-name-3')).toHaveText('Guest Bedroom', { timeout: 20000 });

        // Kitchen: 6 periods
        await setSchedule(page, 0, [
            [7, 0, 210], [9, 0, 150], [12, 30, 215],
            [14, 0, 150], [18, 0, 220], [20, 0, 150],
        ]);
        await expect(page.locator('#room-name-0')).toHaveText('Kitchen', { timeout: 15000 });

        // Living Room: 2 periods
        await setSchedule(page, 1, [
            [18, 0, 240], [23, 0, 150],
        ]);
        await expect(page.locator('#room-name-1')).toHaveText('Living Room', { timeout: 15000 });

        // Main Bedroom: 4 periods
        await setSchedule(page, 2, [
            [7, 0, 210], [9, 0, 150], [22, 30, 230], [23, 30, 150],
        ]);
        await expect(page.locator('#room-name-2')).toHaveText('Main Bedroom', { timeout: 15000 });

        // Guest Bedroom: 4 periods
        await setSchedule(page, 3, [
            [7, 0, 210], [9, 0, 150], [22, 30, 220], [23, 30, 150],
        ]);
        await expect(page.locator('#room-name-3')).toHaveText('Guest Bedroom', { timeout: 15000 });

        // Set all rooms to timed mode
        await setTimedMode(page, 0);
        await setTimedMode(page, 1);
        await setTimedMode(page, 2);
        await setTimedMode(page, 3);

        // Verify all rooms still present
        await expect(page.locator('[id^="room-name-"]')).toHaveCount(4);
    });
});
