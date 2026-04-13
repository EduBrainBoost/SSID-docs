---
title: PHASE 2 — SSID-docs Implementation Plan
date: 2026-04-13
status: PLAN_READY_FOR_REVIEW
---

# PHASE 2: SSID-docs Implementation Plan

**Based on:** PHASE1_SYSTEM_ANALYSIS.md  
**Objective:** Close P0/P1 gaps, update sidebar, enhance test coverage, ensure policy compliance.

**Scope:** SSID-docs repo only. No changes to SSID, SSID-EMS, SSID-orchestrator, SSID-open-core.  
**Build Requirement:** `pnpm install && pnpm build && pnpm test` must pass 100%.  
**Policy:** No hard-deny violations, no private content, no false claims.

---

## EXECUTION PHASES

### PHASE 2.A: Sidebar & Config Updates
### PHASE 2.B: New Content Files (P0 Priority)
### PHASE 2.C: Content File Updates
### PHASE 2.D: Test Suite Extensions
### PHASE 2.E: CI Gate Enhancements
### PHASE 2.F: Validation & Verification

---

## PHASE 2.A: SIDEBAR & CONFIG UPDATES

### 2.A.1: Update `astro.config.mjs`

**File:** `astro.config.mjs`  
**Change Type:** Sidebar restructuring + 4 new categories

**Location:** Lines 36–155 (sidebar array)

**Actions:**

1. **Add new top-level categories** (insert after "Architecture" section, before "Identity"):

```javascript
{
  label: 'System Architecture & Integration',
  items: [
    { label: 'Root-24 Architecture', slug: 'architecture/roots' },
    { label: 'Root-24 Details', slug: 'architecture/root24' },
    { label: '5-Repo System Topology', slug: 'architecture/5-repo-topology' },  // NEW
    { label: '24x16 Matrix', slug: 'architecture/matrix' },
    { label: 'Shards & Hybrid Charts', slug: 'architecture/shards' },
    { label: 'System Artifacts', slug: 'architecture/artifacts' },
    { label: 'EMS Architecture', slug: 'architecture/ems' },
    { label: 'Orchestrator Integration', slug: 'architecture/orchestrator-runtime' },  // NEW
    { label: 'Open-Core Model', slug: 'architecture/open-core' },
    { label: 'Post-Quantum Crypto', slug: 'architecture/post-quantum' },
  ],
},
```

2. **Insert new "Operations & Deployment" section** (after "Developer", before "Operations"):

```javascript
{
  label: 'Deployments & Networks',
  items: [
    { label: 'Local Stack Setup', slug: 'deployments/local-stack' },
    { label: 'Port Matrix (Current)', slug: 'deployments/ports-matrix-current' },  // NEW
    { label: 'Testnet Deployment Guide', slug: 'deployments/testnet-guide' },  // NEW
    { label: 'Testnet Addresses & RPC', slug: 'deployments/testnet-addresses' },  // NEW
    { label: 'Mainnet Readiness Roadmap', slug: 'deployments/mainnet-readiness' },  // NEW
    { label: 'Local CI/CD Reproduction', slug: 'deployments/local-cicd' },  // NEW
  ],
},
```

3. **Rename "Tooling" → "Integration & Tools"** and reorganize:

```javascript
{
  label: 'Integration & Tools',
  items: [
    { label: 'EMS Control Plane (CLI)', slug: 'tooling/ems-control-plane' },  // NEW/UPDATED
    { label: 'EMS Portal Walkthrough', slug: 'tooling/ems-portal' },  // NEW
    { label: 'Orchestrator Runtime', slug: 'tooling/orchestrator-runtime' },  // NEW
    { label: 'Orchestrator Dispatch', slug: 'tooling/dispatcher' },  // EXISTING
    { label: 'Agent Roles', slug: 'tooling/agents' },
    { label: 'Health Checks', slug: 'tooling/health-checks' },
    { label: 'Authentication & Sessions', slug: 'tooling/authentication' },
    { label: 'Autopilot', slug: 'tooling/autopilot' },
    { label: 'Observability', slug: 'tooling/observability' },
    { label: 'Observability: OpenTelemetry', slug: 'tooling/observability-otel' },
    { label: 'Observability: Dashboards', slug: 'tooling/observability-dashboards' },
    { label: 'Observability: SLOs', slug: 'tooling/observability-slos' },
    { label: 'AI Gateway', slug: 'tooling/ai-gateway' },
  ],
},
```

4. **Update "Operations" → keep minimal** (operations/local-stack moved to Deployments):

```javascript
{
  label: 'Operations',
  items: [
    { label: 'Troubleshooting Local Stack', slug: 'operations/local-stack-troubleshooting' },  // NEW
  ],
},
```

