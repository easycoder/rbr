const { test, expect } = require('@playwright/test');

test.describe('Guest Bedroom', () => {

    test('add and configure Guest Bedroom', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for existing rooms to appear
        await expect(page.locator('#room-name-3')).toHaveText('Main Bedroom', { timeout: 20000 });

        // --- Add a room ---
        await page.locator('#hamburger-icon').click();
        const addButton = page.locator('#button-add');
        await expect(addButton).toBeVisible({ timeout: 5000 });
        await addButton.click();

        // New room should appear as "Unnamed" at index 4
        await expect(page.locator('#room-name-4')).toHaveText('Unnamed', { timeout: 15000 });

        // --- Rename to "Guest Bedroom" ---
        await page.locator('#room-tools-4').click();
        await expect(page.locator('#button-edit')).toBeVisible({ timeout: 5000 });
        await page.locator('#button-edit').click();

        await expect(page.locator('#button-name')).toBeVisible({ timeout: 5000 });
        await page.locator('#button-name').click();

        const dialogInput = page.locator('#dialog-input');
        await expect(dialogInput).toBeVisible({ timeout: 5000 });
        await dialogInput.fill('Guest Bedroom');
        await page.locator('#dialog-button1').click();

        await expect(page.locator('#room-name-4')).toHaveText('Guest Bedroom', { timeout: 15000 });

        // --- Configure devices ---
        await page.locator('#room-tools-4').click();
        await expect(page.locator('#button-edit')).toBeVisible({ timeout: 5000 });
        await page.locator('#button-edit').click();

        await expect(page.locator('#button-devices')).toBeVisible({ timeout: 5000 });
        await page.locator('#button-devices').click();

        const sensorInput = page.locator('#dialog-input');
        await expect(sensorInput).toBeVisible({ timeout: 5000 });
        await sensorInput.fill('Guest-Bedroom-thermometer');

        await page.locator('#relayType').selectOption('Zigbee');
        await page.locator('#dialog-relayList').fill('Guest-Bedroom-radiator');
        await page.locator('#dialog-linked').check();
        await page.locator('#dialog-button1').click();

        // Verify all rooms are showing
        await expect(page.locator('#room-name-0')).toHaveText('Kitchen', { timeout: 15000 });
        await expect(page.locator('#room-name-1')).toHaveText('Living Room');
        await expect(page.locator('#room-name-2')).toHaveText('Unnamed');
        await expect(page.locator('#room-name-3')).toHaveText('Main Bedroom');
        await expect(page.locator('#room-name-4')).toHaveText('Guest Bedroom');
        await expect(page.locator('[id^="room-name-"]')).toHaveCount(5);
    });
});
