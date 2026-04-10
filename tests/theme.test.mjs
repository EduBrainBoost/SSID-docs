/**
 * Theme Tests
 * Verify that the cyberpunk theme CSS contains required variables and rules.
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(import.meta.dirname, '..');
const CSS_FILE = path.join(ROOT, 'src', 'styles', 'cyberpunk.css');

export function run() {
  let errors = 0;
  const messages = [];

  // Check CSS file exists
  if (!fs.existsSync(CSS_FILE)) {
    throw new Error('  MISSING: src/styles/cyberpunk.css');
  }

  const css = fs.readFileSync(CSS_FILE, 'utf-8');

  // Required CSS custom properties
  const requiredVars = [
    '--ssid-neon-cyan',
    '--ssid-neon-magenta',
    '--ssid-bg-deep',
    '--ssid-fg-primary',
    '--ssid-border',
    '--ssid-glow-cyan',
  ];

  for (const varName of requiredVars) {
    if (!css.includes(varName)) {
      messages.push(`  MISSING CSS variable: ${varName}`);
      errors++;
    }
  }

  // Required Starlight theme overrides
  const requiredOverrides = [
    '--sl-color-accent',
    '--sl-color-bg',
    '--sl-color-black',
  ];

  for (const override of requiredOverrides) {
    if (!css.includes(override)) {
      messages.push(`  MISSING Starlight override: ${override}`);
      errors++;
    }
  }

  // Required component classes
  const requiredClasses = [
    '.glass-card',
    '.evidence-card',
    '.sot-card',
  ];

  for (const className of requiredClasses) {
    if (!css.includes(className)) {
      messages.push(`  MISSING component class: ${className}`);
      errors++;
    }
  }

  // Check dark theme scoping
  if (!css.includes('[data-theme=\'dark\']')) {
    messages.push('  MISSING dark theme scoping');
    errors++;
  }

  // Check scanline effect
  if (!css.includes('scanline') && !css.includes('repeating-linear-gradient')) {
    messages.push('  MISSING scanline effect');
    errors++;
  }

  // Check no hardcoded light backgrounds in dark scope
  const lightBgPattern = /\[data-theme='dark'\][^}]*background:\s*(#fff|#ffffff|white)/gi;
  if (lightBgPattern.test(css)) {
    messages.push('  WARNING: Light background found in dark theme scope');
    errors++;
  }

  if (errors > 0) {
    messages.push(`  ${errors} theme error(s) found`);
    throw new Error(messages.join('\n'));
  }

  return [
    `  ${requiredVars.length} CSS variables OK`,
    `  ${requiredOverrides.length} Starlight overrides OK`,
    `  ${requiredClasses.length} component classes OK`,
    '  Dark theme scoping OK',
    '  Scanline effect OK',
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
