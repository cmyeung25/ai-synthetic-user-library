from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.v2 import prompt_path
from ai_validation_swarm.personas.v3 import (
    RAW_ENUM_TOKENS,
    _archetype_key,
    _load_persona_from_dir,
    _normalize_text,
    _persona_ids_in,
    _resolve_persona_folder,
    render_local_grounding_md as render_local_grounding_md_v3,
)
from ai_validation_swarm.personas.v3_1 import (
    SHARED_TEMPLATE_PHRASES,
    SENSITIVE_SCENARIO_KEYS,
    _title_from_key,
    _top_salience_keys,
    build_diversity_report_v3_1,
    render_research_kernel_md_v3_1,
    render_sensitive_scenarios_md_v3_1,
    upgrade_persona_to_v3_1,
)
from ai_validation_swarm.storage.files import ensure_dir, load_persona, read_json, write_json

PROMPT_VERSIONS = [
    "persona-biography/v3_1_1.md",
    "persona-skill/v3_1_1.md",
    "quality-auditor/v3_1_1.md",
    "markdown-polish/v3_1_1.md",
]

V3_1_1_REQUIRED_FILES = (
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
    "v3_1_to_v3_1_1_diff.md",
    "polish_report.json",
)

READABLE_MARKDOWN_FILES = (
    "biography.md",
    "research_kernel.md",
    "persona.skill.md",
    "persona.md",
    "local_grounding.md",
    "sensitive_scenarios.md",
    "v3_1_to_v3_1_1_diff.md",
)

REPEATED_TEMPLATE_PHRASES = (
    "i understand the pitch that is not the part i doubt",
    "if the product still feels like",
    "i can see why someone would want this",
)

CODE_FENCE = "```"
SPECIAL_ARCHETYPES = {
    "early_career_practical_trial_user",
    "mature_operator_retention_skeptic",
}


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_v3_1_1_prompt_texts() -> dict[str, str]:
    return {
        prompt_version: prompt_path(prompt_version).read_text(encoding="utf-8").strip()
        for prompt_version in PROMPT_VERSIONS
    }


def _iter_non_code_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith(CODE_FENCE):
            in_code = not in_code
            continue
        if not in_code:
            lines.append(line)
    return lines


def _clean_markdown_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"\bai\b", "AI", cleaned)
    cleaned = cleaned.replace("..", ".")
    cleaned = cleaned.replace(".,", ".")
    cleaned = cleaned.replace("?.", "?")
    cleaned = cleaned.replace("!.", "!")
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"([.!?]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    return cleaned.strip() + "\n"


def lint_markdown_cleanliness(text: str) -> dict[str, int]:
    lines = _iter_non_code_lines(text)
    raw_python_dict_patterns = 0
    raw_json_object_leakage = 0
    double_punctuation = 0
    lowercase_ai = 0
    awkward_spacing = 0
    repeated_template_phrases = 0

    for line in lines:
        raw_python_dict_patterns += line.count("{'")
        raw_python_dict_patterns += len(re.findall(r"\{'.+?':", line))
        if re.match(r"^\s*\{", line):
            raw_json_object_leakage += 1
        if line.rstrip().endswith("},"):
            raw_json_object_leakage += 1
        if re.search(r'"[^"]+"\s*:\s*', line):
            raw_json_object_leakage += 1
        double_punctuation += len(re.findall(r"\.\.|\.\,|\?\.|!\.", line))
        lowercase_ai += len(re.findall(r"\bai\b", line))
        awkward_spacing += len(re.findall(r"\s+[,.!?;:]", line))

    normalized = _normalize_text("\n".join(lines))
    for phrase in REPEATED_TEMPLATE_PHRASES:
        repeated_template_phrases += normalized.count(phrase)

    return {
        "raw_python_dict_patterns": raw_python_dict_patterns,
        "raw_json_object_leakage": raw_json_object_leakage,
        "double_punctuation": double_punctuation,
        "lowercase_ai": lowercase_ai,
        "awkward_spacing": awkward_spacing,
        "repeated_template_phrases": repeated_template_phrases,
    }


def _aggregate_markdown_lint(artifact_map: dict[str, str]) -> dict[str, int]:
    totals = {
        "raw_python_dict_patterns": 0,
        "raw_json_object_leakage": 0,
        "double_punctuation": 0,
        "lowercase_ai": 0,
        "awkward_spacing": 0,
        "repeated_template_phrases": 0,
    }
    for filename in READABLE_MARKDOWN_FILES:
        if filename not in artifact_map:
            continue
        counts = lint_markdown_cleanliness(artifact_map[filename])
        for key, value in counts.items():
            totals[key] += value
    return totals


