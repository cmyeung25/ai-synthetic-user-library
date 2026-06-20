from __future__ import annotations

from pathlib import Path

from ai_validation_swarm.domain.models import FounderBrief, PersonaResponse
from ai_validation_swarm.reporting.markdown import DISCLAIMER


def build_report_payload(
    *,
    run_id: str,
    brief: FounderBrief,
    panel_spec: dict[str, object],
    summary: dict[str, object],
    responses: list[PersonaResponse],
    planner_steps: list[str],
    report_markdown_path: str,
    report_markdown: str,
) -> dict[str, object]:
    return {
        "report_version": "report/v1",
        "run_id": run_id,
        "brief_id": brief.brief_id,
        "project_name": brief.project_name,
        "generated_at": summary.get("generated_at"),
        "run_status": summary.get("run_status"),
        "panel_spec": panel_spec,
        "brief_overview": {
            "problem_statement": brief.problem_statement,
            "target_market": brief.target_market,
            "offered_solution": brief.offered_solution,
            "validation_goal": brief.validation_goal,
            "pricing_hypothesis": brief.pricing_hypothesis,
        },
        "execution": {
            "selected_persona_count": summary.get("selected_persona_count"),
            "successful_response_count": summary.get("successful_response_count"),
            "failed_response_count": summary.get("failed_response_count"),
            "response_coverage_pct": summary.get("response_coverage_pct"),
            "failure_reasons": summary.get("failure_reasons", []),
        },
        "scores": summary.get("average_scores", {}),
        "trigger_clusters": summary.get("trigger_clusters", []),
        "objection_clusters": summary.get("objection_clusters", []),
        "segment_summary": summary.get("segment_summary", {}),
        "risk_map": summary.get("risk_map", []),
        "skeptic_review": summary.get("skeptic_review", {}),
        "assumption_risk_map": summary.get("assumption_risk_map", []),
        "planner_steps": planner_steps,
        "response_index": [
            {
                "synthetic_user_id": response.synthetic_user_id,
                "panel_role": response.panel_role,
                "likely_objection": response.likely_objection,
                "what_would_make_them_try": response.what_would_make_them_try,
                "scorecard": response.scorecard,
            }
            for response in responses
        ],
        "disclaimer": DISCLAIMER,
        "report_markdown_path": report_markdown_path,
        "report_markdown": report_markdown,
    }


def build_archive_index_entry(
    *,
    run_id: str,
    run_payload: dict[str, object],
    report_payload: dict[str, object],
    run_dir: Path,
) -> dict[str, object]:
    selected_persona_ids = run_payload.get("selected_persona_ids", [])
    return {
        "run_id": run_id,
        "brief_id": run_payload["brief_id"],
        "project_name": report_payload["project_name"],
        "run_status": run_payload["status"],
        "selected_persona_count": len(selected_persona_ids) if isinstance(selected_persona_ids, list) else 0,
        "successful_response_count": run_payload["successful_response_count"],
        "failed_response_count": run_payload["failed_response_count"],
        "error_count": run_payload["error_count"],
        "created_at": run_payload["started_at"],
        "model_version": run_payload["model_version"],
        "panel_type": run_payload["panel_spec"]["panel_type"],
        "paths": {
            "run_dir": str(run_dir),
            "report_markdown": str(run_dir / "report.md"),
            "report_json": str(run_dir / "report.json"),
        },
    }
