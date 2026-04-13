/**
 * evidence-export-docs.test.mjs
 *
 * Validates that evidence-export.mdx exists and contains required governance documentation
 *
 * Phase 2 Plan: Public Evidence Export documentation file must exist and cover:
 * - WORM (Write-Once-Read-Many) ledger
 * - Hash chain verification
 * - Policy gate results
 * - Immutable audit trail
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const EVIDENCE_EXPORT_FILE = resolve(
  process.cwd(),
  'src/content/docs/governance/evidence-export.mdx'
);

const REQUIRED_SECTIONS = [
  'Public Evidence Export',
  'What is Evidence',
  'Evidence Structure',
  'Hash Chain Verification',
  'Policy Gate Results',
  'Compliance Audit Records',
  'Smart Contract Evidence',
  'Release Evidence',
  'Incident Response Records',
  'Privacy & Sanitization',
  'Access & Availability',
];

const REQUIRED_KEYWORDS = [
  'immutable',
  'WORM',
  'Write-Once-Read-Many',
  'audit trail',
  'hash chain',
  'evidence',
  'gate',
  'GDPR',
  'eIDAS',
  'MiCA',
  'policy',
  'compliance',
  'signature',
  'cryptographically',
  'verifiable',
];

describe('Evidence Export Documentation', () => {
  it('should have evidence-export.mdx file', () => {
    expect(existsSync(EVIDENCE_EXPORT_FILE)).toBe(true);
  });

  it('should have valid frontmatter', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toMatch(/^---[\s\S]*?---/);
    expect(content).toContain('title:');
    expect(content).toContain('description:');
    expect(content).toContain('Public Evidence Export');
  });

  it('should contain all required sections', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    REQUIRED_SECTIONS.forEach((section) => {
      expect(content).toContain(`## ${section}`);
    });
  });

  it('should contain all required keywords', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8').toLowerCase();

    REQUIRED_KEYWORDS.forEach((keyword) => {
      expect(content).toContain(keyword.toLowerCase());
    });
  });

  it('should explain WORM (Write-Once-Read-Many)', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('WORM');
    expect(content).toContain('Write-Once-Read-Many');
    expect(content).toContain('immutable');
  });

  it('should include hash chain verification instructions', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Hash Chain Verification');
    expect(content).toContain('hash chain');
    expect(content).toContain('verify-evidence-chain');
  });

  it('should document policy gate results', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Policy Gate Results');
    expect(content).toContain('secret-scan');
    expect(content).toContain('denylist-gate');
    expect(content).toContain('structure-guard');
  });

  it('should include compliance frameworks (GDPR, eIDAS, MiCA)', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('GDPR');
    expect(content).toContain('eIDAS');
    expect(content).toContain('MiCA');
    expect(content).toContain('SOC 2');
  });

  it('should have privacy & sanitization section', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Privacy & Sanitization');
    expect(content).toContain('PII');
    expect(content).toContain('Private keys');
  });

  it('should document smart contract anchoring', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Smart Contract Evidence');
    expect(content).toContain('Ethereum Sepolia');
    expect(content).toContain('Polygon Mumbai');
  });

  it('should explain incident response logging', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Incident Response');
    expect(content).toContain('root_cause');
    expect(content).toContain('post_mortem');
  });

  it('should document access methods (JSON, CSV, JSONL)', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('evidence-export.json');
    expect(content).toContain('evidence-export.csv');
    expect(content).toContain('evidence-export.jsonl');
    expect(content).toContain('JSON');
    expect(content).toContain('CSV');
    expect(content).toContain('Streaming');
  });

  it('should include verification examples with GPG/OpenSSL', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('gpg');
    expect(content).toContain('openssl');
    expect(content).toContain('signature');
    expect(content).toContain('Verified OK');
  });

  it('should have meaningful content (>2000 chars)', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');
    expect(content.length).toBeGreaterThan(2000);
  });

  it('should include cross-references to related pages', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('./evidence');
    expect(content).toContain('./policy-gates');
    expect(content).toContain('./pr-only');
  });

  it('should document 10-year retention policy', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('10-year');
    expect(content).toContain('retention');
  });

  it('should list supported export formats', () => {
    const content = readFileSync(EVIDENCE_EXPORT_FILE, 'utf-8');

    expect(content).toContain('Evidence Export Formats');
    const formatsMatch = content.match(/JSON|CSV|JSONL/g);
    expect(formatsMatch).toBeTruthy();
    expect(formatsMatch.length).toBeGreaterThanOrEqual(3);
  });
});
