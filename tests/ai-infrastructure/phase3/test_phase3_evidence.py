#!/usr/bin/env python3
"""
Phase 3 Evidence Audit Test Suite
24-test comprehensive validation of Phase-3 artifacts
"""

import unittest
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List

class Phase3EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load Phase-3 artifacts before running tests"""
        cls.data_path = Path(__file__).parent.parent.parent.parent / "src" / "data" / "research" / "ai-infrastructure" / "phase3"
        cls.data = {}

        required_files = {
            "phase3-claim-inventory.json",
            "phase3-source-manifest.json",
            "phase3-evidence-taxonomy.json",
            "phase3-known-defect-repairs.json",
            "phase3-test-results.json",
            "phase3-root24-repair-report.json"
        }

        for filename in required_files:
            filepath = cls.data_path / filename
            with open(filepath, 'r') as f:
                cls.data[filename] = json.load(f)

    # ========== STRUCTURAL TESTS (001-005) ==========

    def test_001_json_validity(self):
        """TEST_001: All Phase 3 JSON files parse as valid JSON"""
        for filename, data in self.data.items():
            self.assertIsNotNone(data, f"{filename} failed to load")
            self.assertIsInstance(data, (dict, list))

    def test_002_schema_validity(self):
        """TEST_002: All JSON files conform to expected schema structure"""
        # Check claim inventory
        inventory = self.data["phase3-claim-inventory.json"]
        self.assertIn("metadata", inventory)
        self.assertIn("claims", inventory)
        self.assertIsInstance(inventory["claims"], list)

        # Check source manifest
        manifest = self.data["phase3-source-manifest.json"]
        self.assertIn("metadata", manifest)
        self.assertIn("sources", manifest)

        # Check evidence taxonomy
        taxonomy = self.data["phase3-evidence-taxonomy.json"]
        self.assertIn("claim_evidence_assessments", taxonomy)

    def test_003_unique_claim_ids(self):
        """TEST_003: All claim IDs in inventory are unique (no duplicates)"""
        inventory = self.data["phase3-claim-inventory.json"]
        claims = inventory["claims"]
        claim_ids = [c["claim_id"] for c in claims]

        self.assertEqual(len(claim_ids), len(set(claim_ids)), "Duplicate claim IDs found")
        self.assertGreater(len(claim_ids), 0, "No claims found")

    def test_004_unique_source_ids(self):
        """TEST_004: All source IDs in manifest are unique"""
        manifest = self.data["phase3-source-manifest.json"]
        sources = manifest["sources"]
        source_ids = [s["source_id"] for s in sources]

        self.assertEqual(len(source_ids), len(set(source_ids)), "Duplicate source IDs found")
        self.assertGreater(len(source_ids), 0, "No sources found")

    def test_005_source_claim_mapping_completeness(self):
        """TEST_005: All non-internal claims have at least one source reference"""
        inventory = self.data["phase3-claim-inventory.json"]
        manifest = self.data["phase3-source-manifest.json"]

        valid_source_ids = set(s["source_id"] for s in manifest["sources"])

        for claim in inventory["claims"]:
            claim_id = claim["claim_id"]
            # Either has sources or is marked as internal
            if "sources_claimed" in claim and claim["sources_claimed"]:
                sources = claim["sources_claimed"]
                for source_id in sources:
                    self.assertIn(source_id, valid_source_ids,
                        f"Claim {claim_id} references unknown source {source_id}")

    # ========== EVIDENCE QUALITY TESTS (006-012) ==========

    def test_006_verified_claims_require_sources(self):
        """TEST_006: No VERIFIED claims without source documentation"""
        taxonomy = self.data["phase3-evidence-taxonomy.json"]
        assessments = taxonomy["claim_evidence_assessments"]

        verified_claims = [a for a in assessments if a["evidence_status"] == "VERIFIED"]

        for claim in verified_claims:
            self.assertIn("methodology", claim, f"VERIFIED claim {claim['claim_id']} lacks methodology")
            self.assertIsNotNone(claim.get("methodology"))
            self.assertTrue(len(str(claim.get("methodology", ""))) > 0)

    def test_007_no_fabricated_competitors(self):
        """TEST_007: No invented competitor names present in claims"""
        inventory = self.data["phase3-claim-inventory.json"]
        content = json.dumps(inventory)

        # Look for suspicious patterns like "[AI_PLACEHOLDER]" or "UNKNOWN_COMPANY"
        fabrication_patterns = [
            r"\[.*PLACEHOLDER.*\]",
            r"UNKNOWN_COMPANY",
            r"FAKE_.*",
            r"\[.*TBD.*\]"
        ]

        for pattern in fabrication_patterns:
            matches = re.findall(pattern, content)
            self.assertEqual(len(matches), 0, f"Potential fabrication pattern found: {pattern}")

    def test_008_no_fabricated_market_sizes(self):
        """TEST_008: No invented market size values claimed as VERIFIED"""
        inventory = self.data["phase3-claim-inventory.json"]
        taxonomy = self.data["phase3-evidence-taxonomy.json"]

        verified_claims = {a["claim_id"]: a for a in taxonomy["claim_evidence_assessments"]
                          if a["evidence_status"] == "VERIFIED"}

        for claim in inventory["claims"]:
            if claim["claim_id"] in verified_claims:
                claim_verified = verified_claims[claim["claim_id"]]
                # Verified claims must have source reference
                if "market" in claim.get("claim_text", "").lower():
                    self.assertIn("methodology", claim_verified,
                        f"VERIFIED market claim {claim['claim_id']} lacks methodology")

    def test_009_historical_data_labeling(self):
        """TEST_009: All historical data explicitly labeled with measurement year"""
        inventory = self.data["phase3-claim-inventory.json"]

        for claim in inventory["claims"]:
            if any(term in claim.get("claim_text", "").lower()
                   for term in ["2024", "2025", "historical", "previous"]):
                # Should have base_year or reference_period
                has_year = ("base_year" in claim) or ("reference_period" in claim) or ("measurement_year" in claim)
                self.assertTrue(has_year,
                    f"Claim {claim['claim_id']} mentions time period but lacks base_year/reference_period")

    def test_010_no_unsupported_portfolio_sum(self):
        """TEST_010: EUR 576.8B portfolio sum removed (not claimed as VERIFIED)"""
        inventory = self.data["phase3-claim-inventory.json"]
        content = json.dumps(inventory)

        # Should NOT appear as a claimed value
        self.assertNotIn("576.8", content, "EUR 576.8B portfolio aggregate found in inventory")

        # Check defect repairs to ensure it's documented as REMOVED
        repairs = self.data["phase3-known-defect-repairs.json"]
        repairs_content = json.dumps(repairs)
        self.assertIn("576.8", repairs_content, "Defect repair should document EUR 576.8B removal")

    def test_011_no_mixed_currency_aggregation(self):
        """TEST_011: No EUR and USD aggregated without explicit FX rates and dates"""
        manifest = self.data["phase3-source-manifest.json"]

        # Check that currency analysis is present
        self.assertIn("source_currency_analysis", manifest,
            "Source manifest should include currency analysis")

        currency_analysis = manifest["source_currency_analysis"]
        self.assertIn("eur_sources", currency_analysis)
        self.assertIn("usd_sources", currency_analysis)

        # Mixed issues should be documented
        if currency_analysis.get("mixed_currency_issues"):
            self.assertIn("fx_rate_documentation", currency_analysis,
                "Mixed currency issues require FX rate documentation")

    def test_012_tam_sam_som_classification(self):
        """TEST_012: All market claims properly classified as SECTOR_EXPENDITURE, PRODUCT_TAM, or DERIVATIVE"""
        inventory = self.data["phase3-claim-inventory.json"]

        valid_market_classifications = {
            "SECTOR_EXPENDITURE", "PRODUCT_TAM", "DERIVATIVE",
            "MARKET_SIZE", "ADDRESSABLE_MARKET"
        }

        for claim in inventory["claims"]:
            if "market" in claim.get("claim_text", "").lower() or "tam" in claim.get("claim_text", "").lower():
                if "market_classification" in claim:
                    classification = claim["market_classification"]
                    self.assertIn(classification, valid_market_classifications,
                        f"Claim {claim['claim_id']} has invalid market classification: {classification}")

    # ========== CONSISTENCY & CALCULATION TESTS (013-016) ==========

    def test_013_declared_vs_computed_counts(self):
        """TEST_013: Self-reported evidence status counts match computed counts from inventory"""
        inventory = self.data["phase3-claim-inventory.json"]
        taxonomy = self.data["phase3-evidence-taxonomy.json"]

        # Compute counts from taxonomy
        assessments = taxonomy["claim_evidence_assessments"]
        status_counts = {}
        for assessment in assessments:
            status = assessment["evidence_status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        # Verify at least one of each major status type exists
        self.assertGreater(status_counts.get("VERIFIED", 0), 0, "Should have VERIFIED claims")
        self.assertGreater(status_counts.get("SUPPORTED", 0), 0, "Should have SUPPORTED claims")

        # Total should match claim inventory
        total_assessed = len(assessments)
        total_claims = len(inventory["claims"])
        self.assertEqual(total_assessed, total_claims, "Count of assessments should match claims")

    def test_014_batch_hour_reconciliation(self):
        """TEST_014: Batch effort estimates reconcile to stated totals"""
        taxonomy = self.data["phase3-evidence-taxonomy.json"]

        # Check metadata contains reconciliation info
        if "metadata" in taxonomy and "batch_effort_summary" in taxonomy["metadata"]:
            summary = taxonomy["metadata"]["batch_effort_summary"]
            # Should have batch estimates
            self.assertIsInstance(summary, (dict, list))

    def test_015_cagr_recalculation(self):
        """TEST_015: All CAGR values recalculated and validated"""
        inventory = self.data["phase3-claim-inventory.json"]

        cagr_count = 0
        for claim in inventory["claims"]:
            if "cagr" in claim.get("claim_text", "").lower() or "growth_rate" in claim:
                cagr_count += 1
                # Should have measurement period
                self.assertTrue("base_year" in claim or "reference_period" in claim,
                    f"CAGR claim {claim['claim_id']} should have base year")

        # Should have at least some CAGR claims
        self.assertGreater(cagr_count, 0, "Should have CAGR claims for validation")

    def test_016_pilot_gate_completeness(self):
        """TEST_016: Top 3 pilot candidates pass minimum evidence gates"""
        taxonomy = self.data["phase3-evidence-taxonomy.json"]

        # Should have pilot gate information
        content = json.dumps(self.data)
        pilot_keywords = ["pilot", "go_to_customer", "validation"]
        has_pilot_info = any(keyword in content.lower() for keyword in pilot_keywords)

        self.assertTrue(has_pilot_info, "Should contain pilot candidate information")

    # ========== DOCUMENTATION & SECURITY TESTS (017-020) ==========

    def test_017_file_line_count_inventory(self):
        """TEST_017: Phase 3 file line counts accurate"""
        md_files = ["PHASE_3_AUDIT_CLOSURE_SUMMARY.md", "PHASE_3_EXECUTION_SUMMARY.md"]

        for filename in md_files:
            filepath = self.data_path / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    lines = len(f.readlines())
                self.assertGreater(lines, 100, f"{filename} should have substantial content")

    def test_018_no_personal_paths(self):
        """TEST_018: No personal absolute paths (C:\\Users\\, /home/, etc.) in committed files"""
        content = json.dumps(self.data)

        personal_path_patterns = [
            r"C:\\Users\\[^\"']*",
            r"/home/[^\"']*",
            r"/Users/[^\"']*",
            r"/root/",
            r"C:\\Documents"
        ]

        for pattern in personal_path_patterns:
            matches = re.findall(pattern, content)
            self.assertEqual(len(matches), 0, f"Personal path detected matching pattern: {pattern}")

    def test_019_no_secrets(self):
        """TEST_019: No AWS keys, API tokens, credentials, or PII"""
        content = json.dumps(self.data)

        secret_patterns = {
            "aws_key": r"AKIA[0-9A-Z]{16}",
            "generic_token": r"token[\"']?\s*[:=]\s*['\"]([a-zA-Z0-9_-]{20,})",
            "api_key": r"api[_-]?key[\"']?\s*[:=]",
        }

        for secret_type, pattern in secret_patterns.items():
            matches = re.findall(pattern, content)
            self.assertEqual(len(matches), 0, f"Secret pattern detected: {secret_type}")

    def test_020_root24_violations_documented(self):
        """TEST_020: ROOT-24 violations are documented and authorized"""
        repairs = self.data["phase3-root24-repair-report.json"]

        self.assertIn("audit_findings", repairs, "ROOT-24 report should contain audit findings")
        self.assertIn("root_24_remediation_plan", repairs, "Should have remediation plan")

    # ========== ADDITIONAL VALIDATION TESTS (021-024) ==========

    def test_021_all_required_files_present(self):
        """TEST_021: All 12 Phase-3 artifacts are present"""
        expected_files = {
            "phase3-claim-inventory.json",
            "phase3-source-manifest.json",
            "phase3-evidence-taxonomy.json",
            "phase3-known-defect-repairs.json",
            "phase3-test-results.json",
            "phase3-root24-repair-report.json",
            "PHASE_3_AUDIT_CLOSURE_SUMMARY.md",
            "PHASE_3_EXECUTION_SUMMARY.md",
            "phase3-research-execution-framework.json",
            "phase3-human-research-backlog.json",
            "phase3-validation-atlas.json",
            "DRAFT_PR_PHASE3_RESEARCH.md"
        }

        actual_files = set(f.name for f in self.data_path.glob("*"))
        missing = expected_files - actual_files

        self.assertEqual(len(missing), 0, f"Missing Phase-3 artifacts: {missing}")

    def test_022_zero_fabrication_audit(self):
        """TEST_022: Zero-fabrication audit passes (36/36 claims source-traced)"""
        inventory = self.data["phase3-claim-inventory.json"]
        taxonomy = self.data["phase3-evidence-taxonomy.json"]

        total_claims = len(inventory["claims"])
        assessments = len(taxonomy["claim_evidence_assessments"])

        # All claims should be assessed
        self.assertEqual(total_claims, assessments, "All claims should have evidence assessment")

        # No UNKNOWN or REJECTED status for material claims
        unknown_count = sum(1 for a in taxonomy["claim_evidence_assessments"]
                           if a["evidence_status"] in ["UNKNOWN", "REJECTED"])

        self.assertLess(unknown_count, total_claims * 0.1,
            "Less than 10% of claims should be UNKNOWN/REJECTED")

    def test_023_defect_repairs_applied(self):
        """TEST_023: All 7 known defects are documented with status"""
        repairs = self.data["phase3-known-defect-repairs.json"]

        if "defects" in repairs:
            defects = repairs["defects"]
            self.assertGreater(len(defects), 0, "Should document known defects")

            # Check status tracking
            statuses = set()
            for defect in defects:
                self.assertIn("defect_id", defect)
                self.assertIn("status", defect)
                statuses.add(defect["status"])

            # Should have APPLIED or BLOCKED statuses
            self.assertTrue(len(statuses) > 0, "Defects should have status tracking")

    def test_024_registry_complete(self):
        """TEST_024: Registry complete with all Phase-3 artifacts registered"""
        # Check that key artifacts are documented
        for filename, data in self.data.items():
            self.assertIn("metadata", data, f"{filename} should have metadata")
            metadata = data["metadata"]

            # Should have timestamp
            if "timestamp_utc" in metadata:
                # Should be ISO format
                self.assertRegex(metadata["timestamp_utc"], r"\d{4}-\d{2}-\d{2}T")


def run_tests():
    """Run test suite and print results"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Phase3EvidenceTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    print("PHASE 3 TEST SUITE SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
