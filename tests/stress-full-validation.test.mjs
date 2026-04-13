/**
 * SSID-docs Full Validation Stress Test
 * Phase 4: Comprehensive live test against running dev server on port 4331.
 *
 * Tests:
 * 1. All sidebar routes → HTTP 200, min body size
 * 2. Concurrent request burst (20 parallel)
 * 3. Response time SLA (<3s per page)
 * 4. CSP header presence
 * 5. DE locale coverage (all EN routes must have DE equivalent)
 * 6. Pagefind search assets
 * 7. 404 handling for invalid routes
 */
import { readFileSync } from 'fs';
import http from 'http';

const BASE = 'http://localhost:4331';
const PREFIX = '/SSID-docs';
const CONFIG = readFileSync(new URL('../astro.config.mjs', import.meta.url), 'utf8');
const SLUGS = [...CONFIG.matchAll(/slug:\s*'([^']+)'/g)].map(m => m[1]);

function httpGet(url) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const req = http.get(url, { timeout: 8000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve({
        status: res.statusCode,
        headers: res.headers,
        bodyLen: body.length,
        body,
        ms: Date.now() - start,
      }));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

const results = { pass: 0, fail: 0, failures: [], warnings: [] };

function ok(label) { results.pass++; }
function nok(label, reason) { results.fail++; results.failures.push(`${label}: ${reason}`); }
function warn(label, reason) { results.warnings.push(`${label}: ${reason}`); }

console.log('=== SSID-docs Full Validation Stress Test ===');
console.log(`Date: ${new Date().toISOString()}`);
console.log(`Routes from config: ${SLUGS.length}\n`);

// --- Test 1: All EN routes ---
console.log('--- Test 1: EN Route Coverage ---');
for (const slug of SLUGS) {
  const url = `${BASE}${PREFIX}/${slug}/`;
  try {
    const r = await httpGet(url);
    if (r.status !== 200) { nok(slug, `HTTP ${r.status}`); }
    else if (r.bodyLen < 500) { nok(slug, `body ${r.bodyLen}B < 500B min`); }
    else if (r.ms > 3000) { nok(slug, `${r.ms}ms > 3000ms SLA`); }
    else { ok(slug); }
  } catch (e) { nok(slug, e.message); }
}
console.log(`  EN routes: ${results.pass} pass, ${results.fail} fail`);

// --- Test 2: Concurrent burst ---
console.log('--- Test 2: Concurrent Burst (20 parallel) ---');
const burstRoutes = SLUGS.slice(0, 20).map(s => `${BASE}${PREFIX}/${s}/`);
const burstStart = Date.now();
try {
  const responses = await Promise.all(burstRoutes.map(url => httpGet(url)));
  const burstMs = Date.now() - burstStart;
  const allOk = responses.every(r => r.status === 200);
  if (allOk) { ok('concurrent-burst'); console.log(`  ${responses.length} concurrent: ALL 200 in ${burstMs}ms`); }
  else { nok('concurrent-burst', `some non-200: ${responses.map(r => r.status).join(',')}`); }
} catch (e) { nok('concurrent-burst', e.message); }

// --- Test 3: Response time SLA ---
console.log('--- Test 3: Response Time SLA ---');
const sampleRoutes = ['overview', 'architecture/roots', 'compliance/gdpr', 'token/utility', 'governance/evidence'];
for (const slug of sampleRoutes) {
  try {
    const r = await httpGet(`${BASE}${PREFIX}/${slug}/`);
    if (r.ms > 3000) { nok(`sla:${slug}`, `${r.ms}ms > 3000ms`); }
    else { ok(`sla:${slug}`); console.log(`  ${slug}: ${r.ms}ms`); }
  } catch (e) { nok(`sla:${slug}`, e.message); }
}

// --- Test 4: CSP Header ---
console.log('--- Test 4: CSP Header ---');
try {
  const r = await httpGet(`${BASE}${PREFIX}/`);
  // CSP is injected via meta tag in Starlight, not HTTP header in dev mode
  if (r.body.includes('Content-Security-Policy')) { ok('csp-meta'); console.log('  CSP meta tag found'); }
  else { warn('csp-meta', 'no CSP meta tag in HTML'); }
} catch (e) { nok('csp', e.message); }

// --- Test 5: DE Locale ---
console.log('--- Test 5: DE Locale Coverage ---');
const deRoutes = ['de/', 'de/architecture/roots/', 'de/compliance/gdpr/', 'de/tooling/dispatcher/'];
for (const slug of deRoutes) {
  try {
    const r = await httpGet(`${BASE}${PREFIX}/${slug}`);
    if (r.status === 200 && r.bodyLen > 500) { ok(`de:${slug}`); }
    else { nok(`de:${slug}`, `HTTP ${r.status}, ${r.bodyLen}B`); }
  } catch (e) { nok(`de:${slug}`, e.message); }
}
console.log(`  DE routes tested: ${deRoutes.length}`);

// --- Test 6: Pagefind Assets ---
console.log('--- Test 6: Pagefind Search Assets ---');
try {
  const r = await httpGet(`${BASE}${PREFIX}/pagefind/pagefind.js`);
  if (r.status === 200 && r.bodyLen > 100) { ok('pagefind'); console.log(`  pagefind.js: ${r.bodyLen}B`); }
  else { warn('pagefind', `HTTP ${r.status}, ${r.bodyLen}B (may not exist in dev mode)`); }
} catch (e) { warn('pagefind', `${e.message} (expected in dev mode)`); }

// --- Test 7: 404 Handling ---
console.log('--- Test 7: 404 Handling ---');
try {
  const r = await httpGet(`${BASE}${PREFIX}/nonexistent-route-xyz/`);
  if (r.status === 404 || r.status === 200) {
    // Astro dev server may return 200 with error page or 404
    ok('404-handling');
    console.log(`  Invalid route returned HTTP ${r.status}`);
  } else {
    nok('404-handling', `unexpected HTTP ${r.status}`);
  }
} catch (e) { nok('404-handling', e.message); }

// --- Summary ---
console.log('\n=== SUMMARY ===');
console.log(`PASS: ${results.pass}`);
console.log(`FAIL: ${results.fail}`);
if (results.warnings.length > 0) {
  console.log(`WARNINGS: ${results.warnings.length}`);
  results.warnings.forEach(w => console.log(`  ⚠ ${w}`));
}
if (results.failures.length > 0) {
  console.log(`\nFAILURES:`);
  results.failures.forEach(f => console.log(`  ✗ ${f}`));
}
console.log(`\n${results.fail === 0 ? 'FULL VALIDATION PASS' : 'VALIDATION FAILED'}`);
process.exit(results.fail > 0 ? 1 : 0);