5. **Add new "System Status" section** (after "FAQ", before "Research"):

```javascript
{
  label: 'System Status & Evidence',
  items: [
    { label: 'Live Dashboard', slug: 'status' },
    { label: 'Testnet Status', slug: 'status/testnet' },  // NEW
    { label: 'Mainnet Status', slug: 'status/mainnet' },  // NEW
    { label: 'Repository Health', slug: 'status/repos' },  // NEW
    { label: 'Public Evidence Export', slug: 'governance/evidence-export' },  // NEW
  ],
},
```

**Expected Line Changes:** +30 lines (new items) in sidebar array.

---

### 2.A.2: Validate astro.config.mjs Syntax

**Action:** Verify astro.config.mjs parses without errors after edits.

```bash
cd SSID-docs && node -c astro.config.mjs
```

**Expected:** No syntax errors.

---

## PHASE 2.B: NEW CONTENT FILES (P0 PRIORITY)

### 2.B.1: `src/content/docs/architecture/5-repo-topology.mdx`

**Frontmatter:**
```yaml
---
title: 5-Repo System Topology
description: How the SSID ecosystem repositories fit together—roles, dependencies, and integration points.
---
```

**Content Outline:**
1. System Overview Diagram (text description for now; can upgrade to Mermaid/SVG later)
2. **SSID** (Private, Core)
   - Role: Platform kernel, ROOT-24 enforcer, SoT source
   - Tech: Python 3.11+, OPA, Git worktrees
   - Status: Operational (Phase 7/8)
   - Access: Private repo
3. **SSID-EMS** (Private, Control Plane)
   - Role: CLI control plane (ssidctl), Portal frontend, Evidence management
   - Tech: Python (FastAPI) + React/Next.js + PM2
   - Status: Operational (Phase 5+)
   - Key Components: 3-plane model (Control/Data/Evidence), WORM logging
4. **SSID-orchestrator** (Private, Runtime)
   - Role: Runtime dispatch engine, workflow execution, session management
   - Tech: Python 3.11+ + Node.js 22+ + React/Vite
   - Status: Operational (Phase 2 testing)
   - Key Components: Dispatch, workflows, session isolation
5. **SSID-open-core** (Public, SDK/API)
   - Role: Public export of 5 roots, safe subset for external use
   - Tech: Python 3.11+, Git export
   - Exported Roots: 03_core, 12_tooling, 16_codex, 23_compliance, 24_meta_orchestration
   - Status: Operational
   - Source: Sanitized export from SSID
6. **SSID-docs** (Public, Documentation)
   - Role: Public documentation, tutorials, architecture, compliance info
   - Tech: Astro 5 + Starlight 0.37, Node.js 22, pnpm
   - Status: Operational (Port 4331 = G-port)
   - Ingest Source: SSID-open-core only

**Dependency Matrix:**
```
SSID (private) 
  ├─→ SSID-EMS (private) [uses Core APIs]
  ├─→ SSID-orchestrator (private) [coordinates with EMS]
  ├─→ SSID-open-core (public) [controlled export]
  │    └─→ SSID-docs (public) [auto-ingest]
  └─→ SSID-docs (manual refs to architecture)
```

**Key Callouts:**
- SSID-docs NEVER pulls from SSID or SSID-EMS directly
- SSID-open-core is the sanitization layer
- Private repos can only be documented by manual sanitization
- PUBLIC_POLICY.md enforces hard boundaries

**Length:** 500–700 words

**Status:** Ready to write in Phase 2.F

---

### 2.B.2: `src/content/docs/deployments/ports-matrix-current.mdx`

**Frontmatter:**
```yaml
---
title: Port Matrix (Current)
description: Correct port mappings for the G workspace (development environment).
---
```

**Content:**
1. **Quick Reference Table:**

| Service | Port | Health URL | Notes |
|---------|------|-----------|-------|
| EMS Portal Frontend | **3100** | http://localhost:3100 | React, TailwindCSS |
| EMS Portal Backend | **8100** | http://localhost:8100/api/health | FastAPI + uvicorn |
| Legacy Website | **3101** | http://localhost:3101 | Placeholder |
| SSID-docs | **4331** | http://localhost:4331 | Astro + Starlight |
| Orchestrator API | **3310** | http://localhost:3310/api | Python dispatch engine |
| Orchestrator Web UI | **5273** | http://localhost:5273 | React/Vite |
| CCT Docs | **3102** | http://localhost:3102 | Placeholder |
| CCT Dashboard | **4332** | http://localhost:4332 | Placeholder |

