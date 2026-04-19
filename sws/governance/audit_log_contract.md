# SWS Audit Log Contract

Enforced by `SSID-EMS/portal/backend/core/sws/audit_log.py`.

## Shape

`audit_log.jsonl` is an append-only JSONL file. Each line is canonical JSON
(sorted keys, no extra whitespace) with the following fields:

| Field | Type | Note |
|---|---|---|
| `event_type` | string | e.g. `rights_decision`, `retention_purge`, `rbac_deny`, `wave_open`, `wave_close` |
| `actor` | string | RBAC role or system component name |
| `subject` | string | `job_id` / `attempt_id` / `blueprint_id` / "global" |
| `payload` | object | domain-specific data (free shape) |
| `ts` | string | ISO-8601 UTC |
| `prev_hash` | string (hex64) | sha256 of the previous entry's canonical_bytes |
| `self_hash` | string (hex64) | sha256 of this entry's canonical_bytes |

The first entry in a file has `prev_hash = "0" * 64`.

## Invariants

1. **Append-only**: lines are never rewritten. Correcting a mistake produces a new compensating entry.
2. **Canonical serialisation**: `json.dumps(sort_keys=True, separators=(",",":"))` on a fixed field set. Whitespace drift breaks the chain.
3. **Hash chain**: `self_hash = sha256(canonical_bytes(without self_hash))`; `prev_hash` of line N+1 equals `self_hash` of line N.
4. **Verification**: `AuditLog.verify_chain()` recomputes the chain. Any mismatch returns `(False, line_number, reason)`.

## Canonical Bytes

Canonical bytes include exactly: `event_type`, `actor`, `subject`, `payload`, `ts`, `prev_hash`.
The `self_hash` field is excluded from the bytes that produce it.

## Producers

| Producer | event_type(s) |
|---|---|
| `rights_gate.gate_action` | `rights_decision` (per call; also written separately to `rights_decisions.jsonl`) |
| `retention_scheduler` | `retention_purge`, `retention_extend` |
| `rbac.check` | `rbac_deny` (only on failure) |
| `gate_runner_wave_NNN` | `wave_open`, `wave_close` |
| `analyze_spine` / `rebuild_spine` | (use `job_events.jsonl` per job; audit log only receives wave-scope rollups) |

## Retention Class

`audit_log.jsonl` has retention_class `audit_permanent` — never deleted.
Rotation produces a new file `audit_log.<YYYYMMDD>.jsonl` with the previous
chain's last `self_hash` becoming the new file's first `prev_hash`.

## Read Surface

Only the Governor role may call `audit.verify_chain`. Operators / producers
may call `audit.read` for browsing but cannot mutate.
