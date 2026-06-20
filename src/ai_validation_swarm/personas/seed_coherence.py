from __future__ import annotations

import random

OCCUPATION_TITLES = {
    "operations": "operations manager",
    "client_service": "account manager",
    "small_business": "small business owner",
    "finance": "finance manager",
    "procurement": "procurement lead",
    "health_admin": "clinic operations coordinator",
    "education_ops": "program coordinator",
    "community": "community program lead",
    "communications": "communications manager",
    "retail": "retail supervisor",
    "logistics": "logistics coordinator",
    "founder": "startup founder",
    "consulting": "independent consultant",
    "program_management": "program manager",
    "compliance_ops": "compliance operations lead",
    "customer_success": "customer success manager",
    "field_service": "field service coordinator",
}

LIFE_STAGE_OPTIONS = [
    "student_operator",
    "early_adult_small_business_builder",
    "young_operator_founder",
    "early_career_specialist",
    "emerging_manager",
    "young_family_builder",
    "mid_career_operator",
    "client_relationship_manager",
    "regional_business_builder",
    "senior_operator",
    "mature_operator",
    "retention_skeptic",
    "late_career_specialist",
]

PURCHASE_AUTHORITY_TYPES = [
    "personal_decider",
    "low_budget_self_decider",
    "solo_decider",
    "project_based_buyer",
    "client_constrained_decider",
    "owner_decider",
    "owner_with_business_partner_input",
    "owner_with_family_consultation",
    "owner_with_staff_input",
    "manager_approval_needed",
    "team_budget_influencer",
    "department_budget_requester",
    "department_budget_recommender",
    "client_service_recommender",
    "workflow_tool_evaluator",
    "shared_household_decider",
]

REQUIRED_LIFE_STAGE_COVERAGE = {
    "early_adult_small_business_builder",
    "early_career_specialist",
    "mid_career_operator",
    "senior_operator",
    "mature_operator",
}

REQUIRED_PURCHASE_AUTHORITY_COVERAGE = {
    "owner_decider",
    "owner_with_family_consultation",
    "manager_approval_needed",
    "team_budget_influencer",
    "department_budget_recommender",
}


def _pick(rng: random.Random, options: list[str], *, legacy_roll_size: int | None = None) -> str:
    if legacy_roll_size is not None and legacy_roll_size > 0:
        return options[rng.randrange(legacy_roll_size) % len(options)]
    return options[rng.randrange(len(options))]


def occupation_title_for_band(occupation_band: str) -> str:
    return OCCUPATION_TITLES[occupation_band]


def life_stage_candidates(
    *,
    age_band: str,
    occupation_band: str,
    household_structure: str,
    panel_role: str,
) -> list[str]:
    if age_band == "18-24":
        if occupation_band in {"small_business", "founder", "consulting"}:
            return ["young_operator_founder"]
        if "child" in household_structure:
            return ["young_family_builder"]
        return ["student_operator", "early_career_specialist"]

    if age_band == "25-34":
        if occupation_band == "founder":
            return ["young_operator_founder"]
        if occupation_band == "small_business":
            return ["early_adult_small_business_builder"]
        if "child" in household_structure:
            return ["young_family_builder", "emerging_manager"]
        if occupation_band in {"program_management", "community", "customer_success", "communications"}:
            return ["emerging_manager", "early_career_specialist"]
        return ["early_career_specialist", "emerging_manager"]

    if age_band == "35-44":
        if occupation_band in {"founder", "small_business", "consulting"}:
            return ["regional_business_builder", "mid_career_operator"]
        if occupation_band == "client_service":
            return ["client_relationship_manager", "mid_career_operator"]
        return ["mid_career_operator", "client_relationship_manager" if occupation_band == "customer_success" else "mid_career_operator"]

    if age_band == "45-54":
        if occupation_band in {"founder", "small_business", "consulting"}:
            return ["regional_business_builder", "senior_operator"]
        if occupation_band in {"client_service", "customer_success"}:
            return ["client_relationship_manager", "senior_operator"]
        return ["senior_operator", "mid_career_operator"]

    if age_band == "55-64":
        if panel_role == "skeptic" and occupation_band in {"operations", "procurement", "finance", "compliance_ops"}:
            return ["retention_skeptic", "mature_operator"]
        if occupation_band in {"operations", "procurement", "finance", "compliance_ops", "program_management"}:
            return ["mature_operator", "late_career_specialist"]
        return ["late_career_specialist", "mature_operator"]

    return ["mid_career_operator"]


