# SSID-docs Ist-/Soll-Analyse

Datum: 2026-04-12
Repo: SSID-docs
Branch: main (fb549df)
Port: 4331 (G-Zone)

## 1. Ist-Zustand

### 1.1 Stack
- Astro 5.18 + Starlight 0.37.6
- pnpm 10, TypeScript 5.9.3
- Custom Cyberpunk-Theme (cyberpunk.css)
- CSP-Header konfiguriert
- Pagefind-Suchindex integriert

### 1.2 Build-Status
- `astro build`: PASS (119 Seiten, 14.73s)
- `node tests/run.mjs`: 4/4 PASS (Structure, Content, Theme, Security)

### 1.3 Content-Inventar (60 MDX/MD-Dateien)

| Sektion        | Dateien | In Sidebar | Orphan |
|----------------|---------|------------|--------|
| architecture/  | 8       | 5          | 3      |
| compliance/    | 9       | 4          | 5      |
| governance/    | 10      | 6          | 4      |
| tooling/       | 12      | 6          | 6      |
| token/         | 4       | 4          | 0      |
| faq/           | 2       | 2          | 0      |
| identity/      | 2       | 0          | 2      |
| developer/     | 1       | 0          | 1      |
| guides/        | 1       | 0          | 1      |
| operations/    | 1       | 0          | 1      |
| research/      | 1       | 0          | 1      |
| Standalone     | 7       | 5          | 0      |
| de/ (I18N)     | 1       | -          | -      |
| **Gesamt**     | **60**  | **32**     | **24** |

### 1.4 Orphan-Dateien (existieren, aber nicht in Sidebar)
- architecture/root24.mdx, open-core.mdx, post-quantum.mdx
- compliance/audit-framework.mdx, post-quantum-migration.mdx, supply-chain-*.mdx (4x)
- developer/getting-started.mdx
- governance/guards.mdx, runbooks.mdx, secrets-cloud-kms.mdx, secrets-vault-transit.mdx
- guides/quickstart.mdx
- identity/did-method.mdx, vc-lifecycle.mdx
- operations/local-stack.md
- research/permissionless-crypto-assets-2026-03.md
- tooling/authentication.mdx, autopilot.mdx, local-stack.mdx
- tooling/observability-dashboards.mdx, observability-otel.mdx, observability-slos.mdx

### 1.5 I18N-Status
- Konfiguriert: root (en), de
- Deutsche Inhalte: nur index.mdx (Platzhalter)
- Abdeckung: 1/60 = 1.7%

### 1.6 Komponenten
- HeroLanding.astro (Splash-Page)
- MatrixGrid.astro (24x16 Matrix-Visualisierung)
- LiveDashboard.astro

### 1.7 Sicherheit
- CSP-Header aktiv
- Security-Tests: keine privaten Repo-Referenzen
- PUBLIC_POLICY.md vorhanden
- env.example.template (keine .env)

## 2. Soll-Bild

### 2.1 Sidebar-Vollstaendigkeit
Alle 60 vorhandenen Content-Dateien MUESSEN in der Sidebar navigierbar sein.
24 Orphan-Dateien werden in die Sidebar-Konfiguration aufgenommen.

### 2.2 Neue Sidebar-Sektionen
- **Identity** (did-method, vc-lifecycle)
- **Developer** (getting-started, quickstart zusammengefuehrt)
- **Operations** (local-stack, runbooks zusammengefuehrt)
- **Research** (eigenstaendig, aber verlinkt)

### 2.3 Sidebar-Erweiterungen bestehender Sektionen
- Architecture: +root24, +open-core, +post-quantum
- Compliance: +audit-framework, +post-quantum-migration, Supply-Chain-Unterseiten als autogenerate
- Governance: +guards, +runbooks, +secrets-cloud-kms, +secrets-vault-transit
- Tooling: +authentication, +autopilot, +local-stack, Observability-Unterseiten als autogenerate

### 2.4 Public-Safe-Kriterium
- Nur Sidebar-Konfiguration und astro.config.mjs werden geaendert
- Kein Inhalt wird geloescht oder ueberschrieben
- Kein neuer Content wird erfunden
- Keine Secrets, keine PII
- Build muss PASS bleiben
- Alle Tests muessen PASS bleiben

## 3. Risiken
- Falsche Slug-Referenz bricht Build
- Autogenerate auf Verzeichnisse mit gemischtem Content kann Sortierung aendern
- I18N-Erweiterung ist out-of-scope (nur Analyse, keine Umsetzung)

## 4. Metriken
- Vorher: 32/60 Seiten in Sidebar (53%)
- Nachher: 56/60 Seiten in Sidebar (93%) — index.mdx und de/ sind keine Sidebar-Eintraege
- Build-Zeit: Referenz 14.73s
- Testabdeckung: 4/4 PASS bleibt Pflicht
