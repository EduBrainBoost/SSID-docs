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
Add a **Verify base path** step immediately after `pnpm build`.

**v1 (initial, weak):** Used `grep -rl '/SSID-docs/'` which only checks for
substring presence anywhere in HTML files. This can false-pass if `/SSID-docs/`
appears in text content but real `href`/`src` attributes use root-absolute paths
without the prefix.

**v2 (hardened):** Validates actual `href` and `src` attribute values in
generated HTML:

```yaml
- name: Verify base path (/SSID-docs) in href/src attributes
  run: |
    # Extract href/src attribute values from dist/index.html
    # FAIL if any root-absolute URL lacks /SSID-docs/ prefix
    BAD_URLS=$(grep -oP '(?:href|src)="/(?!SSID-docs/)[^"]*"' dist/index.html || true)
    if [ -n "$BAD_URLS" ]; then
      echo "FAIL: root-absolute URLs without /SSID-docs/ prefix"
      exit 1
    fi
    # Verify at least one /SSID-docs/ href/src exists
    GOOD_COUNT=$(grep -cP '(?:href|src)="/SSID-docs/' dist/index.html || echo 0)
    if [ "$GOOD_COUNT" -eq 0 ]; then exit 1; fi
    # Repeat for a second HTML file
    SECOND=$(find dist -name "index.html" -not -path "dist/index.html" | head -1)
    if [ -n "$SECOND" ]; then
      BAD2=$(grep -oP '(?:href|src)="/(?!SSID-docs/)[^"]*"' "$SECOND" || true)
      if [ -n "$BAD2" ]; then exit 1; fi
    fi
    echo "PASS: All href/src attributes use /SSID-docs/ base path"
```

This step exits 1 and blocks deployment if a future change breaks the base path.

### src/remark-base-path.mjs (v3 — content link fix)

The v2 verify step correctly caught a deeper issue: Markdown/MDX content links
like `[text](/faq/token-disambiguation)` are NOT automatically prefixed with the
Astro `base` path. Starlight renders them as `href="/faq/token-disambiguation"`
instead of `href="/SSID-docs/faq/token-disambiguation"`, breaking navigation on
GitHub Pages.

**Fix:** A zero-dependency remark plugin (`src/remark-base-path.mjs`) walks the
MDAST tree and prefixes every root-absolute link with `/SSID-docs` when
`CI=true`. In local dev (`CI` unset), links stay unchanged.

```js
// astro.config.mjs
import remarkBasePath from './src/remark-base-path.mjs';

export default defineConfig({
  markdown: { remarkPlugins: [remarkBasePath] },
  // ...
});
```

This ensures all internal content links carry the correct base path in
production builds without requiring content authors to hardcode `/SSID-docs/`.

## Consequences
- GitHub Pages deployment always uses `/SSID-docs` as base path.
- Local dev workflow is unaffected.
- Any future regression in base path is caught before artifact upload.
- The verify step validates real URL attributes, not just string presence.
- False-pass scenarios from v1 are eliminated.
- Content authors can use root-absolute links (`/faq/...`) without worrying
  about the base path — the remark plugin handles prefixing in CI.

## References
- PR #43: health check path fix (introduced regression)
- PR #44: base path guard + hardened verify step
- PR #45: remark plugin for content link prefixing
- Commit: `1105787`
