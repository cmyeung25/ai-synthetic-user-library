from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.consistency_validator_v3_1_2 import (
    EXPECTED_PANEL_ROLE_BY_ARCHETYPE,
    build_consistency_report_v3_1_2,
    default_identity_language,
    suggested_life_stage,
    suggested_purchase_authority,
)
from ai_validation_swarm.personas.semantic_mapping_validator_v3_1_2 import build_semantic_mapping_report_v3_1_2
from ai_validation_swarm.personas.v2 import prompt_path
from ai_validation_swarm.personas.v3 import (
    RAW_ENUM_TOKENS as V3_RAW_ENUM_TOKENS,
    _load_persona_from_dir,
    _normalize_text,
    _persona_ids_in,
    _resolve_persona_folder,
    render_local_grounding_md as render_local_grounding_md_v3,
)
from ai_validation_swarm.personas.v3_1 import build_diversity_report_v3_1
from ai_validation_swarm.personas.v3_1_1 import (
    READABLE_MARKDOWN_FILES,
    _example_responses,
    _response_variants,
    _v3_1_1_archetype_key,
    build_example_response_quality,
    lint_markdown_cleanliness,
    render_biography_md_v3_1_1,
    render_persona_md_v3_1_1,
    render_persona_skill_md_v3_1_1,
    render_research_kernel_md_v3_1_1,
    render_sensitive_scenarios_md_v3_1_1,
    upgrade_persona_to_v3_1_1,
)
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json

PROMPT_VERSIONS = [
    "persona-biography/v3_1_2.md",
    "local-grounding/v3_1_2.md",
    "sensitive-scenarios/v3_1_2.md",
    "persona-voiceprint/v3_1_2.md",
    "distinctiveness-revision/v3_1_2.md",
    "quality-auditor/v3_1_2.md",
    "persona-skill/v3_1_1.md",
    "markdown-polish/v3_1_1.md",
]

V3_1_2_REQUIRED_FILES = (
    "profile.json",
    "audit.json",
    "persona.md",
    "biography.md",
    "research_kernel.md",
    "persona.skill.md",
    "generation_notes.json",
    "diversity_report.json",
    "local_grounding.md",
    "sensitive_scenarios.md",
    "polish_report.json",
    "consistency_report.json",
    "semantic_mapping_report.json",
    "v3_1_1_to_v3_1_2_diff.md",
)

RAW_ENUM_TOKENS = V3_RAW_ENUM_TOKENS | {
    "owner_decider",
    "owner_with_family_consultation",
    "owner_with_business_partner_input",
    "owner_with_staff_input",
    "manager_approval_needed",
    "department_budget_recommender",
    "workflow_tool_evaluator",
    "early_adult_small_business_builder",
    "young_operator_founder",
    "early_stage_owner_operator",
    "early_career_specialist",
    "emerging_manager",
    "mature_operator",
    "retention_skeptic",
    "late_career_specialist",
}


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_v3_1_2_prompt_texts() -> dict[str, str]:
    return {
        prompt_version: prompt_path(prompt_version).read_text(encoding="utf-8").strip()
        for prompt_version in PROMPT_VERSIONS
    }


