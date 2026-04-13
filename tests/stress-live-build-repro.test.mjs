/**
 * SSID-docs Build Reproducibility Test
 * Runs astro build twice and compares output file list.
 * Ensures deterministic build output.
 */
import { execSync } from 'child_process';
import { readdirSync, statSync } from 'fs';
import { join } from 'path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1');

function listFiles(dir, base = '') {
  const entries = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = base ? `${base}/${entry}` : entry;
    const st = statSync(full);
    if (st.isDirectory()) {
      entries.push(...listFiles(full, rel));
    } else {
      entries.push(rel);
    }
  }
  return entries.sort();
}

console.log(`\n=== Build Reproducibility Test ===\n`);

// Build 1
console.log('Build 1...');
execSync('npx astro build', { cwd: ROOT, stdio: 'pipe', timeout: 120000 });
const files1 = listFiles(join(ROOT, 'dist'));

// Build 2
console.log('Build 2...');
execSync('npx astro build', { cwd: ROOT, stdio: 'pipe', timeout: 120000 });
const files2 = listFiles(join(ROOT, 'dist'));

// Compare
const set1 = new Set(files1);
const set2 = new Set(files2);

const onlyIn1 = files1.filter(f => !set2.has(f));
const onlyIn2 = files2.filter(f => !set1.has(f));

console.log(`Build 1: ${files1.length} files`);
console.log(`Build 2: ${files2.length} files`);

if (onlyIn1.length === 0 && onlyIn2.length === 0 && files1.length === files2.length) {
  console.log('\nBUILD REPRODUCIBILITY TEST PASS');
  process.exit(0);
} else {
  if (onlyIn1.length) { console.log('\nOnly in build 1:'); onlyIn1.forEach(f => console.log(`  ${f}`)); }
  if (onlyIn2.length) { console.log('\nOnly in build 2:'); onlyIn2.forEach(f => console.log(`  ${f}`)); }
  console.log('\nBUILD REPRODUCIBILITY TEST FAILED');
  process.exit(1);
}
