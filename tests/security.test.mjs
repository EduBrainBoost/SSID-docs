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

export function run() {
  const output = [];
  let errors = 0;

  // === 1. Check ingest.mjs does NOT have --local-ssid option ===
  const ingestContent = fs.readFileSync(path.join(ROOT, 'tools', 'ingest.mjs'), 'utf-8');

  if (ingestContent.includes('--local-ssid')) {
    output.push('  FAIL: ingest.mjs contains --local-ssid option (private repo access)');
    errors++;
  }

  if (ingestContent.includes('localSsidPath') || ingestContent.includes('local-ssid')) {
    output.push('  FAIL: ingest.mjs references local SSID path');
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
        output.push(`  FAIL: Dangerous pattern "${desc}" in ${path.relative(ROOT, filePath)}`);
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
        // Skip pattern definition files — they contain patterns as scan rules, not real references
        // Per ADR-0001: Workflow File Exclusion from CI Gate Pattern Scans
        if (entry.name === 'docs_ci.yml' || entry.name === 'validate-ingest-source.mjs' || entry.name === 'validate-ingest-source.yml') continue;
        scanFileForPatterns(full);
      }
    }
  }

  scanDir(path.join(ROOT, 'tools'));
  scanDir(path.join(ROOT, '.github'));
  scanDir(path.join(ROOT, 'scripts'));

  // === 3. Check ingest.mjs has allowlist enforcement ===
  if (!ingestContent.includes('ALLOWED_PATHS')) {
    output.push('  FAIL: ingest.mjs missing ALLOWED_PATHS allowlist');
    errors++;
  }

  if (!ingestContent.includes('BLOCKED_PATTERNS')) {
    output.push('  FAIL: ingest.mjs missing BLOCKED_PATTERNS blocklist');
    errors++;
  }

  if (!ingestContent.includes('SECRET_PATTERNS')) {
    output.push('  FAIL: ingest.mjs missing SECRET_PATTERNS scan');
    errors++;
  }

  if (!ingestContent.includes('validateSourceIsPublic')) {
    output.push('  FAIL: ingest.mjs missing validateSourceIsPublic guard');
    errors++;
  }

  // === 4. Check ingest.mjs has absolute path detection ===
  if (!ingestContent.includes('ABSOLUTE_PATH_PATTERNS')) {
    output.push('  FAIL: ingest.mjs missing ABSOLUTE_PATH_PATTERNS guard');
    errors++;
  }

  // === 5. Check PUBLIC_POLICY.md exists ===
  if (!fs.existsSync(path.join(ROOT, 'PUBLIC_POLICY.md'))) {
    output.push('  FAIL: PUBLIC_POLICY.md missing');
    errors++;
  }

  // === 6. Check CI has required gates ===
  const ciPath = path.join(ROOT, '.github', 'workflows', 'docs_ci.yml');
  if (fs.existsSync(ciPath)) {
    const ciContent = fs.readFileSync(ciPath, 'utf-8');
    if (!ciContent.includes('secret') && !ciContent.includes('Secret')) {
      output.push('  FAIL: CI workflow missing secret scan step');
      errors++;
    }
    if (!ciContent.includes('denylist-gate')) {
      output.push('  FAIL: CI workflow missing denylist-gate job');
      errors++;
    }
  }

  // === 7. Verify no .env files exist ===
  function checkNoEnvFiles(dir) {
    if (!fs.existsSync(dir)) return;
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.name === 'node_modules' || entry.name === '.git') continue;
      if (entry.isDirectory()) {
        checkNoEnvFiles(full);
      } else if (entry.name.startsWith('.env') && entry.name !== '.env.example') {
        output.push(`  FAIL: .env file found: ${path.relative(ROOT, full)}`);
        errors++;
      }
    }
  }

  checkNoEnvFiles(ROOT);

  if (errors > 0) {
    output.push(`  ${errors} security error(s) found`);
    throw new Error(`${errors} security check(s) failed`);
  }

  output.push('  No private repo access patterns');
  output.push('  No dangerous sync/mirror patterns');
  output.push('  Allowlist enforcement verified');
  output.push('  Absolute path detection verified');
  output.push('  CI denylist-gate verified');
  output.push('  PUBLIC_POLICY.md present');
  output.push('  Secret scan in CI verified');
  output.push('  No .env files found');

  return output;
}