def _non_empty(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _clean_list(values: list[Any]) -> list[str]:
    return [_non_empty(value) for value in values if _non_empty(value)]


def _build_generation_status(
    *,
    consistency_report: dict[str, Any],
    diversity_report: dict[str, Any],
    semantic_report: dict[str, Any],
    polish_report: dict[str, Any],
) -> dict[str, Any]:
    blocking_issues: list[str] = []
    status = "accepted"

    if consistency_report.get("status") == "fail":
        status = "failed_consistency"
        blocking_issues.extend(consistency_report.get("hard_fail_reasons", []))
    elif diversity_report.get("overall_similarity_score", 0.0) > 0.70:
        status = "failed_distinctiveness"
        blocking_issues.append("overall_similarity_above_threshold")
    elif semantic_report.get("status") == "fail":
        status = "failed_semantic_mapping"
        blocking_issues.extend(semantic_report.get("failed_fields", []))
    elif consistency_report.get("status") == "warning":
        status = "needs_review"
        blocking_issues.extend(consistency_report.get("warnings", []))
    elif semantic_report.get("warnings") or polish_report.get("remaining_known_limitations"):
        status = "accepted_with_minor_patch"

    accepted = status in {"accepted", "accepted_with_minor_patch"}
    return {
        "status": status,
        "can_enter_library": accepted,
        "can_enter_validation_runner": accepted,
        "blocking_issues": blocking_issues,
        "recommended_action": {
            "accepted": "publish",
            "accepted_with_minor_patch": "publish and queue for human review",
            "needs_review": "human review before library entry",
            "failed_consistency": "repair contradictory fields and rerun validators",
            "failed_distinctiveness": "regenerate behaviourally overlapping sections",
            "failed_semantic_mapping": "repair sensitive scenario field mapping and rerun validators",
            "failed_regeneration": "inspect rejected candidate and rewrite the failing sections manually",
        }[status],
    }


def _ensure_identity_language(persona: PersonaSkill, fixes: list[str]) -> None:
    gender = _non_empty(persona.profile.basic_identity.get("gender"))
    desired = default_identity_language(gender, persona.profile.identity_language)
    if persona.profile.identity_language != desired:
        persona.profile.identity_language = desired
        fixes.append("identity_language_aligned")


def _small_business_context_for(persona: PersonaSkill) -> dict[str, Any]:
    location = _non_empty(persona.profile.basic_identity.get("location")) or "their city"
    channels = ["LINE", "Instagram", "Google Business", "repeat referrals"]
    tools = ["LINE", "Instagram", "Canva", "Google Sheets", "Notion"]
    return {
        "business_type": "content-led microbusiness",
        "customer_channels": channels,
        "revenue_model": "project-based packages with light recurring retainers",
        "daily_business_tasks": [
            "reply to customer inquiries",
            "draft or post short-form content",
            "send quotes and follow-up messages",
            "track payments and weekly cashflow",
            "coordinate suppliers or collaborators when needed",
        ],
        "growth_pressure": (
            f"In {location}, time spent on a new tool has to turn into more replies, bookings, or usable content quickly enough to feel defensible."
        ),
        "customer_relationship_style": "fast, direct, and proof-by-output rather than long explanation",
        "tools_currently_used": tools,
        "what_visible_win_means": [
            "a customer inquiry",
            "a postable piece of content",
            "a campaign output",
            "a faster quote or reply",
            "one visible operational improvement this week",
        ],
        "what_failure_looks_like": "Two evenings of setup still do not produce one usable output, reply, or customer action.",
    }


def _ensure_small_business_context(persona: PersonaSkill, fixes: list[str]) -> None:
    occupation = _non_empty(persona.profile.basic_identity.get("occupation")).lower()
    if "small business owner" not in occupation:
        return
    desired = _small_business_context_for(persona)
    if not persona.profile.small_business_context:
        persona.profile.small_business_context = desired
        fixes.append("small_business_context_added")
    else:
        for key, value in desired.items():
            if not persona.profile.small_business_context.get(key):
                persona.profile.small_business_context[key] = value
                fixes.append(f"small_business_context_{key}_filled")

    persona.profile.life_story["career_path"] = (
        "Runs a content-led microbusiness where client attention is won through quick proofs, clear follow-up, and output that can be used or shown fast. "
        "Tools are judged by whether they help produce one visible business result before the energy for setup runs out."
    )
    persona.profile.life_story["current_daily_routine"] = (
        "Most mornings start with LINE and Instagram message triage, checking which inquiries need replies before noon, then protecting a block for content or client work. "
        "Late afternoon often goes to quotes, payment checks, supplier or collaborator follow-up, and deciding whether a post, campaign, or tool actually moved anything. "
        "They tolerate new products when one bounded test can produce a customer-facing output this week; they stop when setup delays the first visible result."
    )
    persona.profile.daily_micro_behaviours.update(
        {
            "work_start_pattern": "Starts with message triage across LINE, Instagram, and email before deciding which work block can still produce something visible today.",
            "message_checking_pattern": "Checks customer messages in short bursts because slow replies can cost a lead, but avoids tools that turn every burst into one more dashboard ritual.",
            "shopping_moments": "More open to tools after a day when replies, quotes, or content felt scattered and the missed opportunity is still fresh.",
            "decision_moments": "Moves fastest when a product promises one visible output this week, not a full future system.",
            "when_they_are_most_open_to_new_products": "Right after a messy day of chasing replies or rebuilding content by hand.",
            "when_they_are_least_open_to_new_products": "Late at night when the product still wants setup before showing anything useful.",
        }
    )
    persona.profile.behavior_profile["manager_approval_dependence"] = "low"
    persona.profile.problem_context["jobs_to_be_done"] = [
        "reply faster without losing tone",
        "turn effort into one visible customer-facing result quickly",
        "avoid scattered follow-up across too many channels",
    ]


def _ensure_local_grounding(persona: PersonaSkill, fixes: list[str]) -> None:
    location = _non_empty(persona.profile.basic_identity.get("location")).lower()
    local = persona.profile.local_grounding_layer
    if "taipei" in location:
        local["common_apps_or_services"] = _clean_list(
            local.get("common_apps_or_services", []) or ["LINE", "Instagram", "YouTube", "LINE Pay", "PX Pay"]
        )
        local["local_discovery_channels"] = _clean_list(
            local.get("local_discovery_channels", []) or ["LINE referrals", "Google search", "YouTube explainers", "Dcard comparisons"]
        )
    elif "kuala lumpur" in location:
        local["common_apps_or_services"] = _clean_list(
            local.get("common_apps_or_services", []) or ["WhatsApp", "Grab", "Touch 'n Go", "Maybank", "YouTube", "LinkedIn"]
        )
        local["local_discovery_channels"] = _clean_list(
            local.get("local_discovery_channels", []) or ["WhatsApp referrals", "YouTube search", "LinkedIn posts", "Google comparisons"]
        )
    elif "penang" in location:
        local["common_apps_or_services"] = _clean_list(
            local.get("common_apps_or_services", []) or ["WhatsApp", "Grab", "Shopee", "Touch 'n Go", "YouTube"]
        )
    if not local.get("common_apps_or_services"):
        local["common_apps_or_services"] = ["WhatsApp", "YouTube", "Google Search"]
        fixes.append("local_grounding_apps_defaulted")


def _cross_domain_block(
    reaction_basis: str,
    first_question: str,
    positive_trigger: str,
    negative_trigger: str,
    trust_requirement: str,
    likely_objection: str,
    persona_specific_example: str,
) -> dict[str, str]:
    return {
        "reaction_basis": reaction_basis,
        "first_question": first_question,
        "positive_trigger": positive_trigger,
        "negative_trigger": negative_trigger,
        "trust_requirement": trust_requirement,
        "likely_objection": likely_objection,
        "persona_specific_example": persona_specific_example,
    }


def _ambitious_signal_cross_domain(persona: PersonaSkill) -> dict[str, Any]:
    business = persona.profile.small_business_context or _small_business_context_for(persona)
    visible_win = ", ".join(business.get("what_visible_win_means", [])[:3])
    return {
        "generic_new_product": _cross_domain_block(
            "Fast visible progress matters more than elegant long-term theory.",
            "What can I visibly achieve with this in the first week?",
            "A quick, showable result that makes the tool feel real by day three or four.",
            "Setup that asks for patience before any useful output appears.",
            "A bounded path to one real visible result with low embarrassment risk.",
            "The promise is clear, but I still do not see the first public win.",
            "If a new tool can turn one messy content task into a postable result this week, attention stays.",
        ),
        "ai_product": _cross_domain_block(
            "AI only matters if it produces leverage fast enough to use or show.",
            "Can the AI produce something useful enough to use or show this week?",
            "A first draft, lead list, or customer-facing asset that is already close to usable.",
            "The AI needs too much training or setup before it earns one real output.",
            "A concrete before-and-after proof with review control before anything goes public.",
            "If the AI needs training before it creates leverage, I will lose momentum.",
            "A caption or promo asset that only becomes good after five setup steps does not count as a fast win.",
        ),
        "subscription_product": _cross_domain_block(
            "They can justify recurring spend only if the first win repeats cleanly.",
            "What keeps this worth paying for after the first burst?",
            "Week-two and week-three usage still produces something visible without a new learning curve.",
            "Excitement peaks in onboarding, then the product becomes one more monthly maybe.",
            "Proof that the same result can be repeated once novelty wears off.",
            "If the first win is exciting but not repeatable, I will not keep the subscription.",
            "They will pay if the tool keeps helping them produce usable content or faster replies after the launch week.",
        ),
        "small_business_growth_product": _cross_domain_block(
            "Business tools are filtered through weekly proof, not founder optimism.",
            "Can this help me get more leads, replies, bookings, or content this week?",
            "One visible business result arrives without a full migration.",
            "The tool talks about growth but cannot show one near-term output.",
            "A tight test that connects effort to one visible business result quickly.",
            "Growth language is not enough; show me one visible business result.",
            f"They define a visible win as {visible_win}.",
        ),
        "workflow_or_productivity_product": _cross_domain_block(
            "They will tolerate workflow tools only if momentum survives the setup.",
            "Which repetitive task becomes easier this week?",
            "One repetitive follow-up or content-prep step shrinks immediately.",
            "The setup delays the visible win and turns the product into another maintenance loop.",
            "A reversible test that shows a faster reply, quote, or content output within days.",
            "If the first win lives behind setup, the momentum is gone.",
            "A workflow tool that helps send one quote faster this week has a chance; a full migration story does not.",
        ),
        "family_or_household_product": _cross_domain_block(
            "Home purchases still compete with energy and explainability.",
            "Does this make life easier fast enough that I would keep using it at home?",
            "The product reduces one repeat hassle without creating shared setup drama.",
            "It expects a full household routine change before any relief appears.",
            "A light start with private control and one obvious everyday convenience.",
            "I can see the concept, but it still sounds like another thing to maintain at home.",
            "A household tool earns attention only if it makes coordination or reminders lighter immediately.",
        ),
        "health_or_wellbeing_product": _cross_domain_block(
            "They can try wellbeing tools, but only if the signal is encouraging rather than moralizing.",
            "What useful change would I notice in the first week without turning this into homework?",
            "A small visible improvement feels possible without public tracking or shame loops.",
            "The product turns week-one inconsistency into a guilt spiral.",
            "Private, low-pressure use with one clear benefit and easy restart.",
            "If it feels like a compliance tool before it feels helpful, I will stop.",
            "A sleep or habit tool has a chance only if the first benefit is felt quickly and privately.",
        ),
        "financial_product": _cross_domain_block(
            "They evaluate finance tools through clarity, speed, and whether the value survives local reality.",
            "Does this save money or just create a cleaner way to think about saving money?",
            "A clearer next action or one visible local benefit appears quickly.",
            "USD-first assumptions or slow setup make the tool feel imported and theoretical.",
            "TWD logic, plain explanation, and a fast path to one concrete money action.",
            "If the first useful move is still buried in setup, this stays theoretical.",
            "They will trust a finance tool faster if it helps make one local, defensible money decision this week.",
        ),
        "education_or_child_product": _cross_domain_block(
            "They still want first-step usefulness and clear accountability.",
            "Who becomes more organized or more capable in the first week because of this?",
            "The product creates one visible improvement without endless parent or operator overhead.",
            "The product assumes more patience or admin energy than real life has.",
            "A bounded start with obvious usefulness and no hidden maintenance load.",
            "If the adult effort rises before the benefit is visible, the pitch is upside down.",
            "Even outside business, they watch for whether the product creates lift fast enough to justify attention.",
        ),
        "identity_sensitive_product": _cross_domain_block(
            "Inclusive positioning helps only if disclosure stays user-controlled.",
            "Can I use the core value first and decide later what I disclose?",
            "The product respects optional disclosure and still creates fast usefulness.",
            "Disclosure arrives before relevance or visibility defaults feel too exposed.",
            "Optional identity handling, clear purpose, and a private starting mode.",
            "If identity becomes the first task instead of the value, I am less likely to continue.",
            "They want useful first, legible later.",
        ),
        "high_friction_onboarding": _cross_domain_block(
            "This archetype loses patience when the setup story outlasts the first usable output.",
            "How soon before I see something I can actually use?",
            "The onboarding reaches one visible proof before asking for a bigger commitment.",
            "The first useful moment lives behind too many setup steps.",
            "A stripped-down path to one fast result with low public failure risk.",
            "If the first win lives behind setup, the momentum is gone.",
            "A high-friction tool survives only if the setup is paid back by a clear week-one result.",
        ),
    }


def _mature_operator_cross_domain() -> dict[str, Any]:
    return {
        "generic_new_product": _cross_domain_block(
            "Accumulated experience makes them test for month-two logic, not just comprehension.",
            "What burden leaves the user after the demo wears off?",
            "The founder can name the old upkeep that disappears and the month-two routine that remains.",
            "The pitch centralizes work but quietly transfers maintenance to the user.",
            "A believable explanation of month-two behavior, fallback handling, and ownership.",
            "I have seen this pattern before. The efficiency sounds fine, but the maintenance usually moves to the user.",
            "A clean demo means little if week three still depends on manual policing.",
        ),
        "workflow_or_productivity_product": _cross_domain_block(
            "They look for retention logic and hidden admin cost.",
            "Which existing step disappears, and who maintains the new one in month two?",
            "The workflow still holds when the team gets busy and the novelty is gone.",
            "The tool creates duplicate updates or one more upkeep ritual.",
            "A clear answer on maintenance ownership and what happens when people stop being careful.",
            "If this only works while everyone is paying attention, it is not a real operating system.",
            "They remember rollout tools that were praised early and abandoned a month later.",
        ),
        "identity_sensitive_product": _cross_domain_block(
            "They are sensitive to performative inclusion and forced disclosure more than brand theater.",
            "What can stay optional, private, and useful for someone who does not want to explain themselves?",
            "Control stays with the user and the settings do the respectful work, not just the copy.",
            "The product asks for labels, titles, or visible identity defaults before relevance.",
            "Optional disclosure, private defaults, and a clear purpose for every sensitive field.",
            "If the product performs inclusion but still forces a binary workflow, trust drops quietly.",
            "They may not argue loudly; they may simply stop trusting the system.",
        ),
        "high_friction_onboarding": _cross_domain_block(
            "Long onboarding is acceptable only when the month-two value is believable.",
            "Why is this setup burden worth carrying after the first week?",
            "The founder can show what ongoing maintenance becomes lighter, not just what configuration exists.",
            "Onboarding looks like a one-time event but actually creates another recurring admin surface.",
            "Proof that month-two behavior is lighter than today's workaround.",
            "You are asking me to do the maintenance before I know the retention logic.",
            "They want to see how the tool survives an ordinary bad week, not a launch week.",
        ),
    }


def _early_career_cross_domain() -> dict[str, Any]:
    return {
        "generic_new_product": _cross_domain_block(
            "They want small reversible trials that do not spend social capital too early.",
            "What is the smallest real test that does not make me overcommit in front of other people?",
            "A quiet pilot proves usefulness without forcing them to champion the tool immediately.",
            "The product needs them to become the internal evangelist before trust exists.",
            "Peer proof, a bounded first step, and low social risk if the test stalls.",
            "I get the problem. I just need the smallest version that works without me rebuilding my routine.",
            "They prefer one contained handoff improvement over a sweeping workflow promise.",
        ),
        "workflow_or_productivity_product": _cross_domain_block(
            "They are more open than Jordan, but still cautious about looking naive.",
            "Can I test this on one recurring miss before I ask anyone else to change?",
            "One messy handoff or follow-up loop gets cleaner without a visible rollout drama.",
            "The product assumes a full team switch before there is peer proof.",
            "A reversible trial with one believable peer-level use case.",
            "I am not against trying it. I just do not want to champion it too early and then carry the cleanup.",
            "They need a small success they can show without having to defend the whole product.",
        ),
    }


def _privacy_narrow_cross_domain() -> dict[str, Any]:
    return {
        "generic_new_product": _cross_domain_block(
            "They want proof before access, not access before proof.",
            "What is the smallest private trial that still proves the value?",
            "The product works with sample or redacted data first.",
            "The first useful step already demands broad permissions.",
            "Narrow scope, easy rollback, and private defaults.",
            "If the trial needs full access, I am not doing the trial.",
            "They stay curious only when the product starts smaller than its permission request.",
        ),
        "ai_product": _cross_domain_block(
            "AI is judged through data boundaries before novelty.",
            "Can the AI do something useful without training on everything I have?",
            "The model can work in a limited mode before it asks for more.",
            "The AI assumes broad memory or training access as a default.",
            "Minimal data scope, plain retention language, and review before action.",
            "If the AI needs the whole archive before it helps, the trust equation is upside down.",
            "They can like AI and still reject its default data appetite.",
        ),
    }


def _ensure_cross_domain_patch(persona: PersonaSkill, fixes: list[str]) -> None:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "ambitious_signal_seeker":
        persona.profile.cross_domain_product_reaction_model = _ambitious_signal_cross_domain(persona)
        fixes.append("cross_domain_visible_win_rewritten")
        return
    if archetype == "mature_operator_retention_skeptic":
        persona.profile.cross_domain_product_reaction_model.update(_mature_operator_cross_domain())
        fixes.append("cross_domain_mature_operator_rewritten")
        return
    if archetype == "early_career_practical_trial_user":
        persona.profile.cross_domain_product_reaction_model.update(_early_career_cross_domain())
        fixes.append("cross_domain_early_career_rewritten")
        return
    if archetype == "privacy_narrow_trialist":
        persona.profile.cross_domain_product_reaction_model.update(_privacy_narrow_cross_domain())
        fixes.append("cross_domain_privacy_rewritten")


def _ambitious_signal_non_work_scenes(persona: PersonaSkill) -> list[dict[str, str]]:
    name = _non_empty(persona.profile.basic_identity.get("name")) or "This persona"
    location = _non_empty(persona.profile.basic_identity.get("location")) or "their city"
    return [
        {
            "scene_id": "weekend_camera_post",
            "life_period": "20-29",
            "scene_title": "Keeping the camera because the photos were usable immediately",
            "specific_scene": (
                f"{name} bought a second-hand compact camera after a weekend street market in {location} because the photos looked good with almost no tuning. "
                "It stayed, not because the purchase was rational on paper, but because the result was visible the same night."
            ),
            "product_category": "consumer electronics or hobby purchase",
            "decision_context": "Wanted something enjoyable that produced an immediate visible result rather than another hobby that needed research first.",
            "trust_or_price_lesson": "They pay more easily when the output becomes tangible before the setup story gets long.",
            "current_product_research_impact": "This is why fast visible output matters more than feature depth in many early reactions.",
        },
        {
            "scene_id": "short_video_template_keep",
            "life_period": "20-29",
            "scene_title": "Keeping the template pack that made one postable clip fast",
            "specific_scene": (
                f"On a weeknight in {location}, {name} tried a short-video template pack and kept it only because one rough clip became good enough to post that evening. "
                "If the first usable result had needed another hour, the payment would have felt premature."
            ),
            "product_category": "creator or content tool",
            "decision_context": "Needed proof that a paid asset could create outward-facing lift immediately.",
            "trust_or_price_lesson": "Speed to a legible result buys patience; vague future efficiency does not.",
            "current_product_research_impact": "They now separate interesting creative tools from tools that actually produce visible momentum.",
        },
        {
            "scene_id": "wellbeing_app_drop",
            "life_period": "20-29",
            "scene_title": "Dropping the wellness app that still felt like homework on day four",
            "specific_scene": (
                f"{name} tried a wellbeing app after a stressful run of work in {location}, but by the fourth night it was still asking for more tracking before any pattern felt useful. "
                "The app was not bad. It just asked for discipline before giving relief."
            ),
            "product_category": "health or wellbeing product",
            "decision_context": "Wanted a quick sense of benefit, not a new compliance routine.",
            "trust_or_price_lesson": "Even non-work products lose them when setup arrives before felt relief.",
            "current_product_research_impact": "This is why high-friction onboarding lowers trust across categories, not only in software work tools.",
        },
    ]


def _ensure_non_work_scenes(persona: PersonaSkill, fixes: list[str]) -> None:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "ambitious_signal_seeker":
        persona.profile.canonical_biography["non_work_purchase_scenes"] = _ambitious_signal_non_work_scenes(persona)
        fixes.append("non_work_scenes_diversified")


def _repair_semantic_mapping(persona: PersonaSkill, fixes: list[str]) -> None:
    scenarios = persona.profile.sensitive_scenario_reactions
    if not scenarios:
        return
    scenarios.setdefault("identity_disclosure", {})
    scenarios["identity_disclosure"]["what_reduces_trust"] = (
        "Forced labels, binary-only fields, or public profile disclosure defaults that reduce user control before the product has earned relevance."
    )
    scenarios.setdefault("privacy_and_data", {})
    scenarios["privacy_and_data"]["what_reduces_trust"] = (
        "Broad permissions, unclear retention, or AI training access that arrives before a narrow proof of value."
    )
    scenarios.setdefault("health_or_wellbeing_sensitivity", {})
    scenarios["health_or_wellbeing_sensitivity"]["what_reduces_trust"] = (
        "Guilt-heavy nudges, public progress defaults, or wellbeing features that start to feel like surveillance."
    )
    fixes.append("sensitive_mapping_repaired")


def _non_work_scene_quality(persona: PersonaSkill) -> int:
    scenes = persona.profile.canonical_biography.get("non_work_purchase_scenes", [])
    if not scenes:
        return 1
    text = " ".join(_normalize_text(scene.get("specific_scene", "")) for scene in scenes)
    work_tokens = {"workflow", "dashboard", "task board", "spreadsheet", "calendar tool"}
    life_tokens = {"camera", "market", "weekend", "wellbeing", "food", "travel", "class", "hobby", "street", "night"}
    if any(token in text for token in life_tokens):
        return 5
    if any(token in text for token in work_tokens):
        return 3
    return 4


def _apply_consistency_repairs(persona: PersonaSkill, report: dict[str, Any], fixes: list[str]) -> None:
    checks = report.get("checks", {})
    age_check = checks.get("age_life_stage_consistency", {})
    if age_check.get("status") == "fail":
        new_life_stage = age_check.get("suggested_fix") or suggested_life_stage(persona)
        persona.profile.basic_identity["life_stage"] = new_life_stage
        persona.seed.life_stage = new_life_stage
        fixes.append(f"life_stage->{new_life_stage}")

    authority_check = checks.get("occupation_authority_consistency", {})
    if authority_check.get("status") == "fail":
        new_authority = authority_check.get("suggested_fix") or suggested_purchase_authority(persona)
        persona.profile.economic_profile["purchase_authority_type"] = new_authority
        persona.seed.purchase_authority_type = new_authority
        persona.profile.behavior_profile["manager_approval_dependence"] = (
            "high" if new_authority in {"manager_approval_needed", "team_budget_influencer"} else "low"
        )
        fixes.append(f"purchase_authority->{new_authority}")

    pronoun_check = checks.get("gender_pronoun_consistency", {})
    if pronoun_check.get("status") == "fail":
        _ensure_identity_language(persona, fixes)

    daily_check = checks.get("occupation_daily_routine_consistency", {})
    if daily_check.get("status") in {"fail", "warning"}:
        _ensure_small_business_context(persona, fixes)

    locale_check = checks.get("locale_app_payment_consistency", {})
    if locale_check.get("status") == "fail":
        _ensure_local_grounding(persona, fixes)

    archetype_check = checks.get("archetype_panel_role_consistency", {})
    if archetype_check.get("status") == "fail":
        archetype = _non_empty(persona.profile.panel_role_profile.get("behavioural_archetype"))
        expected = EXPECTED_PANEL_ROLE_BY_ARCHETYPE.get(archetype, "")
        if expected:
            persona.profile.panel_role_profile["panel_role"] = expected
            fixes.append(f"panel_role->{expected}")


def _apply_base_repairs(persona: PersonaSkill, fixes: list[str]) -> None:
    _ensure_identity_language(persona, fixes)
    _ensure_local_grounding(persona, fixes)
    _ensure_small_business_context(persona, fixes)
    _ensure_cross_domain_patch(persona, fixes)
    _ensure_non_work_scenes(persona, fixes)
    _repair_semantic_mapping(persona, fixes)


def upgrade_persona_to_v3_1_2(source_persona: PersonaSkill, *, random_seed: int | None = None) -> PersonaSkill:
    persona = copy.deepcopy(source_persona)
    if persona.skill_version not in {"v3.1.1", "v3.1.2"}:
        persona = upgrade_persona_to_v3_1_1(persona, random_seed=random_seed)

    persona.skill_version = "v3.1.2"
    fixes: list[str] = []
    _apply_base_repairs(persona, fixes)
    persona.profile.audit_evidence_layer.update(
        {
            "persona_generation_method": "deterministic_v3_1_2_quality_patch",
            "persona_version": "v3.1.2",
            "generator_version": "persona-generator/v3.1.2",
            "last_audited_at": datetime.now(UTC).date().isoformat(),
        }
    )
    persona.audit = {
        **persona.audit,
        **persona.profile.audit_evidence_layer,
    }
    return persona


def _build_polish_report_v3_1_2(source_dir: Path, rendered_artifacts: dict[str, str], synthetic_user_id: str) -> dict[str, Any]:
    aggregate = {
        "raw_python_dict_patterns": 0,
        "raw_json_object_leakage": 0,
        "double_punctuation": 0,
        "lowercase_ai": 0,
    }
    for filename in READABLE_MARKDOWN_FILES:
        if filename not in rendered_artifacts:
            continue
        counts = lint_markdown_cleanliness(rendered_artifacts[filename])
        for key in aggregate:
            aggregate[key] += counts[key]
    return {
        "synthetic_user_id": synthetic_user_id,
        "source_version": "v3_1_1",
        "target_version": "v3_1_2",
        "changes": {
            "v3_1_1_renderer_cleanup_retained": True,
            "generation_status_added": True,
            "consistency_gate_added": True,
            "semantic_mapping_gate_added": True,
            "rejected_candidate_flow_added": True,
        },
        "before_after_checks": aggregate,
        "remaining_known_limitations": [],
        "source_dir": str(source_dir),
        "human_review_needed": True,
    }


def _build_quality_audit_v3_1_2(
    persona: PersonaSkill,
    *,
    rendered_artifacts: dict[str, str],
    diversity_report: dict[str, Any],
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
    polish_report: dict[str, Any],
) -> dict[str, Any]:
    local_apps = _clean_list(persona.profile.local_grounding_layer.get("common_apps_or_services", []))
    quality_scores = {
        "structure_completeness": 5,
        "biography_depth": 4,
        "lived_scene_quality": 4,
        "non_work_lived_scene_quality": _non_work_scene_quality(persona),
        "local_grounding": 4 if len(local_apps) >= 4 else 3,
        "product_reaction_readiness": 4,
        "sensitive_topic_readiness": 4 if semantic_report.get("status") == "pass" else 2,
        "sensitive_salience_specificity": 4,
        "voice_distinctiveness": 4,
        "archetype_life_arc_distinctiveness": 4,
        "cross_domain_non_work_diversity": 4 if "small_business_growth_product" in persona.profile.cross_domain_product_reaction_model else 3,
        "library_distinctiveness": 4 if diversity_report.get("overall_similarity_score", 0.0) < 0.70 else 2,
        "template_leakage_risk": 4,
        "overall": 4,
    }

    if consistency_report.get("status") == "fail":
        quality_scores["library_distinctiveness"] = min(quality_scores["library_distinctiveness"], 2)
        quality_scores["overall"] = 2
    if diversity_report.get("overall_similarity_score", 0.0) > 0.70:
        quality_scores["library_distinctiveness"] = 2
        quality_scores["overall"] = 2
    if semantic_report.get("status") == "fail":
        quality_scores["sensitive_topic_readiness"] = 2
        quality_scores["overall"] = min(quality_scores["overall"], 2)

    strengths = [
        "Profile, biography, and skill outputs now share one consistent generation status gate.",
        "Cross-domain reactions are rewritten around the active archetype instead of defaulting to generic workflow skepticism.",
        "Sensitive scenarios are checked for field contamination before the persona is allowed into the library.",
    ]
    weaknesses = [
        "Some response language is still cleaner than real distracted user speech in the wild.",
        "Distinctiveness still relies on deterministic rewrites rather than deeper model-sampled variation.",
        "Non-work scenes are improved, but larger libraries will still need broader taste and leisure catalogs.",
    ]
    required_improvements = [
        "Expand direct-generation seed catalogs so upstream v1/v2 inputs need fewer downstream semantic repairs.",
        "Add richer archetype-specific local commerce cues for more cities and occupations.",
        "Introduce stronger deterministic variation for spending taste and discovery language across same-age cohorts.",
    ]
    warnings = list(consistency_report.get("warnings", [])) + list(semantic_report.get("warnings", []))
    if diversity_report.get("overall_similarity_score", 0.0) > 0.55:
        warnings.append("Similarity is below failure threshold but still worth monitoring as the library grows.")
    if not warnings:
        warnings.append("Human review is still needed for realism, even when the generator gates pass.")

    return {
        "scores": quality_scores,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "required_improvements": required_improvements[:3],
        "warnings": warnings[:5],
        "enum_leakage_check": "pass"
        if not any(token in rendered_artifacts["biography.md"] for token in RAW_ENUM_TOKENS)
        else "fail",
        "abstract_language_check": "watch_for_shared_behavioral_language",
        "local_grounding_check": "pass" if len(local_apps) >= 4 else "needs_attention",
        "sensitive_scenario_check": semantic_report.get("status", "warning"),
        "similarity_check": (
            "pass" if diversity_report.get("overall_similarity_score", 0.0) < 0.70 else "failed_distinctiveness_threshold"
        ),
        "human_review_needed": True,
    }


def _build_generation_notes_v3_1_2(
    persona: PersonaSkill,
    *,
    diversity_report: dict[str, Any],
    quality_audit: dict[str, Any],
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
    polish_report: dict[str, Any],
    generation_status: dict[str, Any],
    random_seed: int | None,
    source_version_dir: Path,
) -> dict[str, Any]:
    return {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": "persona-generator/v3.1.2",
        "prompt_versions": PROMPT_VERSIONS,
        "model_used": "deterministic-quality-gated-render-v3_1_2",
        "generated_at": _timestamp(),
        "random_seed": random_seed,
        "source_version_dir": str(source_version_dir),
        "comparison_persona_ids": diversity_report.get("compared_against", []),
        "quality_score_estimate": quality_audit["scores"],
        "consistency_warnings": consistency_report.get("warnings", []),
        "stereotype_warnings": [],
        "missing_fields": [],
        "human_review_needed": True,
        "llm_ready_slots": [
            {
                "prompt_version": prompt_version,
                "provider": "",
                "model": "",
                "seed": random_seed,
                "input_context_ref": persona.profile.synthetic_user_id,
            }
            for prompt_version in PROMPT_VERSIONS
        ],
        "generation_status": generation_status,
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
            "high_similarity_dimensions": diversity_report.get("high_similarity_dimensions", []),
        },
        "consistency_report_summary": {
            "status": consistency_report.get("status", "warning"),
            "hard_fail_reasons": consistency_report.get("hard_fail_reasons", []),
        },
        "semantic_mapping_report_summary": {
            "status": semantic_report.get("status", "warning"),
            "failed_fields": semantic_report.get("failed_fields", []),
        },
        "polish_report_summary": {
            "target_version": polish_report.get("target_version", "v3_1_2"),
            "remaining_known_limitations": polish_report.get("remaining_known_limitations", []),
        },
        "source_version": "v3_1_1",
        "target_version": "v3_1_2",
    }


