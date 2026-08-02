---
title: "Catalog of Hundred AI Skills for AI Agents"
description: "Architecture and implementation catalog with 100 measurable, versioned, and auditable AI skills for AI agents and platform infrastructure."
sidebar:
  label: "100 AI Skills & Agents"
  order: 3
---

# Catalog of Hundred AI Skills for AI Agents

> Architecture and Implementation Catalog: 100 measurable, versioned, and auditable AI skills for AI agents and platform infrastructure.

## Overview

This catalog comprises 100 AI skills organized into ten reusable families, designed to support the [100 AI Business Models](/research/100-ai-business-models-infrastructure-pattern/). Unlike monolithic AI systems, these skills are:

- **Measurable:** Each produces structured outputs with confidence scores, latency, cost, and audit trails
- **Versioned:** Enabling reproducibility, rollback, and compliance documentation
- **Idempotent:** Retries and reconciliation work correctly without side effects
- **Policy-checked:** Intrinsic governance, role-based access, and human handoff capabilities

**Source:** These skills derive from architectural synthesis across regulatory frameworks (EU AI Act, GDPR, BSI guidelines, sector standards like FHIR and XRechnung).

**Status Markers:**
- **VERIFIED:** Regulatory requirements and infrastructure standards
- **INFERENCE:** Skill definitions, API patterns, and business model linkages derived from those standards
- **UNKNOWN:** Unconfirmed implementation details or market availability

## Ten Skill Families

| Family | Focus | Examples |
|--------|-------|----------|
| **A) Intake & Documents** | Unified entry point for text, PDF, voice, image, form | Multimodal gateway, OCR parser, email triage, voice-to-case |
| **B) Understanding & Classification** | Intent detection, document type, entity extraction, risk scoring | Intent classifier, document type detector, entity extractor, code classifier |
| **C) Matching & Routing** | Connect demand to supply, optimize assignment | Provider matcher, slot matcher, dispatch router |
| **D) Forecasting & Prediction** | Anticipate outcomes, demand, resource needs | Churn predictor, demand forecaster, resource planner |
| **E) Optimization & Orchestration** | Sequence steps, coordinate agents, orchestrate events | Workflow orchestrator, load balancer, event coordinator |
| **F) Billing, Settlement & Metering** | Measure usage, calculate charges, distribute revenue | Usage metering, cost calculator, settlement processor |
| **G) Compliance, Audit & Reporting** | Governance, transparency, regulatory proof | Audit logger, compliance checker, provenance tracker |
| **H) Human-in-the-Loop & QA** | Expert review, quality control, escalation | Quality reviewer, human handoff, consensus aggregator |
| **I) Agentic Orchestration & Tool-Use** | Multi-step reasoning, external tool calls, state management | Tool caller, state machine, reasoning engine |
| **J) Domain-Specific Skills** | Vertical specialization (healthcare, legal, finance) | Clinical decision support, legal research, financial modeling |

## Architectural Principles

**Metering-First:** Every skill produces, alongside its functional output:
```
trace_id, actor_id, confidence, latency_ms, cost, version, policy_result, usage_unit
```
This enables dispatch, settlement, payout, and regulatory reporting without separate instrumentation.

**Privacy-by-Design:** GDPR principles built in:
- Data minimization: Use only necessary fields
- Purpose limitation: Explicit consent/legal basis
- Limited retention: Configurable data lifecycle
- Pseudonymization: Where feasible before processing

**Reusability Over Specialization:** A modular stack of ~10 reusable skill families supports all 100 business models far better than 100 unique monolithic systems.

**Semantic Standardization:** Where possible, use domain standards:
- **Healthcare:** FHIR structures, ICD/SNOMED codes
- **Public Billing:** XRechnung/EN 16931
- **Supply Chain:** GS1, epcis events
- **Finance:** SWIFT, ISO 20022

## Catalog Access

The complete skill table with all 100 entries is available in:

- **[PDF](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf)** — Full specification with inputs, outputs, technologies, and business model linkages
- **[JSON Dataset](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)** — Structured data for system design and integration
- **[German Detail Page](/de/research/katalog-100-ki-skills-und-ki-agents/)** — Complete German documentation with tables and implementation guidance

## Cross-Reference to Business Models

Each skill maps to one or more of the 100 business models, indicating:

- Which domains and market segments benefit from this skill
- What downstream business value it enables
- How it fits into larger platform architectures

The [Skill-Model Matrix](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json) makes these connections explicit and machine-readable.

## Technology Stack

**Core AI Techniques:**

| Acronym | Meaning | Typical Use |
|---------|---------|------------|
| LLM | Large Language Model | Text understanding, summarization, code generation |
| VLM | Vision Language Model | Image/document understanding, OCR alternative |
| OCR | Optical Character Recognition | Text extraction from scans and PDFs |
| ASR | Automatic Speech Recognition | Voice-to-text transcription |
| NER | Named Entity Recognition | Extract people, places, amounts, dates |
| TSF | Time-Series Forecasting | Demand, resource, trend prediction |
| GNN | Graph Neural Networks | Relationship and pattern detection |
| RL | Reinforcement Learning | Optimization under constraints |
| RAG | Retrieval-Augmented Generation | Knowledge-grounded Q&A |

## Disclaimers

- **No guarantee of implementation:** Inclusion in the catalog does not mean a production-ready implementation exists today.
- **Analytical synthesis:** Skill definitions are professional estimates based on regulatory and architectural principles, not market surveys.
- **Regulatory evolution:** AI Act, GDPR, and sector regulations continue to evolve; skill design should adapt.
- **Regional variation:** Implementation details vary significantly by jurisdiction and industry sector.

## Related Resources

- **[Overview Page](/research/ai-infrastructure-catalogs/)** — Unified entry point for business models and skills
- **[100 AI Business Models](/research/100-ai-business-models-infrastructure-pattern/)** — Market opportunities and use cases
- **[Shared Architecture Model](/research/ai-infrastructure-catalogs/#gemeinsames-architekturmodell)** — How skills and business models connect