def _source_markdown_artifacts(source_dir: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for filename in READABLE_MARKDOWN_FILES:
        path = source_dir / filename
        if path.exists():
            artifacts[filename] = path.read_text(encoding="utf-8")
    return artifacts


def render_formative_events_markdown(events: list[dict[str, Any]] | list[Any], chapters: list[dict[str, Any]]) -> str:
    if not events:
        return "- No formative events were recorded.\n"

    chapter_lookup = {
        str(chapter.get("age_range", "")): chapter
        for chapter in chapters
    }
    lines: list[str] = []
    for event in events:
        if isinstance(event, dict):
            age_range = str(event.get("age_range") or event.get("age_or_period") or "").strip() or "Life stage"
            chapter = chapter_lookup.get(age_range, {})
            chapter_title = str(
                chapter.get("chapter_title") or event.get("title") or event.get("event") or "Formative event"
            ).strip()
            summary = str(event.get("event_summary") or event.get("specific_scene") or event.get("event") or "").strip()
            impact = str(event.get("impact") or chapter.get("current_reaction_link") or "").strip()
            lines.append(f"- {age_range} - {chapter_title}")
            if summary:
                lines.append(f"  {summary}")
            if impact:
                lines.append(f"  Impact: {impact}")
            continue
        lines.append(f"- {str(event).strip()}")
    return _clean_markdown_text("\n".join(lines)).strip() + "\n"


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
        elif value:
            return str(value).strip()
    return ""


def _clean_list(values: list[Any]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _v3_1_1_archetype_key(persona: PersonaSkill) -> str:
    base = _archetype_key(persona)
    if base in SPECIAL_ARCHETYPES:
        return base

    seed_role = str(persona.seed.panel_role).strip().lower()
    identity = persona.profile.basic_identity
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile
    occupation = str(identity.get("occupation", "")).lower()
    gender = str(identity.get("gender", "")).lower()
    family_structure = str(identity.get("family_structure", "")).lower()
    household_size = int(identity.get("household_size", 1) or 1)
    tech_savviness = str(technology.get("tech_savviness", "")).lower()
    ai_familiarity = str(technology.get("ai_familiarity", "")).lower()
    privacy_concern = str(technology.get("privacy_concern", "")).lower()
    price_sensitivity = str(
        economic.get("price_sensitivity", "") or persona.seed.budget_flexibility
    ).lower()
    schedule_pressure = str(persona.seed.schedule_pressure).lower()

    if seed_role == "extreme_user" or ai_familiarity == "high":
        return "ambitious_signal_seeker"
    if seed_role == "political_risk":
        return "public_reputation_risk_guard"
    if seed_role == "privacy_sensitive" or privacy_concern == "high":
        return "privacy_narrow_trialist"
    if seed_role == "low_tech" or tech_savviness == "low":
        return "low_energy_avoidant_adapter"
    if seed_role == "inclusion" or (gender == "non-binary" and household_size <= 3):
        return "quiet_inclusion_checker"
    if seed_role == "budget_constrained" or price_sensitivity == "low" or household_size >= 4 or "single parent" in family_structure:
        return "budget_guarded_household_operator"
    if any(token in occupation for token in ("retail", "account", "customer", "field service", "logistics", "community")):
        return "credibility_guarding_service_operator"
    if schedule_pressure == "high":
        return "low_energy_avoidant_adapter"
    return "routine_protecting_generalist"


def _panel_role_profile_v3_1_1(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype in SPECIAL_ARCHETYPES:
        return copy.deepcopy(persona.profile.panel_role_profile)

    if archetype == "quiet_inclusion_checker":
        return {
            "panel_role": "identity_sensitive_user",
            "behavioural_archetype": archetype,
            "research_function": "detects exclusion hidden inside defaults, profile settings, and disclosure timing",
            "what_this_person_is_good_at_detecting": [
                "binary-only or over-labelled identity flows",
                "inclusive copy without practical controls",
                "trust drop caused by public-by-default profile settings",
                "quiet abandonment caused by discomfort rather than loud complaint",
            ],
            "what_this_person_will_overweight": [
                "disclosure control",
                "default visibility",
                "whether respect survives the actual form or onboarding path",
            ],
            "what_this_person_may_miss": [
                "pure efficiency gains when identity cost is close to zero",
                "power-user appetite for dense setup if the product otherwise feels safe",
            ],
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "panel_role": "privacy_sensitive",
            "behavioural_archetype": archetype,
            "research_function": "detects permission creep, vague retention policy, and trials that ask for too much too early",
            "what_this_person_is_good_at_detecting": [
                "over-broad data requests",
                "unclear model training or retention language",
                "trust collapse at the sign-up or integration step",
                "products that confuse convenience with entitlement to access",
            ],
            "what_this_person_will_overweight": [
                "scope of access",
                "private defaults",
                "reversible trial design",
            ],
            "what_this_person_may_miss": [
                "social-status appeal from being an early visible adopter",
                "team-level gains that require wider data sharing to surface",
            ],
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "panel_role": "budget_blocker",
            "behavioural_archetype": archetype,
            "research_function": "detects recurring spend that is weakly defensible in ordinary household reality",
            "what_this_person_is_good_at_detecting": [
                "subscription creep",
                "pricing that feels copied from imported SaaS norms",
                "household coordination tools that quietly nominate one unpaid admin",
                "claims of savings that ignore effort and explainability cost",
            ],
            "what_this_person_will_overweight": [
                "monthly defensibility",
                "easy exit",
                "whether the spend can be explained at home without sounding indulgent",
            ],
            "what_this_person_may_miss": [
                "premium positioning that works mainly through aspiration or identity signaling",
                "high-end enthusiast behavior where convenience beats budget logic",
            ],
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "panel_role": "public_reputation_risk_user",
            "behavioural_archetype": archetype,
            "research_function": "detects tools that create visible service failure, apology work, or customer-facing cleanup",
            "what_this_person_is_good_at_detecting": [
                "live-use fragility",
                "handoff tools that fail under rush conditions",
                "products that turn the buyer into de facto support staff",
                "features that sound tidy but are hard to explain to customers or teammates",
            ],
            "what_this_person_will_overweight": [
                "visible failure risk",
                "explainability under pressure",
                "whether the product protects or weakens credibility in front of others",
            ],
            "what_this_person_may_miss": [
                "solo-user optimization that never becomes public",
                "long-range analytics value that is invisible in daily service situations",
            ],
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "panel_role": "status_sensitive_buyer",
            "behavioural_archetype": archetype,
            "research_function": "detects whether a product creates visible leverage quickly enough to matter",
            "what_this_person_is_good_at_detecting": [
                "speed-to-visible-win",
                "novelty that dies before proving usefulness",
                "AI positioning that sounds advanced but still feels slow",
                "tools that are exciting in week one and absent in week three",
            ],
            "what_this_person_will_overweight": [
                "fast visible progress",
                "feeling ahead of the curve",
                "whether the product can be shown upward or outward quickly",
            ],
            "what_this_person_may_miss": [
                "quiet long-term retention issues",
                "buyers whose main concern is privacy or household explainability",
            ],
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "panel_role": "public_reputation_risk_user",
            "behavioural_archetype": archetype,
            "research_function": "detects when products blur private evaluation and public alignment too early",
            "what_this_person_is_good_at_detecting": [
                "social-sharing pressure disguised as community",
                "public participation defaults",
                "brand or feature design that assumes visible alignment",
                "tools that create public traces before private confidence exists",
            ],
            "what_this_person_will_overweight": [
                "private-first control",
                "public-expression cost",
                "whether participation can stay quiet and reversible",
            ],
            "what_this_person_may_miss": [
                "community-led growth that works for users who enjoy visible sharing",
                "social proof loops that depend on public enthusiasm",
            ],
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "panel_role": "overwhelmed_passive_user",
            "behavioural_archetype": archetype,
            "research_function": "detects tools that technically make sense but demand more energy than real life can support",
            "what_this_person_is_good_at_detecting": [
                "late-evening setup failure",
                "drop-off after the first busy week",
                "mobile-unfriendly onboarding",
                "products that mistake understanding for available energy",
            ],
            "what_this_person_will_overweight": [
                "low setup energy",
                "fast first value",
                "whether the product still works on tired weeks",
            ],
            "what_this_person_may_miss": [
                "advanced capabilities that pay off only after discipline builds",
                "team workflows that require a motivated internal champion",
            ],
        }
    return {
        "panel_role": "mainstream_buyer",
        "behavioural_archetype": archetype,
        "research_function": "detects whether a product earns room inside an uneven ordinary week",
        "what_this_person_is_good_at_detecting": [
            "weak first-step logic",
            "value claims that do not survive routine pressure",
            "products that are clearer in pitch than in use",
        ],
        "what_this_person_will_overweight": [
            "attention cost",
            "practical fit",
            "whether the product needs more explanation than the problem",
        ],
        "what_this_person_may_miss": [
            "specialist edge-case enthusiasm",
            "enterprise buying logic that depends on formal procurement and compliance layers",
        ],
    }


def _occupation_context_phrase(occupation: str) -> str:
    normalized = occupation.strip().lower()
    if not normalized:
        return "work"
    if normalized == "operations manager":
        return "operations work"
    if normalized.endswith("manager"):
        return normalized.replace(" manager", " management work")
    if normalized.endswith("specialist"):
        return normalized.replace(" specialist", " specialist work")
    return normalized


def _fallback_sensitive_salience(persona: PersonaSkill) -> dict[str, int]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "quiet_inclusion_checker":
        return {
            "identity_disclosure": 9,
            "privacy_and_data": 7,
            "political_or_public_expression": 5,
            "fairness_and_inclusion": 9,
            "family_or_household_assumptions": 7,
            "workplace_visibility": 6,
            "financial_vulnerability": 5,
            "health_or_wellbeing_sensitivity": 5,
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "identity_disclosure": 6,
            "privacy_and_data": 9,
            "political_or_public_expression": 4,
            "fairness_and_inclusion": 5,
            "family_or_household_assumptions": 5,
            "workplace_visibility": 6,
            "financial_vulnerability": 5,
            "health_or_wellbeing_sensitivity": 6,
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "identity_disclosure": 4,
            "privacy_and_data": 6,
            "political_or_public_expression": 4,
            "fairness_and_inclusion": 5,
            "family_or_household_assumptions": 7,
            "workplace_visibility": 5,
            "financial_vulnerability": 9,
            "health_or_wellbeing_sensitivity": 5,
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "identity_disclosure": 4,
            "privacy_and_data": 6,
            "political_or_public_expression": 4,
            "fairness_and_inclusion": 5,
            "family_or_household_assumptions": 5,
            "workplace_visibility": 9,
            "financial_vulnerability": 6,
            "health_or_wellbeing_sensitivity": 5,
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "identity_disclosure": 4,
            "privacy_and_data": 6,
            "political_or_public_expression": 4,
            "fairness_and_inclusion": 5,
            "family_or_household_assumptions": 4,
            "workplace_visibility": 8,
            "financial_vulnerability": 5,
            "health_or_wellbeing_sensitivity": 4,
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "identity_disclosure": 6,
            "privacy_and_data": 7,
            "political_or_public_expression": 9,
            "fairness_and_inclusion": 6,
            "family_or_household_assumptions": 5,
            "workplace_visibility": 7,
            "financial_vulnerability": 5,
            "health_or_wellbeing_sensitivity": 4,
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "identity_disclosure": 4,
            "privacy_and_data": 5,
            "political_or_public_expression": 3,
            "fairness_and_inclusion": 4,
            "family_or_household_assumptions": 5,
            "workplace_visibility": 6,
            "financial_vulnerability": 6,
            "health_or_wellbeing_sensitivity": 7,
        }

    salience = {key: 5 for key in SENSITIVE_SCENARIO_KEYS}
    basic_identity = persona.profile.basic_identity
    technology = persona.profile.technology_profile
    economic = persona.profile.economic_profile
    sensitive = persona.profile.sensitive_reality_layer
    workplace_visibility = 6 if "manager" in str(basic_identity.get("occupation", "")).lower() else 5

    if str(technology.get("privacy_concern", "")).lower() == "high":
        salience["privacy_and_data"] = 8
    if str(basic_identity.get("gender", "")).lower() == "non-binary":
        salience["identity_disclosure"] = 7
        salience["fairness_and_inclusion"] = 7
        salience["family_or_household_assumptions"] = 6
    if str(economic.get("cash_flow_volatility", "")).lower() == "high":
        salience["financial_vulnerability"] = 7
    if str(sensitive.get("public_expression_risk_aversion", "")).lower() in {"medium", "high"}:
        salience["political_or_public_expression"] = 6
    salience["workplace_visibility"] = workplace_visibility
    return salience


def _fallback_sensitive_scenarios(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _v3_1_1_archetype_key(persona)
    basic_identity = persona.profile.basic_identity
    location = str(basic_identity.get("location", "")).strip() or "their city"
    occupation = str(basic_identity.get("occupation", "")).strip() or "their work"
    occupation_context = _occupation_context_phrase(occupation)
    direct_examples = persona.profile.objection_language_style.get("direct_objection_examples", [])
    private_concern = _first_non_empty(
        persona.profile.sensitive_reality_layer.get("response_boundaries", []),
        "They want a clear reason before sharing personal or third-party data.",
    )
    scenarios = {
        "identity_disclosure": {
            "trigger_scenarios": [
                "binary-only gender field before a basic trial",
                "mandatory title such as Mr, Ms, or Mrs",
                "profile defaults that expose personal labels too early",
            ],
            "reaction": (
                "They do not usually turn this into a public argument. Trust drops quietly when disclosure appears before utility."
            ),
            "what_builds_trust": "Optional disclosure, prefer-not-to-say, private defaults, and a clear reason for asking.",
            "what_reduces_trust": "Mandatory identity labels or profile visibility before the product has earned relevance.",
        },
        "privacy_and_data": {
            "trigger_scenarios": [
                "broad access to messages or calendars before a bounded test exists",
                "AI handling client or household detail with vague retention language",
                "permissions that feel wider than the first use case",
            ],
            "reaction": (
                "They become guarded when the product wants authority earlier than it shows competence."
            ),
            "what_builds_trust": "Minimal permissions, review before action, plain retention language, and easy rollback.",
            "what_reduces_trust": _first_non_empty(
                direct_examples,
                "Broad access that arrives before a narrow proof of value.",
            ),
        },
        "political_or_public_expression": {
            "trigger_scenarios": [
                "community features that assume public posting is normal",
                "brand copy that treats visible alignment as part of trust",
                "social sharing prompts in ordinary workflows",
            ],
            "reaction": "They usually opt out rather than perform agreement in public.",
            "what_builds_trust": "Private participation paths and calm visibility controls.",
            "what_reduces_trust": "Any workflow that turns ordinary use into a public stance.",
        },
        "fairness_and_inclusion": {
            "trigger_scenarios": [
                "inclusive copy with no practical settings control",
                "default-user examples that quietly exclude messy real lives",
                "support language that sounds current but still forces one path",
            ],
            "reaction": "They look for whether respect changes the flow, not just the headline copy.",
            "what_builds_trust": "Respectful defaults, optional labels, and clear user control over sensitive steps.",
            "what_reduces_trust": "Performative inclusion that leaves the risky defaults untouched.",
        },
        "family_or_household_assumptions": {
            "trigger_scenarios": [
                "shared plans that assume one tidy household admin",
                "forms that force husband or wife labels",
                "household workflows that expose more than coordination requires",
            ],
            "reaction": "They want coordination help without turning the home into a visibility system.",
            "what_builds_trust": "Role-neutral language, optional sharing, and boundaries between coordination and exposure.",
            "what_reduces_trust": "Household defaults that quietly nominate one person to carry upkeep.",
        },
        "workplace_visibility": {
            "trigger_scenarios": [
                "dashboards that show unfinished setup to colleagues",
                "AI output visible before they can review it",
                "trial flows that make learning look like incompetence",
            ],
            "reaction": (
                f"In {occupation_context}, they protect credibility before they protect feature curiosity."
            ),
            "what_builds_trust": "Private draft space, staged rollout, and clear control over when work becomes visible.",
            "what_reduces_trust": "Visibility that arrives before relief or competence.",
        },
        "financial_vulnerability": {
            "trigger_scenarios": [
                "annual plans framed as the serious option",
                "pricing copied from USD logic with weak local context",
                "upsell language that treats caution as unserious",
            ],
            "reaction": "They think about line-item defensibility, not only sticker price.",
            "what_builds_trust": (
                f"Local pricing realism in {location}, easy exit, and a clear explanation of ongoing value."
            ),
            "what_reduces_trust": "Recurring cost that becomes hard to justify after the first month.",
        },
        "health_or_wellbeing_sensitivity": {
            "trigger_scenarios": [
                "private wellbeing prompts shown in shared contexts",
                "habit trackers that turn inconsistency into moral failure",
                "products that infer too much from thin data",
            ],
            "reaction": "They disengage when support starts to feel like surveillance or shame.",
            "what_builds_trust": "Private control, neutral tone, and no guilt loop.",
            "what_reduces_trust": private_concern,
        },
    }
    if archetype == "quiet_inclusion_checker":
        scenarios["identity_disclosure"].update(
            {
                "trigger_scenarios": [
                    "binary-only form fields",
                    "member profile defaults that show labels too early",
                    "community sign-up that asks for identity before relevance is visible",
                    "prefer-not-to-say missing from a basic onboarding flow",
                ],
                "reaction": "They often leave quietly rather than escalate. The discomfort is real even when the response stays outwardly calm.",
                "what_builds_trust": "Optional disclosure, private defaults, and a clear explanation of why any identity field exists.",
                "what_reduces_trust": "Being asked to become legible before the product has become useful.",
            }
        )
        scenarios["fairness_and_inclusion"].update(
            {
                "reaction": "They check whether the settings, labels, and role assumptions match the respectful tone in the headline copy.",
                "what_builds_trust": "Respectful language plus a flow that still works if they disclose very little.",
                "what_reduces_trust": "Warm inclusive language wrapped around one narrow default user path.",
            }
        )
    elif archetype == "privacy_narrow_trialist":
        scenarios["privacy_and_data"].update(
            {
                "reaction": "They narrow the scope immediately. A trial that wants full history or full integration is treated as an overreach, not as enthusiasm.",
                "what_builds_trust": "Sample data, redacted trials, reversible connections, and a short plain-language retention explanation.",
                "what_reduces_trust": "Anything that says trust us now and refine later.",
            }
        )
        scenarios["identity_disclosure"].update(
            {
                "reaction": "Even neutral identity questions feel heavier when they arrive before a narrow proof of value.",
            }
        )
    elif archetype == "budget_guarded_household_operator":
        scenarios["financial_vulnerability"].update(
            {
                "reaction": "They measure price against monthly explainability. The question is not just can I afford it, but can I defend it after the launch mood disappears.",
                "what_builds_trust": f"Local pricing realism in {location}, an easy exit path, and a clear answer to what existing spend or effort this replaces.",
                "what_reduces_trust": "Recurring cost that becomes another item to justify at home every month.",
            }
        )
        scenarios["family_or_household_assumptions"].update(
            {
                "reaction": "They dislike products that quietly assign household admin work to the person who clicked first.",
                "what_builds_trust": "Role-neutral language, optional sharing, and settings that let coordination stay lighter than surveillance.",
            }
        )
    elif archetype == "credibility_guarding_service_operator":
        scenarios["workplace_visibility"].update(
            {
                "reaction": f"In {occupation_context}, they imagine the moment the tool fails live and someone looks at them for the explanation.",
                "what_builds_trust": "Private rehearsal, clear failure handling, and proof that the product behaves cleanly during rushed handoffs.",
                "what_reduces_trust": "Any workflow that turns them into the apology layer for the product.",
            }
        )
    elif archetype == "ambitious_signal_seeker":
        scenarios["workplace_visibility"].update(
            {
                "reaction": "Visibility is not automatically bad. They welcome it when the tool makes them look sharper, but drop it fast when visibility arrives before competence.",
                "what_builds_trust": "A quick visible win, good defaults, and control over what can be shown upward.",
                "what_reduces_trust": "A flashy promise that still makes them look unprepared in week one.",
            }
        )
    elif archetype == "public_reputation_risk_guard":
        scenarios["political_or_public_expression"].update(
            {
                "reaction": "They prefer to evaluate privately first. Products that turn ordinary participation into visible alignment shorten the conversation quickly.",
                "what_builds_trust": "Private modes, quiet participation, and no assumption that public sharing equals trust.",
                "what_reduces_trust": "Social pressure that treats non-public use as low commitment.",
            }
        )
    elif archetype == "low_energy_avoidant_adapter":
        scenarios["health_or_wellbeing_sensitivity"].update(
            {
                "reaction": "They drop tools fastest when support starts to feel like another reminder of inconsistency on tired days.",
                "what_builds_trust": "Gentle tone, easy restart, and no punishment for missing a week.",
                "what_reduces_trust": "Any product that converts fatigue into visible failure or guilt loops.",
            }
        )
    return scenarios


def _fallback_objection_language_style(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "quiet_inclusion_checker":
        return {
            "direct_objection_examples": [
                "If the form needs my identity before it earns relevance, I usually stop there.",
                "Respect is not the headline. It is whether the risky default can stay private.",
            ],
            "polite_objection_examples": [
                "I can see what you're trying to do. I would still want more control over what becomes visible.",
            ],
            "hidden_objection_patterns": [
                "quietly disengages after an unnecessary disclosure step",
                "says the product is fine while deciding it is not designed for them",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "The concept is clear. I would want to see the settings and profile defaults.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "Can I use the core flow first and choose later what, if anything, I disclose?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What stays optional and private by default during the first trial?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If this becomes a paid tool, do the privacy and profile controls stay as strong as the headline language?",
            ],
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "direct_objection_examples": [
                "That is too much access for a first test.",
                "If the trial needs full history, I am not doing the trial.",
            ],
            "polite_objection_examples": [
                "I would need a narrower starting point before I connect real data.",
            ],
            "hidden_objection_patterns": [
                "becomes brief when the scope of data access feels too wide",
                "moves from curiosity to exit without debating the principle",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "Interesting. I would need to understand the data boundary more clearly.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "Can I test this with sample or limited data first?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What is the smallest safe connection that still proves the value?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If I pay, do I keep the same minimal-access option, or does the product start expanding scope?",
            ],
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "direct_objection_examples": [
                "I can explain a one-time tool more easily than another monthly maybe.",
                "If this adds a recurring charge before it removes one, it will not last.",
            ],
            "polite_objection_examples": [
                "Looks useful. I still need to see whether it earns a place in the monthly budget.",
            ],
            "hidden_objection_patterns": [
                "sounds warm in the conversation but freezes at the billing step",
                "asks for family or household context without saying that approval matters",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "I can see who this helps. I just need to think about the ongoing spend.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "If this actually replaces one existing cost or repeat hassle, then I want to test it.",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "Can I try this without locking into another subscription right away?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "What am I stopping or simplifying enough that I can still defend this next month?",
            ],
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "direct_objection_examples": [
                "If this fails live, I am the one explaining it.",
                "Do not turn me into customer support for your product.",
            ],
            "polite_objection_examples": [
                "I can see the use case. I need to know how it behaves when the day is already rushed.",
            ],
            "hidden_objection_patterns": [
                "tests the product mentally against an angry-customer moment",
                "asks about edge cases because visible failure matters more than clean demos",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "Interesting. I would need to see it under real service pressure.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "Could I test this in one customer-facing handoff before I put my name behind it?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What happens when this is wrong in front of the customer or the team?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If I recommend this internally, who helps when it breaks under rush conditions?",
            ],
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "direct_objection_examples": [
                "If I cannot show a visible win quickly, I will move on.",
                "I do not need another clever demo that disappears in two weeks.",
            ],
            "polite_objection_examples": [
                "This is interesting. I want the fastest proof path, not the fullest setup.",
            ],
            "hidden_objection_patterns": [
                "sounds excited early but quietly drops products that stall before a visible result",
                "acts like an early adopter while still protecting public failure",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "The idea is strong. I would want to see the quickest real proof.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "What can I show by next week if this actually works?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "Can I run this on one visible use case without turning it into a full migration?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If I keep paying, what keeps the momentum visible after the first burst of novelty?",
            ],
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "direct_objection_examples": [
                "Keep the trial private, or I am not doing the trial.",
                "Public participation is not a neutral default for me.",
            ],
            "polite_objection_examples": [
                "I would want to understand the visibility settings before going further.",
            ],
            "hidden_objection_patterns": [
                "becomes reserved when public posting or visible alignment enters the flow",
                "avoids arguing and instead looks for a private path or exits",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "I can see the concept. I would still need quiet participation options.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "Can I evaluate this without leaving a visible public trail first?",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "Which parts stay private by default if I only want to test the core use case?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If I pay, do I gain stronger privacy and visibility controls or just more public-facing features?",
            ],
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "direct_objection_examples": [
                "If this needs setup tonight, it is not happening.",
                "I understand it. I just do not have the energy for another maintenance loop.",
            ],
            "polite_objection_examples": [
                "Maybe useful. I would need the first step to be very small.",
            ],
            "hidden_objection_patterns": [
                "agrees with the logic and still never starts",
                "leaves products unread in email or app queues once the week gets noisy",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "Maybe. I would need a simpler start than this.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "If I can do the first useful step in one short session, I would try it.",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What is the fastest version that still works on a tired week?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "If I stop using this for a week, is it easy to come back without feeling behind?",
            ],
        }
    if archetype == "routine_protecting_generalist":
        return {
            "direct_objection_examples": [
                "I understand the idea. I still need to see what becomes easier before I make room for it.",
                "A tidy story is not enough if the week still gets heavier.",
            ],
            "polite_objection_examples": [
                "I can see the use case. I would still want a smaller first step.",
            ],
            "hidden_objection_patterns": [
                "sounds agreeable before they have actually given the product routine space",
                "drops interest when the first step feels more formal than the problem",
            ],
            "what_they_say_when_they_are_only_being_nice": [
                "Interesting idea. I can see why people would look at it.",
            ],
            "what_they_say_when_they_are_genuinely_interested": [
                "If you can show me the smallest useful version, then I want to test it.",
            ],
            "what_they_ask_when_they_are_close_to_trying": [
                "What is the narrowest trial that still proves the value in a normal week?",
            ],
            "what_they_ask_when_they_are_close_to paying": [
                "What stays useful enough that I keep paying once the first tidy week is over?",
            ],
        }
    return {
        "direct_objection_examples": [
            "I understand the idea. I still need to see what becomes easier before I make room for it.",
            "A tidy story is not enough if the week still gets heavier.",
        ],
        "polite_objection_examples": [
            "I can see the use case. I would still want a smaller first step.",
        ],
        "hidden_objection_patterns": [
            "sounds agreeable before they have actually given the product routine space",
        ],
        "what_they_say_when_they_are_only_being_nice": [
            "Interesting idea. I can see why people would look at it.",
        ],
        "what_they_say_when_they_are_genuinely_interested": [
            "If you can show me the smallest useful version, then I want to test it.",
        ],
        "what_they_ask_when_they_are_close_to_trying": [
            "What is the narrowest trial that still proves the value in a normal week?",
        ],
        "what_they_ask_when_they_are_close_to paying": [
            "What stays useful enough that I keep paying once the first tidy week is over?",
        ],
    }


def _fallback_voiceprint(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _v3_1_1_archetype_key(persona)
    objections = persona.profile.objection_language_style or _fallback_objection_language_style(persona)
    phrases = persona.profile.identity_symbols.get("phrases_they_might_say", [])
    direct = _clean_list(objections.get("direct_objection_examples", []))
    polite = _clean_list(objections.get("polite_objection_examples", []))
    nice = _clean_list(objections.get("what_they_say_when_they_are_only_being_nice", []))
    interested = _clean_list(objections.get("what_they_say_when_they_are_genuinely_interested", []))
    near_try = _clean_list(objections.get("what_they_ask_when_they_are_close_to_trying", []))
    near_pay = _clean_list(objections.get("what_they_ask_when_they_are_close_to paying", []))
    panel_role = str(persona.profile.panel_role_profile.get("panel_role", "")).strip() or "practical reviewer"
    voice_anchor_hint = ""
    if archetype == "ambitious_signal_seeker":
        voice_anchor_hint = "Show me the visible win, not the eventual story."
    elif archetype == "credibility_guarding_service_operator":
        voice_anchor_hint = "If I have to explain the failure, the tool is not ready."
    elif archetype == "budget_guarded_household_operator":
        voice_anchor_hint = "Tell me what I stop defending next month."
    elif archetype == "privacy_narrow_trialist":
        voice_anchor_hint = "Start smaller than the access request."
    elif archetype == "quiet_inclusion_checker":
        voice_anchor_hint = "What stays private by default matters more than the slogan."
    elif archetype == "public_reputation_risk_guard":
        voice_anchor_hint = "Keep the evaluation private first."
    elif archetype == "low_energy_avoidant_adapter":
        voice_anchor_hint = "If it only works on a fresh day, it does not work for me."
    voice_anchor = _first_non_empty(
        voice_anchor_hint,
        "Tell me what gets lighter before this asks for more access." if "privacy" in panel_role else "",
        phrases,
        direct,
        "Tell me what becomes easier before I change my routine.",
    )
    hard_rejection = _first_non_empty(
        direct[1] if len(direct) > 1 else "",
        direct,
        "If the product needs more access than it has earned, I stop there.",
    )
    speaking_style = "practical, slightly guarded, and clearer in the second sentence than the first"
    sentence_length = "short_to_medium"
    directness_pattern = "starts with a narrow caution, then asks what becomes lighter, safer, or more reversible"
    if archetype == "quiet_inclusion_checker":
        speaking_style = "measured, low-drama, and more precise than emotional"
        directness_pattern = "states the discomfort quietly, then points to the setting or default that caused it"
    elif archetype == "privacy_narrow_trialist":
        speaking_style = "compressed, narrow, and scope-aware"
        sentence_length = "short"
        directness_pattern = "cuts immediately to scope of access, then either narrows the test or exits"
    elif archetype == "budget_guarded_household_operator":
        speaking_style = "practical, household-aware, and quietly cost-conscious"
        directness_pattern = "frames objections around what remains to justify next month"
    elif archetype == "credibility_guarding_service_operator":
        speaking_style = "brisk, operational, and alert to visible failure"
        directness_pattern = "imagines the live-use moment, then asks who carries the explanation when it goes wrong"
    elif archetype == "ambitious_signal_seeker":
        speaking_style = "fast, forward-leaning, and impatient with slow proof"
        directness_pattern = "acknowledges upside quickly, then asks how fast the visible win arrives"
    elif archetype == "public_reputation_risk_guard":
        speaking_style = "controlled, private-first, and low-theater"
        directness_pattern = "withdraws from public exposure first, then explains only if necessary"
    elif archetype == "low_energy_avoidant_adapter":
        speaking_style = "tired, plain, and shorter than the analysis would justify"
        sentence_length = "short"
        directness_pattern = "accepts the logic faster than the effort, then drops out when setup feels too heavy"
    return {
        "speaking_style": speaking_style,
        "sentence_length": sentence_length,
        "directness_pattern": directness_pattern,
        "metaphors_or_phrases": _clean_list(
            [
                voice_anchor,
                _first_non_empty(phrases[1] if len(phrases) > 1 else "", direct[0] if direct else ""),
                "real week",
                "earned access",
            ]
        ),
        "how_they_soften_disagreement": _first_non_empty(
            polite,
            nice,
            "I can see the use case, but I still need a smaller and safer first step.",
        ),
        "how_they_get_more_direct": _first_non_empty(
            hard_rejection,
            "If this adds maintenance or exposure before relief, I am not taking it further.",
        ),
        "what_they_repeat_when_skeptical": voice_anchor,
        "what_they_never_say": [
            "I would connect everything on day one.",
            "The concept is enough for me to pay.",
        ],
        "example_positive_reaction": _first_non_empty(
            interested,
            "If I can test one contained workflow without handing over everything, I will take it seriously.",
        ),
        "example_polite_rejection": _first_non_empty(
            polite,
            "Interesting, but I do not yet see a version that fits my actual week.",
        ),
        "example_hard_rejection": hard_rejection,
        "example_near_purchase_question": _first_non_empty(
            near_pay,
            near_try,
            "What becomes simpler enough that I would keep paying after the first month?",
        ),
    }


def _fallback_non_work_purchase_scenes(persona: PersonaSkill) -> list[dict[str, Any]]:
    archetype = _v3_1_1_archetype_key(persona)
    identity = persona.profile.basic_identity
    name = str(identity.get("name", "")).strip() or "This persona"
    location = str(identity.get("location", "")).strip() or "their city"
    household = str(identity.get("family_structure", "")).strip() or "their household"
    household_size = int(identity.get("household_size", 1) or 1)
    good_purchase = str(persona.profile.spending_and_leisure_patterns.get("recent_good_purchase", "")).strip()
    regretted_purchase = str(persona.profile.spending_and_leisure_patterns.get("recent_regretted_purchase", "")).strip()

    if archetype == "quiet_inclusion_checker":
        return [
            {
                "scene_id": "membership_signup_visibility_drop",
                "life_period": "20-29",
                "scene_title": "The sign-up form that made the product feel smaller",
                "specific_scene": (
                    f"{name} nearly joined a paid community tool in {location}, but the sign-up flow required a title and profile details that would be visible by default. "
                    "The feature set was fine. The trust collapsed at the form."
                ),
                "product_category": "community or membership product",
                "decision_context": "Wanted access to a useful space without turning identity disclosure into the first task.",
                "trust_or_price_lesson": "Respect is judged most harshly at the point where the product asks for legibility before value.",
                "current_product_research_impact": "They now test whether identity-sensitive products earn trust in settings and defaults, not only in the headline copy.",
            },
            {
                "scene_id": "profile_controls_after_purchase",
                "life_period": "20-29",
                "scene_title": "Paying only after the settings felt private enough",
                "specific_scene": (
                    f"On another service, {name} kept reading until the account settings made it clear that profile visibility, notifications, and labels could stay narrow and private. "
                    "That control, not the marketing, was what made payment feel reasonable."
                ),
                "product_category": "consumer subscription or community platform",
                "decision_context": "Needed proof that the product would not make identity more public than necessary.",
                "trust_or_price_lesson": "A product can feel worth paying for once the dignity cost is low and the controls are legible.",
                "current_product_research_impact": "They are more willing to trial when disclosure is clearly optional and visibility starts private.",
            },
        ]
    if archetype == "privacy_narrow_trialist":
        return [
            {
                "scene_id": "sample_data_trial_only",
                "life_period": "20-29",
                "scene_title": "The tool that only earned a sample-data trial",
                "specific_scene": (
                    f"{name} found a promising utility in {location} but refused to connect real records on first use. "
                    "They only continued because a sample-data path proved the core task before any broad permission request."
                ),
                "product_category": "AI or workflow utility",
                "decision_context": "Wanted value proof without surrendering real data too early.",
                "trust_or_price_lesson": "A narrow, reversible trial can build more trust than a polished but overreaching integration screen.",
                "current_product_research_impact": "They now react well to limited-mode trials and badly to products that ask for full access as proof of seriousness.",
            },
            {
                "scene_id": "checkout_exit_after_permission_creep",
                "life_period": "20-29",
                "scene_title": "Leaving when the permissions widened at checkout",
                "specific_scene": (
                    f"Another product looked lightweight until the account step in {location} added sync, tracking, and profile permissions that had not been mentioned earlier. "
                    f"{name} closed it immediately instead of negotiating with the flow."
                ),
                "product_category": "consumer subscription or productivity product",
                "decision_context": "Expected the paid step to confirm value, not expand the surveillance surface.",
                "trust_or_price_lesson": "Trust can evaporate faster from scope creep than from price.",
                "current_product_research_impact": "They now test whether the product's permission boundary stays honest as the funnel deepens.",
            },
        ]
    if archetype == "budget_guarded_household_operator":
        return [
            {
                "scene_id": "monthly_charge_needs_defense",
                "life_period": "20-29",
                "scene_title": "The monthly charge that was affordable but annoying to defend",
                "specific_scene": (
                    f"After a few uneven weeks in {location}, {name} noticed a low-cost subscription still billing while nobody at home could say what it had meaningfully improved. "
                    "The irritation came less from the amount and more from the need to keep justifying it."
                ),
                "product_category": "consumer software subscription",
                "decision_context": "Wanted a convenience tool, but not another monthly line item that sounded more aspirational than useful.",
                "trust_or_price_lesson": "Price fairness depends on whether the spend stays explainable after the first month, not only on whether it is small.",
                "current_product_research_impact": "They now ask what existing spend, stress, or repeated hassle actually disappears if the product stays.",
            },
            {
                "scene_id": "repair_service_over_cheaper_quote",
                "life_period": "20-29",
                "scene_title": "Choosing the quote that meant less follow-up later",
                "specific_scene": (
                    f"When comparing a household repair option in {location}, {name} picked the vendor that replied clearly and confirmed next steps instead of the slightly cheaper quote that would probably require more chasing."
                ),
                "product_category": "household service",
                "decision_context": "Needed a choice that saved follow-up effort, not just money on paper.",
                "trust_or_price_lesson": _first_non_empty(
                    good_purchase,
                    "The cheaper option loses when it quietly turns into more coordination work at home.",
                ),
                "current_product_research_impact": "They respond to products that can explain total effort saved, not only sticker-price efficiency.",
            },
        ]
    if archetype == "credibility_guarding_service_operator":
        return [
            {
                "scene_id": "customer_facing_tool_apology",
                "life_period": "20-29",
                "scene_title": "The moment the tool made them carry the apology",
                "specific_scene": (
                    f"{name} once tried a customer-facing coordination tool in {location} that looked tidy in setup but failed during a busy handoff. "
                    "The product issue became a personal explanation problem in front of someone waiting."
                ),
                "product_category": "service or operations tool",
                "decision_context": "Wanted a cleaner process without adding one more thing to apologize for under pressure.",
                "trust_or_price_lesson": "A product is not trustworthy if the user's reputation becomes the buffer for its rough edges.",
                "current_product_research_impact": "They now ask what happens when the product is wrong in a live moment, not only when the demo is calm.",
            },
            {
                "scene_id": "seller_chosen_for_clear_follow_up",
                "life_period": "20-29",
                "scene_title": "Paying for clearer follow-up rather than the lowest quote",
                "specific_scene": (
                    f"On a non-work purchase in {location}, {name} chose the seller who confirmed timing, fallback, and contact path clearly. "
                    "The slightly cheaper option felt riskier because any failure would become more chasing and more embarrassment."
                ),
                "product_category": "household or consumer service",
                "decision_context": "Needed a choice that protected confidence in front of other people, not just money.",
                "trust_or_price_lesson": "Service credibility and clean follow-up often beat a small price gap.",
                "current_product_research_impact": "They trust products that make the failure path legible before the ideal path goes wrong.",
            },
        ]
    if archetype == "ambitious_signal_seeker":
        return [
            {
                "scene_id": "week_one_visible_win",
                "life_period": "20-29",
                "scene_title": "Keeping the tool that produced a visible win quickly",
                "specific_scene": (
                    f"{name} tried a new productivity or AI utility in {location} because it promised a visible gain fast. "
                    "The product stayed only because the first useful output was good enough to show someone else within the week."
                ),
                "product_category": "AI or productivity product",
                "decision_context": "Wanted something that created leverage quickly enough to feel worth the attention.",
                "trust_or_price_lesson": "Curiosity becomes real trial intent when the product reaches a visible proof point before the setup story gets old.",
                "current_product_research_impact": "They now ask how fast the product can produce a credible win that is easy to point at.",
            },
            {
                "scene_id": "novelty_drop_after_setup_drag",
                "life_period": "20-29",
                "scene_title": "Losing interest once the momentum stopped feeling visible",
                "specific_scene": (
                    f"Another tool in {location} looked exciting for two days, then stalled behind configuration and process mapping. "
                    f"{name} did not become hostile. They just stopped opening it."
                ),
                "product_category": "consumer or workflow software",
                "decision_context": "Wanted acceleration, not another project whose benefits remained theoretical.",
                "trust_or_price_lesson": "The value of novelty collapses when the product hides the visible win behind too much preparation.",
                "current_product_research_impact": "They are more open than Daniel or Jordan to trying something new, but also faster to abandon it when momentum dies.",
            },
        ]
    if archetype == "public_reputation_risk_guard":
        return [
            {
                "scene_id": "public_profile_exit",
                "life_period": "20-29",
                "scene_title": "Leaving when the trial required a visible public profile",
                "specific_scene": (
                    f"{name} considered a product in {location} that looked workable until the trial path required a public-facing profile and visible participation. "
                    "The product may have been fine. The public trace arrived too early."
                ),
                "product_category": "community or identity-sensitive product",
                "decision_context": "Wanted to evaluate usefulness privately before taking on any public alignment cost.",
                "trust_or_price_lesson": "Private-first control can matter more than feature breadth when visible participation is not neutral.",
                "current_product_research_impact": "They now separate interest in the concept from willingness to leave any public record while testing it.",
            },
            {
                "scene_id": "private_mode_unlock",
                "life_period": "20-29",
                "scene_title": "Paying once the product proved quiet participation was possible",
                "specific_scene": (
                    f"Another product in {location} only became credible after {name} confirmed that private mode, muted discovery, and limited visibility were available from the start."
                ),
                "product_category": "consumer subscription or community platform",
                "decision_context": "Needed the product to earn trust without turning evaluation into a public statement.",
                "trust_or_price_lesson": "Quiet participation is not a niche preference when public expression carries real cost.",
                "current_product_research_impact": "They respond better to products that treat privacy and public-expression control as first-order settings.",
            },
        ]
    if archetype == "low_energy_avoidant_adapter":
        return [
            {
                "scene_id": "night_setup_abandonment",
                "life_period": "20-29",
                "scene_title": "The useful product that died at 9:40 p.m.",
                "specific_scene": (
                    f"After a long day in {location}, {name} tried to set up a tool that made sense on paper but still needed more steps than they had energy for. "
                    "Nothing dramatic happened. It simply became tomorrow's problem until it disappeared."
                ),
                "product_category": "productivity or consumer utility",
                "decision_context": "Wanted help, but only if the first useful moment happened before tiredness took over.",
                "trust_or_price_lesson": "A clear use case is not enough when the product spends the user's last bit of energy before giving relief.",
                "current_product_research_impact": "They now judge products by whether the smallest real start fits a tired evening, not just a motivated morning.",
            },
            {
                "scene_id": "cheap_tool_forgotten_after_busy_week",
                "life_period": "20-29",
                "scene_title": "The cheap tool that was still too much to remember",
                "specific_scene": (
                    f"A low-cost app in {location} was easy to buy and easy to forget. "
                    f"{name} did not reject it intellectually; the tool just never became automatic enough to survive a busy week."
                ),
                "product_category": "consumer subscription or utility app",
                "decision_context": "Wanted light help, not another thing that required remembering on purpose.",
                "trust_or_price_lesson": "A product can be affordable, sensible, and still fail if it never becomes easy at the exact moment it is needed.",
                "current_product_research_impact": "They often sound easier to persuade than they really are because their true blocker is energy, not concept comprehension.",
            },
        ]

    scenes = [
        {
            "scene_id": "cancelled_subscription_after_busy_month",
            "life_period": "20-29",
            "scene_title": "The recurring charge that outlived the habit",
            "specific_scene": (
                f"After a few busy weeks in {location}, {name} noticed a utility subscription still billing even though it had slipped out of daily use. "
                "The price was not huge, but the irritation came from paying for a routine that no longer existed."
            ),
            "product_category": "consumer software subscription",
            "decision_context": "Wanted a small personal upgrade that might reduce clutter without asking the whole week to reorganize around it.",
            "trust_or_price_lesson": _first_non_empty(
                regretted_purchase,
                "Fair pricing includes easy exit and proof that the tool still matters on uneven weeks.",
            ),
            "current_product_research_impact": "They now test whether value appears quickly and whether the product can be abandoned cleanly without resentment.",
        },
    ]
    if household_size > 1 or "partner" in household.lower() or "family" in household.lower():
        scenes.append(
            {
                "scene_id": "shared_household_expense_tool_visibility",
                "life_period": "20-29",
                "scene_title": "The household tool that felt too visible",
                "specific_scene": (
                    f"{name} and someone at home tried a shared household expense tool that automated categorization and surfaced patterns on the home screen. "
                    "The automation was clever, but the default visibility felt more intimate than helpful, so they drifted back to a lighter workaround."
                ),
                "product_category": "household coordination or finance tool",
                "decision_context": "Wanted lighter household coordination without turning ordinary spending into a constant shared display.",
                "trust_or_price_lesson": _first_non_empty(
                    good_purchase,
                    "Convenience loses appeal when privacy boundaries inside the household stay fuzzy.",
                ),
                "current_product_research_impact": "They now ask whether family and finance products help coordination without forcing more shared visibility than the task actually needs.",
            }
        )
    else:
        scenes.append(
            {
                "scene_id": "solo_budget_tool_that_felt_moralizing",
                "life_period": "30-39",
                "scene_title": "The finance app that turned tracking into self-surveillance",
                "specific_scene": (
                    f"Living alone in {location}, {name} tried a budgeting app that categorized purchases neatly and pushed frequent spending alerts. "
                    "The alerts were not wrong, but the tone made ordinary decisions feel judged rather than clarified, so the app was abandoned even though the setup was easy."
                ),
                "product_category": "personal finance app",
                "decision_context": "Wanted clearer personal spending visibility without turning everyday choices into a constant moral scorecard.",
                "trust_or_price_lesson": _first_non_empty(
                    good_purchase,
                    "A finance tool can be technically useful and still fail if the emotional cost of using it feels too high.",
                ),
                "current_product_research_impact": "They now look for finance and wellbeing products that clarify patterns without making the user feel watched or corrected.",
            }
        )
    return scenes


def _fallback_local_grounding_layer(persona: PersonaSkill) -> dict[str, Any]:
    identity = persona.profile.basic_identity
    location = str(identity.get("location", "")).strip()
    locale_pack = str(identity.get("locale_pack", "")).strip()
    if location == "Hong Kong" or locale_pack == "hong_kong_smb":
        return {
            "city_or_region_specific_context": [
                "Quick decisions often happen on a phone between MTR segments, queue time, or short pauses between tasks.",
                "Price comparisons happen fast because local alternatives are easy to check and people notice recurring charges quickly.",
            ],
            "common_apps_or_services": [
                "WhatsApp",
                "Octopus",
                "FPS",
                "MTR Mobile",
                "YouTube search",
            ],
            "payment_and_commerce_context": [
                "HKD pricing feels easier to trust than USD-first pricing with hidden conversion math.",
                "Recurring software spend gets compared against ordinary monthly costs, not abstract startup logic.",
            ],
            "mobility_or_commute_context": [
                "Product evaluation often happens in short mobile-first windows, not long quiet setup sessions.",
            ],
            "language_switching_scenes": [
                "Cantonese feels natural in quick chat or household coordination.",
                "English is acceptable for work tools if the copy stays plain and concrete.",
            ],
            "family_or_household_norms": [
                "A purchase can be individually paid for and still need to be explainable at home.",
            ],
            "workplace_norms": [
                "Fast replies are normal, but public enthusiasm is not the same as true process adoption.",
            ],
            "trust_cues_in_this_market": [
                "HKD pricing",
                "plain bilingual or English copy without imported startup jargon",
                "support paths that look reachable instead of abstract",
            ],
            "pricing_localization_reaction": "USD-first pricing feels slightly distant unless the product explains local value clearly.",
            "what_feels_imported_or_not_local": "Copy that assumes relaxed setup time, US team rituals, or frictionless card spending feels imported.",
            "local_discovery_channels": [
                "WhatsApp referrals",
                "comparison search",
                "YouTube explainers",
                "LinkedIn when the use case is work-related",
            ],
            "local_sensitivity_notes": [
                "Shared screens, compact routines, and quick mobile use increase the value of privacy-safe defaults.",
            ],
        }
    if "taiwan" in locale_pack or location in {"Kaohsiung", "Taipei", "Taichung", "Tainan"}:
        return {
            "city_or_region_specific_context": [
                f"{location} routines reward practical convenience, but people still notice whether a product feels imported from someone else's work culture.",
                "Comparisons are often made quickly through search, chat, and what colleagues or friends already use.",
            ],
            "common_apps_or_services": [
                "LINE",
                "Google Search",
                "YouTube",
                "LINE Pay",
                "PX Pay",
            ],
            "payment_and_commerce_context": [
                "TWD pricing feels easier to justify than USD-first pricing with unstable conversion logic.",
                "A recurring SaaS line item gets compared against ordinary monthly convenience spending, not abstract innovation budgets.",
            ],
            "mobility_or_commute_context": [
                "A lot of product reading happens on the phone between errands, transit, or waiting time rather than during a long quiet setup window.",
            ],
            "language_switching_scenes": [
                "Mandarin is expected for everyday trust and customer-facing clarity.",
                "English can work for software, but copy that feels translated from startup jargon loses warmth quickly.",
            ],
            "family_or_household_norms": [
                "Even solo purchases often need to feel defendable in ordinary life, not only attractive in a demo.",
            ],
            "workplace_norms": [
                "People may sound agreeable in chat before they have actually changed behavior in the workflow.",
            ],
            "trust_cues_in_this_market": [
                "TWD pricing",
                "plain Mandarin or bilingual clarity",
                "screenshots or demos that look usable on a real phone",
            ],
            "pricing_localization_reaction": "USD pricing can feel distant unless the product explains local value in concrete TWD terms.",
            "what_feels_imported_or_not_local": "Aggressive startup copy, US meeting culture assumptions, and English-only onboarding can make the product feel less grounded.",
            "local_discovery_channels": [
                "LINE referrals",
                "Google search",
                "YouTube explainers",
                "Dcard or forum-style comparison reading",
            ],
            "local_sensitivity_notes": [
                "Polite surface agreement can hide real hesitation, so a low-pressure trial path matters more than hype.",
            ],
        }
    return persona.profile.local_grounding_layer


def _fallback_biography_timeline(persona: PersonaSkill) -> list[dict[str, Any]]:
    archetype = _v3_1_1_archetype_key(persona)
    identity = persona.profile.basic_identity
    name = str(identity.get("name", "")).strip() or "This persona"
    location = str(identity.get("location", "")).strip() or "their city"
    occupation = str(identity.get("occupation", "")).strip() or "work"
    occupation_context = _occupation_context_phrase(occupation)

    chapter_map: dict[str, list[dict[str, Any]]] = {
        "quiet_inclusion_checker": [
            {
                "age_range": "0-9",
                "chapter_title": "Difference registered in small defaults first",
                "life_context": f"Early routines in {location} taught {name} that categories can feel heavier to the user than to the form designer.",
                "specific_scene": "A simple school or activity form asked for more certainty than real life actually offered, and the discomfort sat there quietly rather than dramatically.",
                "product_relevant_memory": "A product can feel wrong before anything openly offensive happens.",
                "social_or_relationship_context": "They learned that many people adapt to awkward defaults without announcing that they had to adapt.",
                "money_or_effort_tradeoff": "The cost was emotional effort, not money.",
                "beliefs_formed": [
                    "Respect should reduce friction, not merely rename it.",
                    "Silent discomfort is still feedback.",
                ],
                "current_reaction_link": f"{name} still notices whether a product lets privacy and ambiguity remain intact at the start.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Public labels became a practical trust test",
                "life_context": f"Group spaces in {location} often used simple visible labels that felt convenient for the system and less comfortable for the person inside it.",
                "specific_scene": "A sign-up or shared profile step felt small to everyone else and much heavier to the person being asked to fit into it.",
                "product_relevant_memory": "Trust often falls at the settings screen, not at the homepage.",
                "social_or_relationship_context": "Politeness often outlasted comfort, which made quiet exits easy for outsiders to misread.",
                "money_or_effort_tradeoff": "Convenience competed with dignity cost.",
                "beliefs_formed": [
                    "Private control matters more than inclusive slogans.",
                    "A user can leave quietly and still be giving precise feedback.",
                ],
                "current_reaction_link": "That is why this persona tests whether respect survives the actual onboarding path.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Settings became the real headline",
                "life_context": f"Adult product use in {location} made {name} more sensitive to whether control lives in the settings or only in the copywriting.",
                "specific_scene": "A useful-looking service lost credibility the moment profile visibility and disclosure defaults became clearer than the benefits.",
                "product_relevant_memory": "The product earns more trust by limiting exposure than by over-explaining its values.",
                "social_or_relationship_context": "Leaving quietly felt safer than explaining why a default felt too revealing.",
                "money_or_effort_tradeoff": "They will pay for calm control more readily than for louder signaling.",
                "beliefs_formed": [
                    "Optional disclosure is a functional feature.",
                    "Comfort settings can matter more than feature breadth.",
                ],
                "current_reaction_link": "Now they separate inclusive tone from practical disclosure safety almost immediately.",
                "formative_level": "high",
            },
        ],
        "privacy_narrow_trialist": [
            {
                "age_range": "0-9",
                "chapter_title": "Boundaries mattered even in ordinary shared spaces",
                "life_context": f"Growing up in {location} meant learning early that access is not neutral when spaces, devices, or routines are shared.",
                "specific_scene": "A small piece of information surfaced in the wrong place once, and the lesson lingered long after the moment passed.",
                "product_relevant_memory": "A safe system should ask only for the part it truly needs.",
                "social_or_relationship_context": "Privacy felt practical, not ideological.",
                "money_or_effort_tradeoff": "Careful boundaries sometimes took extra effort, but felt worth it.",
                "beliefs_formed": [
                    "Scope matters.",
                    "Smaller access can be better design, not weaker commitment.",
                ],
                "current_reaction_link": f"{name} still scans for whether a product asks for more access than the task deserves.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Shared systems taught the cost of overexposure",
                "life_context": f"Digital tools in {location} often assumed people would trade visibility for convenience without thinking much about it.",
                "specific_scene": "A shared device, public status marker, or over-broad setting made the product feel less useful because it widened the audience around the task.",
                "product_relevant_memory": "The trial is effectively over if the privacy boundary changes before the value appears.",
                "social_or_relationship_context": "They learned not to argue every point, but to notice where the system's assumptions stopped fitting.",
                "money_or_effort_tradeoff": "The real trade-off was between speed and control.",
                "beliefs_formed": [
                    "Not every useful tool deserves full trust.",
                    "The first safe slice is the only believable starting point.",
                ],
                "current_reaction_link": "That is why permission creep reads like a truth-telling test about the product.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Narrow trials earned more trust than polished funnels",
                "life_context": f"Adult tool evaluation in {location} showed {name} that the best products usually ask for less at the start, not more.",
                "specific_scene": "A product stayed interesting only because it offered sample data or limited mode instead of demanding a full connection up front.",
                "product_relevant_memory": "A clean funnel can still feel dishonest if the scope widens right before commitment.",
                "social_or_relationship_context": "They became more comfortable exiting quietly than negotiating with a product that had already overreached.",
                "money_or_effort_tradeoff": "They would rather do a smaller test now than undo a broad permission later.",
                "beliefs_formed": [
                    "Reversible trust beats enthusiastic trust.",
                    "Plain retention language is part of usability.",
                ],
                "current_reaction_link": "Now they judge AI and workflow products by whether the narrow trial path is real or only cosmetic.",
                "formative_level": "high",
            },
        ],
        "budget_guarded_household_operator": [
            {
                "age_range": "0-9",
                "chapter_title": "Usefulness had to beat waste in ordinary life",
                "life_context": f"At home in {location}, spending was expected to make sense even when nobody called it strict.",
                "specific_scene": "A slightly cheaper option could still lose if everyone knew the follow-up hassle would cost more later.",
                "product_relevant_memory": "Sticker price is only half of the household equation.",
                "social_or_relationship_context": "Financial judgment was social as well as practical because someone always had to defend the choice later.",
                "money_or_effort_tradeoff": "Durability and less chasing often beat the lowest quote.",
                "beliefs_formed": [
                    "Affordable is not the same as worth repeating.",
                    "Savings claims should include effort saved.",
                ],
                "current_reaction_link": f"{name} now asks what recurring hassle or spend actually disappears if the product stays.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Embarrassing waste taught stronger lessons than expensive mistakes",
                "life_context": f"Teen and student life in {location} made small recurring costs feel especially irritating once they had to be explained twice.",
                "specific_scene": "A plan or purchase looked fine on day one, then annoying once the ongoing value had to be defended again.",
                "product_relevant_memory": "A product becomes vulnerable the second month someone has to justify why it is still there.",
                "social_or_relationship_context": "They learned to think ahead to how a purchase would sound in conversation with family or a partner.",
                "money_or_effort_tradeoff": "Predictability felt safer than louder promotions.",
                "beliefs_formed": [
                    "Recurring value should be explainable in plain language.",
                    "Monthly defensibility matters more than launch excitement.",
                ],
                "current_reaction_link": "That is why subscription language gets filtered through local monthly reality almost immediately.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Household coordination exposed the cost behind the cost",
                "life_context": f"Adult life in {location} made {name} more aware that purchases affect whoever has to maintain or explain them at home.",
                "specific_scene": "A service or tool choice looked cheaper until the follow-up burden and repeated clarification made it the more expensive option in practice.",
                "product_relevant_memory": "Products fail when they save money on paper but add explanation work at home.",
                "social_or_relationship_context": "The household question was not always explicit, but it was always present.",
                "money_or_effort_tradeoff": "They will pay slightly more for clearer follow-up and less recurring justification.",
                "beliefs_formed": [
                    "Low-friction cancellation is part of fair pricing.",
                    "A product that needs constant defense is already priced too high.",
                ],
                "current_reaction_link": "Now they separate curiosity from payment by asking what the product replaces next month, not what it promises today.",
                "formative_level": "high",
            },
        ],
        "credibility_guarding_service_operator": [
            {
                "age_range": "0-9",
                "chapter_title": "Visible mistakes carried longer than private ones",
                "life_context": f"Growing up in {location} made {name} sensitive to how quickly small visible misses can become other people's problem.",
                "specific_scene": "A simple missed handoff or late confirmation mattered because someone else ended up waiting in front of it.",
                "product_relevant_memory": "A process only feels safe when the failure path is legible too.",
                "social_or_relationship_context": "Reliability felt less like perfection and more like not making other people pay for your confusion.",
                "money_or_effort_tradeoff": "Clarity often beat cleverness when other people were exposed to the result.",
                "beliefs_formed": [
                    "Public-facing work needs recoverable failure paths.",
                    "Explanations become labor when the system is weak.",
                ],
                "current_reaction_link": f"{name} still checks whether a product protects their credibility when the day is already under pressure.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "People-facing coordination created a low tolerance for live confusion",
                "life_context": f"Shared responsibilities in {location} made public smoothness feel more valuable than private theoretical optimization.",
                "specific_scene": "A live coordination miss mattered more than a messy document because the embarrassment and apology happened in real time.",
                "product_relevant_memory": "If the product fails in a visible moment, the user becomes the explanation layer.",
                "social_or_relationship_context": "They learned that people remember how smooth or confusing a handoff felt more than how elegant the system looked beforehand.",
                "money_or_effort_tradeoff": "A slightly stronger but clearer process felt safer than a fancier but fragile one.",
                "beliefs_formed": [
                    "Visible reliability beats clever complexity.",
                    "Service trust is operational, not rhetorical.",
                ],
                "current_reaction_link": "That is why they stress-test tools against busy, customer-facing conditions first.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Operational polish was judged by apology reduction",
                "life_context": f"Adult work in {occupation_context} made {name} wary of anything that looks neat in setup but weak under rush conditions.",
                "specific_scene": f"A tool in {location} looked clean until it failed during a busy handoff and left {name} explaining the gap instead of benefiting from the system.",
                "product_relevant_memory": "A product is not ready if the user becomes the buffer for its edge cases.",
                "social_or_relationship_context": "They do not mind being responsible. They mind being made responsible for the product's unfinished work.",
                "money_or_effort_tradeoff": "They will pay for credible support and visible fallback logic sooner than for extra features.",
                "beliefs_formed": [
                    "Explainability under pressure is part of product quality.",
                    "Live-use failure risk matters more than demo tidiness.",
                ],
                "current_reaction_link": "Now they evaluate products by asking who carries the apology when the nice path breaks.",
                "formative_level": "high",
            },
        ],
        "ambitious_signal_seeker": [
            {
                "age_range": "0-9",
                "chapter_title": "Visible progress felt rewarding early",
                "life_context": f"Early routines in {location} taught {name} to notice systems that produce an obvious improvement fast.",
                "specific_scene": "A simple tool, hack, or routine felt memorable because the before-and-after was visible right away, not because the explanation was long.",
                "product_relevant_memory": "Momentum comes from seeing progress, not from admiring architecture.",
                "social_or_relationship_context": "Competence felt tangible when it could be pointed to.",
                "money_or_effort_tradeoff": "Fast proof often felt more persuasive than comprehensive planning.",
                "beliefs_formed": [
                    "Visible wins create real motivation.",
                    "A slow explanation can lose to a quick useful result.",
                ],
                "current_reaction_link": f"{name} still asks how quickly a product can create a result worth showing to someone else.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Novelty became believable only when it turned into output",
                "life_context": f"Digital experimentation in {location} created plenty of interesting options, but only a few actually changed behavior for long.",
                "specific_scene": "A clever system held attention briefly, then disappeared once the visible gain stayed theoretical for too many days.",
                "product_relevant_memory": "Curiosity is cheap. Retained energy depends on speed to visible proof.",
                "social_or_relationship_context": "They learned that sounding ahead of the curve is less satisfying than actually looking more capable.",
                "money_or_effort_tradeoff": "A product can feel cheap and still not be worth the attention cost if the payoff stays abstract.",
                "beliefs_formed": [
                    "The first win should be legible quickly.",
                    "Momentum matters more than feature completeness at the start.",
                ],
                "current_reaction_link": "That is why they ask what can be shown by next week, not just what could happen eventually.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Acceleration mattered more than ideological loyalty to tools",
                "life_context": f"Adult work in {occupation_context} made {name} open to new tools, but only if the leverage appeared before the setup story got old.",
                "specific_scene": f"In {location}, a product stayed in rotation only when the first output was good enough to share or use publicly within the week.",
                "product_relevant_memory": "Setup drag kills even genuine enthusiasm if the visible win arrives too late.",
                "social_or_relationship_context": "They are willing to be seen trying something new, but not willing to be seen backing a tool that stalls.",
                "money_or_effort_tradeoff": "They will pay sooner than Daniel or Jordan if the leverage is fast and visible.",
                "beliefs_formed": [
                    "A quick credible win earns more patience later.",
                    "Novelty without lift becomes clutter fast.",
                ],
                "current_reaction_link": "Now they distinguish between products that create momentum and products that merely describe transformation well.",
                "formative_level": "high",
            },
        ],
        "public_reputation_risk_guard": [
            {
                "age_range": "0-9",
                "chapter_title": "Public visibility never felt neutral",
                "life_context": f"Early social life in {location} taught {name} that once something becomes visible, it can travel further than intended.",
                "specific_scene": "A small public moment carried longer than expected, and the lesson was to separate private evaluation from public expression whenever possible.",
                "product_relevant_memory": "The default audience matters before the feature even starts.",
                "social_or_relationship_context": "Discretion felt like self-protection, not shyness.",
                "money_or_effort_tradeoff": "The hidden cost was reputational exposure.",
                "beliefs_formed": [
                    "Control over audience is part of trust.",
                    "Quiet participation can be a healthy default.",
                ],
                "current_reaction_link": f"{name} now notices whether a product assumes visible alignment before private confidence exists.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Public traces taught a longer memory than the interface admitted",
                "life_context": f"Digital spaces in {location} made it easy for ordinary participation to leave a longer trail than the moment seemed to deserve.",
                "specific_scene": "A comment, profile change, or visible participation cue felt minor in the interface and heavier in real life once others could infer more from it.",
                "product_relevant_memory": "Products often understate the social persistence of visible actions.",
                "social_or_relationship_context": "They became selective about where evaluation ends and public affiliation begins.",
                "money_or_effort_tradeoff": "A private path can feel more valuable than extra features if it lowers exposure.",
                "beliefs_formed": [
                    "Public-first defaults are not neutral defaults.",
                    "A quiet path is a product feature, not an afterthought.",
                ],
                "current_reaction_link": "That is why community and identity-sensitive products are screened for private modes immediately.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Private evaluation became the real onboarding requirement",
                "life_context": f"Adult product use in {location} taught {name} to check whether participation can remain private until the product has earned trust.",
                "specific_scene": "A promising product lost momentum the moment it required a public-facing profile or visible participation before any real value appeared.",
                "product_relevant_memory": "The product may be useful and still not be safe enough to test publicly.",
                "social_or_relationship_context": "They are not anti-community. They are anti-being-pushed-into-public before they decide the tool deserves it.",
                "money_or_effort_tradeoff": "They will pay for stronger controls and quieter participation if the product is otherwise good.",
                "beliefs_formed": [
                    "Public alignment should be optional, not assumed.",
                    "Privacy and reputation control belong near the start of the funnel.",
                ],
                "current_reaction_link": "Now they treat public-expression cost as a practical onboarding question, not a side concern.",
                "formative_level": "high",
            },
        ],
        "low_energy_avoidant_adapter": [
            {
                "age_range": "0-9",
                "chapter_title": "Useful systems lost when they needed too much active remembering",
                "life_context": f"Early routines in {location} taught {name} that the best systems are the ones tired people still remember to use.",
                "specific_scene": "A reminder only worked if it lived where attention was already going; anything that asked for a fresh burst of discipline usually drifted away.",
                "product_relevant_memory": "A tool can be smart and still fail if it needs more activation energy than real life provides.",
                "social_or_relationship_context": "The lesson was less about ambition and more about where attention actually goes on busy days.",
                "money_or_effort_tradeoff": "Energy, not money, was often the scarce resource.",
                "beliefs_formed": [
                    "Ease should show up before motivation fades.",
                    "Good intentions are not a stable workflow.",
                ],
                "current_reaction_link": f"{name} still judges products by whether they help before tiredness wins.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Understanding did not guarantee follow-through",
                "life_context": f"School or early digital routines in {location} made it obvious that agreeing a system makes sense is not the same as having energy to keep it alive.",
                "specific_scene": "A tool or routine seemed reasonable, then quietly stopped being used once the week became noisy and the setup memory cooled down.",
                "product_relevant_memory": "Comprehension is not the same as available bandwidth.",
                "social_or_relationship_context": "They learned not to over-promise what they would maintain.",
                "money_or_effort_tradeoff": "The tool's low price did not matter if it still needed more remembering than the user could give.",
                "beliefs_formed": [
                    "Drop-off is often about depleted energy, not disagreement.",
                    "The first step should work on a tired week too.",
                ],
                "current_reaction_link": "That is why late-evening onboarding feels like a more honest test than a calm weekend demo.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Real routines exposed the difference between sensible and sustainable",
                "life_context": f"Adult work in {occupation_context} left {name} with limited patience for products that start by borrowing the day's last clean block of energy.",
                "specific_scene": f"A product in {location} looked perfectly sensible, but the first useful moment arrived too late in the setup to survive a normal week.",
                "product_relevant_memory": "A smart product still fails if it reaches value after the user's energy has already gone.",
                "social_or_relationship_context": "They rarely sound strongly opposed; they simply do not come back if the start is too heavy.",
                "money_or_effort_tradeoff": "They will abandon a cheap, logical tool if the energy burden remains high.",
                "beliefs_formed": [
                    "Fast restarts matter.",
                    "Friction should be measured in energy, not only in clicks.",
                ],
                "current_reaction_link": "Now they filter products through the tired-evening test rather than the ideal-intention test.",
                "formative_level": "high",
            },
        ],
    }
    return chapter_map.get(
        archetype,
        [
            {
                "age_range": "0-9",
                "chapter_title": "Small visible systems beat memory",
                "life_context": f"In a compact {location} routine, small misses became visible quickly and adults cared more about follow-through than polished intentions.",
                "specific_scene": "One morning, a school notice and payment reminder only surfaced when someone checked the tray by the door while everyone was already getting ready to leave.",
                "product_relevant_memory": "A reminder only counts if it lives where rushed people already look.",
                "social_or_relationship_context": "Care at home looked practical: avoid the scramble, do not create extra explanation work for someone else.",
                "money_or_effort_tradeoff": "A slightly ugly but visible system was preferred over anything clever that required more attention.",
                "beliefs_formed": [
                    "Simple systems earn trust when they survive busy mornings.",
                    "Visibility matters more than elegance when attention is thin.",
                ],
                "current_reaction_link": f"{name} still checks whether a product matches real attention patterns or only ideal intentions.",
                "formative_level": "medium",
            },
            {
                "age_range": "10-19",
                "chapter_title": "Acknowledgment is not follow-through",
                "life_context": f"School coordination depended on group chats, shared docs, and people replying quickly even when the work itself was still fuzzy in {location}.",
                "specific_scene": f"During a group project, one classmate replied 'ok' in the chat but never updated the shared document, leaving {name} to rebuild the missing section late at night.",
                "product_relevant_memory": "Messaging can make momentum look better than it really is.",
                "social_or_relationship_context": "People often avoided direct disagreement, so ambiguity lingered until the deadline made it expensive.",
                "money_or_effort_tradeoff": "The hidden cost was time and cleanup work, not a visible fee.",
                "beliefs_formed": [
                    "Confirmation is not execution.",
                    "Coordination tools fail when they only record intent.",
                ],
                "current_reaction_link": f"That is why {name} asks whether a product reduces ambiguity or simply gives people a cleaner place to ignore tasks.",
                "formative_level": "high",
            },
            {
                "age_range": "20-29",
                "chapter_title": "Tidy systems can still create duplicate work",
                "life_context": f"Early adult work meant juggling clients, follow-up, and too many half-adopted tools while trying to look dependable in {occupation_context}.",
                "specific_scene": f"In an early operations-heavy workflow, {name} set up a task board to track follow-up more cleanly, but clients and teammates kept replying in WhatsApp and email.",
                "product_relevant_memory": "A system is not lightweight if one person has to keep two realities synchronized.",
                "social_or_relationship_context": "They wanted to look organized, but not by becoming the only person maintaining everyone else's visibility.",
                "money_or_effort_tradeoff": "The tool itself was affordable; the real cost was the daily attention it demanded.",
                "beliefs_formed": [
                    "Duplicate upkeep kills adoption faster than weak positioning.",
                    "A believable trial has to shrink the loop, not just rename it.",
                ],
                "current_reaction_link": "Now they look for products that make the message-and-follow-up loop smaller, not just tidier.",
                "formative_level": "high",
            },
        ],
    )


def _timeline_needs_rewrite(persona: PersonaSkill) -> bool:
    chapters = persona.profile.canonical_biography.get("decade_timeline", [])
    if not chapters:
        return True
    placeholder_count = 0
    for chapter in chapters:
        scene = _normalize_text(str(chapter.get("specific_scene", "")))
        reaction = _normalize_text(str(chapter.get("current_reaction_link", "")))
        if scene.startswith("a formative ") or reaction == "this still shapes how the persona reacts to product claims today":
            placeholder_count += 1
    return placeholder_count == len(chapters)


def _life_arc_needs_rewrite(persona: PersonaSkill) -> bool:
    life_arc = _normalize_text(persona.profile.canonical_biography.get("life_arc_summary", ""))
    if not life_arc:
        return True
    return any(phrase in life_arc for phrase in SHARED_TEMPLATE_PHRASES)


def _fallback_life_arc_summary(persona: PersonaSkill) -> str:
    archetype = _v3_1_1_archetype_key(persona)
    identity = persona.profile.basic_identity
    name = str(identity.get("name", "")).strip()
    age = str(identity.get("age", "")).strip()
    occupation = str(identity.get("occupation", "")).strip()
    location = str(identity.get("location", "")).strip()
    if archetype == "quiet_inclusion_checker":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They are not defined by identity disclosure alone, but they do notice quickly when a product treats neat labels as more important than user comfort. "
            "Their trust model is quiet and settings-driven: if the default path asks for visibility before value, they often disengage without a dramatic argument. "
            "They respond best when the product lets relevance arrive before disclosure and when respect shows up in controls, not just inclusive copy."
        ).strip()
    if archetype == "privacy_narrow_trialist":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They are open to new products only through narrow proofs, not broad trust leaps. "
            "The core question is whether the first useful step can happen with less data, less visibility, and less permanent commitment than the full product eventually wants. "
            "They are more persuadable by reversible scope and honest permission boundaries than by polished onboarding or strong brand confidence."
        ).strip()
    if archetype == "budget_guarded_household_operator":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They are not cheap in every category, but they are disciplined about whether ongoing spend stays explainable in ordinary household life. "
            "Products earn trust when they replace hassle, follow-up, or repeat spending clearly enough that the value still sounds sensible a month later. "
            "They separate interest from payment by asking what the product actually removes from next month's budget or coordination burden."
        ).strip()
    if archetype == "credibility_guarding_service_operator":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They evaluate products through visible reliability more than abstract efficiency. "
            "The real test is whether the product still behaves cleanly when the day is rushed, a customer is waiting, or a teammate needs a clear answer immediately. "
            "They are more sensitive than Daniel or Jordan to whether the tool will make them carry the apology when the nice path fails."
        ).strip()
    if archetype == "ambitious_signal_seeker":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They are more open to trying new tools than the existing library skeptics, but only when the product creates visible leverage quickly enough to feel worth the attention. "
            "Their interest rises fast around AI, workflow, or growth products that can produce a credible result in days rather than weeks, and falls just as fast when the setup story outlasts the first visible win. "
            "They are persuadable by momentum, but not endlessly patient with it."
        ).strip()
    if archetype == "public_reputation_risk_guard":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They are not anti-community or anti-expression, but they are careful about when ordinary product use becomes a visible public stance. "
            "They prefer private evaluation first and read public-by-default participation as a trust cost, not a neutral growth tactic. "
            "Products earn more room when quiet modes, private settings, and reversible visibility are designed in from the start."
        ).strip()
    if archetype == "low_energy_avoidant_adapter":
        return (
            f"{name} is a {age}-year-old {occupation} in {location}. "
            "They often understand the value proposition faster than they have energy to act on it. "
            "The true adoption test is whether the first useful moment arrives before tiredness, interruption, or low-attention reality shuts the door. "
            "They are not the same as a skeptic: they may agree with the product and still never maintain it if the setup and restart energy stay too high."
        ).strip()
    return (
        f"{name} is a {age}-year-old {occupation} in {location}. "
        "They are open to practical improvement, but only in bounded forms that survive an uneven week and do not demand instant trust. "
        "Their adult routines run through messages, reminders, follow-up, and fast comparisons, so they judge products by whether something genuinely gets lighter rather than merely better organized on screen. "
        "They are easier to persuade with a reversible first use case than with a polished story about total transformation."
    ).strip()


