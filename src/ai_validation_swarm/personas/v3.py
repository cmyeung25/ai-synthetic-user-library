from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.v2 import (
    RAW_ENUM_TOKENS as V2_RAW_ENUM_TOKENS,
    _decade_ranges_for_age,
    _dedupe,
    _household_context_phrase,
    _life_arc_summary,
    _locale_texture,
    _occupation_focus,
    _stable_rng,
    prompt_path,
    upgrade_persona_to_v2,
)
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json

PROMPT_VERSIONS = [
    "persona-biography/v3.md",
    "local-grounding/v3.md",
    "sensitive-scenarios/v3.md",
    "persona-voiceprint/v3.md",
    "distinctiveness-revision/v3.md",
    "quality-auditor/v3.md",
]

RAW_ENUM_TOKENS = V2_RAW_ENUM_TOKENS | {
    "shared_household_decider",
    "workflow_maturity",
    "manager_approver",
}

SHARED_TEMPLATE_PHRASES = [
    "not another dashboard",
    "what existing step does this replace",
    "curiosity means the problem statement lands",
    "trial intent appears only when",
    "payment intent appears only after",
]

V3_REQUIRED_FILES = (
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
    "v2_to_v3_diff.md",
)


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_v3_prompt_texts() -> dict[str, str]:
    return {
        prompt_version: prompt_path(prompt_version).read_text(encoding="utf-8").strip()
        for prompt_version in PROMPT_VERSIONS
    }


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _token_set(value: Any) -> set[str]:
    if isinstance(value, dict):
        source = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, list):
        source = " ".join(str(item) for item in value)
    else:
        source = str(value)
    return {token for token in _normalize_text(source).split() if len(token) > 2}


def _token_similarity(left: Any, right: Any) -> float:
    left_tokens = _token_set(left)
    right_tokens = _token_set(right)
    if not left_tokens and not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    universe = left_tokens | right_tokens
    return len(overlap) / max(1, len(universe))


def _text_similarity(left: str, right: str) -> float:
    normalized_left = _normalize_text(left)
    normalized_right = _normalize_text(right)
    if not normalized_left and not normalized_right:
        return 0.0
    token_score = _token_similarity(normalized_left, normalized_right)
    sequence_score = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    return round((token_score * 0.65) + (sequence_score * 0.35), 4)


def _list_of_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return [f"{key}: {value[key]}" for key in sorted(value)]
    if value is None:
        return []
    return [str(value)]


def _flatten_text_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_flatten_text_parts(item))
        return parts
    if isinstance(value, dict):
        parts: list[str] = []
        for key in sorted(value):
            child_parts = _flatten_text_parts(value[key])
            if not child_parts:
                continue
            label = key.replace("_", " ")
            if len(child_parts) == 1:
                parts.append(f"{label}: {child_parts[0]}")
            else:
                parts.append(f"{label}: {'; '.join(child_parts)}")
        return parts
    return [str(value)]


def _stringify_text_field(value: Any, separator: str = " ") -> str:
    return separator.join(part.strip() for part in _flatten_text_parts(value) if str(part).strip())


def _version_dir(base_dir: Path, persona_id: str, version: str) -> Path:
    return base_dir / persona_id / version


def _resolve_persona_folder(base_dir: Path, persona_id: str, preferred_versions: tuple[str, ...] = ("v3", "v2", "root")) -> Path:
    persona_root = base_dir / persona_id
    if not persona_root.exists():
        raise FileNotFoundError(f"Persona '{persona_id}' not found in {base_dir}.")

    for version in preferred_versions:
        if version == "root":
            if (persona_root / "profile.json").exists():
                return persona_root
        else:
            candidate = persona_root / version
            if (candidate / "profile.json").exists():
                return candidate

    if (persona_root / "profile.json").exists():
        return persona_root

    raise FileNotFoundError(f"Could not resolve persona '{persona_id}' in {base_dir}.")


def _load_persona_from_dir(base_dir: Path, persona_id: str, preferred_versions: tuple[str, ...] = ("v3", "v2", "root")) -> PersonaSkill:
    return load_persona(_resolve_persona_folder(base_dir, persona_id, preferred_versions))


def _persona_ids_in(base_dir: Path) -> list[str]:
    if not base_dir.exists():
        return []
    return sorted(path.name for path in base_dir.iterdir() if path.is_dir())


def sync_v2_source_to_canonical(persona_id: str, source_dir: Path, target_base_dir: Path) -> Path:
    source_persona_dir = source_dir / persona_id
    if not source_persona_dir.exists():
        raise FileNotFoundError(f"V2 source for '{persona_id}' not found in {source_dir}.")

    target_persona_root = target_base_dir / persona_id
    target_v2_dir = target_persona_root / "v2"
    ensure_dir(target_persona_root)
    shutil.copytree(source_persona_dir, target_v2_dir, dirs_exist_ok=True)
    return target_v2_dir


def _archetype_key(persona: PersonaSkill) -> str:
    age = int(persona.profile.basic_identity.get("age", 0))
    occupation = str(persona.profile.basic_identity.get("occupation", "")).lower()
    ai_familiarity = str(persona.profile.technology_profile.get("ai_familiarity", "")).lower()

    if age <= 32 and "program manager" in occupation:
        return "early_career_practical_trial_user"
    if age >= 50 and "operations manager" in occupation:
        return "mature_operator_retention_skeptic"
    if "privacy" in str(persona.seed.panel_role).lower():
        return "privacy_absolutist"
    if ai_familiarity == "high":
        return "ambitious_adopter"
    return "workflow_skeptic"


def _panel_role_profile(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "panel_role": "mainstream_buyer",
            "behavioural_archetype": archetype,
            "research_function": "detects whether a product can earn a real first trial without asking for a full routine rebuild",
            "what_this_person_is_good_at_detecting": [
                "lightweight trial credibility",
                "peer-proof dependence",
                "early-career social risk",
                "demo clarity versus weekday reality",
            ],
            "what_this_person_will_overweight": [
                "small first-step usability",
                "practical demos",
                "looking competent while trying something new",
            ],
            "what_this_person_may_miss": [
                "long-run maintenance debt that takes months to surface",
                "compliance-heavy buying logic",
                "specialist power-user appetite for complexity",
            ],
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "panel_role": "skeptic",
            "behavioural_archetype": archetype,
            "research_function": "detects hidden maintenance cost, weak retention logic, vague workflow claims, and disclosure-control gaps",
            "what_this_person_is_good_at_detecting": [
                "demo-to-retention gap",
                "maintenance transfer to the user",
                "weak disclosure control",
                "performative inclusivity with no practical safeguards",
            ],
            "what_this_person_will_overweight": [
                "time protection",
                "long-term routine fit",
                "privacy and dignity cost",
                "post-trial upkeep",
            ],
            "what_this_person_may_miss": [
                "youth novelty appeal",
                "social momentum from early adopters",
                "high-energy experimentation that tolerates messy first weeks",
            ],
        }
    return {
        "panel_role": str(persona.seed.panel_role),
        "behavioural_archetype": archetype,
        "research_function": "tests whether the product earns space in ordinary routines",
        "what_this_person_is_good_at_detecting": ["unclear value", "trust gaps", "hidden friction"],
        "what_this_person_will_overweight": ["practical fit", "clarity"],
        "what_this_person_may_miss": ["high-tolerance early adopter behavior"],
    }


