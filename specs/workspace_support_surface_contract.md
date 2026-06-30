# Workspace Support Surface Contract (Draft)

## Purpose

This document defines the first Milestone 11 support-layer contract for:

- workspace-scoped `support diagnostics`
- durable `support snapshots`
- blocked-submission explanation
- failed-run handoff bundles

The goal is to let a real team diagnose blocked or failed synthetic research work from the product surface without dropping into CLI state, raw SQLite rows, or filesystem inspection.

## Why this contract exists

Research bottleneck improved:

- the platform can now run studies, review evidence, export bundles, and share outputs, but operators still need a product-native way to explain why submission is blocked or why a run failed

What this improves:

- evidence quality
- auditability
- scalable research throughput
- Milestone 11 operability for real teams

Why it matters now:

- project, study, export, and share product objects now exist
- the next real workflow gap is support handoff and failure diagnosis, not broader admin polish

## Endpoints

The local SaaS runtime now exposes:

- `GET /api/v1/support-diagnostics`
- `POST /api/v1/support-snapshots`
- `GET /api/v1/support-snapshots`
- `GET /api/v1/support-snapshots/{support_snapshot_id}`
- `POST /api/v1/support-snapshots/{support_snapshot_id}/handoff`

Related operator-intervention endpoints:

- `POST /api/v1/validation-jobs/{job_id}/cancel`
- `POST /api/v1/validation-jobs/{job_id}/retry`

## Object intent

### `support diagnostics`

`support diagnostics` is a live workspace-scoped explanation payload for:

- whether submission is currently blocked
- why the current workspace cannot submit
- why one selected run failed, is still queued, or is still running
- what the next allowed operator action is

### `support_snapshot`

`support_snapshot` is a durable product object attached to:

- one `workspace`
- one `project` when available
- one `study` when available
- one `validation job`
- one source `run_id` when available

Minimum fields:

- `support_snapshot_id`
- `workspace_id`
- `project_id`
- `study_id`
- `job_id`
- `run_id`
- `title`
- `status`
- `summary`
- `support_root`
- `snapshot_path`
- `created_by_user_id`
- `created_at`
- `updated_at`
- `metadata`

Projected governance fields:

- `handoff`
- `handoff_history`

## Diagnostics rules

### `GET /api/v1/support-diagnostics`

Supported query params:

- `job_id` optional
- `study_id` optional

Behavior:

1. the endpoint always explains the current submission gate for the workspace
2. if `job_id` is present, the selected job must be visible inside the current workspace
3. if `study_id` is present, the selected study must be visible inside the current workspace
4. the endpoint returns governed review/redaction state for the selected or job-linked study when available
5. the endpoint returns a normalized job diagnostic for the selected job when available
6. the endpoint also returns a short recent-failure digest for nearby failed jobs
7. the endpoint preserves an explicit synthetic-only support boundary

Response shape:

```json
{
  "support": {
    "contract_version": "workspace-support-surface/v0-draft",
    "workspace_id": "ws_api_demo",
    "selected_job_id": "job_123",
    "selected_study_id": "study_123",
    "governed_review": {
      "review_gate_status": "assigned_for_review"
    },
    "governed_redaction": {
      "status": "active",
      "rule_count": 2
    },
    "submission_gate": {
      "status": "blocked",
      "blocked_reason_count": 1,
      "blocked_reasons": [
        {
          "code": "concurrency_limit_reached",
          "message": "Workspace 'ws_api_demo' reached the max concurrent job limit (1).",
          "next_action": "Wait for an in-flight run to finish or move to a higher plan limit."
        }
      ]
    },
    "provider_runtime": {
      "contract_version": "workspace-provider-runtime/v0-draft",
      "selected_job_boundary": {
        "provider_name": "unknown-provider",
        "evidence_mode": "unsupported",
        "is_supported": false,
        "runtime_status": "unsupported_provider",
        "failure_kind": "unsupported_provider",
        "boundary_message": "Provider 'unknown-provider' is not supported by the validation-job runtime."
      }
    },
    "job_diagnostic": {
      "job_id": "job_123",
      "status": "failed",
      "provider_name": "unknown-provider",
      "provider_runtime_boundary": {
        "provider_name": "unknown-provider",
        "evidence_mode": "unsupported",
        "runtime_status": "unsupported_provider",
        "failure_kind": "unsupported_provider"
      },
      "failure_category": "provider_configuration",
      "summary": "Unknown provider: unknown-provider",
      "retry_count": 1,
      "created_at": "2026-06-28T02:00:00+00:00",
      "started_at": "2026-06-28T02:00:10+00:00",
      "finished_at": "2026-06-28T02:00:30+00:00",
      "can_cancel": false,
      "can_retry": true,
      "next_actions": [
        "Inspect the failed run inputs and retry from the study surface.",
        "Check provider_name or backend configuration before retrying."
      ]
    },
    "recent_failed_jobs": [
      {
        "job_id": "job_123",
        "status": "failed",
        "provider_name": "unknown-provider",
        "provider_runtime_boundary": {
          "provider_name": "unknown-provider",
          "evidence_mode": "unsupported",
          "runtime_status": "unsupported_provider"
        },
        "retry_count": 1,
        "project_id": "project_123",
        "study_id": "study_123",
        "run_id": "run_123",
        "created_at": "2026-06-28T02:00:00+00:00",
        "started_at": "2026-06-28T02:00:10+00:00",
        "finished_at": "2026-06-28T02:00:30+00:00",
        "last_error": "Unknown provider: unknown-provider"
      }
    ],
    "support_snapshot_count": 1,
    "synthetic_boundary": "Synthetic evidence only. Support diagnostics describe synthetic research runtime state, not human market proof."
  }
}
```

