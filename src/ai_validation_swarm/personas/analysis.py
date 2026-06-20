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


def _distribution(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _distinct_count(distribution: dict[str, int]) -> int:
    return len(distribution)


def build_persona_library_summary(personas: list[PersonaSkill]) -> dict[str, object]:
    locale_packs = sorted(
        {
            locale_pack
            for options in LOCATION_OPTIONS.values()
            for _location, _languages, locale_pack in options
        }
    )

    panel_role_distribution = _distribution([persona.seed.panel_role for persona in personas])
    gender_distribution = _distribution([persona.profile.basic_identity["gender"] for persona in personas])
    location_distribution = _distribution([persona.profile.basic_identity["location"] for persona in personas])
    locale_pack_distribution = _distribution([persona.profile.basic_identity["locale_pack"] for persona in personas])
    life_stage_distribution = _distribution([persona.profile.basic_identity["life_stage"] for persona in personas])
    occupation_distribution = _distribution([persona.profile.basic_identity["occupation"] for persona in personas])
    family_structure_distribution = _distribution([persona.profile.basic_identity["family_structure"] for persona in personas])
    purchase_authority_distribution = _distribution(
        [persona.profile.economic_profile["purchase_authority_type"] for persona in personas]
    )
    workflow_maturity_distribution = _distribution(
        [persona.profile.behavior_profile["workflow_maturity"] for persona in personas]
    )
    cash_flow_distribution = _distribution(
        [persona.profile.economic_profile["cash_flow_volatility"] for persona in personas]
    )

    names = [persona.profile.basic_identity["name"] for persona in personas]
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
    }
