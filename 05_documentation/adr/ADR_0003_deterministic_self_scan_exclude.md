# ADR-0003: Deterministic Self-Scan Exclusion in docs-ci

## Status
Accepted

## Context
The CI workflow file contains scan-rule literals that match its own content when
grep includes YAML files in the search scope. PR #6 mitigated this with pipe
filters, but pipe-level filtering is post-read and regex-based, which is
non-deterministic (dot in path matches any character in regex mode).

## Decision
Add `--exclude="$SELF"` to all three `grep -rn` scan blocks (secret-scan,
absolute-path-leak, private-repo-reference) so the workflow file is never
opened by grep. Change the existing pipe filter from `grep -v` (regex) to
`grep -vF` (fixed string) as belt-and-suspenders fallback.

## Consequences
- Self-match false positives are eliminated at the file-system level.
- The existing pipe filter remains as defense-in-depth with fixed-string mode.
- No policy changes, no pattern changes, no new files beyond this ADR.
