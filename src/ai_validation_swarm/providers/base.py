from __future__ import annotations

from abc import ABC, abstractmethod

from ai_validation_swarm.domain.models import AuditFinding, FounderBrief, PersonaResponse, PersonaSkill, SkepticReview


class BaseProvider(ABC):
    model_version = "unknown"

    @abstractmethod
    def persona_response(self, persona: PersonaSkill, brief: FounderBrief, protocol_id: str) -> PersonaResponse:
        raise NotImplementedError

    @abstractmethod
    def skeptic_review(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> SkepticReview:
        raise NotImplementedError

    @abstractmethod
    def sensitive_audit(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> list[AuditFinding]:
        raise NotImplementedError

    @abstractmethod
    def planner(
        self, brief: FounderBrief, summary: dict[str, object], findings: list[AuditFinding]
    ) -> list[str]:
        raise NotImplementedError
