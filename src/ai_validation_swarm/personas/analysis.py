from __future__ import annotations

from collections import Counter

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.generator import (
    CASH_FLOW_VOLATILITY,
    HOUSEHOLDS,
    LIFE_STAGE_OPTIONS,
    LOCATION_OPTIONS,
    PANEL_ROLES,
    PURCHASE_AUTHORITY_TYPES,
    WORKFLOW_MATURITY,
)
from ai_validation_swarm.personas.seed_coherence import (
    REQUIRED_LIFE_STAGE_COVERAGE,
    REQUIRED_PURCHASE_AUTHORITY_COVERAGE,
)
from ai_validation_swarm.personas.validator import OPTIONAL_STRUCTURED_SECTIONS


REQUIRED_HUMAN_DIFFERENCE_AXES = OPTIONAL_STRUCTURED_SECTIONS["human_difference_axes"]


def _normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def _bucket_human_difference_axis(axis_key: str, raw_value: object) -> str:
    text = _normalize_text(raw_value)
    if not text:
        return "missing"

    if axis_key == "control_preference":
        if any(token in text for token in ("self-serve", "self serve", "autonomy", "independent", "own")):
            return "self_directed"
        if any(token in text for token in ("guided", "scaffold", "support", "step", "help")):
            return "guided"
        return "hybrid"

    if axis_key == "trust_style":
        if any(token in text for token in ("verify", "evidence", "proof", "guard", "cautious", "skeptic")):
            return "verify_first"
        if any(token in text for token in ("institution", "brand", "expert", "authority")):
            return "institution_led"
        if any(token in text for token in ("open", "benefit of the doubt", "collaborative")):
            return "conditionally_open"
        return "contextual"

    if axis_key == "complexity_tolerance":
        if any(token in text for token in ("low", "limited", "simple", "plain")):
            return "low"
        if any(token in text for token in ("high", "deep", "detailed", "complex")):
            return "high"
        return "moderate"

    if axis_key == "decision_tempo":
        if any(token in text for token in ("fast", "quick", "immediate", "rapid")):
            return "fast"
        if any(token in text for token in ("slow", "deliberate", "careful")):
            return "deliberate"
        return "measured"

    if axis_key == "financial_attention_cadence":
        if any(token in text for token in ("daily", "frequent", "constant")):
            return "frequent"
        if any(token in text for token in ("event", "spike", "periodic")):
            return "event_driven"
        return "occasional"

    if axis_key == "relationship_to_money":
        if any(token in text for token in ("security", "buffer", "stability", "safety")):
            return "security"
        if any(token in text for token in ("progress", "growth", "invest", "wealth")):
            return "growth"
        if any(token in text for token in ("constraint", "scarce", "stretch")):
            return "constraint"
        return "practical"

    if axis_key == "risk_orientation":
        if any(token in text for token in ("conservative", "cautious", "downside")):
            return "conservative"
        if any(token in text for token in ("open", "aggressive", "high conviction")):
            return "open"
        return "measured"

    if axis_key == "need_for_explanation":
        if any(token in text for token in ("high", "plain-language", "plain language", "translation", "explanation")):
            return "high"
        if any(token in text for token in ("low", "headline", "summary only", "minimal")):
            return "low"
        return "moderate"

    if axis_key == "life_load":
        if any(token in text for token in ("high", "busy", "heavy", "stretched")):
            return "high"
        if any(token in text for token in ("low", "light", "room")):
            return "low"
        return "moderate"

    if axis_key == "fragmentation_reality":
        if any(token in text for token in ("multiple", "fragmented", "across", "many", "more than one")):
            return "fragmented"
        if any(token in text for token in ("single", "centralized", "one place")):
            return "centralized"
        return "some_fragmentation"

    if axis_key == "guidance_preference":
        if any(token in text for token in ("self-serve", "self serve", "independent")):
            return "self_serve"
        if any(token in text for token in ("hybrid", "optional expert", "optional support")):
            return "hybrid"
        return "guided"

    if axis_key == "reflection_style":
        if any(token in text for token in ("example", "trade-off", "trade off")):
            return "example_tradeoff"
        if any(token in text for token in ("framework", "systematic", "structured")):
            return "systematic"
        if any(token in text for token in ("feeling", "intuition", "gut")):
            return "intuitive"
        return "contextual"

    return "contextual"


