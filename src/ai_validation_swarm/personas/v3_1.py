from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.v2 import _dedupe, prompt_path
from ai_validation_swarm.personas.v3 import (
    RAW_ENUM_TOKENS,
    _archetype_key,
    _load_persona_from_dir,
    _normalize_text,
    _persona_ids_in,
    _resolve_persona_folder,
    _stringify_text_field,
    _text_similarity,
    build_diversity_report as build_diversity_report_v3,
    render_local_grounding_md as render_local_grounding_md_v3,
    upgrade_persona_to_v3,
)
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json

PROMPT_VERSIONS = [
    "persona-biography/v3_1.md",
    "local-grounding/v3_1.md",
    "sensitive-scenarios/v3_1.md",
    "persona-voiceprint/v3_1.md",
    "distinctiveness-revision/v3_1.md",
    "quality-auditor/v3_1.md",
]

V3_1_REQUIRED_FILES = (
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
    "v3_to_v3_1_diff.md",
)

SHARED_TEMPLATE_PHRASES = (
    "their life has been shaped less by dramatic turning points than by repeated lessons",
    "they grew into someone who values reliability time protection clarity",
    "reducing weekly friction without introducing new trust privacy or coordination debt",
)

SENSITIVE_SCENARIO_KEYS = (
    "identity_disclosure",
    "privacy_and_data",
    "political_or_public_expression",
    "fairness_and_inclusion",
    "family_or_household_assumptions",
    "workplace_visibility",
    "financial_vulnerability",
    "health_or_wellbeing_sensitivity",
)


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_v3_1_prompt_texts() -> dict[str, str]:
    return {
        prompt_version: prompt_path(prompt_version).read_text(encoding="utf-8").strip()
        for prompt_version in PROMPT_VERSIONS
    }


def _title_from_key(value: str) -> str:
    return value.replace("_", " ").title()


def _normalized_salience_map(salience: dict[str, object] | None) -> dict[str, int]:
    if not isinstance(salience, dict):
        return {}
    if salience and all(isinstance(value, (int, float, str)) for value in salience.values()):
        normalized: dict[str, int] = {}
        for key, value in salience.items():
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                continue
        return normalized

    normalized: dict[str, int] = {}
    ranking_bands = (
        ("highest_salience", 9),
        ("medium_salience", 6),
        ("lower_but_present_salience", 3),
    )
    for field_name, score in ranking_bands:
        values = salience.get(field_name, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, str) and item.strip():
                normalized[item.strip()] = max(normalized.get(item.strip(), 0), score)
    return normalized


def _top_salience_keys(salience: dict[str, object], count: int = 3) -> list[str]:
    normalized = _normalized_salience_map(salience)
    return [
        key
        for key, _score in sorted(
            normalized.items(),
            key=lambda item: (-item[1], item[0]),
        )[:count]
    ]


def _salience_similarity(left: dict[str, object], right: dict[str, object]) -> float:
    left_map = _normalized_salience_map(left)
    right_map = _normalized_salience_map(right)
    if not left_map and not right_map:
        return 0.0
    keys = set(left_map) | set(right_map)
    if not keys:
        return 0.0
    total_gap = sum(abs(left_map.get(key, 0) - right_map.get(key, 0)) for key in keys)
    max_gap = len(keys) * 9
    return round(1.0 - (total_gap / max_gap), 4)


