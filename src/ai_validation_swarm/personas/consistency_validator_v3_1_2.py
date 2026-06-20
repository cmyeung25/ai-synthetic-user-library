from __future__ import annotations

from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill

AGE_LIFE_STAGE_MAP: list[tuple[range, set[str]]] = [
    (
        range(18, 25),
        {
            "student_operator",
            "early_career_specialist",
            "young_operator_founder",
        },
    ),
    (
        range(25, 35),
        {
            "early_adult_small_business_builder",
            "young_operator_founder",
            "early_career_specialist",
            "young_family_builder",
            "emerging_manager",
        },
    ),
    (
        range(35, 45),
        {
            "mid_career_operator",
            "client_relationship_manager",
            "regional_business_builder",
        },
    ),
    (
        range(45, 55),
        {
            "senior_operator",
            "regional_business_builder",
            "late_career_specialist",
        },
    ),
    (
        range(55, 65),
        {
            "mature_operator",
            "retention_skeptic",
            "late_career_specialist",
        },
    ),
]

EXPECTED_LOCAL_APPS: dict[str, set[str]] = {
    "taipei": {"line", "line pay", "px pay", "jkopay", "google search", "youtube"},
    "kuala lumpur": {"whatsapp", "grab", "touch n go", "touch 'n go", "maybank", "youtube", "linkedin"},
    "penang": {"whatsapp", "grab", "touch n go", "touch 'n go", "shopee", "youtube"},
    "hong kong": {"whatsapp", "payme", "octopus", "openrice", "youtube"},
}

EXPECTED_PANEL_ROLE_BY_ARCHETYPE = {
    "ambitious_signal_seeker": "status_sensitive_buyer",
    "privacy_narrow_trialist": "privacy_sensitive",
    "mature_operator_retention_skeptic": "skeptic",
    "early_career_practical_trial_user": "mainstream_buyer",
    "quiet_inclusion_checker": "identity_sensitive_user",
}


