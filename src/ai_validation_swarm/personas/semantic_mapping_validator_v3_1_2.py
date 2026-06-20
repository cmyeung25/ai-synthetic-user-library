from __future__ import annotations

from typing import Any

from ai_validation_swarm.domain.models import PersonaSkill

GENERIC_WORKFLOW_OBJECTION_TOKENS = {
    "visible win",
    "what does this replace",
    "replace",
    "workflow",
    "setup",
    "momentum",
    "subscription",
    "trial",
}

BOUNDARY_RULE_TOKENS = {
    "third-party data",
    "private third-party data",
    "without a clear reason",
    "share private",
}

ALLOWED_THEME_TOKENS = {
    "privacy_and_data": {
        "permission",
        "retention",
        "model training",
        "training",
        "deletion",
        "third-party sharing",
        "surveillance",
        "review before action",
        "access",
        "broad",
        "scope",
    },
    "health_or_wellbeing_sensitivity": {
        "guilt",
        "moralizing",
        "shame",
        "public progress",
        "surveillance",
        "thin data",
        "compliance",
        "sensitive data",
        "wellbeing",
        "habit",
    },
    "workplace_visibility": {
        "unfinished setup",
        "public failure",
        "visible",
        "visibility",
        "review",
        "reputation",
        "learning",
        "visible incompetence",
        "draft",
        "unprepared",
        "look",
        "week one",
    },
    "identity_disclosure": {
        "forced labels",
        "labeling",
        "binary",
        "title",
        "public profile",
        "disclosure",
        "prefer-not-to-say",
        "visibility",
        "control",
    },
}


def _normalize(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if value is None:
        return ""
    return str(value).strip().lower()


def _find_contamination(block_key: str, what_reduces_trust: str) -> list[str]:
    normalized = _normalize(what_reduces_trust)
    issues: list[str] = []
    if not normalized:
        issues.append("missing what_reduces_trust text")
        return issues

    if block_key == "privacy_and_data":
        if any(token in normalized for token in GENERIC_WORKFLOW_OBJECTION_TOKENS):
            issues.append("contains generic workflow or visible-win objection language")
    if block_key == "health_or_wellbeing_sensitivity":
        if any(token in normalized for token in BOUNDARY_RULE_TOKENS):
            issues.append("contains boundary rule language instead of health-specific trust loss")
        if "pricing" in normalized or "replace" in normalized:
            issues.append("contains pricing or workflow replacement language")
    if block_key == "workplace_visibility":
        if "price" in normalized or "subscription" in normalized:
            issues.append("contains pricing logic instead of visibility or reputation risk")
    if block_key == "identity_disclosure":
        if "trial" in normalized or "visible win" in normalized:
            issues.append("contains trial or momentum language instead of disclosure control")

    allowed_tokens = ALLOWED_THEME_TOKENS.get(block_key, set())
    if allowed_tokens and not any(token in normalized for token in allowed_tokens):
        issues.append("lacks scenario-specific trust vocabulary")
    return issues


def build_semantic_mapping_report_v3_1_2(
    persona: PersonaSkill,
    *,
    auto_fixes_applied: list[str] | None = None,
) -> dict[str, Any]:
    scenarios = persona.profile.sensitive_scenario_reactions
    field_contamination_found: list[dict[str, str]] = []
    failed_fields: list[str] = []
    warnings: list[str] = []

    for block_key in (
        "privacy_and_data",
        "health_or_wellbeing_sensitivity",
        "workplace_visibility",
        "identity_disclosure",
    ):
        block = scenarios.get(block_key, {})
        issues = _find_contamination(block_key, _normalize(block.get("what_reduces_trust", "")))
        if not issues:
            continue
        failed_fields.append(f"{block_key}.what_reduces_trust")
        field_contamination_found.append(
            {
                "field": f"{block_key}.what_reduces_trust",
                "issue": "; ".join(issues),
            }
        )

    if "health_or_wellbeing_sensitivity.what_reduces_trust" in failed_fields:
        warnings.append("Health or wellbeing trust reducer still sounds like a generic boundary rule or non-health objection.")
    if "privacy_and_data.what_reduces_trust" in failed_fields:
        warnings.append("Privacy trust reducer still sounds like workflow momentum instead of access or retention risk.")

    status = "pass"
    if failed_fields:
        status = "fail"
    elif warnings:
        status = "warning"

    return {
        "status": status,
        "field_contamination_found": field_contamination_found,
        "auto_fixes_applied": list(auto_fixes_applied or []),
        "failed_fields": failed_fields,
        "warnings": warnings,
        "human_review_needed": True,
    }
