"""Stack manifest loader and validator."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ManifestError(Exception):
    """Raised when manifest is invalid or missing."""


@dataclass(frozen=True)
class ComponentConfig:
    name: str
    repo: str
    workdir: Path
    managed: bool
    port_preferred: int
    port_candidates: list[int]
    start_template: list[str]
    health_url_template: str
    health_expect_status: int
    depends_on: list[str]


@dataclass(frozen=True)
class StackManifest:
    version: str
    stack_id: str
    github_root: Path
    evidence_root: Path
    components: dict[str, ComponentConfig]


def _parse_component(name: str, raw: dict[str, Any]) -> ComponentConfig:
    port = raw.get("port", {})
    health = raw.get("health", {})
    return ComponentConfig(
        name=name,
        repo=raw.get("repo", ""),
        workdir=Path(raw.get("workdir", ".")),
        managed=raw.get("managed", True),
        port_preferred=port.get("preferred", 0),
        port_candidates=port.get("candidates", []),
        start_template=raw.get("start_template", []),
        health_url_template=health.get("url_template", ""),
        health_expect_status=health.get("expect_status", 200),
        depends_on=raw.get("depends_on", []),
    )


def load_manifest(path: Path) -> StackManifest:
    """Load and validate a local stack manifest YAML."""
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"Invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest must be a YAML mapping, got {type(raw).__name__}")

    if "components" not in raw:
        raise ManifestError("Manifest missing required field: components")

    base = raw.get("base_paths", {})
    components = {}
    for name, comp_raw in raw["components"].items():
        components[name] = _parse_component(name, comp_raw)

    return StackManifest(
        version=raw.get("version", "1.0"),
        stack_id=raw.get("stack_id", "unknown"),
        github_root=Path(base.get("github_root", ".")),
        evidence_root=Path(base.get("evidence_root_default", ".")),
        components=components,
    )


def default_manifest_path() -> Path:
    """Return default manifest path from env or Windows default."""
    env = os.environ.get("SSID_STACK_MANIFEST")
    if env:
        return Path(env)
    return Path(
        r"C:\Users\bibel\SSID-Workspace\SSID-Arbeitsbereich\Github\SSID"
        r"\16_codex\local_stack\local_stack_manifest.yaml"
    )