def _non_empty(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _normalize(value: Any) -> str:
    return _non_empty(value).lower()


def _joined_text(values: list[Any] | tuple[Any, ...]) -> str:
    return " ".join(_non_empty(value).lower() for value in values if _non_empty(value))


def default_identity_language(gender: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    current = current or {}
    normalized_gender = _normalize(gender)
    pronoun_preference = _non_empty(current.get("pronoun_preference"))
    if not pronoun_preference:
        if normalized_gender == "woman":
            pronoun_preference = "she/her"
        elif normalized_gender == "man":
            pronoun_preference = "he/him"
        else:
            pronoun_preference = "they/them"
    narration_style = _non_empty(current.get("narration_pronoun_style"))
    if not narration_style:
        narration_style = (
            "name-forward with they/them references"
            if pronoun_preference == "they/them"
            else "name-forward with aligned pronoun references"
        )
    disclosure = _non_empty(current.get("identity_disclosure_comfort"))
    if not disclosure:
        disclosure = "contextual and user-controlled"
    return {
        "gender_identity": _non_empty(current.get("gender_identity")) or normalized_gender or "not_disclosed",
        "pronoun_preference": pronoun_preference,
        "narration_pronoun_style": narration_style,
        "identity_disclosure_comfort": disclosure,
    }


def suggested_life_stage(persona: PersonaSkill) -> str:
    age = int(persona.profile.basic_identity.get("age", 0) or 0)
    occupation = _normalize(persona.profile.basic_identity.get("occupation"))
    family_structure = _normalize(persona.profile.basic_identity.get("family_structure"))
    if age < 25:
        if "owner" in occupation or "founder" in occupation:
            return "young_operator_founder"
        return "student_operator" if "student" in occupation else "early_career_specialist"
    if age < 35:
        if "owner" in occupation or "founder" in occupation:
            return "early_adult_small_business_builder"
        if "child" in family_structure:
            return "young_family_builder"
        if "manager" in occupation:
            return "emerging_manager"
        return "early_career_specialist"
    if age < 45:
        if "account" in occupation or "client" in occupation:
            return "client_relationship_manager"
        if "owner" in occupation or "consultant" in occupation:
            return "regional_business_builder"
        return "mid_career_operator"
    if age < 55:
        if "owner" in occupation or "founder" in occupation or "consultant" in occupation:
            return "regional_business_builder"
        return "senior_operator"
    if "operations manager" in occupation:
        return "mature_operator"
    return "late_career_specialist"


def suggested_purchase_authority(persona: PersonaSkill) -> str:
    occupation = _normalize(persona.profile.basic_identity.get("occupation"))
    family_structure = _normalize(persona.profile.basic_identity.get("family_structure"))
    if "small business owner" in occupation or "founder" in occupation:
        if "partner" in family_structure:
            return "owner_with_business_partner_input"
        if "parent" in family_structure or "multi-generational" in family_structure:
            return "owner_with_family_consultation"
        return "owner_decider"
    if "consultant" in occupation or "freelancer" in occupation:
        return "solo_decider"
    if "account manager" in occupation:
        return "manager_approval_needed"
    if "operations manager" in occupation:
        return "department_budget_recommender"
    if any(token in occupation for token in ("retail", "logistics", "field service")):
        return "manager_approval_needed"
    if any(token in occupation for token in ("program", "customer success", "community", "communications", "clinic")):
        return "team_budget_influencer"
    if any(token in occupation for token in ("finance", "procurement", "compliance")):
        return "department_budget_recommender"
    if "student" in occupation:
        return "personal_decider"
    return "team_budget_influencer"


def _allowed_life_stages(age: int) -> set[str]:
    for age_range, options in AGE_LIFE_STAGE_MAP:
        if age in age_range:
            return options
    return set()


def _allowed_authorities(occupation: str, family_structure: str) -> set[str]:
    if "small business owner" in occupation or "founder" in occupation:
        options = {"owner_decider", "solo_decider", "owner_with_business_partner_input", "owner_with_staff_input"}
        if "partner" in family_structure or "parent" in family_structure or "multi-generational" in family_structure:
            options.add("owner_with_family_consultation")
        return options
    if "account manager" in occupation:
        return {
            "manager_approval_needed",
            "team_budget_influencer",
            "department_budget_requester",
            "client_service_recommender",
        }
    if "operations manager" in occupation:
        return {
            "team_budget_influencer",
            "department_budget_recommender",
            "shared_household_decider",
            "workflow_tool_evaluator",
        }
    if any(token in occupation for token in ("finance", "procurement", "compliance")):
        return {
            "manager_approval_needed",
            "team_budget_influencer",
            "department_budget_requester",
            "department_budget_recommender",
        }
    if any(token in occupation for token in ("retail", "logistics", "field service")):
        return {
            "manager_approval_needed",
            "team_budget_influencer",
            "workflow_tool_evaluator",
            "shared_household_decider",
            "personal_decider",
        }
    if any(token in occupation for token in ("program", "customer success", "community", "communications", "clinic")):
        return {
            "manager_approval_needed",
            "team_budget_influencer",
            "department_budget_requester",
            "shared_household_decider",
        }
    if "student" in occupation:
        return {"personal_decider", "parent_funded_decider", "low_budget_self_decider"}
    if "consultant" in occupation or "freelancer" in occupation:
        return {"solo_decider", "client_constrained_decider", "project_based_buyer"}
    if "manager" in occupation or "lead" in occupation:
        return {"manager_approval_needed", "team_budget_influencer", "department_budget_recommender"}
    return {
        "solo_decider",
        "team_budget_influencer",
        "shared_household_decider",
        "manager_approval_needed",
        "personal_decider",
    }


def _has_daily_context(persona: PersonaSkill, required_terms: set[str]) -> bool:
    story = persona.profile.life_story
    daily = persona.profile.daily_micro_behaviours
    small_business_context = persona.profile.small_business_context
    combined = _joined_text(
        [
            story.get("current_daily_routine", ""),
            story.get("career_path", ""),
            daily.get("work_start_pattern", ""),
            daily.get("shopping_moments", ""),
            " ".join(str(item) for item in small_business_context.get("daily_business_tasks", [])),
        ]
    )
    return any(term in combined for term in required_terms)


def build_consistency_report_v3_1_2(
    persona: PersonaSkill,
    *,
    rendered_artifacts: dict[str, str] | None = None,
    auto_fixes_applied: list[str] | None = None,
) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    economic = persona.profile.economic_profile
    local_grounding = persona.profile.local_grounding_layer
    panel_role_profile = persona.profile.panel_role_profile
    gender = _normalize(identity.get("gender"))
    occupation = _normalize(identity.get("occupation"))
    family_structure = _normalize(identity.get("family_structure"))
    life_stage = _normalize(identity.get("life_stage"))
    authority = _normalize(economic.get("purchase_authority_type"))
    age = int(identity.get("age", 0) or 0)
    current_identity_language = persona.profile.identity_language or default_identity_language(gender)
    checks: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    hard_fail_reasons: list[str] = []
    applied = list(auto_fixes_applied or [])

    allowed_life_stages = _allowed_life_stages(age)
    age_life_issue = ""
    if allowed_life_stages and life_stage not in allowed_life_stages:
        age_life_issue = f"Age {age} does not fit life_stage '{identity.get('life_stage', '')}'."
        hard_fail_reasons.append("age_life_stage_conflict")
    checks["age_life_stage_consistency"] = {
        "status": "fail" if age_life_issue else "pass",
        "fields_checked": ["age", "life_stage"],
        "issue": age_life_issue,
        "suggested_fix": suggested_life_stage(persona) if age_life_issue else "",
    }

    allowed_authorities = _allowed_authorities(occupation, family_structure)
    authority_issue = ""
    if allowed_authorities and authority not in allowed_authorities:
        authority_issue = (
            f"Occupation '{identity.get('occupation', '')}' does not fit purchase_authority_type "
            f"'{economic.get('purchase_authority_type', '')}'."
        )
        hard_fail_reasons.append("occupation_purchase_authority_conflict")
    checks["occupation_authority_consistency"] = {
        "status": "fail" if authority_issue else "pass",
        "fields_checked": ["occupation", "purchase_authority_type"],
        "issue": authority_issue,
        "suggested_fix": suggested_purchase_authority(persona) if authority_issue else "",
    }

    required_daily_terms: set[str] = set()
    if "small business owner" in occupation:
        required_daily_terms = {
            "customer",
            "order",
            "content",
            "revenue",
            "inventory",
            "booking",
            "lead",
            "supplier",
            "quote",
            "cashflow",
        }
    elif "account manager" in occupation:
        required_daily_terms = {"client", "proposal", "renewal", "pipeline", "follow-up", "crm", "email", "whatsapp"}
    elif "operations manager" in occupation:
        required_daily_terms = {"handoff", "process", "schedule", "service", "dashboard", "exception", "follow-up"}
    daily_issue = ""
    if required_daily_terms and not _has_daily_context(persona, required_daily_terms):
        daily_issue = f"Daily context for '{identity.get('occupation', '')}' is missing expected work realities."
        if "small business owner" in occupation:
            hard_fail_reasons.append("small_business_daily_context_missing")
    checks["occupation_daily_routine_consistency"] = {
        "status": "fail" if "small business owner" in occupation and daily_issue else "warning" if daily_issue else "pass",
        "fields_checked": ["occupation", "current_daily_routine", "daily_micro_behaviours", "small_business_context"],
        "issue": daily_issue,
        "suggested_fix": "Rewrite the routine around real daily work loops for this occupation." if daily_issue else "",
    }
    if daily_issue and "small business owner" not in occupation:
        warnings.append(daily_issue)

    income_level = _normalize(identity.get("income_level"))
    price_sensitivity = _normalize(economic.get("price_sensitivity"))
    cash_volatility = _normalize(economic.get("cash_flow_volatility"))
    pricing_logic_text = _joined_text(
        [
            persona.profile.pricing_logic.get("what_makes_price_feel_fair", ""),
            persona.profile.pricing_logic.get("pricing_objection", ""),
            persona.profile.life_story.get("frustrations", []),
        ]
    )
    income_issue = ""
    if income_level == "middle" and price_sensitivity == "high":
        if cash_volatility != "high" and not any(token in pricing_logic_text for token in ("cash", "rent", "family", "reinvest", "volatility")):
            income_issue = "Middle income with high price sensitivity is not explained by cashflow, family, or reinvestment pressure."
            warnings.append(income_issue)
    if income_level == "upper_middle" and price_sensitivity == "high":
        if not any(token in pricing_logic_text for token in ("value", "scrutiny", "justify", "waste")):
            income_issue = "Upper-middle income with high price sensitivity needs value-scrutiny explanation."
            warnings.append(income_issue)
    checks["income_spending_consistency"] = {
        "status": "warning" if income_issue else "pass",
        "fields_checked": ["income_level", "price_sensitivity", "pricing_logic", "cash_flow_volatility"],
        "issue": income_issue,
        "suggested_fix": "Explain why price caution comes from cashflow or value scrutiny rather than affordability alone." if income_issue else "",
    }

    household_issue = ""
    if "living with parents" in family_structure:
        household_text = _joined_text(
            [
                persona.profile.life_story.get("family_story", ""),
                local_grounding.get("family_or_household_norms", []),
                persona.profile.sensitive_scenario_reactions.get("family_or_household_assumptions", {}).get("reaction", ""),
            ]
        )
        if not any(token in household_text for token in ("parent", "family", "shared", "home", "household")):
            household_issue = "Living-with-parents context is not reflected in decision logic or household narrative."
            warnings.append(household_issue)
    checks["household_decision_consistency"] = {
        "status": "warning" if household_issue else "pass",
        "fields_checked": ["family_structure", "family_story", "local_grounding_layer", "sensitive_scenario_reactions"],
        "issue": household_issue,
        "suggested_fix": "Add household rhythm, shared visibility, or intergenerational influence to the persona." if household_issue else "",
    }

    pronoun = _normalize(current_identity_language.get("pronoun_preference"))
    pronoun_issue = ""
    if gender == "woman" and pronoun not in {"she/her", "they/them"}:
        pronoun_issue = "Gender is woman but pronoun_preference does not align."
    elif gender == "man" and pronoun not in {"he/him", "they/them"}:
        pronoun_issue = "Gender is man but pronoun_preference does not align."
    elif gender == "non-binary" and pronoun not in {"they/them", "she/her", "he/him"}:
        pronoun_issue = "Gender is non-binary but pronoun_preference is missing or implausible."
    if pronoun_issue:
        hard_fail_reasons.append("gender_pronoun_conflict")
    if rendered_artifacts:
        rendered_text = " ".join(rendered_artifacts.values()).lower()
        if pronoun == "they/them" and " she " in rendered_text and " he " in rendered_text:
            warnings.append("Rendered markdown appears to mix gendered pronouns with a neutral narration style.")
    checks["gender_pronoun_consistency"] = {
        "status": "fail" if pronoun_issue else "pass",
        "fields_checked": ["gender", "identity_language"],
        "issue": pronoun_issue,
        "suggested_fix": default_identity_language(gender)["pronoun_preference"] if pronoun_issue else "",
    }

    locale_issue = ""
    location_key = _normalize(identity.get("location"))
    apps = {_normalize(item) for item in local_grounding.get("common_apps_or_services", [])}
    expected_apps = set()
    for market, values in EXPECTED_LOCAL_APPS.items():
        if market in location_key:
            expected_apps = values
            break
    if expected_apps and not apps.intersection(expected_apps):
        locale_issue = f"Common apps and services do not look plausible for {identity.get('location', '')}."
        hard_fail_reasons.append("locale_app_payment_conflict")
    checks["locale_app_payment_consistency"] = {
        "status": "fail" if locale_issue else "pass",
        "fields_checked": ["location", "locale_pack", "local_grounding_layer"],
        "issue": locale_issue,
        "suggested_fix": "Replace generic or mismatched app/payment references with local trust and payment cues." if locale_issue else "",
    }

    archetype = _normalize(panel_role_profile.get("behavioural_archetype"))
    panel_role = _normalize(panel_role_profile.get("panel_role"))
    expected_panel_role = _normalize(EXPECTED_PANEL_ROLE_BY_ARCHETYPE.get(archetype, ""))
    archetype_issue = ""
    if expected_panel_role and panel_role != expected_panel_role:
        archetype_issue = (
            f"Behavioural archetype '{panel_role_profile.get('behavioural_archetype', '')}' contradicts panel_role "
            f"'{panel_role_profile.get('panel_role', '')}'."
        )
        hard_fail_reasons.append("archetype_panel_role_conflict")
    checks["archetype_panel_role_consistency"] = {
        "status": "fail" if archetype_issue else "pass",
        "fields_checked": ["panel_role", "behavioural_archetype"],
        "issue": archetype_issue,
        "suggested_fix": EXPECTED_PANEL_ROLE_BY_ARCHETYPE.get(archetype, "") if archetype_issue else "",
    }

    small_business_context = persona.profile.small_business_context
    if "small business owner" in occupation and not _non_empty(small_business_context.get("business_type")):
        warnings.append("Small business owner is missing small_business_context.business_type.")

    status = "pass"
    if hard_fail_reasons:
        status = "fail"
    elif warnings:
        status = "warning"

    return {
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "persona_version": "v3.1.2",
        "status": status,
        "checks": checks,
        "hard_fail_reasons": hard_fail_reasons,
        "warnings": warnings,
        "auto_fixes_applied": applied,
        "human_review_needed": True,
    }
