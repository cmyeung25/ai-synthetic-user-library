from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, TypeVar
import uuid

from ai_validation_swarm.domain.models import (
    AuditFinding,
    PanelSpec,
    SkepticFinding,
    SkepticReview,
    ValidationRun,
    utc_now_iso,
)
from ai_validation_swarm.domain.validators import load_and_validate_founder_brief, validate_panel_spec
from ai_validation_swarm.personas.generator import PANEL_ROLES
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.reporting.archive import update_run_archive_index
from ai_validation_swarm.reporting.artifacts import build_archive_index_entry, build_report_payload
from ai_validation_swarm.reporting.markdown import render_failure_report, render_report
from ai_validation_swarm.reporting.summary import build_summary
from ai_validation_swarm.saas.run_contract import build_validation_run_contract, write_shared_run_contract
from ai_validation_swarm.sampling.engine import sample_personas
from ai_validation_swarm.storage.files import ensure_dir, load_personas, write_json

PROTOCOL_ID = "problem_validation/v1"
PROMPT_VERSION = "persona-response/v1, skeptic-review/v1, sensitive-audit/v1, report-writer/v1"
T = TypeVar("T")


def _new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    return f"run_{timestamp}_{uuid.uuid4().hex[:8]}"


def _make_error_record(*, stage_name: str, attempt: int, exc: Exception, persona_id: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "stage_name": stage_name,
        "attempt": attempt,
        "error_type": exc.__class__.__name__,
        "message": str(exc),
        "occurred_at": utc_now_iso(),
    }
    if persona_id:
        payload["synthetic_user_id"] = persona_id
    return payload


def _execute_with_retries(
    *,
    stage_name: str,
    max_retries: int,
    operation: Callable[[], T],
    persona_id: str | None = None,
) -> tuple[T | None, dict[str, object], list[dict[str, object]]]:
    started_at = utc_now_iso()
    errors: list[dict[str, object]] = []
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):
        try:
            result = operation()
            return (
                result,
                {
                    "stage_name": stage_name,
                    "status": "succeeded",
                    "attempt_count": attempt,
                    "max_retries": max_retries,
                    "started_at": started_at,
                    "finished_at": utc_now_iso(),
                    "errors": errors,
                },
                errors,
            )
        except Exception as exc:  # pragma: no cover - exercised by integration tests via custom providers
            errors.append(_make_error_record(stage_name=stage_name, attempt=attempt, exc=exc, persona_id=persona_id))

    return (
        None,
        {
            "stage_name": stage_name,
            "status": "failed",
            "attempt_count": total_attempts,
            "max_retries": max_retries,
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "errors": errors,
        },
        errors,
    )


def _execute_stage_with_fallback(
    *,
    stage_name: str,
    max_retries: int,
    operation: Callable[[], T],
    fallback_factory: Callable[[], T] | None = None,
) -> tuple[T | None, dict[str, object], list[dict[str, object]]]:
    result, metadata, errors = _execute_with_retries(stage_name=stage_name, max_retries=max_retries, operation=operation)
    if result is not None:
        metadata["fallback_used"] = False
        return result, metadata, errors

    metadata["fallback_used"] = fallback_factory is not None
    if fallback_factory is None:
        return None, metadata, errors

    fallback_result = fallback_factory()
    metadata["status"] = "fallback"
    metadata["finished_at"] = utc_now_iso()
    return fallback_result, metadata, errors


def _execute_persona_responses(
    *,
    selected_personas: list,
    brief,
    provider: BaseProvider,
    max_retries: int,
) -> tuple[list, list[dict[str, object]], dict[str, object], list[dict[str, object]]]:
    responses = []
    response_records: list[dict[str, object]] = []
    all_errors: list[dict[str, object]] = []
    stage_started_at = utc_now_iso()

    for persona in selected_personas:
        persona_id = persona.profile.synthetic_user_id
        response, metadata, errors = _execute_with_retries(
            stage_name="persona_response",
            max_retries=max_retries,
            operation=lambda persona=persona: provider.persona_response(persona, brief, PROTOCOL_ID),
            persona_id=persona_id,
        )
        all_errors.extend(errors)
        record = {
            "synthetic_user_id": persona_id,
            "panel_role": persona.seed.panel_role,
            "protocol_id": PROTOCOL_ID,
            "status": metadata["status"],
            "attempt_count": metadata["attempt_count"],
            "max_retries": max_retries,
            "started_at": metadata["started_at"],
            "finished_at": metadata["finished_at"],
            "errors": errors,
            "response": response.to_dict() if response is not None else None,
        }
        response_records.append(record)
        if response is not None:
            responses.append(response)

    successful_count = len(responses)
    failed_count = len(selected_personas) - successful_count
    if failed_count == 0:
        status = "succeeded"
    elif successful_count == 0:
        status = "failed"
    else:
        status = "partial_failed"

    stage_result = {
        "stage_name": "persona_responses",
        "status": status,
        "selected_count": len(selected_personas),
        "successful_count": successful_count,
        "failed_count": failed_count,
        "max_retries": max_retries,
        "started_at": stage_started_at,
        "finished_at": utc_now_iso(),
    }
    return responses, response_records, stage_result, all_errors


