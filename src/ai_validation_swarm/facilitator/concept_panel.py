from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import uuid

from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.facilitator.concept_protocols import (
    DEFAULT_CONCEPT_LABEL,
    DEFAULT_CONCEPT_PROTOCOL,
)
from ai_validation_swarm.facilitator.optimism import derive_panel_over_optimism_risks
from ai_validation_swarm.facilitator.providers import FacilitatorProvider
from ai_validation_swarm.observer.runtime import ObserverControlledInterviewRuntime
from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.storage.files import ensure_dir, read_json, write_json


DEFAULT_TOPIC_LABEL = "Concept Validation"
DEFAULT_LANGUAGE = "Natural Cantonese Traditional Chinese"
DEFAULT_CORE_ASSUMPTION_COUNT = 8
DEFAULT_CONCEPT_PANEL_SOFT_TURN_LIMIT = 12
DEFAULT_CONCEPT_PANEL_HARD_TURN_LIMIT = 16

FOLLOWUP_RESEARCH_GOAL = (
    "Interview synthetic personas about follow-up behaviour, trust boundaries, setup tolerance, "
    "pricing conditions, retention risk, and founder assumptions for AI Follow-up Copilot."
)
FOLLOWUP_PRODUCT_CONTEXT = (
    "AI Follow-up Copilot concept validation using the versioned concept interview protocol."
)

DEPTH_PROBE_LABELS = {
    "threshold_probe": "Threshold Probe",
    "contrast_probe": "Contrast / Non-Use Probe",
    "driver_deepening_probe": "Driver-Deepening Probe",
    "output_to_decision_probe": "Output-to-Decision Probe",
}


def _persona_ids(data_dir: Path, selected: list[str] | None = None) -> list[str]:
    available = sorted(
        path.name for path in data_dir.iterdir()
        if path.is_dir() and (path / "v5" / "profile.json").exists()
    )
    if not selected:
        return available
    wanted = sorted(dict.fromkeys(selected))
    missing = [persona_id for persona_id in wanted if persona_id not in set(available)]
    if missing:
        raise ValueError(f"Personas were not found in the library: {missing}")
    return wanted


def _resolve_concept_panel_turn_policy(
    *,
    max_turns: int | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
) -> tuple[int, int]:
    if soft_turn_limit is None and hard_turn_limit is None and max_turns is None:
        return DEFAULT_CONCEPT_PANEL_SOFT_TURN_LIMIT, DEFAULT_CONCEPT_PANEL_HARD_TURN_LIMIT
    baseline = max_turns if max_turns is not None else DEFAULT_CONCEPT_PANEL_SOFT_TURN_LIMIT
    resolved_soft = soft_turn_limit if soft_turn_limit is not None else (
        max_turns if max_turns is not None else DEFAULT_CONCEPT_PANEL_SOFT_TURN_LIMIT
    )
    resolved_hard = hard_turn_limit if hard_turn_limit is not None else (
        max_turns if max_turns is not None else max(DEFAULT_CONCEPT_PANEL_HARD_TURN_LIMIT, resolved_soft)
    )
    return ObserverControlledInterviewRuntime._resolve_turn_limits(
        max_turns=baseline,
        soft_turn_limit=resolved_soft,
        hard_turn_limit=resolved_hard,
    )


