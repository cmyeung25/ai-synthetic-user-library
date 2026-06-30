# Milestone 17 External Human Benchmark Calibration Design Spec

Status: `implemented`

## Purpose

Milestone 17 extends the human calibration pipeline from one checked-in fixture suite toward externally defined human benchmark records.

The research bottleneck is no longer whether the platform can score one fixture-backed benchmark. The next bottleneck is whether real human-reviewed outcome records can be attached, versioned, loaded, and scored without rewriting the calibration flow or weakening evidence boundaries.

## First Implemented Slice

The first M17 slice adds an `external benchmark definition` contract.

`run-human-calibration` suites can now reference benchmark definitions outside the suite file by using:

```json
{
  "benchmark_path": "benchmarks/example_benchmark.json",
  "synthetic_run_dir": "runs/example_run"
}
```

The referenced benchmark definition remains a JSON object containing:

- `benchmark_id`
- `research_stage`
- `evidence_type`
- `source`
- `human_panel`
- `human_outcomes`
- `thresholds`

The calibration artifact now preserves `human_benchmark.benchmark_definition_path` so external benchmark provenance remains visible in the result.

## Second Implemented Slice

The second M17 slice adds a `human-reviewed outcome mapping` contract so external benchmarks do not need to arrive already normalized as final `signals`.

`human_outcomes` can now provide either:

- `signals`
- `review_findings`

`review_findings` is the more realistic reviewer-coded shape. Each finding can describe a human outcome through fields such as:

- `objection`
- `trigger`
- `trust_concern`
- `category`
- `title`
- `observation`
- optional `terms`, `severity`, and `weight`

The calibration layer now maps those reviewer-coded findings into the same normalized signal contract used for scoring.

This keeps the scoring pipeline stable while allowing real study coding records to enter the system without requiring manual pre-conversion into final signal objects.

## Third Implemented Slice

The third M17 slice adds `browser-observed trace alignment` for prototype-validation calibration.

When a comparable run includes `observed_action_trace.json`, the calibration layer now extracts normalized synthetic signals directly from the trace artifact instead of depending only on summary-level report clusters.

The current extracted trace-alignment signals are intentionally narrow:

- `task_failure`
- `abandonment`
- `trust_gap` when the trace contains explicit permission, access, privacy, trust, or value-proof language

This keeps the extraction boundary tied to concrete observed task behavior rather than converting the browser trace into a broad free-form interpretation layer.

## Fourth Implemented Slice

The fourth M17 slice adds `external benchmark readiness projection`.

Each calibration artifact now carries a benchmark-level readiness projection that makes explicit:

- scope
- source coverage
- benchmark origin
- threshold gaps
- gate reasons
- boundary text

Suite summaries now also carry an aggregate readiness projection so external benchmark coverage can be reviewed as one readiness layer instead of only as a list of per-benchmark statuses.

The evidence-reliability layer now reads that projection directly, so product-facing review can show whether a calibration record is fixture-only, threshold-gapped, high-stakes gated, or externally benchmarked enough for scoped readiness claims.

## Repository Evidence

- `src/ai_validation_swarm/evaluation/human_calibration.py` now resolves `benchmark_path` entries from suite-relative JSON definitions and carries the resolved definition path into the output artifact.
- `fixtures/human_calibration/external_suite.json` now demonstrates the external suite form.
- `fixtures/human_calibration/benchmarks/inbox_coach_followup_real_study_sample.json` now demonstrates a `real_human_study` benchmark definition kept outside the suite.
- `tests/unit/test_human_calibration.py` now verifies external benchmark resolution and a `real_human_study` benchmark path that can reach `candidate_replacement_ready` for a scoped sample.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now also maps `human_outcomes.review_findings` into normalized calibration signals while preserving backward compatibility with `human_outcomes.signals`.
- `fixtures/human_calibration/external_review_findings_suite.json` plus `fixtures/human_calibration/benchmarks/inbox_coach_followup_review_findings_sample.json` now demonstrate reviewer-coded benchmark input instead of pre-normalized final signals.
- `tests/unit/test_human_calibration.py` now verifies that reviewer-coded findings are projected into `human_outcome_signals` and can still reach a scoped `candidate_replacement_ready` result.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now also extracts `task_failure`, `abandonment`, and bounded `trust_gap` signals from `observed_action_trace.json` when prototype-validation traces are present in a comparable run.
- `fixtures/human_calibration/runs/browser_trace_permission_dropoff_sample/` plus `fixtures/human_calibration/benchmarks/workspace_review_browser_trace_sample.json` now provide a checked-in browser-trace calibration example with reviewer-coded human task outcomes.
- `fixtures/human_calibration/external_browser_trace_suite.json` now demonstrates the external suite form for a browser-trace benchmark.
- `tests/unit/test_human_calibration.py` now verifies direct trace-signal extraction plus scoped browser-trace-to-human-outcome alignment.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now emits benchmark-level `readiness_projection` records plus suite-level aggregate readiness projection in `summary.json`.
- `fixtures/human_calibration/mixed_external_suite.json` now provides a checked-in aggregate-readiness example covering candidate, high-stakes-gated, and threshold-gap scopes.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects that readiness summary into evidence reliability so calibration review can expose external-benchmark gaps and threshold gaps explicitly.
- `tests/unit/test_human_calibration.py` now verifies aggregate readiness projection, and `tests/unit/test_saas_runtime.py` still passes with the richer evidence-reliability calibration records.

## Boundary

This slice does not prove broad external benchmark coverage.

It proves the calibration system can ingest benchmark definitions from external files, preserve benchmark provenance, accept reviewer-coded human outcomes, compare bounded browser-observed trace outcomes against reviewer-coded human task outcomes, and project scope-limited external readiness without changing the scoring pipeline.

Broad benchmark coverage, repeated real-study outcomes, and multi-market calibration remain later M17 work.
