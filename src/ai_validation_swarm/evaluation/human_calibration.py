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
TRACE_TERMINAL_RESULTS = {"blocked", "stopped", "abandoned", "failed", "partial_success", "backtrack"}
TRACE_TRUST_TERMS = {
    "access",
    "broad",
    "client",
    "credential",
    "data",
    "permission",
    "permissions",
    "privacy",
    "proof",
    "scope",
    "trust",
    "value",
}
CATEGORY_ALIASES = {
    "objection": "objection",
    "trigger": "adoption_trigger",
    "adoption_trigger": "adoption_trigger",
    "trust_concern": "trust_gap",
    "trust_gap": "trust_gap",
    "risk": "risk",
    "task_failure": "task_failure",
    "abandonment": "abandonment",
    "decision_change": "decision_change",
    "adoption_barrier": "adoption_barrier",
}
READY_STATUS_TO_PROJECTION = {
    "calibrated_fixture_only": "fixture_only_scope",
    "directional_calibration_ready": "directional_scope_ready",
    "candidate_replacement_ready": "candidate_scope_ready",
    "high_stakes_human_review_required": "high_stakes_gate",
    "not_ready": "threshold_gap",
}


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


def _read_required_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _resolve_benchmark_definition_path(suite_path: Path, raw_path: Any) -> Path:
    candidate = Path(str(raw_path or "").strip())
    if not str(candidate):
        raise ValueError("Benchmark reference is missing benchmark_path.")
    return candidate if candidate.is_absolute() else (suite_path.parent / candidate).resolve()


def _resolve_suite_benchmark(suite_path: Path, benchmark: dict[str, Any]) -> dict[str, Any]:
    benchmark_path = benchmark.get("benchmark_path")
    if not benchmark_path:
        return dict(benchmark)
    definition_path = _resolve_benchmark_definition_path(suite_path, benchmark_path)
    resolved = _read_required_json_object(definition_path, label="Benchmark definition")
    merged = {
        **resolved,
        **{key: value for key, value in benchmark.items() if key != "benchmark_path"},
        "benchmark_definition_path": str(definition_path),
    }
    return merged


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


def _normalize_category(raw_category: Any) -> str:
    normalized = _slug(str(raw_category or ""))
    return CATEGORY_ALIASES.get(normalized, normalized or "observation")


def _review_finding_to_signal(item: dict[str, Any]) -> dict[str, Any] | None:
    objection = str(item.get("objection") or "").strip()
    trigger = str(item.get("trigger") or "").strip()
    trust_concern = str(item.get("trust_concern") or "").strip()
    title = str(item.get("title") or "").strip()
    observation = str(item.get("observation") or "").strip()
    category = str(item.get("category") or "").strip()

    if objection:
        signal_category = "objection"
        label = objection
    elif trigger:
        signal_category = "adoption_trigger"
        label = trigger
    elif trust_concern:
        signal_category = "trust_gap"
        label = trust_concern
    else:
        signal_category = _normalize_category(category)
        label = title or observation or category

    if not label:
        return None

    explicit_terms = [str(value) for value in item.get("terms", []) if value]
    contextual_terms = [str(item.get(field) or "") for field in SIGNAL_FIELDS if item.get(field)]
    return _signal(
        category=signal_category,
        label=label,
        source="human_outcomes.review_findings",
        severity=str(item.get("severity") or "medium"),
        weight=float(item.get("weight") or 1.0),
        terms=[*explicit_terms, *contextual_terms],
    )


def _dedupe_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        deduped.setdefault(str(signal["signal_id"]), signal)
    return list(deduped.values())


