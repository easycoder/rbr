const { test, expect } = require('@playwright/test');

test.describe('Room Devices', () => {

    test('assign thermometer and radiator to Kitchen', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for the Kitchen room to appear (created and renamed by previous tests)
        const roomName = page.locator('#room-name-0');
        await expect(roomName).toBeVisible({ timeout: 20000 });
        await expect(roomName).toHaveText('Kitchen');

        // Click the edit icon on the room row
        await page.locator('#room-tools-0').click();

        // Room tools menu: click "Edit this room"
        const editButton = page.locator('#button-edit');
        await expect(editButton).toBeVisible({ timeout: 5000 });
        await editButton.click();

        // Room editor menu: click "Edit device parameters"
        const devicesButton = page.locator('#button-devices');
        await expect(devicesButton).toBeVisible({ timeout: 5000 });
        await devicesButton.click();

        // --- Devices dialog ---

        // Set the thermometer sensor ID
        const sensorInput = page.locator('#dialog-input');
        await expect(sensorInput).toBeVisible({ timeout: 5000 });
        await sensorInput.fill('Kitchen-thermometer');

        // Select relay type: Zigbee
        const relayType = page.locator('#relayType');
        await relayType.selectOption('Zigbee');

        // Set the relay address
        const relayList = page.locator('#dialog-relayList');
        await relayList.fill('Kitchen-radiator');

        // Check the "linked" checkbox
        const linkedCheckbox = page.locator('#dialog-linked');
        await linkedCheckbox.check();

        // Click Save
        await page.locator('#dialog-button1').click();

        // Wait for the UI to refresh with the updated room
        await expect(roomName).toHaveText('Kitchen', { timeout: 15000 });

        // Verify the room row is still visible with the correct name
        await expect(page.locator('#room-0')).toBeVisible();
    });
});
