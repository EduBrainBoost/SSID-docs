/**
 * AI Infrastructure Phase-2.1 Tests
 * Runs comprehensive lossless generation tests and negative mutation tests.
 */

import { execSync } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(import.meta.dirname, '..');

export function run() {
  const output = [];

  output.push('Running AI Infrastructure Phase-2.1 Tests...');
  output.push('');

  // Run lossless tests
  output.push('  [1/2] Running lossless generation tests...');
  try {
    execSync(`node ${path.join(ROOT, 'tests/ai-infrastructure-phase2-1-lossless.test.mjs')}`, {
      stdio: 'pipe'
    });
    output.push('  ✓ Lossless generation tests passed (17 tests)');
  } catch (e) {
    output.push('  ✗ Lossless generation tests FAILED');
    throw new Error('Lossless tests failed');
  }

  // Run negative mutation tests
  output.push('  [2/2] Running negative mutation tests...');
  try {
    execSync(`node ${path.join(ROOT, 'tests/ai-infrastructure-phase2-1-negative-mutations.test.mjs')}`, {
      stdio: 'pipe'
    });
    output.push('  ✓ Negative mutation tests passed (13 tests)');
  } catch (e) {
    output.push('  ✗ Negative mutation tests FAILED');
    throw new Error('Negative mutation tests failed');
  }

  output.push('');
  output.push('Results: 30 tests passed');
  output.push('  ✓ All Phase-2.1 lossless generation validations passed');
  output.push('  ✓ All negative mutation tests confirmed generator/validator rejection');

  return output;
}

const isDirectRun =
  process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;

if (isDirectRun) {
  try {
    for (const line of run()) {
      console.log(line);
    }
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
  }
}