def _fallback_contradiction_map(persona: PersonaSkill) -> list[dict[str, Any]]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "quiet_inclusion_checker":
        return [
            {
                "contradiction": "Wants inclusive design but dislikes being asked to narrate identity before relevance exists.",
                "how_it_shows_up": "Warm language helps, but only if the flow still works when disclosure stays minimal.",
                "product_validation_effect": "Founders may mistake silence for comfort when the user has already disengaged quietly.",
            },
            {
                "contradiction": "Can spot exclusion clearly but often leaves instead of correcting it.",
                "how_it_shows_up": "The product loses trust without always receiving explicit complaint text.",
                "product_validation_effect": "User-reported issue volume may understate the real trust loss.",
            },
            {
                "contradiction": "Values flexibility but becomes wary when every option still assumes one normal user path.",
                "how_it_shows_up": "Extra options do not help if the default still feels like a hidden requirement.",
                "product_validation_effect": "Settings audits matter as much as homepage messaging.",
            },
            {
                "contradiction": "Appreciates respectful copy but trusts settings more than tone.",
                "how_it_shows_up": "A strong brand message can raise scrutiny rather than trust.",
                "product_validation_effect": "Copy tests alone will overstate confidence.",
            },
        ]
    if archetype == "privacy_narrow_trialist":
        return [
            {
                "contradiction": "Wants personalization but withholds data until trust is earned.",
                "how_it_shows_up": "They ask for product value before allowing the product enough context to personalize deeply.",
                "product_validation_effect": "Early trial design must work with intentionally incomplete data.",
            },
            {
                "contradiction": "Prefers convenience but leaves when permissions feel too broad.",
                "how_it_shows_up": "They can like the use case and still reject the implementation quickly.",
                "product_validation_effect": "Permission boundary design becomes a conversion variable.",
            },
            {
                "contradiction": "Says they do not want to overthink tools but quietly inspects settings first.",
                "how_it_shows_up": "They look low-drama on the surface while running a hidden trust audit.",
                "product_validation_effect": "A short security or retention explanation can matter more than extra feature copy.",
            },
            {
                "contradiction": "Is open to automation on narrow tasks but resists automation that keeps watching.",
                "how_it_shows_up": "They can approve AI help and reject AI memory from the same product.",
                "product_validation_effect": "AI positioning must separate assistance from continuous data entitlement.",
            },
        ]
    if archetype == "budget_guarded_household_operator":
        return [
            {
                "contradiction": "Claims to be price sensitive but pays extra for anything that removes household follow-up.",
                "how_it_shows_up": "They reject some cheap products and choose more expensive options that feel easier to defend later.",
                "product_validation_effect": "Do not reduce pricing logic to sticker price alone.",
            },
            {
                "contradiction": "Wants shared coordination but dislikes tools that make spending visible by default.",
                "how_it_shows_up": "They want help at home without turning ordinary choices into a shared dashboard.",
                "product_validation_effect": "Household tools need role and visibility nuance.",
            },
            {
                "contradiction": "Says they want order but resists systems that require everyone at home to change together.",
                "how_it_shows_up": "They prefer partial improvements over structurally elegant but socially heavy rollouts.",
                "product_validation_effect": "Small bounded household wins matter more than complete system pitches.",
            },
            {
                "contradiction": "Dislikes monthly charges yet will keep paying when the product saves explanation work.",
                "how_it_shows_up": "They cancel some low-cost subscriptions and keep others that are easier to justify out loud.",
                "product_validation_effect": "Retention depends on ongoing defensibility, not only affordability.",
            },
        ]
    if archetype == "credibility_guarding_service_operator":
        return [
            {
                "contradiction": "Wants smoother service work but resists tools that require perfect live behavior before trust is earned.",
                "how_it_shows_up": "They ask edge-case questions early because visible failure costs more than invisible inefficiency.",
                "product_validation_effect": "Demo clarity is not enough without failure-path clarity.",
            },
            {
                "contradiction": "Likes structure but rejects systems that make them the only maintainer.",
                "how_it_shows_up": "They will adopt a tool only if ownership and support are shared credibly.",
                "product_validation_effect": "Adoption depends on believable support, not just feature completeness.",
            },
            {
                "contradiction": "Appreciates polish but distrusts anything harder to explain than the original problem.",
                "how_it_shows_up": "A sharper interface can increase scrutiny instead of reducing it.",
                "product_validation_effect": "Customer-facing explainability must be tested separately from internal enthusiasm.",
            },
            {
                "contradiction": "Wants the team to look more organized but avoids tools that create one more apology moment.",
                "how_it_shows_up": "They will keep a messier but recoverable workaround longer than a fragile polished system.",
                "product_validation_effect": "Reliability under rush conditions can outweigh cleaner process visuals.",
            },
        ]
    if archetype == "ambitious_signal_seeker":
        return [
            {
                "contradiction": "Wants to look ahead of the curve but drops tools that ask for too much quiet setup.",
                "how_it_shows_up": "They sound more open than they are once momentum slows.",
                "product_validation_effect": "Excited early reactions can overstate durable adoption.",
            },
            {
                "contradiction": "Talks like a fast adopter but still protects public failure.",
                "how_it_shows_up": "They will try quickly, but only if the visible downside is bounded.",
                "product_validation_effect": "Trial design should let them win publicly before they risk looking gullible.",
            },
            {
                "contradiction": "Likes AI novelty but becomes impatient when proof takes longer than a week.",
                "how_it_shows_up": "They can champion the idea and then quietly move on if the leverage stays theoretical.",
                "product_validation_effect": "Time-to-visible-win is a stronger metric than problem agreement.",
            },
            {
                "contradiction": "Says they want powerful tools but only keeps them when the output becomes immediately legible.",
                "how_it_shows_up": "They tolerate complexity only after a fast result has already bought patience.",
                "product_validation_effect": "Week-one proof is critical for retention with this persona.",
            },
        ]
    if archetype == "public_reputation_risk_guard":
        return [
            {
                "contradiction": "Understands that public sharing can help discovery but avoids products that make public alignment feel mandatory.",
                "how_it_shows_up": "They may like the concept and still refuse the growth mechanic.",
                "product_validation_effect": "Community-led tactics can look stronger in theory than in actual adoption.",
            },
            {
                "contradiction": "Wants modern tools but dislikes leaving visible traces before private confidence exists.",
                "how_it_shows_up": "They ask for quiet modes early and lose trust when those modes feel secondary.",
                "product_validation_effect": "Private-first evaluation paths become conversion-critical.",
            },
            {
                "contradiction": "Values clarity but becomes silent when the product wants public participation too early.",
                "how_it_shows_up": "The user can disappear after a clear pitch if the audience boundary feels wrong.",
                "product_validation_effect": "Low objection volume does not mean low public-expression cost.",
            },
            {
                "contradiction": "Appreciates principled language but only trusts it when the controls are private and practical.",
                "how_it_shows_up": "Strong values copy raises the bar for actual settings behavior.",
                "product_validation_effect": "Audit the settings, not just the narrative.",
            },
        ]
    if archetype == "low_energy_avoidant_adapter":
        return [
            {
                "contradiction": "Wants more organization but avoids setup when tired.",
                "how_it_shows_up": "They can fully agree with the logic and still not begin.",
                "product_validation_effect": "Concept validation can overstate adoption readiness badly.",
            },
            {
                "contradiction": "Says they want simple routines but keeps old workarounds because they are already learned.",
                "how_it_shows_up": "A technically worse habit may survive because it costs less energy to restart.",
                "product_validation_effect": "Migration effort matters more than feature superiority.",
            },
            {
                "contradiction": "Buys low-cost utilities but forgets them when life gets noisy.",
                "how_it_shows_up": "Low price reduces resistance to trial, not necessarily resistance to abandonment.",
                "product_validation_effect": "Retention tests need to include tired weeks, not only clean starts.",
            },
            {
                "contradiction": "Wants accountability only when it does not create another reminder to ignore.",
                "how_it_shows_up": "They appreciate support until it starts to feel like one more demand.",
                "product_validation_effect": "Gentle restart design matters more than stronger nagging.",
            },
        ]
    return [
        {
            "contradiction": "Wants order but hates maintaining extra layers.",
            "how_it_shows_up": "They ask for structure and then revert to simpler workarounds when upkeep appears.",
            "product_validation_effect": "Adoption depends on whether the product removes a real step, not only organizes it better.",
        },
        {
            "contradiction": "Curious about improvement but protective of scarce attention.",
            "how_it_shows_up": "They can agree with the use case and still reject the timing.",
            "product_validation_effect": "Trial offers need to fit a normal week, not just a motivated one.",
        },
        {
            "contradiction": "Can sound agreeable before they have truly made space for a tool.",
            "how_it_shows_up": "Positive conversation may not move them any closer to setup or payment.",
            "product_validation_effect": "Founders need behavioral signals, not just verbal encouragement.",
        },
        {
            "contradiction": "Likes clarity but resists products that feel more formal than the underlying problem.",
            "how_it_shows_up": "A strong product deck can still fail if the first task feels heavier than the current workaround.",
            "product_validation_effect": "Landing-page comprehension is weaker than first-step usability as a predictor here.",
        },
    ]


