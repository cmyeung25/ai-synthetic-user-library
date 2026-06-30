from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ai_validation_swarm.domain.models import (
    AuditFinding,
    FounderBrief,
    PersonaResponse,
    PersonaSkill,
    SkepticFinding,
    SkepticReview,
)
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient


PERSONA_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "first_impression": {"type": "string"},
        "pain_relevance": {"type": "string"},
        "solution_attractiveness": {"type": "string"},
        "trust_concern": {"type": "string"},
        "pricing_reaction": {"type": "string"},
        "likely_objection": {"type": "string"},
        "what_would_make_them_try": {"type": "string"},
        "what_would_make_them_reject": {"type": "string"},
        "sensitive_concern_if_any": {"type": "string"},
        "scorecard": {
            "type": "object",
            "properties": {
                "problem_resonance": {"type": "integer"},
                "solution_attractiveness": {"type": "integer"},
                "willingness_to_pay": {"type": "integer"},
            },
            "required": ["problem_resonance", "solution_attractiveness", "willingness_to_pay"],
            "additionalProperties": False,
        },
        "themes": {"type": "object", "additionalProperties": {"type": "string"}},
    },
    "required": [
        "first_impression",
        "pain_relevance",
        "solution_attractiveness",
        "trust_concern",
        "pricing_reaction",
        "likely_objection",
        "what_would_make_them_try",
        "what_would_make_them_reject",
        "sensitive_concern_if_any",
        "scorecard",
        "themes",
    ],
    "additionalProperties": False,
}

SKEPTIC_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "challenged_assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "severity": {"type": "string"},
                    "title": {"type": "string"},
                    "observation": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "recommended_validation_question": {"type": "string"},
                },
                "required": [
                    "finding_id",
                    "severity",
                    "title",
                    "observation",
                    "evidence_refs",
                    "recommended_validation_question",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "challenged_assumptions"],
    "additionalProperties": False,
}

SENSITIVE_AUDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "severity": {"type": "string"},
                    "observation": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "recommended_validation_question": {"type": "string"},
                },
                "required": [
                    "category",
                    "severity",
                    "observation",
                    "evidence_refs",
                    "recommended_validation_question",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

PLANNER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"next_steps": {"type": "array", "items": {"type": "string"}}},
    "required": ["next_steps"],
    "additionalProperties": False,
}


def _required_text(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name, "")).strip()
    if not value:
        raise ValueError(f"LLM validation provider returned empty field '{field_name}'.")
    return value


def _optional_text(payload: dict[str, Any], field_name: str) -> str:
    return str(payload.get(field_name, "")).strip()


def _coerce_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(score, 5))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item).strip() for key, item in value.items() if str(item).strip()}