def _local_grounding_layer(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    location = str(identity.get("location", ""))
    if location == "Penang":
        return {
            "city_or_region_specific_context": [
                "Work talk often continues in WhatsApp threads long after the formal meeting ends.",
                "Practical product opinions are often reinforced over coffee or food rather than through formal tool evaluation sessions.",
                "Regional service rhythms reward what works reliably, not what sounds globally polished.",
            ],
            "common_apps_or_services": [
                "WhatsApp",
                "Grab",
                "Touch 'n Go eWallet",
                "Shopee",
                "Google Sheets",
                "YouTube",
            ],
            "payment_and_commerce_context": [
                "Monthly software spend is mentally converted into MYR household reality very quickly.",
                "Trial-to-paid decisions feel different when a subscription competes with ordinary recurring costs rather than a dedicated software budget.",
            ],
            "mobility_or_commute_context": [
                "Short travel windows and in-between moments make mobile readability matter.",
                "A tool that needs a quiet desktop-only setup loses momentum quickly.",
            ],
            "language_switching_scenes": [
                "English is fine for demos, but cost-benefit discussion may shift into Mandarin or family shorthand when the spend feels real.",
                "Peer recommendation lands better when the language sounds practical rather than corporate.",
            ],
            "family_or_household_norms": [
                "Family routines can influence whether a recurring spend feels sensible or indulgent.",
                "Advice from older relatives may not decide the purchase, but it shapes whether the spend feels defensible.",
            ],
            "workplace_norms": [
                "People may say a workflow looks useful before they know whether they will actually keep using it.",
                "Operational convenience often beats formal process purity.",
            ],
            "trust_cues_in_this_market": [
                "Clear MYR framing or at least an obvious sense of local affordability.",
                "Specific examples from similar Southeast Asian team routines.",
                "Plain onboarding expectations rather than imported startup hype.",
            ],
            "pricing_localization_reaction": "USD-style SaaS pricing feels less credible unless the product clearly earns its place in MYR everyday reality.",
            "what_feels_imported_or_not_local": "English-only startup language, US-first salary assumptions, and feature copy that ignores messaging-heavy coordination feel imported.",
            "local_discovery_channels": [
                "peer referral",
                "practical demo clips",
                "search when a recurring pain point becomes obvious",
                "WhatsApp or small work-circle recommendations",
            ],
            "local_sensitivity_notes": [
                "A product that sounds too polished but not locally grounded can feel expensive before it even shows price.",
                "Trust rises when a product respects mixed-language, messaging-heavy routines without making them sound unsophisticated.",
            ],
        }

    if location == "Kuala Lumpur":
        return {
            "city_or_region_specific_context": [
                "Urban choice density makes generic software promises easier to dismiss.",
                "The product has to feel operationally useful, not just globally respectable.",
                "KL routines reward tools that survive context switching between work, household, and travel time.",
            ],
            "common_apps_or_services": [
                "WhatsApp",
                "Grab",
                "Touch 'n Go eWallet",
                "Maybank2u",
                "LinkedIn",
                "YouTube search",
            ],
            "payment_and_commerce_context": [
                "Pricing shown only in USD invites a second layer of skepticism about local relevance.",
                "Recurring software spend is judged against other urban monthly commitments, not against founder logic alone.",
            ],
            "mobility_or_commute_context": [
                "LRT, MRT, and Grab transitions create many short evaluation windows but few long setup windows.",
                "A product that only makes sense in long desktop sessions feels fragile.",
            ],
            "language_switching_scenes": [
                "English can carry the software explanation, but trust may depend on whether the tone still feels locally sensible.",
                "Malay or mixed English-Malay context matters when the product touches household or service coordination.",
            ],
            "family_or_household_norms": [
                "Shared-household decisions often involve quiet explainability, not dramatic approval rituals.",
                "A tool that creates public identity discomfort at home will be used less, even if the feature set is good.",
            ],
            "workplace_norms": [
                "People may praise process improvement before proving they will maintain it.",
                "A service-ops environment respects competence and continuity more than founder excitement.",
            ],
            "trust_cues_in_this_market": [
                "Control over disclosure fields and profile visibility.",
                "Local pricing logic or at least credible MYR translation.",
                "Evidence that the tool respects long-running operational routines rather than idealized SaaS teams.",
            ],
            "pricing_localization_reaction": "If the product feels priced for imported SaaS norms instead of KL monthly reality, trust drops before the feature conversation finishes.",
            "what_feels_imported_or_not_local": "US-first pricing posture, English-only identity flows, and inclusive branding without privacy control feel imported.",
            "local_discovery_channels": [
                "YouTube comparison search",
                "LinkedIn operator recommendations",
                "WhatsApp peer referral",
                "search triggered by repeated workflow pain",
            ],
            "local_sensitivity_notes": [
                "Optional disclosure and control over public-facing identity matter more than loud inclusive language.",
                "Corporate polish helps only if the product still feels usable in a real ops environment.",
            ],
        }

    return {
        "city_or_region_specific_context": [_locale_texture(identity)],
        "common_apps_or_services": ["WhatsApp", "search", "messaging apps"],
        "payment_and_commerce_context": ["Local affordability matters more than abstract pricing logic."],
        "mobility_or_commute_context": ["Short attention windows shape product evaluation."],
        "language_switching_scenes": ["Trust shifts with audience and context."],
        "family_or_household_norms": ["Household explanation burden changes adoption comfort."],
        "workplace_norms": ["Public agreement is not the same as operational adoption."],
        "trust_cues_in_this_market": ["Practical local examples", "clear pricing logic"],
        "pricing_localization_reaction": "Local affordability shapes trust.",
        "what_feels_imported_or_not_local": "Positioning that ignores local routine reality feels imported.",
        "local_discovery_channels": ["search", "peer recommendation"],
        "local_sensitivity_notes": ["Context matters more than stereotype."],
    }


def _sensitive_scenario_reactions(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    is_non_binary = str(identity.get("gender", "")).lower() == "non-binary"
    archetype = _archetype_key(persona)

    identity_disclosure = {
        "trigger_scenarios": [
            "binary-only gender field",
            "mandatory title such as Mr, Ms, or Mrs",
            "public profile that shows gender marker by default",
            "optional disclosure with a clear purpose",
        ],
        "reaction": "Will notice whether disclosure is necessary before deciding how much trust to offer.",
        "what_builds_trust": "Optional disclosure, a clear reason for asking, and control over who sees the answer.",
        "what_reduces_trust": "Forced labels, public defaults, and identity fields shown before the product has earned relevance.",
    }
    if is_non_binary:
        identity_disclosure = {
            "trigger_scenarios": [
                "binary-only gender field",
                "mandatory title such as Mr, Ms, or Mrs",
                "public profile with gender marker shown by default",
                "household flows that assume husband or wife labels",
                "inclusive marketing with no privacy control",
                "optional disclosure with clear purpose and prefer-not-to-say option",
            ],
            "reaction": "Trust tends to drop quietly rather than explosively. They may disengage rather than complain unless the exclusion is obvious and actionable.",
            "what_builds_trust": "Prefer-not-to-say, optional disclosure, profile visibility controls, and language that does not force a public label before value is clear.",
            "what_reduces_trust": "Performative inclusion with no control, mandatory titles, and household assumptions that flatten real life into binary defaults.",
        }

    return {
        "identity_disclosure": identity_disclosure,
        "privacy_and_data": {
            "trigger_scenarios": [
                "connect work messages before trust exists",
                "upload household or personal history during onboarding",
                "AI summary with unclear retention or training policy",
            ],
            "reaction": "The persona asks whether the product earns the right to see this data now, not eventually.",
            "what_builds_trust": "Bounded permissions, plain data handling language, and reversible setup steps.",
            "what_reduces_trust": "Broad permissions early, vague AI language, and hidden defaults.",
        },
        "political_or_public_expression": {
            "trigger_scenarios": [
                "public feed with identity markers",
                "community features that encourage visible opinion sharing",
                "brand copy that implies one correct social posture",
            ],
            "reaction": "More likely to go quiet than perform agreement in public.",
            "what_builds_trust": "Private participation options and low-pressure public visibility settings.",
            "what_reduces_trust": "Forced visibility and copy that treats public expression as a default sign of trust.",
        },
        "fairness_and_inclusion": {
            "trigger_scenarios": [
                "founder copy that praises inclusivity without changing the workflow",
                "default-user examples that erase non-standard households or identities",
                "onboarding that assumes one life pattern",
            ],
            "reaction": "Looks for whether inclusion changes comfort and control, not just tone.",
            "what_builds_trust": "Concrete control, respectful defaults, and examples that do not flatten different users into a checklist.",
            "what_reduces_trust": "Inclusive branding that still forces the user into imported assumptions.",
        },
        "family_or_household_assumptions": {
            "trigger_scenarios": [
                "partner flows that assume one household decision-maker",
                "family features that assume every household wants shared visibility",
                "child or elder care language that sounds moralizing",
            ],
            "reaction": "Questions whether the product understands that household comfort is uneven, not uniform.",
            "what_builds_trust": "Optional sharing and user control over how visible a task or identity becomes.",
            "what_reduces_trust": "One-size-fits-all household defaults and forced role labels.",
        },
        "workplace_visibility": {
            "trigger_scenarios": [
                "manager dashboard that exposes incomplete setup",
                "team workflow where mistakes become publicly visible too early",
                "AI suggestions shown to others before the user checks them",
            ],
            "reaction": "Will slow adoption if the product makes learning cost visible before competence is built.",
            "what_builds_trust": "Private draft space, staged sharing, and clear user control.",
            "what_reduces_trust": "Public visibility before the user understands the tool's failure modes.",
        },
        "financial_vulnerability": {
            "trigger_scenarios": [
                "annual lock-in during uncertain monthly cash flow",
                "pricing shown only in USD",
                "upsell copy that treats budget hesitation as unserious",
            ],
            "reaction": "Budget pressure is handled as dignity-sensitive, not as simple price resistance.",
            "what_builds_trust": "Month-to-month clarity, local pricing realism, and respectful downgrade or exit paths.",
            "what_reduces_trust": "Aggressive annual pressure and imported affordability assumptions.",
        },
        "health_or_wellbeing_sensitivity": {
            "trigger_scenarios": [
                "tracking tools that sound judgmental",
                "wellbeing prompts shown in public contexts",
                "sensitive self-reporting before trust exists",
            ],
            "reaction": "Avoids products that turn support into surveillance or moral performance.",
            "what_builds_trust": "Neutral tone, private control, and clear limits on what the product can infer.",
            "what_reduces_trust": "Guilt-based copy and overconfident interpretation of sensitive states.",
        },
    }


def _voiceprint(persona: PersonaSkill, *, contrast_mode: bool = False) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "speaking_style": "collaborative, cautious, and practical without sounding cold",
            "sentence_length": "short_to_medium",
            "directness_pattern": "starts socially careful, then becomes more concrete when risk to routine is obvious",
            "metaphors_or_phrases": [
                "smallest version that works",
                "fit it into my week",
                "I do not want to overcommit too early",
            ],
            "how_they_soften_disagreement": "Acknowledges the problem and the founder effort before narrowing the commitment.",
            "how_they_get_more_direct": "Shifts from interest language to first-step language: what is the lightest safe experiment?",
            "what_they_repeat_when_skeptical": "Show me the smallest version that works in a normal week.",
            "what_they_never_say": [
                "This is obviously garbage.",
                "Nobody would use this.",
            ],
            "example_positive_reaction": "That actually looks manageable. If the first step is as small as you say, I would try it on one recurring handoff first.",
            "example_polite_rejection": "I can see why it matters. I just do not think I would commit until I see a lighter first step.",
            "example_hard_rejection": "This already sounds like extra process. I understand the problem, but I still would not put this into my week.",
            "example_near_purchase_question": "If I start with one workflow, what do I actually need to set up in the first 15 minutes?",
        }
    if archetype == "mature_operator_retention_skeptic":
        direct_phrase = "I have seen this pattern before." if contrast_mode else "Show me where the upkeep goes after the demo."
        return {
            "speaking_style": "experienced, compressed, and more direct once a familiar founder pattern appears",
            "sentence_length": "medium",
            "directness_pattern": "does not waste words when maintenance burden or disclosure control looks weak",
            "metaphors_or_phrases": [
                direct_phrase,
                "the maintenance moves to the user",
                "what still survives after month one",
            ],
            "how_they_soften_disagreement": "Uses reserved language rather than warm encouragement.",
            "how_they_get_more_direct": "Moves quickly from concept to burden transfer, retention logic, and disclosure control.",
            "what_they_repeat_when_skeptical": "Show me what burden leaves the user, not what feature arrives.",
            "what_they_never_say": [
                "I love this already.",
                "This feels magical.",
            ],
            "example_positive_reaction": "This is more credible. I can see where it earns a place if the routine still holds after the first month.",
            "example_polite_rejection": "I follow the idea. I just do not see evidence that the maintenance stays low.",
            "example_hard_rejection": "I have seen this pattern before. The demo concentrates the benefit and exports the upkeep to the user. I would pass.",
            "example_near_purchase_question": "After the trial, which existing check, message, or spreadsheet line disappears for good?",
        }
    return {
        "speaking_style": "practical",
        "sentence_length": "medium",
        "directness_pattern": "becomes direct when trust drops",
        "metaphors_or_phrases": ["show me the real use case"],
        "how_they_soften_disagreement": "Acknowledges relevance before withholding commitment.",
        "how_they_get_more_direct": "Asks what real burden disappears.",
        "what_they_repeat_when_skeptical": "Show me the real use case.",
        "what_they_never_say": ["This is perfect."],
        "example_positive_reaction": "I can see the use if the first week stays as simple as the demo.",
        "example_polite_rejection": "I understand it, but I do not see enough reason to change my current habit.",
        "example_hard_rejection": "This creates more process than relief.",
        "example_near_purchase_question": "What exactly would stop happening if this worked?",
    }


def _specific_chapter_scene(persona: PersonaSkill, age_range: str) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    location = str(persona.profile.basic_identity.get("location", ""))
    if archetype == "early_career_practical_trial_user":
        scenes = {
            "0-9": {
                "specific_scene": "At a Penang coffee shop after weekend errands, Daniel watched adults compare two repair options for a household problem. The cheaper option was rejected because it would require another return visit if it failed.",
                "product_relevant_memory": "He remembers that the winning option was not the one with the best pitch, but the one that reduced repeat hassle.",
                "social_or_relationship_context": "Household decisions were discussed in a practical, matter-of-fact tone rather than as big financial strategy.",
                "money_or_effort_tradeoff": "Saving a little money did not win if it created another round of effort later.",
                "beliefs_formed": ["Repeat hassle is a real cost even when it does not appear on the receipt."],
                "current_reaction_link": "This is why he reacts well to products that promise a small but durable reduction in follow-up work.",
                "formative_level": "medium",
            },
            "10-19": {
                "specific_scene": "At 17, Daniel helped keep a student project moving across WhatsApp messages, shared docs, and last-minute reminders. The group sounded aligned in chat, but deadlines still slipped because nobody owned the final follow-up.",
                "product_relevant_memory": "He learned early that a tool can look collaborative while still leaving the real coordination burden on the most conscientious person.",
                "social_or_relationship_context": "He wanted to look dependable without becoming the person who nagged everyone publicly.",
                "money_or_effort_tradeoff": "The trade-off was not money yet; it was whether the extra organizing effort was worth the social awkwardness.",
                "beliefs_formed": ["Visible coordination is only useful if someone actually changes behavior."],
                "current_reaction_link": "This is why polite enthusiasm from a team does not automatically sound like adoption intent to him.",
                "formative_level": "high",
            },
            "20-29": {
                "specific_scene": "At 25, Daniel tried a lightweight tracking board for recurring vendor follow-up in program work. Colleagues liked the idea in the demo, but within two weeks they slipped back into WhatsApp because duplicate updates felt heavier than the missed follow-up they were supposed to prevent.",
                "product_relevant_memory": "He still remembers how fast an apparently clean workflow lost support once it asked for extra maintenance during a busy week.",
                "social_or_relationship_context": "He wanted to look capable in an early-career role, so he noticed how risky it feels to champion a tool before the routine proves itself.",
                "money_or_effort_tradeoff": "The tool was not expensive, but the social and attention cost of pushing it felt high.",
                "beliefs_formed": ["A bounded trial is believable; a full workflow conversion is not."],
                "current_reaction_link": "Now he asks for the smallest working version before he offers real buy-in.",
                "formative_level": "high",
            },
        }
        return scenes[age_range]

    if archetype == "mature_operator_retention_skeptic":
        scenes = {
            "0-9": {
                "specific_scene": "As a child in Kuala Lumpur, Jordan watched a parent rewrite the same household numbers into a notebook after an earlier page had become too messy to trust.",
                "product_relevant_memory": "The lesson was that once a record stops feeling dependable, people quietly rebuild their own version somewhere else.",
                "social_or_relationship_context": "Reliability at home was shown through steady follow-through, not through dramatic statements.",
                "money_or_effort_tradeoff": "The effort of rewriting everything felt preferable to living with an unreliable record.",
                "beliefs_formed": ["People create shadow systems when the official one stops feeling trustworthy."],
                "current_reaction_link": "This is why Jordan pays attention to where users will keep private backup habits after adoption.",
                "formative_level": "medium",
            },
            "10-19": {
                "specific_scene": "In the early 1980s, Jordan helped keep simple paper schedules and phone-call reminders straight for shared responsibilities. One missed handoff was enough to show how a tidy plan on paper could still fail if upkeep lived in one person's memory.",
                "product_relevant_memory": "The failure was not dramatic; it was ordinary and repeatable, which made it memorable.",
                "social_or_relationship_context": "Avoiding embarrassment mattered, but so did not making one person carry every reminder.",
                "money_or_effort_tradeoff": "The cost was time and repetition rather than software spend.",
                "beliefs_formed": ["A system only counts if the upkeep is shared and realistic."],
                "current_reaction_link": "Now Jordan distrusts centralization claims that never explain who performs the maintenance.",
                "formative_level": "medium",
            },
            "20-29": {
                "specific_scene": "Early in office life, Jordan watched a paper-and-spreadsheet process get praised as modernization while the real burden simply moved onto whoever stayed late enough to reconcile the numbers.",
                "product_relevant_memory": "The language was about efficiency; the lived reality was duplicate work hidden behind a neater surface.",
                "social_or_relationship_context": "Jordan learned to notice who absorbs the invisible cleanup after a process change.",
                "money_or_effort_tradeoff": "The new process looked worth funding because it appeared more professional, even though the effort bill moved to staff time.",
                "beliefs_formed": ["Efficiency claims need a labor map, not just a feature list."],
                "current_reaction_link": "This is why Jordan asks what burden moves to the user after the demo.",
                "formative_level": "high",
            },
            "30-39": {
                "specific_scene": "At 34, Jordan helped roll out a shared spreadsheet for recurring service issues. The first week looked promising, but within a month most updates had moved back to WhatsApp because the spreadsheet required duplicate entry and nobody wanted to own the cleanup.",
                "product_relevant_memory": "That rollback is still the reference point whenever a founder says a tool will centralize everything.",
                "social_or_relationship_context": "People praised the idea in meetings but protected themselves by reverting to the channel that actually fit their day.",
                "money_or_effort_tradeoff": "The spreadsheet was cheap. The real cost was the extra maintenance and the subtle blame that followed missed updates.",
                "beliefs_formed": ["Adoption theater is common when the maintenance story is weak."],
                "current_reaction_link": "Now Jordan distinguishes clearly between demo comprehension and durable behavior change.",
                "formative_level": "high",
            },
            "40-49": {
                "specific_scene": "In a later operations role, Jordan saw a reporting dashboard introduced as a visibility solution. It did produce a cleaner record, but only after frontline staff created manual workarounds to feed it the data it expected.",
                "product_relevant_memory": "The tool did not fail in the demo sense. It failed in the retention sense because the burden kept returning to the user.",
                "social_or_relationship_context": "People did not openly rebel; they quietly bypassed the workflow and maintained a second system.",
                "money_or_effort_tradeoff": "Management saw software value, while staff absorbed the hidden effort tax.",
                "beliefs_formed": ["A polished record can simply become a record of user effort."],
                "current_reaction_link": "That memory sharpens Jordan's radar for products that create proof of work instead of removing work.",
                "formative_level": "high",
            },
            "50-59": {
                "specific_scene": "More recently, Jordan has watched vendors talk convincingly about AI assistance and inclusive design while still forcing users into rigid profile fields, public defaults, and month-two upkeep that nobody mentioned during onboarding.",
                "product_relevant_memory": "The mismatch between progressive language and weak control settings leaves a stronger impression than the feature list itself.",
                "social_or_relationship_context": "Jordan is unlikely to argue theatrically. Trust simply drops, and the product loses the benefit of the doubt.",
                "money_or_effort_tradeoff": "At this stage the real question is whether the tool earns protected space in a finite routine, not whether it looks current.",
                "beliefs_formed": ["Respect without control is branding, not safety."],
                "current_reaction_link": "This is why Jordan now tests products for month-two fit, disclosure control, and maintenance transfer before anything else.",
                "formative_level": "high",
            },
        }
        return scenes[age_range]

    return {
        "specific_scene": f"A formative {age_range} scene in {location} taught this persona to look past polished claims.",
        "product_relevant_memory": "The memorable lesson was that visible promises and lived routines often diverge.",
        "social_or_relationship_context": "Social comfort shaped whether the persona would keep using a system once novelty faded.",
        "money_or_effort_tradeoff": "Effort and explainability mattered as much as price.",
        "beliefs_formed": ["A tool must fit ordinary behavior, not ideal behavior."],
        "current_reaction_link": "This still shapes how the persona reacts to product claims today.",
        "formative_level": "medium",
    }


def _canonical_biography_v3(persona: PersonaSkill) -> dict[str, Any]:
    upgraded = copy.deepcopy(persona.profile.canonical_biography)
    chapters: list[dict[str, Any]] = []
    for age_range, start, end in _decade_ranges_for_age(int(persona.profile.basic_identity.get("age", 0))):
        scene_block = _specific_chapter_scene(persona, age_range)
        chapter = {
            "age_range": age_range,
            "chapter_title": {
                "0-9": "Ordinary reliability lessons",
                "10-19": "Learning what follow-through actually costs",
                "20-29": "Early adult experiments under real constraints",
                "30-39": "Workflow reality against process optimism",
                "40-49": "Pattern recognition sharpens",
                "50-59": "Retention becomes the real test",
                "60-69": "Selectivity becomes active strategy",
                "70+": "Only durable value survives",
            }[age_range],
            "life_context": f"{persona.profile.basic_identity['name']} lived this stage through {_household_context_phrase(persona.profile.basic_identity)} and {_locale_texture(persona.profile.basic_identity)}.",
            **scene_block,
        }
        chapters.append(chapter)

    current_identity = (
        f"{persona.profile.basic_identity['name']} wants to look credible without carrying avoidable maintenance for other people's systems."
        if _archetype_key(persona) == "mature_operator_retention_skeptic"
        else f"{persona.profile.basic_identity['name']} wants to look capable, avoid overcommitting too early, and keep experiments small enough to survive a normal week."
    )
    return {
        **upgraded,
        "life_arc_summary": _life_arc_summary(persona),
        "decade_timeline": chapters,
        "formative_events": [
            {
                "age_range": chapter["age_range"],
                "event_summary": chapter["specific_scene"],
                "impact": chapter["current_reaction_link"],
                "formative_level": chapter["formative_level"],
            }
            for chapter in chapters
        ],
        "current_identity": current_identity,
        "current_daily_life": persona.profile.life_story.get("current_daily_routine", ""),
    }


def _daily_micro_behaviours_v3(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "morning_routine": "Checks WhatsApp, calendar, and outstanding follow-up before the day settles, often while planning the first coffee stop or commute transition.",
            "commute_or_transition_time": "Uses small transitions for demo clips, saved links, or clarifying what actually needs action today.",
            "work_start_pattern": "Begins with triage, then looks for one bounded win before the meeting traffic grows.",
            "message_checking_pattern": "Checks more often than preferred because missing a follow-up feels like looking less capable than he wants to look.",
            "break_time_behaviour": "Breaks become product-comparison moments more often than intentional rest.",
            "evening_routine": "Evening setup tolerance drops sharply after 9pm; if a product still needs decisions then, it usually slips.",
            "weekend_pattern": "A mix of recovery, small errands, and low-pressure curiosity rather than full system rebuilding.",
            "shopping_moments": "Most persuadable right after a repeated annoyance, especially when a peer shows a practical demo.",
            "decision_moments": "Decides when the first step feels small enough not to embarrass him if it fails.",
            "stress_moments": "Stress spikes when too many loose threads make him feel reactive instead of dependable.",
            "when_they_are_most_open_to_new_products": "After a messy handoff, missed follow-up, or peer demo that looks lightweight enough to try quietly.",
            "when_they_are_least_open_to_new_products": "Late at night, during stacked admin days, or when the product assumes full routine conversion.",
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "morning_routine": "Carries forward yesterday's unresolved details first, then decides which operational issues are real enough to earn attention today.",
            "commute_or_transition_time": "Uses short windows for YouTube comparison search, Maybank checks, or scanning whether a product explains itself honestly.",
            "work_start_pattern": "Starts deliberately, but quickly tests which promises survive contact with a real operational morning.",
            "message_checking_pattern": "Checks messages because exceptions are how routine failure announces itself.",
            "break_time_behaviour": "Will read a practical review or support article, but not a long founder essay.",
            "evening_routine": "Can tolerate light evaluation in the evening, but not setup that feels like unpaid extra operations work.",
            "weekend_pattern": "Protects weekends more actively and resents products that assume spare attention is always available.",
            "shopping_moments": "Most persuadable when a product acknowledges retention, disclosure control, and long-term fit without being prompted.",
            "decision_moments": "Decides only after asking what burden disappears and what burden quietly shifts onto the user.",
            "stress_moments": "Stress rises when a supposedly helpful system creates a second private workaround.",
            "when_they_are_most_open_to_new_products": "When a recurring operational drag has become undeniable and the product shows month-two realism.",
            "when_they_are_least_open_to_new_products": "When the product sounds more impressed by its own positioning than by the user's upkeep cost.",
        }
    return persona.profile.daily_micro_behaviours


def _interests_and_hobbies_v3(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "primary_interests": [
                "small workflow experiments that feel reversible",
                "comparison-shopping practical software",
                "coffee or food routines that double as informal debrief time",
            ],
            "secondary_interests": [
                "short-form implementation demos",
                "peer recommendations that come with real screenshots or examples",
                "light budgeting that keeps subscriptions honest",
            ],
            "low_energy_hobbies": [
                "watching product walkthroughs during short breaks",
                "saving useful links and only revisiting the best ones",
                "tidying one corner of a digital workflow without fixing the whole system",
            ],
            "social_hobbies": [
                "small catch-ups where practical recommendations travel quickly",
                "sharing one genuinely useful tip rather than becoming the loudest recommender",
            ],
            "private_hobbies": [
                "quietly testing a tool before talking about it",
                "keeping personal notes on what almost worked",
            ],
            "aspirational_hobbies": [
                "building a calmer weekly reset routine",
                "finding one restorative hobby that does not become another optimization project",
            ],
            "abandoned_hobbies": [
                "systems that were fun to set up but too demanding to maintain",
            ],
            "hobbies_they_claim_to_have_but_rarely_do": [
                "keeping every note and reminder system fully tidy",
            ],
            "interest_depth": [
                {
                    "interest_name": "small workflow experiments that feel reversible",
                    "depth_level": "deep",
                    "why_it_matters": "It lets Daniel feel capable without betting too much social capital at once.",
                    "how_it_shapes_purchase_behaviour": "He notices whether a product can start small and stay socially low-risk.",
                    "related_products_they_notice": ["lightweight AI helpers", "workflow templates", "task capture tools"],
                    "related_products_they_ignore": ["full-stack systems that demand immediate migration"],
                }
            ],
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "primary_interests": [
                "spotting where recurring process failures actually begin",
                "comparison-reading practical tools before they touch a live routine",
                "routine improvements that reduce maintenance rather than increase visibility",
            ],
            "secondary_interests": [
                "operator-style reviews",
                "searching for what happened after month one, not just at launch",
                "keeping a few dependable habits instead of trying every new system",
            ],
            "low_energy_hobbies": [
                "watching one or two practical demos before deciding whether more research is justified",
                "reading comment threads for failure modes rather than hype",
                "small home or desk resets that restore control without becoming a big project",
            ],
            "social_hobbies": [
                "small meals or catch-ups where real operator stories are exchanged",
                "low-drama recommendation sharing when something actually held up",
            ],
            "private_hobbies": [
                "quietly tracking whether a product survives its own promises",
                "keeping backup notes because trust is earned slowly",
            ],
            "aspirational_hobbies": [
                "a leisure habit that is restorative without needing performance",
                "using fewer systems, but trusting them more",
            ],
            "abandoned_hobbies": [
                "software routines that looked efficient but exported too much upkeep",
            ],
            "hobbies_they_claim_to_have_but_rarely_do": [
                "revisiting every saved long-form article before deciding",
            ],
            "interest_depth": [
                {
                    "interest_name": "spotting where recurring process failures actually begin",
                    "depth_level": "identity-level",
                    "why_it_matters": "It is bound up with how Jordan understands competence and long-run credibility.",
                    "how_it_shapes_purchase_behaviour": "Jordan looks past launch excitement and examines where maintenance, disclosure, and failure handling land after onboarding.",
                    "related_products_they_notice": ["ops tools", "retention-sensitive workflow systems", "identity-aware account settings"],
                    "related_products_they_ignore": ["novelty-first launches with no upkeep story"],
                }
            ],
        }
    return persona.profile.interests_and_hobbies


def _pricing_logic_v3(persona: PersonaSkill) -> dict[str, Any]:
    base = copy.deepcopy(persona.profile.pricing_logic)
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        base.update(
            {
                "price_sensitivity_level": "medium_high",
                "personal_payment_comfort": "Can justify a monthly spend if the first win is quick and the tool helps him look more reliable, not just more organized on paper.",
                "preferred_pricing_model": "clean monthly plan with a genuinely lightweight trial",
                "maximum_comfortable_price_band": "$8-20/month personal, with better odds if the price feels sane in MYR and the setup is low-friction",
                "pricing_objection": "If I am still doing the same follow-up work plus maintaining this tool, I will pull back fast.",
                "what_makes_price_feel_fair": "A visible first-week win, local affordability logic, and an experiment small enough to survive a busy week.",
                "what_makes_price_feel_suspicious": "USD-style software pricing that assumes a bigger discretionary budget than his actual week allows.",
            }
        )
    elif archetype == "mature_operator_retention_skeptic":
        base.update(
            {
                "personal_payment_comfort": "Will pay if the product demonstrably reduces recurring upkeep, not just if it looks operationally respectable.",
                "work_payment_comfort": "More comfortable when the price can be defended in reduced maintenance, cleaner retention, or better disclosure control.",
                "preferred_pricing_model": "monthly or quarterly, with clean exit terms and no forced annual optimism",
                "maximum_comfortable_price_band": "$10-25/month with a clean monthly exit, unless the spend protects a clearly expensive recurring problem",
                "pricing_objection": "I have seen too many tools price the promise and leave the maintenance bill with the user.",
                "what_makes_price_feel_fair": "Local reality, durable routine fit, and a credible month-two story.",
                "what_makes_price_feel_suspicious": "Imported SaaS pricing logic, annual lock-in, and any model that expects trust before control.",
            }
        )
    return base


def _product_reaction_rules_v3(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "first_checks": [
                "Can I test this quietly on one recurring task first?",
                "Will this make me look more capable or just make me maintain another thing?",
                "Does the founder show the smallest realistic first use case?",
            ],
            "positive_signals": [
                "bounded first step",
                "practical demo from a similar work rhythm",
                "month-to-month price that feels sane in local reality",
            ],
            "negative_signals": [
                "setup that looks heavier than the current workaround",
                "language that sounds impressive but not usable on a weekday",
                "pressure to commit before the first small win appears",
            ],
            "questions_they_would_ask": [
                "What can I try first without rebuilding my routine?",
                "What would I actually stop doing if this worked?",
                "What happens if I lose momentum after the first week?",
            ],
            "claims_they_distrust": [
                "seamless adoption for busy teams",
                "automatic organization without behavior change",
                "AI magic that saves time immediately",
            ],
            "evidence_that_changes_their_mind": [
                "a practical demo from a similar role",
                "proof that the first step is small",
                "signs the tool survives interruptions",
            ],
            "likely_false_positive_interest": "May sound encouraging because the concept feels relevant, even when he is only buying time to think.",
            "difference_between_curiosity_and_purchase": "Interest means the pain feels real. Trial starts only if the first step feels light enough for a normal week. Payment comes later, after the experiment survives interruption and still reduces follow-up.",
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "first_checks": [
                "What burden moves to the user after the demo?",
                "Does this still make sense after the first month?",
                "Where does disclosure control live if the product touches identity or household context?",
            ],
            "positive_signals": [
                "credible retention logic",
                "low-maintenance setup with clear visibility controls",
                "pricing that respects local monthly reality",
            ],
            "negative_signals": [
                "performative inclusivity with weak controls",
                "a dashboard that records user effort instead of reducing it",
                "founder optimism that treats understanding as adoption",
            ],
            "questions_they_would_ask": [
                "Which routine cost disappears for good if this works?",
                "What breaks in month two if the user stops being diligent?",
                "Can I use this without disclosing more than I need to?",
            ],
            "claims_they_distrust": [
                "centralize everything",
                "frictionless onboarding for real teams",
                "inclusive by design without showing the controls",
            ],
            "evidence_that_changes_their_mind": [
                "retention evidence after the demo phase",
                "clear user-control settings",
                "proof that a known workaround can be retired",
            ],
            "likely_false_positive_interest": "May continue the conversation because the founder is articulate, not because the product has earned trust.",
            "difference_between_curiosity_and_purchase": "Understanding the pitch is not the same as making room for it. Trial begins when the upkeep looks bounded. Payment only follows if the routine still holds after goodwill and novelty are gone.",
        }
    return copy.deepcopy(persona.profile.product_reaction_rules)


def _cross_domain_model_v3(persona: PersonaSkill, *, contrast_mode: bool = False) -> dict[str, Any]:
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "generic_new_product": {
                "reaction_basis": "Daniel wants experiments that stay small enough to survive a normal week.",
                "first_question": "Can I try the smallest version of this without creating cleanup if it fails?",
                "positive_trigger": "A bounded first use case that looks realistic on a busy weekday.",
                "negative_trigger": "Immediate pressure to reorganize the whole routine.",
                "trust_requirement": "A practical demo from a similar work rhythm.",
                "likely_objection": "I understand the idea. I just do not want to overcommit before I know it fits.",
                "persona_specific_example": "If this can start with one recurring handoff instead of my whole week, I will pay more attention.",
            },
            "ai_product": {
                "reaction_basis": "He is willing to try AI if it reduces follow-up without making him babysit it.",
                "first_question": "Will this actually help from day one, or do I have to teach it my whole workflow first?",
                "positive_trigger": "AI that shortens message follow-up or next-step capture quickly.",
                "negative_trigger": "AI positioning that sounds clever but still needs manual checking on every pass.",
                "trust_requirement": "Clear boundaries on what the model sees and what still needs a human check.",
                "likely_objection": "If I still have to verify every step, this sounds more like another layer than real help.",
                "persona_specific_example": "I would try AI for follow-up summaries before I would trust it with a full workflow reset.",
            },
            "subscription_product": {
                "reaction_basis": "Recurring spend feels acceptable only if the first win happens fast enough to justify it.",
                "first_question": "Can I stay month-to-month until I know it actually survives my week?",
                "positive_trigger": "Low-friction trial with a clear monthly exit.",
                "negative_trigger": "Annual pressure before the product has earned routine trust.",
                "trust_requirement": "Local affordability logic and a believable first-week payoff.",
                "likely_objection": "I can see why some people would pay. I just would not do it until the small version proves itself.",
                "persona_specific_example": "A month-to-month plan feels easier to defend than a larger commitment I may not keep using.",
            },
            "family_or_household_product": {
                "reaction_basis": "Household tools have to respect mixed attention and uneven enthusiasm.",
                "first_question": "Would this actually fit how people already coordinate, or would it become one more thing I am trying to introduce?",
                "positive_trigger": "Works alongside WhatsApp-style coordination before asking for a new habit.",
                "negative_trigger": "Assumes every household wants another shared place to check.",
                "trust_requirement": "Respect for privacy and light sharing defaults.",
                "likely_objection": "If this becomes my job to maintain for everyone else, I will stop.",
                "persona_specific_example": "I would only try this with a narrow family use case, not a full family system from day one.",
            },
            "health_or_wellbeing_product": {
                "reaction_basis": "He does not want support products to make him feel judged for inconsistent routines.",
                "first_question": "Does this help on a tired week, or only on an ideal week?",
                "positive_trigger": "Gentle, private support with low setup burden.",
                "negative_trigger": "Moralizing copy or streak pressure.",
                "trust_requirement": "Neutral language and clear privacy handling.",
                "likely_objection": "If this turns ordinary inconsistency into a failure signal, I will pull away.",
                "persona_specific_example": "I would trust a low-pressure check-in more than a big optimization plan.",
            },
            "financial_product": {
                "reaction_basis": "Local affordability and defensibility matter more than fintech excitement.",
                "first_question": "Is this priced for local reality or copied from a US SaaS expectation?",
                "positive_trigger": "Simple, locally legible value.",
                "negative_trigger": "USD-normalized pricing logic or hidden fees.",
                "trust_requirement": "Clear MYR-relevant value story and plain trade-off explanation.",
                "likely_objection": "If I need too much translation just to see the value, I already distrust it.",
                "persona_specific_example": "I want to know whether this helps with real recurring money behavior, not just dashboards.",
            },
            "education_or_child_product": {
                "reaction_basis": "He is wary of products that convert care into another system someone has to maintain.",
                "first_question": "Does this reduce stress, or does it just create a better-looking record?",
                "positive_trigger": "One small improvement that fits existing household behavior.",
                "negative_trigger": "Anxiety marketing aimed at responsible adults.",
                "trust_requirement": "Respectful language and practical family fit.",
                "likely_objection": "If the value depends on perfect consistency, I will not believe it.",
                "persona_specific_example": "I would trust a product that handles one recurring coordination issue better than one that promises to fix parenting or learning broadly.",
            },
            "workflow_or_productivity_product": {
                "reaction_basis": "He is willing to try productivity tools if the first experiment is small and socially low-risk.",
                "first_question": "Can I pilot this with one recurring task before I move the whole workflow?",
                "positive_trigger": "A clear first-step pilot that removes one repeat follow-up problem.",
                "negative_trigger": "Another system that needs constant manual upkeep to look useful.",
                "trust_requirement": "Practical demo plus evidence that interruption does not break the setup.",
                "likely_objection": "I do not need a cleaner pitch. I need a smaller first step.",
                "persona_specific_example": "If I can use it for one vendor follow-up loop first, that is credible to me.",
            },
            "identity_sensitive_product": {
                "reaction_basis": "He wants control over when personal context becomes part of the product.",
                "first_question": "Can I keep this private until I know why the product needs that information?",
                "positive_trigger": "Optional disclosure with clear purpose.",
                "negative_trigger": "Mandatory identity or household labeling early in onboarding.",
                "trust_requirement": "Respectful defaults and disclosure control.",
                "likely_objection": "If you ask me for personal context before you earn trust, I slow down.",
                "persona_specific_example": "I will stay engaged longer if the product lets me defer personal fields until the use case is clear.",
            },
            "high_friction_onboarding": {
                "reaction_basis": "His willingness to try is real, but fragile when setup becomes a full project.",
                "first_question": "How much of this can I skip until I know it is actually helping?",
                "positive_trigger": "Progressive onboarding that proves value before asking for full setup.",
                "negative_trigger": "Front-loaded configuration and too many choices early.",
                "trust_requirement": "Visible first win inside a short session.",
                "likely_objection": "The more this feels like homework, the less likely I am to keep going.",
                "persona_specific_example": "I need the first useful moment to arrive before the product asks for discipline.",
            },
        }

    if archetype == "mature_operator_retention_skeptic":
        return {
            "generic_new_product": {
                "reaction_basis": "Jordan has seen well-pitched tools fail once the maintenance pattern appears.",
                "first_question": "What burden moves to the user after the demo stops carrying the story?",
                "positive_trigger": "A clear explanation of what routine burden disappears for good.",
                "negative_trigger": "Efficiency claims with no retention logic.",
                "trust_requirement": "Month-two realism and visible failure handling.",
                "likely_objection": "I have heard the value case. I still need the maintenance case.",
                "persona_specific_example": "A product that earns trust tells me what still works after the launch energy is gone.",
            },
            "ai_product": {
                "reaction_basis": "Low AI familiarity plus operational experience make Jordan focus on supervision and failure cost.",
                "first_question": "Who checks the AI when it gets a detail wrong after week three?",
                "positive_trigger": "AI framed as bounded assistance with clear human control.",
                "negative_trigger": "AI language that assumes trust before accountability is shown.",
                "trust_requirement": "Explicit review boundaries, retention policy, and a practical escalation path.",
                "likely_objection": "If the AI gets the glory while the user keeps the cleanup, I am not interested.",
                "persona_specific_example": "I am more open to AI drafting a follow-up than to AI owning the whole operational memory.",
            },
            "subscription_product": {
                "reaction_basis": "Recurring spend is judged against local monthly reality and long-run usefulness.",
                "first_question": "What happens after the initial interest fades and this still wants a monthly line item?",
                "positive_trigger": "A clean monthly plan with no optimism tax.",
                "negative_trigger": "Annual lock-in or imported pricing logic.",
                "trust_requirement": "A credible month-two story and respectful exit path.",
                "likely_objection": "You are pricing the promise, not the upkeep.",
                "persona_specific_example": "If I still need to defend this line item after month one, the product should have a better answer than enthusiasm.",
            },
            "family_or_household_product": {
                "reaction_basis": "Shared households need explanation and privacy control, not just shared visibility.",
                "first_question": "Who in the house needs to agree before this stops becoming my problem alone?",
                "positive_trigger": "Optional sharing and non-binary household assumptions.",
                "negative_trigger": "Default partner labels or always-on shared visibility.",
                "trust_requirement": "Household control settings that do not assume one domestic template.",
                "likely_objection": "If the product creates family admin in the name of family help, I will step back.",
                "persona_specific_example": "A household tool earns more trust when it lets me control what becomes visible and to whom.",
            },
            "health_or_wellbeing_product": {
                "reaction_basis": "Jordan treats wellbeing tools as dignity-sensitive and suspicious when they sound moralizing.",
                "first_question": "Does this support a real person, or does it just produce a record of noncompliance?",
                "positive_trigger": "Neutral language and private, optional use.",
                "negative_trigger": "Guilt cues, streak culture, or public wellbeing performance.",
                "trust_requirement": "Low-pressure private control and plain limits on what the tool infers.",
                "likely_objection": "I do not want a wellbeing tool that quietly turns support into surveillance.",
                "persona_specific_example": "A wellbeing product should feel calmer after week four, not more performative.",
            },
            "financial_product": {
                "reaction_basis": "Cash-flow volatility and local pricing realism shape trust more than product sophistication.",
                "first_question": "Why is this priced and explained as if everyone budgets in US SaaS logic?",
                "positive_trigger": "Local reality, plain trade-offs, and no shame around caution.",
                "negative_trigger": "Imported affordability assumptions or upsell pressure dressed as urgency.",
                "trust_requirement": "Clear value in MYR reality and honest downside explanation.",
                "likely_objection": "If the product cannot explain itself in local financial terms, I do not trust its risk logic either.",
                "persona_specific_example": "I am more open to a smaller, legible value case than a big imported fintech story.",
            },
            "education_or_child_product": {
                "reaction_basis": "Jordan distrusts products that weaponize responsibility or guilt.",
                "first_question": "Is this built for real families and real inconsistency, or for ideal users who perform care perfectly?",
                "positive_trigger": "Grounded support with low disclosure pressure.",
                "negative_trigger": "Respectability signaling with no practical household fit.",
                "trust_requirement": "Dignified defaults, optionality, and a believable habit model.",
                "likely_objection": "I will not pay for a cleaner record of expectations that ordinary life will not meet.",
                "persona_specific_example": "A child or education product should help under ordinary fatigue, not only under ideal attention.",
            },
            "workflow_or_productivity_product": {
                "reaction_basis": "Years of ops work make Jordan ask where maintenance, proof, and retention really land.",
                "first_question": "Which existing step disappears, not which new record gets created?",
                "positive_trigger": "A workflow demo that shows what stops happening after adoption.",
                "negative_trigger": "Another visibility layer that relies on manual upkeep.",
                "trust_requirement": "Demonstrated removal of duplicate effort and a credible retention story.",
                "likely_objection": "I do not need a better dashboard. I need less hidden cleanup.",
                "persona_specific_example": "If the system still needs a shadow spreadsheet by month two, it has failed.",
            },
            "identity_sensitive_product": {
                "reaction_basis": "Jordan notices whether inclusion changes control or just language.",
                "first_question": "Can I use this without publicly labeling myself before I know why it matters?",
                "positive_trigger": "Optional disclosure, profile visibility control, and purpose-specific identity fields.",
                "negative_trigger": "Mandatory titles, binary defaults, and performative inclusion copy.",
                "trust_requirement": "Control over disclosure, visibility, and household-role language.",
                "likely_objection": "Respect without control does not count as safety to me.",
                "persona_specific_example": "I trust an optional field with a clear reason more than a loud promise of inclusivity with no settings.",
            },
            "high_friction_onboarding": {
                "reaction_basis": "Jordan treats long onboarding as an early signal of long-term maintenance transfer.",
                "first_question": "If setup already needs project discipline, why would retention be any better?",
                "positive_trigger": "A staged setup that proves value before asking for operational commitment.",
                "negative_trigger": "Front-loaded configuration and unclear ownership of upkeep.",
                "trust_requirement": "Visible first value plus explicit explanation of what remains to maintain later.",
                "likely_objection": "The onboarding is already telling me where the future burden will land.",
                "persona_specific_example": "If the first useful moment comes only after a long setup session, I treat that as a retention warning.",
            },
        }

    return copy.deepcopy(persona.profile.cross_domain_product_reaction_model)


