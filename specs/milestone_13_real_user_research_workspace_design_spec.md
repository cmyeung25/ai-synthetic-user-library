# Milestone 13 Design Spec: Real User Research Workspace

## Status

Implemented.

## Product Intent

Milestone 13 turns the proven Stage 15 hosted shell into the first real user-facing research workspace. The product must stop feeling like an engineering console that happens to contain product controls. It should let a researcher, founder, or product lead start and review a study without learning internal run schemas, mode taxonomy, or workflow-builder concepts.

The research bottleneck is activation plus disciplined evidence review:

- users need to express a research question with low setup friction
- users need an explicit plan confirmation before execution
- users need evidence-first review with replay, comparison, calibration, and human-validation gaps visible
- users need durable saved views and decision logs instead of report-only output

## Non-Goals

- Do not create a marketing landing page.
- Do not introduce a workflow-builder or node graph.
- Do not move evidence reliability, contradiction review, calibration, or lineage scoring into frontend heuristics.
- Do not claim synthetic evidence is human market proof.
- Do not block Milestone 14 browser-driven prototype work with a large frontend rewrite.

## Canonical Pages

### 1. New Study

Route intent:

- `/app/new-study`
- `/app/workspace` may still render this as the default first panel until route expansion is implemented.

Purpose:

- capture plain-language research intent
- collect only the next useful missing context
- attach artifacts without forcing users to understand artifact schemas
- infer the likely research mode and evidence classes
- require explicit plan confirmation before execution

Required visible concepts:

- `Ask`
- `Clarify`
- `Confirm Plan`
- synthetic-evidence boundary
- known human-validation gaps
- advanced controls collapsed behind a secondary path

Must not:

- require mode selection before research intent
- expose `brief_path`, `persona_dir`, `provider_name`, or `run_root` as the primary mental model
- make run/job IDs the first-screen object

### 2. Study Workspace

Route intent:

- `/app/studies/{study_id}`

Purpose:

- keep the selected study as the primary product object
- show run status, latest activity, saved evidence views, decision logs, exports/shares, and next research action
- let the user continue a study without reconstructing context from raw artifacts

Required visible concepts:

- current project and study
- study question and first task
- latest run status
- activity timeline
- collaboration objects
- next action
- synthetic boundary reminder

Must not:

- default to a generic tenant dashboard
- make governance settings dominate the research flow
- hide blocked, failed, or inconclusive states

### 3. Evidence Review

Route intent:

- `/app/jobs/{job_id}`
- future route expansion may add `/app/studies/{study_id}/evidence`.

Purpose:

- review selected evidence before summary
- inspect replay and source detail
- compare nearby artifacts and cross-run candidates
- show stability, contradiction, missing context, calibration records, and audit lineage from the Milestone 12 contract
- convert evidence into saved views and decision logs

Required visible concepts:

- selected evidence
- replay focus
- cross-run comparison
- reliability status
- calibration records
- `human_validation_gap`
- saved evidence view
- decision log
- share/export with boundary

Must not:

- hide uncertainty behind polished prose
- present stability labels as human validation
- let users share conclusions without synthetic-boundary language

## Architecture Boundaries

- `frontend/workspace_shell_app` owns real page composition and visual hierarchy.
- `demo/workspace_ui_shared/workspace_shell_app.mjs` remains the shared controller for state mutation and runtime actions during this migration.
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` remains the page-facing projection boundary for backend shell and evidence state.
- `src/ai_validation_swarm/saas/runtime.py` and `src/ai_validation_swarm/saas/evidence_query.py` remain the backend source of truth for workspace shell snapshots and evidence reliability.
- `frontend/workspace_shell_app` must not duplicate reliability scoring, route hydration, or run execution logic.

## Component Ownership Target

Milestone 13 should progressively replace one large Stage 15 shell host with framework-owned product sections:

- `NewStudyPage`
- `StudyWorkspacePage`
- `EvidenceReviewPage`
- `RealUserWorkspaceNav`
- small shared summary/card primitives only where they do not duplicate the existing design-system contracts

During migration, compatibility IDs used by the Stage 15 controller may remain in the DOM so existing tests and hosted smoke flows keep working.

## Visual Direction

Use the existing Moss editorial research-lab direction, but make the first screen feel like a product a real user can operate:

- study-first hierarchy
- restrained serif headings with technical UI text
- dense but calm evidence panels
- visible risk and validation-gap color language
- no purple AI gradients, no generic card dashboard, no empty marketing hero

## Acceptance Criteria

- The hosted React app exposes a real-user page layer for `New Study`, `Study Workspace`, and `Evidence Review`.
- The first-screen product experience is the research workflow, not workspace settings or debug traces.
- New Study keeps plain-language intent and plan confirmation visible before run execution.
- Study Workspace keeps study context, activity, collaboration objects, and next action visible.
- Evidence Review renders Milestone 12 reliability, calibration, audit lineage, contradiction, and human-validation-gap concepts as first-class page requirements.
- Shared shell controller compatibility is preserved while components are migrated.
- Browser layout acceptance gates remain active for critical actions and evidence panels.
- Tests prove the page model preserves the default loop `Ask -> Clarify -> Confirm Plan -> Run -> Review Evidence -> Compare -> Decide -> Share With Boundary`.

## Verification Plan

- Unit-test the shared Milestone 13 page model.
- Source-test the React host for the three canonical page sections and M13 data attributes.
- Keep existing Stage 15 shared-controller tests green.
- Build `frontend/workspace_shell_app`.
- Run hosted smoke once the real-user page layer is wired into the built app.

## Completion Bar

Milestone 13 is complete only when all four tracked stories are implemented:

- New Study page
- Study Workspace page
- Evidence Review page
- component ownership cleanup

The first implementation slice can mark individual stories `in_progress`, but not the milestone complete.
