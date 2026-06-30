# Milestone 24 Longitudinal Study and Panel Learning Design Spec

Status: `implemented`

## Purpose

Milestone 24 addresses the next launch-blocking bottleneck after persona-library explainability: the platform can now explain one panel and one calibration miss, but it still cannot learn cleanly across repeated studies, prototype revisions, or decision history without falling back to ad hoc manual comparison.

This milestone improves:

- decision prediction
- evidence quality
- calibration continuity
- scalable research throughput

It moves the platform closer to replacing interviewer-led work because real research programs depend on comparing what changed over time, not only reading one isolated run at a time.

## Architecture Alignment

1. Research bottleneck improved:
   repeated studies, prototype revisions, and saved decisions are still inspectable only as separate artifacts, so recurring trust gaps, contradictions, and adoption barriers remain labor-intensive to compare.
2. Platform dimension improved:
   decision prediction, evidence quality, calibration continuity, and throughput.
3. Replacement-work relevance:
   yes. A platform that cannot explain whether signals persist, resolve, or drift across iterations cannot credibly replace repeated interviewer-led screening work.
4. Why this work now:
   Milestone 23 now exposes explicit persona-library coverage, miss attribution, and panel explainability, so the next missing layer is longitudinal evidence learning rather than more one-run-only explanation.

## Milestone Scope

- support repeated studies and prototype iterations while preserving study, run, evidence, decision, export/share, and calibration lineage
- compare recurring objections, trust gaps, behavioral failures, and contradictions without overwriting older evidence
- project longitudinal learning through backend-owned comparison contracts instead of chat-only memory or page-local heuristics
- feed panel-learning signals back into future decision prediction while preserving auditability and evidence boundaries

## Planned Slices

### First Implemented Slice

The first M24 slice adds an `evidence-linked longitudinal comparison contract`.

The backend can now compare:

- repeated runs within the same study
- prototype revisions across the same project
- saved evidence views and decision-log outcomes across a study timeline
- attached calibration records across related run families

This slice defines durable identifiers, comparison windows, and artifact lineage before any product-facing trend summaries are trusted.

### Second Implemented Slice

Add `recurring signal and failure-pattern synthesis` so related studies can surface:

- recurring objections
- persistent trust gaps
- repeated task failures or abandonment points
- contradiction patterns that remain unresolved across iterations

This synthesis must preserve older evidence instead of collapsing everything into one latest-state summary.

### Third Implemented Slice

Add `panel learning projection` so longitudinal review can show:

- which segments repeatedly diverge
- which objections or barriers fade after a revision
- where prediction confidence improves, stalls, or drifts
- which decision changes were evidence-backed versus assumption-led

### Fourth Implemented Slice

Run the M24 completion review and decide whether the platform is ready to move into `Milestone 25`, or whether additional longitudinal evidence discipline is still required first.

## Initial Technical Boundary

- build on the existing evidence-query, workspace-shell snapshot, saved-evidence-view, decision-log, and calibration-record contracts
- keep longitudinal comparison backend-owned in Python runtime and artifact/query layers
- do not introduce chat-memory-only history or page-local trend inference as a substitute for explicit evidence lineage
- preserve synthetic-evidence boundaries, contradiction visibility, and human-validation-gap signaling in every longitudinal view

## Proposed Story Breakdown

1. `story.longitudinal.comparison_contract_and_lineage` - `implemented` - `5 SP`
   Outcome: repeated studies, runs, evidence views, and decisions gain one explicit comparison contract with durable lineage.

2. `story.longitudinal.recurring_signal_and_failure_pattern_synthesis` - `implemented` - `8 SP`
   Outcome: recurring objections, trust gaps, contradictions, and task failures become longitudinal evidence instead of manual artifact reading.

3. `story.longitudinal.panel_learning_and_decision_trend_projection` - `implemented` - `5 SP`
   Outcome: longitudinal review can explain what changed, what persisted, and where panel learning should affect later decisions.

4. `story.longitudinal.exit_review` - `implemented` - `3 SP`
   Outcome: Milestone 24 can be closed only after repeated-study learning is explicit enough to justify high-stakes boundary hardening in Milestone 25.

## Verification Plan

- unit or contract tests for longitudinal comparison payload assembly
- runtime tests showing repeated-study lineage persists through evidence and decision artifacts
- evidence-query or workspace-shell integration coverage for selected comparison windows and trend projection
- milestone review confirming longitudinal outputs stay evidence-linked rather than summary-only

## Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` now augments backend-owned evidence-query payloads with `longitudinal_comparison`, including comparison windows, same-study repeated runs, same-project neighboring studies, study-timeline entries, and calibration-lineage summaries.
- The same runtime now projects `audit_lineage.longitudinal_set` so source project/study context, same-study run ids, same-project study ids, and study-timeline entry ids stay attached to evidence review.
- The same runtime now persists a lightweight `longitudinal_focus` snapshot into saved evidence-view and decision-log summaries through `selected_evidence_context`, so study-timeline objects keep durable comparison-window context.
- The same runtime now projects backend-owned `recurring_signal_synthesis` into longitudinal comparison, including recurring pattern rollups, repeated-run observations, and linked study-timeline artifact ids instead of flattening longitudinal review into one latest-state summary.
- The same runtime now persists a lightweight `recurring_signal_focus` snapshot into saved evidence-view and decision-log summaries so recurring-pattern review focus survives beyond the current page session.
- The same runtime now projects backend-owned `panel_learning_projection` into longitudinal comparison, reading `panel_explainability` from run reports plus decision-log history to summarize repeated hotspot axes, persistent under-covered axes, barrier fade/emergence, confidence trend, and evidence-backed versus assumption-led decision changes.
- Decision-log creation now refreshes its own longitudinal snapshot after persistence, so the durable decision artifact can include itself in panel-learning and study-timeline trend projection instead of carrying a stale pre-create view.
- `specs/workspace_evidence_query_contract.md` now records the longitudinal comparison extension to the evidence-query contract, and `specs/workspace_shell_snapshot_contract.md` now records that the embedded shell evidence-query payload carries the same backend-owned longitudinal context.
- `tests/unit/test_saas_runtime.py` now verifies same-study repeated-run lineage, same-project neighboring-study lineage, recurring-pattern synthesis, panel-learning projection, decision-trend projection, and durable longitudinal/recurring/panel-learning focus persistence on saved evidence views and decision logs.

## Milestone Completion Review

Milestone 24 is now complete.

Repository evidence now proves:

- repeated-study comparison is backend-owned instead of page-local reconstruction
- recurring objections, trust gaps, failures, and contradictions stay attached to repeated runs and study-timeline artifacts instead of overwriting older evidence
- panel-learning and decision-trend projection now explain which segments repeatedly diverge, which barriers persist or fade, where confidence stalls or drifts, and whether decision changes were evidence-backed

Downstream milestone decision:

- `keep` `Milestone 25` next because the strongest remaining public-launch blocker is no longer repeated-study evidence continuity, but explicit regulated and high-stakes review boundaries
- `keep` `Milestone 26` after that because broader public launch still depends on both high-stakes review hardening and production-grade customer-facing operational readiness

This completion review does not widen the synthetic-evidence claim boundary.

It only confirms that repeated-study learning is explicit enough to justify moving into high-stakes boundary hardening as the next milestone.

## Boundary

This milestone does not prove replacement-grade learning over time.

It proves only that the repository is moving from one-run review toward evidence-linked longitudinal comparison and panel learning, which is a prerequisite for broader public launch discipline.
