/**
 * SSID Docs Test Runner
 * Runs all test suites and reports results.
 */

import { execSync } from 'node:child_process';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const tests = [
  { name: 'Structure Tests', script: 'tests/structure.test.mjs' },
  { name: 'Content Tests', script: 'tests/content.test.mjs' },
  { name: 'Theme Tests', script: 'tests/theme.test.mjs' },
  { name: 'Security Tests', script: 'tests/security.test.mjs' },
];

let passed = 0;
let failed = 0;
const results = [];

console.log('=== SSID Docs Test Suite ===\n');

for (const test of tests) {
  try {
    const output = execSync(`node ${test.script}`, { cwd: ROOT, encoding: 'utf-8' });
    console.log(`PASS: ${test.name}`);
    if (output.trim()) console.log(output.trim());
    passed++;
    results.push({ name: test.name, result: 'PASS' });
  } catch (err) {
    console.error(`FAIL: ${test.name}`);
    if (err.stdout) console.error(err.stdout);
    if (err.stderr) console.error(err.stderr);
    failed++;
    results.push({ name: test.name, result: 'FAIL' });
  }
  console.log('');
}

console.log('=== Results ===');
console.log(`Passed: ${passed}/${tests.length}`);
console.log(`Failed: ${failed}/${tests.length}`);

if (failed > 0) {
  console.error('\nSome tests failed!');
  process.exit(1);
}

console.log('\nAll tests passed!');
