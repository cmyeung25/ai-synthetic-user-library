# Workspace Decision Review Surface Contract

## Purpose

This document defines the first Milestone 11 `decision review` layer inside the hosted study workspace.

It covers:

- decision-log review status
- threaded decision comments
- decision-log approval and revision workflow
- explicit review assignment and assignment history
- API and shared-shell expectations for keeping review attached to the same study evidence surface

The contract exists so research conclusions can be challenged, approved, or sent back for revision inside the product shell instead of drifting into external notes or chat tools.

## Why this contract exists

Research bottleneck improved:

- teams can already save evidence views and record decisions, but they still lack a durable in-product review path for deciding whether a conclusion is ready to act on

What this improves:

- `evidence_quality`
- `auditability`
- `scalable_research_throughput`

Why it matters now:

- Milestone 11 is the first real study-first product layer
- a user-facing workspace is not credible if decisions can be recorded but not reviewed in place

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/decision-logs/{decision_log_id}/comments`
- `GET /api/v1/decision-logs/{decision_log_id}/comments`
- `POST /api/v1/decision-logs/{decision_log_id}/review-status`
- `POST /api/v1/decision-logs/{decision_log_id}/review-assignment`

`GET /api/v1/decision-logs/{decision_log_id}` now also returns:

- `decision_log`
- `decision_comments`

## Review model

Decision review is attached directly to one `decision_log`.

### Review status

Supported status values:

- `draft`
- `in_review`
- `approved`
- `needs_revision`

Decision logs store review state in decision-log metadata while keeping the existing durable decision-log object shape intact.

Minimum projected fields on decision-log detail:

- `review_status`
- `review_status_history`
- `review_status_updated_at`
- `review_status_updated_by_user_id`
- `latest_review_note`
- `comment_count`
- `review_thread_count`
- `review_assignment`
- `review_assignment_history`
- `provider_runtime_boundary`
- `governed_review`
- `governed_redaction`

`provider_runtime_boundary` must distinguish `mock_demo`, `live_synthetic`, and `unsupported` evidence modes so decision reviewers do not approve a working judgment while losing whether the supporting evidence came from a mock or live provider path.

### Review assignment

Supported assignment status values:

- `unassigned`
- `assigned`

Minimum projected fields:

- `contract_version`
- `status`
- `assignee_user_ids`
- `assignees`
- `latest_note`
- `assigned_at`
- `assigned_by_user_id`

### Decision comment

Minimum fields:

- `decision_comment_id`
- `workspace_id`
- `project_id`
- `study_id`
- `decision_log_id`
- `parent_comment_id`
- `anchor_kind`
- `body`
- `created_by_user_id`
- `created_at`
- `updated_at`

Supported `anchor_kind` values:

- `general`
- `decision_summary`
- `rationale`
- `evidence_view`
- `comparison`

## Creation and mutation rules

### `POST /api/v1/decision-logs/{decision_log_id}/comments`

Request body:

```json
{
  "parent_comment_id": "decision_comment_123",
  "anchor_kind": "comparison",
  "body": "The comparison run shows the same hesitation cluster."
}
```

Rules:

1. caller must be in a submitter-capable workspace role
2. `body` is required
3. replies must stay inside the same decision-log thread
4. comments preserve history; they do not rewrite prior review notes

### `POST /api/v1/decision-logs/{decision_log_id}/review-status`

Request body:

```json
{
  "review_status": "approved",
  "note": "Cross-run evidence is consistent enough to proceed."
}
```

Rules:

1. caller must be in a submitter-capable workspace role
2. `review_status` must be one of the supported values
3. each transition appends to `review_status_history`
4. review status is attached to the same decision log rather than creating a separate approval object
5. only `owner` / `admin` members or explicitly assigned reviewers may move a decision into `approved` or `needs_revision`
6. when the linked study is regulated/high-stakes, governed reviewer responsibility must already be assigned at the study level before a decision can move into `approved` or `needs_revision`

### `POST /api/v1/decision-logs/{decision_log_id}/review-assignment`

Request body:

```json
{
  "assignee_user_ids": ["reviewer_001"],
  "note": "Route this decision to the study reviewer.",
  "metadata": {
    "source": "stage15_demo"
  }
}
```

Rules:

1. caller must be `owner` or `admin`
2. every assignee must be an existing workspace member
3. assignees must have role `owner`, `admin`, or `editor`
4. assignment appends to `review_assignment_history`
5. empty `assignee_user_ids` clears assignment back to `unassigned`
6. assignment stays attached to the same durable decision-log object as evidence linkage, comments, and review status

For regulated/high-stakes studies, new decision logs may inherit default `review_assignment` assignees from the study-level governed reviewer handoff so named reviewer responsibility does not have to be reconstructed per decision.

## Artifact materialization

Decision logs continue to materialize under:

- `saas_runtime/workspaces/{workspace_id}/collaboration/decision_logs/{decision_log_id}/`

Expected files:

- `decision_log.json`
- `README.md`

The materialized decision-log payload now also includes:

- `review_status`
- `comment_count`
- `review_status_history`
- `review_assignment`
- `review_assignment_history`
- `governed_review`
- `governed_redaction`
- `comments`

## Shared-shell expectations

The shared shell runtime client, app controller, frontend adapter, and Stage 15 hosted shell should now support:

1. loading one selected decision log with its threaded comments
2. showing the current review status alongside decision summary and rationale
3. changing decision review status inside the selected decision surface
4. adding top-level comments or replies without leaving the study shell
5. keeping the same decision-log route while review state changes

## Audit rules

The runtime must emit:

- `decision_log.review_status_updated`
- `decision_log.commented`
- `decision_log.review_assignment_updated`
- `study.governed_review_assignment_updated`

These events extend study collaboration into in-product review history.

## Non-goals

This contract does not yet define:

- workspace-wide notifications
- subscriptions or mention delivery
- cross-artifact generic comment threads outside decision logs
- share-publication approval policy
- project-level ACL overrides for review

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
- `frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx`
