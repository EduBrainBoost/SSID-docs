/**
 * SSID Docs - Changelog Generator
 *
 * Generates a changelog page from SSID-open-core git history.
 * SECURITY: Only reads from SSID-open-core (public).
 *
 * Usage:
 *   node tools/changelog-gen.mjs [--open-core <path>] [--limit <n>]
 */

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const DOCS_ROOT = path.resolve(import.meta.dirname, '..');
const DEFAULT_OPEN_CORE = path.resolve(DOCS_ROOT, '..', 'SSID-open-core');

function parseArgs() {
  const args = process.argv.slice(2);
  const config = {
    openCorePath: DEFAULT_OPEN_CORE,
    limit: 50,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--open-core' && args[i + 1]) {
      config.openCorePath = path.resolve(args[++i]);
    } else if (args[i] === '--limit' && args[i + 1]) {
      config.limit = parseInt(args[++i], 10);
    }
  }

  return config;
}

function getGitLog(repoPath, limit) {
  try {
    const output = execSync(
      `git log --pretty=format:"%H|%ai|%s" -n ${limit}`,
      { cwd: repoPath, encoding: 'utf-8', timeout: 30000 },
    );
    return output
      .split('\n')
      .filter(Boolean)
      .map((line) => {
        const [hash, date, ...rest] = line.split('|');
        return {
          hash: hash.trim(),
          date: date.trim().split(' ')[0], // YYYY-MM-DD
          message: rest.join('|').trim(),
        };
      });
  } catch {
    console.error(`[changelog] Failed to read git log from: ${repoPath}`);
    return [];
  }
}

function groupByDate(commits) {
  const grouped = new Map();
  for (const commit of commits) {
    if (!grouped.has(commit.date)) {
      grouped.set(commit.date, []);
    }
    grouped.get(commit.date).push(commit);
  }
  return grouped;
}

function generateMdx(commits) {
  const grouped = groupByDate(commits);
  const lines = [
    '---',
    'title: Changelog',
    'description: Recent changes to the SSID open-core repository.',
    '---',
    '',
    'import { Aside } from "@astrojs/starlight/components";',
    '',
    '<Aside type="note">',
    'This changelog is auto-generated from the SSID-open-core git history.',
    'Only public commits are shown.',
    '</Aside>',
    '',
  ];

  for (const [date, dayCommits] of grouped) {
    lines.push(`## ${date}`);
    lines.push('');
    for (const commit of dayCommits) {
      const shortHash = commit.hash.slice(0, 8);
      lines.push(`- \`${shortHash}\` ${commit.message}`);
    }
    lines.push('');
  }

  if (commits.length === 0) {
    lines.push('*No commits found in the open-core repository.*');
    lines.push('');
  }

  return lines.join('\n');
}

function main() {
  const config = parseArgs();

  console.log('[changelog] SSID Docs - Changelog Generator');
  console.log(`[changelog] Source: ${config.openCorePath}`);
  console.log(`[changelog] Limit: ${config.limit} commits`);

  if (!fs.existsSync(config.openCorePath)) {
    console.error(`[changelog] Source not found: ${config.openCorePath}`);
    process.exit(1);
  }

  const commits = getGitLog(config.openCorePath, config.limit);
  const mdx = generateMdx(commits);

  const outputPath = path.join(DOCS_ROOT, 'src', 'content', 'docs', 'changelog.mdx');
  fs.writeFileSync(outputPath, mdx, 'utf-8');
  console.log(`[changelog] Written: ${outputPath} (${commits.length} commits)`);
}

main();
