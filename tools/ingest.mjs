/**
 * SSID Docs - Deterministic Content Ingest
 *
 * SECURITY: Only reads from SSID-open-core (public).
 * NEVER reads from private SSID repo. No mirroring, no bulk copying.
 * Allowlist-based: only explicitly listed paths are ingested.
 * NO LLM calls. Deterministic only: file scan + index generation.
 *
 * Usage:
 *   node tools/ingest.mjs [--open-core <path>]
 *
 * Default:
 *   --open-core: ../SSID-open-core
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const DOCS_ROOT = path.resolve(import.meta.dirname, '..');
const DEFAULT_OPEN_CORE = path.resolve(DOCS_ROOT, '..', 'SSID-open-core');

// === ALLOWLIST: Only these paths from open-core are ingested ===
const ALLOWED_PATHS = [
  'docs/',
  'policies/',
  'README.md',
  'LICENSE',
  'SECURITY.md',
];

const ALLOWED_EXTENSIONS = ['.md', '.mdx', '.json', '.yaml', '.yml'];

// === BLOCKLIST: These patterns are NEVER ingested ===
const BLOCKED_PATTERNS = [
  /\.env/i,
  /\.key$/i,
  /\.pem$/i,
  /credentials/i,
  /secret/i,
  /private/i,
  /password/i,
  /token.*\.json$/i,
  /audit.*log/i,
  /worm/i,
  /internal/i,
  /\.git\//,
  /node_modules\//,
];

// === SECRET PATTERNS: Files containing these are rejected ===
const SECRET_PATTERNS = [
  /sk_live_/,
  /sk_test_/,
  /PRIVATE[\s_-]?KEY/,
  /-----BEGIN.*KEY-----/,
  /password\s*[:=]\s*["'][^"']{4,}["']/i,
  /api[_-]?key\s*[:=]\s*["'][^"']{8,}["']/i,
  /ghp_[A-Za-z0-9_]{36}/,
  /gho_[A-Za-z0-9_]{36}/,
];

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { openCorePath: DEFAULT_OPEN_CORE };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--open-core' && args[i + 1]) {
      config.openCorePath = path.resolve(args[++i]);
    }
  }

  return config;
}

function hashFile(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

function isAllowed(relativePath) {
  // Check blocklist first (deny takes priority)
  for (const pattern of BLOCKED_PATTERNS) {
    if (pattern.test(relativePath)) {
      console.warn(`[ingest] BLOCKED (pattern): ${relativePath}`);
      return false;
    }
  }

  // Check allowlist
  const allowed = ALLOWED_PATHS.some((prefix) => relativePath.startsWith(prefix));
  if (!allowed) {
    return false; // Silent skip for non-allowed paths
  }

  // Check extension
  const ext = path.extname(relativePath).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return false;
  }

  return true;
}

function containsSecrets(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    for (const pattern of SECRET_PATTERNS) {
      if (pattern.test(content)) {
        console.error(`[ingest] SECRET DETECTED in: ${filePath}`);
        return true;
      }
    }
  } catch {
    // Binary file or read error — skip
    return false;
  }
  return false;
}

function scanDirectory(baseDir, currentDir) {
  const results = [];

  if (!fs.existsSync(currentDir)) {
    console.warn(`[ingest] Directory not found: ${currentDir}`);
    return results;
  }

  const entries = fs.readdirSync(currentDir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(currentDir, entry.name);
    const relativePath = path.relative(baseDir, fullPath).replace(/\\/g, '/');

    if (entry.isDirectory()) {
      results.push(...scanDirectory(baseDir, fullPath));
    } else if (isAllowed(relativePath)) {
      if (containsSecrets(fullPath)) {
        console.error(`[ingest] REJECTED (secrets): ${relativePath}`);
        continue;
      }
      results.push({
        path: fullPath,
        relativePath,
        hash: hashFile(fullPath),
        size: fs.statSync(fullPath).size,
      });
    }
  }

  return results;
}

function writeIndex(indexPath, entries, sourceName) {
  const index = {
    generated_utc: new Date().toISOString(),
    source: sourceName,
    source_type: 'SSID-open-core (public only)',
    deterministic: true,
    llm_used: false,
    private_repo_accessed: false,
    allowlist_enforced: true,
    secret_scan_passed: true,
    entry_count: entries.length,
    entries: entries.map((e) => ({
      relativePath: e.relativePath,
      hash: `sha256:${e.hash}`,
      size: e.size,
    })),
  };

  fs.mkdirSync(path.dirname(indexPath), { recursive: true });
  fs.writeFileSync(indexPath, JSON.stringify(index, null, 2), 'utf-8');
  console.log(`[ingest] Index written: ${indexPath} (${entries.length} entries)`);
}

function validateSourceIsPublic(sourcePath) {
  const resolvedSource = path.resolve(sourcePath).replace(/\\/g, '/').toLowerCase();

  // Block if path points to private SSID repo
  if (resolvedSource.includes('/ssid') && !resolvedSource.includes('/ssid-open-core') && !resolvedSource.includes('/ssid-docs')) {
    console.error('[ingest] SECURITY ERROR: Source path points to private SSID repo!');
    console.error(`[ingest] Path: ${sourcePath}`);
    console.error('[ingest] Only SSID-open-core is allowed as source.');
    process.exit(1);
  }
}

function main() {
  const config = parseArgs();

  console.log('[ingest] SSID Docs - Deterministic Content Ingest');
  console.log('[ingest] SECURITY: Only SSID-open-core (public) is used as source');
  console.log(`[ingest] Source: ${config.openCorePath}`);

  // Validate source is not private repo
  validateSourceIsPublic(config.openCorePath);

  // Scan open-core (allowlist-filtered + secret-scanned)
  const entries = scanDirectory(config.openCorePath, config.openCorePath);
  writeIndex(
    path.join(DOCS_ROOT, 'src', 'content', 'ingest', 'open-core-index.json'),
    entries,
    'SSID-open-core'
  );

  console.log('[ingest] Done. No LLM calls. No private repo access.');
}

main();