2. **Workspace Context:**
   - These are **G-ports** (development/workspace ports)
   - Source: `port-policy.md` in workspace
   - For production (C-ports), see Mainnet Readiness guide
   - Verify: `cat ~/.ssid-system/port-matrix.json` in workspace

3. **Port Conflicts:**
   ```bash
   # Check if port is in use
   netstat -ano | findstr :3100  # Windows
   lsof -i :3100                 # macOS/Linux
   ```

4. **CI Reference:**
   - GitHub Actions uses same port matrix in workflow env vars
   - See: `.github/workflows/docs_ci.yml` for validation

5. **Troubleshooting:**
   - **Port already in use:** Kill conflicting process or change VITE_PORT
   - **CORS errors:** Ensure backend has localhost origins whitelisted
   - **Cookie issues:** Use `localhost` not `127.0.0.1`
   - **Missing env vars:** See each repo's `.env.example`

**Length:** 400–500 words

---

### 2.B.3: `src/content/docs/deployments/testnet-guide.mdx`

**Frontmatter:**
```yaml
---
title: Testnet Deployment Guide
description: Deploy and interact with SSID on public testnets (Sepolia, Mumbai).
---
```

**Content:**
1. **Testnet Overview:**
   - Staging environment for public testing
   - Use real testnet ETH (free via faucets)
   - All contracts are on public chains (Sepolia/Mumbai)
   - NOT production; data subject to reset

2. **Testnet Networks:**

| Network | Chain | RPC | Explorer | Faucet |
|---------|-------|-----|----------|--------|
| **Sepolia** | Ethereum Testnet | https://sepolia.infura.io/v3/YOUR_KEY | Etherscan Sepolia | sepoliafaucet.com |
| **Mumbai** | Polygon Testnet | https://rpc-mumbai.maticvigil.com | PolygonScan Mumbai | mumbaifaucet.com |

3. **Smart Contract Addresses (Testnet):**
   - Source: SSID-open-core exports (if available)
   - Sepolia deployment: `0x...` (IdentityCore contract)
   - Mumbai deployment: `0x...` (Identity contract)
   - **Note:** Check SSID-open-core `contracts/` directory for latest addresses

4. **Deploy to Testnet:**
   ```bash
   cd SSID  # or public deployment repo
   npm install
   # Set TESTNET_RPC_URL, PRIVATE_KEY in .env
   npx hardhat deploy --network sepolia
   ```

5. **Verify on Explorer:**
   - Etherscan: https://sepolia.etherscan.io/address/0x...
   - PolygonScan: https://mumbai.polygonscan.com/address/0x...

6. **Test Fund Your Account:**
   - Sepolia: https://sepoliafaucet.com (request testnet ETH)
   - Mumbai: https://mumbaifaucet.com (request test MATIC)

