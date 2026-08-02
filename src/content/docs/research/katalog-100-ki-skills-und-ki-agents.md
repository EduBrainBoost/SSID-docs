---
title: "Katalog von hundert KI-Skills für KI-Skills und KI-Agents"
description: "Architektur- und Umsetzungskatalog mit 100 messbaren, versionierten und auditierbaren KI-Skills für KI-Agenten und Plattform-Infrastruktur."
sidebar:
  label: "100 AI Skills & Agents"
  order: 3
---

# Katalog von hundert KI-Skills für KI-Skills und KI-Agents

> Architektur- und Umsetzungskatalog: 100 messbare, versionierte und auditierbare KI-Skills für KI-Agenten und Plattform-Infrastruktur.

## Quellen- und Statushinweis

**DOCUMENTED:** Der Inhalt dieser Seite wurde vollständig aus dem kanonischen PDF-Artefakt extrahiert und transkribiert. Das PDF bleibt die kanonische Quelle; diese Seite ist eine originalgetreue, redaktionell bereinigte Textfassung.

**VERIFIED:** Der installierte SHA-256-Hash des PDFs entspricht dem bereitgestellten Quellartefakt.

**INFERENCE:** Produktdesigns, API-Muster, Skill-Zuschnitte, Implementierungsreihenfolgen und Zuordnungen zu den 100 Business-Modellen sind analytische Architektur-Synthese, kein Verzeichnis bestehender Standardprodukte.

**UNKNOWN:** Für die Skills 1–10 (Familie A) enthält die Quelltabelle des PDFs keine expliziten numerischen Business-Modell-Referenzen und keinen separaten Implementierungshinweis (bestätigt durch zwei unabhängige Extraktionsverfahren). Diese Felder bleiben für Skills 1–10 als `UNKNOWN` markiert statt erfunden zu werden.

**UNKNOWN:** Die Aufnahme eines Skills in den Katalog beweist nicht, dass bereits eine produktionsreife Implementierung existiert.

## Executive Summary

- Gute KI-Skills sind keine „Prompts", sondern messbare, versionierte, idempotente Services mit klaren Input-/Output-Verträgen, damit Wiederholungen, Abrechnung, Reconciliation und Audit-Trails deterministisch bleiben. Für Hochrisiko-Einsätze betont der EU AI Act u. a. Logging, Dokumentation, Transparenz und Human Oversight; das BSI betont Logging und Monitoring ebenfalls als Kernkontrollen.
- Privacy-by-Design ist kein Add-on: Datenminimierung, Zweckbindung und begrenzte Speicherfristen sind Kernprinzipien der DSGVO; bei Gesundheitsdaten und anderen sensiblen Daten müssen Skills standardmäßig auf minimale Datenfelder, Rollenrechte, Pseudonymisierung und nachvollziehbare Einwilligungs-/Rechtsgrundlagen prüfen.
- Für DE-relevante Sektoren lohnt sich standardisierte Semantik statt Freitext: im Gesundheitsbereich etwa FHIR-basierte Dokument- und Metadatenstrukturen; im öffentlichen Rechnungsverkehr XRechnung/EN 16931. Das reduziert Integrationskosten und erhöht Auditierbarkeit.
- Skill-Design sollte Metering-first sein: jeder Skill erzeugt neben dem Fachoutput immer auch `trace_id`, `actor_id`, `confidence`, `latency_ms`, `cost`, `version`, `policy_result` und `usage_unit`, damit daraus Dispatch, Settlement, Payout und regulatorisches Reporting ableitbar werden. Diese Empfehlung ist architektonische Synthese aus den zuvor erstellten [100 Business-Modellen](/research/100-ai-business-models-infrastructure-pattern/).
- Am wertvollsten sind wiederverwendbare Skills an den Knotenpunkten Intake → Verständnis → Matching → Prognose → Orchestrierung → Metering → Compliance → Human Review → Tool-Use. Genau dort entsteht aus einzelnen Modellen Plattform-Infrastruktur.

## Evidenz und Designrahmen

**STATUS:** Der folgende Katalog ist eine analytische Architektur-Synthese, kein Verzeichnis bestehender Standardprodukte. VERIFIED sind die regulatorischen und infrastrukturellen Leitplanken; INFERENCE sind die daraus abgeleiteten Skill-Zuschnitte, API-Muster und Zuordnungen zu den zuvor erstellten 100 Business-Modellen.

**EVIDENCE:** Für Hochrisiko- und regulierte Nutzung sind derzeit besonders relevant: der EU AI Act mit Anforderungen u. a. an Transparenz, menschliche Aufsicht, Dokumentation und Logging; die DSGVO mit Zweckbindung und Datenminimierung; BSI-Logging-/Monitoring-Leitlinien; gematik/FHIR-Strukturen für Gesundheitsdokumente; XRechnung/EN 16931 für öffentliche E-Rechnungen in Deutschland.

**FINDINGS:** Für die 100 Business-Modelle sind nicht 100 völlig unterschiedliche Agenten nötig, sondern ein modularer Stack aus etwa zehn wiederkehrenden Skill-Familien. Die höchste Wiederverwendung liegt bei Intake-/Dokumenten-Skills, semantischer Klassifikation, Matching/Routing, Prognose, Event-Orchestrierung und Settlement.

**DECISION:** Die Tabelle priorisiert Skills, die praktisch als API-fähige Bausteine mit JSON/Event-I/O, confidence scoring, policy checks und Human-handoff gebaut werden können. Regulatorische Hinweise sind pro Skill nur dort ergänzt, wo sie den Systementwurf substantiell verändern.

### Notation

LLM = Large Language Model, VLM = Vision-Language Model, OCR = Optical Character Recognition, ASR = Automatic Speech Recognition, NER = Named Entity Recognition, TSF = Time-Series Forecasting, GNN = Graph Neural Network, RL = Reinforcement Learning, HITL = Human in the Loop.

## Katalog der hundert Skills

Die Spalte „Anwendungsfälle (Modell-Nr.)" referenziert die zuvor erstellten [100 KI-gestützten Business-Modelle](/research/100-ai-business-models-infrastructure-pattern/).

Die Spalte „Relevante Modelltypen" entspricht der Spalte „Relevante Modelle (Modelltypen)" des kanonischen PDFs und benennt die Domänen- und Anwendungstypen, in denen der jeweilige Skill wiederverwendet wird.

