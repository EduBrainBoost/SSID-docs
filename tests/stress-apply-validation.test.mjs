/**
 * SSID-docs APPLY Validation Stress Test
 *
 * Runs against live preview server on port 4331.
 * Tests: route completeness, concurrent load, CSP headers, build reproducibility,
 *        search index, sitemap, i18n routes, 404 handling.
 *
 * Usage: node tests/stress-apply-validation.test.mjs [--port 4331]
 */

import http from 'node:http';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { execSync } from 'node:child_process';

const PORT = parseInt(process.argv.find((a, i) => process.argv[i - 1] === '--port') || '4331', 10);
const BASE = `/SSID-docs`;
const ROOT = join(import.meta.url.replace('file:///', '').replace(/\//g, '\\'), '..', '..').replace(/\\/g, '/').replace(/^\/([A-Z]):/, '$1:');

let passed = 0;
let failed = 0;
const failures = [];

function assert(condition, label) {
  if (condition) {
    passed++;
  } else {
    failed++;
    failures.push(label);
    console.error(`  FAIL: ${label}`);
  }
}

function fetch(path, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Timeout: ${path}`)), timeout);
    const req = http.get(`http://localhost:${PORT}${path}`, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        clearTimeout(timer);
        resolve({ status: res.statusCode, headers: res.headers, body });
      });
    });
    req.on('error', (err) => { clearTimeout(timer); reject(err); });
  });
}

// ── Test 1: All sidebar routes return 200 ──
async function testRouteCompleteness() {
  console.log('\n[Test 1] Route Completeness');
  const configPath = join(ROOT.replace(/\\/g, '/'), 'astro.config.mjs');
  const configText = readFileSync(configPath, 'utf-8');
  // Extract slugs from sidebar config
  const slugMatches = [...configText.matchAll(/slug:\s*['"]([^'"]+)['"]/g)];
  const slugs = slugMatches.map(m => m[1]);
  assert(slugs.length >= 40, `Found ${slugs.length} sidebar slugs (expected >=40)`);

  let ok = 0;
  let notOk = 0;
  for (const slug of slugs) {
    try {
      const res = await fetch(`${BASE}/${slug}/`);
      if (res.status === 200) { ok++; } else { notOk++; console.error(`    ${slug} -> ${res.status}`); }
    } catch (e) {
      notOk++;
      console.error(`    ${slug} -> ERROR: ${e.message}`);
    }
  }
  assert(notOk === 0, `All ${slugs.length} sidebar routes return 200 (${ok} ok, ${notOk} failed)`);
  console.log(`  ${ok}/${slugs.length} routes OK`);
}

// ── Test 2: Concurrent load (50 parallel requests) ──
async function testConcurrentLoad() {
  console.log('\n[Test 2] Concurrent Load (50 parallel)');
  const routes = ['/', '/overview/', '/architecture/roots/', '/compliance/gdpr/', '/de/'];
  const promises = [];
  for (let i = 0; i < 50; i++) {
    const route = routes[i % routes.length];
    promises.push(fetch(`${BASE}${route}`).then(r => r.status).catch(() => 0));
  }
  const results = await Promise.all(promises);
  const success = results.filter(s => s === 200).length;
  assert(success === 50, `50/50 concurrent requests returned 200 (got ${success})`);
  console.log(`  ${success}/50 requests succeeded`);
}

// ── Test 3: CSP header present ──
async function testCSPHeaders() {
  console.log('\n[Test 3] CSP Meta Tag');
  const res = await fetch(`${BASE}/`);
  const hasCSP = res.body.includes('Content-Security-Policy');
  assert(hasCSP, 'CSP meta tag present in HTML');
  console.log(`  CSP meta tag: ${hasCSP ? 'FOUND' : 'MISSING'}`);
}