def _default_skeptic_review() -> SkepticReview:
    return SkepticReview(
        review_version="skeptic-review/fallback-v1",
        summary="Skeptic review failed during this run, so these assumptions need manual review.",
        challenged_assumptions=[
            SkepticFinding(
                finding_id="skeptic_fallback_manual_review",
                severity="medium",
                title="Skeptic review unavailable",
                observation="Skeptic review did not complete, so assumption pressure-testing remains incomplete.",
                evidence_refs=["stage_results"],
                recommended_validation_question="Which raw persona signals should be reviewed manually before the founder relies on this run?",
            )
        ],
    )


def _default_audit_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            category="reporting_risk",
            severity="medium",
            observation="Sensitive-topic audit failed during this run. Review raw responses manually before using this output for decisions.",
            evidence_refs=["stage_results"],
            recommended_validation_question="Which safety or trust issues still need manual review before proceeding?",
        )
    ]


def _default_planner_steps() -> list[str]:
    return [
        "Review raw persona responses and logged errors before trusting the current synthesis.",
        "Retry the run after provider stability is restored or narrowed filters are adjusted.",
        "Use direct user interviews to validate the strongest unresolved assumption from this run.",
    ]


def _build_failure_summary(*, brief, selected_persona_count: int, failure_reasons: list[str], error_count: int) -> dict[str, object]:
    fallback_skeptic = _default_skeptic_review().to_dict()
    return {
        "aggregation_version": "aggregator/v1",
        "project_name": brief.project_name,
        "persona_count": selected_persona_count,
        "selected_persona_count": selected_persona_count,
        "successful_response_count": 0,
        "failed_response_count": selected_persona_count,
        "response_coverage_pct": 0.0,
        "run_status": "failed",
        "failure_reasons": failure_reasons,
        "error_count": error_count,
        "average_scores": {},
        "top_buying_triggers": [],
        "top_objections": [],
        "trigger_clusters": [],
        "objection_clusters": [],
        "segment_summary": {},
        "risk_map": [],
        "audit_categories": [],
        "skeptic_review": fallback_skeptic,
        "assumption_risk_map": fallback_skeptic["challenged_assumptions"],
    }


