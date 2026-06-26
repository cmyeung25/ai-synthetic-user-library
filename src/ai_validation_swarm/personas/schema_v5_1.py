from __future__ import annotations

import copy
from typing import Any


PERSONA_SCHEMA_VERSION = "v5.1"
LEGACY_V5_SCHEMA_VERSION = "v5"

V5_1_OPTIONAL_PROFILE_FIELDS: dict[str, tuple[str, ...]] = {
    "persona_schema_meta": (
        "schema_version",
        "source_version",
        "upgrade_strategy",
        "optional_blocks_present",
        "canonicalizations_applied",
    ),
    "relational_defense_model": (
        "self_other_position",
        "default_trust_posture",
        "defensive_style",
        "status_sensitivity",
        "attribution_style",
        "conflict_pattern",
        "withdrawal_pattern",
    ),
    "communication_behavior_model": (
        "baseline_answer_length",
        "clarification_tendency",
        "misunderstanding_risk",
        "topic_drift_tendency",
        "memory_lapse_tendency",
        "revision_tendency",
        "disinterest_expression_style",
        "permission_sensitivity",
        "pricing_confusion_risk",
        "dropoff_style",
    ),
}

V5_1_OPTIONAL_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "behavior_generation_rules": ("when", "then", "because", "source"),
}

V5_TO_V5_1_FALLBACK_MAPPING: dict[str, dict[str, Any]] = {
    "persona_schema_meta": {
        "mapping_type": "metadata",
        "target_fields": {
            "schema_version": PERSONA_SCHEMA_VERSION,
            "source_version": LEGACY_V5_SCHEMA_VERSION,
            "upgrade_strategy": "fallback_from_v5",
            "optional_blocks_present": "derived_after_upgrade",
            "canonicalizations_applied": "applied_upgrade_steps",
        },
    },
    "relational_defense_model": {
        "mapping_type": "derived_optional_block",
        "derived_from": [
            "human_difference_axes",
            "technology_profile.privacy_concern",
            "values.fears",
            "emotional_regulation_style",
        ],
        "policy": "If a legacy v5 artifact does not already contain this block, derive it from adjacent trust, control, risk, and regulation context.",
    },
    "communication_behavior_model": {
        "mapping_type": "derived_optional_block",
        "derived_from": [
            "human_difference_axes",
            "product_reaction_rules.questions_they_would_ask",
            "objection_language_style.polite_objection_examples",
        ],
        "policy": "If a legacy v5 artifact does not already contain this block, derive it from complexity tolerance, explanation need, and objection style.",
    },
    "behavior_generation_rules": {
        "mapping_type": "derived_optional_block",
        "derived_from": [
            "human_difference_axes",
            "relational_defense_model",
            "communication_behavior_model",
        ],
        "policy": "If a legacy v5 artifact does not already contain this block, derive explicit transcript-behavior rules from the persona's axes and behavior models.",
    },
}