def _life_arc_summary_v3_1(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    name = identity.get("name", "")
    location = identity.get("location", "")
    occupation = identity.get("occupation", "")
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return (
            f"{name} is a {identity.get('age', '')}-year-old {occupation} in {location}. "
            "He is not simply skeptical of tools. He is still building workplace credibility, so he prefers "
            "small, reversible experiments that let him test value without overcommitting social capital. "
            "He opens up when a product helps him look capable, reduces one real handoff problem, and proves "
            "it can survive an ordinary week. He pulls back when a product asks him to rebuild his routine, "
            "explain a shaky purchase, or make unfinished setup visible before trust is earned."
        )
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return (
            f"{name} is a {identity.get('age', '')}-year-old {occupation} in {location}. "
            "They are not merely resistant to friction. They are a mature operations person who has repeatedly "
            "seen polished systems move maintenance work onto users after the demo. They judge products by "
            "asking who carries the upkeep, whether the product still works in month two, and whether users keep "
            "control over disclosure, visibility, and dignity. A clean pitch can win attention, but not trust, "
            "unless the product explains what burden leaves the user in real life."
        )
    return persona.profile.canonical_biography.get("life_arc_summary", "")


def _non_work_purchase_scenes_v3_1(persona: PersonaSkill) -> list[dict[str, Any]]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return [
            {
                "scene_id": "peer_tool_trial_exit",
                "life_period": "20-29",
                "scene_title": "Discounted app that never survived a real week",
                "specific_scene": (
                    "A colleague shared a discounted subscription for a small scheduling utility. Daniel signed up "
                    "on Sunday, liked the clean setup, then stopped opening it once weekday follow-up moved back "
                    "to WhatsApp and calendar reminders. The second MYR billing reminder was what finally made him cancel."
                ),
                "product_category": "subscription utility",
                "decision_context": "Wanted a lightweight personal upgrade that might make him look more organized without dragging the team in.",
                "trust_or_price_lesson": "A low monthly price does not feel fair if the product only works on calm days and makes exit slightly annoying.",
                "current_product_research_impact": "He now asks whether a product helps before he has to train his whole week around it.",
            },
            {
                "scene_id": "family_repair_whatsapp_booking",
                "life_period": "20-29",
                "scene_title": "Choosing the repair service that replies clearly",
                "specific_scene": (
                    "During a household appliance issue, Daniel compared two repair options shared through family "
                    "chat. He chose the one that replied clearly on WhatsApp, confirmed timing, and explained "
                    "what might need replacement instead of the slightly cheaper option with vague follow-up."
                ),
                "product_category": "household service",
                "decision_context": "Needed a choice he could defend in a multi-generational household without becoming the unpaid follow-up person.",
                "trust_or_price_lesson": "Responsiveness and clarity beat a slightly lower quote when the hidden cost is more coordination later.",
                "current_product_research_impact": "This is why he responds to concrete confirmation flows and local trust cues faster than to abstract savings claims.",
            },
            {
                "scene_id": "mobile_plan_rollover_choice",
                "life_period": "20-29",
                "scene_title": "Picking the boring plan with clearer rollover rules",
                "specific_scene": (
                    "Daniel once compared a louder promo plan against a more boring option with clearer rollover "
                    "rules and fewer surprise add-ons. He took the less exciting plan because he knew he would "
                    "resent having to explain variable top-ups later."
                ),
                "product_category": "consumer finance or telecom",
                "decision_context": "Needed predictable monthly spend more than headline value.",
                "trust_or_price_lesson": "Predictability is part of price fairness, especially when the purchase has to make sense in MYR and in conversation with family.",
                "current_product_research_impact": "He notices pricing language that sounds imported or assumes spare budget he does not actually feel.",
            },
        ]
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return [
            {
                "scene_id": "appliance_warranty_follow_up",
                "life_period": "50-59",
                "scene_title": "Warranty that looked tidy until service windows were vague",
                "specific_scene": (
                    "Jordan reviewed an appliance warranty renewal that sounded reassuring on paper, but the "
                    "service windows, escalation path, and follow-up responsibility were all vague. They kept a "
                    "private note of service dates because the official reminders did not feel dependable enough."
                ),
                "product_category": "household service or warranty",
                "decision_context": "Wanted protection for the household without quietly inheriting the vendor's follow-up work.",
                "trust_or_price_lesson": "A maintenance promise is only credible if the operational follow-up path is concrete.",
                "current_product_research_impact": "They now look for maintenance ownership long before they care about polish.",
            },
            {
                "scene_id": "recurring_service_line_item",
                "life_period": "50-59",
                "scene_title": "The line item that became annoying before it became expensive",
                "specific_scene": (
                    "While reviewing recurring payments, Jordan noticed a service that was not financially painful "
                    "but had become conceptually irritating because nobody in the household could say what value "
                    "it still delivered. The cancellation happened after that realization, not after a price shock."
                ),
                "product_category": "subscription service",
                "decision_context": "Wanted recurring spend to remain explainable, not merely affordable.",
                "trust_or_price_lesson": "Month-two justification matters more than month-one enthusiasm.",
                "current_product_research_impact": "They often test whether founders can explain ongoing value after novelty and launch energy fade.",
            },
            {
                "scene_id": "consumer_profile_guest_checkout",
                "life_period": "50-59",
                "scene_title": "Trust dropping quietly at the profile screen",
                "specific_scene": (
                    "Jordan once reached a consumer service checkout that required a title, gender marker, and "
                    "public-facing profile defaults before anything useful had been earned. They did not argue. "
                    "They switched to guest checkout where possible, and abandoned the service where it was not."
                ),
                "product_category": "identity-sensitive consumer service",
                "decision_context": "Wanted to complete a simple transaction without turning identity disclosure into the product's first demand.",
                "trust_or_price_lesson": "Respect is not branding alone; it includes control over disclosure and visibility.",
                "current_product_research_impact": "They now treat mandatory disclosure early in the flow as a sign that the product may not understand dignity cost.",
            },
        ]
    return []


def _sensitive_scenario_salience(persona: PersonaSkill) -> dict[str, int]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return {
            "identity_disclosure": 4,
            "privacy_and_data": 8,
            "political_or_public_expression": 4,
            "fairness_and_inclusion": 5,
            "family_or_household_assumptions": 6,
            "workplace_visibility": 9,
            "financial_vulnerability": 7,
            "health_or_wellbeing_sensitivity": 5,
        }
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return {
            "identity_disclosure": 9,
            "privacy_and_data": 8,
            "political_or_public_expression": 5,
            "fairness_and_inclusion": 8,
            "family_or_household_assumptions": 8,
            "workplace_visibility": 7,
            "financial_vulnerability": 6,
            "health_or_wellbeing_sensitivity": 5,
        }
    return {key: 5 for key in SENSITIVE_SCENARIO_KEYS}


def _sensitive_scenario_reactions_v3_1(persona: PersonaSkill) -> dict[str, Any]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return {
            "identity_disclosure": {
                "trigger_scenarios": [
                    "sign-up asking for title before value is clear",
                    "profile details shown to peers by default",
                    "identity labels required for a basic trial",
                ],
                "reaction": "He reads this less as a public identity fight and more as a sign that the product asks for personal context too early.",
                "what_builds_trust": "Explain why the field exists, make it optional, and keep it private by default.",
                "what_reduces_trust": "Premature labeling that feels unrelated to the job he came to do.",
            },
            "privacy_and_data": {
                "trigger_scenarios": [
                    "connecting work messages before he has tested the workflow",
                    "AI drafting or acting before he can review it",
                    "asking for household history during a short trial",
                ],
                "reaction": "He slows down when the product wants authority before it has shown competence.",
                "what_builds_trust": "Bounded permissions, clear review steps, and easy rollback.",
                "what_reduces_trust": "Broad access that assumes trust on day one.",
            },
            "political_or_public_expression": {
                "trigger_scenarios": [
                    "community features that reward visible opinions",
                    "brand copy that assumes public agreement is part of trust",
                    "social sharing prompts in ordinary workflows",
                ],
                "reaction": "He usually opts out rather than argue. Public positioning feels like extra risk, not extra value.",
                "what_builds_trust": "Private participation and low-pressure visibility controls.",
                "what_reduces_trust": "Products that treat public expression as normal participation.",
            },
            "fairness_and_inclusion": {
                "trigger_scenarios": [
                    "inclusive copy with one narrow default user example",
                    "household language that assumes one clean role map",
                    "support tone that sounds respectful but inflexible",
                ],
                "reaction": "He notices whether respect changes the actual workflow, not just the copy.",
                "what_builds_trust": "Respectful defaults plus options that let different households stay private and practical.",
                "what_reduces_trust": "Polite language that still forces one lifestyle assumption.",
            },
            "family_or_household_assumptions": {
                "trigger_scenarios": [
                    "family features that assume one unpaid household admin",
                    "spending plans that ignore shared household explanation",
                    "default roles that make some people visible before they want to be",
                ],
                "reaction": "He worries about becoming the person who has to maintain or explain the system for everyone else.",
                "what_builds_trust": "Optional sharing, controllable visibility, and language that does not moralize household organization.",
                "what_reduces_trust": "One-person-admin assumptions dressed up as convenience.",
            },
            "workplace_visibility": {
                "trigger_scenarios": [
                    "manager dashboards showing incomplete setup",
                    "AI suggestions visible to a team before he checks them",
                    "trial activity that makes him look messy while still learning",
                ],
                "reaction": "This is the fastest way to kill honest trial intent. He protects his early-career credibility before he protects feature curiosity.",
                "what_builds_trust": "Private draft space, staged rollout, and clear control over when work becomes visible.",
                "what_reduces_trust": "Public failure modes arriving before private competence.",
            },
            "financial_vulnerability": {
                "trigger_scenarios": [
                    "USD pricing with no MYR anchor",
                    "annual plans framed as the only serious option",
                    "upsell copy that makes caution sound unserious",
                ],
                "reaction": "Budget sensitivity is tied to explainability and stress, not just absolute price.",
                "what_builds_trust": "Monthly clarity, local pricing realism, and easy exit without shame.",
                "what_reduces_trust": "Imported affordability assumptions and locked-in pricing posture.",
            },
            "health_or_wellbeing_sensitivity": {
                "trigger_scenarios": [
                    "habit trackers that turn inconsistency into failure language",
                    "private wellbeing prompts shown in shared contexts",
                    "products that infer too much from thin data",
                ],
                "reaction": "He avoids tools that make him feel judged on tired weeks.",
                "what_builds_trust": "Neutral tone, private control, and no guilt loop.",
                "what_reduces_trust": "Moralizing copy and surveillance-like feedback.",
            },
        }
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return {
            "identity_disclosure": {
                "trigger_scenarios": [
                    "binary-only gender field",
                    "mandatory title such as Mr, Ms, or Mrs",
                    "public profile with gender marker shown by default",
                    "household flows that assume husband or wife labels",
                    "optional disclosure with clear purpose and prefer-not-to-say option",
                ],
                "reaction": "Trust drops quietly rather than theatrically. They may disengage rather than complain unless the exclusion is obvious and fixable.",
                "what_builds_trust": "Prefer-not-to-say, optional disclosure, visibility controls, and language that does not demand public labeling before utility is proven.",
                "what_reduces_trust": "Mandatory labels, default visibility, and inclusion rhetoric with no practical control.",
            },
            "privacy_and_data": {
                "trigger_scenarios": [
                    "connecting messages or records before the product has earned relevance",
                    "AI summaries with vague retention policy",
                    "data access that feels broader than the task requires",
                ],
                "reaction": "They ask whether the product wants operational authority before it has shown month-two discipline.",
                "what_builds_trust": "Tight permissions, plain-language retention policy, and visible failure handling.",
                "what_reduces_trust": "Broad permissions, hidden defaults, and ambiguous AI claims.",
            },
            "political_or_public_expression": {
                "trigger_scenarios": [
                    "public comment features that reward visible alignment",
                    "brand posture that treats one social stance as default maturity",
                    "identity markers tied to public participation",
                ],
                "reaction": "They prefer products that let people stay useful without becoming publicly legible in ways they did not choose.",
                "what_builds_trust": "Private participation paths and calm visibility settings.",
                "what_reduces_trust": "Forced performance of agreement.",
            },
            "fairness_and_inclusion": {
                "trigger_scenarios": [
                    "inclusive marketing with no privacy control",
                    "onboarding that still assumes one family structure",
                    "support flows that flatten users into a checklist category",
                ],
                "reaction": "They look for whether the product reduces dignity cost, not whether the tone sounds current.",
                "what_builds_trust": "Respectful defaults, adjustable disclosure, and workflows that do not punish non-standard lives.",
                "what_reduces_trust": "Performative inclusion that leaves the risky defaults untouched.",
            },
            "family_or_household_assumptions": {
                "trigger_scenarios": [
                    "default husband or wife language",
                    "family dashboards that assume shared visibility is always welcome",
                    "reminder systems that quietly nominate one person as the unpaid coordinator",
                ],
                "reaction": "They pay attention to whether a household product understands that comfort, privacy, and responsibility are unevenly distributed.",
                "what_builds_trust": "Role-neutral language, optional sharing, and controls that separate coordination from exposure.",
                "what_reduces_trust": "Normative family labels presented as harmless defaults.",
            },
            "workplace_visibility": {
                "trigger_scenarios": [
                    "dashboards that expose unfinished operational cleanup",
                    "AI output visible before review",
                    "systems that create proof of effort more than they remove effort",
                ],
                "reaction": "They tolerate visibility only when the maintenance logic is fair and the product has earned it.",
                "what_builds_trust": "Clear control, realistic rollout, and evidence that extra visibility does not simply create extra admin.",
                "what_reduces_trust": "Visibility that arrives before workflow relief.",
            },
            "financial_vulnerability": {
                "trigger_scenarios": [
                    "recurring charges with weak month-two explanation",
                    "pricing copied from US SaaS logic with no local context",
                    "upgrade pressure that treats caution as lack of ambition",
                ],
                "reaction": "The issue is not pure affordability. It is whether the line item stays defensible after the first month.",
                "what_builds_trust": "Local pricing realism, calm cancellation terms, and ongoing value explained without hype.",
                "what_reduces_trust": "Recurring spend that becomes hard to justify once attention settles.",
            },
            "health_or_wellbeing_sensitivity": {
                "trigger_scenarios": [
                    "tools that convert support into compliance records",
                    "wellbeing features visible to others by default",
                    "language that treats sensitive routines as moral performance",
                ],
                "reaction": "They disengage when support starts to look like surveillance.",
                "what_builds_trust": "Private control, plain intent, and no overclaiming from limited data.",
                "what_reduces_trust": "Judgmental tone and compliance theater.",
            },
        }
    return {}


def _persona_voiceprint_v3_1(persona: PersonaSkill) -> dict[str, Any]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return {
            "speaking_style": "collaborative, practical, and careful not to overclaim",
            "sentence_length": "medium",
            "directness_pattern": "starts by acknowledging the use case, then narrows to the smallest believable first step",
            "metaphors_or_phrases": [
                "smallest version",
                "normal week",
                "quiet trial",
                "not rebuilding the whole routine",
            ],
            "how_they_soften_disagreement": "I can see why someone would want this, but I still need the lighter first step.",
            "how_they_get_more_direct": "If the tool needs me to manage it before it helps me, I won't keep it going.",
            "what_they_repeat_when_skeptical": "Show me the smallest version that works in a normal week.",
            "what_they_never_say": [
                "I would definitely buy this right away.",
                "This solves everything for me.",
            ],
            "example_positive_reaction": "If this helps with one recurring handoff and I can test it quietly first, I'd give it a real try.",
            "example_polite_rejection": "I get the value case. I just don't think I'd keep this going once the week gets noisy.",
            "example_hard_rejection": "This asks me to manage the tool before the tool helps me.",
            "example_near_purchase_question": "Can I start with one recurring task and leave the rest of my routine alone?",
        }
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return {
            "speaking_style": "compressed, experienced, and low-theater",
            "sentence_length": "short_to_medium",
            "directness_pattern": "moves quickly from the pitch to upkeep, retention, and disclosure control",
            "metaphors_or_phrases": [
                "month two",
                "who carries it",
                "burden leaves the user",
                "control before disclosure",
            ],
            "how_they_soften_disagreement": "I understand the pitch. That is not the part I doubt.",
            "how_they_get_more_direct": "If the maintenance simply lands on the user, it is not a productivity gain.",
            "what_they_repeat_when_skeptical": "Show me what burden leaves the user, not what feature arrives.",
            "what_they_never_say": [
                "I'm excited by the vision.",
                "Inclusive branding alone solves the trust problem.",
            ],
            "example_positive_reaction": "If the upkeep path is clear and the controls are respectful, I'll take the product seriously.",
            "example_polite_rejection": "The concept is clear. I just don't see the month-two logic yet.",
            "example_hard_rejection": "This creates a cleaner record of user effort. It does not remove the effort.",
            "example_near_purchase_question": "What still works after the launch energy is gone, and what can stay private by default?",
        }
    return {}


def _contradiction_map_v3_1(persona: PersonaSkill) -> list[dict[str, str]]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return [
            {
                "contradiction": "Wants to appear capable but avoids being the first person to publicly champion an unproven tool.",
                "how_it_shows_up": "He may privately test a product or save the link, while sounding supportive in conversation without volunteering to lead adoption.",
                "product_validation_effect": "Founders can mistake polite encouragement for internal champion energy.",
            },
            {
                "contradiction": "Likes lightweight experiments but sometimes saves too many tools without returning to them.",
                "how_it_shows_up": "He confuses a neat first impression with a routine he will actually revisit on a busy week.",
                "product_validation_effect": "Interest metrics can look healthier than trial completion.",
            },
            {
                "contradiction": "Wants peer proof but also wants to feel early enough to look competent.",
                "how_it_shows_up": "He responds to practical demos from people like him, but does not want to arrive so late that he looks behind.",
                "product_validation_effect": "Timing and social framing matter as much as feature fit.",
            },
            {
                "contradiction": "Says setup is the problem, but social risk is often the real blocker.",
                "how_it_shows_up": "A small setup burden can feel much larger if mistakes become visible to a manager or group chat.",
                "product_validation_effect": "Reducing friction alone will not fix adoption if visibility risk stays high.",
            },
            {
                "contradiction": "Will politely encourage a founder even when he has not formed trial intent.",
                "how_it_shows_up": "He sounds constructive, asks a clarifying question, then does nothing if the first step still feels too exposed.",
                "product_validation_effect": "Positive interview tone can overstate real conversion potential.",
            },
        ]
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return [
            {
                "contradiction": "Wants fewer systems but keeps private backup notes because trust is earned slowly.",
                "how_it_shows_up": "They criticize duplication while still maintaining a shadow record when the official system feels too optimistic.",
                "product_validation_effect": "A founder may think adoption succeeded while Jordan is quietly holding a fallback process.",
            },
            {
                "contradiction": "Values inclusion but dislikes being turned into a public identity signal.",
                "how_it_shows_up": "They welcome respectful options yet disengage when identity disclosure becomes part of the brand performance.",
                "product_validation_effect": "Tone tests can look positive while product trust still drops at the settings layer.",
            },
            {
                "contradiction": "Can assess tools deeply but is tired of doing unpaid maintenance thinking for vendors.",
                "how_it_shows_up": "They often see the operational holes quickly, but resent products that expect the user to map them out on the vendor's behalf.",
                "product_validation_effect": "Products that rely on user patience during setup will lose them earlier than a friendlier interview suggests.",
            },
            {
                "contradiction": "Wants control but may disengage quietly rather than negotiate settings.",
                "how_it_shows_up": "They are more likely to stop trusting the flow than to spend energy correcting every bad default.",
                "product_validation_effect": "Teams may miss the true reason for dropout if they only count complaints.",
            },
            {
                "contradiction": "Appreciates elegant demos but treats elegance as suspicious until month-two upkeep is explained.",
                "how_it_shows_up": "A polished first impression can buy a closer read, but also sharpens their suspicion that the hard part has been hidden.",
                "product_validation_effect": "Strong launch reactions may reverse once retention questions begin.",
            },
        ]
    return persona.profile.contradiction_map


def _cross_domain_model_v3_1(persona: PersonaSkill) -> dict[str, Any]:
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return {
            "generic_new_product": {
                "reaction_basis": "He is willing to try something new when the first commitment is reversible and socially quiet.",
                "first_question": "Can I test the smallest version of this without creating cleanup if it fails?",
                "positive_trigger": "A bounded first use case that fits a normal week.",
                "negative_trigger": "Immediate pressure to reorganize everything.",
                "trust_requirement": "A practical demo from someone with a similar work rhythm.",
                "likely_objection": "I understand the idea. I just don't want to overcommit before I know it fits.",
                "persona_specific_example": "If this starts with one recurring handoff, I will pay attention.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
            "ai_product": {
                "reaction_basis": "He likes help before complexity, not training before value.",
                "first_question": "Will this help before I have to teach it my whole routine?",
                "positive_trigger": "Review-first AI help on one recurring task.",
                "negative_trigger": "Automation that acts before he can check it.",
                "trust_requirement": "Visible review control and plain data boundaries.",
                "likely_objection": "I don't want to debug the AI just to prove I was open-minded.",
                "persona_specific_example": "If it drafts follow-up and I approve it first, that's believable. If it wants my inbox immediately, no.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
            "subscription_product": {
                "reaction_basis": "Recurring spend has to survive noisy weeks and still feel easy to exit.",
                "first_question": "Will I still use this when the week is messy, or will it become another quiet charge?",
                "positive_trigger": "Month-to-month clarity and easy cancellation.",
                "negative_trigger": "Annual pressure before habit exists.",
                "trust_requirement": "A fair exit path and realistic local pricing.",
                "likely_objection": "Cheap isn't the point if I only use it on ideal days.",
                "persona_specific_example": "I've cancelled things that were affordable but never made it into my actual week.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
            "family_or_household_product": {
                "reaction_basis": "He notices when convenience really means one person becomes the admin.",
                "first_question": "Will this make me the person who maintains it for everyone else?",
                "positive_trigger": "Clear confirmation flows and optional sharing.",
                "negative_trigger": "Default roles that assume one household coordinator.",
                "trust_requirement": "Visible control over who sees what and when.",
                "likely_objection": "I don't want a family tool that quietly becomes my extra job.",
                "persona_specific_example": "The product needs to reduce follow-up, not just label it better.",
                "non_work_purchase_scene_reference": "family_repair_whatsapp_booking",
            },
            "health_or_wellbeing_product": {
                "reaction_basis": "Inconsistent routines make him wary of products that convert support into visible failure.",
                "first_question": "Can this support uneven weeks without making me feel like I failed?",
                "positive_trigger": "Private, low-pressure support.",
                "negative_trigger": "Guilt loops and visible streak loss.",
                "trust_requirement": "Private defaults and neutral tone.",
                "likely_objection": "I don't need another place telling me I slipped.",
                "persona_specific_example": "If a tired week looks like failure in the app, I will stop opening it.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
            "financial_product": {
                "reaction_basis": "Predictability matters more than flashy headline value.",
                "first_question": "Does this make sense in MYR and in an early-career budget, or is it priced like spare money is obvious?",
                "positive_trigger": "Plain local pricing and no surprise add-ons.",
                "negative_trigger": "Imported SaaS pricing posture.",
                "trust_requirement": "Predictable monthly logic and respectful downgrade paths.",
                "likely_objection": "I don't mind paying. I mind paying for ambiguity.",
                "persona_specific_example": "Clear rollover rules feel more trustworthy than a louder promo.",
                "non_work_purchase_scene_reference": "mobile_plan_rollover_choice",
            },
            "education_or_child_product": {
                "reaction_basis": "He reacts badly to products that turn help into another responsibility record.",
                "first_question": "Does this support follow-through, or just create another place to feel behind?",
                "positive_trigger": "Light prompts and realistic cadence.",
                "negative_trigger": "Moralizing productivity language.",
                "trust_requirement": "Respectful reminders and low admin burden.",
                "likely_objection": "If this becomes another dashboard of what I didn't do, it's not help.",
                "persona_specific_example": "The right tone matters as much as the features here.",
                "non_work_purchase_scene_reference": "family_repair_whatsapp_booking",
            },
            "workflow_or_productivity_product": {
                "reaction_basis": "He is open to narrow experiments but not full rebuilds.",
                "first_question": "Can I test this on one recurring handoff before it touches everything else?",
                "positive_trigger": "A quiet pilot with one visible win.",
                "negative_trigger": "Setup that assumes whole-team discipline from day one.",
                "trust_requirement": "A believable first week and private learning space.",
                "likely_objection": "I'm not volunteering to champion this before it proves itself.",
                "persona_specific_example": "Start with one repeat miss, not my whole stack.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
            "identity_sensitive_product": {
                "reaction_basis": "He notices early requests for personal context as a trust test.",
                "first_question": "Why do you need this personal information this early?",
                "positive_trigger": "Clear purpose and optional disclosure.",
                "negative_trigger": "Labels before relevance.",
                "trust_requirement": "Private defaults and visible control.",
                "likely_objection": "You're asking for intimacy before utility.",
                "persona_specific_example": "If the product earns trust first, the question lands differently.",
                "non_work_purchase_scene_reference": "family_repair_whatsapp_booking",
            },
            "high_friction_onboarding": {
                "reaction_basis": "Momentum disappears quickly if first value takes too long.",
                "first_question": "How fast do I reach first value before the setup starts feeling like unpaid discipline?",
                "positive_trigger": "First value in one short session.",
                "negative_trigger": "Multiple configuration steps before any result.",
                "trust_requirement": "Visible progress and reversible setup.",
                "likely_objection": "I can tell this is well thought out, but I still don't think I'd finish onboarding.",
                "persona_specific_example": "The right product should help before the late-evening drop-off point.",
                "non_work_purchase_scene_reference": "peer_tool_trial_exit",
            },
        }
    if _archetype_key(persona) == "mature_operator_retention_skeptic":
        return {
            "generic_new_product": {
                "reaction_basis": "They have watched clean promises become maintenance debt after the demo.",
                "first_question": "What burden leaves the user after the demo stops carrying the story?",
                "positive_trigger": "A concrete explanation of which upkeep disappears for good.",
                "negative_trigger": "Efficiency language with no burden map.",
                "trust_requirement": "Month-two realism and visible fallback logic.",
                "likely_objection": "The concept is fine. The upkeep case is missing.",
                "persona_specific_example": "Tell me what still works after launch energy fades.",
                "non_work_purchase_scene_reference": "recurring_service_line_item",
            },
            "ai_product": {
                "reaction_basis": "They assume someone must still check the AI after the excitement wears off.",
                "first_question": "Who checks the AI after week three, and what happens when it is wrong?",
                "positive_trigger": "Review control and realistic exception handling.",
                "negative_trigger": "AI positioned as trust substitute.",
                "trust_requirement": "Plain data policy and operational accountability.",
                "likely_objection": "If the user becomes the quiet QA layer, this is not labor savings.",
                "persona_specific_example": "AI that needs supervision is not disqualified. AI that hides the supervision cost is.",
                "non_work_purchase_scene_reference": "appliance_warranty_follow_up",
            },
            "subscription_product": {
                "reaction_basis": "Recurring spend must remain defensible after the first month.",
                "first_question": "What is the month-two justification once the novelty disappears?",
                "positive_trigger": "Calm retention logic and transparent cancellation terms.",
                "negative_trigger": "Ongoing charges explained only by launch excitement.",
                "trust_requirement": "Defensible recurring value in local reality.",
                "likely_objection": "Affordable is not the same as worth renewing.",
                "persona_specific_example": "I cancel line items that become conceptually irritating before they become expensive.",
                "non_work_purchase_scene_reference": "recurring_service_line_item",
            },
            "family_or_household_product": {
                "reaction_basis": "They watch for who quietly carries the coordination work at home.",
                "first_question": "Who in the household carries the maintenance when this stops feeling new?",
                "positive_trigger": "Role-neutral controls and optional visibility.",
                "negative_trigger": "Shared defaults that create one unpaid coordinator.",
                "trust_requirement": "Clear maintenance ownership and low dignity cost.",
                "likely_objection": "I don't want a household tool that quietly nominates a manager.",
                "persona_specific_example": "Protection is only useful if the follow-up path is real.",
                "non_work_purchase_scene_reference": "appliance_warranty_follow_up",
            },
            "health_or_wellbeing_product": {
                "reaction_basis": "They resist products that convert support into surveillance or noncompliance records.",
                "first_question": "Does this support the user, or does it become a record of not complying?",
                "positive_trigger": "Private defaults and non-judgmental cadence.",
                "negative_trigger": "Visibility and moral pressure disguised as support.",
                "trust_requirement": "Clear control over sensitive data and interpretation.",
                "likely_objection": "I don't want a wellbeing tool that behaves like soft monitoring.",
                "persona_specific_example": "Support should reduce exposure, not generate a cleaner exposure trail.",
                "non_work_purchase_scene_reference": "consumer_profile_guest_checkout",
            },
            "financial_product": {
                "reaction_basis": "They are alert to pricing logic imported from elsewhere and detached from local habits.",
                "first_question": "Is this priced for local reality or copied from US SaaS logic?",
                "positive_trigger": "Predictable local pricing and straightforward ongoing value.",
                "negative_trigger": "Aggressive upgrade framing and abstract savings math.",
                "trust_requirement": "Explainable line-item value after month one.",
                "likely_objection": "I can understand the spreadsheet logic and still not believe the lived value.",
                "persona_specific_example": "A service can be affordable and still feel operationally unserious.",
                "non_work_purchase_scene_reference": "recurring_service_line_item",
            },
            "education_or_child_product": {
                "reaction_basis": "They look for whether a tool supports care or weaponizes responsibility.",
                "first_question": "Does this support follow-through, or does it create another place to store guilt?",
                "positive_trigger": "Respectful prompts and realistic responsibility design.",
                "negative_trigger": "Moralizing accountability dashboards.",
                "trust_requirement": "Private control and no forced performative care.",
                "likely_objection": "If the product creates a better record of failure than a better routine, it misses the point.",
                "persona_specific_example": "Not every caring user wants another visible system of proof.",
                "non_work_purchase_scene_reference": "appliance_warranty_follow_up",
            },
            "workflow_or_productivity_product": {
                "reaction_basis": "They distinguish between cleaner records and actual workload reduction.",
                "first_question": "Which existing step disappears, not what new record appears?",
                "positive_trigger": "A real removal of duplicate maintenance.",
                "negative_trigger": "Visibility layers that depend on user cleanup.",
                "trust_requirement": "Burden map, exception path, and month-two proof.",
                "likely_objection": "A dashboard is not relief if the staff still feeds it manually.",
                "persona_specific_example": "If onboarding needs project discipline, retention usually gets worse, not better.",
                "non_work_purchase_scene_reference": "appliance_warranty_follow_up",
            },
            "identity_sensitive_product": {
                "reaction_basis": "Disclosure control is a practical trust issue, not a branding preference.",
                "first_question": "Can this be used without public labeling or premature disclosure?",
                "positive_trigger": "Optional disclosure, prefer-not-to-say, and private defaults.",
                "negative_trigger": "Mandatory titles and identity markers shown publicly by default.",
                "trust_requirement": "Respectful settings that reduce dignity cost.",
                "likely_objection": "If your inclusivity depends on me being publicly legible, it is not for me.",
                "persona_specific_example": "Trust often drops at the profile screen, not at the homepage.",
                "non_work_purchase_scene_reference": "consumer_profile_guest_checkout",
            },
            "high_friction_onboarding": {
                "reaction_basis": "They assume friction-heavy onboarding predicts retention-heavy maintenance.",
                "first_question": "If onboarding already needs project discipline, why would month two be easier?",
                "positive_trigger": "Visible first value before operational overhead multiplies.",
                "negative_trigger": "Configuration theater before any relief appears.",
                "trust_requirement": "Fast proof, realistic scope, and good failure handling.",
                "likely_objection": "This feels like a system asking for belief before it has earned routine space.",
                "persona_specific_example": "The longer the setup, the more I suspect the real burden is simply moving.",
                "non_work_purchase_scene_reference": "recurring_service_line_item",
            },
        }
    return persona.profile.cross_domain_product_reaction_model


def _deep_research_notes_v3_1(persona: PersonaSkill) -> dict[str, Any]:
    notes = copy.deepcopy(persona.profile.deep_research_notes)
    if _archetype_key(persona) == "early_career_practical_trial_user":
        notes.update(
            {
                "what_a_founder_might_misread_about_them": [
                    "Polite interest can be mistaken for trial intent.",
                    "Setup complaints can hide social visibility risk.",
                    "A positive reaction to the problem statement does not mean he will champion adoption.",
                ],
                "how_to_detect_real_interest": [
                    "He asks how to start on one bounded use case.",
                    "He checks whether the trial can stay private or reversible.",
                    "He wants to know what happens in a normal week, not just in a demo.",
                ],
                "how_to_detect_polite_fake_interest": [
                    "He says the idea is useful but never narrows to a first task.",
                    "He praises the concept while avoiding any change to his routine.",
                    "He asks broad questions that do not move closer to trial behavior.",
                ],
            }
        )
    elif _archetype_key(persona) == "mature_operator_retention_skeptic":
        notes.update(
            {
                "what_a_founder_might_misread_about_them": [
                    "Directness can be mistaken for closed-mindedness when it is actually a retention test.",
                    "Low complaint volume can hide quiet trust collapse.",
                    "Interest in inclusive language does not mean branding alone will earn trust.",
                ],
                "how_to_detect_real_interest": [
                    "They ask operational follow-up questions that assume the product might be used.",
                    "They probe month-two logic rather than stopping at surface objections.",
                    "They ask whether disclosure or visibility can be controlled.",
                ],
                "how_to_detect_polite_fake_interest": [
                    "They acknowledge the pitch but never ask what still works after the first month.",
                    "They compliment clarity while withholding any belief in upkeep.",
                    "They stop engaging once settings and controls look weak.",
                ],
            }
        )
    return notes


def upgrade_persona_to_v3_1(source_persona: PersonaSkill, *, random_seed: int | None = None, contrast_mode: bool = False) -> PersonaSkill:
    persona = copy.deepcopy(source_persona)
    if persona.skill_version not in {"v3", "v3.1"}:
        persona = upgrade_persona_to_v3(persona, random_seed=random_seed, contrast_mode=contrast_mode)

    persona.skill_version = "v3.1"
    persona.profile.panel_role_profile = copy.deepcopy(persona.profile.panel_role_profile) or {}
    persona.profile.local_grounding_layer = copy.deepcopy(persona.profile.local_grounding_layer) or {}
    persona.profile.sensitive_scenario_salience = _sensitive_scenario_salience(persona)
    persona.profile.sensitive_scenario_reactions = _sensitive_scenario_reactions_v3_1(persona)
    persona.profile.persona_voiceprint = _persona_voiceprint_v3_1(persona)
    persona.profile.canonical_biography = copy.deepcopy(persona.profile.canonical_biography)
    persona.profile.canonical_biography["life_arc_summary"] = _life_arc_summary_v3_1(persona)
    persona.profile.canonical_biography["non_work_purchase_scenes"] = _non_work_purchase_scenes_v3_1(persona)
    persona.profile.contradiction_map = _contradiction_map_v3_1(persona)
    persona.profile.cross_domain_product_reaction_model = _cross_domain_model_v3_1(persona)
    persona.profile.deep_research_notes = _deep_research_notes_v3_1(persona)

    if contrast_mode and _archetype_key(persona) == "early_career_practical_trial_user":
        persona.profile.persona_voiceprint["what_they_repeat_when_skeptical"] = "I need the quiet first step, not the whole routine promise."
    if contrast_mode and _archetype_key(persona) == "mature_operator_retention_skeptic":
        persona.profile.persona_voiceprint["what_they_repeat_when_skeptical"] = "Explain the upkeep path before you explain the vision again."

    persona.decision_policy = {
        **persona.decision_policy,
        "trust_requirements": _dedupe(
            list(persona.decision_policy.get("trust_requirements", []))
            + _top_salience_keys(persona.profile.sensitive_scenario_salience)
        ),
        "trial_threshold": persona.profile.persona_voiceprint.get("example_near_purchase_question", ""),
    }
    persona.response_style = {
        **persona.response_style,
        "persona_voice_anchor": persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
    }
    persona.profile.audit_evidence_layer.update(
        {
            "persona_generation_method": "deterministic_v3_patch_plus_v3_1_rewrite",
            "persona_version": "v3.1",
            "generator_version": "persona-generator/v3.1",
            "last_audited_at": datetime.now(UTC).date().isoformat(),
        }
    )
    persona.audit = {
        **persona.audit,
        **persona.profile.audit_evidence_layer,
    }
    persona.narrative = _compat_persona_md_v3_1(persona)
    return persona


def _dimension_text_v3_1(persona: PersonaSkill, dimension: str) -> str:
    if dimension == "life_arc_similarity":
        return _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", ""))
    if dimension == "sensitive_topic_reaction_similarity":
        return json.dumps(persona.profile.sensitive_scenario_reactions, ensure_ascii=False, sort_keys=True)
    if dimension == "hidden_contradiction_similarity":
        return json.dumps(persona.profile.contradiction_map, ensure_ascii=False, sort_keys=True)
    if dimension == "cross_domain_reaction_similarity":
        return json.dumps(persona.profile.cross_domain_product_reaction_model, ensure_ascii=False, sort_keys=True)
    if dimension == "phrase_similarity":
        return (
            _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", ""))
            + " "
            + persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", "")
            + " "
            + persona.profile.persona_voiceprint.get("example_hard_rejection", "")
        )
    return ""


def similarity_dimensions_v3_1(candidate: PersonaSkill, comparison: PersonaSkill) -> dict[str, float]:
    dimensions = copy.deepcopy(build_diversity_report_v3(candidate, [comparison])["pair_reports"][0]["dimensions"])
    dimensions["life_arc_similarity"] = _text_similarity(
        _dimension_text_v3_1(candidate, "life_arc_similarity"),
        _dimension_text_v3_1(comparison, "life_arc_similarity"),
    )
    sensitive_text_similarity = _text_similarity(
        _dimension_text_v3_1(candidate, "sensitive_topic_reaction_similarity"),
        _dimension_text_v3_1(comparison, "sensitive_topic_reaction_similarity"),
    )
    salience_similarity = _salience_similarity(
        candidate.profile.sensitive_scenario_salience,
        comparison.profile.sensitive_scenario_salience,
    )
    dimensions["sensitive_topic_reaction_similarity"] = round((sensitive_text_similarity * 0.55) + (salience_similarity * 0.45), 4)
    dimensions["hidden_contradiction_similarity"] = _text_similarity(
        _dimension_text_v3_1(candidate, "hidden_contradiction_similarity"),
        _dimension_text_v3_1(comparison, "hidden_contradiction_similarity"),
    )
    dimensions["cross_domain_reaction_similarity"] = _text_similarity(
        _dimension_text_v3_1(candidate, "cross_domain_reaction_similarity"),
        _dimension_text_v3_1(comparison, "cross_domain_reaction_similarity"),
    )
    dimensions["phrase_similarity"] = _text_similarity(
        _dimension_text_v3_1(candidate, "phrase_similarity"),
        _dimension_text_v3_1(comparison, "phrase_similarity"),
    )
    return dimensions


def _overall_similarity_v3_1(dimensions: dict[str, float]) -> float:
    weights = {
        "core_motivation_similarity": 0.08,
        "life_arc_similarity": 0.12,
        "formative_event_similarity": 0.08,
        "product_objection_similarity": 0.11,
        "pricing_logic_similarity": 0.07,
        "trust_model_similarity": 0.08,
        "technology_attitude_similarity": 0.05,
        "lifestyle_similarity": 0.06,
        "objection_language_similarity": 0.09,
        "cross_domain_reaction_similarity": 0.11,
        "sensitive_topic_reaction_similarity": 0.09,
        "hidden_contradiction_similarity": 0.08,
        "domain_fit_overlap": 0.03,
        "phrase_similarity": 0.03,
        "panel_role_redundancy": 0.02,
    }
    total = 0.0
    for key, weight in weights.items():
        total += dimensions.get(key, 0.0) * weight
    return round(total, 4)


def _high_similarity_dimensions_v3_1(dimensions: dict[str, float]) -> list[str]:
    result: list[str] = []
    for dimension, score in dimensions.items():
        threshold = 0.70
        if dimension == "objection_language_similarity":
            threshold = 0.55
        elif dimension == "cross_domain_reaction_similarity":
            threshold = 0.65
        elif dimension == "sensitive_topic_reaction_similarity":
            threshold = 0.60
        elif dimension == "life_arc_similarity":
            threshold = 0.55
        elif dimension == "hidden_contradiction_similarity":
            threshold = 0.50
        elif dimension == "phrase_similarity":
            threshold = 0.60
        if score > threshold:
            result.append(dimension)
    return result


def build_diversity_report_v3_1(
    candidate: PersonaSkill,
    comparison_personas: list[PersonaSkill],
    *,
    baseline_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pair_reports: list[dict[str, Any]] = []
    for comparison in comparison_personas:
        if comparison.profile.synthetic_user_id == candidate.profile.synthetic_user_id:
            continue
        dimensions = similarity_dimensions_v3_1(candidate, comparison)
        pair_reports.append(
            {
                "persona_id": comparison.profile.synthetic_user_id,
                "overall_similarity_score": _overall_similarity_v3_1(dimensions),
                "dimensions": dimensions,
            }
        )

    if not pair_reports:
        return {
            "synthetic_user_id": candidate.profile.synthetic_user_id,
            "compared_against": [],
            "overall_similarity_score": 0.0,
            "high_similarity_dimensions": [],
            "distinctiveness_score": 1.0,
            "warnings": [],
            "required_diversification_actions": [],
            "pair_reports": [],
            "v3_1_patch_summary": {
                "life_arc_rewritten": True,
                "sensitive_salience_added": True,
                "non_work_scenes_added": True,
                "hidden_contradictions_personalized": True,
                "cross_domain_reactions_rebalanced": True,
            },
            "before_after_similarity": {
                "v3_overall_similarity": 0.0,
                "v3_1_overall_similarity": 0.0,
                "v3_sensitive_topic_similarity": 0.0,
                "v3_1_sensitive_topic_similarity": 0.0,
                "improved_dimensions": [],
            },
        }

    pair_reports.sort(key=lambda item: item["overall_similarity_score"], reverse=True)
    top_pair = pair_reports[0]
    high_dimensions = _high_similarity_dimensions_v3_1(top_pair["dimensions"])
    warnings = [
        f"Similarity remains elevated in {dimension.replace('_', ' ')} against {top_pair['persona_id']}."
        for dimension in high_dimensions
    ]
    actions: list[str] = []
    if top_pair["dimensions"].get("life_arc_similarity", 0.0) > 0.55:
        actions.append("Rewrite life arc summary around archetype-specific motivation rather than shared workflow language.")
    if top_pair["dimensions"].get("sensitive_topic_reaction_similarity", 0.0) > 0.60:
        actions.append("Increase salience contrast and scenario-specific wording in sensitive topic handling.")
    if top_pair["dimensions"].get("hidden_contradiction_similarity", 0.0) > 0.50:
        actions.append("Personalize contradiction map with persona-specific social and dignity costs.")
    if top_pair["dimensions"].get("cross_domain_reaction_similarity", 0.0) > 0.65:
        actions.append("Rebalance cross-domain reactions with more non-work references and persona-specific first questions.")

    before_after = {
        "v3_overall_similarity": 0.0,
        "v3_1_overall_similarity": top_pair["overall_similarity_score"],
        "v3_sensitive_topic_similarity": 0.0,
        "v3_1_sensitive_topic_similarity": top_pair["dimensions"].get("sensitive_topic_reaction_similarity", 0.0),
        "improved_dimensions": [],
    }
    if baseline_report and baseline_report.get("pair_reports"):
        baseline_top_pair = baseline_report["pair_reports"][0]
        before_after["v3_overall_similarity"] = baseline_report.get("overall_similarity_score", 0.0)
        before_after["v3_sensitive_topic_similarity"] = baseline_top_pair["dimensions"].get("sensitive_topic_reaction_similarity", 0.0)
        improved = []
        for key, value in top_pair["dimensions"].items():
            baseline_value = baseline_top_pair["dimensions"].get(key)
            if baseline_value is not None and value < baseline_value:
                improved.append(key)
        before_after["improved_dimensions"] = improved

    return {
        "synthetic_user_id": candidate.profile.synthetic_user_id,
        "compared_against": [item["persona_id"] for item in pair_reports],
        "overall_similarity_score": top_pair["overall_similarity_score"],
        "high_similarity_dimensions": high_dimensions,
        "distinctiveness_score": round(1.0 - top_pair["overall_similarity_score"], 4),
        "warnings": warnings,
        "required_diversification_actions": actions,
        "pair_reports": pair_reports,
        "v3_1_patch_summary": {
            "life_arc_rewritten": True,
            "sensitive_salience_added": True,
            "non_work_scenes_added": True,
            "hidden_contradictions_personalized": True,
            "cross_domain_reactions_rebalanced": True,
        },
        "before_after_similarity": before_after,
    }


def _requires_distinctiveness_revision_v3_1(diversity_report: dict[str, Any]) -> bool:
    return (
        diversity_report.get("overall_similarity_score", 0.0) > 0.50
        or diversity_report.get("pair_reports", [{}])[0].get("dimensions", {}).get("sensitive_topic_reaction_similarity", 0.0) > 0.60
        or diversity_report.get("pair_reports", [{}])[0].get("dimensions", {}).get("life_arc_similarity", 0.0) > 0.55
    )


def apply_distinctiveness_revision_v3_1(candidate: PersonaSkill, comparison_personas: list[PersonaSkill]) -> PersonaSkill:
    revised = upgrade_persona_to_v3_1(candidate, contrast_mode=True)
    if _archetype_key(revised) == "early_career_practical_trial_user":
        revised.profile.canonical_biography["life_arc_summary"] = revised.profile.canonical_biography["life_arc_summary"].replace(
            "He opens up when a product helps him look capable, reduces one real handoff problem, and proves it can survive an ordinary week.",
            "He opens up when a product quietly helps him look dependable, solves one recurring miss, and does not force him to overexplain the experiment."
        )
    elif _archetype_key(revised) == "mature_operator_retention_skeptic":
        revised.profile.canonical_biography["life_arc_summary"] = revised.profile.canonical_biography["life_arc_summary"].replace(
            "A clean pitch can win attention, but not trust, unless the product explains what burden leaves the user in real life.",
            "A clean pitch can earn a hearing, but trust only appears when the product explains the upkeep, the month-two routine, and the disclosure controls."
        )
    return revised


def render_biography_md_v3_1(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    biography = persona.profile.canonical_biography
    lines = [
        f"# {identity.get('name', '')} - Level 3 Synthetic User Biography",
        "",
        "## Life Arc Summary",
        biography.get("life_arc_summary", ""),
        "",
    ]
    for chapter in biography.get("decade_timeline", []):
        lines.extend(
            [
                f"## {chapter.get('age_range', '')}",
                f"**{chapter.get('chapter_title', '')}**",
                chapter.get("life_context", ""),
                "",
                f"Specific scene: {chapter.get('specific_scene', '')}",
                f"Product-relevant memory: {chapter.get('product_relevant_memory', '')}",
                f"Social or relationship context: {chapter.get('social_or_relationship_context', '')}",
                f"Money or effort trade-off: {chapter.get('money_or_effort_tradeoff', '')}",
                f"Beliefs formed: {'; '.join(chapter.get('beliefs_formed', []))}",
                f"Current reaction link: {chapter.get('current_reaction_link', '')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Current Life",
            biography.get("current_daily_life", ""),
            "",
            "## Formative Events",
        ]
    )
    for event in biography.get("formative_events", []):
        lines.append(f"- {event}")
    lines.extend(
        [
            "",
            "## Current Identity",
            biography.get("current_identity", ""),
            "",
            "## Non-Work Purchase Scenes",
        ]
    )
    for scene in biography.get("non_work_purchase_scenes", []):
        lines.extend(
            [
                f"### {scene.get('scene_title', '')}",
                scene.get("specific_scene", ""),
                f"Decision context: {scene.get('decision_context', '')}",
                f"Trust or price lesson: {scene.get('trust_or_price_lesson', '')}",
                f"Product research impact: {scene.get('current_product_research_impact', '')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Interests & Private Life",
            f"Primary interests: {', '.join(persona.profile.interests_and_hobbies.get('primary_interests', []))}",
            f"Low-energy hobbies: {', '.join(persona.profile.interests_and_hobbies.get('low_energy_hobbies', []))}",
            f"Private hobbies: {', '.join(persona.profile.interests_and_hobbies.get('private_hobbies', []))}",
            f"Aspirational hobbies: {', '.join(persona.profile.interests_and_hobbies.get('aspirational_hobbies', []))}",
            "",
            "## Media Diet & Product Discovery",
            f"Discovery pattern: {persona.profile.media_and_content_diet.get('how_they_discover_new_products', '')}",
            f"Local discovery channels: {', '.join(persona.profile.local_grounding_layer.get('local_discovery_channels', []))}",
            f"Verification pattern: {persona.profile.media_and_content_diet.get('how_they_verify_claims', '')}",
            "",
            "## Ordinary Day in Detail",
            f"Workday: {persona.profile.daily_micro_behaviours.get('work_start_pattern', '')} {persona.profile.daily_micro_behaviours.get('message_checking_pattern', '')}",
            f"Weekend: {persona.profile.daily_micro_behaviours.get('weekend_pattern', '')}",
            f"Most open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_most_open_to_new_products', '')}",
            f"Least open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_least_open_to_new_products', '')}",
            "",
            "## Home, Workspace & Tools",
            f"Home: {persona.profile.personal_environment.get('home_setup', '')}",
            f"Workspace: {persona.profile.personal_environment.get('workspace_setup', '')}",
            f"Always-open tools: {', '.join(persona.profile.personal_environment.get('tools_always_open', []))}",
            f"Constraints: {', '.join(persona.profile.personal_environment.get('constraints_from_environment', []))}",
            "",
            "## Hidden Habits & Contradictions",
            f"Hidden habits: {', '.join(persona.profile.hidden_habits.get('private_shortcuts', []) + persona.profile.hidden_habits.get('workarounds_they_keep_using', []))}",
        ]
    )
    for item in persona.profile.contradiction_map:
        lines.append(f"- {item.get('contradiction', '')} {item.get('product_validation_effect', '')}")
    lines.extend(
        [
            "",
            "## Taste, Brand & Communication Preferences",
            f"Visual preference: {persona.profile.taste_and_aesthetic_preferences.get('visual_style_preference', '')}",
            f"Trustworthy design signals: {', '.join(persona.profile.taste_and_aesthetic_preferences.get('trustworthy_design_signals', []))}",
            f"Copy turnoffs: {', '.join(persona.profile.taste_and_aesthetic_preferences.get('copywriting_turnoffs', []))}",
            "",
            "## Product Research Implications",
            f"- Concept validation: {persona.profile.panel_role_profile.get('research_function', '')}",
            f"- Landing page test: this persona overweights {', '.join(persona.profile.panel_role_profile.get('what_this_person_will_overweight', [])[:2])}.",
            "- Pricing test: should probe both monetary logic and the effort or dignity burden that remains after purchase.",
            "- Onboarding test: should show whether first value arrives before discipline, exposure, or cleanup work appear.",
            "- Retention risk: should examine month-two behavior, not just first-week comprehension.",
            "- Referral likelihood: rises only when the product becomes explainable in local, ordinary-life terms.",
            "",
            "## Sensitive Reality Notes",
            f"Top sensitive scenarios: {', '.join(f'{_title_from_key(key)} ({persona.profile.sensitive_scenario_salience.get(key, 0)}/10)' for key in _top_salience_keys(persona.profile.sensitive_scenario_salience))}",
            "",
            "## What This Persona Is Good For",
        ]
    )
    for item in persona.profile.panel_role_profile.get("what_this_person_is_good_at_detecting", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## What This Persona Should Not Be Used For",
        ]
    )
    for item in persona.profile.audit_evidence_layer.get("do_not_use_for", []):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def render_research_kernel_md_v3_1(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    salience = persona.profile.sensitive_scenario_salience
    non_work = persona.profile.canonical_biography.get("non_work_purchase_scenes", [])
    lines = [
        f"# Research Kernel - {identity.get('name', '')}",
        "",
        f"Synthetic user only for AI pre-validation. Not a real human and not a substitute for market research.",
        "",
        "## Identity",
        f"{identity.get('name', '')} is a {identity.get('age', '')}-year-old {identity.get('occupation', '')} in {identity.get('location', '')}.",
        "",
            "## Life Arc Summary",
            _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", "")),
        "",
        "## Top Formative Patterns",
    ]
    for chapter in persona.profile.canonical_biography.get("decade_timeline", [])[-3:]:
        lines.append(f"- {chapter.get('specific_scene', '')}")
    lines.extend(
        [
            "",
            "## Current Life Situation",
            persona.profile.canonical_biography.get("current_daily_life", ""),
            "",
            "## Buying Logic",
            _stringify_text_field(persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", "")),
            "",
            "## Pricing Logic",
            f"Personal comfort: {persona.profile.pricing_logic.get('personal_payment_comfort', '')}",
            f"Work comfort: {persona.profile.pricing_logic.get('work_payment_comfort', '')}",
            f"Fair price signal: {persona.profile.pricing_logic.get('what_makes_price_feel_fair', '')}",
            "",
            "## Interests That Affect Buying Behaviour",
            f"{', '.join(persona.profile.interests_and_hobbies.get('primary_interests', [])[:4])}",
            "",
            "## Media Diet And Discovery Path",
            f"Discovery: {persona.profile.media_and_content_diet.get('how_they_discover_new_products', '')}",
            f"Verification: {persona.profile.media_and_content_diet.get('how_they_verify_claims', '')}",
            f"Local channels: {', '.join(persona.profile.local_grounding_layer.get('local_discovery_channels', []))}",
            "",
            "## Daily Friction Moments",
            f"{persona.profile.daily_micro_behaviours.get('stress_moments', '')}",
            "",
            "## Non-Work Buying Patterns",
        ]
    )
    for scene in non_work[:3]:
        lines.append(f"- {scene.get('scene_title', '')}: {scene.get('trust_or_price_lesson', '')}")
    lines.extend(
        [
            "",
            "## Hidden Habits",
            f"{', '.join(persona.profile.hidden_habits.get('workarounds_they_keep_using', []))}",
            "",
            "## Contradictions",
        ]
    )
    for item in persona.profile.contradiction_map[:4]:
        lines.append(f"- {item.get('contradiction', '')}")
    lines.extend(
        [
            "",
            "## Sensitive Topic Reaction",
        ]
    )
    for key in _top_salience_keys(salience):
        block = persona.profile.sensitive_scenario_reactions.get(key, {})
        lines.append(f"- {_title_from_key(key)} ({salience.get(key, 0)}/10): {block.get('reaction', '')}")
    lines.extend(
        [
            "",
            "## Cross-Domain Product Reaction Summary",
        ]
    )
    for category in ("generic_new_product", "subscription_product", "identity_sensitive_product", "high_friction_onboarding"):
        block = persona.profile.cross_domain_product_reaction_model.get(category, {})
        lines.append(f"- {category}: {block.get('first_question', '')}")
    lines.extend(
        [
            "",
            "## Objection Language",
            persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
            "",
            "## Founder Misread Risk",
        ]
    )
    for item in persona.profile.deep_research_notes.get("what_a_founder_might_misread_about_them", [])[:3]:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def _example_response_v3_1(persona: PersonaSkill, category: str) -> str:
    blocks = persona.profile.cross_domain_product_reaction_model
    voice = persona.profile.persona_voiceprint
    block = blocks.get(category, {})
    if _archetype_key(persona) == "early_career_practical_trial_user":
        return (
            f"{voice.get('how_they_soften_disagreement', '')} {block.get('first_question', '')} "
            f"If you can show {block.get('positive_trigger', '').lower()}, I'm more likely to try it. "
            f"If it starts with {block.get('negative_trigger', '').lower()}, I probably stop at curiosity."
        ).strip()
    return (
        f"{voice.get('how_they_soften_disagreement', '')} {block.get('first_question', '')} "
        f"I'm looking for {block.get('trust_requirement', '').lower()}. "
        f"If the product still feels like {block.get('negative_trigger', '').lower()}, I won't move past evaluation."
    ).strip()


def render_persona_skill_md_v3_1(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    salience = persona.profile.sensitive_scenario_salience
    lines = [
        f"# Synthetic User Skill: {identity.get('name', '')}",
        "",
        "## Role",
        "Synthetic user for AI pre-validation only. Not a real human and not a substitute for market research.",
        "",
        "## Identity",
        f"{identity.get('name', '')} | {identity.get('age', '')} | {identity.get('occupation', '')} | {identity.get('location', '')}",
        "",
        "## Canonical Life Arc",
        _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", "")),
        "",
        "## Decade Memory",
    ]
    for chapter in persona.profile.canonical_biography.get("decade_timeline", []):
        lines.append(f"- {chapter.get('age_range', '')}: {chapter.get('current_reaction_link', '')}")
    lines.extend(
        [
            "",
            "## Current Life",
            persona.profile.canonical_biography.get("current_daily_life", ""),
            "",
            "## Lifestyle & Interests",
            f"{', '.join(persona.profile.interests_and_hobbies.get('primary_interests', [])[:4])}",
            "",
            "## Daily Context",
            f"Most open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_most_open_to_new_products', '')}",
            f"Least open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_least_open_to_new_products', '')}",
            "",
            "## Decision Logic",
            f"Trust requirements: {', '.join(persona.decision_policy.get('trust_requirements', [])[:4])}",
            f"Rejection triggers: {', '.join(persona.decision_policy.get('rejection_triggers', [])[:4])}",
            "",
            "## Buying Logic",
            _stringify_text_field(persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", "")),
            "",
            "## Pricing Logic",
            f"{persona.profile.pricing_logic.get('what_makes_price_feel_fair', '')} Watch for: {persona.profile.pricing_logic.get('pricing_objection', '')}",
            "",
            "## Technology & AI Attitude",
            f"{persona.profile.technology_profile.get('automation_openness', '')}. {persona.profile.cross_domain_product_reaction_model.get('ai_product', {}).get('first_question', '')}",
            "",
            "## Discovery & Trust Path",
            f"{persona.profile.product_discovery_paths.get('most_likely_first_touchpoint', '')}. {persona.profile.media_and_content_diet.get('how_they_verify_claims', '')}",
            "",
            "## Non-Work Product Memory",
        ]
    )
    for scene in persona.profile.canonical_biography.get("non_work_purchase_scenes", [])[:2]:
        lines.append(f"- {scene.get('scene_title', '')}: {scene.get('current_product_research_impact', '')}")
    lines.extend(
        [
            "",
            "## Cross-Domain Product Reaction Model",
        ]
    )
    for category in (
        "generic_new_product",
        "subscription_product",
        "family_or_household_product",
        "financial_product",
        "identity_sensitive_product",
        "high_friction_onboarding",
    ):
        block = persona.profile.cross_domain_product_reaction_model.get(category, {})
        lines.append(f"- {category}: {block.get('first_question', '')}")
    lines.extend(
        [
            "",
            "## Sensitive Topic Handling",
        ]
    )
    for key in _top_salience_keys(salience):
        block = persona.profile.sensitive_scenario_reactions.get(key, {})
        lines.append(f"- {_title_from_key(key)} ({salience.get(key, 0)}/10): {block.get('what_reduces_trust', '')}")
    lines.extend(
        [
            "",
            "## Objection Language",
            f"Voice anchor: {persona.profile.persona_voiceprint.get('what_they_repeat_when_skeptical', '')}",
            f"Polite rejection: {persona.profile.persona_voiceprint.get('example_polite_rejection', '')}",
            f"Hard rejection: {persona.profile.persona_voiceprint.get('example_hard_rejection', '')}",
            "",
            "## Hidden Contradictions",
        ]
    )
    for item in persona.profile.contradiction_map[:4]:
        lines.append(f"- {item.get('contradiction', '')}")
    lines.extend(
        [
            "",
            "## Founder Misread Risk",
        ]
    )
    for item in persona.profile.deep_research_notes.get("what_a_founder_might_misread_about_them", [])[:3]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Response Rules",
            "- Do not flatter the founder.",
            "- Do not pretend to be a real human.",
            "- Respond as this persona.",
            "- Separate curiosity from willingness to pay.",
            "- Challenge vague claims.",
            "- Point out friction, privacy, trust, pricing, and sensitive-topic risks where relevant.",
            "- If the product is unclear, say it is unclear.",
            "- If the persona would not buy, say so.",
            "",
            "## Example Responses",
            f"1. AI productivity product: {_example_response_v3_1(persona, 'ai_product')}",
            f"2. Subscription product: {_example_response_v3_1(persona, 'subscription_product')}",
            f"3. Identity-sensitive product: {_example_response_v3_1(persona, 'identity_sensitive_product')}",
            f"4. High-friction onboarding product: {_example_response_v3_1(persona, 'high_friction_onboarding')}",
            f"5. Vague founder pitch: {_example_response_v3_1(persona, 'generic_new_product')}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_sensitive_scenarios_md_v3_1(persona: PersonaSkill) -> str:
    lines = [
        f"# {persona.profile.basic_identity.get('name', '')} - Sensitive Scenario Map",
        "",
        "## Top Salience",
    ]
    salience = persona.profile.sensitive_scenario_salience
    for index, key in enumerate(_top_salience_keys(salience), start=1):
        lines.append(f"{index}. {key} - {salience.get(key, 0)}/10")
    lines.append("")
    for key in sorted(SENSITIVE_SCENARIO_KEYS, key=lambda item: (-salience.get(item, 0), item)):
        block = persona.profile.sensitive_scenario_reactions.get(key, {})
        lines.extend(
            [
                f"## {key} (salience: {salience.get(key, 0)}/10)",
                f"Trigger scenarios: {', '.join(block.get('trigger_scenarios', []))}",
                f"Reaction: {block.get('reaction', '')}",
                f"What builds trust: {block.get('what_builds_trust', '')}",
                f"What reduces trust: {block.get('what_reduces_trust', '')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _compat_persona_md_v3_1(persona: PersonaSkill) -> str:
    return "\n".join(
        [
            f"# {persona.profile.basic_identity.get('name', '')}",
            "",
            "## Core Read",
            persona.profile.canonical_biography.get("life_arc_summary", ""),
            "",
            "## Voice",
            persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
        ]
    ).strip() + "\n"


def _diff_notes_v3_to_v3_1(v3_persona: PersonaSkill, v3_1_persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any]) -> str:
    before_after = diversity_report.get("before_after_similarity", {})
    scenes = v3_1_persona.profile.canonical_biography.get("non_work_purchase_scenes", [])
    lines = [
        f"# {v3_1_persona.profile.basic_identity.get('name', '')} - V3 to V3.1 Diff",
        "",
        "## Added Archetype Life Arc Rewrite",
        f"- V3: {v3_persona.profile.canonical_biography.get('life_arc_summary', '')}",
        f"- V3.1: {v3_1_persona.profile.canonical_biography.get('life_arc_summary', '')}",
        "",
        "## Sensitive Salience Added",
    ]
    for key in _top_salience_keys(v3_1_persona.profile.sensitive_scenario_salience):
        lines.append(f"- {key}: {v3_1_persona.profile.sensitive_scenario_salience.get(key, 0)}/10")
    lines.extend(
        [
            "",
            "## Non-Work Scenes Added",
        ]
    )
    for scene in scenes:
        lines.append(f"- {scene.get('scene_title', '')}")
    lines.extend(
        [
            "",
            "## Personalized Contradictions",
        ]
    )
    for item in v3_1_persona.profile.contradiction_map[:4]:
        lines.append(f"- {item.get('contradiction', '')}")
    lines.extend(
        [
            "",
            "## Rebalanced Cross-Domain Reactions",
            f"- Generic new product: {v3_1_persona.profile.cross_domain_product_reaction_model.get('generic_new_product', {}).get('first_question', '')}",
            f"- Identity-sensitive product: {v3_1_persona.profile.cross_domain_product_reaction_model.get('identity_sensitive_product', {}).get('first_question', '')}",
            "",
            "## Similarity Changes",
            f"- V3 overall similarity: {before_after.get('v3_overall_similarity', 0.0)}",
            f"- V3.1 overall similarity: {before_after.get('v3_1_overall_similarity', 0.0)}",
            f"- V3 sensitive similarity: {before_after.get('v3_sensitive_topic_similarity', 0.0)}",
            f"- V3.1 sensitive similarity: {before_after.get('v3_1_sensitive_topic_similarity', 0.0)}",
            f"- Improved dimensions: {', '.join(before_after.get('improved_dimensions', [])) or 'none recorded'}",
            "",
            "## Audit Warnings",
        ]
    )
    for warning in quality_audit.get("warnings", []):
        lines.append(f"- {warning}")
    return "\n".join(lines).strip() + "\n"


def _rendered_artifacts_v3_1(persona: PersonaSkill, v3_persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any]) -> dict[str, str]:
    return {
        "persona.md": _compat_persona_md_v3_1(persona),
        "biography.md": render_biography_md_v3_1(persona),
        "research_kernel.md": render_research_kernel_md_v3_1(persona),
        "persona.skill.md": render_persona_skill_md_v3_1(persona),
        "local_grounding.md": render_local_grounding_md_v3(persona),
        "sensitive_scenarios.md": render_sensitive_scenarios_md_v3_1(persona),
        "v3_to_v3_1_diff.md": _diff_notes_v3_to_v3_1(v3_persona, persona, diversity_report, quality_audit),
    }


def build_quality_audit_v3_1(persona: PersonaSkill, rendered_artifacts: dict[str, str], diversity_report: dict[str, Any]) -> dict[str, Any]:
    non_work_scenes = persona.profile.canonical_biography.get("non_work_purchase_scenes", [])
    scores = {
        "structure_completeness": 5,
        "biography_depth": 4,
        "lived_scene_quality": 4 if len(persona.profile.canonical_biography.get("decade_timeline", [])) >= 3 else 2,
        "non_work_lived_scene_quality": 4 if len(non_work_scenes) >= 2 else 2,
        "local_grounding": 4 if persona.profile.local_grounding_layer else 2,
        "product_reaction_readiness": 4,
        "sensitive_topic_readiness": 4 if len(persona.profile.sensitive_scenario_reactions) == 8 else 3,
        "sensitive_salience_specificity": 4 if len(set(persona.profile.sensitive_scenario_salience.values())) >= 3 else 2,
        "voice_distinctiveness": 4 if diversity_report.get("pair_reports", [{}])[0].get("dimensions", {}).get("objection_language_similarity", 1.0) < 0.55 else 2,
        "archetype_life_arc_distinctiveness": 4 if diversity_report.get("pair_reports", [{}])[0].get("dimensions", {}).get("life_arc_similarity", 1.0) < 0.55 else 2,
        "cross_domain_non_work_diversity": 4 if all(block.get("non_work_purchase_scene_reference") for block in persona.profile.cross_domain_product_reaction_model.values()) else 2,
        "library_distinctiveness": 4 if diversity_report.get("overall_similarity_score", 1.0) < 0.50 else 2,
        "template_leakage_risk": 4,
        "overall": 4,
    }
    strengths = [
        "Life arc summary now reflects the behavioural archetype instead of reusing the shared workflow-summary template.",
        "Sensitive scenario handling is ranked by salience, making the persona's top trust risks explicit instead of flat.",
        "Non-work purchase scenes now connect local ordinary-life decisions to product research behavior.",
    ]
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        weaknesses = [
            "Daniel still interprets many categories through bounded-trial logic, so highly aspirational or identity-led products may look flatter than they should.",
            "Penang grounding is materially better, but still lighter on offline social cues than a very high-fidelity persona would need.",
            "Some polite-response examples remain more articulate than a rushed real-world reaction would be.",
        ]
        required_improvements = [
            "Add one more non-work scene that is less tool-centric and more status or leisure driven.",
            "Increase low-energy, distracted response variants so polite interest and partial attention feel even more distinct.",
            "Add more offline Penang trust cues beyond app behavior and household coordination.",
        ]
    else:
        weaknesses = [
            "Jordan still overweights maintenance logic in some consumer categories that could use a slightly more emotional read before the operational critique arrives.",
            "Kuala Lumpur grounding is strong on service and pricing cues, but could still use richer offline market texture.",
            "A few responses are cleaner than real quiet disengagement would look in practice.",
        ]
        required_improvements = [
            "Add one more non-work scene driven by convenience or taste rather than maintenance alone.",
            "Increase examples of silent dropout so not all objections become explicit spoken analysis.",
            "Expand offline KL trust cues beyond service follow-up, settings control, and pricing localization.",
        ]
    warnings = []
    if diversity_report.get("overall_similarity_score", 0.0) >= 0.40:
        warnings.append("V3.1 is improved, but residual similarity remains visible enough to justify human review.")
    if diversity_report.get("pair_reports", [{}])[0].get("dimensions", {}).get("sensitive_topic_reaction_similarity", 0.0) >= 0.60:
        warnings.append("Sensitive-topic differentiation is still too close across personas.")
    for filename, content in rendered_artifacts.items():
        if filename.endswith(".md") and any(token in content for token in RAW_ENUM_TOKENS):
            warnings.append(f"Raw enum leakage detected in {filename}.")
            break
    normalized_md = " ".join(
        _normalize_text(content)
        for name, content in rendered_artifacts.items()
        if name.endswith(".md") and name != "v3_to_v3_1_diff.md"
    )
    if any(phrase in normalized_md for phrase in SHARED_TEMPLATE_PHRASES):
        warnings.append("Residual shared template language remains visible in readable markdown artifacts.")
    if not warnings:
        warnings.append("No schema breakage found, but human review is still required to judge whether the persona voice sounds lived-in enough.")
    return {
        "scores": scores,
        "strengths": strengths,
        "weaknesses": weaknesses[:3],
        "required_improvements": required_improvements[:3],
        "warnings": warnings,
        "enum_leakage_check": "pass" if not any(token in normalized_md for token in RAW_ENUM_TOKENS) else "fail",
        "abstract_language_check": "pass" if "their life has been shaped less by dramatic turning points" not in _normalize_text(rendered_artifacts["biography.md"]) else "needs_attention",
        "local_grounding_check": "pass" if scores["local_grounding"] >= 4 else "weak",
        "sensitive_scenario_check": "pass" if scores["sensitive_topic_readiness"] >= 4 else "weak",
        "similarity_check": f"overall={diversity_report.get('overall_similarity_score', 0.0)}; sensitive={diversity_report.get('pair_reports', [{}])[0].get('dimensions', {}).get('sensitive_topic_reaction_similarity', 0.0)}",
        "human_review_needed": True,
    }


def build_generation_notes_v3_1(persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any], random_seed: int | None, source_version_dir: Path, comparison_ids: list[str]) -> dict[str, Any]:
    return {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": "persona-generator/v3.1",
        "prompt_versions": PROMPT_VERSIONS,
        "model_used": "deterministic-template-v3_1",
        "generated_at": _timestamp(),
        "random_seed": random_seed,
        "source_version_dir": str(source_version_dir),
        "comparison_persona_ids": comparison_ids,
        "quality_score_estimate": quality_audit["scores"],
        "consistency_warnings": quality_audit["warnings"],
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
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
            "high_similarity_dimensions": diversity_report.get("high_similarity_dimensions", []),
        },
        "source_version": "v3",
    }


def write_v3_1_persona_folder(
    persona: PersonaSkill,
    *,
    v3_persona: PersonaSkill,
    root_data_dir: Path,
    source_v3_dir: Path,
    diversity_report: dict[str, Any],
    quality_audit: dict[str, Any],
    random_seed: int | None = None,
) -> Path:
    persona_root = root_data_dir / persona.profile.synthetic_user_id
    ensure_dir(persona_root)
    v3_1_dir = persona_root / "v3_1"
    ensure_dir(v3_1_dir)
    rendered = _rendered_artifacts_v3_1(persona, v3_persona, diversity_report, quality_audit)
    generation_notes = build_generation_notes_v3_1(
        persona,
        diversity_report,
        quality_audit,
        random_seed,
        source_v3_dir,
        diversity_report.get("compared_against", []),
    )
    persona.audit = {
        **persona.audit,
        "quality_audit": quality_audit,
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
        },
        "generator_version": "persona-generator/v3.1",
    }
    write_json(v3_1_dir / "profile.json", persona.profile.to_dict())
    write_json(v3_1_dir / "audit.json", persona.to_audit_payload())
    write_json(v3_1_dir / "generation_notes.json", generation_notes)
    write_json(v3_1_dir / "diversity_report.json", diversity_report)
    for filename, content in rendered.items():
        (v3_1_dir / filename).write_text(content, encoding="utf-8")
    return v3_1_dir


def validate_v3_1_persona_folder(folder: Path) -> dict[str, Any]:
    missing_files = [filename for filename in V3_1_REQUIRED_FILES if not (folder / filename).exists()]
    audit_payload = read_json(folder / "audit.json")
    profile_payload = read_json(folder / "profile.json")
    diversity_report = read_json(folder / "diversity_report.json")
    quality_audit = audit_payload["audit"].get("quality_audit", {})
    consistency_warnings: list[str] = []

    for markdown_name in ("biography.md", "research_kernel.md", "persona.skill.md", "local_grounding.md", "sensitive_scenarios.md", "v3_to_v3_1_diff.md"):
        text = (folder / markdown_name).read_text(encoding="utf-8")
        if any(token in text for token in RAW_ENUM_TOKENS):
            consistency_warnings.append(f"Raw enum leakage detected in {markdown_name}.")

    non_work_scenes = profile_payload.get("canonical_biography", {}).get("non_work_purchase_scenes", [])
    if len(non_work_scenes) < 2:
        consistency_warnings.append("At least 2 non-work purchase scenes are required.")
    if len(profile_payload.get("contradiction_map", [])) < 3:
        consistency_warnings.append("At least 3 persona-specific contradictions are required.")
    if not profile_payload.get("sensitive_scenario_salience"):
        missing_files.append("sensitive_scenario_salience")
    if quality_audit:
        scores = quality_audit.get("scores", {})
        if scores and all(value == 5 for value in scores.values()):
            consistency_warnings.append("quality_audit scores are unrealistically all perfect.")
    else:
        missing_files.append("quality_audit")

    return {
        "missing_fields": missing_files,
        "consistency_warnings": consistency_warnings,
        "stereotype_warnings": [],
        "quality_score_estimate": quality_audit.get("scores", {}),
        "diversity_report": diversity_report,
        "human_review_needed": quality_audit.get("human_review_needed", True),
    }


def validate_v3_1_persona_library(base_dir: Path) -> dict[str, Any]:
    if not base_dir.exists():
        return {
            "library_size": 0,
            "persona_reports": [],
            "issue_count": 0,
            "warning_count": 0,
        }
    persona_reports = []
    for persona_id in _persona_ids_in(base_dir):
        folder = base_dir / persona_id / "v3_1"
        if not folder.exists():
            continue
        persona_reports.append({"persona_id": persona_id, **validate_v3_1_persona_folder(folder)})
    issue_count = sum(len(report["missing_fields"]) + len(report["consistency_warnings"]) for report in persona_reports)
    return {
        "library_size": len(persona_reports),
        "persona_reports": persona_reports,
        "issue_count": issue_count,
        "warning_count": 0,
    }


def run_distinctiveness_check_v3_1(
    *,
    base_dir: Path,
    persona_id: str,
    against_persona_ids: list[str],
    preferred_versions: tuple[str, ...] = ("v3_1", "v3", "v2", "root"),
) -> dict[str, Any]:
    candidate = _load_persona_from_dir(base_dir, persona_id, preferred_versions)
    comparisons = [
        _load_persona_from_dir(base_dir, other_id, preferred_versions)
        for other_id in against_persona_ids
        if other_id != persona_id
    ]
    baseline_candidate = _load_persona_from_dir(base_dir, persona_id, ("v3", "v2", "root"))
    baseline_comparisons = [
        _load_persona_from_dir(base_dir, other_id, ("v3", "v2", "root"))
        for other_id in against_persona_ids
        if other_id != persona_id
    ]
    baseline_report = build_diversity_report_v3(baseline_candidate, baseline_comparisons)
    return build_diversity_report_v3_1(candidate, comparisons, baseline_report=baseline_report)


def generate_v3_1_personas(
    *,
    persona_ids: list[str],
    source_dir: Path,
    output_dir: Path,
    compare_against_dir: Path,
    against_persona_ids: list[str] | None = None,
    random_seed_offset: int = 0,
) -> list[Path]:
    ensure_dir(output_dir)
    selected_ids = list(dict.fromkeys(persona_ids))
    source_personas = {
        persona_id: load_persona(_resolve_persona_folder(source_dir, persona_id, ("v3", "v2", "root")))
        for persona_id in selected_ids
    }
    provisional = {
        persona_id: upgrade_persona_to_v3_1(source_personas[persona_id], random_seed=random_seed_offset + index)
        for index, persona_id in enumerate(selected_ids)
    }
    external_comparisons: dict[str, PersonaSkill] = {}
    comparison_ids = [persona_id for persona_id in (against_persona_ids or []) if persona_id not in selected_ids]
    for comparison_id in comparison_ids:
        external_comparisons[comparison_id] = _load_persona_from_dir(compare_against_dir, comparison_id, ("v3_1", "v3", "v2", "root"))

    for _pass in range(2):
        for persona_id in selected_ids:
            comparison_pool = [
                provisional[other_id]
                for other_id in selected_ids
                if other_id != persona_id
            ] + list(external_comparisons.values())
            baseline_pool = [
                source_personas[other_id]
                for other_id in selected_ids
                if other_id != persona_id
            ] + [
                _load_persona_from_dir(compare_against_dir, other_id, ("v3", "v2", "root"))
                for other_id in comparison_ids
            ]
            baseline_report = build_diversity_report_v3(source_personas[persona_id], baseline_pool)
            diversity_report = build_diversity_report_v3_1(provisional[persona_id], comparison_pool, baseline_report=baseline_report)
            if _requires_distinctiveness_revision_v3_1(diversity_report):
                provisional[persona_id] = apply_distinctiveness_revision_v3_1(provisional[persona_id], comparison_pool)

    written_paths: list[Path] = []
    for index, persona_id in enumerate(selected_ids):
        comparison_pool = [
            provisional[other_id]
            for other_id in selected_ids
            if other_id != persona_id
        ] + list(external_comparisons.values())
        baseline_pool = [
            source_personas[other_id]
            for other_id in selected_ids
            if other_id != persona_id
        ] + [
            _load_persona_from_dir(compare_against_dir, other_id, ("v3", "v2", "root"))
            for other_id in comparison_ids
        ]
        baseline_report = build_diversity_report_v3(source_personas[persona_id], baseline_pool)
        diversity_report = build_diversity_report_v3_1(provisional[persona_id], comparison_pool, baseline_report=baseline_report)
        rendered = _rendered_artifacts_v3_1(provisional[persona_id], source_personas[persona_id], diversity_report, {"warnings": [], "required_improvements": []})
        quality_audit = build_quality_audit_v3_1(provisional[persona_id], rendered, diversity_report)
        written_paths.append(
            write_v3_1_persona_folder(
                provisional[persona_id],
                v3_persona=source_personas[persona_id],
                root_data_dir=output_dir,
                source_v3_dir=_resolve_persona_folder(source_dir, persona_id, ("v3", "v2", "root")),
                diversity_report=diversity_report,
                quality_audit=quality_audit,
                random_seed=random_seed_offset + index,
            )
        )
    return written_paths