7. **Health Check:**
   ```bash
   curl https://sepolia.infura.io/v3/YOUR_KEY -X POST \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

**Length:** 600–800 words

**Data Source:** SSID-open-core exports (contracts/testnet-addresses.json, if available)

---

### 2.B.4: `src/content/docs/deployments/testnet-addresses.mdx`

**Frontmatter:**
```yaml
---
title: Testnet Contract Addresses & RPC Endpoints
description: Current testnet deployment information for Sepolia and Mumbai.
---
```

**Content:**
1. **Sepolia Deployment**
   - IdentityCore: `0x...` (auto-derived from SSID-open-core)
   - IdentityResolver: `0x...`
   - TokenContract: `0x...` (if applicable)
   - Governance: `0x...` (DAO contract, if applicable)

2. **Mumbai Deployment**
   - Similar structure for Polygon testnet

3. **RPC Endpoints**
   - Infura Sepolia
   - Alchemy Mumbai
   - Public RPC URLs

4. **Verification**
   - Explorer links
   - `npx hardhat verify` commands

**Note:** This page is **auto-derived from SSID-open-core exports**. If a deploy tool exists, automate the population.

**Length:** 300–400 words

---

### 2.B.5: `src/content/docs/deployments/mainnet-readiness.mdx`

**Frontmatter:**
```yaml
---
title: Mainnet Readiness Roadmap
description: Prerequisites, gates, and timeline for production deployment.
---
```

**Content:**
1. **Current Status:**
   - **Testnet:** ✓ Live on Sepolia/Mumbai
   - **Mainnet:** ⏳ In Development (Phase 8 of 10)
   - **Timeline:** Target Q2 2026 (subject to audit completion)

2. **Production Checklist:**
   - [ ] Smart contract security audit (external firm)
   - [ ] 100% test coverage for critical paths
   - [ ] Legal review (MiCA, eIDAS compliance)
   - [ ] KYC/AML provider integration
   - [ ] Multi-sig for contract upgrades
   - [ ] Rate limiting & DDoS protection
   - [ ] Incident response runbook
   - [ ] Production monitoring & alerting

3. **Deployment Gates (Sequential):**
   - Gate 1: Code Audit ✓ (scheduled Q2 2026)
   - Gate 2: Legal Clearance ⏳ (pending)
   - Gate 3: Security Review (3rd party) ⏳
   - Gate 4: Board Approval ⏳
   - Gate 5: Production Cutover ⏳

4. **Phase Timeline:**

| Phase | Milestone | Target Date | Status |
|-------|-----------|-------------|--------|
| **Phase 8** | All testnet gates pass | 2026-05-15 | 🔄 In Progress |
| **Phase 9** | Audit + legal clearance | 2026-06-15 | 🔄 In Progress |
| **Phase 10** | Mainnet deployment | 2026-07-01 | ⏳ Pending |

5. **What is NOT Production Ready:**
   - Community governance (manual voting in testnet)
   - Advanced fee models (v1 only)
   - Cross-chain bridges (out of scope)

6. **Contact & Questions:**
   - Governance: [DAO forum](https://forum.example.com)
   - Security: [security@ssid.example.com](mailto:security@ssid.example.com)

**Important Disclaimer:**
> This roadmap is **informational** and **not a guarantee** of mainnet launch. Actual deployment depends on audit results, legal review, and governance decisions. **No funds should be committed** to SSID until mainnet is officially live and verified on public blockchains.

**Length:** 800–1000 words

---

### 2.B.6: `src/content/docs/tooling/ems-control-plane.mdx`

**Frontmatter:**
```yaml
---
title: EMS Control Plane — CLI & Portal
description: Manage SSID system via ssidctl CLI and EMS Portal interface.
---
```

**Content:**
1. **Overview:**
   - EMS = External Management System (Control Plane)
   - Two interfaces: **CLI** (ssidctl) and **Portal** (web UI)
   - Manages: SSID core updates, evidence logging, policy enforcement
   - Access: Password-based auth (development) / OAuth (production)

2. **Architecture (3-Plane Model):**
   ```
   Control Plane (EMS)
         ↓
   Data Plane (SSID Core)
         ↓
   Evidence Plane (WORM Store)
   ```

3. **ssidctl CLI Installation:**
   ```bash
   pip install -e "SSID-EMS[dev]"
   ssidctl --version
   ```

4. **Configuration:**
   ```yaml
   # config/ems.yaml
   ssid_repo_path: /path/to/SSID
   evidence_path: /path/to/evidence
   worm_store: /path/to/worm
   ```

5. **Common Commands:**

| Command | Purpose | Example |
|---------|---------|---------|
| `ssidctl bootstrap` | Initialize EMS state | ssidctl bootstrap |
| `ssidctl validate` | Run SoT validator | ssidctl validate --all |
| `ssidctl dispatch` | Execute dispatcher | ssidctl dispatch --task update-root |
| `ssidctl evidence list` | View evidence log | ssidctl evidence list --filter="gate=secret-scan" |
| `ssidctl gates` | Show all gates | ssidctl gates --status |

6. **EMS Portal (Web UI):**
   - URL: http://localhost:3100 (dev)
   - Login: admin / (from config)
   - Dashboard: System health, last operations, evidence summary
   - Workflows: Trigger manual updates, view dispatch logs
   - Settings: Configure gates, manage users, export settings

7. **Health Check:**
   ```bash
   curl http://localhost:8100/api/health
   ```

8. **Troubleshooting:**
   - **Connection refused:** Is EMS backend running? Check port 8100
   - **Auth failure:** Verify credentials in ems.yaml
   - **WORM write error:** Check disk space and permissions

**Length:** 1000–1200 words

**Data Source:** Sanitized from SSID-EMS README + CLI help output

---

### 2.B.7: `src/content/docs/tooling/orchestrator-runtime.mdx`

**Frontmatter:**
```yaml
---
title: Orchestrator Runtime — Dispatch & Workflows
description: Execute and monitor SSID workflows via the orchestrator runtime.
---
```

**Content:**
1. **Overview:**
   - Orchestrator = Runtime execution engine
   - Responsible for: Task dispatch, workflow execution, session management
   - Interfaces: Python API + Node.js web UI + REST API

2. **Architecture:**
   - **Dispatcher:** Routes tasks to agents/services
   - **Workflows:** Multi-step processes (e.g., identity verification)
   - **Sessions:** Isolated execution contexts for tasks
   - **Health Checks:** Monitor agent/service availability

3. **Installation:**
   ```bash
   cd SSID-orchestrator
   pip install -e ".[dev]"
   npm install
   ```

4. **Starting the Runtime:**
   ```bash
   # Terminal 1: Python dispatcher
   python -m ssid_orchestrator.dispatcher --port 3310

   # Terminal 2: Node.js API server
   npm run dev --port 3310

   # Terminal 3: Web UI (Vite)
   npm run dev:ui --port 5273
   ```

5. **Health Check:**
   ```bash
   curl http://localhost:3310/api/health
   ```

6. **Common Workflows:**

| Workflow | Input | Output | Status |
|----------|-------|--------|--------|
| `identity-resolve` | DID | Resolved document | ✓ Available |
| `verify-credential` | VC + public key | Signature valid? | ✓ Available |
| `update-identity` | Updates + signature | New document hash | ✓ Available |
| `initiate-kyc` | User data | KYC provider response | ✓ Available |

7. **Web UI (Orchestrator Portal):**
   - URL: http://localhost:5273 (dev)
   - Dashboard: Active workflows, session status
   - Logs: Real-time dispatch logs, error traces
   - Settings: Configure timeouts, retry policies

8. **Monitoring & Debugging:**
   ```bash
   # View active sessions
   curl http://localhost:3310/api/sessions

   # View workflow status
   curl http://localhost:3310/api/workflows/{workflow_id}
   ```

**Length:** 900–1100 words

**Data Source:** Sanitized from SSID-orchestrator README + API docs

---

## PHASE 2.C: CONTENT FILE UPDATES (Priority Order)

### 2.C.1: Update `src/content/docs/operations/local-stack.md`

**Current Issue:** Uses C-ports (3000, 8000, 3001) instead of G-ports (3100, 8100, 3101)

**Change:**

**Old Port Table:**
```
| Service              | Port | Health URL                          |
|----------------------|------|-------------------------------------|
| EMS Portal Frontend  | 3000 | http://localhost:3000                |
| EMS Portal Backend   | 8000 | http://localhost:8000/api/health     |
```

**New Port Table:**
```
| Service              | Port | Health URL                          |
|----------------------|------|-------------------------------------|
| EMS Portal Frontend  | 3100 | http://localhost:3100                |
| EMS Portal Backend   | 8100 | http://localhost:8100/api/health     |
```

**Additional Changes:**
- Add note: "These are **G-ports** (workspace/development). See Port Matrix (Current) for full reference."
- Add reference to `port-policy.md` in workspace
- Update PM2 commands to reference correct ports
- Add explicit note: "Use `localhost`, not `127.0.0.1` to avoid cookie issues."

**Line Changes:** ~20 lines updated.

---

### 2.C.2: Update `src/content/docs/status.mdx`

**Current Issue:** Status snapshot is from 2026-03-02 (41 days old)

**Change:**

**Old Aside:**
```
Last updated: 2026-03-02.
```

**New Aside:**
```
⚠️ This page displays a **snapshot** of system status as of 2026-04-13.
For real-time status, see public evidence exports or GitHub Actions CI logs.
To auto-update this page, see [Public Evidence Export](../governance/evidence-export).
```

**Add Section:** "How Status is Updated"
- Manual snapshot (current approach): Editor updates date + content
- Proposed: Auto-fetch from GitHub Actions API or public export endpoint
- Roadmap: Automated daily update via GitHub Actions

**Line Changes:** ~30 lines added.

---

### 2.C.3: Update `src/content/docs/tooling/mission-control.mdx`

**Current Issue:** Page exists but is sparse (< 300 words)

**Change:** Expand or merge into `ems-control-plane.mdx` (created in 2.B.6)

**Action:** 
- Keep `mission-control.mdx` as redirect/summary
- Link to `ems-control-plane.mdx` for full details
- Remove redundancy

---

### 2.C.4: Update `src/content/docs/tooling/dispatcher.mdx`

**Current Issue:** Dispatcher docs are narrow; need broader orchestrator context

**Change:**
- Keep `dispatcher.mdx` focused on dispatcher component
- Create `orchestrator-runtime.mdx` (done in 2.B.7) for full orchestrator context
- Update `dispatcher.mdx` to reference orchestrator-runtime.mdx

---

### 2.C.5: Update `src/content/docs/architecture/open-core.mdx`

**Change:** Add forward reference to new 5-repo-topology.mdx

**Old Text:**
```
This repository exposes **5 exported root modules**...
```

**New Text:**
```
This repository exposes **5 exported root modules** (see [5-Repo System Topology](../architecture/5-repo-topology) for full context)...
```

**Line Changes:** ~5 lines.

---

## PHASE 2.D: TEST SUITE EXTENSIONS

### 2.D.1: Create `tests/ports-matrix-validator.test.mjs`

**Purpose:** Validate that port matrix in local-stack.md matches workspace config

**Pseudo-code:**
```javascript
import fs from 'fs';
import path from 'path';
import { readFileSync } from 'fs';