| Nr. | Skill-Name | Kurzbeschreibung | Inputs/Outputs | KI-Technologien | Relevante Modelltypen | Anwendungsfälle (Modell-Nr.) | Implementierungshinweis |
|---:|---|---|---|---|---|---|---|
| **A** | **Intake & Dokumentenverarbeitung** | | | | | | |
| 1 | Multimodal Intake Gateway | Einheitlicher Eingang für Text, PDF, Bild, Formular, Chat und Voice; erzeugt aus rohem Input einen normierten Case. | In: Dateien, Nachrichten, Audio, Metadaten. Out: case_id, Kanal, Rohartefakte, Vor-Metadaten. | LLM, VLM, OCR, ASR | Healthcare Intake, Claims, Public Services | nicht spezifiziert (UNKNOWN) | — |
| 2 | OCR- und Layout-Parser | Extrahiert Text, Tabellen, Felder und Seitenlogik aus PDFs/Scans. | In: PDF/Bild. Out: Textblöcke, Bounding Boxes, Tabellen-JSON. | OCR, LayoutLM/VLM | Abrechnung, Factoring, Claims, Procurement | nicht spezifiziert (UNKNOWN) | — |
| 3 | E-Mail- und Anhangs-Triage | Erfasst eingehende Mails, trennt Fälle, Anhänge und Folgeaktionen. | In: RFC822-Mail, Anhänge. Out: Fallzuordnung, Doktypen, Priorität. | LLM, OCR, Klassifikation | Inkasso, Facility, Vergabe, Travel | nicht spezifiziert (UNKNOWN) | — |
| 4 | Formular-Autofill-Extractor | Liest Pflichtfelder und füllt strukturierte Antrags-/Einreichungsmodelle vor. | In: Formulare, PDFs, Nutzerangaben. Out: validiertes Formular-JSON. | LLM, Regeln, OCR | Genehmigung, Benefits, Kommune, Migration | nicht spezifiziert (UNKNOWN) | — |
| 5 | Voice-to-Case Intake | Wandelt freies Telefon-/Sprachaufkommen in strukturierte Fälle um. | In: Audio/VoIP, Sprecherkanal. Out: Transkript, Zusammenfassung, Fallobjekt. | ASR, Speaker diarization, LLM | Teletriage, Dolmetschen, Callcenter, Kommune | nicht spezifiziert (UNKNOWN) | — |
| 6 | Bild-Intake-Validator | Prüft, ob Bilder für Schadens-, Mangel- oder Inspektionsfälle brauchbar sind. | In: Fotos/Videos. Out: Qualitätsurteil, Nachforderungs-Prompts, Referenzbilder. | Vision, VLM | Schaden, Renovierung, Abfall, Recommerce | nicht spezifiziert (UNKNOWN) | — |
| 7 | Dokument-Deduplikation und Versionsauflösung | Erkennt Dubletten, neue Versionen und zusammengehörige Dokumentketten. | In: Dokumente, Hashes, Metadaten. Out: Version Graph, Master-Dokument. | Embeddings, Graph, Regeln | Abrechnung, Entlassung, Due Diligence, Grants | nicht spezifiziert (UNKNOWN) | — |
| 8 | PII/PHI-Redaction Skill | Erkennt und maskiert personenbezogene/sensible Daten vor Weitergabe. | In: Text, PDF, Audio-Transkript. Out: redigierte Fassung, Redaktionsprotokoll. | NER, LLM, Regeln | Health, Legal, Benefits, Cyber | nicht spezifiziert (UNKNOWN) | — |
| 9 | Schema-Mapping Skill | Überführt Freitext/Felder in Zielschemata wie Claims, Orders, FHIR, XRechnung. | In: Extrakte, Freitext. Out: normalisierte JSON-Objekte. | LLM, Regeln, Ontologien | Billing, Carbon, Vergabe, Research | nicht spezifiziert (UNKNOWN) | — |
| 10 | Consent- und Provenance-Binder | Verknüpft Fall, Einwilligung/Rechtsgrundlage, Quelle und Datenherkunft. | In: Case, User action, Metadaten. Out: Provenance-Record, Consent-Status. | Regeln, Graph | Homecare, Sprachmittlung, Benefits, Health Data | nicht spezifiziert (UNKNOWN) | — |
| **B** | **Verständnis & Klassifikation** | | | | | | |
| 11 | Intent- und Task-Classifier | Erkennt, welches Problem vorliegt und welcher Skill- oder Prozesspfad gestartet werden muss. | In: Text/Voice summary. Out: Intention, Task-Type, Confidence. | LLM, Klassifikation | Intake, Service, Benefits, Contact Center | 1, 2, 67, 83, 84 | Temperature niedrig; Closed Taxonomy + OOD-Erkennung statt Freitextlabels. |
| 12 | Dokumenttyp-Klassifikator | Bestimmt zuverlässig Art und Zweck eines Dokuments. | In: PDF/Bild/Text. Out: Typ, Untertyp, Routing-Hinweis. | OCR, VLM, LLM | Abrechnung, Factoring, Genehmigung, Vergabe | 3, 16, 34, 56, 83 | Typkatalog versionieren; Unknown-Klasse obligatorisch. |
| 13 | Entity- und Feld-Extractor | Zieht strukturierte Entitäten wie Beträge, Daten, Parteien, Codes, Orte. | In: Text/Dokumente. Out: Entitäten mit Positionen und Confidence. | NER, LLM, OCR | Billing, Schaden, Bau, ESG, Legal | 3, 20, 26, 46, 68 | Felder mit Provenance (Seite/Box/Textspanne) zurückgeben. |
| 14 | Code- und Katalog-Klassifikator | Ordnet Inhalte normierten Katalogen zu, z. B. ICD, HS, Tarif, Materialcode. | In: Freitext/Beschreibung/Bild. Out: Top-k Codes + Begründung. | LLM, Retrieval, Regeln | Medizin, Pharma, EPR, Zoll, Public Billing | 3, 11, 47, 60, 97 | Bei High-risk immer menschliche Bestätigung; Katalogversion speichern. |
| 15 | Dringlichkeits- und Risikoscorer | Bewertet Priorität, Gefahrenlage oder Bearbeitungsdringlichkeit. | In: Fallinhalt, Historie, Regeln. Out: Risk/priority score, SLA-Klasse. | LLM, XGBoost, Regeln | Teletriage, Pflege, Discharge, Leckage | 2, 4, 15, 27, 48 | Explainability-Felder ausgeben; kein Blind-Autodispatch bei Grenzfällen. |
| 16 | Beschwerde- und Mängelkategorisierung | Strukturiert Beschwerden, Störungen oder Sachmängel in operative Cluster. | In: Tickets, Bilder, Notizen. Out: Kategorie, Subsystem, Severity. | LLM, VLM, Klassifikation | Mieter, Abfall, FM, Legal Claims | 27, 39, 48, 68, 87 | Klassenbaum pro Domäne pflegen; Drift-Monitoring nötig. |
| 17 | Outcome- und Status-Extractor | Liest aus Freitexten den tatsächlichen Status eines Falls heraus. | In: E-Mails, Berichte, ERP-Notizen. Out: Status, next step, blockers. | LLM, Regeln | Entlassung, Claims, Logistik, Trials | 15, 20, 61, 65, 89 | Statuswerte streng enumerieren; Freitext nur als Beleg anhängen. |
| 18 | Mehrsprachiger semantischer Normalizer | Vereinheitlicht Inhalte sprach- und begriffsunabhängig auf eine interne Semantik. | In: Multilinguale Texte. Out: normierter semantischer Frame. | Multilingual LLM, Embeddings | Dolmetschen, Remittance, Migration, Trade | 13, 18, 85, 95 | Locale, Country, legal context separat als Features modellieren. |
| 19 | Knowledge-grounded QA Retriever | Beantwortet Fragen nur mit dokumentierten Quellen aus Policy, FAQ oder Wissensbasis. | In: Frage + Corpus. Out: Antwort + Quellenanker. | RAG, LLM, Retrieval | Genehmigung, Vergabe, Legal, Kommune | 34, 56, 68, 83, 84 | Keine „free-form authority"; Antwort nur mit source IDs ausgeben. |
| 20 | Widerspruchs- und Konsistenzprüfer | Findet widersprüchliche Angaben über Dokumente, Systeme und Zeit hinweg. | In: mehrere Records/Dokumente. Out: Konfliktliste, Plausibilitätsscore. | LLM, Graph, Regeln | Abrechnung, DD, Legal, Grants, Data Rights | 3, 35, 68, 90, 99 | CONFLICT als erster Output-Class; niemals stillschweigend überschreiben. |
| **C** | **Matching & Routing** | | | | | | |
| 21 | Provider Matcher | Findet den passenden Leistungserbringer anhand Bedarf, Qualität, Ort und Regeln. | In: Case, Provider graph. Out: Ranked providers. | Embeddings, Graph, Ranking | Ärzte, Pflege, Therapy, Handwerk | 1, 4, 6, 32, 72 | Features: Skills, Auslastung, Distanz, SLA, Compliance-Flags. |
| 22 | Slot Matcher | Passt Nachfrage auf konkrete freie Zeiten, Restslots oder Fenster. | In: Verfügbarkeiten, Präferenzen. Out: gebuchte oder vorgeschlagene Slots. | Constraints, Ranking, TSF | Termine, Reha, Hospitality, Beauty | 1, 6, 37, 72, 80 | Kalender-API plus Hold/Confirm-Mechanik; Race-Conditions absichern. |
| 23 | Skill-based Dispatch Router | Weist operative Tickets an genau passende Teams/Subunternehmer zu. | In: Task, Skill matrix, Region. Out: assignee, ETA, dispatch packet. | Graph, Constraints, LLM | FM, Handwerk, Field Service, Gastro | 27, 31, 32, 59, 81 | Harte Constraints vor ML-Ranking auswerten. |
| 24 | Bid- und Auction Router | Leitet Beschaffungs- oder Lead-Fälle an passende Bieter/Anbieter weiter. | In: Request, Supplier graph. Out: Invite list, bid window. | Ranking, LLM, Graph | Trade finance, Einkauf, Vergabe, Influencer | 22, 55, 56, 64, 75 | Fairness- und Anti-Spam-Regeln nötig; Supplier caps definieren. |
| 25 | Kapazitätsbalancer | Glättet Last über Standorte, Teams oder Partnernetzwerke. | In: Nachfrage, Kapazität, Forecast. Out: rebalanced assignments. | TSF, Optimierung | Pflege, Radiologie, Handwerk, Logistik | 4, 7, 32, 61, 67 | Partnernetz als Graph modellieren; Übersteuerung nur mit SLA-Regeln. |
| 26 | Escalation Router | Erkennt, wann ein Fall in höheren Review-, Notfall- oder Spezialpfad wechselt. | In: Score, policy flags, events. Out: escalated path. | Regeln, LLM, Anomaly detection | Triage, Water damage, Contact Center, Legal Aid | 2, 15, 48, 67, 86 | Einfache Regel-DSL bevorzugen; Audit-Pflicht. |
| 27 | Specialist Referral Matcher | Matcht seltene oder komplexe Fälle an Spezialist:innen oder Zentren. | In: Case summary, specialist graph. Out: referral shortlist. | Graph, Embeddings, Ranking | Psychotherapie, Pathologie, Zweitmeinung, Trials | 5, 7, 14, 89 | Expertise-Matrix pflegen; niedrige Recall-Fehler wichtiger als Precision. |
| 28 | Kanal-Orchestrator | Wählt den besten Bearbeitungskanal: App, Mail, Telefon, Chat, API oder Vor-Ort. | In: Nutzerprofil, Case, Kosten. Out: channel recommendation/action. | LLM, Bandits, Regeln | Remittance, Travel, Kommune, Callcenter | 18, 23, 65, 67, 84 | Kommunikationspräferenzen und Rechtsmitteilungen trennen. |
| 29 | Supply-Demand Clearing Engine | Zentraler Matching-Skill für kleine Anbieter, volatile Nachfrage und variable Erlösverteilung. | In: Nachfrage, Supply, Regeln, Preise. Out: Zuweisungen, Clearing-Events. | Graph, Marktmechanismen, RL optional | Factoring, Handwerk, VPP, Parking, Warehouse | 16, 32, 43, 51, 62 | Event-sourced; Reservierung, Finalisierung und Reversal modellieren. |
| 30 | Human Reviewer Assignment | Weist Grenzfälle an geeignete Reviewer mit passenden Rechten und Skills zu. | In: Task, confidence, reviewer pool. Out: review task. | Ranking, Regeln | Claims, Underwriting, QC, Cyber | 20, 21, 57, 68, 96 | Four-eyes optional; Reviewer-Feedback strukturiert zurückführen. |
| **D** | **Prognose & Prognostik** | | | | | | |
| 31 | No-show Forecast | Schätzt Ausfallwahrscheinlichkeit von Terminen oder Schichten. | In: Kalender, Historie, Kontext. Out: no-show risk, overbooking hint. | TSF, XGBoost | Arzttermine, Psychotherapie, Heilmittel, Beauty | 1, 5, 6, 72, 80 | Bias auf vulnerable Gruppen prüfen; nur mit UX-Fallbacks einsetzen. |
| 32 | Claim Cost Estimator | Schätzt Schaden-/Reparatur-/Fallkosten frühzeitig. | In: FNOL, Bilder, Historie. Out: cost range, reserve hint. | Vision, GBM, LLM | Kfz, Property, Water damage, Repair | 20, 21, 48, 79, 100 | Range statt Punktwert; Belegbilder und Referenzfälle speichern. |
| 33 | Nachfrageprognose | Prognostiziert Volumen nach Zeit, Region, Kanal oder Segment. | In: historische Events, externe Faktoren. Out: demand forecast. | TSF, Prophet/Transformers | Hospitality, Retail, Procurement, Delivery | 37, 42, 55, 77, 82 | Forecast-Horizonte explizit machen; kalendarische Features separat führen. |
| 34 | ETA- und Lead-Time-Forecast | Schätzt Durchlauf- und Ankunftszeiten für Fälle, Transporte oder Genehmigungen. | In: Route/Process events. Out: ETA, uncertainty band. | TSF, Graph, Boosting | Maritime, Freight, Warehouse, Cold chain | 54, 61, 62, 95 | Unsicherheitsband feldmäßig zurückgeben; nicht nur ETA-Punktwert. |
| 35 | Default- und Fraud-Risk Score | Schätzt Ausfall- oder Betrugswahrscheinlichkeit. | In: Transaktionen, Historie, Netzwerkdaten. Out: risk score, reasons. | GNN, GBM, Regeln | Factoring, Remittance, Claims, Collections | 16, 18, 20, 24, 94 | Erklärbarkeit und manual override verpflichtend. |
| 36 | Churn- und Adhärenz-Risiko | Erkennt, wer abspringt, nicht zahlt oder Therapie/Lernpfade abbricht. | In: Usage, outcomes, contacts. Out: churn/adherence score. | TSF, Klassifikation | Homecare, Tutoring, Upskilling, Wellness | 8, 72, 73, 80 | Nur verhaltensnahe Features; special category data minimieren. |
| 37 | Failure-/Incident-Forecast | Sagt technische oder operative Ausfälle früh voraus. | In: Telemetrie, Sensorik, Events. Out: failure risk, lead time. | Anomaly detection, TSF | Leckage, Micromobility, Field Service, Irrigation | 48, 52, 59, 93 | Streaming-gestützt; Alert-Fatigue mit Threshold Governance vermeiden. |
| 38 | Preiselastizitäts-Prognose | Schätzt, wie Nachfrage auf Preise oder Rabatte reagiert. | In: Preis-Historie, Kontext, Segment. Out: elasticity interval. | Causal ML, TSF | Short stay, EV charging, Heat pump leads, Surplus food | 37, 41, 44, 77, 82 | Keine black-box Auto-Preisung ohne Guardrails. |
| 39 | Outcome Probability Estimator | Schätzt Erfolg, Abschluss oder Wirksamkeit eines Falls. | In: Patient/case/project features. Out: success probability. | GBM, LLM, Survival models | Therapie, Reha, Recruiting, Trials | 5, 12, 71, 72, 89 | Reines Decision support; kein autonomer Ausschluss ohne Review. |
| 40 | Ressourcenverbrauchs-Forecast | Schätzt Energie, Material, Zeit oder Budget pro Fall/Auftrag. | In: Betrieb, Asset, Job scope. Out: expected resource curve. | TSF, Regression | ESG, Tarife, VPP, Depot charging, Industry flex | 36, 42, 43, 50, 100 | Units strikt typisieren; kWh, m³, EUR, minutes nicht mischen. |
| **E** | **Optimierung & Orchestrierung** | | | | | | |
| 41 | Routenoptimierer | Optimiert physische Touren für Service, Pflege, Logistik oder Delivery. | In: Stops, Zeiten, Restriktionen. Out: route plan, expected KPIs. | OR, RL optional, Graph | Pflege, Dispatch, Fleet charging, Cold chain | 4, 27, 50, 61, 95 | Deterministische Solver bevorzugen; Heuristik nur als Fallback. |
| 42 | Schedule Optimizer | Baut optimale Zeitpläne für Personen, Ressourcen und Jobs. | In: Slots, Skills, Regeln. Out: plan with constraints satisfied. | Constraint solving | Termine, Pflege, FM, Shift exchange | 1, 4, 31, 59, 81 | Reserve-/Hold-Zustände explizit modellieren. |
| 43 | Best-Next-Action Planner | Wählt den nächsten sinnvollen Schritt pro Fall. | In: case state, policies, history. Out: ordered actions. | LLM planner, Regeln | Triage, Homecare, Tax, Contact Center | 2, 8, 23, 67, 83 | Aktionskatalog begrenzen; immer „why this action" loggen. |
| 44 | Dynamic Pricing Engine | Setzt Preise oder Rabatte kontext- und kapazitätsabhängig. | In: demand, supply, policy, risk. Out: suggested price. | Causal ML, Bandits | Hospitality, EV charging, Parking, Beauty, Surplus | 37, 41, 51, 80, 82 | Preisgrenzen, Anti-discrimination und Explainability erforderlich. |
| 45 | Resource Allocation Optimizer | Verteilt knappe Ressourcen über Standorte, Fälle oder Märkte. | In: assets, demand, priorities. Out: allocation plan. | OR, Graph | Radiology, capacity markets, warehouse, industry flex | 7, 25, 43, 62, 100 | hard_constraints vs. soft_constraints getrennt halten. |
| 46 | Queue Prioritizer | Sortiert Arbeitsvorräte nach SLA, Risiko und Wertbeitrag. | In: queue events, scores. Out: ranked work queue. | Regeln, Ranking | Triage, discharges, public services, legal aid | 2, 15, 84, 86, 96 | Keine versteckten Priorisierungsmerkmale; rationale ausgeben. |
| 47 | Cross-System Workflow Orchestrator | Koordiniert Tasks über CRM, ERP, Ticketing, Clearing und Doksysteme. | In: case state, tool states. Out: workflow transitions, events. | Agent orchestration, rules | Discharge, payments, DD, travel, public sector | 12, 15, 35, 65, 84 | Saga-Pattern; kompensierende Aktionen definieren. |
| 48 | Exception Recovery Planner | Baut Wiederanlaufpfade bei Fehlern, Ausfällen oder Konflikten. | In: failed events, context. Out: retry/rollback/escalate plan. | Regeln, LLM | Payments, damage, transport, travel | 17, 48, 61, 65, 95 | Kein blindes Retriggern; idempotente Recovery-Runs. |
| 49 | Inventory- und Replenishment-Optimizer | Steuert Bestand und Nachschub nach Forecast und Servicelevel. | In: stock, demand, lead time. Out: replenishment actions. | TSF, OR | Pharma substitution, spare parts, returns, retail, agri | 11, 58, 63, 76, 92 | SKU-master als SoT; Substitute und MOQ modellieren. |
| 50 | Negotiation- und Proposal Optimizer | Erzeugt preis- und regelkonforme Angebote, Gegenvorschläge oder RFP-Antworten. | In: Anforderungen, Referenzen, Policy. Out: proposal draft, trade-offs. | LLM, retrieval, optimization | Trade finance, procurement, public bids, materials | 22, 55, 56, 64, 66 | Freigabestufe vor Versand; Halluzinationsverbot via Retrieval. |
| **F** | **Abrechnung, Settlement & Metering** | | | | | | |
| 51 | Usage Meter Collector | Misst jede fachliche Nutzung in abrechenbaren Einheiten. | In: events, sessions, sensor/use data. Out: metering events. | Event processing | EV, VPP, fleet, SaaS usage | 41, 43, 50, 51, 98 | Immer usage_unit, actor, asset, time_window, source loggen. |
| 52 | Event-to-Invoice Mapper | Übersetzt Events in Rechnungspositionen oder Leistungsziffern. | In: usage events, tariff rules. Out: invoice lines / service codes. | Regeln, LLM assistiert Mapping | Praxisabrechnung, reconciliation, transit, public billing | 3, 17, 53, 61, 97 | Output als line-item JSON; Tax/Code-Engine getrennt halten. |
| 53 | Revenue Splitter | Verteilt Erlöse regelbasiert über Anbieter, Plattform, Referrer und Worker. | In: settled revenue, contracts. Out: payout ledger. | Regeln, Ledger logic | Remittance, charging, VPP, licensing, delivery | 18, 41, 43, 74, 77 | Double-entry-Ledger; Split-Regeln versionieren. |
| 54 | Reconciliation Matcher | Gleicht Rechnungen, Buchungen, Avis, Stornos und Gutschriften ab. | In: banking/ERP/payment records. Out: matched sets, breaks. | Matching ML, Regeln | B2B payments, collections, freight, travel, e-invoice | 17, 24, 61, 65, 97 | ISO 20022/SEPA-Felder ausnutzen; unmatched cases separat. |
| 55 | Dynamic Tariff Calculator | Berechnet kontextabhängige Tarife, Preise oder Zuschläge. | In: tariff tables, context. Out: price breakdown. | Regeln, optimization | EV charging, power tariffs, fleet, transport | 41, 42, 50, 53, 54 | Tariff engine deklarativ; keine Logik in Prompts verstecken. |
| 56 | SLA- und Outcome-Meter | Misst Erfüllung gegen SLA, Qualität oder Outcome-basiertes Pricing. | In: process events, QA data. Out: SLA status, billable outcome. | Event analytics | FM, field service, BPO, staffing, audits | 31, 59, 67, 69, 76 | Outcome-Schema vor Vertragsstart festlegen. |
| 57 | Payout Scheduler | Orchestriert zeitlich und bedingungslogisch Auszahlungen. | In: ledger, milestones, holds. Out: payout orders. | Regeln, workflow | Remittance, procurement finance, VPP, shifts, creators | 18, 25, 43, 69, 74 | Hold/release/reverse explizit; Kalender und Cutoffs berücksichtigen. |
| 58 | Dispute Resolver | Erstellt strukturierte Streitfälle zu Preis, Leistung oder Qualität. | In: contested events/docs. Out: dispute bundle, proposed resolution. | LLM, retrieval, rules | Claims, collections, transit, freight, small claims | 20, 24, 53, 61, 87 | Belege unveränderlich referenzieren; menschliche Entscheidungspfade vorsehen. |
| 59 | Fraudulent Billing Detector | Findet anomale Abrechnungsmuster, Duplikate und Schätzbetrug. | In: line items, behavior, history. Out: fraud score, flags. | Anomaly detection, GNN | Health billing, insurance, EPR, maritime | 3, 20, 21, 47, 54 | Hoher False-positive-Schaden: nur Review-Trigger, kein Auto-Block. |
| 60 | Cost Attribution Engine | Ordnet Kosten verursachungsgerecht Teams, Kund:innen, Assets oder Aufgaben zu. | In: spend, usage, org graph. Out: cost allocations. | Rules, graph, analytics | Insurance, travel, learning, FinOps, agentic SaaS | 19, 65, 73, 97, 98 | Cost center, tenant, case, asset strikt trennen. |
| **G** | **Compliance, Audit & Reporting** | | | | | | |
| 61 | Policy Rule Engine | Prüft Fälle gegen rechts-, vertrags- oder prozessbezogene Regeln. | In: normalized case + policy set. Out: allow/deny/needs review. | Regeln, DSL, LLM für Erklärung | Genehmigung, carbon, packaging, procurement, public service | 34, 46, 47, 56, 84 | Regeln deklarativ; Policies versionieren und testbar machen. |
| 62 | Retention-/Deletion-Orchestrator | Steuert Löschfristen, Archivierung und Datensparsamkeit über Systeme hinweg. | In: records, legal basis, retention rules. Out: retention actions. | Regeln, workflow | Health, legal, public services, cyber | 1, 8, 68, 83, 96 | DSGVO-Fristen/Exceptions modellieren; Löschbeleg speichern. |
| 63 | Audit-Trail Composer | Baut aus Events einen lesbaren, prüfbaren Verlauf pro Fall/Transaktion. | In: raw events. Out: ordered audit narrative + evidence links. | Event analytics, LLM summarization | Payments, insurance, ESG, freight, public services | 17, 21, 46, 61, 84 | Append-only event store; Mensch- und Systemaktionen getrennt markieren. |
| 64 | Explainability Generator | Erzeugt knappe, fallbezogene Begründungen zu Scores, Klassifikationen und Entscheidungen. | In: model output + features. Out: explanation bundle. | LLM, SHAP-like methods | Triage, claims, risk, recruiting, cyber | 15, 20, 35, 71, 96 | Explanation nie aus Rohprompts ableiten; echte Feature-Bezüge verwenden. |
| 65 | AI-Act Risk Triage | Prüft, ob ein Use Case eher gering-, transparent- oder hochrisikorelevant ist. | In: use case, domain, user group. Out: risk class hint, obligations list. | Regeln, LLM assistiert | Recruiting, public service, legal aid, cyber, agents | 71, 83, 84, 86, 96 | Compliance-Skill, kein Rechtsgutachten; Zweifel als needs_legal_review. |
| 66 | Consent-/Lawful-Basis Checker | Prüft, ob Datenverarbeitung auf tragfähiger Grundlage und im Scope erfolgt. | In: subject, purpose, dataset. Out: lawful basis status. | Regeln, graph | Health, homecare, translation, public sector | 1, 8, 13, 83, 91 | Zweckbindung maschinenlesbar erzwingen; Art.-9-Daten gesondert markieren. |
| 67 | Sanctions-/KYC-/AML Screen | Prüft Parteien und Zahlungen gegen Identitäts-, Sanktions- oder AML-Logiken. | In: identities, transaction data. Out: hits, review flags. | Entity resolution, graph, rules | Remittance, trade finance, debt, freelancer payroll | 18, 22, 24, 70, 96 | Keine fuzzy auto-denials; Treffer in Review-Queue. |
| 68 | Qualitäts- und Drift-Monitor | Überwacht Modellgüte, Datenverschiebung und Prozessfehler. | In: predictions, labels, ops metrics. Out: alerts, retrain suggestions. | Monitoring, stats, ML Ops | Radiology, underwriting, queueing, recruiting, cyber | 7, 20, 31, 71, 96 | Slice-basierte Metriken; Governance für Retraining. |
| 69 | Regulatorischer Report-Generator | Erzeugt normierte Reports aus Betriebs- und Falldaten. | In: normalized ledger/events. Out: report packages. | Regeln, templating, LLM summarization | ETS, maritime, procurement, trials, e-invoicing | 46, 54, 56, 89, 97 | Output bevorzugt XML/CSV/PDF plus machine-readable JSON. |
| 70 | Evidence Pack Assembler | Bündelt alle Prüfbelege für Audit, Due Diligence oder Aufsicht. | In: events, docs, screenshots, models. Out: evidence bundle. | Workflow, retrieval, LLM summary | Claims, recycling, public bids, grants | 21, 40, 46, 56, 90 | Hashes, timestamps und source refs unveränderlich speichern. |
| **H** | **Human-in-the-loop & Quality Control** | | | | | | |
| 71 | Confidence Gating | Schaltet je nach Sicherheit zwischen Auto, Assist und Human Review um. | In: model outputs + confidence. Out: execution mode. | Calibration, rules | Triage, imaging, recruiting, cyber | 2, 7, 20, 71, 96 | Confidence kalibrieren; keine nackten Logits als Gate verwenden. |
| 72 | Annotation Workbench | Oberfläche und Backend für Labeling, Review und Korrekturtraining. | In: items, schema. Out: gold labels, disagreements. | HITL tooling | Education, QC, trials, cyber | 72, 76, 89, 96 | Rollenrechte, adjudication und sampling strategisch aufsetzen. |
| 73 | Reviewer Copilot | Unterstützt Reviewer mit Zusammenfassung, Evidenzlinks und Präzedenzfällen. | In: review task. Out: draft decision support. | LLM, retrieval | Billing, claims, procurement, legal | 3, 21, 56, 68, 87 | Nur Assist-Modus; final decision vom Menschen. |
| 74 | Vier-Augen-Workflow | Erzwingt Doppelprüfung bei kritischen Fällen oder Auszahlungen. | In: task, risk level. Out: approval states. | Workflow, rules | Insurance, public sector, legal, cyber | 19, 21, 68, 84, 96 | Reviewer-Trennung technisch erzwingen; kein gemeinsames Konto. |
| 75 | Active-Learning Sampler | Wählt die informativsten Fälle für Nachlabeling und Modellverbesserung. | In: unlabeled pool, uncertainty. Out: label queue. | Active learning | Intake, QC, forecasting, cyber | 11, 20, 31, 76, 96 | Budget- und Balance-Constraints im Sampling ergänzen. |
| 76 | Ground-Truth Builder | Baut belastbare Referenzdaten aus mehreren Quellen und Reviews auf. | In: raw cases, labels, outcomes. Out: curated truth set. | Data curation, rules | Tutoring, shelf audit, trials, cyber | 72, 76, 89, 96 | Outcome-Leakage verhindern; Freeze-Snapshots für Benchmarking. |
| 77 | Red-Team/Testfall-Generator | Erzeugt adversariale, randständige und policy-kritische Testfälle. | In: policies, known failures. Out: stress test suite. | LLM, fuzzing | AI compliance, recruiting, public service, security | 65, 71, 83, 96, 98 | Separate sichere Testumgebung; Ergebnisse versioniert sichern. |
| 78 | Feedback-Miner | Analysiert Nutzer-, Partner- und Bearbeiterfeedback auf systematische Probleme. | In: Feedback, tickets, ratings. Out: themes, fix suggestions. | Topic modeling, LLM | Scheduling, hospitality, creator, delivery, beauty | 1, 37, 75, 77, 80 | Feedback mit Produkt-/Policy-Versionen joinen. |
| 79 | Correction-to-Rule Learner | Leitet aus wiederkehrenden Korrekturen neue Regeln oder Prompt-Constraints ab. | In: edits, overrides. Out: proposed rule changes. | Pattern mining, LLM | Billing, reconciliation, procurement, public billing | 3, 17, 56, 61, 97 | Änderungen nie automatisch live schalten; Review-Board vorsehen. |
| 80 | Safe Fallback Handler | Führt bei Unsicherheit kontrolliert in Formulare, Checklisten oder menschliche Bearbeitung zurück. | In: failure state. Out: fallback path. | Regeln, workflow | Triage, discharges, leak claims, public services | 2, 15, 48, 84, 96 | Fallback ist Produktfunktion, nicht nur Error-Page. |
| **I** | **Agentic Orchestration & Tool-Use** | | | | | | |
| 81 | Tool Selector | Wählt für einen Schritt das richtige Tool, Modell oder Subsystem. | In: goal, context, tool registry. Out: chosen tool + args. | LLM router, rules | Procurement, public sector, freight, SaaS brokers | 55, 56, 61, 83, 97 | Tool-Metadaten als Registry pflegen; Whitelist statt freier Auswahl. |
| 82 | Multi-Step Plan Synthesizer | Zerlegt ein Ziel in prüfbare Teilaufgaben mit Dependencies. | In: objective, constraints. Out: executable plan. | LLM planning | Genehmigung, DD, travel, benefits | 12, 34, 47, 65, 83 | Planstruktur als DAG/JSON, nicht nur als Text. |
| 83 | Memory- und Context Manager | Hält fallrelevanten Kontext über Schritte, Sessions und Kanäle konsistent. | In: events, notes, docs. Out: context state. | Retrieval, summarization | Termine, DD, legal review, public service | 1, 15, 35, 68, 84 | Kurzzeit- vs. Langzeitkontext trennen; TTLs definieren. |
| 84 | API Contract Validator | Prüft vor Tool-Aufruf Daten, Pflichtfelder, Datentypen und Versionen. | In: candidate payload. Out: validated payload/errors. | Regeln, schema validation | Payments, EV, procurement, e-invoice, agents | 17, 41, 56, 97, 98 | JSON Schema/OpenAPI/AsyncAPI; Fail-fast vor Side Effects. |
| 85 | Transactional Action Guard | Verhindert gefährliche, irreversible oder doppelte Aktionen. | In: planned action, state. Out: allow/hold/block. | Regeln, risk engine | Remittance, debt, VPP, public actions, SaaS agents | 18, 24, 43, 84, 98 | Idempotency keys und dry-run Mode obligatorisch. |
| 86 | Event-Driven Agent Runtime | Führt Agents zustandsbasiert auf Events statt rein synchronen Calls aus. | In: domain events. Out: scheduled actions, state transitions. | Workflow engines, agents | Discharge, EV, damage, freight, cyber | 15, 41, 48, 61, 96 | Event bus + DLQ; replay-fähig aufbauen. |
| 87 | Multi-Agent Coordinator | Koordiniert spezialisierte Agents mit Rollen, Budgets und Übergaben. | In: goal + subagents. Out: combined plan/result. | Multi-agent orchestration | VPP, public workflows, freight, contact center | 43, 47, 61, 83, 98 | Ein Supervisor-Agent mit Policy-Gates ist robuster als freie Schwärme. |
| 88 | Retrieval-and-Tool Fusion | Verbindet Wissensretrieval direkt mit Tool-Ausführung und Ergebnisvalidierung. | In: query, corpora, tools. Out: answer + executed tool results. | RAG, LLM, tool use | Vergabe, legal, benefits, grants | 34, 56, 68, 83, 90 | Quellenzitate und Tool-Outputs strikt trennen. |
| 89 | Goal- und Constraint Tracker | Überwacht, ob der Agent noch im Scope, Budget und Compliance-Rahmen arbeitet. | In: plan, state, constraints. Out: status, violations. | Rules, planning | Tarife, workflows, fleet, public cases, industry flex | 42, 47, 50, 83, 100 | must_not, Budget, Deadline, privacy scope als harte Constraints führen. |
| 90 | Sandboxed Execution Broker | Isoliert riskante Tools wie Dateioperationen, Parser oder Browseraktionen. | In: task, artifact refs. Out: sandbox result, logs. | Sandboxing, policy engines | Legal docs, public sector, grants, cyber, agents | 68, 84, 90, 96, 98 | Netzwerk-/Dateirechte minimal halten; Vollprotokoll speichern. |
| **J** | **Domain-specific Skills** | | | | | | |
| 91 | FHIR-/DICOM-Clinical Packager | Verpackt klinische Dokumente, Metadaten und Bildreferenzen interoperabel. | In: clinical docs, images, patient refs. Out: FHIR/DICOM bundles. | Regeln, mapping, VLM optional | Healthcare records, radiology, homecare, trials | 1, 7, 8, 12, 89 | FHIR DocumentReference/Patient/Encounter sauber befüllen; Gesundheitsdaten besonders schützen. |
| 92 | Medizin-Coding- und Abrechnungs-Copilot | Unterstützt Kodierung und Leistungsabrechnung aus Dokumentation und Verlauf. | In: Arztbrief, Diktat, Befund. Out: Code-Vorschläge, Prüfflags. | LLM, retrieval, rules | Praxisabrechnung, Zahnlabor, Arznei, Pathologie | 3, 10, 11, 12, 14 | Kein vollautonomes Final-Coding ohne Review; Codeversionen speichern. |
| 93 | Energy Flex Dispatch Agent | Schaltet/vermarktet flexible Lasten oder Speicher nach Preis, Netzsignal und Nebenbedingungen. | In: tariffs, telemetry, asset state. Out: dispatch plan, bid events. | TSF, OR, RL optional | Dynamic tariff, VPP, demand response, grid connection | 42, 43, 45, 49, 100 | OCPP/OCPI/SCADA-artige Schnittstellen sauber kapseln; Safety-first. |
| 94 | LV-/Nachtrag-Interpreter für Bau | Versteht Leistungsverzeichnisse, Nachträge und Mengengerüste domänenspezifisch. | In: LV, Pläne, Nachträge. Out: Positionsstruktur, Konfliktliste, Preisbasis. | LLM, OCR, rules | Baurechnung, Renovierung, Genehmigung, Bauabfall, Materialeinkauf | 26, 33, 34, 40, 64 | Positionsnummern, Einheiten, Mengen nie im Prompt „schätzen" lassen. |
| 95 | Shipment Exception Agent | Bearbeitet Versandprobleme wie Delay, Damage, Missing Docs oder Customs Holds. | In: shipment events, docs. Out: exception case, actions, ETA update. | TSF, LLM, rules | Maritime, freight, warehouse, cold chain | 54, 61, 62, 95 | Event-Correlation über consignment/container IDs; SLAs messen. |
| 96 | Covenant- und Invoice-Risk Agent | Prüft Rechnungen, Verträge und Bonitäts-/Covenant-Signale für Finanzierungsentscheidungen. | In: invoices, bank data, contracts. Out: risk memo, flags, decision support. | GNN, GBM, LLM | Factoring, reconciliation, trade finance, procurement finance | 16, 17, 22, 25, 35 | Finanzdaten feldgenau extrahieren; keine autonomen Kreditentscheidungen ohne Governance. |
| 97 | XRechnung-/Vergabe-Agent | Baut, validiert und verarbeitet öffentliche Rechnungen und Ausschreibungsartefakte. | In: order/invoice/bid docs. Out: XRechnung/XML, submission pack, validation errors. | Regeln, XML/UBL, LLM assistiert | Public procurement, kommune, grants | 56, 84, 90, 97 | XRechnung/EN16931 und Schematron-Validierung als harte Pipeline. |
| 98 | Shelf- und Return-Decision Agent | Erkennt Shelf-Probleme, Retourenpfade und Recovery-Entscheidungen im Handel. | In: shelf images, order/return data. Out: issue class, routing, recovery value. | Vision, VLM, optimization | Recommerce, shelf audit, local delivery, surplus food | 63, 76, 77, 82 | Store-/SKU-Masterdaten als SoT; Recovery-Regeln versioniert. |
| 99 | Plot-/Weather-Advisory Agent | Kombiniert Schlag-, Wetter- und Inputdaten zu handlungsnahen Empfehlungen. | In: field boundaries, weather, sensors, crop plan. Out: advisory actions, risk alerts. | TSF, geospatial ML, rules | Farm inputs, irrigation, crop insurance, cold chain | 92, 93, 94, 95 | GeoJSON/Raster sauber trennen; Empfehlungen als Decision Support. |
| 100 | Property-/Insurance Damage Vision Agent | Bewertet Sachschäden an Fahrzeugen, Gebäuden oder Geräten visuell im Erstkontakt. | In: images/video + FNOL data. Out: damage classes, severity, review flag. | Vision, VLM, anomaly detection | Kfz claims, property claims, waste, repair | 20, 21, 39, 48, 79 | Bounding boxes + Evidenzbilder zurückgeben; menschliche Freigabe bei Zahlentscheidungen. |

