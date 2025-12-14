from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_evidence_id() -> str:
    # Stable-ish readable id; uuid keeps it unique
    return f"ev_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"


@dataclass
class EvidenceBuilder:
    """
    Evidence Bundle Builder v0

    Produces an auditable evidence packet aligned with evidence/README.md.

    This module is intentionally strict and boring:
    - it records what happened
    - it does NOT calculate confidence
    - it does NOT perform computations
    - it does NOT interpret data
    """

    question: str
    intent: str
    role: Optional[str] = None
    evidence_id: str = field(default_factory=_new_evidence_id)
    generated_at: str = field(default_factory=_now_iso)

    data_used: List[Dict[str, Any]] = field(default_factory=list)
    computations: List[Dict[str, Any]] = field(default_factory=list)
    model_calls: List[Dict[str, Any]] = field(default_factory=list)
    kb_rules_applied: List[Dict[str, Any]] = field(default_factory=list)

    assumptions: List[Dict[str, Any]] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)

    attachments: Dict[str, List[str]] = field(default_factory=lambda: {"charts": [], "tables": [], "links": []})

    # -------------------------
    # Factory
    # -------------------------
    @staticmethod
    def start(question: str, intent: str, role: Optional[str] = None) -> "EvidenceBuilder":
        return EvidenceBuilder(question=question, intent=intent, role=role)

    # -------------------------
    # Recorders
    # -------------------------
    def add_data_used(
        self,
        *,
        source_type: str,
        source_name: str,
        query: Dict[str, Any],
        time_window: Optional[Dict[str, str]] = None,
        row_count: Optional[int] = None,
        quality_notes: str = "",
    ) -> None:
        self.data_used.append(
            {
                "source_type": source_type,
                "source_name": source_name,
                "query": query,
                "time_window": time_window,
                "row_count": row_count,
                "quality_notes": quality_notes,
            }
        )

    def add_computation(
        self,
        *,
        name: str,
        inputs: List[str],
        method: str,
        outputs: Dict[str, Any],
        assumptions_refs: Optional[List[str]] = None,
    ) -> None:
        self.computations.append(
            {
                "name": name,
                "inputs": inputs,
                "method": method,
                "outputs": outputs,
                "assumptions_refs": assumptions_refs or [],
            }
        )

    def add_model_call(
        self,
        *,
        model_name: str,
        model_version: Optional[str] = None,
        inputs_summary: Optional[Dict[str, Any]] = None,
        outputs_summary: Optional[Dict[str, Any]] = None,
        model_confidence: Optional[Any] = None,
        limitations: str = "",
    ) -> None:
        self.model_calls.append(
            {
                "model_name": model_name,
                "model_version": model_version,
                "inputs_summary": inputs_summary or {},
                "outputs_summary": outputs_summary or {},
                "model_confidence": model_confidence,
                "limitations": limitations,
            }
        )

    def add_kb_rule(
        self,
        *,
        kb_ref: str,
        rule_summary: str,
        impact_on_answer: str,
    ) -> None:
        self.kb_rules_applied.append(
            {
                "kb_ref": kb_ref,
                "rule_summary": rule_summary,
                "impact_on_answer": impact_on_answer,
            }
        )

    def add_assumption(self, *, ref: str, description: str) -> None:
        self.assumptions.append({"ref": ref, "description": description})

    def add_gap(self, gap: str) -> None:
        self.gaps.append(gap)

    def add_risk_note(self, note: str) -> None:
        self.risk_notes.append(note)

    def add_attachment(self, *, kind: str, ref: str) -> None:
        if kind not in self.attachments:
            self.attachments[kind] = []
        self.attachments[kind].append(ref)

    # -------------------------
    # Finalize
    # -------------------------
    def finalize(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "generated_at": self.generated_at,
            "question": self.question,
            "intent": self.intent,
            "role": self.role,
            "data_used": self.data_used,
            "computations": self.computations,
            "model_calls": self.model_calls,
            "kb_rules_applied": self.kb_rules_applied,
            "assumptions_and_gaps": {
                "assumptions": self.assumptions,
                "gaps": self.gaps,
                "risk_notes": "; ".join(self.risk_notes) if self.risk_notes else "",
            },
            "attachments": self.attachments,
        }
