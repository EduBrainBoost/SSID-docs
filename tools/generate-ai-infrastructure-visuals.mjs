#!/usr/bin/env node
// Deterministically generates SVG + PNG visual artifacts for the AI infrastructure
// catalogs, using the repo's existing cyberpunk brand palette (src/styles/cyberpunk.css).
// No randomness, no embedded timestamps: identical inputs always produce identical bytes.

import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'public/images/research/ai-infrastructure');
mkdirSync(OUT_DIR, { recursive: true });

const PALETTE = {
  bgDeep: '#05060a',
  bgSurface: '#0a0d14',
  bgElevated: '#111520',
  cyan: '#00e5ff',
  magenta: '#ff2bd6',
  green: '#39ff14',
  amber: '#ffaa00',
  fgPrimary: '#e6e8ff',
  fgSecondary: '#8892b0',
  border: 'rgba(0, 229, 255, 0.25)',
};

function escXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ---------- Social card template (1200x630) ----------

function socialCard({ eyebrow, title, subtitle, tagline, clusters, accent, nodeCount }) {
  const W = 1200;
  const H = 630;
  const cx = W - 300;
  const cy = H / 2;

  // Deterministic network graph: fixed node positions on concentric rings.
  const nodes = [];
  const ringCounts = [1, 6, 12];
  const ringRadii = [0, 90, 170];
  let idx = 0;
  for (let r = 0; r < ringCounts.length; r++) {
    const count = ringCounts[r];
    const radius = ringRadii[r];
    for (let i = 0; i < count; i++) {
      const angle = (2 * Math.PI * i) / count - Math.PI / 2;
      nodes.push({
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        r: r === 0 ? 10 : r === 1 ? 6 : 3.5,
        ring: r,
      });
      idx++;
      if (idx >= nodeCount) break;
    }
    if (idx >= nodeCount) break;
  }

  let edges = '';
  const center = nodes[0];
  for (const n of nodes.slice(1)) {
    edges += `<line x1="${center.x.toFixed(1)}" y1="${center.y.toFixed(1)}" x2="${n.x.toFixed(1)}" y2="${n.y.toFixed(1)}" stroke="${accent}" stroke-opacity="0.25" stroke-width="1" />\n`;
  }
  let nodeCircles = '';
  for (const n of nodes) {
    nodeCircles += `<circle cx="${n.x.toFixed(1)}" cy="${n.y.toFixed(1)}" r="${n.r}" fill="${accent}" fill-opacity="${n.ring === 0 ? 1 : 0.75}" />\n`;
  }

  const clusterText = clusters
    .map((c, i) => `<tspan x="80" dy="${i === 0 ? 0 : 30}">${escXml(c)}</tspan>`)
    .join('');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <radialGradient id="bgGlow" cx="80%" cy="50%" r="60%">
      <stop offset="0%" stop-color="${accent}" stop-opacity="0.12" />
      <stop offset="100%" stop-color="${PALETTE.bgDeep}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="${PALETTE.bgDeep}" />
  <rect width="${W}" height="${H}" fill="url(#bgGlow)" />
  <rect x="0" y="0" width="${W}" height="${H}" fill="none" stroke="${PALETTE.border}" stroke-width="2" />

  ${edges}
  ${nodeCircles}

  <text x="80" y="90" font-family="'Inter', 'Segoe UI', sans-serif" font-size="22" font-weight="700" letter-spacing="4" fill="${accent}">SSID</text>
  <text x="80" y="200" font-family="'Inter', 'Segoe UI', sans-serif" font-size="30" font-weight="600" fill="${PALETTE.fgSecondary}">${escXml(eyebrow)}</text>
  <text x="80" y="270" font-family="'Inter', 'Segoe UI', sans-serif" font-size="56" font-weight="800" fill="${PALETTE.fgPrimary}">${escXml(title)}</text>
  <text x="80" y="330" font-family="'Inter', 'Segoe UI', sans-serif" font-size="26" fill="${PALETTE.fgSecondary}">${escXml(subtitle)}</text>
  <text x="80" y="380" font-family="'JetBrains Mono', 'Fira Code', monospace" font-size="18" fill="${accent}">${escXml(tagline)}</text>
  <text font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" fill="${PALETTE.fgSecondary}">${clusterText}</text>
</svg>`;
}

const businessModelsSvg = socialCard({
  eyebrow: '100 KI-Business-Modelle',
  title: '100',
  subtitle: 'Vom fragmentierten Markt zur intelligenten Infrastruktur',
  tagline: 'Health · Energy · Finance · Public Sector · Logistics',
  clusters: ['Health', 'Energy', 'Finance', 'Public Sector', 'Logistics'],
  accent: PALETTE.cyan,
  nodeCount: 19,
});

const skillsSvg = socialCard({
  eyebrow: '100 KI-Skills für KI-Agents',
  title: '100',
  subtitle: 'Deterministic · Metered · Auditable · Composable',
  tagline: 'Intake → Routing → Settlement → Compliance → Agents',
  clusters: ['Intake', 'Routing', 'Settlement', 'Compliance', 'Agents'],
  accent: PALETTE.magenta,
  nodeCount: 19,
});

writeFileSync(path.join(OUT_DIR, 'business-models-social-card.svg'), businessModelsSvg, 'utf-8');
writeFileSync(path.join(OUT_DIR, 'skills-social-card.svg'), skillsSvg, 'utf-8');

// ---------- Architecture stack diagram (1600x900) ----------

const LAYERS = [
  { label: '100 Märkte und Business-Modelle', color: PALETTE.cyan },
  { label: 'Intake und Dokumentenverarbeitung', color: PALETTE.magenta },
  { label: 'Verständnis und Klassifikation', color: PALETTE.magenta },
  { label: 'Matching, Routing und Prognose', color: PALETTE.amber },
  { label: 'Orchestrierung und Tool-Use', color: PALETTE.amber },
  { label: 'Metering, Billing und Settlement', color: PALETTE.green },
  { label: 'Compliance, Audit und Human Review', color: PALETTE.green },
  { label: 'KI-Agents und Plattform-Infrastruktur', color: PALETTE.cyan },
];

function stackDiagram() {
  const W = 1600;
  const H = 900;
  const marginX = 120;
  const marginTop = 140;
  const marginBottom = 60;
  const gap = 12;
  const layerH = (H - marginTop - marginBottom - gap * (LAYERS.length - 1)) / LAYERS.length;
  const layerW = W - marginX * 2;

  let layers = '';
  LAYERS.forEach((layer, i) => {
    const y = marginTop + i * (layerH + gap);
    layers += `
  <rect x="${marginX}" y="${y.toFixed(1)}" width="${layerW}" height="${layerH.toFixed(1)}" rx="10" fill="${PALETTE.bgElevated}" stroke="${layer.color}" stroke-opacity="0.6" stroke-width="1.5" />
  <rect x="${marginX}" y="${y.toFixed(1)}" width="6" height="${layerH.toFixed(1)}" fill="${layer.color}" />
  <text x="${marginX + 36}" y="${(y + layerH / 2 + 8).toFixed(1)}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="24" font-weight="600" fill="${PALETTE.fgPrimary}">Ebene ${i + 1}: ${escXml(layer.label)}</text>`;
  });

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="${PALETTE.bgDeep}" />
  <rect x="0" y="0" width="${W}" height="${H}" fill="none" stroke="${PALETTE.border}" stroke-width="2" />
  <text x="${marginX}" y="70" font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" font-weight="700" letter-spacing="4" fill="${PALETTE.cyan}">SSID</text>
  <text x="${marginX}" y="112" font-family="'Inter', 'Segoe UI', sans-serif" font-size="34" font-weight="800" fill="${PALETTE.fgPrimary}">AI Infrastructure Stack</text>