def _diff_markdown_v3_1_1_to_v3_1_2(
    persona: PersonaSkill,
    *,
    generation_status: dict[str, Any],
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
    diversity_report: dict[str, Any],
) -> str:
    lines = [
        f"# {persona.profile.basic_identity.get('name', '')} - V3.1.1 to V3.1.2 Diff",
        "",
        "## Quality Patch Scope",
        "- Added cross-field consistency validation.",
        "- Added sensitive semantic mapping validation.",
        "- Added generation status gate and rejected-candidate flow.",
        "- Retained V3.1.1 markdown polish and response-variant improvements.",
        "",
        "## Generator Status",
        f"- Status: {generation_status.get('status', '')}",
        f"- Can enter library: {generation_status.get('can_enter_library', False)}",
        f"- Can enter validation runner: {generation_status.get('can_enter_validation_runner', False)}",
        "",
        "## Consistency Fixes",
        f"- Hard fail reasons: {', '.join(consistency_report.get('hard_fail_reasons', [])) or 'none'}",
        f"- Auto fixes applied: {', '.join(consistency_report.get('auto_fixes_applied', [])) or 'none'}",
        "",
        "## Sensitive Mapping Fixes",
        f"- Failed fields after final pass: {', '.join(semantic_report.get('failed_fields', [])) or 'none'}",
        f"- Auto fixes applied: {', '.join(semantic_report.get('auto_fixes_applied', [])) or 'none'}",
        "",
        "## Distinctiveness Snapshot",
        f"- Overall similarity: {diversity_report.get('overall_similarity_score', 0.0)}",
        f"- High-similarity dimensions: {', '.join(diversity_report.get('high_similarity_dimensions', [])) or 'none'}",
        "",
        "## Applied Behaviour Changes",
        "- Rewrote archetype-specific cross-domain reactions where needed.",
        "- Enforced at least one true non-work lived scene for the ambitious signal seeker path.",
        "- Added explicit identity language and corrected authority/life-stage mismatches.",
    ]
    return "\n".join(lines).strip() + "\n"


