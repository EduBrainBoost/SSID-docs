#!/usr/bin/env node
// Parses the canonical AI infrastructure documentation pages and regenerates
// the structured JSON catalogs, matrix, and manifest.
//
// CANONICAL SOURCES:
// 1. src/content/docs/research/100-ai-business-models-infrastructure-pattern.md
//    → parses legacy business model fields (id 1-100, market, pain_point, etc.)
//
// 2. src/data/research/ai-infrastructure/enrichment-atlas.json (REQUIRED)
//    → contains Phase-2.1 hardening dimensions for all 100 models
//    → NEVER optional; generation MUST fail if missing or incomplete
//    → provides: model_id, source_number, primary_cluster, region,
//      economics_breakdown, risk, ssid_relevance, infrastructure_pattern,
//      market_sizing, cold_start_strategy, competitive_landscape,
//      data_and_integration_dependencies, regulatory_constraints,
//      ai_vs_infrastructure_moat, market_maturity, evidence_status, validation_atlas
//
// 3. src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md
//    → parses 100 skills and their business model mappings
//
// OUTPUT CONTRACT:
// Each business model in output MUST contain all 27 fields:
// - 8 legacy fields (id, market, pain_point, ai_solution, monetization, market_comment, maturity, status)
// - 10 Phase-2.1 hardening dimensions (infrastructure_pattern, market_sizing, etc.)
// - 9 enrichment metadata fields (model_id, source_number, primary_cluster, etc.)
//
// FAILURE CONDITIONS (all are hard-fail):
// - enrichment-atlas.json missing
// - enrichment-atlas.json has < 100 records
// - Any model missing from enrichment-atlas
// - Any enrichment record with duplicate ID
// - Any required hardening dimension null/undefined
// - Output model count ≠ 100
// - Output model IDs ≠ 1–100 (consecutive)
// - Schema validation failure

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function fail(message) {
  console.error(`BLOCKED: ${message}`);
  process.exit(1);
}

function validateEnrichmentIntegrity(model, enrichment, modelId) {
  const dimensions = [
    'infrastructure_pattern', 'market_sizing', 'cold_start_strategy',
    'competitive_landscape', 'data_and_integration_dependencies',
    'regulatory_constraints', 'ai_vs_infrastructure_moat', 'market_maturity',
    'evidence_status', 'validation_atlas'
  ];

  for (const dim of dimensions) {
    if (!(dim in enrichment)) {
      fail(`Enrichment for model ${modelId} missing required field: ${dim}`);
    }
    if (enrichment[dim] === null || enrichment[dim] === undefined) {
      fail(`Enrichment for model ${modelId} has null/undefined ${dim}`);
    }
    if (typeof enrichment[dim] === 'object' && Object.keys(enrichment[dim]).length === 0) {
      fail(`Enrichment for model ${modelId} has empty object for ${dim}`);
    }
    if (!(dim in model)) {
      fail(`Merged model ${modelId} missing field: ${dim}`);
    }
  }
}

function readText(relPath) {
  const p = path.join(ROOT, relPath);
  if (!existsSync(p)) fail(`Missing required file: ${relPath}`);
  return readFileSync(p, 'utf-8');
}

function sha256(relPath) {
  const p = path.join(ROOT, relPath);
  if (!existsSync(p)) fail(`Missing required artifact: ${relPath}`);
  return createHash('sha256').update(readFileSync(p)).digest('hex');
}

function splitRow(line) {
  // Splits a markdown table row "| a | b | c |" into ["a","b","c"], trimmed.
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells = [];
  let cur = '';
  let escaped = false;
  for (const ch of trimmed) {
    if (escaped) {
      cur += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      escaped = true;
      continue;
    }
    if (ch === '|') {
      cells.push(cur.trim());
      cur = '';
      continue;
    }
    cur += ch;
  }
  cells.push(cur.trim());
  return cells;
}

