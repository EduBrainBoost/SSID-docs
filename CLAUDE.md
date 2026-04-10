# CLAUDE.md — SSID-docs Governance Rules

## Identity

- **Repo**: SSID-docs
- **Primary Branch**: main
- **Purpose**: Public-facing documentation site for the SSID project
- **Scope**: User documentation, guides, generated API reference, and I18N content

## Write Scope

- Documentation content (MDX files)
- Astro/Starlight configuration
- I18N translation files
- Static assets for documentation
- Repository-local automation and quality gates

## Forbidden

- Storing system secrets in docs
- Manual API documentation when the source of truth is OpenAPI
- System-level documentation that belongs in `16_codex` of the main SSID repo
- Placing PII in any documentation content
- Writing outside this repository
- Editing `.git/` directly

## Stack

- Astro + Starlight (SSG)
- MDX content format
- pnpm package manager
- I18N support required for all user-facing content

## Ports

| Service   | G-Port (Workspace) | C-Port (Canonical) |
|-----------|--------------------|--------------------|
| SSID-docs | 4331               | 4321               |

## Rules

- **SAFE-FIX**: Permanent, non-interactive, SHA256-logged write enforcement
- **NON-CUSTODIAL**: No PII in documentation, hash-only references
- **ROOT-24-LOCK**: Documentation must reflect the canonical 24-root structure accurately
- **SOURCE-OF-TRUTH**: API references and cross-repo docs must be validated against source repositories
- **QUALITY-GATES**: Validate MDX syntax, I18N completeness, and internal links before merge
- **LOCAL-FIRST**: build, test, verify, commit, push

## Scope Discipline

- Only do the explicitly assigned task; do not expand scope without approval
- Prefer the narrower scope when the request is ambiguous
- Do not modify other repositories while working in `SSID-docs`

## Verification

- Do not declare completion without `pnpm build` and `pnpm test`
- Validate internal links and I18N completeness for changed docs
- Verify runtime behavior and CSP output when config or routing changes

## Starlight Rules

- Use only `note`, `tip`, `caution`, and `danger` for `Aside`
- Keep MDX valid for Astro/Starlight builds

## Regulatory Language

- Treat the token as utility/governance only
- Avoid investment-style phrasing such as returns, guaranteed profit, or custody implications
- Mark hypothetical stablecoin mappings as hypothetical and not planned
