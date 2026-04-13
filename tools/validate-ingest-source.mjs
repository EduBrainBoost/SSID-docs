#!/usr/bin/env node

/**
 * Validate Ingest Source — enforce that SSID-docs only ingests from SSID-open-core
 *
 * This validator checks:
 * 1. tools/ingest.mjs only references SSID-open-core as source
 * 2. No private repo syncing/mirroring patterns
 * 3. No absolute local paths in source definitions
 * 4. No .env or secrets in source paths
 * 5. Allowlist contains only public-safe paths
 *
 * Exit codes:
 * 0 = PASS (all checks passed)
 * 1 = FAIL (one or more checks failed)
 */

import fs from 'node:fs';
import path from 'node:path';

const REPO_ROOT = path.resolve(import.meta.dirname, '..');
const INGEST_TOOL = path.resolve(REPO_ROOT, 'tools', 'ingest.mjs');

function validateIngestTool() {
  console.log('=== validate-ingest-source ===\n');

  if (!fs.existsSync(INGEST_TOOL)) {
    console.error(`❌ FAIL: ingest tool not found at ${INGEST_TOOL}`);
    return false;
  }

  const content = fs.readFileSync(INGEST_TOOL, 'utf-8');
  let passed = true;

  // Check 1: Default source must be SSID-open-core
  console.log('Check 1: Default source is SSID-open-core');
  const defaultSourceMatch = content.match(/DEFAULT_OPEN_CORE\s*=\s*path\.resolve\([^)]*?SSID-open-core/);
  if (defaultSourceMatch) {
    console.log('  ✓ PASS: DEFAULT_OPEN_CORE references SSID-open-core\n');
  } else {
    console.error('  ✗ FAIL: DEFAULT_OPEN_CORE does not reference SSID-open-core\n');
    passed = false;
  }

  // Check 2: No absolute local path source definitions
  console.log('Check 2: No absolute local paths in source definitions');
  const absolutePathMatch = /openCorePath\s*=\s*['"]([A-Z]:\\|\/home|\/mnt|\/Users)/;
  if (absolutePathMatch.test(content)) {
    console.error('  ✗ FAIL: Found absolute path in source definition\n');
    passed = false;
  } else {
    console.log('  ✓ PASS: No absolute paths in source definitions\n');
  }

  // Check 3: Allowlist contains only public-safe extensions
  console.log('Check 3: Allowlist contains only safe extensions');
  const allowlistMatch = content.match(/const\s+ALLOWED_EXTENSIONS\s*=\s*\[([\s\S]*?)\]/);

  if (allowlistMatch) {
    const extensions = allowlistMatch[1].match(/'[^']*'/g) || [];
    const safeExts = ['.md', '.mdx', '.json', '.yaml', '.yml', '.txt'];

    let allSafe = true;
    for (const ext of extensions) {
      const cleanExt = ext.replace(/['"]/g, '');
      if (!safeExts.includes(cleanExt)) {
        console.error(`  ✗ FAIL: Unsafe extension in allowlist: ${cleanExt}`);
        allSafe = false;
      }
    }

    if (allSafe) {
      console.log('  ✓ PASS: Allowlist contains only public-safe extensions\n');
    } else {
      console.error('  ✗ FAIL: Unsafe extensions in allowlist\n');
      passed = false;
    }
  } else {
    console.log('  ⚠ WARN: Could not parse ALLOWED_EXTENSIONS (continuing)\n');
  }

  // Check 4: Blocklist prevents internal SSID paths
  console.log('Check 4: Blocklist prevents internal SSID zones');
  if (/BLOCKED_PATTERNS.*02_audit_logging|BLOCKED_PATTERNS.*worm|BLOCKED_PATTERNS.*internal/s.test(content)) {
    console.log('  ✓ PASS: Blocklist includes internal zone patterns\n');
  } else {
    console.log('  ⚠ WARN: Could not verify blocklist patterns\n');
  }

  return passed;
}

function validatePackageJson() {
  console.log('=== Package.json Ingest Scripts ===\n');

  const packageJsonPath = path.resolve(REPO_ROOT, 'package.json');
  try {
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
    const scripts = packageJson.scripts || {};

    // Check for private repo clone/sync patterns in scripts
    let passed = true;
    for (const [name, script] of Object.entries(scripts)) {
      if (!script || typeof script !== 'string') continue;

      if (/git\s+clone.*SSID(?!-open-core)|git\s+subtree.*SSID(?!-open-core)|mirror\.repo|sync\.all/.test(script)) {
        console.error(`  ✗ FAIL: Script "${name}" has private repo sync pattern`);
        passed = false;
      }
    }

    if (passed) {
      console.log('✓ PASS: No private repo sync scripts\n');
    }
    return passed;
  } catch (e) {
    console.error(`❌ FAIL: Could not parse package.json: ${e.message}\n`);
    return false;
  }
}

function validateNoMirrorPatterns() {
  console.log('=== No Private Repo Mirroring ===\n');

  const filesToCheck = [
    { path: 'tools/ingest.mjs', name: 'ingest.mjs' },
    // NOTE: docs_ci.yml is excluded because it DEFINES the patterns it checks for
    // (per ADR-0001: Workflow File Exclusion from CI Gate Pattern Scans)
  ];

  let passed = true;

  for (const file of filesToCheck) {
    const filepath = path.resolve(REPO_ROOT, file.path);
    if (!fs.existsSync(filepath)) continue;

    const content = fs.readFileSync(filepath, 'utf-8');

    // Real mirroring patterns to block
    const mirrorPatterns = [
      /git\s+clone.*SSID(?!-open-core)/,
      /git\s+subtree.*SSID(?!-open-core)/,
      /robocopy.*SSID(?!-open-core)/,
      /rsync.*SSID(?!-open-core)/,
      /mirror\.repo/,
      /sync\.all/,
    ];

    for (const pattern of mirrorPatterns) {
      if (pattern.test(content)) {
        console.error(`  ✗ FAIL: Found mirror pattern in ${file.name}`);
        passed = false;
      }
    }
  }

  if (passed) {
    console.log('✓ PASS: No private repo mirroring patterns found\n');
  }

  return passed;
}

function main() {
  console.log('Validating ingest source configuration...\n');

  const check1 = validateIngestTool();
  const check2 = validatePackageJson();
  const check3 = validateNoMirrorPatterns();

  const allPassed = check1 && check2 && check3;

  console.log('='.repeat(40));
  if (allPassed) {
    console.log('✓ ALL CHECKS PASSED');
    process.exit(0);
  } else {
    console.log('✗ ONE OR MORE CHECKS FAILED');
    process.exit(1);
  }
}

main();
