from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_validation_swarm.saas.metadata_store import metadata_db_path


ALLOWED_FAMILIES = {"all", "input", "trace", "analysis", "output"}
ALLOWED_SORTS = {"relevance", "newest", "family"}


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
            elif name == "stage_results.json" and isinstance(payload, dict):
                summary = "Execution-stage status summary."
                detail_lines = [
                    f"{stage}: {stage_payload.get('status', 'unknown')}"
                    for stage, stage_payload in payload.items()
                    if isinstance(stage_payload, dict)
                ][:6]
            elif name == "errors.json" and isinstance(payload, list):
                summary = f"{len(payload)} error record(s)."
                detail_lines = [
                    f"{item.get('stage_name', 'stage')}: {item.get('message', '')}"
                    for item in payload[:5]
                    if isinstance(item, dict)
                ]
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
            SELECT run_id, run_kind, status, finished_at, output_path, primary_artifact_path, result_json
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
            "finished_at": str(run_row["finished_at"] or ""),
            "output_path": str(run_row["output_path"]),
            "primary_artifact_path": str(run_row["primary_artifact_path"]),
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


def _facet_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "all": len(artifacts),
        "input": sum(1 for item in artifacts if item["family"] == "input"),
        "trace": sum(1 for item in artifacts if item["family"] == "trace"),
        "analysis": sum(1 for item in artifacts if item["family"] == "analysis"),
        "output": sum(1 for item in artifacts if item["family"] == "output"),
    }


def _boundary_warning(run_kind: str, status: str) -> str:
    if status != "completed":
        return "Evidence query remains pending until the run is completed."
    if run_kind == "validation_run":
        return "The run artifacts are ready for operator review, but the evidence remains synthetic and bounded by the current validation contract."
    if run_kind in {"facilitated_interview", "observer_controlled_interview"}:
        return "The interview artifacts are queryable, but the evidence remains synthetic and bounded by the current interview contract."
    return "The run artifacts are queryable, but the evidence remains synthetic and bounded by the current platform contract."


def build_pending_evidence_query(
    *,
    run_id: str | None,
    query_text: str = "",
    active_family: str = "all",
    sort_by: str = "relevance",
    boundary_warning: str = "Evidence query remains pending until the run is completed.",
) -> dict[str, Any]:
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

    results = artifacts
    if active_family != "all":
        results = [item for item in results if item["family"] == active_family]
    ranked = []
    for item in results:
        item_copy = dict(item)
        item_copy["relevance_score"] = _query_score(item_copy, query_text)
        ranked.append(item_copy)
    ranked = [item for item in ranked if query_text == "" or int(item["relevance_score"]) > 0]
    sorted_results = _sort_results(ranked, sort_by)
    selected_result = next((item for item in sorted_results if item["id"] == selected_result_id), None)
    if selected_result is None and sorted_results:
        selected_result = sorted_results[0]
    replay_sequence = selected_result.get("replay_steps", []) if selected_result else []
    replay_focus = next((step for step in replay_sequence if str(step.get("id", "")) == str(selected_replay_step_id or "")), None)
    if replay_focus is None and replay_sequence:
        replay_focus = replay_sequence[0]

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
        "results": [
            {
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
            for item in sorted_results
        ],
        "selected_result": selected_result,
        "linked_artifact": selected_result,
        "replay_sequence": replay_sequence,
        "replay_focus_step": replay_focus,
        "boundary_warning": _boundary_warning(str(run_record["run_kind"]), str(run_record["status"])),
    }