def _objection_language_v3(persona: PersonaSkill) -> dict[str, Any]:
    voiceprint = persona.profile.persona_voiceprint
    archetype = _archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "direct_objection_examples": [
                "I get the problem. I just need to see the smallest version that works without me rebuilding my routine.",
                "This may be useful, but the setup already sounds heavier than the first test should be.",
                "If the value only appears after a big commitment, I would probably hesitate.",
            ],
            "polite_objection_examples": [
                "I can see why someone would want this. I am just not ready to commit without a lighter first step.",
                "It makes sense in theory. I am less sure it fits how my actual week behaves.",
            ],
            "hidden_objection_patterns": [
                "sounds positive but keeps asking for a smaller first step",
                "stays interested at the concept level without offering real commitment",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "This is interesting.",
                "I can see the use case.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                voiceprint["example_near_purchase_question"],
                "Could I try this on one recurring task first?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What can I skip until I know the first small version works?",
                "How fast would I know whether this actually fits my week?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If it works, what current workaround would I actually stop using?",
                "How easy is it to pull back if the routine does not stick?",
            ],
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "direct_objection_examples": [
                "I have seen this pattern before. The pitch is about efficiency, but the maintenance usually moves to the user.",
                "You are showing me the benefit. I still need the upkeep story.",
                "If the product only looks good while users are disciplined, I treat that as a retention problem.",
            ],
            "polite_objection_examples": [
                "I follow the idea. I just do not yet see evidence that the routine burden stays low.",
                "The concept is clear. The long-run fit is not.",
            ],
            "hidden_objection_patterns": [
                "continues the discussion but stops offering goodwill",
                "moves quickly to burden transfer, retention, or disclosure control",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "There may be a use case for this.",
                "I understand what you are trying to do.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                voiceprint["example_near_purchase_question"],
                "What still works after month one without extra user cleanup?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "Where can I test the value without handing over too much control too early?",
                "If I stop after two weeks, what have I actually set in motion?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "Which existing check, message, or spreadsheet line disappears for good?",
                "How does the product behave once the user stops giving it ideal attention?",
            ],
        }
    return copy.deepcopy(persona.profile.objection_language_style)


