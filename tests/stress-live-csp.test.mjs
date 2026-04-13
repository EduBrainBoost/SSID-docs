/**
 * SSID-docs Live CSP & Security Headers Test
 * Validates Content-Security-Policy meta tag in HTML responses.
 */
import http from 'http';

const BASE = 'http://localhost:4331';
const SAMPLE_ROUTES = [
  '/SSID-docs/',
  '/SSID-docs/overview/',
  '/SSID-docs/architecture/roots/',
  '/SSID-docs/de/',
];

function fetchBody(url) {
  return new Promise((resolve, reject) => {
    http.get(url, { timeout: 5000 }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve({ status: res.statusCode, body, headers: res.headers }));
    }).on('error', reject);
  });
}

console.log(`\n=== Live CSP & Security Headers Test ===\n`);

let pass = 0;
let fail = 0;
const failures = [];

for (const route of SAMPLE_ROUTES) {
  const url = `${BASE}${route}`;
  try {
    const r = await fetchBody(url);
    if (r.status !== 200) {
      fail++;
      failures.push(`${route}: HTTP ${r.status}`);
      continue;
    }

    // Check CSP meta tag exists
    const cspMatch = r.body.match(/http-equiv=["']Content-Security-Policy["']/i);
    if (!cspMatch) {
      fail++;
      failures.push(`${route}: missing CSP meta tag`);
    } else {
      pass++;
    }

    // Check no inline scripts (other than Astro's hydration)
    const scriptTags = [...r.body.matchAll(/<script(?![^>]*src=)[^>]*>/gi)];
    // Astro adds inline scripts for hydration, those are expected
    // But check for suspicious patterns
    const suspicious = scriptTags.filter(s => {
      const tag = s[0];
      return tag.includes('eval(') || tag.includes('document.write(');
    });
    if (suspicious.length > 0) {
      fail++;
      failures.push(`${route}: suspicious inline script detected`);
    } else {
      pass++;
    }

    // Check no external font loading (privacy)
    if (r.body.includes('fonts.googleapis.com') || r.body.includes('fonts.gstatic.com')) {
      fail++;
      failures.push(`${route}: external font loading detected (privacy)`);
    } else {
      pass++;
    }

  } catch (e) {
    fail++;
    failures.push(`${route}: ${e.message}`);
  }
}

console.log(`Passed: ${pass}`);
console.log(`Failed: ${fail}`);
if (failures.length > 0) {
  console.log(`\nFailures:`);
  failures.forEach(f => console.log(`  - ${f}`));
}
console.log(`\n${fail === 0 ? 'CSP & SECURITY TEST PASS' : 'CSP & SECURITY TEST FAILED'}`);
process.exit(fail > 0 ? 1 : 0);
