---
title: "AI Infrastructure Catalogs"
description: "Gemeinsame Übersicht über 100 KI-Business-Modelle und 100 KI-Skills für KI-Agenten."
sidebar:
  label: "AI Infrastructure Catalogs"
  order: 1
---

# AI Infrastructure Catalogs

![AI Infrastructure Stack](/SSID-docs/images/research/ai-infrastructure/ai-infrastructure-stack.png)

Dieser Bereich verbindet zwei zusammengehörige Forschungspakete zu einem gemeinsamen Infrastrukturmodell:

- **100 Business-Modelle** beschreiben die wirtschaftlichen Märkte und Plattformchancen.
- **100 KI-Skills** beschreiben die technischen, regulatorischen und operativen Bausteine, mit denen diese Plattformen umgesetzt werden.

Jeder Skill referenziert konkrete Business-Modell-Nummern (soweit im Quell-PDF ausgewiesen); jedes Business-Modell lässt sich auf den gemeinsamen technischen Skill-Stack zurückführen.

## Business-Modelle

![100 KI-Business-Modelle](/SSID-docs/images/research/ai-infrastructure/business-models-social-card.png)

**Anzahl:** 100

Strategischer Chancen-, Plattform- und Infrastrukturatlas mit 100 analytisch abgeleiteten Geschäftsmodellen nach dem Infrastrukturmuster: kleine Anbieter, fragmentierte Märkte, hohe Ausgabenströme — von Gesundheit über Bau/Handwerk bis Energie, Versicherung, Logistik und öffentliche Beschaffung.

Wichtigste Cluster: Gesundheit/Pflege, Bau/Handwerk/Wohnen, Insurance/Payments, Energie/Flexibilität, öffentliche Beschaffung, KMU-Services.

- [Detailseite: Hundert KI-gestützte Business-Modelle](/research/100-ai-business-models-infrastructure-pattern/)
- [PDF](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf) · [SHA-256](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf.sha256)
- [JSON-Datensatz](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)

## KI-Skills

![100 KI-Skills für KI-Agents](/SSID-docs/images/research/ai-infrastructure/skills-social-card.png)

**Anzahl:** 100

Architektur- und Umsetzungskatalog mit 100 messbaren, versionierten und auditierbaren KI-Skills für KI-Agenten, organisiert in zehn Skill-Familien:

A) Intake & Dokumentenverarbeitung · B) Verständnis & Klassifikation · C) Matching & Routing · D) Prognose & Prognostik · E) Optimierung & Orchestrierung · F) Abrechnung, Settlement & Metering · G) Compliance, Audit & Reporting · H) Human-in-the-loop & Quality Control · I) Agentic Orchestration & Tool-Use · J) Domain-specific Skills

- [Detailseite: Katalog von hundert KI-Skills für KI-Skills und KI-Agents](/research/katalog-100-ki-skills-und-ki-agents/)
- [PDF](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf) · [SHA-256](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf.sha256)
- [JSON-Datensatz](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)

## Gemeinsames Architekturmodell

```
Marktproblem
  → Intake
  → Verständnis
  → Matching
  → Prognose
  → Orchestrierung
  → Metering
  → Settlement
  → Compliance
  → Human Review
  → Agent Runtime
```

Dieser Fluss verbindet die 100 Business-Modelle (das "Was" — welcher Markt, welcher Schmerzpunkt, welche Monetarisierung) mit den 100 KI-Skills (das "Wie" — welche technischen Bausteine den jeweiligen Schritt umsetzen).

## Verknüpfung

In der Skills-Tabelle referenziert die Spalte „Anwendungsfälle (Modell-Nr.)" die Nummern der 100 Business-Modelle. So lässt sich für jeden Skill nachvollziehen, welche Business-Modelle ihn benötigen, und umgekehrt für jedes Business-Modell ableiten, welche Skills es technisch trägt. Diese Zuordnung ist im maschinenlesbaren [Skill-Modell-Matrix-Datensatz](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json) sowie in `src/data/research/ai-infrastructure/skill-model-matrix.json` strukturiert verfügbar.

## Downloads

| Artefakt | Link |
|---|---|
| Business-Modelle PDF | [100-ai-business-models-infrastructure-pattern.pdf](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf) |
| Business-Modelle SHA-256 | [100-ai-business-models-infrastructure-pattern.pdf.sha256](/SSID-docs/downloads/research/ai-infrastructure/100-ai-business-models-infrastructure-pattern.pdf.sha256) |
| KI-Skills PDF | [katalog-100-ki-skills-und-ki-agents.pdf](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf) |
| KI-Skills SHA-256 | [katalog-100-ki-skills-und-ki-agents.pdf.sha256](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf.sha256) |
| Manifest (JSON) | [catalog-manifest.json](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json) |

## Status

**DOCUMENTED:** Beide Kataloge wurden vollständig aus ihren jeweiligen Quellartefakten (Markdown-Ausgangstext bzw. PDF) in dieses Dokumentationssystem integriert.

**INFERENCE:** Die Business-Modelle sind eine analytische Markt- und Plattformableitung. Die Skills sind eine analytische Architektur-Synthese. Die Integration beweist nicht, dass alle Modelle und Skills bereits implementiert sind.