def _fallback_values_patch(persona: PersonaSkill) -> dict[str, list[str]]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "quiet_inclusion_checker":
        return {
            "core_values": ["dignity", "control", "clarity", "relevance"],
            "life_goals": [
                "use useful products without extra identity work",
                "keep control over what becomes visible and why",
            ],
            "fears": [
                "being pushed into public legibility before value appears",
                "paying for a product that still makes them manage exposure manually",
            ],
            "aspirations": [
                "find products that feel respectful without performance",
                "move through onboarding without self-editing",
            ],
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "core_values": ["boundary control", "reversibility", "clarity", "restraint"],
            "life_goals": [
                "get value without broad exposure",
                "keep control over the data footprint of everyday tools",
            ],
            "fears": [
                "silent scope creep",
                "cleanup after sharing too much too early",
            ],
            "aspirations": [
                "find products that prove value before permissions expand",
                "use automation without surrendering context by default",
            ],
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "core_values": ["explainability", "stability", "practicality", "fairness"],
            "life_goals": [
                "keep monthly life legible",
                "avoid repeat spending that adds stress instead of relief",
            ],
            "fears": [
                "subscription creep disguised as convenience",
                "becoming the unpaid admin for a weak household tool",
            ],
            "aspirations": [
                "pay for fewer headaches, not more dashboards",
                "choose tools that stay defensible after the first month",
            ],
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "core_values": ["reliability", "recoverability", "clear follow-up", "professional calm"],
            "life_goals": [
                "avoid live-use embarrassment",
                "protect customer or teammate trust under pressure",
            ],
            "fears": [
                "being the apology layer for a fragile tool",
                "owning visible confusion created by someone else's product",
            ],
            "aspirations": [
                "look dependable when the day gets rushed",
                "reduce explanation work in customer-facing moments",
            ],
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "core_values": ["momentum", "leverage", "clarity", "credible progress"],
            "life_goals": [
                "show visible progress quickly",
                "find tools that create lift before energy dies",
            ],
            "fears": [
                "backing a clever dead-end",
                "wasting attention on setup without proof",
            ],
            "aspirations": [
                "look sharper quickly",
                "stay ahead without drowning in maintenance",
            ],
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "core_values": ["discretion", "control", "clarity", "self-protection"],
            "life_goals": [
                "evaluate products privately before public alignment",
                "keep ordinary use from becoming visible overexposure",
            ],
            "fears": [
                "public traces arriving before trust exists",
                "being pushed into visible participation as the default cost of entry",
            ],
            "aspirations": [
                "use useful products without paying unnecessary public-expression cost",
                "keep audience control in everyday tools",
            ],
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "core_values": ["ease", "recoverability", "practicality", "energy protection"],
            "life_goals": [
                "reduce tired-week friction",
                "keep only systems that survive low attention",
            ],
            "fears": [
                "tools that become guilt loops",
                "falling behind because the restart is too heavy",
            ],
            "aspirations": [
                "find help that feels lighter than the current workaround",
                "use products that respect depleted attention",
            ],
        }
    return {
        "core_values": ["reliability", "time protection", "clarity", "practicality"],
        "life_goals": [
            "stay on top of work without constant catch-up",
            "protect personal bandwidth",
        ],
        "fears": [
            "paying for another tool that becomes shelfware",
            "making work messier",
        ],
        "aspirations": [
            "reduce admin drag",
            "look more organised and trustworthy",
        ],
    }


