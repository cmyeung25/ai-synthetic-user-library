from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.reporting.markdown import DISCLAIMER
from ai_validation_swarm.storage.files import ensure_dir, export_file, read_json, write_json
from ai_validation_swarm.validation.runner import run_validation

DEFAULT_SUITE_PATH = Path("fixtures/evaluation/suite.json")
DEFAULT_OUTPUT_ROOT = Path("evaluations")
REQUIRED_REPORT_JSON_KEYS = [
    "report_version",
    "run_id",
    "brief_id",
    "project_name",
    "run_status",
    "panel_spec",
    "execution",
    "scores",
    "risk_map",
    "skeptic_review",
    "planner_steps",
    "response_index",
    "disclaimer",
]
REQUIRED_REPORT_SECTIONS = [
    "## 1. Executive Summary",
    "## 2. Concept Understanding",
    "## 3. Target Segment Fit",
    "## 4. Problem Resonance Score",
    "## 5. Solution Attractiveness Score",
    "## 6. Willingness to Pay Signals",
    "## 7. Top Buying Triggers",
    "## 8. Top Objections",
    "## 9. Segment-by-Segment Reaction",
    "## 10. Sensitive Topic Risk",
    "## 11. Privacy / Fairness / Inclusion Risk",
    "## 12. Assumption Risk Map",
    "## 13. Recommended Repositioning",
    "## 14. Suggested Landing Page Message",
    "## 15. Suggested Concierge MVP",
    "## 16. Suggested 7-Day No-Code Validation Plan",
    "## 17. Suggested Real User Interview Script",
    "## 18. What This AI Validation Cannot Prove",
    "## 19. Disclaimer",
]


def load_evaluation_suite(path: Path = DEFAULT_SUITE_PATH) -> dict[str, object]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Evaluation suite must be a JSON object.")
    fixtures = payload.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("Evaluation suite must define at least one fixture.")
    return payload


def build_report_projection(report_payload: dict[str, object]) -> dict[str, object]:
    return {
        "brief_id": report_payload.get("brief_id"),
        "project_name": report_payload.get("project_name"),
        "run_status": report_payload.get("run_status"),
        "panel_spec": report_payload.get("panel_spec"),
        "execution": report_payload.get("execution"),
        "scores": report_payload.get("scores"),
        "trigger_clusters": [
            {
                "trigger": item.get("trigger"),
                "count": item.get("count"),
                "share_pct": item.get("share_pct"),
                "panel_roles": item.get("panel_roles"),
                "persona_ids": item.get("persona_ids"),
            }
            for item in report_payload.get("trigger_clusters", [])
        ],
        "objection_clusters": [
            {
                "objection": item.get("objection"),
                "count": item.get("count"),
                "share_pct": item.get("share_pct"),
                "panel_roles": item.get("panel_roles"),
                "persona_ids": item.get("persona_ids"),
            }
            for item in report_payload.get("objection_clusters", [])
        ],
        "risk_map": [
            {
                "category": item.get("category"),
                "highest_severity": item.get("highest_severity"),
                "finding_count": item.get("finding_count"),
            }
            for item in report_payload.get("risk_map", [])
        ],
        "assumption_risk_map": [
            {
                "finding_id": item.get("finding_id"),
                "severity": item.get("severity"),
                "title": item.get("title"),
            }
            for item in report_payload.get("assumption_risk_map", [])
        ],
        "planner_steps": report_payload.get("planner_steps", []),
        "response_index": [
            {
                "synthetic_user_id": item.get("synthetic_user_id"),
                "panel_role": item.get("panel_role"),
                "likely_objection": item.get("likely_objection"),
                "what_would_make_them_try": item.get("what_would_make_them_try"),
                "scorecard": item.get("scorecard"),
            }
            for item in report_payload.get("response_index", [])
        ],
    }


def build_report_fingerprint(report_payload: dict[str, object]) -> str:
    projection = build_report_projection(report_payload)
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _gate_result(name: str, passed: bool, details: str) -> dict[str, object]:
    return {
        "gate": name,
        "status": "passed" if passed else "failed",
        "details": details,
    }


def _score_range_gates(
    report_payload: dict[str, object],
    expectations: dict[str, object],
) -> list[dict[str, object]]:
    gates: list[dict[str, object]] = []
    scores = report_payload.get("scores", {})
    score_ranges = expectations.get("score_ranges", {})
    if not isinstance(score_ranges, dict):
        return gates

    for score_name, bounds in score_ranges.items():
        if not isinstance(bounds, dict):
            continue
        actual_value = scores.get(score_name)
        passed = actual_value is not None
        reasons: list[str] = []
        if actual_value is None:
            reasons.append("missing score")
        else:
            numeric_value = float(actual_value)
            min_value = bounds.get("min")
            max_value = bounds.get("max")
            if min_value is not None and numeric_value < float(min_value):
                passed = False
                reasons.append(f"{numeric_value} < min {min_value}")
            if max_value is not None and numeric_value > float(max_value):
                passed = False
                reasons.append(f"{numeric_value} > max {max_value}")
            if not reasons:
                reasons.append(f"{numeric_value} within expected range")

        gates.append(_gate_result(f"score_range:{score_name}", passed, "; ".join(reasons)))

    return gates


