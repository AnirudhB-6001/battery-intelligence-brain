# Brain Capabilities v0 (Frozen)

## What the Brain can do (today)
- Ingest telemetry from a CSV-backed adapter (synthetic v0 dataset).
- Compare SoH degradation trends across assets using deterministic slope estimates.
- Scan for temperature spike anomalies using percentile-based thresholds.
- Link multiple intents into a single explanation while explicitly labeling hypotheses.
- Produce a stable `BrainResponse` JSON packet:
  - `answer`
  - `confidence` (band + reasons + escalation)
  - `evidence` (auditable bundle)
  - `data` (structured metrics payload)

## What the Brain refuses to do (v0)
- Claim causality (only “plausible contributor” language allowed).
- Predict future degradation or RUL.
- Provide financial impact estimates.
- Make physics-based claims (no electrochem model in v0).
- Use proprietary model outputs (none integrated in v0).
- Use LLMs for reasoning (LLM is explicitly out of scope for v0).

## Confidence meanings (v0)
### High
- Sufficient data coverage, no major gaps, computations stable, corroboration not required.

### Medium
- One or more limitations present (e.g., missing telemetry intervals), but core trend/anomaly still detectable.

### Low
- Insufficient data to compute key metrics OR contradictions OR major gaps. Requires follow-up or human review.

## Evidence guarantees (v0)
- Every answer includes an evidence bundle that records:
  - data sources used
  - computations performed
  - gaps noted
  - KB rule placeholders (if referenced)
- Evidence is designed to remain valid when telemetry sources change.

## Plug-in points (future)
- Replace synthetic telemetry with real telemetry adapters.
- Attach physics model outputs as computations.
- Attach ML/digital twin outputs as additional data sources.
- Add an LLM as a narrator ONLY (never as the source of truth).

- Introduce Confidence Engine v1 in Phase 2 to centralize scoring + reasons.
- Define structured confidence subscores: coverage, missingness, corroboration, stability.
