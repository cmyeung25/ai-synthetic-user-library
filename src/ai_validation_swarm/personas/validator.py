from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.generator import FIRST_NAMES_BY_GENDER, LOCATION_OPTIONS


@dataclass(slots=True)
class PersonaValidationIssue:
    persona_id: str
    check_name: str
    message: str


class PersonaArtifactValidationError(ValueError):
    def __init__(self, issues: list[PersonaValidationIssue]) -> None:
        self.issues = issues
        details = "; ".join(f"{issue.check_name}: {issue.message}" for issue in issues)
        super().__init__(f"Persona artifact validation failed: {details}")


def _expected_languages_by_location() -> dict[str, set[str]]:
    expected: dict[str, set[str]] = defaultdict(set)
    for options in LOCATION_OPTIONS.values():
        for location, languages, _locale_pack in options:
            expected[location].update(languages)
    return expected


def _validate_household_consistency(
    *,
    persona_id: str,
    family_structure: object,
    household_size: object,
    marital_status: object,
) -> list[PersonaValidationIssue]:
    issues: list[PersonaValidationIssue] = []
    family_structure_value = str(family_structure)
    marital_status_value = str(marital_status)

    if family_structure_value == "living alone":
        if household_size != 1:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size 1 for '{family_structure_value}', got {household_size}.",
                )
            )
        if marital_status_value != "single":
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="marital_status",
                    message=f"Expected marital_status 'single' for '{family_structure_value}', got '{marital_status_value}'.",
                )
            )
    elif family_structure_value == "living with partner":
        if household_size != 2:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size 2 for '{family_structure_value}', got {household_size}.",
                )
            )
        if marital_status_value != "married":
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="marital_status",
                    message=f"Expected marital_status 'married' for '{family_structure_value}', got '{marital_status_value}'.",
                )
            )
    elif family_structure_value == "living with partner and one child":
        if household_size != 3:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size 3 for '{family_structure_value}', got {household_size}.",
                )
            )
        if marital_status_value != "married":
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="marital_status",
                    message=f"Expected marital_status 'married' for '{family_structure_value}', got '{marital_status_value}'.",
                )
            )
    elif family_structure_value == "living with parents":
        if not isinstance(household_size, int) or household_size < 2:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size >= 2 for '{family_structure_value}', got {household_size}.",
                )
            )
        if marital_status_value != "single":
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="marital_status",
                    message=f"Expected marital_status 'single' for '{family_structure_value}', got '{marital_status_value}'.",
                )
            )
    elif family_structure_value == "living with roommates":
        if not isinstance(household_size, int) or household_size < 2:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size >= 2 for '{family_structure_value}', got {household_size}.",
                )
            )
    elif family_structure_value == "single parent with one child":
        if household_size != 2:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size 2 for '{family_structure_value}', got {household_size}.",
                )
            )
        if marital_status_value != "single":
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="marital_status",
                    message=f"Expected marital_status 'single' for '{family_structure_value}', got '{marital_status_value}'.",
                )
            )
    elif family_structure_value == "multi-generational household":
        if not isinstance(household_size, int) or household_size < 4:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="household_size",
                    message=f"Expected household_size >= 4 for '{family_structure_value}', got {household_size}.",
                )
            )
    else:
        issues.append(
            PersonaValidationIssue(
                persona_id=persona_id,
                check_name="family_structure",
                message=f"Unsupported family_structure '{family_structure_value}'.",
            )
        )

    return issues


def _persona_id(persona: PersonaSkill) -> str:
    return str(persona.profile.basic_identity.get("synthetic_user_id", "unknown"))


def _is_public_figure_perspective(persona: PersonaSkill) -> bool:
    extensions = getattr(persona.profile, "extensions", {})
    if not isinstance(extensions, dict):
        return False
    return extensions.get("persona_kind") == "public_figure_perspective"


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_non_empty_string(item) for item in value)


def _non_empty_string_or_object(value: object) -> bool:
    return _non_empty_string(value) or (isinstance(value, dict) and bool(value))


def _non_empty_string_or_object_or_string_list(value: object) -> bool:
    return _non_empty_string(value) or _non_empty_string_list(value) or (isinstance(value, dict) and bool(value))


OPTIONAL_STRUCTURED_SECTIONS: dict[str, tuple[str, ...]] = {
    "human_difference_axes": (
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
    ),
    "banking_context": (
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
    ),
    "persona_schema_meta": (
        "schema_version",
        "source_version",
        "upgrade_strategy",
        "optional_blocks_present",
        "canonicalizations_applied",
    ),
    "relational_defense_model": (
        "self_other_position",
        "default_trust_posture",
        "defensive_style",
        "status_sensitivity",
        "attribution_style",
        "conflict_pattern",
        "withdrawal_pattern",
    ),
    "communication_behavior_model": (
        "baseline_answer_length",
        "clarification_tendency",
        "misunderstanding_risk",
        "topic_drift_tendency",
        "memory_lapse_tendency",
        "revision_tendency",
        "disinterest_expression_style",
        "permission_sensitivity",
        "pricing_confusion_risk",
        "dropoff_style",
    ),
}


