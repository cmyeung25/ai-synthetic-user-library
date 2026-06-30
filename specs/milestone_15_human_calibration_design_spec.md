# Milestone 15 Human Calibration and Replacement-Readiness Design Spec

Status: `implemented`

## Purpose

Milestone 15 closes the gap between synthetic repeatability and human-outcome calibration.

The platform now has a fixture-backed human calibration workflow that can attach manually reviewed human outcome signals to comparable synthetic runs, score prediction alignment, preserve panel deltas, and emit replacement-readiness status by research stage and evidence type.

## Alignment Check

- Research bottleneck improved: synthetic findings were repeatable but not compared against human-reviewed outcomes.
- Primary improvements: `calibration`, `decision prediction`, `evidence quality`, and `auditability`.
- Replacement-workflow relevance: teams can now see where synthetic evidence aligns or diverges from human-reviewed outcomes instead of treating repeated synthetic signals as proof.
- Boundary: the checked-in benchmark is a fixture-backed human review dataset. It validates the calibration pipeline and contract, not broad market replacement-readiness.

## Implemented Contract

The implemented calibration artifact is `human_calibration.json` with contract version `human-calibration/v1`.

It contains:

- attached benchmark identity and source type
- comparable run identity and evidence type
- human outcome signals
- extracted synthetic prediction signals
- precision, recall, F1, and alignment score
- synthetic panel versus human panel delta
- replacement-readiness status and thresholds
- synthetic-evidence boundary text

The default suite lives at `fixtures/human_calibration/suite.json`.

The CLI entrypoint is:

```powershell
$env:PYTHONPATH='src'
python -m ai_validation_swarm.cli.main run-human-calibration --suite fixtures/human_calibration/suite.json
```

## Architecture Boundary

- `src/ai_validation_swarm/evaluation/human_calibration.py` owns benchmark loading, signal extraction, scoring, artifact writing, markdown summary rendering, and suite execution.
- `src/ai_validation_swarm/saas/evidence_query.py` remains the backend-owned evidence reliability layer and now projects attached `human_calibration.json` records into `evidence_reliability.calibration_records`.
- No SaaS database migration is required for v1. Calibration records are appendable run artifacts, consistent with the current file-backed evidence model.

## Readiness Status Rules

- `calibrated_fixture_only`: fixture-backed human review meets configured thresholds, but is not replacement-grade proof.
- `directional_calibration_ready`: real human study data is attached and meets directional thresholds, but not replacement thresholds.
- `candidate_replacement_ready`: real human study data meets replacement-readiness thresholds for the specified research stage and evidence type.
- `high_stakes_human_review_required`: the benchmark is marked high-stakes and therefore remains gated regardless of alignment score.
- `not_ready`: attached outcomes do not meet configured thresholds.

Replacement-readiness is scoped to the benchmark's `research_stage` and `evidence_type`.
The platform must not claim blanket replacement-readiness from one calibrated benchmark.

## Acceptance Evidence

- `tests/unit/test_human_calibration.py` verifies benchmark attachment, accuracy scoring, fixture-only readiness boundaries, suite summary writing, and evidence reliability projection.
- `run-human-calibration` CLI smoke verifies that the checked-in suite produces a `summary.json` archive.
- Evidence query reliability records now include `human_benchmark_alignment` when a completed run has an attached `human_calibration.json`.

## Remaining Boundary

The platform can now perform human calibration when benchmark outcomes are attached.
It now also supports externally referenced benchmark definition files through suite-level `benchmark_path` entries, but it still needs broader external benchmark coverage before claiming replacement-grade reliability across markets, stages, or high-stakes domains.
