from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient, OpenAIProviderConfig

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"

PERSONA_ENRICHMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "required": [
        "values",
        "life_story",
        "behavior_profile",
        "problem_context",
        "sensitive_reality_layer",
        "decision_policy",
        "response_style",
        "narrative",
        "rationale",
    ],
    "properties": {
        "values": {"type": "object"},
        "life_story": {"type": "object"},
        "behavior_profile": {"type": "object"},
        "problem_context": {"type": "object"},
        "sensitive_reality_layer": {"type": "object"},
        "decision_policy": {"type": "object"},
        "response_style": {"type": "object"},
        "narrative": {"type": "string"},
        "rationale": {"type": "string"},
    },
}

PERSONA_JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "required": [
        "verdict",
        "plausibility_score",
        "stereotype_risk_score",
        "panel_fit_score",
        "findings",
        "revision_hints",
        "rationale",
    ],
    "properties": {
        "verdict": {"type": "string"},
        "plausibility_score": {"type": ["number", "integer"]},
        "stereotype_risk_score": {"type": ["number", "integer"]},
        "panel_fit_score": {"type": ["number", "integer"]},
        "findings": {"type": "array"},
        "revision_hints": {"type": "array"},
        "rationale": {"type": "string"},
    },
}


def _load_prompt(path_parts: list[str]) -> str:
    return (PROMPTS_ROOT.joinpath(*path_parts)).read_text(encoding="utf-8").strip()


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _merge_profile_dict(target: dict[str, Any], patch: dict[str, Any], *, protected_keys: set[str] | None = None) -> dict[str, Any]:
    protected = protected_keys or set()
    merged = dict(target)
    for key, value in patch.items():
        if key in protected:
            continue
        merged[key] = value
    return merged


def _llm_provider_name(config: OpenAIProviderConfig) -> str:
    if config.transport in {"codex_cli", "codex_sdk_node"}:
        return "codex"
    return config.provider_name


def _persona_enrichment_prompt_version(config: OpenAIProviderConfig) -> str:
    if _llm_provider_name(config) == "agnes":
        return "persona-enrichment/v2"
    return "persona-enrichment/v1"


def _persona_enrichment_prompt_path(config: OpenAIProviderConfig) -> list[str]:
    _, version = _persona_enrichment_prompt_version(config).split("/", 1)
    return ["persona-enrichment", f"{version}.md"]


def _persona_generation_method(config: OpenAIProviderConfig) -> str:
    version = _persona_enrichment_prompt_version(config).rsplit("/", 1)[-1]
    return f"deterministic_seed_plus_{_llm_provider_name(config)}_enrichment_{version}"