## Exemplarischer Agent-Workflow

Acht exemplarische Skills spielen in einem robusten Agent-Workflow zusammen. Die fachliche Logik ist absichtlich generisch gehalten, damit sie sowohl auf Arzttermine, Handwerker-Dispatch, Kfz-Schaden, öffentliche Anträge als auch B2B-Abrechnung passt:

```
Multimodal Intake Gateway
  → Dokumenttyp-Klassifikator
  → Entity- und Feld-Extractor
  → Provider Matcher oder Skill-based Dispatch Router
  → Best-Next-Action Planner
  → Usage Meter Collector
  → Event-to-Invoice Mapper
  → Audit-Trail Composer
  → Confidence Gating und Human Review
  → (bei Bedarf) Correction-to-Rule Learner
```

Architektonisch ist der wichtigste Punkt hier die Trennung von Fachoutput und Kontrolloutput: Jeder Skill sollte nicht nur „seine" Antwort liefern, sondern parallel Metadaten für Confidence, Provenance, Policy und Metering ausgeben. Damit bleiben Human Oversight, Reconciliation und spätere Erlösverteilung direkt anschlussfähig. Für Hochrisiko-/regulierte Fälle ergibt sich diese Struktur praktisch auch aus den Anforderungen an Logging, Nachvollziehbarkeit und menschliche Aufsicht.

