/**
 * AI Infrastructure Catalogs Tests
 * Covers structure, content, cross-references, locale consistency, image
 * dimensions, and (when available) build output for the 100 AI business
 * models + 100 AI skills catalogs module.
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = path.resolve(import.meta.dirname, '..');
const rp = (p) => path.join(ROOT, p);
const exists = (p) => fs.existsSync(rp(p));
const readJson = (p) => JSON.parse(fs.readFileSync(rp(p), 'utf-8'));
const readText = (p) => fs.readFileSync(rp(p), 'utf-8');

// Reads width/height from a PNG's IHDR chunk without decoding pixel data.
function pngDimensions(p) {
  const buf = fs.readFileSync(rp(p));
  if (buf.readUInt32BE(0) !== 0x89504e47 && buf.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') {
    throw new Error(`${p} is not a valid PNG (bad signature)`);
  }
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

export function run() {
  const errors = [];
  const messages = [];

  // --- Structure ---
  const requiredDirs = [
    'src/data/research/ai-infrastructure',
    'src/data/research/ai-infrastructure/schemas',
    'public/images/research/ai-infrastructure',
  ];
  for (const d of requiredDirs) {
    if (!exists(d)) errors.push(`Missing directory: ${d}`);
  }

  const requiredDataFiles = [
    'src/data/research/ai-infrastructure/business-models.json',
    'src/data/research/ai-infrastructure/skills.json',
    'src/data/research/ai-infrastructure/skill-model-matrix.json',
    'src/data/research/ai-infrastructure/catalog-manifest.json',
    'src/data/research/ai-infrastructure/schemas/business-model.schema.json',
    'src/data/research/ai-infrastructure/schemas/skill.schema.json',
    'src/data/research/ai-infrastructure/schemas/catalog-manifest.schema.json',
  ];
  for (const f of requiredDataFiles) {
    if (!exists(f)) errors.push(`Missing data/schema file: ${f}`);
  }

  const requiredPages = [
    'src/content/docs/research/ai-infrastructure-catalogs.md',
    'src/content/docs/research/100-ai-business-models-infrastructure-pattern.md',
    'src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md',
    'src/content/docs/de/research/ai-infrastructure-catalogs.md',
    'src/content/docs/de/research/100-ai-business-models-infrastructure-pattern.md',
    'src/content/docs/de/research/katalog-100-ki-skills-und-ki-agents.md',
  ];
  for (const p of requiredPages) {
    if (!exists(p)) errors.push(`Missing documentation page: ${p}`);
  }

  const requiredPdfs = [
    'public/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf',
    'public/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf.sha256',
    'public/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf',
    'public/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf.sha256',
  ];
  for (const p of requiredPdfs) {
    if (!exists(p)) errors.push(`Missing PDF artifact: ${p}`);
  }

  const requiredImages = [
    'public/images/research/ai-infrastructure/business-models-social-card.svg',
    'public/images/research/ai-infrastructure/business-models-social-card.png',
    'public/images/research/ai-infrastructure/skills-social-card.svg',
    'public/images/research/ai-infrastructure/skills-social-card.png',
    'public/images/research/ai-infrastructure/ai-infrastructure-stack.svg',
    'public/images/research/ai-infrastructure/ai-infrastructure-stack.png',
  ];
  for (const p of requiredImages) {
    if (!exists(p)) errors.push(`Missing image: ${p}`);
  }

  if (errors.length) {
    throw new Error(errors.join('\n'));
  }
  messages.push('  Structure: all directories, data/schema files, pages, PDFs, and images present');

  // --- Content: IDs, duplicates, empty fields ---
  const bm = readJson('src/data/research/ai-infrastructure/business-models.json');
  if (bm.models.length !== 100) errors.push(`business-models.json: expected 100, got ${bm.models.length}`);
  const bmIds = bm.models.map((m) => m.id).sort((a, b) => a - b);
  for (let i = 1; i <= 100; i++) if (!bmIds.includes(i)) errors.push(`business-models.json missing ID ${i}`);
  const bmDup = bmIds.filter((id, i, arr) => arr.indexOf(id) !== i);
  if (bmDup.length) errors.push(`business-models.json duplicate IDs: ${[...new Set(bmDup)].join(', ')}`);
  for (const m of bm.models) {
    for (const f of ['market', 'pain_point', 'ai_solution', 'monetization']) {
      if (!m[f] || !m[f].trim()) errors.push(`business model ${m.id} missing field ${f}`);
    }
  }

  const sk = readJson('src/data/research/ai-infrastructure/skills.json');
  if (sk.skills.length !== 100) errors.push(`skills.json: expected 100, got ${sk.skills.length}`);
  const skIds = sk.skills.map((s) => s.id).sort((a, b) => a - b);
  for (let i = 1; i <= 100; i++) if (!skIds.includes(i)) errors.push(`skills.json missing ID ${i}`);
  const skDup = skIds.filter((id, i, arr) => arr.indexOf(id) !== i);
  if (skDup.length) errors.push(`skills.json duplicate IDs: ${[...new Set(skDup)].join(', ')}`);
  for (const s of sk.skills) {
    if (!s.name || !s.name.trim()) errors.push(`skill ${s.id} missing name`);
    if (!s.description || !s.description.trim()) errors.push(`skill ${s.id} missing description`);
    for (const f of ['inputs', 'outputs', 'technologies', 'model_types']) {
      if (!Array.isArray(s[f]) || s[f].length === 0) errors.push(`skill ${s.id} has empty array field ${f}`);
    }
  }

  // The skills markdown must carry all 8 source columns of the canonical PDF
  // table, including "Relevante Modelltypen".
  for (const p of [
    'src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md',
    'src/content/docs/de/research/katalog-100-ki-skills-und-ki-agents.md',
  ]) {
    let rows = 0;
    for (const line of readText(p).split('\n')) {
      const m = line.match(/^\|\s*(\d{1,3})\s*\|/);
      if (!m) continue;
      rows++;
      const cells = line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
      if (cells.length !== 8) errors.push(`${p}: skill row ${m[1]} has ${cells.length} columns, expected 8`);
      else if (!cells[5]) errors.push(`${p}: skill row ${m[1]} has empty "Relevante Modelltypen"`);
    }
    if (rows !== 100) errors.push(`${p}: expected 100 skill rows, found ${rows}`);
  }

  const FORBIDDEN = ['TODO', 'TBD', 'restlicher Inhalt', 'weitere Modelle', 'weitere Skills', 'placeholder', 'truncated'];
  for (const p of requiredPages) {
    const text = readText(p);
    for (const term of FORBIDDEN) {
      if (text.includes(term)) errors.push(`Placeholder "${term}" found in ${p}`);
    }
  }

  if (errors.length) throw new Error(errors.join('\n'));
  messages.push('  Content: 100 business models + 100 skills, IDs 1-100 complete, 8-column skill rows, no duplicates, no placeholders');

  // --- References ---
  const familiesPresent = new Set(sk.skills.map((s) => s.family));
  for (const fam of ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']) {
    if (!familiesPresent.has(fam)) errors.push(`Skill family ${fam} missing`);
  }
  for (const s of sk.skills) {
    for (const ref of s.business_model_ids) {
      if (ref < 1 || ref > 100) errors.push(`Skill ${s.id} has invalid business_model_id ${ref}`);
    }
  }
  const matrix = readJson('src/data/research/ai-infrastructure/skill-model-matrix.json');
  if (matrix.links.length !== sk.skills.length) errors.push('skill-model-matrix.json link count mismatch with skills.json');

  const manifest = readJson('src/data/research/ai-infrastructure/catalog-manifest.json');
  for (const entry of manifest.catalogs) {
    if (!/^[a-f0-9]{64}$/.test(entry.sha256)) errors.push(`Manifest entry ${entry.id} has invalid sha256 format`);
  }

  if (errors.length) throw new Error(errors.join('\n'));
  messages.push('  References: skill-model matrix consistent, all business-model refs in range, manifest hashes well-formed');

  // --- Schema conformance ---
  // Minimal draft-2020-12 subset check: required keys, no unknown keys,
  // integer bounds and non-empty strings/arrays as declared by the schemas.
  const schemaDir = 'src/data/research/ai-infrastructure/schemas';
  function validate(node, schema, pathLabel) {
    if (!schema || typeof schema !== 'object') return;
    if (schema.$ref === '#/$defs/skill') return; // resolved by caller
    if (schema.type === 'object') {
      for (const key of schema.required || []) {
        if (!(key in node)) errors.push(`${pathLabel}: missing required key "${key}"`);
      }
      if (schema.additionalProperties === false) {
        for (const key of Object.keys(node)) {
          if (!schema.properties || !(key in schema.properties)) {
            errors.push(`${pathLabel}: unexpected key "${key}"`);
          }
        }
      }
      for (const [key, sub] of Object.entries(schema.properties || {})) {
        if (key in node) validate(node[key], sub, `${pathLabel}.${key}`);
      }
      return;
    }
    if (schema.type === 'array') {
      if (!Array.isArray(node)) { errors.push(`${pathLabel}: expected array`); return; }
      if (schema.minItems != null && node.length < schema.minItems) errors.push(`${pathLabel}: fewer than ${schema.minItems} items`);
      if (schema.maxItems != null && node.length > schema.maxItems) errors.push(`${pathLabel}: more than ${schema.maxItems} items`);
      if (schema.uniqueItems && new Set(node.map(String)).size !== node.length) errors.push(`${pathLabel}: items not unique`);
      node.forEach((item, i) => validate(item, schema.items, `${pathLabel}[${i}]`));
      return;
    }
    if (schema.type === 'integer') {
      if (!Number.isInteger(node)) errors.push(`${pathLabel}: expected integer, got ${JSON.stringify(node)}`);
      if (schema.minimum != null && node < schema.minimum) errors.push(`${pathLabel}: below minimum ${schema.minimum}`);
      if (schema.maximum != null && node > schema.maximum) errors.push(`${pathLabel}: above maximum ${schema.maximum}`);
      if (schema.const != null && node !== schema.const) errors.push(`${pathLabel}: expected const ${schema.const}`);
      return;
    }
    if (schema.type === 'string') {
      if (typeof node !== 'string') errors.push(`${pathLabel}: expected string`);
      else {
        if (schema.minLength != null && node.length < schema.minLength) errors.push(`${pathLabel}: shorter than ${schema.minLength}`);
        if (schema.const != null && node !== schema.const) errors.push(`${pathLabel}: expected const "${schema.const}"`);
        if (schema.enum && !schema.enum.includes(node)) errors.push(`${pathLabel}: "${node}" not in enum`);
      }
    }
  }

  const bmSchema = readJson(`${schemaDir}/business-model.schema.json`);
  validate(bm, bmSchema, 'business-models.json');

  const skSchema = readJson(`${schemaDir}/skill.schema.json`);
  const skSchemaResolved = JSON.parse(JSON.stringify(skSchema));
  skSchemaResolved.properties.skills.items = skSchema.$defs.skill;
  delete skSchemaResolved.$defs;
  validate(sk, skSchemaResolved, 'skills.json');

  const manifestSchema = readJson(`${schemaDir}/catalog-manifest.schema.json`);
  validate(manifest, manifestSchema, 'catalog-manifest.json');

  if (errors.length) throw new Error(errors.join('\n'));
  messages.push('  Schemas: business-models.json, skills.json, catalog-manifest.json conform to their JSON Schemas');

  // --- Locale ---
  const localePairs = [
    ['src/content/docs/research/ai-infrastructure-catalogs.md', 'src/content/docs/de/research/ai-infrastructure-catalogs.md'],
    ['src/content/docs/research/100-ai-business-models-infrastructure-pattern.md', 'src/content/docs/de/research/100-ai-business-models-infrastructure-pattern.md'],
    ['src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md', 'src/content/docs/de/research/katalog-100-ki-skills-und-ki-agents.md'],
  ];
  for (const [root, de] of localePairs) {
    if (readText(root) !== readText(de)) errors.push(`Root/DE mismatch: ${root} vs ${de}`);
  }
  if (errors.length) throw new Error(errors.join('\n'));
  messages.push('  Locale: root/DE routes exist, content byte-identical for all 3 pages');

  // --- Images ---
  const imageChecks = [
    ['public/images/research/ai-infrastructure/business-models-social-card.png', 1200, 630],
    ['public/images/research/ai-infrastructure/skills-social-card.png', 1200, 630],
    ['public/images/research/ai-infrastructure/ai-infrastructure-stack.png', 1600, 900],
  ];
  for (const [p, w, h] of imageChecks) {
    const dims = pngDimensions(p);
    if (dims.width !== w || dims.height !== h) {
      errors.push(`${p}: expected ${w}x${h}, got ${dims.width}x${dims.height}`);
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  messages.push('  Images: social cards 1200x630, architecture diagram 1600x900');

  // --- Build (only if dist/ exists from a prior `astro build`) ---
  const distFiles = [
    'dist/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf',
    'dist/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf',
    'dist/images/research/ai-infrastructure/business-models-social-card.png',
    'dist/images/research/ai-infrastructure/skills-social-card.png',
    'dist/images/research/ai-infrastructure/ai-infrastructure-stack.png',
  ];
  if (exists('dist')) {
    for (const p of distFiles) {
      if (!exists(p)) errors.push(`Missing dist artifact: ${p}`);
    }
    if (errors.length) throw new Error(errors.join('\n'));
    messages.push('  Build: dist/ contains all expected AI infrastructure artifacts');
  } else {
    messages.push('  Build: dist/ not present yet — skipped (run after `pnpm build`)');
  }

  return messages;
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
