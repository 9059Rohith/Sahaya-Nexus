import { expect, test } from '@playwright/test';

const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8100';

test('reviewed request stays on device offline and sends only after explicit retry', async ({ page, context, request }) => {
  expect(new URL(apiURL).port).toBe('8100');
  const health = await request.get(`${apiURL}/api/v1/health`);
  expect((await health.json()).mode).toBe('test');
  const email = `offline-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`;
  const password = 'isolated-offline-test-password-123';
  const registered = await request.post(`${apiURL}/api/v1/auth/register`, { data: { name: 'Offline QA Citizen', email, password } });
  expect(registered.status(), await registered.text()).toBe(201);
  const token = (await registered.json()).token as string;

  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).first().click();
  await expect(page.getByRole('heading', { name: 'How can Sahaya help?' })).toBeVisible();
  const description = `A blocked public footpath requires repair ${Date.now()}`;
  await page.getByRole('textbox', { name: 'Description' }).fill(description);
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByLabel('Location', { exact: true }).fill('Central Kochi');
  await page.getByLabel('Category').selectOption('COMMUNITY');
  await context.setOffline(true);
  await page.getByRole('button', { name: 'Submit request' }).click();
  await expect(page.getByRole('heading', { name: 'Request saved on this device' })).toBeVisible();
  await expect(page.locator('.offline-queue blockquote')).toHaveText(description);
  await context.setOffline(false);
  const before = await request.get(`${apiURL}/api/v1/requests`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await before.json()) as unknown[]).toHaveLength(0);
  await page.getByRole('button', { name: 'Send now' }).click();
  await expect(page.getByRole('heading', { name: description })).toBeVisible();
  const after = await request.get(`${apiURL}/api/v1/requests`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await after.json()) as unknown[]).toHaveLength(1);
});
