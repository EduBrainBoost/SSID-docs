# SSID Social Media Workflow System

## Ziel
Deterministischer, auditierbarer Content-Workflow für SSID.

## Pipeline
1. Topic Definition (SoT-basiert)
2. Hook Generation
3. Content Production (Script, Visual Prompt)
4. Compliance Check (non-custodial, no claims)
5. Approval Gate
6. Publishing
7. Tracking + Evidence

## Artefakte
- topic.yaml
- hook.md
- script.md
- visual_prompt.md
- post.md
- evidence.json

## Regeln
- Keine unverified claims
- Keine regulatorischen Risiken
- Hash-basierte Referenzen für Inhalte
- Jede Veröffentlichung erzeugt Evidence

## Output Templates
### Hook
"🚨 Problem …"

### Script
Problem → Lösung → Demo → CTA

### Visual Prompt
Cyberpunk / Governance / Proof-based imagery

### Post
SEO + Plattformoptimiert

## Integration
- EMS Trigger
- Orchestrator Pipeline
- Evidence Logging → 02_audit_logging