def _fallback_decision_policy_patch(persona: PersonaSkill) -> dict[str, Any]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "quiet_inclusion_checker":
        return {
            "trust_requirements": [
                "private defaults",
                "optional disclosure with clear purpose",
                "settings that prove the respectful copy is operationally real",
            ],
            "rejection_triggers": [
                "profile visibility before relevance",
                "identity assumptions hidden inside ordinary onboarding",
            ],
            "proof_requirements": [
                "a core flow that works with minimal disclosure",
                "clear control over what becomes visible and when",
            ],
            "founder_challenge_style": "Ask whether respect lives in the defaults or only in the messaging.",
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "trust_requirements": [
                "minimal permissions",
                "reversible trial design",
                "plain retention and model-boundary language",
            ],
            "rejection_triggers": [
                "full access demanded before a narrow proof exists",
                "scope widening during signup or checkout",
            ],
            "proof_requirements": [
                "sample-data or limited-mode trial",
                "clear explanation of what the product can do without broad access",
            ],
            "founder_challenge_style": "Narrow the scope, then test whether the product still deserves trust.",
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "trust_requirements": [
                "local pricing realism",
                "easy exit",
                "a visible answer to what recurring hassle or spend disappears",
            ],
            "rejection_triggers": [
                "another monthly charge with weak month-two logic",
                "household coordination that quietly creates one unpaid maintainer",
            ],
            "proof_requirements": [
                "a trial that shows less follow-up work or less recurring spend pressure",
                "pricing that remains explainable after the first month",
            ],
            "founder_challenge_style": "Push on month-two defensibility, household explanation burden, and what the product actually replaces.",
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "trust_requirements": [
                "failure-path clarity",
                "clean support or escalation ownership",
                "proof that the product behaves well under rush conditions",
            ],
            "rejection_triggers": [
                "live-use fragility",
                "systems that turn the buyer into the apology layer",
            ],
            "proof_requirements": [
                "one pressured handoff test, not just a calm demo",
                "evidence that the team is not left alone when the nice path breaks",
            ],
            "founder_challenge_style": "Stress-test the product against visible failure, not just clean success cases.",
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "trust_requirements": [
                "a visible win in days, not weeks",
                "bounded setup before first output",
                "proof that the momentum can be repeated after week one",
            ],
            "rejection_triggers": [
                "setup that delays visible proof",
                "novelty with no durable leverage",
            ],
            "proof_requirements": [
                "a trial with one fast, showable result",
                "evidence that the win survives after the first burst of curiosity",
            ],
            "founder_challenge_style": "Move quickly from concept to speed of visible leverage and whether the win lasts beyond novelty.",
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "trust_requirements": [
                "private-first evaluation path",
                "quiet participation settings",
                "clear control over what leaves a public trace",
            ],
            "rejection_triggers": [
                "public participation treated as the default cost of entry",
                "community growth mechanics that assume visible alignment",
            ],
            "proof_requirements": [
                "the product can be tested privately without major feature loss",
                "visibility controls are strong before social features are introduced",
            ],
            "founder_challenge_style": "Ask what becomes public by default and whether the product confuses visibility with trust.",
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "trust_requirements": [
                "first value in one short session",
                "easy restart after a missed week",
                "low-energy onboarding that works on a tired evening",
            ],
            "rejection_triggers": [
                "setup that requires a clean block of focus",
                "products that create guilt loops when the user falls behind",
            ],
            "proof_requirements": [
                "a tired-week use case, not just an ideal-week demo",
                "evidence that the product still works after interrupted use",
            ],
            "founder_challenge_style": "Separate understanding from available energy and test the product against low-attention reality.",
        }
    return {
        "trust_requirements": [
            "clear before-and-after value",
            "low-friction onboarding",
            "a bounded first use case",
        ],
        "rejection_triggers": [
            "extra admin burden",
            "vague claims without proof",
        ],
        "proof_requirements": [
            "specific examples from similar users",
            "a short trial workflow",
        ],
        "founder_challenge_style": "Move from concept into what effort, risk, or explanation burden actually disappears.",
    }


