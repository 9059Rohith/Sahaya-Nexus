import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8100';

test('verified owner invites a registered member who explicitly accepts', async ({ page, request }) => {
  expect(new URL(apiURL).port).toBe('8100');
  const health = await request.get(`${apiURL}/api/v1/health`);
  expect((await health.json()).mode).toBe('test');
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const password = 'isolated-membership-test-password-123';
  const ownerEmail = `org-owner-${suffix}@example.org`;
  const memberEmail = `org-member-${suffix}@example.org`;
  const adminEmail = `org-admin-${suffix}@example.org`;
  async function register(name: string, email: string) {
    const response = await request.post(`${apiURL}/api/v1/auth/register`, { data: { name, email, password } });
    expect(response.status(), await response.text()).toBe(201);
    return (await response.json()).token as string;
  }
  const ownerToken = await register('Organization Owner', ownerEmail);
  const memberToken = await register('Organization Member', memberEmail);
  const adminToken = await register('Organization Admin', adminEmail);
  const promoted = spawnSync('python', ['-m', 'scripts.qa_promote_admin', adminEmail], {
    cwd: resolve(process.cwd(), '../backend'),
    env: { ...process.env, APP_MODE: 'test', DATABASE_URL: 'sqlite:///./qa-e2e.db' },
    encoding: 'utf8',
  });
  expect(promoted.status, promoted.stderr || promoted.stdout).toBe(0);
  const organizationName = `QA Food Team ${suffix}`;
  const created = await request.post(`${apiURL}/api/v1/organizations`, { headers: { Authorization: `Bearer ${ownerToken}` }, data: { name: organizationName, service_categories: ['FOOD'] } });
  expect(created.status(), await created.text()).toBe(201);
  const organizationID = (await created.json()).id as string;
  const verified = await request.post(`${apiURL}/api/v1/admin/organizations/${organizationID}/verify`, { headers: { Authorization: `Bearer ${adminToken}` }, data: { decision: 'VERIFIED', reason: 'Isolated QA identity review' } });
  expect(verified.ok(), await verified.text()).toBeTruthy();

  await page.goto('/login');
  await page.getByLabel('Email').fill(ownerEmail);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).first().click();
  await page.getByRole('button', { name: 'Organization', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Team members' })).toBeVisible();
  await page.getByLabel('Account email').fill(memberEmail);
  await page.getByRole('button', { name: 'Send in-app invitation' }).click();
  await expect(page.getByText(memberEmail)).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();

  await page.getByLabel('Email').fill(memberEmail);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await expect(page.getByLabel('Email')).toHaveValue(memberEmail);
  await page.getByRole('button', { name: 'Sign in' }).first().click();
  await expect(page.getByRole('heading', { name: 'How can Sahaya help?' })).toBeVisible();
  await page.getByRole('button', { name: 'Organization', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Organization invitations' })).toBeVisible();
  await page.getByRole('button', { name: 'Join organization' }).click();
  await expect(page.getByRole('button', { name: 'Join organization' })).toHaveCount(0);
  await expect(page.locator('.org-row strong').filter({ hasText: organizationName })).toBeVisible();
  const mine = await request.get(`${apiURL}/api/v1/organizations/mine`, { headers: { Authorization: `Bearer ${memberToken}` } });
  expect((await mine.json())[0].membership_role).toBe('MEMBER');
});
