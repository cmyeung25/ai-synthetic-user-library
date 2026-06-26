from __future__ import annotations

import random
from dataclasses import asdict
from datetime import UTC, datetime

from ai_validation_swarm.domain.models import PersonaSeed, PersonaSkill, SyntheticUser
from ai_validation_swarm.personas.seed_coherence import (
    LIFE_STAGE_OPTIONS,
    PURCHASE_AUTHORITY_TYPES,
    choose_life_stage,
    occupation_title_for_band,
    choose_purchase_authority,
)

# POC note:
# The option pools in this module are intentionally small so the generator stays auditable.
# The SaaS path should replace them with larger weighted catalogs and diversity controls.

PANEL_ROLES = [
    "mainstream",
    "skeptic",
    "privacy_sensitive",
    "inclusion",
    "political_risk",
    "low_tech",
    "budget_constrained",
    "extreme_user",
    "expert_advisor",
]

FIRST_NAMES_BY_GENDER = {
    "woman": [
        "Mei",
        "Priya",
        "Aisha",
        "Grace",
        "Nina",
        "Ivy",
        "Hannah",
        "Chloe",
        "Jasmine",
        "Elaine",
        "Sofia",
        "Mira",
        "Leah",
        "Carmen",
        "Joanna",
        "Vanessa",
        "Natalie",
        "Farah",
        "Rina",
        "Celeste",
    ],
    "man": [
        "Daniel",
        "Leo",
        "Marcus",
        "Ethan",
        "Noah",
        "Jason",
        "Adrian",
        "Ryan",
        "Calvin",
        "Victor",
        "Isaac",
        "Julian",
        "Owen",
        "Benjamin",
        "Miles",
        "Aaron",
        "Sean",
        "Felix",
        "Kevin",
        "Darren",
    ],
    "non-binary": [
        "Alex",
        "Jordan",
        "Sam",
        "Taylor",
        "Casey",
        "Avery",
        "Quinn",
        "Morgan",
        "Riley",
        "Jamie",
        "Emerson",
        "Hayden",
        "Parker",
        "Skyler",
        "Blake",
        "River",
        "Sage",
        "Reese",
        "Finley",
        "Devon",
    ],
}

LAST_NAMES = [
    "Chan",
    "Wong",
    "Tan",
    "Lee",
    "Patel",
    "Lim",
    "Ng",
    "Lau",
    "Ho",
    "Yap",
    "Cheung",
    "Koh",
    "Cheng",
    "Tanaka",
    "Lin",
    "Su",
    "Goh",
    "Teo",
    "Mak",
    "Chu",
    "Fong",
    "Poon",
    "Tay",
    "Foo",
]

LOCATION_OPTIONS = {
    "urban_core": [
        ("Hong Kong", ["Cantonese", "English"], "hong_kong_smb"),
        ("Singapore", ["English", "Mandarin"], "singapore_smb"),
        ("Taipei", ["Mandarin", "English"], "taiwan_knowledge_work"),
        ("Kuala Lumpur", ["English", "Malay"], "regional_sea_service_ops"),
    ],
    "suburban": [
        ("New Territories", ["Cantonese", "English"], "new_territories_operator"),
        ("Johor Bahru", ["English", "Malay"], "regional_sea_service_ops"),
        ("Taoyuan", ["Mandarin"], "taiwan_knowledge_work"),
        ("Shatin", ["Cantonese", "English"], "hong_kong_smb"),
    ],
    "regional": [
        ("Ipoh", ["English", "Malay"], "regional_sea_service_ops"),
        ("Kaohsiung", ["Mandarin"], "taiwan_knowledge_work"),
        ("Penang", ["English", "Mandarin"], "regional_sea_service_ops"),
        ("Kuching", ["English", "Malay"], "regional_sea_service_ops"),
    ],
}

AGE_BANDS = {
    "18-24": (18, 24),
    "25-34": (25, 34),
    "35-44": (35, 44),
    "45-54": (45, 54),
    "55-64": (55, 64),
}

