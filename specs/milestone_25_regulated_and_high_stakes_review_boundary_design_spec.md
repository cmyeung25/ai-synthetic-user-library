# Milestone 25 Regulated and High-Stakes Review Boundary Design Spec

Status: `implemented`

## Purpose

Milestone 25 addresses the next launch-blocking bottleneck after longitudinal study learning: the platform can now explain what persists or changes across repeated studies, but it still lacks one explicit regulated and high-stakes review boundary for studies that touch finance, health, employment, legal, children, public safety, destructive execution, or credentialed flows.

This milestone improves:

- evidence quality
- auditability
- decision prediction discipline
- scalable research throughput for governed use cases

It moves the platform closer to replacing interviewer-led work because governed research programs need explicit safety, redaction, and reviewer-handoff boundaries before study outputs can be trusted operationally.

## Architecture Alignment

1. Research bottleneck improved:
   high-stakes studies still depend on ad hoc operator judgment even though the platform already exposes readiness gates, reviewer assignment, support handoff, and repeated-study longitudinal learning.
2. Platform dimension improved:
   evidence quality, auditability, safety boundary discipline, and throughput for governed research review.
3. Replacement-work relevance:
   yes. Without explicit regulated and high-stakes handling, the platform cannot credibly expand beyond bounded low-stakes synthetic research support.
4. Why this work now:
   Milestone 24 now makes repeated-study continuity explicit, so the next missing public-launch blocker is governed review handling rather than more longitudinal evidence plumbing.

## Milestone Scope

- formalize high-stakes and regulated study classification before execution, review, export, or sharing
- require explicit reviewer handoff, policy labeling, and bounded circulation for high-stakes evidence
- add redaction and compliance-ready audit-bundle projection without destroying evidence lineage
- ensure synthetic evidence cannot be presented as determinative proof in regulated contexts

## Planned Slices

### First Active Slice

Add `regulated study classification and pre-run boundary gating` so the platform can:

- classify finance, health, employment, legal, children, public-safety, destructive, or credentialed workflows as high-stakes
- require explicit boundary handling before execution proceeds
- keep that classification backend-owned across runtime, evidence review, and export/share boundaries

### Second Slice

Add `reviewer handoff and policy labeling` so governed studies can:

- require named reviewer responsibility
- carry policy labels and human-review-required notes through evidence, decisions, exports, and shares
- show why a study was allowed, blocked, or escalated

### Third Slice

Add `redaction and compliance-ready audit bundles` so governed studies can:

- redact sensitive fields or viewer-unsafe detail without losing why the redaction happened
- emit audit bundles that reconstruct classification, review, escalation, and distribution state
- preserve synthetic-evidence boundaries while making compliance review inspectable

### Fourth Slice

Run the M25 completion review and decide whether the platform is ready to move into `Milestone 26`, or whether additional governed-boundary hardening is still required first.

## Initial Technical Boundary

- build on the existing readiness-gate, launch-scope, decision-review, support-handoff, export/share, and workspace-audit contracts
- keep high-stakes classification, reviewer requirements, policy labels, and redaction state backend-owned in the Python runtime and persisted artifacts
- avoid page-local high-stakes inference or export-time warning banners as a substitute for explicit governed runtime state
- preserve synthetic-evidence boundaries, human-review-required labels, and append-only audit history in every governed flow

## Proposed Story Breakdown

1. `story.high_stakes.classification_and_pre_run_boundary_gate` - `implemented` - `3 SP`
   Outcome: high-stakes study classification becomes explicit and backend-owned before execution and sharing.

2. `story.high_stakes.reviewer_handoff_and_policy_labels` - `implemented` - `3 SP`
   Outcome: governed studies carry reviewer responsibility and policy labels across evidence, decisions, exports, and shares.

3. `story.high_stakes.redaction_and_compliance_audit_bundle` - `implemented` - `5 SP`
   Outcome: governed studies can redact and package compliance-ready audit evidence without breaking lineage.

4. `story.high_stakes.exit_review` - `implemented` - `2 SP`
   Outcome: Milestone 25 can close only after governed-boundary handling is explicit enough to justify scaled public launch readiness work in Milestone 26.

## Verification Plan

- runtime tests for high-stakes classification, gate enforcement, and governed export/share restrictions
- contract tests for policy labels, reviewer handoff state, and redaction/audit-bundle projection
- study-history and audit-surface tests proving governed decisions remain reconstructable
- milestone review confirming regulated handling stays backend-owned rather than warning-banner-only

