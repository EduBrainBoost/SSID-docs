/**
 * Remark plugin: prefix internal absolute links with the configured base path.
 *
 * In Astro / Starlight, Markdown link destinations like `/faq/general/`
 * are NOT automatically prefixed with `base` from astro.config.mjs.
 * This plugin rewrites every root-absolute link (`/...`) that is not
 * already prefixed and is not an external URL, so generated `href`
 * attributes carry the correct `/SSID-docs/...` prefix in production
 * while staying root-relative (`/...`) in local dev (base = '/').
 */
import { visit } from 'unist-util-visit';

const base = process.env.CI ? '/SSID-docs' : '';

export default function remarkBasePath() {
  return (tree) => {
    visit(tree, 'link', (node) => {
      if (
        typeof node.url === 'string' &&
        node.url.startsWith('/') &&
        !node.url.startsWith('//') &&             // not protocol-relative
        !node.url.startsWith(`${base}/`) &&        // not already prefixed
        base.length > 0                            // only rewrite in CI
      ) {
        node.url = base + node.url;
      }
    });
  };
}
