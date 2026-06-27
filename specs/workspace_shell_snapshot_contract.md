# Workspace Shell Snapshot Contract (Draft)

## Purpose

This document defines the `backend-driven shell hydration contract` between:

- the local SaaS runtime
- the shared workspace shell app controller
- the product-facing workspace review surface

The goal is to let the frontend load one coherent workspace shell snapshot instead of stitching together:

- workspace session
- selected validation job
- completed-run evidence query

through separate page-driven API calls.

## Why this contract exists

Research bottleneck improved:

- the workspace shell had reached the point where multi-endpoint orchestration inside the page was becoming the main integration bottleneck

What this improves:

- scalable research throughput
- evidence discipline
- frontend/backend contract clarity
- promotion path from engineering demo to real hosted shell

Why it matters now:

- the repo already has authenticated session loading, validation-job APIs, and completed-run evidence query
- Stage 13 proved the shared app controller boundary
- the next gap is to make the visible shell itself hydrate from a backend-owned object

## Alignment to platform goals

1. Which research bottleneck does this improve?
   It reduces operator friction between run monitoring and evidence review by returning one snapshot-ready shell payload.
2. Does it improve realism, decision prediction, evidence quality, calibration, or throughput?
   It improves throughput and evidence discipline by keeping the visible review surface aligned with one backend contract.
3. Does it move the platform closer to replacing interviewer-led work?
   Yes. A credible workspace needs one dependable execution-to-review boundary instead of page-local orchestration glue.
4. Why is this necessary now?
   Because the shell already has enough live runtime behavior that frontend-owned hydration logic would create drift and slow productization.

## Endpoint

- `GET /api/v1/workspace-shell`

## Query parameters

Minimum supported parameters:

- `job_id`
- `query_text`
- `active_family`
- `sort_by`
- `selected_result_id`
- `selected_replay_step_id`

The frontend may omit `job_id` when it only needs workspace/session context.

## Response shape

Example:

```json
{
  "snapshot": {
    "snapshot_version": "workspace-shell/v0-draft",
    "session": {
      "auth": {
        "workspace_id": "ws_api_demo",
        "role": "owner"
      }
    },
    "jobs": [
      {
        "job_id": "job_001",
        "status": "completed",
        "provider_name": "mock",
        "output_run_path": "runs/job_001"
      }
    ],
    "selected_job_id": "job_001",
    "selected_job": {
      "job_id": "job_001",
      "status": "completed"
    },
    "evidence_query": {
      "query_status": "query_ready",
      "result_count": 1,
      "selected_result_id": "query-run_report",
      "selected_replay_step_id": "step-03",
      "results": [
        {
          "id": "query-run_report",
          "title": "Run report"
        }
      ]
    },
    "capabilities": {
      "validation_jobs": true,
      "evidence_query": true,
      "workspace_shell_snapshot": true
    },
    "runtime_sync": {
      "poll_recommended_ms": 4000,
      "snapshot_endpoint": "/api/v1/workspace-shell"
    },
    "synthetic_boundary": "Synthetic evidence only."
  }
}
```

## Canonical fields

### `snapshot_version`

Version marker for frontend contract compatibility.

Current value:

- `workspace-shell/v0-draft`

### `session`

Should reuse the session summary shape already served by `GET /api/v1/session`.

### `jobs`

Should expose the current workspace job list with the same lifecycle semantics already used by the validation-job API.

### `selected_job_id`

Should reflect:

1. an explicit `job_id` query parameter when present
2. otherwise the first available job
3. otherwise `null`

### `selected_job`

Should be the selected job object or `null`.

### `evidence_query`

Should embed the completed-run or pending-run evidence query payload instead of forcing the frontend to make a second query call during ordinary shell refresh.

### `capabilities`

Should merge existing runtime capabilities with:

- `workspace_shell_snapshot: true`

### `runtime_sync`

Must return:

- `poll_recommended_ms`
- `snapshot_endpoint`

This lets the shared shell controller drive heartbeat timing without hard-coding every value in the page.

## Derivation rules

The backend should derive the snapshot in this order:

1. authenticated workspace session
2. workspace job list
3. selected job
4. evidence query for the selected job, or a pending query placeholder when no query-ready job exists
5. runtime sync recommendation and synthetic boundary

The frontend should treat the snapshot as the first hydration source for live shell state.

## Non-goals

This contract does not yet define:

- push subscriptions or websockets
- persistent conversational thread state
- cross-run comparison payloads
- deep replay artifact expansion beyond the current evidence-query payload
- tenant-admin or billing-management surfaces

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_runtime_sync.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`

Manual demo surface:

- `demo/workspace_ui_moss_stage14/index.html`
