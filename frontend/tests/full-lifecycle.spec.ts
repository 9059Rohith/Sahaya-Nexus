import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const apiURL = process.env.E2E_API_URL || 'http://127.0.0.1:8100';
const databaseURL = process.env.E2E_DB_URL || 'sqlite:///./qa-e2e.db';

test('browser intake reaches confirmed impact through real API and isolated database', async ({ page, request }) => {
  expect(new URL(apiURL).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  expect(new URL(apiURL).port).toBe('8100');
  expect(databaseURL).toBe('sqlite:///./qa-e2e.db');
  const health = await request.get(`${apiURL}/api/v1/health`);
  expect(health.ok()).toBeTruthy();
  expect((await health.json()).mode).toBe('test');

  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const password = 'isolated-browser-test-password-123';
  const citizenEmail = `lifecycle-citizen-${suffix}@example.org`;
  const orgEmail = `lifecycle-org-${suffix}@example.org`;
  const adminEmail = `lifecycle-admin-${suffix}@example.org`;
  const api = (path: string) => `${apiURL}/api/v1${path}`;
  const baseline = await request.get(api('/impact'));
  const baselineImpact = await baseline.json() as { verified_outcomes: number; by_category: Record<string, { units: Record<string, number> }> };
  const initialOutcomes = baselineImpact.verified_outcomes;
  const initialMeals = baselineImpact.by_category.FOOD?.units.meals || 0;
  async function register(name: string, email: string): Promise<string> {
    const response = await request.post(api('/auth/register'), { data: { name, email, password } });
    expect(response.status(), await response.text()).toBe(201);
    return (await response.json()).token as string;
  }
  const citizenToken = await register('Lifecycle Citizen', citizenEmail);
  const orgToken = await register('Lifecycle Organization', orgEmail);
  const adminToken = await register('Lifecycle Operator', adminEmail);
  const backendDirectory = resolve(process.cwd(), '../backend');
  const promoted = spawnSync('python', ['-m', 'scripts.qa_promote_admin', adminEmail], {
    cwd: backendDirectory,
    env: { ...process.env, APP_MODE: 'test', DATABASE_URL: databaseURL },
    encoding: 'utf8',
  });
  expect(promoted.status, promoted.stderr || promoted.stdout).toBe(0);
  const citizen = { Authorization: `Bearer ${citizenToken}` };
  const org = { Authorization: `Bearer ${orgToken}` };
  const admin = { Authorization: `Bearer ${adminToken}` };
  async function post(path: string, headers: Record<string, string>, data: object, status = 200) {
    const response = await request.post(api(path), { headers, data });
    expect(response.status(), await response.text()).toBe(status);
    return response.json();
  }
  async function get(path: string, headers: Record<string, string>) {
    const response = await request.get(api(path), { headers });
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }

  const organization = await post('/organizations', org, { name: `Lifecycle Food Team ${suffix}`, service_categories: ['FOOD'] }, 201);
  const resource = await post(`/organizations/${organization.id}/resources`, org, {
    title: 'Meal pickup capacity', category: 'FOOD', capacity: 100, service_radius_km: 25,
    latitude: 10.0, longitude: 76.0,
  }, 201);
  await post(`/admin/organizations/${organization.id}/verify`, admin, { decision: 'VERIFIED', reason: 'Isolated test organization review complete' });

  await page.goto('/login');
  await page.getByLabel('Email').fill(citizenEmail);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).first().click();
  await expect(page.getByRole('heading', { name: 'How can Sahaya help?' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Description' }).fill('I have 60 meals available until tonight for collection.');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByLabel('Category')).toHaveValue('FOOD');
  await expect(page.getByLabel('Quantity')).toHaveValue('60');
  await page.getByLabel('Location', { exact: true }).fill('Central Kochi');
  await page.getByLabel('Latitude').fill('10.01');
  await page.getByLabel('Longitude').fill('76.01');
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const localDeadline = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
  await page.getByLabel('Safe until').fill(localDeadline);
  await page.getByRole('button', { name: 'Submit request' }).click();
  await expect(page.getByRole('heading', { name: /I have 60 meals available/ })).toBeVisible();
  const needs = await get('/requests', citizen) as { id: string; quantity: number; category: string }[];
  const need = needs.find(item => item.quantity === 60 && item.category === 'FOOD');
  expect(need).toBeTruthy();
  const requestID = need!.id;
  await page.getByLabel('Write a message').fill('The meals are available at the reception desk.');
  await page.getByRole('button', { name: 'Send message' }).click();
  await expect(page.getByText('The meals are available at the reception desk.')).toBeVisible();

  for (const stage of ['UNDERSTANDING', 'VALIDATION', 'VERIFICATION']) {
    await post(`/admin/requests/${requestID}/transition`, admin, { to_status: stage, reason: 'Isolated test operator reviewed request' });
  }
  await post(`/admin/requests/${requestID}/verify`, admin, { decision: 'VERIFIED', reason: 'Isolated test requester and details confirmed' });
  for (const stage of ['PRIORITIZATION', 'MATCHING']) {
    await post(`/admin/requests/${requestID}/transition`, admin, { to_status: stage, reason: 'Isolated test verified request advanced' });
  }
  const matches = await get(`/matching/${requestID}`, admin) as { id: string }[];
  expect(matches.some(match => match.id === resource.id)).toBeTruthy();
  await post(`/admin/requests/${requestID}/assign`, admin, { resource_id: resource.id, reason: 'Isolated test verified capacity and proximity' });
  await post(`/requests/${requestID}/messages`, org, { body: 'Our verified collection team is on the way.' }, 201);
  await page.getByRole('button', { name: 'Refresh messages' }).click();
  await expect(page.getByText('Our verified collection team is on the way.')).toBeVisible();
  for (const action of ['accept', 'start', 'arrive']) await post(`/assignments/${requestID}/${action}`, org, {});
  await post(`/assignments/${requestID}/complete`, org, { summary: 'Isolated test meals collected', impact_value: 60, impact_unit: 'meals' });
  await post(`/requests/${requestID}/feedback`, citizen, { answer: 'YES', comment: 'Meals collected' });
  await post(`/admin/requests/${requestID}/record-impact`, admin, {});
  const finalRequest = await get(`/requests/${requestID}`, citizen) as { status: string };
  expect(finalRequest.status).toBe('IMPACT_RECORDED');

  await page.reload();
  await page.getByRole('button', { name: 'Impact', exact: true }).click();
  await expect(page.locator('.impact-total strong')).toHaveText(String(initialOutcomes + 1));
  const finalImpact = await request.get(api('/impact'));
  expect((await finalImpact.json()).by_category.FOOD.units.meals).toBe(initialMeals + 60);
});