ROLE_PROFILES = {
    "mainstream": {
        "age_bands": ["25-34", "35-44", "45-54"],
        "occupation_bands": ["operations", "client_service", "small_business", "program_management"],
        "income_bands": ["middle", "upper_middle", "lower_middle"],
        "budget_flexibility": ["medium", "medium", "high"],
        "privacy_risk_tolerance": ["medium"],
        "digital_literacy_ceiling": ["medium", "high"],
    },
    "skeptic": {
        "age_bands": ["35-44", "45-54", "55-64"],
        "occupation_bands": ["finance", "procurement", "operations", "compliance_ops"],
        "income_bands": ["middle", "upper_middle"],
        "budget_flexibility": ["medium"],
        "privacy_risk_tolerance": ["low", "medium"],
        "digital_literacy_ceiling": ["medium", "high"],
    },
    "privacy_sensitive": {
        "age_bands": ["25-34", "35-44", "45-54"],
        "occupation_bands": ["health_admin", "education_ops", "operations", "compliance_ops"],
        "income_bands": ["middle"],
        "budget_flexibility": ["medium"],
        "privacy_risk_tolerance": ["low"],
        "digital_literacy_ceiling": ["medium"],
    },
    "inclusion": {
        "age_bands": ["25-34", "35-44", "45-54"],
        "occupation_bands": ["community", "education_ops", "client_service", "customer_success"],
        "income_bands": ["middle"],
        "budget_flexibility": ["medium"],
        "privacy_risk_tolerance": ["medium"],
        "digital_literacy_ceiling": ["medium"],
    },
    "political_risk": {
        "age_bands": ["35-44", "45-54", "55-64"],
        "occupation_bands": ["communications", "small_business", "operations", "community"],
        "income_bands": ["middle", "upper_middle"],
        "budget_flexibility": ["medium"],
        "privacy_risk_tolerance": ["low", "medium"],
        "digital_literacy_ceiling": ["medium", "high"],
    },
    "low_tech": {
        "age_bands": ["35-44", "45-54", "55-64"],
        "occupation_bands": ["retail", "logistics", "small_business", "field_service"],
        "income_bands": ["middle", "lower_middle"],
        "budget_flexibility": ["low", "medium"],
        "privacy_risk_tolerance": ["medium"],
        "digital_literacy_ceiling": ["low"],
    },
    "budget_constrained": {
        "age_bands": ["18-24", "25-34", "35-44"],
        "occupation_bands": ["retail", "operations", "education_ops", "field_service"],
        "income_bands": ["lower_middle", "middle"],
        "budget_flexibility": ["low"],
        "privacy_risk_tolerance": ["medium"],
        "digital_literacy_ceiling": ["medium"],
    },
    "extreme_user": {
        "age_bands": ["25-34", "35-44", "45-54"],
        "occupation_bands": ["founder", "consulting", "small_business", "customer_success"],
        "income_bands": ["middle", "upper_middle"],
        "budget_flexibility": ["high"],
        "privacy_risk_tolerance": ["medium", "high"],
        "digital_literacy_ceiling": ["high"],
    },
    "expert_advisor": {
        "age_bands": ["35-44", "45-54", "55-64"],
        "occupation_bands": ["founder", "consulting", "program_management", "communications"],
        "income_bands": ["upper_middle", "middle"],
        "budget_flexibility": ["medium", "high"],
        "privacy_risk_tolerance": ["medium"],
        "digital_literacy_ceiling": ["high"],
    },
}

HOUSEHOLDS = [
    "living alone",
    "living with partner",
    "living with partner and one child",
    "living with parents",
    "living with roommates",
    "single parent with one child",
    "multi-generational household",
]

PAYMENT_ENVIRONMENTS = ["digital-first", "mixed", "careful subscription user"]
SCHEDULE_PRESSURE = ["low", "medium", "high"]
CAREGIVING_LOAD = ["low", "medium", "high"]
TRUST_THRESHOLDS = ["needs_social_proof", "needs_trial", "adopts_after_peer_signal"]
SWITCHING_COSTS = ["low", "medium", "high"]
EMPLOYMENT_STABILITY = ["stable", "variable", "contract_based"]
WORKFLOW_MATURITY = ["ad_hoc", "repeatable", "documented", "tool_heavy"]
DECISION_SPEED = ["fast", "deliberate", "committee_slow"]
PROOF_THRESHOLDS = ["light_demo", "visible_trial", "case_studies_required", "peer_reference_required"]
CASH_FLOW_VOLATILITY = ["low", "medium", "high"]
ACCESSIBILITY_NEEDS = [
    "none",
    "prefers_low_cognitive_load",
    "needs_clear_visual_hierarchy",
    "prefers_short_forms",
]
HOUSEHOLD_SIZE_BY_STRUCTURE = {
    "living alone": 1,
    "living with partner": 2,
    "living with partner and one child": 3,
    "living with roommates": 2,
    "single parent with one child": 2,
}


