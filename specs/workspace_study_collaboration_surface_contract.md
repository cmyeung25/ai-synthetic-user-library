# Workspace Study Collaboration Surface Contract

## Purpose

This document defines the first durable Milestone 11 collaboration layer inside a study workspace:

- `saved evidence views`
- `decision logs`
- study-scoped collaboration artifact materialization
- API and shared-shell expectations for loading, creating, and selecting those objects

The contract exists to keep evidence review state and product decisions durable inside study context instead of forcing operators to reconstruct comparison state from raw runs each time.

## Why this contract exists

Research bottleneck improved:

- operators can already run studies and inspect evidence, but they still lose review focus and decision history across repeated follow-up work

What this improves:

- `evidence_quality`
- `auditability`
- `scalable_research_throughput`

Why it matters now:

- Milestone 11 is the first real user-facing product layer
- that layer needs durable study collaboration before broader admin expansion is worth the complexity

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/evidence-views`
- `GET /api/v1/evidence-views`
- `GET /api/v1/evidence-views/{evidence_view_id}`
- `POST /api/v1/decision-logs`
- `GET /api/v1/decision-logs`
- `GET /api/v1/decision-logs/{decision_log_id}`

## Object intent

### Saved evidence view

Saved evidence view preserves one evidence-review slice inside a study.

Minimum fields:

- `evidence_view_id`
- `workspace_id`
- `project_id`
- `study_id`
- `job_id`
- `run_id`
- `title`
- `note`
- `query_text`
- `active_family`
- `sort_by`
- `selected_result_id`
- `selected_replay_step_id`
- `selected_comparison_run_id`
- `payload_path`
- `created_by_user_id`
- `created_at`
- `updated_at`

### Decision log

Decision log preserves one study decision and its evidence linkage.

Minimum fields:

- `decision_log_id`
- `workspace_id`
- `project_id`
- `study_id`
- `job_id`
- `run_id`
- `evidence_view_id`
- `title`
- `decision_summary`
- `rationale`
- `selected_result_id`
- `selected_comparison_run_id`
- `payload_path`
- `created_by_user_id`
- `created_at`
- `updated_at`

## Creation rules

### `POST /api/v1/evidence-views`

Request body:

```json
{
  "study_id": "study_123",
  "job_id": "job_123",
  "title": "Trust blockers review",
  "note": "Preserve the comparison-focused evidence slice.",
  "query_text": "trust",
  "active_family": "trace",
  "sort_by": "relevance",
  "selected_result_id": "query-run_report",
  "selected_replay_step_id": "response-02",
  "selected_comparison_run_id": "run_456"
}
```

Response:

```json
{
  "evidence_view": {
    "evidence_view_id": "evidence_view_123",
    "study_id": "study_123",
    "job_id": "job_123",
    "title": "Trust blockers review",
    "has_replay_focus": true,
    "has_comparison_focus": true
  }
}
```

Creation constraints:

1. caller must be in a submitter-capable workspace role
2. `study_id` must be visible inside the authenticated workspace
3. if `job_id` is supplied, it must belong to the same study and be `completed`
4. saved view selection state must stay bounded to workspace-visible evidence

### `POST /api/v1/decision-logs`

Request body:

```json
{
  "study_id": "study_123",
  "job_id": "job_123",
  "evidence_view_id": "evidence_view_123",
  "title": "Do not ship yet",
  "decision_summary": "Trust blockers still dominate the study evidence.",
  "rationale": "The same hesitation appears across replay and cross-run comparison.",
  "selected_result_id": "query-run_report",
  "selected_comparison_run_id": "run_456"
}
```

Response:

```json
{
  "decision_log": {
    "decision_log_id": "decision_log_123",
    "study_id": "study_123",
    "evidence_view_id": "evidence_view_123",
    "decision_summary": "Trust blockers still dominate the study evidence.",
    "has_linked_evidence_view": true,
    "has_comparison_focus": true
  }
}
```

Creation constraints:

1. caller must be in a submitter-capable workspace role
2. `decision_summary` is required
3. linked `evidence_view_id`, when supplied, must be visible inside the same workspace and study
4. decision logs preserve history; they do not rewrite prior decisions

## Artifact materialization

Saved evidence views are materialized under:

- `saas_runtime/workspaces/{workspace_id}/collaboration/evidence_views/{evidence_view_id}/`

Expected files:

- `evidence_view.json`
- `README.md`

Decision logs are materialized under:

- `saas_runtime/workspaces/{workspace_id}/collaboration/decision_logs/{decision_log_id}/`

Expected files:

- `decision_log.json`
- `README.md`

## Session and product count rules

The collaboration surface now propagates into:

- workspace session `capabilities.study_collaboration`
- workspace session `product_counts.evidence_views`
- workspace session `product_counts.decision_logs`
- project summary `evidence_view_count`
- project summary `decision_log_count`
- study summary `evidence_view_count`
- study summary `decision_log_count`

## Shared-shell expectations

The shared shell runtime client, app controller, frontend adapter, and Stage 15 hosted shell should now support:

1. loading study-scoped saved evidence views and decision logs
2. creating those objects from the selected study context
3. selecting one saved evidence view and reseeding the visible evidence-review state
4. selecting one decision log and projecting its decision summary and rationale
5. clearing stale collaboration state when project or study scope changes
6. treating `/app/evidence-views/{evidence_view_id}` and `/app/decision-logs/{decision_log_id}` as first-class hosted-shell routes that hydrate collaboration detail through controller-owned detail loaders

## Audit rules

The runtime must emit:

- `evidence_view.saved`
- `decision_log.created`

These remain workspace audit events, not a substitute for the newer decision-review contract defined in `specs/workspace_decision_review_surface_contract.md`.

## Non-goals

This contract does not yet define:

- generic cross-artifact threaded comments outside decision logs
- workspace-wide approval workflows beyond decision-log review
- broader decision-status transitions such as archived
- per-project ACL overrides
- notifications or subscriptions

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/job_store.py`
- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`
