from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adapters.telemetry import CsvTelemetryAdapter
from adapters.telemetry.csv_adapter import TimeWindow
from evidence import EvidenceBuilder
from brain.contracts import BrainResponse, Confidence
from brain.confidence_bridge_v1 import score_confidence_v1


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _filter_numeric(rows: List[Dict[str, Any]], key: str) -> List[Tuple[datetime, float, str]]:
    out: List[Tuple[datetime, float, str]] = []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            out.append((_parse_iso(r["timestamp"]), float(v), r.get("data_quality_flag", "ok")))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    return out


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    vs = sorted(values)
    k = int(round((len(vs) - 1) * p))
    return vs[max(0, min(len(vs) - 1, k))]


def anomaly_scan_v0(
    adapter: CsvTelemetryAdapter,
    asset_id: str,
    *,
    start_iso: str,
    end_iso: str,
    role: str = "ops",
) -> BrainResponse:
    question = f"Scan {asset_id} for temperature anomalies in the given window."
    intent = "anomaly_scan_temp_v0"
    ev = EvidenceBuilder.start(question, intent, role=role)

    tw = TimeWindow.from_iso(start_iso, end_iso)

    # Pull telemetry
    ts = adapter.get_timeseries(asset_id, ["temperature"], tw, include_missing=True)
    rows = ts["rows"]
    missing = sum(1 for r in rows if r.get("data_quality_flag") == "missing")
    quality_notes = f"{missing} missing rows" if missing else "no missing rows"

    ev.add_data_used(
        source_type="telemetry",
        source_name=str(adapter.base_dir.name),
        query={"asset_id": asset_id, "signals": ["temperature"], "granularity": "15m"},
        time_window=ts["time_window"],
        row_count=ts["row_count"],
        quality_notes=quality_notes,
    )

    temps = _filter_numeric(rows, "temperature")
    temp_values = [v for _, v, dq in temps if dq != "missing"]

    if len(temp_values) < 40:
        ev.add_gap("Insufficient temperature points for anomaly scan.")
        conf = Confidence(
            band="low",
            reasons=["Not enough valid temperature data to detect anomalies."],
            escalation="ask_followup",
        )
        return BrainResponse(
            answer=f"Insufficient data to scan {asset_id} for temperature anomalies.",
            confidence=conf,
            evidence=ev.finalize(),
            data={"asset_id": asset_id, "points": len(temp_values), "missing_rows": missing},
        )

    # Simple spike detection rule (v0):
    # define baseline as median-ish (50th percentile) and spike threshold as 95th percentile + margin
    p50 = _percentile(temp_values, 0.50)
    p95 = _percentile(temp_values, 0.95)
    if p50 is None or p95 is None:
        ev.add_gap("Could not compute temperature percentiles.")
        conf = Confidence(band="low", reasons=["Temperature distribution unavailable."], escalation="ask_followup")
        return BrainResponse(
            answer=f"Unable to compute temperature anomaly thresholds for {asset_id}.",
            confidence=conf,
            evidence=ev.finalize(),
            data={"asset_id": asset_id, "missing_rows": missing},
        )

    # margin makes it robust for synthetic noise
    threshold = p95 + 1.0

    spike_points = [(t, v) for (t, v, dq) in temps if dq != "missing" and v >= threshold]

    # Pull events as secondary evidence
    events = adapter.get_events(asset_id, tw)

    # Computation evidence
    ev.add_computation(
        name="temp_spike_scan",
        inputs=["temperature"],
        method="Compute p50 and p95 of temperature; flag spike if temperature >= (p95 + 1.0°C).",
        outputs={
            "p50": round(p50, 3),
            "p95": round(p95, 3),
            "threshold": round(threshold, 3),
            "spike_count": len(spike_points),
            "first_spike_ts": spike_points[0][0].isoformat() if spike_points else None,
            "last_spike_ts": spike_points[-1][0].isoformat() if spike_points else None,
        },
        assumptions_refs=["ASSUMP_SYNTHETIC_DATA_BEHAVES_REALISTICALLY_V0"],
    )

    # Confidence (v0)
    reasons: List[str] = []
    band = "high"
    escalation = "none"

    if missing > 0:
        band = "medium"
        reasons.append("Telemetry contains missing intervals; anomaly confidence reduced.")

    # If spikes detected, answer accordingly
    if spike_points:
        first = spike_points[0][0].isoformat()
        last = spike_points[-1][0].isoformat()
        answer = f"Temperature anomaly detected for {asset_id}: spike activity observed from {first} to {last} (threshold ≈ {threshold:.2f}°C)."
    else:
        answer = f"No temperature spike anomalies detected for {asset_id} in the window (threshold ≈ {threshold:.2f}°C)."

    # Add gaps notes
    if missing > 0:
        ev.add_gap(f"{asset_id} has {missing} missing telemetry rows in-window.")

    # Attach events as additional context (not a model call, but evidence payload)
    data = {
        "asset_id": asset_id,
        "comparison_window": {"start": start_iso, "end": end_iso},
        "stats": {"p50": p50, "p95": p95, "threshold": threshold},
        "spikes": [{"timestamp": t.isoformat(), "temperature": v} for (t, v) in spike_points[:20]],  # cap for readability
        "spike_count": len(spike_points),
        "events": events,
        "missing_rows": missing,
    }

    # If events mention a spike, boost confidence slightly (still capped)
    if any(e.get("event_type") == "temp_spike" for e in events) and spike_points:
        if band == "medium":
            reasons.append("Event log corroborates temperature spike detection.")

    conf = Confidence(
        band=band,
        reasons=reasons if reasons else ["Sufficient temperature coverage for anomaly scan in v0."],
        escalation=escalation,
    )

    event_hit = any(e.get("event_type") == "temp_spike" for e in events) if events else False
    
    # Existing v0 reasons/band/escalation computed above:
    # band, reasons, escalation
    
    # Confidence Engine v1 (now active)Confidence Engine v1 (migration-only): compute score but do not change v0 output yet
    
    engine_conf = score_confidence_v1(
        missing_rows=missing,
        total_rows=ts["row_count"],
        computed_metrics_ok=True,
        corroboration=0.8 if event_hit else None,
        intent=intent,
    )

    band = engine_conf["band"]
    escalation = engine_conf["escalation"]

    confidence = {
        "band": band,
        "reasons": reasons if reasons else ["Sufficient support for anomaly detection in v0."],
        "escalation": escalation,
    }

    data["confidence_v1"] = engine_conf

    return BrainResponse(
        answer=answer,
        confidence=Confidence(band=band, reasons=confidence["reasons"], escalation=escalation),
        evidence=ev.finalize(),
        data=data,
    )
    
    return BrainResponse(answer=answer, confidence=conf, evidence=ev.finalize(), data=data)


def main() -> None:
    adapter = CsvTelemetryAdapter("synthetic_data/generated/v0")

    start = "2025-12-01T00:00:00+00:00"
    end = "2025-12-15T00:00:00+00:00"

    # In our synthetic world, rack_02 has the spike
    resp = anomaly_scan_v0(adapter, "rack_02", start_iso=start, end_iso=end, role="ops")
    print(json.dumps(resp.to_dict(), indent=2))


if __name__ == "__main__":
    main()