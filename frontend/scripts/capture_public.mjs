import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'Welcome back' }).waitFor();
  const directory = resolve('../docs/screenshots');
  await mkdir(directory, { recursive: true });
  await page.screenshot({ path: resolve(directory, 'public-landing.png'), fullPage: true });
} finally {
  await browser.close();
}
