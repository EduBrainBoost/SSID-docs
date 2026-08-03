"""
Phase 2.1 Schema Contract Validation Tests
Validates 100 AI infrastructure business models against strict schema contracts.
"""

import json
import re
from pathlib import Path
from datetime import datetime
import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


# Paths to data and schema
DATA_DIR = Path(__file__).parent.parent.parent / "src" / "data" / "research" / "ai-infrastructure"
SCHEMA_FILE = DATA_DIR / "schemas" / "business-model.schema.json"
CATALOG_FILE = DATA_DIR / "business-models.json"


@pytest.fixture(scope="session")
def schema():
    """Load the business model schema."""
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def catalog(schema):
    """Load the business models catalog."""
    with open(CATALOG_FILE, encoding="utf-8") as f:
        catalog_data = json.load(f)
    return catalog_data


class TestMetaSchema:
    """Validate schema structure against JSON Schema Draft 2020-12."""

    def test_schema_is_valid_draft_2020_12(self, schema):
        """Schema must conform to JSON Schema Draft 2020-12 metaschema."""
        Validator = Draft202012Validator
        Validator.check_schema(schema)  # Raises if invalid
        assert Validator.__name__ == "Draft202012Validator"

    def test_schema_declares_correct_version(self, schema):
        """Schema must declare Draft 2020-12."""
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


class TestCatalogStructure:
    """Validate overall catalog structure."""

    def test_catalog_has_required_root_properties(self, catalog):
        """Catalog must have required root properties."""
        required = ["catalog_id", "title", "language", "count", "models"]
        for prop in required:
            assert prop in catalog, f"Missing required property: {prop}"

    def test_catalog_id_is_correct(self, catalog):
        """Catalog ID must be correct value."""
        assert catalog["catalog_id"] == "ai-infrastructure-business-models-100"

    def test_catalog_language_is_de(self, catalog):
        """Catalog language must be German."""
        assert catalog["language"] == "de"

    def test_catalog_count_is_100(self, catalog):
        """Catalog must declare exactly 100 models."""
        assert catalog["count"] == 100

    def test_catalog_has_100_models(self, catalog):
        """Catalog must contain exactly 100 models."""
        assert len(catalog["models"]) == 100

    def test_catalog_validates_against_schema(self, schema, catalog):
        """Complete catalog must validate against schema."""
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = list(validator.iter_errors(catalog))
        assert len(errors) == 0, f"Catalog validation failed: {errors}"


class TestFullDocumentValidation:
    """Validate entire catalog against schema."""

    def test_no_validation_errors(self, schema, catalog):
        """Complete document must have zero validation errors."""
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(catalog),
            key=lambda e: list(e.absolute_path),
        )
        error_messages = [f"{list(e.absolute_path)}: {e.message}" for e in errors]
        assert len(errors) == 0, "\n".join(error_messages)


class TestModelLevelValidation:
    """Validate individual models against schema."""

    def test_exactly_100_models(self, catalog):
        """Catalog must contain exactly 100 models."""
        assert len(catalog["models"]) == 100

    def test_all_models_validate(self, schema, catalog):
        """All 100 models must individually validate."""
        model_schema = schema["$defs"]["model"]
        validator = Draft202012Validator(model_schema, format_checker=FormatChecker())

        # Need to resolve references
        from jsonschema import RefResolver
        resolver = RefResolver.from_schema(schema)

        passed = 0
        failed_models = []

        for idx, model in enumerate(catalog["models"]):
            validator_with_resolver = Draft202012Validator(
                model_schema,
                format_checker=FormatChecker(),
                resolver=resolver,
            )
            errors = list(validator_with_resolver.iter_errors(model))

            if errors:
                failed_models.append({
                    "index": idx,
                    "id": model.get("id"),
                    "model_id": model.get("model_id"),
                    "errors": [e.message for e in errors[:3]],
                })
            else:
                passed += 1

        assert passed == 100, f"Only {passed}/100 models passed validation"
        assert len(failed_models) == 0, f"Failed models: {failed_models}"