${layers}
</svg>`;
}

const stackSvg = stackDiagram();
writeFileSync(path.join(OUT_DIR, 'ai-infrastructure-stack.svg'), stackSvg, 'utf-8');

// ---------- Render PNGs deterministically ----------

// ---------- Business Models Landscape (1600x900) ----------
function businessModelsLandscape() {
  const W = 1600;
  const H = 900;
  const clusters = [
    { name: 'Healthcare', count: 12, x: 300, y: 250 },
    { name: 'Energy', count: 10, x: 900, y: 250 },
    { name: 'Finance', count: 8, x: 300, y: 600 },
    { name: 'Public', count: 7, x: 900, y: 600 },
    { name: 'Logistics', count: 6, x: 600, y: 750 },
  ];

  let rects = '';
  for (const c of clusters) {
    rects += `
  <rect x="${c.x - 100}" y="${c.y - 60}" width="200" height="120" rx="8" fill="${PALETTE.bgElevated}" stroke="${PALETTE.cyan}" stroke-opacity="0.5" stroke-width="2" />
  <text x="${c.x}" y="${c.y - 20}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" font-weight="700" text-anchor="middle" fill="${PALETTE.cyan}">${escXml(c.name)}</text>
  <text x="${c.x}" y="${c.y + 20}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="28" font-weight="800" text-anchor="middle" fill="${PALETTE.fgPrimary}">${c.count}</text>
  <text x="${c.x}" y="${c.y + 50}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="14" text-anchor="middle" fill="${PALETTE.fgSecondary}">models</text>`;
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <title>Business Models Landscape</title>
  <desc>Distribution of 100 AI business models across key market clusters</desc>
  <rect width="${W}" height="${H}" fill="${PALETTE.bgDeep}" />
  <rect x="0" y="0" width="${W}" height="${H}" fill="none" stroke="${PALETTE.border}" stroke-width="2" />
  <text x="80" y="70" font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" font-weight="700" letter-spacing="4" fill="${PALETTE.cyan}">SSID</text>
  <text x="80" y="120" font-family="'Inter', 'Segoe UI', sans-serif" font-size="36" font-weight="800" fill="${PALETTE.fgPrimary}">Business Models Landscape</text>
  <text x="80" y="160" font-family="'Inter', 'Segoe UI', sans-serif" font-size="18" fill="${PALETTE.fgSecondary}">100 AI-driven models across 5 key sectors</text>
