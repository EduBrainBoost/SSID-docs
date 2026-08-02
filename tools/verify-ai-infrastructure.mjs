#!/usr/bin/env node
// Verifies the full AI infrastructure catalogs module: content counts, ID
// integrity, cross-references, PDF hashes, images, navigation, and manifest
// consistency. Exits non-zero on any failure.

import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let failures = 0;

function ok(msg) {
  console.log(`VERIFIED: ${msg}`);
}
function bad(msg) {
  console.error(`BLOCKED: ${msg}`);
  failures++;
}
function rp(p) {
  return path.join(ROOT, p);
}
function exists(p) {
  return existsSync(rp(p));
}
function readJson(p) {
  return JSON.parse(readFileSync(rp(p), 'utf-8'));
}
function readText(p) {
  return readFileSync(rp(p), 'utf-8');
}
function sha256(p) {
  return createHash('sha256').update(readFileSync(rp(p))).digest('hex');
}

const FORBIDDEN = [
  '\\.\\.\\.', '\\bTODO\\b', '\\bTBD\\b', 'restlicher Inhalt', 'weitere Modelle',
  'weitere Skills', 'analog fortsetzen', 'gekürzt', 'truncated', 'placeholder',
  'HIER EINFÜGEN', 'QUELLE FEHLT',
];

function checkPlaceholders(p) {
  const text = readText(p);
  for (const pattern of FORBIDDEN) {
    const re = new RegExp(pattern);
    if (re.test(text)) bad(`Placeholder pattern "${pattern}" found in ${p}`);
  }
}

// ---------- 1. Structured data ----------

const dataDir = 'src/data/research/ai-infrastructure';
const requiredData = ['business-models.json', 'skills.json', 'skill-model-matrix.json', 'catalog-manifest.json'];
for (const f of requiredData) {
  if (!exists(`${dataDir}/${f}`)) bad(`Missing data file: ${dataDir}/${f}`);
}
const requiredSchemas = ['business-model.schema.json', 'skill.schema.json', 'catalog-manifest.schema.json'];
for (const f of requiredSchemas) {
  if (!exists(`${dataDir}/schemas/${f}`)) bad(`Missing schema: ${dataDir}/schemas/${f}`);
}

if (failures === 0 || exists(`${dataDir}/business-models.json`)) {
  const bm = readJson(`${dataDir}/business-models.json`);
  if (bm.models.length !== 100) bad(`business-models.json: expected 100 models, got ${bm.models.length}`);
  const bmIds = bm.models.map((m) => m.id).sort((a, b) => a - b);
  const missingBm = [];
  for (let i = 1; i <= 100; i++) if (!bmIds.includes(i)) missingBm.push(i);
  if (missingBm.length) bad(`business-models.json missing IDs: ${missingBm.join(', ')}`);
  const dupBm = bmIds.filter((id, i, arr) => arr.indexOf(id) !== i);
  if (dupBm.length) bad(`business-models.json duplicate IDs: ${[...new Set(dupBm)].join(', ')}`);
  if (bm.count !== bm.models.length) bad(`business-models.json count field (${bm.count}) != actual length (${bm.models.length})`);
  for (const m of bm.models) {
    for (const field of ['market', 'pain_point', 'ai_solution', 'monetization', 'market_comment']) {
      if (!m[field] || !m[field].trim()) bad(`business model ${m.id} has empty field "${field}"`);
    }
  }
  if (!failures) ok(`business-models.json — 100 models, IDs 1-100 complete, no duplicates, no empty required fields.`);
}

