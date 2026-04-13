/**
 * Frontmatter Stress Test
 * Validates every content file has valid frontmatter with required fields.
 *
 * Run: node tests/stress-frontmatter.test.mjs
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const SRC_DOCS = join(ROOT, 'src', 'content', 'docs');

let passed = 0;
let failed = 0;
const errors = [];

console.log('=== Frontmatter Stress Test ===\n');

function collectFiles(dir) {
  const files = [];
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...collectFiles(full));
    } else if (entry.endsWith('.mdx') || entry.endsWith('.md')) {
      files.push(full);
    }
  }
  return files;
}

const files = collectFiles(SRC_DOCS);
console.log(`Found ${files.length} content files\n`);

for (const file of files) {
  const content = readFileSync(file, 'utf-8');
  const rel = file.replace(ROOT, '').replace(/\\/g, '/');

  // Check frontmatter exists
  if (!content.startsWith('---')) {
    failed++;
    errors.push(`${rel}: no frontmatter block`);
    continue;
  }

  const fmEnd = content.indexOf('---', 3);
  if (fmEnd === -1) {
    failed++;
    errors.push(`${rel}: unclosed frontmatter`);
    continue;
  }

  const fm = content.substring(3, fmEnd);

  // Must have title
  if (!/title\s*:/.test(fm)) {
    failed++;
    errors.push(`${rel}: missing title`);
    continue;
  }

  // No empty title
  if (/title\s*:\s*['"]?\s*['"]?\s*$/.test(fm)) {
    failed++;
    errors.push(`${rel}: empty title`);
    continue;
  }

  passed++;
}

console.log(`Passed: ${passed}/${files.length}`);
console.log(`Failed: ${failed}/${files.length}`);

if (failed > 0) {
  console.log('\nErrors:');
  for (const e of errors) console.log(`  - ${e}`);
  process.exit(1);
}

console.log('\nAll frontmatter stress tests passed!');
