const { test, expect } = require('@playwright/test');

test.describe('Delete Temporary Room', () => {

    test('delete the temporary "Unnamed" room', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for all 5 rooms to appear
        await expect(page.locator('#room-name-4')).toHaveText('Guest Bedroom', { timeout: 20000 });

        // Verify the temp room is at index 2
        await expect(page.locator('#room-name-2')).toHaveText('Unnamed');

        // Click the edit icon on the temp room
        await page.locator('#room-tools-2').click();

        // Click "Delete this room"
        const deleteButton = page.locator('#button-delete');
        await expect(deleteButton).toBeVisible({ timeout: 5000 });
        await deleteButton.click();

        // Confirm deletion — click "Yes"
        const yesButton = page.locator('#dialog-button1');
        await expect(yesButton).toBeVisible({ timeout: 5000 });
        await yesButton.click();

        // After deletion, rooms should shift: 4 rooms remaining
        await expect(page.locator('[id^="room-name-"]')).toHaveCount(4, { timeout: 15000 });

        // Verify the correct rooms remain in order
        await expect(page.locator('#room-name-0')).toHaveText('Kitchen');
        await expect(page.locator('#room-name-1')).toHaveText('Living Room');
        await expect(page.locator('#room-name-2')).toHaveText('Main Bedroom');
        await expect(page.locator('#room-name-3')).toHaveText('Guest Bedroom');
    });
});
