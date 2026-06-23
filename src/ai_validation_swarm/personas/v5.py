from __future__ import annotations

import copy
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from ai_validation_swarm.domain.models import PersonaSeed, PersonaSkill, SyntheticUser
from ai_validation_swarm.personas.v2 import prompt_path
from ai_validation_swarm.personas.v3_1 import build_diversity_report_v3_1
from ai_validation_swarm.personas.v3_1_2 import RAW_ENUM_TOKENS
from ai_validation_swarm.personas.validator import ensure_valid_persona_artifact
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig, OpenAIResponsesClient
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json


GENERATOR_VERSION = "persona-generator/v5"
PROMPT_VERSION = "persona-synthesis/v5.md"
AUDIT_PROMPT_VERSION = "quality-auditor/v5.md"
SYNTHETIC_DISCLAIMER = (
    "This is a synthetic user for AI pre-validation only. It is not a real person and does not replace human market research."
)
DO_NOT_USE_FOR = [
    "claims about real market demand",
    "discriminatory targeting or exclusion",
    "high-stakes decisions without human evidence",
]
BASE_PROFILE_SECTIONS = tuple(
    field.name
    for field in fields(SyntheticUser)
    if field.name not in {
        "audit_evidence_layer",
        "generation_status",
        "extensions",
        "consistency_exceptions",
        "human_difference_axes",
        "banking_context",
    }
)
OPTIONAL_GUIDED_PROFILE_SECTIONS = ("human_difference_axes", "banking_context")

LLM_PROFILE_FIELDS = BASE_PROFILE_SECTIONS

PROFILE_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "basic_identity": (
        "name", "age", "gender", "location", "language", "occupation", "education_level",
        "income_level", "marital_status", "family_structure", "household_size", "living_area", "housing_status",
    ),
    "personality_belief": ("decision_style", "risk_tolerance", "trust_orientation"),
    "technology_profile": ("tech_savviness", "privacy_concern", "automation_openness"),
    "economic_profile": ("price_sensitivity", "subscription_tolerance", "switching_cost"),
    "values": ("core_values", "fears", "aspirations"),
    "life_story": ("career_path", "current_daily_routine", "frustrations"),
    "behavior_profile": ("buying_behavior", "decision_blockers"),
    "problem_context": ("active_pain_points", "jobs_to_be_done", "willingness_to_pay"),
    "sensitive_reality_layer": ("fairness_and_inclusion_profile", "response_boundaries"),
}

OPTIONAL_GUIDED_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "human_difference_axes": (
        "control_preference",
        "trust_style",
        "complexity_tolerance",
        "decision_tempo",
        "financial_attention_cadence",
        "relationship_to_money",
        "risk_orientation",
        "need_for_explanation",
        "life_load",
        "fragmentation_reality",
        "guidance_preference",
        "reflection_style",
    ),
    "banking_context": (
        "bank_relationship",
        "investment_experience",
        "investment_products_held",
        "investable_assets_band",
        "monthly_income_band",
        "primary_financial_goal",
        "current_investment_decision_process",
        "relationship_manager_usage",
        "digital_banking_usage",
        "trust_in_bank",
        "trust_in_blackrock_or_institutional_brand",
        "risk_understanding_level",
        "portfolio_complexity",
        "external_asset_fragmentation",
        "data_sharing_comfort",
        "advisory_preference",
        "fee_sensitivity",
        "past_bad_investment_experience",
        "suitability_sensitivity",
    ),
}

DEEP_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "childhood_environment": (
        "family_structure_and_stability", "caregiver_dynamics", "emotional_climate", "money_environment",
        "authority_and_rules", "ordinary_childhood_scenes", "adult_decision_links", "uncertainty_notes",
    ),
    "canonical_biography": (
        "life_arc_summary", "decade_timeline", "formative_events", "current_identity", "current_daily_life",
        "product_research_implications",
    ),
    "pricing_logic": (
        "price_sensitivity_level", "personal_payment_comfort", "preferred_pricing_model", "pricing_objection",
        "what_makes_price_feel_fair",
    ),
    "product_reaction_rules": (
        "first_checks", "positive_signals", "negative_signals", "questions_they_would_ask",
        "difference_between_curiosity_and_purchase",
    ),
    "local_grounding_layer": (
        "city_or_region_specific_context", "payment_and_commerce_context", "language_switching_scenes",
        "trust_cues_in_this_market", "local_discovery_channels",
    ),
    "persona_voiceprint": (
        "speaking_style", "directness_pattern", "example_positive_reaction", "example_polite_rejection",
        "example_hard_rejection", "example_near_purchase_question",
    ),
    "interests_and_hobbies": (
        "primary_interests", "low_energy_hobbies", "social_hobbies", "private_hobbies", "aspirational_hobbies",
        "abandoned_hobbies", "interest_depth",
    ),
    "product_discovery_paths": ("most_likely_first_touchpoint", "channels_that_work", "trial_trigger", "conversion_path"),
    "objection_language_style": (
        "polite_objection_examples", "what_they_say_when_they_are_genuinely_interested",
        "what_they_ask_when_they_are_close_to_trying", "what_they_ask_when_they_are_close_to paying",
    ),
}

SENSITIVE_SCENARIOS = (
    "identity_disclosure", "privacy_and_data", "political_or_public_expression", "fairness_and_inclusion",
    "family_or_household_assumptions", "workplace_visibility", "financial_vulnerability", "health_or_wellbeing_sensitivity",
)

CROSS_DOMAIN_CATEGORIES = (
    "generic_new_product", "ai_product", "subscription_product", "family_or_household_product",
    "health_or_wellbeing_product", "financial_product", "education_or_child_product",
    "workflow_or_productivity_product", "identity_sensitive_product", "high_friction_onboarding",
)
FLEXIBLE_PROFILE_SECTIONS = {
    "daily_micro_behaviours",
    "identity_symbols",
    "sensitive_scenario_salience",
}

SUMMARY_WRAPPABLE_PROFILE_SECTIONS = {
    "domain_fit",
    "workflow_adoption_model",
    "identity_and_inclusion_reaction",
    "media_and_content_diet",
    "social_circle_and_communities",
    "taste_and_aesthetic_preferences",
    "spending_and_leisure_patterns",
    "personal_environment",
    "emotional_regulation_style",
    "hidden_habits",
    "cultural_texture",
    "deep_research_notes",
    "panel_role_profile",
    "identity_language",
    "small_business_context",
}