const EXPECTED_PORTS = {
  'EMS Portal Frontend': 3100,
  'EMS Portal Backend': 8100,
  // ... etc
};

export async function test_ports_matrix_correctness() {
  const localStackContent = readFileSync(
    'src/content/docs/deployments/ports-matrix-current.mdx', 
    'utf-8'
  );
  
  // Extract port table from markdown
  const ports = extractPortTable(localStackContent);
  
  // Verify each port
  Object.entries(EXPECTED_PORTS).forEach(([service, expectedPort]) => {
    const actual = ports[service];
    if (actual !== expectedPort) {
      throw new Error(`Port mismatch for ${service}: expected ${expectedPort}, got ${actual}`);
    }
  });
  
  console.log('✓ PASS: All ports match expected workspace matrix');
}
```

**Expected:** Test passes with G-ports (3100, 8100, 3102, 3310, 5273, 4331, 4332).

---

### 2.D.2: Create `tests/sidebar-soll-completeness.test.mjs`

**Purpose:** Enforce that SOLL sidebar categories are present

**Pseudo-code:**
```javascript
export const SOLL_CATEGORIES = [
  'System Architecture & Integration',
  'Getting Started',
  'Operations & Deployments',  // NEW
  'Identity & Credentials',
  'Governance & Operations',
  'Integration & Tools',
  'Smart Contracts',  // NEW (if applicable)
  'Compliance & Regulations',
  'Token Economics',
  'Developer Resources',
  'System Status & Evidence',  // NEW
  'FAQ & Troubleshooting',
  'Research & Roadmap',
  'About',
];

