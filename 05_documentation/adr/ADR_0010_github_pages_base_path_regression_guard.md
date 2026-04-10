# ADR-0010: GitHub Pages Base Path Regression Guard

## Status
Accepted

## Context
PR #43 (health check base path fix) introduced a regression in `astro.config.mjs`:
`base: '/'` replaced the required `base: '/SSID-docs'`, causing GitHub Pages
to deploy assets and HTML without the `/SSID-docs/` prefix. The site became
unreachable at its canonical URL `https://edubrainboost.github.io/SSID-docs/`.

Two root causes:

1. **No environment-aware base path** — `astro.config.mjs` used a hard-coded
   `base: '/'` instead of differentiating between local dev and CI/production.
2. **No build-time guard** — `pages.yml` had no step to verify the base path
   was correctly applied before uploading the Pages artifact.

## Decision

### astro.config.mjs
Use `process.env.CI` to select the base path at build time:

```js
const base = process.env.CI ? '/SSID-docs' : '/';
```

- `CI=true` is set automatically by GitHub Actions — production builds use `/SSID-docs`.
- Local dev (`CI` unset) uses `/` — no prefix needed for `localhost:4331`.

### .github/workflows/pages.yml
Add a **Verify base path** step immediately after `pnpm build`:

```yaml
- name: Verify base path (/SSID-docs)
  run: |
    COUNT=$(grep -rl '/SSID-docs/' dist/ --include="*.html" 2>/dev/null | wc -l)
    if [ "$COUNT" -eq 0 ]; then
      echo "FAIL: /SSID-docs/ base path missing in dist/*.html"
      exit 1
    fi
    echo "PASS: /SSID-docs/ confirmed in $COUNT HTML file(s)"
```

This step exits 1 and blocks deployment if a future change breaks the base path.

## Consequences
- GitHub Pages deployment always uses `/SSID-docs` as base path.
- Local dev workflow is unaffected.
- Any future regression in base path is caught before artifact upload.
- The verify step serves as a living regression test in CI.

## References
- PR #43: health check path fix (introduced regression)
- PR #44: this fix
- Commit: `1105787`
