"""Agent registry: scan, lock, verify, install agent definitions.

Also exports role-mapping constants and helpers for G-006 contract validation.
"""

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass
class AgentEntry:
    agent_id: str
    file: str
    sha256: str
    model: str
    category: str


@dataclass
class VerifyResult:
    passed: bool
    findings: list[str]


_READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
_READ_BASH_TOOLS = {"Read", "Grep", "Glob", "Bash"}


def _infer_category(tools_set: set[str], permission_mode: str) -> str:
    if permission_mode == "plan" and tools_set <= _READ_ONLY_TOOLS:
        return "read-only"
    if tools_set == _READ_BASH_TOOLS and "Edit" not in tools_set and "Write" not in tools_set:
        return "read-bash"
    if "Edit" in tools_set and "Write" in tools_set:
        return "write-ssid"
    if "Write" in tools_set and "Edit" not in tools_set:
        return "write-ems"
    if "Bash" in tools_set and "Write" not in tools_set and "Edit" not in tools_set:
        return "ems-board"
    return "unknown"


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise ValueError(f"No frontmatter in {path.name}")
    return yaml.safe_load(match.group(1))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AgentRegistry:
    def __init__(self, ems_root: Path):
        self.ems_root = ems_root
        self.agents_dir = ems_root / ".claude" / "agents"

    def scan(self) -> list[AgentEntry]:
        entries = []
        for f in sorted(self.agents_dir.glob("*.md")):
            fm = _parse_frontmatter(f)
            tools_str = fm.get("tools", "")
            if isinstance(tools_str, str):
                tools = {t.strip() for t in tools_str.split(",")}
            else:
                tools = set(tools_str)
            category = _infer_category(tools, fm.get("permissionMode", "default"))
            entries.append(
                AgentEntry(
                    agent_id=fm["name"],
                    file=str(f.relative_to(self.ems_root)).replace("\\", "/"),
                    sha256=_sha256_file(f),
                    model=fm.get("model", "inherit"),
                    category=category,
                )
            )
        return entries

    def generate_lockfile(self, ems_git_sha: str) -> dict:
        entries = self.scan()
        return {
            "version": "1.0.0",
            "ems_git_sha": ems_git_sha,
            "agents": [asdict(e) for e in entries],
        }

    def write_lockfile(self, ems_git_sha: str) -> Path:
        lockpath = self.ems_root / "agents.lock.json"
        data = self.generate_lockfile(ems_git_sha)
        lockpath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return lockpath

    def verify_lockfile(self) -> VerifyResult:
        lockpath = self.ems_root / "agents.lock.json"
        if not lockpath.exists():
            return VerifyResult(passed=False, findings=["agents.lock.json not found"])
        data = json.loads(lockpath.read_text(encoding="utf-8"))
        findings = []
        for entry in data.get("agents", []):
            fpath = self.ems_root / entry["file"]
            if not fpath.exists():
                findings.append(f"Missing: {entry['file']}")
                continue
            actual_sha = _sha256_file(fpath)
            if actual_sha != entry["sha256"]:
                findings.append(
                    f"sha256 mismatch for {entry['agent_id']}: "
                    f"expected {entry['sha256'][:12]}..., got {actual_sha[:12]}..."
                )
        return VerifyResult(passed=len(findings) == 0, findings=findings)

    def verify_definitions(self) -> VerifyResult:
        """Verify canonical agent definitions in agents/definitions/.

        Checks that all 11 expected SSID agents exist and have valid frontmatter.
        """
        from ssidctl.core.attestation import EXPECTED_AGENTS

        defs_dir = self.ems_root / "agents" / "definitions"
        findings = []

        if not defs_dir.exists():
            return VerifyResult(
                passed=False,
                findings=["agents/definitions/ directory not found"],
            )

        for agent_name in EXPECTED_AGENTS:
            agent_file = defs_dir / f"{agent_name}.md"
            if not agent_file.exists():
                findings.append(f"Missing definition: {agent_name}.md")
                continue
            try:
                _parse_frontmatter(agent_file)
            except ValueError as e:
                findings.append(f"Invalid frontmatter: {agent_name}.md ({e})")

        return VerifyResult(passed=len(findings) == 0, findings=findings)

    def install(self, target_dir: Path) -> list[dict]:
        lockpath = self.ems_root / "agents.lock.json"
        if not lockpath.exists():
            raise FileNotFoundError("agents.lock.json not found. Run 'ssidctl agents lock' first.")
        verify = self.verify_lockfile()
        if not verify.passed:
            raise ValueError(f"Lockfile verification failed: {'; '.join(verify.findings)}")
        data = json.loads(lockpath.read_text(encoding="utf-8"))
        evidences = []
        for entry in data["agents"]:
            src = self.ems_root / entry["file"]
            dst = target_dir / f"{entry['agent_id']}.md"
            shutil.copy2(src, dst)
            evidences.append(
                {
                    "ems_git_sha": data["ems_git_sha"],
                    "agent_id": entry["agent_id"],
                    "agent_sha256": entry["sha256"],
                    "target": str(target_dir),
                }
            )
        return evidences


# ---------------------------------------------------------------------------
# G-006: SSID contract role → EMS agent profile mapping
# ---------------------------------------------------------------------------

# Mapping from SSID contract role names to EMS agent profile IDs.
# Each role maps to a list because some roles may share a profile.
SSID_ROLE_MAPPING: dict[str, list[str]] = {
    "Planner": ["01_ssid_planner"],
    "Analyst": ["02_context_analyst"],
    "Implementer": ["03_patch_implementer"],
    "TestRunner": ["04_gate_runner_auditor"],
    "ComplianceAuditor": ["04_gate_runner_auditor"],
    "Reviewer": ["05_review_validator"],
    "PRIntegrator": ["07_pr_integrator"],
    "OpsRunner": ["08_ops_runner"],
}

# The canonical set of SSID contract role names
SSID_CONTRACT_ROLES: frozenset[str] = frozenset(SSID_ROLE_MAPPING.keys())

# Agents that exist only in EMS (no SSID contract role maps to them)
EMS_ONLY_AGENTS: list[str] = [
    "06_drift_sentinel",
    "09_memory_curator",
    "10_content_pipeline",
]

# Agents used for governance / compliance work (subset of all agents)
GOVERNANCE_AGENTS: list[str] = [
    "11_board_manager",
]

# All 11 known agent profile IDs
ALL_KNOWN_AGENT_IDS: frozenset[str] = frozenset(
    {aid for agents in SSID_ROLE_MAPPING.values() for aid in agents}
    | set(EMS_ONLY_AGENTS)
    | set(GOVERNANCE_AGENTS)
)


def resolve_agents(roles: list[str]) -> list[str]:
    """Resolve a list of SSID contract role names to EMS agent profile IDs.

    - Deduplicates while preserving order of first occurrence.
    - Raises ValueError for any unknown role name.
    """
    unknown = [r for r in roles if r not in SSID_CONTRACT_ROLES]
    if unknown:
        raise ValueError(f"Unknown SSID contract roles: {unknown!r}")

    seen: set[str] = set()
    result: list[str] = []
    for role in roles:
        for aid in SSID_ROLE_MAPPING[role]:
            if aid not in seen:
                seen.add(aid)
                result.append(aid)
    return result


def validate_roles(identifiers: list[str]) -> bool:
    """Return True if every identifier is either a valid SSID contract role
    or a known EMS agent profile ID; False otherwise.
    """
    all_valid = SSID_CONTRACT_ROLES | ALL_KNOWN_AGENT_IDS
    return all(ident in all_valid for ident in identifiers)
