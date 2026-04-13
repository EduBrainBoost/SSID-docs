/**
 * Content Tests
 * Verify that all MDX content files have valid frontmatter and structure.
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

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
  // Handle both LF and CRLF line endings
  const normalized = content.replace(/\r\n/g, '\n');
  const match = normalized.match(/^---\n([\s\S]*?)\n---/);
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

export function run() {
  let errors = 0;
  let fileCount = 0;
  const messages = [];

  const mdxFiles = findMdxFiles(DOCS_DIR);

  for (const file of mdxFiles) {
    const relPath = path.relative(ROOT, file);
    const content = fs.readFileSync(file, 'utf-8');
    fileCount++;

    // Check frontmatter exists
    const fm = parseFrontmatter(content);
    if (!fm) {
      messages.push(`  MISSING frontmatter: ${relPath}`);
      errors++;
      continue;
    }

    // Check required frontmatter fields
    if (!fm.title) {
      messages.push(`  MISSING title in frontmatter: ${relPath}`);
      errors++;
    }

    if (!fm.description) {
      messages.push(`  MISSING description in frontmatter: ${relPath}`);
      errors++;
    }

    // Check content is non-empty (beyond frontmatter)
    const normalizedContent = content.replace(/\r\n/g, '\n');
    const body = normalizedContent.replace(/^---\n[\s\S]*?\n---\n*/, '').trim();
    if (body.length < 50) {
      messages.push(`  EMPTY/SHORT content: ${relPath} (${body.length} chars)`);
      errors++;
    }

    // Check no secrets patterns
    const secretPatterns = [
      /sk_live_/i,
      /PRIVATE[._]KEY\s*[:=]\s*0x[0-9a-f]{32,}/i,  // Only match actual hex-encoded keys (32+ chars)
      /password\s*=\s*["'][^"']+["']/i,
      /api_key\s*=\s*["'][^"']+["']/i,
    ];

    for (const pattern of secretPatterns) {
      if (pattern.test(content)) {
        messages.push(`  POTENTIAL SECRET in: ${relPath}`);
        errors++;
      }
    }
  }

  if (errors > 0) {
    messages.push(`  ${errors} content error(s) found`);
    throw new Error(messages.join('\n'));
  }

  return [
    `  ${fileCount} content files validated`,
    '  All frontmatter valid',
    '  No secrets detected',
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
