/**
 * Structure Tests
 * Verify that all required files and directories exist.
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');

const requiredFiles = [
  'astro.config.mjs',
  'tsconfig.json',
  'package.json',
  'README.md',
  'LICENSE',
  'SECURITY.md',
  'CODEOWNERS',
  '.gitignore',
  '.github/workflows/docs_ci.yml',
  'src/styles/cyberpunk.css',
  'src/assets/ssid-logo-dark.svg',
  'src/assets/ssid-logo-light.svg',
  'tools/ingest.mjs',
  'src/content.config.ts',
];

const requiredDirs = [
  'src/content/docs',
  'src/content/docs/architecture',
  'src/content/docs/governance',
  'src/content/docs/compliance',
  'src/content/docs/tooling',
  'src/content/docs/token',
  'src/content/docs/faq',
  'src/styles',
  'src/assets',
  'tools',
  'tests',
  '.github/workflows',
];

const contentFiles = [
  'src/content/docs/overview.mdx',
  'src/content/docs/architecture/matrix.mdx',
  'src/content/docs/architecture/shards.mdx',
  'src/content/docs/architecture/artifacts.mdx',
  'src/content/docs/governance/pr-only.mdx',
  'src/content/docs/governance/evidence.mdx',
  'src/content/docs/governance/policy-gates.mdx',
  'src/content/docs/compliance/gdpr.mdx',
  'src/content/docs/compliance/eidas.mdx',
  'src/content/docs/compliance/mica.mdx',
  'src/content/docs/tooling/dispatcher.mdx',
  'src/content/docs/tooling/agents.mdx',
  'src/content/docs/tooling/health-checks.mdx',
  'src/content/docs/token/utility.mdx',
  'src/content/docs/token/non-custodial.mdx',
  'src/content/docs/faq/general.mdx',
  'src/content/docs/faq/token-disambiguation.mdx',
];

let errors = 0;

// Check required files
for (const file of requiredFiles) {
  const fullPath = path.join(ROOT, file);
  if (!fs.existsSync(fullPath)) {
    console.error(`  MISSING file: ${file}`);
    errors++;
  }
}

// Check required directories
for (const dir of requiredDirs) {
  const fullPath = path.join(ROOT, dir);
  if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isDirectory()) {
    console.error(`  MISSING directory: ${dir}`);
    errors++;
  }
}

// Check content files
for (const file of contentFiles) {
  const fullPath = path.join(ROOT, file);
  if (!fs.existsSync(fullPath)) {
    console.error(`  MISSING content: ${file}`);
    errors++;
  }
}

// Check package.json has required scripts
const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8'));
const requiredScripts = ['dev', 'build', 'preview', 'test', 'ingest'];
for (const script of requiredScripts) {
  if (!pkg.scripts?.[script]) {
    console.error(`  MISSING script: ${script}`);
    errors++;
  }
}

// Check dependencies
const requiredDeps = ['astro', '@astrojs/starlight'];
for (const dep of requiredDeps) {
  if (!pkg.dependencies?.[dep]) {
    console.error(`  MISSING dependency: ${dep}`);
    errors++;
  }
}

if (errors > 0) {
  console.error(`  ${errors} structure error(s) found`);
  process.exit(1);
}

console.log(`  ${requiredFiles.length} files OK`);
console.log(`  ${requiredDirs.length} directories OK`);
console.log(`  ${contentFiles.length} content files OK`);
console.log(`  ${requiredScripts.length} scripts OK`);
console.log(`  ${requiredDeps.length} dependencies OK`);
