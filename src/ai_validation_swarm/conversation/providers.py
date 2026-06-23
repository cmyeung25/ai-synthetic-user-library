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

PERSONA_DRIVER_TRACE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "synthetic_only_disclaimer",
        "surface_read",
        "likely_drivers",
        "unspoken_constraints",
        "value_tensions",
        "missed_follow_up_questions",
    ],
    "properties": {
        "synthetic_only_disclaimer": {"type": "string"},
        "surface_read": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "what_the_persona_explicitly_said",
                "what_they_seemed_to_optimize_for",
                "what_stayed_implicit",
            ],
            "properties": {
                "what_the_persona_explicitly_said": {"type": "array", "items": {"type": "string"}},
                "what_they_seemed_to_optimize_for": {"type": "string"},
                "what_stayed_implicit": {"type": "array", "items": {"type": "string"}},
            },
        },
        "likely_drivers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "driver",
                    "driver_type",
                    "why_it_matters_here",
                    "evidence_refs",
                    "profile_source_refs",
                    "confidence",
                    "observed_vs_inferred",
                ],
                "properties": {
                    "driver": {"type": "string"},
                    "driver_type": {
                        "type": "string",
                        "enum": [
                            "core_value",
                            "past_experience",
                            "daily_constraint",
                            "identity_or_role",
                            "decision_style",
                            "trust_pattern",
                            "knowledge_gap",
                            "emotional_protection",
                            "other",
                        ],
                    },
                    "why_it_matters_here": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "profile_source_refs": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "observed_vs_inferred": {
                        "type": "string",
                        "enum": ["mostly_observed", "mixed", "mostly_inferred"],
                    },
                },
            },
        },
        "unspoken_constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "constraint",
                    "why_likely",
                    "evidence_refs",
                    "profile_source_refs",
                    "confidence",
                ],
                "properties": {
                    "constraint": {"type": "string"},
                    "why_likely": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "profile_source_refs": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
            },
        },
        "value_tensions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "tension",
                    "side_a",
                    "side_b",
                    "evidence_refs",
                    "profile_source_refs",
                    "confidence",
                ],
                "properties": {
                    "tension": {"type": "string"},
                    "side_a": {"type": "string"},
                    "side_b": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "profile_source_refs": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
            },
        },
        "missed_follow_up_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "why_this_would_clarify", "priority"],
                "properties": {
                    "question": {"type": "string"},
                    "why_this_would_clarify": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
            },
        },
    },
}


@dataclass(slots=True)
class ChatResult:
    reply: str
    intent_level: str
    confidence: str
    provider_session_id: str = ""


@dataclass(slots=True)
class PersonaDriverTraceResult:
    payload: dict[str, Any]
    provider_session_id: str = ""


class ConversationProvider(Protocol):
    provider_name: str
    model_name: str

    def respond(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
        provider_session_id: str = "",
    ) -> ChatResult: ...

    def generate_persona_driver_trace(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
    ) -> PersonaDriverTraceResult: ...


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

    def generate_persona_driver_trace(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
    ) -> PersonaDriverTraceResult:
        del persona
        payload = self.client.create_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=PERSONA_DRIVER_TRACE_SCHEMA,
        )
        metadata = getattr(self.client, "last_transport_metadata", {})
        transport_session_id = str(metadata.get("codex_session_id", ""))
        return PersonaDriverTraceResult(payload=payload, provider_session_id=transport_session_id)


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

    def generate_persona_driver_trace(
        self, *, system_prompt: str, user_prompt: str, persona: PersonaSkill,
    ) -> PersonaDriverTraceResult:
        del system_prompt, user_prompt
        profile = persona.profile
        values = profile.values if isinstance(profile.values, dict) else {}
        core_values = values.get("core_values", []) if isinstance(values.get("core_values", []), list) else []
        first_value = str(core_values[0]) if core_values else "keep life manageable"
        payload = {
            "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
            "surface_read": {
                "what_the_persona_explicitly_said": [
                    "The persona answered narrowly and left room for follow-up.",
                ],
                "what_they_seemed_to_optimize_for": "A practical answer that protects their existing routine.",
                "what_stayed_implicit": [
                    "Deeper reasons were likely present but not fully surfaced in the short exchange.",
                ],
            },
            "likely_drivers": [
                {
                    "driver": first_value,
                    "driver_type": "core_value",
                    "why_it_matters_here": "The persona tends to judge new ideas through whether they reduce day-to-day friction.",
                    "evidence_refs": ["exchange_1.persona"],
                    "profile_source_refs": ["values.core_values"],
                    "confidence": "medium",
                    "observed_vs_inferred": "mixed",
                }
            ],
            "unspoken_constraints": [
                {
                    "constraint": "The persona may not want to spend extra time learning a new workflow before seeing proof.",
                    "why_likely": "Short answers and cautious intent usually imply limited activation bandwidth.",
                    "evidence_refs": ["exchange_1.persona"],
                    "profile_source_refs": ["behavior_profile", "workflow_adoption_model"],
                    "confidence": "low",
                }
            ],
            "value_tensions": [
                {
                    "tension": "Curiosity versus activation effort",
                    "side_a": "Can see possible value",
                    "side_b": "Does not want another thing to maintain",
                    "evidence_refs": ["exchange_1.persona"],
                    "profile_source_refs": ["values.core_values", "behavior_profile"],
                    "confidence": "medium",
                }
            ],
            "missed_follow_up_questions": [
                {
                    "question": "What was the part of that situation that bothered you after the task itself was done?",
                    "why_this_would_clarify": "It would surface whether the deeper issue was trust, effort, embarrassment, or uncertainty.",
                    "priority": "high",
                }
            ],
        }
        return PersonaDriverTraceResult(payload=payload)
