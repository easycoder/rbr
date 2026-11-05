// playwright.config.js — the UI suite.
//
//   npm run test:ui
//
// The page under test is the static PWA in new-ui/. It is served here from the
// repository root by tests/ui/serve.js, which also vends a fake credentials.json
// from memory so no file is written into new-ui/ and no real broker details are
// ever involved.
//
// There is no controller in this loop. The browser's MQTT client is replaced by
// a stub (tests/ui/support/browser-stub.js) and each spec decides what the
// controller "replies" — a valid map, a malformed one, silence, a disconnect.
// The run needs no broker, no controller, no PHP and no network beyond the
// first fetch of the pinned AllSpeak runtime.
//
// Chromium must be installed once per machine or CI runner:
//   npx playwright install chromium

const { defineConfig } = require('@playwright/test');

const PORT = 4173;

module.exports = defineConfig({
  testDir: './tests/ui',
  timeout: 60000,
  // One worker and no parallelism: the specs drive a single stubbed broker and
  // assert on ordered traffic, so interleaving would only add flakiness.
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    // sw.js is network-first and would cache responses behind the test's back.
    // The suite tests the page, not the service worker.
    serviceWorkers: 'block',
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `node tests/ui/serve.js ${PORT}`,
    url: `http://127.0.0.1:${PORT}/new-ui/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