def _choose(rng: random.Random, options: list[str]) -> str:
    return options[rng.randrange(len(options))]


def _panel_for_index(index: int) -> str:
    return PANEL_ROLES[index % len(PANEL_ROLES)]


def _humanize_token(value: str) -> str:
    return value.replace("_", " ")


def build_seed(index: int, rng: random.Random, panel_role: str | None = None) -> PersonaSeed:
    role = panel_role or _panel_for_index(index)
    profile = ROLE_PROFILES[role]
    location_type = _choose(rng, list(LOCATION_OPTIONS.keys()))
    household_structure = _choose(rng, HOUSEHOLDS)
    age_band = _choose(rng, profile["age_bands"])
    occupation_band = _choose(rng, profile["occupation_bands"])
    return PersonaSeed(
        seed_id=f"seed_{index + 1:04d}",
        panel_role=role,
        age_band=age_band,
        location_type=location_type,
        household_structure=household_structure,
        occupation_band=occupation_band,
        income_band=_choose(rng, profile["income_bands"]),
        education_band=_choose(rng, ["diploma", "bachelor", "postgraduate"]),
        language=[],
        device_environment=_choose(rng, ["smartphone-first", "phone-plus-laptop", "multi-device"]),
        payment_environment=_choose(rng, PAYMENT_ENVIRONMENTS),
        purchase_authority_type=choose_purchase_authority(
            rng=rng,
            age_band=age_band,
            occupation_band=occupation_band,
            household_structure=household_structure,
            panel_role=role,
            legacy_roll_size=4,
        ),
        employment_stability=_choose(rng, EMPLOYMENT_STABILITY),
        workflow_maturity=_choose(rng, WORKFLOW_MATURITY),
        schedule_pressure=_choose(rng, SCHEDULE_PRESSURE),
        budget_flexibility=_choose(rng, profile["budget_flexibility"]),
        caregiving_load=_choose(rng, CAREGIVING_LOAD),
        trust_threshold=_choose(rng, TRUST_THRESHOLDS),
        switching_cost_level=_choose(rng, SWITCHING_COSTS),
        privacy_risk_tolerance=_choose(rng, profile["privacy_risk_tolerance"]),
        digital_literacy_ceiling=_choose(rng, profile["digital_literacy_ceiling"]),
        decision_speed=_choose(rng, DECISION_SPEED),
        proof_threshold=_choose(rng, PROOF_THRESHOLDS),
        cash_flow_volatility=_choose(rng, CASH_FLOW_VOLATILITY),
        occupation_title=occupation_title_for_band(occupation_band),
        life_stage=choose_life_stage(
            rng=rng,
            age_band=age_band,
            occupation_band=occupation_band,
            household_structure=household_structure,
            panel_role=role,
            legacy_roll_size=5,
        ),
    )


def _age_for_band(rng: random.Random, age_band: str) -> int:
    start, end = AGE_BANDS[age_band]
    return rng.randint(start, end)


def _score_from_level(level: str) -> int:
    return {"low": 2, "medium": 3, "high": 4}.get(level, 3)


def _name_for_index(index: int, gender: str) -> str:
    first_names = FIRST_NAMES_BY_GENDER[gender]
    first = first_names[index % len(first_names)]
    # Rotate both components from the first record so early batches do not all share a surname.
    last = LAST_NAMES[index % len(LAST_NAMES)]
    return f"{first} {last}"


def _household_size_for_structure(rng: random.Random, family_structure: str) -> int:
    if family_structure in HOUSEHOLD_SIZE_BY_STRUCTURE:
        return HOUSEHOLD_SIZE_BY_STRUCTURE[family_structure]
    if family_structure == "living with parents":
        return rng.choice([2, 3, 4])
    if family_structure == "multi-generational household":
        return rng.choice([4, 5, 6])
    raise ValueError(f"Unsupported family structure: {family_structure}")