def _trace_context_terms(trace: dict[str, Any], actions: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for key in ("summary", "first_error", "drop_off_point", "completion_notes", "task_outcome"):
        value = str(trace.get(key) or "").strip()
        if value:
            terms.append(value)
    for action in actions:
        if not isinstance(action, dict):
            continue
        for key in ("action", "target", "screen", "result", "note"):
            value = str(action.get(key) or "").strip()
            if value:
                terms.append(value)
    return terms


def _extract_observed_trace_signals(run_dir: Path) -> list[dict[str, Any]]:
    trace = _read_optional_json(run_dir / "observed_action_trace.json")
    if not trace:
        return []
    actions = trace.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    task_outcome = str(trace.get("task_outcome") or "").strip().lower()
    first_error = str(trace.get("first_error") or "").strip()
    drop_off_point = str(trace.get("drop_off_point") or "").strip()
    terms = _trace_context_terms(trace, actions)
    signals: list[dict[str, Any]] = []

    if first_error or (task_outcome and task_outcome != "success"):
        signals.append(
            _signal(
                category="task_failure",
                label=first_error or f"task outcome {task_outcome}",
                source="observed_action_trace",
                severity="high" if task_outcome in TRACE_TERMINAL_RESULTS else "medium",
                terms=terms,
            )
        )

    action_results = {
        str(action.get("result") or "").strip().lower()
        for action in actions
        if isinstance(action, dict) and str(action.get("result") or "").strip()
    }
    if drop_off_point or task_outcome in TRACE_TERMINAL_RESULTS or bool(action_results & TRACE_TERMINAL_RESULTS):
        signals.append(
            _signal(
                category="abandonment",
                label=drop_off_point or f"incomplete task outcome {task_outcome or 'unknown'}",
                source="observed_action_trace",
                severity="high" if task_outcome in {"abandoned", "failed", "blocked"} else "medium",
                terms=terms,
            )
        )

    if _tokens(" ".join(terms)) & TRACE_TRUST_TERMS:
        trust_label = first_error or drop_off_point or str(trace.get("summary") or "").strip() or "permission or trust concern"
        signals.append(
            _signal(
                category="trust_gap",
                label=trust_label,
                source="observed_action_trace",
                severity="medium",
                terms=terms,
            )
        )

    return signals


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

    signals.extend(_extract_observed_trace_signals(run_dir))
    return _dedupe_signals(signals)


def load_human_benchmark_suite(path: Path = DEFAULT_SUITE_PATH) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Human benchmark suite must be a JSON object.")
    benchmarks = payload.get("benchmarks", [])
    if not isinstance(benchmarks, list) or not benchmarks:
        raise ValueError("Human benchmark suite must define at least one benchmark.")
    resolved_benchmarks: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict):
            continue
        resolved_benchmarks.append(_resolve_suite_benchmark(path.resolve(), benchmark))
    if not resolved_benchmarks:
        raise ValueError("Human benchmark suite has no usable benchmark objects.")
    payload = {
        **payload,
        "suite_path": str(path.resolve()),
        "benchmarks": resolved_benchmarks,
    }
    return payload


