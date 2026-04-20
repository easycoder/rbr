const { test, expect } = require('@playwright/test');

test.describe('Add Room', () => {

    test('adding a room from empty map updates the UI', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for MQTT to connect and screen to render
        await page.waitForEvent('console', {
            predicate: msg => msg.text().includes('Screen is ready'),
            timeout: 20000,
        });

        // Verify no rooms are shown initially
        await expect(page.locator('#room-0')).not.toBeVisible({ timeout: 5000 });

        // Click the hamburger to open the main menu
        await page.locator('#hamburger-icon').click();

        // Wait for the menu to render and click "Add a room"
        const addButton = page.locator('#button-add');
        await expect(addButton).toBeVisible({ timeout: 5000 });
        await addButton.click();

        // The room row should appear after the controller responds
        const roomContainer = page.locator('#room-0');
        await expect(roomContainer).toBeVisible({ timeout: 15000 });

        // The room name should be "Unnamed" (from newroomspec.json)
        await expect(page.locator('#room-name-0')).toHaveText('Unnamed', { timeout: 5000 });

        // Key room elements are present
        await expect(page.locator('#room-temp-0')).toBeVisible();
        await expect(page.locator('#room-tools-0')).toBeVisible();
        await expect(page.locator('#room-status-0')).toBeVisible();

        // The system name should show "RBR Test System" (renamed in setup-02)
        await expect(page.locator('#system-name')).toHaveText('RBR Test System');

        // Only one room (no duplicates)
        await expect(page.locator('[id^="room-name-"]')).toHaveCount(1);
    });
});