class TestIDContract:
    """Validate ID consistency across all models."""

    def test_100_unique_numeric_ids(self, catalog):
        """Must have 100 unique numeric IDs."""
        ids = [m["id"] for m in catalog["models"]]
        assert len(set(ids)) == 100, f"Duplicate numeric IDs found"

    def test_numeric_ids_are_1_to_100(self, catalog):
        """Numeric IDs must be exactly 1-100."""
        ids = sorted([m["id"] for m in catalog["models"]])
        assert ids == list(range(1, 101)), "IDs are not 1-100"

    def test_100_unique_model_ids(self, catalog):
        """Must have 100 unique model IDs."""
        model_ids = [m["model_id"] for m in catalog["models"]]
        assert len(set(model_ids)) == 100, "Duplicate model IDs found"

    def test_model_ids_match_format(self, catalog):
        """All model IDs must match AI-INFRA-NNN format."""
        pattern = r"^AI-INFRA-\d{3}$"
        for model in catalog["models"]:
            mid = model["model_id"]
            assert re.match(pattern, mid), f"Invalid model_id format: {mid}"

    def test_model_id_suffix_matches_numeric_id(self, catalog):
        """Model ID suffix must match numeric ID."""
        for model in catalog["models"]:
            numeric_id = model["id"]
            model_id = model["model_id"]
            suffix = int(re.match(r"^AI-INFRA-(\d+)$", model_id).group(1))
            assert suffix == numeric_id, f"ID mismatch: {numeric_id} vs {suffix}"

    def test_source_numbers_match_ids(self, catalog):
        """Source numbers must exactly match numeric IDs."""
        for model in catalog["models"]:
            assert model["source_number"] == model["id"], \
                f"source_number {model['source_number']} != id {model['id']}"

    def test_no_missing_ids(self, catalog):
        """All IDs 1-100 must be present."""
        ids = {m["id"] for m in catalog["models"]}
        expected = set(range(1, 101))
        missing = expected - ids
        assert len(missing) == 0, f"Missing IDs: {missing}"

    def test_no_duplicate_ids(self, catalog):
        """No duplicate numeric IDs."""
        ids = [m["id"] for m in catalog["models"]]
        duplicates = [x for x in ids if ids.count(x) > 1]
        assert len(duplicates) == 0, f"Duplicate IDs: {set(duplicates)}"


class TestDimensionCompleteness:
    """Validate that required dimension fields are present."""

    @pytest.mark.parametrize("model_index", range(100))
    def test_infrastructure_pattern_required_fields(self, catalog, model_index):
        """infrastructure_pattern must have required fields."""
        model = catalog["models"][model_index]
        dim = model["infrastructure_pattern"]
        required = ["type", "architecture", "coordination_model", "network_effect", "evidence"]
        for field in required:
            assert field in dim, f"Model {model_index}: missing {field}"

    @pytest.mark.parametrize("model_index", range(100))
    def test_market_sizing_required_fields(self, catalog, model_index):
        """market_sizing must have required fields."""
        model = catalog["models"][model_index]
        dim = model["market_sizing"]
        required = ["tam", "sam", "som", "currency", "base_year", "methodology",
                   "geographic_scope", "market_definition", "evidence"]
        for field in required:
            assert field in dim, f"Model {model_index}: missing {field}"

    @pytest.mark.parametrize("model_index", range(100))
    def test_validation_atlas_required_fields(self, catalog, model_index):
        """validation_atlas must have required fields."""
        model = catalog["models"][model_index]
        dim = model["validation_atlas"]
        required = ["overall_status", "validation_score", "last_validated_utc"]
        for field in required:
            assert field in dim, f"Model {model_index}: missing {field}"


