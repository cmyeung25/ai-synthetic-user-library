from __future__ import annotations

import copy
import random
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.personas.seed_coherence import LIFE_STAGE_OPTIONS, PURCHASE_AUTHORITY_TYPES
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"

PROMPT_VERSIONS = [
    "persona-biography/v2.md",
    "research-kernel/v2.md",
    "persona-skill/v2.md",
    "persona-quality-auditor/v2.md",
]

RAW_ENUM_TOKENS = {
    "tool_heavy",
    "committee_slow",
    "regional_sea_service_ops",
    "hong_kong_smb",
    "taiwan_knowledge_work",
    "new_territories_operator",
    "needs_social_proof",
    "adopts_after_peer_signal",
    "visible_trial",
    "case_studies_required",
    "peer_reference_required",
    "phone-plus-laptop",
    "smartphone-first",
    *LIFE_STAGE_OPTIONS,
    *PURCHASE_AUTHORITY_TYPES,
}

RENDERED_ARTIFACT_FILENAMES = (
    "persona.md",
    "biography.md",
    "research_kernel.md",
    "persona.skill.md",
)


def _stable_rng(persona: PersonaSkill, random_seed: int | None = None) -> random.Random:
    if random_seed is not None:
        return random.Random(random_seed)
    persona_id = persona.profile.basic_identity.get("synthetic_user_id", "su_0000")
    numeric = int(str(persona_id).split("_")[-1])
    age = int(persona.profile.basic_identity.get("age", 0))
    return random.Random(1000 + numeric * 17 + age * 31)


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def prompt_path(prompt_version: str) -> Path:
    return PROMPTS_ROOT / prompt_version


def load_v2_prompt_texts() -> dict[str, str]:
    return {
        prompt_version: prompt_path(prompt_version).read_text(encoding="utf-8").strip()
        for prompt_version in PROMPT_VERSIONS
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _current_stage_end(age: int) -> int:
    if age < 10:
        return 9
    if age < 20:
        return 19
    if age < 30:
        return 29
    if age < 40:
        return 39
    if age < 50:
        return 49
    if age < 60:
        return 59
    if age < 70:
        return 69
    return 79


def _decade_ranges_for_age(age: int) -> list[tuple[str, int, int]]:
    ranges = [
        ("0-9", 0, 9),
        ("10-19", 10, 19),
        ("20-29", 20, 29),
        ("30-39", 30, 39),
        ("40-49", 40, 49),
        ("50-59", 50, 59),
        ("60-69", 60, 69),
        ("70+", 70, 79),
    ]
    limit = _current_stage_end(age)
    return [item for item in ranges if item[1] <= limit]


def _workflow_phrase(seed: dict[str, Any]) -> str:
    return {
        "ad_hoc": "still held together by memory, message search, and ad-hoc checklists",
        "repeatable": "repeatable enough to function, but still dependent on personal discipline",
        "documented": "documented well enough that handoffs matter and exceptions stand out",
        "tool_heavy": "spread across many tools, which makes duplication and drift easy",
    }.get(str(seed.get("workflow_maturity", "")), "held together by practical routines")


def _decision_speed_phrase(seed: dict[str, Any]) -> str:
    return {
        "fast": "moves quickly once the benefit is concrete",
        "deliberate": "takes time to compare trade-offs before committing",
        "committee_slow": "gets slowed down by comparison, review, and the need to justify the choice to others",
    }.get(str(seed.get("decision_speed", "")), "does not rush decisions")


def _locale_texture(identity: dict[str, Any]) -> str:
    location = str(identity.get("location", "their city"))
    living_area = str(identity.get("living_area", "urban"))
    if living_area == "urban_core":
        return f"{location} pace, dense choices, and constant comparison with other tools and services nearby"
    if living_area == "regional":
        return f"{location} routines, where convenience matters but people still notice whether a product feels grounded in real life"
    return f"{location} everyday routines, where practicality and trust travel together"


def _household_context_phrase(identity: dict[str, Any]) -> str:
    family_structure = str(identity.get("family_structure", "shared household"))
    mapping = {
        "living alone": "living alone",
        "living with partner": "sharing daily routines with a partner",
        "living with partner and one child": "balancing partner and child routines at home",
        "living with parents": "sharing a home with parents",
        "living with roommates": "coordinating around roommates and shared space",
        "single parent with one child": "handling parent responsibilities without much slack",
        "multi-generational household": "living in a multi-generational household",
    }
    return mapping.get(family_structure, family_structure)


def _occupation_focus(occupation: str) -> str:
    lowered = occupation.lower()
    if "program manager" in lowered:
        return "keeping projects, requests, and follow-up aligned across people who are rarely in the same context at the same time"
    if "operations manager" in lowered:
        return "keeping recurring operations dependable while handling exceptions before they become visible failures"
    if "manager" in lowered:
        return "making coordination visible enough to trust without creating more admin"
    if "founder" in lowered or "owner" in lowered:
        return "protecting momentum while avoiding tools that create new maintenance overhead"
    return "keeping work dependable when attention is split across multiple obligations"


def _life_stage_pressure(persona: PersonaSkill) -> str:
    age = int(persona.profile.basic_identity.get("age", 0))
    if age < 30:
        return "still shaping adult routines while trying not to look disorganised"
    if age < 45:
        return "managing stacked commitments that compete for the same attention"
    if age < 60:
        return "protecting time and energy more deliberately because wasted effort is easier to spot now"
    return "being selective about what deserves a place in a limited routine"


def _life_arc_summary(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    values = persona.profile.values
    seed = asdict(persona.seed)
    core_values = ", ".join(values.get("core_values", [])[:3])
    return (
        f"{identity['name']} is a {identity['age']}-year-old {identity['occupation']} in {identity['location']}. "
        f"Their life has been shaped less by dramatic turning points than by repeated lessons about reliability, "
        f"bandwidth, and how small operational failures create social cost. They grew into someone who values "
        f"{core_values}, and who evaluates new products through the lens of whether they reduce weekly friction "
        f"without introducing new trust, privacy, or coordination debt. Their current life is { _workflow_phrase(seed) }, "
        f"so even interesting products must survive a practical test: can this fit real routines instead of ideal ones?"
    )


def _build_life_story_v2(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    seed = asdict(persona.seed)
    pain_points = persona.profile.problem_context.get("active_pain_points", [])
    trust_needs = persona.decision_policy.get("trust_requirements", [])
    hidden_needs = persona.profile.life_story.get("hidden_needs", [])
    occupation_focus = _occupation_focus(str(identity.get("occupation", "")))
    household_context = _household_context_phrase(identity)
    schedule_pressure = str(seed.get("schedule_pressure", "medium"))
    decision_speed = _decision_speed_phrase(seed)
    life_stage_pressure = _life_stage_pressure(persona)
    if schedule_pressure == "high":
        daily_routine = (
            "Most weekdays start with WhatsApp, calendar, and follow-up triage before deeper work has a chance to settle. "
            f"In {identity['occupation']} work, they spend a large share of attention on {occupation_focus}. "
            "They are most open to a new product right after an avoidable coordination miss or a messy handoff, "
            "and least open when setup assumes a clean block of focus at the end of the day."
        )
    elif schedule_pressure == "low":
        daily_routine = (
            "A normal day starts with carrying forward yesterday's loose ends, then deciding which operational details actually need action today. "
            f"Their work still revolves around {occupation_focus}, but the pressure shows up more as accumulated drag than as visible chaos. "
            "They are willing to examine a product carefully, yet patience disappears if the path from trial to usefulness stays abstract."
        )
    else:
        daily_routine = (
            "A normal day starts with message triage, then a steady attempt to protect one or two useful blocks of attention. "
            f"The work centers on {occupation_focus}, so new tools are judged by whether they simplify follow-up instead of rearranging it. "
            "They are most open to new products when a pain point is concrete, and least open when setup asks for uninterrupted focus."
        )
    return {
        "childhood_background": (
            f"Grew up around ordinary conversations about responsibility, money, and keeping commitments in {_locale_texture(identity)}. "
            "The lasting lesson was that practical follow-through matters more than polished intentions."
        ),
        "education_journey": (
            f"Education felt useful when it translated into competence, not status alone. "
            f"They learned to trust explanations that connect clearly to day-to-day use, which still shapes how they listen to product claims."
        ),
        "career_path": (
            f"Moved into {identity['occupation']} work because it rewards {occupation_focus}, "
            f"not because the role sounds glamorous. Over time they learned that tool choice changes how much hidden "
            f"coordination work lands on them and how visible that burden becomes to other people."
        ),
        "family_story": (
            f"{household_context.capitalize()} shapes time, patience, and what kinds of product promises feel realistic. "
            f"At this life stage they are {life_stage_pressure}, so even stable home routines do not create unlimited attention."
        ),
        "current_daily_routine": daily_routine,
        "recent_life_events": [
            "reviewed recent software spend more critically than before",
            "noticed that scattered follow-up work is costing more attention than expected",
            f"became more skeptical of products that sound polished but do not replace an existing step because their decision style {decision_speed}",
        ],
        "frustrations": _dedupe(
            pain_points
            + [
                "having to mentally translate vague product claims into real workflow impact",
                "losing trust when a tool looks easy in a demo but awkward in ordinary use",
            ]
        ),
        "hidden_needs": _dedupe(
            hidden_needs
            + [
                "wants a product to make them feel more composed, not more monitored",
                "needs proof that the product understands ordinary human inconsistency",
                f"responds better to trust cues like {', '.join(trust_needs[:2])} than to hype",
                f"wants a tool that respects the social cost of dropped follow-up in {identity['occupation']} work",
            ]
        ),
    }


def _build_decade_chapter(persona: PersonaSkill, age_range: str, start: int, end: int) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    seed = asdict(persona.seed)
    locale_texture = _locale_texture(identity)
    household = str(identity.get("family_structure", "household"))
    stage_title = {
        "0-9": "Ordinary rules, ordinary signals",
        "10-19": "Learning what competence looks like",
        "20-29": "Early independence under practical pressure",
        "30-39": "Commitments become structural",
        "40-49": "Trade-offs become visible",
        "50-59": "Protection of time becomes sharper",
        "60-69": "Selectivity becomes a strategy",
        "70+": "Only clear value survives attention",
    }[age_range]

    if age_range == "0-9":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": f"Early life was shaped by {household} routines and {locale_texture}.",
            "key_experiences": [
                "noticed which adults followed through and which only spoke confidently",
                "learned that small household frictions create stress long before anyone names them",
            ],
            "relationships": "Trust formed around consistency, not charisma.",
            "money_lessons": "Money talk was practical and tied to usefulness, waste, and what could wait.",
            "technology_exposure": "Technology was present as a tool, not as an identity.",
            "trust_lessons": "Promises became believable only when matched by observable follow-through.",
            "identity_development": "Started seeing reliability as socially valuable.",
            "emotional_imprint": "Calm systems felt safer than noisy improvisation.",
            "beliefs_formed": ["practical help matters more than impressive language"],
            "current_product_research_impact": "Still notices whether a product sounds helpful or merely polished.",
            "formative_level": "medium",
        }
    if age_range == "10-19":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "School, peers, and early self-management created the first sustained comparison between effort and reward.",
            "key_experiences": [
                "saw that some systems reward organisation while others simply create more admin",
                "learned to adapt language and presentation to context",
            ],
            "relationships": "Peer judgement mattered, but so did avoiding avoidable embarrassment.",
            "money_lessons": "Started distinguishing between things that feel valuable and things that merely feel current.",
            "technology_exposure": "Digital habits formed around convenience, messaging, and what fit ordinary attention spans.",
            "trust_lessons": "Became more skeptical of claims that look universal but fail in lived detail.",
            "identity_development": "Began developing an internal standard for what feels credible.",
            "emotional_imprint": "Overpromised simplicity became memorable in a bad way.",
            "beliefs_formed": ["clarity is a trust signal", "friction hides in the details people skip over"],
            "current_product_research_impact": "Still tests whether a product respects attention and dignity.",
            "formative_level": "medium",
        }
    if age_range == "20-29":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "Early adult life made time, cost, and coordination feel concrete rather than abstract.",
            "key_experiences": [
                "learned that adoption work often gets quietly pushed onto the busiest person",
                "became more aware of the difference between curiosity and sustainable use",
            ],
            "relationships": "Work, family, and partner expectations started colliding in ordinary schedule decisions.",
            "money_lessons": "Recurring costs started to feel different from one-off purchases because every month needs re-justification.",
            "technology_exposure": "Tried enough tools to see that demos hide maintenance cost.",
            "trust_lessons": "Began trusting products that admit limits more than those that sound frictionless.",
            "identity_development": "Identity became tied to looking dependable under messy conditions.",
            "emotional_imprint": "Messy handoffs and dropped follow-up became more costly than inconvenience alone.",
            "beliefs_formed": ["good tools reduce cognitive residue", "switching cost is real even when vendors pretend otherwise"],
            "current_product_research_impact": "Makes them careful about onboarding, switching, and whether a tool truly replaces anything.",
            "formative_level": "high",
        }
    if age_range == "30-39":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "Responsibilities became layered enough that time and attention had to be defended deliberately.",
            "key_experiences": [
                "saw that tools affect relationship dynamics when they expose or hide disorder",
                "became more selective about what deserves another log-in, inbox, or dashboard",
            ],
            "relationships": "Home and work pressures stopped being separate in any clean way.",
            "money_lessons": "Value became tied to recovery of time, reduced anxiety, and fewer avoidable mistakes.",
            "technology_exposure": "Technology choices started reflecting role complexity rather than novelty.",
            "trust_lessons": "Products earned trust by being specific about data, workflow fit, and failure modes.",
            "identity_development": "Became more protective of personal standards around competence and privacy.",
            "emotional_imprint": "Anything that multiplies maintenance feels worse than something merely imperfect.",
            "beliefs_formed": ["clarity without extra admin is rare and valuable"],
            "current_product_research_impact": "More likely to ask hard questions about setup, handoff, and hidden labour.",
            "formative_level": "high",
        }
    if age_range == "40-49":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "Experience made patterns easier to spot, but patience for vague solutions thinner.",
            "key_experiences": [
                "learned to distinguish useful efficiency from performative optimisation",
                "became less willing to subsidise bad product design with personal discipline",
            ],
            "relationships": "Trust widened for people who are concrete and narrowed for people who oversell.",
            "money_lessons": "Spending became easier to justify when risk and support are obvious, not when feature volume is high.",
            "technology_exposure": "Technology became a sorting tool: what deserves adoption versus what stays interesting but irrelevant.",
            "trust_lessons": "Serious products should withstand comparison, not avoid it.",
            "identity_development": "Confidence comes more from judgement than from trying everything.",
            "emotional_imprint": "Tolerance for hidden complexity dropped.",
            "beliefs_formed": ["not every interesting tool deserves a place in real life"],
            "current_product_research_impact": "Sharper at spotting founder optimism that confuses understanding with adoption.",
            "formative_level": "medium",
        }
    if age_range == "50-59":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "The question shifted from whether a tool can work to whether it earns a place in a finite routine.",
            "key_experiences": [
                "became more vocal about hidden friction",
                "noticed that many products optimise for demos more than staying power",
            ],
            "relationships": "Selective sharing became a form of self-protection, not distance.",
            "money_lessons": "Good spending feels grounded, calm, and explainable.",
            "technology_exposure": "Keeps useful tools, ignores feature theatre.",
            "trust_lessons": "Believes good products should still make sense under fatigue.",
            "identity_development": "Less interested in appearing current, more interested in staying effective.",
            "emotional_imprint": "Bad tools feel disrespectful of lived complexity.",
            "beliefs_formed": ["stability is a product benefit, not a boring extra"],
            "current_product_research_impact": "Pushes founders hardest on retention and real-life fit.",
            "formative_level": "medium",
        }
    if age_range == "60-69":
        return {
            "age_range": age_range,
            "chapter_title": stage_title,
            "life_context": "Attention became more intentionally allocated, and novelty had to justify itself quickly.",
            "key_experiences": [
                "became more willing to say no early",
                "preferred tools that lower noise without requiring identity performance",
            ],
            "relationships": "Values calm trust over impressive positioning.",
            "money_lessons": "Wants spending to feel deliberate rather than constantly defended.",
            "technology_exposure": "Adopts when clear usefulness outruns the mental cost of switching.",
            "trust_lessons": "Trust grows through respect for context, not through intensity of claims.",
            "identity_development": "Selectivity becomes part of competence.",
            "emotional_imprint": "Frustration with unnecessary complexity hardens into refusal.",
            "beliefs_formed": ["a tool should fit the person, not demand performance from them"],
            "current_product_research_impact": "Useful for testing clarity, trust, and friction tolerance.",
            "formative_level": "medium",
        }
    return {
        "age_range": age_range,
        "chapter_title": stage_title,
        "life_context": "Attention is reserved for what feels genuinely useful.",
        "key_experiences": ["keeps only routines that still feel worth carrying"],
        "relationships": "Trust stays local, earned, and specific.",
        "money_lessons": "Comfort comes from explainable value.",
        "technology_exposure": "Technology must justify itself quickly.",
        "trust_lessons": "Clarity beats hype.",
        "identity_development": "Identity is less about experimentation and more about fit.",
        "emotional_imprint": "Low patience for noise.",
        "beliefs_formed": ["only lasting usefulness deserves space"],
        "current_product_research_impact": "Strong filter for fluff.",
        "formative_level": "low",
    }


