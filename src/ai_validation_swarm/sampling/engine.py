from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from ai_validation_swarm.domain.models import PanelSpec, PersonaSkill
from ai_validation_swarm.personas.analysis import REQUIRED_HUMAN_DIFFERENCE_AXES, _bucket_human_difference_axis


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
        "synthetic_user_id": persona.profile.synthetic_user_id,
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
    eligible: list[PersonaSkill],
    chosen: list[PersonaSkill],
    eligible_before_filters: int,
    eligible_after_filters: int,
    filter_stage_counts: dict[str, int],
) -> dict[str, object]:
    occupation_counts = Counter(persona.profile.basic_identity["occupation"] for persona in chosen)
    location_counts = Counter(persona.profile.basic_identity["location"] for persona in chosen)
    gender_counts = Counter(persona.profile.basic_identity["gender"] for persona in chosen)

    selected_axis_coverage = _build_axis_coverage(chosen)
    eligible_axis_coverage = _build_axis_coverage(eligible)

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
        "human_difference_axis_coverage": {
            "selected_panel": selected_axis_coverage,
            "eligible_pool_after_filters": eligible_axis_coverage,
        },
        "undercovered_axes": _build_undercovered_axes(
            selected_axis_coverage=selected_axis_coverage,
            eligible_axis_coverage=eligible_axis_coverage,
        ),
        "similarity_hotspots": _build_similarity_hotspots(selected_axis_coverage, selected_count=len(chosen)),
        "selection_rationale_by_persona": _build_selection_rationale(
            panel_spec=panel_spec,
            chosen=chosen,
            selected_axis_coverage=selected_axis_coverage,
        ),
    }


def _build_rationale(explainability: dict[str, object]) -> str:
    occupations = explainability["top_occupations"]
    filters = explainability["filters"]
    undercovered_axes = explainability.get("undercovered_axes", [])
    occupation_text = ", ".join(f"{name} ({count})" for name, count in occupations) if occupations else "none"
    filter_text = (
        ", ".join(f"{key}={value}" for key, value in filters.items())
        if filters
        else "no extra filters"
    )
    rationale = (
        f"Sampled {explainability['actual_sample_size']} personas from panel '{explainability['panel_type']}' "
        f"using preset '{explainability['preset_name']}'. Eligible candidates moved from "
        f"{explainability['eligible_before_filters']} to {explainability['eligible_after_filters']} after filters "
        f"({filter_text}). Most common occupations in the final sample: {occupation_text}."
    )
    if isinstance(undercovered_axes, list) and undercovered_axes:
        thin_axes = ", ".join(str(record.get("axis")) for record in undercovered_axes[:3])
        rationale += f" Human-difference coverage still looks thin on: {thin_axes}."
    return rationale


def _human_difference_axes(persona: PersonaSkill) -> dict[str, object]:
    axes = getattr(persona.profile, "human_difference_axes", {})
    return axes if isinstance(axes, dict) else {}


def _axis_raw_value(persona: PersonaSkill, axis_key: str) -> str:
    return str(_human_difference_axes(persona).get(axis_key) or "").strip()


def _axis_bucket_value(persona: PersonaSkill, axis_key: str) -> str:
    raw_value = _axis_raw_value(persona, axis_key)
    if not raw_value:
        return "missing"
    return _bucket_human_difference_axis(axis_key, raw_value)


def _bucketed_axes_for_persona(persona: PersonaSkill) -> dict[str, str]:
    bucketed: dict[str, str] = {}
    for axis_key in REQUIRED_HUMAN_DIFFERENCE_AXES:
        bucket = _axis_bucket_value(persona, axis_key)
        if bucket != "missing":
            bucketed[axis_key] = bucket
    return bucketed