def _summary_payload(
    run_id: str,
    interviews: list[dict[str, Any]],
    *,
    topic_label: str,
    language: str,
    core_assumption_count: int,
) -> dict[str, Any]:
    assumption_rows: dict[int, dict[str, Any]] = {}
    additional_findings: list[dict[str, Any]] = []
    driver_type_counts: Counter[str] = Counter()
    recurring_drivers: dict[str, dict[str, Any]] = {}
    recurring_constraints: dict[str, dict[str, Any]] = {}
    recurring_tensions: dict[str, dict[str, Any]] = {}
    recurring_facilitator_failure_modes: dict[str, dict[str, Any]] = {}
    recurring_missed_followups: dict[str, dict[str, Any]] = {}
    recurring_misclassified_drivers: dict[str, dict[str, Any]] = {}
    recurring_missing_depth_probes: dict[str, dict[str, Any]] = {}
    depth_completion_counts: Counter[str] = Counter()
    realism_scores: list[float] = []

    def _normalize_key(value: str) -> str:
        return " ".join(str(value).strip().casefold().split())

    def _add_grouped_item(
        bucket: dict[str, dict[str, Any]],
        *,
        key: str,
        label: str,
        item_type: str = "",
        persona_id: str,
        persona_name: str,
        confidence: str,
        why: str = "",
    ) -> None:
        row = bucket.setdefault(key, {
            "label": label,
            "item_type": item_type,
            "persona_ids": set(),
            "persona_names": [],
            "confidence_counts": Counter(),
            "example_why": why,
        })
        if persona_id not in row["persona_ids"]:
            row["persona_ids"].add(persona_id)
            row["persona_names"].append(persona_name)
        row["confidence_counts"][confidence or "unknown"] += 1
        if not row.get("example_why") and why:
            row["example_why"] = why

    for interview in interviews:
        report = interview.get("report", {})
        driver_trace = interview.get("persona_driver_trace", {})
        realism = interview.get("conversation_realism", {})
        if isinstance(realism.get("overall_score"), (int, float)):
            realism_scores.append(float(realism.get("overall_score", 0)))
        for index, item in enumerate(report.get("assumption_validation", []), start=1):
            if index > core_assumption_count:
                additional_findings.append({
                    "persona_id": interview["persona_id"],
                    "persona_name": interview["persona_name"],
                    "finding": item.get("assumption", ""),
                    "status": item.get("status", "unknown"),
                    "rationale": item.get("rationale", ""),
                })
                continue
            row = assumption_rows.setdefault(index, {
                "assumption": item.get("assumption", f"assumption_{index}"),
                "status_counts": Counter(),
                "persona_results": [],
            })
            status = item.get("status", "unknown")
            row["status_counts"][status] += 1
            row["persona_results"].append({
                "persona_id": interview["persona_id"],
                "persona_name": interview["persona_name"],
                "status": status,
                "rationale": item.get("rationale", ""),
            })

        for driver in driver_trace.get("likely_drivers", []):
            driver_type = str(driver.get("driver_type", "other"))
            driver_label = str(driver.get("driver", "")).strip()
            if not driver_label:
                continue
            driver_type_counts[driver_type] += 1
            _add_grouped_item(
                recurring_drivers,
                key=f"{driver_type}|{_normalize_key(driver_label)}",
                label=driver_label,
                item_type=driver_type,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence=str(driver.get("confidence", "unknown")),
                why=str(driver.get("why_it_matters_here", "")),
            )
        for constraint in driver_trace.get("unspoken_constraints", []):
            constraint_label = str(constraint.get("constraint", "")).strip()
            if not constraint_label:
                continue
            _add_grouped_item(
                recurring_constraints,
                key=_normalize_key(constraint_label),
                label=constraint_label,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence=str(constraint.get("confidence", "unknown")),
                why=str(constraint.get("why_likely", "")),
            )
        for tension in driver_trace.get("value_tensions", []):
            tension_label = str(tension.get("tension", "")).strip()
            if not tension_label:
                continue
            _add_grouped_item(
                recurring_tensions,
                key=_normalize_key(tension_label),
                label=tension_label,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence=str(tension.get("confidence", "unknown")),
                why=f"{tension.get('side_a', '')} vs {tension.get('side_b', '')}".strip(),
            )
        audit_feedback = interview.get("facilitator_audit_feedback", {})
        audit_summary = audit_feedback.get("summary", {})
        failure_mode = str(audit_summary.get("primary_failure_mode", "")).strip()
        if failure_mode:
            _add_grouped_item(
                recurring_facilitator_failure_modes,
                key=_normalize_key(failure_mode),
                label=failure_mode,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence="observed",
                why=str(audit_summary.get("depth_vs_coverage_assessment", "")),
            )
        for follow_up in audit_feedback.get("high_value_missed_followups", []):
            trigger_type = str(follow_up.get("trigger_type", "")).strip() or "unknown"
            learning = str(follow_up.get("generic_learning", "")).strip()
            question = str(follow_up.get("missed_followup_question", "")).strip()
            if not learning and not question:
                continue
            key = f"{trigger_type}|{_normalize_key(learning or question)}"
            _add_grouped_item(
                recurring_missed_followups,
                key=key,
                label=question or learning,
                item_type=trigger_type,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence=str(follow_up.get("priority", "unknown")),
                why=learning,
            )
        for pattern in audit_feedback.get("likely_misclassified_driver_patterns", []):
            underlying_driver = str(pattern.get("possible_underlying_driver", "")).strip()
            learning = str(pattern.get("generic_learning", "")).strip()
            surface_frame = str(pattern.get("observed_surface_frame", "")).strip()
            if not underlying_driver and not learning:
                continue
            key = _normalize_key(learning or underlying_driver or surface_frame)
            _add_grouped_item(
                recurring_misclassified_drivers,
                key=key,
                label=underlying_driver or learning or surface_frame,
                item_type=surface_frame,
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence="observed",
                why=learning,
            )
        coverage_status = interview.get("coverage_status", {}) or {}
        depth_requirements = list(coverage_status.get("depth_requirements", []) or [])
        depth_missing = list(coverage_status.get("depth_missing", []) or [])
        if depth_requirements:
            if coverage_status.get("depth_complete"):
                depth_completion_counts["complete"] += 1
            elif depth_missing:
                depth_completion_counts["incomplete"] += 1
            else:
                depth_completion_counts["unknown"] += 1
        else:
            depth_completion_counts["not_tracked"] += 1
        for probe in depth_missing:
            label = DEPTH_PROBE_LABELS.get(str(probe), str(probe))
            _add_grouped_item(
                recurring_missing_depth_probes,
                key=_normalize_key(str(probe)),
                label=label,
                item_type=str(probe),
                persona_id=interview["persona_id"],
                persona_name=interview["persona_name"],
                confidence="missing",
                why="This depth probe type was still missing at interview close.",
            )

    problem_counts = Counter(
        item.get("report", {}).get("problem_evidence", {}).get("strength", "unknown")
        for item in interviews
    )
    quality_scores = [
        item.get("quality", {}).get("scores", {}).get("overall") for item in interviews
        if isinstance(item.get("quality", {}).get("scores", {}).get("overall"), int)
    ]
    return {
        "run_id": run_id,
        "topic": topic_label,
        "language": language,
        "core_assumption_count": core_assumption_count,
        "persona_count": len(interviews),
        "problem_strength_counts": dict(problem_counts),
        "average_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        "average_conversation_realism_score": (
            round(sum(realism_scores) / len(realism_scores), 2) if realism_scores else None
        ),
        "driver_type_counts": dict(driver_type_counts),
        "common_likely_drivers": [{
            "driver": row["label"],
            "driver_type": row["item_type"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "confidence_counts": dict(row["confidence_counts"]),
            "example_why_it_matters_here": row["example_why"],
        } for row in sorted(
            recurring_drivers.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "common_unspoken_constraints": [{
            "constraint": row["label"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "confidence_counts": dict(row["confidence_counts"]),
            "example_why_likely": row["example_why"],
        } for row in sorted(
            recurring_constraints.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "common_value_tensions": [{
            "tension": row["label"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "confidence_counts": dict(row["confidence_counts"]),
            "example_frame": row["example_why"],
        } for row in sorted(
            recurring_tensions.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "facilitator_primary_failure_modes": [{
            "failure_mode": row["label"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "example_assessment": row["example_why"],
        } for row in sorted(
            recurring_facilitator_failure_modes.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "common_missed_high_value_followups": [{
            "question": row["label"],
            "trigger_type": row["item_type"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "priority_counts": dict(row["confidence_counts"]),
            "generic_learning": row["example_why"],
        } for row in sorted(
            recurring_missed_followups.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "common_likely_misclassified_drivers": [{
            "possible_underlying_driver": row["label"],
            "observed_surface_frame": row["item_type"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "generic_learning": row["example_why"],
        } for row in sorted(
            recurring_misclassified_drivers.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "depth_completion_counts": dict(depth_completion_counts),
        "common_missing_depth_probes": [{
            "probe_type": row["item_type"],
            "probe_label": row["label"],
            "persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "why_it_matters": row["example_why"],
        } for row in sorted(
            recurring_missing_depth_probes.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "assumption_matrix": [{
            "assumption_index": index,
            "assumption": row["assumption"],
            "status_counts": dict(row["status_counts"]),
            "persona_results": row["persona_results"],
        } for index, row in sorted(assumption_rows.items())],
        "additional_persona_specific_findings": additional_findings,
        "personas": [{
            "persona_id": item["persona_id"],
            "persona_name": item["persona_name"],
            "interview_id": item["interview_id"],
            "problem_strength": item.get("report", {}).get("problem_evidence", {}).get("strength", "unknown"),
            "pricing_signal": item.get("report", {}).get("pricing_signal", {}),
            "retention_risk": item.get("report", {}).get("retention_risk", {}),
            "quality": item.get("quality", {}).get("scores", {}),
            "top_likely_drivers": item.get("persona_driver_trace", {}).get("likely_drivers", [])[:3],
            "top_unspoken_constraints": item.get("persona_driver_trace", {}).get("unspoken_constraints", [])[:2],
            "value_tensions": item.get("persona_driver_trace", {}).get("value_tensions", [])[:2],
            "missed_follow_up_questions": item.get("persona_driver_trace", {}).get("missed_follow_up_questions", [])[:2],
            "facilitator_primary_failure_mode": (
                item.get("facilitator_audit_feedback", {}).get("summary", {}).get("primary_failure_mode", "")
            ),
            "facilitator_missed_followups": (
                item.get("facilitator_audit_feedback", {}).get("high_value_missed_followups", [])[:2]
            ),
            "facilitator_likely_misclassified_drivers": (
                item.get("facilitator_audit_feedback", {}).get("likely_misclassified_driver_patterns", [])[:2]
            ),
            "conversation_realism": item.get("conversation_realism", {}),
            "depth_complete": bool((item.get("coverage_status", {}) or {}).get("depth_complete", False)),
            "missing_depth_probes": list((item.get("coverage_status", {}) or {}).get("depth_missing", []) or []),
            "required_depth_probes": list((item.get("coverage_status", {}) or {}).get("depth_requirements", []) or []),
        } for item in interviews],
        "potential_over_optimism_risks": derive_panel_over_optimism_risks(interviews),
        "synthetic_only_disclaimer": (
            "This panel contains synthetic AI pre-validation only. It cannot establish market demand, "
            "pricing, prevalence, or replace interviews with real people."
        ),
    }


def _facilitator_audit_panel_payload(
    run_id: str,
    interviews: list[dict[str, Any]],
    *,
    topic_label: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    recurring_tags: dict[str, dict[str, Any]] = {}
    recurring_prompt_adjustments: dict[str, dict[str, Any]] = {}
    recurring_carry_forward_rules: dict[str, dict[str, Any]] = {}
    blocked_feedback_patterns: dict[str, dict[str, Any]] = {}

    def _normalize_key(value: str) -> str:
        return " ".join(str(value).strip().casefold().split())

    def _group(
        bucket: dict[str, dict[str, Any]],
        *,
        key: str,
        label: str,
        persona_id: str,
        persona_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        row = bucket.setdefault(key, {
            "label": label,
            "persona_ids": set(),
            "persona_names": [],
            "details": details or {},
        })
        if persona_id not in row["persona_ids"]:
            row["persona_ids"].add(persona_id)
            row["persona_names"].append(persona_name)

    def _candidate_strength(persona_count: int) -> str:
        if persona_count >= 3:
            return "strong"
        if persona_count >= 2:
            return "medium"
        return "weak"

    audited_persona_count = 0
    blocked_feedback_count = 0

    for interview in interviews:
        audit = interview.get("facilitator_audit_feedback", {})
        if not audit:
            continue
        audited_persona_count += 1
        persona_id = interview["persona_id"]
        persona_name = interview["persona_name"]

        for item in audit.get("facilitator_feedback_tags", []):
            tag = str(item.get("tag", "")).strip()
            if not tag:
                continue
            _group(
                recurring_tags,
                key=_normalize_key(tag),
                label=tag,
                persona_id=persona_id,
                persona_name=persona_name,
                details={
                    "severity": str(item.get("severity", "unknown")),
                    "observed_pattern": str(item.get("observed_pattern", "")),
                    "why_it_matters": str(item.get("why_it_matters", "")),
                },
            )

        for item in audit.get("prompt_adjustments", []):
            if not bool(item.get("safe_for_global_reuse", False)):
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            adjustment_type = str(item.get("adjustment_type", "")).strip()
            _group(
                recurring_prompt_adjustments,
                key=f"{adjustment_type}|{_normalize_key(text)}",
                label=text,
                persona_id=persona_id,
                persona_name=persona_name,
                details={
                    "adjustment_type": adjustment_type,
                    "reuse_scope": str(item.get("reuse_scope", "")),
                },
            )

        for item in audit.get("carry_forward_rules", []):
            if not bool(item.get("safe_for_global_reuse", False)):
                continue
            rule = str(item.get("rule", "")).strip()
            if not rule:
                continue
            _group(
                recurring_carry_forward_rules,
                key=_normalize_key(rule),
                label=rule,
                persona_id=persona_id,
                persona_name=persona_name,
                details={
                    "rule_id": str(item.get("rule_id", "")),
                    "source_tags": list(item.get("source_tags", [])),
                    "confidence": str(item.get("confidence", "unknown")),
                },
            )

        for item in audit.get("blocked_feedback", []):
            blocked_item = str(item.get("blocked_item", "")).strip()
            block_reason = str(item.get("block_reason", "")).strip() or "unspecified"
            if not blocked_item:
                continue
            blocked_feedback_count += 1
            _group(
                blocked_feedback_patterns,
                key=f"{block_reason}|{_normalize_key(blocked_item)}",
                label=blocked_item,
                persona_id=persona_id,
                persona_name=persona_name,
                details={"block_reason": block_reason},
            )

    distilled_prompt_adjustments = [{
        "adjustment_type": row["details"].get("adjustment_type", ""),
        "text": row["label"],
        "reuse_scope": row["details"].get("reuse_scope", ""),
        "support_persona_count": len(row["persona_ids"]),
        "personas": row["persona_names"],
        "candidate_strength": _candidate_strength(len(row["persona_ids"])),
        "safe_for_global_reuse": True,
    } for row in sorted(
        recurring_prompt_adjustments.values(),
        key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
    )]

    distilled_carry_forward_rules = [{
        "rule_id": row["details"].get("rule_id", ""),
        "rule": row["label"],
        "source_tags": row["details"].get("source_tags", []),
        "confidence": row["details"].get("confidence", "unknown"),
        "support_persona_count": len(row["persona_ids"]),
        "personas": row["persona_names"],
        "candidate_strength": _candidate_strength(len(row["persona_ids"])),
        "safe_for_global_reuse": True,
    } for row in sorted(
        recurring_carry_forward_rules.values(),
        key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
    )]

    ready_for_global = [item for item in distilled_carry_forward_rules if item["support_persona_count"] >= 2]

    return {
        "artifact_version": "v1",
        "feedback_scope": "panel",
        "run_id": run_id,
        "topic": topic_label,
        "audited_persona_count": audited_persona_count,
        "persona_count": len(interviews),
        "ready_for_global_rule_count": len(ready_for_global),
        "blocked_feedback_count": blocked_feedback_count,
        "top_failure_modes": summary.get("facilitator_primary_failure_modes", []),
        "recurring_feedback_tags": [{
            "tag": row["label"],
            "severity": row["details"].get("severity", "unknown"),
            "support_persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
            "observed_pattern": row["details"].get("observed_pattern", ""),
            "why_it_matters": row["details"].get("why_it_matters", ""),
        } for row in sorted(
            recurring_tags.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "common_missed_high_value_followups": summary.get("common_missed_high_value_followups", []),
        "common_likely_misclassified_drivers": summary.get("common_likely_misclassified_drivers", []),
        "distilled_prompt_adjustments": distilled_prompt_adjustments,
        "distilled_carry_forward_rules": distilled_carry_forward_rules,
        "ready_for_global_candidate_rules": ready_for_global,
        "blocked_feedback_patterns": [{
            "blocked_item": row["label"],
            "block_reason": row["details"].get("block_reason", "unspecified"),
            "support_persona_count": len(row["persona_ids"]),
            "personas": row["persona_names"],
        } for row in sorted(
            blocked_feedback_patterns.values(),
            key=lambda item: (-len(item["persona_ids"]), item["label"].casefold()),
        )],
        "synthetic_only_disclaimer": (
            "This facilitator audit digest is synthetic offline learning evidence only. "
            "It should be reviewed before any rule is promoted into the facilitator core."
        ),
    }


def _render_facilitator_audit_panel(audit_panel: dict[str, Any]) -> str:
    lines = [
        f"# {audit_panel.get('topic', DEFAULT_TOPIC_LABEL)} Facilitator Audit Digest", "",
        f"> {audit_panel.get('synthetic_only_disclaimer', '')}", "",
        f"- Audited personas: {audit_panel.get('audited_persona_count', 0)}/{audit_panel.get('persona_count', 0)}",
        f"- Ready-for-global rule candidates: {audit_panel.get('ready_for_global_rule_count', 0)}",
        f"- Blocked feedback items: {audit_panel.get('blocked_feedback_count', 0)}", "",
    ]
    if audit_panel.get("top_failure_modes"):
        lines.extend(["## Top Failure Modes", ""])
        for item in audit_panel["top_failure_modes"]:
            lines.append(
                f"- {item.get('failure_mode', '')} across {item.get('persona_count', 0)} personas: "
                f"{', '.join(item.get('personas', []))}"
            )
            if item.get("example_assessment"):
                lines.append(f"  Assessment: {item.get('example_assessment', '')}")
        lines.append("")
    if audit_panel.get("recurring_feedback_tags"):
        lines.extend(["## Recurring Feedback Tags", ""])
        for item in audit_panel["recurring_feedback_tags"]:
            lines.append(
                f"- [{item.get('severity', 'unknown')}] {item.get('tag', '')} across "
                f"{item.get('support_persona_count', 0)} personas: {', '.join(item.get('personas', []))}"
            )
        lines.append("")
    if audit_panel.get("distilled_carry_forward_rules"):
        lines.extend(["## Distilled Carry-Forward Rules", ""])
        for item in audit_panel["distilled_carry_forward_rules"]:
            lines.append(
                f"- [{item.get('candidate_strength', 'weak')}] {item.get('rule', '')} "
                f"(support={item.get('support_persona_count', 0)})"
            )
        lines.append("")
    if audit_panel.get("distilled_prompt_adjustments"):
        lines.extend(["## Distilled Prompt Adjustments", ""])
        for item in audit_panel["distilled_prompt_adjustments"]:
            lines.append(
                f"- [{item.get('candidate_strength', 'weak')}] {item.get('adjustment_type', '')}: {item.get('text', '')}"
            )
        lines.append("")
    if audit_panel.get("common_missed_high_value_followups"):
        lines.extend(["## Common Missed High-Value Follow-Ups", ""])
        for item in audit_panel["common_missed_high_value_followups"]:
            lines.append(
                f"- [{item.get('trigger_type', 'unknown')}] {item.get('question', '')} "
                f"(support={item.get('persona_count', 0)})"
            )
        lines.append("")
    if audit_panel.get("common_likely_misclassified_drivers"):
        lines.extend(["## Common Likely Misclassified Drivers", ""])
        for item in audit_panel["common_likely_misclassified_drivers"]:
            lines.append(
                f"- {item.get('observed_surface_frame', '')} -> {item.get('possible_underlying_driver', '')} "
                f"(support={item.get('persona_count', 0)})"
            )
        lines.append("")
    if audit_panel.get("blocked_feedback_patterns"):
        lines.extend(["## Blocked Feedback Patterns", ""])
        for item in audit_panel["blocked_feedback_patterns"]:
            lines.append(
                f"- {item.get('block_reason', 'unspecified')}: {item.get('blocked_item', '')} "
                f"(support={item.get('support_persona_count', 0)})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _facilitator_audit_learning_report_payload(
    *,
    label: str,
    audit_panels: list[dict[str, Any]],
) -> dict[str, Any]:
    aggregated_failure_modes: dict[str, dict[str, Any]] = {}
    aggregated_feedback_tags: dict[str, dict[str, Any]] = {}
    aggregated_followups: dict[str, dict[str, Any]] = {}
    aggregated_misclassified_drivers: dict[str, dict[str, Any]] = {}
    aggregated_rule_candidates: dict[str, dict[str, Any]] = {}
    aggregated_blocked_patterns: dict[str, dict[str, Any]] = {}

    def _normalize_key(value: str) -> str:
        return " ".join(str(value).strip().casefold().split())

    def _merge(
        bucket: dict[str, dict[str, Any]],
        *,
        key: str,
        label_text: str,
        run_id: str,
        persona_count: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        row = bucket.setdefault(key, {
            "label": label_text,
            "run_ids": set(),
            "support_persona_count": 0,
            "details": details or {},
        })
        row["run_ids"].add(run_id)
        row["support_persona_count"] += max(0, int(persona_count))
        if details and not row.get("details"):
            row["details"] = details

    def _cross_run_strength(run_count: int, persona_count: int) -> str:
        if run_count >= 3 or persona_count >= 6:
            return "strong"
        if run_count >= 2 or persona_count >= 4:
            return "medium"
        return "weak"

    total_audited_personas = 0
    total_blocked_feedback = 0
    included_runs: list[dict[str, Any]] = []

    for payload in audit_panels:
        run_id = str(payload.get("run_id", ""))
        topic = str(payload.get("topic", ""))
        audited_personas = int(payload.get("audited_persona_count", 0) or 0)
        ready_count = int(payload.get("ready_for_global_rule_count", 0) or 0)
        blocked_count = int(payload.get("blocked_feedback_count", 0) or 0)
        total_audited_personas += audited_personas
        total_blocked_feedback += blocked_count
        included_runs.append({
            "run_id": run_id,
            "topic": topic,
            "audited_persona_count": audited_personas,
            "ready_for_global_rule_count": ready_count,
            "blocked_feedback_count": blocked_count,
        })

        for item in payload.get("top_failure_modes", []):
            failure_mode = str(item.get("failure_mode", "")).strip()
            if not failure_mode:
                continue
            _merge(
                aggregated_failure_modes,
                key=_normalize_key(failure_mode),
                label_text=failure_mode,
                run_id=run_id,
                persona_count=int(item.get("persona_count", 0) or 0),
                details={"example_assessment": str(item.get("example_assessment", ""))},
            )

        for item in payload.get("recurring_feedback_tags", []):
            tag = str(item.get("tag", "")).strip()
            if not tag:
                continue
            _merge(
                aggregated_feedback_tags,
                key=_normalize_key(tag),
                label_text=tag,
                run_id=run_id,
                persona_count=int(item.get("support_persona_count", 0) or 0),
                details={
                    "severity": str(item.get("severity", "unknown")),
                    "observed_pattern": str(item.get("observed_pattern", "")),
                    "why_it_matters": str(item.get("why_it_matters", "")),
                },
            )

        for item in payload.get("common_missed_high_value_followups", []):
            question = str(item.get("question", "")).strip()
            trigger_type = str(item.get("trigger_type", "")).strip()
            if not question and not trigger_type:
                continue
            _merge(
                aggregated_followups,
                key=f"{trigger_type}|{_normalize_key(question)}",
                label_text=question,
                run_id=run_id,
                persona_count=int(item.get("persona_count", 0) or 0),
                details={
                    "trigger_type": trigger_type,
                    "generic_learning": str(item.get("generic_learning", "")),
                },
            )

        for item in payload.get("common_likely_misclassified_drivers", []):
            possible_underlying_driver = str(item.get("possible_underlying_driver", "")).strip()
            observed_surface_frame = str(item.get("observed_surface_frame", "")).strip()
            if not possible_underlying_driver and not observed_surface_frame:
                continue
            _merge(
                aggregated_misclassified_drivers,
                key=f"{_normalize_key(observed_surface_frame)}|{_normalize_key(possible_underlying_driver)}",
                label_text=possible_underlying_driver,
                run_id=run_id,
                persona_count=int(item.get("persona_count", 0) or 0),
                details={
                    "observed_surface_frame": observed_surface_frame,
                    "generic_learning": str(item.get("generic_learning", "")),
                },
            )

        for item in payload.get("distilled_carry_forward_rules", []):
            rule = str(item.get("rule", "")).strip()
            if not rule:
                continue
            _merge(
                aggregated_rule_candidates,
                key=_normalize_key(rule),
                label_text=rule,
                run_id=run_id,
                persona_count=int(item.get("support_persona_count", 0) or 0),
                details={
                    "rule_id": str(item.get("rule_id", "")),
                    "source_tags": list(item.get("source_tags", [])),
                    "confidence": str(item.get("confidence", "unknown")),
                },
            )

        for item in payload.get("blocked_feedback_patterns", []):
            blocked_item = str(item.get("blocked_item", "")).strip()
            if not blocked_item:
                continue
            _merge(
                aggregated_blocked_patterns,
                key=f"{str(item.get('block_reason', 'unspecified')).strip()}|{_normalize_key(blocked_item)}",
                label_text=blocked_item,
                run_id=run_id,
                persona_count=int(item.get("support_persona_count", 0) or 0),
                details={"block_reason": str(item.get("block_reason", "unspecified"))},
            )

    cross_run_rules = [{
        "rule_id": row["details"].get("rule_id", ""),
        "rule": row["label"],
        "source_tags": row["details"].get("source_tags", []),
        "confidence": row["details"].get("confidence", "unknown"),
        "support_run_count": len(row["run_ids"]),
        "support_persona_count": row["support_persona_count"],
        "candidate_strength": _cross_run_strength(len(row["run_ids"]), row["support_persona_count"]),
        "ready_for_human_review": len(row["run_ids"]) >= 2,
    } for row in sorted(
        aggregated_rule_candidates.values(),
        key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
    )]

    return {
        "artifact_version": "v1",
        "feedback_scope": "batch",
        "label": label,
        "run_count": len(audit_panels),
        "total_audited_personas": total_audited_personas,
        "total_blocked_feedback": total_blocked_feedback,
        "included_runs": included_runs,
        "recurring_failure_modes": [{
            "failure_mode": row["label"],
            "support_run_count": len(row["run_ids"]),
            "support_persona_count": row["support_persona_count"],
            "candidate_strength": _cross_run_strength(len(row["run_ids"]), row["support_persona_count"]),
            "example_assessment": row["details"].get("example_assessment", ""),
        } for row in sorted(
            aggregated_failure_modes.values(),
            key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
        )],
        "recurring_feedback_tags": [{
            "tag": row["label"],
            "severity": row["details"].get("severity", "unknown"),
            "support_run_count": len(row["run_ids"]),
            "support_persona_count": row["support_persona_count"],
            "observed_pattern": row["details"].get("observed_pattern", ""),
            "why_it_matters": row["details"].get("why_it_matters", ""),
        } for row in sorted(
            aggregated_feedback_tags.values(),
            key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
        )],
        "recurring_missed_high_value_followups": [{
            "question": row["label"],
            "trigger_type": row["details"].get("trigger_type", ""),
            "support_run_count": len(row["run_ids"]),
            "support_persona_count": row["support_persona_count"],
            "candidate_strength": _cross_run_strength(len(row["run_ids"]), row["support_persona_count"]),
            "generic_learning": row["details"].get("generic_learning", ""),
        } for row in sorted(
            aggregated_followups.values(),
            key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
        )],
        "recurring_likely_misclassified_drivers": [{
            "possible_underlying_driver": row["label"],
            "observed_surface_frame": row["details"].get("observed_surface_frame", ""),
            "support_run_count": len(row["run_ids"]),
            "support_persona_count": row["support_persona_count"],
            "candidate_strength": _cross_run_strength(len(row["run_ids"]), row["support_persona_count"]),
            "generic_learning": row["details"].get("generic_learning", ""),
        } for row in sorted(
            aggregated_misclassified_drivers.values(),
            key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
        )],
        "cross_run_carry_forward_rules": cross_run_rules,
        "human_review_candidates": [item for item in cross_run_rules if item["ready_for_human_review"]],
        "blocked_feedback_patterns": [{
            "blocked_item": row["label"],
            "block_reason": row["details"].get("block_reason", "unspecified"),
            "support_run_count": len(row["run_ids"]),
            "support_persona_count": row["support_persona_count"],
        } for row in sorted(
            aggregated_blocked_patterns.values(),
            key=lambda item: (-len(item["run_ids"]), -item["support_persona_count"], item["label"].casefold()),
        )],
        "synthetic_only_disclaimer": (
            "This cross-run facilitator audit report is synthetic offline learning evidence only. "
            "Nothing here should be injected into facilitator prompts without human review."
        ),
    }


def _render_facilitator_audit_learning_report(report: dict[str, Any]) -> str:
    lines = [
        f"# {report.get('label', 'Facilitator Audit Learning Report')}", "",
        f"> {report.get('synthetic_only_disclaimer', '')}", "",
        f"- Runs: {report.get('run_count', 0)}",
        f"- Total audited personas: {report.get('total_audited_personas', 0)}",
        f"- Human-review rule candidates: {len(report.get('human_review_candidates', []))}",
        f"- Total blocked feedback items: {report.get('total_blocked_feedback', 0)}", "",
    ]
    if report.get("recurring_failure_modes"):
        lines.extend(["## Recurring Failure Modes", ""])
        for item in report["recurring_failure_modes"]:
            lines.append(
                f"- [{item.get('candidate_strength', 'weak')}] {item.get('failure_mode', '')} "
                f"(runs={item.get('support_run_count', 0)}, personas={item.get('support_persona_count', 0)})"
            )
        lines.append("")
    if report.get("cross_run_carry_forward_rules"):
        lines.extend(["## Cross-Run Carry-Forward Rules", ""])
        for item in report["cross_run_carry_forward_rules"]:
            lines.append(
                f"- [{item.get('candidate_strength', 'weak')}] {item.get('rule', '')} "
                f"(runs={item.get('support_run_count', 0)}, personas={item.get('support_persona_count', 0)})"
            )
        lines.append("")
    if report.get("human_review_candidates"):
        lines.extend(["## Human Review Candidates", ""])
        for item in report["human_review_candidates"]:
            lines.append(
                f"- {item.get('rule', '')} "
                f"(runs={item.get('support_run_count', 0)}, personas={item.get('support_persona_count', 0)})"
            )
        lines.append("")
    if report.get("recurring_missed_high_value_followups"):
        lines.extend(["## Recurring Missed High-Value Follow-Ups", ""])
        for item in report["recurring_missed_high_value_followups"]:
            lines.append(
                f"- [{item.get('trigger_type', 'unknown')}] {item.get('question', '')} "
                f"(runs={item.get('support_run_count', 0)})"
            )
        lines.append("")
    if report.get("recurring_likely_misclassified_drivers"):
        lines.extend(["## Recurring Likely Misclassified Drivers", ""])
        for item in report["recurring_likely_misclassified_drivers"]:
            lines.append(
                f"- {item.get('observed_surface_frame', '')} -> {item.get('possible_underlying_driver', '')} "
                f"(runs={item.get('support_run_count', 0)})"
            )
        lines.append("")
    if report.get("blocked_feedback_patterns"):
        lines.extend(["## Blocked Feedback Patterns", ""])
        for item in report["blocked_feedback_patterns"]:
            lines.append(
                f"- {item.get('block_reason', 'unspecified')}: {item.get('blocked_item', '')} "
                f"(runs={item.get('support_run_count', 0)})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_summary(summary: dict[str, Any], interviews: list[dict[str, Any]]) -> str:
    lines = [
        f"# {summary['topic']} Synthetic Persona Panel", "",
        f"> {summary['synthetic_only_disclaimer']}", "",
        f"- Personas: {summary['persona_count']}",
        f"- Language: {summary['language']}",
        f"- Average interview quality: {summary['average_quality_score']}",
        f"- Average conversation realism: {summary.get('average_conversation_realism_score')}",
        f"- Problem evidence: {summary['problem_strength_counts']}", "",
        *( [f"- Depth coverage: {summary['depth_completion_counts']}"] if summary.get("depth_completion_counts") else [] ),
        "",
        "## Persona Results", "",
    ]
    for item in interviews:
        report = item.get("report", {})
        pricing = report.get("pricing_signal", {})
        retention = report.get("retention_risk", {})
        quality = item.get("quality", {}).get("scores", {})
        lines.extend([
            f"### {item['persona_id']} - {item['persona_name']}", "",
            f"- Problem evidence: {report.get('problem_evidence', {}).get('strength', 'unknown')}",
            f"- Pricing: {pricing.get('monthly_comfort_range', 'unknown')} ({pricing.get('evidence_strength', 'unknown')})",
            f"- Workflow effect: {retention.get('workflow_effect', 'unclear')}",
            f"- Quality: {quality.get('overall', 'unknown')}/5", "",
        ])
        realism = item.get("conversation_realism", {})
        if realism:
            lines.append(
                f"- Conversation realism: {realism.get('overall_score', 'unknown')} "
                f"({realism.get('friction_mode', 'off')})"
            )
        coverage = item.get("coverage_status", {}) or {}
        depth_missing = list(coverage.get("depth_missing", []) or [])
        if coverage.get("depth_requirements"):
            lines.append(f"- Depth complete: {coverage.get('depth_complete', False)}")
            if depth_missing:
                rendered = ", ".join(DEPTH_PROBE_LABELS.get(str(probe), str(probe)) for probe in depth_missing)
                lines.append(f"- Missing depth probes: {rendered}")
            else:
                lines.append("- Missing depth probes: none")
        audit = item.get("facilitator_audit_feedback", {})
        audit_summary = audit.get("summary", {})
        if audit_summary.get("primary_failure_mode"):
            lines.append(f"- Facilitator gap: {audit_summary.get('primary_failure_mode', '')}")
        for driver in item.get("persona_driver_trace", {}).get("likely_drivers", [])[:2]:
            lines.append(
                f"- Driver: {driver.get('driver', '')} "
                f"({driver.get('driver_type', '')}, {driver.get('confidence', 'unknown')})"
            )
        for tension in item.get("persona_driver_trace", {}).get("value_tensions", [])[:1]:
            lines.append(
                f"- Tension: {tension.get('tension', '')} "
                f"({tension.get('side_a', '')} vs {tension.get('side_b', '')})"
            )
        for follow_up in item.get("persona_driver_trace", {}).get("missed_follow_up_questions", [])[:1]:
            lines.append(f"- Missed follow-up: {follow_up.get('question', '')}")
        for follow_up in audit.get("high_value_missed_followups", [])[:1]:
            lines.append(f"- Audit follow-up gap: {follow_up.get('missed_followup_question', '')}")
        for pattern in audit.get("likely_misclassified_driver_patterns", [])[:1]:
            lines.append(
                f"- Audit driver risk: {pattern.get('observed_surface_frame', '')} -> "
                f"{pattern.get('possible_underlying_driver', '')}"
            )
        if item.get("persona_driver_trace", {}).get("likely_drivers"):
            lines.append("")
        for insight in report.get("key_insights", []):
            for clean_insight in str(insight).replace("??,'", "\n").splitlines():
                clean_insight = clean_insight.strip(" ,'\"")
                if clean_insight:
                    lines.append(f"- {clean_insight}")
        lines.append("")
    if summary.get("potential_over_optimism_risks"):
        lines.extend(["## Potential Over-Optimism Risks", ""])
        for item in summary["potential_over_optimism_risks"]:
            lines.append(f"- {item}")
        lines.append("")
    if summary.get("common_likely_drivers"):
        lines.extend(["## Common Likely Drivers", ""])
        for item in summary["common_likely_drivers"]:
            lines.append(
                f"- {item['driver']} [{item['driver_type']}] "
                f"across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("example_why_it_matters_here"):
                lines.append(f"  Why it mattered: {item['example_why_it_matters_here']}")
        lines.append("")
    if summary.get("common_unspoken_constraints"):
        lines.extend(["## Common Unspoken Constraints", ""])
        for item in summary["common_unspoken_constraints"]:
            lines.append(
                f"- {item['constraint']} across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("example_why_likely"):
                lines.append(f"  Why likely: {item['example_why_likely']}")
        lines.append("")
    if summary.get("common_value_tensions"):
        lines.extend(["## Common Value Tensions", ""])
        for item in summary["common_value_tensions"]:
            lines.append(
                f"- {item['tension']} across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("example_frame"):
                lines.append(f"  Frame: {item['example_frame']}")
        lines.append("")
    if summary.get("facilitator_primary_failure_modes"):
        lines.extend(["## Facilitator Audit Patterns", ""])
        for item in summary["facilitator_primary_failure_modes"]:
            lines.append(
                f"- {item['failure_mode']} across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("example_assessment"):
                lines.append(f"  Assessment: {item['example_assessment']}")
        lines.append("")
    if summary.get("common_missing_depth_probes"):
        lines.extend(["## Common Missing Depth Probes", ""])
        for item in summary["common_missing_depth_probes"]:
            lines.append(
                f"- {item['probe_label']} across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("why_it_matters"):
                lines.append(f"  Why it matters: {item['why_it_matters']}")
        lines.append("")
    if summary.get("common_missed_high_value_followups"):
        lines.extend(["## Common Missed High-Value Follow-Ups", ""])
        for item in summary["common_missed_high_value_followups"]:
            lines.append(
                f"- [{item['trigger_type']}] {item['question']} across {item['persona_count']} personas: "
                f"{', '.join(item['personas'])}"
            )
            if item.get("generic_learning"):
                lines.append(f"  Learning: {item['generic_learning']}")
        lines.append("")
    if summary.get("common_likely_misclassified_drivers"):
        lines.extend(["## Common Likely Misclassified Drivers", ""])
        for item in summary["common_likely_misclassified_drivers"]:
            lines.append(
                f"- {item['observed_surface_frame']} -> {item['possible_underlying_driver']} "
                f"across {item['persona_count']} personas: {', '.join(item['personas'])}"
            )
            if item.get("generic_learning"):
                lines.append(f"  Learning: {item['generic_learning']}")
        lines.append("")
    lines.extend(["## Assumption Matrix", ""])
    for row in summary.get("assumption_matrix", []):
        lines.append(f"### {row['assumption_index']}. {row['assumption']}")
        lines.append(f"- Counts: {row['status_counts']}")
        for result in row["persona_results"]:
            lines.append(f"- {result['persona_id']} {result['persona_name']}: {result['status']} - {result['rationale']}")
        lines.append("")
    if summary.get("additional_persona_specific_findings"):
        lines.extend(["## Additional Persona-Specific Risks", ""])
        for item in summary["additional_persona_specific_findings"]:
            lines.append(
                f"- {item['persona_id']} {item['persona_name']}: {item['status']} - "
                f"{item['finding']} ({item['rationale']})"
            )
        lines.append("")
    lines.extend(["## Next Experiments", ""])
    for item in interviews:
        lines.append(f"- {item['persona_id']}: {item.get('report', {}).get('next_experiment', '')}")
    return "\n".join(lines).rstrip() + "\n"


def run_concept_panel(
    *,
    data_dir: Path,
    output_dir: Path,
    facilitator_provider: FacilitatorProvider,
    persona_provider: ConversationProvider,
    quality_provider: FacilitatorProvider,
    research_goal: str,
    product_context: str,
    topic_label: str,
    concept_protocol: str = DEFAULT_CONCEPT_PROTOCOL,
    concept_label: str = "",
    output_language: str = DEFAULT_LANGUAGE,
    core_assumption_count: int = DEFAULT_CORE_ASSUMPTION_COUNT,
    persona_ids: list[str] | None = None,
    max_turns: int | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
    friction_mode: str = "off",
    progress_writer=None,
    approved_learning_rules_path: Path | None = None,
) -> Path:
    resolved_soft_turn_limit, resolved_hard_turn_limit = _resolve_concept_panel_turn_policy(
        max_turns=max_turns,
        soft_turn_limit=soft_turn_limit,
        hard_turn_limit=hard_turn_limit,
    )
    run_id = f"concept_panel_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}"
    run_dir = output_dir / run_id
    interview_dir = run_dir / "interviews"
    ensure_dir(interview_dir)
    runtime = ObserverControlledInterviewRuntime(
        data_dir=data_dir,
        session_dir=interview_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
        progress_writer=progress_writer,
        approved_learning_rules_path=approved_learning_rules_path,
    )
    interviews: list[dict[str, Any]] = []
    for persona_id in _persona_ids(data_dir, persona_ids):
        if progress_writer is not None:
            progress_writer(f"[panel] start persona={persona_id}")
        folder, session = runtime.start(
            persona_id=persona_id,
            research_goal=research_goal,
            interview_mode="concept_validation",
            product_context=product_context,
            concept_protocol=concept_protocol,
            concept_label=concept_label or topic_label,
            output_language=output_language,
            max_turns=resolved_hard_turn_limit,
            soft_turn_limit=resolved_soft_turn_limit,
            hard_turn_limit=resolved_hard_turn_limit,
            friction_mode=friction_mode,
        )
        while session.status not in {"completed", "failed"}:
            session = runtime.continue_interview(session.interview_id)
        report = read_json(folder / "insight_report.json") if (folder / "insight_report.json").exists() else {}
        quality = read_json(folder / "quality_evaluation.json") if (folder / "quality_evaluation.json").exists() else {}
        persona_runtime_session_id = getattr(session, "persona_conversation_session_id", "")
        interviews.append({
            "persona_id": persona_id,
            "persona_name": session.persona_name,
            "interview_id": session.interview_id,
            "status": session.status,
            "error": session.last_error,
            "folder": str(folder),
            "report": report,
            "quality": quality,
            "coverage_status": getattr(session, "coverage_status", {}),
            "persona_driver_trace": (
                read_json(folder / "persona_driver_trace.json")
                if (folder / "persona_driver_trace.json").exists() else {}
            ),
            "conversation_realism": (
                read_json(
                    folder / "persona_runtime" / persona_runtime_session_id / "conversation_realism_report.json"
                )
                if (
                    folder / "persona_runtime" / persona_runtime_session_id / "conversation_realism_report.json"
                ).exists() else {}
            ),
            "facilitator_audit_feedback": (
                read_json(folder / "facilitator_audit_feedback.json")
                if (folder / "facilitator_audit_feedback.json").exists() else {}
            ),
        })
        if progress_writer is not None:
            progress_writer(
                f"[panel] done persona={persona_id} status={session.status} interview_id={session.interview_id}"
            )
        write_json(run_dir / "progress.json", {"run_id": run_id, "interviews": interviews})

    summary = _summary_payload(
        run_id,
        interviews,
        topic_label=topic_label,
        language=output_language,
        core_assumption_count=core_assumption_count,
    )
    audit_panel = _facilitator_audit_panel_payload(
        run_id,
        interviews,
        topic_label=topic_label,
        summary=summary,
    )
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
    write_json(run_dir / "facilitator_audit_panel.json", audit_panel)
    (run_dir / "facilitator_audit_panel.md").write_text(
        _render_facilitator_audit_panel(audit_panel),
        encoding="utf-8",
    )
    write_json(run_dir / "manifest.json", {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "topic_label": topic_label,
        "research_goal": research_goal,
        "product_context": product_context,
        "concept_protocol": concept_protocol,
        "concept_label": concept_label or topic_label,
        "persona_ids": [item["persona_id"] for item in interviews],
        "core_assumption_count": core_assumption_count,
        "max_turns": resolved_hard_turn_limit,
        "soft_turn_limit": resolved_soft_turn_limit,
        "hard_turn_limit": resolved_hard_turn_limit,
        "friction_mode": friction_mode,
        "language": output_language,
        "synthetic_only": True,
    })
    return run_dir


def run_ai_followup_copilot_panel(
    *,
    data_dir: Path,
    output_dir: Path,
    facilitator_provider: FacilitatorProvider,
    persona_provider: ConversationProvider,
    quality_provider: FacilitatorProvider,
    max_turns: int | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
    friction_mode: str = "off",
    progress_writer=None,
    approved_learning_rules_path: Path | None = None,
) -> Path:
    return run_concept_panel(
        data_dir=data_dir,
        output_dir=output_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
        research_goal=FOLLOWUP_RESEARCH_GOAL,
        product_context=FOLLOWUP_PRODUCT_CONTEXT,
        topic_label=DEFAULT_CONCEPT_LABEL,
        concept_protocol=DEFAULT_CONCEPT_PROTOCOL,
        concept_label=DEFAULT_CONCEPT_LABEL,
        output_language=DEFAULT_LANGUAGE,
        core_assumption_count=DEFAULT_CORE_ASSUMPTION_COUNT,
        max_turns=max_turns,
        soft_turn_limit=soft_turn_limit,
        hard_turn_limit=hard_turn_limit,
        friction_mode=friction_mode,
        progress_writer=progress_writer,
        approved_learning_rules_path=approved_learning_rules_path,
    )


def summarize_existing_concept_panel(
    *,
    run_dir: Path,
    persona_ids: list[str],
    topic_label: str = "",
    output_language: str = "",
    core_assumption_count: int | None = None,
) -> Path:
    manifest = read_json(run_dir / "manifest.json") if (run_dir / "manifest.json").exists() else {}
    selected = set(persona_ids)
    interviews: list[dict[str, Any]] = []
    for folder in sorted((run_dir / "interviews").iterdir()):
        interview_path = folder / "interview.json"
        if not folder.is_dir() or not interview_path.exists():
            continue
        session = read_json(interview_path)
        persona_id = str(session.get("persona_id", ""))
        if persona_id not in selected or session.get("status") != "completed":
            continue
        interviews.append({
            "persona_id": persona_id,
            "persona_name": session.get("persona_name", persona_id),
            "interview_id": session.get("interview_id", folder.name),
            "status": session.get("status", ""),
            "error": session.get("last_error", ""),
            "folder": str(folder),
            "report": read_json(folder / "insight_report.json"),
            "quality": read_json(folder / "quality_evaluation.json"),
            "coverage_status": session.get("coverage_status", {}),
            "persona_driver_trace": (
                read_json(folder / "persona_driver_trace.json")
                if (folder / "persona_driver_trace.json").exists() else {}
            ),
            "conversation_realism": (
                read_json(
                    folder
                    / "persona_runtime"
                    / str(session.get("persona_conversation_session_id", ""))
                    / "conversation_realism_report.json"
                )
                if (
                    folder
                    / "persona_runtime"
                    / str(session.get("persona_conversation_session_id", ""))
                    / "conversation_realism_report.json"
                ).exists() else {}
            ),
            "facilitator_audit_feedback": (
                read_json(folder / "facilitator_audit_feedback.json")
                if (folder / "facilitator_audit_feedback.json").exists() else {}
            ),
        })
    missing = selected - {item["persona_id"] for item in interviews}
    if missing:
        raise ValueError(f"Completed concept interviews were not found for: {sorted(missing)}")
    run_id = run_dir.name
    resolved_topic = topic_label or manifest.get("topic_label") or manifest.get("concept_label") or DEFAULT_TOPIC_LABEL
    resolved_language = output_language or manifest.get("language") or DEFAULT_LANGUAGE
    resolved_assumptions = core_assumption_count or int(
        manifest.get("core_assumption_count", DEFAULT_CORE_ASSUMPTION_COUNT)
    )
    summary = _summary_payload(
        run_id,
        sorted(interviews, key=lambda item: item["persona_id"]),
        topic_label=resolved_topic,
        language=resolved_language,
        core_assumption_count=resolved_assumptions,
    )
    audit_panel = _facilitator_audit_panel_payload(
        run_id,
        sorted(interviews, key=lambda item: item["persona_id"]),
        topic_label=resolved_topic,
        summary=summary,
    )
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
    write_json(run_dir / "facilitator_audit_panel.json", audit_panel)
    (run_dir / "facilitator_audit_panel.md").write_text(
        _render_facilitator_audit_panel(audit_panel),
        encoding="utf-8",
    )
    write_json(run_dir / "progress.json", {"run_id": run_id, "interviews": interviews})
    write_json(run_dir / "manifest.json", {
        "run_id": run_id,
        "updated_at": utc_now_iso(),
        "topic_label": resolved_topic,
        "language": resolved_language,
        "core_assumption_count": resolved_assumptions,
        "persona_ids": sorted(selected),
        "persona_count": len(interviews),
        "synthetic_only": True,
    })
    return run_dir


def aggregate_facilitator_audit_runs(
    *,
    run_dirs: list[Path],
    output_dir: Path,
    label: str = "Facilitator Audit Learning Report",
) -> Path:
    audit_panels: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        panel_path = run_dir / "facilitator_audit_panel.json"
        if not panel_path.exists():
            raise ValueError(f"Facilitator audit panel was not found for run: {run_dir}")
        audit_panels.append(read_json(panel_path))
    ensure_dir(output_dir)
    report = _facilitator_audit_learning_report_payload(label=label, audit_panels=audit_panels)
    write_json(output_dir / "facilitator_audit_learning_report.json", report)
    (output_dir / "facilitator_audit_learning_report.md").write_text(
        _render_facilitator_audit_learning_report(report),
        encoding="utf-8",
    )
    write_json(output_dir / "manifest.json", {
        "label": label,
        "run_dirs": [str(path) for path in run_dirs],
        "run_count": len(run_dirs),
        "created_at": utc_now_iso(),
        "synthetic_only": True,
    })
    return output_dir


def _compare_facilitator_learning_effect_payload(
    *,
    label: str,
    baseline_runs: list[dict[str, Any]],
    candidate_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    def _average_quality(runs: list[dict[str, Any]]) -> float | None:
        scores = [
            run.get("panel_summary", {}).get("average_quality_score")
            for run in runs
            if isinstance(run.get("panel_summary", {}).get("average_quality_score"), (int, float))
        ]
        if not scores:
            return None
        return round(sum(float(item) for item in scores) / len(scores), 2)

    def _failure_mode_counts(runs: list[dict[str, Any]]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for run in runs:
            for item in run.get("audit_panel", {}).get("top_failure_modes", []):
                mode = str(item.get("failure_mode", "")).strip()
                if mode:
                    counts[mode] += int(item.get("persona_count", 0) or 0)
        return dict(counts)

    def _approved_rule_usage_counts(runs: list[dict[str, Any]]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for run in runs:
            for interview in run.get("interviews", []):
                for rule_id in interview.get("approved_learning_rule_ids", []):
                    if str(rule_id).strip():
                        counts[str(rule_id).strip()] += 1
        return dict(counts)

    def _followup_counts(runs: list[dict[str, Any]]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for run in runs:
            for item in run.get("audit_panel", {}).get("common_missed_high_value_followups", []):
                question = str(item.get("question", "")).strip()
                if question:
                    counts[question] += int(item.get("persona_count", 0) or 0)
        return dict(counts)

    def _effect_assessment(quality_delta: float | None, baseline_failures: dict[str, int], candidate_failures: dict[str, int]) -> str:
        if quality_delta is None and not baseline_failures and not candidate_failures:
            return "insufficient_evidence"
        baseline_total = sum(baseline_failures.values())
        candidate_total = sum(candidate_failures.values())
        if quality_delta is not None and quality_delta > 0 and candidate_total <= baseline_total:
            return "improved"
        if quality_delta is not None and quality_delta < 0 and candidate_total >= baseline_total:
            return "regressed"
        return "mixed_or_inconclusive"

    baseline_avg_quality = _average_quality(baseline_runs)
    candidate_avg_quality = _average_quality(candidate_runs)
    quality_delta = None
    if baseline_avg_quality is not None and candidate_avg_quality is not None:
        quality_delta = round(candidate_avg_quality - baseline_avg_quality, 2)
    baseline_failures = _failure_mode_counts(baseline_runs)
    candidate_failures = _failure_mode_counts(candidate_runs)
    baseline_followups = _followup_counts(baseline_runs)
    candidate_followups = _followup_counts(candidate_runs)
    approved_rule_usage = _approved_rule_usage_counts(candidate_runs)

    failure_mode_deltas = []
    for mode in sorted(set(baseline_failures) | set(candidate_failures)):
        baseline_count = baseline_failures.get(mode, 0)
        candidate_count = candidate_failures.get(mode, 0)
        failure_mode_deltas.append({
            "failure_mode": mode,
            "baseline_persona_count": baseline_count,
            "candidate_persona_count": candidate_count,
            "delta": candidate_count - baseline_count,
        })

    followup_deltas = []
    for question in sorted(set(baseline_followups) | set(candidate_followups)):
        baseline_count = baseline_followups.get(question, 0)
        candidate_count = candidate_followups.get(question, 0)
        followup_deltas.append({
            "question": question,
            "baseline_persona_count": baseline_count,
            "candidate_persona_count": candidate_count,
            "delta": candidate_count - baseline_count,
        })

    return {
        "artifact_version": "v1",
        "label": label,
        "baseline_run_count": len(baseline_runs),
        "candidate_run_count": len(candidate_runs),
        "baseline_average_quality_score": baseline_avg_quality,
        "candidate_average_quality_score": candidate_avg_quality,
        "quality_score_delta": quality_delta,
        "approved_rule_usage_counts": approved_rule_usage,
        "failure_mode_deltas": failure_mode_deltas,
        "missed_followup_deltas": followup_deltas,
        "effect_assessment": _effect_assessment(quality_delta, baseline_failures, candidate_failures),
        "synthetic_only_disclaimer": (
            "This facilitator learning effect report is synthetic comparative evidence only. "
            "Use it to judge whether approved learning rules seem directionally helpful before broader adoption."
        ),
    }


def _render_facilitator_learning_effect_report(report: dict[str, Any]) -> str:
    lines = [
        f"# {report.get('label', 'Facilitator Learning Effect Report')}", "",
        f"> {report.get('synthetic_only_disclaimer', '')}", "",
        f"- Baseline runs: {report.get('baseline_run_count', 0)}",
        f"- Candidate runs: {report.get('candidate_run_count', 0)}",
        f"- Baseline average quality: {report.get('baseline_average_quality_score', 'n/a')}",
        f"- Candidate average quality: {report.get('candidate_average_quality_score', 'n/a')}",
        f"- Quality delta: {report.get('quality_score_delta', 'n/a')}",
        f"- Effect assessment: {report.get('effect_assessment', 'unknown')}", "",
    ]
    if report.get("approved_rule_usage_counts"):
        lines.extend(["## Approved Rule Usage", ""])
        for rule_id, count in sorted(report["approved_rule_usage_counts"].items()):
            lines.append(f"- {rule_id}: {count}")
        lines.append("")
    if report.get("failure_mode_deltas"):
        lines.extend(["## Failure Mode Deltas", ""])
        for item in report["failure_mode_deltas"]:
            lines.append(
                f"- {item.get('failure_mode', '')}: baseline={item.get('baseline_persona_count', 0)}, "
                f"candidate={item.get('candidate_persona_count', 0)}, delta={item.get('delta', 0)}"
            )
        lines.append("")
    if report.get("missed_followup_deltas"):
        lines.extend(["## Missed Follow-Up Deltas", ""])
        for item in report["missed_followup_deltas"]:
            lines.append(
                f"- {item.get('question', '')}: baseline={item.get('baseline_persona_count', 0)}, "
                f"candidate={item.get('candidate_persona_count', 0)}, delta={item.get('delta', 0)}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def compare_facilitator_learning_effects(
    *,
    baseline_run_dirs: list[Path],
    candidate_run_dirs: list[Path],
    output_dir: Path,
    label: str = "Facilitator Learning Effect Report",
) -> Path:
    def _load_runs(run_dirs: list[Path]) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for run_dir in run_dirs:
            panel_summary_path = run_dir / "panel_summary.json"
            audit_panel_path = run_dir / "facilitator_audit_panel.json"
            interviews_dir = run_dir / "interviews"
            if not panel_summary_path.exists() or not audit_panel_path.exists():
                raise ValueError(f"Panel summary or facilitator audit panel was not found for run: {run_dir}")
            interviews: list[dict[str, Any]] = []
            if interviews_dir.exists():
                for folder in sorted(interviews_dir.iterdir()):
                    interview_path = folder / "interview.json"
                    if folder.is_dir() and interview_path.exists():
                        interviews.append(read_json(interview_path))
            runs.append({
                "run_dir": str(run_dir),
                "panel_summary": read_json(panel_summary_path),
                "audit_panel": read_json(audit_panel_path),
                "interviews": interviews,
            })
        return runs

    baseline_runs = _load_runs(baseline_run_dirs)
    candidate_runs = _load_runs(candidate_run_dirs)
    ensure_dir(output_dir)
    report = _compare_facilitator_learning_effect_payload(
        label=label,
        baseline_runs=baseline_runs,
        candidate_runs=candidate_runs,
    )
    write_json(output_dir / "facilitator_learning_effect_report.json", report)
    (output_dir / "facilitator_learning_effect_report.md").write_text(
        _render_facilitator_learning_effect_report(report),
        encoding="utf-8",
    )
    write_json(output_dir / "manifest.json", {
        "label": label,
        "baseline_run_dirs": [str(path) for path in baseline_run_dirs],
        "candidate_run_dirs": [str(path) for path in candidate_run_dirs],
        "created_at": utc_now_iso(),
        "synthetic_only": True,
    })
    return output_dir