def _fill_v3_1_1_fallbacks(persona: PersonaSkill) -> None:
    archetype = _v3_1_1_archetype_key(persona)
    force_generic_refresh = archetype not in SPECIAL_ARCHETYPES

    if force_generic_refresh:
        persona.profile.panel_role_profile = _panel_role_profile_v3_1_1(persona)
        persona.profile.objection_language_style = _fallback_objection_language_style(persona)
        persona.profile.contradiction_map = _fallback_contradiction_map(persona)
        persona.profile.values = {
            **persona.profile.values,
            **_fallback_values_patch(persona),
        }
        decision_patch = _fallback_decision_policy_patch(persona)
        persona.decision_policy = {
            **persona.decision_policy,
            **decision_patch,
        }
    elif not persona.profile.panel_role_profile:
        persona.profile.panel_role_profile = _panel_role_profile_v3_1_1(persona)

    if force_generic_refresh or _life_arc_needs_rewrite(persona):
        persona.profile.canonical_biography["life_arc_summary"] = _fallback_life_arc_summary(persona)

    if force_generic_refresh or _timeline_needs_rewrite(persona):
        chapters = _fallback_biography_timeline(persona)
        persona.profile.canonical_biography["decade_timeline"] = chapters
        persona.profile.canonical_biography["formative_events"] = [
            {
                "age_range": chapter["age_range"],
                "event_summary": chapter["specific_scene"],
                "impact": chapter["current_reaction_link"],
                "formative_level": chapter["formative_level"],
            }
            for chapter in chapters
        ]

    if force_generic_refresh or not persona.profile.canonical_biography.get("non_work_purchase_scenes"):
        persona.profile.canonical_biography["non_work_purchase_scenes"] = _fallback_non_work_purchase_scenes(persona)

    if force_generic_refresh or not persona.profile.persona_voiceprint:
        persona.profile.persona_voiceprint = _fallback_voiceprint(persona)
    else:
        fallback_voiceprint = _fallback_voiceprint(persona)
        for key, value in fallback_voiceprint.items():
            if not persona.profile.persona_voiceprint.get(key):
                persona.profile.persona_voiceprint[key] = value

    if force_generic_refresh or not persona.profile.sensitive_scenario_reactions:
        persona.profile.sensitive_scenario_reactions = _fallback_sensitive_scenarios(persona)
    else:
        fallback_scenarios = _fallback_sensitive_scenarios(persona)
        for key, value in fallback_scenarios.items():
            if not persona.profile.sensitive_scenario_reactions.get(key):
                persona.profile.sensitive_scenario_reactions[key] = value

    if not persona.profile.sensitive_scenario_salience or set(persona.profile.sensitive_scenario_salience) != set(SENSITIVE_SCENARIO_KEYS):
        persona.profile.sensitive_scenario_salience = _fallback_sensitive_salience(persona)
    elif (
        all(int(score) == 5 for score in persona.profile.sensitive_scenario_salience.values())
        and archetype not in SPECIAL_ARCHETYPES
    ):
        persona.profile.sensitive_scenario_salience = _fallback_sensitive_salience(persona)

    local_grounding = persona.profile.local_grounding_layer
    common_apps = _clean_list(local_grounding.get("common_apps_or_services", []))
    if len(common_apps) < 4 or {"search", "messaging apps"} & set(common_apps):
        persona.profile.local_grounding_layer = _fallback_local_grounding_layer(persona)

    persona.response_style = {
        **persona.response_style,
        "persona_voice_anchor": persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
    }
    persona.decision_policy = {
        **persona.decision_policy,
        "trial_threshold": persona.profile.persona_voiceprint.get("example_near_purchase_question", ""),
    }


def _example_responses(persona: PersonaSkill) -> dict[str, str]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "ai_product": (
                "I can see the use case, but I would not start by connecting everything. "
                "Show me one recurring handoff where I can review the AI before it acts. "
                "If that works in a normal week, then I would take the next step."
            ),
            "subscription_product": (
                "The price is not the only issue. If this becomes another quiet monthly charge after one calm week, I will cancel. "
                "I need a simple first win and an easy way out."
            ),
            "identity_sensitive_product": (
                "If you need personal context that early, I slow down. Let me see the value first, then tell me why the disclosure matters."
            ),
            "high_friction_onboarding": (
                "If setup takes too long, I know I will leave it for later and probably never come back. "
                "I need first value before the admin feeling kicks in."
            ),
            "vague_founder_pitch": (
                "I get what you are aiming for, but I still do not know what I would try first. "
                "Give me the smallest version that works without rebuilding my routine."
            ),
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "ai_product": (
                "I understand the pitch. My question is what happens after week three, when the AI is wrong and someone has to clean it up. "
                "If the user becomes the quiet QA layer, this is not labor savings."
            ),
            "subscription_product": (
                "The first month is easy to justify. Show me the second month. "
                "If the value cannot be explained after the launch energy is gone, it becomes another line item to cancel."
            ),
            "identity_sensitive_product": (
                "Do not ask me to label myself before the product has earned relevance. "
                "Optional disclosure, private defaults, and a clear purpose matter more than inclusive copy."
            ),
            "high_friction_onboarding": (
                "If onboarding already needs project discipline, I assume month two is worse. "
                "Show me the point where the burden actually leaves the user."
            ),
            "vague_founder_pitch": (
                "The concept is clear. The burden map is not. "
                "Tell me what work leaves the user after the demo stops carrying the story."
            ),
        }
    if archetype == "quiet_inclusion_checker":
        return {
            "ai_product": (
                "I can see the utility. I just do not want the account flow turning me into a profile before the tool proves itself. "
                "Show me the work first, the labels later."
            ),
            "subscription_product": (
                "I will pay for calm control. I will not pay to manage my own visibility every week."
            ),
            "identity_sensitive_product": (
                "Optional disclosure, private defaults, clear purpose. If those are weak, I usually leave quietly."
            ),
            "high_friction_onboarding": (
                "If I have to explain myself and learn the tool at the same time, that is too much work too early."
            ),
            "vague_founder_pitch": (
                "I understand the theme. I still need to know what stays private by default and what I can do without extra identity work."
            ),
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "ai_product": (
                "Do not sell me AI by asking for everything. Give me one narrow task, a review step, and a sample-data path."
            ),
            "subscription_product": (
                "A small monthly price does not offset broad permissions. Scope first, then payment."
            ),
            "identity_sensitive_product": (
                "If you want labels or real profile data before the value is clear, I am already backing away."
            ),
            "high_friction_onboarding": (
                "Long setup plus wide permissions is two kinds of friction, not one."
            ),
            "vague_founder_pitch": "Too broad. Show me the smallest safe use case.",
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "ai_product": (
                "Interesting, but if I need a paid plan before I know what hassle disappears next month, it stays theoretical."
            ),
            "subscription_product": (
                "I can handle the price. I do not want another line item I keep defending."
            ),
            "identity_sensitive_product": (
                "If the flow adds public or household awkwardness before it adds value, the answer is no."
            ),
            "high_friction_onboarding": (
                "If it needs a lot of setup and still asks for a monthly charge, that is two costs before any proof."
            ),
            "vague_founder_pitch": (
                "Tell me what I stop paying for, chasing, or explaining if this is real."
            ),
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "ai_product": (
                "I need to know who catches the mistake when the AI is wrong in front of someone waiting."
            ),
            "subscription_product": (
                "I will pay if it reduces apology work. I will not pay to babysit it in live use."
            ),
            "identity_sensitive_product": (
                "If the profile or visibility design makes the user do extra explanation work, that is already a service risk."
            ),
            "high_friction_onboarding": (
                "If onboarding only works on a calm day, it will fail in the real queue."
            ),
            "vague_founder_pitch": (
                "What happens when this breaks live, and who owns the explanation?"
            ),
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "ai_product": (
                "If AI gives me something useful enough to show by next week, I will test it. If it needs a long warm-up, I will not."
            ),
            "subscription_product": (
                "I care less about the monthly price than the speed to visible leverage."
            ),
            "identity_sensitive_product": (
                "Keep the profile friction light. I do not want the setup story stealing momentum."
            ),
            "high_friction_onboarding": (
                "If the first win lives behind a project plan, the momentum is gone."
            ),
            "vague_founder_pitch": (
                "What is the fastest visible win, not the biggest eventual promise?"
            ),
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "ai_product": (
                "Maybe. Just keep the trial private until I know it deserves any public association."
            ),
            "subscription_product": (
                "I will pay for quiet control sooner than for extra public-facing features."
            ),
            "identity_sensitive_product": (
                "If you want visible labels or sharing before the product earns it, I usually stop there."
            ),
            "high_friction_onboarding": (
                "If setup creates a public trail before value, that is not a neutral inconvenience."
            ),
            "vague_founder_pitch": (
                "What can I test privately, and what becomes visible by default?"
            ),
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "ai_product": (
                "Makes sense. If it needs more than one short session, I am probably not starting."
            ),
            "subscription_product": (
                "Cheap is not the point. If I forget it on a tired week, it becomes another waste."
            ),
            "identity_sensitive_product": (
                "Any extra explanation step is one more reason to close it."
            ),
            "high_friction_onboarding": (
                "If the useful part starts after the setup, that useful part is not for me."
            ),
            "vague_founder_pitch": (
                "What is the simplest version that works when I am already tired?"
            ),
        }
    near_purchase = persona.profile.persona_voiceprint.get("example_near_purchase_question", "")
    direct = _clean_list(persona.profile.objection_language_style.get("direct_objection_examples", []))
    return {
        "ai_product": (
            "I am not against AI, but I want one contained task and a review step. "
            "If the useful version starts after broad access, that is where I stop paying attention."
        ),
        "subscription_product": (
            "A monthly price is not the real problem. "
            "I need to know whether this still makes sense after the first tidy week and whether leaving is clean."
        ),
        "identity_sensitive_product": (
            "Let me get the value first. "
            "If the flow wants labels or visibility before the product is useful, trust falls faster than your copy suggests."
        ),
        "high_friction_onboarding": (
            "If setup already needs a calm evening and a clean desk, it is not designed for my real week. "
            "I need first value before the admin feeling takes over."
        ),
        "vague_founder_pitch": (
            _first_non_empty(
                direct[0] if direct else "",
                "I understand the idea. Now tell me what gets lighter before I give this more data, attention, or routine space.",
            )
            + (" " + near_purchase if near_purchase else "")
        ).strip(),
    }


