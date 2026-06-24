from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.storage.files import ensure_dir, read_json, write_json


def load_approved_facilitator_learning_registry(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "artifact_version": "v1",
            "approved_rules": [],
            "synthetic_only_disclaimer": (
                "Approved facilitator learning rules are generic heuristics distilled from synthetic audit workflows. "
                "They still require human judgment in use."
            ),
        }
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Approved facilitator learning registry must be a JSON object.")
    rules = payload.get("approved_rules")
    if not isinstance(rules, list):
        raise ValueError("Approved facilitator learning registry must contain an approved_rules list.")
    payload.setdefault("artifact_version", "v1")
    payload.setdefault(
        "synthetic_only_disclaimer",
        "Approved facilitator learning rules are generic heuristics distilled from synthetic audit workflows. They still require human judgment in use.",
    )
    normalized_rules: list[dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized.setdefault("status", "approved")
        normalized_rules.append(normalized)
    payload["approved_rules"] = normalized_rules
    return payload


def build_approved_facilitator_learning_prompt_fragment(
    path: Path | None,
    *,
    max_rules: int = 5,
) -> tuple[str, list[str]]:
    registry = load_approved_facilitator_learning_registry(path)
    approved_rules = [
        item for item in registry.get("approved_rules", [])
        if isinstance(item, dict) and str(item.get("status", "approved")).strip() == "approved"
    ]
    if not approved_rules:
        return "", []
    selected = approved_rules[: max(0, int(max_rules))]
    lines = [
        "HUMAN-APPROVED FACILITATOR LEARNING RULES:",
        "Apply these only when they are supported by the actual transcript.",
        "Treat them as generic interviewing heuristics, never as domain assumptions, expected pain points, or mandatory outcomes.",
        "",
    ]
    rule_ids: list[str] = []
    for item in selected:
        rule_id = str(item.get("rule_id", "")).strip()
        rule = str(item.get("rule", "")).strip()
        if not rule:
            continue
        label = f"{rule_id}: " if rule_id else ""
        lines.append(f"- {label}{rule}")
        if rule_id:
            rule_ids.append(rule_id)
    fragment = "\n".join(lines).rstrip()
    return (fragment if len(lines) > 4 else ""), rule_ids


def promote_facilitator_learning_rules(
    *,
    report_path: Path,
    registry_path: Path,
    rule_ids: list[str],
    approved_by: str = "",
    approval_note: str = "",
) -> dict[str, Any]:
    report = read_json(report_path)
    candidates = report.get("human_review_candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("Facilitator audit learning report must contain a human_review_candidates list.")
    wanted = [item.strip() for item in rule_ids if str(item).strip()]
    if not wanted:
        raise ValueError("At least one rule_id must be supplied for promotion.")
    by_id = {
        str(item.get("rule_id", "")).strip(): item
        for item in candidates
        if isinstance(item, dict) and str(item.get("rule_id", "")).strip()
    }
    missing = [rule_id for rule_id in wanted if rule_id not in by_id]
    if missing:
        raise ValueError(f"Requested rule_ids are not available for human review promotion: {missing}")

    registry = load_approved_facilitator_learning_registry(registry_path)
    existing_rules = {
        str(item.get("rule_id", "")).strip(): item
        for item in registry.get("approved_rules", [])
        if isinstance(item, dict) and str(item.get("rule_id", "")).strip()
    }
    source_label = str(report.get("label", "")).strip()
    for rule_id in wanted:
        candidate = by_id[rule_id]
        existing_rules[rule_id] = {
            "rule_id": rule_id,
            "rule": str(candidate.get("rule", "")).strip(),
            "source_tags": list(candidate.get("source_tags", [])),
            "confidence": str(candidate.get("confidence", "unknown")),
            "support_run_count": int(candidate.get("support_run_count", 0) or 0),
            "support_persona_count": int(candidate.get("support_persona_count", 0) or 0),
            "candidate_strength": str(candidate.get("candidate_strength", "unknown")),
            "approved_at": utc_now_iso(),
            "approved_by": approved_by.strip() or "manual_review",
            "approval_note": approval_note.strip(),
            "source_report": str(report_path),
            "source_label": source_label,
            "status": "approved",
        }
    registry["artifact_version"] = "v1"
    registry["updated_at"] = utc_now_iso()
    registry["approved_rules"] = sorted(existing_rules.values(), key=lambda item: str(item.get("rule_id", "")).casefold())
    ensure_dir(registry_path.parent)
    write_json(registry_path, registry)
    markdown_path = registry_path.with_suffix(".md")
    markdown_path.write_text(render_approved_facilitator_learning_registry(registry), encoding="utf-8")
    return registry


def disable_facilitator_learning_rules(
    *,
    registry_path: Path,
    rule_ids: list[str],
    disabled_by: str = "",
    disable_note: str = "",
) -> dict[str, Any]:
    registry = load_approved_facilitator_learning_registry(registry_path)
    wanted = [item.strip() for item in rule_ids if str(item).strip()]
    if not wanted:
        raise ValueError("At least one rule_id must be supplied for disable.")
    rules = registry.get("approved_rules", [])
    by_id = {
        str(item.get("rule_id", "")).strip(): item
        for item in rules
        if isinstance(item, dict) and str(item.get("rule_id", "")).strip()
    }
    missing = [rule_id for rule_id in wanted if rule_id not in by_id]
    if missing:
        raise ValueError(f"Requested rule_ids were not found in the approved registry: {missing}")
    for rule_id in wanted:
        item = by_id[rule_id]
        item["status"] = "disabled"
        item["disabled_at"] = utc_now_iso()
        item["disabled_by"] = disabled_by.strip() or "manual_review"
        item["disable_note"] = disable_note.strip()
    registry["updated_at"] = utc_now_iso()
    ensure_dir(registry_path.parent)
    write_json(registry_path, registry)
    markdown_path = registry_path.with_suffix(".md")
    markdown_path.write_text(render_approved_facilitator_learning_registry(registry), encoding="utf-8")
    return registry


def render_approved_facilitator_learning_registry(registry: dict[str, Any]) -> str:
    rules = registry.get("approved_rules", [])
    active_count = sum(1 for item in rules if str(item.get("status", "approved")).strip() == "approved")
    disabled_count = sum(1 for item in rules if str(item.get("status", "")).strip() == "disabled")
    lines = [
        "# Approved Facilitator Learning Rules", "",
        f"> {registry.get('synthetic_only_disclaimer', '')}", "",
        f"- Total rules: {len(rules)}",
        f"- Active rules: {active_count}",
        f"- Disabled rules: {disabled_count}",
        f"- Updated at: {registry.get('updated_at', '')}", "",
    ]
    for item in rules:
        lines.extend([
            f"## {item.get('rule_id', '(no id)')}", "",
            f"- Rule: {item.get('rule', '')}",
            f"- Status: {item.get('status', 'approved')}",
            f"- Candidate strength: {item.get('candidate_strength', 'unknown')}",
            f"- Support: runs={item.get('support_run_count', 0)}, personas={item.get('support_persona_count', 0)}",
            f"- Approved by: {item.get('approved_by', '')}",
            f"- Source label: {item.get('source_label', '')}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
