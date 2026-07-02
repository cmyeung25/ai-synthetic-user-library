from __future__ import annotations

import copy
import random
from typing import Any

from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v3_1_2 import RAW_ENUM_TOKENS, upgrade_persona_to_v3_1_2
from ai_validation_swarm.personas.v5 import V5SynthesisRequest, V5SynthesisResult


def build_frontline_v5_generation_guide(
    *,
    panel_type: str,
    target_audience: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audience = target_audience if isinstance(target_audience, dict) else {}
    audience_summary = str(audience.get("summary") or "General product research participants").strip()
    return {
        "mode": "guided",
        "required_profile_sections": ["human_difference_axes"],
        "fixed": {
            "panel_type": panel_type,
            "research_use": "frontline_research_studio_participant",
        },
        "preferred": {
            "target_audience_summary": audience_summary,
            "persona_generation_rule": (
                "Create a reusable V5.1 synthetic participant from ordinary life context, human difference axes, "
                "decision behavior, trust thresholds, and adoption barriers. Do not pre-bake agreement with the study concept."
            ),
            "evidence_boundary": "Synthetic participant only; not recruited human market proof.",
        },
    }


def _childhood() -> dict[str, Any]:
    return {
        "family_structure_and_stability": "A mostly stable household with ordinary changes in adult availability.",
        "caregiver_dynamics": "Care was practical, with explanations offered more often as the child grew older.",
        "emotional_climate": "Warm but not highly expressive; repair usually followed a cooling-off period.",
        "money_environment": "Purchases were discussed through trade-offs, durability, and timing.",
        "authority_and_rules": "Rules gained trust when adults explained their purpose.",
        "ordinary_childhood_scenes": [
            {
                "age": 7,
                "setting": "home",
                "scene": "Compared two small purchases with a parent before choosing the more durable one.",
                "lesson_at_the_time": "Small choices add up over time.",
                "adult_echo": "Checks recurring effort and total cost before adopting a product.",
            },
            {
                "age": 10,
                "setting": "school",
                "scene": "Shared a computer for a group task where unclear turns caused frustration.",
                "lesson_at_the_time": "Shared systems need clear roles.",
                "adult_echo": "Notices ownership, permission, and handoff rules in new workflows.",
            },
            {
                "age": 14,
                "setting": "local shop",
                "scene": "Waited while an old device was repaired instead of replaced.",
                "lesson_at_the_time": "Support and reversibility can matter more than novelty.",
                "adult_echo": "Asks what happens when setup breaks or the first attempt fails.",
            },
        ],
        "adult_decision_links": [
            {
                "childhood_pattern": "budget comparison",
                "adult_value_or_assumption": "cost repeats",
                "product_judgment_effect": "checks ongoing cost and admin drag",
                "limits_of_inference": "still buys occasional novelty when stakes are low",
            },
            {
                "childhood_pattern": "shared device friction",
                "adult_value_or_assumption": "roles and recovery paths matter",
                "product_judgment_effect": "asks who owns the next step",
                "limits_of_inference": "can still enjoy self-serve tools",
            },
            {
                "childhood_pattern": "repair visit",
                "adult_value_or_assumption": "support quality signals reliability",
                "product_judgment_effect": "checks whether help is available after setup",
                "limits_of_inference": "does not reject new products automatically",
            },
            {
                "childhood_pattern": "explained rules",
                "adult_value_or_assumption": "purpose earns trust",
                "product_judgment_effect": "questions silent defaults",
                "limits_of_inference": "can act quickly when the risk is bounded",
            },
        ],
        "uncertainty_notes": "These are plausible influences for simulation, not deterministic causes.",
    }


def _remove_enum_tokens(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _remove_enum_tokens(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_remove_enum_tokens(item) for item in value]
    if isinstance(value, str):
        for token in RAW_ENUM_TOKENS:
            value = value.replace(token, token.replace("_", " "))
    return value


class FrontlineLocalV5SynthesisAdapter:
    """Local V5.1 adapter used when Studio needs deterministic reserve personas without a live transport."""

    def synthesize(self, request: V5SynthesisRequest) -> V5SynthesisResult:
        contract = request.contract()
        panel_type = str(request.guide.get("fixed", {}).get("panel_type") or "mainstream")
        seed = build_seed(
            index=max(1, request.random_seed % 10_000),
            rng=random.Random(request.random_seed),
            panel_role=panel_type,
        )
        persona = upgrade_persona_to_v3_1_2(
            enrich_seed(seed=seed, index=max(1, request.random_seed % 10_000), rng=random.Random(request.random_seed + 1)),
            random_seed=request.random_seed,
        )
        profile = _remove_enum_tokens(persona.profile.to_dict())
        identity = profile.setdefault("basic_identity", {})
        identity["synthetic_user_id"] = request.synthetic_user_id
        profile["childhood_environment"] = _childhood()
        profile.setdefault("canonical_biography", {})
        profile["canonical_biography"].setdefault(
            "product_research_implications",
            ["Concrete proof matters more than polished claims."],
        )
        profile["panel_role_profile"] = {
            "panel_role": panel_type,
            "research_function": "Reusable Frontline Research Studio synthetic participant",
            "source": "frontline_local_v5_1_generation",
        }
        if "human_difference_axes" in contract.get("profile_sections", []):
            profile["human_difference_axes"] = {
                "control_preference": "Hybrid; wants room to decide but appreciates clear defaults.",
                "trust_style": "Evidence-first with cautious benefit of the doubt for credible proof.",
                "complexity_tolerance": "Moderate; will engage when detail clearly helps the decision.",
                "decision_tempo": "Measured; gathers enough signal before acting.",
                "financial_attention_cadence": "Periodic with event-driven spikes when consequences rise.",
                "relationship_to_money": "Money is a practical buffer and progress marker.",
                "risk_orientation": "Open to measured risk when the downside is understandable.",
                "need_for_explanation": "High enough to want plain-language framing and concrete examples.",
                "life_load": "Moderate; daily life leaves limited room for unnecessary friction.",
                "fragmentation_reality": "Some information and decisions live across more than one place.",
                "guidance_preference": "Hybrid self-serve plus optional expert clarification.",
                "reflection_style": "Explains decisions through recent examples and trade-offs.",
            }
        profile["relational_defense_model"] = {
            "self_other_position": "self_protective_other_guarded",
            "default_trust_posture": "guarded_until_proven_safe",
            "defensive_style": "question_then_withhold",
            "status_sensitivity": "medium",
            "attribution_style": "assumes_optimistic_claims_hide_cost",
            "conflict_pattern": "polite_pushback_then_detach",
            "withdrawal_pattern": "shorter_answers_when_not_convinced",
        }
        profile["communication_behavior_model"] = {
            "baseline_answer_length": "short_to_medium",
            "clarification_tendency": "high_when_abstract",
            "misunderstanding_risk": "high_when_concept_dense",
            "topic_drift_tendency": "medium_via_life_examples",
            "memory_lapse_tendency": "medium",
            "revision_tendency": "medium",
            "disinterest_expression_style": "polite_but_direct",
            "permission_sensitivity": "high",
            "pricing_confusion_risk": "medium",
            "dropoff_style": "says_probably_wont_bother_without_a_fast_first_win",
        }
        for category, block in profile.get("cross_domain_product_reaction_model", {}).items():
            if isinstance(block, dict):
                block.setdefault("reaction_basis", "Ordinary buying and tool-use experience shapes this response.")
                block.setdefault("first_question", "What would this change in an ordinary week?")
                block.setdefault("positive_trigger", "A concrete and reversible proof of value.")
                block.setdefault("negative_trigger", "A claim that hides the ongoing effort.")
                block.setdefault("trust_requirement", "Clear limits and evidence.")
                block.setdefault("likely_objection", "The benefit may not survive normal use.")
                block.setdefault("persona_specific_example", f"They would test {category.replace('_', ' ')} in one bounded situation.")
        for field_name in ("audit_evidence_layer", "generation_status", "extensions", "consistency_exceptions"):
            profile.pop(field_name, None)

        return V5SynthesisResult(
            profile=profile,
            decision_policy=copy.deepcopy(persona.decision_policy),
            response_style=copy.deepcopy(persona.response_style),
            narrative=persona.narrative,
            generation_rationale="Local Frontline V5.1 reserve persona generation.",
            quality_self_review={
                "strengths": ["Reusable life context", "Explicit human-difference axes", "Decision behavior preserved"],
                "weaknesses": ["Local deterministic generation still needs human calibration review"],
                "uncertainties": ["Some local texture is inferred"],
                "human_review_priorities": ["Review realism before using as replacement-grade evidence"],
            },
            concept_outputs={},
            provider="local_frontline_v5_generator",
            model="persona-generator/v5.1-local",
            metadata={
                "transport": "local_deterministic",
                "generator_path": "frontline_local_v5_1",
                "transport_metadata": {
                    "usage": {
                        "input_tokens_estimated": 1000,
                        "output_tokens_estimated": 2000,
                        "total_tokens_estimated": 3000,
                        "source": "local_frontline_v5_generator_estimate",
                    }
                },
            },
        )
