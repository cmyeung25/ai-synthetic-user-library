# Workspace Session Runtime Contract (Draft)

## Purpose

This document defines the authenticated workspace-session contract that sits between:

- the local SaaS runtime auth boundary
- workspace, billing, and plan-limit state
- the Workspace UI shell that needs session-aware runtime context

The goal is to stop the shell from treating bearer-token auth as a blind string input with no explicit workspace session surface.

## Why this contract exists

Research bottleneck improved:

- the workspace shell can submit and inspect runs, but the operator still lacks one explicit runtime surface that confirms which workspace, role, plan, and limits are currently in effect

What this improves:

- scalable research throughput
- operator confidence
- evidence discipline
- frontend/runtime integration clarity

Why it matters now:

- the repository already has real authenticated API ingress
- Stage 12 already proves job submission and evidence query
- the next step toward a real product shell is making auth and workspace context visible as first-class runtime state

## HTTP boundary

Method:

- `GET /api/v1/session`

Auth:

- required `Authorization: Bearer <token>`

Response shape:

```json
{
  "session": {
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
    "job_counts": {
      "total": 4,
      "queued": 1,
      "running": 0,
      "completed": 2,
      "failed": 1,
      "canceled": 0
    },
    "paths": {
      "workspace_root": "C:/.../saas_runtime/workspaces/ws_api_demo",
      "briefs_root": "C:/.../briefs",
      "personas_root": "C:/.../personas",
      "runs_root": "C:/.../runs"
    },
    "capabilities": {
      "validation_jobs": true,
      "evidence_query": true,
      "worker_runtime": true,
      "session_auth": true
    },
    "synthetic_boundary": "Synthetic evidence only. Authenticated workspace access does not change the evidence boundary."
  }
}
```

## Canonical fields

### `auth`

Use to confirm:

- active workspace
- active user
- active role

### `workspace`

Use to confirm:

- display name
- plan tier
- workspace lifecycle status

### `billing_account`

Use to confirm:

- billing state that gates run submission
- seat count visible to the operator shell

### `plan_limits`

Use to make runtime constraints explicit before or during execution:

- daily runs
- concurrent jobs
- artifact retention days

### `job_counts`

Use for small operational summaries, not for deep observability.

### `paths`

These are engineering-facing local-runtime references. They are useful for this demo stage because the product shell still coexists with a filesystem-backed runtime.

### `capabilities`

These flags keep the shell aligned with what the local runtime actually exposes.

### `synthetic_boundary`

Auth and workspace identity do not change the research evidence boundary. This warning should remain visible.

## Frontend bridge boundary

Recommended implementation shape:

```ts
type WorkspaceSessionRuntimeBridgeInput = {
  sessionPayload: WorkspaceSessionPayload | null;
  apiBaseUrl: string;
  bearerToken: string;
  lastError: string | null;
};

type WorkspaceSessionRuntimeBridgeOutput = {
  sessionStatus: "missing_token" | "session_unloaded" | "session_loaded" | "auth_error";
  pill: { tone: string; label: string };
  actions: {
    loadWorkspaceSession: { intent: "load_workspace_session"; enabled: boolean };
  };
  metrics: Record<string, string | null>;
  sessionSummary: SummaryRow[];
  limitSummary: SummaryRow[];
  jobSummary: SummaryRow[];
  pathSummary: SummaryRow[];
  capabilityCards: SessionCapabilityCard[];
  endpointSummary: SummaryRow[];
  boundaryWarning: string;
  jsonPanel: WorkspaceSessionPayload | null;
};
```

## Verification plan

To know this contract is working:

1. API tests for:
   - missing bearer token
   - successful session load
   - CORS preflight on `/api/v1/session`
2. frontend bridge tests for:
   - missing token
   - loaded session
   - auth error
3. Stage 12 should render workspace session state from one shared bridge module
4. Stage 12 live runtime actions should compose through one shared client instead of reimplementing fetch/state handling inside the page

## Current repository evidence

- [src/ai_validation_swarm/saas/runtime.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/runtime.py>) now exposes `describe_workspace_session(...)`
- [src/ai_validation_swarm/saas/api.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/api.py>) now exposes `GET /api/v1/session`
- [demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs>) now defines the shared frontend bridge for session-aware runtime state
- [demo/workspace_ui_shared/workspace_shell_runtime_client.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_shell_runtime_client.mjs>) now centralizes live session/job/evidence-query fetch and state transitions for the engineering shell
- [tests/unit/test_saas_runtime.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/tests/unit/test_saas_runtime.py>) now verifies the backend session route
- [tests/workspace_ui/test_workspace_session_runtime_bridge.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/tests/workspace_ui/test_workspace_session_runtime_bridge.mjs>) now verifies the frontend session bridge
