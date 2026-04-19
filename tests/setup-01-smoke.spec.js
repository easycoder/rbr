const { test, expect } = require('@playwright/test');

test.describe('RBR UI smoke tests', () => {

    test.beforeEach(async ({ page }) => {
        // Collect console output for debugging
        page.on('console', msg => {
            if (msg.type() === 'log') console.log('  [browser]', msg.text());
        });
    });

    test('page loads and has correct title', async ({ page }) => {
        await page.goto('/index.html');
        await expect(page).toHaveTitle('RBR UI');
    });

    test('rbr.as script is fetched and compiled', async ({ page }) => {
        let scriptStatus = 0;
        const errors = [];

        page.on('response', res => {
            if (res.url().includes('resources/as/rbr.as')) {
                scriptStatus = res.status();
            }
        });
        page.on('pageerror', err => errors.push(err.message));

        await page.goto('/index.html');
        // Wait for AllSpeak to fetch and compile rbr.as
        await page.waitForTimeout(5000);

        expect(scriptStatus).toBe(200);
        expect(errors).toEqual([]);
    });

    test('MQTT connects successfully', async ({ page }) => {
        await page.goto('/index.html');

        // Wait for the "MQTT Connected" log from rbr.as
        await page.waitForEvent('console', {
            predicate: msg => msg.text().includes('MQTT Connected'),
            timeout: 15000,
        });
    });

    test('main screen renders after MQTT connect', async ({ page }) => {
        await page.goto('/index.html');

        const screen = page.locator('#rbr-screen');
        await expect(screen).toBeVisible({ timeout: 15000 });
    });

    test('banner shows "Room By Room"', async ({ page }) => {
        await page.goto('/index.html');

        const banner = page.locator('#rbr-banner');
        await expect(banner).toBeVisible({ timeout: 15000 });
        await expect(banner).toHaveText('Room By Room');
    });

    test('key UI elements are rendered', async ({ page }) => {
        await page.goto('/index.html');

        await expect(page.locator('#mainpanel')).toBeVisible({ timeout: 15000 });
        await expect(page.locator('#system-name')).toBeVisible();
        await expect(page.locator('#profile-button')).toBeVisible();
        await expect(page.locator('#hamburger-icon')).toBeVisible();
        await expect(page.locator('#statistics-icon')).toBeVisible();
    });

    test('subtitle text is correct', async ({ page }) => {
        await page.goto('/index.html');

        const subtitle = page.locator('text=Intelligent heating when and where you need it');
        await expect(subtitle).toBeVisible({ timeout: 15000 });
    });

    test('no JavaScript errors on load', async ({ page }) => {
        const errors = [];
        page.on('pageerror', err => errors.push(err.message));

        await page.goto('/index.html');
        // Wait for the screen to fully render
        await page.locator('#rbr-screen').waitFor({ timeout: 15000 });

        expect(errors).toEqual([]);
    });
});
