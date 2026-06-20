from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient


INTENT_LEVELS = {
    "unclear", "understands", "curious", "willing_to_try", "willing_to_pay",
    "willing_to_recommend", "long_term_adoption", "rejects",
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply", "intent_level", "confidence"],
    "properties": {
        "reply": {"type": "string"},
        "intent_level": {"type": "string", "enum": sorted(INTENT_LEVELS)},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}


@dataclass(slots=True)
class ChatResult:
    reply: str
    intent_level: str
    confidence: str
    provider_session_id: str = ""


class ConversationProvider(Protocol):
    provider_name: str
    model_name: str

    def respond(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
        provider_session_id: str = "",
    ) -> ChatResult: ...


class OpenAIConversationProvider:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self.client = client
        config = client.config
        self.provider_name = "codex" if config.transport.startswith("codex") else "openai"
        self.model_name = config.model

    def respond(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
        provider_session_id: str = "",
    ) -> ChatResult:
        is_codex = self.client.config.transport == "codex_cli"
        payload = self.client.create_json_response(
            system_prompt=(
                "Continue the existing synthetic persona conversation. Preserve its established identity, voice, boundaries, and intent distinctions."
                if is_codex and provider_session_id else system_prompt
            ),
            user_prompt=user_prompt,
            output_schema=RESPONSE_SCHEMA,
            codex_session_id=provider_session_id or None,
            persist_codex_session=is_codex,
        )
        reply = str(payload.get("reply", "")).replace("\ufffc", "").strip()
        intent = str(payload.get("intent_level", "unclear")).strip()
        confidence = str(payload.get("confidence", "low")).strip()
        if not reply:
            raise ValueError("Conversation provider returned an empty reply.")
        if intent not in INTENT_LEVELS:
            intent = "unclear"
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        metadata = getattr(self.client, "last_transport_metadata", {})
        transport_session_id = str(metadata.get("codex_session_id", ""))
        return ChatResult(
            reply=reply,
            intent_level=intent,
            confidence=confidence,
            provider_session_id=transport_session_id or provider_session_id,
        )


class MockConversationProvider:
    provider_name = "mock"
    model_name = "mock-conversation/v1"

    def respond(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
        provider_session_id: str = "",
    ) -> ChatResult:
        del system_prompt
        profile = persona.profile
        voice = profile.persona_voiceprint
        reactions = profile.product_reaction_rules
        latest = user_prompt.rsplit("LATEST USER MESSAGE:", 1)[-1].strip()
        lowered = latest.lower()

        if not latest or len(latest.split()) < 3:
            reply = "I need a more concrete example before I can judge whether this fits my life. What exactly would I need to do?"
            return ChatResult(reply=reply, intent_level="unclear", confidence="high")
        if any(word in lowered for word in ("price", "pricing", "pay", "subscription", "價錢", "月費")):
            objection = profile.pricing_logic.get("pricing_objection", "I would need the value and exit terms to be clearer.")
            reply = f"{objection} I can understand the offer without being ready to pay for it."
            return ChatResult(reply=reply, intent_level="understands", confidence="medium")
        if any(word in lowered for word in ("privacy", "gender", "identity", "data", "私隱", "身份")):
            reply = voice.get("example_hard_rejection") or "I would not continue unless the audience and data controls were explicit."
            return ChatResult(reply=str(reply), intent_level="rejects", confidence="high")
        positive = voice.get("example_positive_reaction")
        if positive:
            return ChatResult(reply=str(positive), intent_level="willing_to_try", confidence="medium")
        questions = reactions.get("questions_they_would_ask", [])
        question = str(questions[0]) if questions else "What would this change in one ordinary week?"
        return ChatResult(reply=f"I understand the direction, but I would test one small case first. {question}", intent_level="curious", confidence="medium")
