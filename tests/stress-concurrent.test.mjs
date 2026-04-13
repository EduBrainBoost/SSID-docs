/**
 * Concurrent Load Stress Test
 * Fires parallel requests at the dev server to validate stability under load.
 * Requires dev server on port 4331.
 *
 * Run: node tests/stress-concurrent.test.mjs
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
  console.log('=== Concurrent Load Stress Test ===\n');

  const port = await findPort();
  if (!port) {
    console.log('SKIP: No dev server found. Start with: pnpm dev --port 4331');
    process.exit(2);
  }

  console.log(`Using port ${port}`);

  const CONCURRENCY = 20;
  const ROUNDS = 3;
  let totalPassed = 0;
  let totalFailed = 0;
  const timings = [];

  for (let round = 1; round <= ROUNDS; round++) {
    console.log(`\nRound ${round}/${ROUNDS}: ${CONCURRENCY} concurrent requests`);
    const start = performance.now();

    // Pick random slugs for this round
    const batch = Array.from({ length: CONCURRENCY }, () => {
      const idx = Math.floor(Math.random() * slugs.length);
      return slugs[idx];
    });

    const results = await Promise.allSettled(
      batch.map(async (slug) => {
        const url = `http://localhost:${port}/SSID-docs/${slug}/`;
        const res = await fetch(url);
        return { slug, status: res.status };
      })
    );

    const elapsed = performance.now() - start;
    timings.push(elapsed);

    let roundPass = 0;
    let roundFail = 0;
    for (const r of results) {
      if (r.status === 'fulfilled' && r.value.status === 200) {
        roundPass++;
      } else {
        roundFail++;
        const detail = r.status === 'rejected' ? r.reason?.message : `HTTP ${r.value?.status}`;
        console.log(`  FAIL: ${r.value?.slug || 'unknown'} — ${detail}`);
      }
    }

    totalPassed += roundPass;
    totalFailed += roundFail;
    console.log(`  ${roundPass}/${CONCURRENCY} OK in ${elapsed.toFixed(0)}ms`);
  }

  const totalReqs = CONCURRENCY * ROUNDS;
  const avgTime = timings.reduce((a, b) => a + b, 0) / timings.length;

  console.log(`\n=== Results ===`);
  console.log(`Total: ${totalPassed}/${totalReqs} passed`);
  console.log(`Failed: ${totalFailed}/${totalReqs}`);
  console.log(`Avg round time: ${avgTime.toFixed(0)}ms`);

  if (totalFailed > 0) {
    process.exit(1);
  }

  console.log('\nAll concurrent stress tests passed!');
}

runTests().catch(e => {
  console.error('Concurrent test error:', e.message);
  process.exit(1);
});