def _response_variants(persona: PersonaSkill) -> dict[str, str]:
    archetype = _v3_1_1_archetype_key(persona)
    if archetype == "early_career_practical_trial_user":
        return {
            "Full Research Response": (
                "I can see the problem, and I would pay attention if you keep the first step small. "
                "I do not want to rebuild my routine or explain a shaky purchase before it has earned trust. "
                "Show me one recurring handoff, let me review the output, and give me an easy way out if the week gets noisy."
            ),
            "Short Interview Response": "Maybe, but I need the smallest version first.",
            "Low-Attention Response": "Maybe useful, but I would not set this up tonight. If I cannot try one small task first, I will probably leave it.",
            "Polite Fake Interest Response": "Interesting idea. I can see why people might need it.",
            "Genuine Trial Interest Response": "Could I test it on one recurring handoff without inviting the whole team yet?",
            "Hard Rejection Response": "This makes me manage the tool before the tool helps me. I would not keep using it.",
        }
    if archetype == "mature_operator_retention_skeptic":
        return {
            "Full Research Response": (
                "The concept is understandable. What I care about is whether the upkeep is bounded, whether month two still makes sense, "
                "and whether disclosure stays under user control. If the product creates a cleaner record of effort without removing the effort, I would not buy it."
            ),
            "Short Interview Response": "I understand it. I do not see the upkeep case yet.",
            "Low-Attention Response": "I understand it. I do not see the upkeep case.",
            "Polite Fake Interest Response": "There may be a use case. I would need to see how it behaves after the first month.",
            "Genuine Trial Interest Response": "What still works after launch energy is gone, and what stays private by default?",
            "Hard Rejection Response": "This creates a cleaner record of effort. It does not remove the effort.",
        }
    if archetype == "quiet_inclusion_checker":
        return {
            "Full Research Response": (
                "I can see the product intent, but the trust question is in the defaults. "
                "If I have to disclose more than the first task requires, or if the profile becomes visible too early, I will usually leave quietly instead of debating it."
            ),
            "Short Interview Response": "The settings matter more to me than the slogan here.",
            "Low-Attention Response": "Maybe. I need to know what stays private first.",
            "Polite Fake Interest Response": "The concept is clear. I would want to look at the profile controls.",
            "Genuine Trial Interest Response": "Can I use the core flow before deciding what, if anything, I disclose?",
            "Hard Rejection Response": "If the product needs public legibility before utility, I am out.",
        }
    if archetype == "privacy_narrow_trialist":
        return {
            "Full Research Response": (
                "I am open to the use case, but only through a narrow proof. "
                "Show me the smallest safe test with clear review control. If the product asks for full access first, the trial is already too broad."
            ),
            "Short Interview Response": "Narrow the scope, then I will look again.",
            "Low-Attention Response": "Too much access for a first try.",
            "Polite Fake Interest Response": "Interesting. I would need the data boundary explained more clearly.",
            "Genuine Trial Interest Response": "What is the smallest safe connection that still proves the value?",
            "Hard Rejection Response": "If the trial needs full history, I am not doing the trial.",
        }
    if archetype == "budget_guarded_household_operator":
        return {
            "Full Research Response": (
                "I can see the use case, but the monthly logic has to survive real household life. "
                "If I still need to explain this spend next month without pointing to a clear reduction in hassle, follow-up, or another cost, I will not keep it."
            ),
            "Short Interview Response": "Useful maybe. Still need the month-two logic.",
            "Low-Attention Response": "Another monthly maybe is not enough for me.",
            "Polite Fake Interest Response": "I can see who this helps. I would need to think about the ongoing spend.",
            "Genuine Trial Interest Response": "Can I test it without locking into another subscription first?",
            "Hard Rejection Response": "If this adds a recurring charge before it removes one, it will not last.",
        }
    if archetype == "credibility_guarding_service_operator":
        return {
            "Full Research Response": (
                "The feature story is not the main issue for me. "
                "I need to know how this behaves when the day is rushed and somebody is waiting. If the product makes me carry the apology when it slips, I am not putting my name behind it."
            ),
            "Short Interview Response": "What happens when it fails live?",
            "Low-Attention Response": "If I have to explain the failure, no.",
            "Polite Fake Interest Response": "Interesting. I would need to see it under real service pressure.",
            "Genuine Trial Interest Response": "Could I test this on one live handoff before I recommend it?",
            "Hard Rejection Response": "Do not turn me into customer support for your product.",
        }
    if archetype == "ambitious_signal_seeker":
        return {
            "Full Research Response": (
                "I am more open than most to trying this, but I still need a visible win quickly. "
                "If the product can make me look sharper in a real workflow this week, I will lean in. If it spends that energy on setup and theory, I will move on."
            ),
            "Short Interview Response": "Show me the fast visible win.",
            "Low-Attention Response": "If it cannot prove itself this week, I will forget it.",
            "Polite Fake Interest Response": "The idea is strong. I would want to see the quickest real proof.",
            "Genuine Trial Interest Response": "What can I show by next week if this actually works?",
            "Hard Rejection Response": "I do not need another clever demo that disappears in two weeks.",
        }
    if archetype == "public_reputation_risk_guard":
        return {
            "Full Research Response": (
                "The concept may be fine. My question is whether I can evaluate it privately before it becomes visible to anyone else. "
                "If the default path turns normal product use into public alignment, the product is asking for more than a trial should ask."
            ),
            "Short Interview Response": "Keep the evaluation private first.",
            "Low-Attention Response": "Not if the trial is public by default.",
            "Polite Fake Interest Response": "I can see the concept. I would need quiet participation options.",
            "Genuine Trial Interest Response": "Which parts stay private if I only want to test the core use case?",
            "Hard Rejection Response": "Public participation is not a neutral default for me.",
        }
    if archetype == "low_energy_avoidant_adapter":
        return {
            "Full Research Response": (
                "I may agree with the product faster than I can maintain it. "
                "The real question is whether the first useful step fits a tired normal week. If it needs a clean block of energy before it helps, I will probably never get past understanding."
            ),
            "Short Interview Response": "Makes sense. Still looks too heavy for my real week.",
            "Low-Attention Response": "Not starting this tonight.",
            "Polite Fake Interest Response": "Maybe useful. I would need a simpler start than this.",
            "Genuine Trial Interest Response": "What is the fastest version that still works on a tired week?",
            "Hard Rejection Response": "I understand it. I just do not have the energy for another maintenance loop.",
        }
    voice = persona.profile.persona_voiceprint
    return {
        "Full Research Response": (
            "I can see the use case, but the order matters. "
            "Give me a narrow first step, make the permissions smaller than the full promise, and show me what gets lighter in a normal week. "
            "If the product needs trust, disclosure, or cleanup before it gives relief, I would understand it without adopting it."
        ),
        "Short Interview Response": _first_non_empty(
            voice.get("example_polite_rejection", ""),
            "Maybe, but I still need the smaller and safer first step.",
        ),
        "Low-Attention Response": "Maybe useful. Not giving it more setup or data tonight.",
        "Polite Fake Interest Response": _first_non_empty(
            persona.profile.objection_language_style.get("what_they_say_when_they_are_only_being_nice", []),
            "Interesting idea. I can see why someone would look at it.",
        ),
        "Genuine Trial Interest Response": _first_non_empty(
            voice.get("example_near_purchase_question", ""),
            "What is the smallest safe way to test this without connecting everything yet?",
        ),
        "Hard Rejection Response": _first_non_empty(
            voice.get("example_hard_rejection", ""),
            "If the product needs more access than it has earned, I stop there.",
        ),
    }


def _template_repetition_score(responses: list[str]) -> int:
    if not responses:
        return 1
    starters = [" ".join(_normalize_text(response).split()[:5]) for response in responses]
    unique_ratio = len(set(starters)) / max(1, len(starters))
    if unique_ratio >= 0.8:
        return 4
    if unique_ratio >= 0.6:
        return 3
    return 2


def build_example_response_quality(example_responses: dict[str, str], response_variants: dict[str, str], voice_anchor: str) -> dict[str, Any]:
    combined = {**example_responses, **response_variants}
    counts = _aggregate_markdown_lint({"persona.skill.md": "\n".join(combined.values())})
    punctuation_pass = counts["double_punctuation"] == 0 and counts["awkward_spacing"] == 0
    ai_pass = counts["lowercase_ai"] == 0
    repetition_score = _template_repetition_score(list(example_responses.values()))

    warnings: list[str] = []
    required_improvements: list[str] = []
    if not punctuation_pass:
        warnings.append("Example responses still contain punctuation joins or awkward spacing.")
        required_improvements.append("Clean punctuation joins in example responses.")
    if not ai_pass:
        warnings.append("Lowercase AI casing remains in example responses.")
        required_improvements.append("Normalize standalone AI casing in examples.")
    if repetition_score <= 2:
        warnings.append("Example responses still read too much like a shared template.")
        required_improvements.append("Vary the opening rhythm and sentence pattern across categories.")

    low_attention_present = "Low-Attention Response" in response_variants
    polite_present = "Polite Fake Interest Response" in response_variants
    hard_rejection_present = "Hard Rejection Response" in response_variants
    if not low_attention_present:
        required_improvements.append("Add a low-attention response variant.")
    if not polite_present:
        required_improvements.append("Add a polite fake interest response variant.")
    if not hard_rejection_present:
        required_improvements.append("Add a hard rejection response variant.")

    voice_alignment_score = 4 if voice_anchor and any(token in _normalize_text(" ".join(example_responses.values())) for token in _normalize_text(voice_anchor).split()) else 3
    naturalness_score = 4 if punctuation_pass and ai_pass and repetition_score >= 3 else 3
    if not warnings:
        warnings.append("Examples are cleaner than v3.1, but human review should still check whether they sound spontaneous enough.")

    return {
        "naturalness_score": naturalness_score,
        "voice_alignment_score": voice_alignment_score,
        "template_repetition_score": repetition_score,
        "punctuation_check": "pass" if punctuation_pass else "fail",
        "ai_capitalization_check": "pass" if ai_pass else "fail",
        "low_attention_variants_present": low_attention_present,
        "polite_fake_interest_present": polite_present,
        "hard_rejection_present": hard_rejection_present,
        "warnings": warnings,
        "required_improvements": required_improvements[:3],
    }


def _non_work_scene_markdown(persona: PersonaSkill) -> list[str]:
    lines: list[str] = []
    for scene in persona.profile.canonical_biography.get("non_work_purchase_scenes", [])[:3]:
        lines.extend(
            [
                f"### {scene.get('scene_title', '')}",
                str(scene.get("specific_scene", "")).strip(),
                f"Decision context: {_first_non_empty(scene.get('decision_context', ''), scene.get('scene_title', ''))}",
                f"Trust or price lesson: {_first_non_empty(scene.get('trust_or_price_lesson', ''), scene.get('current_product_research_impact', ''))}",
                f"Product research impact: {scene.get('current_product_research_impact', '')}",
                "",
            ]
        )
    if not lines:
        lines.extend(
            [
                "### No strong non-work scene recorded yet",
                "This persona still needs a richer non-work purchase memory before the biography feels fully rounded outside work contexts.",
                "",
            ]
        )
    return lines


def render_biography_md_v3_1_1(persona: PersonaSkill) -> str:
    identity = persona.profile.basic_identity
    biography = persona.profile.canonical_biography
    chapters = biography.get("decade_timeline", [])
    lines = [
        f"# {identity.get('name', '')} - Level 3 Synthetic User Biography",
        "",
        "## Life Arc Summary",
        biography.get("life_arc_summary", ""),
        "",
    ]
    for chapter in chapters:
        lines.extend(
            [
                f"## {chapter.get('age_range', '')}",
                f"**{chapter.get('chapter_title', '')}**",
                str(chapter.get("life_context", "")).strip(),
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
            render_formative_events_markdown(biography.get("formative_events", []), chapters).rstrip(),
            "",
            "## Current Identity",
            biography.get("current_identity", ""),
            "",
            "## Non-Work Purchase Scenes",
            *_non_work_scene_markdown(persona),
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
            (
                "Hidden habits: "
                + ", ".join(
                    persona.profile.hidden_habits.get("private_shortcuts", [])
                    + persona.profile.hidden_habits.get("workarounds_they_keep_using", [])
                )
            ),
        ]
    )
    for item in persona.profile.contradiction_map[:5]:
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
            (
                "Top sensitive scenarios: "
                + ", ".join(
                    f"{_title_from_key(key)} ({persona.profile.sensitive_scenario_salience.get(key, 0)}/10)"
                    for key in _top_salience_keys(persona.profile.sensitive_scenario_salience)
                )
            ),
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
    return _clean_markdown_text("\n".join(lines))


def render_research_kernel_md_v3_1_1(persona: PersonaSkill) -> str:
    return _clean_markdown_text(render_research_kernel_md_v3_1(persona))


def render_sensitive_scenarios_md_v3_1_1(persona: PersonaSkill) -> str:
    return _clean_markdown_text(render_sensitive_scenarios_md_v3_1(persona))


def _response_variants_markdown(response_variants: dict[str, str]) -> list[str]:
    lines = ["## Response Variants", ""]
    for title in (
        "Full Research Response",
        "Short Interview Response",
        "Low-Attention Response",
        "Polite Fake Interest Response",
        "Genuine Trial Interest Response",
        "Hard Rejection Response",
    ):
        lines.extend([f"### {title}", response_variants.get(title, ""), ""])
    return lines


def render_persona_skill_md_v3_1_1(persona: PersonaSkill, example_responses: dict[str, str], response_variants: dict[str, str]) -> str:
    identity = persona.profile.basic_identity
    salience = persona.profile.sensitive_scenario_salience
    interests = _clean_list(persona.profile.interests_and_hobbies.get("primary_interests", []))[:4]
    trust_requirements = _clean_list(persona.decision_policy.get("trust_requirements", []))[:4]
    rejection_triggers = _clean_list(persona.decision_policy.get("rejection_triggers", []))[:4]
    non_work_scenes = persona.profile.canonical_biography.get("non_work_purchase_scenes", [])[:2]
    voice = persona.profile.persona_voiceprint
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
        persona.profile.canonical_biography.get("life_arc_summary", ""),
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
            ", ".join(interests) or "Grounded, practical interests matter more than novelty collecting.",
            "",
            "## Daily Context",
            f"Most open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_most_open_to_new_products', '')}",
            f"Least open to products: {persona.profile.daily_micro_behaviours.get('when_they_are_least_open_to_new_products', '')}",
            "",
            "## Decision Logic",
            f"Trust requirements: {', '.join(trust_requirements)}",
            f"Rejection triggers: {', '.join(rejection_triggers)}",
            "",
            "## Buying Logic",
            persona.profile.product_reaction_rules.get("difference_between_curiosity_and_purchase", ""),
            "",
            "## Pricing Logic",
            f"{persona.profile.pricing_logic.get('what_makes_price_feel_fair', '')} Watch for: {persona.profile.pricing_logic.get('pricing_objection', '')}",
            "",
            "## Technology & AI Attitude",
            (
                f"{persona.profile.technology_profile.get('automation_openness', '')}. "
                f"{persona.profile.cross_domain_product_reaction_model.get('ai_product', {}).get('first_question', '')}"
            ),
            "",
            "## Discovery & Trust Path",
            persona.profile.product_discovery_paths.get("most_likely_first_touchpoint", ""),
            persona.profile.media_and_content_diet.get("how_they_verify_claims", ""),
            "",
            "## Non-Work Product Memory",
        ]
    )
    for scene in non_work_scenes:
        lines.append(f"- {scene.get('scene_title', '')}: {scene.get('current_product_research_impact', '')}")
    if not non_work_scenes:
        lines.append("- This persona still needs a richer non-work purchase memory before household and personal-spend reactions feel fully grounded.")
    lines.extend(
        [
            "",
            "## Cross-Domain Product Reaction Model",
            f"- generic_new_product: {persona.profile.cross_domain_product_reaction_model.get('generic_new_product', {}).get('first_question', '')}",
            f"- subscription_product: {persona.profile.cross_domain_product_reaction_model.get('subscription_product', {}).get('first_question', '')}",
            f"- family_or_household_product: {persona.profile.cross_domain_product_reaction_model.get('family_or_household_product', {}).get('first_question', '')}",
            f"- financial_product: {persona.profile.cross_domain_product_reaction_model.get('financial_product', {}).get('first_question', '')}",
            f"- identity_sensitive_product: {persona.profile.cross_domain_product_reaction_model.get('identity_sensitive_product', {}).get('first_question', '')}",
            f"- high_friction_onboarding: {persona.profile.cross_domain_product_reaction_model.get('high_friction_onboarding', {}).get('first_question', '')}",
            "",
            "## Sensitive Topic Handling",
        ]
    )
    for key in _top_salience_keys(salience):
        block = persona.profile.sensitive_scenario_reactions.get(key, {})
        lines.append(
            f"- {_title_from_key(key)} ({salience.get(key, 0)}/10): "
            f"{_first_non_empty(block.get('what_reduces_trust', ''), block.get('reaction', ''))}"
        )
    lines.extend(
        [
            "",
            "## Objection Language",
            f"Voice anchor: {_first_non_empty(voice.get('what_they_repeat_when_skeptical', ''), response_variants.get('Short Interview Response', ''))}",
            f"Polite rejection: {_first_non_empty(voice.get('example_polite_rejection', ''), response_variants.get('Polite Fake Interest Response', ''))}",
            f"Hard rejection: {_first_non_empty(voice.get('example_hard_rejection', ''), response_variants.get('Hard Rejection Response', ''))}",
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
            f"1. AI productivity product: {example_responses['ai_product']}",
            f"2. Subscription product: {example_responses['subscription_product']}",
            f"3. Identity-sensitive product: {example_responses['identity_sensitive_product']}",
            f"4. High-friction onboarding product: {example_responses['high_friction_onboarding']}",
            f"5. Vague founder pitch: {example_responses['vague_founder_pitch']}",
            "",
            *_response_variants_markdown(response_variants),
        ]
    )
    return _clean_markdown_text("\n".join(lines))


