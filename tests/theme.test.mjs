/**
 * Theme Tests
 * Verify that the cyberpunk theme CSS contains required variables and rules.
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const CSS_FILE = path.join(ROOT, 'src', 'styles', 'cyberpunk.css');

let errors = 0;

// Check CSS file exists
if (!fs.existsSync(CSS_FILE)) {
  console.error('  MISSING: src/styles/cyberpunk.css');
  process.exit(1);
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
    console.error(`  MISSING CSS variable: ${varName}`);
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
    console.error(`  MISSING Starlight override: ${override}`);
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
    console.error(`  MISSING component class: ${className}`);
    errors++;
  }
}

// Check dark theme scoping
if (!css.includes('[data-theme=\'dark\']')) {
  console.error('  MISSING dark theme scoping');
  errors++;
}

// Check scanline effect
if (!css.includes('scanline') && !css.includes('repeating-linear-gradient')) {
  console.error('  MISSING scanline effect');
  errors++;
}

// Check no hardcoded light backgrounds in dark scope
const lightBgPattern = /\[data-theme='dark'\][^}]*background:\s*(#fff|#ffffff|white)/gi;
if (lightBgPattern.test(css)) {
  console.error('  WARNING: Light background found in dark theme scope');
  errors++;
}

if (errors > 0) {
  console.error(`  ${errors} theme error(s) found`);
  process.exit(1);
}

console.log(`  ${requiredVars.length} CSS variables OK`);
console.log(`  ${requiredOverrides.length} Starlight overrides OK`);
console.log(`  ${requiredClasses.length} component classes OK`);
console.log(`  Dark theme scoping OK`);
console.log(`  Scanline effect OK`);
