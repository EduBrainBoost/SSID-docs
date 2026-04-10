import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://edubrainboost.github.io',
  base: process.env.NODE_ENV === 'production' ? '/SSID-docs' : '/',
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
            { label: 'Guard System', slug: 'governance/guards' },
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
            { label: 'Autopilot', slug: 'tooling/autopilot' },
            { label: 'Authentication (OIDC/JWT)', slug: 'tooling/authentication' },
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
