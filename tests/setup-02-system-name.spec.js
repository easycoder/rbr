const { test, expect } = require('@playwright/test');

test.describe('System Name', () => {

    test('rename system from "New System" to "RBR Test System"', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for screen to be ready
        await page.waitForEvent('console', {
            predicate: msg => msg.text().includes('Screen is ready'),
            timeout: 20000,
        });

        // System name should show "New System" (from template map)
        await expect(page.locator('#system-name')).toHaveText('New System', { timeout: 15000 });

        // Click the hamburger to open the main menu
        await page.locator('#hamburger-icon').click();

        // Click "Set the system name"
        const getNameButton = page.locator('#button-getname');
        await expect(getNameButton).toBeVisible({ timeout: 5000 });
        await getNameButton.click();

        // Fill in the new name
        const nameInput = page.locator('#getname-input');
        await expect(nameInput).toBeVisible({ timeout: 5000 });
        await nameInput.fill('RBR Test System');

        // Click OK
        await page.locator('#getname-ok').click();

        // Verify the system name updated
        await expect(page.locator('#system-name')).toHaveText('RBR Test System', { timeout: 15000 });
    });
});