def run_validation(
    brief_path: Path,
    persona_dir: Path,
    panel_spec: PanelSpec,
    provider: BaseProvider,
    run_root: Path,
    *,
    max_retries: int = 1,
) -> Path:
    brief = load_and_validate_founder_brief(brief_path)
    panel_spec = validate_panel_spec(panel_spec, allowed_panel_types=set(PANEL_ROLES))
    personas = load_personas(persona_dir)
    if not personas:
        raise ValueError("No personas found. Generate personas before running validation.")

    run_id = _new_run_id()
    run_dir = run_root / run_id
    ensure_dir(run_dir)
    started_at = utc_now_iso()

    artifact_paths = [
        "brief.json",
        "panel.json",
        "selected_personas.json",
        "sampling.json",
        "raw_responses.json",
        "stage_results.json",
        "errors.json",
        "skeptic.json",
        "audit.json",
        "aggregation.json",
        "summary.json",
        "report.json",
        "planner.json",
        "report.md",
    ]

    write_json(run_dir / "brief.json", brief.to_dict())
    write_json(run_dir / "panel.json", panel_spec.to_dict())
    selected_personas = []
    stage_results: dict[str, object] = {}
    error_records: list[dict[str, object]] = []
    failure_reasons: list[str] = []
    run_status = "running"
    summary: dict[str, object]
    successful_response_count = 0
    failed_response_count = 0
    report_markdown = ""
    report_payload: dict[str, object]

    try:
        sampling_result = sample_personas(personas, panel_spec)
        selected_personas = sampling_result.personas
        stage_results["sampling"] = {
            "stage_name": "sampling",
            "status": "succeeded",
            "selected_count": len(selected_personas),
            "started_at": started_at,
            "finished_at": utc_now_iso(),
        }
        write_json(run_dir / "selected_personas.json", [persona.profile.basic_identity for persona in selected_personas])
        write_json(
            run_dir / "sampling.json",
            {
                "rationale": sampling_result.rationale,
                "explainability": sampling_result.explainability,
            },
        )

        responses, response_records, persona_stage_result, persona_errors = _execute_persona_responses(
            selected_personas=selected_personas,
            brief=brief,
            provider=provider,
            max_retries=max_retries,
        )
        error_records.extend(persona_errors)
        stage_results["persona_responses"] = persona_stage_result
        successful_response_count = persona_stage_result["successful_count"]
        failed_response_count = persona_stage_result["failed_count"]
        write_json(run_dir / "raw_responses.json", response_records)

        if successful_response_count == 0:
            run_status = "failed"
            failure_reasons.append("All persona responses failed after retries.")
            summary = _build_failure_summary(
                brief=brief,
                selected_persona_count=len(selected_personas),
                failure_reasons=failure_reasons,
                error_count=len(error_records),
            )
            write_json(run_dir / "skeptic.json", _default_skeptic_review().to_dict())
            write_json(run_dir / "aggregation.json", summary)
            write_json(run_dir / "audit.json", [finding.to_dict() for finding in _default_audit_findings()])
            write_json(run_dir / "planner.json", _default_planner_steps())
            report_markdown = render_failure_report(
                brief,
                selected_persona_count=len(selected_personas),
                failure_reasons=failure_reasons,
                error_count=len(error_records),
            )
            summary["generated_at"] = utc_now_iso()
            report_payload = build_report_payload(
                run_id=run_id,
                brief=brief,
                panel_spec=panel_spec.to_dict(),
                summary=summary,
                responses=[],
                planner_steps=_default_planner_steps(),
                report_markdown_path="report.md",
                report_markdown=report_markdown,
            )
            write_json(run_dir / "report.json", report_payload)
            (run_dir / "report.md").write_text(report_markdown, encoding="utf-8")
        else:
            run_status = "partial_failed" if failed_response_count > 0 else "completed"

            skeptic, skeptic_metadata, skeptic_errors = _execute_stage_with_fallback(
                stage_name="skeptic_review",
                max_retries=max_retries,
                operation=lambda: provider.skeptic_review(brief, selected_personas, responses),
                fallback_factory=_default_skeptic_review,
            )
            stage_results["skeptic_review"] = skeptic_metadata
            error_records.extend(skeptic_errors)
            if skeptic_metadata["status"] != "succeeded":
                run_status = "partial_failed"
                failure_reasons.append("Skeptic review failed after retries; fallback output was used.")

            findings, audit_metadata, audit_errors = _execute_stage_with_fallback(
                stage_name="sensitive_audit",
                max_retries=max_retries,
                operation=lambda: provider.sensitive_audit(brief, selected_personas, responses),
                fallback_factory=_default_audit_findings,
            )
            stage_results["sensitive_audit"] = audit_metadata
            error_records.extend(audit_errors)
            if audit_metadata["status"] != "succeeded":
                run_status = "partial_failed"
                failure_reasons.append("Sensitive-topic audit failed after retries; fallback output was used.")

            summary = build_summary(
                brief,
                selected_personas,
                responses,
                findings,
                skeptic,
                run_status=run_status,
                failure_reasons=failure_reasons,
            )
            stage_results["aggregation"] = {
                "stage_name": "aggregation",
                "status": "succeeded",
                "started_at": utc_now_iso(),
                "finished_at": utc_now_iso(),
            }

            planner_steps, planner_metadata, planner_errors = _execute_stage_with_fallback(
                stage_name="planner",
                max_retries=max_retries,
                operation=lambda: provider.planner(brief, summary, findings),
                fallback_factory=_default_planner_steps,
            )
            stage_results["planner"] = planner_metadata
            error_records.extend(planner_errors)
            if planner_metadata["status"] != "succeeded":
                run_status = "partial_failed"
                failure_reasons.append("Validation planner failed after retries; fallback steps were used.")
                summary["run_status"] = run_status
                summary["failure_reasons"] = failure_reasons

            report_result, report_metadata, report_errors = _execute_stage_with_fallback(
                stage_name="report_writer",
                max_retries=max_retries,
                operation=lambda: render_report(brief, summary, findings, planner_steps, responses),
                fallback_factory=lambda: render_failure_report(
                    brief,
                    selected_persona_count=len(selected_personas),
                    failure_reasons=failure_reasons or ["Report rendering failed after retries."],
                    error_count=len(error_records),
                ),
            )
            stage_results["report_writer"] = report_metadata
            error_records.extend(report_errors)
            if report_metadata["status"] != "succeeded":
                run_status = "partial_failed"
                failure_reasons.append("Report rendering failed after retries; fallback report was used.")
                summary["run_status"] = run_status
                summary["failure_reasons"] = failure_reasons

            write_json(run_dir / "skeptic.json", skeptic.to_dict())
            write_json(run_dir / "audit.json", [finding.to_dict() for finding in findings])
            write_json(run_dir / "aggregation.json", summary)
            write_json(run_dir / "planner.json", planner_steps)
            report_markdown = str(report_result)
            summary["generated_at"] = utc_now_iso()
            report_payload = build_report_payload(
                run_id=run_id,
                brief=brief,
                panel_spec=panel_spec.to_dict(),
                summary=summary,
                responses=responses,
                planner_steps=planner_steps,
                report_markdown_path="report.md",
                report_markdown=report_markdown,
            )
            write_json(run_dir / "report.json", report_payload)
            (run_dir / "report.md").write_text(report_markdown, encoding="utf-8")

    except Exception as exc:
        run_status = "failed"
        error_records.append(_make_error_record(stage_name="validation_runner", attempt=1, exc=exc))
        failure_reasons.append(str(exc))
        summary = _build_failure_summary(
            brief=brief,
            selected_persona_count=len(selected_personas),
            failure_reasons=failure_reasons,
            error_count=len(error_records),
        )
        stage_results["validation_runner"] = {
            "stage_name": "validation_runner",
            "status": "failed",
            "started_at": started_at,
            "finished_at": utc_now_iso(),
        }
        if not (run_dir / "selected_personas.json").exists():
            write_json(run_dir / "selected_personas.json", [persona.profile.basic_identity for persona in selected_personas])
        if not (run_dir / "sampling.json").exists():
            write_json(
                run_dir / "sampling.json",
                {
                    "rationale": "",
                    "explainability": {},
                    "status": "failed",
                    "failure_reasons": failure_reasons,
                },
            )
        if not (run_dir / "raw_responses.json").exists():
            write_json(run_dir / "raw_responses.json", [])
        if not (run_dir / "skeptic.json").exists():
            write_json(run_dir / "skeptic.json", _default_skeptic_review().to_dict())
        if not (run_dir / "audit.json").exists():
            write_json(run_dir / "audit.json", [finding.to_dict() for finding in _default_audit_findings()])
        if not (run_dir / "aggregation.json").exists():
            write_json(run_dir / "aggregation.json", summary)
        if not (run_dir / "planner.json").exists():
            write_json(run_dir / "planner.json", _default_planner_steps())
        report_markdown = render_failure_report(
            brief,
            selected_persona_count=len(selected_personas),
            failure_reasons=failure_reasons,
            error_count=len(error_records),
        )
        summary["generated_at"] = utc_now_iso()
        report_payload = build_report_payload(
            run_id=run_id,
            brief=brief,
            panel_spec=panel_spec.to_dict(),
            summary=summary,
            responses=[],
            planner_steps=_default_planner_steps(),
            report_markdown_path="report.md",
            report_markdown=report_markdown,
        )
        write_json(run_dir / "report.json", report_payload)
        (run_dir / "report.md").write_text(report_markdown, encoding="utf-8")

    write_json(run_dir / "errors.json", error_records)
    write_json(run_dir / "stage_results.json", stage_results)
    write_json(run_dir / "summary.json", summary)

    run_manifest = ValidationRun(
        run_id=run_id,
        brief_id=brief.brief_id,
        panel_spec=panel_spec,
        selected_persona_ids=[persona.profile.synthetic_user_id for persona in selected_personas],
        prompt_version=PROMPT_VERSION,
        model_version=provider.model_version,
        started_at=started_at,
        finished_at=utc_now_iso(),
        token_estimate=0,
        cost_estimate=0.0,
        status=run_status,
        successful_response_count=successful_response_count,
        failed_response_count=failed_response_count,
        error_count=len(error_records),
        failure_reasons=failure_reasons,
        artifact_paths=artifact_paths,
    )
    run_payload = run_manifest.to_dict()
    write_json(run_dir / "run.json", run_payload)
    write_shared_run_contract(
        run_dir / "run_contract.json",
        build_validation_run_contract(
            run_id=run_id,
            brief_id=brief.brief_id,
            panel_spec=panel_spec,
            created_at=started_at,
            started_at=started_at,
            status=run_status,
            output_path=run_dir,
            artifact_paths=artifact_paths + ["run_contract.json"],
            selected_persona_ids=[persona.profile.synthetic_user_id for persona in selected_personas],
            successful_response_count=successful_response_count,
            failed_response_count=failed_response_count,
            error_count=len(error_records),
            provider_name=provider.__class__.__name__,
            model_name=provider.model_version,
            finished_at=run_payload["finished_at"],
        ),
    )
    update_run_archive_index(
        run_root / "index.json",
        build_archive_index_entry(
            run_id=run_id,
            run_payload=run_payload,
            report_payload=report_payload,
            run_dir=run_dir,
        ),
    )
    return run_dir
