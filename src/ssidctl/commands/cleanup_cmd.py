"""ssidctl cleanup-runs — move expired run directories to state/runs/stale/.

Retention policy is read from policies/retention_policy.yaml.
Only run directories matching RUN-* or ISO-timestamp patterns are processed.
WORM-protected and evidence-referenced runs are never moved.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ssidctl.config import EMSConfig

# Path to the retention policy — tests may patch this via monkeypatch or patch()
_POLICY_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "policies" / "retention_policy.yaml"
)  # noqa: E501

# Patterns that identify a run directory by name
_RUN_PATTERNS = [
    re.compile(r"^RUN-\d{8}T\d{6}Z"),  # RUN-20260307T110650Z-...
    re.compile(r"^RUN-[A-Z]"),  # RUN-MC-P0-FULL-001, etc.
    re.compile(r"^\d{8}T\d{6}Z$"),  # 20260306T210000Z
]

# ISO timestamp extractors
_TS_PATTERN = re.compile(r"(\d{8})T(\d{6})Z")

# Directories/files that are never run dirs
_SKIP_NAMES = {"evidence", "stale", "export"}


def _is_run_dir(name: str) -> bool:
    """Return True if the entry name looks like a run directory."""
    if name in _SKIP_NAMES:
        return False
    # File extensions → not a dir name we care about
    if "." in name and not name.startswith("RUN-"):
        return False
    return any(pat.match(name) for pat in _RUN_PATTERNS)


def _extract_timestamp(name: str) -> datetime | None:
    """Extract a UTC datetime from a run directory name, or None if not parseable."""
    m = _TS_PATTERN.search(name)
    if not m:
        return None
    date_str, time_str = m.group(1), m.group(2)
    try:
        return datetime(
            int(date_str[:4]),
            int(date_str[4:6]),
            int(date_str[6:8]),
            int(time_str[:2]),
            int(time_str[2:4]),
            int(time_str[4:6]),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def _has_worm_marker(path: Path) -> bool:
    """Return True if the run directory contains a WORM/SEALED/.worm marker."""
    return any((path / marker).exists() for marker in ("SEALED", "WORM", ".worm"))


def _load_retention_days(tier: str) -> int:
    """Load retention_days for the given tier from the retention policy YAML."""
    if not _POLICY_PATH.exists():
        return 30  # safe default
    policy = yaml.safe_load(_POLICY_PATH.read_text(encoding="utf-8"))
    tier_cfg = policy.get("tiers", {}).get(tier, {})
    return int(tier_cfg.get("retention_days", 30))


def _classify_candidates(
    runs_dir: Path,
    evidence_dir: Path,
    retention_days: int,
    now: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify all entries in runs_dir into expired / protected / skipped.

    Returns (expired, protected, skipped) where each item is a dict with at
    least "name" and optionally "reason".
    """
    expired: list[dict[str, Any]] = []
    protected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    evidence_runs = evidence_dir / "runs"

    for entry in sorted(runs_dir.iterdir()):
        name = entry.name

        # Skip non-directories
        if not entry.is_dir():
            skipped.append({"name": name, "reason": "not a directory"})
            continue

        # Skip non-run directories
        if not _is_run_dir(name):
            skipped.append({"name": name, "reason": "not a run directory"})
            continue

        # WORM protection
        if _has_worm_marker(entry):
            protected.append({"name": name, "reason": "WORM marker present"})
            continue

        # Evidence reference protection
        if evidence_runs.is_dir() and (evidence_runs / name).exists():
            protected.append({"name": name, "reason": "referenced in evidence"})
            continue

        # Timestamp-based expiry
        ts = _extract_timestamp(name)
        if ts is None:
            # No timestamp → can't determine age → skip
            skipped.append({"name": name, "reason": "no timestamp in name"})
            continue

        age_days = (now - ts).days
        if age_days > retention_days:
            expired.append({"name": name, "age_days": age_days, "path": entry})
        else:
            skipped.append(
                {"name": name, "reason": f"within retention ({age_days}d < {retention_days}d)"}
            )  # noqa: E501

    return expired, protected, skipped


def _write_manifest_entry(manifest_path: Path, entry: dict[str, Any]) -> None:
    """Append a JSON line to the cleanup manifest."""
    record = {k: v for k, v in entry.items() if k != "path"}
    record["cleaned_at"] = datetime.now(tz=UTC).isoformat()
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def cmd_cleanup_runs(args: argparse.Namespace, config: EMSConfig) -> int:
    """Main entry point for ssidctl cleanup-runs."""
    tier = getattr(args, "tier", "short_term")
    execute = getattr(args, "execute", False)

    retention_days = _load_retention_days(tier)

    runs_dir = config.paths.state_dir / "runs"
    evidence_dir = config.paths.evidence_dir

    if not runs_dir.exists():
        return 0

    now = datetime.now(tz=UTC)
    expired, protected, skipped = _classify_candidates(runs_dir, evidence_dir, retention_days, now)

    stale_dir = runs_dir / "stale"
    manifest_path = stale_dir / "cleanup_manifest.jsonl"

    if not execute:
        # Dry-run: just report
        print(f"[dry-run] Tier: {tier}, retention: {retention_days}d")
        print(f"  Expired: {len(expired)}")
        print(f"  Protected: {len(protected)}")
        print(f"  Skipped: {len(skipped)}")
        for item in expired:
            print(f"  WOULD MOVE: {item['name']} (age: {item['age_days']}d)")
        return 0

    # Execute: move expired runs to stale/
    stale_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for item in expired:
        src: Path = item["path"]
        dst = stale_dir / item["name"]
        shutil.move(str(src), str(dst))
        _write_manifest_entry(manifest_path, item)
        moved += 1

    print(f"[cleanup-runs] Moved {moved} run(s) to stale/ (tier={tier})")
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("cleanup-runs", help="Move expired run directories to stale/")
    parser.add_argument("--execute", action="store_true", help="Actually move (default: dry-run)")
    parser.add_argument(
        "--tier", default="short_term", help="Retention tier (default: short_term)"
    )  # noqa: E501
    parser.set_defaults(func=cmd_cleanup_runs)