class OpenAIValidationProvider(BaseProvider):
    def __init__(self, client: OpenAIResponsesClient, *, provider_name: str | None = None) -> None:
        self.client = client
        config = client.config
        if provider_name:
            self.provider_name = provider_name
        elif config.transport == "codex_sdk_node":
            self.provider_name = "codex-sdk"
        elif str(config.transport).startswith("codex"):
            self.provider_name = "codex"
        else:
            self.provider_name = str(getattr(config, "provider_name", "") or "openai")
        self.model_name = str(getattr(config, "model", "") or "unknown")
        self.transport = str(getattr(config, "transport", "") or "unknown")
        self.auth_source = str(getattr(config, "auth_source", "") or "unknown")
        self.model_version = f"{self.provider_name}:{self.model_name}"

    def persona_response(self, persona: PersonaSkill, brief: FounderBrief, protocol_id: str) -> PersonaResponse:
        payload = self.client.create_json_response(
            system_prompt=_validation_system_prompt(),
            user_prompt=_persona_response_prompt(persona=persona, brief=brief, protocol_id=protocol_id),
            output_schema=PERSONA_RESPONSE_SCHEMA,
        )
        scorecard_payload = payload.get("scorecard", {})
        scorecard = scorecard_payload if isinstance(scorecard_payload, dict) else {}
        return PersonaResponse(
            synthetic_user_id=persona.profile.synthetic_user_id,
            panel_role=persona.seed.panel_role,
            protocol_id=protocol_id,
            first_impression=_required_text(payload, "first_impression"),
            pain_relevance=_required_text(payload, "pain_relevance"),
            solution_attractiveness=_required_text(payload, "solution_attractiveness"),
            trust_concern=_required_text(payload, "trust_concern"),
            pricing_reaction=_required_text(payload, "pricing_reaction"),
            likely_objection=_required_text(payload, "likely_objection"),
            what_would_make_them_try=_required_text(payload, "what_would_make_them_try"),
            what_would_make_them_reject=_required_text(payload, "what_would_make_them_reject"),
            sensitive_concern_if_any=_optional_text(payload, "sensitive_concern_if_any"),
            scorecard={
                "problem_resonance": _coerce_score(scorecard.get("problem_resonance")),
                "solution_attractiveness": _coerce_score(scorecard.get("solution_attractiveness")),
                "willingness_to_pay": _coerce_score(scorecard.get("willingness_to_pay")),
            },
            themes=_string_map(payload.get("themes")),
            response_version="persona-response/v1",
        )

    def skeptic_review(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> SkepticReview:
        payload = self.client.create_json_response(
            system_prompt=_validation_system_prompt(),
            user_prompt=_skeptic_review_prompt(brief=brief, personas=personas, responses=responses),
            output_schema=SKEPTIC_REVIEW_SCHEMA,
        )
        findings: list[SkepticFinding] = []
        for item in payload.get("challenged_assumptions", []):
            if not isinstance(item, dict):
                continue
            findings.append(
                SkepticFinding(
                    finding_id=_required_text(item, "finding_id"),
                    severity=_required_text(item, "severity"),
                    title=_required_text(item, "title"),
                    observation=_required_text(item, "observation"),
                    evidence_refs=_string_list(item.get("evidence_refs")),
                    recommended_validation_question=_required_text(item, "recommended_validation_question"),
                )
            )
        if not findings:
            raise ValueError("LLM validation provider returned no skeptic findings.")
        return SkepticReview(
            review_version="skeptic-review/v1",
            summary=_required_text(payload, "summary"),
            challenged_assumptions=findings,
        )

    def sensitive_audit(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> list[AuditFinding]:
        payload = self.client.create_json_response(
            system_prompt=_validation_system_prompt(),
            user_prompt=_sensitive_audit_prompt(brief=brief, personas=personas, responses=responses),
            output_schema=SENSITIVE_AUDIT_SCHEMA,
        )
        findings: list[AuditFinding] = []
        for item in payload.get("findings", []):
            if not isinstance(item, dict):
                continue
            findings.append(_audit_finding_from_payload(item))
        if not findings:
            raise ValueError("LLM validation provider returned no audit findings.")
        return findings

    def planner(self, brief: FounderBrief, summary: dict[str, object], findings: list[AuditFinding]) -> list[str]:
        payload = self.client.create_json_response(
            system_prompt=_validation_system_prompt(),
            user_prompt=_planner_prompt(brief=brief, summary=summary, findings=findings),
            output_schema=PLANNER_SCHEMA,
        )
        steps = _string_list(payload.get("next_steps"))
        if not steps:
            raise ValueError("LLM validation provider returned no planner steps.")
        return steps


def _audit_finding_from_payload(payload: dict[str, Any]) -> AuditFinding:
    return AuditFinding(
        category=_required_text(payload, "category"),
        severity=_required_text(payload, "severity"),
        observation=_required_text(payload, "observation"),
        evidence_refs=_string_list(payload.get("evidence_refs")),
        recommended_validation_question=_required_text(payload, "recommended_validation_question"),
    )


def _validation_system_prompt() -> str:
    return (
        "You are a rigorous synthetic-user research engine. Return only JSON that matches the requested schema. "
        "Treat all outputs as simulated evidence, not human market proof. Preserve uncertainty, objections, trust gaps, "
        "adoption barriers, and next-step human validation gaps."
    )


def _persona_response_prompt(*, persona: PersonaSkill, brief: FounderBrief, protocol_id: str) -> str:
    return "\n".join(
        [
            "Generate one behaviorally plausible synthetic persona response for this validation study.",
            "Do not be agreeable by default. Ground the response in the persona's constraints, risk tolerance, routines, and decision policy.",
            "Use scorecard values from 1 to 5.",
            _json_block(
                {
                    "protocol_id": protocol_id,
                    "founder_brief": brief.to_dict(),
                    "persona": _persona_payload(persona),
                }
            ),
        ]
    )


def _skeptic_review_prompt(
    *, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
) -> str:
    return "\n".join(
        [
            "Review the synthetic validation responses as a skeptical research reviewer.",
            "Identify weak assumptions, false positives, adoption gaps, trust gaps, and what human validation is still needed.",
            _json_block(
                {
                    "founder_brief": brief.to_dict(),
                    "personas": [_persona_payload(persona) for persona in personas],
                    "responses": [response.to_dict() for response in responses],
                }
            ),
        ]
    )


def _sensitive_audit_prompt(
    *, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
) -> str:
    return "\n".join(
        [
            "Audit the study for sensitive-topic, reporting, privacy, discrimination, and high-stakes decision risks.",
            "Always include at least one audit finding, even if the finding is low severity and boundary-focused.",
            _json_block(
                {
                    "founder_brief": brief.to_dict(),
                    "personas": [_persona_payload(persona) for persona in personas],
                    "responses": [response.to_dict() for response in responses],
                }
            ),
        ]
    )


def _planner_prompt(*, brief: FounderBrief, summary: dict[str, object], findings: list[AuditFinding]) -> str:
    return "\n".join(
        [
            "Create a practical next-step validation plan from the synthetic evidence.",
            "Keep steps concrete, research-oriented, and explicit about what must still be checked with humans.",
            _json_block(
                {
                    "founder_brief": brief.to_dict(),
                    "summary": summary,
                    "audit_findings": [finding.to_dict() for finding in findings],
                }
            ),
        ]
    )


def _json_block(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _persona_payload(persona: PersonaSkill) -> dict[str, Any]:
    return asdict(persona)