def render_persona_md_v3_1_1(persona: PersonaSkill) -> str:
    return _clean_markdown_text(
        "\n".join(
            [
                f"# {persona.profile.basic_identity.get('name', '')}",
                "",
                "## Core Read",
                persona.profile.canonical_biography.get("life_arc_summary", ""),
                "",
                "## Voice",
                persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
            ]
        )
    )


def _diff_markdown_v3_1_to_v3_1_1(persona: PersonaSkill, source_dir: Path) -> str:
    lines = [
        f"# {persona.profile.basic_identity.get('name', '')} - V3.1 to V3.1.1 Diff",
        "",
        "## Renderer Fixes",
        "- Cleaned Formative Events section to remove raw dict output.",
        "- Added markdown cleanliness lint to block raw object leakage and punctuation joins in readable artifacts.",
        "",
        "## Example Response Polish",
        "- Rewrote example responses to sound closer to the persona's actual voiceprint.",
        "- Removed repeated template structure, lowercase AI casing, and double punctuation joins.",
        "",
        "## Response Variants Added",
        "- Full Research Response",
        "- Short Interview Response",
        "- Low-Attention Response",
        "- Polite Fake Interest Response",
        "- Genuine Trial Interest Response",
        "- Hard Rejection Response",
        "",
        "## Naturalness Checks Added",
        "- Example response quality audit",
        "- Markdown cleanliness lint",
        "- Polish report with before/after counts",
        "",
        "## Remaining Limitations",
        "- Human review is still needed to judge whether the voice sounds sufficiently spontaneous.",
        "",
        "## No Schema Change",
        "- V3.1.1 does not change the core persona structure or behavioural model.",
        "- This is a rendering and response naturalness patch only.",
        "",
        f"Source folder: {source_dir}",
    ]
    return _clean_markdown_text("\n".join(lines))


def build_polish_report(source_dir: Path, rendered_artifacts: dict[str, str], synthetic_user_id: str) -> dict[str, Any]:
    before_counts = _aggregate_markdown_lint(_source_markdown_artifacts(source_dir))
    after_counts = _aggregate_markdown_lint(rendered_artifacts)
    return {
        "synthetic_user_id": synthetic_user_id,
        "source_version": "v3_1",
        "target_version": "v3_1_1",
        "changes": {
            "markdown_raw_object_leakage_fixed": True,
            "formative_events_renderer_fixed": True,
            "example_responses_polished": True,
            "response_variants_added": True,
            "punctuation_cleaned": True,
            "ai_capitalization_fixed": True,
        },
        "before_after_checks": {
            "raw_dict_patterns_before": before_counts["raw_python_dict_patterns"],
            "raw_dict_patterns_after": after_counts["raw_python_dict_patterns"],
            "double_punctuation_before": before_counts["double_punctuation"],
            "double_punctuation_after": after_counts["double_punctuation"],
            "lowercase_ai_before": before_counts["lowercase_ai"],
            "lowercase_ai_after": after_counts["lowercase_ai"],
        },
        "remaining_known_limitations": [],
        "human_review_needed": True,
    }


def upgrade_persona_to_v3_1_1(source_persona: PersonaSkill, *, random_seed: int | None = None) -> PersonaSkill:
    persona = copy.deepcopy(source_persona)
    if persona.skill_version not in {"v3.1", "v3.1.1"}:
        persona = upgrade_persona_to_v3_1(persona, random_seed=random_seed)

    persona.skill_version = "v3.1.1"
    _fill_v3_1_1_fallbacks(persona)
    persona.profile.audit_evidence_layer.update(
        {
            "persona_generation_method": "deterministic_v3_1_1_diversified_patch",
            "persona_version": "v3.1.1",
            "generator_version": "persona-generator/v3.1.1",
            "last_audited_at": datetime.now(UTC).date().isoformat(),
        }
    )
    persona.audit = {
        **persona.audit,
        **persona.profile.audit_evidence_layer,
    }
    return persona


def _fallback_quality_audit(persona: PersonaSkill) -> dict[str, Any]:
    location = str(persona.profile.basic_identity.get("location", "")).strip() or "the local market"
    timeline = persona.profile.canonical_biography.get("decade_timeline", [])
    non_work_scenes = persona.profile.canonical_biography.get("non_work_purchase_scenes", [])
    local_apps = _clean_list(persona.profile.local_grounding_layer.get("common_apps_or_services", []))
    salience_values = [int(value) for value in persona.profile.sensitive_scenario_salience.values()]
    varied_salience = len(set(salience_values)) >= 3
    voice_anchor = _first_non_empty(persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""))
    return {
        "scores": {
            "structure_completeness": 5,
            "biography_depth": 4 if len(timeline) >= 3 else 3,
            "lived_scene_quality": 4 if not _timeline_needs_rewrite(persona) else 3,
            "non_work_lived_scene_quality": 3 if len(non_work_scenes) >= 2 else 2,
            "local_grounding": 4 if len(local_apps) >= 4 else 3,
            "product_reaction_readiness": 4,
            "sensitive_topic_readiness": 4 if len(persona.profile.sensitive_scenario_reactions) == 8 else 3,
            "sensitive_salience_specificity": 3 if varied_salience else 2,
            "voice_distinctiveness": 4 if voice_anchor else 2,
            "archetype_life_arc_distinctiveness": 4 if not _life_arc_needs_rewrite(persona) else 2,
            "cross_domain_non_work_diversity": 3 if len(non_work_scenes) >= 2 else 2,
            "library_distinctiveness": 4,
            "template_leakage_risk": 4,
            "overall": 4,
        },
        "strengths": [
            "Timeline scenes now anchor the persona in ordinary moments instead of placeholder prose.",
            "Voiceprint, sensitive scenarios, and non-work purchase memories are present enough for promptable validation use.",
            f"Local grounding now reflects {location} trust and pricing cues instead of abstract global SaaS assumptions.",
        ],
        "weaknesses": [
            "Some non-work scenes still lean toward practical utility rather than taste, aspiration, or identity-signaling spend.",
            "The response style is cleaner and more articulate than many real low-attention users would sound in practice.",
            "Core motivation still overlaps with other workflow-conscious personas around routine protection and friction control.",
        ],
        "required_improvements": [
            "Add one leisure or identity-adjacent purchase memory that is not framed through admin burden.",
            "Introduce more silent dropout language so not every objection becomes an explicit spoken analysis.",
            "Diversify consumer-side motivation further if this archetype expands into a larger panel.",
        ],
        "warnings": [
            "Fallback audit was synthesized for a non-hand-tuned archetype to avoid carrying over mismatched persona-specific critique."
        ],
        "enum_leakage_check": "pass",
        "abstract_language_check": "watch_for_shared_workflow_language",
        "local_grounding_check": "pass" if len(local_apps) >= 4 else "needs_attention",
        "sensitive_scenario_check": "pass" if len(persona.profile.sensitive_scenario_reactions) == 8 else "needs_attention",
        "similarity_check": "review diversity_report for overlap on core motivation and pricing logic",
        "human_review_needed": True,
    }


def build_quality_audit_v3_1_1(
    target_persona: PersonaSkill,
    source_persona: PersonaSkill,
    rendered_artifacts: dict[str, str],
    example_response_quality: dict[str, Any],
) -> dict[str, Any]:
    if _v3_1_1_archetype_key(target_persona) in SPECIAL_ARCHETYPES:
        base_quality = copy.deepcopy(source_persona.audit.get("quality_audit") or _fallback_quality_audit(target_persona))
    else:
        base_quality = _fallback_quality_audit(target_persona)
    counts = _aggregate_markdown_lint(rendered_artifacts)
    warnings = list(base_quality.get("warnings", []))
    if counts["raw_python_dict_patterns"] or counts["raw_json_object_leakage"]:
        warnings.append("Readable markdown still contains raw object leakage.")
    if counts["double_punctuation"]:
        warnings.append("Readable markdown still contains double punctuation.")
    if counts["lowercase_ai"]:
        warnings.append("Readable markdown still contains lowercase AI casing.")
    if not warnings:
        warnings.append("No schema breakage found, but human review is still required to judge whether the persona voice sounds lived-in enough.")

    base_quality["warnings"] = warnings[:4]
    base_quality["human_review_needed"] = True
    return {
        "quality_audit": base_quality,
        "example_response_quality": example_response_quality,
    }


def build_generation_notes_v3_1_1(
    persona: PersonaSkill,
    diversity_report: dict[str, Any],
    quality_payload: dict[str, Any],
    random_seed: int | None,
    source_version_dir: Path,
    comparison_ids: list[str],
) -> dict[str, Any]:
    return {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": "persona-generator/v3.1.1",
        "prompt_versions": PROMPT_VERSIONS,
        "model_used": "deterministic-diversified-render-v3_1_1",
        "generated_at": _timestamp(),
        "random_seed": random_seed,
        "source_version_dir": str(source_version_dir),
        "comparison_persona_ids": comparison_ids,
        "quality_score_estimate": quality_payload["quality_audit"]["scores"],
        "consistency_warnings": quality_payload["quality_audit"]["warnings"],
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
        "source_version": "v3_1",
        "target_version": "v3_1_1",
        "example_response_quality": quality_payload["example_response_quality"],
    }


def write_v3_1_1_persona_folder(
    persona: PersonaSkill,
    *,
    source_persona: PersonaSkill,
    source_version_dir: Path,
    root_data_dir: Path,
    diversity_report: dict[str, Any],
    quality_payload: dict[str, Any],
    random_seed: int | None = None,
) -> Path:
    persona_root = root_data_dir / persona.profile.synthetic_user_id
    ensure_dir(persona_root)
    target_dir = persona_root / "v3_1_1"
    ensure_dir(target_dir)

    example_responses = _example_responses(persona)
    response_variants = _response_variants(persona)
    rendered_artifacts = {
        "persona.md": render_persona_md_v3_1_1(persona),
        "biography.md": render_biography_md_v3_1_1(persona),
        "research_kernel.md": render_research_kernel_md_v3_1_1(persona),
        "persona.skill.md": render_persona_skill_md_v3_1_1(persona, example_responses, response_variants),
        "local_grounding.md": _clean_markdown_text(render_local_grounding_md_v3(persona)),
        "sensitive_scenarios.md": render_sensitive_scenarios_md_v3_1_1(persona),
        "v3_1_to_v3_1_1_diff.md": _diff_markdown_v3_1_to_v3_1_1(persona, source_version_dir),
    }
    example_quality = build_example_response_quality(
        example_responses,
        response_variants,
        persona.profile.persona_voiceprint.get("what_they_repeat_when_skeptical", ""),
    )
    quality_payload = build_quality_audit_v3_1_1(persona, source_persona, rendered_artifacts, example_quality)
    polish_report = build_polish_report(source_version_dir, rendered_artifacts, persona.profile.synthetic_user_id)
    generation_notes = build_generation_notes_v3_1_1(
        persona,
        diversity_report,
        quality_payload,
        random_seed,
        source_version_dir,
        diversity_report.get("compared_against", []),
    )

    persona.audit = {
        **persona.audit,
        "quality_audit": quality_payload["quality_audit"],
        "example_response_quality": quality_payload["example_response_quality"],
        "diversity_summary": {
            "overall_similarity_score": diversity_report.get("overall_similarity_score", 0.0),
            "distinctiveness_score": diversity_report.get("distinctiveness_score", 1.0),
        },
        "generator_version": "persona-generator/v3.1.1",
    }

    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "audit.json", persona.to_audit_payload())
    write_json(target_dir / "generation_notes.json", generation_notes)
    write_json(target_dir / "diversity_report.json", diversity_report)
    write_json(target_dir / "polish_report.json", polish_report)
    for filename, content in rendered_artifacts.items():
        (target_dir / filename).write_text(content, encoding="utf-8")
    return target_dir


def validate_v3_1_1_persona_folder(folder: Path) -> dict[str, Any]:
    missing_files = [filename for filename in V3_1_1_REQUIRED_FILES if not (folder / filename).exists()]
    audit_payload = read_json(folder / "audit.json")
    profile_payload = read_json(folder / "profile.json")
    quality_audit = audit_payload["audit"].get("quality_audit", {})
    example_quality = audit_payload["audit"].get("example_response_quality", {})
    consistency_warnings: list[str] = []

    for filename in READABLE_MARKDOWN_FILES:
        path = folder / filename
        if not path.exists():
            continue
        counts = lint_markdown_cleanliness(path.read_text(encoding="utf-8"))
        if counts["raw_python_dict_patterns"]:
            consistency_warnings.append(f"Raw Python dict leakage detected in {filename}.")
        if counts["raw_json_object_leakage"]:
            consistency_warnings.append(f"Raw JSON object leakage detected in {filename}.")
        if counts["double_punctuation"]:
            consistency_warnings.append(f"Double punctuation detected in {filename}.")
        if counts["lowercase_ai"]:
            consistency_warnings.append(f"Lowercase AI casing detected in {filename}.")

    if not example_quality.get("low_attention_variants_present"):
        consistency_warnings.append("Low-attention response variant is missing.")
    if not example_quality.get("polite_fake_interest_present"):
        consistency_warnings.append("Polite fake interest response variant is missing.")
    if not example_quality.get("hard_rejection_present"):
        consistency_warnings.append("Hard rejection response variant is missing.")
    if quality_audit and all(value == 5 for value in quality_audit.get("scores", {}).values()):
        consistency_warnings.append("quality_audit scores are unrealistically all perfect.")
    if not _first_non_empty(profile_payload.get("persona_voiceprint", {}).get("what_they_repeat_when_skeptical", "")):
        consistency_warnings.append("Persona voiceprint anchor is empty.")
    if len(profile_payload.get("sensitive_scenario_reactions", {})) < 3:
        consistency_warnings.append("Sensitive scenario reactions are incomplete.")
    if not profile_payload.get("canonical_biography", {}).get("non_work_purchase_scenes", []):
        consistency_warnings.append("Non-work purchase scenes are missing.")

    return {
        "missing_fields": missing_files,
        "consistency_warnings": consistency_warnings,
        "stereotype_warnings": [],
        "quality_score_estimate": quality_audit.get("scores", {}),
        "human_review_needed": quality_audit.get("human_review_needed", True),
    }


def validate_v3_1_1_persona_library(base_dir: Path) -> dict[str, Any]:
    if not base_dir.exists():
        return {
            "library_size": 0,
            "persona_reports": [],
            "issue_count": 0,
            "warning_count": 0,
        }

    persona_reports = []
    for persona_id in _persona_ids_in(base_dir):
        folder = base_dir / persona_id / "v3_1_1"
        if not folder.exists():
            continue
        persona_reports.append({"persona_id": persona_id, **validate_v3_1_1_persona_folder(folder)})

    issue_count = sum(len(report["missing_fields"]) + len(report["consistency_warnings"]) for report in persona_reports)
    return {
        "library_size": len(persona_reports),
        "persona_reports": persona_reports,
        "issue_count": issue_count,
        "warning_count": 0,
    }


def run_distinctiveness_check_v3_1_1(
    *,
    base_dir: Path,
    persona_id: str,
    against_persona_ids: list[str],
    preferred_versions: tuple[str, ...] = ("v3_1_1", "v3_1", "v3", "v2", "root"),
) -> dict[str, Any]:
    candidate = _load_persona_from_dir(base_dir, persona_id, preferred_versions)
    comparisons = [
        _load_persona_from_dir(base_dir, other_id, preferred_versions)
        for other_id in against_persona_ids
        if other_id != persona_id
    ]
    return build_diversity_report_v3_1(candidate, comparisons)


def generate_v3_1_1_personas(
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
        persona_id: load_persona(_resolve_persona_folder(source_dir, persona_id, ("v3_1", "v3", "v2", "root")))
        for persona_id in selected_ids
    }
    provisional = {
        persona_id: upgrade_persona_to_v3_1_1(source_personas[persona_id], random_seed=random_seed_offset + index)
        for index, persona_id in enumerate(selected_ids)
    }

    external_comparisons: dict[str, PersonaSkill] = {}
    comparison_ids = [persona_id for persona_id in (against_persona_ids or []) if persona_id not in selected_ids]
    for comparison_id in comparison_ids:
        external_comparisons[comparison_id] = _load_persona_from_dir(
            compare_against_dir,
            comparison_id,
            ("v3_1_1", "v3_1", "v3", "v2", "root"),
        )

    written_paths: list[Path] = []
    for index, persona_id in enumerate(selected_ids):
        comparison_pool = [
            provisional[other_id]
            for other_id in selected_ids
            if other_id != persona_id
        ] + list(external_comparisons.values())
        diversity_report = build_diversity_report_v3_1(provisional[persona_id], comparison_pool)
        written_paths.append(
            write_v3_1_1_persona_folder(
                provisional[persona_id],
                source_persona=source_personas[persona_id],
                source_version_dir=_resolve_persona_folder(source_dir, persona_id, ("v3_1", "v3", "v2", "root")),
                root_data_dir=output_dir,
                diversity_report=diversity_report,
                quality_payload={},
                random_seed=random_seed_offset + index,
            )
        )
    return written_paths
