from __future__ import annotations

import copy
from typing import Any

"""
Legacy project-specific V5 panel presets.

These presets were created for earlier banking POC work and are not the default
or recommended representation of current V5 platform behaviour.

Current V5 direction:
- generate reusable personas from human_difference_axes and generic life context
- assemble interview panels from an existing V5 pool or dynamic sampling
- avoid fixed concept-shaped archetype sets as the default panel mechanism

This module remains only for legacy-compatible regeneration of prior project
artifacts.
"""


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

_HUMAN_DIFFERENCE_AXES_FIELDS = [
    "control_preference",
    "trust_style",
    "complexity_tolerance",
    "decision_tempo",
    "financial_attention_cadence",
    "relationship_to_money",
    "risk_orientation",
    "need_for_explanation",
    "life_load",
    "fragmentation_reality",
    "guidance_preference",
    "reflection_style",
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
        "required_profile_sections": ["human_difference_axes"],
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
            "persona_generation_rule": (
                "Build the person from ordinary life, values, routines, and human difference axes first. "
                "Do not pre-encode a single banking pain or assume the concept is relevant in the same way for every participant."
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
                    "control_preference": "Low to moderate; wants guidance and guardrails before acting alone.",
                    "trust_style": "Starts with borrowed trust from familiar brands or peers, then looks for simple proof.",
                    "complexity_tolerance": "Low; disengages when the explanation becomes too abstract or jargon-heavy.",
                    "decision_tempo": "Fast at idea discovery, slower at final commitment when real money is involved.",
                    "financial_attention_cadence": "Event-driven; checks more after market moves or social prompts than on a fixed schedule.",
                    "relationship_to_money": "Money feels tied to progress, independence, and not falling behind peers.",
                    "risk_orientation": "Curious about upside but emotionally sensitive to visible losses and embarrassment.",
                    "need_for_explanation": "High; learns through stories, simple comparisons, and concrete examples.",
                    "life_load": "Moderate; early-career work and social life compete for attention.",
                    "fragmentation_reality": "Low to moderate; small holdings split across one bank and perhaps one external app.",
                    "guidance_preference": "Self-serve first with optional human backup when uncertainty spikes.",
                    "reflection_style": "Answers through recent episodes and feelings rather than stable investing principles.",
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
                    "control_preference": "High; wants direct control over holdings, timing, and interpretation.",
                    "trust_style": "Evidence-first; respects competence more than relationship warmth.",
                    "complexity_tolerance": "High; comfortable with layered data if it improves decisions.",
                    "decision_tempo": "Fast once convinced the signal is useful enough.",
                    "financial_attention_cadence": "Frequent and routine; reviews positions as part of normal media and market consumption.",
                    "relationship_to_money": "Money is both a scorecard and a tool for autonomy.",
                    "risk_orientation": "Accepts volatility if they believe they understand the trade-off.",
                    "need_for_explanation": "Medium; prefers concise but information-dense explanations.",
                    "life_load": "Moderate; investing is a meaningful hobby as well as a financial activity.",
                    "fragmentation_reality": "High; assets are spread across bank, broker, and external research tools.",
                    "guidance_preference": "Independent by default; will use expert input only if it is additive and non-patronizing.",
                    "reflection_style": "Frames answers in comparisons, trade-offs, and process quality.",
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
                    "control_preference": "Moderate; wants to approve changes personally but values steady guidance.",
                    "trust_style": "Relationship-based with caution; familiarity matters, but fear of surprises is strong.",
                    "complexity_tolerance": "Low to moderate; accepts complexity only when clearly tied to safety or income continuity.",
                    "decision_tempo": "Slow and deliberate, especially when principal feels exposed.",
                    "financial_attention_cadence": "Calendar-driven; pays attention around maturities, cash-flow needs, and major headlines.",
                    "relationship_to_money": "Money is security, dignity, and peace of mind more than personal expression.",
                    "risk_orientation": "Loss-averse and drawdown-sensitive, especially late in the cycle.",
                    "need_for_explanation": "High; wants plain-language reassurance and concrete downside framing.",
                    "life_load": "Moderate; family, retirement planning, and health concerns can crowd out analytical attention.",
                    "fragmentation_reality": "Low to moderate; most holdings sit with known institutions, though product layers may still be opaque.",
                    "guidance_preference": "Human explanation first, app support second.",
                    "reflection_style": "Judges ideas through past bad periods, cash-flow consequences, and whether sleep would be affected.",
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
                    "control_preference": "Moderate; wants clarity before deciding, but does not need to micromanage every position.",
                    "trust_style": "Pragmatic; trusts systems that connect clearly to household outcomes.",
                    "complexity_tolerance": "Moderate; will handle detail if it helps protect family plans.",
                    "decision_tempo": "Measured; decisions compete with other family and work priorities.",
                    "financial_attention_cadence": "Routine but not constant; usually reviewed around bills, school planning, or annual check-ins.",
                    "relationship_to_money": "Money is a planning tool for stability and future options for the family.",
                    "risk_orientation": "Balanced but responsibility-heavy; downside matters because other people depend on the plan.",
                    "need_for_explanation": "High; wants translation from numbers to household consequences.",
                    "life_load": "High; work, caregiving, and coordination reduce spare cognitive bandwidth.",
                    "fragmentation_reality": "Moderate to high; family assets span banking, insurance, MPF, and sometimes spouse-held accounts.",
                    "guidance_preference": "Hybrid; wants self-serve visibility with occasional advisor interpretation.",
                    "reflection_style": "Explains choices through family trade-offs, timelines, and regret avoidance.",
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
                    "control_preference": "Moderate to high; delegates some analysis but not final judgment.",
                    "trust_style": "Credential-aware; trusts prestige and process if both feel coherent.",
                    "complexity_tolerance": "High; expects professional nuance and dislikes over-simplification.",
                    "decision_tempo": "Moderate; willing to wait for a proper explanation when ticket sizes are meaningful.",
                    "financial_attention_cadence": "Structured; reviews around scheduled RM meetings, market events, and portfolio reviews.",
                    "relationship_to_money": "Money is stewardship, status maintenance, and optionality for later life or family.",
                    "risk_orientation": "Selective; accepts complexity but expects it to be justified and monitored.",
                    "need_for_explanation": "Medium to high; wants a polished explanation with defendable logic.",
                    "life_load": "Moderate; professional and family commitments limit time, but expectations of service are high.",
                    "fragmentation_reality": "Moderate; assets may sit across multiple product wrappers and banking relationships.",
                    "guidance_preference": "Advisor-led discussion supported by strong analytics, not pure self-serve.",
                    "reflection_style": "Assesses whether advice feels consistent, professional, and aligned with prior experience.",
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
                    "control_preference": "High; needs to see and compare moving parts across markets directly.",
                    "trust_style": "Verification-oriented; trusts consolidation only if data lineage is clear.",
                    "complexity_tolerance": "High; willing to navigate multi-layer explanations if they match portfolio reality.",
                    "decision_tempo": "Variable; can move quickly on market shifts but takes time on cross-border setup choices.",
                    "financial_attention_cadence": "Frequent and trigger-based around FX, rates, and geopolitical developments.",
                    "relationship_to_money": "Money is flexibility across geographies, currencies, and family obligations.",
                    "risk_orientation": "Comfortable with complexity but wary of hidden transmission channels.",
                    "need_for_explanation": "Medium to high; wants plain language for summary and technical detail on demand.",
                    "life_load": "High; cross-border admin and family or business commitments add coordination strain.",
                    "fragmentation_reality": "Very high; holdings and records are spread across markets, currencies, and institutions.",
                    "guidance_preference": "Tool-led first, with specialist help only when edge cases matter.",
                    "reflection_style": "Talks in scenarios, jurisdictions, and practical constraints rather than product labels alone.",
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
                    "control_preference": "High; wants to retain veto power and interpret motives personally.",
                    "trust_style": "Defensive; trust starts low and must be rebuilt through transparency and consistency.",
                    "complexity_tolerance": "Moderate; will engage with detail if it helps spot hidden incentives.",
                    "decision_tempo": "Slow when counterparties are involved; assumes persuasion pressure may be present.",
                    "financial_attention_cadence": "Irregular but intense when something feels off or a recommendation appears.",
                    "relationship_to_money": "Money is hard-won and tied to self-protection after prior regret.",
                    "risk_orientation": "Cautious in both market risk and institutional risk.",
                    "need_for_explanation": "High; wants to know not just the answer but whose interests shape the answer.",
                    "life_load": "Moderate; distrust itself consumes attention and extends decision time.",
                    "fragmentation_reality": "Moderate; may keep assets spread out partly to avoid over-dependence on one institution.",
                    "guidance_preference": "Prefers neutral tools over relationship-driven advice.",
                    "reflection_style": "Returns to prior disappointments and consistency checks when evaluating new claims.",
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


def build_v5_panel_preset(preset_name: str, *, starting_id: int = 1201) -> dict[str, Any]:
    if preset_name == HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK:
        return build_hk_retail_bank_portfolio_health_check_panel(starting_id=starting_id)
    raise ValueError(
        f"Unsupported legacy V5 panel preset: {preset_name}. "
        "Current V5 no longer treats fixed project-specific archetype panels as the default path."
    )

