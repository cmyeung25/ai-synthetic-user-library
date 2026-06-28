from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_validation_swarm.saas.metadata_store import metadata_db_path


ALLOWED_FAMILIES = {"all", "input", "trace", "analysis", "output"}
ALLOWED_SORTS = {"relevance", "newest", "family"}
CROSS_RUN_MAX_CANDIDATES = 3


INPUT_ARTIFACTS = {
    "brief.json",
    "panel.json",
    "selected_personas.json",
    "sampling.json",
}
TRACE_ARTIFACTS = {
    "raw_responses.json",
    "stage_results.json",
    "errors.json",
    "run.json",
}
ANALYSIS_ARTIFACTS = {
    "audit.json",
    "aggregation.json",
    "summary.json",
    "skeptic.json",
    "planner.json",
}
OUTPUT_ARTIFACTS = {
    "report.json",
    "report.md",
    "run_contract.json",
}


def _connect_metadata(index_root: Path) -> sqlite3.Connection:
    db_path = metadata_db_path(index_root)
    if not db_path.exists():
        raise FileNotFoundError(f"Metadata index not found: {db_path}")
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def _normalize_query_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_family(value: str | None) -> str:
    family = (value or "all").strip().lower()
    return family if family in ALLOWED_FAMILIES else "all"


def _normalize_sort(value: str | None) -> str:
    sort_by = (value or "relevance").strip().lower()
    return sort_by if sort_by in ALLOWED_SORTS else "relevance"


def _artifact_family(artifact_rel_path: str) -> str:
    name = Path(artifact_rel_path).name
    if name in INPUT_ARTIFACTS:
        return "input"
    if name in TRACE_ARTIFACTS:
        return "trace"
    if name in ANALYSIS_ARTIFACTS:
        return "analysis"
    return "output"


def _artifact_kind(artifact_rel_path: str) -> str:
    name = Path(artifact_rel_path).name
    mapping = {
        "brief.json": "brief",
        "panel.json": "panel_spec",
        "selected_personas.json": "selected_personas",
        "sampling.json": "sampling_rationale",
        "raw_responses.json": "persona_responses",
        "stage_results.json": "stage_results",
        "errors.json": "error_log",
        "run.json": "run_manifest",
        "audit.json": "audit_findings",
        "aggregation.json": "aggregation",
        "summary.json": "run_summary",
        "skeptic.json": "skeptic_review",
        "planner.json": "planner_steps",
        "report.json": "report",
        "report.md": "summary_markdown",
        "run_contract.json": "run_contract",
    }
    return mapping.get(name, Path(artifact_rel_path).suffix.lstrip(".") or "artifact")


def _artifact_title(artifact_rel_path: str) -> str:
    name = Path(artifact_rel_path).name
    mapping = {
        "brief.json": "Run brief",
        "panel.json": "Panel spec",
        "selected_personas.json": "Selected personas",
        "sampling.json": "Sampling rationale",
        "raw_responses.json": "Persona responses",
        "stage_results.json": "Stage results",
        "errors.json": "Error log",
        "run.json": "Run manifest",
        "audit.json": "Sensitive-topic audit",
        "aggregation.json": "Aggregation summary",
        "summary.json": "Run summary",
        "skeptic.json": "Skeptic review",
        "planner.json": "Planner steps",
        "report.json": "Run report",
        "report.md": "Markdown report",
        "run_contract.json": "Run contract",
    }
    return mapping.get(name, name)


def _result_id_for_artifact(artifact_rel_path: str) -> tuple[str, str]:
    slug = (
        artifact_rel_path.replace("\\", "/")
        .replace("/", "-")
        .replace(".", "-")
        .replace(" ", "-")
        .lower()
    )
    artifact_id = f"artifact-{slug}"
    return artifact_id, f"query-{artifact_id}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_markdown_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _humanize_stage_name(stage_name: str) -> str:
    return stage_name.replace("_", " ").strip().title()


def _planner_timestamp(step_text: str, index: int) -> str:
    text = str(step_text or "").strip()
    if ":" in text:
        prefix = text.split(":", 1)[0].strip()
        if prefix:
            return prefix
    return f"step {index}"