def _domain_fit_v3(persona: PersonaSkill) -> dict[str, Any]:
    domain_fit = copy.deepcopy(persona.profile.domain_fit)
    profile = persona.profile.panel_role_profile
    domain_fit["panel_roles"] = _dedupe(domain_fit.get("panel_roles", []) + [profile.get("panel_role", ""), profile.get("behavioural_archetype", "")])
    return domain_fit


def _persona_diff_notes(v2_persona: PersonaSkill, v3_persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any]) -> str:
    chapters = v3_persona.profile.canonical_biography.get("decade_timeline", [])
    lived_scene_count = sum(1 for chapter in chapters if chapter.get("specific_scene"))
    return "\n".join(
        [
            f"# {v3_persona.profile.synthetic_user_id} V2 To V3 Diff",
            "",
            "## Added Lived Scenes",
            f"- Added {lived_scene_count} decade-linked specific scenes with product memories and current reaction links.",
            "",
            "## Diversified Voice",
            f"- New behavioural archetype: {v3_persona.profile.panel_role_profile.get('behavioural_archetype', '')}",
            f"- New voiceprint anchor: {v3_persona.profile.persona_voiceprint.get('what_they_repeat_when_skeptical', '')}",
            "",
            "## Improved Local Grounding",
            f"- Added local grounding cues for {v3_persona.profile.basic_identity.get('location', '')}.",
            f"- Local pricing reaction: {v3_persona.profile.local_grounding_layer.get('pricing_localization_reaction', '')}",
            "",
            "## Improved Sensitive Scenarios",
            f"- Added scenario reactions for {', '.join(v3_persona.profile.sensitive_scenario_reactions.keys())}.",
            "",
            "## Reduced Shared Template Language",
            f"- Diversity high-similarity dimensions: {', '.join(diversity_report.get('high_similarity_dimensions', [])) or 'none after final pass'}",
            "",
            "## Audit Warnings",
            *[f"- {warning}" for warning in quality_audit.get("warnings", [])],
            "",
            "## Remaining Gaps",
            *[f"- {item}" for item in quality_audit.get("required_improvements", [])],
            "",
            "## V2 Baseline Note",
            f"- V2 source skill version: {v2_persona.skill_version}",
            f"- V3 generator version: persona-generator/v3",
        ]
    ).strip() + "\n"


