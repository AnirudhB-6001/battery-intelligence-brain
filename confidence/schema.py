from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ConfidenceSignals:
    """
    Normalized signals used to score confidence across intents.

    All fields are optional so intents can adopt this gradually.
    """
    # Data quality
    missing_rows: Optional[int] = None
    total_rows: Optional[int] = None
    coverage_ratio: Optional[float] = None  # 0..1 if precomputed
    time_span_days: Optional[float] = None

    # Computation health
    computed_metrics_ok: Optional[bool] = None
    metric_stability: Optional[float] = None  # 0..1 where 1 = stable, if available

    # Corroboration
    corroboration: Optional[float] = None  # 0..1 (events corroborate telemetry etc.)
    contradictions: Optional[int] = None

    # Domain risk modifiers
    severity: Optional[float] = None  # 0..1 estimated severity of detected condition
    novelty: Optional[float] = None   # 0..1 how unusual/unseen (optional)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfidenceBreakdown:
    coverage: float
    quality: float
    corroboration: float
    stability: float
    contradiction: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfidenceResult:
    band: str  # high | medium | low
    reasons: List[str]
    escalation: str  # none | ask_followup | human_review
    score: float  # 0..1
    breakdown: ConfidenceBreakdown
    signals: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["breakdown"] = self.breakdown.to_dict()
        return out
