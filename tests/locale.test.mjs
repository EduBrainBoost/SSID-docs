/**
 * Locale Completeness Test
 * Verifies DE locale files exist for every EN content file.
 *
 * Run: node tests/locale.test.mjs
 */

import { readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const CONTENT_DIR = join(ROOT, 'src', 'content', 'docs');
const DE_DIR = join(CONTENT_DIR, 'de');

function collectFiles(dir, base) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = relative(base, full).replace(/\\/g, '/');
    if (entry === 'de' || entry === 'node_modules') continue;
    if (statSync(full).isDirectory()) {
      results.push(...collectFiles(full, base));
    } else if (entry.endsWith('.mdx') || entry.endsWith('.md')) {
      results.push(rel);
    }
  }
  return results;
}

export function run() {
  const output = [];

  const enFiles = collectFiles(CONTENT_DIR, CONTENT_DIR);
  const deFiles = existsSync(DE_DIR)
    ? collectFiles(DE_DIR, DE_DIR)
    : [];

  const deSet = new Set(deFiles);
  const missing = enFiles.filter(f => !deSet.has(f));

  const coveragePercent = enFiles.length > 0
    ? Math.round(((enFiles.length - missing.length) / enFiles.length) * 100)
    : 100;

  output.push(`  EN files: ${enFiles.length}`);
  output.push(`  DE files: ${deFiles.length}`);
  output.push(`  DE coverage: ${coveragePercent}%`);

  if (missing.length > 0 && missing.length <= 10) {
    output.push(`  Missing DE translations:`);
    for (const m of missing) {
      output.push(`    - ${m}`);
    }
  } else if (missing.length > 10) {
    output.push(`  ${missing.length} files missing DE translation (showing first 10):`);
    for (const m of missing.slice(0, 10)) {
      output.push(`    - ${m}`);
    }
  }

  // This test is informational — DE locale is optional but tracked
  output.push(`  Locale test complete (informational)`);
  return output;
}