def _evaluate_run(
    *,
    report_payload: dict[str, object],
    report_markdown: str,
    run_payload: dict[str, object],
    expectations: dict[str, object],
    default_forbidden_phrases: list[str],
) -> list[dict[str, object]]:
    gates: list[dict[str, object]] = []
    expected_status = str(expectations.get("expected_run_status", "completed"))
    actual_status = str(run_payload.get("status"))
    gates.append(
        _gate_result(
            "run_status",
            actual_status == expected_status,
            f"expected {expected_status}, got {actual_status}",
        )
    )

    expected_success_count = expectations.get("expected_successful_response_count")
    if expected_success_count is not None:
        actual_success_count = int(run_payload.get("successful_response_count", 0))
        gates.append(
            _gate_result(
                "successful_response_count",
                actual_success_count == int(expected_success_count),
                f"expected {expected_success_count}, got {actual_success_count}",
            )
        )

    missing_json_keys = [key for key in REQUIRED_REPORT_JSON_KEYS if key not in report_payload]
    missing_sections = [section for section in REQUIRED_REPORT_SECTIONS if section not in report_markdown]
    gates.append(
        _gate_result(
            "report_completeness",
            not missing_json_keys and not missing_sections,
            f"missing_json_keys={missing_json_keys}; missing_sections={missing_sections}",
        )
    )

    disclaimer_in_markdown = DISCLAIMER in report_markdown
    disclaimer_in_json = report_payload.get("disclaimer") == DISCLAIMER
    gates.append(
        _gate_result(
            "disclaimer",
            disclaimer_in_markdown and disclaimer_in_json,
            f"markdown={disclaimer_in_markdown}; json={disclaimer_in_json}",
        )
    )

    risk_map = report_payload.get("risk_map", [])
    actual_categories = sorted(
        {
            str(entry.get("category"))
            for entry in risk_map
            if isinstance(entry, dict) and entry.get("category") is not None
        }
    )
    required_categories = expectations.get("required_audit_categories", [])
    missing_categories = [
        category for category in required_categories if category not in actual_categories
    ] if isinstance(required_categories, list) else []
    gates.append(
        _gate_result(
            "required_audit_categories",
            not missing_categories,
            f"required={required_categories}; actual={actual_categories}; missing={missing_categories}",
        )
    )

    phrases = list(default_forbidden_phrases)
    if isinstance(expectations.get("forbidden_phrases"), list):
        phrases.extend(str(item) for item in expectations["forbidden_phrases"])
    found_phrases = [phrase for phrase in phrases if phrase.lower() in report_markdown.lower()]
    gates.append(
        _gate_result(
            "forbidden_phrase_scan",
            not found_phrases,
            f"found={found_phrases}",
        )
    )

    gates.extend(_score_range_gates(report_payload, expectations))
    return gates


def _fixture_name(fixture: dict[str, object]) -> str:
    return str(fixture.get("name") or fixture.get("fixture_id") or "fixture")


def _panel_spec_from_fixture(fixture: dict[str, object]) -> PanelSpec:
    panel_payload = fixture.get("panel_spec", {})
    if not isinstance(panel_payload, dict):
        raise ValueError(f"Fixture '{fixture.get('fixture_id', 'unknown')}' has invalid panel_spec.")
    return PanelSpec(
        panel_type=str(panel_payload["panel_type"]),
        sample_size=int(panel_payload["sample_size"]),
        random_seed=int(panel_payload["random_seed"]) if panel_payload.get("random_seed") is not None else None,
        filters=dict(panel_payload.get("filters", {})),
        preset_name=str(panel_payload.get("preset_name", panel_payload["panel_type"])),
    )


def _fixture_brief_path(suite_path: Path, fixture: dict[str, object]) -> Path:
    brief_path = fixture.get("brief_path")
    if not isinstance(brief_path, str) or not brief_path:
        raise ValueError(f"Fixture '{fixture.get('fixture_id', 'unknown')}' is missing brief_path.")
    return (suite_path.parent / brief_path).resolve()


