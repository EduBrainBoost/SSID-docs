/**
 * Build Stress Test
 * Runs the Astro build and validates output metrics.
 *
 * Run: node tests/build-stress.test.mjs
 */

import { execSync } from 'node:child_process';
import { readdirSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const DIST = join(ROOT, 'dist');

let passed = 0;
let failed = 0;
const errors = [];

console.log('=== Build Stress Test ===\n');

// Test 1: Build completes without error
console.log('Running astro build...');
try {
  const output = execSync('npx astro build', { cwd: ROOT, encoding: 'utf-8', timeout: 120000 });
  console.log('PASS: Build completed successfully');
  passed++;
} catch (e) {
  console.log(`FAIL: Build failed: ${e.message}`);
  failed++;
  errors.push('Build failed');
}

// Test 2: dist/ directory exists and has content
if (existsSync(DIST)) {
  console.log('PASS: dist/ directory exists');
  passed++;
} else {
  console.log('FAIL: dist/ directory missing');
  failed++;
  errors.push('dist/ missing');
}

// Test 3: Count HTML files in dist
function countHtml(dir) {
  let count = 0;
  if (!existsSync(dir)) return 0;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      count += countHtml(full);
    } else if (entry.endsWith('.html')) {
      count++;
    }
  }
  return count;
}

const htmlCount = countHtml(DIST);
const MIN_PAGES = 100;

if (htmlCount >= MIN_PAGES) {
  console.log(`PASS: ${htmlCount} HTML pages generated (min: ${MIN_PAGES})`);
  passed++;
} else {
  console.log(`FAIL: Only ${htmlCount} HTML pages (min: ${MIN_PAGES})`);
  failed++;
  errors.push(`Only ${htmlCount} pages`);
}

// Test 4: Pagefind search index exists
const pagefindDir = join(DIST, 'pagefind');
if (existsSync(pagefindDir)) {
  console.log('PASS: Pagefind search index exists');
  passed++;
} else {
  console.log('FAIL: Pagefind search index missing');
  failed++;
  errors.push('Pagefind missing');
}

// Test 5: Sitemap exists
const sitemapFile = join(DIST, 'sitemap-index.xml');
if (existsSync(sitemapFile)) {
  console.log('PASS: sitemap-index.xml exists');
  passed++;
} else {
  console.log('FAIL: sitemap-index.xml missing');
  failed++;
  errors.push('Sitemap missing');
}

// Test 6: No error.html pages (broken routes)
function findErrorPages(dir) {
  const results = [];
  if (!existsSync(dir)) return results;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      results.push(...findErrorPages(full));
    } else if (entry === '500.html' || entry === '404.html') {
      // 404.html is expected for Starlight, skip it
      if (entry === '500.html') results.push(full);
    }
  }
  return results;
}

const errorPages = findErrorPages(DIST);
if (errorPages.length === 0) {
  console.log('PASS: No 500.html error pages found');
  passed++;
} else {
  console.log(`FAIL: ${errorPages.length} error pages found`);
  failed++;
  errors.push(`${errorPages.length} error pages`);
}

// Summary
console.log(`\n=== Results ===`);
console.log(`Passed: ${passed}/6`);
console.log(`Failed: ${failed}/6`);

if (failed > 0) {
  console.log(`\nErrors: ${errors.join(', ')}`);
  process.exit(1);
}

console.log('\nAll build stress tests passed!');
