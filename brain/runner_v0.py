from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from adapters.telemetry import CsvTelemetryAdapter
from adapters.telemetry.csv_adapter import TimeWindow
from evidence import EvidenceBuilder


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _filter_numeric(rows: List[Dict[str, Any]], key: str) -> List[Tuple[datetime, float]]:
    out: List[Tuple[datetime, float]] = []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            out.append((_parse_iso(r["timestamp"]), float(v)))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    return out


def _slope_per_day(points: List[Tuple[datetime, float]]) -> Optional[float]:
    """
    Very simple slope estimate: (mean(last 10%) - mean(first 10%)) / days_span
    Stable enough for synthetic v0. Returns units: value per day.
    """
    if len(points) < 20:
        return None

    n = len(points)
    k = max(3, int(0.1 * n))
    first = [v for _, v in points[:k]]
    last = [v for _, v in points[-k:]]
    m1 = _mean(first)
    m2 = _mean(last)
    if m1 is None or m2 is None:
        return None

    t0 = points[0][0]
    t1 = points[-1][0]
    days = max(1e-6, (t1 - t0).total_seconds() / 86400.0)
    return (m2 - m1) / days


@dataclass
class BrainResult:
    answer: str
    confidence: Dict[str, Any]
    evidence: Dict[str, Any]


def compare_soh_trend_v0(
    adapter: CsvTelemetryAdapter,
    asset_ids: List[str],
    *,
    start_iso: str,
    end_iso: str,
    day7_boundary_iso: str,
    role: str = "asset_manager",
) -> BrainResult:
    question = f"Which asset is degrading faster between {asset_ids} in the given window?"
    intent = "soh_trend_compare_v0"
    ev = EvidenceBuilder.start(question, intent, role=role)

    tw = TimeWindow.from_iso(start_iso, end_iso)
    boundary = _parse_iso(day7_boundary_iso)

    per_asset = {}
    gaps_notes = []
    for asset_id in asset_ids:
        ts = adapter.get_timeseries(asset_id, ["soh", "temperature"], tw, include_missing=True)

        # record data_used
        rows = ts["rows"]
        missing = sum(1 for r in rows if r.get("data_quality_flag") == "missing")
        quality_notes = f"{missing} missing rows" if missing else "no missing rows"
        ev.add_data_used(
            source_type="telemetry",
            source_name=str(adapter.base_dir.name),
            query={"asset_id": asset_id, "signals": ["soh", "temperature"], "granularity": "15m"},
            time_window=ts["time_window"],
            row_count=ts["row_count"],
            quality_notes=quality_notes,
        )

        # split pre/post boundary
        soh_points = _filter_numeric(rows, "soh")
        pre = [(t, v) for (t, v) in soh_points if t < boundary]
        post = [(t, v) for (t, v) in soh_points if t >= boundary]

        pre_slope = _slope_per_day(pre)
        post_slope = _slope_per_day(post)

        per_asset[asset_id] = {
            "pre_slope_per_day": pre_slope,
            "post_slope_per_day": post_slope,
            "missing_rows": missing,
            "row_count": ts["row_count"],
        }

        if missing > 0:
            gaps_notes.append(f"{asset_id} has {missing} missing telemetry rows in-window.")

    # Decide “degrading faster” = more negative post slope
    # If slopes missing, confidence drops.
    def score(a: Dict[str, Any]) -> Optional[float]:
        s = a.get("post_slope_per_day")
        return s if s is not None else None

    valid = [(aid, score(per_asset[aid])) for aid in asset_ids if score(per_asset[aid]) is not None]
    if not valid:
        ev.add_gap("No valid post-boundary SoH slope could be computed for any asset.")
        answer = "Insufficient data to compare degradation trends (post-boundary slope unavailable)."
        confidence = {
            "band": "low",
            "reasons": ["Missing or insufficient SoH data in the comparison window."],
            "escalation": "ask_followup",
        }
        return BrainResult(answer=answer, confidence=confidence, evidence=ev.finalize())

    # pick most negative slope (fastest decline)
    worst_asset, worst_slope = sorted(valid, key=lambda x: x[1])[0]

    # Add computation evidence
    outputs = {"boundary": day7_boundary_iso, "per_asset": per_asset, "winner": worst_asset}
    ev.add_computation(
        name="soh_slope_compare",
        inputs=["soh"],
        method="Split window into pre/post boundary; estimate slope per day using mean(last 10%) - mean(first 10%). Compare post-boundary slopes across assets.",
        outputs=outputs,
        assumptions_refs=["ASSUMP_SOH_IS_VALID_PROXY_V0"],
    )

    # Add KB rule placeholder ref (structure-first)
    ev.add_kb_rule(
        kb_ref="knowledge_base/thresholds/README.md",
        rule_summary="Threshold framework placeholder (v0).",
        impact_on_answer="No threshold enforcement in v0; comparison is relative only.",
    )

    # Confidence (v0): rule-based
    reasons = []
    band = "high"
    escalation = "none"

    # Missingness penalty
    any_missing = any(per_asset[aid]["missing_rows"] > 0 for aid in asset_ids)
    if any_missing:
        band = "medium"
        reasons.append("Telemetry contains missing intervals; trend confidence reduced.")

    # Slope robustness penalty
    any_none = any(per_asset[aid]["post_slope_per_day"] is None for aid in asset_ids)
    if any_none:
        band = "medium"
        reasons.append("One or more assets lacked sufficient post-boundary points; comparison limited.")

    # If both missing + slope issues -> low
    if any_missing and any_none:
        band = "low"
        escalation = "ask_followup"
        reasons.append("Data quality issues may bias comparison; consider extending the window.")

    # Record gaps as evidence
    for g in gaps_notes:
        ev.add_gap(g)

    answer = (
        f"{worst_asset} appears to be degrading faster (more negative post-boundary SoH slope) "
        f"within {start_iso} → {end_iso}."
    )

    confidence = {
        "band": band,
        "reasons": reasons if reasons else ["Sufficient data coverage for a relative comparison in v0."],
        "escalation": escalation,
    }

    return BrainResult(answer=answer, confidence=confidence, evidence=ev.finalize())


def main():
    adapter = CsvTelemetryAdapter("synthetic_data/generated/v0")

    # Our synthetic world: 14 days from 2025-12-01
    start = "2025-12-01T00:00:00+00:00"
    end = "2025-12-15T00:00:00+00:00"
    # Boundary: Day 7 from start
    day7 = "2025-12-08T00:00:00+00:00"

    result = compare_soh_trend_v0(adapter, ["rack_01", "rack_02"], start_iso=start, end_iso=end, day7_boundary_iso=day7)

    print("\n=== ANSWER ===")
    print(result.answer)
    print("\n=== CONFIDENCE ===")
    print(result.confidence)
    print("\n=== EVIDENCE (truncated) ===")
    # Print evidence id + high-level keys only to keep output readable
    ev = result.evidence
    print({k: ev[k] for k in ["evidence_id", "generated_at", "intent", "role"]})
    print("data_used:", len(ev.get("data_used", [])))
    print("computations:", len(ev.get("computations", [])))
    print("gaps:", ev.get("assumptions_and_gaps", {}).get("gaps", []))


if __name__ == "__main__":
    main()