def _compat_persona_md_v3(persona: PersonaSkill) -> str:
    return "\n".join(
        [
            f"# {persona.profile.basic_identity['name']}",
            "",
            "## Snapshot",
            f"- ID: {persona.profile.synthetic_user_id}",
            f"- Archetype: {persona.profile.panel_role_profile.get('behavioural_archetype', '')}",
            f"- Location: {persona.profile.basic_identity.get('location', '')}",
            "",
            "## Core Read",
            persona.profile.canonical_biography.get("life_arc_summary", ""),
            "",
            "## Voice",
            persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
        ]
    ).strip() + "\n"


def upgrade_persona_to_v3(source_persona: PersonaSkill, *, random_seed: int | None = None, contrast_mode: bool = False) -> PersonaSkill:
    persona = copy.deepcopy(source_persona)
    if persona.skill_version != "v2" or not persona.profile.canonical_biography:
        persona = upgrade_persona_to_v2(persona, random_seed=random_seed)

    persona.skill_version = "v3"
    persona.profile.panel_role_profile = _panel_role_profile(persona)
    persona.profile.local_grounding_layer = _local_grounding_layer(persona)
    persona.profile.sensitive_scenario_reactions = _sensitive_scenario_reactions(persona)
    persona.profile.persona_voiceprint = _voiceprint(persona, contrast_mode=contrast_mode)
    persona.profile.daily_micro_behaviours = _daily_micro_behaviours_v3(persona)
    persona.profile.interests_and_hobbies = _interests_and_hobbies_v3(persona)
    persona.profile.pricing_logic = _pricing_logic_v3(persona)
    persona.profile.product_reaction_rules = _product_reaction_rules_v3(persona)
    persona.profile.cross_domain_product_reaction_model = _cross_domain_model_v3(persona, contrast_mode=contrast_mode)
    persona.profile.objection_language_style = _objection_language_v3(persona)
    persona.profile.domain_fit = _domain_fit_v3(persona)
    persona.profile.canonical_biography = _canonical_biography_v3(persona)

    if _archetype_key(persona) == "early_career_practical_trial_user":
        trust_requirements = [
            "a practical demo from a similar role",
            "a bounded first step",
            "an easy monthly exit",
        ]
        rejection_triggers = [
            "full routine rebuild before proof",
            "setup that makes failure socially visible too early",
            "USD-style pricing without local reality",
        ]
    elif _archetype_key(persona) == "mature_operator_retention_skeptic":
        trust_requirements = [
            "proof that maintenance actually leaves the user",
            "month-two retention logic",
            "clear disclosure and visibility controls",
        ]
        rejection_triggers = [
            "performative inclusivity without settings",
            "manual upkeep hidden behind a polished dashboard",
            "pricing the promise before proving the routine fit",
        ]
    else:
        trust_requirements = persona.decision_policy.get("trust_requirements", [])
        rejection_triggers = persona.decision_policy.get("rejection_triggers", [])

    persona.decision_policy = {
        **persona.decision_policy,
        "trust_requirements": trust_requirements,
        "rejection_triggers": rejection_triggers,
        "founder_challenge_style": (
            "Start respectful but concrete." if _archetype_key(persona) == "early_career_practical_trial_user"
            else "Move quickly from concept to burden transfer, retention logic, and disclosure control."
        ),
        "trial_threshold": persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
    }
    persona.response_style = {
        **persona.response_style,
        "preferred_response_shape": "context -> objection or caution -> what would change confidence",
        "persona_voice_anchor": persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
    }
    persona.profile.audit_evidence_layer.update(
        {
            "persona_generation_method": "deterministic_seed_plus_template_enhancement_v3",
            "persona_version": "v3",
            "generator_version": "persona-generator/v3",
            "last_audited_at": datetime.now(UTC).date().isoformat(),
        }
    )
    persona.audit = {
        **persona.audit,
        **persona.profile.audit_evidence_layer,
    }
    persona.narrative = _compat_persona_md_v3(persona)
    return persona