def _contract_profile_sections(guide: dict[str, Any]) -> tuple[str, ...]:
    requested = guide.get("required_profile_sections", [])
    if not isinstance(requested, list):
        requested = []
    extras = [
        section
        for section in requested
        if section in OPTIONAL_GUIDED_PROFILE_SECTIONS
    ]
    return tuple(dict.fromkeys((*BASE_PROFILE_SECTIONS, *extras)))


def _contract_required_profile_fields(guide: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    required = dict(PROFILE_REQUIRED_FIELDS)
    for section in _contract_profile_sections(guide):
        if section in OPTIONAL_GUIDED_REQUIRED_FIELDS:
            required[section] = OPTIONAL_GUIDED_REQUIRED_FIELDS[section]
    return required


def _contract_concept_output_fields(guide: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    contracts = guide.get("concept_output_contracts", {})
    if not isinstance(contracts, dict):
        return {}
    output: dict[str, tuple[str, ...]] = {}
    for concept_key, raw_contract in contracts.items():
        if not isinstance(concept_key, str) or not isinstance(raw_contract, dict):
            continue
        required_fields = raw_contract.get("required_fields", [])
        if isinstance(required_fields, list) and all(isinstance(item, str) and item.strip() for item in required_fields):
            output[concept_key] = tuple(required_fields)
    return output


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resume_seed_from_artifacts(target_dir: Path) -> int | None:
    log_path = target_dir / "generation.log.jsonl"
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("event") == "generation.started" and isinstance(record.get("random_seed"), int):
                return int(record["random_seed"])

    notes_path = target_dir / "generation_notes.json"
    if notes_path.exists():
        notes = read_json(notes_path)
        if isinstance(notes, dict) and isinstance(notes.get("random_seed"), int):
            return int(notes["random_seed"])

    request_path = target_dir / "llm_request.json"
    if request_path.exists():
        request_payload = read_json(request_path)
        if isinstance(request_payload, dict):
            user_payload = request_payload.get("user_payload")
            if isinstance(user_payload, dict) and isinstance(user_payload.get("random_seed"), int):
                return int(user_payload["random_seed"])
    return None


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _string_values(item)]
    if isinstance(value, list):
        return [text for item in value for text in _string_values(item)]
    return []


class GenerationEventLog:
    def __init__(self, path: Path, writer: Callable[[str], None] | None = None) -> None:
        self.path = path
        self.writer = writer
        ensure_dir(path.parent)

    def emit(self, event: str, **payload: Any) -> None:
        record = {"timestamp": _timestamp(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        if self.writer is not None:
            summary = " ".join(f"{key}={value}" for key, value in payload.items() if key not in {"detail", "payload"})
            self.writer(f"[v5] {event}{(' ' + summary) if summary else ''}")


@dataclass(slots=True)
class V5SynthesisRequest:
    synthetic_user_id: str
    random_seed: int
    guide: dict[str, Any]
    prompt_text: str
    attempt: int = 1

    def contract(self) -> dict[str, Any]:
        profile_sections = _contract_profile_sections(self.guide)
        required_profile_fields = _contract_required_profile_fields(self.guide)
        concept_output_fields = _contract_concept_output_fields(self.guide)
        return {
            "profile_sections": list(profile_sections),
            "required_profile_fields": {key: list(value) for key, value in required_profile_fields.items()},
            "required_depth_fields": {key: list(value) for key, value in DEEP_REQUIRED_FIELDS.items()},
            "childhood": {"minimum_scenes": 3, "minimum_adult_decision_links": 4},
            "nested_shapes": {
                "basic_identity.language": "array of non-empty language strings",
                "values.core_values/fears/aspirations": "each is an array of non-empty strings",
                "life_story.frustrations": "array of non-empty strings",
                "behavior_profile.decision_blockers": "array of non-empty strings",
                "problem_context.active_pain_points/jobs_to_be_done": "each is an array of non-empty strings",
                "sensitive_reality_layer.response_boundaries": "array of non-empty strings",
                "decision_policy.trust_requirements/rejection_triggers/proof_requirements": "each is an array of non-empty strings",
                "childhood_environment.ordinary_childhood_scenes": {
                    "type": "array<object>",
                    "minimum_items": 3,
                    "fields": ["age", "setting", "scene", "lesson_at_the_time", "adult_echo"],
                },
                "childhood_environment.adult_decision_links": {
                    "type": "array<object>",
                    "minimum_items": 4,
                    "fields": ["childhood_pattern", "adult_value_or_assumption", "product_judgment_effect", "limits_of_inference"],
                },
                "canonical_biography.decade_timeline": {
                    "type": "array<object>",
                    "minimum_specific_scenes": 3,
                    "fields": [
                        "age_range", "chapter_title", "life_context", "specific_scene", "product_relevant_memory",
                        "social_or_relationship_context", "money_or_effort_tradeoff", "beliefs_formed",
                        "current_reaction_link", "formative_level",
                    ],
                },
                "canonical_biography.formative_events": {
                    "type": "array<object>",
                    "fields": ["age_range", "event_summary", "impact"],
                },
                "contradiction_map": {
                    "type": "array<object>",
                    "minimum_items": 4,
                    "fields": ["contradiction", "how_it_shows_up", "product_validation_effect"],
                },
                "interests_and_hobbies.interest_depth": {
                    "type": "object",
                    "fields": ["interest_name", "depth_level", "why_it_matters", "how_it_shapes_purchase_behaviour", "related_products_they_notice", "related_products_they_ignore"],
                },
            },
            "biography": {"minimum_specific_scenes": 3, "timeline_stops_at_current_age": True},
            "contradiction_map": {"minimum_items": 4, "items_must_be_objects": True},
            "cross_domain_product_reaction_model": {
                "categories": list(CROSS_DOMAIN_CATEGORIES),
                "fields_per_category": [
                    "reaction_basis", "first_question", "positive_trigger", "negative_trigger",
                    "trust_requirement", "likely_objection", "persona_specific_example",
                ],
            },
            "sensitive_scenario_reactions": {"categories": list(SENSITIVE_SCENARIOS)},
            "decision_policy": ["adoption_style", "trust_requirements", "rejection_triggers", "proof_requirements"],
            "response_style": ["articulation_level", "directness", "detail_tendency"],
            "concept_outputs": (
                {
                    "mode": "required_when_declared",
                    "contracts": {key: list(value) for key, value in concept_output_fields.items()},
                }
                if concept_output_fields
                else {"mode": "none"}
            ),
        }

    def payload(self) -> dict[str, Any]:
        return {
            "task": "Create one complete V5 synthetic user in a single coherent synthesis pass.",
            "synthetic_user_id": self.synthetic_user_id,
            "random_seed": self.random_seed,
            "guide": self.guide,
            "guide_rules": {
                "fixed": "Values under guide.fixed must be followed exactly unless physically impossible.",
                "preferred": "Values under guide.preferred should shape the persona but can be reconciled for coherence.",
                "open": "Everything not guided is selected by the model for plausible breadth and coherence.",
            },
            "contract": self.contract(),
            "attempt": self.attempt,
        }


@dataclass(slots=True)
class V5SynthesisResult:
    profile: dict[str, Any]
    decision_policy: dict[str, Any]
    response_style: dict[str, Any]
    narrative: str
    generation_rationale: str
    quality_self_review: dict[str, Any]
    concept_outputs: dict[str, Any]
    provider: str
    model: str
    metadata: dict[str, Any]


class V5SynthesisAdapter(Protocol):
    def synthesize(self, request: V5SynthesisRequest) -> V5SynthesisResult: ...


def build_v5_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "profile", "decision_policy", "response_style", "narrative", "generation_rationale", "quality_self_review"
        ],
        "properties": {
            "profile": {"type": "object"},
            "decision_policy": {"type": "object"},
            "response_style": {"type": "object"},
            "narrative": {"type": "string"},
            "generation_rationale": {"type": "string"},
            "quality_self_review": {"type": "object"},
            "concept_outputs": {"type": "object"},
        },
    }


class OpenAIV5SynthesisAdapter:
    def __init__(self, client: OpenAIResponsesClient, config: OpenAIProviderConfig) -> None:
        self.client = client
        self.config = config

    def synthesize(self, request: V5SynthesisRequest) -> V5SynthesisResult:
        payload = self.client.create_json_response(
            system_prompt=request.prompt_text,
            user_prompt=json.dumps(request.payload(), ensure_ascii=False, indent=2),
            output_schema=build_v5_output_schema(),
            use_transport_output_schema=self.config.transport != "codex_sdk_node",
        )
        return V5SynthesisResult(
            profile=dict(payload.get("profile", {})),
            decision_policy=dict(payload.get("decision_policy", {})),
            response_style=dict(payload.get("response_style", {})),
            narrative=str(payload.get("narrative", "")).strip(),
            generation_rationale=str(payload.get("generation_rationale", "")).strip(),
            quality_self_review=dict(payload.get("quality_self_review", {})),
            concept_outputs=dict(payload.get("concept_outputs", {})),
            provider="codex" if self.config.transport.startswith("codex") else "openai",
            model=self.config.model,
            metadata={
                "transport": self.config.transport,
                "auth_source": self.config.auth_source,
                "reasoning_effort": self.config.model_reasoning_effort,
                "transport_metadata": copy.deepcopy(self.client.last_transport_metadata),
            },
        )


def _result_from_payload(payload: dict[str, Any]) -> V5SynthesisResult:
    return V5SynthesisResult(
        profile=dict(payload.get("profile", {})),
        decision_policy=dict(payload.get("decision_policy", {})),
        response_style=dict(payload.get("response_style", {})),
        narrative=str(payload.get("narrative", "")).strip(),
        generation_rationale=str(payload.get("generation_rationale", "")).strip(),
        quality_self_review=dict(payload.get("quality_self_review", {})),
        concept_outputs=dict(payload.get("concept_outputs", {})),
        provider=str(payload.get("provider", "")),
        model=str(payload.get("model", "")),
        metadata=dict(payload.get("metadata", {})),
    )


def normalize_v5_result_structure(result: V5SynthesisResult) -> list[str]:
    """Apply lossless container coercions only; never synthesize persona content."""
    changes: list[str] = []
    list_paths = (
        (result.profile.get("basic_identity", {}), "language", "basic_identity.language"),
        (result.profile.get("values", {}), "core_values", "values.core_values"),
        (result.profile.get("values", {}), "fears", "values.fears"),
        (result.profile.get("values", {}), "aspirations", "values.aspirations"),
        (result.profile.get("life_story", {}), "frustrations", "life_story.frustrations"),
        (result.profile.get("behavior_profile", {}), "decision_blockers", "behavior_profile.decision_blockers"),
        (result.profile.get("problem_context", {}), "active_pain_points", "problem_context.active_pain_points"),
        (result.profile.get("problem_context", {}), "jobs_to_be_done", "problem_context.jobs_to_be_done"),
        (result.profile.get("sensitive_reality_layer", {}), "response_boundaries", "sensitive_reality_layer.response_boundaries"),
        (result.decision_policy, "trust_requirements", "decision_policy.trust_requirements"),
        (result.decision_policy, "rejection_triggers", "decision_policy.rejection_triggers"),
        (result.decision_policy, "proof_requirements", "decision_policy.proof_requirements"),
    )
    for container, key, path in list_paths:
        if isinstance(container, dict) and isinstance(container.get(key), str) and container[key].strip():
            container[key] = [container[key].strip()]
            changes.append(f"wrapped_single_string_as_list:{path}")
    for section_name in SUMMARY_WRAPPABLE_PROFILE_SECTIONS:
        section_value = result.profile.get(section_name)
        if isinstance(section_value, str) and section_value.strip():
            result.profile[section_name] = {"summary": section_value.strip()}
            changes.append(f"wrapped_string_as_object:{section_name}")
    scenarios = result.profile.get("sensitive_scenario_reactions")
    if isinstance(scenarios, dict):
        for key, value in list(scenarios.items()):
            if isinstance(value, str) and value.strip():
                scenarios[key] = {"reaction": value.strip()}
                changes.append(f"wrapped_string_as_object:sensitive_scenario_reactions.{key}")
    return changes


def validate_v5_result(result: V5SynthesisResult, persona_id: str, guide: dict[str, Any] | None = None) -> list[str]:
    findings: list[str] = []
    guide = guide or {}
    profile_sections = _contract_profile_sections(guide)
    required_profile_fields = _contract_required_profile_fields(guide)
    concept_output_fields = _contract_concept_output_fields(guide)
    for section in profile_sections:
        value = result.profile.get(section)
        expected_list = section == "contradiction_map"
        if expected_list and not isinstance(value, list):
            findings.append(f"profile_section_type:{section}:list")
        elif section in FLEXIBLE_PROFILE_SECTIONS and not _is_present(value):
            findings.append(f"profile_section_type:{section}:present")
        elif not expected_list and section not in FLEXIBLE_PROFILE_SECTIONS and not isinstance(value, dict):
            findings.append(f"profile_section_type:{section}:object")
    for section, required in {**required_profile_fields, **DEEP_REQUIRED_FIELDS}.items():
        payload = result.profile.get(section, {})
        if not isinstance(payload, dict):
            continue
        for field_name in required:
            if not _is_present(payload.get(field_name)):
                findings.append(f"missing:{section}.{field_name}")

    identity = result.profile.get("basic_identity", {})
    age = identity.get("age") if isinstance(identity, dict) else None
    if not isinstance(age, int) or isinstance(age, bool) or not 18 <= age <= 85:
        findings.append("invalid:basic_identity.age")
    if isinstance(identity, dict) and identity.get("synthetic_user_id") not in {None, "", persona_id}:
        findings.append("invalid:basic_identity.synthetic_user_id")
    if isinstance(identity, dict) and (
        not isinstance(identity.get("language"), list)
        or not all(isinstance(item, str) and item.strip() for item in identity.get("language", []))
    ):
        findings.append("invalid:basic_identity.language:list_of_strings")

    childhood = result.profile.get("childhood_environment", {})
    if isinstance(childhood, dict):
        childhood_scenes = childhood.get("ordinary_childhood_scenes", [])
        if not isinstance(childhood_scenes, list) or len(childhood_scenes) < 3:
            findings.append("minimum:childhood_environment.ordinary_childhood_scenes:3")
        elif any(not isinstance(item, dict) or not all(_is_present(item.get(key)) for key in (
            "age", "setting", "scene", "lesson_at_the_time", "adult_echo"
        )) for item in childhood_scenes):
            findings.append("invalid:childhood_environment.ordinary_childhood_scenes:object_shape")
        adult_links = childhood.get("adult_decision_links", [])
        if not isinstance(adult_links, list) or len(adult_links) < 4:
            findings.append("minimum:childhood_environment.adult_decision_links:4")
        elif any(not isinstance(item, dict) or not all(_is_present(item.get(key)) for key in (
            "childhood_pattern", "adult_value_or_assumption", "product_judgment_effect", "limits_of_inference"
        )) for item in adult_links):
            findings.append("invalid:childhood_environment.adult_decision_links:object_shape")
    biography = result.profile.get("canonical_biography", {})
    if isinstance(biography, dict):
        timeline = biography.get("decade_timeline", [])
        if not isinstance(timeline, list):
            timeline = []
        invalid_chapters = [chapter for chapter in timeline if not isinstance(chapter, dict)]
        if invalid_chapters:
            findings.append("invalid:canonical_biography.decade_timeline:object_shape")
        scenes = [chapter for chapter in timeline if isinstance(chapter, dict) and chapter.get("specific_scene")]
        if len(scenes) < 3:
            findings.append("minimum:canonical_biography.specific_scenes:3")
    contradictions = result.profile.get("contradiction_map", [])
    if isinstance(contradictions, list) and len(contradictions) < 4:
        findings.append("minimum:contradiction_map:4")
    elif isinstance(contradictions, list) and any(not isinstance(item, dict) for item in contradictions):
        findings.append("invalid:contradiction_map:object_shape")
    cross_domain = result.profile.get("cross_domain_product_reaction_model", {})
    if isinstance(cross_domain, dict):
        for category in CROSS_DOMAIN_CATEGORIES:
            block = cross_domain.get(category, {})
            if not isinstance(block, dict) or not all(_is_present(block.get(key)) for key in (
                "reaction_basis", "first_question", "positive_trigger", "negative_trigger",
                "trust_requirement", "likely_objection", "persona_specific_example",
            )):
                findings.append(f"incomplete:cross_domain_product_reaction_model.{category}")
    scenarios = result.profile.get("sensitive_scenario_reactions", {})
    if isinstance(scenarios, dict):
        for category in SENSITIVE_SCENARIOS:
            if not isinstance(scenarios.get(category), dict) or not scenarios.get(category):
                findings.append(f"missing:sensitive_scenario_reactions.{category}")
    for field_name in ("adoption_style", "trust_requirements", "rejection_triggers", "proof_requirements"):
        if not _is_present(result.decision_policy.get(field_name)):
            findings.append(f"missing:decision_policy.{field_name}")
    for field_name in ("articulation_level", "directness", "detail_tendency"):
        if not _is_present(result.response_style.get(field_name)):
            findings.append(f"missing:response_style.{field_name}")
    if concept_output_fields:
        if not isinstance(result.concept_outputs, dict):
            findings.append("invalid:concept_outputs")
        else:
            for concept_key, required_fields in concept_output_fields.items():
                payload = result.concept_outputs.get(concept_key, {})
                if not isinstance(payload, dict):
                    findings.append(f"missing:concept_outputs.{concept_key}")
                    continue
                for field_name in required_fields:
                    if not _is_present(payload.get(field_name)):
                        findings.append(f"missing:concept_outputs.{concept_key}.{field_name}")
    if not result.narrative:
        findings.append("missing:narrative")
    prose = "\n".join(_string_values(result.profile) + _string_values(result.concept_outputs) + [result.narrative])
    leaked = sorted(token for token in RAW_ENUM_TOKENS if token in prose)
    if leaked:
        findings.append(f"enum_leakage:{','.join(leaked)}")
    return findings


def _age_band(age: int) -> str:
    lower = max(18, (age // 10) * 10)
    upper = lower + 9
    return f"{lower}-{upper}"


def _mapping_value_text(payload: Any, key: str, default: str = "") -> str:
    if isinstance(payload, dict):
        value = payload.get(key)
        return str(value) if _is_present(value) else default
    return default


def _build_seed(persona_id: str, profile: dict[str, Any]) -> PersonaSeed:
    identity = profile["basic_identity"]
    economics = profile["economic_profile"]
    technology = profile["technology_profile"]
    panel = profile.get("panel_role_profile", {})
    age = int(identity["age"])
    return PersonaSeed(
        seed_id=f"v5-{persona_id}",
        panel_role=str(panel.get("panel_role") or "general_research_participant"),
        age_band=_age_band(age),
        location_type=str(identity.get("living_area") or "urban_or_regional"),
        household_structure=str(identity["family_structure"]),
        occupation_band=str(identity["occupation"]),
        occupation_title=str(identity["occupation"]),
        income_band=str(identity["income_level"]),
        education_band=str(identity["education_level"]),
        language=list(identity["language"]),
        device_environment=str(technology.get("device_environment") or technology.get("tech_savviness")),
        payment_environment=str(economics.get("payment_environment") or "locally typical digital and bank payments"),
        schedule_pressure=_mapping_value_text(profile.get("daily_micro_behaviours"), "stress_moments", "context dependent"),
        budget_flexibility=str(economics.get("budget_flexibility") or economics.get("price_sensitivity")),
        caregiving_load=_mapping_value_text(profile.get("life_story"), "caregiving_context", "context dependent"),
        trust_threshold=str(profile["personality_belief"].get("trust_orientation")),
        switching_cost_level=str(economics.get("switching_cost")),
        privacy_risk_tolerance=str(technology.get("privacy_concern")),
        digital_literacy_ceiling=str(technology.get("tech_savviness")),
        locale_pack=str(identity.get("location", "")),
        life_stage=str(identity.get("life_stage") or f"adult age {age}"),
        purchase_authority_type=str(economics.get("purchase_authority_type") or "context dependent"),
        employment_stability=str(economics.get("employment_stability") or "not specified"),
        workflow_maturity=_mapping_value_text(profile.get("workflow_adoption_model"), "setup_tolerance", "context dependent"),
        decision_speed=str(profile["personality_belief"].get("decision_style")),
        proof_threshold=_mapping_value_text(profile.get("product_reaction_rules"), "evidence_that_changes_their_mind", "context dependent"),
        cash_flow_volatility=str(economics.get("cash_flow_volatility") or "not specified"),
    )


def result_to_persona(result: V5SynthesisResult, persona_id: str) -> PersonaSkill:
    profile_payload = copy.deepcopy(result.profile)
    identity = profile_payload.setdefault("basic_identity", {})
    identity["synthetic_user_id"] = persona_id
    profile_payload.setdefault("human_difference_axes", {})
    profile_payload.setdefault("banking_context", {})
    profile_payload["audit_evidence_layer"] = {
        "persona_generation_method": "single_pass_llm_v5_synthesis",
        "persona_version": "v5",
        "generator_version": GENERATOR_VERSION,
        "evidence_grade": "synthetic_prevalidation_only",
        "synthetic_only_disclaimer": SYNTHETIC_DISCLAIMER,
        "do_not_use_for": DO_NOT_USE_FOR,
        "last_audited_at": datetime.now(UTC).date().isoformat(),
    }
    profile_payload["generation_status"] = {
        "status": "accepted",
        "can_enter_library": True,
        "can_enter_validation_runner": True,
        "blocking_issues": [],
    }
    profile_payload.setdefault("extensions", {})
    profile_payload.setdefault("consistency_exceptions", [])
    allowed = {field.name for field in fields(SyntheticUser)}
    unknown = sorted(set(profile_payload) - allowed)
    if unknown:
        raise ValueError(f"V5 profile returned unknown sections: {', '.join(unknown)}")
    missing = sorted(allowed - set(profile_payload))
    if missing:
        raise ValueError(f"V5 profile missing sections: {', '.join(missing)}")
    profile = SyntheticUser(**profile_payload)
    seed = _build_seed(persona_id, profile_payload)
    audit_evidence = copy.deepcopy(profile.audit_evidence_layer)
    persona = PersonaSkill(
        skill_version="v5",
        seed=seed,
        profile=profile,
        decision_policy=copy.deepcopy(result.decision_policy),
        response_style=copy.deepcopy(result.response_style),
        narrative=result.narrative,
        audit={**audit_evidence},
    )
    ensure_valid_persona_artifact(persona)
    return persona


def _usage_and_cost(metadata: dict[str, Any], input_text: str, output_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    usage = copy.deepcopy(metadata.get("transport_metadata", {}).get("usage", {}))
    if not usage:
        input_estimate = max(1, len(input_text) // 4)
        output_estimate = max(1, len(output_text) // 4)
        usage = {
            "input_tokens_estimated": input_estimate,
            "output_tokens_estimated": output_estimate,
            "total_tokens_estimated": input_estimate + output_estimate,
            "source": "estimated_from_text",
        }
    input_tokens = usage.get("input_tokens") or usage.get("input_tokens_estimated") or 0
    output_tokens = usage.get("output_tokens") or usage.get("output_tokens_estimated") or 0
    input_rate = float(os.getenv("AI_VALIDATION_INPUT_COST_PER_MILLION", "0") or 0)
    output_rate = float(os.getenv("AI_VALIDATION_OUTPUT_COST_PER_MILLION", "0") or 0)
    configured = input_rate > 0 or output_rate > 0
    cost = ((input_tokens * input_rate) + (output_tokens * output_rate)) / 1_000_000 if configured else None
    return usage, {
        "currency": "USD",
        "estimated_cost": round(cost, 6) if cost is not None else None,
        "input_cost_per_million": input_rate or None,
        "output_cost_per_million": output_rate or None,
        "note": "Set AI_VALIDATION_INPUT_COST_PER_MILLION and AI_VALIDATION_OUTPUT_COST_PER_MILLION for a monetary estimate." if not configured else "Estimate based on configured per-million token rates.",
    }


def _quality_report(persona: PersonaSkill, result: V5SynthesisResult) -> dict[str, Any]:
    profile = persona.profile
    local_count = len(profile.local_grounding_layer.get("city_or_region_specific_context", []))
    scene_count = sum(1 for chapter in profile.canonical_biography.get("decade_timeline", []) if chapter.get("specific_scene"))
    return {
        "status": "accepted_with_human_review",
        "scores": {
            "structure_completeness": 5,
            "biography_depth": 4 if scene_count >= 3 else 2,
            "lived_scene_quality": 4 if scene_count >= 3 else 2,
            "local_grounding": 4 if local_count >= 3 else 3,
            "product_reaction_readiness": 4,
            "sensitive_topic_readiness": 4,
            "voice_distinctiveness": 4,
            "overall": 4,
        },
        "strengths": list(result.quality_self_review.get("strengths", []))[:5],
        "weaknesses": list(result.quality_self_review.get("weaknesses", []))[:5] or ["Human review has not yet calibrated realism."],
        "uncertainties": list(result.quality_self_review.get("uncertainties", []))[:5],
        "human_review_priorities": list(result.quality_self_review.get("human_review_priorities", []))[:5],
        "auditor_mode": "deterministic_contract_plus_model_self_review",
        "human_review_needed": True,
    }


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(_as_text(item) for item in value if _as_text(item))
    if isinstance(value, dict):
        return "; ".join(
            f"{key.replace('_', ' ')}: {_as_text(item)}"
            for key, item in value.items()
            if _as_text(item)
        )
    if value is None:
        return ""
    return str(value)


def _bullet_lines(values: Any) -> list[str]:
    if isinstance(values, list):
        return [f"- {_as_text(item)}" for item in values if _as_text(item)]
    text = _as_text(values)
    return [f"- {text}"] if text else []


def _render_v5_artifacts(persona: PersonaSkill) -> dict[str, str]:
    profile = persona.profile
    identity = profile.basic_identity
    name = str(identity.get("name", persona.profile.synthetic_user_id))
    biography = profile.canonical_biography
    childhood = profile.childhood_environment
    voice = profile.persona_voiceprint
    human_difference_axes = profile.human_difference_axes
    banking_context = profile.banking_context
    disclaimer = f"> {SYNTHETIC_DISCLAIMER}"

    persona_md = "\n".join([
        f"# {name}", "", disclaimer, "", persona.narrative.strip(), "",
        f"**Location:** {_as_text(identity.get('location'))}",
        f"**Occupation:** {_as_text(identity.get('occupation'))}",
        f"**Research role:** {_as_text(profile.panel_role_profile.get('research_function') or profile.panel_role_profile.get('panel_role'))}",
        "",
    ])
    if human_difference_axes:
        persona_md += "\n".join(["**Human Difference Axes:**", _as_text(human_difference_axes), "", ""])
    if banking_context:
        persona_md += "\n".join(["**Banking Context:**", _as_text(banking_context), "", ""])

    bio_lines = [f"# {name} - Level 3 Synthetic User Biography", "", disclaimer, "", "## Life Arc Summary", "", _as_text(biography.get("life_arc_summary")), ""]
    bio_lines.extend(["## Childhood Environment", "", _as_text(childhood.get("family_structure_and_stability")), ""])
    for scene in childhood.get("ordinary_childhood_scenes", []):
        if isinstance(scene, dict):
            bio_lines.extend([
                f"### Age {_as_text(scene.get('age'))}: {_as_text(scene.get('setting'))}", "",
                _as_text(scene.get("scene")), "",
                f"Early lesson: {_as_text(scene.get('lesson_at_the_time'))}",
                f"Adult echo: {_as_text(scene.get('adult_echo'))}", "",
            ])
    for chapter in biography.get("decade_timeline", []):
        if not isinstance(chapter, dict):
            continue
        bio_lines.extend([
            f"## {_as_text(chapter.get('age_range'))}: {_as_text(chapter.get('chapter_title'))}", "",
            _as_text(chapter.get("life_context")), "", _as_text(chapter.get("specific_scene")), "",
            f"Product-relevant memory: {_as_text(chapter.get('product_relevant_memory'))}",
            f"Relationships: {_as_text(chapter.get('social_or_relationship_context'))}",
            f"Money or effort trade-off: {_as_text(chapter.get('money_or_effort_tradeoff'))}",
            f"Current reaction link: {_as_text(chapter.get('current_reaction_link'))}", "",
        ])
    bio_lines.extend([
        "## Current Life", "", _as_text(biography.get("current_daily_life")), "",
        "## Interests & Private Life", "", _as_text(profile.interests_and_hobbies), "",
        "## Media Diet & Product Discovery", "", _as_text(profile.media_and_content_diet), "", _as_text(profile.product_discovery_paths), "",
        "## Ordinary Day in Detail", "", _as_text(profile.daily_micro_behaviours), "",
        "## Hidden Habits & Contradictions", "", _as_text(profile.hidden_habits), "",
    ])
    bio_lines.extend(_bullet_lines(profile.contradiction_map))
    bio_lines.extend(["", "## Product Research Implications", "", _as_text(biography.get("product_research_implications")), "", "## What This Persona Should Not Be Used For", ""])
    bio_lines.extend(f"- {item}" for item in DO_NOT_USE_FOR)
    bio_lines.append("")

    kernel_lines = [
        f"# Research Kernel: {name}", "", disclaimer, "", "## Identity", "",
        f"{name} is {_as_text(identity.get('age'))}, lives in {_as_text(identity.get('location'))}, and works as {_as_text(identity.get('occupation'))}.", "",
        "## Life Arc", "", _as_text(biography.get("life_arc_summary")), "",
        "## Current Context", "", _as_text(profile.life_story.get("current_daily_routine")), "",
        "## Values, Trust & Buying Logic", "", _as_text(profile.values), "", _as_text(persona.decision_policy), "",
        "## Pricing Logic", "", _as_text(profile.pricing_logic), "",
        "## Technology Attitude", "", _as_text(profile.technology_profile), "",
        "## Interests That Affect Buying", "", _as_text(profile.interests_and_hobbies.get("interest_depth")), "",
        "## Discovery Path & Daily Friction", "", _as_text(profile.product_discovery_paths), "", _as_text(profile.daily_micro_behaviours), "",
    ]
    if human_difference_axes:
        kernel_lines.extend(["## Human Difference Axes", "", _as_text(human_difference_axes), ""])
    if banking_context:
        kernel_lines.extend(["## Banking Context", "", _as_text(banking_context), ""])
    kernel_lines.extend(["## Contradictions", ""])
    kernel_lines.extend(_bullet_lines(profile.contradiction_map))
    kernel_lines.extend(["", "## Objection Language", "", _as_text(profile.objection_language_style), "", "## Founder Misread Risk", "", _as_text(profile.deep_research_notes.get("what_a_founder_might_misread_about_them")), "", "## Response Rule", "", "Do not flatter the founder. Separate curiosity, trial, payment, and durable adoption.", ""])

    skill_lines = [
        f"# Synthetic User Skill: {name}", "", "## Role", "", disclaimer, "", "Respond as this synthetic persona for AI pre-validation while never claiming to be a real person.", "",
        "## Identity", "", _as_text(identity), "", "## Canonical Life Arc", "", _as_text(biography.get("life_arc_summary")), "",
        "## Childhood Foundations", "", _as_text(childhood.get("adult_decision_links")), "",
        "## Current Life", "", _as_text(biography.get("current_daily_life")), "",
        "## Lifestyle & Interests", "", _as_text(profile.interests_and_hobbies), "",
        "## Daily Context", "", _as_text(profile.daily_micro_behaviours), "",
        "## Discovery & Trust Path", "", _as_text(profile.product_discovery_paths), "", _as_text(persona.decision_policy.get("trust_requirements")), "",
        "## Decision & Buying Logic", "", _as_text(profile.product_reaction_rules), "", _as_text(profile.behavior_profile), "",
        "## Pricing Logic", "", _as_text(profile.pricing_logic), "", "## Technology & AI Attitude", "", _as_text(profile.technology_profile), "",
        "## Cross-Domain Product Reaction Model", "", _as_text(profile.cross_domain_product_reaction_model), "",
        "## Sensitive Topic Handling", "", _as_text(profile.sensitive_scenario_reactions), "",
        "## Objection Language", "", _as_text(profile.objection_language_style), "",
    ]
    if human_difference_axes:
        skill_lines.extend(["## Human Difference Axes", "", _as_text(human_difference_axes), ""])
    if banking_context:
        skill_lines.extend(["## Banking Context", "", _as_text(banking_context), ""])
    skill_lines.extend(["## Hidden Contradictions", ""])
    skill_lines.extend(_bullet_lines(profile.contradiction_map))
    skill_lines.extend([
        "", "## Founder Misread Risk", "", _as_text(profile.deep_research_notes.get("what_a_founder_might_misread_about_them")), "",
        "## Response Rules", "", "- Do not flatter the founder.", "- Do not pretend to be a real human.",
        "- Separate curiosity from willingness to pay and long-term adoption.", "- Challenge vague claims and name likely abandonment.",
        "- Point out friction, privacy, trust, pricing, and sensitive-topic risks where relevant.", "- If the product is unclear or this persona would not buy, say so.", "",
        "## Example Responses", "", f"- Positive: {_as_text(voice.get('example_positive_reaction'))}",
        f"- Polite rejection: {_as_text(voice.get('example_polite_rejection'))}", f"- Hard rejection: {_as_text(voice.get('example_hard_rejection'))}",
        f"- Near-purchase question: {_as_text(voice.get('example_near_purchase_question'))}", "",
    ])

    local_lines = [f"# Local Grounding: {name}", "", disclaimer, ""]
    for key, value in profile.local_grounding_layer.items():
        local_lines.extend([f"## {key.replace('_', ' ').title()}", "", _as_text(value), ""])
    sensitive_lines = [f"# Sensitive Scenarios: {name}", "", disclaimer, ""]
    for key, value in profile.sensitive_scenario_reactions.items():
        sensitive_lines.extend([f"## {key.replace('_', ' ').title()}", "", _as_text(value), ""])

    return {
        "persona.md": persona_md.rstrip() + "\n",
        "biography.md": "\n".join(bio_lines).rstrip() + "\n",
        "research_kernel.md": "\n".join(kernel_lines).rstrip() + "\n",
        "persona.skill.md": "\n".join(skill_lines).rstrip() + "\n",
        "local_grounding.md": "\n".join(local_lines).rstrip() + "\n",
        "sensitive_scenarios.md": "\n".join(sensitive_lines).rstrip() + "\n",
    }


def _load_comparison_personas(output_dir: Path, persona_id: str) -> list[PersonaSkill]:
    personas: list[PersonaSkill] = []
    if not output_dir.exists():
        return personas
    for folder in sorted(output_dir.iterdir()):
        candidate = folder / "v5"
        if folder.name == persona_id or not (candidate / "profile.json").exists():
            continue
        try:
            personas.append(load_persona(candidate))
        except Exception:
            continue
    return personas


def generate_v5_persona(
    *,
    persona_id: str,
    output_dir: Path,
    adapter: V5SynthesisAdapter,
    guide: dict[str, Any] | None = None,
    random_seed: int | None = None,
    max_transport_attempts: int = 2,
    resume_response: bool = False,
    progress_writer: Callable[[str], None] | None = None,
) -> Path:
    if not persona_id.startswith("su_") or not persona_id[3:].isdigit():
        raise ValueError(f"Invalid synthetic user ID: {persona_id}")
    target_dir = output_dir / persona_id / "v5"
    work_dir = output_dir / ".v5_generation" / persona_id
    seed = random_seed
    if seed is None and resume_response:
        seed = _resume_seed_from_artifacts(target_dir)
    if seed is None:
        seed = random.SystemRandom().randint(1, 2_147_483_647)
    ensure_dir(target_dir)
    ensure_dir(work_dir)
    transport_log_path = target_dir / "llm_transport.log"
    if not transport_log_path.exists():
        transport_log_path.write_text("", encoding="utf-8")
    log = GenerationEventLog(target_dir / "generation.log.jsonl", progress_writer)
    prompt_text = prompt_path(PROMPT_VERSION).read_text(encoding="utf-8").strip()
    stored_guide: dict[str, Any] | None = None
    brief_path = target_dir / "generation_brief.json"
    if guide is None and resume_response and brief_path.exists():
        loaded_brief = read_json(brief_path)
        if isinstance(loaded_brief, dict):
            stored_guide = loaded_brief

    normalized_guide = copy.deepcopy(guide or stored_guide or {"mode": "open", "fixed": {}, "preferred": {}})
    normalized_guide.setdefault("mode", "guided" if guide else "open")
    normalized_guide.setdefault("fixed", {})
    normalized_guide.setdefault("preferred", {})
    request = V5SynthesisRequest(persona_id, seed, normalized_guide, prompt_text)
    request_payload = request.payload()
    write_json(brief_path, normalized_guide)
    write_json(target_dir / "llm_request.json", {
        "prompt_version": PROMPT_VERSION,
        "system_prompt": prompt_text,
        "user_payload": request_payload,
        "input_sha256": _stable_hash({"system_prompt": prompt_text, "user_payload": request_payload}),
    })
    log.emit("generation.started", persona_id=persona_id, random_seed=seed, guide_mode=normalized_guide["mode"])

    result: V5SynthesisResult | None = None
    last_error: Exception | None = None
    started_at = time.perf_counter()
    response_path = target_dir / "llm_response.json"
    if resume_response and response_path.exists():
        saved_payload = json.loads(response_path.read_text(encoding="utf-8"))
        if not isinstance(saved_payload, dict):
            raise ValueError(f"Saved V5 response is not an object: {response_path}")
        result = _result_from_payload(saved_payload)
        log.emit("llm.response.resumed", response_path=str(response_path))
    else:
        for attempt in range(1, max(1, max_transport_attempts) + 1):
            request.attempt = attempt
            log.emit("llm.request.started", attempt=attempt, prompt_version=PROMPT_VERSION)
            try:
                result = adapter.synthesize(request)
                log.emit("llm.request.completed", attempt=attempt, elapsed_seconds=round(time.perf_counter() - started_at, 2))
                break
            except Exception as exc:
                last_error = exc
                log.emit("llm.request.failed", attempt=attempt, error_type=type(exc).__name__, detail=str(exc))
    if result is None:
        write_json(work_dir / "failure.json", {"error": str(last_error), "failed_at": _timestamp()})
        log.emit("generation.failed", stage="transport", detail=str(last_error))
        raise ValueError(f"V5 transport failed for {persona_id}: {last_error}") from last_error

    structural_normalizations = normalize_v5_result_structure(result)
    if structural_normalizations:
        log.emit("response.structure_normalized", detail=structural_normalizations)
    raw_response = {
        "profile": result.profile,
        "decision_policy": result.decision_policy,
        "response_style": result.response_style,
        "narrative": result.narrative,
        "generation_rationale": result.generation_rationale,
        "quality_self_review": result.quality_self_review,
        "concept_outputs": result.concept_outputs,
        "provider": result.provider,
        "model": result.model,
        "metadata": result.metadata,
    }
    write_json(target_dir / "llm_response.json", raw_response)
    write_json(work_dir / "completed_response.json", raw_response)
    findings = validate_v5_result(result, persona_id, normalized_guide)
    if findings:
        write_json(target_dir / "contract_report.json", {"status": "rejected", "findings": findings})
        log.emit("generation.rejected", stage="contract", finding_count=len(findings), detail=findings)
        raise ValueError(f"V5 synthesis contract failed for {persona_id}: {', '.join(findings)}")

    persona = result_to_persona(result, persona_id)
    rendered = _render_v5_artifacts(persona)
    comparisons = _load_comparison_personas(output_dir, persona_id)
    duplicate_report = build_diversity_report_v3_1(persona, comparisons)
    duplicate_report.update({
        "purpose": "reporting and panel selection only",
        "admission_policy": "do_not_reject_natural_human_similarity",
        "generator_version": GENERATOR_VERSION,
    })
    quality_report = _quality_report(persona, result)
    persona.audit.update({
        "generator_version": GENERATOR_VERSION,
        "quality_audit": quality_report,
        "generation_status": persona.profile.generation_status,
    })
    ensure_valid_persona_artifact(persona)

    input_text = prompt_text + "\n" + json.dumps(request_payload, ensure_ascii=False)
    output_text = json.dumps(raw_response, ensure_ascii=False)
    usage, cost = _usage_and_cost(result.metadata, input_text, output_text)
    generation_notes = {
        "synthetic_user_id": persona_id,
        "seed_id": persona.seed.seed_id,
        "generator_version": GENERATOR_VERSION,
        "generation_mode": "single_pass_llm_synthesis",
        "guide_mode": normalized_guide["mode"],
        "provider": result.provider,
        "model_used": result.model,
        "prompt_versions": [PROMPT_VERSION, AUDIT_PROMPT_VERSION],
        "random_seed": seed,
        "transport_attempts": request.attempt,
        "resumed_from_saved_response": resume_response,
        "structural_normalizations": structural_normalizations,
        "generated_at": _timestamp(),
        "elapsed_seconds": round(time.perf_counter() - started_at, 2),
        "input_context_sha256": _stable_hash(request_payload),
        "output_sha256": _stable_hash(raw_response),
        "token_usage": usage,
        "cost_estimate": cost,
        "transport_metadata": result.metadata,
        "human_review_needed": True,
    }
    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "audit.json", persona.to_audit_payload())
    write_json(target_dir / "generation_notes.json", generation_notes)
    write_json(target_dir / "contract_report.json", {"status": "pass", "findings": []})
    write_json(target_dir / "quality_report.json", quality_report)
    write_json(target_dir / "duplicate_report.json", duplicate_report)
    if result.concept_outputs:
        write_json(target_dir / "concept_outputs.json", result.concept_outputs)
    for filename, content in rendered.items():
        (target_dir / filename).write_text(content, encoding="utf-8")
    log.emit(
        "generation.accepted",
        elapsed_seconds=generation_notes["elapsed_seconds"],
        token_usage=usage,
        estimated_cost=cost["estimated_cost"],
    )
    return target_dir


def validate_v5_persona_folder(folder: Path) -> dict[str, Any]:
    required = {
        "profile.json", "audit.json", "persona.md", "biography.md", "research_kernel.md", "persona.skill.md",
        "local_grounding.md", "sensitive_scenarios.md", "generation_notes.json", "generation.log.jsonl",
        "llm_transport.log",
        "generation_brief.json", "llm_request.json", "llm_response.json", "contract_report.json",
        "quality_report.json", "duplicate_report.json",
    }
    missing = sorted(name for name in required if not (folder / name).exists())
    warnings: list[str] = []
    if not missing:
        try:
            persona = load_persona(folder)
            if persona.skill_version != "v5":
                warnings.append("skill_version is not v5")
            notes = json.loads((folder / "generation_notes.json").read_text(encoding="utf-8"))
            if notes.get("generator_version") != GENERATOR_VERSION:
                warnings.append("generation_notes generator_version mismatch")
            if not notes.get("token_usage"):
                warnings.append("token usage is missing")
            if json.loads((folder / "contract_report.json").read_text(encoding="utf-8")).get("status") != "pass":
                warnings.append("contract report did not pass")
            brief = json.loads((folder / "generation_brief.json").read_text(encoding="utf-8"))
            if _contract_concept_output_fields(brief) and not (folder / "concept_outputs.json").exists():
                warnings.append("concept outputs are missing")
        except Exception as exc:
            warnings.append(f"runtime artifact validation failed: {exc}")
    return {"valid": not missing and not warnings, "missing_fields": missing, "warnings": warnings}
