# Milestone 23 Persona Library and Human Difference Calibration Design Spec

Status: `implemented`

## Purpose

Milestone 23 addresses the main post-governance bottleneck before scaled public launch readiness: the platform still cannot explain persona-library coverage and human-difference gaps strongly enough to justify broader confidence in panel composition.

This milestone improves:

- behavioral realism
- decision prediction
- evidence quality
- calibration explainability

It moves the platform closer to replacing interviewer-led work because panel misses can no longer stay hidden behind generic persona counts or opaque selection metadata.

## Architecture Alignment

1. Research bottleneck improved:
   persona and panel coverage are still implicit, so teams cannot tell whether a miss came from missing human differences, facilitator behavior, stimulus interpretation, or synthesis/ranking.
2. Platform dimension improved:
   behavioral realism, decision prediction, evidence quality, and calibration.
3. Replacement-work relevance:
   yes. A system that cannot explain which humans it is simulating well, and which it is not, cannot credibly replace interviewer-led screening work.
4. Why this work now:
   Milestone 22 hardened governance, but public-launch sequencing is still blocked by research-signal weakness rather than workflow control.

## Milestone Scope

- expand reusable persona-library coverage while preserving concept-neutral human difference axes
- make human-difference coverage queryable and explainable rather than implicit in narrative persona artifacts only
- attribute calibration misses across persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking
- improve panel-selection explainability without baking current study conclusions into reusable persona core

## First Implemented Slice

The first M23 slice adds a `persona coverage and human-difference summary` foundation.

The repository now supports:

- library summaries that report required human-difference axes, per-axis presence, per-axis bucket coverage, and explicit coverage gaps
- supporting behavior-model coverage checks for:
  - `relational_defense_model`
  - `communication_behavior_model`
  - `behavior_generation_rules`
- metadata-index persistence for every populated `human_difference_axes.*` field through `persona_trait_assignments`

This slice is intentionally foundational. It does not yet explain calibration misses across full benchmark deltas, but it creates the durable coverage contract needed for later panel-selection and calibration-attribution work.

## Planned Remaining Slices

### Second Implemented Slice

The second M23 slice adds `calibration miss attribution`.

Calibration artifacts can now distinguish whether a miss most likely came from:

- persona coverage gap
- facilitator behavior gap
- stimulus interpretation gap
- synthesis/ranking gap

This attribution is explicitly heuristic. It is meant for calibration triage and improvement planning, not as final causal proof.

### Third Implemented Slice

The third M23 slice adds `panel composition explainability`.

Selected panels can now report:

- which human-difference axes were intentionally covered
- which axes remain thin or missing
- where high similarity still clusters
- why a given persona was included beyond a generic filter match

### Fourth Slice

Run the M23 completion review and decide whether the platform is ready to move into longitudinal learning as `Milestone 24`, or whether additional persona-library calibration work is still required first.

## Repository Evidence

- `src/ai_validation_swarm/personas/analysis.py` now emits `human_difference_axis_summary`, including per-axis coverage status, bucket distribution, behavior-model coverage, and explicit gap records.
- `src/ai_validation_swarm/saas/metadata_store.py` now persists every populated `human_difference_axes.*` value into `persona_trait_assignments`, preserving trait provenance for later explainable panel composition.
- `src/ai_validation_swarm/cli/main.py` now surfaces the new human-difference coverage summary in `summarize-personas`.
- `tests/unit/test_persona_analysis.py` now verifies both the legacy summary path and the new human-difference coverage/gap contract.
- `tests/unit/test_metadata_store.py` now verifies that human-difference axes are persisted into the metadata index as durable trait assignments.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now emits `miss_attribution`, including likely-cause records for persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking gaps when calibration misses exist.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects that attribution into product-facing `calibration_records` as `calibration_miss_attribution` instead of leaving the page layer to infer it locally.
- `tests/unit/test_human_calibration.py` now verifies both a fully aligned benchmark case and a deliberately mismatched prototype-validation case that surfaces all four likely-cause classes.
- `src/ai_validation_swarm/sampling/engine.py` now emits backend-owned panel explainability records, including selected-vs-eligible human-difference coverage, under-covered axis projection, similarity hotspots, and per-persona inclusion rationale.
- `src/ai_validation_swarm/validation/runner.py` now persists that explainability into `sampling.json`, while `src/ai_validation_swarm/reporting/artifacts.py` now projects the same backend-owned panel rationale and explainability into `report.json`.
- `tests/unit/test_sampling.py` now verifies under-covered axis projection, similarity hotspot detection, and per-persona inclusion rationale.
- `tests/integration/test_validation_run.py` now verifies that validation runs persist `panel_rationale` and `panel_explainability` through report artifacts.

## Story Breakdown

1. `story.persona_library.coverage_summary_and_gap_contract` - `implemented` - `5 SP`
   Outcome: persona-library coverage and human-difference gaps become explicit in summary artifacts and metadata trait assignments.

2. `story.persona_library.calibration_miss_attribution` - `implemented` - `8 SP`
   Outcome: calibration records explain likely miss origin instead of collapsing all misses into one alignment delta.

3. `story.persona_library.panel_explainability_and_gap_projection` - `implemented` - `5 SP`
   Outcome: panel composition can explain covered and under-covered human-difference axes plus major similarity hotspots.

4. `story.persona_library.exit_review` - `implemented` - `3 SP`
   Outcome: Milestone 23 can be closed only after coverage explainability and attribution are usable enough to support Milestone 24 sequencing.

## Completion Review

Milestone 23 is now complete because the repository can:

- summarize persona-library human-difference coverage and explicit gaps
- persist human-difference trait provenance for later explainable panel composition
- attribute likely calibration misses across persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking
- project backend-owned panel explainability into sampling and report artifacts, including under-covered axes, similarity hotspots, and per-persona inclusion rationale

Current milestone review decision:

- `keep` `Milestone 24` next because the main remaining reliability bottleneck is no longer one-run panel explainability, but evidence-linked learning across repeated studies and prototype revisions
- `keep` `Milestone 25` after that because high-stakes boundary hardening still depends on stronger longitudinal evidence discipline
- `keep` `Milestone 26` as the broader public-launch gate because calibration, governance, longitudinal learning, and high-stakes boundaries still need to converge before wider self-serve claims

Immediate next milestone:

- `Milestone 24: Longitudinal Study and Panel Learning`

## Verification

- `python -m unittest tests.unit.test_persona_analysis tests.unit.test_metadata_store tests.unit.test_persona_validator`
- `python -m unittest tests.unit.test_saas_runtime tests.unit.test_human_calibration`

## Boundary

This slice does not prove that persona coverage is already sufficient for public launch.

It proves only that the repository now exposes an explicit, durable, and test-covered contract for human-difference coverage and gap visibility, which is a prerequisite for stronger panel calibration and public-launch discipline.
