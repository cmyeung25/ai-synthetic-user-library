from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from ai_validation_swarm.domain.models import PanelSpec, PersonaSkill


@dataclass(slots=True)
class SamplingResult:
    personas: list[PersonaSkill]
    rationale: str
    explainability: dict[str, object]


def _value_for_filter(persona: PersonaSkill, filter_key: str) -> object:
    identity = persona.profile.basic_identity
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile

    mapping = {
        "panel_role": persona.seed.panel_role,
        "location": identity["location"],
        "location_type": persona.seed.location_type,
        "occupation": identity["occupation"],
        "occupation_band": persona.seed.occupation_band,
        "income_level": identity["income_level"],
        "income_band": persona.seed.income_band,
        "education_level": identity["education_level"],
        "age_band": persona.seed.age_band,
        "age": identity["age"],
        "language": identity["language"],
        "gender": identity["gender"],
        "tech_savviness": technology["tech_savviness"],
        "ai_familiarity": technology["ai_familiarity"],
        "privacy_concern": technology["privacy_concern"],
        "price_sensitivity": economic["price_sensitivity"],
        "subscription_tolerance": economic["subscription_tolerance"],
        "family_structure": identity["family_structure"],
    }
    if filter_key not in mapping:
        raise ValueError(f"Unsupported sampling filter '{filter_key}'.")
    return mapping[filter_key]


def _matches_filter(actual_value: object, expected_value: object) -> bool:
    if isinstance(actual_value, list):
        if isinstance(expected_value, list):
            return set(expected_value).issubset(set(actual_value))
        return str(expected_value) in {str(item) for item in actual_value}

    if isinstance(expected_value, list):
        return str(actual_value) in {str(item) for item in expected_value}

    return str(actual_value) == str(expected_value)


def _apply_filters(personas: list[PersonaSkill], filters: dict[str, object]) -> tuple[list[PersonaSkill], dict[str, int]]:
    filtered = personas
    stage_counts: dict[str, int] = {"before_filters": len(personas)}
    for filter_key, expected_value in filters.items():
        filtered = [
            persona
            for persona in filtered
            if _matches_filter(_value_for_filter(persona, filter_key), expected_value)
        ]
        stage_counts[f"after_{filter_key}"] = len(filtered)
    return filtered, stage_counts


def _build_explainability(
    panel_spec: PanelSpec,
    chosen: list[PersonaSkill],
    eligible_before_filters: int,
    eligible_after_filters: int,
    filter_stage_counts: dict[str, int],
) -> dict[str, object]:
    occupation_counts = Counter(persona.profile.basic_identity["occupation"] for persona in chosen)
    location_counts = Counter(persona.profile.basic_identity["location"] for persona in chosen)
    gender_counts = Counter(persona.profile.basic_identity["gender"] for persona in chosen)

    return {
        "panel_type": panel_spec.panel_type,
        "preset_name": panel_spec.preset_name or panel_spec.panel_type,
        "requested_sample_size": panel_spec.sample_size,
        "actual_sample_size": len(chosen),
        "random_seed": panel_spec.random_seed,
        "filters": panel_spec.filters,
        "eligible_before_filters": eligible_before_filters,
        "eligible_after_filters": eligible_after_filters,
        "filter_stage_counts": filter_stage_counts,
        "top_occupations": occupation_counts.most_common(5),
        "top_locations": location_counts.most_common(5),
        "gender_mix": dict(gender_counts),
        "selected_persona_ids": [persona.profile.synthetic_user_id for persona in chosen],
    }


def _build_rationale(explainability: dict[str, object]) -> str:
    occupations = explainability["top_occupations"]
    filters = explainability["filters"]
    occupation_text = ", ".join(f"{name} ({count})" for name, count in occupations) if occupations else "none"
    filter_text = (
        ", ".join(f"{key}={value}" for key, value in filters.items())
        if filters
        else "no extra filters"
    )
    return (
        f"Sampled {explainability['actual_sample_size']} personas from panel '{explainability['panel_type']}' "
        f"using preset '{explainability['preset_name']}'. Eligible candidates moved from "
        f"{explainability['eligible_before_filters']} to {explainability['eligible_after_filters']} after filters "
        f"({filter_text}). Most common occupations in the final sample: {occupation_text}."
    )


def sample_personas(personas: list[PersonaSkill], panel_spec: PanelSpec) -> SamplingResult:
    eligible = [persona for persona in personas if persona.seed.panel_role == panel_spec.panel_type]
    if not eligible:
        raise ValueError(f"No personas available for panel type: {panel_spec.panel_type}")

    eligible_before_filters = len(eligible)
    filtered, filter_stage_counts = _apply_filters(eligible, panel_spec.filters)
    if not filtered:
        raise ValueError(
            f"No personas available for panel '{panel_spec.panel_type}' after applying filters: {panel_spec.filters}"
        )

    sample_size = min(panel_spec.sample_size, len(eligible))
    rng = random.Random(panel_spec.random_seed)
    chosen = rng.sample(filtered, min(panel_spec.sample_size, len(filtered)))

    explainability = _build_explainability(
        panel_spec=panel_spec,
        chosen=chosen,
        eligible_before_filters=eligible_before_filters,
        eligible_after_filters=len(filtered),
        filter_stage_counts=filter_stage_counts,
    )
    rationale = _build_rationale(explainability)
    return SamplingResult(personas=chosen, rationale=rationale, explainability=explainability)
