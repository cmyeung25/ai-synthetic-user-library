# Workspace Study Activity Surface Contract

## Purpose

This document defines the first durable Milestone 11 `study activity` layer inside the hosted workspace shell.

It exists to keep cross-artifact study continuity visible in one place after the platform already gained:

- project and study product objects
- saved evidence views
- decision logs and decision review
- export and share bundles
- support snapshots

Without this layer, the shell still forces users to reconstruct what changed across runs, evidence, review, export, and support actions by jumping between separate panels.

## Why this contract exists

Research bottleneck improved:

- real study follow-up work becomes fragmented after the first run because review, export, share, and support actions are durable but not summarized in one study-scoped timeline

What this improves:

- `evidence_quality`
- `auditability`
- `scalable_research_throughput`

Why it matters now:

- Milestone 11 is the first real user-facing product layer
- that layer needs a study-first continuity surface before broader notification or inbox features are worth the complexity

## Endpoint

The local SaaS runtime now exposes:

- `GET /api/v1/studies/{study_id}/activity`

Query parameters:

- `limit`

## Response shape

Response:

```json
{
  "study_activity": {
    "project_id": "project_123",
    "study_id": "study_123",
    "activity_events": [
      {
        "activity_id": "audit_123",
        "action": "decision_log.review_status_updated",
        "event_family": "review",
        "tone": "active",
        "headline": "Decision review updated",
        "summary": "The selected decision moved to in_review.",
        "actor_user_id": "reviewer_001",
        "actor_role": "editor",
        "created_at": "2026-06-28T02:12:00+00:00",
        "route_kind": "decision_log",
        "route_id": "decision_log_123",
        "route_path": "/app/decision-logs/decision_log_123"
      }
    ]
  }
}
```

## Activity source rules

Study activity is a study-scoped projection over workspace audit events.

It is not a second persistence system.

The runtime should:

1. read recent workspace audit events from the existing audit store
2. keep only events that belong to the selected study
3. map those events into UI-ready timeline cards with stable route hints
4. preserve reverse-chronological ordering from the underlying audit feed

## Included event families

The first contract covers these study-visible actions:

- `study.created`
- `validation_job.submitted`
- `validation_job.started`
- `validation_job.completed`
- `validation_job.failed`
- `validation_job.canceled`
- `validation_job.retried`
- `evidence_view.saved`
- `decision_log.created`
- `decision_log.commented`
- `decision_log.review_status_updated`
- `export_bundle.created`
- `share_bundle.created`
- `share_bundle.revoked`
- `support_snapshot.created`

This is the minimum cross-artifact continuity layer for the current Milestone 11 surface.

## Route contract

Each activity item may expose:

- `route_kind`
- `route_id`
- `route_path`

Current route kinds:

- `study`
- `job`
- `evidence_view`
- `decision_log`
- `export_bundle`
- `share_bundle`
- `support_snapshot`

The hosted shell should treat those activity cards as deep-linkable selection shortcuts, not as plain text notifications.

## Session and shell rules

The study-activity surface now propagates into:

- workspace session `capabilities.study_activity`
- shared runtime-client state `liveStudyActivity`
- shared app-controller method `loadStudyActivity(...)`
- frontend adapter `product_surface.study_activity`
- frontend adapter `product_surface.study_activity_summary`

The hosted shell should now:

1. clear stale study activity when project or study scope changes
2. load study activity when a study becomes the selected operating object
3. refresh study activity after collaboration and product actions that materially change study continuity
4. render study activity as a study-scoped timeline, not as a workspace-wide alert center
5. let users open the linked product object directly from the activity card

## UI expectations

The Stage 15 hosted shell should show:

- one `Study activity` summary block
- one `Cross-artifact timeline` list
- one explicit reload action for the selected study

The surface should stay visually secondary to conversational intake and evidence review, but primary enough to preserve study continuity without filesystem inspection.

## Non-goals

This contract does not yet define:

- push notifications
- email or chat delivery
- subscriptions or watcher rules
- workspace-wide inbox aggregation
- unread state
- incident-thread collaboration

Those belong to later collaboration and notification layers.

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`
- `tests/workspace_ui/test_stage15_shell_document.mjs`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`
- `frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx`