## Priorisierung und Fazit

**FINDINGS:** Die höchste kurzfristige Hebelwirkung haben die Skills 1–10, 11–20, 21–30, 51–60 und 61–70. Diese Gruppen bilden zusammen den minimalen Infrastrukturkern: Intake, Semantik, Clearing/Routing, Metering/Settlement und Compliance. Ohne diese fünf Blöcke bleibt ein Agent nettes Frontend; mit ihnen wird er plattformfähig.

**DECISION:** Für einen realen Build-Plan empfiehlt sich eine Reihenfolge in drei Wellen.

- **Erste Welle:** 1, 2, 9, 11, 13, 21, 29, 51, 54, 61, 63, 71, 84, 85.
- **Zweite Welle:** 15, 31, 33, 41, 42, 43, 56, 68, 73, 83, 86.
- **Dritte Welle:** vertikale Skills 91–100 je nach Zielmarkt.

**NEXT ACTION:** Der rationalste nächste Schritt ist nicht, sofort 100 getrennte Agents zu bauen, sondern zuerst eine Skill Registry mit einheitlichem Contract zu definieren: `input_schema`, `output_schema`, `policies`, `metering_unit`, `confidence_policy`, `fallback_policy`, `allowed_tools`, `regulatory_tags`. Danach können die vertikalen Agents aus denselben Bausteinen zusammengesetzt werden.

