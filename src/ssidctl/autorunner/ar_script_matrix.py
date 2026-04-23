"""AR Script Matrix — maps AR_IDs to SSID script paths and invocation templates."""

from __future__ import annotations

from dataclasses import dataclass, field


class UnknownARIdError(KeyError):
    pass


@dataclass
class ARScriptDef:
    ar_id: str
    script_path: str
    args_template: list[str]
    extra_scripts: list[ARScriptDef] = field(default_factory=list)
    agent_id: str = ""
    agent_model: str = "haiku"


_REGISTRY: dict[str, ARScriptDef] = {
    "AR-01": ARScriptDef(
        ar_id="AR-01",
        script_path="23_compliance/scripts/pii_regex_scan.py",
        args_template=[
            "--files",
            "{repo_root}",
            "--patterns",
            "23_compliance/rules/pii_patterns.yaml",
            "--out",
            "{out}",
            "--repo-root",
            "{repo_root}",
        ],
        agent_id="SEC-05",
        agent_model="opus",
    ),
    "AR-03": ARScriptDef(
        ar_id="AR-03",
        script_path="02_audit_logging/scripts/collect_unanchored.py",
        args_template=[
            "--out",
            "{out}",
            "--agent-runs-dir",
            "02_audit_logging/agent_runs",
            "--since-last-anchor",
            "02_audit_logging/anchor_state.json",
        ],
        extra_scripts=[
            ARScriptDef(
                ar_id="AR-03-merkle",
                script_path="02_audit_logging/scripts/build_merkle_tree.py",
                args_template=["--collect-out", "{collect_out}", "--out", "{out}"],
            )
        ],
        agent_id="OPS-08",
        agent_model="haiku",
    ),
    "AR-04": ARScriptDef(
        ar_id="AR-04",
        script_path="23_compliance/scripts/dora_incident_plan_check.py",
        args_template=["--out", "{out}", "--repo-root", "{repo_root}"],
        extra_scripts=[
            ARScriptDef(
                ar_id="AR-04-validate",
                script_path="23_compliance/scripts/dora_content_validate.py",
                args_template=[
                    "--check-out",
                    "{check_out}",
                    "--out",
                    "{out}",
                    "--repo-root",
                    "{repo_root}",
                ],
            )
        ],
        agent_id="CMP-14",
        agent_model="sonnet",
    ),
    "AR-06": ARScriptDef(
        ar_id="AR-06",
        script_path="05_documentation/scripts/generate_from_chart.py",
        args_template=[
            "--charts",
            "{repo_root}",
            "--template",
            "05_documentation/templates/chart_to_markdown.j2",
            "--out-dir",
            "05_documentation/generated",
            "--out-manifest",
            "{out}",
            "--repo-root",
            "{repo_root}",
        ],
        agent_id="DOC-20",
        agent_model="haiku",
    ),
    "AR-09": ARScriptDef(
        ar_id="AR-09",
        script_path="01_ai_layer/scripts/model_inventory.py",
        args_template=[
            "--out",
            "{out}",
            "--scan-dirs",
            "01_ai_layer",
            "08_identity_score",
            "--repo-root",
            "{repo_root}",
        ],
        extra_scripts=[
            ARScriptDef(
                ar_id="AR-09-fairness",
                script_path="08_identity_score/scripts/pofi_audit.py",
                args_template=[
                    "--out",
                    "{out}",
                    "--bias-suite",
                    "22_datasets/bias_test_suite.yaml",
                ],
            )
        ],
        agent_id="ARS-29",
        agent_model="opus",
    ),
    "AR-10": ARScriptDef(
        ar_id="AR-10",
        script_path="23_compliance/scripts/fee_policy_audit.py",
        args_template=["--policy", "23_compliance/fee_allocation_policy.yaml", "--out", "{out}"],
        extra_scripts=[
            ARScriptDef(
                ar_id="AR-10-subscription",
                script_path="23_compliance/scripts/subscription_audit.py",
                args_template=[
                    "--policy",
                    "07_governance_legal/subscription_revenue_policy.yaml",
                    "--out",
                    "{out}",
                ],
            ),
            ARScriptDef(
                ar_id="AR-10-pofi",
                script_path="23_compliance/scripts/pofi_formula_check.py",
                args_template=[
                    "--policy",
                    "07_governance_legal/proof_of_fairness_policy.yaml",
                    "--out",
                    "{out}",
                ],
            ),
            ARScriptDef(
                ar_id="AR-10-dao",
                script_path="23_compliance/scripts/dao_params_check.py",
                args_template=[
                    "--policy",
                    "07_governance_legal/subscription_revenue_policy.yaml",
                    "--out",
                    "{out}",
                ],
            ),
        ],
        agent_id="CMP-14",
        agent_model="sonnet",
    ),
}


class ARScriptMatrix:
    def get(self, ar_id: str) -> ARScriptDef:
        if ar_id not in _REGISTRY:
            raise UnknownARIdError(f"Unknown AR ID: {ar_id}. Valid: {sorted(_REGISTRY)}")
        return _REGISTRY[ar_id]

    def all_ids(self) -> list[str]:
        return sorted(_REGISTRY.keys())
