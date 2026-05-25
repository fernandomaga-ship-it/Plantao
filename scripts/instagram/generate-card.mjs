#!/usr/bin/env node
/**
 * Generates a 1080x1080 Instagram card PNG for today's AMIB topic.
 * Uses Playwright to render card-template.html with the topic data injected.
 *
 * Output: /tmp/instagram-card.png
 * Stdout: path to the generated PNG
 *
 * Usage: node generate-card.mjs [topic-index]
 *   topic-index: override the automatic rotation (0-based)
 */

import { chromium } from 'playwright';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dir = dirname(fileURLToPath(import.meta.url));

const topics = JSON.parse(readFileSync(join(__dir, 'topics.json'), 'utf8'));
const templatePath = join(__dir, 'card-template.html');
const outputPath = '/tmp/instagram-card.png';

// Determine today's topic by cycling through the list using the day-of-year
function getTodayIndex() {
  if (process.argv[2] !== undefined) return parseInt(process.argv[2], 10) % topics.length;
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((now - start) / 86_400_000);
  return dayOfYear % topics.length;
}

const idx = getTodayIndex();
const topic = topics[idx];

console.error(`[generate-card] Topic ${idx}: "${topic.titulo}"`);

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage();

await page.setViewportSize({ width: 1080, height: 1080 });

// Read template and inject data
const html = readFileSync(templatePath, 'utf8');
const injected = html.replace(
  'const data = window.__TOPIC_DATA__;',
  `const data = ${JSON.stringify({ ...topic, handle: process.env.IG_HANDLE || '@drfernandomaga' })};`
);

await page.setContent(injected, { waitUntil: 'networkidle' });
await page.screenshot({ path: outputPath, type: 'png', clip: { x: 0, y: 0, width: 1080, height: 1080 } });

await browser.close();

// Print output path + topic JSON for the post script
process.stdout.write(
  JSON.stringify({ imagePath: outputPath, topic }) + '\n'
);