def _build_raw_response_replay_steps(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replay_steps: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        response = item.get("response") if isinstance(item.get("response"), dict) else {}
        synthetic_user_id = str(item.get("synthetic_user_id") or f"persona_{index}")
        panel_role = str(item.get("panel_role") or response.get("panel_role") or "").strip()
        objection = str(response.get("likely_objection") or "no explicit objection")
        try_signal = str(response.get("what_would_make_them_try") or "no explicit try signal")
        trust_concern = str(response.get("trust_concern") or "").strip()
        pricing_reaction = str(response.get("pricing_reaction") or "").strip()
        reject_signal = str(response.get("what_would_make_them_reject") or "").strip()
        note_parts = []
        if panel_role:
            note_parts.append(f"Role: {panel_role}.")
        note_parts.append(f"Objection: {objection}.")
        note_parts.append(f"Try signal: {try_signal}.")
        if trust_concern:
            note_parts.append(f"Trust concern: {trust_concern}.")
        if pricing_reaction:
            note_parts.append(f"Pricing reaction: {pricing_reaction}.")
        if reject_signal:
            note_parts.append(f"Reject signal: {reject_signal}.")
        replay_steps.append(
            {
                "id": f"response-{index:02d}",
                "title": f"{synthetic_user_id} response",
                "timestamp": _first_text(item.get("finished_at"), item.get("started_at")) or f"response {index}",
                "note": " ".join(note_parts),
                "synthetic_user_id": synthetic_user_id,
                "panel_role": panel_role or None,
            }
        )
    return replay_steps


def _build_stage_result_replay_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    replay_steps: list[dict[str, Any]] = []
    for stage_name, stage_payload in payload.items():
        if not isinstance(stage_payload, dict):
            continue
        status = str(stage_payload.get("status") or "unknown")
        errors = stage_payload.get("errors") if isinstance(stage_payload.get("errors"), list) else []
        note_parts = [f"Status: {status}."]
        if isinstance(stage_payload.get("selected_count"), int):
            note_parts.append(f"Selected: {stage_payload['selected_count']}.")
        if isinstance(stage_payload.get("successful_count"), int):
            note_parts.append(f"Successful: {stage_payload['successful_count']}.")
        if isinstance(stage_payload.get("failed_count"), int):
            note_parts.append(f"Failed: {stage_payload['failed_count']}.")
        if isinstance(stage_payload.get("attempt_count"), int):
            note_parts.append(f"Attempts: {stage_payload['attempt_count']}.")
        if isinstance(stage_payload.get("max_retries"), int):
            note_parts.append(f"Max retries: {stage_payload['max_retries']}.")
        if stage_payload.get("fallback_used") is True:
            note_parts.append("Fallback used.")
        if errors:
            note_parts.append(f"Errors: {len(errors)}.")
            first_error = next((str(item).strip() for item in errors if str(item).strip()), "")
            if first_error:
                note_parts.append(f"First error: {first_error}.")
        replay_steps.append(
            {
                "id": f"stage-{stage_name}",
                "title": _humanize_stage_name(str(stage_name)),
                "timestamp": _first_text(stage_payload.get("finished_at"), stage_payload.get("started_at")) or status,
                "note": " ".join(note_parts),
            }
        )
    return replay_steps


def _build_error_replay_steps(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replay_steps: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        replay_steps.append(
            {
                "id": f"error-{index:02d}",
                "title": _humanize_stage_name(str(item.get("stage_name") or f"error_{index}")),
                "timestamp": _first_text(item.get("timestamp"), item.get("finished_at"), item.get("started_at")) or f"error {index}",
                "note": str(item.get("message") or "No error detail available."),
            }
        )
    return replay_steps


def _build_planner_replay_steps(payload: list[Any]) -> list[dict[str, Any]]:
    replay_steps: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        text = str(item or "").strip()
        if not text:
            continue
        replay_steps.append(
            {
                "id": f"planner-{index:02d}",
                "title": f"Planner step {index}",
                "timestamp": _planner_timestamp(text, index),
                "note": text,
            }
        )
    return replay_steps


def _report_summary(payload: dict[str, Any]) -> tuple[str, list[str]]:
    project_name = str(payload.get("project_name") or "report")
    run_status = str(payload.get("run_status") or "unknown")
    summary = f"{project_name} report with run status {run_status}."
    detail_lines: list[str] = []
    brief = payload.get("brief_overview")
    if isinstance(brief, dict) and brief.get("validation_goal"):
        detail_lines.append(f"Validation goal: {brief['validation_goal']}")
    scores = payload.get("scores")
    if isinstance(scores, dict):
        detail_lines.append(
            "Scores: "
            + ", ".join(f"{key}={value}" for key, value in scores.items() if value is not None)
        )
    objections = payload.get("objection_clusters")
    if isinstance(objections, list) and objections:
        first = objections[0]
        if isinstance(first, dict) and first.get("objection"):
            detail_lines.append(f"Top objection: {first['objection']}")
    planner_steps = payload.get("planner_steps")
    if isinstance(planner_steps, list) and planner_steps:
        detail_lines.append(f"Next step: {planner_steps[0]}")
    return summary, detail_lines


def _summary_payload_summary(payload: dict[str, Any]) -> tuple[str, list[str]]:
    run_status = str(payload.get("run_status") or "unknown")
    summary = f"Run summary with status {run_status}."
    detail_lines: list[str] = []
    triggers = payload.get("top_buying_triggers")
    if isinstance(triggers, list) and triggers:
        first = triggers[0]
        if isinstance(first, dict) and first.get("trigger"):
            detail_lines.append(f"Top trigger: {first['trigger']}")
    objections = payload.get("top_objections")
    if isinstance(objections, list) and objections:
        first = objections[0]
        if isinstance(first, dict) and first.get("objection"):
            detail_lines.append(f"Top objection: {first['objection']}")
    risk_map = payload.get("risk_map")
    if isinstance(risk_map, list) and risk_map:
        first = risk_map[0]
        if isinstance(first, dict) and first.get("category"):
            detail_lines.append(f"Primary risk: {first['category']}")
    return summary, detail_lines


def _build_artifact_entry(
    *,
    run_id: str,
    artifact_rel_path: str,
    artifact_path: Path,
    artifact_type: str,
    sort_timestamp: int,
) -> dict[str, Any]:
    family = _artifact_family(artifact_rel_path)
    kind = _artifact_kind(artifact_rel_path)
    title = _artifact_title(artifact_rel_path)
    artifact_id, result_id = _result_id_for_artifact(artifact_rel_path)
    tags = [family, kind]
    detail_lines: list[str] = []
    replay_steps: list[dict[str, Any]] = []
    summary = f"{title} artifact."

    try:
        if artifact_path.suffix.lower() == ".json":
            payload = _read_json(artifact_path)
            name = Path(artifact_rel_path).name
            if name == "brief.json" and isinstance(payload, dict):
                summary = str(payload.get("validation_goal") or payload.get("problem_statement") or summary)
                detail_lines = [
                    f"Project: {payload.get('project_name', '')}",
                    f"Target market: {payload.get('target_market', '')}",
                ]
            elif name == "panel.json" and isinstance(payload, dict):
                summary = f"Panel type {payload.get('panel_type', '')} with sample size {payload.get('sample_size', '')}."
                detail_lines = [
                    f"Random seed: {payload.get('random_seed', '')}",
                    f"Preset: {payload.get('preset_name', '') or 'none'}",
                ]
            elif name == "selected_personas.json" and isinstance(payload, list):
                summary = f"{len(payload)} selected persona record(s)."
                detail_lines = [
                    f"{item.get('name', 'persona')}: {item.get('occupation', '')}"
                    for item in payload[:3]
                    if isinstance(item, dict)
                ]
            elif name == "sampling.json" and isinstance(payload, dict):
                summary = str(payload.get("rationale") or "Sampling rationale for the selected panel.")
                explainability = payload.get("explainability")
                if isinstance(explainability, dict):
                    detail_lines = [
                        f"{key}: {value}"
                        for key, value in list(explainability.items())[:3]
                    ]
            elif name == "raw_responses.json" and isinstance(payload, list):
                summary = f"{len(payload)} persona response record(s) captured."
                detail_lines = []
                for item in payload[:3]:
                    if not isinstance(item, dict):
                        continue
                    response = item.get("response") if isinstance(item.get("response"), dict) else {}
                    detail_lines.append(
                        f"{item.get('synthetic_user_id', 'persona')}: objection {response.get('likely_objection', 'n/a')} | try signal {response.get('what_would_make_them_try', 'n/a')}"
                    )
                replay_steps = _build_raw_response_replay_steps(payload)
            elif name == "stage_results.json" and isinstance(payload, dict):
                summary = "Execution-stage status summary."
                detail_lines = [
                    f"{stage}: {stage_payload.get('status', 'unknown')}"
                    for stage, stage_payload in payload.items()
                    if isinstance(stage_payload, dict)
                ][:6]
                replay_steps = _build_stage_result_replay_steps(payload)
            elif name == "errors.json" and isinstance(payload, list):
                summary = f"{len(payload)} error record(s)."
                detail_lines = [
                    f"{item.get('stage_name', 'stage')}: {item.get('message', '')}"
                    for item in payload[:5]
                    if isinstance(item, dict)
                ]
                replay_steps = _build_error_replay_steps(payload)
            elif name == "audit.json" and isinstance(payload, list):
                summary = f"{len(payload)} audit finding(s)."
                detail_lines = [
                    f"{item.get('category', 'audit')}: {item.get('observation', '')}"
                    for item in payload[:5]
                    if isinstance(item, dict)
                ]
            elif name == "aggregation.json" and isinstance(payload, dict):
                summary, detail_lines = _summary_payload_summary(payload)
            elif name == "summary.json" and isinstance(payload, dict):
                summary, detail_lines = _summary_payload_summary(payload)
            elif name == "skeptic.json" and isinstance(payload, dict):
                summary = str(payload.get("summary") or "Skeptic review output.")
                detail_lines = [
                    f"{item.get('severity', 'unknown')}: {item.get('title', '')}"
                    for item in payload.get("challenged_assumptions", [])[:5]
                    if isinstance(item, dict)
                ]
            elif name == "planner.json" and isinstance(payload, list):
                summary = f"{len(payload)} planner step(s) generated."
                detail_lines = [str(item) for item in payload[:5]]
                replay_steps = _build_planner_replay_steps(payload)
            elif name == "report.json" and isinstance(payload, dict):
                summary, detail_lines = _report_summary(payload)
            elif name == "run.json" and isinstance(payload, dict):
                summary = f"Run manifest with status {payload.get('status', 'unknown')}."
                detail_lines = [
                    f"Panel type: {payload.get('panel_spec', {}).get('panel_type', '')}" if isinstance(payload.get("panel_spec"), dict) else "",
                    f"Selected personas: {len(payload.get('selected_persona_ids', []))}" if isinstance(payload.get("selected_persona_ids"), list) else "",
                ]
            elif name == "run_contract.json" and isinstance(payload, dict):
                request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
                result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
                summary = f"Shared run contract for {request.get('run_kind', 'run')} with status {result.get('status', 'unknown')}."
                detail_lines = [
                    f"Entrypoint: {request.get('entrypoint', '')}",
                    f"Primary artifact: {result.get('primary_artifact_path', '')}",
                ]
        elif artifact_path.suffix.lower() == ".md":
            lines = _read_markdown_lines(artifact_path)
            heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), "")
            summary = heading or f"{title} markdown artifact."
            detail_lines = [line for line in lines if not line.startswith("#")][:5]
    except Exception as exc:
        summary = f"{title} artifact could not be parsed cleanly."
        detail_lines = [str(exc)]

    detail_lines = [line for line in detail_lines if line][:5]
    replay_step_titles = [str(step.get("title", "")) for step in replay_steps if isinstance(step, dict)]
    return {
        "id": result_id,
        "artifact_id": artifact_id,
        "run_id": run_id,
        "title": title,
        "family": family,
        "kind": kind,
        "artifact_path": str(artifact_path),
        "artifact_rel_path": artifact_rel_path,
        "summary": summary,
        "tags": tags,
        "detail_lines": detail_lines,
        "replay_steps": replay_steps,
        "replay_step_titles": [value for value in replay_step_titles if value],
        "sort_timestamp": sort_timestamp,
        "artifact_type": artifact_type,
    }


