from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.storage.files import ensure_dir, read_json, write_json


CONTRACT_VERSION = "human-calibration/v1"
DEFAULT_SUITE_PATH = Path("fixtures/human_calibration/suite.json")
DEFAULT_OUTPUT_ROOT = Path("evaluations/human_calibration")
SIGNAL_FIELDS = ("objection", "trigger", "trust_concern", "category", "title", "observation")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "signal"


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) >= 3}


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _signal(
    *,
    category: str,
    label: str,
    source: str,
    severity: str = "medium",
    weight: float = 1.0,
    terms: list[str] | None = None,
) -> dict[str, Any]:
    signal_terms = sorted(_tokens(" ".join([label, *(terms or [])])))
    return {
        "signal_id": f"{category}:{_slug(label)}",
        "category": category,
        "label": label,
        "source": source,
        "severity": severity,
        "weight": float(weight),
        "terms": signal_terms,
    }


def extract_synthetic_signals(run_dir: Path) -> list[dict[str, Any]]:
    report = _read_optional_json(run_dir / "report.json")
    stage_results = _read_optional_json(run_dir / "stage_results.json")
    signals: list[dict[str, Any]] = []

    for item in report.get("objection_clusters", []) if isinstance(report.get("objection_clusters"), list) else []:
        if isinstance(item, dict) and item.get("objection"):
            signals.append(_signal(category="objection", label=str(item["objection"]), source="report.objection_clusters"))

    for item in report.get("trigger_clusters", []) if isinstance(report.get("trigger_clusters"), list) else []:
        if isinstance(item, dict) and item.get("trigger"):
            signals.append(_signal(category="adoption_trigger", label=str(item["trigger"]), source="report.trigger_clusters"))

    segment_summary = report.get("segment_summary", {})
    if isinstance(segment_summary, dict):
        for segment in segment_summary.values():
            if not isinstance(segment, dict):
                continue
            for item in segment.get("top_trust_concerns", []) if isinstance(segment.get("top_trust_concerns"), list) else []:
                if isinstance(item, dict) and item.get("trust_concern"):
                    signals.append(
                        _signal(
                            category="trust_gap",
                            label=str(item["trust_concern"]),
                            source="report.segment_summary.top_trust_concerns",
                        )
                    )

    for item in report.get("risk_map", []) if isinstance(report.get("risk_map"), list) else []:
        if isinstance(item, dict) and item.get("category"):
            label = str(item.get("category") or "")
            observations = " ".join(str(value) for value in item.get("observations", []) if value)
            signals.append(
                _signal(
                    category="risk",
                    label=label,
                    source="report.risk_map",
                    severity=str(item.get("highest_severity") or "medium"),
                    terms=[observations],
                )
            )

    if isinstance(stage_results.get("stages"), list):
        for item in stage_results["stages"]:
            if isinstance(item, dict) and str(item.get("status", "")).lower() in {"failed", "blocked"}:
                signals.append(
                    _signal(
                        category="task_failure",
                        label=str(item.get("name") or item.get("stage") or "task failure"),
                        source="stage_results.stages",
                        severity="high",
                        terms=[str(item.get("error") or item.get("note") or "")],
                    )
                )

    deduped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        deduped.setdefault(str(signal["signal_id"]), signal)
    return list(deduped.values())


def load_human_benchmark_suite(path: Path = DEFAULT_SUITE_PATH) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Human benchmark suite must be a JSON object.")
    benchmarks = payload.get("benchmarks", [])
    if not isinstance(benchmarks, list) or not benchmarks:
        raise ValueError("Human benchmark suite must define at least one benchmark.")
    return payload


def _expected_signals(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    outcomes = benchmark.get("human_outcomes", {})
    if not isinstance(outcomes, dict) or not isinstance(outcomes.get("signals"), list):
        raise ValueError(f"Benchmark '{benchmark.get('benchmark_id', 'unknown')}' must define human_outcomes.signals.")
    signals = []
    for item in outcomes["signals"]:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "").strip()
        label = str(item.get("label") or "").strip()
        if not category or not label:
            continue
        signals.append(
            _signal(
                category=category,
                label=label,
                source="human_outcomes.signals",
                severity=str(item.get("severity") or "medium"),
                weight=float(item.get("weight") or 1.0),
                terms=[*(str(value) for value in item.get("terms", []) if value)],
            )
        )
    if not signals:
        raise ValueError(f"Benchmark '{benchmark.get('benchmark_id', 'unknown')}' has no usable human outcome signals.")
    return signals


def _matches(predicted: dict[str, Any], expected: dict[str, Any]) -> bool:
    if predicted.get("category") == expected.get("category"):
        predicted_terms = set(predicted.get("terms", []))
        expected_terms = set(expected.get("terms", []))
        return bool(predicted_terms & expected_terms) or _slug(str(predicted.get("label"))) == _slug(str(expected.get("label")))
    return bool(set(predicted.get("terms", [])) & set(expected.get("terms", [])))