def _coverage_status(*, persona_count: int, missing_count: int, bucket_count: int) -> str:
    if persona_count == 0:
        return "missing_from_library"
    if missing_count:
        return "partial_presence"
    if bucket_count <= 1:
        return "single_pattern_only"
    return "covered"


def _human_difference_axis_summary(personas: list[PersonaSkill]) -> dict[str, object]:
    persona_count = len(personas)
    persona_ids = [persona.profile.synthetic_user_id for persona in personas]
    axis_coverage: dict[str, object] = {}
    coverage_gaps: list[dict[str, object]] = []

    personas_with_axes_count = 0
    for persona in personas:
        axes = getattr(persona.profile, "human_difference_axes", {})
        if isinstance(axes, dict) and axes:
            personas_with_axes_count += 1

    for axis_key in REQUIRED_HUMAN_DIFFERENCE_AXES:
        values: list[tuple[str, str]] = []
        missing_persona_ids: list[str] = []
        for persona, persona_id in zip(personas, persona_ids):
            axes = getattr(persona.profile, "human_difference_axes", {})
            raw_value = axes.get(axis_key) if isinstance(axes, dict) else None
            value = str(raw_value or "").strip()
            if value:
                values.append((persona_id, value))
            else:
                missing_persona_ids.append(persona_id)

        bucket_distribution = _distribution([_bucket_human_difference_axis(axis_key, value) for _persona_id, value in values])
        coverage_status = _coverage_status(
            persona_count=len(values),
            missing_count=len(missing_persona_ids),
            bucket_count=len(bucket_distribution),
        )
        axis_summary = {
            "persona_count": len(values),
            "missing_persona_count": len(missing_persona_ids),
            "missing_persona_ids": missing_persona_ids,
            "bucket_distribution": bucket_distribution,
            "bucket_count": len(bucket_distribution),
            "example_values": [value for _persona_id, value in values[:3]],
            "coverage_status": coverage_status,
        }
        axis_coverage[axis_key] = axis_summary

        if coverage_status != "covered":
            coverage_gaps.append(
                {
                    "axis": axis_key,
                    "gap_type": coverage_status,
                    "missing_persona_ids": missing_persona_ids,
                }
            )

    behavior_model_coverage = {}
    for field_name in (
        "relational_defense_model",
        "communication_behavior_model",
        "behavior_generation_rules",
    ):
        present_count = 0
        for persona in personas:
            value = getattr(persona.profile, field_name, {})
            if isinstance(value, list):
                if value:
                    present_count += 1
            elif isinstance(value, dict):
                if value:
                    present_count += 1
        behavior_model_coverage[field_name] = {
            "persona_count": present_count,
            "missing_persona_count": persona_count - present_count,
            "coverage_status": "covered" if persona_count and present_count == persona_count else "partial_presence" if present_count else "missing_from_library",
        }

    axes_with_any_coverage_count = sum(
        1 for summary in axis_coverage.values() if int(summary["persona_count"]) > 0
    )
    axes_with_full_presence_count = sum(
        1 for summary in axis_coverage.values() if int(summary["missing_persona_count"]) == 0 and int(summary["persona_count"]) > 0
    )
    axes_with_multi_pattern_count = sum(
        1 for summary in axis_coverage.values() if int(summary["bucket_count"]) > 1 and int(summary["missing_persona_count"]) == 0
    )

    return {
        "required_axes": list(REQUIRED_HUMAN_DIFFERENCE_AXES),
        "persona_with_axes_count": personas_with_axes_count,
        "axes_with_any_coverage_count": axes_with_any_coverage_count,
        "axes_with_full_presence_count": axes_with_full_presence_count,
        "axes_with_multi_pattern_count": axes_with_multi_pattern_count,
        "axis_coverage": axis_coverage,
        "behavior_model_coverage": behavior_model_coverage,
        "coverage_gaps": coverage_gaps,
    }


