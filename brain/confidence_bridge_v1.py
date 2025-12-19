from __future__ import annotations

from typing import Any, Dict, Optional

from confidence import ConfidenceEngineV1, ConfidenceSignals

_ENGINE = ConfidenceEngineV1()


def gap_stats_from_rows(rows: list[dict]) -> dict[str, int]:
    """
    Compute missing gap clustering statistics from adapter rows.
    Assumes missing rows use data_quality_flag == "missing".
    Returns: {missing_rows, missing_streak_max, missing_streaks}
    """
    missing_rows = 0
    missing_streak_max = 0
    missing_streaks = 0

    streak = 0
    for r in rows:
        is_missing = r.get("data_quality_flag") == "missing"
        if is_missing:
            missing_rows += 1
            streak += 1
        else:
            if streak > 0:
                missing_streaks += 1
                missing_streak_max = max(missing_streak_max, streak)
                streak = 0

    # handle streak ending at end
    if streak > 0:
        missing_streaks += 1
        missing_streak_max = max(missing_streak_max, streak)

    return {
        "missing_rows": missing_rows,
        "missing_streak_max": missing_streak_max,
        "missing_streaks": missing_streaks,
    }


def score_confidence_v1(
    *,
    missing_rows: Optional[int] = None,
    total_rows: Optional[int] = None,
    coverage_ratio: Optional[float] = None,
    time_span_days: Optional[float] = None,
    missing_streak_max: Optional[int] = None,
    missing_streaks: Optional[int] = None,
    computed_metrics_ok: Optional[bool] = None,
    metric_stability: Optional[float] = None,
    corroboration: Optional[float] = None,
    contradictions: Optional[int] = None,
    severity: Optional[float] = None,
    novelty: Optional[float] = None,
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Migration-only bridge.
    Calls ConfidenceEngineV1 but does NOT enforce/override the intent's confidence output yet.

    Returns the full engine result dict so intents can optionally use it later.
    For Issue #15, callers should NOT change outward-facing confidence fields.
    """
    sig = ConfidenceSignals(
        missing_rows=missing_rows,
        total_rows=total_rows,
        coverage_ratio=coverage_ratio,
        time_span_days=time_span_days,
        missing_streak_max=missing_streak_max,
        missing_streaks=missing_streaks,
        computed_metrics_ok=computed_metrics_ok,
        metric_stability=metric_stability,
        corroboration=corroboration,
        contradictions=contradictions,
        severity=severity,
        novelty=novelty,
    )
    res = _ENGINE.score(sig, context={"intent": intent} if intent else None)
    return res.to_dict()
