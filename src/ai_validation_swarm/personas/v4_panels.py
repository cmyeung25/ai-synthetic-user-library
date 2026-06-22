from __future__ import annotations

import copy
from typing import Any


HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK = "hk_retail_bank_portfolio_health_check"

_BANKING_CONTEXT_FIELDS = [
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
]

_CONCEPT_REACTION_FIELDS = [
    "first_reaction",
    "strongest_appeal",
    "biggest_concern",
    "what_they_understand",
    "what_they_misunderstand",
    "data_they_would_share",
    "data_they_would_not_share",
    "preferred_explanation_format",
    "whether_rm_needed",
    "whether_they_would_pay",
    "what_would_make_them_try",
    "what_would_make_them_abandon",
]


def _merge_guide(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in {"fixed", "preferred"}:
            target = dict(merged.get(key, {}))
            if isinstance(value, dict):
                target.update(value)
            merged[key] = target
            continue
        merged[key] = copy.deepcopy(value)
    return merged


def _persona_id(number: int) -> str:
    if number < 0:
        raise ValueError("Persona ID number must be non-negative.")
    return f"su_{number:04d}"


def build_hk_retail_bank_portfolio_health_check_panel(*, starting_id: int = 1201) -> dict[str, Any]:
    common_guide: dict[str, Any] = {
        "mode": "guided",
        "required_profile_sections": ["banking_context"],
        "panel_preset": HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
        "research_context": {
            "market": "Hong Kong retail and affluent retail banking",
            "poc_goal": (
                "Test whether Hong Kong retail banking customers accept bank-delivered institutional-grade "
                "portfolio risk analytics to understand their investments before making decisions."
            ),
            "positioning": (
                "Bank app Portfolio Health Check with institutional-grade investment risk analysis, "
                "not direct Aladdin retail selling and not AI auto-trading."
            ),
            "core_assumptions": [
                "Customers may feel current bank advice is too product-led rather than portfolio-led.",
                "Customers may struggle to interpret portfolio risk, stress tests, and scenario analysis.",
                "Institutional brands such as BlackRock may increase trust for some customers and trigger conflict concerns for others.",
                "Customers may hesitate to let the bank aggregate external holdings across stocks, funds, ETFs, bonds, insurance, and MPF.",
                "Risk analysis may either encourage action or make customers more conservative.",
                "Some customers want RM interpretation while others prefer self-serve app analysis.",
                "Premium analytics or advisory may be chargeable for some segments.",
                "Skeptical customers may fear the tool is just a more sophisticated sales engine.",
            ],
            "concept_card": {
                "name": "Portfolio Health Check",
                "description": (
                    "A bank app feature that uses institutional-grade portfolio analytics, similar to "
                    "BlackRock Aladdin or Aladdin Wealth capabilities, to show total portfolio risk, concentration, "
                    "stress tests, scenario analysis, risk-profile mismatch, plain-language explanations, and an optional RM review report."
                ),
                "non_goals": [
                    "Not auto-trading",
                    "Not direct execution without customer confirmation",
                    "Not sold as a pure Aladdin retail product",
                ],
            },
        },
        "concept_output_contracts": {
            "portfolio_health_check": {
                "description": (
                    "Concept-specific reaction to the bank app Portfolio Health Check stimulus. "
                    "This is not a stable persona trait and should be returned as sidecar concept output."
                ),
                "required_fields": list(_CONCEPT_REACTION_FIELDS),
            }
        },
        "fixed": {
            "location": "Hong Kong",
            "market_scope": "retail_or_affluent_retail_banking",
            "preferred_languages": ["Cantonese", "English"],
            "concept_frame": "institutional_grade_portfolio_risk_analytics_in_bank_app",
        },
        "preferred": {
            "portfolio_health_check_must_cover": [
                "whole-portfolio risk",
                "sector and geography concentration",
                "currency exposure",
                "stress testing",
                "scenario analysis",
                "risk-profile mismatch explanation",
            ],
            "response_rule": (
                "Distinguish what this person understands, what still confuses them, and whether the feature would increase trust, action, or avoidance."
            ),
        },
    }

    personas = [
        {
            "label": "learning_oriented_first_time_investor",
            "archetype": "學習型",
            "guide": {
                "fixed": {
                    "age_range": "25-30",
                    "investable_assets_band": "HKD 50k-200k",
                    "persona_focus": "Young First-Time Investor",
                    "monthly_income_band": "early_career_professional",
                },
                "preferred": {
                    "bank_relationship": "Uses one main retail bank app and may buy simple funds or ETFs there.",
                    "investment_experience": "Recently started investing and learns from friends, YouTube, and social media.",
                    "investment_products_held": ["ETF", "mutual fund", "a few single-name stocks"],
                    "primary_financial_goal": "Build confidence and avoid obvious mistakes while growing savings.",
                    "current_investment_decision_process": "Idea first, risk understanding later.",
                    "relationship_manager_usage": "Rarely speaks to RM unless very unsure.",
                    "digital_banking_usage": "High app usage, low patience for dense financial jargon.",
                    "risk_understanding_level": "Knows diversification in theory but not portfolio analytics in depth.",
                    "interview_focus": [
                        "Whether stress testing feels educational or scary",
                        "Whether explanations need visuals and plain language",
                        "Whether the feature increases confidence enough to ask for help",
                    ],
                },
            },
        },
        {
            "label": "self_directed_active_investor",
            "archetype": "自主型",
            "guide": {
                "fixed": {
                    "age_range": "30-45",
                    "investable_assets_band": "HKD 500k-3m",
                    "persona_focus": "Self-Directed Active Investor",
                },
                "preferred": {
                    "bank_relationship": "Uses a bank for cash and some holdings but prefers broker tools for active positions.",
                    "investment_experience": "Comfortable with stocks, ETFs, and funds; follows markets actively.",
                    "investment_products_held": ["Hong Kong stocks", "US stocks", "ETF", "fund"],
                    "primary_financial_goal": "Improve whole-portfolio visibility without giving up control.",
                    "current_investment_decision_process": "Self-research, comparison charts, external communities, selective bank use.",
                    "relationship_manager_usage": "Low trust in RM product pushes.",
                    "digital_banking_usage": "High, but compares with broker-grade interfaces.",
                    "risk_understanding_level": "Understands portfolio concepts and wants depth, not generic warnings.",
                    "interview_focus": [
                        "Whether bank analytics are deep and timely enough",
                        "Whether external holdings sync is worth the privacy trade-off",
                        "Whether institutional analytics can win back wallet share",
                    ],
                },
            },
        },
        {
            "label": "conservative_income_seeker",
            "archetype": "保守收息型",
            "guide": {
                "fixed": {
                    "age_range": "50-70",
                    "investable_assets_band": "HKD 1m-8m",
                    "persona_focus": "Conservative Income Seeker",
                },
                "preferred": {
                    "bank_relationship": "Long-term relationship with a traditional bank and familiar branch or RM touchpoints.",
                    "investment_experience": "Experienced in deposits, bonds, income funds, and high-yield stocks, but not factor analysis.",
                    "investment_products_held": ["time deposit", "bond", "income fund", "high-dividend stock"],
                    "primary_financial_goal": "Protect principal and maintain dependable income.",
                    "current_investment_decision_process": "Prefers trusted explanations and stability over frequent changes.",
                    "relationship_manager_usage": "Moderate to high when discussing income products.",
                    "digital_banking_usage": "Moderate; accepts app use if clearly explained.",
                    "risk_understanding_level": "May over-associate income products with low risk.",
                    "interview_focus": [
                        "Whether rate and credit stress tests are enlightening or feel like fear-based selling",
                        "Whether cash-flow safety framing works better than analytics framing",
                        "Whether RM explanation is necessary for trust",
                    ],
                },
            },
        },
        {
            "label": "family_goal_based_planner",
            "archetype": "家庭目標型",
            "guide": {
                "fixed": {
                    "age_range": "35-50",
                    "investable_assets_band": "HKD 1m-5m",
                    "persona_focus": "Family Wealth Planner",
                },
                "preferred": {
                    "bank_relationship": "Uses the bank as a household financial hub across savings, mortgage, insurance, and investments.",
                    "investment_experience": "Practical rather than hobbyist; invests for family milestones.",
                    "investment_products_held": ["insurance", "education savings fund", "stock", "fund", "MPF"],
                    "primary_financial_goal": "Protect education, housing, and retirement goals for the family.",
                    "current_investment_decision_process": "Balances goal progress, family obligations, and risk tolerance.",
                    "relationship_manager_usage": "Selective; wants advice connected to goals, not just products.",
                    "digital_banking_usage": "High for household admin and monitoring.",
                    "risk_understanding_level": "Understands risk better when tied to life goals and downside consequences.",
                    "interview_focus": [
                        "Whether goal-success framing beats abstract risk framing",
                        "Whether they will aggregate MPF, insurance, and family assets",
                        "Whether shared household visibility matters",
                    ],
                },
            },
        },
        {
            "label": "rm_trusting_affluent_client",
            "archetype": "RM 信任型",
            "guide": {
                "fixed": {
                    "age_range": "45-65",
                    "investable_assets_band": "HKD 8m-50m",
                    "persona_focus": "Affluent RM-Advised Client",
                },
                "preferred": {
                    "bank_relationship": "Affluent or private banking relationship with regular RM contact.",
                    "investment_experience": "Owns a diversified mix and expects professional service quality.",
                    "investment_products_held": ["bond", "fund", "structured product", "FX", "insurance"],
                    "primary_financial_goal": "Protect and grow wealth with credible advisory support.",
                    "current_investment_decision_process": "Discusses with RM but remains alert to product bias.",
                    "relationship_manager_usage": "High, but trust must feel earned each review cycle.",
                    "digital_banking_usage": "Moderate to high as a monitoring and review tool.",
                    "risk_understanding_level": "Comfortable with advisory conversations, less interested in raw dashboards alone.",
                    "interview_focus": [
                        "Whether BlackRock-powered analytics increase advisory credibility",
                        "Whether third-party analytics reduce product-push suspicion",
                        "Whether premium reporting feels worth paying for",
                    ],
                },
            },
        },
        {
            "label": "cross_border_multi_currency_investor",
            "archetype": "跨境複雜型",
            "guide": {
                "fixed": {
                    "age_range": "30-55",
                    "investable_assets_band": "HKD 2m-12m",
                    "persona_focus": "Cross-Border Multi-Currency Investor",
                },
                "preferred": {
                    "bank_relationship": "Maintains banking relationships across currencies and possibly multiple jurisdictions.",
                    "investment_experience": "Comfortable with multi-market holdings and currency movements.",
                    "investment_products_held": ["HKD cash", "USD assets", "RMB assets", "US ETF", "Hong Kong stocks", "A-share exposure"],
                    "primary_financial_goal": "See total cross-border risk clearly before reallocating.",
                    "current_investment_decision_process": "Looks across currencies, rates, and markets rather than only products.",
                    "relationship_manager_usage": "Moderate when useful, but independent verification matters.",
                    "digital_banking_usage": "High, expects bilingual clarity and consolidated views.",
                    "risk_understanding_level": "Understands some complexity but still lacks one whole-portfolio view.",
                    "interview_focus": [
                        "Whether FX and cross-market scenario analytics solve a real blind spot",
                        "Whether cross-border data sharing feels risky",
                        "Whether dual-language explanation matters for usability and trust",
                    ],
                },
            },
        },
        {
            "label": "bank_skeptical_cautious_customer",
            "archetype": "銀行懷疑型",
            "guide": {
                "fixed": {
                    "age_range": "35-60",
                    "investable_assets_band": "HKD 500k-5m",
                    "persona_focus": "Bank-Skeptical Cautious Customer",
                },
                "preferred": {
                    "bank_relationship": "Uses banks out of necessity but keeps emotional distance from advisory messages.",
                    "investment_experience": "Has prior losses or regrets from past products and now looks for hidden incentives.",
                    "investment_products_held": ["fund", "stock", "possibly structured product or insurance from past cycle"],
                    "primary_financial_goal": "Avoid being sold the wrong thing again.",
                    "current_investment_decision_process": "Questions motives first, features second.",
                    "relationship_manager_usage": "Low unless forced by circumstance or trust is rebuilt slowly.",
                    "digital_banking_usage": "Moderate; will read carefully if the claim touches risk.",
                    "risk_understanding_level": "Sensitive to downside and suitability, but distrust changes how they interpret evidence.",
                    "interview_focus": [
                        "What transparency would make the model feel credible",
                        "Whether BlackRock branding helps or deepens conflict concerns",
                        "Whether the feature should stop at risk alerting rather than recommendations",
                    ],
                },
            },
        },
    ]

    generated_personas: list[dict[str, Any]] = []
    for offset, persona in enumerate(personas):
        persona_id = _persona_id(starting_id + offset)
        guide = _merge_guide(common_guide, persona["guide"])
        generated_personas.append(
            {
                "persona_id": persona_id,
                "label": persona["label"],
                "archetype": persona["archetype"],
                "guide": guide,
            }
        )

    return {
        "preset_name": HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
        "starting_id": starting_id,
        "persona_count": len(generated_personas),
        "personas": generated_personas,
    }


def build_v4_panel_preset(preset_name: str, *, starting_id: int = 1201) -> dict[str, Any]:
    if preset_name == HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK:
        return build_hk_retail_bank_portfolio_health_check_panel(starting_id=starting_id)
    raise ValueError(f"Unsupported V4 panel preset: {preset_name}")

