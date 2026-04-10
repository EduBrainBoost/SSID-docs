/**
 * Remark plugin: prefix internal absolute links with the configured base path.
 *
 * In Astro / Starlight, Markdown link destinations like `/faq/general/`
 * are NOT automatically prefixed with `base` from astro.config.mjs.
 * This plugin rewrites every root-absolute link (`/...`) that is not
 * already prefixed and is not an external URL, so generated `href`
 * attributes carry the correct `/SSID-docs/...` prefix in production
 * while staying root-relative (`/...`) in local dev (base = '/').
 *
 * Zero external dependencies — walks the MDAST tree manually.
 */

const base = process.env.CI ? '/SSID-docs' : '';

function walkTree(node) {
  if (node.type === 'link' && typeof node.url === 'string') {
    if (
      node.url.startsWith('/') &&
      !node.url.startsWith('//') &&
      !node.url.startsWith(`${base}/`) &&
      base.length > 0
    ) {
      node.url = base + node.url;
    }
  }
  if (Array.isArray(node.children)) {
    for (const child of node.children) {
      walkTree(child);
    }
  }
}

export default function remarkBasePath() {
  return (tree) => {
    walkTree(tree);
  };
}
