#!/usr/bin/env node
/**
 * Perceptual screenshot sync: copy PNGs from <srcDir> to <destDir> only when
 * they MEANINGFULLY differ (pixelmatch), so headless-chromium sub-pixel
 * rasterisation flicker doesn't churn the committed screenshots on every
 * capture run.
 *
 * Usage: node compare-screenshots.mjs <srcDir> <destDir>
 * Prints one line per updated file; exits 0 always (the caller inspects
 * `git status` to decide whether anything changed).
 */

import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';

// Anti-aliasing flicker measures well under this; real UI changes are
// orders of magnitude above it.
const MAX_IGNORED_DIFF_PIXELS = 64;

const [srcDir, destDir] = process.argv.slice(2);
if (!srcDir || !destDir) {
  console.error('usage: compare-screenshots.mjs <srcDir> <destDir>');
  process.exit(2);
}

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) yield* walk(full);
    else if (entry.endsWith('.png')) yield full;
  }
}

let updated = 0;
let unchanged = 0;
for (const srcFile of walk(srcDir)) {
  const rel = relative(srcDir, srcFile);
  const destFile = join(destDir, rel);

  let changed = true;
  if (existsSync(destFile)) {
    try {
      const a = PNG.sync.read(readFileSync(srcFile));
      const b = PNG.sync.read(readFileSync(destFile));
      if (a.width === b.width && a.height === b.height) {
        const diff = pixelmatch(a.data, b.data, null, a.width, a.height, { threshold: 0.1 });
        changed = diff > MAX_IGNORED_DIFF_PIXELS;
      }
    } catch {
      // Unreadable/corrupt (e.g. an unsmudged LFS pointer) — treat as changed.
    }
  }

  if (changed) {
    mkdirSync(dirname(destFile), { recursive: true });
    copyFileSync(srcFile, destFile);
    console.log(`updated ${rel}`);
    updated += 1;
  } else {
    unchanged += 1;
  }
}

console.log(`${updated} updated, ${unchanged} unchanged (diff tolerance ${MAX_IGNORED_DIFF_PIXELS}px)`);