// ---------- Business models ----------

function parseBusinessModels() {
  const md = readText('src/content/docs/research/100-ai-business-models-infrastructure-pattern.md');
  const lines = md.split('\n');
  const models = [];
  for (const line of lines) {
    if (!/^\|\s*\d+\s*\|/.test(line)) continue;
    const cells = splitRow(line);
    if (cells.length < 6) continue;
    const id = Number(cells[0]);
    if (!Number.isInteger(id) || id < 1 || id > 100) continue;
    const [, market, painPoint, aiSolution, monetization, marketComment] = cells;

    const maturityMatch = marketComment.match(/Reife:\s*([^.]+)\./);
    const status = /^VERIFIED:/.test(marketComment)
      ? 'VERIFIED'
      : /^Proxy:/.test(marketComment)
        ? 'INFERENCE'
        : /unspezifiziert/i.test(marketComment)
          ? 'UNKNOWN'
          : 'INFERENCE';

    models.push({
      id,
      market: market,
      pain_point: painPoint,
      ai_solution: aiSolution,
      monetization: monetization,
      market_comment: marketComment,
      maturity: maturityMatch ? maturityMatch[1].trim() : 'UNKNOWN',
      status,
    });
  }
  return models;
}

function loadEnrichmentAtlas() {
  const raw = readText('src/data/research/ai-infrastructure/enrichment-atlas.json');
  let atlas;
  try {
    atlas = JSON.parse(raw);
  } catch (e) {
    fail(`Failed to parse enrichment-atlas.json: ${e.message}`);
  }
  if (!atlas.enrichments || !Array.isArray(atlas.enrichments)) {
    fail('Enrichment atlas must have enrichments array.');
  }
  const byId = {};
  for (const rec of atlas.enrichments) {
    if (!Number.isInteger(rec.id) || rec.id < 1 || rec.id > 100) {
      fail(`Enrichment record has invalid id: ${rec.id}`);
    }
    if (byId[rec.id]) fail(`Enrichment has duplicate id: ${rec.id}`);
    byId[rec.id] = rec;
  }
  return byId;
}

function mergeWithEnrichment(legacyModels, enrichmentByID) {
  const merged = [];
  const seenIds = new Set();

  // Validate enrichment atlas has exactly 100 records covering IDs 1-100
  if (Object.keys(enrichmentByID).length !== 100) {
    fail(`Enrichment atlas must have exactly 100 records, found ${Object.keys(enrichmentByID).length}`);
  }
  for (let i = 1; i <= 100; i++) {
    if (!enrichmentByID[i]) {
      fail(`Enrichment atlas missing required model ID: ${i}`);
    }
  }

  for (const model of legacyModels) {
    const enrichment = enrichmentByID[model.id];
    if (!enrichment) fail(`No enrichment found for model ID ${model.id}`);

    const fullModel = {
      ...model,
      model_id: enrichment.model_id,
      source_number: enrichment.source_number,
      primary_cluster: enrichment.primary_cluster,
      primary_cluster_label: enrichment.primary_cluster_label,
      region: enrichment.region,
      source_reference: enrichment.source_reference,
      economics_breakdown: enrichment.economics_breakdown,
      risk: enrichment.risk,
      ssid_relevance: enrichment.ssid_relevance,
      infrastructure_pattern: enrichment.infrastructure_pattern,
      market_sizing: enrichment.market_sizing,
      cold_start_strategy: enrichment.cold_start_strategy,
      competitive_landscape: enrichment.competitive_landscape,
      data_and_integration_dependencies: enrichment.data_and_integration_dependencies,
      regulatory_constraints: enrichment.regulatory_constraints,
      ai_vs_infrastructure_moat: enrichment.ai_vs_infrastructure_moat,
      market_maturity: enrichment.market_maturity,
      evidence_status: enrichment.evidence_status,
      validation_atlas: enrichment.validation_atlas,
    };

    validateEnrichmentIntegrity(fullModel, enrichment, model.id);

    merged.push(fullModel);
    seenIds.add(model.id);
  }

  // Verify all enrichment records were used
  for (const id of Object.keys(enrichmentByID)) {
    const numId = Number(id);
    if (!seenIds.has(numId)) {
      fail(`Enrichment atlas has model ID not in legacy models: ${id}`);
    }
  }

  return merged;
}