def _problem_pains(seed: PersonaSeed) -> list[str]:
    pains = ["too many tools", "manual follow-up", "context scattered across messages"]
    if seed.schedule_pressure == "high":
        pains.append("not enough uninterrupted time")
    if seed.caregiving_load == "high":
        pains.append("family responsibilities make admin work feel heavier")
    if seed.panel_role == "budget_constrained":
        pains.append("subscription creep across business tools")
    if seed.panel_role == "privacy_sensitive":
        pains.append("sharing sensitive client or customer details across apps")
    if seed.panel_role == "low_tech":
        pains.append("new tools often create more setup work than relief")
    if seed.workflow_maturity in {"ad_hoc", "tool_heavy"}:
        pains.append("workflow habits break when too many exceptions pile up")
    if seed.cash_flow_volatility == "high":
        pains.append("short-term cash pressure makes software decisions feel riskier")
    return pains


def _response_boundaries(seed: PersonaSeed) -> list[str]:
    boundaries = ["will not share private third-party data without a clear reason"]
    if seed.panel_role in {"political_risk", "privacy_sensitive"}:
        boundaries.append("avoids products that require sensitive profiling")
    if seed.panel_role == "inclusion":
        boundaries.append("flags wording that could exclude less-confident users")
    if seed.life_stage == "young_family_builder":
        boundaries.append("will reject workflows that assume uninterrupted attention or endless setup time")
    return boundaries


def _decision_policy(seed: PersonaSeed) -> dict[str, list[str] | str]:
    trust_requirements = ["clear before-and-after value", "low-friction onboarding"]
    rejection_triggers = ["extra admin burden", "vague claims without proof"]
    proof_requirements = ["specific examples from similar users", "a short trial workflow"]

    if seed.privacy_risk_tolerance == "low":
        trust_requirements.append("plain-language data handling explanation")
        rejection_triggers.append("unclear data retention or model training policy")
        proof_requirements.append("proof that sensitive data can stay minimal")

    if seed.budget_flexibility == "low":
        rejection_triggers.append("subscription cost that grows before value is obvious")
        proof_requirements.append("simple ROI signal within the first week")

    if seed.digital_literacy_ceiling == "low":
        trust_requirements.append("simple setup with very few moving parts")
        rejection_triggers.append("a setup process that assumes technical confidence")
    if seed.workflow_maturity == "tool_heavy":
        rejection_triggers.append("another tool that adds one more dashboard without replacing existing work")
    if seed.decision_speed == "committee_slow":
        proof_requirements.append("buy-in material that can be shared with other decision-makers")
    if seed.purchase_authority_type in {
        "manager_approval_needed",
        "team_budget_influencer",
        "department_budget_requester",
        "department_budget_recommender",
        "client_service_recommender",
        "workflow_tool_evaluator",
        "owner_with_business_partner_input",
        "owner_with_family_consultation",
        "owner_with_staff_input",
    }:
        proof_requirements.append("evidence that the workflow can survive internal review and comparison")
    if seed.purchase_authority_type in {"shared_household_decider", "owner_with_family_consultation"}:
        proof_requirements.append("pricing and effort that can be explained clearly in household terms")

    adoption_style = {
        "extreme_user": "tries new tools early if the workflow gain is obvious",
        "skeptic": "waits for evidence and edge-case answers before changing habits",
        "low_tech": "adopts slowly and only if the tool feels easier than the current workaround",
    }.get(seed.panel_role, "adopts when the payoff is concrete and the risk feels bounded")

    return {
        "adoption_style": adoption_style,
        "trust_requirements": trust_requirements,
        "rejection_triggers": rejection_triggers,
        "proof_requirements": proof_requirements,
    }


def _response_style(seed: PersonaSeed) -> dict[str, str]:
    articulation = "high" if seed.panel_role in {"skeptic", "extreme_user"} else "medium"
    if seed.panel_role == "low_tech":
        articulation = "low"
    return {
        "articulation_level": articulation,
        "directness": "high" if seed.panel_role in {"skeptic", "budget_constrained"} else "medium",
        "detail_tendency": "high" if seed.panel_role == "privacy_sensitive" or seed.proof_threshold == "case_studies_required" else "medium",
    }


