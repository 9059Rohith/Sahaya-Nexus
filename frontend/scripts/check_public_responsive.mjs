import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: true });
try {
  for (const width of [320, 375, 768, 1024, 1440, 1920]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    if (dimensions.content > dimensions.viewport) {
      throw new Error(`Horizontal overflow at ${width}px: ${JSON.stringify(dimensions)}`);
    }
    console.log(`${width}px: no horizontal overflow`);
    await page.close();
  }
  const page = await browser.newPage();
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  const requestDraft = 'I need help with a blocked community entrance';
  await page.locator('#public-need-draft').fill(requestDraft);
  await page.locator('.public-draft button').click();
  const saved = await page.evaluate(() => localStorage.getItem('sahaya_draft'));
  if (saved !== requestDraft) throw new Error('Public request draft was not saved locally');
  console.log('Public request draft: saved locally');
  await page.close();
} finally {
  await browser.close();
}