def choose_life_stage(
    *,
    rng: random.Random,
    age_band: str,
    occupation_band: str,
    household_structure: str,
    panel_role: str,
    legacy_roll_size: int | None = None,
) -> str:
    candidates = life_stage_candidates(
        age_band=age_band,
        occupation_band=occupation_band,
        household_structure=household_structure,
        panel_role=panel_role,
    )
    return _pick(rng, candidates, legacy_roll_size=legacy_roll_size)


def purchase_authority_candidates(
    *,
    age_band: str,
    occupation_band: str,
    household_structure: str,
    panel_role: str,
) -> list[str]:
    shared_household = household_structure in {
        "living with partner",
        "living with partner and one child",
        "single parent with one child",
        "multi-generational household",
    }
    family_consult = household_structure in {
        "living with parents",
        "living with partner",
        "living with partner and one child",
        "single parent with one child",
        "multi-generational household",
    }

    if age_band == "18-24" and occupation_band not in {"small_business", "founder", "consulting"}:
        return ["low_budget_self_decider", "personal_decider"]

    if occupation_band == "small_business":
        if family_consult:
            return ["owner_with_family_consultation", "owner_decider"]
        return ["owner_decider", "owner_with_staff_input"]

    if occupation_band == "founder":
        if family_consult:
            return ["owner_with_family_consultation", "owner_with_business_partner_input", "owner_decider"]
        return ["owner_with_business_partner_input", "owner_decider"]

    if occupation_band == "consulting":
        if shared_household and panel_role in {"budget_constrained", "mainstream"}:
            return ["shared_household_decider", "solo_decider", "project_based_buyer"]
        return ["solo_decider", "project_based_buyer", "client_constrained_decider"]

    if occupation_band == "client_service":
        return ["manager_approval_needed", "client_service_recommender", "team_budget_influencer"]

    if occupation_band in {"operations", "logistics", "field_service"}:
        if age_band in {"45-54", "55-64"}:
            return ["department_budget_recommender", "workflow_tool_evaluator", "team_budget_influencer"]
        return ["manager_approval_needed", "team_budget_influencer", "workflow_tool_evaluator"]

    if occupation_band in {"finance", "procurement", "compliance_ops"}:
        if age_band in {"45-54", "55-64"}:
            return ["department_budget_recommender", "team_budget_influencer"]
        return ["manager_approval_needed", "department_budget_requester", "team_budget_influencer"]

    if occupation_band in {"program_management", "customer_success", "community", "communications", "education_ops", "health_admin"}:
        if shared_household and panel_role in {"budget_constrained", "mainstream", "inclusion"}:
            return ["shared_household_decider", "team_budget_influencer", "manager_approval_needed"]
        return ["team_budget_influencer", "manager_approval_needed", "department_budget_requester"]

    if occupation_band == "retail":
        if shared_household:
            return ["shared_household_decider", "manager_approval_needed", "personal_decider"]
        return ["manager_approval_needed", "personal_decider"]

    if shared_household:
        return ["shared_household_decider", "team_budget_influencer"]
    return ["manager_approval_needed", "team_budget_influencer"]


def choose_purchase_authority(
    *,
    rng: random.Random,
    age_band: str,
    occupation_band: str,
    household_structure: str,
    panel_role: str,
    legacy_roll_size: int | None = None,
) -> str:
    candidates = purchase_authority_candidates(
        age_band=age_band,
        occupation_band=occupation_band,
        household_structure=household_structure,
        panel_role=panel_role,
    )
    return _pick(rng, candidates, legacy_roll_size=legacy_roll_size)