export async function test_sidebar_completeness() {
  const config = await import('../astro.config.mjs');
  const sidebar = config.default.integrations[0].sidebar;
  const actual_categories = sidebar.map(s => s.label);
  
  SOLL_CATEGORIES.forEach(category => {
    if (!actual_categories.includes(category)) {
      throw new Error(`Missing SOLL category: "${category}"`);
    }
  });
  
  console.log('✓ PASS: All SOLL categories present in sidebar');
}
```

**Expected:** All 14 SOLL categories found.

---

### 2.D.3: Create `tests/deployment-docs-presence.test.mjs`

**Purpose:** Ensure local/testnet/mainnet deployment guides exist

**Pseudo-code:**
```javascript
export const REQUIRED_DEPLOYMENT_FILES = [
  'src/content/docs/deployments/local-stack.md',
  'src/content/docs/deployments/ports-matrix-current.mdx',
  'src/content/docs/deployments/testnet-guide.mdx',
  'src/content/docs/deployments/mainnet-readiness.mdx',
];

export async function test_deployment_docs_presence() {
  REQUIRED_DEPLOYMENT_FILES.forEach(file => {
    if (!fs.existsSync(file)) {
      throw new Error(`Missing deployment doc: ${file}`);
    }
  });
  
  console.log('✓ PASS: All deployment guides present');
}
```

**Expected:** All 4 files exist.

---

### 2.D.4: Create `tests/evidence-export-docs.test.mjs`

**Purpose:** Verify governance/evidence-export.mdx exists and documents public evidence endpoint

**Pseudo-code:**
```javascript
export async function test_evidence_export_documented() {
  const content = readFileSync('src/content/docs/governance/evidence-export.mdx', 'utf-8');
  
  const required_terms = [
    'public evidence export',
    'endpoint',
    'verification',
    'immutability',
  ];
  
  required_terms.forEach(term => {
    if (!content.toLowerCase().includes(term)) {
      throw new Error(`Evidence export doc missing term: "${term}"`);
    }
  });
  
  console.log('✓ PASS: Evidence export documentation complete');
}
```

**Expected:** All terms found.

---

### 2.D.5: Add Tests to `tests/run.mjs`

**Action:** Register new tests in main test runner

```javascript
import { test_ports_matrix_correctness } from './ports-matrix-validator.test.mjs';
import { test_sidebar_completeness } from './sidebar-soll-completeness.test.mjs';
import { test_deployment_docs_presence } from './deployment-docs-presence.test.mjs';
import { test_evidence_export_documented } from './evidence-export-docs.test.mjs';

