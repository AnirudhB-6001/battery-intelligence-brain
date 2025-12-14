from __future__ import annotations

import argparse
import json
from typing import List, Optional

from adapters.telemetry import CsvTelemetryAdapter
from brain.contracts import BrainResponse, Confidence

# intents
from brain.runner_v0 import compare_soh_trend_v0
from brain.anomaly_scan_v0 import anomaly_scan_v0
from brain.linked_reasoning_v0 import linked_degradation_analysis_v0


SUPPORTED_INTENTS = [
    "auto",
    "soh_trend_compare_v0",
    "anomaly_scan_temp_v0",
    "linked_degradation_v0",
]


def _infer_intent(question: str) -> str:
    q = (question or "").lower()

    # If user asks "why" + "degrad" -> linked reasoning
    if "why" in q and ("degrad" in q or "soh" in q):
        return "linked_degradation_v0"

    # Temperature anomaly intent
    if any(k in q for k in ["temp", "thermal", "overheat", "spike", "anomal"]):
        return "anomaly_scan_temp_v0"

    # SoH / degradation compare intent
    if any(k in q for k in ["soh", "degrad", "health", "declin", "trend", "faster"]):
        return "soh_trend_compare_v0"

    # Default: linked reasoning if multiple assets, else anomaly scan if single asset
    return "soh_trend_compare_v0"


def route(
    adapter: CsvTelemetryAdapter,
    question: str,
    assets: List[str],
    *,
    start_iso: str,
    end_iso: str,
    boundary_iso: str,
    intent: str = "auto",
    role: str = "asset_manager",
) -> BrainResponse:
    chosen = intent
    if chosen == "auto":
        chosen = _infer_intent(question)

    if chosen not in SUPPORTED_INTENTS:
        return BrainResponse(
            answer=f"Unsupported intent: {chosen}. Supported: {SUPPORTED_INTENTS}",
            confidence=Confidence(band="low", reasons=["Invalid intent supplied."], escalation="ask_followup"),
            evidence={"intent": "router_v0", "error": "unsupported_intent", "requested": chosen},
            data={"supported_intents": SUPPORTED_INTENTS},
        )

    # Dispatch
    if chosen == "soh_trend_compare_v0":
        if len(assets) < 2:
            return BrainResponse(
                answer="soh_trend_compare_v0 requires at least 2 assets to compare.",
                confidence=Confidence(band="low", reasons=["Need 2+ assets for comparison."], escalation="ask_followup"),
                evidence={"intent": "router_v0", "error": "insufficient_assets"},
                data={"required_assets": 2, "provided_assets": assets},
            )
        return compare_soh_trend_v0(
            adapter,
            assets,
            start_iso=start_iso,
            end_iso=end_iso,
            day7_boundary_iso=boundary_iso,
            role=role,
        )

    if chosen == "anomaly_scan_temp_v0":
        if len(assets) != 1:
            return BrainResponse(
                answer="anomaly_scan_temp_v0 requires exactly 1 asset.",
                confidence=Confidence(band="low", reasons=["Need exactly 1 asset for anomaly scan."], escalation="ask_followup"),
                evidence={"intent": "router_v0", "error": "invalid_assets_for_anomaly"},
                data={"required_assets": 1, "provided_assets": assets},
            )
        return anomaly_scan_v0(
            adapter,
            assets[0],
            start_iso=start_iso,
            end_iso=end_iso,
            role="ops",
        )

    if chosen == "linked_degradation_v0":
        if len(assets) < 2:
            return BrainResponse(
                answer="linked_degradation_v0 requires at least 2 assets (winner chosen from comparison).",
                confidence=Confidence(band="low", reasons=["Need 2+ assets for linked reasoning."], escalation="ask_followup"),
                evidence={"intent": "router_v0", "error": "insufficient_assets_for_linked"},
                data={"required_assets": 2, "provided_assets": assets},
            )
        return linked_degradation_analysis_v0(
            adapter,
            assets,
            start_iso=start_iso,
            end_iso=end_iso,
            boundary_iso=boundary_iso,
            role=role,
        )

    # Should never hit
    return BrainResponse(
        answer="Router reached an unreachable state.",
        confidence=Confidence(band="low", reasons=["Unexpected dispatch failure."], escalation="human_review"),
        evidence={"intent": "router_v0", "error": "unreachable"},
        data={"chosen_intent": chosen},
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Battery Intelligence Brain Router v0")
    p.add_argument("--question", required=True, help="Natural language question")
    p.add_argument("--assets", nargs="+", required=True, help="One or more asset IDs")
    p.add_argument("--intent", default="auto", choices=SUPPORTED_INTENTS, help="Force an intent or use auto")
    p.add_argument("--start", default="2025-12-01T00:00:00+00:00")
    p.add_argument("--end", default="2025-12-15T00:00:00+00:00")
    p.add_argument("--boundary", default="2025-12-08T00:00:00+00:00")
    p.add_argument("--role", default="asset_manager")
    args = p.parse_args()

    adapter = CsvTelemetryAdapter("synthetic_data/generated/v0")

    resp = route(
        adapter,
        question=args.question,
        assets=args.assets,
        start_iso=args.start,
        end_iso=args.end,
        boundary_iso=args.boundary,
        intent=args.intent,
        role=args.role,
    )

    print(json.dumps(resp.to_dict(), indent=2))


if __name__ == "__main__":
    main()