def validate_persona_artifact(persona: PersonaSkill) -> list[PersonaValidationIssue]:
    issues: list[PersonaValidationIssue] = []
    persona_id = _persona_id(persona)

    required_sections: dict[str, tuple[dict[str, object], dict[str, str]]] = {
        "basic_identity": (
            persona.profile.basic_identity,
            {
                "synthetic_user_id": "string",
                "name": "string",
                "age": "int",
                "gender": "string",
                "location": "string",
                "language": "string_list",
                "occupation": "string",
                "education_level": "string",
                "income_level": "string",
                "marital_status": "string",
                "family_structure": "string",
                "household_size": "int",
                "living_area": "string",
                "housing_status": "string",
            },
        ),
        "personality_belief": (
            persona.profile.personality_belief,
            {
                "decision_style": "string",
                "risk_tolerance": "string",
                "trust_orientation": "string",
            },
        ),
        "technology_profile": (
            persona.profile.technology_profile,
            {
                "tech_savviness": "string",
                "privacy_concern": "string",
                "automation_openness": "string",
            },
        ),
        "economic_profile": (
            persona.profile.economic_profile,
            {
                "price_sensitivity": "string",
                "subscription_tolerance": "string",
                "switching_cost": "string",
            },
        ),
        "values": (
            persona.profile.values,
            {
                "core_values": "string_list",
                "fears": "string_list",
                "aspirations": "string_list",
            },
        ),
        "life_story": (
            persona.profile.life_story,
            {
                "career_path": "string",
                "current_daily_routine": "string",
                "frustrations": "string_list",
            },
        ),
        "behavior_profile": (
            persona.profile.behavior_profile,
            {
                "buying_behavior": "string",
                "decision_blockers": "string_list",
            },
        ),
        "problem_context": (
            persona.profile.problem_context,
            {
                "active_pain_points": "string_list",
                "jobs_to_be_done": "string_list",
                "willingness_to_pay": "string_or_object",
            },
        ),
        "sensitive_reality_layer": (
            persona.profile.sensitive_reality_layer,
            {
                "fairness_and_inclusion_profile": "string_or_object",
                "response_boundaries": "string_list",
            },
        ),
        "audit_evidence_layer": (
            persona.profile.audit_evidence_layer,
            {
                "persona_generation_method": "string",
                "evidence_grade": "string",
                "synthetic_only_disclaimer": "string",
                "do_not_use_for": "string_list",
            },
        ),
        "decision_policy": (
            persona.decision_policy,
            {
                "adoption_style": "string",
                "trust_requirements": "string_list",
                "rejection_triggers": "string_list",
                "proof_requirements": "string_list",
            },
        ),
        "response_style": (
            persona.response_style,
            {
                "articulation_level": "string",
                "directness": "string",
                "detail_tendency": "string",
            },
        ),
        "seed": (
            persona.seed.to_dict(),
            {
                "seed_id": "string",
                "panel_role": "string",
                "age_band": "string",
                "location_type": "string",
                "household_structure": "string",
                "occupation_band": "string",
                "occupation_title": "string",
                "income_band": "string",
                "education_band": "string",
                "language": "string_list",
                "device_environment": "string",
                "payment_environment": "string",
                "schedule_pressure": "string",
                "budget_flexibility": "string",
                "caregiving_load": "string",
                "trust_threshold": "string",
                "switching_cost_level": "string",
                "privacy_risk_tolerance": "string",
                "digital_literacy_ceiling": "string",
            },
        ),
    }

    for section_name, (section_payload, required_fields) in required_sections.items():
        if not isinstance(section_payload, dict):
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="section_type",
                    message=f"Section '{section_name}' must be an object.",
                )
            )
            continue

        for field_name, field_type in required_fields.items():
            value = section_payload.get(field_name)
            if field_type == "string":
                valid = _non_empty_string(value)
            elif field_type == "string_list":
                valid = _non_empty_string_list(value)
            elif field_type == "int":
                valid = isinstance(value, int) and not isinstance(value, bool)
            elif field_type == "string_or_object":
                valid = _non_empty_string_or_object(value)
            else:
                valid = value is not None

            if not valid:
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="required_field",
                        message=f"Section '{section_name}' has invalid or missing field '{field_name}'.",
                    )
                )

    if not _non_empty_string(persona.skill_version):
        issues.append(
            PersonaValidationIssue(
                persona_id=persona_id,
                check_name="skill_version",
                message="skill_version must be a non-empty string.",
            )
        )

    if not _non_empty_string(persona.narrative):
        issues.append(
            PersonaValidationIssue(
                persona_id=persona_id,
                check_name="narrative",
                message="persona narrative must not be empty.",
            )
        )

    profile_disclaimer = persona.profile.audit_evidence_layer.get("synthetic_only_disclaimer", "")
    audit_disclaimer = persona.audit.get("synthetic_only_disclaimer", "")
    if profile_disclaimer != audit_disclaimer:
        issues.append(
            PersonaValidationIssue(
                persona_id=persona_id,
                check_name="audit_sync",
                message="synthetic_only_disclaimer differs between profile and audit payload.",
            )
        )

    profile_do_not_use = persona.profile.audit_evidence_layer.get("do_not_use_for", [])
    audit_do_not_use = persona.audit.get("do_not_use_for", [])
    if profile_do_not_use != audit_do_not_use:
        issues.append(
            PersonaValidationIssue(
                persona_id=persona_id,
                check_name="audit_sync",
                message="do_not_use_for differs between profile and audit payload.",
            )
        )

    for section_name, required_fields in OPTIONAL_STRUCTURED_SECTIONS.items():
        section_payload = getattr(persona.profile, section_name, {})
        if section_payload in ({}, None):
            continue
        if not isinstance(section_payload, dict):
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="section_type",
                    message=f"Optional section '{section_name}' must be an object when present.",
                )
            )
            continue
        for field_name in required_fields:
            if not _non_empty_string_or_object_or_string_list(section_payload.get(field_name)):
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="required_field",
                        message=f"Optional section '{section_name}' has invalid or missing field '{field_name}'.",
                    )
                )
    behavior_rules = getattr(persona.profile, "behavior_generation_rules", [])
    if behavior_rules not in ([], None):
        if not isinstance(behavior_rules, list):
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="section_type",
                    message="Optional section 'behavior_generation_rules' must be a list when present.",
                )
            )
        else:
            for item in behavior_rules:
                if not isinstance(item, dict) or not _non_empty_string_or_object(item.get("because")):
                    issues.append(
                        PersonaValidationIssue(
                            persona_id=persona_id,
                            check_name="required_field",
                            message="Optional section 'behavior_generation_rules' must contain objects with a non-empty 'because' field.",
                        )
                    )
                    break

    return issues


