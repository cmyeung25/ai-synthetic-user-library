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

- `project_id`
- `study_id`
- `job_id`
- `query_text`
- `active_family`
- `sort_by`
- `selected_result_id`
- `selected_replay_step_id`
- `selected_comparison_run_id`

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
    "projects": [
      {
        "project_id": "project_001",
        "name": "Inbox Coach Launch"
      }
    ],
    "selected_project_id": "project_001",
    "selected_project": {
      "project_id": "project_001"
    },
    "studies": [
      {
        "study_id": "study_001",
        "project_id": "project_001",
        "latest_job_id": "job_001"
      }
    ],
    "selected_study_id": "study_001",
    "selected_study": {
      "study_id": "study_001"
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
      "replay_context": {
        "selected_result_has_replay": false,
        "replay_result_count": 2,
        "selected_family_replay_result_count": 0,
        "note": "Selected evidence has no replay steps. 2 other visible result(s) carry replay context."
      },
      "comparison_context": {
        "selected_family_result_count": 1,
        "selected_family_replay_result_count": 0,
        "recommended_comparison_id": "query-raw_responses",
        "note": "Selected evidence has no direct replay steps. Compare with replay-bearing artifacts for execution context."
      },
      "cross_run_comparison": {
        "comparison_run_count": 1,
        "selected_comparison_run_id": "run_20260628_102100",
        "selected_comparison_job_id": "job_007",
        "note": "1 comparable completed run is available for cross-run review."
      },
      "longitudinal_comparison": {
        "contract_version": "workspace-longitudinal-comparison/v0-draft",
        "selected_window_id": "same_study_runs",
        "same_study_run_count": 1,
        "same_project_study_count": 1,
        "study_timeline_entry_count": 4,
        "recurring_signal_synthesis": {
          "contract_version": "workspace-longitudinal-recurring-signals/v0-draft",
          "pattern_count": 1,
          "persistent_pattern_count": 1
        },
        "panel_learning_projection": {
          "contract_version": "workspace-longitudinal-panel-learning/v0-draft",
          "decision_trends": {
            "total_decision_count": 1,
            "latest_review_status": "approved"
          }
        },
        "note": "Review same-study runs first, then the study timeline, before widening to neighboring studies in the same project."
      },
      "results": [
        {
          "id": "query-run_report",
          "title": "Run report"
        }
      ]
    },
    "provider_runtime": {
      "contract_version": "workspace-provider-runtime/v0-draft",
      "catalog": [
        {
          "provider_name": "mock",
          "evidence_mode": "mock_demo",
          "runtime_status": "ready_to_queue"
        },
        {
          "provider_name": "codex",
          "evidence_mode": "live_synthetic",
          "auth_readiness": "ready"
        }
      ],
      "selected_job_boundary": {
        "contract_version": "validation-provider-runtime/v0-draft",
        "provider_name": "codex",
        "provider_family": "codex",
        "evidence_mode": "live_synthetic",
        "is_supported": true,
        "is_live_provider": true,
        "is_codex_provider": true,
        "requires_auth": true,
        "auth_readiness": "ready",
        "runtime_status": "completed",
        "failure_kind": null,
        "boundary_label": "Live synthetic evidence",
        "boundary_message": "This provider creates live synthetic evidence. It is not human market proof."
      },
      "job_counts": {
        "mock_demo": 0,
        "live_synthetic": 1,
        "unsupported": 0
      }
    },
    "capabilities": {
      "validation_jobs": true,
      "evidence_query": true,
      "provider_runtime_boundary": true,
      "live_validation_providers": true,
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

## Provider Runtime Boundary

The snapshot owns provider readiness and evidence-mode interpretation so frontend components do not infer this from raw job status or provider names.

Minimum fields:

- `session.validation_provider_catalog`
- `provider_runtime.catalog`
- `provider_runtime.selected_job_boundary`
- `provider_runtime.job_counts`
- `evidence_query.provider_runtime_boundary`
- `selected_job.metadata.provider_runtime_boundary`

Required behavior:

- `mock` must be labeled as `mock_demo`
- `codex`, `codex-sdk`, `openai`, and `agnes` must be labeled as `live_synthetic`
- unsupported providers must produce `runtime_status: unsupported_provider`
- missing local credentials must produce `runtime_status: missing_auth`
- provider runtime state must preserve the synthetic-evidence boundary and must not imply human market proof

## Canonical fields

### `snapshot_version`

Version marker for frontend contract compatibility.

Current value:

- `workspace-shell/v0-draft`

### `session`

Should reuse the session summary shape already served by `GET /api/v1/session`.

### `jobs`

Should expose the current workspace job list with the same lifecycle semantics already used by the validation-job API.

### `projects`

Should expose visible workspace projects for the hosted product shell.

### `selected_project_id`

Should reflect:

1. an explicit `project_id` query parameter when present
2. otherwise the project implied by the selected study when present
3. otherwise the first visible project
4. otherwise `null`

### `studies`

Should expose visible workspace studies, scoped to the selected project when one is selected.

### `selected_study_id`

Should reflect:

1. an explicit `study_id` query parameter when present
2. otherwise the first visible study in the scoped project view
3. otherwise `null`

### `selected_job_id`

Should reflect:

1. an explicit `job_id` query parameter when present
2. otherwise the latest job implied by the selected study when available
3. otherwise the first available job
4. otherwise `null`

### `selected_job`

Should be the selected job object or `null`.

### `evidence_query`

Should embed the completed-run or pending-run evidence query payload, including replay context, nearby comparison guidance, initial cross-run comparison guidance, backend-owned longitudinal comparison context, recurring longitudinal signal synthesis, and panel-learning / decision-trend projection, instead of forcing the frontend to make a second query call during ordinary shell refresh.

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
