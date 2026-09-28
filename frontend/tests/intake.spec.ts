import { expect, test } from '@playwright/test';

test.beforeEach(async ({ request }) => {
  const response = await request.get('/api/v1/health');
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).mode).toBe('test');
});
test('citizen reviews and submits a real database request', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.org`;
  await page.setViewportSize({ width: 1586, height: 992 });
  await page.goto('/signup');
  await page.getByLabel('Name').fill('E2E Citizen');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill('E2E-local-password-123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'How can Sahaya help?' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'No requests yet' })).toBeVisible();
  await page.screenshot({ path: 'test-results/latest-dashboard.png' });

  await page.getByRole('textbox', { name: 'Description' }).fill('I have 60 meals left from an event and need collection tonight.');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { name: 'Review our interpretation' })).toBeVisible();
  await expect(page.getByLabel('Category')).toHaveValue('FOOD');
  await expect(page.getByLabel('Quantity')).toHaveValue('60');
  await page.getByLabel('Location', { exact: true }).fill('Central Kochi');
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const localDateTime = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  await page.getByLabel('Safe until').fill(localDateTime);
  await page.getByRole('button', { name: 'Submit request' }).click();
  await expect(page.getByRole('heading', { name: /I have 60 meals left/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Activity timeline' })).toBeVisible();
  await expect(page.getByText('Citizen submitted and confirmed the request')).toBeVisible();
});

test('mobile layout has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Public support, made accountable.' })).toBeVisible();
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await expect(page.getByRole('navigation', { name: 'Public navigation' }).getByRole('link', { name: 'Sign in' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Public navigation' }).getByRole('link', { name: 'Create account' })).toBeVisible();
  const widths = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
  expect(widths.content).toBeLessThanOrEqual(widths.viewport);
});
