/**
 * sidebar-soll-categories.test.mjs
 *
 * Validates that all SOLL (target) sidebar categories are present in astro.config.mjs
 *
 * Phase 2 Plan required: 15 categories minimum (was 11, added 4)
 * - System Architecture & Integration
 * - Deployments & Networks
 * - Integration & Tools (renamed from Tooling)
 * - System Status & Evidence
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const CONFIG_FILE = resolve(process.cwd(), 'astro.config.mjs');

// SOLL categories (expected/target)
const SOLL_CATEGORIES = [
  'Overview',
  'System Architecture & Integration',
  'Identity',
  'Governance',
  'Compliance',
  'Integration & Tools',
  'Token',
  'Developer',
  'Deployments & Networks',
  'Operations',
  'Research',
  'FAQ',
  'System Status & Evidence',
  'Project',
];

const SOLL_DEPLOYMENT_ITEMS = [
  'Local Stack Setup',
  'Port Matrix (Current)',
  'Testnet Deployment Guide',
  'Testnet Addresses & RPC',
  'Mainnet Readiness Roadmap',
];

const SOLL_ARCHITECTURE_ITEMS = [
  '5-Repo System Topology',
  'Orchestrator Integration',
];

const SOLL_TOOLING_ITEMS = [
  'EMS Control Plane (CLI)',
  'EMS Portal Walkthrough',
  'Orchestrator Runtime',
];

describe('Sidebar SOLL Categories', () => {
  let configContent;

  beforeEach(() => {
    configContent = readFileSync(CONFIG_FILE, 'utf-8');
  });

  it('should have all 14+ SOLL top-level categories', () => {
    const missing = [];

    SOLL_CATEGORIES.forEach((category) => {
      if (!configContent.includes(`label: '${category}'`)) {
        missing.push(category);
      }
    });

    expect(missing).toEqual([]);
  });

  it('should have Deployments & Networks category with all required items', () => {
    // Find the Deployments & Networks section
    const deploymentsMatch = configContent.match(
      /label:\s*['"]Deployments\s*&\s*Networks['"][\s\S]*?(?=\},?\s*\{|\]\s*,)/
    );

    expect(deploymentsMatch).toBeTruthy();
    const deploymentsSection = deploymentsMatch[0];

    SOLL_DEPLOYMENT_ITEMS.forEach((item) => {
      expect(deploymentsSection).toContain(item);
    });
  });

  it('should have System Architecture & Integration category', () => {
    const architectureMatch = configContent.match(
      /label:\s*['"]System Architecture\s*&\s*Integration['"][\s\S]*?(?=\},?\s*\{|\]\s*,)/
    );

    expect(architectureMatch).toBeTruthy();
  });

  it('should have 5-Repo System Topology in architecture section', () => {
    expect(configContent).toContain('5-Repo System Topology');
    expect(configContent).toContain('architecture/5-repo-topology');
  });

  it('should have System Status & Evidence category', () => {
    const statusMatch = configContent.match(
      /label:\s*['"]System Status\s*&\s*Evidence['"][\s\S]*?(?=\},?\s*\{|\]\s*,)/
    );

    expect(statusMatch).toBeTruthy();
  });

  it('should have Integration & Tools category (renamed from Tooling)', () => {
    expect(configContent).toContain('Integration & Tools');
  });

  it('should have EMS Control Plane and Orchestrator Runtime in tooling section', () => {
    const toolingMatch = configContent.match(
      /label:\s*['"]Integration\s*&\s*Tools['"][\s\S]*?(?=\},?\s*\{|\]\s*,)/
    );

    expect(toolingMatch).toBeTruthy();
    const toolingSection = toolingMatch[0];

    expect(toolingSection).toContain('EMS Control Plane (CLI)');
    expect(toolingSection).toContain('Orchestrator Runtime');
  });

  it('should have correct slugs for new deployment pages', () => {
    const deploymentSlugs = [
      'deployments/local-stack',
      'deployments/ports-matrix-current',
      'deployments/testnet-guide',
      'deployments/testnet-addresses',
      'deployments/mainnet-readiness',
    ];

    deploymentSlugs.forEach((slug) => {
      expect(configContent).toContain(`slug: '${slug}'`);
    });
  });

  it('should have correct slugs for new tooling pages', () => {
    const toolingSlugs = [
      'tooling/ems-control-plane',
      'tooling/orchestrator-runtime',
    ];

    toolingSlugs.forEach((slug) => {
      expect(configContent).toContain(`slug: '${slug}'`);
    });
  });

  it('should have correct slug for 5-repo-topology', () => {
    expect(configContent).toContain(`slug: 'architecture/5-repo-topology'`);
  });

  it('should have Operating category for troubleshooting', () => {
    expect(configContent).toContain('Operations');
    expect(configContent).toContain('operations/troubleshooting');
  });

  it('should maintain alphabetical-ish ordering of categories', () => {
    // Extract categories in order
    const categoryMatches = configContent.match(/label:\s*['"]([^'"]+)['"]/g);
    const categories = categoryMatches.map((m) => m.match(/label:\s*['"]([^'"]+)['"]/)[1]);

    // Check that core categories appear in expected order
    const overviewIdx = categories.indexOf('Overview');
    const architectureIdx = categories.indexOf('System Architecture & Integration');
    const complianceIdx = categories.indexOf('Compliance');
    const deploymentsIdx = categories.indexOf('Deployments & Networks');

    expect(overviewIdx).toBeLessThan(architectureIdx);
    expect(architectureIdx).toBeLessThan(complianceIdx);
    expect(complianceIdx).toBeLessThan(deploymentsIdx);
  });
});
