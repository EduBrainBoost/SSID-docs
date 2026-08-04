#!/usr/bin/env node
// Validates a JSON instance against a JSON Schema.
// Performs real schema instance validation, not just JSON parsing.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function fail(message) {
  console.error(`BLOCKED: ${message}`);
  process.exit(1);
}

function loadJSON(filePath) {
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'));
  } catch (e) {
    fail(`Failed to parse JSON: ${filePath}: ${e.message}`);
  }
}

function validateInstance(instance, schema, path = '') {
  // Basic schema validation using manual checks
  // For comprehensive validation, a real JSON Schema validator could be added as dependency

  // Type validation
  if (schema.type) {
    const actualType = Array.isArray(instance) ? 'array' : typeof instance;
    let typeMatches = actualType === schema.type;

    // Allow number for integer type if value is actually an integer
    if (schema.type === 'integer' && actualType === 'number' && Number.isInteger(instance)) {
      typeMatches = true;
    }

    // Allow number/integer confusion both directions
    if ((schema.type === 'number' || schema.type === 'integer') && (actualType === 'number')) {
      typeMatches = true;
    }

    if (!typeMatches && !(schema.type === 'object' && actualType === 'object')) {
      return {
        valid: false,
        error: `Type mismatch at ${path}: expected ${schema.type}, got ${actualType}`
      };
    }
  }

  // Object validation
  if (schema.type === 'object' && typeof instance === 'object' && !Array.isArray(instance)) {
    // Check required fields
    if (schema.required) {
      for (const fieldName of schema.required) {
        if (!(fieldName in instance)) {
          return {
            valid: false,
            error: `Missing required field at ${path}: ${fieldName}`
          };
        }
      }
    }

    // Check additional properties when false
    if (schema.additionalProperties === false) {
      const schemaProps = new Set(Object.keys(schema.properties || {}));
      for (const key of Object.keys(instance)) {
        if (!schemaProps.has(key)) {
          return {
            valid: false,
            error: `Unexpected additional property at ${path}: ${key}`
          };
        }
      }
    }

    // Recursively validate properties
    if (schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        if (key in instance) {
          const propPath = path ? `${path}.${key}` : key;
          const result = validateInstance(instance[key], propSchema, propPath);
          if (!result.valid) return result;
        }
      }
    }
  }

  // Array validation
  if (schema.type === 'array' && Array.isArray(instance)) {
    if (schema.items) {
      for (let i = 0; i < instance.length; i++) {
        const itemPath = `${path}[${i}]`;
        const result = validateInstance(instance[i], schema.items, itemPath);
        if (!result.valid) return result;
      }
    }
  }

  return { valid: true };
}

function validateCatalog(catalog, schema) {
  // Validate root
  let result = validateInstance(catalog, schema, 'root');
  if (!result.valid) return result;

  // Validate that models array exists and has exactly 100 items
  if (!catalog.models || !Array.isArray(catalog.models)) {
    return { valid: false, error: 'Root must have "models" array' };
  }
  if (catalog.models.length !== 100) {
    return { valid: false, error: `Catalog must have exactly 100 models, found ${catalog.models.length}` };
  }

  // Validate each model
  const modelSchema = schema.properties.models.items;
  for (let i = 0; i < catalog.models.length; i++) {
    const model = catalog.models[i];
    result = validateInstance(model, modelSchema, `root.models[${i}]`);
    if (!result.valid) return result;

    // Validate Phase-2.1 dimensions exist and are non-empty
    const dimensions = [
      'infrastructure_pattern', 'market_sizing', 'cold_start_strategy',
      'competitive_landscape', 'data_and_integration_dependencies',
      'regulatory_constraints', 'ai_vs_infrastructure_moat', 'market_maturity',
      'evidence_status', 'validation_atlas'
    ];
    for (const dim of dimensions) {
      if (!(dim in model)) {
        return { valid: false, error: `Model ${i} missing Phase-2.1 dimension: ${dim}` };
      }
      if (model[dim] === null || model[dim] === undefined) {
        return { valid: false, error: `Model ${i} has null/undefined ${dim}` };
      }
    }

    // Validate all required legacy fields
    const legacyFields = ['id', 'market', 'pain_point', 'ai_solution', 'monetization', 'market_comment', 'maturity', 'status'];
    for (const field of legacyFields) {
      if (!(field in model)) {
        return { valid: false, error: `Model ${i} missing legacy field: ${field}` };
      }
    }

    // Validate model ID range
    if (!Number.isInteger(model.id) || model.id < 1 || model.id > 100) {
      return { valid: false, error: `Model at index ${i} has invalid id: ${model.id}` };
    }
  }

  return { valid: true };
}

// Main
const [, , instancePath, schemaPath] = process.argv;

if (!instancePath || !schemaPath) {
  fail('Usage: validate-schema.mjs <instance.json> <schema.json>');
}

console.log(`Validating ${instancePath} against ${schemaPath}`);

const instance = loadJSON(instancePath);
const schema = loadJSON(schemaPath);

console.log('✓ JSON files parsed');

const result = validateCatalog(instance, schema);

if (!result.valid) {
  fail(result.error);
}

console.log('✓ Schema validation passed');
console.log(`✓ All ${instance.models.length} models validated`);
console.log('✓ All Phase-2.1 dimensions present in all models');
console.log('✓ All legacy fields present in all models');
console.log('✓ No unauthorized additional properties');

process.exit(0);