def _build_canonical_biography(persona: PersonaSkill) -> dict[str, Any]:
    age = int(persona.profile.basic_identity.get("age", 0))
    chapters = [
        _build_decade_chapter(persona, age_range, start, end)
        for age_range, start, end in _decade_ranges_for_age(age)
    ]
    formative_events = [
        {
            "age_range": chapter["age_range"],
            "event_summary": chapter["chapter_title"],
            "impact": chapter["current_product_research_impact"],
            "formative_level": chapter["formative_level"],
        }
        for chapter in chapters
        if chapter["formative_level"] in {"high", "medium"}
    ]
    identity = persona.profile.basic_identity
    household_context = _household_context_phrase(identity)
    current_identity = (
        f"{identity['name']} sees themselves as someone who should be able to keep commitments visible, "
        f"avoid preventable friction, and stay credible both in {identity['occupation']} work and in {household_context}."
    )
    return {
        "life_arc_summary": _life_arc_summary(persona),
        "decade_timeline": chapters,
        "formative_events": formative_events,
        "current_identity": current_identity,
        "current_daily_life": persona.profile.life_story.get("current_daily_routine", ""),
        "money_lessons": "Recurring cost, maintenance burden, and explainability all matter more than surface excitement.",
        "technology_exposure": "Technology is welcome when it clearly reduces noise; it becomes suspect when it adds invisible upkeep.",
        "trust_lessons": "Specificity, reversibility, and respect for context build trust faster than grand claims.",
        "family_relationship_context": persona.profile.life_story.get("family_story", ""),
        "work_study_development": persona.profile.life_story.get("career_path", ""),
        "sensitive_identity_or_social_context": (
            "Sensitive topics matter most when they affect privacy, dignity, public expression, and whether the product assumes too much."
        ),
        "life_stage_product_research_effect": (
            "Each life stage increased sensitivity to hidden effort, misleading simplicity, and the gap between curiosity and adoption."
        ),
        "cross_domain_product_reaction_model": (
            "Across domains, this persona first asks what problem is being removed, what trust cost is being introduced, "
            "and whether the product respects ordinary inconsistency."
        ),
    }


