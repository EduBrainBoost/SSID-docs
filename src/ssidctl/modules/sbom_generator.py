"""SBOM Generator — produces CycloneDX-compatible Software Bill of Materials.

Scans requirements.txt (Python) and package.json (Node.js) to produce a
deterministic SBOM document.  Uses only stdlib (json, pathlib, hashlib).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SBOMGenerator:
    """Generate a CycloneDX-compatible SBOM from project dependency files."""

    TOOL_NAME = "ssidctl-sbom-generator"
    TOOL_VERSION = "1.0.0"
    SPEC_VERSION = "1.4"
    BOM_FORMAT = "CycloneDX"

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def generate(self, *, timestamp: str | None = None) -> dict[str, Any]:
        """Return a CycloneDX-compatible SBOM dict.

        Parameters
        ----------
        timestamp:
            ISO-8601 timestamp override (useful for deterministic tests).
            If *None*, the current UTC time is used.
        """
        ts = timestamp or datetime.now(UTC).isoformat()

        components: list[dict[str, Any]] = []
        dependencies: list[dict[str, Any]] = []

        # Python deps ---------------------------------------------------
        py_components = self._parse_requirements()
        components.extend(py_components)
        for comp in py_components:
            dependencies.append({"ref": comp["bom-ref"], "dependsOn": []})

        # Node deps -----------------------------------------------------
        node_components = self._parse_package_json()
        components.extend(node_components)
        for comp in node_components:
            dependencies.append({"ref": comp["bom-ref"], "dependsOn": []})

        serial = self._serial_number(ts, components)

        return {
            "bomFormat": self.BOM_FORMAT,
            "specVersion": self.SPEC_VERSION,
            "serialNumber": serial,
            "metadata": {
                "timestamp": ts,
                "tools": [
                    {
                        "name": self.TOOL_NAME,
                        "version": self.TOOL_VERSION,
                    }
                ],
                "component": {
                    "type": "application",
                    "name": self.repo_root.name,
                    "version": "0.0.0",
                },
            },
            "components": components,
            "dependencies": dependencies,
        }

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bom_ref(ecosystem: str, name: str) -> str:
        return f"pkg:{ecosystem}/{name}"

    def _parse_requirements(self) -> list[dict[str, Any]]:
        """Parse *all* requirements.txt files found under repo_root."""
        components: list[dict[str, Any]] = []
        seen: set[str] = set()

        for req_file in sorted(self.repo_root.rglob("requirements.txt")):
            for comp in self._parse_single_requirements(req_file):
                ref = comp["bom-ref"]
                if ref not in seen:
                    seen.add(ref)
                    components.append(comp)
        return components

    def _parse_single_requirements(self, path: Path) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        if not path.is_file():
            return components

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            name, version = self._split_requirement(line)
            ref = self._bom_ref("pypi", name)
            components.append(
                {
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": f"pkg:pypi/{name}@{version}" if version else f"pkg:pypi/{name}",
                    "bom-ref": ref,
                    "ecosystem": "pypi",
                }
            )
        return components

    @staticmethod
    def _split_requirement(line: str) -> tuple[str, str]:
        """Return (package_name, version_spec) from a pip requirement line."""
        # Handle extras like package[extra]>=1.0
        for sep in ("===", "~=", "==", "!=", ">=", "<=", ">", "<"):
            if sep in line:
                idx = line.index(sep)
                name = line[:idx].strip()
                version = line[idx:].strip()
                # strip extras from name
                if "[" in name:
                    name = name[: name.index("[")]
                return name, version
        # no version specifier
        name = line.strip()
        if "[" in name:
            name = name[: name.index("[")]
        return name, ""

    def _parse_package_json(self) -> list[dict[str, Any]]:
        """Parse *all* package.json files found under repo_root."""
        components: list[dict[str, Any]] = []
        seen: set[str] = set()

        for pkg_file in sorted(self.repo_root.rglob("package.json")):
            # Skip node_modules
            if "node_modules" in pkg_file.parts:
                continue
            for comp in self._parse_single_package_json(pkg_file):
                ref = comp["bom-ref"]
                if ref not in seen:
                    seen.add(ref)
                    components.append(comp)
        return components

    def _parse_single_package_json(self, path: Path) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        if not path.is_file():
            return components

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return components

        for section in ("dependencies", "devDependencies"):
            deps = data.get(section, {})
            if not isinstance(deps, dict):
                continue
            for name, version_spec in sorted(deps.items()):
                ref = self._bom_ref("npm", name)
                if any(c["bom-ref"] == ref for c in components):
                    continue
                components.append(
                    {
                        "type": "library",
                        "name": name,
                        "version": str(version_spec),
                        "purl": f"pkg:npm/{name}@{version_spec}",
                        "bom-ref": ref,
                        "ecosystem": "npm",
                    }
                )
        return components

    @staticmethod
    def _serial_number(timestamp: str, components: list[dict]) -> str:
        """Deterministic serial number derived from content hash."""
        h = hashlib.sha256()
        h.update(timestamp.encode())
        for comp in components:
            h.update(comp["bom-ref"].encode())
        return f"urn:uuid:{h.hexdigest()[:32]}"