def _stringify_audit_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _pick_fields(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def _build_enrichment_payload(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    personality = persona.profile.personality_belief
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile
    values = persona.profile.values
    life_story = persona.profile.life_story
    behavior = persona.profile.behavior_profile
    problem = persona.profile.problem_context
    sensitive = persona.profile.sensitive_reality_layer

    return {
        "seed": persona.seed.to_dict(),
        "identity_anchors": _pick_fields(
            identity,
            (
                "synthetic_user_id",
                "name",
                "age",
                "gender",
                "location",
                "language",
                "occupation",
                "family_structure",
                "household_size",
                "living_area",
                "life_stage",
            ),
        ),
        "fixed_signals": {
            "personality": _pick_fields(
                personality,
                (
                    "decision_style",
                    "risk_tolerance",
                    "trust_orientation",
                    "self_image",
                    "social_comparison_tendency",
                ),
            ),
            "technology_profile": _pick_fields(
                technology,
                (
                    "tech_savviness",
                    "ai_familiarity",
                    "digital_payment_comfort",
                    "privacy_concern",
                    "app_fatigue",
                    "automation_openness",
                    "accessibility_needs",
                    "language_confidence",
                ),
            ),
            "economic_profile": _pick_fields(
                economic,
                (
                    "disposable_income",
                    "price_sensitivity",
                    "subscription_tolerance",
                    "current_alternatives",
                    "switching_cost",
                    "purchase_authority_type",
                    "employment_stability",
                    "cash_flow_volatility",
                ),
            ),
            "values": _pick_fields(
                values,
                (
                    "core_values",
                    "life_goals",
                    "fears",
                    "aspirations",
                    "identity_anchors",
                    "moral_boundaries",
                    "status_concerns",
                ),
            ),
            "life_story": _pick_fields(
                life_story,
                (
                    "career_path",
                    "family_story",
                    "current_daily_routine",
                    "recent_life_events",
                    "frustrations",
                    "hidden_needs",
                ),
            ),
            "behavior_profile": _pick_fields(
                behavior,
                (
                    "buying_behavior",
                    "information_sources",
                    "social_media_usage",
                    "referral_influence",
                    "brand_trust_signals",
                    "decision_blockers",
                    "emotional_triggers",
                    "workflow_maturity",
                    "documentation_discipline",
                    "manager_approval_dependence",
                ),
            ),
            "problem_context": _pick_fields(
                problem,
                (
                    "active_pain_points",
                    "latent_pain_points",
                    "jobs_to_be_done",
                    "current_workaround",
                    "urgency_level",
                    "willingness_to_change",
                    "willingness_to_pay",
                    "proof_threshold",
                ),
            ),
            "sensitive_reality_layer": _pick_fields(
                sensitive,
                (
                    "social_risk_profile",
                    "fairness_and_inclusion_profile",
                    "taboo_topic_comfort",
                    "political_sensitivity",
                    "discrimination_awareness",
                    "public_expression_risk_aversion",
                    "identity_labeling_comfort",
                    "response_boundaries",
                    "public_explanation_preference",
                ),
            ),
        },
        "current_decision_policy": persona.decision_policy,
        "current_response_style": persona.response_style,
        "edit_rules": [
            "Preserve all seed facts and identity anchors exactly.",
            "Deepen realism through routines, tradeoffs, blockers, trust logic, and constraints.",
            "Do not invent medical, legal, or diagnostic claims.",
            "Keep the output suitable for product validation rather than profiling.",
        ],
    }


class OpenAIPersonaEnricher:
    prompt_version = "persona-enrichment/v1"

    def __init__(self, client: OpenAIResponsesClient, config: OpenAIProviderConfig) -> None:
        self.client = client
        self.config = config
        self.prompt_version = _persona_enrichment_prompt_version(config)
        self.system_prompt = _load_prompt(_persona_enrichment_prompt_path(config))

    def enrich(self, persona: PersonaSkill) -> PersonaSkill:
        payload = _build_enrichment_payload(persona)
        user_prompt = "\n".join(
            [
                "Enrich this seeded synthetic persona without changing identity anchors or structural facts.",
                "Use the payload below as fixed anchors plus starting signals. You may expand realism, but you must not contradict the anchors.",
                "Return valid JSON only.",
                "Required keys: values, life_story, behavior_profile, problem_context, sensitive_reality_layer, decision_policy, response_style, narrative, rationale.",
                json.dumps(payload, ensure_ascii=False, indent=2),
            ]
        )
        enriched = self.client.create_json_response(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_schema=PERSONA_ENRICHMENT_SCHEMA,
        )

        persona.profile.values = _merge_profile_dict(persona.profile.values, self._expect_object(enriched, "values"))
        persona.profile.life_story = _merge_profile_dict(persona.profile.life_story, self._expect_object(enriched, "life_story"))
        persona.profile.behavior_profile = _merge_profile_dict(
            persona.profile.behavior_profile,
            self._expect_object(enriched, "behavior_profile"),
        )
        persona.profile.problem_context = _merge_profile_dict(
            persona.profile.problem_context,
            self._expect_object(enriched, "problem_context"),
        )
        persona.profile.sensitive_reality_layer = _merge_profile_dict(
            persona.profile.sensitive_reality_layer,
            self._expect_object(enriched, "sensitive_reality_layer"),
            protected_keys={"sensitive_identity_context"},
        )
        persona.decision_policy = _merge_profile_dict(persona.decision_policy, self._expect_object(enriched, "decision_policy"))
        persona.response_style = _merge_profile_dict(persona.response_style, self._expect_object(enriched, "response_style"))
        persona.narrative = str(enriched.get("narrative", persona.narrative)).strip() or persona.narrative

        persona.profile.audit_evidence_layer["persona_generation_method"] = _persona_generation_method(self.config)
        persona.profile.audit_evidence_layer["evidence_grade"] = "synthetic_llm_enriched"
        persona.profile.audit_evidence_layer["last_audited_at"] = datetime.now(UTC).date().isoformat()

        persona.audit = {
            **persona.audit,
            **persona.profile.audit_evidence_layer,
            "llm_enrichment": {
                "provider": _llm_provider_name(self.config),
                "profile": self.config.profile,
                "model": self.config.model,
                "prompt_version": self.prompt_version,
                "generated_at": _timestamp(),
                "rationale": _stringify_audit_value(enriched.get("rationale", "")),
            },
        }
        return persona

    @staticmethod
    def _expect_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
        value = payload.get(key, {})
        return dict(value) if isinstance(value, dict) else {}


class OpenAIPersonaJudge:
    prompt_version = "persona-judge/v1"

    def __init__(self, client: OpenAIResponsesClient, config: OpenAIProviderConfig) -> None:
        self.client = client
        self.config = config
        self.system_prompt = _load_prompt(["persona-judge", "v1.md"])

    def judge(self, persona: PersonaSkill) -> dict[str, Any]:
        payload = {
            "seed": persona.seed.to_dict(),
            "profile": persona.profile.to_dict(),
            "decision_policy": persona.decision_policy,
            "response_style": persona.response_style,
            "narrative": persona.narrative,
            "audit": persona.audit,
        }
        user_prompt = "\n".join(
            [
                "Judge this synthetic persona for plausibility, stereotype risk, and panel fit.",
                "Return valid JSON only.",
                "Required keys: verdict, plausibility_score, stereotype_risk_score, panel_fit_score, findings, revision_hints, rationale.",
                json.dumps(payload, ensure_ascii=False, indent=2),
            ]
        )
        result = self.client.create_json_response(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_schema=PERSONA_JUDGE_SCHEMA,
        )
        result["provider"] = _llm_provider_name(self.config)
        result["profile"] = self.config.profile
        result["model"] = self.config.model
        result["prompt_version"] = self.prompt_version
        result["generated_at"] = _timestamp()

        stereotype_score = result.get("stereotype_risk_score")
        if isinstance(stereotype_score, (int, float)):
            bounded = max(1, min(int(round(float(stereotype_score))), 5))
            persona.profile.audit_evidence_layer["stereotype_risk_score"] = bounded
            persona.audit["stereotype_risk_score"] = bounded
        return result
