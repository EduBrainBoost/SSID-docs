/**
 * Content Tests
 * Verify that all MDX content files have valid frontmatter and structure.
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const DOCS_DIR = path.join(ROOT, 'src', 'content', 'docs');

function findMdxFiles(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...findMdxFiles(full));
    } else if (entry.name.endsWith('.mdx') || entry.name.endsWith('.md')) {
      results.push(full);
    }
  }
  return results;
}

function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  const fm = {};
  const lines = match[1].split('\n');
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim();
      fm[key] = value;
    }
  }
  return fm;
}

let errors = 0;
let fileCount = 0;

const mdxFiles = findMdxFiles(DOCS_DIR);

for (const file of mdxFiles) {
  const relPath = path.relative(ROOT, file);
  const content = fs.readFileSync(file, 'utf-8');
  fileCount++;

  // Check frontmatter exists
  const fm = parseFrontmatter(content);
  if (!fm) {
    console.error(`  MISSING frontmatter: ${relPath}`);
    errors++;
    continue;
  }

  // Check required frontmatter fields
  if (!fm.title) {
    console.error(`  MISSING title in frontmatter: ${relPath}`);
    errors++;
  }

  if (!fm.description) {
    console.error(`  MISSING description in frontmatter: ${relPath}`);
    errors++;
  }

  // Check content is non-empty (beyond frontmatter)
  const body = content.replace(/^---\n[\s\S]*?\n---\n*/, '').trim();
  if (body.length < 50) {
    console.error(`  EMPTY/SHORT content: ${relPath} (${body.length} chars)`);
    errors++;
  }

  // Check no secrets patterns
  const secretPatterns = [
    /sk_live_/i,
    /PRIVATE.KEY/,
    /password\s*=\s*["'][^"']+["']/i,
    /api_key\s*=\s*["'][^"']+["']/i,
  ];

  for (const pattern of secretPatterns) {
    if (pattern.test(content)) {
      console.error(`  POTENTIAL SECRET in: ${relPath}`);
      errors++;
    }
  }
}

if (errors > 0) {
  console.error(`  ${errors} content error(s) found`);
  process.exit(1);
}

console.log(`  ${fileCount} content files validated`);
console.log(`  All frontmatter valid`);
console.log(`  No secrets detected`);
