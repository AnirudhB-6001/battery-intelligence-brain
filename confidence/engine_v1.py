from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from confidence.schema import ConfidenceSignals, ConfidenceResult, ConfidenceBreakdown


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


@dataclass
class ConfidenceEngineV1:
    """
    Confidence Engine v1

    - Centralizes confidence scoring so intents can stop embedding ad-hoc rules.
    - Produces: band + reasons + escalation + score + breakdown.
    - NOT wired into intents yet (Issue #13 is engine only).
    """

    # weights for combined score
    w_coverage: float = 0.25
    w_quality: float = 0.25
    w_corroboration: float = 0.20
    w_stability: float = 0.20
    w_contradiction: float = 0.10

    # band thresholds
    high_threshold: float = 0.75
    medium_threshold: float = 0.50

    def score(self, signals: ConfidenceSignals, *, context: Optional[Dict[str, Any]] = None) -> ConfidenceResult:
        ctx = context or {}
        reasons: List[str] = []

        # ----- Coverage -----
        if signals.coverage_ratio is not None:
            coverage = _clamp(signals.coverage_ratio)
        elif signals.total_rows is not None and signals.missing_rows is not None:
            coverage = _clamp(1.0 - _safe_div(float(signals.missing_rows), float(signals.total_rows)))
        else:
            coverage = 0.6  # neutral default for gradual adoption
            reasons.append("Coverage ratio not provided; using neutral default.")

        # ----- Quality -----
        # Quality is impacted by missingness; if not known, neutral.
        if signals.total_rows is not None and signals.missing_rows is not None:
            miss_ratio = _safe_div(float(signals.missing_rows), float(signals.total_rows))
            quality = _clamp(1.0 - miss_ratio * 1.2)  # missing hurts a bit more than linear
            if miss_ratio > 0.0:
                reasons.append("Telemetry contains missing intervals; confidence reduced.")

            # ----- Gap clustering penalty (Issue 17.1) -----
            # Continuous missing blocks are riskier than scattered misses.
            streak_max = signals.missing_streak_max or 0
            streaks = signals.missing_streaks or 0

            if streak_max > 0:
                cluster_penalty = 0.0

                # At 15m cadence: 4 = 1h gap; 8 = 2h; 16 = 4h.
                if streak_max >= 4:
                    cluster_penalty += 0.05
                if streak_max >= 8:
                    cluster_penalty += 0.07
                if streak_max >= 16:
                    cluster_penalty += 0.10

                # If gaps are mostly scattered (many streaks, small max), reduce penalty.
                if streaks >= 3 and streak_max <= 4:
                    cluster_penalty *= 0.5

                if cluster_penalty > 0.0:
                    quality = _clamp(quality - cluster_penalty)
                    reasons.append("Missing telemetry is clustered (continuous gaps); confidence reduced.")
        else:
            quality = 0.6
            reasons.append("Missingness not provided; using neutral default.")

        # ----- Stability -----
        if signals.metric_stability is not None:
            stability = _clamp(signals.metric_stability)
        else:
            # If we at least know metrics computed OK, treat as moderately stable
            stability = 0.7 if signals.computed_metrics_ok else 0.55
            if signals.computed_metrics_ok is None:
                reasons.append("Metric stability not provided; using neutral default.")
            elif signals.computed_metrics_ok is False:
                reasons.append("Some computations failed or were incomplete; confidence reduced.")

        # ----- Corroboration -----
        if signals.corroboration is not None:
            corroboration = _clamp(signals.corroboration)
            if corroboration >= 0.7:
                reasons.append("Independent evidence corroborates the finding.")
        else:
            corroboration = 0.5  # neutral: no corroboration signal provided
            # No reason added; lack of corroboration isn't always a flaw.

        # ----- Contradictions -----
        contradictions = signals.contradictions or 0
        if contradictions <= 0:
            contradiction = 1.0
        else:
            contradiction = _clamp(1.0 - 0.25 * float(contradictions))
            reasons.append("Contradictory signals detected; confidence reduced.")

        # ----- Combined score -----
        score = (
            self.w_coverage * coverage
            + self.w_quality * quality
            + self.w_corroboration * corroboration
            + self.w_stability * stability
            + self.w_contradiction * contradiction
        )
        score = _clamp(score)

        breakdown = ConfidenceBreakdown(
            coverage=coverage,
            quality=quality,
            corroboration=corroboration,
            stability=stability,
            contradiction=contradiction,
        )

        # ----- Band + escalation -----
        if score >= self.high_threshold:
            band = "high"
            escalation = "none"
        elif score >= self.medium_threshold:
            band = "medium"
            escalation = "none"
        else:
            band = "low"
            escalation = "ask_followup"

        # Tighten escalation if computations failed
        if signals.computed_metrics_ok is False:
            band = "low"
            escalation = "ask_followup"

        # Add minimal context note (optional)
        if ctx.get("intent"):
            # do not add too much noise to reasons
            pass

        # Ensure reasons not empty (for UX)
        if not reasons:
            reasons = ["Sufficient support for the conclusion at v1 confidence criteria."]

        return ConfidenceResult(
            band=band,
            reasons=reasons,
            escalation=escalation,
            score=score,
            breakdown=breakdown,
            signals=signals.to_dict(),
        )
