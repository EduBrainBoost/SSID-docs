/**
 * Route Stress Test
 * Starts the dev server and verifies every sidebar route returns HTTP 200.
 * Requires port 4331 or falls back to 4332.
 *
 * Run: node tests/route-stress.test.mjs
 */

import { execSync, spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const CONFIG_FILE = join(ROOT, 'astro.config.mjs');

// Extract all sidebar slugs
const configContent = readFileSync(CONFIG_FILE, 'utf-8');
const slugRegex = /slug:\s*['"]([^'"]+)['"]/g;
const slugs = [];
let match;
while ((match = slugRegex.exec(configContent)) !== null) {
  slugs.push(match[1]);
}

// Also test index and de/ landing
const routes = [
  '',          // index
  ...slugs,
];

async function fetchWithRetry(url, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, { redirect: 'follow' });
      return res.status;
    } catch {
      if (i < retries - 1) await new Promise(r => setTimeout(r, 1000));
    }
  }
  return -1;
}

async function findPort() {
  for (const port of [4331, 4332, 4333, 4334, 4335, 4336]) {
    try {
      const res = await fetch(`http://localhost:${port}/SSID-docs/`);
      if (res.status === 200) return port;
    } catch { /* try next */ }
  }
  return null;
}

async function runTests() {
  console.log('=== Route Stress Test ===\n');

  const port = await findPort();
  if (!port) {
    console.log('SKIP: No dev server found on ports 4331-4333.');
    console.log('Start the dev server first: pnpm dev --port 4331');
    process.exit(2);
  }

  console.log(`Using dev server on port ${port}`);
  console.log(`Testing ${routes.length} routes...\n`);

  let passed = 0;
  let failed = 0;
  const failures = [];

  for (const slug of routes) {
    const url = `http://localhost:${port}/SSID-docs/${slug}${slug ? '/' : ''}`;
    const status = await fetchWithRetry(url);
    if (status === 200) {
      passed++;
    } else {
      failed++;
      failures.push({ slug: slug || '(index)', status });
      console.log(`  FAIL: ${slug || '(index)'} => HTTP ${status}`);
    }
  }

  console.log(`\n=== Results ===`);
  console.log(`Passed: ${passed}/${routes.length}`);
  console.log(`Failed: ${failed}/${routes.length}`);

  if (failed > 0) {
    console.log('\nFailed routes:');
    for (const f of failures) {
      console.log(`  - ${f.slug} (HTTP ${f.status})`);
    }
    process.exit(1);
  }

  console.log('\nAll route stress tests passed!');
}

runTests().catch(e => {
  console.error('Route test error:', e.message);
  process.exit(1);
});