def run_evaluation_suite(
    *,
    suite_path: Path = DEFAULT_SUITE_PATH,
    persona_dir: Path,
    provider,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    max_retries: int = 1,
    repeat_count: int = 2,
) -> Path:
    if repeat_count < 1:
        raise ValueError("repeat_count must be at least 1.")

    suite_payload = load_evaluation_suite(suite_path)
    fixtures = suite_payload["fixtures"]
    default_forbidden_phrases = [
        str(item) for item in suite_payload.get("default_forbidden_phrases", [])
    ]

    evaluation_id = datetime.now(UTC).strftime("eval_%Y%m%d_%H%M%S_%f")
    evaluation_dir = output_root / evaluation_id
    fixtures_output_dir = evaluation_dir / "fixtures"
    ensure_dir(fixtures_output_dir)
    export_file(suite_path, evaluation_dir / "suite.json")

    fixture_results: list[dict[str, object]] = []
    failed_fixture_count = 0

    for fixture_payload in fixtures:
        if not isinstance(fixture_payload, dict):
            raise ValueError("Each evaluation fixture must be a JSON object.")
        fixture_id = str(fixture_payload.get("fixture_id", "")).strip()
        if not fixture_id:
            raise ValueError("Each evaluation fixture must define a non-empty fixture_id.")

        fixture_dir = fixtures_output_dir / fixture_id
        ensure_dir(fixture_dir)
        brief_path = _fixture_brief_path(suite_path, fixture_payload)
        panel_spec = _panel_spec_from_fixture(fixture_payload)
        expectations = fixture_payload.get("expectations", {})
        if not isinstance(expectations, dict):
            raise ValueError(f"Fixture '{fixture_id}' has invalid expectations.")

        repeats: list[dict[str, object]] = []
        fingerprints: list[str] = []

        for repeat_index in range(1, repeat_count + 1):
            run_root = fixture_dir / f"repeat_{repeat_index}"
            run_dir = run_validation(
                brief_path=brief_path,
                persona_dir=persona_dir,
                panel_spec=panel_spec,
                provider=provider,
                run_root=run_root,
                max_retries=max_retries,
            )
            report_payload = read_json(run_dir / "report.json")
            run_payload = read_json(run_dir / "run.json")
            report_markdown = (run_dir / "report.md").read_text(encoding="utf-8")
            gates = _evaluate_run(
                report_payload=report_payload,
                report_markdown=report_markdown,
                run_payload=run_payload,
                expectations=expectations,
                default_forbidden_phrases=default_forbidden_phrases,
            )
            fingerprint = build_report_fingerprint(report_payload)
            fingerprints.append(fingerprint)
            repeats.append(
                {
                    "repeat_index": repeat_index,
                    "run_dir": str(run_dir),
                    "run_id": run_payload.get("run_id"),
                    "run_status": run_payload.get("status"),
                    "successful_response_count": run_payload.get("successful_response_count"),
                    "failed_response_count": run_payload.get("failed_response_count"),
                    "selected_persona_ids": run_payload.get("selected_persona_ids", []),
                    "report_fingerprint": fingerprint,
                    "score_snapshot": report_payload.get("scores", {}),
                    "audit_categories": [
                        entry.get("category")
                        for entry in report_payload.get("risk_map", [])
                        if isinstance(entry, dict) and entry.get("category") is not None
                    ],
                    "quality_gates": gates,
                }
            )

        deterministic_match = len(set(fingerprints)) == 1
        deterministic_gate = _gate_result(
            "deterministic_rerun",
            deterministic_match,
            f"fingerprints={fingerprints}",
        )
        primary_repeat = repeats[0]
        primary_gates = list(primary_repeat["quality_gates"])
        primary_gates.append(deterministic_gate)
        failed_gates = [gate["gate"] for gate in primary_gates if gate["status"] == "failed"]
        fixture_status = "passed" if not failed_gates else "failed"
        if fixture_status == "failed":
            failed_fixture_count += 1

        fixture_results.append(
            {
                "fixture_id": fixture_id,
                "name": _fixture_name(fixture_payload),
                "status": fixture_status,
                "canonical_run_dir": primary_repeat["run_dir"],
                "report_fingerprint": primary_repeat["report_fingerprint"],
                "deterministic_match": deterministic_match,
                "score_snapshot": primary_repeat["score_snapshot"],
                "audit_categories": primary_repeat["audit_categories"],
                "selected_persona_ids": primary_repeat["selected_persona_ids"],
                "quality_gates": primary_gates,
                "failed_gates": failed_gates,
                "repeats": repeats,
            }
        )

    summary = {
        "evaluation_version": "evaluation-harness/v1",
        "suite_id": suite_payload.get("suite_id", "evaluation_suite"),
        "suite_version": suite_payload.get("suite_version", "evaluation-suite/v1"),
        "provider": getattr(provider, "model_version", "unknown"),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "repeat_count": repeat_count,
        "fixture_count": len(fixture_results),
        "passed_fixture_count": len(fixture_results) - failed_fixture_count,
        "failed_fixture_count": failed_fixture_count,
        "overall_status": "passed" if failed_fixture_count == 0 else "failed",
        "fixtures": fixture_results,
    }
    write_json(evaluation_dir / "summary.json", summary)
    from ai_validation_swarm.evaluation.rubric import render_manual_rubric

    (evaluation_dir / "manual_rubric.md").write_text(render_manual_rubric(summary), encoding="utf-8")
    return evaluation_dir