const tests = [
  // ... existing tests
  ['Ports Matrix Validator', test_ports_matrix_correctness],
  ['Sidebar SOLL Completeness', test_sidebar_completeness],
  ['Deployment Docs Presence', test_deployment_docs_presence],
  ['Evidence Export Documented', test_evidence_export_documented],
];

// Run all tests...
```

**Expected:** 4 new tests added; all pass.

---

## PHASE 2.E: CI GATE ENHANCEMENTS

### 2.E.1: Update `.github/workflows/docs_ci.yml`

**Purpose:** Add validation for new content completeness checks

**Changes:**

1. **After `denylist-gate` job**, add new job:

```yaml
deployment-docs-gate:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Check deployment documentation
      run: |
        echo "=== Deployment Docs Presence Check ==="
        FAIL=0
        
        for file in \
          "src/content/docs/deployments/local-stack.md" \
          "src/content/docs/deployments/ports-matrix-current.mdx" \
          "src/content/docs/deployments/testnet-guide.mdx" \
          "src/content/docs/deployments/mainnet-readiness.mdx"; do
          if [ ! -f "$file" ]; then
            echo "FAIL: Missing deployment doc: $file"
            FAIL=1
          fi
        done
        
        if [ "$FAIL" -eq 1 ]; then
          exit 1
        fi
        echo "PASS: All deployment docs present"
```

2. **In `build` job**, add step before "Run tests":

```yaml
- name: Verify port matrix correctness
  run: |
    echo "=== Port Matrix Validation ==="
    if grep -q "3000\|8000\|3001" src/content/docs/deployments/ports-matrix-current.mdx; then
      echo "FAIL: Port matrix contains C-ports instead of G-ports"
      exit 1
    fi
    echo "PASS: Port matrix uses correct G-ports"
```

**Line Changes:** ~40 lines added to docs_ci.yml.

---

## PHASE 2.F: VALIDATION & VERIFICATION

### 2.F.1: Local Build & Test

**Steps:**

```bash
cd SSID-docs

# 1. Install dependencies
pnpm install --frozen-lockfile

# 2. Type check
pnpm astro check

# 3. Build site
pnpm build

# 4. Run all tests
pnpm test

# 5. Verify no secrets
grep -r "C:\\Users\\" src/ && echo "FAIL: Windows path leaked" || echo "PASS: No Windows paths"
grep -r "sk_live_\|sk_test_\|ghp_\|gho_" src/ && echo "FAIL: Credentials found" || echo "PASS: No credentials"
```

**Expected Output:**
```
✓ Type check: OK
✓ Build: 66 pages compiled
✓ Tests: 18 passed (13 existing + 4 new + 1 existing baseline)
✓ Security: PASS (no secrets/paths)
```

### 2.F.2: Sidebar Completeness Audit

**Action:** Verify new sidebar categories render correctly

```bash
# After build, check dist/ for new routes
test -f dist/en/deployments/local-stack/index.html && echo "✓ deployments/local-stack route"
test -f dist/en/deployments/testnet-guide/index.html && echo "✓ deployments/testnet-guide route"
test -f dist/en/architecture/5-repo-topology/index.html && echo "✓ architecture/5-repo-topology route"
test -f dist/en/tooling/ems-control-plane/index.html && echo "✓ tooling/ems-control-plane route"
```

### 2.F.3: Security Audit

**Action:** Run security checks manually

```bash
# 1. Check for forbidden file types
find src -name "*.pem" -o -name "*.key" -o -name "*.env" && echo "FAIL" || echo "PASS: No forbidden files"

# 2. Check for absolute paths
grep -r "C:\\\\Users\|/home/.*SSID\|Users/bibel" src && echo "FAIL" || echo "PASS: No absolute paths"

