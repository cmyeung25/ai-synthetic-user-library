# Workspace Settings Surface Contract

## Status

- contract: `workspace_settings_surface`
- version: `workspace-settings-surface/v0-draft`
- milestone: `Milestone 11`
- status: `in_progress`
- owner: `platform-system-architect`

## Purpose

This contract defines the first real Milestone 11 workspace-governance surface above the authenticated local SaaS runtime.

It exists to make membership, quota, retention, billing visibility, and API access lifecycle usable from the product shell without requiring direct SQLite edits, filesystem inspection, or ad hoc bootstrap commands.

This surface improves:

- `evidence_quality` by keeping governance changes auditable and workspace-scoped
- `scalable_research_throughput` by letting operators manage membership and API access inside the same product context
- `operational_auditability` by preserving durable token and member lifecycle events

## Product Boundary

This is a secondary surface.

- the default user path remains `study-first`
- workspace settings must not replace conversational intake as the product landing flow
- governance controls should be visible only when the user intentionally opens workspace settings

## Auth Model

All endpoints require bearer-token auth in the current workspace context.

Visible roles:

- `owner`
- `admin`
- `editor`
- `viewer`
- `billing_admin`

Mutation roles:

- `owner`
- `admin`

Additional role rules:

- only `owner` can assign the `owner` role
- owner-role downgrade is not supported through this surface
- only `owner` can issue or revoke a token for an owner account

## Endpoints

### `GET /api/v1/workspace-settings`

Returns the current workspace-governance snapshot.

Response shape:

```json
{
  "workspace_settings": {
    "contract_version": "workspace-settings-surface/v0-draft",
    "auth": {
      "workspace_id": "ws_api_demo",
      "user_id": "owner_api",
      "role": "owner",
      "token": "token-api"
    },
    "workspace": {
      "workspace_id": "ws_api_demo",
      "display_name": "Workspace API Demo",
      "plan_tier": "trial",
      "status": "active"
    },
    "billing_account": {
      "status": "trialing",
      "seat_count": 1
    },
    "plan_limits": {
      "daily_runs": 3,
      "max_concurrent_jobs": 1,
      "artifact_retention_days": 7
    },
    "members": [
      {
        "user_id": "owner_api",
        "role": "owner",
        "joined_at": "2026-06-28T00:00:00+00:00"
      }
    ],
    "api_tokens": [
      {
        "token_id": "token_abcdef123456",
        "token_hint": "token_...3456",
        "user_id": "owner_api",
        "role": "owner",
        "issued_at": "2026-06-28T00:00:00+00:00",
        "active": true,
        "current": true
      }
    ],
    "capabilities": {
      "workspace_settings": true,
      "member_admin": true,
      "token_admin": true,
      "audit_history": true,
      "billing_overview": true
    },
    "policies": {
      "region_code": "HK",
      "data_residency_region": "ap-east-1",
      "artifact_retention_days": 7,
      "daily_runs": 3,
      "max_concurrent_jobs": 1
    },
    "synthetic_boundary": "Synthetic evidence only. Workspace governance controls do not change the evidence boundary."
  }
}
```

Rules:

- token values must stay masked in `api_tokens`
- the current authenticated token may be identified through `current`
- billing is read-only in this snapshot endpoint; writable billing/quota mutation lives in `specs/workspace_billing_quota_surface_contract.md`
- detailed audit-history browsing lives in `specs/workspace_audit_history_surface_contract.md`

### `POST /api/v1/workspace-members`

Creates or updates one workspace member.

Request shape:

```json
{
  "user_id": "researcher_001",
  "role": "editor"
}
```

Response shape:

```json
{
  "member": {
    "user_id": "researcher_001",
    "role": "editor",
    "joined_at": "2026-06-28T00:05:00+00:00"
  },
  "workspace_settings": {}
}
```

Rules:

- response must include a refreshed `workspace_settings` snapshot
- existing tokens for that member must have their stored role synchronized
- member updates must emit an audit event

### `POST /api/v1/api-tokens`

Issues a new workspace-scoped API token for an existing member.

Request shape:

```json
{
  "user_id": "researcher_001"
}
```

Response shape:

```json
{
  "api_token": {
    "token": "token_abcdef123456",
    "token_hint": "token_...3456",
    "user_id": "researcher_001",
    "role": "editor",
    "issued_at": "2026-06-28T00:06:00+00:00",
    "active": true,
    "current": false
  },
  "workspace_settings": {}
}
```

Rules:

- the plaintext `token` is returned only at issue time
- the token role is derived from the current member role
- token issuance must emit an audit event

### `POST /api/v1/api-tokens/{token_id}/revoke`

Revokes an existing workspace token.

Response shape:

```json
{
  "api_token": {
    "token_id": "token_abcdef123456",
    "token_hint": "token_...3456",
    "user_id": "researcher_001",
    "role": "editor",
    "issued_at": "2026-06-28T00:06:00+00:00",
    "active": false,
    "current": false
  },
  "workspace_settings": {}
}
```

Rules:

- revoked tokens remain visible as inactive audit objects
- token revocation must emit an audit event

## Hosted Shell Projection

The Stage 15 hosted shell consumes this contract through:

- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`
- `demo/workspace_ui_shared/workspace_shell_app.mjs`
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs`
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`

Visible shell behaviors in this contract version:

- load settings snapshot
- inspect membership, billing overview, quota, retention, and token state
- upsert a member
- issue a token
- revoke a token
- show plaintext token only in the current shell session immediately after issuance

## Data Integrity Rule

Workspace-member updates must not invalidate unrelated tokens.

Current repository rule:

- member rows are updated with per-member upsert semantics
- only members removed from the workspace may cascade-delete their own tokens
- role synchronization must not delete tokens for surviving members

This rule exists because governance mutations are operational controls, not token-reset operations.

## Non-Goals

Not included in `v0-draft`:

- billing plan mutation
- seat purchasing
- SSO or IdP configuration
- project-level ACL
- token scopes beyond workspace role
- secret rotation UX beyond issue/revoke

## Verification

Repository evidence for this contract:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `src/ai_validation_swarm/saas/job_store.py`
- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`

Verification commands:

- `python -m unittest tests.unit.test_saas_runtime`
- `node --test tests/workspace_ui/*.mjs`
