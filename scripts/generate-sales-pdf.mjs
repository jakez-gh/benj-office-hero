/**
 * Generate a PDF copy of the sales deck from its HTML source.
 *
 * Uses Playwright (already installed in apps/admin-web) to open the HTML
 * file via a file:// URL, wait for images to load, then export A4 landscape PDF.
 *
 * Usage (from repo root):
 *   node scripts/generate-sales-pdf.mjs
 *
 * Output:
 *   docs/sales/office-hero-sales-deck.pdf
 *
 * Prerequisites:
 *   pnpm install --filter admin-web  (installs @playwright/test)
 *   npx playwright install chromium  (from apps/admin-web/)
 */

import { chromium } from '@playwright/test';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const HTML_PATH = resolve(REPO_ROOT, 'docs', 'sales', 'sales-deck.html');
const PDF_PATH  = resolve(REPO_ROOT, 'docs', 'sales', 'office-hero-sales-deck.pdf');

if (!existsSync(HTML_PATH)) {
  console.error(`ERROR: Source file not found: ${HTML_PATH}`);
  process.exit(1);
}

console.log('Launching Chromium…');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

// Load the HTML using a file:// URL so relative image paths resolve correctly
const fileUrl = `file://${HTML_PATH.replace(/\\/g, '/')}`;
console.log(`Loading: ${fileUrl}`);
await page.goto(fileUrl, { waitUntil: 'load' });

// Wait for all images to finish loading (screenshots embedded in slides)
await page.waitForFunction(() => {
  const imgs = Array.from(document.querySelectorAll('img'));
  return imgs.every(img => img.complete);
}, { timeout: 15_000 });

// Small settle delay for layout/fonts
await new Promise(r => setTimeout(r, 500));

console.log(`Generating PDF → ${PDF_PATH}`);
await page.pdf({
  path: PDF_PATH,
  format: 'A4',
  landscape: true,
  printBackground: true,
  margin: { top: '0', right: '0', bottom: '0', left: '0' },
});

await browser.close();
console.log('Done.');
