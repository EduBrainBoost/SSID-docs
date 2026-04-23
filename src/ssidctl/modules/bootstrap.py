"""Bootstrap module — SSID repo skeleton generation.

Creates the 24 root directories, minimal gate scripts, and SoT seed
placeholders. Operates via worktree + branch + PR workflow.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class BootstrapError(Exception):
    pass


# The canonical 24 root modules for SSID
ROOT_24_DIRS = [
    "01_ai_layer",
    "02_audit_logging",
    "03_core",
    "04_deployment",
    "05_documentation",
    "06_data_pipeline",
    "07_governance_legal",
    "08_identity_score",
    "09_meta_identity",
    "10_interoperability",
    "11_test_simulation",
    "12_tooling",
    "13_ui_layer",
    "14_zero_time_auth",
    "15_infra",
    "16_codex",
    "17_observability",
    "18_data_layer",
    "19_adapters",
    "20_foundation",
    "21_post_quantum_crypto",
    "22_datasets",
    "23_compliance",
    "24_meta_orchestration",
]


def generate_skeleton(target_dir: Path) -> dict[str, Any]:
    """Generate the SSID 24-root skeleton in target_dir.

    Returns summary of what was created.
    """
    created_dirs = []
    created_files = []

    for root in ROOT_24_DIRS:
        root_path = target_dir / root
        root_path.mkdir(parents=True, exist_ok=True)

        # README placeholder
        readme = root_path / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {root}\n\nSoT seed placeholder.\n",
                encoding="utf-8",
            )
            created_files.append(str(readme.relative_to(target_dir)))

        # .gitkeep to ensure empty dirs are tracked
        gitkeep = root_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            created_files.append(str(gitkeep.relative_to(target_dir)))

        created_dirs.append(root)

    return {
        "root_count": len(created_dirs),
        "dirs": created_dirs,
        "files": created_files,
    }


def generate_gates_surface(target_dir: Path) -> list[str]:
    """Generate minimal gate script stubs in 12_tooling.

    Returns list of created file paths (relative).
    """
    tooling = target_dir / "12_tooling"
    scripts_dir = tooling / "scripts"
    cli_dir = tooling / "cli"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    cli_dir.mkdir(parents=True, exist_ok=True)

    created = []

    # structure_guard stub
    sg = scripts_dir / "structure_guard.py"
    if not sg.exists():
        sg.write_text(
            '"""Structure guard stub — validates 24 root directories."""\n'
            "import sys\n"
            "from pathlib import Path\n\n"
            "def main():\n"
            "    repo = Path(__file__).resolve().parent.parent.parent\n"
            "    roots = sorted(d.name for d in repo.iterdir()\n"
            "                   if d.is_dir() and d.name[:2].isdigit())\n"
            "    if len(roots) == 24:\n"
            "        sys.exit(0)\n"
            "    else:\n"
            '        print(f"Expected 24 roots, found {len(roots)}")\n'
            "        sys.exit(24)\n\n"
            'if __name__ == "__main__":\n'
            "    main()\n",
            encoding="utf-8",
        )
        created.append(str(sg.relative_to(target_dir)))

    return created


EMS_STATE_DIRS = [
    "board",
    "content",
    "team",
    "calendar",
    "memory",
    "memory/docs",
    "incidents",
    "tasks",
    "locks",
]


def bootstrap_ems_state(state_dir: Path, evidence_dir: Path, vault_dir: Path) -> dict[str, Any]:
    """Create all EMS state directories needed for operation.

    Returns summary of what was created.
    """
    created = []
    for d in EMS_STATE_DIRS:
        p = state_dir / d
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(d))

    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "runs").mkdir(exist_ok=True)
    created.append("evidence/runs")

    vault_dir.mkdir(parents=True, exist_ok=True)
    created.append("vault")

    return {
        "state_dir": str(state_dir),
        "evidence_dir": str(evidence_dir),
        "vault_dir": str(vault_dir),
        "dirs_created": created,
    }


def validate_skeleton(target_dir: Path) -> dict[str, Any]:
    """Validate that a skeleton is complete.

    Returns {valid: bool, root_count: int, missing: [...]}
    """
    found = []
    missing = []

    for root in ROOT_24_DIRS:
        if (target_dir / root).is_dir():
            found.append(root)
        else:
            missing.append(root)

    return {
        "valid": len(found) == 24,
        "root_count": len(found),
        "missing": missing,
    }


def bootstrap_and_pr(
    target_dir: Path,
    branch: str = "bootstrap/skeleton",
    commit_msg: str = "feat: SSID 24-root skeleton (bootstrap)",
) -> dict[str, Any]:
    """Generate skeleton, commit, and return info for PR creation.

    This does NOT push or create PR — caller must do that via gh CLI.
    Returns {branch, commit_sha, root_count, files_created}.
    """

    def _git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(target_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BootstrapError(f"Git failed: {result.stderr.strip()}")
        return result.stdout

    # Create branch
    _git("checkout", "-b", branch)

    # Generate skeleton + gates
    skel = generate_skeleton(target_dir)
    gates = generate_gates_surface(target_dir)

    # Stage and commit
    _git("add", "-A")
    _git("commit", "-m", commit_msg)

    sha = _git("rev-parse", "HEAD").strip()

    return {
        "branch": branch,
        "commit_sha": sha,
        "root_count": skel["root_count"],
        "files_created": len(skel["files"]) + len(gates),
    }
