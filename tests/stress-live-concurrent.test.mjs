/**
 * SSID-docs Live Concurrent Load Test
 * Fires N parallel requests to simulate concurrent access.
 * Measures response times and checks for failures.
 */
import http from 'http';

const BASE = 'http://localhost:4331';
const CONCURRENCY = 20;
const ROUTES = [
  '/SSID-docs/',
  '/SSID-docs/overview/',
  '/SSID-docs/architecture/roots/',
  '/SSID-docs/architecture/root24/',
  '/SSID-docs/identity/did-method/',
  '/SSID-docs/governance/pr-only/',
  '/SSID-docs/compliance/gdpr/',
  '/SSID-docs/tooling/dispatcher/',
  '/SSID-docs/token/utility/',
  '/SSID-docs/de/',
  '/SSID-docs/developer/getting-started/',
  '/SSID-docs/faq/general/',
  '/SSID-docs/roadmap/',
  '/SSID-docs/status/',
  '/SSID-docs/security/',
  '/SSID-docs/architecture/matrix/',
  '/SSID-docs/architecture/shards/',
  '/SSID-docs/governance/evidence/',
  '/SSID-docs/compliance/eidas/',
  '/SSID-docs/tooling/agents/',
];

function timedFetch(url) {
  const start = performance.now();
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 10000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve({ url, status: res.statusCode, ms: Math.round(performance.now() - start), bodyLen: body.length }));
    });
    req.on('error', (e) => resolve({ url, status: 0, ms: Math.round(performance.now() - start), error: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ url, status: 0, ms: Math.round(performance.now() - start), error: 'timeout' }); });
  });
}

console.log(`\n=== Live Concurrent Load Test ===`);
console.log(`Concurrency: ${CONCURRENCY} parallel requests\n`);

const promises = ROUTES.slice(0, CONCURRENCY).map(r => timedFetch(`${BASE}${r}`));
const results = await Promise.all(promises);

let pass = 0;
let fail = 0;
const times = [];

for (const r of results) {
  if (r.status === 200 && r.bodyLen > 500) {
    pass++;
    times.push(r.ms);
  } else {
    fail++;
    console.log(`  [FAIL] ${r.url} -> ${r.error || 'HTTP ' + r.status}`);
  }
}

times.sort((a, b) => a - b);
const avg = Math.round(times.reduce((s, t) => s + t, 0) / times.length);
const p50 = times[Math.floor(times.length * 0.5)];
const p95 = times[Math.floor(times.length * 0.95)];
const max = times[times.length - 1];

console.log(`Results: ${pass} pass, ${fail} fail`);
console.log(`Latency: avg=${avg}ms  p50=${p50}ms  p95=${p95}ms  max=${max}ms`);
console.log(`\n${fail === 0 ? 'CONCURRENT LOAD TEST PASS' : 'CONCURRENT LOAD TEST FAILED'}`);
process.exit(fail > 0 ? 1 : 0);