def _dimension_text(persona: PersonaSkill, dimension: str) -> str:
    if dimension == "core_motivation_similarity":
        return " ".join(
            persona.profile.values.get("life_goals", [])
            + persona.profile.values.get("aspirations", [])
            + persona.profile.values.get("fears", [])
        )
    if dimension == "life_arc_similarity":
        return _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", ""))
    if dimension == "formative_event_similarity":
        return " ".join(
            chapter.get("specific_scene", "")
            for chapter in persona.profile.canonical_biography.get("decade_timeline", [])
        )
    if dimension == "product_objection_similarity":
        return " ".join(
            persona.profile.product_reaction_rules.get("questions_they_would_ask", [])
            + persona.profile.product_reaction_rules.get("negative_signals", [])
            + persona.profile.objection_language_style.get("direct_objection_examples", [])
        )
    if dimension == "pricing_logic_similarity":
        return json.dumps(persona.profile.pricing_logic, ensure_ascii=False, sort_keys=True)
    if dimension == "trust_model_similarity":
        return (
            " ".join(persona.decision_policy.get("trust_requirements", []))
            + " "
            + " ".join(persona.profile.product_reaction_rules.get("evidence_that_changes_their_mind", []))
            + " "
            + json.dumps(persona.profile.sensitive_scenario_reactions.get("privacy_and_data", {}), ensure_ascii=False, sort_keys=True)
        )
    if dimension == "technology_attitude_similarity":
        return (
            json.dumps(persona.profile.technology_profile, ensure_ascii=False, sort_keys=True)
            + " "
            + json.dumps(persona.profile.cross_domain_product_reaction_model.get("ai_product", {}), ensure_ascii=False, sort_keys=True)
        )
    if dimension == "lifestyle_similarity":
        lifestyle_parts = (
            _list_of_strings(persona.profile.interests_and_hobbies)
            + _list_of_strings(persona.profile.daily_micro_behaviours)
            + _list_of_strings(persona.profile.personal_environment)
        )
        return " ".join(lifestyle_parts)
    if dimension == "objection_language_similarity":
        return json.dumps(persona.profile.objection_language_style, ensure_ascii=False, sort_keys=True) + " " + json.dumps(persona.profile.persona_voiceprint, ensure_ascii=False, sort_keys=True)
    if dimension == "cross_domain_reaction_similarity":
        return json.dumps(persona.profile.cross_domain_product_reaction_model, ensure_ascii=False, sort_keys=True)
    if dimension == "sensitive_topic_reaction_similarity":
        return json.dumps(persona.profile.sensitive_scenario_reactions, ensure_ascii=False, sort_keys=True)
    if dimension == "phrase_similarity":
        return (
            _stringify_text_field(persona.profile.canonical_biography.get("life_arc_summary", ""))
            + " "
            + persona.profile.persona_voiceprint.get("example_hard_rejection", "")
            + " "
            + persona.profile.persona_voiceprint.get("example_near_purchase_question", "")
            + " "
            + _stringify_text_field(persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""))
        )
    raise KeyError(dimension)


def _domain_fit_overlap(left: PersonaSkill, right: PersonaSkill) -> float:
    left_values = set(left.profile.domain_fit.get("best_fit_domains", [])) | set(left.profile.domain_fit.get("panel_roles", []))
    right_values = set(right.profile.domain_fit.get("best_fit_domains", [])) | set(right.profile.domain_fit.get("panel_roles", []))
    if not left_values and not right_values:
        return 0.0
    return round(len(left_values & right_values) / max(1, len(left_values | right_values)), 4)


def _panel_role_redundancy(left: PersonaSkill, right: PersonaSkill) -> float:
    left_profile = left.profile.panel_role_profile
    right_profile = right.profile.panel_role_profile
    if left_profile.get("behavioural_archetype") == right_profile.get("behavioural_archetype"):
        return 1.0
    if left_profile.get("panel_role") == right_profile.get("panel_role"):
        return 0.45
    return 0.2


def similarity_dimensions(candidate: PersonaSkill, comparison: PersonaSkill) -> dict[str, float]:
    dimensions = {}
    for key in (
        "core_motivation_similarity",
        "life_arc_similarity",
        "formative_event_similarity",
        "product_objection_similarity",
        "pricing_logic_similarity",
        "trust_model_similarity",
        "technology_attitude_similarity",
        "lifestyle_similarity",
        "objection_language_similarity",
        "cross_domain_reaction_similarity",
        "sensitive_topic_reaction_similarity",
        "phrase_similarity",
    ):
        dimensions[key] = _text_similarity(_dimension_text(candidate, key), _dimension_text(comparison, key))
    dimensions["domain_fit_overlap"] = _domain_fit_overlap(candidate, comparison)
    dimensions["panel_role_redundancy"] = _panel_role_redundancy(candidate, comparison)
    return dimensions


def _overall_similarity(dimensions: dict[str, float]) -> float:
    weights = {
        "core_motivation_similarity": 0.08,
        "life_arc_similarity": 0.1,
        "formative_event_similarity": 0.1,
        "product_objection_similarity": 0.14,
        "pricing_logic_similarity": 0.08,
        "trust_model_similarity": 0.1,
        "technology_attitude_similarity": 0.06,
        "lifestyle_similarity": 0.08,
        "objection_language_similarity": 0.1,
        "cross_domain_reaction_similarity": 0.14,
        "sensitive_topic_reaction_similarity": 0.06,
        "domain_fit_overlap": 0.03,
        "phrase_similarity": 0.09,
        "panel_role_redundancy": 0.04,
    }
    total = sum(dimensions[key] * weight for key, weight in weights.items())
    return round(total, 4)


def build_diversity_report(candidate: PersonaSkill, comparison_personas: list[PersonaSkill]) -> dict[str, Any]:
    pair_reports: list[dict[str, Any]] = []
    for comparison in comparison_personas:
        if comparison.profile.synthetic_user_id == candidate.profile.synthetic_user_id:
            continue
        dimensions = similarity_dimensions(candidate, comparison)
        pair_reports.append(
            {
                "persona_id": comparison.profile.synthetic_user_id,
                "overall_similarity_score": _overall_similarity(dimensions),
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
        }

    pair_reports.sort(key=lambda item: item["overall_similarity_score"], reverse=True)
    top_pair = pair_reports[0]
    high_dimensions = [
        dimension
        for dimension, score in top_pair["dimensions"].items()
        if (
            (dimension == "product_objection_similarity" and score > 0.75)
            or (dimension == "cross_domain_reaction_similarity" and score > 0.70)
            or (dimension == "phrase_similarity" and score > 0.60)
            or (dimension not in {"product_objection_similarity", "cross_domain_reaction_similarity", "phrase_similarity"} and score > 0.70)
        )
    ]

    warnings: list[str] = []
    actions: list[str] = []
    other_id = top_pair["persona_id"]
    for dimension in high_dimensions:
        pretty_name = dimension.replace("_", " ")
        warnings.append(f"Similarity remains elevated in {pretty_name} against {other_id}.")
    if top_pair["overall_similarity_score"] > 0.70:
        actions.append("Increase behavioural differentiation and archetype-specific phrasing.")
    if top_pair["dimensions"]["product_objection_similarity"] > 0.75:
        actions.append("Rewrite objection language and practical pushback in a more persona-specific way.")
    if top_pair["dimensions"]["cross_domain_reaction_similarity"] > 0.70:
        actions.append("Diversify cross-domain first questions, trust requirements, and likely objections.")
    if top_pair["dimensions"]["phrase_similarity"] > 0.60:
        actions.append("Rewrite repeated phrasing and reduce template-like lines.")
    if top_pair["dimensions"]["panel_role_redundancy"] > 0.70:
        actions.append("Sharpen the behavioural archetype and what this persona overweights.")

    return {
        "synthetic_user_id": candidate.profile.synthetic_user_id,
        "compared_against": [item["persona_id"] for item in pair_reports],
        "overall_similarity_score": top_pair["overall_similarity_score"],
        "high_similarity_dimensions": high_dimensions,
        "distinctiveness_score": round(1.0 - top_pair["overall_similarity_score"], 4),
        "warnings": warnings,
        "required_diversification_actions": actions,
        "pair_reports": pair_reports,
    }


def _requires_distinctiveness_revision(diversity_report: dict[str, Any]) -> bool:
    return (
        diversity_report["overall_similarity_score"] > 0.70
        or any(dimension in diversity_report["high_similarity_dimensions"] for dimension in ("product_objection_similarity", "cross_domain_reaction_similarity", "phrase_similarity"))
    )


def apply_distinctiveness_revision(candidate: PersonaSkill, comparison_personas: list[PersonaSkill]) -> PersonaSkill:
    revised = upgrade_persona_to_v3(candidate, contrast_mode=True)
    if _archetype_key(revised) == "early_career_practical_trial_user":
        revised.profile.local_grounding_layer["trust_cues_in_this_market"] = _dedupe(
            revised.profile.local_grounding_layer.get("trust_cues_in_this_market", [])
            + ["peer demo that looks small enough to try without team-wide commitment"]
        )
    if _archetype_key(revised) == "mature_operator_retention_skeptic":
        revised.profile.local_grounding_layer["trust_cues_in_this_market"] = _dedupe(
            revised.profile.local_grounding_layer.get("trust_cues_in_this_market", [])
            + ["control over profile fields and visibility before any public-facing identity step"]
        )
    return revised


def render_biography_md(persona: PersonaSkill) -> str:
    biography = persona.profile.canonical_biography
    sections = [
        f"# {persona.profile.basic_identity['name']} - Level 3 Synthetic User Biography",
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
                f"Specific scene: {chapter['specific_scene']}",
                f"Product-relevant memory: {chapter['product_relevant_memory']}",
                f"Social or relationship context: {chapter['social_or_relationship_context']}",
                f"Money or effort trade-off: {chapter['money_or_effort_tradeoff']}",
                f"Beliefs formed: {', '.join(chapter['beliefs_formed'])}",
                f"Current reaction link: {chapter['current_reaction_link']}",
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
                f"- {item['age_range']}: {item['event_summary']}"
                for item in biography.get("formative_events", [])
            ],
            "",
            "## Current Identity",
            biography.get("current_identity", ""),
            "",
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
            f"Workday: {persona.profile.daily_micro_behaviours.get('morning_routine', '')} {persona.profile.daily_micro_behaviours.get('work_start_pattern', '')} {persona.profile.daily_micro_behaviours.get('evening_routine', '')}",
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
            f"Hidden habits: {', '.join(persona.profile.hidden_habits.get('workarounds_they_keep_using', []))}",
            *[
                f"- {item['contradiction']} {item['product_validation_effect']}"
                for item in persona.profile.contradiction_map
            ],
            "",
            "## Taste, Brand & Communication Preferences",
            f"Visual preference: {persona.profile.taste_and_aesthetic_preferences.get('visual_style_preference', '')}",
            f"Trustworthy design signals: {', '.join(persona.profile.taste_and_aesthetic_preferences.get('trustworthy_design_signals', []))}",
            f"Copy turnoffs: {', '.join(persona.profile.taste_and_aesthetic_preferences.get('copywriting_turnoffs', []))}",
            "",
            "## Product Research Implications",
            f"- Concept validation: {persona.profile.panel_role_profile.get('research_function', '')}",
            f"- Landing page test: this persona overweights {', '.join(persona.profile.panel_role_profile.get('what_this_person_will_overweight', [])[:2])}.",
            "- Pricing test: should probe both affordability logic and the effort burden that would remain after payment.",
            "- Onboarding test: should show whether the first value moment arrives before discipline is required.",
            "- Retention risk: should examine what happens once novelty, social goodwill, or founder attention fade.",
            "- Referral likelihood: rises only after the product survives ordinary use and feels explainable to local peers.",
            "",
            "## Sensitive Reality Notes",
            persona.profile.sensitive_reality_layer.get("fairness_and_inclusion_profile", ""),
            "",
            "## What This Persona Is Good For",
            *[f"- {item}" for item in persona.profile.panel_role_profile.get("what_this_person_is_good_at_detecting", [])],
            "",
            "## What This Persona Should Not Be Used For",
            *[f"- {item}" for item in persona.profile.audit_evidence_layer.get("do_not_use_for", [])],
        ]
    )
    return "\n".join(sections).strip() + "\n"


