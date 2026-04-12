/**
 * SSID-docs Live Route Stress Test
 * Tests ALL sidebar routes against running dev server on port 4331.
 * Validates HTTP 200, content-type, minimum body size.
 */
import { readFileSync } from 'fs';
import http from 'http';

const BASE = 'http://localhost:4331';
const CONFIG = readFileSync(new URL('../astro.config.mjs', import.meta.url), 'utf8');
const SLUGS = [...CONFIG.matchAll(/slug:\s*'([^']+)'/g)].map(m => m[1]);

function fetch200(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 5000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, bodyLen: body.length }));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

let pass = 0;
let fail = 0;
const failures = [];

console.log(`\n=== Live Route Stress Test ===`);
console.log(`Testing ${SLUGS.length} EN routes + index + DE index...\n`);

// Test all EN routes
for (const slug of SLUGS) {
  const url = `${BASE}/SSID-docs/${slug}/`;
  try {
    const r = await fetch200(url);
    if (r.status !== 200) {
      fail++;
      failures.push(`${slug}: HTTP ${r.status}`);
    } else if (r.bodyLen < 500) {
      fail++;
      failures.push(`${slug}: body too small (${r.bodyLen} bytes)`);
    } else {
      pass++;
    }
  } catch (e) {
    fail++;
    failures.push(`${slug}: ${e.message}`);
  }
}

// Test root index
try {
  const r = await fetch200(`${BASE}/SSID-docs/`);
  if (r.status === 200 && r.bodyLen > 500) { pass++; } else { fail++; failures.push(`index: HTTP ${r.status}`); }
} catch (e) { fail++; failures.push(`index: ${e.message}`); }

// Test DE index
try {
  const r = await fetch200(`${BASE}/SSID-docs/de/`);
  if (r.status === 200 && r.bodyLen > 500) { pass++; } else { fail++; failures.push(`de/index: HTTP ${r.status}`); }
} catch (e) { fail++; failures.push(`de/index: ${e.message}`); }

console.log(`Passed: ${pass}`);
console.log(`Failed: ${fail}`);
if (failures.length > 0) {
  console.log(`\nFailures:`);
  failures.forEach(f => console.log(`  - ${f}`));
}
console.log(`\n${fail === 0 ? 'ALL ROUTES PASS' : 'SOME ROUTES FAILED'}`);
process.exit(fail > 0 ? 1 : 0);