def _build_domain_fit(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    seed = asdict(persona.seed)
    best_fit = [
        "B2B workflow automation",
        "workflow or productivity product",
    ]
    if persona.profile.technology_profile.get("ai_familiarity") in {"medium", "high"}:
        best_fit.append("AI productivity tools")
    if seed.get("caregiving_load") in {"medium", "high"} or "child" in str(identity.get("family_structure", "")):
        best_fit.append("family operations")
        best_fit.append("education products")
    if seed.get("cash_flow_volatility") in {"medium", "high"} or persona.profile.economic_profile.get("price_sensitivity") == "low":
        best_fit.append("consumer finance")
    if seed.get("panel_role") == "privacy_sensitive":
        best_fit.append("identity-sensitive products")
    weak_fit = ["luxury aspiration products"] if persona.profile.economic_profile.get("price_sensitivity") != "high" else ["high-end hobby gear"]
    panel_roles = _dedupe(
        [
            seed.get("panel_role", ""),
            "skeptic" if seed.get("trust_threshold") != "needs_trial" else "trial-seeker",
            "privacy_sensitive" if seed.get("privacy_risk_tolerance") == "low" else "mainstream_buyer",
            "budget_constrained" if persona.profile.economic_profile.get("price_sensitivity") == "low" else "workflow_buyer",
        ]
    )
    return {
        "best_fit_domains": _dedupe(best_fit),
        "weak_fit_domains": weak_fit,
        "sample_when": [
            "testing whether a product survives practical scrutiny",
            "checking if clear value turns into trial intent",
            "evaluating friction, trust, pricing, and adoption realism",
        ],
        "avoid_sampling_when": [
            "you need a clinical or regulated professional judgement",
            "you need niche enthusiast depth outside the persona's lived context",
        ],
        "panel_roles": panel_roles,
    }


def _build_pricing_logic(persona: PersonaSkill) -> dict[str, Any]:
    economic = persona.profile.economic_profile
    seed = asdict(persona.seed)
    price_level = economic.get("price_sensitivity", "medium")
    max_band = {
        "low": "$8-15/month personal, or one-off purchases that feel safer than recurring spend",
        "medium": "$15-35/month personal when weekly value is obvious",
        "high": "$35-80/month if the product clearly replaces existing work or is reimbursable",
    }.get(price_level, "$15-35/month personal when weekly value is obvious")
    if seed.get("cash_flow_volatility") == "high":
        max_band = "$10-25/month with a clean monthly exit, unless the spend protects a clearly expensive recurring problem"
    elif economic.get("disposable_income") == "upper_middle" and economic.get("switching_cost") == "high":
        max_band = "$20-45/month when the tool reduces coordination mistakes or protects reputation, not just time"
    return {
        "price_sensitivity_level": price_level,
        "personal_payment_comfort": (
            "Will pay personally once the product removes a repeating annoyance, not just when it sounds clever."
        ),
        "work_payment_comfort": (
            "More comfortable when the price can be justified in time saved, error reduction, or handoff quality."
        ),
        "preferred_pricing_model": "short free trial followed by a clear monthly plan with an easy exit",
        "free_trial_required": True,
        "preferred_trial_length": "7-14 days with one concrete workflow to test",
        "subscription_fatigue": "Not against subscriptions in principle, but suspicious of anything that becomes another forgotten monthly line item.",
        "annual_plan_resistance": "High unless the product has already earned routine use and trust.",
        "approval_needed_if": (
            "The product affects shared workflow, touches sensitive data, or costs enough that the justification must be explained to someone else."
        ),
        "maximum_comfortable_price_band": max_band,
        "pricing_objection": "If I still have to keep my old workaround, this price feels like paying for extra admin.",
        "what_makes_price_feel_fair": "Specific value, visible reduction in friction, and pricing that matches the size of the problem solved.",
        "what_makes_price_feel_suspicious": "Complicated tiers, aggressive annual lock-in, and promises that sound bigger than the actual first-week experience.",
    }


def _build_workflow_adoption_model(persona: PersonaSkill) -> dict[str, Any]:
    tech = persona.profile.technology_profile
    seed = asdict(persona.seed)
    low_setup = tech.get("tech_savviness") == "low" or seed.get("schedule_pressure") == "high"
    return {
        "must_replace_existing_step": True,
        "dashboard_tolerance": "low" if tech.get("app_fatigue") == "high" else "medium",
        "setup_tolerance": "low" if low_setup else "medium",
        "data_connection_concern": "high" if seed.get("privacy_risk_tolerance") == "low" else "medium",
        "first_week_success_condition": [
            "the first use case is obvious without a long walkthrough",
            "no hidden configuration appears after the initial setup",
            "the product reduces one real follow-up task quickly",
        ],
        "drop_off_triggers": [
            "setup that has to be restarted after interruption",
            "too many choices before value is visible",
            "another dashboard with nothing clearly replaced",
        ],
        "integration_expectations": [
            "should fit messaging-heavy routines",
            "should not require perfect data hygiene on day one",
            "should explain what happens to connected data in plain language",
        ],
        "habit_change_barriers": [
            "already has messy but familiar workarounds",
            "does not want a tool that exposes disorganisation without helping fix it",
            f"current routine is {_workflow_phrase(seed)}",
        ],
    }


def _build_product_reaction_rules(persona: PersonaSkill) -> dict[str, Any]:
    trust_requirements = persona.decision_policy.get("trust_requirements", [])
    proof_requirements = persona.decision_policy.get("proof_requirements", [])
    return {
        "first_checks": [
            "what exact step disappears if this works",
            "how hard it is to try without reorganising everything",
            "what data or behaviour the product expects too early",
        ],
        "positive_signals": [
            "concrete examples tied to ordinary routines",
            "clear boundaries about what the product does not do",
            "evidence that the first week can produce a visible win",
        ],
        "negative_signals": [
            "vague founder certainty",
            "claims that collapse curiosity, trial, and payment into one step",
            "design or copy that sounds more impressed with itself than with the user's constraints",
        ],
        "questions_they_would_ask": [
            "What would I stop doing if I used this?",
            "What does setup look like on a tired weekday, not in a polished demo?",
            "What would make me regret connecting real data here?",
        ],
        "claims_they_distrust": [
            "frictionless for everyone",
            "AI that understands your whole life immediately",
            "saves hours without showing where those hours come from",
        ],
        "evidence_that_changes_their_mind": _dedupe(proof_requirements + trust_requirements),
        "likely_false_positive_interest": (
            "May sound positive when the concept is understandable, even if they are only acknowledging relevance rather than signalling intent."
        ),
        "difference_between_curiosity_and_purchase": (
            "Curiosity means the problem statement lands. Trial intent appears only when the path feels bounded. Payment intent appears only after the product proves it can replace effort rather than add another layer."
        ),
    }


def _build_cross_domain_product_reaction_model(persona: PersonaSkill) -> dict[str, Any]:
    pricing = _build_pricing_logic(persona)
    trust = persona.decision_policy.get("trust_requirements", [])
    objections = persona.profile.behavior_profile.get("decision_blockers", [])

    def block(first_question: str, positive: str, negative: str, trust_requirement: str, objection: str) -> dict[str, str]:
        return {
            "first_question": first_question,
            "positive_trigger": positive,
            "negative_trigger": negative,
            "trust_requirement": trust_requirement,
            "likely_objection": objection,
        }

    trust_requirement = ", ".join(trust[:2]) if trust else "clear practical proof"
    likely_objection = objections[0] if objections else "I still do not know what would change in real life."
    return {
        "generic_new_product": block(
            "What real-life friction disappears if this works?",
            "A narrow use case that is immediately understandable.",
            "A big promise with no obvious first step.",
            trust_requirement,
            likely_objection,
        ),
        "ai_product": block(
            "What does the AI actually do without me babysitting it?",
            "AI that reduces repetitive follow-up rather than replacing judgment theatrically.",
            "AI framed like magic instead of a bounded tool.",
            "plain language about what the model sees, remembers, and gets wrong",
            "I do not want to trade clarity for cleverness.",
        ),
        "subscription_product": block(
            "Why should this become a recurring cost instead of a one-off tool?",
            "Pricing that matches a repeated, measurable benefit.",
            "Recurring spend before routine value exists.",
            "a credible first-week win and an easy exit path",
            pricing["pricing_objection"],
        ),
        "family_or_household_product": block(
            "Does this lower coordination stress or just document it?",
            "Makes shared tasks more visible without adding another place to check.",
            "Assumes every household has the same rhythm or privacy comfort.",
            "respect for household boundaries and uneven attention",
            "This looks like more family admin disguised as help.",
        ),
        "health_or_wellbeing_product": block(
            "Is this supportive, or is it quietly judgmental?",
            "Specific support that respects ordinary inconsistency.",
            "Language that sounds moralising, diagnostic, or guilt-based.",
            "clear limits, privacy respect, and emotionally neutral guidance",
            "I do not want a wellbeing product that makes me feel monitored.",
        ),
        "financial_product": block(
            "What downside am I accepting if I trust this?",
            "Transparent trade-offs and explainable value.",
            "Hidden incentives or copy that hides cost and risk.",
            "traceable logic and plain-English risk explanations",
            "If I cannot explain the financial logic, I will not trust it.",
        ),
        "education_or_child_product": block(
            "Is this actually useful, or is it just respectable-looking?",
            "Specific developmental or practical value that fits real routines.",
            "Parent guilt marketing or impossible consistency demands.",
            "evidence that the product respects family time and different learning styles",
            "I do not want to pay for anxiety dressed up as support.",
        ),
        "workflow_or_productivity_product": block(
            "What existing step does this replace on a busy day?",
            "Shows that it reduces follow-up, re-entry, or missed context.",
            "Adds another inbox, dashboard, or ritual.",
            "a workflow demo grounded in interruption, not ideal focus time",
            "I have seen too many products that add process without removing work.",
        ),
        "identity_sensitive_product": block(
            "Does this product let me keep control over what I disclose?",
            "Inclusive language with optional disclosure and respectful defaults.",
            "Forced labeling, shallow representation, or public-facing risk.",
            "control, optionality, and non-performative respect",
            "If the product decides too much about me before I speak, I pull back.",
        ),
        "high_friction_onboarding": block(
            "Why does this need so much from me before it proves anything?",
            "A staged setup where the first useful moment comes early.",
            "Long setup before even one credible result.",
            "proof that the product understands fatigue and interruption",
            "If onboarding already feels like project work, I will likely stop.",
        ),
    }


def _build_identity_and_inclusion_reaction(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "inclusive_language_expectation": "Wants respectful language that does not assume one default user or one tidy life situation.",
        "representation_signals_that_help": [
            "examples that show more than one type of user context",
            "optional rather than forced identity labeling",
            "plain wording around privacy and control",
        ],
        "representation_turnoffs": [
            "performative inclusivity with no practical control",
            "forced demographic assumptions in onboarding",
            "marketing that sounds like it wants praise more than trust",
        ],
        "when_they_speak_up": "More likely to object when exclusion is obvious and actionable.",
        "when_they_go_quiet": "More likely to disengage than argue if the product feels subtly misaligned or patronising.",
    }


def _build_interest_layer(persona: PersonaSkill, rng: random.Random) -> dict[str, Any]:
    occupation = str(persona.profile.basic_identity.get("occupation", ""))
    family_structure = str(persona.profile.basic_identity.get("family_structure", ""))
    schedule_pressure = str(persona.seed.schedule_pressure)
    age = int(persona.profile.basic_identity.get("age", 0))
    tech_savviness = str(persona.profile.technology_profile.get("tech_savviness", "medium"))
    primary = [
        "comparison-shopping practical tools",
        "food or coffee places chosen more for routine comfort than trend-chasing",
    ]
    if age < 35:
        primary.append("short-form productivity experiments")
    else:
        primary.append("maintenance-minded routine improvements")
    if "manager" in occupation or "program" in occupation:
        primary.append("observing how people coordinate messy work in real life")
    if "operations" in occupation.lower():
        primary.append("spotting where recurring process failures start")
    secondary = ["walks with a podcast", "light personal finance tracking", "messaging-based planning with friends or family"]
    low_energy = ["scrolling product reviews without purchasing", "tidying one corner instead of the whole space"]
    if tech_savviness == "high":
        low_energy.append("YouTube explainers during small breaks")
    else:
        low_energy.append("watching a few practical demos before deciding whether a tool is worth more reading")
    social = ["small catch-ups over food", "group chats tied to practical logistics", "occasionally sharing tool recommendations when they actually worked"]
    private = ["keeping personal notes", "quietly testing new workflows before mentioning them", "reading comparison tables longer than they admit"]
    aspirational = ["a hobby that feels restorative enough to justify real time", "a cleaner weekly reset routine", "using technology more intentionally instead of reactively"]
    abandoned = ["systems that were fun to set up but too demanding to maintain", "at least one hobby that lost momentum when ordinary responsibilities increased"]
    claim_but_rarely_do = ["trying to keep every digital note neatly organised"]
    if "child" in family_structure:
        secondary.append("family planning that tries to stay calm rather than perfect")
        aspirational.append("having uninterrupted leisure time without needing to earn it first")
    if schedule_pressure == "high":
        low_energy.append("saving interesting links for later and rarely revisiting all of them")
    if age >= 50:
        secondary.append("keeping a few dependable routines rather than constantly trying new ones")
        aspirational.append("a leisure habit that does not turn into another optimisation project")
    if tech_savviness != "high":
        abandoned.append("some software workflows that promised efficiency but never felt worth maintaining")
    interest_depth = [
        {
            "interest_name": "comparison-shopping practical tools",
            "depth_level": "moderate",
            "why_it_matters": "It gives them a sense of control before spending time or money.",
            "how_it_shapes_purchase_behaviour": "They notice trade-off tables, reviews, and plain-English product boundaries.",
            "related_products_they_notice": ["productivity apps", "home or work organisation tools", "budget-aware subscriptions"],
            "related_products_they_ignore": ["pure novelty apps with no obvious sustained use"],
        },
        {
            "interest_name": "quiet workflow experimentation",
            "depth_level": "identity-level" if persona.profile.technology_profile.get("tech_savviness") == "high" else "moderate",
            "why_it_matters": "It lets them feel slightly more capable before they explain anything to others.",
            "how_it_shapes_purchase_behaviour": "They are open to trials but allergic to tools that punish imperfect adoption.",
            "related_products_they_notice": ["AI helpers", "automation tools", "templated planning systems"],
            "related_products_they_ignore": ["tools that demand immediate team-wide rollout"],
        },
    ]
    return {
        "primary_interests": _dedupe(primary),
        "secondary_interests": _dedupe(secondary),
        "low_energy_hobbies": _dedupe(low_energy),
        "social_hobbies": _dedupe(social),
        "private_hobbies": _dedupe(private),
        "aspirational_hobbies": _dedupe(aspirational),
        "abandoned_hobbies": _dedupe(abandoned),
        "hobbies_they_claim_to_have_but_rarely_do": _dedupe(claim_but_rarely_do),
        "interest_depth": interest_depth,
    }


def _build_media_diet(persona: PersonaSkill) -> dict[str, Any]:
    tech = persona.profile.technology_profile
    age = int(persona.profile.basic_identity.get("age", 0))
    if tech.get("tech_savviness") == "low":
        social_platforms = ["WhatsApp", "Facebook groups"]
    elif age >= 50:
        social_platforms = ["WhatsApp", "LinkedIn", "YouTube search"]
    else:
        social_platforms = ["WhatsApp", "LinkedIn"]
    return {
        "news_sources": ["search-driven reading", "a small number of local or regional business/news sources"],
        "social_platforms": social_platforms,
        "youtube_or_video_habits": ["short explainers", "comparison videos when the purchase feels close"],
        "podcasts_or_audio": ["practical interviews", "topic-specific episodes during commute or chores"],
        "newsletters_or_blogs": ["occasionally saved articles, usually when a problem already feels active"],
        "offline_information_sources": ["friends who actually used the tool", "coworker or partner feedback", "observing how people around them cope"],
        "trusted_experts": ["people who describe trade-offs plainly", "operators who admit limits", "peers with similar routines"],
        "ignored_sources": ["overexcited launch threads", "empty thought-leadership language", "reviews that sound copied from marketing"],
        "content_style_preference": "prefers concrete examples, comparison points, and plain language over visionary storytelling",
        "attention_span_pattern": "willing to go deep only after the product earns relevance; otherwise filters quickly",
        "how_they_verify_claims": "Checks whether the claim survives comparison, real constraints, and the first-week experience.",
        "how_they_discover_new_products": "Usually through search, peer mention, and noticing repeated pain rather than random browsing.",
    }


def _build_daily_micro_behaviours(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    occupation_focus = _occupation_focus(str(identity.get("occupation", "")))
    schedule_pressure = str(persona.seed.schedule_pressure)
    if schedule_pressure == "high":
        morning_routine = "Usually checks messages before breakfast or before fully settling in, because unresolved follow-up can hijack the whole morning."
        work_start = f"Begins with triage rather than ideal planning, then tries to reclaim one clear next step in work that depends on {occupation_focus}."
        evening = "Evenings are where setup tolerance drops sharply; anything that asks for fresh configuration after 9pm is likely to be postponed."
    elif schedule_pressure == "low":
        morning_routine = "Starts by carrying forward yesterday's open items and deciding what actually deserves attention today."
        work_start = f"Work starts more deliberately, but it still revolves around {occupation_focus}, so abstract tools struggle to hold interest."
        evening = "Evenings can handle light evaluation, but not a sprawling onboarding flow that feels like unpaid admin."
    else:
        morning_routine = "Usually checks messages or loose ends before the day properly starts, which means anything urgent can reframe the whole morning."
        work_start = f"Begins with triage rather than ideal planning, then tries to reclaim one clear next step around {occupation_focus}."
        evening = "Evenings are where tool setup tolerance drops sharply; if the product demands fresh attention then, abandonment risk rises."
    return {
        "morning_routine": morning_routine,
        "commute_or_transition_time": "Uses transition time for low-stakes reading, voice notes, or deciding what can safely wait.",
        "work_start_pattern": work_start,
        "message_checking_pattern": "Checks messages more often than they would like, because hidden coordination risk feels expensive.",
        "break_time_behaviour": "Short breaks often become micro-research moments for reviews, comparisons, or catching up on deferred admin.",
        "evening_routine": evening,
        "weekend_pattern": "Weekends are for recovery plus a small amount of catch-up, not a full systems rebuild.",
        "shopping_moments": "Most likely to try a product right after a specific frustration, not during vague inspiration.",
        "decision_moments": "Decisions crystallise when the cost of doing nothing becomes easier to picture than the effort of trying.",
        "stress_moments": "Stress rises when many small loose ends coexist and nothing feels fully closed.",
        "when_they_are_most_open_to_new_products": "Immediately after a repeated pain point becomes concrete and embarrassing or tiring enough.",
        "when_they_are_least_open_to_new_products": "Late at night, during heavy admin days, or whenever setup feels like a second job.",
    }


def _build_social_circle(persona: PersonaSkill) -> dict[str, Any]:
    family_structure = _household_context_phrase(persona.profile.basic_identity)
    purchase_authority = str(persona.seed.purchase_authority_type)
    return {
        "close_circle": ["partner or close family", "one or two friends who understand their real routine", "a colleague they trust to be practical"],
        "work_circle": ["people affected by handoff quality", "peers who notice whether a tool creates extra follow-up", "stakeholders who care more about reliability than novelty"],
        "family_influence": f"{family_structure.capitalize()} shapes how much risk, time, and public explanation a new product can demand.",
        "peer_group_norms": "Social proof matters, but only when it comes from people with comparable constraints.",
        "communities_they_belong_to": ["messaging-based peer groups", "lightweight professional communities", "practical interest circles rather than identity-performance spaces"],
        "communities_they_observe_but_do_not_join": ["large hype-heavy product communities", "expert spaces that assume too much free time"],
        "who_influences_their_purchases": ["trusted peers", "a partner or family member when shared routines are affected", "operators who explain trade-offs plainly"],
        "who_they_ask_before_buying": [
            "someone who will tell them what broke in real use",
            "someone affected by the spend or workflow change",
            f"whoever shares decision authority when the purchase mode is {purchase_authority}",
        ],
        "who_they_avoid_discussing_sensitive_topics_with": ["people who treat identity, money, or privacy as abstract debates rather than lived context"],
        "social_proof_required": "Moderate: not crowd validation, but one believable path from someone similar.",
    }


def _build_taste(persona: PersonaSkill) -> dict[str, Any]:
    age = int(persona.profile.basic_identity.get("age", 0))
    return {
        "visual_style_preference": "clear, calm, and purposeful rather than loud or overly polished",
        "ui_density_preference": "medium: enough information to trust, but not enough to feel buried" if age < 50 else "medium-high: enough detail to understand what is really being promised",
        "tone_preference": "respectful, specific, and slightly skeptical of its own claims",
        "brand_personality_preference": "quietly competent rather than disruptive for its own sake",
        "trustworthy_design_signals": ["honest comparison framing", "clear explanation of data handling", "visible constraints", "proof that onboarding is bounded"],
        "design_turnoffs": ["gratuitous animation", "mystery meat navigation", "empty whitespace that hides missing detail"],
        "copywriting_turnoffs": ["AI-powered revolution language", "forced urgency", "generic empowerment slogans"],
        "preferred_explanation_format": "short examples first, then detail on demand",
        "examples_of_brands_or_products_they_find_trustworthy": ["products that explain trade-offs without embarrassment", "tools with plain setup expectations"],
        "examples_of_products_they_find_annoying": ["products that confuse elegance with omission", "tools that act clever when the user needs clarity"],
    }


def _build_spending(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "small_impulse_purchases": ["snacks or drinks that create a brief sense of reset", "low-cost utilities that promise micro-relief"],
        "planned_purchases": ["anything subscription-based", "tools that affect routine", "items tied to family or work reliability"],
        "guilty_pleasures": ["small conveniences that feel more justified than they really are", "keeping at least one subscription longer than its actual usage"],
        "things_they_will_pay_premium_for": ["time recovery", "reliability", "privacy reassurance when the risk feels real"],
        "things_they_refuse_to_pay_for": ["status-feeling software with no durable utility", "features that create more set-up than relief"],
        "subscription_cemetery": ["tools that looked sensible in week one and invisible by week four"],
        "recent_cancelled_subscriptions": ["at least one tool that kept billing after it stopped being part of daily life"],
        "recent_good_purchase": "A purchase that removed a small but recurring annoyance without needing upkeep theatre.",
        "recent_regretted_purchase": "Something that looked efficient but quietly added one more thing to maintain.",
        "how_they_justify_spending": "By asking whether the product saves repeat effort, lowers social risk, or protects energy.",
        "how_they_explain_spending_to_others": "Framed in practical terms: time saved, hassle avoided, or one fewer thing to juggle mentally.",
    }


def _build_environment(persona: PersonaSkill) -> dict[str, Any]:
    seed = asdict(persona.seed)
    return {
        "home_setup": "Functional rather than staged. Convenience matters, but so does not having to explain every personal workflow to other people nearby.",
        "workspace_setup": "A mix of practical tools and a few too many open loops, with organisation that looks better from a distance than up close.",
        "devices_owned": [seed.get("device_environment", "phone-plus-laptop").replace("-", " "), "at least one trusted messaging device"],
        "tools_always_open": ["messages", "calendar", "notes or reminders", "some form of comparison or search tab"],
        "physical_objects_on_desk_or_bag": ["charger", "water bottle or coffee", "one object that exists because they do not trust memory alone"],
        "storage_or_organisation_style": "Partial order: enough structure to recover, not enough to feel pristine.",
        "noise_level_in_daily_life": "Moderate; interruptions are normal, not exceptional.",
        "privacy_at_home_or_work": "Context-dependent, which affects willingness to use voice, disclose personal detail, or test identity-sensitive flows openly.",
        "constraints_from_environment": ["mobile-first moments", "interrupted attention", "limited patience for heavyweight tools on ordinary hardware"],
    }


def _build_emotional_regulation(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "stress_response": "Gets more narrow and practical under stress; wants fewer moving parts, not more inspiring possibilities.",
        "avoidance_pattern": "Avoids products that seem to require a clean slate, because real life rarely offers one.",
        "comfort_behaviours": ["searching for examples before deciding", "using familiar workarounds for one more week", "postponing setup until it feels safer"],
        "what_makes_them_feel_in_control": ["visible next steps", "reversible choices", "knowing what data is involved", "one bounded trial instead of a full migration"],
        "what_makes_them_feel_exposed": ["tools that publicly display disorder", "forced identity disclosure", "workflows that make mistakes hard to hide while learning"],
        "what_makes_them_feel_judged": ["moralising copy", "product language that assumes discipline is the same as virtue", "support content that feels patronising"],
        "how_they_recover_after_bad_decisions": "First shrinks the experiment, then keeps only what was concretely useful.",
        "how_they_react_to_failed_tools": "Becomes slower to trust the next promise and more attentive to hidden setup cost.",
    }


def _build_hidden_habits(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "private_shortcuts": ["keeps too much in message search", "uses temporary reminders that quietly become permanent"],
        "things_they_do_but_would_not_admit": ["sometimes judges tools by whether they reduce embarrassment as much as whether they save time"],
        "workarounds_they_keep_using": ["parallel systems that should have been retired", "copying key details into a simpler place just in case"],
        "bad_habits_that_affect_product_use": ["tries to evaluate tools while distracted", "gives up on setup when a small interruption breaks momentum"],
        "things_they_procrastinate_on": ["clean migrations", "subscription reviews until the annoyance becomes obvious", "formalising a workaround that still sort of works"],
        "areas_where_they_overestimate_themselves": ["how much future setup patience they will have", "how often they will revisit saved product links"],
        "areas_where_they_underestimate_themselves": ["how quickly they can spot vague claims", "how much their everyday frustration can predict long-term adoption failure"],
    }


def _build_identity_symbols(persona: PersonaSkill) -> dict[str, Any]:
    values = persona.profile.values
    return {
        "objects_that_represent_them": ["a notes app full of half-organised intent", "one tool they trust because it stayed useful under stress"],
        "phrases_they_might_say": ["I need to know what this replaces.", "I do not want another thing to maintain.", "If this only works in ideal conditions, it will not stick."],
        "things_they_are_proud_of": values.get("identity_anchors", [])[:3],
        "things_they_are_quietly_insecure_about": ["how many parallel workarounds they still need", "whether other people notice the invisible effort behind their reliability"],
        "status_markers_they_care_about": ["being seen as dependable", "looking thoughtful rather than gullible", "not appearing careless with private information"],
        "status_markers_they_reject": ["performative busyness", "trend-chasing without usefulness", "spending that cannot be justified"],
        "how_they_want_products_to_make_them_feel": "More composed, more credible, and less fragmented.",
    }


def _build_cultural_texture(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    languages = identity.get("language", [])
    return {
        "local_context_markers": [identity.get("location", ""), _locale_texture(identity)],
        "language_switching_pattern": f"Language choice shifts by audience and setting; {', '.join(languages)} are used with different levels of formality or intimacy.",
        "family_norms": "Practical obligations tend to matter more than abstract self-description.",
        "workplace_norms": "Politeness can hide disagreement, so product enthusiasm is not the same as adoption intent.",
        "money_talk_norms": "Spending is easier to defend when tied to usefulness, stability, or care rather than pure preference.",
        "privacy_norms": "What is acceptable to share depends heavily on audience and context, not just on the data itself.",
        "authority_relationship": "Respects competence and specificity more than rank theatre.",
        "how_culture_affects_product_trust": "Trust rises when the product reads local caution and social context as normal instead of as resistance.",
        "how_culture_affects_public_feedback": "More likely to soften objections in public and become precise in smaller, safer settings.",
    }


def _build_discovery_paths(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "most_likely_first_touchpoint": "Search, peer mention, or a comparison moment triggered by a specific frustration.",
        "channels_that_work": ["peer referral", "searchable comparison content", "clear product demos", "operator-style case stories"],
        "channels_that_do_not_work": ["generic founder storytelling", "broad hype threads", "identity-flattering marketing with no workflow detail"],
        "message_format_that_gets_attention": "one concrete before-and-after scenario",
        "message_format_that_gets_ignored": "vision-first copy with no bounded first use case",
        "referral_path": "A believable recommendation from someone who used it under similar constraints.",
        "trial_trigger": "A repeated pain point plus a trial that feels reversible.",
        "conversion_path": "Understanding -> bounded trial -> visible relief -> payment -> gradual routine trust.",
        "drop_off_path": "Curiosity -> setup friction -> interruption -> no obvious first win -> abandonment.",
    }


def _build_objection_language(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "direct_objection_examples": [
            "I understand the idea, but I still do not know what this replaces.",
            "This setup already sounds heavier than the problem I have.",
            "You are describing curiosity, not a reason for me to pay.",
        ],
        "polite_objection_examples": [
            "I can see why some people might like it, but I am not sure it fits how I actually work.",
            "It is interesting, though I would need to see a much simpler first step.",
        ],
        "hidden_objection_patterns": [
            "says the product is interesting but never asks about next steps",
            "keeps the conversation abstract when they do not trust the practical path",
        ],
        "what_they_say_when_they_are_only_being_nice": [
            "This is a cool idea.",
            "I can imagine there is a market for this.",
        ],
        "what_they_say_when_they_are_genuinely_interested": [
            "Can you show me one ordinary use case from start to finish?",
            "What happens if I stop halfway through setup?",
        ],
        "what_they_ask_when_they_are_close_to_trying": [
            "What is the smallest safe way to test this?",
            "How long before I know whether it fits?",
        ],
        "what_they_ask_when_they_are_close_to paying": [
            "What would I actually stop paying for or doing if this worked?",
            "How easy is it to leave if it does not hold up after a month?",
        ],
    }


def _build_contradictions(persona: PersonaSkill) -> list[dict[str, str]]:
    contradictions = [
        {
            "contradiction": "Wants convenience but resists setup.",
            "how_it_shows_up": "Can recognise the value of a tool and still abandon it if onboarding asks for too much uninterrupted focus.",
            "product_validation_effect": "Founders may misread agreement on the problem as willingness to adopt the solution.",
        },
        {
            "contradiction": "Wants organisation but avoids products that expose disorganisation too early.",
            "how_it_shows_up": "Prefers tools that help quietly before asking for visible structure.",
            "product_validation_effect": "A product that feels publicly evaluative will suppress honest trial behaviour.",
        },
        {
            "contradiction": "Values clarity but sometimes delays decisions by over-comparing.",
            "how_it_shows_up": "Looks for enough proof to feel safe, then risks stretching evaluation too long.",
            "product_validation_effect": "Interest can stay alive without converting unless the trial path is sharply bounded.",
        },
        {
            "contradiction": "Talks about price carefully but is willing to spend when the product protects time or dignity.",
            "how_it_shows_up": "May reject moderate pricing for a weak tool, then pay more for something that genuinely lowers stress.",
            "product_validation_effect": "Simple price-sensitivity labels can mislead founders about what 'too expensive' really means.",
        },
        {
            "contradiction": "Can be skeptical of hype but still drawn to elegant demos.",
            "how_it_shows_up": "A polished first impression can buy attention, but not durable trust.",
            "product_validation_effect": "Landing page success may overstate actual adoption potential.",
        },
    ]
    if persona.seed.privacy_risk_tolerance == "low":
        contradictions.append(
            {
                "contradiction": "Likes smart automation but distrusts broad data access.",
                "how_it_shows_up": "Feels real attraction to convenience and real hesitation about what must be shared to get it.",
                "product_validation_effect": "AI appeal can coexist with refusal to connect real data.",
            }
        )
    return contradictions


def _build_deep_research_notes(persona: PersonaSkill) -> dict[str, Any]:
    return {
        "what_a_founder_might_misread_about_them": [
            "May confuse clear understanding with purchase intent.",
            "May misread politeness as belief that the product fits routine reality.",
            "May overvalue conceptual enthusiasm and undervalue setup resistance.",
        ],
        "what_this_person_will_not_say_directly": [
            "That the product makes them feel slightly judged or exposed.",
            "That they do not trust the founder's certainty yet.",
            "That the real issue is not the feature, but the extra maintenance they can already imagine.",
        ],
        "what_interview_questions_work_best": [
            "Ask for the last time this problem happened in detail.",
            "Ask what would need to disappear for the product to feel worth keeping.",
            "Ask what would make them stop halfway through trying it.",
        ],
        "what_interview_questions_fail": [
            "Would you use this?",
            "Do you like this idea?",
            "Would this save time? without grounding it in a real day",
        ],
        "how_to_detect_real_interest": [
            "They ask bounded next-step questions.",
            "They compare the tool against a real existing workaround.",
            "They ask about reversal cost or first-week proof.",
        ],
        "how_to_detect_polite_fake_interest": [
            "They stay complimentary but abstract.",
            "They never ask what setup requires.",
            "They agree with the problem statement but do not explore behaviour change.",
        ],
        "best_validation_method_for_this_person": "A concrete workflow walkthrough plus a bounded trial with one believable use case.",
        "worst_validation_method_for_this_person": "An abstract pitch, a hype-heavy landing page, or a long feature tour detached from ordinary routines.",
        "ethical_cautions_when_researching_this_person": [
            "Do not exploit anxiety, guilt, or identity exposure to force urgency.",
            "Do not treat privacy hesitation as ignorance.",
            "Do not equate politeness with informed consent or enthusiasm.",
        ],
    }


def _build_sensitive_reality_layer_v2(persona: PersonaSkill) -> dict[str, Any]:
    base = dict(persona.profile.sensitive_reality_layer)
    base.update(
        {
            "sensitive_identity_context": {
                "disclosure_preference": "not_disclosed unless clearly relevant",
                "relevant_when": ["privacy risk", "social visibility", "public explanation burden", "inclusive language mismatch"],
                "notes": "Identity matters through comfort, trust, and public-expression cost, not as a shortcut to behaviour.",
            },
            "social_risk_profile": "Does not want a product to create avoidable reputational or relational friction.",
            "social_risk_profile_detail": {
                "public_mistake_cost": "moderate",
                "embarrassment_triggers": ["messy setup exposed too early", "unclear automation acting on their behalf", "tone that feels patronising"],
            },
            "fairness_and_inclusion_profile": "Expects respectful language and control over what must be disclosed.",
            "fairness_and_inclusion_detail": {
                "watches_for": ["forced identity assumptions", "default-user language", "hidden exclusion in examples"],
                "preferred_fix": "plain, optional, user-controlled handling of identity-relevant flows",
            },
            "taboo_topic_comfort": "context-dependent and usually cautious in public-facing situations",
            "taboo_topic_comfort_detail": {
                "public": "low",
                "private": "medium",
                "when_it_changes": "comfort rises when the topic is clearly necessary, handled respectfully, and not used to flatten the person into a label",
            },
            "sensitive_product_reaction_rules": [
                "pushes back if a product asks for identity disclosure before value is clear",
                "trust drops if the product frames people as categories before context",
                "responds better when privacy, dignity, and control are described concretely",
            ],
        }
    )
    return base


def _augment_decision_policy_v2(persona: PersonaSkill) -> dict[str, Any]:
    decision_policy = copy.deepcopy(persona.decision_policy)
    decision_policy.update(
        {
            "curiosity_threshold": "The problem feels real and the product is understandable.",
            "trial_threshold": "A bounded first use case exists and the setup looks survivable.",
            "payment_threshold": "A real reduction in weekly friction is visible, not just promised.",
            "adoption_threshold": "The product remains useful after novelty wears off and actually replaces a workaround.",
            "founder_challenge_style": "If the founder is vague, optimistic, or blurs interest with adoption, this persona should say so directly.",
        }
    )
    return decision_policy


def _augment_response_style_v2(persona: PersonaSkill) -> dict[str, Any]:
    response_style = copy.deepcopy(persona.response_style)
    response_style.update(
        {
            "objection_style": "more precise when trust is low, warmer when the founder proves they understand constraints",
            "founder_flattery_rule": "Do not reward vague optimism with false encouragement.",
            "preferred_response_shape": "problem -> friction -> trust or pricing concern -> what would change their mind",
        }
    )
    return response_style


def upgrade_persona_to_v2(persona: PersonaSkill, *, random_seed: int | None = None) -> PersonaSkill:
    upgraded = copy.deepcopy(persona)
    rng = _stable_rng(persona, random_seed)

    upgraded.skill_version = "v2"
    upgraded.profile.life_story = _build_life_story_v2(upgraded)
    upgraded.profile.canonical_biography = _build_canonical_biography(upgraded)
    upgraded.profile.domain_fit = _build_domain_fit(upgraded)
    upgraded.profile.pricing_logic = _build_pricing_logic(upgraded)
    upgraded.profile.workflow_adoption_model = _build_workflow_adoption_model(upgraded)
    upgraded.profile.product_reaction_rules = _build_product_reaction_rules(upgraded)
    upgraded.profile.identity_and_inclusion_reaction = _build_identity_and_inclusion_reaction(upgraded)
    upgraded.profile.cross_domain_product_reaction_model = _build_cross_domain_product_reaction_model(upgraded)
    upgraded.profile.interests_and_hobbies = _build_interest_layer(upgraded, rng)
    upgraded.profile.media_and_content_diet = _build_media_diet(upgraded)
    upgraded.profile.daily_micro_behaviours = _build_daily_micro_behaviours(upgraded)
    upgraded.profile.social_circle_and_communities = _build_social_circle(upgraded)
    upgraded.profile.taste_and_aesthetic_preferences = _build_taste(upgraded)
    upgraded.profile.spending_and_leisure_patterns = _build_spending(upgraded)
    upgraded.profile.personal_environment = _build_environment(upgraded)
    upgraded.profile.emotional_regulation_style = _build_emotional_regulation(upgraded)
    upgraded.profile.hidden_habits = _build_hidden_habits(upgraded)
    upgraded.profile.identity_symbols = _build_identity_symbols(upgraded)
    upgraded.profile.cultural_texture = _build_cultural_texture(upgraded)
    upgraded.profile.product_discovery_paths = _build_discovery_paths(upgraded)
    upgraded.profile.objection_language_style = _build_objection_language(upgraded)
    upgraded.profile.contradiction_map = _build_contradictions(upgraded)
    upgraded.profile.deep_research_notes = _build_deep_research_notes(upgraded)
    upgraded.profile.sensitive_reality_layer = _build_sensitive_reality_layer_v2(upgraded)

    upgraded.decision_policy = _augment_decision_policy_v2(upgraded)
    upgraded.response_style = _augment_response_style_v2(upgraded)

    upgraded.profile.audit_evidence_layer["persona_generation_method"] = "deterministic_seed_plus_template_enhancement_v2"
    upgraded.profile.audit_evidence_layer["persona_version"] = "v2"
    upgraded.profile.audit_evidence_layer["generator_version"] = "persona-generator/v2"
    upgraded.profile.audit_evidence_layer["last_audited_at"] = datetime.now(UTC).date().isoformat()

    upgraded.audit = {
        **upgraded.audit,
        **upgraded.profile.audit_evidence_layer,
    }
    upgraded.narrative = render_compat_persona_md(upgraded)
    return upgraded


def render_biography_md(persona: PersonaSkill) -> str:
    biography = persona.profile.canonical_biography
    interests = persona.profile.interests_and_hobbies
    media = persona.profile.media_and_content_diet
    daily = persona.profile.daily_micro_behaviours
    environment = persona.profile.personal_environment
    contradictions = persona.profile.contradiction_map
    taste = persona.profile.taste_and_aesthetic_preferences
    identity = persona.profile.basic_identity
    sections: list[str] = [
        f"# {identity['name']} - Level 3 Synthetic User Biography",
        "",
        "## Life Arc Summary",
        biography.get("life_arc_summary", ""),
        "",
    ]
    for chapter in biography.get("decade_timeline", []):
        sections.extend(
            [
                f"## {chapter['age_range']}",
                f"**{chapter['chapter_title']}**",
                chapter["life_context"],
                "",
                "Key experiences:",
                *[f"- {item}" for item in chapter.get("key_experiences", [])],
                "",
                f"Relationships: {chapter['relationships']}",
                f"Money lessons: {chapter['money_lessons']}",
                f"Technology exposure: {chapter['technology_exposure']}",
                f"Trust lessons: {chapter['trust_lessons']}",
                f"Identity development: {chapter['identity_development']}",
                f"Emotional imprint: {chapter['emotional_imprint']}",
                f"Product research impact: {chapter['current_product_research_impact']}",
                "",
            ]
        )
    sections.extend(
        [
            "## Current Life",
            biography.get("current_daily_life", ""),
            "",
            "## Formative Events",
            *[
                f"- {item['age_range']}: {item['event_summary']} - {item['impact']}"
                for item in biography.get("formative_events", [])
            ],
            "",
            "## Current Identity",
            biography.get("current_identity", ""),
            "",
            "## Interests & Private Life",
            f"Primary interests: {', '.join(interests.get('primary_interests', []))}",
            f"Low-energy hobbies: {', '.join(interests.get('low_energy_hobbies', []))}",
            f"Private hobbies: {', '.join(interests.get('private_hobbies', []))}",
            f"Aspirational hobbies: {', '.join(interests.get('aspirational_hobbies', []))}",
            "",
            "## Media Diet & Product Discovery",
            f"News and information sources: {', '.join(media.get('news_sources', []))}",
            f"Platforms and channels: {', '.join(media.get('social_platforms', []))}",
            f"Discovery pattern: {media.get('how_they_discover_new_products', '')}",
            f"Verification pattern: {media.get('how_they_verify_claims', '')}",
            "",
            "## Ordinary Day in Detail",
            f"Workday: {daily.get('morning_routine', '')} {daily.get('work_start_pattern', '')} {daily.get('evening_routine', '')}",
            f"Weekend: {daily.get('weekend_pattern', '')}",
            f"Most open to products: {daily.get('when_they_are_most_open_to_new_products', '')}",
            f"Least open to products: {daily.get('when_they_are_least_open_to_new_products', '')}",
            "",
            "## Home, Workspace & Tools",
            f"Home: {environment.get('home_setup', '')}",
            f"Workspace: {environment.get('workspace_setup', '')}",
            f"Always-open tools: {', '.join(environment.get('tools_always_open', []))}",
            f"Constraints: {', '.join(environment.get('constraints_from_environment', []))}",
            "",
            "## Hidden Habits & Contradictions",
            f"Hidden habits: {', '.join(persona.profile.hidden_habits.get('workarounds_they_keep_using', []))}",
            *[
                f"- {item['contradiction']} {item['product_validation_effect']}"
                for item in contradictions
            ],
            "",
            "## Taste, Brand & Communication Preferences",
            f"Visual preference: {taste.get('visual_style_preference', '')}",
            f"Trustworthy design signals: {', '.join(taste.get('trustworthy_design_signals', []))}",
            f"Copy turnoffs: {', '.join(taste.get('copywriting_turnoffs', []))}",
            "",
            "## Product Research Implications",
            "- Concept validation: works best when the product is framed around one repeated friction, not a grand transformation.",
            "- Landing page test: must separate understandable from desirable and desirable from adoptable.",
            "- Pricing test: should probe what existing effort or spend the product replaces.",
            "- Onboarding test: must be evaluated under interruption, fatigue, and imperfect setup tolerance.",
            "- Retention risk: rises sharply if value is visible only after disciplined usage.",
            "- Referral likelihood: increases only after the product survives lived use, not just initial clarity.",
            "",
            "## Sensitive Reality Notes",
            persona.profile.sensitive_reality_layer.get("fairness_and_inclusion_profile", ""),
            "",
            "## What This Persona Is Good For",
            f"- {', '.join(persona.profile.domain_fit.get('sample_when', []))}",
            "",
            "## What This Persona Should Not Be Used For",
            *[f"- {item}" for item in persona.profile.audit_evidence_layer.get("do_not_use_for", [])],
        ]
    )
    return "\n".join(sections).strip() + "\n"


def render_research_kernel_md(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    biography = persona.profile.canonical_biography
    sections = [
        f"# Research Kernel: {identity['name']}",
        "",
        "## Identity",
        f"{identity['name']} is a {identity['age']}-year-old {identity['occupation']} in {identity['location']}. "
        f"They are a synthetic user for AI pre-validation, not a real human research participant.",
        "",
        "## Life Arc Summary",
        biography.get("life_arc_summary", ""),
        "",
        "## Top Formative Patterns",
        "- Repeatedly learned to distrust polished promises that hide upkeep.",
        "- Treats reliability and reversibility as trust signals.",
        "- Reads small workflow friction as a predictor of long-term abandonment.",
        "",
        "## Current Life Situation",
        persona.profile.life_story.get("current_daily_routine", ""),
        "",
        "## Core Values",
        ", ".join(persona.profile.values.get("core_values", [])),
        "",
        "## Trust Model",
        f"Trust grows through {', '.join(persona.decision_policy.get('trust_requirements', []))}. "
        "Vague certainty and hidden complexity reduce trust quickly.",
        "",
        "## Buying Logic",
        persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
        "",
        "## Pricing Logic",
        persona.profile.pricing_logic.get("pricing_objection", ""),
        persona.profile.pricing_logic.get("what_makes_price_feel_fair", ""),
        "",
        "## Technology Attitude",
        f"AI familiarity: {persona.profile.technology_profile.get('ai_familiarity', '')}. "
        f"Privacy concern: {persona.profile.technology_profile.get('privacy_concern', '')}. "
        "Technology earns a place only if it lowers noise without multiplying maintenance.",
        "",
        "## Interests That Affect Buying Behaviour",
        f"Primary interests: {', '.join(persona.profile.interests_and_hobbies.get('primary_interests', []))}",
        f"Interest depth: {persona.profile.interests_and_hobbies.get('interest_depth', [{}])[0].get('interest_name', '')} matters because it shapes how they evaluate utility over novelty.",
        "",
        "## Media Diet And Discovery Path",
        persona.profile.media_and_content_diet.get("how_they_discover_new_products", ""),
        persona.profile.product_discovery_paths.get("conversion_path", ""),
        "",
        "## Daily Friction Moments",
        persona.profile.daily_micro_behaviours.get("stress_moments", ""),
        persona.profile.daily_micro_behaviours.get("when_they_are_least_open_to_new_products", ""),
        "",
        "## Hidden Habits",
        ", ".join(persona.profile.hidden_habits.get("workarounds_they_keep_using", [])),
        "",
        "## Contradictions",
        *[f"- {item['contradiction']}" for item in persona.profile.contradiction_map],
        "",
        "## Sensitive Topic Reaction",
        persona.profile.sensitive_reality_layer.get("fairness_and_inclusion_profile", ""),
        "",
        "## Cross-Domain Product Reaction Summary",
        "Across domains, they first ask what problem is being removed, what trust cost is being introduced, and whether the product fits imperfect routines.",
        "",
        "## Strong Objections",
        *[f"- {item}" for item in persona.profile.product_reaction_rules.get("negative_signals", [])],
        "",
        "## Objection Language",
        *[f"- {item}" for item in persona.profile.objection_language_style.get("direct_objection_examples", [])],
        "",
        "## Founder Misread Risk",
        *[f"- {item}" for item in persona.profile.deep_research_notes.get("what_a_founder_might_misread_about_them", [])],
        "",
        "## Response Style",
        persona.response_style.get("preferred_response_shape", ""),
        "",
        "## Do Not Flatter Founder Rule",
        "Do not flatter the founder. If the product is vague, high-friction, untrustworthy, overpriced, or weakly differentiated, say so plainly.",
    ]
    return "\n".join(sections).strip() + "\n"


def _example_response(persona: PersonaSkill, title: str, reaction_key: str, extra_line: str) -> str:
    reaction = persona.profile.cross_domain_product_reaction_model.get(reaction_key, {})
    return "\n".join(
        [
            f"### {title}",
            f"> First question: {reaction.get('first_question', '')}",
            f"> Positive trigger: {reaction.get('positive_trigger', '')}",
            f"> Likely objection: {reaction.get('likely_objection', '')}",
            f"> Response: {extra_line}",
            "",
        ]
    ).strip()


def render_persona_skill_md(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    biography = persona.profile.canonical_biography
    household_context = _household_context_phrase(identity)
    rules = [
        "Do not flatter the founder.",
        "Do not pretend to be a real human.",
        "Respond as this persona.",
        "Separate curiosity from willingness to pay.",
        "Challenge vague claims.",
        "Point out friction, privacy, trust, pricing, and sensitive topic risks where relevant.",
        "If the product is unclear, say it is unclear.",
        "If the persona would not buy, say so.",
    ]
    sections = [
        f"# Synthetic User Skill: {identity['name']}",
        "",
        "## Role",
        "This is a synthetic user skill for AI pre-validation only. It can challenge product assumptions, but it is not a substitute for real human market research.",
        "",
        "## Identity",
        f"{identity['name']} is a {identity['age']}-year-old {identity['occupation']} in {identity['location']}, {household_context}.",
        "",
        "## Canonical Life Arc",
        biography.get("life_arc_summary", ""),
        "",
        "## Decade Memory",
        *[f"- {item['age_range']}: {item['current_product_research_impact']}" for item in biography.get("decade_timeline", [])],
        "",
        "## Current Life",
        persona.profile.life_story.get("current_daily_routine", ""),
        "",
        "## Formative Patterns",
        *[f"- {item['impact']}" for item in biography.get("formative_events", [])[:8]],
        "",
        "## Lifestyle & Interests",
        f"Primary interests that affect buying behaviour: {', '.join(persona.profile.interests_and_hobbies.get('primary_interests', []))}",
        f"Low-energy habits that shape trial behaviour: {', '.join(persona.profile.interests_and_hobbies.get('low_energy_hobbies', []))}",
        "",
        "## Daily Context",
        persona.profile.daily_micro_behaviours.get("when_they_are_most_open_to_new_products", ""),
        persona.profile.daily_micro_behaviours.get("when_they_are_least_open_to_new_products", ""),
        "",
        "## Decision Logic",
        persona.decision_policy.get("founder_challenge_style", ""),
        "",
        "## Buying Logic",
        persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
        "",
        "## Pricing Logic",
        persona.profile.pricing_logic.get("pricing_objection", ""),
        persona.profile.pricing_logic.get("maximum_comfortable_price_band", ""),
        "",
        "## Technology & AI Attitude",
        f"AI familiarity: {persona.profile.technology_profile.get('ai_familiarity', '')}. "
        f"Privacy concern: {persona.profile.technology_profile.get('privacy_concern', '')}. "
        "They will not reward 'AI' as a label unless it reduces real work and explains risk clearly.",
        "",
        "## Discovery & Trust Path",
        persona.profile.product_discovery_paths.get("most_likely_first_touchpoint", ""),
        persona.profile.product_discovery_paths.get("conversion_path", ""),
        "",
        "## Cross-Domain Product Reaction Model",
        *[
            f"- {key}: first question = {value.get('first_question', '')}; likely objection = {value.get('likely_objection', '')}"
            for key, value in persona.profile.cross_domain_product_reaction_model.items()
        ],
        "",
        "## Sensitive Topic Handling",
        persona.profile.sensitive_reality_layer.get("fairness_and_inclusion_profile", ""),
        "Will react strongly when a product forces labels, hides privacy implications, or assumes one default household or identity experience.",
        "",
        "## Objection Language",
        *[f"- {item}" for item in persona.profile.objection_language_style.get("direct_objection_examples", [])],
        "",
        "## Hidden Contradictions",
        *[f"- {item['contradiction']}" for item in persona.profile.contradiction_map],
        "",
        "## Founder Misread Risk",
        *[f"- {item}" for item in persona.profile.deep_research_notes.get("what_a_founder_might_misread_about_them", [])],
        "",
        "## Response Rules",
        *[f"- {rule}" for rule in rules],
        "",
        "## Example Responses",
        _example_response(
            persona,
            "AI Productivity Product",
            "ai_product",
            "I might try this if it clearly removes follow-up work, but I still need to know what I stop doing and what the AI sees.",
        ),
        "",
        _example_response(
            persona,
            "Subscription Product",
            "subscription_product",
            "I can understand the offer and still say no if the recurring cost arrives before the routine benefit feels earned.",
        ),
        "",
        _example_response(
            persona,
            "Identity-Sensitive Product",
            "identity_sensitive_product",
            "If you ask me to label myself before I trust you, I will probably disengage rather than debate you.",
        ),
        "",
        _example_response(
            persona,
            "High-Friction Onboarding Product",
            "high_friction_onboarding",
            "If onboarding already feels like project work, I assume ongoing use will ask for too much discipline from me.",
        ),
        "",
        _example_response(
            persona,
            "Vague Founder Pitch",
            "generic_new_product",
            "I understand your enthusiasm, but I do not yet understand the lived change. Right now this sounds clearer as curiosity than as payment intent.",
        ),
    ]
    return "\n".join(sections).strip() + "\n"


def render_compat_persona_md(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    return "\n".join(
        [
            f"# {identity['name']}",
            "",
            "## Snapshot",
            f"- ID: {identity['synthetic_user_id']}",
            f"- Occupation: {identity['occupation']}",
            f"- Location: {identity['location']}",
            f"- Household: {identity['family_structure']}",
            "",
            "## Core Read",
            persona.profile.canonical_biography.get("life_arc_summary", ""),
            "",
            "## Validation Stance",
            persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
            "",
            "## Immediate Frictions",
            *[f"- {item}" for item in persona.profile.problem_context.get("active_pain_points", [])[:5]],
        ]
    ).strip() + "\n"


def _required_v2_profile_sections() -> dict[str, str]:
    return {
        "canonical_biography": "object",
        "domain_fit": "object",
        "pricing_logic": "object",
        "workflow_adoption_model": "object",
        "product_reaction_rules": "object",
        "identity_and_inclusion_reaction": "object",
        "cross_domain_product_reaction_model": "object",
        "interests_and_hobbies": "object",
        "media_and_content_diet": "object",
        "daily_micro_behaviours": "object",
        "social_circle_and_communities": "object",
        "taste_and_aesthetic_preferences": "object",
        "spending_and_leisure_patterns": "object",
        "personal_environment": "object",
        "emotional_regulation_style": "object",
        "hidden_habits": "object",
        "identity_symbols": "object",
        "cultural_texture": "object",
        "product_discovery_paths": "object",
        "objection_language_style": "object",
        "contradiction_map": "list",
        "deep_research_notes": "object",
    }


def audit_v2_persona(persona: PersonaSkill, rendered_artifacts: dict[str, str]) -> dict[str, Any]:
    consistency_warnings: list[str] = []
    stereotype_warnings: list[str] = []
    missing_fields: list[str] = []
    profile_payload = persona.profile.to_dict()
    for field_name, field_type in _required_v2_profile_sections().items():
        value = profile_payload.get(field_name)
        if field_type == "object" and not isinstance(value, dict):
            missing_fields.append(field_name)
        elif field_type == "list" and not isinstance(value, list):
            missing_fields.append(field_name)

    age = int(persona.profile.basic_identity.get("age", 0))
    expected_chapters = len(_decade_ranges_for_age(age))
    actual_chapters = len(persona.profile.canonical_biography.get("decade_timeline", []))
    if actual_chapters != expected_chapters:
        consistency_warnings.append(
            f"Decade coverage mismatch: expected {expected_chapters}, got {actual_chapters}."
        )

    contradictions = persona.profile.contradiction_map
    if len(contradictions) < 4:
        consistency_warnings.append("contradiction_map has fewer than 4 entries.")

    interest_depth = persona.profile.interests_and_hobbies.get("interest_depth", [])
    if not isinstance(interest_depth, list) or not interest_depth:
        consistency_warnings.append("interests_and_hobbies lacks structured interest_depth entries.")

    combined_text = "\n".join(rendered_artifacts.values())
    for token in RAW_ENUM_TOKENS:
        if token in combined_text:
            consistency_warnings.append(f"enum leakage detected: '{token}'")

    required_skill_sections = [
        "## Role",
        "## Canonical Life Arc",
        "## Cross-Domain Product Reaction Model",
        "## Sensitive Topic Handling",
        "## Response Rules",
        "## Example Responses",
    ]
    skill_text = rendered_artifacts.get("persona.skill.md", "")
    for section in required_skill_sections:
        if section not in skill_text:
            missing_fields.append(f"persona.skill.md missing section {section}")

    required_biography_sections = [
        "## Life Arc Summary",
        "## Current Life",
        "## Interests & Private Life",
        "## Media Diet & Product Discovery",
        "## Hidden Habits & Contradictions",
    ]
    biography_text = rendered_artifacts.get("biography.md", "")
    for section in required_biography_sections:
        if section not in biography_text:
            missing_fields.append(f"biography.md missing section {section}")

    research_kernel_text = rendered_artifacts.get("research_kernel.md", "")
    word_count = len(research_kernel_text.split())
    if word_count < 500 or word_count > 1200:
        consistency_warnings.append(
            f"research_kernel.md word count {word_count} is outside the target range."
        )

    sensitive_rules = persona.profile.sensitive_reality_layer.get("sensitive_product_reaction_rules", [])
    if not sensitive_rules:
        consistency_warnings.append("sensitive_product_reaction_rules is empty.")

    if persona.profile.personality_belief.get("metaphysical_profile", "").lower().count("decision rule") == 0:
        stereotype_warnings.append("metaphysical_profile no longer explicitly limits causal use.")

    quality_score_estimate = {
        "structure_completeness": max(1, 5 - len(missing_fields)),
        "biography_depth": 5 if actual_chapters >= 3 else 3,
        "product_reaction_readiness": 5 if len(contradictions) >= 4 else 3,
        "sensitive_topic_readiness": 5 if sensitive_rules else 3,
    }

    return {
        "consistency_warnings": consistency_warnings,
        "stereotype_warnings": stereotype_warnings,
        "missing_fields": missing_fields,
        "quality_score_estimate": quality_score_estimate,
        "human_review_needed": True,
    }


def build_generation_notes(
    persona: PersonaSkill,
    *,
    rendered_artifacts: dict[str, str],
    random_seed: int | None = None,
    migration_notes: list[str] | None = None,
) -> dict[str, Any]:
    audit = audit_v2_persona(persona, rendered_artifacts)
    llm_model = persona.audit.get("llm_enrichment", {}).get("model", "")
    return {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": "persona-generator/v2",
        "prompt_versions": PROMPT_VERSIONS,
        "model_used": llm_model or "deterministic-template-v2",
        "generated_at": _timestamp(),
        "random_seed": random_seed,
        "consistency_warnings": audit["consistency_warnings"],
        "stereotype_warnings": audit["stereotype_warnings"],
        "missing_fields": audit["missing_fields"],
        "quality_score_estimate": audit["quality_score_estimate"],
        "human_review_needed": audit["human_review_needed"],
        "migration_notes": migration_notes or [],
    }


def _build_rendered_artifacts(persona: PersonaSkill) -> dict[str, str]:
    return {
        "persona.md": render_compat_persona_md(persona),
        "biography.md": render_biography_md(persona),
        "research_kernel.md": render_research_kernel_md(persona),
        "persona.skill.md": render_persona_skill_md(persona),
    }


def read_v2_rendered_artifacts(folder: Path) -> dict[str, str]:
    return {
        filename: (folder / filename).read_text(encoding="utf-8")
        for filename in RENDERED_ARTIFACT_FILENAMES
        if (folder / filename).exists()
    }


def validate_v2_persona_folder(folder: Path) -> dict[str, Any]:
    persona = load_persona(folder)
    rendered_artifacts = read_v2_rendered_artifacts(folder)
    audit = audit_v2_persona(persona, rendered_artifacts)

    for filename in RENDERED_ARTIFACT_FILENAMES:
        if filename not in rendered_artifacts:
            audit["missing_fields"].append(filename)

    generation_notes_path = folder / "generation_notes.json"
    if not generation_notes_path.exists():
        audit["missing_fields"].append("generation_notes.json")
    else:
        generation_notes = read_json(generation_notes_path)
        if generation_notes.get("generator_version") != "persona-generator/v2":
            audit["consistency_warnings"].append(
                "generation_notes.json does not declare generator_version persona-generator/v2."
            )
        missing_prompt_versions = [
            prompt_version
            for prompt_version in PROMPT_VERSIONS
            if prompt_version not in generation_notes.get("prompt_versions", [])
        ]
        if missing_prompt_versions:
            audit["missing_fields"].append(
                f"generation_notes.json missing prompt_versions: {', '.join(missing_prompt_versions)}"
            )

    return audit


def write_v2_persona_folder(
    persona: PersonaSkill,
    *,
    base_dir: Path,
    random_seed: int | None = None,
    source_folder: Path | None = None,
    migration_notes: list[str] | None = None,
) -> Path:
    folder = base_dir / persona.profile.synthetic_user_id
    ensure_dir(folder)
    if source_folder is not None and source_folder.exists():
        legacy_dir = folder / "legacy_v1"
        ensure_dir(legacy_dir)
        for filename in ("profile.json", "audit.json", "persona.md"):
            source_path = source_folder / filename
            if source_path.exists():
                shutil.copyfile(source_path, legacy_dir / filename)

    rendered_artifacts = _build_rendered_artifacts(persona)
    generation_notes = build_generation_notes(
        persona,
        rendered_artifacts=rendered_artifacts,
        random_seed=random_seed,
        migration_notes=migration_notes,
    )
    persona.audit = {
        **persona.audit,
        "quality_audit": {
            "consistency_warnings": generation_notes["consistency_warnings"],
            "stereotype_warnings": generation_notes["stereotype_warnings"],
            "missing_fields": generation_notes["missing_fields"],
            "quality_score_estimate": generation_notes["quality_score_estimate"],
            "human_review_needed": generation_notes["human_review_needed"],
        },
        "generator_version": "persona-generator/v2",
    }

    write_json(folder / "profile.json", persona.profile.to_dict())
    write_json(folder / "audit.json", persona.to_audit_payload())
    for filename, content in rendered_artifacts.items():
        (folder / filename).write_text(content, encoding="utf-8")
    write_json(folder / "generation_notes.json", generation_notes)
    return folder


def generate_personas_v2(count: int, random_seed: int = 11, enricher=None, judge=None) -> list[PersonaSkill]:
    base_personas = generate_personas(count=count, random_seed=random_seed, enricher=None, judge=None)
    personas: list[PersonaSkill] = []
    for index, persona in enumerate(base_personas):
        upgraded = upgrade_persona_to_v2(persona, random_seed=random_seed + index)
        if enricher is not None:
            upgraded = enricher.enrich(upgraded)
        if judge is not None:
            upgraded.audit["judge_review"] = judge.judge(upgraded)
        upgraded.narrative = render_compat_persona_md(upgraded)
        personas.append(upgraded)
    return personas


def migrate_personas_to_v2(
    *,
    personas: list[PersonaSkill],
    output_dir: Path,
    source_base_dir: Path | None = None,
    random_seed_offset: int = 0,
) -> list[Path]:
    written_folders: list[Path] = []
    for index, persona in enumerate(personas):
        upgraded = upgrade_persona_to_v2(persona, random_seed=random_seed_offset + index)
        source_folder = None
        if source_base_dir is not None:
            source_folder = source_base_dir / persona.profile.synthetic_user_id
        written_folders.append(
            write_v2_persona_folder(
                upgraded,
                base_dir=output_dir,
                random_seed=random_seed_offset + index,
                source_folder=source_folder,
                migration_notes=[
                    "Migrated from v1 artifacts.",
                    "Original v1 files preserved under legacy_v1/ when source files were available.",
                ],
            )
        )
    return written_folders


def validate_v2_persona_library(base_dir: Path) -> dict[str, Any]:
    if not base_dir.exists():
        return {
            "library_size": 0,
            "persona_reports": [],
            "issue_count": 0,
            "warning_count": 0,
        }

    persona_reports: list[dict[str, Any]] = []
    for folder in sorted(path for path in base_dir.iterdir() if path.is_dir()):
        audit = validate_v2_persona_folder(folder)
        persona_reports.append(
            {
                "persona_id": folder.name,
                **audit,
            }
        )

    issue_count = sum(
        len(report["missing_fields"]) + len(report["consistency_warnings"])
        for report in persona_reports
    )
    warning_count = sum(len(report["stereotype_warnings"]) for report in persona_reports)
    return {
        "library_size": len(persona_reports),
        "persona_reports": persona_reports,
        "issue_count": issue_count,
        "warning_count": warning_count,
    }
