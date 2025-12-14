# Battery Intelligence Brain

This project builds a **Battery Intelligence Brain**: a stable orchestration layer that sits between changing inputs (telemetry, markets, models, synthetic data) and outputs (answers, reports, decisions).

## North Star
The Brain stays constant. Inputs and models can change later.

## Anchor Document
The system is governed by the Brain Contract:
- `docs/brain_contract.md`

**Rule:** If a feature does not fit the Brain Contract, it does not belong in the system (until the contract is revised explicitly).

## Repo Structure (mirrors the contract)
- `brain/` — orchestration, reasoning, confidence
- `adapters/` — telemetry, market, model ports (replaceable)
- `knowledge_base/` — operational knowledge (glossary, playbooks, thresholds)
- `evidence/` — evidence bundle generation
- `outputs/` — role-based formatting
- `synthetic_data/` — synthetic datasets + generators
- `docs/` — contract + project docs

## How We Work
- GitHub Issues = one thinking problem
- GitHub Projects = Kanban (Backlog / Active / Blocked / Done)
- Small increments. No drifting architecture.


## Brain v0

# Battery Intelligence Brain (v0)

A deterministic, auditable reasoning system for analyzing battery telemetry and producing explainable insights.

This repository contains **Brain v0** — a frozen MVP that focuses on:
- clear reasoning
- explicit uncertainty
- traceable evidence
- zero dependency on proprietary models or LLMs

---

## What the Brain does (v0)

The Brain can:
- Ingest telemetry from a CSV-backed adapter (synthetic dataset v0).
- Compare State-of-Health (SoH) degradation trends across assets.
- Detect temperature spike anomalies.
- Link multiple analyses into a single explanatory response.
- Emit a stable, structured JSON response (`BrainResponse`) containing:
  - `answer`
  - `confidence`
  - `evidence`
  - `data`

The Brain **does not**:
- Claim causality (only plausible contributors).
- Predict remaining useful life (RUL).
- Perform financial or revenue impact analysis.
- Apply electrochemical or physics-based models.
- Use proprietary data or machine learning models.
- Use LLMs for reasoning.

See [`docs/brain_capabilities_v0.md`](docs/brain_capabilities_v0.md) for the frozen v0 specification.

---

## Project Structure (key parts)

brain/
- runner_v0.py # SoH degradation comparison
- anomaly_scan_v0.py # Temperature anomaly detection
- linked_reasoning_v0.py # Multi-intent explanatory reasoning
- router_v0.py # Unified entrypoint (recommended)
- contracts.py # BrainResponse + Confidence contracts

adapters/
- telemetry/
- csv_adapter.py # CSV telemetry adapter

evidence/
- builder.py # Evidence bundle construction

synthetic_data/
- generated/v0/ # Synthetic telemetry dataset

docs/
- brain_capabilities_v0.md # Frozen Brain v0 scope + guarantees

## How to run the Brain (recommended)

All interaction should go through the **Brain Router v0**.

### 1 Compare degradation trends

python3 -m brain.router_v0 \
  --question "Is rack_02 degrading faster?" \
  --assets rack_01 rack_02

python3 -m brain.router_v0 \
  --question "Did rack_02 have a temperature spike?" \
  --assets rack_02

python3 -m brain.router_v0 \
  --question "Why is rack_02 degrading?" \
  --assets rack_01 rack_02

Each command outputs a structured JSON response suitable for:

- CLI inspection

- API responses

- dashboards

- downstream systems

## BrainResponse format (v0)

Every response follows the same contract:

{
  "answer": "...",
  "confidence": {
    "band": "high | medium | low",
    "reasons": ["..."],
    "escalation": "none | ask_followup | human_review"
  },
  "evidence": { "... auditable bundle ..." },
  "data": { "... structured metrics & hypotheses ..." }
}

## Confidence semantics (v0)

- High: Sufficient data coverage; stable computations.

- Medium: One or more data limitations (e.g. missing telemetry).

- Low: Insufficient or contradictory data; follow-up required.

Confidence is deterministic and intent-local in v0.

## Phase status

Phase 1: Complete and frozen
(Telemetry ingestion, evidence, reasoning, router, documentation)

Phase 2 (planned):

- Confidence engine centralization

- Physics model integration

- Proprietary ML / digital twin hooks

- Real telemetry adapters

- API surface (FastAPI)

- Optional LLM narration layer (non-decisional)


## Philosophy

This system is intentionally conservative.

The Brain prefers:

- explaining what is known

- labeling what is uncertain

- refusing to guess when data is insufficient

It is designed to attach to proprietary intelligence later — not replace it.