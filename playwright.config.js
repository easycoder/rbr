const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: 'http://localhost:9000',
  },
});