let skillsDoc = null;
if (exists(`${dataDir}/skills.json`)) {
  skillsDoc = readJson(`${dataDir}/skills.json`);
  if (skillsDoc.skills.length !== 100) bad(`skills.json: expected 100 skills, got ${skillsDoc.skills.length}`);
  const skIds = skillsDoc.skills.map((s) => s.id).sort((a, b) => a - b);
  const missingSk = [];
  for (let i = 1; i <= 100; i++) if (!skIds.includes(i)) missingSk.push(i);
  if (missingSk.length) bad(`skills.json missing IDs: ${missingSk.join(', ')}`);
  const dupSk = skIds.filter((id, i, arr) => arr.indexOf(id) !== i);
  if (dupSk.length) bad(`skills.json duplicate IDs: ${[...new Set(dupSk)].join(', ')}`);

  const famPresent = new Set(skillsDoc.skills.map((s) => s.family));
  for (const fam of ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']) {
    if (!famPresent.has(fam)) bad(`skills.json: family ${fam} has no members`);
  }
  let badRefs = 0;
  for (const s of skillsDoc.skills) {
    for (const ref of s.business_model_ids) {
      if (ref < 1 || ref > 100) {
        bad(`skill ${s.id} references invalid business_model_id ${ref}`);
        badRefs++;
      }
    }
    if (!s.name || !s.name.trim()) bad(`skill ${s.id} has empty name`);
    for (const field of ['inputs', 'outputs', 'technologies', 'model_types']) {
      if (!Array.isArray(s[field]) || s[field].length === 0) bad(`skill ${s.id} has empty array field "${field}"`);
    }
  }
  if (!failures) ok(`skills.json — 100 skills, IDs 1-100 complete, families A-J present, all business-model references valid, inputs/outputs/technologies/model_types populated.`);
}

if (exists(`${dataDir}/skill-model-matrix.json`) && skillsDoc) {
  const matrix = readJson(`${dataDir}/skill-model-matrix.json`);
  if (matrix.links.length !== skillsDoc.skills.length) {
    bad(`skill-model-matrix.json: link count (${matrix.links.length}) != skill count (${skillsDoc.skills.length})`);
  } else {
    ok(`skill-model-matrix.json — consistent with skills.json (${matrix.links.length} links).`);
  }
}

// ---------- 2. PDF artifacts ----------

const businessPdf = 'public/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf';
const businessShaFile = `${businessPdf}.sha256`;
const skillsPdf = 'public/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf';
const skillsShaFile = `${skillsPdf}.sha256`;
const EXPECTED_SKILLS_HASH = '5d534f595b960a8e37434cee889ab1f60b67be3b4ff272d488afbbb1a294d89d';

for (const f of [businessPdf, businessShaFile, skillsPdf, skillsShaFile]) {
  if (!exists(f)) bad(`Missing PDF artifact: ${f}`);
}
if (exists(skillsPdf)) {
  const hash = sha256(skillsPdf);
  if (hash !== EXPECTED_SKILLS_HASH) bad(`Skills PDF hash mismatch: expected ${EXPECTED_SKILLS_HASH}, got ${hash}`);
  else ok(`Skills PDF hash exact match: ${hash}`);
}
if (exists(businessPdf) && exists(`${dataDir}/catalog-manifest.json`)) {
  const manifest = readJson(`${dataDir}/catalog-manifest.json`);
  const entry = manifest.catalogs.find((c) => c.id === 'business-models');
  const actualHash = sha256(businessPdf);
  if (!entry) bad('catalog-manifest.json missing business-models entry');
  else if (entry.sha256 !== actualHash) bad(`Business PDF hash mismatch with manifest: manifest=${entry.sha256}, actual=${actualHash}`);
  else ok(`Business PDF hash matches manifest: ${actualHash}`);
}

// ---------- 3. Documentation pages ----------

const pages = [
  'src/content/docs/research/ai-infrastructure-catalogs.md',
  'src/content/docs/research/100-ai-business-models-infrastructure-pattern.md',
  'src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md',
  'src/content/docs/de/research/ai-infrastructure-catalogs.md',
  'src/content/docs/de/research/100-ai-business-models-infrastructure-pattern.md',
  'src/content/docs/de/research/katalog-100-ki-skills-und-ki-agents.md',
];
for (const p of pages) {
  if (!exists(p)) bad(`Missing documentation page: ${p}`);
  else checkPlaceholders(p);
}
if (!failures) ok(`All 6 root/DE documentation pages present, no placeholders detected.`);

const localePairs = [
  ['src/content/docs/research/ai-infrastructure-catalogs.md', 'src/content/docs/de/research/ai-infrastructure-catalogs.md'],
  ['src/content/docs/research/100-ai-business-models-infrastructure-pattern.md', 'src/content/docs/de/research/100-ai-business-models-infrastructure-pattern.md'],
  ['src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md', 'src/content/docs/de/research/katalog-100-ki-skills-und-ki-agents.md'],
];
for (const [root, de] of localePairs) {
  if (exists(root) && exists(de)) {
    if (readText(root) !== readText(de)) bad(`Root/DE content mismatch: ${root} vs ${de}`);
  }
}
if (!failures) ok(`Root/DE content byte-identical for all 3 page pairs.`);

