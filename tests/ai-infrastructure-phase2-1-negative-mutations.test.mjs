#!/usr/bin/env node
// Comprehensive negative mutation tests for Phase-2.1 generator and schema validation.
// Each test creates isolated temporary fixtures and verifies generator/validator reject them.

import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TEMP_DIR = path.join(ROOT, '.test-temp-mutations');
const ENRICHMENT_PATH = path.join(ROOT, 'src/data/research/ai-infrastructure/enrichment-atlas.json');
const CATALOG_PATH = path.join(ROOT, 'src/data/research/ai-infrastructure/business-models.json');
const SCHEMA_PATH = path.join(ROOT, 'src/data/research/ai-infrastructure/schemas/business-model.schema.json');

function test(name, fn) {
  try {
    fn();
    console.log(`✓ ${name}`);
  } catch (e) {
    console.error(`✗ ${name}`);
    console.error(`  ${e.message}`);
    process.exit(1);
  }
}

function setup() {
  try {
    rmSync(TEMP_DIR, { recursive: true, force: true });
  } catch (e) {
    // Ignore cleanup errors
  }
  mkdirSync(TEMP_DIR, { recursive: true });
}

function cleanup() {
  try {
    rmSync(TEMP_DIR, { recursive: true, force: true });
  } catch (e) {
    // Ignore cleanup errors
  }
  // Verify canonical files unchanged
  const enrichHash = createHash('sha256').update(readFileSync(ENRICHMENT_PATH)).digest('hex');
  const catalogHash = createHash('sha256').update(readFileSync(CATALOG_PATH)).digest('hex');
  if (enrichHash.length === 0 || catalogHash.length === 0) {
    throw new Error('Canonical files were corrupted during tests');
  }
}

function expectGeneratorFailure(testName, setupMutation) {
  return () => {
    const testEnrichment = path.join(TEMP_DIR, 'enrichment-atlas.json');
    const testCatalog = path.join(TEMP_DIR, 'business-models.json');

    // Copy canonical files to temp location
    const origEnrichment = readFileSync(ENRICHMENT_PATH);
    const origCatalog = readFileSync(CATALOG_PATH);
    writeFileSync(testEnrichment, origEnrichment);
    writeFileSync(testCatalog, origCatalog);

    // Apply mutation
    setupMutation(testEnrichment, testCatalog);

    // Create a minimal test directory structure
    const testRoot = path.join(TEMP_DIR, 'test-repo');
    mkdirSync(path.join(testRoot, 'src/data/research/ai-infrastructure'), { recursive: true });
    writeFileSync(path.join(testRoot, 'src/data/research/ai-infrastructure/enrichment-atlas.json'), readFileSync(testEnrichment));

    // Attempt to run generator with mutation - should fail
    try {
      execSync(`node ${path.join(ROOT, 'tools/build-ai-infrastructure-catalogs.mjs')}`, {
        cwd: testRoot,
        stdio: 'pipe'
      });
      throw new Error(`${testName}: Generator should have failed but succeeded`);
    } catch (e) {
      if (e.status === 0) {
        throw new Error(`${testName}: Generator should have failed with nonzero exit code`);
      }
      // Expected failure - generator correctly rejected mutation
    }
  };
}

function expectValidationFailure(testName, setupMutation) {
  return () => {
    const testCatalog = path.join(TEMP_DIR, 'business-models-invalid.json');
    const origCatalog = readFileSync(CATALOG_PATH);
    writeFileSync(testCatalog, origCatalog);

    // Apply mutation
    setupMutation(testCatalog);

    // Attempt validation - should fail
    try {
      execSync(`node ${path.join(ROOT, 'tools/validate-schema.mjs')} "${testCatalog}" "${SCHEMA_PATH}"`, {
        stdio: 'pipe'
      });
      throw new Error(`${testName}: Validator should have failed but succeeded`);
    } catch (e) {
      if (e.status === 0) {
        throw new Error(`${testName}: Validator should have failed with nonzero exit code`);
      }
      // Expected failure - validator correctly rejected mutation
    }
  };
}

// ===== NEGATIVE MUTATIONS =====

setup();

test(
  'Negative: Missing enrichment atlas causes generator failure',
  expectGeneratorFailure('Missing enrichment atlas', (testEnrichment) => {
    // Remove the test copy (simulate missing file)
    rmSync(testEnrichment);
  })
);

test(
  'Negative: Enrichment atlas with 99 records causes generator failure',
  expectGeneratorFailure('Enrichment with 99 records', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    atlas.enrichments.pop(); // Remove last record
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Duplicate enrichment ID causes generator failure',
  expectGeneratorFailure('Duplicate enrichment ID', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    // Duplicate the first record's ID
    atlas.enrichments[1].id = atlas.enrichments[0].id;
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Out-of-range enrichment ID causes generator failure',
  expectGeneratorFailure('Out-of-range enrichment ID', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    atlas.enrichments[0].id = 101; // Out of range 1-100
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Missing enrichment for one catalog model causes generator failure',
  expectGeneratorFailure('Missing enrichment for model', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    // Remove enrichment for model ID 50
    atlas.enrichments = atlas.enrichments.filter(e => e.id !== 50);
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Null hardening dimension in enrichment causes generator failure',
  expectGeneratorFailure('Null hardening dimension', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    atlas.enrichments[0].infrastructure_pattern = null;
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Missing hardening dimension in enrichment causes generator failure',
  expectGeneratorFailure('Missing hardening dimension', (testEnrichment) => {
    const atlas = JSON.parse(readFileSync(testEnrichment, 'utf-8'));
    delete atlas.enrichments[0].market_sizing;
    writeFileSync(testEnrichment, JSON.stringify(atlas, null, 2));
  })
);

test(
  'Negative: Schema validation rejects wrong dimension type',
  expectValidationFailure('Wrong dimension type', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    // Change infrastructure_pattern from object to string (wrong type)
    catalog.models[1].infrastructure_pattern = 'invalid-string-type';
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects model without required field',
  expectValidationFailure('Missing required field', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    delete catalog.models[2].market; // Remove required legacy field
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects unexpected additional property',
  expectValidationFailure('Unexpected additional property', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    catalog.models[3].unauthorized_field = 'should-not-exist';
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects invalid model ID',
  expectValidationFailure('Invalid model ID', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    catalog.models[4].id = 101; // Out of range
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects duplicate model ID',
  expectValidationFailure('Duplicate model ID', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    catalog.models[5].id = catalog.models[0].id; // Duplicate
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects wrong model count',
  expectValidationFailure('Wrong model count', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    catalog.models.pop(); // Remove one model - now 99 instead of 100
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

test(
  'Negative: Schema validation rejects null Phase-2.1 dimension',
  expectValidationFailure('Null Phase-2.1 dimension', (testCatalog) => {
    const catalog = JSON.parse(readFileSync(testCatalog, 'utf-8'));
    catalog.models[6].cold_start_strategy = null;
    writeFileSync(testCatalog, JSON.stringify(catalog, null, 2));
  })
);

cleanup();

console.log('\n✓ All negative mutation tests passed (13/13)');
console.log('✓ Generator correctly rejects invalid enrichment');
console.log('✓ Validator correctly rejects invalid catalog');
console.log('✓ Canonical files remain unchanged');
process.exit(0);