def _render_artifacts(persona: PersonaSkill) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    example_responses = _example_responses(persona)
    response_variants = _response_variants(persona)
    rendered = {
        "persona.md": render_persona_md_v3_1_1(persona),
        "biography.md": render_biography_md_v3_1_1(persona),
        "research_kernel.md": render_research_kernel_md_v3_1_1(persona),
        "persona.skill.md": render_persona_skill_md_v3_1_1(persona, example_responses, response_variants),
        "local_grounding.md": render_local_grounding_md_v3(persona).strip() + "\n",
        "sensitive_scenarios.md": render_sensitive_scenarios_md_v3_1_1(persona),
    }
    return rendered, example_responses, response_variants


def _save_rejected_candidate(
    *,
    output_dir: Path,
    persona: PersonaSkill,
    failure_report: dict[str, Any],
    diversity_report: dict[str, Any],
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target_dir = output_dir / "rejected" / persona.profile.synthetic_user_id / timestamp
    ensure_dir(target_dir)
    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "failure_report.json", failure_report)
    write_json(target_dir / "diversity_report.json", diversity_report)
    write_json(target_dir / "consistency_report.json", consistency_report)
    write_json(target_dir / "semantic_mapping_report.json", semantic_report)
    return target_dir


def _build_failure_report(
    *,
    generation_status: dict[str, Any],
    attempts: int,
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
    diversity_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "failed_regeneration",
        "attempts": attempts,
        "generation_status": {**generation_status, "status": "failed_regeneration", "can_enter_library": False, "can_enter_validation_runner": False},
        "consistency_report_summary": {
            "status": consistency_report.get("status", "warning"),
            "hard_fail_reasons": consistency_report.get("hard_fail_reasons", []),
        },
        "semantic_report_summary": {
            "status": semantic_report.get("status", "warning"),
            "failed_fields": semantic_report.get("failed_fields", []),
        },
        "diversity_report_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "high_similarity_dimensions": diversity_report.get("high_similarity_dimensions", []),
        },
    }