def render_research_kernel_md(persona: PersonaSkill) -> str:
    voiceprint = persona.profile.persona_voiceprint
    profile = persona.profile.panel_role_profile
    return "\n".join(
        [
            f"# Research Kernel: {persona.profile.basic_identity['name']}",
            "",
            "## Identity",
            f"{persona.profile.basic_identity['name']} is a synthetic user for AI pre-validation only. They are a {persona.profile.basic_identity['age']}-year-old {persona.profile.basic_identity['occupation']} in {persona.profile.basic_identity['location']}.",
            "",
            "## Life Arc Summary",
            persona.profile.canonical_biography.get("life_arc_summary", ""),
            "",
            "## Top Formative Patterns",
            *[
                f"- {chapter['current_reaction_link']}"
                for chapter in persona.profile.canonical_biography.get("decade_timeline", [])[:4]
            ],
            "",
            "## Current Life Situation",
            persona.profile.canonical_biography.get("current_daily_life", ""),
            "",
            "## Core Values",
            ", ".join(persona.profile.values.get("core_values", [])),
            "",
            "## Trust Model",
            f"Trust grows through {', '.join(persona.decision_policy.get('trust_requirements', []))}. This persona also needs {persona.profile.sensitive_scenario_reactions.get('privacy_and_data', {}).get('what_builds_trust', '').lower()}",
            "",
            "## Buying Logic",
            persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
            "",
            "## Pricing Logic",
            persona.profile.pricing_logic.get("pricing_objection", ""),
            persona.profile.pricing_logic.get("what_makes_price_feel_fair", ""),
            "",
            "## Technology Attitude",
            f"AI familiarity: {persona.profile.technology_profile.get('ai_familiarity', '')}. Privacy concern: {persona.profile.technology_profile.get('privacy_concern', '')}.",
            "",
            "## Interests That Affect Buying Behaviour",
            f"Primary interests: {', '.join(persona.profile.interests_and_hobbies.get('primary_interests', []))}",
            "",
            "## Media Diet And Discovery Path",
            persona.profile.media_and_content_diet.get("how_they_discover_new_products", ""),
            f"Local discovery channels: {', '.join(persona.profile.local_grounding_layer.get('local_discovery_channels', []))}",
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
            "## Objection Language",
            *[f"- {item}" for item in persona.profile.objection_language_style.get("direct_objection_examples", [])],
            "",
            "## Sensitive Topic Reaction",
            persona.profile.sensitive_scenario_reactions.get("identity_disclosure", {}).get("reaction", ""),
            "",
            "## Cross-Domain Product Reaction Summary",
            f"This persona is best at detecting {', '.join(profile.get('what_this_person_is_good_at_detecting', [])[:3])}.",
            "",
            "## Founder Misread Risk",
            *[f"- {item}" for item in persona.profile.deep_research_notes.get("what_a_founder_might_misread_about_them", [])],
            "",
            "## Response Style",
            voiceprint.get("speaking_style", ""),
            "",
            "## Do Not Flatter Founder Rule",
            "Do not flatter the founder. If the product is vague, imported, high-maintenance, poorly localized, or weak on disclosure control, say so plainly.",
        ]
    ).strip() + "\n"


def _example_response(persona: PersonaSkill, category: str) -> str:
    reaction = persona.profile.cross_domain_product_reaction_model.get(category, {})
    voiceprint = persona.profile.persona_voiceprint
    if category == "ai_product":
        response_line = voiceprint.get("example_positive_reaction", "")
    elif category == "subscription_product":
        response_line = voiceprint.get("example_polite_rejection", "")
    elif category == "identity_sensitive_product":
        response_line = voiceprint.get("example_hard_rejection", "")
    elif category == "high_friction_onboarding":
        response_line = voiceprint.get("example_hard_rejection", "")
    else:
        response_line = voiceprint.get("example_near_purchase_question", "")
    return "\n".join(
        [
            f"### {category.replace('_', ' ').title()}",
            f"> Reaction basis: {reaction.get('reaction_basis', '')}",
            f"> First question: {reaction.get('first_question', '')}",
            f"> Positive trigger: {reaction.get('positive_trigger', '')}",
            f"> Likely objection: {reaction.get('likely_objection', '')}",
            f"> Persona-specific example: {reaction.get('persona_specific_example', '')}",
            f"> Voice sample: {response_line}",
        ]
    )


def render_persona_skill_md(persona: PersonaSkill) -> str:
    voiceprint = persona.profile.persona_voiceprint
    return "\n".join(
        [
            f"# Synthetic User Skill: {persona.profile.basic_identity['name']}",
            "",
            "## Role",
            "This is a synthetic user skill for AI pre-validation only. It can challenge product assumptions, but it is not a substitute for real human market research.",
            "",
            "## Identity",
            f"{persona.profile.basic_identity['name']} is a {persona.profile.basic_identity['age']}-year-old {persona.profile.basic_identity['occupation']} in {persona.profile.basic_identity['location']}, { _household_context_phrase(persona.profile.basic_identity) }.",
            "",
            "## Canonical Life Arc",
            persona.profile.canonical_biography.get("life_arc_summary", ""),
            "",
            "## Decade Memory",
            *[
                f"- {chapter['age_range']}: {chapter['specific_scene']}"
                for chapter in persona.profile.canonical_biography.get("decade_timeline", [])
            ],
            "",
            "## Current Life",
            persona.profile.canonical_biography.get("current_daily_life", ""),
            "",
            "## Formative Patterns",
            *[
                f"- {chapter['current_reaction_link']}"
                for chapter in persona.profile.canonical_biography.get("decade_timeline", [])[:6]
            ],
            "",
            "## Lifestyle & Interests",
            f"Primary interests that affect product reaction: {', '.join(persona.profile.interests_and_hobbies.get('primary_interests', []))}",
            f"Low-energy patterns that affect trial behavior: {', '.join(persona.profile.interests_and_hobbies.get('low_energy_hobbies', []))}",
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
            f"AI familiarity: {persona.profile.technology_profile.get('ai_familiarity', '')}. Privacy concern: {persona.profile.technology_profile.get('privacy_concern', '')}.",
            "",
            "## Discovery & Trust Path",
            persona.profile.media_and_content_diet.get("how_they_discover_new_products", ""),
            f"Local discovery channels: {', '.join(persona.profile.local_grounding_layer.get('local_discovery_channels', []))}",
            "",
            "## Cross-Domain Product Reaction Model",
            *[
                f"- {key}: {value.get('first_question', '')} | trust requirement = {value.get('trust_requirement', '')}"
                for key, value in persona.profile.cross_domain_product_reaction_model.items()
            ],
            "",
            "## Sensitive Topic Handling",
            persona.profile.sensitive_scenario_reactions.get("identity_disclosure", {}).get("reaction", ""),
            persona.profile.sensitive_scenario_reactions.get("fairness_and_inclusion", {}).get("what_builds_trust", ""),
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
            "- Do not flatter the founder.",
            "- Do not pretend to be a real human.",
            "- Respond as this persona.",
            "- Separate curiosity from willingness to pay.",
            "- Challenge vague claims.",
            "- Point out friction, privacy, trust, pricing, sensitive topic risks, and local-market mismatch where relevant.",
            "- If the product is unclear, say it is unclear.",
            "- If the persona would not buy, say so.",
            "",
            "## Example Responses",
            _example_response(persona, "ai_product"),
            "",
            _example_response(persona, "subscription_product"),
            "",
            _example_response(persona, "identity_sensitive_product"),
            "",
            _example_response(persona, "high_friction_onboarding"),
            "",
            _example_response(persona, "generic_new_product"),
            "",
            "## Persona Voiceprint",
            f"Speaking style: {voiceprint.get('speaking_style', '')}",
            f"Soft disagreement: {voiceprint.get('how_they_soften_disagreement', '')}",
            f"Direct disagreement: {voiceprint.get('how_they_get_more_direct', '')}",
            f"Repeated skeptical phrase: {voiceprint.get('what_they_repeat_when_skeptical', '')}",
        ]
    ).strip() + "\n"


def render_local_grounding_md(persona: PersonaSkill) -> str:
    layer = persona.profile.local_grounding_layer
    return "\n".join(
        [
            f"# Local Grounding: {persona.profile.basic_identity['name']}",
            "",
            "## City Or Region Specific Context",
            *[f"- {item}" for item in layer.get("city_or_region_specific_context", [])],
            "",
            "## Common Apps Or Services",
            *[f"- {item}" for item in layer.get("common_apps_or_services", [])],
            "",
            "## Payment And Commerce Context",
            *[f"- {item}" for item in layer.get("payment_and_commerce_context", [])],
            "",
            "## Mobility Or Commute Context",
            *[f"- {item}" for item in layer.get("mobility_or_commute_context", [])],
            "",
            "## Language Switching Scenes",
            *[f"- {item}" for item in layer.get("language_switching_scenes", [])],
            "",
            "## Household And Workplace Norms",
            *[f"- {item}" for item in layer.get("family_or_household_norms", [])],
            *[f"- {item}" for item in layer.get("workplace_norms", [])],
            "",
            "## Trust Cues In This Market",
            *[f"- {item}" for item in layer.get("trust_cues_in_this_market", [])],
            "",
            "## Pricing Localization Reaction",
            layer.get("pricing_localization_reaction", ""),
            "",
            "## What Feels Imported Or Not Local",
            layer.get("what_feels_imported_or_not_local", ""),
            "",
            "## Local Sensitivity Notes",
            *[f"- {item}" for item in layer.get("local_sensitivity_notes", [])],
        ]
    ).strip() + "\n"


def render_sensitive_scenarios_md(persona: PersonaSkill) -> str:
    layer = persona.profile.sensitive_scenario_reactions
    sections = [f"# Sensitive Scenarios: {persona.profile.basic_identity['name']}", ""]
    for key in (
        "identity_disclosure",
        "privacy_and_data",
        "political_or_public_expression",
        "fairness_and_inclusion",
        "family_or_household_assumptions",
        "workplace_visibility",
        "financial_vulnerability",
        "health_or_wellbeing_sensitivity",
    ):
        block = layer.get(key, {})
        sections.extend(
            [
                f"## {key.replace('_', ' ').title()}",
                "Trigger scenarios:",
                *[f"- {item}" for item in block.get("trigger_scenarios", [])],
                f"Reaction: {block.get('reaction', '')}",
                f"What builds trust: {block.get('what_builds_trust', '')}",
                f"What reduces trust: {block.get('what_reduces_trust', '')}",
                "",
            ]
        )
    return "\n".join(sections).strip() + "\n"