def _build_evidence_catalog(index_root: Path, run_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with closing(_connect_metadata(index_root)) as connection:
        run_row = connection.execute(
            """
            SELECT
                run_id,
                run_kind,
                status,
                created_at,
                finished_at,
                output_path,
                primary_artifact_path,
                brief_id,
                research_goal,
                interview_mode,
                result_json
            FROM run_records
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if run_row is None:
            raise FileNotFoundError(f"Run '{run_id}' not found in metadata index.")

        run_record = {
            "run_id": str(run_row["run_id"]),
            "run_kind": str(run_row["run_kind"]),
            "status": str(run_row["status"]),
            "created_at": str(run_row["created_at"] or ""),
            "finished_at": str(run_row["finished_at"] or ""),
            "output_path": str(run_row["output_path"]),
            "primary_artifact_path": str(run_row["primary_artifact_path"]),
            "brief_id": str(run_row["brief_id"] or ""),
            "research_goal": str(run_row["research_goal"] or ""),
            "interview_mode": str(run_row["interview_mode"] or ""),
            "result_json": json.loads(str(run_row["result_json"])) if str(run_row["result_json"]) else {},
        }
        artifact_rows = connection.execute(
            """
            SELECT artifact_rel_path, artifact_path, artifact_type
            FROM artifact_records
            WHERE run_id = ?
            ORDER BY artifact_rel_path
            """,
            (run_id,),
        ).fetchall()

    artifacts: list[dict[str, Any]] = []
    total = len(artifact_rows)
    for index, row in enumerate(artifact_rows):
        artifact_path = Path(str(row["artifact_path"]))
        if not artifact_path.exists():
            continue
        artifacts.append(
            _build_artifact_entry(
                run_id=run_id,
                artifact_rel_path=str(row["artifact_rel_path"]),
                artifact_path=artifact_path,
                artifact_type=str(row["artifact_type"]),
                sort_timestamp=total - index,
            )
        )
    return run_record, artifacts


def _query_score(record: dict[str, Any], query_text: str) -> int:
    if not query_text:
        return 1
    haystacks = [
        record.get("title", ""),
        record.get("summary", ""),
        record.get("family", ""),
        record.get("kind", ""),
        record.get("artifact_path", ""),
        *record.get("tags", []),
        *record.get("replay_step_titles", []),
        *record.get("detail_lines", []),
    ]
    score = 0
    for value in haystacks:
        if query_text in str(value).lower():
            score += 1
    return score


def _sort_results(results: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    items = list(results)
    if sort_by == "family":
        items.sort(key=lambda item: f"{item['family']}:{item['title']}")
        return items
    if sort_by == "newest":
        items.sort(key=lambda item: int(item.get("sort_timestamp", 0)), reverse=True)
        return items
    items.sort(
        key=lambda item: (
            int(item.get("relevance_score", 0)),
            int(item.get("sort_timestamp", 0)),
        ),
        reverse=True,
    )
    return items


def _rank_visible_results(
    artifacts: list[dict[str, Any]],
    *,
    query_text: str,
    active_family: str,
    sort_by: str,
) -> list[dict[str, Any]]:
    results = artifacts
    if active_family != "all":
        results = [item for item in results if item["family"] == active_family]
    ranked: list[dict[str, Any]] = []
    for item in results:
        item_copy = dict(item)
        item_copy["relevance_score"] = _query_score(item_copy, query_text)
        ranked.append(item_copy)
    ranked = [item for item in ranked if query_text == "" or int(item["relevance_score"]) > 0]
    return _sort_results(ranked, sort_by)


def _replay_result_count(results: list[dict[str, Any]]) -> int:
    return sum(1 for item in results if item.get("replay_steps"))


def _facet_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "all": len(artifacts),
        "input": sum(1 for item in artifacts if item["family"] == "input"),
        "trace": sum(1 for item in artifacts if item["family"] == "trace"),
        "analysis": sum(1 for item in artifacts if item["family"] == "analysis"),
        "output": sum(1 for item in artifacts if item["family"] == "output"),
    }


def _project_query_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "artifact_id": item["artifact_id"],
        "title": item["title"],
        "family": item["family"],
        "kind": item["kind"],
        "artifact_path": item["artifact_path"],
        "summary": item["summary"],
        "tags": item["tags"],
        "replay_step_titles": item["replay_step_titles"],
        "relevance_score": item["relevance_score"],
    }


def _pick_selected_result(
    sorted_results: list[dict[str, Any]],
    selected_result_id: str | None,
) -> dict[str, Any] | None:
    selected = next((item for item in sorted_results if item["id"] == selected_result_id), None)
    if selected is not None:
        return selected
    replay_trace = next(
        (item for item in sorted_results if item.get("family") == "trace" and item.get("replay_steps")),
        None,
    )
    if replay_trace is not None:
        return replay_trace
    replay_bearing = next((item for item in sorted_results if item.get("replay_steps")), None)
    if replay_bearing is not None:
        return replay_bearing
    return sorted_results[0] if sorted_results else None


def _cross_run_signal_score(
    current_run_record: dict[str, Any],
    candidate_run_record: dict[str, Any],
    query_text: str,
) -> int:
    score = 0
    current_brief_id = str(current_run_record.get("brief_id") or "").strip()
    candidate_brief_id = str(candidate_run_record.get("brief_id") or "").strip()
    current_mode = str(current_run_record.get("interview_mode") or "").strip()
    candidate_mode = str(candidate_run_record.get("interview_mode") or "").strip()
    current_goal = _normalize_query_text(str(current_run_record.get("research_goal") or ""))
    candidate_goal = _normalize_query_text(str(candidate_run_record.get("research_goal") or ""))
    if current_brief_id and candidate_brief_id and current_brief_id == candidate_brief_id:
        score += 4
    if current_mode and candidate_mode and current_mode == candidate_mode:
        score += 3
    if current_goal and candidate_goal and current_goal == candidate_goal:
        score += 2
    if query_text and any(
        query_text in _normalize_query_text(str(candidate_run_record.get(field) or ""))
        for field in ("run_id", "brief_id", "research_goal", "interview_mode")
    ):
        score += 1
    return score


def _cross_run_relation_note(
    current_run_record: dict[str, Any],
    candidate_run_record: dict[str, Any],
    query_text: str,
) -> str:
    parts: list[str] = []
    current_brief_id = str(current_run_record.get("brief_id") or "").strip()
    candidate_brief_id = str(candidate_run_record.get("brief_id") or "").strip()
    current_mode = str(current_run_record.get("interview_mode") or "").strip()
    candidate_mode = str(candidate_run_record.get("interview_mode") or "").strip()
    current_goal = _normalize_query_text(str(current_run_record.get("research_goal") or ""))
    candidate_goal = _normalize_query_text(str(candidate_run_record.get("research_goal") or ""))
    if current_brief_id and candidate_brief_id and current_brief_id == candidate_brief_id:
        parts.append("same brief")
    if current_mode and candidate_mode and current_mode == candidate_mode:
        parts.append("same interview mode")
    if current_goal and candidate_goal and current_goal == candidate_goal:
        parts.append("same research goal")
    if query_text and any(
        query_text in _normalize_query_text(str(candidate_run_record.get(field) or ""))
        for field in ("run_id", "brief_id", "research_goal", "interview_mode")
    ):
        parts.append("query-aligned")
    if not parts:
        parts.append("same workspace evidence scope")
    return ", ".join(parts)


def _comparison_result_match_priority(
    candidate_result: dict[str, Any],
    selected_result: dict[str, Any] | None,
) -> tuple[int, int, int, int]:
    selected_kind = str(selected_result.get("kind") or "") if selected_result else ""
    selected_family = str(selected_result.get("family") or "") if selected_result else ""
    return (
        1 if selected_kind and str(candidate_result.get("kind") or "") == selected_kind else 0,
        1 if selected_family and str(candidate_result.get("family") or "") == selected_family else 0,
        1 if candidate_result.get("replay_steps") else 0,
        int(candidate_result.get("relevance_score", 0)),
    )


def _project_cross_run_candidate(
    candidate_run_record: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    *,
    current_run_record: dict[str, Any],
    query_text: str,
    active_family: str,
) -> dict[str, Any]:
    result_count = len(candidate_results)
    replay_result_count = _replay_result_count(candidate_results)
    return {
        "run_id": str(candidate_run_record.get("run_id") or ""),
        "run_kind": str(candidate_run_record.get("run_kind") or ""),
        "status": str(candidate_run_record.get("status") or ""),
        "finished_at": str(candidate_run_record.get("finished_at") or ""),
        "brief_id": str(candidate_run_record.get("brief_id") or ""),
        "research_goal": str(candidate_run_record.get("research_goal") or ""),
        "interview_mode": str(candidate_run_record.get("interview_mode") or ""),
        "shared_signal_count": _cross_run_signal_score(current_run_record, candidate_run_record, query_text),
        "relation_note": _cross_run_relation_note(current_run_record, candidate_run_record, query_text),
        "result_count": result_count,
        "replay_result_count": replay_result_count,
        "selected_family_result_count": (
            result_count
            if active_family == "all"
            else sum(1 for item in candidate_results if item.get("family") == active_family)
        ),
        "top_result_id": candidate_results[0]["id"] if candidate_results else None,
        "top_result_title": candidate_results[0]["title"] if candidate_results else None,
    }


def _pick_cross_run_selected_candidate(
    projected_candidates: list[dict[str, Any]],
    selected_comparison_run_id: str | None,
) -> dict[str, Any] | None:
    if selected_comparison_run_id:
        selected = next(
            (
                item
                for item in projected_candidates
                if str(item.get("run_id") or "") == str(selected_comparison_run_id)
            ),
            None,
        )
        if selected is not None:
            return selected
    return projected_candidates[0] if projected_candidates else None


def _build_cross_run_selected_projection(
    projected_candidate: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    selected_result: dict[str, Any] | None,
) -> dict[str, Any]:
    selected_family = str(selected_result.get("family") or "") if selected_result else ""
    selected_kind = str(selected_result.get("kind") or "") if selected_result else ""
    ranked_results = sorted(
        candidate_results,
        key=lambda item: (
            *_comparison_result_match_priority(item, selected_result),
            int(item.get("sort_timestamp", 0)),
        ),
        reverse=True,
    )
    recommended_result = ranked_results[0] if ranked_results else None
    shared_family_result_count = sum(
        1 for item in candidate_results if selected_family and str(item.get("family") or "") == selected_family
    )
    shared_kind_result_count = sum(
        1 for item in candidate_results if selected_kind and str(item.get("kind") or "") == selected_kind
    )
    shared_replay_result_count = sum(
        1
        for item in candidate_results
        if selected_family
        and str(item.get("family") or "") == selected_family
        and item.get("replay_steps")
    )
    comparison_results = [_project_query_result(item) for item in ranked_results[:3]]
    if shared_kind_result_count:
        note = "Compare same-kind artifacts across runs to check whether the same signal repeats under the same evidence surface."
        recommended_reason = "A same-kind artifact is the closest cross-run comparison for the current evidence focus."
    elif shared_family_result_count:
        note = "Compare same-family artifacts across runs to see whether the same hesitation or objection repeats nearby."
        recommended_reason = "A same-family artifact preserves the current evidence layer even when the exact artifact kind differs."
    elif comparison_results:
        note = "No same-family match is available. Compare the nearest replay-bearing artifact to preserve execution context."
        recommended_reason = "The best available comparison is the highest-signal artifact in the comparison run."
    else:
        note = "No visible evidence remains in the comparison run under the current query scope."
        recommended_reason = None
    return {
        **projected_candidate,
        "recommended_result_id": recommended_result["id"] if recommended_result else None,
        "recommended_result_title": recommended_result["title"] if recommended_result else None,
        "recommended_result_reason": recommended_reason,
        "shared_family_result_count": shared_family_result_count,
        "shared_kind_result_count": shared_kind_result_count,
        "shared_replay_result_count": shared_replay_result_count,
        "comparison_results": comparison_results,
        "note": note,
    }


def _build_cross_run_comparison(
    index_root: Path,
    *,
    current_run_record: dict[str, Any],
    query_text: str,
    active_family: str,
    sort_by: str,
    selected_result: dict[str, Any] | None,
    selected_comparison_run_id: str | None = None,
) -> dict[str, Any]:
    with closing(_connect_metadata(index_root)) as connection:
        candidate_rows = connection.execute(
            """
            SELECT
                run_id,
                run_kind,
                status,
                created_at,
                finished_at,
                brief_id,
                research_goal,
                interview_mode,
                output_path,
                primary_artifact_path,
                result_json
            FROM run_records
            WHERE run_id <> ? AND status = 'completed' AND run_kind = ?
            ORDER BY finished_at DESC, created_at DESC, run_id DESC
            """,
            (str(current_run_record.get("run_id") or ""), str(current_run_record.get("run_kind") or "")),
        ).fetchall()

    candidates: list[dict[str, Any]] = []
    for row in candidate_rows:
        candidate_run_record = {
            "run_id": str(row["run_id"]),
            "run_kind": str(row["run_kind"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"] or ""),
            "finished_at": str(row["finished_at"] or ""),
            "brief_id": str(row["brief_id"] or ""),
            "research_goal": str(row["research_goal"] or ""),
            "interview_mode": str(row["interview_mode"] or ""),
            "output_path": str(row["output_path"] or ""),
            "primary_artifact_path": str(row["primary_artifact_path"] or ""),
            "result_json": json.loads(str(row["result_json"])) if str(row["result_json"]) else {},
        }
        try:
            _, candidate_artifacts = _build_evidence_catalog(index_root, candidate_run_record["run_id"])
        except FileNotFoundError:
            continue
        candidate_results = _rank_visible_results(
            candidate_artifacts,
            query_text=query_text,
            active_family=active_family,
            sort_by=sort_by,
        )
        if not candidate_results:
            continue
        projected_candidate = _project_cross_run_candidate(
            candidate_run_record,
            candidate_results,
            current_run_record=current_run_record,
            query_text=query_text,
            active_family=active_family,
        )
        candidates.append(
            {
                "projection": projected_candidate,
                "results": candidate_results,
            }
        )

    candidates.sort(
        key=lambda item: (
            int(item["projection"].get("shared_signal_count", 0)),
            1 if item["projection"].get("replay_result_count") else 0,
            str(item["projection"].get("finished_at") or ""),
            str(item["projection"].get("run_id") or ""),
        ),
        reverse=True,
    )
    candidates = candidates[:CROSS_RUN_MAX_CANDIDATES]
    projected_candidates = [item["projection"] for item in candidates]
    selected_candidate = _pick_cross_run_selected_candidate(projected_candidates, selected_comparison_run_id)
    candidate_lookup = {
        str(item["projection"].get("run_id") or ""): item for item in candidates
    }
    selected_projection = None
    if selected_candidate is not None:
        selected_lookup = candidate_lookup.get(str(selected_candidate.get("run_id") or ""))
        if selected_lookup is not None:
            selected_projection = _build_cross_run_selected_projection(
                selected_candidate,
                selected_lookup["results"],
                selected_result,
            )
    candidate_count = len(projected_candidates)
    if candidate_count == 0:
        note = "No comparable completed runs are available in the current workspace scope."
    elif candidate_count == 1:
        note = "1 comparable completed run is available for cross-run review."
    else:
        note = f"{candidate_count} comparable completed runs are available for cross-run review."
    return {
        "comparison_run_count": candidate_count,
        "candidate_runs": projected_candidates,
        "selected_comparison_run_id": selected_projection["run_id"] if selected_projection else None,
        "selected_comparison_run": selected_projection,
        "note": note,
    }


def _evidence_text(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    values = [
        item.get("title", ""),
        item.get("summary", ""),
        item.get("family", ""),
        item.get("kind", ""),
        item.get("artifact_path", ""),
        *item.get("tags", []),
        *item.get("replay_step_titles", []),
        *item.get("detail_lines", []),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _evidence_signal_id(item: dict[str, Any] | None) -> str | None:
    if not isinstance(item, dict):
        return None
    family = str(item.get("family") or "").strip()
    kind = str(item.get("kind") or "").strip()
    if not family and not kind:
        return None
    return f"{family}:{kind}"


def _extract_signal_terms(item: dict[str, Any] | None) -> list[str]:
    text = _evidence_text(item)
    terms = []
    for term in [
        "objection",
        "trust",
        "risk",
        "hesitat",
        "reject",
        "pricing",
        "fallback",
        "error",
        "failed",
        "try signal",
        "adoption",
        "human validation",
    ]:
        if term in text:
            terms.append(term)
    return terms


def _has_contradiction_signal(item: dict[str, Any] | None) -> bool:
    text = _evidence_text(item)
    return any(
        marker in text
        for marker in [
            "contradict",
            "unsupported",
            "reject",
            "risk",
            "error",
            "failed",
            "trust concern",
            "skeptic",
            "needs revision",
        ]
    )


def _support_card(
    *,
    source: str,
    item: dict[str, Any],
    relation: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "id": str(item.get("id") or item.get("run_id") or ""),
        "run_id": str(item.get("run_id") or ""),
        "artifact_id": str(item.get("artifact_id") or ""),
        "title": str(item.get("title") or item.get("top_result_title") or item.get("run_id") or "Evidence"),
        "family": str(item.get("family") or ""),
        "kind": str(item.get("kind") or ""),
        "relation": relation,
        "summary": str(item.get("summary") or item.get("relation_note") or ""),
    }


def _build_supporting_evidence(
    *,
    selected_result: dict[str, Any] | None,
    comparison_context: dict[str, Any],
    cross_run_comparison: dict[str, Any],
) -> list[dict[str, Any]]:
    if selected_result is None:
        return []
    supporting: list[dict[str, Any]] = []
    selected_signal = _evidence_signal_id(selected_result)
    for candidate in comparison_context.get("comparison_candidates", [])[:3]:
        if not isinstance(candidate, dict):
            continue
        candidate_signal = _evidence_signal_id(candidate)
        if candidate_signal and candidate_signal == selected_signal:
            supporting.append(
                _support_card(
                    source="same_run",
                    item=candidate,
                    relation=str(candidate.get("relation_note") or "same-run comparable evidence"),
                )
            )
    selected_run = cross_run_comparison.get("selected_comparison_run")
    if isinstance(selected_run, dict):
        for result in selected_run.get("comparison_results", [])[:3]:
            if not isinstance(result, dict):
                continue
            result_signal = _evidence_signal_id(result)
            if result_signal and result_signal == selected_signal:
                supporting.append(
                    _support_card(
                        source="cross_run",
                        item={**result, "run_id": selected_run.get("run_id")},
                        relation=str(selected_run.get("recommended_result_reason") or selected_run.get("relation_note") or "cross-run comparable evidence"),
                    )
                )
    return supporting[:5]


def _build_contradicting_evidence(
    *,
    comparison_context: dict[str, Any],
    cross_run_comparison: dict[str, Any],
) -> list[dict[str, Any]]:
    contradicting: list[dict[str, Any]] = []
    for candidate in comparison_context.get("comparison_candidates", [])[:3]:
        if isinstance(candidate, dict) and _has_contradiction_signal(candidate):
            contradicting.append(
                _support_card(
                    source="same_run",
                    item=candidate,
                    relation=str(candidate.get("relation_note") or "risk-bearing nearby evidence"),
                )
            )
    selected_run = cross_run_comparison.get("selected_comparison_run")
    if isinstance(selected_run, dict):
        for result in selected_run.get("comparison_results", [])[:3]:
            if isinstance(result, dict) and _has_contradiction_signal(result):
                contradicting.append(
                    _support_card(
                        source="cross_run",
                        item={**result, "run_id": selected_run.get("run_id")},
                        relation="cross-run risk or contradiction signal",
                    )
                )
    return contradicting[:5]


def _build_missing_context(
    *,
    selected_result: dict[str, Any] | None,
    replay_sequence: list[dict[str, Any]],
    cross_run_comparison: dict[str, Any],
    supporting_evidence: list[dict[str, Any]],
    human_calibration: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    if human_calibration:
        readiness = human_calibration.get("replacement_readiness", {})
        status = readiness.get("status") if isinstance(readiness, dict) else "unknown"
        if status not in {"candidate_replacement_ready", "directional_calibration_ready", "calibrated_fixture_only"}:
            missing.append(
                {
                    "id": "human_calibration_threshold_gap",
                    "label": "human calibration threshold gap",
                    "severity": "high",
                    "note": "Attached human outcome calibration does not meet the configured readiness threshold.",
                }
            )
    else:
        missing.append(
            {
                "id": "human_validation_gap",
                "label": "human validation gap",
                "severity": "high",
                "note": "Synthetic evidence has not been calibrated against human outcome data for this claim.",
            }
        )
    if selected_result is None:
        missing.append(
            {
                "id": "selected_evidence_missing",
                "label": "selected evidence missing",
                "severity": "medium",
                "note": "No selected result is available for reliability review.",
            }
        )
    if not replay_sequence:
        missing.append(
            {
                "id": "replay_missing",
                "label": "replay missing",
                "severity": "medium",
                "note": "The selected evidence has no replay-linked step, so audit depth is limited.",
            }
        )
    if int(cross_run_comparison.get("comparison_run_count") or 0) == 0:
        missing.append(
            {
                "id": "comparison_run_missing",
                "label": "comparison run missing",
                "severity": "high",
                "note": "No comparable completed run is available for repeatability review.",
            }
        )
    if not supporting_evidence:
        missing.append(
            {
                "id": "supporting_context_missing",
                "label": "supporting context missing",
                "severity": "medium",
                "note": "No same-kind supporting artifact is available under the current query scope.",
            }
        )
    return missing


def _stability_label(
    *,
    cross_run_comparison: dict[str, Any],
    supporting_evidence: list[dict[str, Any]],
    contradicting_evidence: list[dict[str, Any]],
) -> str:
    if contradicting_evidence:
        return "mixed_or_contradictory"
    if any(item.get("source") == "cross_run" for item in supporting_evidence):
        return "repeated_signal"
    if int(cross_run_comparison.get("comparison_run_count") or 0) > 0:
        return "comparison_available"
    return "single_run_signal"


def _stability_score(
    *,
    label: str,
    replay_sequence: list[dict[str, Any]],
    supporting_evidence: list[dict[str, Any]],
    contradicting_evidence: list[dict[str, Any]],
    missing_context: list[dict[str, Any]],
) -> int:
    score = 20
    if replay_sequence:
        score += 15
    score += min(30, len(supporting_evidence) * 12)
    if label == "repeated_signal":
        score += 20
    elif label == "comparison_available":
        score += 10
    if contradicting_evidence:
        score -= min(25, len(contradicting_evidence) * 10)
    score -= min(20, len([item for item in missing_context if item.get("severity") == "high"]) * 10)
    return max(0, min(100, score))


def _build_calibration_records(
    *,
    stability_label: str,
    stability_score: int,
    supporting_evidence: list[dict[str, Any]],
    contradicting_evidence: list[dict[str, Any]],
    missing_context: list[dict[str, Any]],
    human_calibration: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    records = [
        {
            "id": "synthetic_boundary",
            "status": "requires_human_validation",
            "label": "Synthetic evidence boundary",
            "note": "This reliability review improves repeatability discipline but remains synthetic evidence, not human market proof.",
        },
        {
            "id": "repeatability",
            "status": stability_label,
            "label": "Repeatability signal",
            "score": stability_score,
            "supporting_count": len(supporting_evidence),
            "contradicting_count": len(contradicting_evidence),
        },
        {
            "id": "coverage_gap",
            "status": "open" if missing_context else "covered",
            "label": "Coverage and calibration gaps",
            "missing_count": len(missing_context),
            "note": "Missing context must stay visible before using this evidence for stronger prediction claims.",
        },
    ]
    if human_calibration:
        accuracy = human_calibration.get("prediction_accuracy", {})
        readiness = human_calibration.get("replacement_readiness", {})
        benchmark = human_calibration.get("human_benchmark", {})
        records.append(
            {
                "id": "human_benchmark_alignment",
                "status": readiness.get("status", "unknown") if isinstance(readiness, dict) else "unknown",
                "label": "Human benchmark alignment",
                "benchmark_id": human_calibration.get("benchmark_id"),
                "source_type": benchmark.get("source_type") if isinstance(benchmark, dict) else None,
                "alignment_score": accuracy.get("alignment_score") if isinstance(accuracy, dict) else None,
                "precision": accuracy.get("precision") if isinstance(accuracy, dict) else None,
                "recall": accuracy.get("recall") if isinstance(accuracy, dict) else None,
                "note": readiness.get("boundary") if isinstance(readiness, dict) else "",
            }
        )
    return records


def _load_human_calibration_record(run_record: dict[str, Any]) -> dict[str, Any] | None:
    candidate_paths = []
    for key in ("output_path", "primary_artifact_path"):
        raw = str(run_record.get(key) or "").strip()
        if not raw:
            continue
        path = Path(raw)
        candidate_paths.append(path / "human_calibration.json" if path.is_dir() else path.parent / "human_calibration.json")
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("contract_version") == "human-calibration/v1":
            return payload
    return None


def _build_audit_lineage(
    *,
    run_record: dict[str, Any],
    selected_result: dict[str, Any] | None,
    replay_focus: dict[str, Any] | None,
    cross_run_comparison: dict[str, Any],
) -> dict[str, Any]:
    selected_run = cross_run_comparison.get("selected_comparison_run")
    return {
        "contract_version": "workspace-evidence-audit-lineage/v0-draft",
        "source_run": {
            "run_id": str(run_record.get("run_id") or ""),
            "run_kind": str(run_record.get("run_kind") or ""),
            "brief_id": str(run_record.get("brief_id") or ""),
            "research_goal": str(run_record.get("research_goal") or ""),
            "interview_mode": str(run_record.get("interview_mode") or ""),
            "finished_at": str(run_record.get("finished_at") or ""),
            "output_path": str(run_record.get("output_path") or ""),
            "primary_artifact_path": str(run_record.get("primary_artifact_path") or ""),
        },
        "selected_evidence": {
            "result_id": str(selected_result.get("id") or "") if selected_result else None,
            "artifact_id": str(selected_result.get("artifact_id") or "") if selected_result else None,
            "family": str(selected_result.get("family") or "") if selected_result else None,
            "kind": str(selected_result.get("kind") or "") if selected_result else None,
            "artifact_path": str(selected_result.get("artifact_path") or "") if selected_result else None,
            "artifact_rel_path": str(selected_result.get("artifact_rel_path") or "") if selected_result else None,
            "signal_id": _evidence_signal_id(selected_result),
            "signal_terms": _extract_signal_terms(selected_result),
        },
        "replay": {
            "selected_replay_step_id": str(replay_focus.get("id") or "") if isinstance(replay_focus, dict) else None,
            "selected_replay_step_title": str(replay_focus.get("title") or "") if isinstance(replay_focus, dict) else None,
            "selected_replay_step_timestamp": str(replay_focus.get("timestamp") or "") if isinstance(replay_focus, dict) else None,
        },
        "comparison_set": {
            "comparison_run_count": int(cross_run_comparison.get("comparison_run_count") or 0),
            "candidate_run_ids": [
                str(item.get("run_id") or "")
                for item in cross_run_comparison.get("candidate_runs", [])
                if isinstance(item, dict) and item.get("run_id")
            ],
            "selected_comparison_run_id": (
                str(selected_run.get("run_id") or "") if isinstance(selected_run, dict) else None
            ),
            "selected_comparison_result_id": (
                str(selected_run.get("recommended_result_id") or "") if isinstance(selected_run, dict) else None
            ),
        },
    }


def _build_evidence_reliability(
    *,
    run_record: dict[str, Any],
    selected_result: dict[str, Any] | None,
    replay_sequence: list[dict[str, Any]],
    replay_focus: dict[str, Any] | None,
    comparison_context: dict[str, Any],
    cross_run_comparison: dict[str, Any],
) -> dict[str, Any]:
    supporting_evidence = _build_supporting_evidence(
        selected_result=selected_result,
        comparison_context=comparison_context,
        cross_run_comparison=cross_run_comparison,
    )
    contradicting_evidence = _build_contradicting_evidence(
        comparison_context=comparison_context,
        cross_run_comparison=cross_run_comparison,
    )
    human_calibration = _load_human_calibration_record(run_record)
    missing_context = _build_missing_context(
        selected_result=selected_result,
        replay_sequence=replay_sequence,
        cross_run_comparison=cross_run_comparison,
        supporting_evidence=supporting_evidence,
        human_calibration=human_calibration,
    )
    stability_label = _stability_label(
        cross_run_comparison=cross_run_comparison,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
    )
    stability_score = _stability_score(
        label=stability_label,
        replay_sequence=replay_sequence,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        missing_context=missing_context,
    )
    audit_lineage = _build_audit_lineage(
        run_record=run_record,
        selected_result=selected_result,
        replay_focus=replay_focus,
        cross_run_comparison=cross_run_comparison,
    )
    return {
        "contract_version": "workspace-evidence-reliability/v0-draft",
        "review_status": "reliability_ready" if selected_result else "reliability_pending",
        "stability_label": stability_label,
        "stability_score": stability_score,
        "selected_signal_id": _evidence_signal_id(selected_result),
        "signal_terms": _extract_signal_terms(selected_result),
        "supporting_evidence": supporting_evidence,
        "contradicting_evidence": contradicting_evidence,
        "missing_context": missing_context,
        "calibration_records": _build_calibration_records(
            stability_label=stability_label,
            stability_score=stability_score,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
            missing_context=missing_context,
            human_calibration=human_calibration,
        ),
        "audit_lineage": audit_lineage,
        "human_calibration": human_calibration,
        "synthetic_boundary": "Synthetic evidence only. Reliability labels require human calibration before replacement-grade claims.",
    }


def _pending_audit_lineage(run_id: str | None) -> dict[str, Any]:
    return {
        "contract_version": "workspace-evidence-audit-lineage/v0-draft",
        "source_run": {
            "run_id": run_id,
            "run_kind": None,
            "brief_id": "",
            "research_goal": "",
            "interview_mode": "",
            "finished_at": "",
            "output_path": "",
            "primary_artifact_path": "",
        },
        "selected_evidence": {
            "result_id": None,
            "artifact_id": None,
            "family": None,
            "kind": None,
            "artifact_path": None,
            "artifact_rel_path": None,
            "signal_id": None,
            "signal_terms": [],
        },
        "replay": {
            "selected_replay_step_id": None,
            "selected_replay_step_title": None,
            "selected_replay_step_timestamp": None,
        },
        "comparison_set": {
            "comparison_run_count": 0,
            "candidate_run_ids": [],
            "selected_comparison_run_id": None,
            "selected_comparison_result_id": None,
        },
    }


def _pending_evidence_reliability(run_id: str | None) -> dict[str, Any]:
    audit_lineage = _pending_audit_lineage(run_id)
    return {
        "contract_version": "workspace-evidence-reliability/v0-draft",
        "review_status": "reliability_pending",
        "stability_label": "pending",
        "stability_score": 0,
        "selected_signal_id": None,
        "signal_terms": [],
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "missing_context": [
            {
                "id": "completed_run_missing",
                "label": "completed run missing",
                "severity": "high",
                "note": "Evidence reliability remains pending until a completed run is ready.",
            },
            {
                "id": "human_validation_gap",
                "label": "human validation gap",
                "severity": "high",
                "note": "Synthetic evidence has not been calibrated against human outcome data for this claim.",
            },
        ],
        "calibration_records": [
            {
                "id": "synthetic_boundary",
                "status": "requires_human_validation",
                "label": "Synthetic evidence boundary",
                "note": "No reliability claim is available before a completed run is reviewed.",
            }
        ],
        "audit_lineage": audit_lineage,
        "human_calibration": None,
        "synthetic_boundary": "Synthetic evidence only. Reliability labels require completed evidence and human calibration before replacement-grade claims.",
    }


def _boundary_warning(run_kind: str, status: str) -> str:
    if status != "completed":
        return "Evidence query remains pending until the run is completed."
    if run_kind == "validation_run":
        return "The run artifacts are ready for operator review, but the evidence remains synthetic and bounded by the current validation contract."
    if run_kind in {"facilitated_interview", "observer_controlled_interview"}:
        return "The interview artifacts are queryable, but the evidence remains synthetic and bounded by the current interview contract."
    return "The run artifacts are queryable, but the evidence remains synthetic and bounded by the current platform contract."


def _comparison_relation_note(candidate: dict[str, Any], selected_result: dict[str, Any]) -> str:
    if candidate.get("family") == selected_result.get("family") and candidate.get("replay_steps"):
        return "same family with replay context"
    if candidate.get("family") == selected_result.get("family"):
        return "same family as selected evidence"
    if candidate.get("replay_steps"):
        return "neighboring replay-bearing evidence"
    return "neighboring evidence surface"


def _build_comparison_context(
    sorted_results: list[dict[str, Any]],
    selected_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if selected_result is None:
        return {
            "selected_family_result_count": 0,
            "selected_family_replay_result_count": 0,
            "comparison_candidates": [],
            "recommended_comparison_id": None,
            "recommended_comparison_reason": None,
            "note": "Select evidence to unlock nearby comparison guidance.",
        }

    sibling_results = [
        item for item in sorted_results if item.get("id") and item["id"] != selected_result["id"]
    ]
    selected_family = str(selected_result.get("family") or "")
    selected_has_replay = bool(selected_result.get("replay_steps"))
    selected_family_result_count = sum(
        1 for item in sorted_results if str(item.get("family") or "") == selected_family
    )
    selected_family_replay_result_count = sum(
        1
        for item in sorted_results
        if str(item.get("family") or "") == selected_family and item.get("replay_steps")
    )
    ranked_candidates = sorted(
        sibling_results,
        key=lambda item: (
            1 if item.get("replay_steps") else 0,
            1 if item.get("family") == selected_family else 0,
            int(item.get("relevance_score", 0)),
            int(item.get("sort_timestamp", 0)),
        ),
        reverse=True,
    )[:3]
    if selected_has_replay:
        ranked_candidates = sorted(
            sibling_results,
            key=lambda item: (
                1 if item.get("family") == selected_family else 0,
                1 if item.get("replay_steps") else 0,
                int(item.get("relevance_score", 0)),
                int(item.get("sort_timestamp", 0)),
            ),
            reverse=True,
        )[:3]
    comparison_candidates = []
    for item in ranked_candidates:
        projection = _project_query_result(item)
        projection["relation_note"] = _comparison_relation_note(item, selected_result)
        projection["has_replay"] = bool(item.get("replay_steps"))
        comparison_candidates.append(projection)

    recommended = comparison_candidates[0] if comparison_candidates else None
    if not comparison_candidates:
        note = "No additional evidence is available for side-by-side comparison."
        recommended_reason = None
    elif not selected_has_replay and any(item.get("has_replay") for item in comparison_candidates):
        note = "Selected evidence has no direct replay steps. Compare with replay-bearing artifacts for execution context."
        recommended_reason = "Selected evidence lacks replay; a replay-bearing neighbor is the fastest way to inspect concrete execution context."
    elif selected_family_result_count > 1:
        note = "Use same-family evidence to check whether the same signal repeats across nearby artifacts."
        recommended_reason = "A same-family artifact provides the tightest comparison for repeated signals."
    else:
        note = "Use nearby evidence to compare whether the same hesitation shows up in other artifacts."
        recommended_reason = "Nearby artifacts provide the best available comparison surface for the current selection."

    return {
        "selected_family_result_count": selected_family_result_count,
        "selected_family_replay_result_count": selected_family_replay_result_count,
        "comparison_candidates": comparison_candidates,
        "recommended_comparison_id": recommended["id"] if recommended else None,
        "recommended_comparison_reason": recommended_reason,
        "note": note,
    }


def _build_replay_context(
    sorted_results: list[dict[str, Any]],
    selected_result: dict[str, Any] | None,
    replay_sequence: list[dict[str, Any]],
) -> dict[str, Any]:
    replay_result_count = sum(1 for item in sorted_results if item.get("replay_steps"))
    selected_family = str(selected_result.get("family") or "") if selected_result else ""
    selected_family_replay_result_count = sum(
        1
        for item in sorted_results
        if str(item.get("family") or "") == selected_family and item.get("replay_steps")
    )
    selected_has_replay = bool(replay_sequence)
    if selected_has_replay:
        note = f"{len(replay_sequence)} replay step(s) are linked to the selected evidence."
    elif replay_result_count:
        note = f"Selected evidence has no replay steps. {replay_result_count} other visible result(s) carry replay context."
    else:
        note = "No replay-linked steps are available for the current result set."
    return {
        "selected_result_has_replay": selected_has_replay,
        "replay_result_count": replay_result_count,
        "selected_family_replay_result_count": selected_family_replay_result_count,
        "note": note,
    }


def build_pending_evidence_query(
    *,
    run_id: str | None,
    query_text: str = "",
    active_family: str = "all",
    sort_by: str = "relevance",
    boundary_warning: str = "Evidence query remains pending until the run is completed.",
) -> dict[str, Any]:
    evidence_reliability = _pending_evidence_reliability(run_id)
    return {
        "run_id": run_id,
        "query_status": "query_pending",
        "query_text": _normalize_query_text(query_text),
        "active_family": _normalize_family(active_family),
        "sort_by": _normalize_sort(sort_by),
        "facet_counts": {"all": 0, "input": 0, "trace": 0, "analysis": 0, "output": 0},
        "result_count": 0,
        "selected_result_id": None,
        "selected_artifact_id": None,
        "selected_replay_step_id": None,
        "results": [],
        "selected_result": None,
        "linked_artifact": None,
        "replay_sequence": [],
        "replay_focus_step": None,
        "replay_context": {
            "selected_result_has_replay": False,
            "replay_result_count": 0,
            "selected_family_replay_result_count": 0,
            "note": "No replay-linked steps are available until a completed run is ready."
        },
        "comparison_context": {
            "selected_family_result_count": 0,
            "selected_family_replay_result_count": 0,
            "comparison_candidates": [],
            "recommended_comparison_id": None,
            "recommended_comparison_reason": None,
            "note": "Comparison guidance remains unavailable until a completed run is ready."
        },
        "cross_run_comparison": {
            "comparison_run_count": 0,
            "candidate_runs": [],
            "selected_comparison_run_id": None,
            "selected_comparison_run": None,
            "note": "Cross-run comparison remains unavailable until a completed run is ready.",
        },
        "evidence_reliability": evidence_reliability,
        "audit_lineage": evidence_reliability["audit_lineage"],
        "boundary_warning": boundary_warning,
    }


def query_run_evidence(
    index_root: Path,
    *,
    run_id: str,
    query_text: str = "",
    active_family: str = "all",
    sort_by: str = "relevance",
    selected_result_id: str | None = None,
    selected_replay_step_id: str | None = None,
    selected_comparison_run_id: str | None = None,
) -> dict[str, Any]:
    query_text = _normalize_query_text(query_text)
    active_family = _normalize_family(active_family)
    sort_by = _normalize_sort(sort_by)

    run_record, artifacts = _build_evidence_catalog(index_root, run_id)
    if run_record["status"] != "completed":
        return build_pending_evidence_query(
            run_id=run_id,
            query_text=query_text,
            active_family=active_family,
            sort_by=sort_by,
            boundary_warning=_boundary_warning(str(run_record["run_kind"]), str(run_record["status"])),
        )

    sorted_results = _rank_visible_results(
        artifacts,
        query_text=query_text,
        active_family=active_family,
        sort_by=sort_by,
    )
    selected_result = _pick_selected_result(sorted_results, selected_result_id)
    replay_sequence = selected_result.get("replay_steps", []) if selected_result else []
    replay_focus = next((step for step in replay_sequence if str(step.get("id", "")) == str(selected_replay_step_id or "")), None)
    if replay_focus is None and replay_sequence:
        replay_focus = replay_sequence[0]
    replay_context = _build_replay_context(sorted_results, selected_result, replay_sequence)
    comparison_context = _build_comparison_context(sorted_results, selected_result)
    cross_run_comparison = _build_cross_run_comparison(
        index_root,
        current_run_record=run_record,
        query_text=query_text,
        active_family=active_family,
        sort_by=sort_by,
        selected_result=selected_result,
        selected_comparison_run_id=selected_comparison_run_id,
    )
    evidence_reliability = _build_evidence_reliability(
        run_record=run_record,
        selected_result=selected_result,
        replay_sequence=replay_sequence,
        replay_focus=replay_focus,
        comparison_context=comparison_context,
        cross_run_comparison=cross_run_comparison,
    )

    return {
        "run_id": run_id,
        "run_kind": run_record["run_kind"],
        "query_status": "query_ready",
        "query_text": query_text,
        "active_family": active_family,
        "sort_by": sort_by,
        "facet_counts": _facet_counts(artifacts),
        "result_count": len(sorted_results),
        "selected_result_id": selected_result["id"] if selected_result else None,
        "selected_artifact_id": selected_result["artifact_id"] if selected_result else None,
        "selected_replay_step_id": replay_focus.get("id") if isinstance(replay_focus, dict) else None,
        "results": [_project_query_result(item) for item in sorted_results],
        "selected_result": selected_result,
        "linked_artifact": selected_result,
        "replay_sequence": replay_sequence,
        "replay_focus_step": replay_focus,
        "replay_context": replay_context,
        "comparison_context": comparison_context,
        "cross_run_comparison": cross_run_comparison,
        "evidence_reliability": evidence_reliability,
        "audit_lineage": evidence_reliability["audit_lineage"],
        "boundary_warning": _boundary_warning(str(run_record["run_kind"]), str(run_record["status"])),
    }