// ---------- Skills ----------

const FAMILIES = {
  A: 'Intake & Dokumentenverarbeitung',
  B: 'Verständnis & Klassifikation',
  C: 'Matching & Routing',
  D: 'Prognose & Prognostik',
  E: 'Optimierung & Orchestrierung',
  F: 'Abrechnung, Settlement & Metering',
  G: 'Compliance, Audit & Reporting',
  H: 'Human-in-the-loop & Quality Control',
  I: 'Agentic Orchestration & Tool-Use',
  J: 'Domain-specific Skills',
};

function splitInputsOutputs(cell) {
  // Source column format: "In: <inputs>. Out: <outputs>."
  const m = cell.match(/^In:\s*(.*?)\.?\s*Out:\s*(.*)$/s);
  if (!m) return { inputs: [], outputs: [] };
  const listify = (s) =>
    s
      .replace(/\.\s*$/, '')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);
  return { inputs: listify(m[1]), outputs: listify(m[2]) };
}

function parseSkills() {
  const md = readText('src/content/docs/research/katalog-100-ki-skills-und-ki-agents.md');
  const lines = md.split('\n');
  const skills = [];
  let currentFamily = null;

  for (const line of lines) {
    if (!line.trim().startsWith('|')) continue;
    const cells = splitRow(line);

    // Family header row: | **A** | **Family Name** | | | | | |
    const familyMatch = cells[0] && cells[0].match(/^\*\*([A-J])\*\*$/);
    if (familyMatch) {
      currentFamily = familyMatch[1];
      continue;
    }

    if (!/^\d{1,3}$/.test(cells[0])) continue;
    const id = Number(cells[0]);
    if (id < 1 || id > 100) continue;
    if (cells.length < 8) fail(`Skill row ${id} has ${cells.length} columns, expected 8.`);

    const [, name, description, inputsOutputs, technologiesRaw, modelTypesRaw, modelRefsRaw, hintRaw] = cells;
    const businessModelIds = (modelRefsRaw.match(/\d+/g) || []).map(Number);
    const technologies = technologiesRaw.split(',').map((s) => s.trim()).filter(Boolean);
    const modelTypes = modelTypesRaw.split(',').map((s) => s.trim()).filter(Boolean);
    const hint = hintRaw === '—' ? '' : hintRaw;
    const { inputs, outputs } = splitInputsOutputs(inputsOutputs);

    skills.push({
      id,
      family: currentFamily,
      name,
      description,
      inputs,
      outputs,
      inputs_outputs: inputsOutputs,
      technologies,
      model_types: modelTypes,
      business_model_ids: businessModelIds,
      implementation_note: hint,
    });
  }
  return skills;
}

// ---------- Build ----------