def _rendered_artifacts(persona: PersonaSkill, v2_persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any]) -> dict[str, str]:
    return {
        "persona.md": _compat_persona_md_v3(persona),
        "biography.md": render_biography_md(persona),
        "research_kernel.md": render_research_kernel_md(persona),
        "persona.skill.md": render_persona_skill_md(persona),
        "local_grounding.md": render_local_grounding_md(persona),
        "sensitive_scenarios.md": render_sensitive_scenarios_md(persona),
        "v2_to_v3_diff.md": _persona_diff_notes(v2_persona, persona, diversity_report, quality_audit),
    }


def build_quality_audit_v3(persona: PersonaSkill, rendered_artifacts: dict[str, str], diversity_report: dict[str, Any]) -> dict[str, Any]:
    lived_scenes = persona.profile.canonical_biography.get("decade_timeline", [])
    local_grounding_score = 4 if len(persona.profile.local_grounding_layer.get("trust_cues_in_this_market", [])) >= 3 else 3
    sensitive_score = 4 if len(persona.profile.sensitive_scenario_reactions) >= 8 else 3
    voice_score = 4 if diversity_report.get("pair_reports") and diversity_report["overall_similarity_score"] < 0.65 else 3
    library_score = 4 if diversity_report.get("overall_similarity_score", 0.0) < 0.65 else 2
    template_score = 3
    scores = {
        "structure_completeness": 5,
        "biography_depth": 4,
        "lived_scene_quality": 4 if len(lived_scenes) >= 3 else 2,
        "local_grounding": local_grounding_score,
        "product_reaction_readiness": 4,
        "sensitive_topic_readiness": sensitive_score,
        "voice_distinctiveness": voice_score,
        "library_distinctiveness": library_score,
        "template_leakage_risk": template_score,
        "overall": 4 if library_score >= 4 else 3,
    }

    strengths = [
        f"Includes {len(lived_scenes)} decade-linked lived scenes rather than abstract timeline-only summaries.",
        f"Local grounding is tied to {persona.profile.basic_identity.get('location', '')} purchase and trust cues instead of generic geography labels.",
        "Sensitive scenarios now include concrete disclosure, privacy, household, workplace, financial, and wellbeing triggers.",
    ]

    archetype = _archetype_key(persona)
    weaknesses = [
        "Some cross-domain reactions still lean too heavily on workflow logic even after diversification.",
        "A few biography lines remain summary-like and could carry more sensory or situational detail.",
        "Local grounding is stronger than v2, but still lighter on offline trust cues and non-digital scenes than a high-fidelity human profile would need.",
    ]
    if archetype == "early_career_practical_trial_user":
        weaknesses[0] = "Daniel still reads many products through bounded-trial logic, which can compress emotional or status-driven categories into the same evaluation frame."
    if archetype == "mature_operator_retention_skeptic":
        weaknesses[0] = "Jordan still overweights maintenance transfer across multiple domains, which may underrepresent more emotionally led consumer reactions."

    required_improvements = [
        "Add one or two more low-stakes lived scenes that show ordinary purchase discovery outside work contexts.",
        "Increase local grounding through more offline trust signals, not just app and pricing references.",
        "Further diversify cross-domain reactions so not every category routes through the same core caution.",
    ]
    if diversity_report.get("overall_similarity_score", 0.0) >= 0.55:
        required_improvements.append("Push Daniel and Jordan further apart in how they phrase objection, especially in non-work categories.")

    warnings = []
    if diversity_report.get("overall_similarity_score", 0.0) >= 0.55:
        warnings.append("Residual similarity remains visible in the broad anti-friction lens across product categories.")
    if any(token in rendered_artifacts["biography.md"] for token in RAW_ENUM_TOKENS):
        warnings.append("Raw enum leakage detected in biography.")
    if any(phrase in _normalize_text(rendered_artifacts["persona.skill.md"]) for phrase in SHARED_TEMPLATE_PHRASES):
        warnings.append("Template phrase reuse remains too visible in persona.skill.md.")
    if not warnings:
        warnings.append("No hard schema issues remain, but this persona still needs more non-work lived texture before it would feel high-fidelity.")

    abstract_hits = [
        phrase
        for phrase in ("values reliability", "practical routines", "ordinary inconsistency")
        if phrase in _normalize_text(rendered_artifacts["biography.md"])
    ]
    return {
        "scores": scores,
        "strengths": strengths,
        "weaknesses": weaknesses[:3],
        "required_improvements": required_improvements[:4],
        "warnings": warnings,
        "enum_leakage_check": "pass" if not any(token in rendered_artifacts["biography.md"] for token in RAW_ENUM_TOKENS) else "fail",
        "abstract_language_check": "needs_attention" if abstract_hits else "pass",
        "local_grounding_check": "pass" if local_grounding_score >= 4 else "weak",
        "sensitive_scenario_check": "pass" if sensitive_score >= 4 else "weak",
        "similarity_check": f"overall={diversity_report.get('overall_similarity_score', 0.0)}",
        "human_review_needed": True,
    }


def build_generation_notes_v3(persona: PersonaSkill, diversity_report: dict[str, Any], quality_audit: dict[str, Any], random_seed: int | None, source_version_dir: Path, comparison_ids: list[str]) -> dict[str, Any]:
    return {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": "persona-generator/v3",
        "prompt_versions": PROMPT_VERSIONS,
        "model_used": "deterministic-template-v3",
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
    }


def write_v3_persona_folder(
    persona: PersonaSkill,
    *,
    v2_persona: PersonaSkill,
    root_data_dir: Path,
    source_v2_dir: Path,
    diversity_report: dict[str, Any],
    quality_audit: dict[str, Any],
    random_seed: int | None = None,
) -> Path:
    persona_root = root_data_dir / persona.profile.synthetic_user_id
    ensure_dir(persona_root)
    sync_v2_source_to_canonical(persona.profile.synthetic_user_id, source_v2_dir.parent, root_data_dir)

    v3_dir = persona_root / "v3"
    ensure_dir(v3_dir)
    rendered = _rendered_artifacts(persona, v2_persona, diversity_report, quality_audit)
    generation_notes = build_generation_notes_v3(
        persona,
        diversity_report,
        quality_audit,
        random_seed,
        source_v2_dir,
        diversity_report.get("compared_against", []),
    )

    persona.audit = {
        **persona.audit,
        "quality_audit": quality_audit,
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
        },
        "generator_version": "persona-generator/v3",
    }

    write_json(v3_dir / "profile.json", persona.profile.to_dict())
    write_json(v3_dir / "audit.json", persona.to_audit_payload())
    write_json(v3_dir / "generation_notes.json", generation_notes)
    write_json(v3_dir / "diversity_report.json", diversity_report)
    for filename, content in rendered.items():
        (v3_dir / filename).write_text(content, encoding="utf-8")
    return v3_dir


def validate_v3_persona_folder(folder: Path) -> dict[str, Any]:
    missing_files = [filename for filename in V3_REQUIRED_FILES if not (folder / filename).exists()]
    persona = load_persona(folder)
    audit_payload = read_json(folder / "audit.json")
    profile_payload = read_json(folder / "profile.json")
    diversity_report = read_json(folder / "diversity_report.json")
    quality_audit = audit_payload["audit"].get("quality_audit", {})

    consistency_warnings: list[str] = []
    if any(token in (folder / "biography.md").read_text(encoding="utf-8") for token in RAW_ENUM_TOKENS):
        consistency_warnings.append("Raw enum leakage detected in biography.md.")

    for chapter in profile_payload.get("canonical_biography", {}).get("decade_timeline", []):
        if not chapter.get("specific_scene"):
            consistency_warnings.append(f"Missing specific_scene in chapter {chapter.get('age_range', 'unknown')}.")

    if not profile_payload.get("local_grounding_layer"):
        missing_files.append("local_grounding_layer")
    if not profile_payload.get("sensitive_scenario_reactions"):
        missing_files.append("sensitive_scenario_reactions")
    if not profile_payload.get("persona_voiceprint"):
        missing_files.append("persona_voiceprint")

    if quality_audit:
        scores = quality_audit.get("scores", {})
        if scores and all(value == 5 for value in scores.values()):
            consistency_warnings.append("quality_audit scores are unrealistically all perfect.")
        if len(quality_audit.get("weaknesses", [])) < 3:
            consistency_warnings.append("quality_audit must include at least 3 weaknesses.")
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


def validate_v3_persona_library(base_dir: Path) -> dict[str, Any]:
    if not base_dir.exists():
        return {
            "library_size": 0,
            "persona_reports": [],
            "issue_count": 0,
            "warning_count": 0,
        }

    persona_reports = []
    for persona_id in _persona_ids_in(base_dir):
        v3_dir = base_dir / persona_id / "v3"
        if not v3_dir.exists():
            continue
        report = validate_v3_persona_folder(v3_dir)
        persona_reports.append({"persona_id": persona_id, **report})

    issue_count = sum(len(report["missing_fields"]) + len(report["consistency_warnings"]) for report in persona_reports)
    warning_count = sum(len(report["stereotype_warnings"]) for report in persona_reports)
    return {
        "library_size": len(persona_reports),
        "persona_reports": persona_reports,
        "issue_count": issue_count,
        "warning_count": warning_count,
    }


def run_distinctiveness_check(
    *,
    base_dir: Path,
    persona_id: str,
    against_persona_ids: list[str],
    preferred_versions: tuple[str, ...] = ("v3", "v2", "root"),
) -> dict[str, Any]:
    candidate = _load_persona_from_dir(base_dir, persona_id, preferred_versions)
    comparisons = [
        _load_persona_from_dir(base_dir, other_id, preferred_versions)
        for other_id in against_persona_ids
        if other_id != persona_id
    ]
    return build_diversity_report(candidate, comparisons)


def generate_v3_personas(
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
    for persona_id in selected_ids:
        sync_v2_source_to_canonical(persona_id, source_dir, output_dir)

    source_personas = {
        persona_id: load_persona(source_dir / persona_id)
        for persona_id in selected_ids
    }

    provisional = {
        persona_id: upgrade_persona_to_v3(source_personas[persona_id], random_seed=random_seed_offset + index)
        for index, persona_id in enumerate(selected_ids)
    }

    external_comparisons: dict[str, PersonaSkill] = {}
    if against_persona_ids:
        comparison_ids = [persona_id for persona_id in against_persona_ids if persona_id not in selected_ids]
    else:
        comparison_ids = []
    for comparison_id in comparison_ids:
        external_comparisons[comparison_id] = _load_persona_from_dir(compare_against_dir, comparison_id)

    for _pass in range(2):
        for persona_id in selected_ids:
            comparison_pool = [
                provisional[other_id]
                for other_id in selected_ids
                if other_id != persona_id
            ] + list(external_comparisons.values())
            diversity_report = build_diversity_report(provisional[persona_id], comparison_pool)
            if _requires_distinctiveness_revision(diversity_report):
                provisional[persona_id] = apply_distinctiveness_revision(provisional[persona_id], comparison_pool)

    written_paths: list[Path] = []
    for index, persona_id in enumerate(selected_ids):
        comparison_pool = [
            provisional[other_id]
            for other_id in selected_ids
            if other_id != persona_id
        ] + list(external_comparisons.values())
        diversity_report = build_diversity_report(provisional[persona_id], comparison_pool)
        rendered = _rendered_artifacts(provisional[persona_id], source_personas[persona_id], diversity_report, {"warnings": [], "required_improvements": []})
        quality_audit = build_quality_audit_v3(provisional[persona_id], rendered, diversity_report)
        written_paths.append(
            write_v3_persona_folder(
                provisional[persona_id],
                v2_persona=source_personas[persona_id],
                root_data_dir=output_dir,
                source_v2_dir=source_dir / persona_id,
                diversity_report=diversity_report,
                quality_audit=quality_audit,
                random_seed=random_seed_offset + index,
            )
        )
    return written_paths
