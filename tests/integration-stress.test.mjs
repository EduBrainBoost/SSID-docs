/**
 * Integration Stress Test
 * Comprehensive validation: build, content integrity, i18n, CSP, sidebar, search.
 *
 * Run: node tests/integration-stress.test.mjs
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const DIST = join(ROOT, 'dist');
const SRC_DOCS = join(ROOT, 'src', 'content', 'docs');
const CONFIG = join(ROOT, 'astro.config.mjs');

let passed = 0;
let failed = 0;
const errors = [];

function assert(condition, name, detail) {
  if (condition) {
    console.log(`  PASS: ${name}`);
    passed++;
  } else {
    console.log(`  FAIL: ${name} — ${detail}`);
    failed++;
    errors.push(`${name}: ${detail}`);
  }
}

// --- Test 1: Config integrity ---
console.log('\n[1] Config Integrity');
const configContent = readFileSync(CONFIG, 'utf-8');
assert(configContent.includes("port: 4331"), 'Port 4331 configured', 'port not set to 4331');
assert(configContent.includes("@astrojs/starlight"), 'Starlight integration present', 'starlight missing');
assert(configContent.includes("defaultLocale: 'root'"), 'Default locale set', 'defaultLocale missing');
assert(configContent.includes("lang: 'de'"), 'German locale configured', 'de locale missing');
assert(configContent.includes("Content-Security-Policy"), 'CSP header configured', 'CSP missing');
assert(configContent.includes("base: '/SSID-docs/'"), 'Base path /SSID-docs/', 'base path wrong');

// --- Test 2: Content files ---
console.log('\n[2] Content Files');
function countFiles(dir, ext) {
  let count = 0;
  if (!existsSync(dir)) return 0;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      count += countFiles(full, ext);
    } else if (entry.endsWith(ext)) {
      count++;
    }
  }
  return count;
}

const mdxCount = countFiles(SRC_DOCS, '.mdx');
const mdCount = countFiles(SRC_DOCS, '.md');
const totalContent = mdxCount + mdCount;
assert(totalContent >= 50, `Content files: ${totalContent}`, `Expected >=50, got ${totalContent}`);

// --- Test 3: i18n - DE translations exist ---
console.log('\n[3] i18n Validation');
const deDir = join(SRC_DOCS, 'de');
assert(existsSync(deDir), 'DE locale directory exists', 'src/content/docs/de/ missing');
if (existsSync(deDir)) {
  const deCount = countFiles(deDir, '.mdx') + countFiles(deDir, '.md');
  assert(deCount >= 5, `DE translations: ${deCount}`, `Expected >=5 DE docs, got ${deCount}`);
}

// --- Test 4: Sidebar completeness ---
console.log('\n[4] Sidebar Completeness');
const slugRegex = /slug:\s*['"]([^'"]+)['"]/g;
const sidebarSlugs = [];
let match;
while ((match = slugRegex.exec(configContent)) !== null) {
  sidebarSlugs.push(match[1]);
}
assert(sidebarSlugs.length >= 40, `Sidebar slugs: ${sidebarSlugs.length}`, `Expected >=40, got ${sidebarSlugs.length}`);

// Check each sidebar slug has a corresponding content file
let missingSlugs = 0;
for (const slug of sidebarSlugs) {
  const mdxPath = join(SRC_DOCS, ...slug.split('/')) + '.mdx';
  const mdPath = join(SRC_DOCS, ...slug.split('/')) + '.md';
  const indexMdx = join(SRC_DOCS, ...slug.split('/'), 'index.mdx');
  if (!existsSync(mdxPath) && !existsSync(mdPath) && !existsSync(indexMdx)) {
    missingSlugs++;
  }
}
assert(missingSlugs === 0, `Sidebar-to-content mapping`, `${missingSlugs} sidebar slugs have no content file`);

// --- Test 5: Build output ---
console.log('\n[5] Build Output');
assert(existsSync(DIST), 'dist/ exists', 'dist/ missing');
if (existsSync(DIST)) {
  const htmlCount = countFiles(DIST, '.html');
  assert(htmlCount >= 100, `HTML pages: ${htmlCount}`, `Expected >=100, got ${htmlCount}`);

  const pagefind = join(DIST, 'pagefind');
  assert(existsSync(pagefind), 'Pagefind index exists', 'pagefind/ missing');

  const sitemap = join(DIST, 'sitemap-index.xml');
  assert(existsSync(sitemap), 'Sitemap exists', 'sitemap-index.xml missing');
}

// --- Test 6: Assets ---
console.log('\n[6] Assets');
assert(existsSync(join(ROOT, 'src', 'assets', 'ssid-logo-light.svg')), 'Light logo exists', 'missing');
assert(existsSync(join(ROOT, 'src', 'assets', 'ssid-logo-dark.svg')), 'Dark logo exists', 'missing');
assert(existsSync(join(ROOT, 'src', 'styles', 'cyberpunk.css')), 'Custom CSS exists', 'missing');

// --- Test 7: No secrets in content ---
console.log('\n[7] Security: No Secrets in Content');
function checkNoSecrets(dir) {
  let violations = 0;
  if (!existsSync(dir)) return 0;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      violations += checkNoSecrets(full);
    } else if (entry.endsWith('.mdx') || entry.endsWith('.md')) {
      const content = readFileSync(full, 'utf-8');
      if (/(?:api[_-]?key|secret[_-]?key|password|private[_-]?key)\s*[:=]\s*['"][^'"]{8,}/i.test(content)) {
        violations++;
        console.log(`    SECRET FOUND: ${full}`);
      }
    }
  }
  return violations;
}
const secretViolations = checkNoSecrets(SRC_DOCS);
assert(secretViolations === 0, 'No secrets in docs', `${secretViolations} files contain secrets`);

// --- Test 8: Package.json scripts ---
console.log('\n[8] Package Scripts');
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf-8'));
assert(pkg.scripts?.dev?.includes('4331'), 'dev script uses port 4331', 'wrong port');
assert(pkg.scripts?.build?.includes('astro'), 'build script uses astro', 'missing');
assert(pkg.scripts?.test, 'test script exists', 'missing');

// --- Summary ---
console.log('\n=== Integration Stress Test Results ===');
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  console.log(`\nErrors:\n${errors.map(e => `  - ${e}`).join('\n')}`);
  process.exit(1);
}

console.log('\nAll integration stress tests passed!');
