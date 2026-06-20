from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import FounderBrief, PanelSpec

FOUNDER_BRIEF_REQUIRED_FIELDS = {
    "brief_id",
    "project_name",
    "problem_statement",
    "target_market",
    "offered_solution",
    "validation_goal",
}

FOUNDER_BRIEF_OPTIONAL_FIELDS = {
    "pricing_hypothesis",
    "landing_page_text",
    "mvp_scope",
    "concierge_mvp_idea",
    "assumptions",
    "constraints",
    "known_risks",
}

ALLOWED_FOUNDER_BRIEF_FIELDS = FOUNDER_BRIEF_REQUIRED_FIELDS | FOUNDER_BRIEF_OPTIONAL_FIELDS


@dataclass(slots=True)
class InputValidationError(ValueError):
    issues: list[str]

    def __str__(self) -> str:
        if not self.issues:
            return "Input validation failed."
        return "Input validation failed: " + "; ".join(self.issues)


def _expect_dict(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputValidationError([f"{context} must be a JSON object."])
    return payload


def _require_non_empty_string(payload: dict[str, Any], key: str, issues: list[str]) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        issues.append(f"'{key}' must be a string.")
        return ""
    normalized = value.strip()
    if not normalized:
        issues.append(f"'{key}' must not be empty.")
    return normalized


def _optional_string(payload: dict[str, Any], key: str, issues: list[str]) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str):
        issues.append(f"'{key}' must be a string when provided.")
        return ""
    return value.strip()


def _optional_string_list(payload: dict[str, Any], key: str, issues: list[str]) -> list[str]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        issues.append(f"'{key}' must be an array of strings when provided.")
        return []
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            issues.append(f"'{key}[{index}]' must be a string.")
            continue
        stripped = item.strip()
        if not stripped:
            issues.append(f"'{key}[{index}]' must not be empty.")
            continue
        normalized.append(stripped)
    return normalized


def validate_founder_brief_payload(payload: Any) -> FounderBrief:
    payload = _expect_dict(payload, "Founder brief")
    issues: list[str] = []

    unexpected = sorted(set(payload) - ALLOWED_FOUNDER_BRIEF_FIELDS)
    for key in unexpected:
        issues.append(f"Unexpected field '{key}' in founder brief.")

    missing = sorted(field for field in FOUNDER_BRIEF_REQUIRED_FIELDS if field not in payload)
    for key in missing:
        issues.append(f"Missing required field '{key}'.")

    brief = FounderBrief(
        brief_id=_require_non_empty_string(payload, "brief_id", issues),
        project_name=_require_non_empty_string(payload, "project_name", issues),
        problem_statement=_require_non_empty_string(payload, "problem_statement", issues),
        target_market=_require_non_empty_string(payload, "target_market", issues),
        offered_solution=_require_non_empty_string(payload, "offered_solution", issues),
        validation_goal=_require_non_empty_string(payload, "validation_goal", issues),
        pricing_hypothesis=_optional_string(payload, "pricing_hypothesis", issues),
        landing_page_text=_optional_string(payload, "landing_page_text", issues),
        mvp_scope=_optional_string(payload, "mvp_scope", issues),
        concierge_mvp_idea=_optional_string(payload, "concierge_mvp_idea", issues),
        assumptions=_optional_string_list(payload, "assumptions", issues),
        constraints=_optional_string_list(payload, "constraints", issues),
        known_risks=_optional_string_list(payload, "known_risks", issues),
    )

    if issues:
        raise InputValidationError(issues)
    return brief


def load_and_validate_founder_brief(path: Path) -> FounderBrief:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise InputValidationError([f"Founder brief file not found: {path}"])
    except json.JSONDecodeError as exc:
        raise InputValidationError([f"Founder brief is not valid JSON: {exc.msg} at line {exc.lineno}."]) from exc
    return validate_founder_brief_payload(payload)


def validate_panel_spec(panel_spec: PanelSpec, *, allowed_panel_types: set[str] | None = None) -> PanelSpec:
    issues: list[str] = []

    panel_type = panel_spec.panel_type.strip() if isinstance(panel_spec.panel_type, str) else ""
    if not panel_type:
        issues.append("'panel_type' must be a non-empty string.")
    elif allowed_panel_types is not None and panel_type not in allowed_panel_types:
        issues.append(f"'panel_type' must be one of: {', '.join(sorted(allowed_panel_types))}.")

    if not isinstance(panel_spec.sample_size, int) or isinstance(panel_spec.sample_size, bool):
        issues.append("'sample_size' must be an integer.")
    elif panel_spec.sample_size <= 0:
        issues.append("'sample_size' must be greater than 0.")

    if panel_spec.random_seed is not None:
        if not isinstance(panel_spec.random_seed, int) or isinstance(panel_spec.random_seed, bool):
            issues.append("'random_seed' must be an integer when provided.")
        elif panel_spec.random_seed < 0:
            issues.append("'random_seed' must be 0 or greater.")

    if not isinstance(panel_spec.filters, dict):
        issues.append("'filters' must be a key-value object.")
    else:
        for key, value in panel_spec.filters.items():
            if not isinstance(key, str) or not key.strip():
                issues.append("Sampling filter keys must be non-empty strings.")
                continue
            if isinstance(value, str):
                if not value.strip():
                    issues.append(f"Sampling filter '{key}' must not be empty.")
            elif isinstance(value, list):
                if not value:
                    issues.append(f"Sampling filter '{key}' list must not be empty.")
                for index, item in enumerate(value):
                    if not isinstance(item, str) or not item.strip():
                        issues.append(f"Sampling filter '{key}[{index}]' must be a non-empty string.")
            else:
                issues.append(f"Sampling filter '{key}' must be a string or list of strings.")

    if panel_spec.preset_name and not isinstance(panel_spec.preset_name, str):
        issues.append("'preset_name' must be a string when provided.")

    if issues:
        raise InputValidationError(issues)

    return PanelSpec(
        panel_type=panel_type,
        sample_size=panel_spec.sample_size,
        random_seed=panel_spec.random_seed,
        filters=panel_spec.filters,
        preset_name=panel_spec.preset_name.strip() if isinstance(panel_spec.preset_name, str) else "",
    )