class TestDateTimeFormats:
    """Validate datetime format compliance."""

    @pytest.mark.parametrize("model_index", range(100))
    def test_evidence_last_verified_utc_format(self, catalog, model_index):
        """Evidence timestamps must be ISO 8601 datetime."""
        model = catalog["models"][model_index]

        # Check multiple evidence fields
        evidence_fields = [
            ("infrastructure_pattern", "evidence"),
            ("market_sizing", "evidence"),
            ("evidence_status", None),  # Direct evidence
        ]

        for path in evidence_fields:
            if path[1]:
                dim = model[path[0]]
                evidence = dim.get(path[1])
            else:
                evidence = model[path[0]]

            if evidence and "last_verified_utc" in evidence:
                dt_str = evidence["last_verified_utc"]
                # Should be valid ISO 8601
                try:
                    datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"Invalid datetime: {dt_str}")

    @pytest.mark.parametrize("model_index", range(100))
    def test_validation_atlas_last_validated_utc_format(self, catalog, model_index):
        """validation_atlas.last_validated_utc must be ISO 8601."""
        model = catalog["models"][model_index]
        dt_str = model["validation_atlas"]["last_validated_utc"]
        try:
            datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid datetime: {dt_str}")


class TestCrosFieldConsistency:
    """Validate cross-field consistency rules."""

    @pytest.mark.parametrize("model_index", range(100))
    def test_failed_zero_means_pass_status(self, catalog, model_index):
        """If failed > 0, status cannot be PASS."""
        model = catalog["models"][model_index]
        atlas = model.get("validation_atlas", {})

        categories = [k for k in atlas.keys() if k.endswith("_validation")]
        for cat_name in categories:
            cat = atlas.get(cat_name, {})
            if cat:
                failed = cat.get("failed", 0)
                status = cat.get("status")
                if failed > 0:
                    assert status != "PASS", \
                        f"Model {model_index} {cat_name}: failed > 0 but status is PASS"


class TestNoUnexpectedFields:
    """Validate no additional unexpected properties."""

    def test_catalog_no_unexpected_root_properties(self, schema, catalog):
        """Catalog has no properties beyond schema definition."""
        schema_props = set(schema["properties"].keys())
        catalog_props = set(catalog.keys())
        unexpected = catalog_props - schema_props
        assert len(unexpected) == 0, f"Unexpected root properties: {unexpected}"


class TestNegativeFixtures:
    """Test that invalid data is rejected."""

    def test_missing_model_id_rejected(self, schema, catalog):
        """Model without model_id must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        del valid_model["model_id"]

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model without model_id"

    def test_invalid_model_id_format_rejected(self, schema, catalog):
        """Model with invalid model_id format must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        valid_model["model_id"] = "INVALID-FORMAT"

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model with invalid model_id format"

    def test_numeric_id_zero_rejected(self, schema, catalog):
        """Model with id=0 must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        valid_model["id"] = 0

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model with id=0"

    def test_numeric_id_101_rejected(self, schema, catalog):
        """Model with id=101 must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        valid_model["id"] = 101

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model with id=101"

    def test_invalid_validation_score_101_rejected(self, schema, catalog):
        """Model with validation_score > 100 must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        valid_model["validation_atlas"] = valid_model["validation_atlas"].copy()
        valid_model["validation_atlas"]["validation_score"] = 101

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model with validation_score > 100"

    def test_invalid_durability_score_11_rejected(self, schema, catalog):
        """Model with durability_score > 10 must be rejected."""
        from jsonschema import RefResolver
        model_schema = schema["$defs"]["model"]
        resolver = RefResolver.from_schema(schema)

        valid_model = catalog["models"][0].copy()
        valid_model["ai_vs_infrastructure_moat"] = valid_model["ai_vs_infrastructure_moat"].copy()
        valid_model["ai_vs_infrastructure_moat"]["durability_score"] = 11

        validator = Draft202012Validator(
            model_schema,
            format_checker=FormatChecker(),
            resolver=resolver,
        )
        errors = list(validator.iter_errors(valid_model))
        assert len(errors) > 0, "Should reject model with durability_score > 10"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
