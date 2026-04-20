const { test, expect } = require('@playwright/test');

test.describe('Profile Name', () => {

    test('rename profile from "Default" to "Normal"', async ({ page }) => {
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });

        await page.goto('/index.html');

        // Wait for screen to be ready
        await page.waitForEvent('console', {
            predicate: msg => msg.text().includes('Screen is ready'),
            timeout: 20000,
        });

        // Profile button should show "Default"
        const profileButton = page.locator('#profile-button');
        await expect(profileButton).toContainText('Default', { timeout: 15000 });

        // Click the profile button to open profiles page
        await profileButton.click();

        // Click the edit icon for the first profile (index 0)
        const editIcon = page.locator('#profile-edit-0');
        await expect(editIcon).toBeVisible({ timeout: 5000 });
        await editIcon.click();

        // Rename dialog: clear and type "Normal"
        const dialogInput = page.locator('#dialog-input');
        await expect(dialogInput).toBeVisible({ timeout: 5000 });
        await dialogInput.fill('Normal');

        // Click OK
        await page.locator('#dialog-button1').click();

        // The profile select button should now show "Normal"
        await expect(page.locator('#profile-select-0')).toHaveText('Normal', { timeout: 5000 });

        // Click OK to save and exit the profiles page
        await page.locator('#profiles-ok-button').click();

        // Back on the main screen, profile button should show "Normal"
        await expect(profileButton).toContainText('Normal', { timeout: 15000 });
    });
});
