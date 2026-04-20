const { test, expect } = require('@playwright/test');

test.describe('Add Temporary Room', () => {

    test('add a temporary room after Living Room', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for Living Room to appear (from previous test)
        await expect(page.locator('#room-name-1')).toHaveText('Living Room', { timeout: 20000 });

        // Add a room via the hamburger menu
        await page.locator('#hamburger-icon').click();
        const addButton = page.locator('#button-add');
        await expect(addButton).toBeVisible({ timeout: 5000 });
        await addButton.click();

        // New room should appear as "Unnamed" at index 2
        await expect(page.locator('#room-name-2')).toHaveText('Unnamed', { timeout: 15000 });

        // Verify we now have 3 rooms
        await expect(page.locator('[id^="room-name-"]')).toHaveCount(3);
    });
});
