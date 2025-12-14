from __future__ import annotations

from typing import Any, Dict, Optional

from confidence import ConfidenceEngineV1, ConfidenceSignals

_ENGINE = ConfidenceEngineV1()


def score_confidence_v1(
    *,
    missing_rows: Optional[int] = None,
    total_rows: Optional[int] = None,
    coverage_ratio: Optional[float] = None,
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
        computed_metrics_ok=computed_metrics_ok,
        metric_stability=metric_stability,
        corroboration=corroboration,
        contradictions=contradictions,
        severity=severity,
        novelty=novelty,
    )
    res = _ENGINE.score(sig, context={"intent": intent} if intent else None)
    return res.to_dict()
