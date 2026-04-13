import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://edubrainboost.github.io',
  base: '/SSID-docs/',
  server: { port: 4331 },
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
            { label: 'Root-24 Details', slug: 'architecture/root24' },
            { label: '24x16 Matrix', slug: 'architecture/matrix' },
            { label: 'Shards & Hybrid Charts', slug: 'architecture/shards' },
            { label: 'Deterministic Artifacts', slug: 'architecture/artifacts' },
            { label: 'EMS Architecture', slug: 'architecture/ems' },
            { label: 'Open-Core Model', slug: 'architecture/open-core' },
            { label: 'Post-Quantum Crypto', slug: 'architecture/post-quantum' },
          ],
        },
        {
          label: 'Identity',
          items: [
            { label: 'DID Method', slug: 'identity/did-method' },
            { label: 'VC Lifecycle', slug: 'identity/vc-lifecycle' },
          ],
        },
        {
          label: 'Governance',
          items: [
            { label: 'PR-Only Workflow', slug: 'governance/pr-only' },
            { label: 'Evidence & WORM', slug: 'governance/evidence' },
            { label: 'Policy Gates', slug: 'governance/policy-gates' },
            { label: 'Guard Rails', slug: 'governance/guards' },
            { label: 'DAO Governance', slug: 'governance/dao' },
            { label: 'Incident Response & DR', slug: 'governance/incident-response' },
            { label: 'Runbooks', slug: 'governance/runbooks' },
            { label: 'Secrets Management', slug: 'governance/secrets-management' },
            { label: 'Vault Transit', slug: 'governance/secrets-vault-transit' },
            { label: 'Cloud KMS', slug: 'governance/secrets-cloud-kms' },
          ],
        },
        {
          label: 'Compliance',
          items: [
            { label: 'DSGVO / GDPR', slug: 'compliance/gdpr' },
            { label: 'eIDAS', slug: 'compliance/eidas' },
            { label: 'MiCA Positioning', slug: 'compliance/mica' },
            { label: 'Audit Framework', slug: 'compliance/audit-framework' },
            { label: 'Post-Quantum Migration', slug: 'compliance/post-quantum-migration' },
            { label: 'Supply-Chain Security', slug: 'compliance/supply-chain' },
            { label: 'Supply-Chain: SBOM', slug: 'compliance/supply-chain-sbom' },
            { label: 'Supply-Chain: SLSA', slug: 'compliance/supply-chain-slsa' },
            { label: 'Supply-Chain: Sigstore', slug: 'compliance/supply-chain-sigstore' },
            { label: 'Supply-Chain: Reproducible Builds', slug: 'compliance/supply-chain-reproducible-builds' },
          ],
        },
        {
          label: 'Tooling',
          items: [
            { label: 'Dispatcher Workflow', slug: 'tooling/dispatcher' },
            { label: 'Agent Roles', slug: 'tooling/agents' },
            { label: 'Mission Control (EMS)', slug: 'tooling/mission-control' },
            { label: 'Health Checks', slug: 'tooling/health-checks' },
            { label: 'Authentication', slug: 'tooling/authentication' },
            { label: 'Autopilot', slug: 'tooling/autopilot' },
            { label: 'Local Stack', slug: 'tooling/local-stack' },
            { label: 'Observability', slug: 'tooling/observability' },
            { label: 'Observability: OpenTelemetry', slug: 'tooling/observability-otel' },
            { label: 'Observability: Dashboards', slug: 'tooling/observability-dashboards' },
            { label: 'Observability: SLOs', slug: 'tooling/observability-slos' },
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
          label: 'Developer',
          items: [
            { label: 'Getting Started', slug: 'developer/getting-started' },
            { label: 'Quickstart Guide', slug: 'guides/quickstart' },
          ],
        },
        {
          label: 'Operations',
          items: [
            { label: 'Local Stack Setup', slug: 'operations/local-stack' },
          ],
        },
        {
          label: 'Research',
          items: [
            { label: 'Permissionless Crypto Assets', slug: 'research/permissionless-crypto-assets-2026-03' },
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
