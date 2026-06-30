# Workspace MVP Release Review Contract (Draft)

## Purpose

This document defines the final Milestone 20 release-review contract for bounded design-partner shares.

The goal is to ensure that a design-partner share is not publicly readable just because readiness, promotion, and onboarding exist. One final release-review checkpoint must explicitly approve the partner-facing artifact.

## Why this contract exists

Research bottleneck improved:

- controlled MVP launch still needed one final delivery gate between an internally prepared partner share and an externally readable partner share

What this improves:

- evidence quality
- auditability
- scalable research throughput
- safe bounded market release

Why it matters now:

- M20 already has readiness, promotion, and onboarding
- the last missing gap is the final release decision on the actual partner-facing share artifact

## Endpoints

The local SaaS runtime now exposes:

- `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review-request`
- `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review`

## Object intent

`mvp_release_review` is share-bundle-scoped governance state.

It is backend-owned and persists in share metadata and public payloads.

Minimum fields:

- `contract_version`
- `eligible`
- `status`
- `requested_by_user_id`
- `requested_at`
- `request_note`
- `reviewed_by_user_id`
- `reviewed_at`
- `review_note`
- `checklist`
- `note`
- `mvp_release_review_history`

## Status model

Current statuses:

- `not_applicable`
- `blocked`
- `approval_required`
- `pending_approval`
- `approved`
- `rejected`

Interpretation:

- `not_applicable`: the share is internal-only and does not need controlled MVP release review
- `blocked`: readiness boundaries still block the share before release review can matter
- `approval_required`: the share is fully prepared but still needs final release approval
- `pending_approval`: final release review has been requested and is awaiting owner/admin review
- `approved`: the public share can be delivered to the named design partner
- `rejected`: the release review was rejected; a new request is required before public delivery

## Eligibility checklist

`mvp_release_review.checklist` currently requires:

- `readiness_gate_ok`
- `promotion_approved`
- `partner_onboarding_ready`

If any checklist item is false, the share is not eligible for release review approval.

## Public-read gate

For `mvp_launch_scope.status = design_partner_candidate`:

- public share read is blocked until `mvp_release_review.status = approved`
- approved public read still preserves readiness, promotion, onboarding, and bounded circulation policy in the payload
- approved public read now also preserves `mvp_release_review_history`, so final release can be reconstructed rather than inferred from one latest status

For internal-only shares:

- public read does not require M20 release review

## Governance visibility

The runtime now also emits:

- `share_bundle.mvp_release_review_requested`
- `share_bundle.mvp_release_reviewed`

Those governance actions are projected into study activity so final partner-facing release review stays visible in the same study timeline as the underlying evidence and share object.

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `specs/workspace_share_bundle_contract.md`

## Boundary

This contract still does not prove:

- production deployment readiness
- hosted operational monitoring
- typed production API boundary
- post-M20 launch scale
