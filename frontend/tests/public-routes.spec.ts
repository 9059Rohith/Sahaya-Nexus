import { expect, test } from '@playwright/test';

test('public homepage leads to separate sign-in and sign-up pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Public support, made accountable.' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Public navigation' })).toBeVisible();
  await expect(page.locator('#auth-form')).toHaveCount(0);

  await page.getByRole('link', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await expect(page.getByLabel('Email')).toBeVisible();

  await page.locator('.auth-switch').getByRole('link', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/signup$/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
  await expect(page.getByLabel('Name')).toBeVisible();
  await page.getByRole('button', { name: 'Show password' }).click();
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('type', 'text');
});