### Kernsatz für die Umsetzung

Erst Skills mit deterministischem Vertrag und Auditfähigkeit bauen, dann Agents. Das ist für Deutschland und regulierte Märkte besonders wichtig, weil Standards, Datenschutz und Nachvollziehbarkeit keine Nacharbeiten sind, sondern Architekturvorgaben.

## Vollständiges PDF

[PDF öffnen oder herunterladen](/SSID-docs/downloads/research/ai-infrastructure/katalog-100-ki-skills-und-ki-agents.pdf) · [Manifest (JSON)](/SSID-docs/downloads/research/ai-infrastructure/catalog-manifest.json)

**Dateiformat:** PDF 1.7
**Seiten:** 11
**Seitengröße:** A4
**SHA-256:** `5d534f595b960a8e37434cee889ab1f60b67be3b4ff272d488afbbb1a294d89d`

## Verwandte Seiten

- [AI Infrastructure Catalogs — Übersicht](/research/ai-infrastructure-catalogs/)
- [Hundert KI-gestützte Business-Modelle nach dem Infrastrukturmuster](/research/100-ai-business-models-infrastructure-pattern/)

## Quellen

Quellenangaben aus dem PDF-Original (Fußnoten 1–12), zusammengefasst:

1. AI Act enters into force — European Commission. https://commission.europa.eu/news-and-media/news/ai-act-enters-force-2024-08-01_en
2. Consolidated TEXT: 32016R0679 (DSGVO) — EN — 04.05.2016. https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A02016R0679-20160504
3. ePA MHD DocumentReference — Definitions — Implementation Guide ePA MHD Service v1.1.2. https://gemspec.gematik.de/ig/fhir/epa-mhd/1.1.2/StructureDefinition-epa-mhd-document-reference-definitions.html
4. Regulation (EU) 2024/1689 (EU AI Act). https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ%3AL_202401689
5. Nutzungsbedingungen (XRechnung/OZG-RE). https://xrechnung-bdr.de/edi/assets/ozg/de/Nutzungsbedingungen-OZG-RE.pdf
