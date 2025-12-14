from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class Confidence:
    band: str  # high | medium | low
    reasons: list[str]
    escalation: str  # none | ask_followup | human_review

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrainResponse:
    answer: str
    confidence: Confidence
    evidence: Dict[str, Any]
    data: Optional[Dict[str, Any]] = None  # structured metrics payload (optional)

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "answer": self.answer,
            "confidence": self.confidence.to_dict(),
            "evidence": self.evidence,
        }
        if self.data is not None:
            out["data"] = self.data
        return out
