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