function validateOutputModels(models) {
  if (models.length !== 100) {
    fail(`Output must contain exactly 100 models, got ${models.length}`);
  }

  const requiredFields = [
    // Legacy fields (8)
    'id', 'market', 'pain_point', 'ai_solution', 'monetization', 'market_comment', 'maturity', 'status',
    // Enrichment metadata (9)
    'model_id', 'source_number', 'primary_cluster', 'primary_cluster_label', 'region', 'source_reference', 'economics_breakdown', 'risk', 'ssid_relevance',
    // Phase-2.1 hardening dimensions (10)
    'infrastructure_pattern', 'market_sizing', 'cold_start_strategy', 'competitive_landscape',
    'data_and_integration_dependencies', 'regulatory_constraints', 'ai_vs_infrastructure_moat',
    'market_maturity', 'evidence_status', 'validation_atlas'
  ];

  const modelIds = new Set();
  for (const model of models) {
    for (const field of requiredFields) {
      if (!(field in model)) {
        fail(`Model ${model.id} missing required field: ${field}`);
      }
      if (model[field] === null || model[field] === undefined) {
        fail(`Model ${model.id} has null/undefined ${field}`);
      }
    }
    if (model.id < 1 || model.id > 100 || !Number.isInteger(model.id)) {
      fail(`Model has invalid id: ${model.id}`);
    }
    if (modelIds.has(model.id)) {
      fail(`Duplicate model ID: ${model.id}`);
    }
    modelIds.add(model.id);
  }

  // Verify IDs are exactly 1-100
  for (let i = 1; i <= 100; i++) {
    if (!modelIds.has(i)) {
      fail(`Missing model ID: ${i}`);
    }
  }
}

