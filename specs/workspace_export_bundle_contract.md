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
- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request`
- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review`

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
- `readiness_gate`
- `public_claims_boundary`
- `mvp_launch_scope`
- `mvp_promotion`
- `mvp_promotion_history`
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
8. the bundle now also writes one backend-owned readiness gate so downstream surfaces do not invent customer-facing claim policy
9. the bundle now also writes one backend-owned MVP launch scope so circulation rules do not depend on page-local interpretation
10. the bundle now also writes one backend-owned MVP promotion state so design-partner circulation requires explicit approval instead of implicit operator judgment
11. the bundle now also preserves append-only `mvp_promotion_history` so later partner-facing circulation can show who requested and reviewed promotion
12. the bundle now also writes one backend-owned `governed_review` projection so regulated/high-stakes reviewer responsibility and policy labels stay visible outside page-local UI state
13. the bundle now also writes one backend-owned `governed_redaction` projection plus `compliance_audit_bundle` so viewer-safe circulation policy and audit reconstruction remain durable
14. the bundle now also writes one backend-owned `public_claims_boundary` so broader customer-facing claim posture and benchmark disclosure do not depend on page-local interpretation
15. the runtime records an audit event for export creation

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
    "synthetic_boundary": "Synthetic evidence only. This export is derived from synthetic-user research and is not human market proof.",
    "readiness_gate": {
      "status": "human_validation_required",
      "market_claims_allowed": false,
      "distribution_note": "Synthetic evidence may be shared only with explicit boundary language until human calibration is attached."
    },
    "provider_runtime_boundary": {
      "provider_name": "mock",
      "evidence_mode": "mock_demo",
      "runtime_status": "completed",
      "boundary_message": "This provider creates mock demo evidence for product flow testing only."
    },
    "public_claims_boundary": {
      "status": "research_preview_only",
      "customer_claim_status": "synthetic_preview_only"
    },
    "governed_review": {
      "review_gate_status": "assigned_for_review",
      "human_review_required": true
    },
    "governed_redaction": {
      "status": "active",
      "rule_count": 2
    },
    "compliance_audit_bundle": {
      "status": "ready",
      "study_id": "study_123"
    },
    "mvp_launch_scope": {
      "status": "internal_only",
      "launch_type": "not_launch_ready",
      "allowed_audiences": ["internal_team"],
      "share_allowed": true,
      "market_claims_allowed": false
    },
    "mvp_promotion": {
      "status": "not_applicable",
      "eligible": false,
      "share_requires_approval": false
    }
  }
}
```

## MVP promotion workflow

When an export bundle becomes `design_partner_candidate`, the same export object can now move through a bounded promotion workflow before any partner-facing public share is created.

See `specs/workspace_mvp_promotion_contract.md` for:

- promotion request rules
- review rules
- approval statuses
- share gating for design-partner-candidate exports

## Persistence boundary

Each created bundle now persists:

- a row in the runtime relational store
- a bundle directory under `workspaces/<workspace_id>/exports/<export_bundle_id>/`
- `export_manifest.json`
- `README.md`
- one or more exported files derived from the source run artifacts

The manifest now keeps `public_claims_boundary` attached so benchmark disclosure, customer-facing claim limits, and replacement-grade prohibitions remain durable on the exported artifact.

The manifest and export-bundle summary also keep `provider_runtime_boundary` attached so exported artifacts preserve whether the evidence was `mock_demo`, `live_synthetic`, or `unsupported`.

## Audit rule

Export creation now emits an audit event with:

- actor user id
- actor role
- action `export_bundle.created`
- target id
- project, study, job, and run lineage
- export format
- readiness status
- provider name, evidence mode, and provider runtime status
- MVP launch-scope status
- MVP promotion status
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