def _build_axis_coverage(personas: list[PersonaSkill]) -> dict[str, object]:
    axis_coverage: dict[str, object] = {}
    personas_with_axes = 0

    for persona in personas:
        if _human_difference_axes(persona):
            personas_with_axes += 1

    for axis_key in REQUIRED_HUMAN_DIFFERENCE_AXES:
        bucket_distribution: Counter[str] = Counter()
        bucket_persona_ids: dict[str, list[str]] = defaultdict(list)
        bucket_examples: dict[str, list[str]] = defaultdict(list)
        missing_persona_ids: list[str] = []

        for persona in personas:
            persona_id = persona.profile.synthetic_user_id
            raw_value = _axis_raw_value(persona, axis_key)
            if not raw_value:
                missing_persona_ids.append(persona_id)
                continue
            bucket = _bucket_human_difference_axis(axis_key, raw_value)
            bucket_distribution[bucket] += 1
            bucket_persona_ids[bucket].append(persona_id)
            if raw_value not in bucket_examples[bucket] and len(bucket_examples[bucket]) < 3:
                bucket_examples[bucket].append(raw_value)

        axis_coverage[axis_key] = {
            "persona_count": sum(bucket_distribution.values()),
            "missing_persona_count": len(missing_persona_ids),
            "missing_persona_ids": missing_persona_ids,
            "bucket_distribution": dict(sorted(bucket_distribution.items())),
            "bucket_persona_ids": {bucket: ids for bucket, ids in sorted(bucket_persona_ids.items())},
            "bucket_examples": {bucket: values for bucket, values in sorted(bucket_examples.items())},
            "bucket_count": len(bucket_distribution),
        }

    return {
        "required_axes": list(REQUIRED_HUMAN_DIFFERENCE_AXES),
        "persona_with_axes_count": personas_with_axes,
        "axis_coverage": axis_coverage,
    }


def _build_undercovered_axes(
    *,
    selected_axis_coverage: dict[str, object],
    eligible_axis_coverage: dict[str, object],
) -> list[dict[str, object]]:
    selected_axes = selected_axis_coverage.get("axis_coverage", {})
    eligible_axes = eligible_axis_coverage.get("axis_coverage", {})
    undercovered: list[dict[str, object]] = []

    for axis_key in REQUIRED_HUMAN_DIFFERENCE_AXES:
        selected_summary = selected_axes.get(axis_key, {})
        eligible_summary = eligible_axes.get(axis_key, {})
        selected_distribution = selected_summary.get("bucket_distribution", {})
        eligible_distribution = eligible_summary.get("bucket_distribution", {})
        selected_buckets = set(selected_distribution)
        eligible_buckets = set(eligible_distribution)
        missing_buckets = sorted(bucket for bucket in eligible_buckets if bucket not in selected_buckets)

        coverage_status = "fully_reflected"
        note = ""
        if missing_buckets:
            coverage_status = "missing_eligible_patterns"
            note = "Selected panel does not cover every eligible human-difference bucket."
        elif eligible_buckets and len(selected_buckets) == 1 and len(eligible_buckets) > 1:
            coverage_status = "single_pattern_only"
            note = "Selected panel reflects only one eligible human-difference pattern."
        elif selected_summary.get("missing_persona_count", 0) and eligible_summary.get("persona_count", 0):
            coverage_status = "partial_presence"
            note = "Some selected personas are missing this human-difference axis."

        if coverage_status == "fully_reflected":
            continue

        undercovered.append(
            {
                "axis": axis_key,
                "coverage_status": coverage_status,
                "selected_bucket_count": len(selected_buckets),
                "eligible_bucket_count": len(eligible_buckets),
                "selected_bucket_distribution": selected_distribution,
                "eligible_bucket_distribution": eligible_distribution,
                "missing_buckets": missing_buckets,
                "selected_missing_persona_ids": selected_summary.get("missing_persona_ids", []),
                "note": note,
            }
        )

    return undercovered


def _build_similarity_hotspots(axis_coverage: dict[str, object], *, selected_count: int) -> list[dict[str, object]]:
    hotspots: list[dict[str, object]] = []
    for axis_key, axis_summary in axis_coverage.get("axis_coverage", {}).items():
        bucket_distribution = axis_summary.get("bucket_distribution", {})
        bucket_persona_ids = axis_summary.get("bucket_persona_ids", {})
        bucket_examples = axis_summary.get("bucket_examples", {})
        for bucket, count in bucket_distribution.items():
            if count < 2:
                continue
            coverage_share = round(count / selected_count, 4) if selected_count else 0.0
            if count < 3 and coverage_share < 0.5:
                continue
            hotspots.append(
                {
                    "axis": axis_key,
                    "bucket": bucket,
                    "persona_count": count,
                    "selected_share": coverage_share,
                    "persona_ids": bucket_persona_ids.get(bucket, []),
                    "example_values": bucket_examples.get(bucket, []),
                    "note": f"{count} selected personas cluster on {axis_key}={bucket}.",
                }
            )
    hotspots.sort(key=lambda item: (item["selected_share"], item["persona_count"], str(item["axis"])), reverse=True)
    return hotspots[:5]