## Handoff mutation rules

### `POST /api/v1/support-snapshots/{support_snapshot_id}/handoff`

Request body:

```json
{
  "status": "assigned",
  "assigned_user_id": "reviewer_001",
  "note": "Please confirm provider configuration before retry.",
  "metadata": {
    "source": "stage15_demo"
  }
}
```

Supported handoff status values:

- `unassigned`
- `assigned`
- `acknowledged`
- `resolved`

Rules:

1. caller must be `owner`, `admin`, or `editor`
2. `assigned` requires `assigned_user_id`
3. `assigned_user_id` must belong to an `owner`, `admin`, or `editor` workspace member
4. `acknowledged` or `resolved` require an existing assignment
5. only the assigned handoff owner or `owner` / `admin` members may acknowledge or resolve the handoff
6. only `owner` / `admin` members may clear assignment back to `unassigned`
7. each mutation appends to `handoff_history`

## Failure categories

Provider runtime boundary is more specific than the legacy `failure_category` field.

Provider-specific statuses include:

- `unsupported_provider`
- `missing_auth`
- `timeout`
- `refusal`
- `retryable_transport`
- `provider_configuration`

The legacy `failure_category` remains for support grouping and backwards compatibility.

Current first-pass failure categories:

- `artifact_retention_expired`
- `job_canceled`
- `provider_configuration`
- `missing_input_artifact`
- `workspace_boundary_violation`
- `runtime_failure`
- `awaiting_worker`
- `in_progress`
- `no_failure`

These categories are product-language support buckets, not low-level exception-class guarantees.

## Submission-gate categories

Current first-pass blocked reasons:

- `role_forbidden`
- `billing_inactive`
- `concurrency_limit_reached`
- `daily_limit_reached`

The support surface should keep these machine-stable codes while also returning operator-facing next actions.

## Snapshot creation rules

### `POST /api/v1/support-snapshots`

Request body:

```json
{
  "job_id": "job_123",
  "title": "Provider failure handoff",
  "notes": "Checked study inputs. Provider name still set to unknown-provider.",
  "metadata": {
    "source": "stage15_demo"
  }
}
```

Creation behavior:

1. the selected job must be visible in the current workspace
2. the runtime resolves project, study, and run lineage from the job metadata when present
3. the runtime generates a support diagnostic snapshot at creation time
4. the snapshot is materialized under the workspace support root
5. the runtime writes both `support_snapshot.json` and `README.md`
6. the snapshot row is persisted in the runtime relational store

Response shape:

```json
{
  "support_snapshot": {
    "support_snapshot_id": "support_123",
    "study_id": "study_123",
    "job_id": "job_123",
    "title": "Provider failure handoff",
    "status": "generated",
    "summary": "Unknown provider: unknown-provider"
  }
}
```

## Operator intervention rules

The first Milestone 11 support layer now includes two product-surface interventions:

1. `cancel queued job`
2. `retry failed or canceled job`

Rules:

- cancel is allowed only when the selected job is still `queued`
- retry is allowed only when the selected job status is `failed` or `canceled`
- retry creates a new queued job and preserves the old job as audit history
- both actions preserve workspace/project/study lineage through job metadata
- both actions remain role-gated to submitter-capable roles

The support diagnostics payload should expose these controls through stable booleans such as:

- `job_diagnostic.can_cancel`
- `job_diagnostic.can_retry`

## Persistence boundary

Each created support snapshot now persists:

- a row in the runtime relational store
- a support directory under `workspaces/<workspace_id>/support/<support_snapshot_id>/`
- `support_snapshot.json`
- `README.md`

The materialized payload now also includes:

- `handoff`
- `handoff_history`

## Product-surface implications

The Stage 15 shared shell now projects support state through:

- `support_surface.submission_gate_summary`
- `support_surface.blocked_reasons`
- `support_surface.job_diagnostic_summary`
- `support_surface.job_diagnostic_cards`
- `support_surface.recent_failures`
- `product_surface.support_snapshots`
- `product_surface.selected_support_snapshot_summary`

This is the current product-layer render contract for operator support.

## Non-goals

This first contract does not yet define:

- stuck-worker intervention controls for already-running jobs
- real-time streaming logs
- comment threads on support snapshots
- external support ticket sync
- richer calibration or cross-run audit dashboards

Those remain later Milestone 11 or post-Milestone 11 support layers.

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
- `demo/workspace_ui_moss_stage15/index.html`

Audit events:

- `support_snapshot.generated`
- `support_snapshot.handoff_updated`