# 3. Check for private repo patterns
grep -r "local.ssid\|sync.all\|mirror.repo\|git.filter-repo" src && echo "FAIL" || echo "PASS: No private patterns"
```

**Expected:** All PASS.

---

## IMPLEMENTATION ORDER (Phase 2.F Execution)

Execute in this order for optimal dependency flow:

1. **2.A.1–2.A.2** — Update astro.config.mjs (sidebar config)
2. **2.B.1–2.B.7** — Create new content files
3. **2.C.1–2.C.5** — Update existing content files
4. **2.D.1–2.D.5** — Add new tests
5. **2.E.1** — Update CI gates
6. **2.F.1–2.F.3** — Validation & verification

---

## PHASE 2 EXIT CHECKLIST

- [ ] astro.config.mjs updated with 4 new sidebar categories
- [ ] 7 new `.mdx` files created (4 P0 deployments, 2 P0 tooling, 1 P0 architecture)
- [ ] 5 existing content files updated (local-stack, status, mission-control, dispatcher, open-core)
- [ ] 4 new test files added + registered in run.mjs
- [ ] docs_ci.yml extended with deployment-docs-gate + port-matrix validation
- [ ] `pnpm install` succeeds
- [ ] `pnpm astro check` passes
- [ ] `pnpm build` produces 66+ pages (was 66, now 73)
- [ ] `pnpm test` passes 100% (18 tests: 13 existing + 4 new + 1 baseline)
- [ ] `git status` shows only new/updated SSID-docs files
- [ ] No secrets, absolute paths, or private repo references in diff
- [ ] All routes render correctly (spot-check 4 new routes in dist/)
- [ ] Security audit passes (no forbidden files/patterns)

---

## BLOCKERS & DEPENDENCIES

### Hard Blockers (External)
- ❌ Testnet contract addresses — Must be extracted from SSID-open-core exports or provided
- ❌ Evidence export endpoint — Must exist or be mocked for documentation

### Soft Blockers (Can be worked around)
- ⚠ Smart contracts public? — If not, skip 2.B.3 contract addresses section

### Assumptions
- ✓ Port matrix is stable (G-ports: 3100, 8100, 3102, 3310, 5273, 4331, 4332)
- ✓ EMS/Orchestrator can be documented from README + CLI help (no internal code exposed)
- ✓ astro.config.mjs syntax is Node.js-compatible

---

## SUCCESS CRITERIA (Phase 2)

| Criterion | Success | Evidence |
|-----------|---------|----------|
| **Content Gaps Closed** | P0 gaps all addressed | 7 new files + 5 updates |
| **Sidebar Complete** | All SOLL categories present | astro.config.mjs shows 14 top-level categories |
| **Tests Pass** | 100% test success | `pnpm test` output: 18 PASS |
| **No Policy Violations** | Security audit PASS | No secrets/paths in `git diff` |
| **Build Success** | Site builds cleanly | `pnpm build` completes with 0 errors |
| **Routes Render** | All new routes work | dist/ contains 73 pages (was 66) |
| **Ports Correct** | G-ports in all docs | local-stack.md + ports-matrix-current.mdx use 3100/8100 |
| **EMS/Orchestrator Documented** | ≥2 pages each | ems-control-plane.mdx + orchestrator-runtime.mdx created |
| **Testnet Guide Present** | Users can deploy to testnet | testnet-guide.mdx + testnet-addresses.mdx created |
| **Mainnet Clarity** | No false "live" claims | mainnet-readiness.mdx clearly marks as roadmap, not live |

---

## POST-IMPLEMENTATION

### Immediate (Right After Phase 2)
1. Commit all changes: `git add -A && git commit -m "Phase 2: Complete SSID-docs system documentation"`
2. Open PR on SSID-docs repo
3. Run docs_ci.yml CI checks (must all PASS)
4. Request review from CODEOWNERS

### Follow-Up (Phase 3+)
1. **Auto-Generate Port Matrix** — Create tool to export workspace port-matrix.json → markdown
2. **Auto-Update Status** — GitHub Actions job to update status.mdx daily from public exports
3. **Smart Contract ABI** — If contracts are public, auto-generate ABI docs from source
4. **Evidence Export** — Link to live public evidence endpoint (requires SSID infrastructure)
5. **Localization** — Complete German (de/) translations for all new docs

---

## CONFIGURATION ARTIFACTS

### ports-matrix.json (Reference)

```json
{
  "workspace": "G",
  "ports": {
    "ems_portal_frontend": 3100,
    "ems_portal_backend": 8100,
    "legacy_website": 3101,
    "ssid_docs": 4331,
    "orchestrator_api": 3310,
    "orchestrator_ui": 5273,
    "cct_docs": 3102,
    "cct_dashboard": 4332
  }
}
```

### astro.config.mjs Sidebar (Excerpt)

See **PHASE 2.A.1** for full sidebar structure.

---

## PHASE 2 COMPLETION

**Estimated Effort:** 
- Content writing: ~8 hours
- Config/test changes: ~2 hours
- Testing/validation: ~2 hours
- **Total:** ~12 hours (1–2 days of focused work)

**Deliverables:**
1. ✓ PHASE2_IMPLEMENTATION_PLAN.md (this file)
2. ✓ 7 new content files
3. ✓ 5 updated content files
4. ✓ 4 new test files
5. ✓ Updated CI gates
6. ✓ Updated astro.config.mjs

**Exit Status:** Ready for GitHub PR review.

---

**Plan Date:** 2026-04-13  
**Plan Status:** READY FOR REVIEW  
**Next Phase:** PHASE 2.F Implementation (apply Phase 2 changes)