def write_v3_1_2_persona_folder(
    persona: PersonaSkill,
    *,
    source_version_dir: Path,
    root_data_dir: Path,
    diversity_report: dict[str, Any],
    consistency_report: dict[str, Any],
    semantic_report: dict[str, Any],
    polish_report: dict[str, Any],
    generation_status: dict[str, Any],
    random_seed: int | None,
) -> Path:
    persona_root = root_data_dir / persona.profile.synthetic_user_id
    ensure_dir(persona_root)
    target_dir = persona_root / "v3_1_2"
    ensure_dir(target_dir)

    rendered_artifacts, example_responses, response_variants = _render_artifacts(persona)
    example_quality = build_example_response_quality(
        example_responses,
        response_variants,
        persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
    )
    quality_audit = _build_quality_audit_v3_1_2(
        persona,
        rendered_artifacts=rendered_artifacts,
        diversity_report=diversity_report,
        consistency_report=consistency_report,
        semantic_report=semantic_report,
        polish_report=polish_report,
    )
    rendered_artifacts["v3_1_1_to_v3_1_2_diff.md"] = _diff_markdown_v3_1_1_to_v3_1_2(
        persona,
        generation_status=generation_status,
        consistency_report=consistency_report,
        semantic_report=semantic_report,
        diversity_report=diversity_report,
    )
    generation_notes = _build_generation_notes_v3_1_2(
        persona,
        diversity_report=diversity_report,
        quality_audit=quality_audit,
        consistency_report=consistency_report,
        semantic_report=semantic_report,
        polish_report=polish_report,
        generation_status=generation_status,
        random_seed=random_seed,
        source_version_dir=source_version_dir,
    )

    persona.profile.generation_status = generation_status
    persona.audit = {
        **persona.audit,
        "quality_audit": quality_audit,
        "example_response_quality": example_quality,
        "generation_status": generation_status,
        "consistency_report_summary": {
            "status": consistency_report.get("status", "warning"),
            "hard_fail_reasons": consistency_report.get("hard_fail_reasons", []),
        },
        "semantic_mapping_report_summary": {
            "status": semantic_report.get("status", "warning"),
            "failed_fields": semantic_report.get("failed_fields", []),
        },
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
        },
        "generator_version": "persona-generator/v3.1.2",
    }

    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "audit.json", persona.to_audit_payload())
    write_json(target_dir / "generation_notes.json", generation_notes)
    write_json(target_dir / "diversity_report.json", diversity_report)
    write_json(target_dir / "consistency_report.json", consistency_report)
    write_json(target_dir / "semantic_mapping_report.json", semantic_report)
    write_json(target_dir / "polish_report.json", polish_report)
    for filename, content in rendered_artifacts.items():
        (target_dir / filename).write_text(content, encoding="utf-8")
    return target_dir


