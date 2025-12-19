from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adapters.telemetry import CsvTelemetryAdapter
from adapters.telemetry.csv_adapter import TimeWindow
from evidence import EvidenceBuilder
from brain.contracts import BrainResponse, Confidence

from brain.confidence_bridge_v1 import score_confidence_v1, gap_stats_from_rows


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
    Very simple slope estimate:
    (mean(last 10%) - mean(first 10%)) / days_span
    Returns units: value per day.
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


def compare_soh_trend_v0(
    adapter: CsvTelemetryAdapter,
    asset_ids: List[str],
    *,
    start_iso: str,
    end_iso: str,
    day7_boundary_iso: str,
    role: str = "asset_manager",
) -> BrainResponse:
    question = f"Which asset is degrading faster between {asset_ids} in the given window?"
    intent = "soh_trend_compare_v0"
    ev = EvidenceBuilder.start(question, intent, role=role)

    tw = TimeWindow.from_iso(start_iso, end_iso)
    boundary = _parse_iso(day7_boundary_iso)

    per_asset: Dict[str, Any] = {}
    gaps_notes: List[str] = []

    # --- NEW: gap clustering aggregates ---
    total_missing_rows = 0
    total_rows = 0
    missing_streak_max = 0
    missing_streaks = 0

    for asset_id in asset_ids:
        ts = adapter.get_timeseries(asset_id, ["soh", "temperature"], tw, include_missing=True)

        rows = ts["rows"]
        gap = gap_stats_from_rows(rows)

        missing = gap["missing_rows"]
        quality_notes = f"{missing} missing rows" if missing else "no missing rows"

        # aggregate gap stats (worst-case logic)
        total_missing_rows += gap["missing_rows"]
        total_rows += ts["row_count"]
        missing_streak_max = max(missing_streak_max, gap["missing_streak_max"])
        missing_streaks += gap["missing_streaks"]

        ev.add_data_used(
            source_type="telemetry",
            source_name=str(adapter.base_dir.name),
            query={"asset_id": asset_id, "signals": ["soh", "temperature"], "granularity": "15m"},
            time_window=ts["time_window"],
            row_count=ts["row_count"],
            quality_notes=quality_notes,
        )

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

    def score(a: Dict[str, Any]) -> Optional[float]:
        s = a.get("post_slope_per_day")
        return s if s is not None else None

    valid = [(aid, score(per_asset[aid])) for aid in asset_ids if score(per_asset[aid]) is not None]

    if not valid:
        ev.add_gap("No valid post-boundary SoH slope could be computed for any asset.")
        answer = "Insufficient data to compare degradation trends (post-boundary slope unavailable)."
        conf = Confidence(
            band="low",
            reasons=["Missing or insufficient SoH data in the comparison window."],
            escalation="ask_followup",
        )
        return BrainResponse(answer=answer, confidence=conf, evidence=ev.finalize(), data={"per_asset": per_asset})

    # Pick most negative slope = fastest decline
    worst_asset, _worst_slope = sorted(valid, key=lambda x: x[1])[0]

    outputs = {"boundary": day7_boundary_iso, "per_asset": per_asset, "winner": worst_asset}
    ev.add_computation(
        name="soh_slope_compare",
        inputs=["soh"],
        method="Split window into pre/post boundary; estimate slope per day using mean(last 10%) - mean(first 10%). Compare post-boundary slopes across assets.",
        outputs=outputs,
        assumptions_refs=["ASSUMP_SOH_IS_VALID_PROXY_V0"],
    )

    ev.add_kb_rule(
        kb_ref="knowledge_base/thresholds/README.md",
        rule_summary="Threshold framework placeholder (v0).",
        impact_on_answer="No threshold enforcement in v0; comparison is relative only.",
    )

    # Confidence (v0 reasons only)
    reasons: List[str] = []
    band = "high"
    escalation = "none"

    any_missing = any(per_asset[aid]["missing_rows"] > 0 for aid in asset_ids)
    if any_missing:
        band = "medium"
        reasons.append("Telemetry contains missing intervals; trend confidence reduced.")

    any_none = any(per_asset[aid]["post_slope_per_day"] is None for aid in asset_ids)
    if any_none:
        band = "medium"
        reasons.append("One or more assets lacked sufficient post-boundary points; comparison limited.")

    if any_missing and any_none:
        band = "low"
        escalation = "ask_followup"
        reasons.append("Data quality issues may bias comparison; consider extending the window.")

    for g in gaps_notes:
        ev.add_gap(g)

    answer = (
        f"{worst_asset} appears to be degrading faster (more negative post-boundary SoH slope) "
        f"within {start_iso} → {end_iso}."
    )

    data = {
        "comparison_window": {"start": start_iso, "end": end_iso},
        "boundary": day7_boundary_iso,
        "per_asset": per_asset,
        "winner": worst_asset,
    }

    # --- Confidence Engine v1 (now with gap clustering signals) ---
    engine_conf = score_confidence_v1(
        missing_rows=total_missing_rows,
        total_rows=total_rows,
        missing_streak_max=missing_streak_max,
        missing_streaks=missing_streaks,
        computed_metrics_ok=True,
        corroboration=None,
        intent=intent,
    )

    band = engine_conf["band"]
    escalation = engine_conf["escalation"]

    data["confidence_v1"] = engine_conf

    return BrainResponse(
        answer=answer,
        confidence=Confidence(
            band=band,
            reasons=reasons if reasons else ["Sufficient support for the conclusion at v0 criteria."],
            escalation=escalation,
        ),
        evidence=ev.finalize(),
        data=data,
    )

    return BrainResponse(answer=answer, confidence=conf, evidence=ev.finalize(), data=data)


def main() -> None:
    adapter = CsvTelemetryAdapter("synthetic_data/generated/v0")

    start = "2025-12-01T00:00:00+00:00"
    end = "2025-12-15T00:00:00+00:00"
    day7 = "2025-12-08T00:00:00+00:00"

    resp = compare_soh_trend_v0(
        adapter,
        ["rack_01", "rack_02"],
        start_iso=start,
        end_iso=end,
        day7_boundary_iso=day7,
    )

    print(json.dumps(resp.to_dict(), indent=2))


if __name__ == "__main__":
    main()
