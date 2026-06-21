from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import uuid

from ai_validation_swarm.domain.models import utc_now_iso
from ai_validation_swarm.facilitator.providers import FacilitatorProvider
from ai_validation_swarm.observer.runtime import ObserverControlledInterviewRuntime
from ai_validation_swarm.conversation.providers import ConversationProvider
from ai_validation_swarm.storage.files import ensure_dir, read_json, write_json


RESEARCH_GOAL = (
    "了解 persona 有冇真實 follow-up 遺漏問題、目前點處理，以及 AI Follow-up Copilot 嘅信任、"
    "首個價值、setup、pricing、retention 同 founder assumptions。"
)
PRODUCT_CONTEXT = "AI Follow-up Copilot concept validation；必須依照 versioned protocol，中立介紹，唔可以銷售。"
CORE_ASSUMPTION_COUNT = 8


def _persona_ids(data_dir: Path) -> list[str]:
    return sorted(
        path.name for path in data_dir.iterdir()
        if path.is_dir() and (
            (path / "v3_3" / "profile.json").exists()
            or (path / "v3_2" / "profile.json").exists()
        )
    )


def _summary_payload(run_id: str, interviews: list[dict[str, Any]]) -> dict[str, Any]:
    assumption_rows: dict[int, dict[str, Any]] = {}
    additional_findings: list[dict[str, Any]] = []
    for interview in interviews:
        report = interview.get("report", {})
        for index, item in enumerate(report.get("assumption_validation", []), start=1):
            if index > CORE_ASSUMPTION_COUNT:
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
        "topic": "AI Follow-up Copilot",
        "language": "Natural Cantonese Traditional Chinese",
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
        "# AI Follow-up Copilot Synthetic Persona Panel", "",
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
            # Some providers serialize two list items into one string. Preserve both
            # observations while keeping the panel report readable.
            for clean_insight in str(insight).replace("。','", "。\n").splitlines():
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


def run_ai_followup_copilot_panel(
    *,
    data_dir: Path,
    output_dir: Path,
    facilitator_provider: FacilitatorProvider,
    persona_provider: ConversationProvider,
    quality_provider: FacilitatorProvider,
    max_turns: int = 12,
) -> Path:
    run_id = f"followup_copilot_{utc_now_iso()[:10].replace('-', '')}_{uuid.uuid4().hex[:8]}"
    run_dir = output_dir / run_id
    interview_dir = run_dir / "interviews"
    ensure_dir(interview_dir)
    runtime = ObserverControlledInterviewRuntime(
        data_dir=data_dir,
        session_dir=interview_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
    )
    interviews: list[dict[str, Any]] = []
    for persona_id in _persona_ids(data_dir):
        folder, session = runtime.start(
            persona_id=persona_id,
            research_goal=RESEARCH_GOAL,
            interview_mode="concept_validation",
            product_context=PRODUCT_CONTEXT,
            output_language="Natural Cantonese Traditional Chinese",
            max_turns=max_turns,
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
        write_json(run_dir / "progress.json", {"run_id": run_id, "interviews": interviews})

    summary = _summary_payload(run_id, interviews)
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
    write_json(run_dir / "manifest.json", {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "persona_ids": [item["persona_id"] for item in interviews],
        "max_turns": max_turns,
        "language": "Natural Cantonese Traditional Chinese",
        "synthetic_only": True,
    })
    return run_dir


def summarize_existing_concept_panel(*, run_dir: Path, persona_ids: list[str]) -> Path:
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
    summary = _summary_payload(run_id, sorted(interviews, key=lambda item: item["persona_id"]))
    write_json(run_dir / "panel_summary.json", summary)
    (run_dir / "panel_summary.md").write_text(_render_summary(summary, interviews), encoding="utf-8")
    write_json(run_dir / "progress.json", {"run_id": run_id, "interviews": interviews})
    write_json(run_dir / "manifest.json", {
        "run_id": run_id,
        "updated_at": utc_now_iso(),
        "persona_ids": sorted(selected),
        "persona_count": len(interviews),
        "language": "Natural Cantonese Traditional Chinese",
        "synthetic_only": True,
    })
    return run_dir
