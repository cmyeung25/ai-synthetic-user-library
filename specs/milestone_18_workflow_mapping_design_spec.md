# Milestone 18 Workflow Mapping Design Spec

Status: `implemented`

## Purpose

Milestone 18 starts by turning `workflow_mapping` into a first-class discovery interview mode.

The research bottleneck is incomplete discovery coverage. The platform can already discover whether a problem is real, explore root cause, and reconstruct decisions, but it still lacked a dedicated way to map the current workflow itself: step sequence, handoffs, fragmentation, workaround chains, switching cost, and responsibility gaps.

## First Implemented Slice

The first M18 slice adds a `workflow_mapping` mode contract across CLI, runtime, prompt, and observer paths.

The implemented coverage contract now requires:

- `recent_behaviour`
- `workflow_sequence`
- `handoff_boundary`
- `fragmentation_point`
- `current_workaround`
- `switching_cost`
- `responsibility_gap`

The runtime now treats `workflow_mapping` as a real interview mode rather than a roadmap-only placeholder:

- CLI accepts `workflow_mapping`
- facilitator runtime validates it as a supported mode
- observer runtime inherits the same mode contract
- the facilitator prompt now teaches the LLM to stay in current-state workflow evidence instead of drifting into concept evaluation
- the runtime blocks premature closure until workflow coverage is complete

## Repository Evidence

- `src/ai_validation_swarm/cli/main.py` now accepts `workflow_mapping` in both facilitated and observer interview entrypoints.
- `src/ai_validation_swarm/facilitator/runtime.py` now defines workflow-mapping coverage requirements, gap instructions, and closure-gate enforcement.
- `src/ai_validation_swarm/prompts/facilitator-interview/v2.md` now includes workflow-mapping interviewing rules.
- `src/ai_validation_swarm/prompts/facilitator-synthesis/v2.md` now includes workflow-mapping synthesis rules.
- `src/ai_validation_swarm/prompts/facilitator-quality-evaluator/v2.md` now audits workflow-mapping-specific failure modes.
- `tests/unit/test_facilitator_runtime.py` now verifies a full workflow-mapping runtime path with complete coverage.
- `tests/unit/test_observer_runtime.py` now verifies that workflow_mapping reaches facilitator and quality contexts in the observer path.

## Second Implemented Slice

The second M18 slice turns workflow-mapping output into richer discovery evidence rather than leaving it as generic interview prose.

The implemented evidence layer now adds:

- a structured `workflow_map` projection inside `insight_report.json`
- workflow-map-aware evidence-query parsing and replay-style review steps for workflow sequence, handoff, fragmentation, workaround, switching-cost, and responsibility-gap evidence
- saved evidence view and decision-log linkage that persists selected workflow evidence context instead of dropping that discovery signal at collaboration time

This means workflow evidence now survives into the review layer in a more product-usable way:

- the backend can expose workflow-map artifacts as queryable evidence
- saved evidence views can remember whether the selected evidence focused on workflow fragmentation
- decision logs can inherit the same workflow evidence focus and signal lineage

## Additional Repository Evidence

- `src/ai_validation_swarm/facilitator/runtime.py` now writes a structured `workflow_map` projection into workflow-mapping insight reports.
- `src/ai_validation_swarm/saas/evidence_query.py` now recognizes workflow-mapping interview artifacts and workflow-map synthesis artifacts as richer queryable evidence with workflow-aware tags and replay-style steps.
- `src/ai_validation_swarm/saas/runtime.py` now persists selected workflow evidence context into saved evidence views and decision logs.
- `tests/unit/test_facilitator_runtime.py` now verifies workflow-map evidence projection and evidence-query consumption for a workflow-mapping interview run.
- `tests/unit/test_saas_runtime.py` now verifies workflow-map evidence context is carried into saved evidence views and decision logs.

## Milestone Completion Review

Milestone 18 is now complete.

Implemented capability now proves:

- discovery coverage includes `pain_point_discovery`, `explore_root_cause`, `decision_reconstruction`, and `workflow_mapping`
- workflow-mapping runs produce richer queryable workflow evidence instead of only prose summary artifacts
- workflow evidence can persist into saved evidence views and decision logs for later study review

Current platform state after completion:

- strongest improvement: current-state discovery work can now preserve workflow fragmentation, handoff, switching-cost, and responsibility-gap evidence as reviewable research signal
- most important remaining bottleneck: customer-facing distribution still lacks a calibrated readiness gate even though reliability and calibration records now exist
- sequencing decision: keep Milestone 19 next, because the missing capability is not more discovery coverage but market-facing evidence-boundary control

## Boundary

Milestone 18 completion does not claim human proof.

Discovery coverage is now more complete, but the platform still needs Milestone 19 readiness gates before exports, shares, and design-partner circulation can rely on calibrated customer-facing evidence boundaries.
