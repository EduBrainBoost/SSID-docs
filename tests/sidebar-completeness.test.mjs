/**
 * Sidebar Completeness Stress Test
 * Verifies that every content file in src/content/docs/ (except index.mdx and de/)
 * is referenced in the Starlight sidebar configuration.
 *
 * Run: node tests/sidebar-completeness.test.mjs
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(__dirname, '..');
const CONTENT_DIR = join(ROOT, 'src', 'content', 'docs');
const CONFIG_FILE = join(ROOT, 'astro.config.mjs');

function collectFiles(dir, base) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = relative(base, full).replace(/\\/g, '/');
    if (statSync(full).isDirectory()) {
      results.push(...collectFiles(full, base));
    } else if (entry.endsWith('.mdx') || entry.endsWith('.md')) {
      results.push(rel);
    }
  }
  return results;
}

function fileToSlug(filePath) {
  return filePath
    .replace(/\.(mdx|md)$/, '')
    .replace(/\/index$/, '');
}

function extractSlugs(configContent) {
  const slugRegex = /slug:\s*['"]([^'"]+)['"]/g;
  const slugs = [];
  let match;
  while ((match = slugRegex.exec(configContent)) !== null) {
    slugs.push(match[1]);
  }
  return slugs;
}

export function run() {
  const output = [];
  let passed = 0;
  let errors = 0;

  const allFiles = collectFiles(CONTENT_DIR, CONTENT_DIR);
  const configContent = readFileSync(CONFIG_FILE, 'utf-8');
  const sidebarSlugs = new Set(extractSlugs(configContent));

  const navigableFiles = allFiles.filter(f => {
    if (f === 'index.mdx') return false;
    if (f.startsWith('de/')) return false;
    return true;
  });

  // Test 1: Every navigable file has a sidebar entry
  const orphans = [];
  for (const file of navigableFiles) {
    const slug = fileToSlug(file);
    if (!sidebarSlugs.has(slug)) {
      orphans.push({ file, slug });
    }
  }

  if (orphans.length === 0) {
    output.push(`  All ${navigableFiles.length} content files are in sidebar`);
    passed++;
  } else {
    output.push(`  ${orphans.length} orphan files not in sidebar`);
    errors++;
  }

  // Test 2: Every sidebar slug points to an existing file
  const fileSlugs = new Set(navigableFiles.map(fileToSlug));
  const deadLinks = [];
  for (const slug of sidebarSlugs) {
    if (!fileSlugs.has(slug)) {
      deadLinks.push(slug);
    }
  }

  if (deadLinks.length === 0) {
    output.push(`  All ${sidebarSlugs.size} sidebar slugs point to existing files`);
    passed++;
  } else {
    output.push(`  ${deadLinks.length} dead sidebar links`);
    errors++;
  }

  // Test 3: No duplicate slugs in sidebar
  const slugCounts = {};
  const slugDupRegex = /slug:\s*['"]([^'"]+)['"]/g;
  let m;
  while ((m = slugDupRegex.exec(configContent)) !== null) {
    slugCounts[m[1]] = (slugCounts[m[1]] || 0) + 1;
  }
  const duplicates = Object.entries(slugCounts).filter(([, c]) => c > 1);

  if (duplicates.length === 0) {
    output.push(`  No duplicate sidebar slugs`);
    passed++;
  } else {
    output.push(`  ${duplicates.length} duplicate slugs`);
    errors++;
  }

  // Test 4: Sidebar coverage ratio
  const coverageRatio = sidebarSlugs.size / navigableFiles.length;
  const coveragePercent = Math.round(coverageRatio * 100);

  if (coveragePercent >= 90) {
    output.push(`  Sidebar coverage ${coveragePercent}% (${sidebarSlugs.size}/${navigableFiles.length})`);
    passed++;
  } else {
    output.push(`  Sidebar coverage only ${coveragePercent}%`);
    errors++;
  }

  // Test 5: Config braces balanced
  const opens = (configContent.match(/\{/g) || []).length;
  const closes = (configContent.match(/\}/g) || []).length;
  if (opens === closes) {
    output.push(`  Config braces balanced (${opens} pairs)`);
    passed++;
  } else {
    output.push(`  Unbalanced braces (${opens} open, ${closes} close)`);
    errors++;
  }

  if (errors > 0) {
    throw new Error(`${errors} sidebar completeness check(s) failed\n` + output.join('\n'));
  }

  return output;
}

const isDirectRun =
  process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;

if (isDirectRun) {
  try {
    console.log('=== Sidebar Completeness Test ===\n');
    for (const line of run()) {
      console.log(line);
    }
    console.log('\nAll sidebar completeness tests passed!');
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
  }
}
