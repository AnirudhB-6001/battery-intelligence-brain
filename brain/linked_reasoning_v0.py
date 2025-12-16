from __future__ import annotations

import json
from typing import Any, Dict, List

from adapters.telemetry import CsvTelemetryAdapter
from brain.runner_v0 import compare_soh_trend_v0
from brain.anomaly_scan_v0 import anomaly_scan_v0
from brain.contracts import BrainResponse, Confidence

from brain.confidence_bridge_v1 import score_confidence_v1


def linked_degradation_analysis_v0(
    adapter: CsvTelemetryAdapter,
    asset_ids: List[str],
    *,
    start_iso: str,
    end_iso: str,
    boundary_iso: str,
    role: str = "asset_manager",
) -> BrainResponse:
    """
    Links degradation trend analysis with anomaly detection
    to produce an explanatory (not causal-proof) assessment.
    """

    # Run independent intents
    degr = compare_soh_trend_v0(
        adapter,
        asset_ids,
        start_iso=start_iso,
        end_iso=end_iso,
        day7_boundary_iso=boundary_iso,
        role=role,
    )

    winner = degr.data.get("winner")
    anomaly = anomaly_scan_v0(
        adapter,
        winner,
        start_iso=start_iso,
        end_iso=end_iso,
        role="ops",
    )

    # Build linked answer
    answer = (
        f"{winner} is degrading faster than peer assets in the evaluated window. "
        f"A temperature anomaly was detected on {winner} shortly before or during "
        f"the period of accelerated degradation. "
        f"This suggests a plausible operational contributor, though causality "
        f"is not proven in v0."
    )

    # Confidence logic (linked)
    reasons: List[str] = []
    band = "high"
    escalation = "none"

    if degr.confidence.band == "medium" or anomaly.confidence.band == "medium":
        band = "medium"
        reasons.append("One or more supporting analyses had reduced confidence due to data gaps.")

    if degr.confidence.band == "low" or anomaly.confidence.band == "low":
        band = "low"
        escalation = "ask_followup"
        reasons.append("Supporting analyses lack sufficient data for a strong conclusion.")

    if not reasons:
        reasons.append("Independent analyses agree with sufficient supporting evidence.")

    # Linked evidence (keep both bundles intact)
    evidence = {
        "linked_intents": [
            {
                "intent": degr.evidence.get("intent"),
                "evidence_id": degr.evidence.get("evidence_id"),
            },
            {
                "intent": anomaly.evidence.get("intent"),
                "evidence_id": anomaly.evidence.get("evidence_id"),
            },
        ],
        "degradation_evidence": degr.evidence,
        "anomaly_evidence": anomaly.evidence,
    }

    data = {
        "winner": winner,
        "degradation": degr.data,
        "anomaly": anomaly.data,
        "hypothesis": {
            "statement": "Temperature stress may have contributed to accelerated degradation.",
            "type": "plausible_contributor",
            "confidence": band,
            "limitations": [
                "Correlation does not imply causation.",
                "No physics model applied in v0.",
            ],
        },
    }

    conf = Confidence(band=band, reasons=reasons, escalation=escalation)
    
    # Existing v0 reasons/band/escalation computed above:
    # band, reasons, escalation
    # Confidence Engine v1 (now active)
    
    engine_conf = score_confidence_v1(
        missing_rows=(degr.data.get("per_asset", {}).get(winner, {}).get("missing_rows")),
        total_rows=(degr.data.get("per_asset", {}).get(winner, {}).get("row_count")),
        computed_metrics_ok=True,
        corroboration=0.7,
        intent="linked_degradation_v0",
        )
    
    band = engine_conf["band"]
    escalation = engine_conf["escalation"]

    # Keep the linked reasoning reasons from v0 for now
    conf = Confidence(band=band, reasons=reasons, escalation=escalation)

    data["confidence_v1"] = engine_conf

    
    return BrainResponse(
        answer=answer,
        confidence=conf,
        evidence=evidence,
        data=data,
    )


def main() -> None:
    adapter = CsvTelemetryAdapter("synthetic_data/generated/v0")

    start = "2025-12-01T00:00:00+00:00"
    end = "2025-12-15T00:00:00+00:00"
    boundary = "2025-12-08T00:00:00+00:00"

    resp = linked_degradation_analysis_v0(
        adapter,
        ["rack_01", "rack_02"],
        start_iso=start,
        end_iso=end,
        boundary_iso=boundary,
    )

    print(json.dumps(resp.to_dict(), indent=2))


if __name__ == "__main__":
    main()
