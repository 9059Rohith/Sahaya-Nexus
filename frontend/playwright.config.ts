import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL;
if (!baseURL || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname) || new URL(baseURL).port === '3000') {
  throw new Error('Set E2E_BASE_URL to an isolated local test installation (never the live port 3000).');
}

export default defineConfig({
  testDir: './tests',
  use: { baseURL, ...devices['Desktop Chrome'] },
  reporter: 'list',
  retries: 0,
});
