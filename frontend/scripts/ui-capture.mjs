import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';

const url = new URL(process.argv[2] ?? 'http://127.0.0.1:3000/');
const output = await mkdtemp(join(tmpdir(), 'jagsi-ui-'));
const channel = process.env.JAGSI_BROWSER_CHANNEL ?? (process.platform === 'win32' ? 'msedge' : 'chromium');
const browser = await chromium.launch({ channel, headless: true });
try {
  for (const [width, height] of [[390, 844], [768, 1024], [1440, 900]]) {
    const page = await browser.newPage({ viewport: { width, height }, reducedMotion: 'reduce' });
    const response = await page.goto(url.href, { waitUntil: 'domcontentloaded' });
    if (!response?.ok()) throw new Error(`Could not render ${url}: HTTP ${response?.status()}`);
    await page.locator('main').first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const path = join(output, `${width}.png`);
    await page.screenshot({ path, fullPage: true, animations: 'disabled', timeout: 30000 });
    console.log(path);
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) {
      console.error(`Horizontal overflow at ${width}px`);
      process.exitCode = 1;
    }
    await page.close();
  }
} finally {
  await browser.close();
}
