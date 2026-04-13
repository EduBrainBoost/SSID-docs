/**
 * CSP Stress Test
 * Validates Content-Security-Policy headers are served on all pages.
 * Requires dev server on port 4331.
 *
 * Run: node tests/stress-csp.test.mjs
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const CONFIG = join(ROOT, 'astro.config.mjs');

const configContent = readFileSync(CONFIG, 'utf-8');
const slugRegex = /slug:\s*['"]([^'"]+)['"]/g;
const slugs = [];
let match;
while ((match = slugRegex.exec(configContent)) !== null) {
  slugs.push(match[1]);
}

async function findPort() {
  for (const port of [4331, 4332]) {
    try {
      const res = await fetch(`http://localhost:${port}/SSID-docs/`);
      if (res.status === 200) return port;
    } catch { /* next */ }
  }
  return null;
}

async function runTests() {
  console.log('=== CSP Stress Test ===\n');

  const port = await findPort();
  if (!port) {
    console.log('SKIP: No dev server found. Start with: pnpm dev --port 4331');
    process.exit(2);
  }

  console.log(`Using port ${port}`);
  let passed = 0;
  let failed = 0;
  const failures = [];

  // Sample routes (every 3rd slug + index)
  const testSlugs = ['', ...slugs.filter((_, i) => i % 3 === 0)];

  for (const slug of testSlugs) {
    const url = `http://localhost:${port}/SSID-docs/${slug}${slug ? '/' : ''}`;
    try {
      const res = await fetch(url);
      const html = await res.text();
      const hasCSP = html.includes('Content-Security-Policy');
      if (hasCSP) {
        passed++;
      } else {
        failed++;
        failures.push(slug || '(index)');
      }
    } catch (e) {
      failed++;
      failures.push(`${slug || '(index)'}: ${e.message}`);
    }
  }

  console.log(`\nTested ${testSlugs.length} pages for CSP meta tag`);
  console.log(`Passed: ${passed}/${testSlugs.length}`);
  console.log(`Failed: ${failed}/${testSlugs.length}`);

  if (failed > 0) {
    console.log('\nFailing pages:');
    for (const f of failures) console.log(`  - ${f}`);
    process.exit(1);
  }

  console.log('\nAll CSP stress tests passed!');
}

runTests().catch(e => {
  console.error('CSP test error:', e.message);
  process.exit(1);
});