def _narrative(skill: PersonaSkill) -> str:
    profile = skill.profile
    identity = profile.basic_identity
    story = profile.life_story
    decision_policy = skill.decision_policy
    return "\n".join(
        [
            f"# {identity['name']}",
            "",
            "## Snapshot",
            f"- ID: {identity['synthetic_user_id']}",
            f"- Panel role: {skill.seed.panel_role}",
            f"- Occupation: {identity['occupation']}",
            f"- Household: {identity['family_structure']}",
            "",
            "## Daily Reality",
            story["current_daily_routine"],
            "",
            "## What Shapes Decisions",
            f"- Adoption style: {decision_policy['adoption_style']}",
            f"- Trust requirements: {', '.join(decision_policy['trust_requirements'])}",
            f"- Rejection triggers: {', '.join(decision_policy['rejection_triggers'])}",
            f"- Proof requirements: {', '.join(decision_policy['proof_requirements'])}",
            "",
            "## Response Boundaries",
            f"- {profile.sensitive_reality_layer['response_boundaries'][0]}",
        ]
    )


def _housing_status(seed: PersonaSeed, rng: random.Random) -> str:
    if seed.income_band == "upper_middle":
        return _choose(rng, ["owner-occupier", "renting"])
    if seed.household_structure in {"living with parents", "multi-generational household"}:
        return _choose(rng, ["family home", "owner-occupier"])
    return _choose(rng, ["renting", "family home"])


def _marital_status(family_structure: str) -> str:
    if family_structure in {"living with partner", "living with partner and one child"}:
        return "married"
    return "single"


