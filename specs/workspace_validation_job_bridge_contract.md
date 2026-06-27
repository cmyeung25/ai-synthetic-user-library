# Workspace Validation Job Bridge Contract (Draft)

## Purpose

This document defines the bridge between:

- the Workspace UI draft-plan state
- the existing authenticated `validation-jobs` API
- the frontend run-monitor state that should stay aligned with that API

The goal is to make the runtime ingress boundary explicit before the workspace shell is wired to real fetches.

## Why this contract exists

Research bottleneck improved:

- the workspace shell is not operationally credible if confirmation can happen on screen but the frontend still lacks a stable way to submit and monitor real runs

What this improves:

- scalable research throughput
- auditability
- runtime clarity
- frontend/backend contract discipline

Why it matters now:

- the repository already exposes authenticated `POST/GET /api/v1/validation-jobs`
- the integrated workspace shell should connect to that real ingress before broader SaaS product work
- the evidence query endpoint is still missing, so the runtime bridge must keep that gap explicit

## Architecture role

This bridge contract is the runtime-ingress layer between planning and execution.

It is:

- downstream of the draft plan and frontend adapter
- upstream of the local SaaS runtime API
- responsible for request mapping and response normalization
- the runtime-facing input to the later shell frontend adapter layer

It is not:

- the richer planning object itself
- the evidence query contract
- the run artifact persistence schema

## Source-of-truth order

The source-of-truth order should be:

1. draft plan object
2. validation-job API request payload
3. validation-job API response
4. derived run-monitor record in the workspace shell

The frontend should not guess queue or worker state when a job payload already exists.

## Request mapping scope

The bridge should decide:

1. whether the draft is actually ready for submission
2. how to map a confirmed draft into `ValidationJobRequest`
3. how to carry draft context into API metadata without replacing the system of record
4. how to normalize returned job records into frontend run-monitor state
5. which capability gap still remains because the query/replay endpoint does not yet exist

## Input contracts

### 1. Draft plan

Minimum consumed fields:

- `draft_plan_id`
- `workspace_id`
- `status`
- `source_intent.user_text`
- `inference.primary_mode`
- `proposed_run.first_task`
- `proposed_run.provider_name`
- `evidence_boundary`
- `remediation.blocking_reasons`
- `confirmation.status`

### 2. Workspace runtime context

Example:

```json
{
  "workspace_id": "ws_api_demo",
  "brief_path": "briefs/brief.json",
  "persona_dir": "personas",
  "panel_type": "mainstream",
  "sample_size": 5,
  "provider_name": "mock",
  "priority": "normal",
  "max_retries": 1,
  "run_root": "runs",
  "idempotency_key": "stage12-demo-job"
}
```

This context carries runtime-local information that the draft plan does not own directly.

### 3. Validation job response

Example response payload from the existing API:

```json
{
  "job_id": "job_20260627_abcdef12",
  "workspace_id": "ws_api_demo",
  "brief_id": "brief_001",
  "status": "queued",
  "provider_name": "mock",
  "output_run_path": null,
  "retry_count": 0,
  "created_at": "2026-06-27T22:45:00Z",
  "started_at": null,
  "finished_at": null,
  "last_error": "",
  "metadata": {
    "workspace_id": "ws_api_demo",
    "draft_plan_id": "draft_plan_20260627_proto_07",
    "primary_mode": "prototype_validation",
    "first_task": "connect data"
  }
}
```

## Request output contract

Example frontend-generated request:

```json
{
  "brief_path": "briefs/brief.json",
  "persona_dir": "personas",
  "panel_spec": {
    "panel_type": "mainstream",
    "sample_size": 5,
    "random_seed": 11
  },
  "provider_name": "mock",
  "priority": "normal",
  "max_retries": 1,
  "idempotency_key": "stage12-demo-job",
  "run_root": "runs",
  "metadata": {
    "workspace_id": "ws_api_demo",
    "draft_plan_id": "draft_plan_20260627_proto_07",
    "primary_mode": "prototype_validation",
    "first_task": "connect data",
    "source_intent": "Where do new operators hesitate during onboarding, and do they continue after the first task?",
    "bridge_version": "workspace-validation-job-bridge/v0-draft"
  }
}
```

