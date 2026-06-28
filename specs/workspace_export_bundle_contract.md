# Workspace Export Bundle Contract (Draft)

## Purpose

This document defines the first Milestone 11 export-layer contract for:

- durable `export bundles`
- study-scoped evidence packaging
- explicit synthetic boundary preservation
- audit recording for export creation

The goal is to let a real team package synthetic evidence from a selected study and completed run without dropping lineage, boundary language, or workspace ownership.

## Why this contract exists

Research bottleneck improved:

- the platform can already run studies and review evidence, but a real product still needs a durable way to carry study evidence into downstream decision workflows

What this improves:

- evidence quality
- auditability
- scalable research throughput
- Milestone 11 product usability beyond the operator shell

Why it matters now:

- project and study objects now exist
- the next product-layer gap is safe export, not more raw runtime plumbing

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/export-bundles`
- `GET /api/v1/export-bundles`
- `GET /api/v1/export-bundles/{export_bundle_id}`

## Object intent

`export_bundle` is a durable product object attached to:

- one `workspace`
- one `project`
- one `study`
- one completed `validation job`
- one source `run_id`

Minimum fields:

- `export_bundle_id`
- `workspace_id`
- `project_id`
- `study_id`
- `job_id`
- `run_id`
- `title`
- `status`
- `export_format`
- `bundle_root`
- `manifest_path`
- `exported_files`
- `synthetic_boundary`
- `created_by_user_id`
- `created_at`

## Supported export formats

Current first-pass formats:

- `bundle_json`
- `report_markdown`
- `report_json`
- `report_csv`

## Creation rules

### `POST /api/v1/export-bundles`

Request body:

```json
{
  "study_id": "study_123",
  "job_id": "job_123",
  "title": "Exec review export",
  "export_format": "report_csv",
  "artifact_ids": ["report.json", "summary.json"]
}
```

Creation behavior:

1. the selected study must be visible in the current workspace
2. the selected job must be visible in the current workspace
3. the selected job must be `completed`
4. the selected job metadata must point back to the selected study
5. the runtime resolves the source `run_id` and run artifact directory
6. the runtime materializes a durable bundle under the workspace export root
7. the bundle always writes a manifest and synthetic-boundary context
8. the runtime records an audit event for export creation

Response shape:

```json
{
  "export_bundle": {
    "export_bundle_id": "export_123",
    "study_id": "study_123",
    "job_id": "job_123",
    "run_id": "run_20260628_123456",
    "title": "Exec review export",
    "status": "published",
    "export_format": "report_csv",
    "exported_file_count": 1,
    "synthetic_boundary": "Synthetic evidence only. This export is derived from synthetic-user research and is not human market proof."
  }
}
```

## Persistence boundary

Each created bundle now persists:

- a row in the runtime relational store
- a bundle directory under `workspaces/<workspace_id>/exports/<export_bundle_id>/`
- `export_manifest.json`
- `README.md`
- one or more exported files derived from the source run artifacts

## Audit rule

Export creation now emits an audit event with:

- actor user id
- actor role
- action `export_bundle.created`
- target id
- project, study, job, and run lineage
- export format
- manifest path

## Non-goals

This first contract does not yet define:

- the share-bundle lifecycle, revocation, or expiry rules
- viewer-facing public delivery payloads
- project-level export approval policy
- export expiration workflows
- download authorization beyond workspace visibility

Those are layered separately in `specs/workspace_share_bundle_contract.md`.

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