def _evaluate_candidate(
    persona: PersonaSkill,
    *,
    comparison_pool: list[PersonaSkill],
    source_version_dir: Path,
    fixes: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    consistency_report = build_consistency_report_v3_1_2(persona, auto_fixes_applied=fixes)
    if consistency_report.get("status") != "pass":
        _apply_consistency_repairs(persona, consistency_report, fixes)
        consistency_report = build_consistency_report_v3_1_2(persona, auto_fixes_applied=fixes)

    semantic_report = build_semantic_mapping_report_v3_1_2(persona, auto_fixes_applied=fixes)
    if semantic_report.get("status") == "fail":
        _repair_semantic_mapping(persona, fixes)
        semantic_report = build_semantic_mapping_report_v3_1_2(persona, auto_fixes_applied=fixes)

    rendered_artifacts, _example_responses_map, _response_variants_map = _render_artifacts(persona)
    consistency_report = build_consistency_report_v3_1_2(
        persona,
        rendered_artifacts=rendered_artifacts,
        auto_fixes_applied=fixes,
    )
    diversity_report = build_diversity_report_v3_1(persona, comparison_pool)
    polish_report = _build_polish_report_v3_1_2(source_version_dir, rendered_artifacts, persona.profile.synthetic_user_id)
    generation_status = _build_generation_status(
        consistency_report=consistency_report,
        diversity_report=diversity_report,
        semantic_report=semantic_report,
        polish_report=polish_report,
    )
    return consistency_report, semantic_report, diversity_report, polish_report, generation_status, rendered_artifacts


def _targeted_regeneration(persona: PersonaSkill, *, fixes: list[str]) -> None:
    _ensure_identity_language(persona, fixes)
    _ensure_small_business_context(persona, fixes)
    _ensure_cross_domain_patch(persona, fixes)
    _ensure_non_work_scenes(persona, fixes)
    _repair_semantic_mapping(persona, fixes)


def generate_v3_1_2_personas(
    *,
    persona_ids: list[str],
    source_dir: Path,
    output_dir: Path,
    compare_against_dir: Path,
    against_persona_ids: list[str] | None = None,
    random_seed_offset: int = 0,
    max_attempts: int = 3,
) -> list[Path]:
    ensure_dir(output_dir)
    selected_ids = list(dict.fromkeys(persona_ids))
    source_personas = {
        persona_id: load_persona(_resolve_persona_folder(source_dir, persona_id, ("v3_1_1", "v3_1", "v3", "v2", "root")))
        for persona_id in selected_ids
    }
    provisional = {
        persona_id: upgrade_persona_to_v3_1_2(source_personas[persona_id], random_seed=random_seed_offset + index)
        for index, persona_id in enumerate(selected_ids)
    }

    external_comparisons: dict[str, PersonaSkill] = {}
    for comparison_id in [persona_id for persona_id in (against_persona_ids or []) if persona_id not in selected_ids]:
        external_comparisons[comparison_id] = _load_persona_from_dir(
            compare_against_dir,
            comparison_id,
            ("v3_1_2", "v3_1_1", "v3_1", "v3", "v2", "root"),
        )

    written_paths: list[Path] = []
    for index, persona_id in enumerate(selected_ids):
        source_version_dir = _resolve_persona_folder(source_dir, persona_id, ("v3_1_1", "v3_1", "v3", "v2", "root"))
        comparison_pool = [provisional[other_id] for other_id in selected_ids if other_id != persona_id] + list(external_comparisons.values())
        candidate = provisional[persona_id]
        final_reports: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None = None

        for attempt in range(1, max_attempts + 1):
            fixes: list[str] = []
            if attempt > 1:
                _targeted_regeneration(candidate, fixes=fixes)
            consistency_report, semantic_report, diversity_report, polish_report, generation_status, _rendered = _evaluate_candidate(
                candidate,
                comparison_pool=comparison_pool,
                source_version_dir=source_version_dir,
                fixes=fixes,
            )
            final_reports = (consistency_report, semantic_report, diversity_report, polish_report, generation_status)
            if generation_status["status"] not in {"failed_consistency", "failed_distinctiveness", "failed_semantic_mapping"}:
                break
        else:
            pass

        assert final_reports is not None
        consistency_report, semantic_report, diversity_report, polish_report, generation_status = final_reports
        if generation_status["status"] in {"failed_consistency", "failed_distinctiveness", "failed_semantic_mapping"}:
            failure_report = _build_failure_report(
                generation_status=generation_status,
                attempts=max_attempts,
                consistency_report=consistency_report,
                semantic_report=semantic_report,
                diversity_report=diversity_report,
            )
            _save_rejected_candidate(
                output_dir=output_dir,
                persona=candidate,
                failure_report=failure_report,
                diversity_report=diversity_report,
                consistency_report=consistency_report,
                semantic_report=semantic_report,
            )
            continue

        written_paths.append(
            write_v3_1_2_persona_folder(
                candidate,
                source_version_dir=source_version_dir,
                root_data_dir=output_dir,
                diversity_report=diversity_report,
                consistency_report=consistency_report,
                semantic_report=semantic_report,
                polish_report=polish_report,
                generation_status=generation_status,
                random_seed=random_seed_offset + index,
            )
        )
    return written_paths


def run_distinctiveness_check_v3_1_2(
    *,
    base_dir: Path,
    persona_id: str,
    against_persona_ids: list[str],
    preferred_versions: tuple[str, ...] = ("v3_1_2", "v3_1_1", "v3_1", "v3", "v2", "root"),
) -> dict[str, Any]:
    candidate = _load_persona_from_dir(base_dir, persona_id, preferred_versions)
    comparisons = [
        _load_persona_from_dir(base_dir, other_id, preferred_versions)
        for other_id in against_persona_ids
        if other_id != persona_id
    ]
    return build_diversity_report_v3_1(candidate, comparisons)


def validate_v3_1_2_persona_folder(folder: Path) -> dict[str, Any]:
    missing_files = [filename for filename in V3_1_2_REQUIRED_FILES if not (folder / filename).exists()]
    consistency_warnings: list[str] = []
    if missing_files:
        return {
            "missing_fields": missing_files,
            "consistency_warnings": consistency_warnings,
            "stereotype_warnings": [],
            "quality_score_estimate": {},
            "human_review_needed": True,
        }

    audit_payload = read_json(folder / "audit.json")
    profile_payload = read_json(folder / "profile.json")
    consistency_report = read_json(folder / "consistency_report.json")
    semantic_report = read_json(folder / "semantic_mapping_report.json")
    diversity_report = read_json(folder / "diversity_report.json")
    quality_audit = audit_payload["audit"].get("quality_audit", {})
    generation_status = audit_payload["audit"].get("generation_status", {})

    for filename in READABLE_MARKDOWN_FILES:
        path = folder / filename
        if not path.exists():
            continue
        counts = lint_markdown_cleanliness(path.read_text(encoding="utf-8"))
        if counts["raw_python_dict_patterns"]:
            consistency_warnings.append(f"Raw object leakage detected in {filename}.")
        if counts["raw_json_object_leakage"]:
            consistency_warnings.append(f"Raw JSON object leakage detected in {filename}.")
        if any(token in path.read_text(encoding="utf-8") for token in RAW_ENUM_TOKENS):
            consistency_warnings.append(f"Enum leakage detected in {filename}.")

    if consistency_report.get("status") == "fail" and generation_status.get("can_enter_library"):
        consistency_warnings.append("Failed consistency report should block library entry.")
    if semantic_report.get("status") == "fail" and quality_audit.get("scores", {}).get("sensitive_topic_readiness", 5) > 2:
        consistency_warnings.append("Sensitive readiness score is too high for failed semantic mapping.")
    if diversity_report.get("overall_similarity_score", 0.0) > 0.70 and generation_status.get("can_enter_library"):
        consistency_warnings.append("Distinctiveness hard fail should block library entry.")
    if all(value == 5 for value in quality_audit.get("scores", {}).values()):
        consistency_warnings.append("quality_audit scores are unrealistically all perfect.")
    if not profile_payload.get("generation_status"):
        consistency_warnings.append("generation_status is missing from profile.json.")

    return {
        "missing_fields": missing_files,
        "consistency_warnings": consistency_warnings,
        "stereotype_warnings": [],
        "quality_score_estimate": quality_audit.get("scores", {}),
        "human_review_needed": quality_audit.get("human_review_needed", True),
    }


def validate_v3_1_2_persona_library(base_dir: Path) -> dict[str, Any]:
    if not base_dir.exists():
        return {"library_size": 0, "persona_reports": [], "issue_count": 0, "warning_count": 0}

    persona_reports: list[dict[str, Any]] = []
    for persona_id in [value for value in _persona_ids_in(base_dir) if value != "rejected"]:
        folder = base_dir / persona_id / "v3_1_2"
        if not folder.exists():
            continue
        persona_reports.append({"persona_id": persona_id, **validate_v3_1_2_persona_folder(folder)})

    issue_count = sum(len(report["missing_fields"]) + len(report["consistency_warnings"]) for report in persona_reports)
    return {
        "library_size": len(persona_reports),
        "persona_reports": persona_reports,
        "issue_count": issue_count,
        "warning_count": 0,
    }
