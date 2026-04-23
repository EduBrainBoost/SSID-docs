"""ssidctl public-export — sanitized artifact export to open-core."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from ssidctl.config import EMSConfig
from ssidctl.core.timeutil import utcnow_iso


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "public-export",
        help="Export sanitized artifacts from SSID to SSID-open-core",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without acting",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Path to opencore_export_policy.yaml (auto-detected if omitted)",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Path to SSID-open-core repo (auto-detected if omitted)",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create a PR in open-core after export",
    )
    parser.set_defaults(func=cmd_public_export)


def cmd_public_export(args: argparse.Namespace, config: EMSConfig) -> int:
    from ssidctl.services.export_pipeline import ExportPipeline

    source_repo = config.paths.ssid_repo

    # Locate policy file
    policy_path = args.policy
    if policy_path is None:
        policy_path = source_repo / "16_codex" / "opencore_export_policy.yaml"
    if not policy_path.exists():
        print(f"Error: export policy not found: {policy_path}", file=sys.stderr)
        return 1

    # Determine staging dir
    staging_dir = Path(tempfile.mkdtemp(prefix="ssid-export-"))

    pipeline = ExportPipeline(
        source_repo=source_repo,
        policy_path=policy_path,
        staging_dir=staging_dir,
    )

    print(f"Source: {source_repo}")
    print(f"Policy: {policy_path}")
    if args.dry_run:
        print("Mode: DRY RUN")
    print()

    result = pipeline.run(dry_run=args.dry_run)

    # Print summary
    print(f"Scanned:        {result.total_files} files")
    print(f"Exported:       {result.exported_files} files")
    print(f"Denied (glob):  {len(result.denied)} files")
    print(f"Blocked (secret): {len(result.secret_blocked)} files")
    print()

    if result.denied:
        print("Denied paths:")
        for p in result.denied[:20]:
            print(f"  - {p}")
        if len(result.denied) > 20:
            print(f"  ... and {len(result.denied) - 20} more")
        print()

    if result.secret_blocked:
        print("Secret-blocked paths:")
        for p in result.secret_blocked[:20]:
            print(f"  - {p}")
        if len(result.secret_blocked) > 20:
            print(f"  ... and {len(result.secret_blocked) - 20} more")
        print()

    if result.entries:
        print("Exported files:")
        for entry in result.entries[:30]:
            marker = " [sanitized]" if entry.sanitized else ""
            print(f"  {entry.rel_path}{marker}")
        if len(result.entries) > 30:
            print(f"  ... and {len(result.entries) - 30} more")
        print()

    # Write manifest
    manifest_dir = config.paths.ems_repo / "runs"
    manifest_path = manifest_dir / f"export-{utcnow_iso().replace(':', '-')}.json"
    pipeline.write_manifest(result, manifest_path)
    print(f"Manifest: {manifest_path}")

    if args.dry_run:
        print("\nDry run complete — no files were copied.")
        return 0

    # Optionally create PR
    if args.create_pr:
        target_repo = args.target
        if target_repo is None:
            # Convention: sibling directory to SSID
            target_repo = source_repo.parent / "SSID-open-core"

        if not target_repo.exists():
            print(f"Error: target repo not found: {target_repo}", file=sys.stderr)
            return 1

        return _create_pr(staging_dir, target_repo)

    print(f"\nStaged files at: {staging_dir}")
    print("Use --create-pr to push to SSID-open-core.")
    return 0


def _create_pr(staging_dir: Path, target_repo: Path) -> int:
    """Copy staged files to open-core and create a PR."""
    import shutil

    timestamp = utcnow_iso().replace(":", "-")
    branch = f"export/{timestamp}"

    # Create branch in target repo
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=str(target_repo),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"Error creating branch: {exc}", file=sys.stderr)
        return 1

    # Copy staged files to target
    for src in staging_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(staging_dir)
        dest = target_repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    # Stage and commit
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(target_repo),
        capture_output=True,
        timeout=30,
    )
    subprocess.run(
        ["git", "commit", "-m", f"export: sanitized update {timestamp}"],
        cwd=str(target_repo),
        capture_output=True,
        timeout=30,
    )

    # Push and create PR
    push_result = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=str(target_repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if push_result.returncode != 0:
        print(f"Push failed: {push_result.stderr}", file=sys.stderr)
        return 1

    pr_result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            f"Export: sanitized update {timestamp}",
            "--body",
            "Automated sanitized export from SSID via `ssidctl public-export`.",
        ],
        cwd=str(target_repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if pr_result.returncode == 0:
        print(f"PR created: {pr_result.stdout.strip()}")
    else:
        print(f"PR creation failed: {pr_result.stderr}", file=sys.stderr)
        return 1

    return 0