def _distribution(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _distinct_count(distribution: dict[str, int]) -> int:
    return len(distribution)


def _persona_field(
    persona: PersonaSkill,
    section_name: str,
    field_name: str,
    *,
    seed_field_name: str = "",
    default: str = "unknown",
) -> str:
    section = getattr(persona.profile, section_name, {})
    value = section.get(field_name) if isinstance(section, dict) else None
    if (value is None or value == "") and seed_field_name:
        value = getattr(persona.seed, seed_field_name, "")
    text = str(value or "").strip()
    return text or default


def build_persona_library_summary(personas: list[PersonaSkill]) -> dict[str, object]:
    locale_packs = sorted(
        {
            locale_pack
            for options in LOCATION_OPTIONS.values()
            for _location, _languages, locale_pack in options
        }
    )

    panel_role_distribution = _distribution([persona.seed.panel_role for persona in personas])
    gender_distribution = _distribution([
        _persona_field(persona, "basic_identity", "gender")
        for persona in personas
    ])
    location_distribution = _distribution([
        _persona_field(persona, "basic_identity", "location", seed_field_name="locale_pack")
        for persona in personas
    ])
    locale_pack_distribution = _distribution([
        _persona_field(persona, "basic_identity", "locale_pack", seed_field_name="locale_pack")
        for persona in personas
    ])
    life_stage_distribution = _distribution([
        _persona_field(persona, "basic_identity", "life_stage", seed_field_name="life_stage")
        for persona in personas
    ])
    occupation_distribution = _distribution([
        _persona_field(persona, "basic_identity", "occupation", seed_field_name="occupation_title")
        for persona in personas
    ])
    family_structure_distribution = _distribution([
        _persona_field(persona, "basic_identity", "family_structure", seed_field_name="household_structure")
        for persona in personas
    ])
    purchase_authority_distribution = _distribution(
        [
            _persona_field(persona, "economic_profile", "purchase_authority_type", seed_field_name="purchase_authority_type")
            for persona in personas
        ]
    )
    workflow_maturity_distribution = _distribution(
        [
            _persona_field(persona, "behavior_profile", "workflow_maturity", seed_field_name="workflow_maturity")
            for persona in personas
        ]
    )
    cash_flow_distribution = _distribution(
        [
            _persona_field(persona, "economic_profile", "cash_flow_volatility", seed_field_name="cash_flow_volatility")
            for persona in personas
        ]
    )

    names = [
        _persona_field(persona, "basic_identity", "name", default=persona.profile.synthetic_user_id)
        for persona in personas
    ]
    unique_names = len(set(names))

    coverage_checks = {
        "all_names_unique": unique_names == len(personas),
        "all_panel_roles_covered": set(panel_role_distribution) == set(PANEL_ROLES),
        "all_locale_packs_covered": set(locale_pack_distribution) == set(locale_packs),
        "all_life_stages_covered": REQUIRED_LIFE_STAGE_COVERAGE.issubset(set(life_stage_distribution)),
        "all_family_structures_covered": set(family_structure_distribution) == set(HOUSEHOLDS),
        "all_purchase_authority_types_covered": REQUIRED_PURCHASE_AUTHORITY_COVERAGE.issubset(
            set(purchase_authority_distribution)
        ),
        "all_workflow_maturity_types_covered": set(workflow_maturity_distribution) == set(WORKFLOW_MATURITY),
        "all_cash_flow_volatility_types_covered": set(cash_flow_distribution) == set(CASH_FLOW_VOLATILITY),
    }
    human_difference_axis_summary = _human_difference_axis_summary(personas)

    return {
        "library_size": len(personas),
        "unique_name_count": unique_names,
        "distinct_counts": {
            "panel_role": _distinct_count(panel_role_distribution),
            "gender": _distinct_count(gender_distribution),
            "location": _distinct_count(location_distribution),
            "locale_pack": _distinct_count(locale_pack_distribution),
            "life_stage": _distinct_count(life_stage_distribution),
            "occupation": _distinct_count(occupation_distribution),
            "family_structure": _distinct_count(family_structure_distribution),
            "purchase_authority_type": _distinct_count(purchase_authority_distribution),
            "workflow_maturity": _distinct_count(workflow_maturity_distribution),
            "cash_flow_volatility": _distinct_count(cash_flow_distribution),
        },
        "distributions": {
            "panel_role": panel_role_distribution,
            "gender": gender_distribution,
            "location": location_distribution,
            "locale_pack": locale_pack_distribution,
            "life_stage": life_stage_distribution,
            "occupation": occupation_distribution,
            "family_structure": family_structure_distribution,
            "purchase_authority_type": purchase_authority_distribution,
            "workflow_maturity": workflow_maturity_distribution,
            "cash_flow_volatility": cash_flow_distribution,
        },
        "coverage_checks": coverage_checks,
        "human_difference_axis_summary": human_difference_axis_summary,
    }
