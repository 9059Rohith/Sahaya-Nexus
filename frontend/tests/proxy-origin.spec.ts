import { expect, test } from '@playwright/test';

test('HTTPS proxy accepts its public origin and rejects another origin', async ({ request }) => {
  const headers = {
    Host: 'help.sahaya.test',
    'X-Forwarded-Proto': 'https',
    Origin: 'https://help.sahaya.test',
  };
  const allowed = await request.post('/api/v1/auth/login', { headers, data: {} });
  expect(allowed.status()).toBe(422);

  const denied = await request.post('/api/v1/auth/login', {
    headers: { ...headers, Origin: 'https://other.test' },
    data: {},
  });
  expect(denied.status()).toBe(403);
});
