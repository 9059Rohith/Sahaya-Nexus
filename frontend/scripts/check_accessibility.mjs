import { chromium } from '@playwright/test';
import axe from 'axe-core';

const browser = await chromium.launch({ headless: true });
try {
  for (const language of ['en', 'hi', 'ta', 'ml']) {
    const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.locator('#auth-language').selectOption(language);
    await page.addScriptTag({ content: axe.source });
    const result = await page.evaluate(() => window.axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    }));
    if (result.violations.length) {
      console.error(language, JSON.stringify(result.violations.map(item => ({
        id: item.id, impact: item.impact, nodes: item.nodes.map(node => node.target),
      })), null, 2));
      throw new Error(`${language}: ${result.violations.length} accessibility violations`);
    }
    console.log(`${language}: no automated WCAG A/AA violations on public page`);
    await page.close();
  }
} finally {
  await browser.close();
}