def _expected_signals(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    outcomes = benchmark.get("human_outcomes", {})
    if not isinstance(outcomes, dict):
        raise ValueError(f"Benchmark '{benchmark.get('benchmark_id', 'unknown')}' must define human_outcomes.")
    signals: list[dict[str, Any]] = []
    for item in outcomes.get("signals", []):
        if not isinstance(item, dict):
            continue
        category = _normalize_category(item.get("category"))
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
    for item in outcomes.get("review_findings", []):
        if not isinstance(item, dict):
            continue
        signal = _review_finding_to_signal(item)
        if signal is not None:
            signals.append(signal)
    if not signals:
        raise ValueError(
            f"Benchmark '{benchmark.get('benchmark_id', 'unknown')}' must define usable human_outcomes.signals or human_outcomes.review_findings."
        )
    return _dedupe_signals(signals)


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


def _build_readiness_projection(
    *,
    benchmark: dict[str, Any],
    metrics: dict[str, Any],
    replacement: dict[str, Any],
    human_panel: dict[str, Any],
    synthetic_panel: dict[str, Any],
    predicted: list[dict[str, Any]],
    expected: list[dict[str, Any]],
) -> dict[str, Any]:
    source = benchmark.get("source", {}) if isinstance(benchmark.get("source"), dict) else {}
    thresholds = replacement.get("thresholds", {}) if isinstance(replacement.get("thresholds"), dict) else {}
    projection_status = READY_STATUS_TO_PROJECTION.get(
        str(replacement.get("status") or "not_ready"),
        "threshold_gap",
    )
    gate_reasons: list[str] = []
    threshold_gaps: list[str] = []

    if bool(replacement.get("high_stakes_gate")):
        gate_reasons.append("high_stakes_human_review_required")

    metric_checks = {
        "precision": (
            float(metrics.get("precision") or 0.0),
            float(thresholds.get("min_precision") or 0.0),
        ),
        "recall": (
            float(metrics.get("recall") or 0.0),
            float(thresholds.get("min_recall") or 0.0),
        ),
        "alignment_score": (
            float(metrics.get("alignment_score") or 0.0),
            float(thresholds.get("min_alignment_score") or 0.0),
        ),
    }
    for label, (actual, minimum) in metric_checks.items():
        if actual < minimum:
            threshold_gaps.append(f"{label}_below_threshold")
    if projection_status == "fixture_only_scope":
        gate_reasons.append("fixture_human_review_only")
    if projection_status == "directional_scope_ready":
        gate_reasons.append("replacement_threshold_not_met")
    if projection_status == "threshold_gap":
        gate_reasons.extend(threshold_gaps or ["configured_readiness_threshold_not_met"])

    source_type = str(source.get("source_type") or "fixture_human_review")
    benchmark_definition_path = str(benchmark.get("benchmark_definition_path") or "").strip()
    return {
        "contract_version": "human-calibration-readiness/v1",
        "status": projection_status,
        "status_reason": str(replacement.get("status") or "unknown"),
        "scope": {
            "benchmark_id": benchmark.get("benchmark_id"),
            "research_stage": str(benchmark.get("research_stage") or "unknown"),
            "evidence_type": str(benchmark.get("evidence_type") or "unknown"),
        },
        "coverage": {
            "source_type": source_type,
            "review_method": str(source.get("review_method") or ""),
            "benchmark_origin": "external_definition" if benchmark_definition_path else "inline_suite",
            "benchmark_definition_path": benchmark_definition_path or None,
            "human_participant_count": int(human_panel.get("participant_count") or 0),
            "synthetic_sample_size": int(synthetic_panel.get("sample_size") or 0),
            "human_outcome_count": len(expected),
            "predicted_signal_count": len(predicted),
        },
        "quality": {
            "alignment_score": float(metrics.get("alignment_score") or 0.0),
            "precision": float(metrics.get("precision") or 0.0),
            "recall": float(metrics.get("recall") or 0.0),
            "threshold_passed": bool(replacement.get("threshold_passed")),
            "replacement_threshold_met": str(replacement.get("status") or "") == "candidate_replacement_ready",
        },
        "gate_reasons": sorted(dict.fromkeys(reason for reason in gate_reasons if reason)),
        "threshold_gaps": sorted(dict.fromkeys(gap for gap in threshold_gaps if gap)),
        "boundary": str(replacement.get("boundary") or ""),
    }


def _load_optional_run_contract(run_dir: Path) -> dict[str, Any]:
    payload = _read_optional_json(run_dir / "run_contract.json")
    if isinstance(payload, dict) and payload.get("contract_version") == "shared-run-contract/v1":
        return payload
    return {}


def _coverage_status_from_run_contract(run_contract: dict[str, Any]) -> dict[str, Any]:
    result = run_contract.get("result", {}) if isinstance(run_contract.get("result"), dict) else {}
    metadata = result.get("metadata", {}) if isinstance(result.get("metadata"), dict) else {}
    coverage = metadata.get("coverage_status", {}) if isinstance(metadata.get("coverage_status"), dict) else {}
    return coverage


def _selected_persona_ids(run_payload: dict[str, Any], run_contract: dict[str, Any]) -> list[str]:
    selected = run_payload.get("selected_persona_ids")
    if isinstance(selected, list) and selected:
        return [str(item) for item in selected if str(item or "").strip()]
    result = run_contract.get("result", {}) if isinstance(run_contract.get("result"), dict) else {}
    selected = result.get("selected_persona_ids")
    if isinstance(selected, list):
        return [str(item) for item in selected if str(item or "").strip()]
    return []


def _cause_record(
    *,
    cause_id: str,
    label: str,
    confidence: str,
    reason: str,
    evidence: dict[str, Any],
    applies_to: list[str],
) -> dict[str, Any]:
    return {
        "cause_id": cause_id,
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
        "applies_to": applies_to,
    }


def _missing_and_unsupported_signals(
    *,
    metrics: dict[str, Any],
    predicted: list[dict[str, Any]],
    expected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    missed_ids = {str(item) for item in metrics.get("missed_human_signal_ids", [])}
    unsupported_ids = {str(item) for item in metrics.get("unsupported_synthetic_signal_ids", [])}
    missing_human_signals = [item for item in expected if str(item.get("signal_id") or "") in missed_ids]
    unsupported_synthetic_signals = [item for item in predicted if str(item.get("signal_id") or "") in unsupported_ids]
    return missing_human_signals, unsupported_synthetic_signals


def _build_miss_attribution(
    *,
    benchmark: dict[str, Any],
    metrics: dict[str, Any],
    predicted: list[dict[str, Any]],
    expected: list[dict[str, Any]],
    run_payload: dict[str, Any],
    run_contract: dict[str, Any],
    stimulus_analysis: dict[str, Any],
    human_panel: dict[str, Any],
    synthetic_panel: dict[str, Any],
) -> dict[str, Any]:
    false_negative = int(metrics.get("false_negative") or 0)
    false_positive = int(metrics.get("false_positive") or 0)
    missing_human_signals, unsupported_synthetic_signals = _missing_and_unsupported_signals(
        metrics=metrics,
        predicted=predicted,
        expected=expected,
    )
    missing_categories = sorted({str(item.get("category") or "") for item in missing_human_signals if item.get("category")})
    unsupported_categories = sorted(
        {str(item.get("category") or "") for item in unsupported_synthetic_signals if item.get("category")}
    )
    selected_persona_ids = _selected_persona_ids(run_payload, run_contract)
    sample_size = int(
        synthetic_panel.get("sample_size")
        or len(selected_persona_ids)
        or 0
    )
    human_participant_count = int(human_panel.get("participant_count") or 0)
    coverage_status = _coverage_status_from_run_contract(run_contract)
    interpretation_risks = (
        list(stimulus_analysis.get("interpretation_risks", []))
        if isinstance(stimulus_analysis.get("interpretation_risks"), list)
        else []
    )
    stimulus_missing_context = (
        list(stimulus_analysis.get("missing_context", []))
        if isinstance(stimulus_analysis.get("missing_context"), list)
        else []
    )

    likely_causes: list[dict[str, Any]] = []
    if false_negative > 0:
        if (
            (sample_size and human_participant_count and sample_size < human_participant_count)
            or len(missing_categories) >= 2
            or (sample_size <= 1 and len(missing_categories) >= 1)
        ):
            confidence = "high" if sample_size and human_participant_count and sample_size < human_participant_count else "medium"
            likely_causes.append(
                _cause_record(
                    cause_id="persona_coverage_gap",
                    label="Persona or panel coverage gap",
                    confidence=confidence,
                    reason=(
                        "Human outcome categories remained unmatched while the selected synthetic panel appears narrower than the human comparison context."
                        if confidence == "high"
                        else "Human outcome categories remained unmatched, suggesting relevant human-difference patterns may be underrepresented in the selected personas."
                    ),
                    evidence={
                        "missing_human_signal_ids": metrics.get("missed_human_signal_ids", []),
                        "missing_categories": missing_categories,
                        "synthetic_sample_size": sample_size,
                        "human_participant_count": human_participant_count,
                        "selected_persona_ids": selected_persona_ids,
                    },
                    applies_to=["false_negative"],
                )
            )

        coverage_complete = bool(coverage_status.get("coverage_complete", True))
        depth_complete = bool(coverage_status.get("depth_complete", True))
        coverage_missing = list(coverage_status.get("missing", [])) if isinstance(coverage_status.get("missing"), list) else []
        depth_missing = list(coverage_status.get("depth_missing", [])) if isinstance(coverage_status.get("depth_missing"), list) else []
        if not coverage_complete or not depth_complete or coverage_missing or depth_missing:
            confidence = "high" if (not coverage_complete or not depth_complete) else "medium"
            likely_causes.append(
                _cause_record(
                    cause_id="facilitator_behavior_gap",
                    label="Facilitator coverage or probing gap",
                    confidence=confidence,
                    reason="Run-level coverage metadata shows unresolved coverage or depth requirements before calibration misses are considered.",
                    evidence={
                        "coverage_complete": coverage_complete,
                        "depth_complete": depth_complete,
                        "coverage_missing": coverage_missing,
                        "depth_missing": depth_missing,
                    },
                    applies_to=["false_negative"],
                )
            )

        research_stage = str(benchmark.get("research_stage") or "")
        evidence_type = str(benchmark.get("evidence_type") or "")
        if interpretation_risks or stimulus_missing_context:
            confidence = "high" if interpretation_risks else "medium"
            likely_causes.append(
                _cause_record(
                    cause_id="stimulus_interpretation_gap",
                    label="Stimulus interpretation gap",
                    confidence=confidence,
                    reason=(
                        "Prototype or stimulus analysis already recorded interpretation risk or missing context, so some misses may come from how the stimulus was understood rather than from persona truth alone."
                    ),
                    evidence={
                        "research_stage": research_stage,
                        "evidence_type": evidence_type,
                        "interpretation_risks": interpretation_risks,
                        "stimulus_missing_context": stimulus_missing_context,
                        "analysis_type": str(stimulus_analysis.get("analysis_type") or ""),
                    },
                    applies_to=["false_negative"],
                )
            )

    if false_positive > 0:
        confidence = "high" if false_positive >= max(1, false_negative) else "medium"
        likely_causes.append(
            _cause_record(
                cause_id="synthesis_ranking_gap",
                label="Synthesis or ranking gap",
                confidence=confidence,
                reason="Synthetic output surfaced unsupported signals that were not confirmed by the human comparison set, which points to aggregation, weighting, or ranking overreach.",
                evidence={
                    "unsupported_synthetic_signal_ids": metrics.get("unsupported_synthetic_signal_ids", []),
                    "unsupported_categories": unsupported_categories,
                    "false_positive": false_positive,
                    "precision": float(metrics.get("precision") or 0.0),
                },
                applies_to=["false_positive"],
            )
        )

    if false_negative == 0 and false_positive == 0:
        return {
            "contract_version": "human-calibration-miss-attribution/v1",
            "status": "fully_aligned",
            "primary_cause_id": None,
            "primary_cause_label": "",
            "likely_causes": [],
            "summary": "No material calibration miss was detected for this benchmark comparison.",
            "boundary": "Miss attribution is heuristic calibration triage. A clean alignment result does not prove universal coverage outside this scoped benchmark.",
        }

    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    likely_causes.sort(key=lambda item: confidence_rank.get(str(item.get("confidence") or "low"), 1), reverse=True)
    primary = likely_causes[0] if likely_causes else None
    return {
        "contract_version": "human-calibration-miss-attribution/v1",
        "status": "miss_detected",
        "primary_cause_id": str(primary.get("cause_id") or "") if isinstance(primary, dict) else "unknown",
        "primary_cause_label": str(primary.get("label") or "") if isinstance(primary, dict) else "Unknown miss source",
        "likely_causes": likely_causes,
        "summary": (
            str(primary.get("reason") or "")
            if isinstance(primary, dict)
            else "Calibration misses were detected, but the current run artifacts do not isolate one strong likely cause."
        ),
        "boundary": "Miss attribution is heuristic calibration triage. It highlights likely sources of mismatch, not final causal proof.",
    }


def _aggregate_suite_readiness(results: list[dict[str, Any]]) -> dict[str, Any]:
    projection_statuses = [str(item.get("readiness_projection", {}).get("status") or "") for item in results if isinstance(item, dict)]
    coverage_items = [item.get("readiness_projection", {}).get("coverage", {}) for item in results if isinstance(item, dict)]
    gate_reasons: list[str] = []
    for item in results:
        projection = item.get("readiness_projection", {}) if isinstance(item, dict) else {}
        for reason in projection.get("gate_reasons", []) if isinstance(projection, dict) else []:
            if reason:
                gate_reasons.append(str(reason))
    counts = {
        "candidate_scope_count": projection_statuses.count("candidate_scope_ready"),
        "directional_scope_count": projection_statuses.count("directional_scope_ready"),
        "fixture_only_scope_count": projection_statuses.count("fixture_only_scope"),
        "high_stakes_gate_count": projection_statuses.count("high_stakes_gate"),
        "threshold_gap_count": projection_statuses.count("threshold_gap"),
    }
    if counts["candidate_scope_count"] > 0:
        status = "scoped_external_readiness_available"
    elif counts["directional_scope_count"] > 0:
        status = "directional_external_readiness_only"
    elif counts["fixture_only_scope_count"] > 0 and counts["threshold_gap_count"] == 0:
        status = "fixture_only_calibration"
    elif counts["high_stakes_gate_count"] > 0 and counts["candidate_scope_count"] == 0 and counts["directional_scope_count"] == 0:
        status = "high_stakes_gate_active"
    else:
        status = "threshold_gap"
    return {
        "contract_version": "human-calibration-suite-readiness/v1",
        "status": status,
        "external_benchmark_count": sum(
            1 for coverage in coverage_items
            if isinstance(coverage, dict) and str(coverage.get("benchmark_origin") or "") == "external_definition"
        ),
        "real_human_study_count": sum(
            1 for coverage in coverage_items
            if isinstance(coverage, dict) and str(coverage.get("source_type") or "") == "real_human_study"
        ),
        "fixture_human_review_count": sum(
            1 for coverage in coverage_items
            if isinstance(coverage, dict) and str(coverage.get("source_type") or "") != "real_human_study"
        ),
        **counts,
        "gate_reasons": sorted(dict.fromkeys(gate_reasons)),
        "supported_scopes": [
            {
                "benchmark_id": item.get("benchmark_id"),
                "research_stage": item.get("run", {}).get("research_stage"),
                "evidence_type": item.get("run", {}).get("evidence_type"),
                "status": item.get("readiness_projection", {}).get("status"),
                "source_type": item.get("human_benchmark", {}).get("source_type"),
                "alignment_score": item.get("prediction_accuracy", {}).get("alignment_score"),
            }
            for item in results
            if isinstance(item, dict)
        ],
    }


def evaluate_run_against_benchmark(*, run_dir: Path, benchmark: dict[str, Any]) -> dict[str, Any]:
    run_payload = _read_optional_json(run_dir / "run.json")
    report_payload = _read_optional_json(run_dir / "report.json")
    run_contract = _load_optional_run_contract(run_dir)
    stimulus_analysis = _read_optional_json(run_dir / "stimulus_analysis.json")
    predicted = extract_synthetic_signals(run_dir)
    expected = _expected_signals(benchmark)
    metrics = _score_alignment(predicted, expected)
    source = benchmark.get("source", {}) if isinstance(benchmark.get("source"), dict) else {}
    human_panel = benchmark.get("human_panel", {}) if isinstance(benchmark.get("human_panel"), dict) else {}
    synthetic_panel = report_payload.get("panel_spec", {}) if isinstance(report_payload.get("panel_spec"), dict) else {}
    replacement = _replacement_readiness(benchmark=benchmark, metrics=metrics)
    readiness_projection = _build_readiness_projection(
        benchmark=benchmark,
        metrics=metrics,
        replacement=replacement,
        human_panel=human_panel,
        synthetic_panel=synthetic_panel,
        predicted=predicted,
        expected=expected,
    )
    miss_attribution = _build_miss_attribution(
        benchmark=benchmark,
        metrics=metrics,
        predicted=predicted,
        expected=expected,
        run_payload=run_payload,
        run_contract=run_contract,
        stimulus_analysis=stimulus_analysis,
        human_panel=human_panel,
        synthetic_panel=synthetic_panel,
    )
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
            "benchmark_definition_path": benchmark.get("benchmark_definition_path"),
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
        "readiness_projection": readiness_projection,
        "miss_attribution": miss_attribution,
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
    projection = payload.get("readiness_projection", {})
    miss_attribution = payload.get("miss_attribution", {})
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
            f"- Readiness projection: {projection.get('status') if isinstance(projection, dict) else ''}",
            f"- Miss attribution status: {miss_attribution.get('status') if isinstance(miss_attribution, dict) else ''}",
            f"- Primary likely cause: {miss_attribution.get('primary_cause_label') if isinstance(miss_attribution, dict) else ''}",
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
        "readiness_projection": _aggregate_suite_readiness(results),
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
    projection = payload.get("readiness_projection", {})
    if isinstance(projection, dict):
        lines.extend(
            [
                "",
                "## Readiness Projection",
                f"- Status: {projection.get('status')}",
                f"- External benchmarks: {projection.get('external_benchmark_count')}",
                f"- Real human studies: {projection.get('real_human_study_count')}",
                f"- Candidate scopes: {projection.get('candidate_scope_count')}",
                f"- Directional scopes: {projection.get('directional_scope_count')}",
                f"- High-stakes gates: {projection.get('high_stakes_gate_count')}",
                f"- Threshold gaps: {projection.get('threshold_gap_count')}",
            ]
        )
    lines.append("")
    return "\n".join(lines)
