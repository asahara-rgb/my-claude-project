#!/usr/bin/env node
// HTML/SVG で描いた原稿ページを PNG にレンダリングする（Playwright + Chromium）。
//   node tools/render_pages.mjs <srcDir> <outDir> [--scale 1]
// srcDir 内の *.html を名前順に、各ページの <html data-width data-height>（省略時 1600x2560）で撮影。
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';

const require = createRequire(import.meta.url);
function loadPlaywright() {
  try { return require('playwright'); } catch {}
  const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
  return require(path.join(globalRoot, 'playwright'));
}

const [src, out, ...rest] = process.argv.slice(2);
if (!src || !out) {
  console.error('usage: node tools/render_pages.mjs <srcDir> <outDir> [--scale N]');
  process.exit(2);
}
const scaleIdx = rest.indexOf('--scale');
const scale = scaleIdx >= 0 ? Number(rest[scaleIdx + 1]) : 1;

const { chromium } = loadPlaywright();
fs.mkdirSync(out, { recursive: true });
const files = fs.readdirSync(src).filter(f => f.endsWith('.html')).sort();
const browser = await chromium.launch();
for (const f of files) {
  const page = await browser.newPage({ deviceScaleFactor: scale });
  await page.goto('file://' + path.resolve(src, f));
  await page.evaluate(() => document.fonts.ready);
  const { w, h } = await page.evaluate(() => ({
    w: Number(document.documentElement.dataset.width || 1600),
    h: Number(document.documentElement.dataset.height || 2560),
  }));
  await page.setViewportSize({ width: w, height: h });
  const dest = path.join(out, f.replace(/\.html$/, '.png'));
  await page.screenshot({ path: dest, clip: { x: 0, y: 0, width: w, height: h } });
  console.log(`${f} -> ${dest} (${w}x${h})`);
  await page.close();
}
await browser.close();