def _selected_attribute_value(persona: PersonaSkill, attribute_key: str) -> str:
    if attribute_key == "occupation":
        return str(persona.profile.basic_identity.get("occupation", ""))
    if attribute_key == "location":
        return str(persona.profile.basic_identity.get("location", ""))
    if attribute_key == "life_stage":
        return str(persona.profile.basic_identity.get("life_stage") or persona.seed.life_stage)
    if attribute_key == "workflow_maturity":
        return str(persona.profile.behavior_profile.get("workflow_maturity") or persona.seed.workflow_maturity)
    return ""


def _build_selection_rationale(
    *,
    panel_spec: PanelSpec,
    chosen: list[PersonaSkill],
    selected_axis_coverage: dict[str, object],
) -> list[dict[str, object]]:
    attribute_keys = ("occupation", "location", "life_stage", "workflow_maturity")
    attribute_counts = {
        key: Counter(_selected_attribute_value(persona, key) for persona in chosen if _selected_attribute_value(persona, key))
        for key in attribute_keys
    }
    axis_coverage = selected_axis_coverage.get("axis_coverage", {})
    selection_rationale: list[dict[str, object]] = []

    for persona in chosen:
        persona_id = persona.profile.synthetic_user_id
        matched_filters = {
            filter_key: _value_for_filter(persona, filter_key)
            for filter_key in panel_spec.filters
        }
        axis_contributions: list[dict[str, object]] = []
        for axis_key, bucket in _bucketed_axes_for_persona(persona).items():
            bucket_persona_ids = axis_coverage.get(axis_key, {}).get("bucket_persona_ids", {})
            shared_ids = bucket_persona_ids.get(bucket, [])
            if len(shared_ids) == 1:
                contribution_type = "unique_bucket"
            elif len(shared_ids) <= max(2, len(chosen) // 2):
                contribution_type = "minority_bucket"
            else:
                continue
            axis_contributions.append(
                {
                    "axis": axis_key,
                    "bucket": bucket,
                    "contribution_type": contribution_type,
                }
            )

        distinctive_attributes: list[dict[str, str]] = []
        for attribute_key in attribute_keys:
            attribute_value = _selected_attribute_value(persona, attribute_key)
            if not attribute_value:
                continue
            if attribute_counts[attribute_key][attribute_value] == 1:
                distinctive_attributes.append(
                    {
                        "attribute": attribute_key,
                        "value": attribute_value,
                    }
                )
            if len(distinctive_attributes) >= 3:
                break

        if matched_filters:
            filter_bits = ", ".join(f"{key}={value}" for key, value in matched_filters.items())
            filter_prefix = f"Matched {filter_bits}"
        else:
            filter_prefix = f"Matched the {panel_spec.panel_type} panel requirements"
        contribution_bits = ", ".join(
            f"{record['axis']}={record['bucket']}" for record in axis_contributions[:3]
        )
        distinctive_bits = ", ".join(
            f"{record['attribute']}={record['value']}" for record in distinctive_attributes[:2]
        )
        if contribution_bits:
            inclusion_reason = f"{filter_prefix} and adds panel coverage for {contribution_bits}."
        elif distinctive_bits:
            inclusion_reason = f"{filter_prefix} and stays distinctive through {distinctive_bits}."
        else:
            inclusion_reason = f"{filter_prefix} and helps complete the selected panel sample."

        selection_rationale.append(
            {
                "synthetic_user_id": persona_id,
                "matched_filters": matched_filters,
                "axis_contributions": axis_contributions[:5],
                "distinctive_attributes": distinctive_attributes,
                "inclusion_reason": inclusion_reason,
            }
        )

    return selection_rationale


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
        eligible=filtered,
        chosen=chosen,
        eligible_before_filters=eligible_before_filters,
        eligible_after_filters=len(filtered),
        filter_stage_counts=filter_stage_counts,
    )
    rationale = _build_rationale(explainability)
    return SamplingResult(personas=chosen, rationale=rationale, explainability=explainability)
