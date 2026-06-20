from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ai_validation_swarm.domain.models import utc_now_iso


@dataclass(slots=True)
class ConversationTurn:
    turn_id: int
    role: str
    content: str
    created_at: str = field(default_factory=utc_now_iso)
    intent_level: str = ""
    confidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConversationSession:
    session_id: str
    persona_id: str
    persona_name: str
    persona_version: str
    provider: str
    model: str
    prompt_version: str
    provider_session_id: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    status: str = "active"
    synthetic_only_disclaimer: str = "Synthetic user for AI pre-validation only; not human market evidence."
    turns: list[ConversationTurn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["turn_count"] = len(self.turns)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ConversationSession:
        turns = [ConversationTurn(**turn) for turn in payload.get("turns", [])]
        allowed = {
            "session_id", "persona_id", "persona_name", "persona_version", "provider",
            "model", "prompt_version", "created_at", "updated_at", "status",
            "synthetic_only_disclaimer", "provider_session_id",
        }
        values = {key: value for key, value in payload.items() if key in allowed}
        return cls(**values, turns=turns)
