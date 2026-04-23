"""Guard/Gate matrix loader.

Loads guard_gate_matrix.yaml and policy files from the policies/ directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_POLICIES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "policies"


@dataclass(frozen=True)
class GuardDef:
    id: str
    name: str
    phase: str
    description: str
    bootstrap: str
    enabled: bool
    configurable: bool = False


@dataclass(frozen=True)
class GateDef:
    id: str
    name: str
    script: str
    exit_codes: dict[int, str]
    mode: str
    args: list[str] = field(default_factory=list)
    skip_reason: str = ""


@dataclass(frozen=True)
class Matrix:
    guards: list[GuardDef]
    gates: list[GateDef]


def load_matrix(matrix_path: Path | None = None) -> Matrix:
    """Load guard/gate matrix from YAML."""
    if matrix_path is None:
        matrix_path = _POLICIES_DIR / "guard_gate_matrix.yaml"

    with open(matrix_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    guards = []
    for g in raw.get("guards", []):
        guards.append(
            GuardDef(
                id=g["id"],
                name=g["name"],
                phase=g["phase"],
                description=g["description"],
                bootstrap=g["bootstrap"],
                enabled=g.get("enabled", True),
                configurable=g.get("configurable", False),
            )
        )

    gates = []
    for g in raw.get("gates", []):
        exit_codes = {int(k): v for k, v in g.get("exit_codes", {}).items()}
        gates.append(
            GateDef(
                id=g["id"],
                name=g["name"],
                script=g.get("script", ""),
                exit_codes=exit_codes,
                mode=g["mode"],
                args=g.get("args", []),
                skip_reason=g.get("skip_reason", ""),
            )
        )

    return Matrix(guards=guards, gates=gates)


def load_forbidden_extensions(path: Path | None = None) -> list[str]:
    if path is None:
        path = _POLICIES_DIR / "forbidden_extensions.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("extensions", [])


def load_forbidden_paths(path: Path | None = None) -> list[str]:
    if path is None:
        path = _POLICIES_DIR / "forbidden_paths.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("paths", [])


def load_token_lexicon(path: Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        path = _POLICIES_DIR / "token_legal_lexicon.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("prohibited_terms", [])


def load_failure_taxonomy(path: Path | None = None) -> dict[str, dict[str, str]]:
    if path is None:
        path = _POLICIES_DIR / "failure_taxonomy.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("codes", {})
