/**
 * Structure Tests
 * Verify that all required files and directories exist.
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

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

export function run() {
  let errors = 0;
  const messages = [];

  // Check required files
  for (const file of requiredFiles) {
    const fullPath = path.join(ROOT, file);
    if (!fs.existsSync(fullPath)) {
      messages.push(`  MISSING file: ${file}`);
      errors++;
    }
  }

  // Check required directories
  for (const dir of requiredDirs) {
    const fullPath = path.join(ROOT, dir);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isDirectory()) {
      messages.push(`  MISSING directory: ${dir}`);
      errors++;
    }
  }

  // Check content files
  for (const file of contentFiles) {
    const fullPath = path.join(ROOT, file);
    if (!fs.existsSync(fullPath)) {
      messages.push(`  MISSING content: ${file}`);
      errors++;
    }
  }

  // Check package.json has required scripts
  const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8'));
  const requiredScripts = ['dev', 'build', 'preview', 'test', 'ingest'];
  for (const script of requiredScripts) {
    if (!pkg.scripts?.[script]) {
      messages.push(`  MISSING script: ${script}`);
      errors++;
    }
  }

  // Check dependencies
  const requiredDeps = ['astro', '@astrojs/starlight'];
  for (const dep of requiredDeps) {
    if (!pkg.dependencies?.[dep]) {
      messages.push(`  MISSING dependency: ${dep}`);
      errors++;
    }
  }

  if (errors > 0) {
    messages.push(`  ${errors} structure error(s) found`);
    throw new Error(messages.join('\n'));
  }

  return [
    `  ${requiredFiles.length} files OK`,
    `  ${requiredDirs.length} directories OK`,
    `  ${contentFiles.length} content files OK`,
    `  ${requiredScripts.length} scripts OK`,
    `  ${requiredDeps.length} dependencies OK`,
  ];
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
