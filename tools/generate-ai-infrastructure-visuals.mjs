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

async function renderAll() {
  await sharp(Buffer.from(businessModelsSvg)).resize(1200, 630).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'business-models-social-card.png'));
  await sharp(Buffer.from(skillsSvg)).resize(1200, 630).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'skills-social-card.png'));
  await sharp(Buffer.from(stackSvg)).resize(1600, 900).png({ compressionLevel: 9 }).toFile(path.join(OUT_DIR, 'ai-infrastructure-stack.png'));

  const dims = await Promise.all(
    ['business-models-social-card.png', 'skills-social-card.png', 'ai-infrastructure-stack.png'].map(async (f) => {
      const meta = await sharp(path.join(OUT_DIR, f)).metadata();
      return { file: f, width: meta.width, height: meta.height };
    })
  );
  for (const d of dims) {
    console.log(`VERIFIED: ${d.file} — ${d.width}x${d.height}`);
  }
}

renderAll();
