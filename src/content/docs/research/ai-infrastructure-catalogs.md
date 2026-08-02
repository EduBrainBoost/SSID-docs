---
title: "AI Infrastructure Catalogs"
description: "Unified overview of 100 AI business models and 100 AI skills for AI agents."
sidebar:
  label: "AI Infrastructure Catalogs"
  order: 1
---

# AI Infrastructure Catalogs

![AI Infrastructure Stack](/SSID-docs/images/research/ai-infrastructure/ai-infrastructure-stack.png)

This section connects two complementary research packages into a unified infrastructure model:

- **100 Business Models** describe economic markets and platform opportunities.
- **100 AI Skills** describe the technical, regulatory, and operational components with which these platforms are implemented.

Each skill references specific business model numbers (as indicated in the source PDF); each business model can be traced back to the shared technical skill stack.

## Business Models

![100 AI Business Models](/SSID-docs/images/research/ai-infrastructure/business-models-landscape.png)

**Count:** 100

Strategic market, platform, and infrastructure atlas comprising 100 analytically derived AI business models based on the infrastructure pattern: small providers, fragmented markets, high spending streams — from healthcare through construction/trades to energy, insurance, logistics, and public procurement.

Key clusters: Healthcare/Care, Construction/Trades/Housing, Insurance/Payments, Energy/Flexibility, Public Procurement, SME Services.

- [Detail Page: Hundred AI-Driven Business Models](/research/100-ai-business-models-infrastructure-pattern/)
- [PDF](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf) · [SHA-256](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf.sha256)
- [JSON Dataset](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)

## AI Skills

![100 AI Skills for AI Agents](/SSID-docs/images/research/ai-infrastructure/skills-capability-map.png)

**Count:** 100

Architecture and implementation catalog with 100 measurable, versioned, and auditable AI skills for AI agents, organized into ten skill families:

A) Intake & Document Processing · B) Understanding & Classification · C) Matching & Routing · D) Forecasting & Prediction · E) Optimization & Orchestration · F) Billing, Settlement & Metering · G) Compliance, Audit & Reporting · H) Human-in-the-Loop & Quality Control · I) Agentic Orchestration & Tool-Use · J) Domain-Specific Skills

- [Detail Page: Catalog of Hundred AI Skills for AI Agents](/research/katalog-100-ki-skills-und-ki-agents/)
- [PDF](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf) · [SHA-256](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf.sha256)
- [JSON Dataset](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)

## Shared Architecture Model

```
Market Problem
  → Intake
  → Understanding
  → Matching
  → Forecasting
  → Orchestration
  → Metering
  → Settlement
  → Compliance
  → Human Review
  → Agent Runtime
```

This flow connects the 100 business models (the "What" — which market, which pain point, which monetization) with the 100 AI skills (the "How" — which technical components implement each step).

## Linkage

In the skills table, the "Use Cases (Model #)" column references the numbers of the 100 business models. This allows tracing, for each skill, which business models require it, and conversely for each business model, which skills provide its technical foundation. This mapping is available in machine-readable form in the [Skill-Model Matrix Dataset](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json) and in `src/data/research/ai-infrastructure/skill-model-matrix.json`.

## Downloads

| Artifact | Link |
|---|---|
| Business Models PDF | [100-ai-business-models-infrastructure-pattern.pdf](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf) |
| Business Models SHA-256 | [100-ai-business-models-infrastructure-pattern.pdf.sha256](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf.sha256) |
| AI Skills PDF | [katalog-100-ki-skills-und-ki-agents.pdf](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf) |
| AI Skills SHA-256 | [katalog-100-ki-skills-und-ki-agents.pdf.sha256](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf.sha256) |
| Manifest (JSON) | [catalog-manifest.json](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json) |
| Business Models Landscape | [business-models-landscape.svg](/SSID-docs/images/research/ai-infrastructure/business-models-landscape.svg) |
| Skills Capability Map | [skills-capability-map.svg](/SSID-docs/images/research/ai-infrastructure/skills-capability-map.svg) |
| Model-Skill Matrix | [model-skill-matrix.svg](/SSID-docs/images/research/ai-infrastructure/model-skill-matrix.svg) |

## Status

**DOCUMENTED:** Both catalogs have been fully integrated from their respective source artifacts (markdown source text and PDF) into this documentation system.

**INFERENCE:** The business models represent an analytical market and platform derivation. The skills represent an analytical architecture synthesis. The integration does not prove that all models and skills are already implemented.

## Localization

- **Root (/research/)**: English language
- **German (/de/research/)**: German language (Deutsch)