## Repository Evidence

- `specs/milestone_25_regulated_and_high_stakes_review_boundary_design_spec.md` now records the accepted M25 scope, technical boundary, story breakdown, and current slice status.
- `src/ai_validation_swarm/saas/runtime.py` now classifies study intent, desired output, first task, and artifact references into backend-owned `regulated_review_boundary` state for finance, health, employment, legal, children, public-safety, destructive, and credentialed workflows.
- the same runtime now blocks validation-job submission when a linked study is regulated/high-stakes and lacks explicit governed boundary acknowledgement, instead of relying on page-local warning text.
- the same runtime now projects that governed boundary into study summaries, workspace support diagnostics, validation-job metadata, export manifests, and share payloads so runtime, support, export, and share surfaces read one backend-owned boundary contract.
- `src/ai_validation_swarm/saas/api.py` now accepts `study_id` on `/api/v1/support-diagnostics`, letting support surfaces load the same governed submission gate before a run exists.
- `specs/workspace_project_study_contract.md` now records `regulated_review_boundary` as part of the study surface and study-to-run linkage contract.
- `tests/unit/test_saas_runtime.py` now verifies blocked regulated-study submission, explicit acknowledgement-based allow execution, support diagnostics boundary projection, and regulated boundary propagation into export/share artifacts.
- `src/ai_validation_swarm/saas/runtime.py` now persists study-level governed reviewer assignment, projects backend-owned `governed_review` state into evidence query, evidence views, decision logs, export manifests, share payloads, and support diagnostics, and blocks partner-facing share creation when reviewer responsibility is missing or escalated.
- the same runtime now lets regulated/high-stakes decision logs inherit default reviewer assignment from the study-level governed handoff and blocks final decision approval until named governed reviewer responsibility exists.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/studies/{study_id}/governed-review-assignment`.
- `tests/unit/test_saas_runtime.py` now verifies governed reviewer assignment mutation, study-activity audit history, evidence-query governed policy projection, decision-review inheritance, export refresh, and share gating/release after governed reviewer assignment.
- `src/ai_validation_swarm/saas/runtime.py` now persists study-level governed redaction policy, projects backend-owned `governed_redaction` state into evidence query, evidence views, decision logs, support diagnostics, export manifests, and share payloads, and blocks partner-facing share creation until active viewer-safe redaction exists.
- the same runtime now writes `compliance_audit_bundle.json` for export bundles, share bundles, and governed support snapshots, preserving classification, reviewer, redaction, readiness, circulation, and audit-history reconstruction without exposing raw internal reasoning as human proof.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/studies/{study_id}/governed-redaction`.
- `tests/unit/test_saas_runtime.py` now verifies governed redaction mutation, share redaction application, compliance-audit-bundle persistence, and study-activity audit history.
- Milestone 14 already safety-gates credentialed, destructive, external, payment, token, and transfer browser behavior before synthesis.
- Milestone 19 already blocks high-stakes human-review-required evidence from public share creation.
- Milestone 22 already exposes reviewer assignment, support handoff, and append-only governance history that M25 can reuse for governed review boundaries.
- Milestone 24 already makes repeated-study learning explicit enough that governed review can now reason over persisted evidence continuity instead of isolated one-run output.

## Boundary

This milestone does not prove replacement-grade reliability in regulated or high-stakes domains.

It only formalizes the governed review boundary required before broader public launch readiness can be evaluated responsibly.

## Completion Review

- strongest current platform capability:
  one backend-owned study, evidence, export, share, support, and audit boundary now carries explicit regulated/high-stakes classification, reviewer responsibility, viewer-safe redaction, and compliance reconstruction without relying on page-local warnings.
- most important remaining bottleneck:
  broader public launch still lacks one backend-owned customer-facing claim and benchmark-disclosure boundary for ordinary teams outside the controlled design-partner loop.
- downstream milestone decision:
  keep `Milestone 26` next and begin it now.
- why M25 can close:
  the implemented runtime and test coverage now satisfy all three functional exit criteria from the roadmap:
  explicit governed handling before execution or sharing, durable safety/calibration labels on distributed bundles, and support/audit reconstruction for blocked versus allowed versus escalated governed flows.
