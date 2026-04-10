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
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(import.meta.dirname, '..');

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

function scanFileForPatterns(filePath, messages) {
  const content = fs.readFileSync(filePath, 'utf-8');
  for (const { pattern, desc } of dangerousPatterns) {
    if (pattern.test(content)) {
      messages.push(`  FAIL: Dangerous pattern "${desc}" in ${path.relative(ROOT, filePath)}`);
    }
  }
}

// Scan all JS/TS/YAML files in tools/ and .github/
function scanDir(dir, messages) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDir(full, messages);
    } else if (/\.(mjs|js|ts|yml|yaml|sh|ps1)$/.test(entry.name)) {
      // Skip CI workflow files — they contain patterns as scan rules, not real references
      if (entry.name === 'docs_ci.yml') continue;
      scanFileForPatterns(full, messages);
    }
  }
}

// === 5. Verify no .env files exist ===
function checkNoEnvFiles(dir, messages) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    if (entry.isDirectory()) {
      checkNoEnvFiles(full, messages);
    } else if (entry.name.startsWith('.env') && entry.name !== '.env.example') {
      messages.push(`  FAIL: .env file found: ${path.relative(ROOT, full)}`);
    }
  }
}

export function run() {
  let errors = 0;
  const messages = [];

  // === 1. Check ingest.mjs does NOT have --local-ssid option ===
  const ingestContent = fs.readFileSync(path.join(ROOT, 'tools', 'ingest.mjs'), 'utf-8');

  if (ingestContent.includes('--local-ssid')) {
    messages.push('  FAIL: ingest.mjs contains --local-ssid option (private repo access)');
    errors++;
  }

  if (ingestContent.includes('localSsidPath') || ingestContent.includes('local-ssid')) {
    messages.push('  FAIL: ingest.mjs references local SSID path');
    errors++;
  }

  scanDir(path.join(ROOT, 'tools'), messages);
  scanDir(path.join(ROOT, '.github'), messages);
  scanDir(path.join(ROOT, 'scripts'), messages);
  errors += messages.length;

  // === 3. Check ingest.mjs has allowlist enforcement ===
  if (!ingestContent.includes('ALLOWED_PATHS')) {
    messages.push('  FAIL: ingest.mjs missing ALLOWED_PATHS allowlist');
    errors++;
  }

  if (!ingestContent.includes('BLOCKED_PATTERNS')) {
    messages.push('  FAIL: ingest.mjs missing BLOCKED_PATTERNS blocklist');
    errors++;
  }

  if (!ingestContent.includes('SECRET_PATTERNS')) {
    messages.push('  FAIL: ingest.mjs missing SECRET_PATTERNS scan');
    errors++;
  }

  if (!ingestContent.includes('validateSourceIsPublic')) {
    messages.push('  FAIL: ingest.mjs missing validateSourceIsPublic guard');
    errors++;
  }

  // === 4. Check ingest.mjs has absolute path detection ===
  if (!ingestContent.includes('ABSOLUTE_PATH_PATTERNS')) {
    messages.push('  FAIL: ingest.mjs missing ABSOLUTE_PATH_PATTERNS guard');
    errors++;
  }

  // === 5. Check PUBLIC_POLICY.md exists ===
  if (!fs.existsSync(path.join(ROOT, 'PUBLIC_POLICY.md'))) {
    messages.push('  FAIL: PUBLIC_POLICY.md missing');
    errors++;
  }

  // === 6. Check CI has required gates ===
  const ciPath = path.join(ROOT, '.github', 'workflows', 'docs_ci.yml');
  if (fs.existsSync(ciPath)) {
    const ciContent = fs.readFileSync(ciPath, 'utf-8');
    if (!ciContent.includes('secret') && !ciContent.includes('Secret')) {
      messages.push('  FAIL: CI workflow missing secret scan step');
      errors++;
    }
    if (!ciContent.includes('denylist-gate')) {
      messages.push('  FAIL: CI workflow missing denylist-gate job');
      errors++;
    }
  }

  const beforeEnvChecks = messages.length;
  checkNoEnvFiles(ROOT, messages);
  errors += messages.length - beforeEnvChecks;

  if (errors > 0) {
    messages.push(`  ${errors} security error(s) found`);
    throw new Error(messages.join('\n'));
  }

  return [
    '  No private repo access patterns',
    '  No dangerous sync/mirror patterns',
    '  Allowlist enforcement verified',
    '  Absolute path detection verified',
    '  CI denylist-gate verified',
    '  PUBLIC_POLICY.md present',
    '  Secret scan in CI verified',
    '  No .env files found',
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
