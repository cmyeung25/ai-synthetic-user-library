# Workspace Share Bundle Contract (Draft)

## Purpose

This document defines the Milestone 11 sharing-layer contract for:

- durable `share bundles`
- viewer-safe synthetic evidence delivery
- public share paths with expiry and revocation
- audit recording for share creation and revocation

The goal is to let a team share study evidence outside the authenticated workspace shell without dropping the synthetic boundary, study lineage, or run lineage.

## Why this contract exists

Research bottleneck improved:

- export bundles package evidence durably, but real teams still need a controlled way to hand that evidence to viewers who are not operating inside the authenticated workspace shell

What this improves:

- evidence quality
- auditability
- scalable research throughput
- Milestone 11 product usability for review and circulation workflows

Why it matters now:

- project, study, and export bundle objects now exist
- the next user-facing gap is safe viewer delivery, not more raw export plumbing

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/share-bundles`
- `GET /api/v1/share-bundles`
- `GET /api/v1/share-bundles/{share_bundle_id}`
- `POST /api/v1/share-bundles/{share_bundle_id}/revoke`
- `GET /public/v1/share-bundles/{share_key}`

## Object intent

`share_bundle` is a durable product object attached to:

- one `workspace`
- one `export_bundle`
- one `project`
- one `study`
- one `validation job`
- one source `run_id`

Minimum fields:

- `share_bundle_id`
- `workspace_id`
- `export_bundle_id`
- `project_id`
- `study_id`
- `job_id`
- `run_id`
- `title`
- `status`
- `share_key`
- `public_path`
- `share_root`
- `share_payload_path`
- `synthetic_boundary`
- `published_at`
- `expires_at`
- `revoked_at`
- `created_by_user_id`

## Creation rules

### `POST /api/v1/share-bundles`

Request body:

```json
{
  "export_bundle_id": "export_123",
  "title": "Board review share",
  "expires_in_days": 7
}
```

Creation behavior:

1. the selected export bundle must be visible in the current workspace
2. the selected export bundle must already be `published`
3. the runtime creates one opaque `share_key`
4. the runtime materializes a viewer-safe payload under the workspace share root
5. the payload preserves synthetic boundary, source export lineage, study context, and exported file inventory
6. the runtime records an audit event for share creation

Response shape:

```json
{
  "share_bundle": {
    "share_bundle_id": "share_123",
    "export_bundle_id": "export_123",
    "study_id": "study_123",
    "job_id": "job_123",
    "status": "published",
    "public_path": "/public/v1/share-bundles/shk_123",
    "share_file_count": 2,
    "synthetic_boundary": "Synthetic evidence only. This export is derived from synthetic-user research and is not human market proof."
  }
}
```

## Public delivery boundary

### `GET /public/v1/share-bundles/{share_key}`

This is the viewer-safe payload endpoint.

Required behavior:

- no workspace bearer token required
- return only the materialized share payload
- keep `synthetic_boundary`, `project_id`, `study_id`, `job_id`, `run_id`, and `export_bundle_id` visible
- expose only copied share-file metadata, not raw workspace-internal source browsing

When a share is unavailable:

- unknown share key: `404`
- revoked share: `410`
- expired share: `410`

## Persistence boundary

Each created share now persists:

- a row in the runtime relational store
- a directory under `workspaces/<workspace_id>/shares/<share_bundle_id>/`
- `share_payload.json`
- `README.md`
- copied public files under `files/`

## Revocation and expiry

### `POST /api/v1/share-bundles/{share_bundle_id}/revoke`

Revocation behavior:

1. the share status becomes `revoked`
2. `revoked_at` is persisted
3. the public endpoint returns `410 Gone`
4. the runtime records an audit event for revocation

Expiry behavior:

- the runtime persists `expires_at` when provided
- expired shares become `expired` on read and public access returns `410 Gone`

## Audit rule

Share creation now emits:

- action `share_bundle.created`
- actor user id and role
- export, project, study, job, and run lineage
- public path
- expiry state

Share revocation now emits:

- action `share_bundle.revoked`
- actor user id and role
- export, project, study, job, and run lineage
- public path
- revoked timestamp

## Non-goals

This contract does not yet define:

- anonymous download analytics
- approval workflows before publishing a share
- comment threads on shared artifacts
- workspace-wide share policy configuration
- external identity or signed-viewer sessions

Those are later Milestone 11 or post-Milestone 11 collaboration layers.

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
