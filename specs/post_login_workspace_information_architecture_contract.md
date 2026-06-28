# Post-Login Workspace Information Architecture Contract

Status: `accepted_for_future_implementation`

Owner: `platform-development-chief`

Date accepted: `2026-06-29`

## Purpose

This contract records the information architecture for the logged-in product surface.

The logged-in experience must behave as a `study-first research workspace`, not a generic dashboard, prompt playground, job monitor, or admin console.

The primary product object is `Study`.
`Run`, `Job`, `Prompt`, `Export`, and `Dashboard` are secondary objects that exist inside or around a study.

## Alignment Check

- Research bottleneck improved: users need a durable path from research intent to evidence review, comparison, decision logging, and bounded sharing without losing study context.
- Primary improvements: `evidence quality`, `auditability`, `decision prediction`, and `scalable research throughput`.
- Replacement-workflow relevance: the IA keeps the product operating loop close to interviewer-led research work: frame the question, clarify context, confirm the plan, run, review evidence, compare, decide, and share with evidence boundaries.
- Boundary: this IA does not itself prove behavioral realism or replacement-readiness. Milestone 15 calibration remains the core next research-signal milestone.

## Product Object Hierarchy

The logged-in workspace should teach this hierarchy through navigation and default route behavior:

```text
Workspace
|-- Home / Studies
|   |-- Continue latest study
|   |-- New study
|   |-- Recent studies
|   `-- Needs attention
|-- Project
|   |-- Project overview
|   |-- Studies
|   |-- Decisions
|   `-- Shared outputs
|-- Study
|   |-- Study workspace
|   |-- Plan
|   |-- Runs
|   |-- Evidence
|   |-- Compare
|   |-- Decisions
|   `-- Share / Export
|-- Evidence Library
|   |-- Saved evidence views
|   |-- Cross-run comparisons
|   |-- Calibration records
|   `-- Human-validation gaps
|-- Activity / Audit
|   |-- Study activity
|   |-- Workspace audit
|   `-- Support history
`-- Settings
    |-- Members
    |-- Billing / quota
    |-- API tokens
    `-- Retention / governance
```

## Default Landing Rules

1. If the workspace has an active study, post-login should land in `Study Workspace` for the latest active study.
2. The landing state should show the latest run, open decision, evidence gaps, and the next useful research action.
3. If the workspace has no study, post-login should land in `New Study` with conversational intake.
4. If the user enters through a deep link, the target route should open directly while preserving project and study context in the shell.
5. `/app/jobs/{job_id}` should route to evidence review for the selected job, not to a raw job monitor, while keeping the owning study visible when linkage exists.

## Primary Navigation

The default logged-in navigation should prioritize research work:

- `New Study`
- `Studies`
- `Evidence`
- `Decisions`
- `Activity`

The first screen must not ask users to choose internal mode taxonomy, run schemas, or workflow-builder concepts before they can express the research problem.

## Secondary Navigation

Governance and operational controls must exist, but they should not dominate the research workspace:

- `Workspace settings`
- `Support`
- `Billing`
- `API tokens`
- `Retention / governance`

These areas are secondary because they support research execution rather than define the user's main mental model.

## Route Ownership

The eventual framework-owned route model should follow these semantics:

| Route | Primary surface | IA rule |
| --- | --- | --- |
| `/app/workspace` | Home / Studies or continue latest study | Do not become a generic KPI dashboard. |
| `/app/new-study` | New Study | Conversational intake, progressive clarification, explicit plan confirmation. |
| `/app/projects/{project_id}` | Project overview | Show project context, studies, decisions, and shared outputs. |
| `/app/studies/{study_id}` | Study Workspace | Default study operating surface. |
| `/app/studies/{study_id}/plan` | Plan | Confirmed or draft research plan with evidence-boundary notes. |
| `/app/studies/{study_id}/runs` | Runs | Study-scoped run timeline, not global job management. |
| `/app/studies/{study_id}/evidence` | Evidence Review | Evidence-first review, replay lineage, contradictions, calibration state. |
| `/app/studies/{study_id}/compare` | Compare | Cross-run, segment, artifact, or study-revision comparison. |
| `/app/studies/{study_id}/decisions` | Decisions | Decision logs with supporting evidence and human-validation gaps. |
| `/app/jobs/{job_id}` | Evidence Review deep link | Resolve job to study context when available. |
| `/app/evidence-views/{view_id}` | Saved Evidence View | Durable evidence slice with provenance. |
| `/app/decision-logs/{decision_log_id}` | Decision Review | Durable working judgment with boundary language. |
| `/app/export-bundles/{export_id}` | Export Review | Distribution artifact after study work. |
| `/app/share-bundles/{share_id}` | Share Review | Viewer-safe boundary-preserving share state. |
| `/app/activity` | Activity / Audit | Workspace and study activity history. |
| `/app/settings/*` | Settings | Members, billing, quota, tokens, retention, governance. |
| `/app/support/*` | Support | Support snapshots and support history. |

## Active-Route Shell Rule

The final product surface should not behave like one long one-page app.

Only one primary research surface should be expanded at a time:

- New Study
- Study Workspace
- Evidence Review
- Compare
- Decisions
- Activity
- Settings

Other areas should be reachable through navigation, summary cards, deep links, or drawers.

Dense study context is acceptable.
Stacking every workspace, study, evidence, settings, support, export, and debug region into one continuous page is not acceptable for the final logged-in IA.

## Evidence Boundary Requirements

Every primary route must preserve these product-surface rules:

- keep `study` as the primary context
- keep synthetic-evidence boundary text visible where findings are interpreted
- keep contradiction, missing-context, and `human_validation_gap` states visible in default review paths
- keep replay lineage and audit lineage close to evidence claims
- keep comparison first-class rather than treating each run as an isolated output
- keep decision logs as durable product outcomes, not optional report notes

## What Waits

These surfaces should not be prioritized before the IA is implemented around the study-first loop:

- broad executive dashboards
- marketing-style success metrics
- workflow-builder or node-graph setup
- global job-management-first pages
- admin settings as the post-login landing experience
- report-only output flows that bypass comparison and decision logging

## Implementation Acceptance Criteria

Future implementation can count this IA as complete only when:

- post-login landing follows the active-study, no-study, and deep-link rules
- the shell has route-owned page state instead of one always-expanded long page
- primary nav matches the research loop rather than admin or job management
- secondary settings/support/billing/API surfaces stay available without becoming the main landing model
- `/app/jobs/{job_id}` deep links preserve evidence review plus study context
- automated browser smoke includes acceptance gates for no critical overlap, no text occlusion, and no fixed or sticky layer blocking primary research actions
- tests or source checks prove the default route order keeps research pages before settings, support, and debug surfaces

## Relationship To Milestones

This IA is accepted as a planned product-surface workstream after the first real-user workspace page layer.

It should be implemented alongside continued framework-host decomposition, but it must not displace Milestone 15 human calibration as the next core research-signal milestone.