def canonicalize_v5_1_profile_payload(
    profile_payload: dict[str, Any],
    *,
    source_version: str = PERSONA_SCHEMA_VERSION,
    force_meta: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    upgraded = copy.deepcopy(profile_payload)
    applied: list[str] = []
    axes = upgraded.get("human_difference_axes", {})
    if not isinstance(axes, dict):
        axes = {}
        upgraded["human_difference_axes"] = axes

    relational = upgraded.get("relational_defense_model")
    if not isinstance(relational, dict) or not relational:
        relational = _derive_relational_defense_model(
            axes=axes,
            technology_profile=upgraded.get("technology_profile", {}),
            values=upgraded.get("values", {}),
            emotional_regulation_style=upgraded.get("emotional_regulation_style", {}),
        )
        upgraded["relational_defense_model"] = relational
        applied.append("relational_defense_model<-derived_defaults")

    communication = upgraded.get("communication_behavior_model")
    if not isinstance(communication, dict) or not communication:
        communication = _derive_communication_behavior_model(
            axes=axes,
            product_reaction_rules=upgraded.get("product_reaction_rules", {}),
            objection_language_style=upgraded.get("objection_language_style", {}),
        )
        upgraded["communication_behavior_model"] = communication
        applied.append("communication_behavior_model<-derived_defaults")

    rules = upgraded.get("behavior_generation_rules")
    if not isinstance(rules, list) or not rules:
        rules = _derive_behavior_generation_rules(axes=axes, relational=relational, communication=communication)
        upgraded["behavior_generation_rules"] = rules
        applied.append("behavior_generation_rules<-derived_defaults")

    meta = upgraded.get("persona_schema_meta")
    if force_meta or not isinstance(meta, dict) or not meta:
        upgraded["persona_schema_meta"] = _schema_meta(
            source_version=source_version,
            optional_blocks_present=_present_optional_blocks(upgraded),
            canonicalizations_applied=applied,
        )
    else:
        meta = dict(meta)
        meta.setdefault("schema_version", PERSONA_SCHEMA_VERSION)
        meta.setdefault("source_version", source_version)
        meta.setdefault("upgrade_strategy", _upgrade_strategy(source_version))
        meta.setdefault("optional_blocks_present", _present_optional_blocks(upgraded))
        meta.setdefault("canonicalizations_applied", applied)
        upgraded["persona_schema_meta"] = meta
    return upgraded, applied


def schema_v5_1_definition() -> dict[str, Any]:
    return {
        "schema_version": PERSONA_SCHEMA_VERSION,
        "backward_compatible_with": [LEGACY_V5_SCHEMA_VERSION],
        "optional_profile_fields": {
            **{key: list(value) for key, value in V5_1_OPTIONAL_PROFILE_FIELDS.items()},
            **{key: list(value) for key, value in V5_1_OPTIONAL_LIST_FIELDS.items()},
        },
        "fallback_mapping": copy.deepcopy(V5_TO_V5_1_FALLBACK_MAPPING),
        "semantics": {
            "human_difference_axes": "Stable person-level difference axes that shape decisions and tolerance thresholds.",
            "relational_defense_model": "Stable self-other and trust-protection posture. Not a runtime friction switch.",
            "communication_behavior_model": "Baseline conversational tendencies that can surface during interviews.",
            "behavior_generation_rules": "Explicit mappings from person-level traits into expected transcript behavior.",
            "friction_mode": "Runtime interview setting, not persona truth.",
        },
    }


def _derive_relational_defense_model(
    *,
    axes: dict[str, Any],
    technology_profile: Any,
    values: Any,
    emotional_regulation_style: Any,
) -> dict[str, str]:
    trust_style = _axis_value(axes, "trust_style")
    control_preference = _axis_value(axes, "control_preference")
    risk_orientation = _axis_value(axes, "risk_orientation")
    privacy = _lookup(technology_profile, "privacy_concern")
    fears = " ".join(_strings(values.get("fears") if isinstance(values, dict) else values))
    regulation = _lookup(emotional_regulation_style, "summary") or _lookup(emotional_regulation_style, "conflict_recovery_style")
    if _matches_any(trust_style, "guard", "verify", "proof", "skeptic", "cautious"):
        self_other_position = "self_protective_other_guarded"
        trust_posture = "guarded_until_proven_safe"
        defensive_style = "question_then_withhold"
    elif _matches_any(trust_style, "institution", "benefit", "collaborative", "open"):
        self_other_position = "secure_collaborative"
        trust_posture = "conditionally_open_then_verify"
        defensive_style = "seek_clarity_before_pushback"
    else:
        self_other_position = "contextual_cautious"
        trust_posture = "evaluate_case_by_case"
        defensive_style = "hold_back_until_use_case_is_clear"
    status_sensitivity = "medium_high" if _matches_any(control_preference, "high", "strong") or "embarrass" in fears else "medium"
    attribution_style = (
        "assumes_optimistic_claims_hide_cost"
        if _matches_any(trust_style, "verify", "skeptic", "proof", "guard") or _matches_any(privacy, "high", "cautious")
        else "gives_claims_a_short_trial_before_judging"
    )
    conflict_pattern = (
        "polite_pushback_then_detach"
        if _matches_any(risk_orientation, "conservative", "measured", "cautious") or _matches_any(regulation, "cooling", "distance")
        else "clarifies_then_decides"
    )
    withdrawal_pattern = (
        "shorter_answers_when_not_convinced"
        if _matches_any(control_preference, "high", "strong") or _matches_any(trust_style, "guard", "verify")
        else "asks_for_one_more_example_before_disengaging"
    )
    return {
        "self_other_position": self_other_position,
        "default_trust_posture": trust_posture,
        "defensive_style": defensive_style,
        "status_sensitivity": status_sensitivity,
        "attribution_style": attribution_style,
        "conflict_pattern": conflict_pattern,
        "withdrawal_pattern": withdrawal_pattern,
    }


def _derive_communication_behavior_model(
    *,
    axes: dict[str, Any],
    product_reaction_rules: Any,
    objection_language_style: Any,
) -> dict[str, str]:
    life_load = _axis_value(axes, "life_load")
    complexity = _axis_value(axes, "complexity_tolerance")
    guidance = _axis_value(axes, "guidance_preference")
    control = _axis_value(axes, "control_preference")
    tempo = _axis_value(axes, "decision_tempo")
    fragmentation = _axis_value(axes, "fragmentation_reality")
    need_explanation = _axis_value(axes, "need_for_explanation")
    question_style = _lookup(product_reaction_rules, "questions_they_would_ask")
    objection_style = _lookup(objection_language_style, "polite_objection_examples")
    return {
        "baseline_answer_length": (
            "short_to_medium"
            if _matches_any(life_load, "high", "busy", "heavy", "stretched")
            else "medium_with_concrete_examples"
        ),
        "clarification_tendency": (
            "high_when_abstract"
            if _matches_any(complexity, "low", "limited") or _matches_any(guidance, "example", "guided")
            else "moderate_when_terms_are_unclear"
        ),
        "misunderstanding_risk": (
            "high_when_concept_dense"
            if _matches_any(complexity, "low", "limited")
            else "moderate_when_jargon_or_permissions_are_implicit"
        ),
        "topic_drift_tendency": (
            "medium_via_life_examples"
            if _matches_any(guidance, "example", "guided") or question_style
            else "low"
        ),
        "memory_lapse_tendency": (
            "medium"
            if _matches_any(life_load, "high", "busy") or _matches_any(fragmentation, "high", "fragmented")
            else "low"
        ),
        "revision_tendency": (
            "medium"
            if _matches_any(tempo, "slow", "deliberate", "careful")
            else "low_to_medium"
        ),
        "disinterest_expression_style": (
            "polite_but_direct"
            if objection_style or _matches_any(control, "high", "strong")
            else "quiet_fade_or_short_pushback"
        ),
        "permission_sensitivity": (
            "high"
            if _matches_any(control, "high", "strong") or _matches_any(fragmentation, "high", "fragmented")
            else "medium"
        ),
        "pricing_confusion_risk": (
            "medium"
            if _matches_any(need_explanation, "high") or _matches_any(complexity, "low", "limited")
            else "low_to_medium"
        ),
        "dropoff_style": (
            "says_probably_wont_bother_without_a_fast_first_win"
            if _matches_any(life_load, "high", "busy") or _matches_any(tempo, "slow", "deliberate")
            else "asks_for_a_smaller_test_before_deciding"
        ),
    }


def _derive_behavior_generation_rules(
    *,
    axes: dict[str, Any],
    relational: dict[str, Any],
    communication: dict[str, Any],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    if _matches_any(_axis_value(axes, "life_load"), "high", "busy", "heavy", "stretched"):
        rules.append({
            "when": {"human_difference_axes.life_load": "high"},
            "then": [
                "increase_short_answer_probability",
                "lower_patience_for_long_setup",
                "increase_dropoff_after_no_fast_first_win",
            ],
            "because": "High life load reduces patience and available activation bandwidth.",
            "source": "human_difference_axes",
        })
    if _matches_any(_axis_value(axes, "complexity_tolerance"), "low", "limited"):
        rules.append({
            "when": {"human_difference_axes.complexity_tolerance": "low"},
            "then": [
                "increase_clarification_requests",
                "increase_misunderstanding_of_dense_concepts",
                "prefer_examples_over_abstraction",
            ],
            "because": "Lower complexity tolerance raises comprehension friction for dense pitches.",
            "source": "human_difference_axes",
        })
    if str(relational.get("default_trust_posture", "")).startswith("guarded"):
        rules.append({
            "when": {"relational_defense_model.default_trust_posture": relational.get("default_trust_posture", "")},
            "then": [
                "probe_permissions_and_reversibility",
                "discount_unverified_benefit_claims",
                "shorten_answers_when_not_convinced",
            ],
            "because": "Guarded trust posture makes proof and reversibility central.",
            "source": "relational_defense_model",
        })
    if str(communication.get("permission_sensitivity", "")) == "high":
        rules.append({
            "when": {"communication_behavior_model.permission_sensitivity": "high"},
            "then": [
                "raise_permission_or_setup_questions_early",
                "surface_review_and_undo_concerns",
            ],
            "because": "This persona wants control before relying on a new workflow.",
            "source": "communication_behavior_model",
        })
    if not rules:
        rules.append({
            "when": {
                "communication_behavior_model.baseline_answer_length": communication.get("baseline_answer_length", ""),
                "relational_defense_model.default_trust_posture": relational.get("default_trust_posture", ""),
            },
            "then": [
                "keep_response_length_within_baseline",
                "let_trust_posture_shape_how_quickly_benefit_claims_are_accepted",
            ],
            "because": "Even low-friction personas need an explicit baseline mapping from profile traits into transcript behavior.",
            "source": "persona_baseline",
        })
    return rules


def _schema_meta(
    *,
    source_version: str,
    optional_blocks_present: list[str],
    canonicalizations_applied: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": PERSONA_SCHEMA_VERSION,
        "source_version": source_version,
        "upgrade_strategy": _upgrade_strategy(source_version),
        "optional_blocks_present": optional_blocks_present,
        "canonicalizations_applied": canonicalizations_applied,
    }


def _present_optional_blocks(payload: dict[str, Any]) -> list[str]:
    present: list[str] = []
    for key in V5_1_OPTIONAL_PROFILE_FIELDS:
        value = payload.get(key)
        if isinstance(value, dict) and value:
            present.append(key)
        elif isinstance(value, list) and value:
            present.append(key)
    return present


def _axis_value(axes: dict[str, Any], key: str) -> str:
    value = axes.get(key, "")
    return value.casefold() if isinstance(value, str) else str(value).casefold()


def _lookup(payload: Any, key: str) -> str:
    if isinstance(payload, dict):
        value = payload.get(key, "")
        if isinstance(value, list):
            return " ".join(str(item) for item in value)
        return str(value)
    return ""


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _matches_any(value: str, *tokens: str) -> bool:
    return any(token in value for token in tokens)


def _upgrade_strategy(source_version: str) -> str:
    if source_version == PERSONA_SCHEMA_VERSION:
        return "native_v5_1"
    if source_version == LEGACY_V5_SCHEMA_VERSION:
        return "fallback_from_v5"
    return "non_compatible_legacy_source"


def upgrade_profile_payload_to_v5_1(
    profile_payload: dict[str, Any],
    *,
    source_version: str = LEGACY_V5_SCHEMA_VERSION,
    force_meta: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    upgraded, applied = canonicalize_v5_1_profile_payload(
        profile_payload,
        source_version=source_version,
        force_meta=force_meta,
    )
    if source_version == LEGACY_V5_SCHEMA_VERSION and applied:
        applied = [step.replace("<-derived_defaults", "<-v5_fallback_derivation") for step in applied]
        meta = dict(upgraded.get("persona_schema_meta", {}))
        meta["schema_version"] = PERSONA_SCHEMA_VERSION
        meta["source_version"] = source_version
        meta["upgrade_strategy"] = "fallback_from_v5"
        meta["optional_blocks_present"] = _present_optional_blocks(upgraded)
        meta["canonicalizations_applied"] = applied
        upgraded["persona_schema_meta"] = meta
    return upgraded, applied