// Model number coverage in business-models.md
if (exists('src/content/docs/research/100-ai-business-models-infrastructure-pattern.md')) {
  const text = readText('src/content/docs/research/100-ai-business-models-infrastructure-pattern.md');
  const missing = [];
  for (let i = 1; i <= 100; i++) {
    if (!new RegExp(`^\\|\\s*${i}\\s*\\|`, 'm').test(text)) missing.push(i);
  }
  if (missing.length) bad(`Business model markdown missing rows: ${missing.join(', ')}`);
}

// Skill number coverage in skills.md
if (exists('src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md')) {
  const text = readText('src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md');
  const missing = [];
  for (let i = 1; i <= 100; i++) {
    if (!new RegExp(`^\\| ${i} \\|`, 'm').test(text)) missing.push(i);
  }
  if (missing.length) bad(`Skills markdown missing rows: ${missing.join(', ')}`);
  else ok(`Skills markdown contains all 100 skill rows.`);

  // Every skill row must carry all 8 source columns, including the
  // "Relevante Modelltypen" column transcribed from the canonical PDF.
  const shortRows = [];
  const emptyModelTypes = [];
  for (const line of text.split('\n')) {
    const m = line.match(/^\|\s*(\d{1,3})\s*\|/);
    if (!m) continue;
    const cells = line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
    if (cells.length !== 8) shortRows.push(`${m[1]}(${cells.length})`);
    else if (!cells[5]) emptyModelTypes.push(m[1]);
  }
  if (shortRows.length) bad(`Skills markdown rows without 8 columns: ${shortRows.join(', ')}`);
  else if (emptyModelTypes.length) bad(`Skills markdown rows with empty "Relevante Modelltypen": ${emptyModelTypes.join(', ')}`);
  else ok(`Skills markdown rows all carry 8 source columns incl. "Relevante Modelltypen".`);
}

// ---------- 4. Images ----------

const imgDir = 'public/images/research/ai-infrastructure';
const expectedImages = {
  'business-models-social-card.svg': null,
  'business-models-social-card.png': { w: 1200, h: 630 },
  'skills-social-card.svg': null,
  'skills-social-card.png': { w: 1200, h: 630 },
  'ai-infrastructure-stack.svg': null,
  'ai-infrastructure-stack.png': { w: 1600, h: 900 },
};

for (const [file, dims] of Object.entries(expectedImages)) {
  const p = `${imgDir}/${file}`;
  if (!exists(p)) {
    bad(`Missing image: ${p}`);
    continue;
  }
  if (dims) {
    const meta = await sharp(rp(p)).metadata();
    if (meta.width !== dims.w || meta.height !== dims.h) {
      bad(`${file}: expected ${dims.w}x${dims.h}, got ${meta.width}x${meta.height}`);
    } else {
      ok(`${file} — ${meta.width}x${meta.height}`);
    }
  }
}

// ---------- 5. Navigation ----------

const astroConfig = readText('astro.config.mjs');
const requiredSlugs = [
  'research/ai-infrastructure-catalogs',
  'research/100-ai-business-models-infrastructure-pattern',
  'research/katalog-100-ki-skills-und-ki-agents',
];
for (const slug of requiredSlugs) {
  if (!astroConfig.includes(`slug: '${slug}'`)) bad(`Sidebar missing entry for slug: ${slug}`);
}
if (!failures) ok(`Sidebar contains all 3 new Research entries.`);

// ---------- 6. Public URL sanity in overview page ----------

if (exists('src/content/docs/research/ai-infrastructure-catalogs.md')) {
  const overview = readText('src/content/docs/research/ai-infrastructure-catalogs.md');
  const requiredUrls = [
    '/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf',
    '/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf',
    '/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json',
    '/research/100-ai-business-models-infrastructure-pattern/',
    '/research/katalog-100-ki-skills-und-ki-agents/',
  ];
  for (const url of requiredUrls) {
    if (!overview.includes(url)) bad(`Overview page missing expected URL: ${url}`);
  }
  if (!failures) ok(`Overview page contains all required public URLs.`);
}

// ---------- Result ----------

if (failures > 0) {
  console.error(`FAIL: ${failures} check(s) failed.`);
  process.exit(1);
} else {
  console.log('PASS: AI infrastructure catalogs module verification complete.');
  process.exit(0);
}