def ensure_valid_persona_artifact(persona: PersonaSkill) -> None:
    issues = validate_persona_artifact(persona)
    if issues:
        raise PersonaArtifactValidationError(issues)


def validate_personas(personas: list[PersonaSkill]) -> list[PersonaValidationIssue]:
    issues: list[PersonaValidationIssue] = []
    expected_languages = _expected_languages_by_location()

    id_counts = Counter(_persona_id(persona) for persona in personas)
    for persona_id, count in id_counts.items():
        if count > 1:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="duplicate_id",
                    message=f"Synthetic user ID appears {count} times.",
                )
            )

    name_counts = Counter(persona.profile.basic_identity["name"] for persona in personas)

    for persona in personas:
        issues.extend(validate_persona_artifact(persona))
        identity = persona.profile.basic_identity
        persona_id = _persona_id(persona)
        name_value = identity.get("name", "")
        if not _is_public_figure_perspective(persona):
            first_name = name_value.split()[0] if _non_empty_string(name_value) else ""
            gender = str(identity.get("gender", ""))

            if not first_name:
                pass
            elif gender not in FIRST_NAMES_BY_GENDER:
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="unsupported_gender",
                        message=f"Gender '{gender}' has no configured name pool.",
                    )
                )
            elif first_name not in FIRST_NAMES_BY_GENDER[gender]:
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="name_gender",
                        message=f"First name '{first_name}' does not match gender '{gender}'.",
                    )
                )

            issues.extend(
                _validate_household_consistency(
                    persona_id=persona_id,
                    family_structure=identity.get("family_structure"),
                    household_size=identity.get("household_size"),
                    marital_status=identity.get("marital_status"),
                )
            )

            location = identity.get("location")
            raw_languages = identity.get("language", [])
            languages = set(raw_languages) if isinstance(raw_languages, list) else set()
            if location not in expected_languages:
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="location",
                        message=f"Location '{location}' is not in the configured location catalog.",
                    )
                )
            elif not languages.issubset(expected_languages[location]):
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="location_language",
                        message=f"Languages {sorted(languages)} do not match configured options for '{location}'.",
                    )
                )

            if _non_empty_string(name_value) and name_counts[name_value] > 1:
                issues.append(
                    PersonaValidationIssue(
                        persona_id=persona_id,
                        check_name="duplicate_name",
                        message=f"Name '{name_value}' appears {name_counts[name_value]} times in the library.",
                    )
                )

        disclaimer = persona.audit.get("synthetic_only_disclaimer", "").strip()
        if not disclaimer:
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="missing_disclaimer",
                    message="Synthetic-only disclaimer is missing.",
                )
            )

        if not persona.audit.get("do_not_use_for"):
            issues.append(
                PersonaValidationIssue(
                    persona_id=persona_id,
                    check_name="missing_do_not_use_for",
                    message="do_not_use_for should not be empty.",
                )
            )

    return issues
