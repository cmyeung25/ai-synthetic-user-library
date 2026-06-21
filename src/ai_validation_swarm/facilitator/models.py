from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

from ai_validation_swarm.domain.models import utc_now_iso


@dataclass(slots=True)
class FacilitatorDecision:
    interview_phase: str
    probing_strategy: str
    decision_rationale: str
    message_to_persona: str
    evidence_updates: list[dict[str, Any]]
    root_cause_hypotheses: list[dict[str, Any]]
    open_questions: list[str]
    should_end: bool
    end_reason: str
    question_evidence_basis: str = "current_event"
    question_evidence_target: str = "context"
    provider_session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class InterviewExchange:
    exchange_id: int
    facilitator_question: str
    persona_response: str
    facilitator_phase: str
    probing_strategy: str
    question_evidence_basis: str = "current_event"
    question_evidence_target: str = "context"
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class InterviewSession:
    interview_id: str
    persona_id: str
    persona_name: str
    research_goal: str
    product_context: str
    output_language: str
    facilitator_provider: str
    facilitator_model: str
    persona_provider: str
    persona_model: str
    facilitator_prompt_version: str
    synthesis_prompt_version: str
    concept_protocol_version: str = ""
    concept_label: str = ""
    interview_mode: str = "explore_root_cause"
    hypothesis: str = ""
    facilitator_provider_session_id: str = ""
    persona_provider_session_id: str = ""
    persona_conversation_session_id: str = ""
    quality_provider: str = ""
    quality_model: str = ""
    quality_prompt_version: str = ""
    quality_provider_session_id: str = ""
    hypothesis_evidence_judge_prompt_version: str = ""
    hypothesis_evidence_judge_provider_session_id: str = ""
    max_turns: int = 10
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    status: str = "active"
    stop_reason: str = ""
    synthetic_only_disclaimer: str = "Synthetic-user interview for AI pre-validation only; not human market evidence."
    facilitator_decisions: list[dict[str, Any]] = field(default_factory=list)
    exchanges: list[InterviewExchange] = field(default_factory=list)
    pending_facilitator_decision: dict[str, Any] = field(default_factory=dict)
    observer_interventions: list[dict[str, Any]] = field(default_factory=list)
    last_error: str = ""
    failed_operation: str = ""
    failed_payload: dict[str, Any] = field(default_factory=dict)
    insight_report: dict[str, Any] = field(default_factory=dict)
    quality_evaluation: dict[str, Any] = field(default_factory=dict)
    hypothesis_evidence_judgment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["exchange_count"] = len(self.exchanges)
        payload["facilitator_decision_count"] = len(self.facilitator_decisions)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> InterviewSession:
        exchanges = [InterviewExchange(**item) for item in payload.get("exchanges", [])]
        allowed = {item.name for item in fields(cls)} - {"exchanges"}
        values = {key: value for key, value in payload.items() if key in allowed}
        return cls(**values, exchanges=exchanges)
