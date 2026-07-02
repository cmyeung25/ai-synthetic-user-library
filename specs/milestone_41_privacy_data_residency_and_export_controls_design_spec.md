# Milestone 41: Privacy, Data Residency, and Export Controls Design Spec

Status: implemented.

Owner layer: SaaS runtime, API contract manifest, Frontline Research Studio governance surface, export/share boundary.

Last updated: 2026-07-02.

## Purpose

Milestone 41 makes customer data handling explicit before broader customer, team, enterprise, or public-launch expansion.

The research bottleneck is trust in the evidence pipeline. Users need to upload artifacts, run synthetic interviews, inspect transcripts and traces, export findings, and share decisions without losing control of retained, redacted, deleted, or synthetic-only material. If privacy and export handling are implicit, the platform cannot credibly expose raw transcript or reasoning-trace evidence to real users.

## Alignment Check

- Research bottleneck improved: users can safely review and distribute simulated research artifacts while preserving evidence lineage and auditability.
- Primary improvements: evidence quality, auditability, customer readiness, and scalable research throughput.
- North-star fit: replacing parts of interviewer-led work requires inspectable raw evidence, but raw evidence must stay governed by retention, redaction, deletion, data-residency, and synthetic-evidence boundaries.

## Scope

M41 adds one backend-owned governance contract:

- `workspace-privacy-export-controls/v1`

The contract covers:

- workspace isolation and local-first storage boundary
- declared data-residency policy
- artifact retention behavior for uploaded artifacts, generated evidence, exports, shares, and calibration records
- deletion request recording without destroying evidence lineage by default
- governed redaction audit lineage
- export/share status, expiry, review, and synthetic-only boundary copy
- readiness blockers for broader customer review

## User-Facing Product Placement

This is not a top-level research workflow step.

Frontline placement:

- `/studio`: workspace overview card showing privacy/export readiness, retention days, residency region, exports, shares, and blockers.
- `/studio/share/{share_bundle_id}`: share review card showing the same privacy/export boundary before circulation.

No global navigation item is required for M41. The controls support governance around studies, runs, evidence, exports, and shares without replacing the study-first workspace.

## Data and API Contract

Read endpoint:

- `GET /api/v1/privacy-export-controls`

Optional query parameters:

- `study_id`
- `export_bundle_id`
- `share_bundle_id`

Mutation endpoints:

- `POST /api/v1/privacy-export-controls/policy`
- `POST /api/v1/privacy-export-controls/deletion-requests`

Policy payload fields:

- `data_residency_region`
- `artifact_retention_days`
- `deletion_request_policy`
- `export_review_required`
- `share_default_expiry_days`
- `note`

Deletion request payload fields:

- `scope_type`
- `scope_id`
- `reason`
- `requested_action`
- `approval_note`

Deletion requests are append-only governance events. They do not silently erase run history, transcript provenance, or decision lineage. Share-bundle deletion requests may revoke the share when the requested action is `revoke_share`, `delete_or_revoke`, or `delete`.

## Evidence Boundary Rules

- Uploaded artifacts, transcript exchanges, facilitator traces, synthetic participant reasoning traces, generated findings, reports, calibration records, exports, and shares are simulated research artifacts.
- Privacy controls can retain, redact, revoke, mark for deletion, or purge payloads, but must preserve why the action happened and which downstream outputs were affected.
- Synthetic participant reasoning traces must not be described as real human inner thoughts.
- Deletion or redaction must not turn synthetic evidence into human proof or market proof.

## Local-First to SaaS Boundary

The current implementation is local-first:

- SQLite stores workspace settings, policy history, deletion requests, share/export metadata, and audit events.
- Filesystem artifacts remain the local development record for generated evidence and exports.

Future SaaS/cloud implementation must enforce the same contract through:

- production database records
- object storage
- backup and restore policy
- storage-region placement
- worker placement
- audit retention

Production SaaS must not treat server local disk as the durable source of truth.

## Acceptance Criteria

- A workspace can read one privacy/export controls summary with retention, residency, deletion, redaction, export/share, lineage, audit, and readiness fields.
- Privacy policy mutations update data residency, artifact retention, deletion policy, export review, share expiry, policy history, and audit events.
- Deletion requests preserve reason, requester, scope, affected jobs/runs/exports/shares, and lineage-retained status.
- Share-bundle deletion requests can revoke the share while preserving the deletion request and audit trail.
- Frontline workspace and share surfaces explain retained, redacted, deleted, and synthetic-only material without exposing raw storage implementation language as the primary user model.
- Contract manifest and service metadata list the M41 endpoints.
- Tests verify read, policy update, deletion request, and audit behavior.

## Implemented Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` exposes `describe_workspace_privacy_export_controls`, `update_workspace_privacy_policy`, and `record_workspace_privacy_deletion_request`.
- `src/ai_validation_swarm/saas/api.py` exposes `GET /api/v1/privacy-export-controls`, `POST /api/v1/privacy-export-controls/policy`, and `POST /api/v1/privacy-export-controls/deletion-requests`.
- `frontend/frontline_research_studio/src/main.jsx` renders `#privacy-export-controls-card` on the workspace overview and `#share-privacy-boundary` on share review.
- `tests/unit/test_saas_runtime.py` verifies the privacy/export controls API, policy mutation, deletion request recording, and audit events.

## Roadmap Impact

M41 completes the customer-data-control gate required before integration events, webhooks, procurement packs, or broader customer onboarding.

The next milestone should keep the user's requested live-interview visibility in scope by promoting run progress from polling-only UI into bounded integration/run-event contracts. True streaming, webhooks, and observed-interview event delivery should not bypass the M41 privacy/export controls or M37 transcript/trace evidence boundaries.
