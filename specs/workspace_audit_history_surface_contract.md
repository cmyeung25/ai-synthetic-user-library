# Workspace Audit History Surface Contract

## Status

- contract: `workspace_audit_history_surface`
- version: `workspace-audit-history-surface/v0-draft`
- milestone: `Milestone 11`
- status: `in_progress`
- owner: `platform-system-architect`

## Purpose

This contract makes workspace audit history visible and queryable from the Milestone 11 product shell.

It exists because governance and operator controls are not credible user-facing surfaces unless the resulting audit events can be inspected without SQLite access, filesystem inspection, or ad hoc debugging.

This surface improves:

- `evidence_quality` by keeping governance and operator actions attached to durable audit records
- `operational_auditability` by exposing who changed what, when, and against which workspace object
- `scalable_research_throughput` by letting teams inspect recent operational history inside the same shell instead of dropping into backend-only workflows

## Product Boundary

This is a secondary workspace-governance surface.

- the default path remains `study-first`
- audit history must stay visible from workspace settings, not replace study intake or evidence review as the hero flow
- the audit surface is read-only in this contract version

## Auth Model

All endpoints require bearer-token auth in the current workspace context.

Visible roles:

- `owner`
- `admin`
- `editor`
- `viewer`
- `billing_admin`

Rules:

- all authenticated workspace roles may inspect visible audit history
- this surface only returns events for the authenticated workspace
- role visibility does not weaken the synthetic-only boundary

## Endpoint

### `GET /api/v1/audit-events`

Returns the most recent workspace audit events, optionally filtered.

Supported query parameters:

- `target_type`
- `action_prefix`
- `limit`

Response shape:

```json
{
  "audit_history": {
    "contract_version": "workspace-audit-history-surface/v0-draft",
    "auth": {
      "workspace_id": "ws_api_demo",
      "user_id": "owner_api",
      "role": "owner",
      "token": "token-api"
    },
    "filters": {
      "target_type": "api_token",
      "action_prefix": "api_token.",
      "limit": 5
    },
    "audit_events": [
      {
        "audit_event_id": "audit_001",
        "workspace_id": "ws_api_demo",
        "actor_user_id": "owner_api",
        "actor_role": "owner",
        "action": "api_token.issued",
        "target_type": "api_token",
        "target_id": "token_...3456",
        "event_payload": {
          "user_id": "researcher_001",
          "role": "editor"
        },
        "created_at": "2026-06-28T00:06:00+00:00"
      }
    ],
    "capabilities": {
      "workspace_settings": true,
      "audit_history": true
    },
    "synthetic_boundary": "Synthetic evidence only. Audit history shows simulated-research operations and governance events, not human validation."
  }
}
```

Rules:

- `limit` defaults to `20`
- `limit` must be clamped to a safe maximum in the runtime
- `target_type` applies exact-match filtering
- `action_prefix` applies prefix filtering such as `api_token.` or `workspace_`
- events must be returned newest-first by `created_at` and then `audit_event_id`

## Event Scope

This contract is intentionally workspace-wide.

It may expose events for:

- workspace membership changes
- API token issue and revoke
- billing and quota changes
- export and share operations
- support and intervention events

This allows one visible operational history instead of fragmented per-surface audit lists.

## Hosted Shell Projection

The Stage 15 hosted shell consumes this contract through:

- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`

Visible shell behaviors in this contract version:

- load recent audit history on demand
- filter by `target_type`
- filter by `action_prefix`
- inspect actor, action, target, timestamp, and compact payload summary

## Non-Goals

Not included in `v0-draft`:

- pagination or cursoring
- free-text audit search
- diff-aware event visualization
- approval workflows
- inline audit-event comments
- project-level or study-level saved audit views

## Verification

Repository evidence for this contract:

- `src/ai_validation_swarm/saas/job_store.py`
- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`

Verification commands:

- `python -m unittest tests.unit.test_saas_runtime`
- `node --test tests/workspace_ui/*.mjs`
