import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkBasePath from './src/remark-base-path.mjs';

// Production (CI=true on GitHub Actions) → /SSID-docs
// Dev / local                            → / (no prefix)
const base = process.env.CI ? '/SSID-docs' : '/';

export default defineConfig({
  site: 'https://edubrainboost.github.io',
  base,
  server: { port: 4331 },
  markdown: {
    remarkPlugins: [remarkBasePath],
  },
  integrations: [
    starlight({
      title: 'SSID',
      description: 'Self-Sovereign Identity Documentation',
      logo: {
        light: './src/assets/ssid-logo-light.svg',
        dark: './src/assets/ssid-logo-dark.svg',
        replacesTitle: false,
      },
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/EduBrainBoost/SSID-open-core',
        },
      ],
      head: [
        {
          tag: 'meta',
          attrs: {
            'http-equiv': 'Content-Security-Policy',
            content: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';",
          },
        },
      ],
      customCss: [
        './src/styles/cyberpunk.css',
      ],
      sidebar: [
        {
          label: 'Overview',
          items: [
            { label: 'What is SSID?', slug: 'overview' },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Root-24 Architecture', slug: 'architecture/roots' },
            { label: '24x16 Matrix', slug: 'architecture/matrix' },
            { label: 'Shards & Hybrid Charts', slug: 'architecture/shards' },
            { label: 'Deterministic Artifacts', slug: 'architecture/artifacts' },
            { label: 'EMS Architecture', slug: 'architecture/ems' },
          ],
        },
        {
          label: 'Governance',
          items: [
            { label: 'PR-Only Workflow', slug: 'governance/pr-only' },
            { label: 'Evidence & WORM', slug: 'governance/evidence' },
            { label: 'Policy Gates', slug: 'governance/policy-gates' },
            { label: 'DAO Governance', slug: 'governance/dao' },
            { label: 'Incident Response & DR', slug: 'governance/incident-response' },
            { label: 'Secrets Management', slug: 'governance/secrets-management' },
          ],
        },
        {
          label: 'Compliance',
          items: [
            { label: 'DSGVO / GDPR', slug: 'compliance/gdpr' },
            { label: 'eIDAS', slug: 'compliance/eidas' },
            { label: 'MiCA Positioning', slug: 'compliance/mica' },
            { label: 'Supply-Chain Security', slug: 'compliance/supply-chain' },
          ],
        },
        {
          label: 'Tooling',
          items: [
            { label: 'Dispatcher Workflow', slug: 'tooling/dispatcher' },
            { label: 'Agent Roles', slug: 'tooling/agents' },
            { label: 'Mission Control (EMS)', slug: 'tooling/mission-control' },
            { label: 'Health Checks', slug: 'tooling/health-checks' },
            { label: 'Observability', slug: 'tooling/observability' },
            { label: 'AI Gateway', slug: 'tooling/ai-gateway' },
          ],
        },
        {
          label: 'Token',
          items: [
            { label: 'Utility & Governance', slug: 'token/utility' },
            { label: 'Non-Custodial Design', slug: 'token/non-custodial' },
            { label: 'Fee Models', slug: 'token/fee-models' },
            { label: 'Token Distribution', slug: 'token/distribution' },
          ],
        },
        {
          label: 'FAQ',
          items: [
            { label: 'General FAQ', slug: 'faq/general' },
            { label: 'Token Disambiguation', slug: 'faq/token-disambiguation' },
          ],
        },
        {
          label: 'Project',
          items: [
            { label: 'Roadmap', slug: 'roadmap' },
            { label: 'Status', slug: 'status' },
            { label: 'Changelog', slug: 'changelog' },
            { label: 'Security & Disclosure', slug: 'security' },
            { label: 'Export Transparency', slug: 'exports' },
          ],
        },
      ],
      defaultLocale: 'root',
      locales: {
        root: { label: 'English', lang: 'en' },
        de: { label: 'Deutsch', lang: 'de' },
      },
    }),
  ],
});