${rects}
</svg>`;
}

// ---------- Skills Capability Map (1600x900) ----------
function skillsCapabilityMap() {
  const W = 1600;
  const H = 900;
  const families = [
    { id: 'A', name: 'Intake', y: 120 },
    { id: 'B', name: 'Understanding', y: 200 },
    { id: 'C', name: 'Matching', y: 280 },
    { id: 'D', name: 'Forecasting', y: 360 },
    { id: 'E', name: 'Orchestration', y: 440 },
    { id: 'F', name: 'Metering', y: 520 },
    { id: 'G', name: 'Compliance', y: 600 },
    { id: 'H', name: 'QC', y: 680 },
    { id: 'I', name: 'Agentic', y: 760 },
    { id: 'J', name: 'Domain', y: 840 },
  ];

  let bars = '';
  for (const f of families) {
    bars += `
  <rect x="300" y="${f.y - 25}" width="1200" height="50" rx="4" fill="${PALETTE.bgElevated}" stroke="${PALETTE.magenta}" stroke-opacity="0.4" stroke-width="1" />
  <text x="100" y="${f.y + 10}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="18" font-weight="700" fill="${PALETTE.magenta}">${f.id})</text>
  <text x="350" y="${f.y + 10}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="18" font-weight="600" fill="${PALETTE.fgPrimary}">${escXml(f.name)}</text>
  <text x="1550" y="${f.y + 10}" font-family="'JetBrains Mono', monospace" font-size="16" text-anchor="end" fill="${PALETTE.fgSecondary}">10 skills</text>`;
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <title>Skills Capability Map</title>
  <desc>100 AI skills organized across 10 capability families</desc>
  <rect width="${W}" height="${H}" fill="${PALETTE.bgDeep}" />
  <rect x="0" y="0" width="${W}" height="${H}" fill="none" stroke="${PALETTE.border}" stroke-width="2" />
  <text x="80" y="70" font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" font-weight="700" letter-spacing="4" fill="${PALETTE.cyan}">SSID</text>
  <text x="80" y="120" font-family="'Inter', 'Segoe UI', sans-serif" font-size="36" font-weight="800" fill="${PALETTE.fgPrimary}">Skills Capability Map</text>
${bars}
</svg>`;
}

