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
- `readiness_gate`
- `public_claims_boundary`
- `mvp_launch_scope`
- `mvp_promotion`
- `mvp_promotion_history`
- `partner_onboarding`
- `mvp_release_review`
- `mvp_release_review_history`
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
  "expires_in_days": 7,
  "partner_name": "Acme Design Partner",
  "partner_team_label": "Research Ops",
  "partner_use_case": "prototype_validation_review",
  "support_channel": "partner-success@acme.test",
  "review_window_days": 10
}
```

Creation behavior:

1. the selected export bundle must be visible in the current workspace
2. the selected export bundle must already be `published`
3. the runtime creates one opaque `share_key`
4. the runtime materializes a viewer-safe payload under the workspace share root
5. the runtime rejects creation when the inherited readiness gate requires restricted human review rather than boundary-only circulation
6. the runtime also rejects `design_partner_candidate` public share creation until the source export bundle has an approved MVP promotion state
7. approved `design_partner_candidate` shares must also provide named partner context before creation succeeds
8. approved `design_partner_candidate` shares are still created with a pending final release-review state before public delivery is allowed
9. the payload preserves synthetic boundary, source export lineage, study context, exported file inventory, one backend-owned readiness gate, one backend-owned MVP launch scope, one backend-owned MVP promotion state plus promotion history, one backend-owned partner onboarding pack, and one backend-owned MVP release-review state plus release history
10. the payload also preserves one backend-owned `public_claims_boundary` so broader customer-facing claim limits and benchmark disclosure stay attached to the shared artifact
11. the runtime records an audit event for share creation

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
      "applied_redactions": [
        {
          "path": "study_context.research_intent",
          "reason": "Protect sensitive workflow detail."
        }
      ]
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
    },
    "partner_onboarding": {
      "status": "not_applicable",
      "partner_name": "",
      "partner_use_case": "",
      "circulation_policy": {
        "status": "internal_only"
      }
    },
    "mvp_release_review": {
      "status": "not_applicable",
      "eligible": false
    }
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
- keep `readiness_gate` visible so viewers cannot mistake shared synthetic evidence for customer-validated proof
- keep `provider_runtime_boundary` visible so viewers can tell whether the evidence was mock demo output or live synthetic evidence
- keep `governed_review` visible so regulated/high-stakes reviewer responsibility and human-review-required policy labels remain attached to the shared artifact
- keep `governed_redaction` and `compliance_audit_bundle` visible so viewer-safe masking and the reason for each redaction remain reconstructable on the shared artifact
- keep `public_claims_boundary` visible so customer-facing claim posture, benchmark disclosure, and replacement-grade prohibitions remain attached to the shared artifact
- keep `mvp_launch_scope` visible so viewers can see whether the share is internal-only, blocked, or design-partner-candidate circulation
- keep `mvp_promotion` visible so viewers can see whether design-partner circulation was explicitly approved
- keep `mvp_promotion_history` visible so viewers and operators can reconstruct the bounded-circulation approval path
- keep `partner_onboarding` visible so named-partner circulation, acknowledgements, support path, and resharing boundaries remain explicit
- keep `mvp_release_review` visible so partner-facing delivery still reflects the final release decision on the actual public artifact
- keep `mvp_release_review_history` visible so the final release decision is not reduced to one latest-status field
- expose only copied share-file metadata, not raw workspace-internal source browsing

When a share is unavailable:

- unknown share key: `404`
- revoked share: `410`
- expired share: `410`
- pending or unapproved design-partner release review: `410`
- regulated/high-stakes governed reviewer assignment missing or escalated: share creation is blocked before publication

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
- readiness status
- provider name, evidence mode, and provider runtime status
- MVP launch-scope status
- MVP promotion status
- partner onboarding status
- MVP release-review status
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
