# Contributing to SSID-docs

Thank you for your interest in contributing to the SSID documentation. This document describes the workflow, standards, and rules for contributing.

## Workflow

1. **Fork** the repository on GitHub.
2. **Create a branch** from `main`:
   - Content: `content/<short-name>`
   - Fix: `fix/<short-name>`
3. **Implement** your changes following the standards below.
4. **Test** your changes locally (see Testing section).
5. **Submit a Pull Request** against `main` with a clear description.

## Stack

- **Framework**: Astro + Starlight (SSG)
- **Content format**: MDX
- **Package manager**: pnpm
- **I18N**: Required for all user-facing content

## Testing

```bash
pnpm install
pnpm test
pnpm build
```

Verify that the build completes without errors before submitting a PR.

## Content Guidelines

- All documentation is written in **MDX format**.
- **I18N support is mandatory**: All user-facing content must support internationalization.
- **No system secrets in docs**: Never include credentials, API keys, tokens, or internal infrastructure details.
- **API documentation is generated from OpenAPI specs** — do not write API docs manually. The source of truth is the OpenAPI schema.
- System-level documentation belongs in `16_codex` (SSID main repo), not here.

## Port Rules

This workspace uses **G-ports only**:

| Service    | Port |
|------------|------|
| SSID-docs  | 4331 |

Do **not** use canonical port (4321) — that is reserved for the read-only reference copy.

## Mandatory Rules

- **SAFE-FIX enforced**: All write operations must be additive. No blind overwrites.
- **Non-custodial principle**: Never include PII in documentation.
- **No hardcoded paths**: Use relative paths or configuration variables.
- **ROOT-24-LOCK**: The 24 root folders in the SSID repo are canonical. Documentation must reflect the canonical structure accurately.

## Commit Messages

Use conventional commit format:

```
type(scope): short description

Optional longer description.
```

Types: `feat`, `fix`, `docs`, `content`, `refactor`, `chore`

## Code of Conduct

Be respectful, constructive, and collaborative. Discrimination or harassment of any kind is not tolerated.