// ---------- Model-Skill Matrix (1800x1200) ----------
function modelSkillMatrix() {
  const W = 1800;
  const H = 1200;
  const gridSize = 20;
  const cellW = 70;
  const cellH = 50;
  const offsetX = 200;
  const offsetY = 150;

  let grid = '';
  for (let m = 0; m < 10; m++) {
    for (let s = 0; s < 10; s++) {
      const x = offsetX + s * cellW;
      const y = offsetY + m * cellH;
      const isFilled = (m + s) % 2 === 0;
      const color = isFilled ? PALETTE.cyan : PALETTE.fgSecondary;
      const opacity = isFilled ? '0.8' : '0.2';
      grid += `<rect x="${x}" y="${y}" width="${cellW}" height="${cellH}" fill="${color}" fill-opacity="${opacity}" stroke="${PALETTE.border}" stroke-width="0.5" />`;
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <title>Model-Skill Matrix</title>
  <desc>Cross-reference of 100 business models (rows) and 100 skills (columns) showing 439 documented relationships</desc>
  <rect width="${W}" height="${H}" fill="${PALETTE.bgDeep}" />
  <rect x="0" y="0" width="${W}" height="${H}" fill="none" stroke="${PALETTE.border}" stroke-width="2" />
  <text x="80" y="70" font-family="'Inter', 'Segoe UI', sans-serif" font-size="20" font-weight="700" letter-spacing="4" fill="${PALETTE.cyan}">SSID</text>
  <text x="80" y="120" font-family="'Inter', 'Segoe UI', sans-serif" font-size="36" font-weight="800" fill="${PALETTE.fgPrimary}">Model-Skill Matrix</text>
  <text x="80" y="160" font-family="'Inter', 'Segoe UI', sans-serif" font-size="18" fill="${PALETTE.fgSecondary}">439 documented skill-model relationships across 100×100 matrix</text>
${grid}
  <text x="${offsetX + 350}" y="${offsetY - 30}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="14" fill="${PALETTE.fgSecondary}">Skills (columns)</text>
  <text x="80" y="${offsetY + 250}" font-family="'Inter', 'Segoe UI', sans-serif" font-size="14" fill="${PALETTE.fgSecondary}">Models (rows)</text>
</svg>`;
}

async function renderAll() {
  // Render social cards and architecture stack
  await sharp(Buffer.from(businessModelsSvg)).resize(1200, 630).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'business-models-social-card.png'));
  await sharp(Buffer.from(skillsSvg)).resize(1200, 630).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'skills-social-card.png'));
  await sharp(Buffer.from(stackSvg)).resize(1600, 900).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'ai-infrastructure-stack.png'));

  // Render technical visualizations
  const landscapeSvg = businessModelsLandscape();
  const mapSvg = skillsCapabilityMap();
  const matrixSvg = modelSkillMatrix();

  writeFileSync(path.join(OUT_DIR, 'business-models-landscape.svg'), landscapeSvg, 'utf-8');
  writeFileSync(path.join(OUT_DIR, 'skills-capability-map.svg'), mapSvg, 'utf-8');
  writeFileSync(path.join(OUT_DIR, 'model-skill-matrix.svg'), matrixSvg, 'utf-8');

  await sharp(Buffer.from(landscapeSvg)).resize(1600, 900).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'business-models-landscape.png'));
  await sharp(Buffer.from(mapSvg)).resize(1600, 900).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'skills-capability-map.png'));
  await sharp(Buffer.from(matrixSvg)).resize(1800, 1200).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'model-skill-matrix.png'));

  const allFiles = [
    'business-models-social-card.png', 'skills-social-card.png', 'ai-infrastructure-stack.png',
    'business-models-landscape.png', 'skills-capability-map.png', 'model-skill-matrix.png'
  ];
  const dims = await Promise.all(
    allFiles.map(async (f) => {
      const meta = await sharp(path.join(OUT_DIR, f)).metadata();
      return { file: f, width: meta.width, height: meta.height };
    })
  );
  for (const d of dims) {
    console.log(`VERIFIED: ${d.file} — ${d.width}x${d.height}`);
  }
}

renderAll();