## Response normalization contract

Example frontend-normalized run record:

```json
{
  "job_id": "job_20260627_abcdef12",
  "status": "queued",
  "queue_position": null,
  "worker_id": null,
  "current_step": null,
  "attempt_count": 0,
  "last_event_at": "2026-06-27T22:45:00Z",
  "failure_reason": null,
  "artifact_refs": []
}
```

## Canonical fields

### `submission_ready`

This should be `true` only when:

- `confirmation.status == confirmed` or `draft.status == confirmed`
- `remediation.blocking_reasons` is empty

### `request_payload`

This is the final API-facing request shape derived from the draft plus runtime context.

### `derived_run_record`

This should be the normalized object the workspace shell can hand directly to the shared run-monitor derivation.

### `live_review_gap`

This field should remain explicit until the metadata-backed evidence query and replay endpoint exists.

## Derivation rules

### Rule 1: confirmation gates submission

The bridge may preview a request early, but it must not claim the draft is submittable until confirmation is real and blockers are empty.

### Rule 2: runtime context stays separate from planning context

`brief_path`, `persona_dir`, and `run_root` belong to runtime context, not to the conversational planning object.

### Rule 3: API metadata can carry draft lineage

The request metadata should preserve draft lineage such as:

- `workspace_id`
- `draft_plan_id`
- `primary_mode`
- `first_task`

without pretending that API metadata replaces the draft plan.

### Rule 4: response state drives run-monitor state

If a live job payload exists, the frontend run monitor should derive from that payload instead of stale local assumptions.

### Rule 5: evidence query remains a separate boundary

The validation-job bridge must not silently collapse job ingress and evidence review into one hidden surface.

Completed-run evidence query may now be served by a separate backend endpoint, but the validation-job bridge should still keep these boundaries explicit:

- job ingress and lifecycle state come from the validation-job API
- evidence query comes from a separate completed-run query endpoint
- replay depth still depends on whether the run artifacts actually contain trace-linked steps

## Frontend function boundary

Recommended implementation shape:

```ts
type WorkspaceValidationBridgeInput = {
  draftPlan: DraftPlan;
  workspaceContext: RuntimeWorkspaceContext;
  jobList: ValidationJobApiRecord[];
  selectedJob: ValidationJobApiRecord | null;
  apiBaseUrl: string;
  lastError: string | null;
};

type WorkspaceValidationBridgeOutput = {
  bridgeStatus: BridgeStatus;
  submissionReady: boolean;
  requestPayload: ValidationJobRequestPayload;
  jobCount: number;
  selectedJobId: string | null;
  selectedJobStatus: string | null;
  derivedRunRecord: WorkspaceRunRecord | null;
  endpointSummary: EndpointSummary;
  liveReviewGap: string;
  warning: string | null;
};
```

## Verification plan

To know this contract is working:

1. contract tests for:
   - request mapping from confirmed draft
   - submission gating from unconfirmed or blocked draft
   - job-response normalization
   - bridge summary state
2. API tests proving browser-callable CORS headers exist for `validation-jobs`
3. integrated shell demo review where a live API job can drive the shell run-monitor state

## Current repository evidence

- [src/ai_validation_swarm/saas/api.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/api.py>) already exposes authenticated `POST/GET /api/v1/validation-jobs`
- [src/ai_validation_swarm/saas/runtime.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/runtime.py>) already submits, lists, and processes validation jobs
- [demo/workspace_ui_shared/workspace_runtime_bridge.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_runtime_bridge.mjs>) now defines the frontend bridge mapping and job normalization helpers

This contract exists so the workspace shell can connect to the current runtime ingress cleanly before the later evidence-query endpoint is added.
