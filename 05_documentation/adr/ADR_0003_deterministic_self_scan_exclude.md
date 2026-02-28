# ADR-0003: Deterministic Self-Scan Exclusion in docs-ci

## Status
Accepted

## Context
The `docs_ci.yml` workflow contains pattern literals (`PRIVATE.KEY`, `sk_live_`,
`C:\Users\`, etc.) as scan rules inside `grep -rn` invocations. These scans
include `*.yml`/`*.yaml` files, so the workflow file can match its own rules.

PR #6 added `grep -v "$SELF"` pipe filters to suppress self-matches. This works
in practice but has two weaknesses:

1. **Non-deterministic** — `grep -v` treats `$SELF` as regex (`.` matches any
   character). The path `.github/workflows/docs_ci.yml` contains dots that
   could theoretically match unintended strings.
2. **Post-read filtering** — The file is still opened and matched by `grep -rn`;
   only the output is filtered. A deterministic solution should prevent reading
   the file altogether.

## Decision
Add `--exclude="$SELF"` to all three `grep -rn` scan blocks so the file is
never opened:

- **secret-scan** → Check for secrets
- **denylist-gate** → Absolute path leak scan
- **denylist-gate** → Private repo reference scan

Additionally, change the existing pipe filter from `grep -v "$SELF"` (regex) to
`grep -vF "$SELF"` (fixed string) as belt-and-suspenders fallback.

## Consequences
- Self-match false positives are eliminated at the file-system level.
- The existing `grep -vF` fallback remains as defense-in-depth.
- No policy changes, no pattern changes, no new files beyond this ADR.
