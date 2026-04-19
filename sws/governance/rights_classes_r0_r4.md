# SWS Rights Classes R0–R4 — Governance

Canonical rights classification used by every SWS ingest/analyze/rebuild/publish path.
Enforced by `SSID-EMS/portal/backend/core/sws/rights_gate.py` and the pipeline
stage `rights_check`.

## Classes

| Class | Name | Examples | Allowed Actions |
|---|---|---|---|
| **R0** | Own upload / own-licensed | User uploads their own recording; fully owned IP | ingest, analyze, rebuild, publish, distribute |
| **R1** | Platform-licensed with proof | Stock footage with valid license, platform API grant with receipt | ingest, analyze, rebuild, publish, distribute |
| **R2** | Fair-use / transformative | Academic commentary, parody, critique with transformative intent | ingest, analyze, rebuild (NOT publish, NOT distribute) |
| **R3** | Restricted — analysis only | Competitor videos ingested for structural analysis, no derivative | ingest, analyze |
| **R4** | Prohibited | Content that is explicitly blocked (takedowns, NSFW, illegal) | — |

## Hard Constraints

- `allow_1to1_copy = false` in every `rebuild_blueprint.replacement_policy`. Replacement references must never point at the original source file.
- A job must be classified before any analyze stage runs. `rights_check` is the first stage in the analyze DAG.
- R3 and R2 jobs MAY NOT produce a `render_output_manifest` with `status=succeeded` outside of an internal environment; the QA Engine blocks the promotion to a publish bundle.
- R4 jobs are denied at ingest. The rights_manifest records the denial with `allowed=false` and a `reason` string.

## Evidence Requirements

Every rights decision must carry at least one evidence record:

| Kind | Required for |
|---|---|
| `own_upload_declaration` | R0 |
| `license_proof` | R0 (if licensed asset), R1 |
| `platform_api_grant` | R1 |
| `fair_use_analysis` | R2 |
| `rejection_reason` | R4 (and any denied R3 publish attempts) |

Evidence records are embedded in `rights_manifest.evidence[]` per
`rights_manifest.schema.json`.

## Policy Version & Append-Only Log

- Decisions include `policy_version` so old jobs remain interpretable when the policy evolves.
- Every decision is appended to `rights_decisions.jsonl` (per-lane) via `gate_action(log_path=...)`.
- Decisions are immutable; an override produces a new entry with `policy_version` bumped, not a mutation of the original.

## Review

- R1 licenses expire — the QA Engine flags blueprints whose license evidence has passed its expiry.
- Quarterly governance review (LANE_E V1.5 deliverable) verifies the decision log against the schema and scans for R3/R4 decisions that produced downstream artifacts.
