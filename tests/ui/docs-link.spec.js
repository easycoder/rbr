// docs-link.spec.js — Find out more opens the documentation.
//
//   npm run test:ui
//
// The documentation is published at /docs/ beside the site's own page, so the
// button is a plain link rather than a new window or a script. What this guards
// is that the section named "Find out more" still offers it, and that it points
// at the reader's address rather than at the repository or the app.

const { test, expect } = require('@playwright/test');

test('Find out more links to the documentation on this site', async ({ page }) => {
  await page.goto('/index.html');
  const link = page.locator('#contact').getByRole('link', { name: 'Read the documentation' });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('href', '/docs/');
});