function build() {
  const legacyModels = parseBusinessModels();
  if (legacyModels.length !== 100) fail(`Expected 100 business models, parsed ${legacyModels.length}.`);
  const modelIds = legacyModels.map((m) => m.id).sort((a, b) => a - b);
  for (let i = 0; i < 100; i++) {
    if (modelIds[i] !== i + 1) fail(`Business model ID mismatch at position ${i}: expected ${i + 1}, got ${modelIds[i]}.`);
  }

  const enrichmentByID = loadEnrichmentAtlas();
  const models = mergeWithEnrichment(legacyModels, enrichmentByID);

  // Validate output before writing
  validateOutputModels(models);

  const skills = parseSkills();
  if (skills.length !== 100) fail(`Expected 100 skills, parsed ${skills.length}.`);
  const skillIds = skills.map((s) => s.id).sort((a, b) => a - b);
  for (let i = 0; i < 100; i++) {
    if (skillIds[i] !== i + 1) fail(`Skill ID mismatch at position ${i}: expected ${i + 1}, got ${skillIds[i]}.`);
  }
  for (const s of skills) {
    if (!s.family || !FAMILIES[s.family]) fail(`Skill ${s.id} has invalid or missing family "${s.family}".`);
    if (!s.name) fail(`Skill ${s.id} has an empty name.`);
    if (!s.technologies.length) fail(`Skill ${s.id} has no technologies.`);
    if (!s.model_types.length) fail(`Skill ${s.id} has no model types.`);
    if (!s.inputs.length) fail(`Skill ${s.id} has no parsed inputs.`);
    if (!s.outputs.length) fail(`Skill ${s.id} has no parsed outputs.`);
    for (const ref of s.business_model_ids) {
      if (ref < 1 || ref > 100) fail(`Skill ${s.id} references out-of-range business model ID ${ref}.`);
    }
  }
  const familiesPresent = new Set(skills.map((s) => s.family));
  for (const fam of Object.keys(FAMILIES)) {
    if (!familiesPresent.has(fam)) fail(`Skill family ${fam} has no members.`);
  }

  // business-models.json
  const businessModelsDoc = {
    catalog_id: 'ai-infrastructure-business-models-100',
    title: 'Hundert KI-gestützte Business-Modelle nach dem Infrastrukturmuster',
    language: 'de',
    count: models.length,
    models,
  };

  // skills.json
  const skillsDoc = {
    catalog_id: 'ai-agent-skills-100',
    title: 'Katalog von hundert KI-Skills für KI-Skills und KI-Agents',
    language: 'de',
    count: skills.length,
    families: Object.entries(FAMILIES).map(([id, name]) => ({ id, name })),
    skills,
  };

  // skill-model-matrix.json
  const links = skills.map((s) => ({ skill_id: s.id, business_model_ids: s.business_model_ids }));
  const skillsByBusinessModel = {};
  for (const s of skills) {
    for (const modelId of s.business_model_ids) {
      const key = String(modelId);
      if (!skillsByBusinessModel[key]) skillsByBusinessModel[key] = [];
      skillsByBusinessModel[key].push(s.id);
    }
  }
  const businessModelsBySkillFamily = {};
  for (const s of skills) {
    if (!businessModelsBySkillFamily[s.family]) businessModelsBySkillFamily[s.family] = new Set();
    for (const modelId of s.business_model_ids) businessModelsBySkillFamily[s.family].add(modelId);
  }
  const businessModelsBySkillFamilyOut = Object.fromEntries(
    Object.entries(businessModelsBySkillFamily).map(([k, v]) => [k, [...v].sort((a, b) => a - b)])
  );

  const matrixDoc = {
    business_model_count: models.length,
    skill_count: skills.length,
    links,
    skills_by_business_model: skillsByBusinessModel,
    business_models_by_skill_family: businessModelsBySkillFamilyOut,
  };

  // PDF hashes
  const businessPdfHash = sha256('public/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf');
  const skillsPdfHash = sha256('public/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf');
  const expectedSkillsHash = '5d534f595b960a8e37434cee889ab1f60b67be3b4ff272d488afbbb1a294d89d';
  if (skillsPdfHash !== expectedSkillsHash) {
    fail(`Skills PDF hash mismatch: expected ${expectedSkillsHash}, got ${skillsPdfHash}.`);
  }

  const manifestDoc = {
    module: 'ai-infrastructure-catalogs',
    version: '1.0.0',
    catalogs: [
      {
        id: 'business-models',
        count: models.length,
        page: '/research/100-ai-business-models-infrastructure-pattern/',
        page_de: '/de/research/100-ai-business-models-infrastructure-pattern/',
        pdf: '/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf',
        sha256: businessPdfHash,
      },
      {
        id: 'skills',
        count: skills.length,
        page: '/research/katalog-100-ki-skills-und-ki-agents/',
        page_de: '/de/research/katalog-100-ki-skills-und-ki-agents/',
        pdf: '/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf',
        sha256: skillsPdfHash,
      },
    ],
    visuals: [
      '/SSID-docs/images/research/ai-infrastructure/business-models-social-card.png',
      '/SSID-docs/images/research/ai-infrastructure/skills-social-card.png',
      '/SSID-docs/images/research/ai-infrastructure/ai-infrastructure-stack.png',
    ],
  };

  const dataDir = 'src/data/research/ai-infrastructure';
  mkdirSync(path.join(ROOT, dataDir), { recursive: true });
  writeFileSync(path.join(ROOT, dataDir, 'business-models.json'), JSON.stringify(businessModelsDoc, null, 2) + '\n', 'utf-8');
  writeFileSync(path.join(ROOT, dataDir, 'skills.json'), JSON.stringify(skillsDoc, null, 2) + '\n', 'utf-8');
  writeFileSync(path.join(ROOT, dataDir, 'skill-model-matrix.json'), JSON.stringify(matrixDoc, null, 2) + '\n', 'utf-8');
  writeFileSync(path.join(ROOT, dataDir, 'catalog-manifest.json'), JSON.stringify(manifestDoc, null, 2) + '\n', 'utf-8');

  const publicManifestPath = 'public/downloads/research/ai-infrastructure/catalog-manifest.json';
  writeFileSync(path.join(ROOT, publicManifestPath), JSON.stringify(manifestDoc, null, 2) + '\n', 'utf-8');

  console.log(`VERIFIED: business-models.json — ${models.length} models, IDs 1-100 complete.`);
  console.log(`VERIFIED: skills.json — ${skills.length} skills, IDs 1-100 complete, families A-J present.`);
  console.log(`VERIFIED: skill-model-matrix.json — ${links.length} links.`);
  console.log(`VERIFIED: catalog-manifest.json (internal + public) — business PDF sha256=${businessPdfHash}, skills PDF sha256=${skillsPdfHash}.`);
}

build();