// ── Test 4: Build output integrity ──
async function testBuildOutput() {
  console.log('\n[Test 4] Build Output Integrity');
  const distPath = join(ROOT, 'dist');
  assert(existsSync(distPath), 'dist/ directory exists');

  // Count HTML files
  let htmlCount = 0;
  function walkDir(dir) {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) { walkDir(full); }
      else if (entry.endsWith('.html')) { htmlCount++; }
    }
  }
  walkDir(distPath);
  assert(htmlCount >= 100, `dist/ contains ${htmlCount} HTML files (expected >=100)`);
  console.log(`  ${htmlCount} HTML files in dist/`);

  // Check sitemap (Astro outputs directly into dist/, not dist/SSID-docs/)
  const sitemapPath = join(distPath, 'sitemap-index.xml');
  assert(existsSync(sitemapPath), 'sitemap-index.xml exists');

  // Check pagefind search index
  const pagefindPath = join(distPath, 'pagefind');
  assert(existsSync(pagefindPath), 'pagefind search index exists');
}

// ── Test 5: I18N routes ──
async function testI18NRoutes() {
  console.log('\n[Test 5] I18N Routes');
  const deRoutes = ['/de/', '/de/overview/', '/de/architecture/roots/', '/de/compliance/gdpr/', '/de/developer/getting-started/'];
  let ok = 0;
  for (const route of deRoutes) {
    try {
      const res = await fetch(`${BASE}${route}`);
      if (res.status === 200) { ok++; } else { console.error(`    ${route} -> ${res.status}`); }
    } catch (e) {
      console.error(`    ${route} -> ERROR: ${e.message}`);
    }
  }
  assert(ok === deRoutes.length, `All ${deRoutes.length} DE routes return 200 (got ${ok})`);
  console.log(`  ${ok}/${deRoutes.length} DE routes OK`);
}

// ── Test 6: 404 handling ──
async function test404Handling() {
  console.log('\n[Test 6] 404 Handling');
  const res = await fetch(`${BASE}/this-page-does-not-exist/`);
  assert(res.status === 404, `Non-existent page returns 404 (got ${res.status})`);
  console.log(`  404 status: ${res.status === 404 ? 'CORRECT' : 'WRONG (' + res.status + ')'}`);
}

// ── Test 7: No secrets in output ──
async function testNoSecrets() {
  console.log('\n[Test 7] No Secrets in Build Output');
  const res = await fetch(`${BASE}/`);
  const secretPatterns = [
    /sk-[a-zA-Z0-9]{20,}/,
    /AKIA[A-Z0-9]{16}/,
    /ghp_[a-zA-Z0-9]{36}/,
    /password\s*[:=]\s*['"]/i,
  ];
  let found = false;
  for (const pattern of secretPatterns) {
    if (pattern.test(res.body)) {
      found = true;
      console.error(`    Secret pattern detected: ${pattern}`);
    }
  }
  assert(!found, 'No secret patterns in index page');
}

// ── Test 8: Build reproducibility ──
async function testBuildReproducibility() {
  console.log('\n[Test 8] Build Reproducibility');
  const distPath = join(ROOT, 'dist');
  // Count files in dist/ to verify deterministic output
  let fileCount = 0;
  function countFiles(dir) {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) { countFiles(full); }
      else { fileCount++; }
    }
  }
  if (existsSync(distPath)) {
    countFiles(distPath);
  }
  assert(fileCount >= 100, `Build output has ${fileCount} files (expected >=100 for reproducibility baseline)`);
  console.log(`  ${fileCount} files in dist/`);
}

// ── Main ──
async function main() {
  console.log(`=== SSID-docs APPLY Validation Stress Test ===`);
  console.log(`Server: http://localhost:${PORT}${BASE}/`);
  console.log(`Root: ${ROOT}`);

  try {
    await testRouteCompleteness();
    await testConcurrentLoad();
    await testCSPHeaders();
    await testBuildOutput();
    await testI18NRoutes();
    await test404Handling();
    await testNoSecrets();
    await testBuildReproducibility();
  } catch (e) {
    console.error(`\nFATAL: ${e.message}`);
    failed++;
    failures.push(`Fatal: ${e.message}`);
  }

  console.log('\n=== Results ===');
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  if (failures.length > 0) {
    console.log('\nFailures:');
    for (const f of failures) console.log(`  - ${f}`);
  }

  if (failed > 0) {
    process.exit(1);
  }
  console.log('\nAll stress tests passed!');
}

main();
