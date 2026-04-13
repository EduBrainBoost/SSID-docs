/**
 * deployment-docs-presence.test.mjs
 *
 * Validates that all required deployment documentation files exist
 *
 * Phase 2 Plan: 4 deployment guide files are required
 * - local-stack
 * - ports-matrix-current
 * - testnet-guide
 * - testnet-addresses
 * - mainnet-readiness
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const DOCS_ROOT = resolve(process.cwd(), 'src/content/docs/deployments');

const REQUIRED_DEPLOYMENT_FILES = [
  {
    name: 'local-stack.md',
    path: 'local-stack.md',
    description: 'Local stack setup guide',
    requiredContent: ['Local Stack', 'G-Workspace', 'G-port'],
  },
  {
    name: 'ports-matrix-current.mdx',
    path: 'ports-matrix-current.mdx',
    description: 'Port matrix reference with G and C ports',
    requiredContent: ['G-Workspace Ports', 'C-Canonical Ports', '3100', '8100', '4331'],
  },
  {
    name: 'testnet-guide.mdx',
    path: 'testnet-guide.mdx',
    description: 'Testnet deployment guide (Sepolia/Mumbai)',
    requiredContent: ['Ethereum Sepolia', 'Polygon Mumbai', 'testnet', 'faucet'],
  },
  {
    name: 'testnet-addresses.mdx',
    path: 'testnet-addresses.mdx',
    description: 'Testnet contract addresses and RPC endpoints',
    requiredContent: ['RPC', 'contract', 'Sepolia', 'Mumbai'],
  },
  {
    name: 'mainnet-readiness.mdx',
    path: 'mainnet-readiness.mdx',
    description: 'Mainnet readiness roadmap and gates',
    requiredContent: ['mainnet', 'NOT LIVE', 'gate', 'readiness'],
  },
];

describe('Deployment Documentation Presence', () => {
  it('should have all required deployment files', () => {
    const missing = [];

    REQUIRED_DEPLOYMENT_FILES.forEach((file) => {
      const filePath = resolve(DOCS_ROOT, file.path);
      if (!existsSync(filePath)) {
        missing.push(file.name);
      }
    });

    expect(missing).toEqual([]);
  });

  it('should have local-stack documentation', () => {
    const filePath = resolve(DOCS_ROOT, 'local-stack.md');
    expect(existsSync(filePath)).toBe(true);

    const content = readFileSync(filePath, 'utf-8');
    expect(content).toContain('G-Workspace');
    expect(content).toContain('3100');
    expect(content).toContain('8100');
  });

  it('should have ports-matrix-current with G and C ports', () => {
    const filePath = resolve(DOCS_ROOT, 'ports-matrix-current.mdx');
    expect(existsSync(filePath)).toBe(true);

    const content = readFileSync(filePath, 'utf-8');
    expect(content).toContain('G-Workspace Ports');
    expect(content).toContain('C-Canonical Ports');
    expect(content).toContain('3100');
    expect(content).toContain('8100');
    expect(content).toContain('4331');
  });

  it('should have testnet deployment guide (Sepolia + Mumbai)', () => {
    const filePath = resolve(DOCS_ROOT, 'testnet-guide.mdx');
    expect(existsSync(filePath)).toBe(true);

    const content = readFileSync(filePath, 'utf-8');
    expect(content).toContain('Ethereum Sepolia');
    expect(content).toContain('Polygon Mumbai');
    expect(content).toContain('faucet');
    expect(content).toContain('testnet');
  });

  it('should have testnet addresses and RPC endpoints', () => {
    const filePath = resolve(DOCS_ROOT, 'testnet-addresses.mdx');
    expect(existsSync(filePath)).toBe(true);

    const content = readFileSync(filePath, 'utf-8');
    expect(content).toContain('RPC');
    expect(content).toContain('Sepolia');
    expect(content).toContain('Mumbai');
    expect(content).toContain('contract');
  });

  it('should have mainnet readiness roadmap with disclaimer', () => {
    const filePath = resolve(DOCS_ROOT, 'mainnet-readiness.mdx');
    expect(existsSync(filePath)).toBe(true);

    const content = readFileSync(filePath, 'utf-8');
    expect(content).toContain('NOT LIVE');
    expect(content).toContain('mainnet');
    expect(content).toContain('gate');
    expect(content).toContain('readiness');
  });

  it('should have all required files with valid frontmatter', () => {
    REQUIRED_DEPLOYMENT_FILES.forEach((file) => {
      const filePath = resolve(DOCS_ROOT, file.path);
      if (existsSync(filePath)) {
        const content = readFileSync(filePath, 'utf-8');

        // Check for MDX/MD frontmatter
        expect(content).toMatch(/^---[\s\S]*?---/);

        // Check for title and description
        expect(content).toContain('title:');
        expect(content).toContain('description:');
      }
    });
  });

  it('should have deployment docs with meaningful content', () => {
    REQUIRED_DEPLOYMENT_FILES.forEach((file) => {
      const filePath = resolve(DOCS_ROOT, file.path);
      if (existsSync(filePath)) {
        const content = readFileSync(filePath, 'utf-8');

        // Check minimum content length (at least 1000 chars = ~200 words)
        expect(content.length).toBeGreaterThan(1000);

        // Check for required keywords
        file.requiredContent.forEach((keyword) => {
          expect(content.toLowerCase()).toContain(keyword.toLowerCase());
        });
      }
    });
  });

  it('should have no stale dates in deployment docs', () => {
    const STALE_DATE = '2026-03-02'; // Known stale date from Phase 1

    REQUIRED_DEPLOYMENT_FILES.forEach((file) => {
      const filePath = resolve(DOCS_ROOT, file.path);
      if (existsSync(filePath)) {
        const content = readFileSync(filePath, 'utf-8');

        // Should not contain stale dates
        expect(content).not.toContain(STALE_DATE);
      }
    });
  });

  it('should have cross-references between deployment pages', () => {
    const ports = readFileSync(resolve(DOCS_ROOT, 'ports-matrix-current.mdx'), 'utf-8');
    const testnet = readFileSync(resolve(DOCS_ROOT, 'testnet-guide.mdx'), 'utf-8');
    const mainnet = readFileSync(resolve(DOCS_ROOT, 'mainnet-readiness.mdx'), 'utf-8');

    // Cross-links between pages
    expect(ports).toContain('../deployments/local-stack');
    expect(testnet).toContain('./ports-matrix-current');
    expect(mainnet).toContain('./testnet-guide');
  });
});