def _score_alignment(predicted: list[dict[str, Any]], expected: list[dict[str, Any]]) -> dict[str, Any]:
    matched_predicted: set[str] = set()
    matched_expected: set[str] = set()
    matches: list[dict[str, Any]] = []

    for expected_signal in expected:
        for predicted_signal in predicted:
            if str(predicted_signal["signal_id"]) in matched_predicted:
                continue
            if _matches(predicted_signal, expected_signal):
                matched_predicted.add(str(predicted_signal["signal_id"]))
                matched_expected.add(str(expected_signal["signal_id"]))
                matches.append(
                    {
                        "expected_signal_id": expected_signal["signal_id"],
                        "predicted_signal_id": predicted_signal["signal_id"],
                        "category": expected_signal["category"],
                    }
                )
                break

    true_positive = len(matches)
    false_positive = len(predicted) - true_positive
    false_negative = len(expected) - true_positive
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(expected) if expected else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "alignment_score": round(f1 * 100, 1),
        "matches": matches,
        "missed_human_signal_ids": [
            item["signal_id"] for item in expected if str(item["signal_id"]) not in matched_expected
        ],
        "unsupported_synthetic_signal_ids": [
            item["signal_id"] for item in predicted if str(item["signal_id"]) not in matched_predicted
        ],
    }