def enrich_seed(seed: PersonaSeed, index: int, rng: random.Random) -> PersonaSkill:
    location, languages, locale_pack = LOCATION_OPTIONS[seed.location_type][rng.randrange(len(LOCATION_OPTIONS[seed.location_type]))]
    age = _age_for_band(rng, seed.age_band)
    occupation = seed.occupation_title or occupation_title_for_band(seed.occupation_band)
    synthetic_user_id = f"su_{index + 1:04d}"
    gender = _choose(rng, ["woman", "man", "non-binary"])
    name = _name_for_index(index, gender)

    family_structure = seed.household_structure
    basic_identity = {
        "synthetic_user_id": synthetic_user_id,
        "name": name,
        "age": age,
        "gender": gender,
        "location": location,
        "language": languages,
        "locale_pack": locale_pack,
        "occupation": occupation,
        "education_level": seed.education_band,
        "income_level": seed.income_band,
        "marital_status": _marital_status(family_structure),
        "family_structure": family_structure,
        "household_size": _household_size_for_structure(rng, family_structure),
        "living_area": seed.location_type,
        "housing_status": _housing_status(seed, rng),
        "life_stage": seed.life_stage,
    }

    personality_belief = {
        "mbti": _choose(rng, ["ISTJ", "ENFJ", "INTP", "ESFJ", "ENTJ", "ISFJ"]),
        "big_five": {
            "openness": 72 if seed.panel_role == "extreme_user" else 54,
            "conscientiousness": 71,
            "extraversion": 46 if seed.panel_role == "skeptic" else 58,
            "agreeableness": 61,
            "neuroticism": 52 if seed.schedule_pressure == "high" else 38,
        },
        "zodiac": _choose(rng, ["Aries", "Leo", "Virgo", "Libra", "Capricorn", "Pisces"]),
        "metaphysical_profile": "Used only as cultural flavor, never as a decision rule.",
        "decision_style": "practical and constrained by real workflow trade-offs",
        "risk_tolerance": seed.trust_threshold,
        "trust_orientation": "needs proof from concrete workflows, not just positioning",
        "self_image": "responsible, busy, and careful about adding complexity",
        "social_comparison_tendency": "moderate",
    }

    technology_profile = {
        "tech_savviness": seed.digital_literacy_ceiling,
        "ai_familiarity": "high" if seed.panel_role == "extreme_user" else "medium" if seed.digital_literacy_ceiling == "high" else "low",
        "digital_payment_comfort": "high" if seed.payment_environment == "digital-first" else "medium",
        "privacy_concern": "high" if seed.privacy_risk_tolerance == "low" else "medium",
        "app_fatigue": "high" if seed.schedule_pressure == "high" else "medium",
        "automation_openness": "high" if seed.panel_role == "extreme_user" else "medium",
        "accessibility_needs": _choose(rng, ACCESSIBILITY_NEEDS),
        "language_confidence": "high" if len(languages) > 1 else "medium",
    }

    economic_profile = {
        "disposable_income": seed.income_band,
        "price_sensitivity": seed.budget_flexibility,
        "subscription_tolerance": "low" if seed.budget_flexibility == "low" else "medium",
        "purchase_decision_process": "tests fit against current workflow before committing",
        "current_alternatives": ["manual notes", "spreadsheets", "existing messaging apps"],
        "switching_cost": seed.switching_cost_level,
        "purchase_authority_type": seed.purchase_authority_type,
        "employment_stability": seed.employment_stability,
        "cash_flow_volatility": seed.cash_flow_volatility,
    }

    values = {
        "core_values": ["reliability", "time protection", "clarity", "practicality"][:3 + (1 if seed.panel_role == "skeptic" else 0)],
        "life_goals": ["stay on top of work without constant catch-up", "protect personal bandwidth", "keep promises visible"][:2 + (1 if seed.schedule_pressure == "high" else 0)],
        "fears": ["paying for another tool that becomes shelfware", "making work messier", "looking careless with follow-up"][:2 + (1 if seed.panel_role in {"privacy_sensitive", "political_risk"} else 0)],
        "aspirations": ["reduce admin drag", "look more organised and trustworthy", "protect energy for higher-value work"][:2 + (1 if seed.panel_role != "low_tech" else 0)],
        "identity_anchors": ["responsible teammate", "careful buyer", "steady operator"][:2 + (1 if seed.panel_role in {"mainstream", "budget_constrained"} else 0)],
        "moral_boundaries": ["will not trade away other people's privacy for convenience"],
        "status_concerns": ["does not want to appear disorganised in front of clients or team"],
    }

    life_story = {
        "childhood_background": f"Grew up in a household that valued practical decisions and financial caution in a {locale_pack.replace('_', ' ')} context.",
        "education_journey": (
            f"Completed {seed.education_band} level education and learned through a mix of formal training "
            f"and on-the-job repetition during a {_humanize_token(seed.life_stage)} phase."
        ),
        "career_path": (
            f"Moved into {occupation} work because it rewards reliability and the ability to keep moving parts aligned. "
            f"Workflow maturity is currently {_humanize_token(seed.workflow_maturity)}."
        ),
        "family_story": f"Currently {family_structure}, which shapes both available time and risk tolerance. Caregiving load is {seed.caregiving_load}.",
        "current_daily_routine": (
            "Most weekdays are split between coordination work, message follow-up, and protecting small windows of focused time. "
            f"Schedule pressure is {seed.schedule_pressure}, decision speed is {_humanize_token(seed.decision_speed)}, and purchase authority is {_humanize_token(seed.purchase_authority_type)}."
        ),
        "recent_life_events": ["recently reviewed software spend", "trying to reduce context-switching during the week", f"reassessing workflow due to {seed.cash_flow_volatility} cash-flow volatility"][:2 + (1 if seed.cash_flow_volatility != "low" else 0)],
        "frustrations": _problem_pains(seed),
        "hidden_needs": ["wants confidence that a new tool will simplify the week quickly", "needs a reason to trust the workflow before sharing real work into it"],
    }

    behavior_profile = {
        "buying_behavior": "waits until value is concrete enough to justify habit change",
        "information_sources": ["peer referrals", "product demos", "comparison notes"],
        "social_media_usage": ["LinkedIn", "WhatsApp groups"],
        "referral_influence": "moderate to high",
        "brand_trust_signals": ["clear onboarding", "specific user stories", "visible privacy stance"],
        "decision_blockers": ["uncertain ROI", "messy setup", "trust gap"],
        "emotional_triggers": ["relief from admin burden", "feeling more in control of follow-up"],
        "workflow_maturity": seed.workflow_maturity,
        "documentation_discipline": "high" if seed.workflow_maturity in {"documented", "tool_heavy"} else "medium",
        "manager_approval_dependence": (
            "high"
            if seed.purchase_authority_type
            in {
                "manager_approval_needed",
                "team_budget_influencer",
                "department_budget_requester",
                "department_budget_recommender",
                "client_service_recommender",
                "workflow_tool_evaluator",
            }
            else "low"
        ),
    }

    problem_context = {
        "active_pain_points": _problem_pains(seed),
        "latent_pain_points": ["mental load from tracking too many loose ends", "slow drift between promises and actual follow-up"],
        "jobs_to_be_done": ["capture next actions reliably", "reduce manual follow-up work", "avoid dropped tasks"],
        "current_workaround": ["manual checklist", "calendar reminders", "message search"],
        "urgency_level": "medium" if seed.panel_role == "mainstream" else "high" if seed.panel_role == "extreme_user" else "medium",
        "willingness_to_change": "high" if seed.switching_cost_level == "low" else "medium",
        "willingness_to_pay": "medium" if seed.budget_flexibility != "low" else "low",
        "proof_threshold": seed.proof_threshold,
    }

    sensitive_reality_layer = {
        "sensitive_identity_context": ["synthetic persona for pre-validation only"],
        "social_risk_profile": "does not want to look careless with colleagues' or clients' information",
        "fairness_and_inclusion_profile": "expects product language to remain respectful and not assume one type of user",
        "taboo_topic_comfort": "low",
        "political_sensitivity": "medium" if seed.panel_role == "political_risk" else "low",
        "discrimination_awareness": "high" if seed.panel_role in {"inclusion", "privacy_sensitive"} else "medium",
        "public_expression_risk_aversion": "high" if seed.panel_role == "political_risk" else "medium",
        "identity_labeling_comfort": "low",
        "response_boundaries": _response_boundaries(seed),
        "public_explanation_preference": "plain language with concrete examples",
    }

    audit_evidence_layer = {
        "persona_generation_method": "deterministic_seed_plus_template_enrichment_v1",
        "evidence_grade": "synthetic_seeded",
        "source_basis": ["panel_frame", "seed_constraints", "trait_catalogs", "template_enrichment"],
        "stereotype_risk_score": _score_from_level("medium"),
        "synthetic_only_disclaimer": "Synthetic persona for AI pre-validation only.",
        "do_not_use_for": [
            "employment screening",
            "credit or insurance decisions",
            "medical guidance",
            "legal guidance",
            "discriminatory targeting",
        ],
        "last_audited_at": datetime.now(UTC).date().isoformat(),
        "persona_version": "v1",
        "diversity_dimensions": [
            "panel_role",
            "locale_pack",
            "life_stage",
            "purchase_authority_type",
            "workflow_maturity",
            "cash_flow_volatility",
        ],
    }

    profile = SyntheticUser(
        basic_identity=basic_identity,
        personality_belief=personality_belief,
        technology_profile=technology_profile,
        economic_profile=economic_profile,
        values=values,
        life_story=life_story,
        behavior_profile=behavior_profile,
        problem_context=problem_context,
        sensitive_reality_layer=sensitive_reality_layer,
        audit_evidence_layer=audit_evidence_layer,
    )

    skill = PersonaSkill(
        skill_version="v1",
        seed=PersonaSeed(**{**asdict(seed), "language": languages, "locale_pack": locale_pack}),
        profile=profile,
        decision_policy=_decision_policy(seed),
        response_style=_response_style(seed),
        narrative="",
        audit=audit_evidence_layer,
    )
    skill.narrative = _narrative(skill)
    return skill


def generate_personas(count: int, random_seed: int = 11, enricher=None, judge=None) -> list[PersonaSkill]:
    personas: list[PersonaSkill] = []
    for index in range(count):
        rng = random.Random(random_seed + index)
        seed = build_seed(index=index, rng=rng)
        persona = enrich_seed(seed=seed, index=index, rng=rng)
        if enricher is not None:
            persona = enricher.enrich(persona)
        if judge is not None:
            persona.audit["judge_review"] = judge.judge(persona)
        personas.append(persona)
    return personas
