"""Attack Surface Mapper — static analysis of FastAPI router endpoints.

Scans ``portal/backend/routers/`` for route decorators and dependency
injection patterns to classify each endpoint as authenticated or
unauthenticated, and to identify HTTP methods and input types.

Uses only stdlib (pathlib, re, json).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AttackSurfaceMapper:
    """Map the attack surface of the portal backend routers."""

    # Regex patterns ---------------------------------------------------
    _ROUTE_RE = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*\"([^\"]+)\"")
    _FUNC_RE = re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(")
    _AUTH_PATTERNS: tuple[str, ...] = (
        "require_capability",
        "require_permission",
        "get_current_identity",
        "Depends(",
    )
    _INPUT_PATTERNS: dict[str, re.Pattern[str]] = {
        "path_param": re.compile(r"\{(\w+)\}"),
        "query_param": re.compile(r":\s*(?:Annotated\[)?(?:str|int|float|bool|Optional)"),
        "body_model": re.compile(
            r":\s*(?:Annotated\[)?(\w+Body|\w+Request|\w+Create|\w+Update|\w+Payload)"
        ),  # noqa: E501
        "request_object": re.compile(r"request\s*:\s*Request"),
    }

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)
        self.routers_dir = self.repo_root / "portal" / "backend" / "routers"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def map_surface(self, *, timestamp: str | None = None) -> dict[str, Any]:
        """Return a full attack-surface report.

        Parameters
        ----------
        timestamp:
            ISO-8601 override for deterministic output.
        """
        ts = timestamp or datetime.now(UTC).isoformat()

        endpoints: list[dict[str, Any]] = []
        if self.routers_dir.is_dir():
            for py_file in sorted(self.routers_dir.glob("*.py")):
                if py_file.name.startswith("__"):
                    continue
                endpoints.extend(self._scan_router(py_file))

        # Summary statistics
        total = len(endpoints)
        authenticated = sum(1 for e in endpoints if e["authenticated"])
        unauthenticated = total - authenticated
        methods_summary: dict[str, int] = {}
        for ep in endpoints:
            m = ep["method"]
            methods_summary[m] = methods_summary.get(m, 0) + 1

        return {
            "attack_surface_report": {
                "timestamp": ts,
                "routers_dir": str(self.routers_dir),
                "summary": {
                    "total_endpoints": total,
                    "authenticated": authenticated,
                    "unauthenticated": unauthenticated,
                    "methods": methods_summary,
                },
                "endpoints": endpoints,
                "risk_findings": self._compute_risk_findings(endpoints),
            }
        }

    # ------------------------------------------------------------------
    # internal scanning
    # ------------------------------------------------------------------

    def _scan_router(self, path: Path) -> list[dict[str, Any]]:
        """Parse a single router file and return endpoint descriptors."""
        endpoints: list[dict[str, Any]] = []
        lines = path.read_text(encoding="utf-8").splitlines()
        module_name = path.stem

        i = 0
        while i < len(lines):
            match = self._ROUTE_RE.search(lines[i])
            if match:
                method = match.group(1).upper()
                route_path = match.group(2)

                # Collect the function signature (may span multiple lines)
                func_name = ""
                func_block_lines: list[str] = []
                j = i + 1
                # Find the def line
                while j < len(lines) and j < i + 15:
                    func_match = self._FUNC_RE.search(lines[j])
                    if func_match:
                        func_name = func_match.group(1)
                        # Grab up to closing paren
                        k = j
                        while k < len(lines) and k < j + 20:
                            func_block_lines.append(lines[k])
                            if "):" in lines[k] or ") ->" in lines[k]:
                                break
                            k += 1
                        break
                    j += 1

                func_block = "\n".join(func_block_lines)
                authenticated = self._is_authenticated(func_block)
                input_types = self._detect_input_types(route_path, func_block)
                path_params = self._INPUT_PATTERNS["path_param"].findall(route_path)

                endpoints.append(
                    {
                        "module": module_name,
                        "method": method,
                        "path": route_path,
                        "function": func_name,
                        "authenticated": authenticated,
                        "input_types": input_types,
                        "path_params": path_params,
                    }
                )
            i += 1

        return endpoints

    def _is_authenticated(self, func_block: str) -> bool:
        """Heuristic: does the function signature reference auth deps?"""
        return any(pattern in func_block for pattern in self._AUTH_PATTERNS)

    def _detect_input_types(self, route_path: str, func_block: str) -> list[str]:
        """Classify input vectors present in the endpoint."""
        types: list[str] = []
        if self._INPUT_PATTERNS["path_param"].search(route_path):
            types.append("path_parameter")
        if self._INPUT_PATTERNS["body_model"].search(func_block):
            types.append("request_body")
        if self._INPUT_PATTERNS["request_object"].search(func_block):
            types.append("request_object")
        if self._INPUT_PATTERNS["query_param"].search(func_block):
            types.append("query_parameter")
        return types

    # ------------------------------------------------------------------
    # risk findings
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_risk_findings(
        endpoints: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        # 1) Unauthenticated POST/PUT/PATCH/DELETE endpoints
        for ep in endpoints:
            if not ep["authenticated"] and ep["method"] in (
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            ):
                findings.append(
                    {
                        "risk": "high",
                        "category": "unauthenticated_write",
                        "endpoint": f"{ep['method']} {ep['path']}",
                        "module": ep["module"],
                        "detail": (
                            "Write endpoint without detected authentication "
                            "dependency — verify auth is applied via middleware "
                            "or parent router."
                        ),
                    }
                )

        # 2) Unauthenticated GET endpoints (lower risk, still notable)
        for ep in endpoints:
            if not ep["authenticated"] and ep["method"] == "GET":
                findings.append(
                    {
                        "risk": "low",
                        "category": "unauthenticated_read",
                        "endpoint": f"{ep['method']} {ep['path']}",
                        "module": ep["module"],
                        "detail": (
                            "Read endpoint without detected authentication — "
                            "verify data exposure is intentional."
                        ),
                    }
                )

        # 3) Endpoints accepting path params (injection surface)
        for ep in endpoints:
            if ep["path_params"]:
                findings.append(
                    {
                        "risk": "medium",
                        "category": "path_parameter_injection",
                        "endpoint": f"{ep['method']} {ep['path']}",
                        "module": ep["module"],
                        "detail": (
                            f"Path parameters {ep['path_params']} — ensure "
                            "proper validation and sanitization."
                        ),
                    }
                )

        return findings
