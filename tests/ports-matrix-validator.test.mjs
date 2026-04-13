/**
 * ports-matrix-validator.test.mjs
 *
 * Validates that documentation uses G-workspace ports (3100, 8100, etc.)
 * and NOT C-canonical ports (3000, 8000, etc.)
 *
 * Critical for preventing port matrix confusion in development environments.
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const DOCS_ROOT = resolve(process.cwd(), 'src/content/docs');
const CONFIG_FILE = resolve(process.cwd(), 'astro.config.mjs');

// Files to check for port matrix correctness
const FILES_TO_CHECK = [
  'deployments/ports-matrix-current.mdx',
  'operations/local-stack.md',
  'tooling/ems-control-plane.mdx',
  'tooling/orchestrator-runtime.mdx',
];

// G-Workspace (correct) ports
const G_PORTS = {
  3100: 'EMS Portal Frontend',
  8100: 'EMS Backend API',
  3310: 'Orchestrator API',
  5273: 'Orchestrator Web UI',
  4331: 'SSID-docs',
  4332: 'CCT Dashboard (future)',
};

// C-Canonical (production-only) ports - should NOT appear in dev docs
const C_PORTS = {
  3000: 'EMS Portal Frontend (C)',
  8000: 'EMS Backend API (C)',
  3001: 'Legacy Website (C)',
  3002: 'CCT Docs (C)',
  3210: 'Orchestrator API (C)',
  5173: 'Orchestrator Web UI (C)',
  4321: 'SSID-docs (C)',
  4322: 'CCT Dashboard (C)',
};

describe('Port Matrix Validation', () => {
  it('should use G-workspace ports (3100, 8100) in development docs', () => {
    let foundGPorts = false;
    let violations = [];

    FILES_TO_CHECK.forEach((file) => {
      const filePath = resolve(DOCS_ROOT, file);
      const content = readFileSync(filePath, 'utf-8');

      // Check for G-Ports (should be present)
      Object.keys(G_PORTS).forEach((port) => {
        if (content.includes(port.toString())) {
          foundGPorts = true;
        }
      });

      // Check for C-Ports (should NOT be present, except in port-matrix-current for reference)
      Object.keys(C_PORTS).forEach((port) => {
        if (content.includes(port.toString())) {
          // Allow C-ports in ports-matrix-current.mdx (reference table)
          if (file !== 'deployments/ports-matrix-current.mdx') {
            violations.push(`File ${file} contains C-port ${port} (${C_PORTS[port]})`);
          }
        }
      });
    });

    // Assert: G-ports found and no violations
    expect(violations).toEqual([]);
    expect(foundGPorts).toBe(true);
  });

  it('should NOT contain legacy C-ports (3000, 8000) in local-stack.md', () => {
    const filePath = resolve(DOCS_ROOT, 'operations/local-stack.md');
    const content = readFileSync(filePath, 'utf-8');

    expect(content).not.toContain('3000');
    expect(content).not.toContain('8000');
    expect(content).toContain('3100');
    expect(content).toContain('8100');
  });

  it('should reference G-ports in ports-matrix-current.mdx', () => {
    const filePath = resolve(DOCS_ROOT, 'deployments/ports-matrix-current.mdx');
    const content = readFileSync(filePath, 'utf-8');

    // G-ports section
    expect(content).toContain('G-Workspace Ports (Development)');
    expect(content).toContain('3100');
    expect(content).toContain('8100');
    expect(content).toContain('3310');
    expect(content).toContain('5273');
    expect(content).toContain('4331');

    // C-ports section (for reference)
    expect(content).toContain('C-Canonical Ports (Production)');
    expect(content).toContain('3000');
    expect(content).toContain('8000');
  });

  it('should include port correction warnings for legacy users', () => {
    const filePath = resolve(DOCS_ROOT, 'deployments/ports-matrix-current.mdx');
    const content = readFileSync(filePath, 'utf-8');

    expect(content).toContain('INCORRECT');
    expect(content).toContain('CORRECT');
    expect(content).toContain('legacy');
  });
});
