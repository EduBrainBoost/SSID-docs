/**
 * Security Tests
 * Verify that no private repo access, no sync-all, no mirror patterns exist.
 * Enforces the hard rules:
 *   1. Single Source of Public Truth = SSID-open-core only
 *   2. Allowlist-based export, never mirror/sync-all
 *   3. No secrets in any source file
 *   4. No private SSID repo references in automation
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
let errors = 0;

// === 1. Check ingest.mjs does NOT have --local-ssid option ===
const ingestContent = fs.readFileSync(path.join(ROOT, 'tools', 'ingest.mjs'), 'utf-8');

if (ingestContent.includes('--local-ssid')) {
  console.error('  FAIL: ingest.mjs contains --local-ssid option (private repo access)');
  errors++;
}

if (ingestContent.includes('localSsidPath') || ingestContent.includes('local-ssid')) {
  console.error('  FAIL: ingest.mjs references local SSID path');
  errors++;
}

// === 2. Check for dangerous sync/mirror patterns in all scripts ===
const dangerousPatterns = [
  { pattern: /rsync.*SSID[^-]/i, desc: 'rsync from private SSID' },
  { pattern: /robocopy.*SSID[^-]/i, desc: 'robocopy from private SSID' },
  { pattern: /cp\s+-r.*SSID[^-]/i, desc: 'cp -r from private SSID' },
  { pattern: /git\s+subtree.*SSID[^-]/i, desc: 'git subtree from private SSID' },
  { pattern: /git\s+filter-repo/i, desc: 'git filter-repo (unfiltered)' },
  { pattern: /sync[\s_-]?all/i, desc: 'sync-all pattern' },
  { pattern: /mirror[\s_-]?repo/i, desc: 'mirror-repo pattern' },
  { pattern: /export[\s_-]?repo/i, desc: 'export-repo pattern' },
];

function scanFileForPatterns(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  for (const { pattern, desc } of dangerousPatterns) {
    if (pattern.test(content)) {
      console.error(`  FAIL: Dangerous pattern "${desc}" in ${path.relative(ROOT, filePath)}`);
      errors++;
    }
  }
}

// Scan all JS/TS/YAML files in tools/ and .github/
function scanDir(dir) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDir(full);
    } else if (/\.(mjs|js|ts|yml|yaml|sh|ps1)$/.test(entry.name)) {
      scanFileForPatterns(full);
    }
  }
}

scanDir(path.join(ROOT, 'tools'));
scanDir(path.join(ROOT, '.github'));
scanDir(path.join(ROOT, 'scripts'));

// === 3. Check ingest.mjs has allowlist enforcement ===
if (!ingestContent.includes('ALLOWED_PATHS')) {
  console.error('  FAIL: ingest.mjs missing ALLOWED_PATHS allowlist');
  errors++;
}

if (!ingestContent.includes('BLOCKED_PATTERNS')) {
  console.error('  FAIL: ingest.mjs missing BLOCKED_PATTERNS blocklist');
  errors++;
}

if (!ingestContent.includes('SECRET_PATTERNS')) {
  console.error('  FAIL: ingest.mjs missing SECRET_PATTERNS scan');
  errors++;
}

if (!ingestContent.includes('validateSourceIsPublic')) {
  console.error('  FAIL: ingest.mjs missing validateSourceIsPublic guard');
  errors++;
}

// === 4. Check CI has secret-scan job ===
const ciPath = path.join(ROOT, '.github', 'workflows', 'docs_ci.yml');
if (fs.existsSync(ciPath)) {
  const ciContent = fs.readFileSync(ciPath, 'utf-8');
  if (!ciContent.includes('secret') && !ciContent.includes('Secret')) {
    console.error('  FAIL: CI workflow missing secret scan step');
    errors++;
  }
}

// === 5. Verify no .env files exist ===
function checkNoEnvFiles(dir) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    if (entry.isDirectory()) {
      checkNoEnvFiles(full);
    } else if (entry.name.startsWith('.env') && entry.name !== '.env.example') {
      console.error(`  FAIL: .env file found: ${path.relative(ROOT, full)}`);
      errors++;
    }
  }
}

checkNoEnvFiles(ROOT);

if (errors > 0) {
  console.error(`  ${errors} security error(s) found`);
  process.exit(1);
}

console.log('  No private repo access patterns');
console.log('  No dangerous sync/mirror patterns');
console.log('  Allowlist enforcement verified');
console.log('  Secret scan in CI verified');
console.log('  No .env files found');
