const { test, expect } = require('@playwright/test');

test.describe('Rename Room', () => {
    test.setTimeout(90000);

    test('rename "Unnamed" room to "Kitchen"', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for the room to appear (created by previous test)
        const roomName = page.locator('#room-name-0');
        await expect(roomName).toBeVisible({ timeout: 20000 });
        await expect(roomName).toHaveText('Unnamed');

        // Click the edit icon on the room row
        await page.locator('#room-tools-0').click();

        // Room tools menu: click "Edit this room"
        const editButton = page.locator('#button-edit');
        await expect(editButton).toBeVisible({ timeout: 5000 });
        await editButton.click();

        // Room editor menu: click "Edit the room name"
        const nameButton = page.locator('#button-name');
        await expect(nameButton).toBeVisible({ timeout: 5000 });
        await nameButton.click();

        // Name dialog: clear input and type "Kitchen"
        const dialogInput = page.locator('#dialog-input');
        await expect(dialogInput).toBeVisible({ timeout: 5000 });
        await dialogInput.fill('Kitchen');

        // Click OK
        await page.locator('#dialog-button1').click();

        // Wait for the UI to update — the room name should now be "Kitchen"
        await expect(roomName).toHaveText('Kitchen', { timeout: 15000 });
    });
});
