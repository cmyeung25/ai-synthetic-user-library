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


def _persona_ids(data_dir: Path, selected: list[str] | None = None) -> list[str]:
    available = sorted(
        path.name for path in data_dir.iterdir()
        if path.is_dir() and (
            (path / "v4" / "profile.json").exists()
            or (path / "v3_3" / "profile.json").exists()
            or (path / "v3_2" / "profile.json").exists()
        )
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
    for interview in interviews:
        report = interview.get("report", {})
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
        } for item in interviews],
        "synthetic_only_disclaimer": (
            "This panel contains synthetic AI pre-validation only. It cannot establish market demand, "
            "pricing, prevalence, or replace interviews with real people."
        ),
    }


def _render_summary(summary: dict[str, Any], interviews: list[dict[str, Any]]) -> str:
    lines = [
        f"# {summary['topic']} Synthetic Persona Panel", "",
        f"> {summary['synthetic_only_disclaimer']}", "",
        f"- Personas: {summary['persona_count']}",
        f"- Language: {summary['language']}",
        f"- Average interview quality: {summary['average_quality_score']}",
        f"- Problem evidence: {summary['problem_strength_counts']}", "",
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
        for insight in report.get("key_insights", []):
            for clean_insight in str(insight).replace("??,'", "\n").splitlines():
                clean_insight = clean_insight.strip(" ,'\"")
                if clean_insight:
                    lines.append(f"- {clean_insight}")
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
    progress_writer=None,
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
        )
        while session.status not in {"completed", "failed"}:
            session = runtime.continue_interview(session.interview_id)
        report = read_json(folder / "insight_report.json") if (folder / "insight_report.json").exists() else {}
        quality = read_json(folder / "quality_evaluation.json") if (folder / "quality_evaluation.json").exists() else {}
        interviews.append({
            "persona_id": persona_id,
            "persona_name": session.persona_name,
            "interview_id": session.interview_id,
            "status": session.status,
            "error": session.last_error,
            "folder": str(folder),
            "report": report,
            "quality": quality,
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
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
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
    progress_writer=None,
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
        progress_writer=progress_writer,
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
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
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
