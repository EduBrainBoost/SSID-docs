/**
 * SSID Docs Test Runner
 * Runs all test suites and reports results in-process to avoid Windows spawn issues.
 */

const tests = [
  { name: 'Structure Tests', module: './structure.test.mjs' },
  { name: 'Content Tests', module: './content.test.mjs' },
  { name: 'Theme Tests', module: './theme.test.mjs' },
  { name: 'Security Tests', module: './security.test.mjs' },
];

let passed = 0;
let failed = 0;
const results = [];

console.log('=== SSID Docs Test Suite ===\n');

for (const test of tests) {
  try {
    const testModule = await import(new URL(test.module, import.meta.url));
    const outputLines = testModule.run();
    console.log(`PASS: ${test.name}`);
    for (const line of outputLines) {
      console.log(line);
    }
    passed++;
    results.push({ name: test.name, result: 'PASS' });
  } catch (err) {
    console.error(`FAIL: ${test.name}`);
    if (err instanceof Error && err.message) {
      console.error(err.message);
    } else {
      console.error(String(err));
    }
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
