# Workspace MVP Promotion Contract (Draft)

## Purpose

This document defines the Milestone 20 promotion-review contract that sits between:

- readiness-gated export bundles
- controlled design-partner circulation
- public share creation for bounded MVP delivery

The goal is to stop `design_partner_candidate` evidence from going public by default. A candidate export must first move through an explicit request-and-review workflow.

## Why this contract exists

Research bottleneck improved:

- the platform can already classify launch scope, but controlled MVP launch still needs one explicit approval layer before a candidate study bundle can circulate to design partners

What this improves:

- evidence quality
- calibration discipline
- auditability
- scalable research throughput for controlled market release

Why it matters now:

- Milestone 19 already protects readiness boundaries
- the next M20 gap is not more readiness scoring, but explicit partner-facing approval workflow

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request`
- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review`

## Object intent

`mvp_promotion` is export-bundle-scoped governance state.

It is derived from `mvp_launch_scope`, then persisted inside export/share metadata so the same approval state can travel with the distribution artifact.

Minimum fields:

- `contract_version`
- `eligible`
- `status`
- `target_audience`
- `share_requires_approval`
- `requested_by_user_id`
- `requested_at`
- `request_note`
- `reviewed_by_user_id`
- `reviewed_at`
- `review_note`
- `note`
- `mvp_promotion_history`

## Status model

Current statuses:

- `not_applicable`
- `blocked`
- `approval_required`
- `pending_approval`
- `approved`
- `rejected`

Interpretation:

- `not_applicable`: the export is internal-only, so no design-partner promotion exists
- `blocked`: readiness gates already block circulation, so promotion is unavailable
- `approval_required`: the export is a design-partner candidate, but no request has been submitted
- `pending_approval`: a bounded external-circulation request is waiting for owner/admin review
- `approved`: the export can create partner-facing public shares
- `rejected`: the prior request was rejected; a fresh request is required before approval

## Request rule

### `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request`

Request body:

```json
{
  "note": "Request approval for bounded design-partner circulation."
}
```

Creation behavior:

1. the export bundle must be visible in the current workspace
2. the caller must have an export-capable role
3. the export bundle must already be `design_partner_candidate`
4. the export bundle must not already be `approved` or `pending_approval`
5. the runtime persists `pending_approval` into export-bundle metadata and manifest state
6. the runtime appends one `requested` entry to `mvp_promotion_history`
7. the runtime records an audit event for the request

## Review rule

### `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review`

Request body:

```json
{
  "decision": "approved",
  "note": "Approved for controlled MVP circulation."
}
```

Review behavior:

1. the export bundle must be visible in the current workspace
2. the caller must hold an owner/admin review role
3. the export bundle must currently be `pending_approval`
4. `decision` must be `approved` or `rejected`
5. the runtime persists the reviewed state into export-bundle metadata and manifest state
6. the runtime appends one `reviewed` entry to `mvp_promotion_history`
7. the runtime records an audit event for the review

## Share gate rule

For `mvp_launch_scope.status = design_partner_candidate`:

- public share creation is blocked until `mvp_promotion.status = approved`
- public share payloads preserve the same `mvp_promotion` object and `mvp_promotion_history`
- public share read re-checks that the payload still carries `approved` promotion state

## Governance visibility

The runtime now also emits:

- `export_bundle.mvp_promotion_requested`
- `export_bundle.mvp_promotion_reviewed`

Those governance actions are projected into study activity so partner-facing circulation review remains visible inside the same study timeline as evidence, decisions, exports, shares, and support.

For `internal_only` exports:

- boundary-only internal shares can still be created without MVP promotion

For `blocked` exports:

- readiness-gate restrictions still block public share creation first

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/job_store.py`
- `src/ai_validation_swarm/saas/api.py`

## Boundary

This contract does not yet prove:

- automated partner provisioning
- partner-specific workspace policy
- commercial pilot billing workflow
- final public-launch readiness