def _replacement_readiness(
    *,
    benchmark: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    thresholds = benchmark.get("thresholds", {}) if isinstance(benchmark.get("thresholds"), dict) else {}
    min_precision = float(thresholds.get("min_precision", 0.6))
    min_recall = float(thresholds.get("min_recall", 0.6))
    min_alignment_score = float(thresholds.get("min_alignment_score", 60))
    replacement_min_score = float(thresholds.get("replacement_readiness_min_score", 85))
    source = benchmark.get("source", {}) if isinstance(benchmark.get("source"), dict) else {}
    source_type = str(source.get("source_type") or "fixture_human_review")
    high_stakes_gate = bool(benchmark.get("high_stakes_domain") or benchmark.get("requires_high_stakes_review"))

    threshold_passed = (
        float(metrics["precision"]) >= min_precision
        and float(metrics["recall"]) >= min_recall
        and float(metrics["alignment_score"]) >= min_alignment_score
    )
    replacement_candidate = threshold_passed and float(metrics["alignment_score"]) >= replacement_min_score
    if high_stakes_gate:
        status = "high_stakes_human_review_required"
    elif source_type != "real_human_study":
        status = "calibrated_fixture_only" if threshold_passed else "not_ready"
    elif replacement_candidate:
        status = "candidate_replacement_ready"
    elif threshold_passed:
        status = "directional_calibration_ready"
    else:
        status = "not_ready"

    return {
        "status": status,
        "confidence_score": float(metrics["alignment_score"]),
        "research_stage": str(benchmark.get("research_stage") or "unknown"),
        "evidence_type": str(benchmark.get("evidence_type") or "unknown"),
        "thresholds": {
            "min_precision": min_precision,
            "min_recall": min_recall,
            "min_alignment_score": min_alignment_score,
            "replacement_readiness_min_score": replacement_min_score,
        },
        "threshold_passed": threshold_passed,
        "high_stakes_gate": high_stakes_gate,
        "boundary": (
            "High-stakes evidence requires explicit human review regardless of synthetic alignment score."
            if high_stakes_gate
            else
            "Fixture-backed human review calibrates the pipeline but is not replacement-grade proof."
            if source_type != "real_human_study"
            else "Human outcome data is attached; replacement readiness remains scoped to this stage and evidence type."
        ),
    }


def evaluate_run_against_benchmark(*, run_dir: Path, benchmark: dict[str, Any]) -> dict[str, Any]:
    run_payload = _read_optional_json(run_dir / "run.json")
    report_payload = _read_optional_json(run_dir / "report.json")
    predicted = extract_synthetic_signals(run_dir)
    expected = _expected_signals(benchmark)
    metrics = _score_alignment(predicted, expected)
    source = benchmark.get("source", {}) if isinstance(benchmark.get("source"), dict) else {}
    human_panel = benchmark.get("human_panel", {}) if isinstance(benchmark.get("human_panel"), dict) else {}
    synthetic_panel = report_payload.get("panel_spec", {}) if isinstance(report_payload.get("panel_spec"), dict) else {}
    replacement = _replacement_readiness(benchmark=benchmark, metrics=metrics)
    return {
        "contract_version": CONTRACT_VERSION,
        "benchmark_id": benchmark.get("benchmark_id"),
        "benchmark_name": benchmark.get("name", benchmark.get("benchmark_id")),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "run": {
            "run_id": run_payload.get("run_id") or report_payload.get("run_id") or run_dir.name,
            "run_dir": str(run_dir),
            "run_status": run_payload.get("status") or report_payload.get("run_status"),
            "research_stage": benchmark.get("research_stage"),
            "evidence_type": benchmark.get("evidence_type"),
        },
        "human_benchmark": {
            "source_type": source.get("source_type", "fixture_human_review"),
            "review_method": source.get("review_method", "manual_fixture"),
            "outcome_count": len(expected),
            "participant_count": int(human_panel.get("participant_count") or 0),
            "segment": human_panel.get("segment", ""),
        },
        "synthetic_panel_delta": {
            "synthetic_sample_size": int(synthetic_panel.get("sample_size") or 0),
            "human_participant_count": int(human_panel.get("participant_count") or 0),
            "panel_type": synthetic_panel.get("panel_type", ""),
            "coverage_label": "human_panel_attached" if human_panel else "human_panel_missing",
        },
        "predicted_signals": predicted,
        "human_outcome_signals": expected,
        "prediction_accuracy": metrics,
        "replacement_readiness": replacement,
        "synthetic_boundary": "Calibration compares synthetic evidence to human-reviewed outcomes; it does not turn synthetic output into human market proof.",
    }


def attach_human_calibration(
    *,
    run_dir: Path,
    benchmark: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    result = evaluate_run_against_benchmark(run_dir=run_dir, benchmark=benchmark)
    target = output_path or run_dir / "human_calibration.json"
    ensure_dir(target.parent)
    write_json(target, result)
    markdown_path = target.with_suffix(".md")
    markdown_path.write_text(render_human_calibration_markdown(result), encoding="utf-8")
    return result


def render_human_calibration_markdown(payload: dict[str, Any]) -> str:
    accuracy = payload["prediction_accuracy"]
    readiness = payload["replacement_readiness"]
    return "\n".join(
        [
            "# Human Calibration Record",
            "",
            f"- Benchmark: {payload.get('benchmark_id')}",
            f"- Run: {payload['run'].get('run_id')}",
            f"- Precision: {accuracy['precision']}",
            f"- Recall: {accuracy['recall']}",
            f"- F1: {accuracy['f1']}",
            f"- Alignment score: {accuracy['alignment_score']}",
            f"- Replacement-readiness status: {readiness['status']}",
            f"- Boundary: {payload['synthetic_boundary']}",
            "",
            "## Missed Human Signals",
            *[f"- {item}" for item in accuracy.get("missed_human_signal_ids", [])],
            "",
            "## Unsupported Synthetic Signals",
            *[f"- {item}" for item in accuracy.get("unsupported_synthetic_signal_ids", [])],
            "",
        ]
    )


def run_human_calibration_suite(
    *,
    suite_path: Path = DEFAULT_SUITE_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    benchmark_id: str = "",
    run_dir: Path | None = None,
) -> Path:
    suite = load_human_benchmark_suite(suite_path)
    calibration_id = datetime.now(UTC).strftime("human_calibration_%Y%m%d_%H%M%S_%f")
    output_dir = output_root / calibration_id
    ensure_dir(output_dir)
    results: list[dict[str, Any]] = []

    for benchmark in suite["benchmarks"]:
        if not isinstance(benchmark, dict):
            continue
        if benchmark_id and benchmark.get("benchmark_id") != benchmark_id:
            continue
        benchmark_run_dir = run_dir
        if benchmark_run_dir is None:
            raw_run_dir = benchmark.get("synthetic_run_dir")
            if not raw_run_dir:
                raise ValueError(f"Benchmark '{benchmark.get('benchmark_id')}' needs synthetic_run_dir or --run-dir.")
            benchmark_run_dir = (suite_path.parent / str(raw_run_dir)).resolve()
        target = output_dir / f"{benchmark.get('benchmark_id', 'benchmark')}.human_calibration.json"
        results.append(attach_human_calibration(run_dir=benchmark_run_dir, benchmark=benchmark, output_path=target))

    if not results:
        raise ValueError("No human calibration benchmarks matched the requested filter.")

    summary = {
        "contract_version": "human-calibration-suite-result/v1",
        "suite_id": suite.get("suite_id"),
        "suite_version": suite.get("suite_version"),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "benchmark_count": len(results),
        "average_alignment_score": round(
            sum(float(item["prediction_accuracy"]["alignment_score"]) for item in results) / len(results),
            1,
        ),
        "replacement_readiness": [item["replacement_readiness"] for item in results],
        "results": results,
    }
    write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(render_suite_summary_markdown(summary), encoding="utf-8")
    return output_dir


def render_suite_summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Human Calibration Suite Summary",
        "",
        f"- Suite: {payload.get('suite_id')}",
        f"- Benchmarks: {payload.get('benchmark_count')}",
        f"- Average alignment score: {payload.get('average_alignment_score')}",
        "",
        "## Replacement Readiness",
    ]
    for item in payload.get("replacement_readiness", []):
        if isinstance(item, dict):
            lines.append(
                f"- {item.get('research_stage')} / {item.get('evidence_type')}: "
                f"{item.get('status')} ({item.get('confidence_score')})"
            )
    lines.append("")
    return "\n".join(lines)
