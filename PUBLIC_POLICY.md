# SSID-docs Public Content Policy

## Purpose
This document defines what may and must not be committed to the SSID-docs repository.
SSID-docs is a **public** repository. Every file is world-readable.

## Single Source of Public Truth
- **Only SSID-open-core** is an allowed source for automated content ingestion.
- The private **SSID** repository must **never** be used as an automated source.
- No mirroring, bulk-copy, or sync-all operations from any private repo.

## Allowed Content

| Category | Examples |
|----------|---------|
| Documentation pages | `.mdx`, `.md` files in `src/content/docs/` |
| Theme/styling | CSS, SVG assets |
| Build config | `astro.config.mjs`, `tsconfig.json`, `package.json` |
| CI/CD workflows | `.github/workflows/*.yml` |
| Tooling (public) | `tools/ingest.mjs` (allowlist-based, no private access) |
| Tests | `tests/*.mjs` |
| Policy docs | This file, `SECURITY.md`, `LICENSE`, `CODEOWNERS` |

## Denied Content (hard block)

### File types — never commit
- `.pem`, `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`
- `.env`, `.env.*` (except `.env.example` with no real values)

### Path patterns — never create
- `02_audit_logging/**` (SSID-internal audit structure)
- `**/worm/**` (WORM log structure)
- `**/registry/*internal*` (internal task registry)
- `**/*credential*`, `**/*secret*` (credential files)

### Content patterns — never include in any file
- Absolute local paths: `<WINDOWS_HOME_PATH>`, `/home/.../<PROJECT>`
- Private keys, API keys, tokens, passwords
- GitHub personal access tokens (`ghp_*`, `gho_*`)
- References to private SSID repo internals

## Enforcement Gates (CI)

| Gate | Job | What it checks |
|------|-----|---------------|
| **Build** | `build` | Type check + Astro build + test suite |
| **Secret Scan** | `secret-scan` | Credential patterns in source files |
| **File Type Deny** | `denylist-gate` | Forbidden extensions (.pem, .key, etc.) |
| **Path Deny** | `denylist-gate` | SSID-internal path structures |
| **Absolute Path Leak** | `denylist-gate` | Local filesystem paths in content |
| **Private Repo Ref** | `denylist-gate` | Sync/mirror/clone references to private SSID |

All gates must PASS before a PR can be merged. No overrides.

## Ingest Rules (`tools/ingest.mjs`)

- Source: **SSID-open-core only** (validated by `validateSourceIsPublic()`)
- Allowlist: Only `docs/`, `policies/`, `README.md`, `LICENSE`, `SECURITY.md`
- Blocklist: Credentials, keys, internal paths, WORM, audit logs
- Secret scan: Every file content-scanned before indexing
- Absolute path scan: Blocks files containing local filesystem paths
- Output: Deterministic JSON index (no LLM, no network calls)

## Review Process

1. All changes via PR (branch protection enforced)
2. CODEOWNERS auto-requested
3. CI gates must all pass
4. Manual content review for sensitive architectural details
5. Merge via squash (clean history)
