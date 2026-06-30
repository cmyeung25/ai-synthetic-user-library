# Milestone 22 Design Spec: Team Collaboration and Governance Hardening

Status: `implemented`

## Purpose

Milestone 21 completed the deployment and wrapper boundary. The next bottleneck is real team use:

- decisions can already be recorded and reviewed, but reviewer responsibility is still too implicit
- support snapshots can already be created, but handoff ownership is still too informal
- broader paid-pilot use still needs stronger governance signals than comments and generic audit history alone

This milestone improves `evidence_quality`, `auditability`, and `scalable_research_throughput` by making review and support responsibility explicit inside the study-first workspace.

## Alignment Check

1. Which research bottleneck does this improve?
   It closes the gap between single-operator use and multi-person team review/handoff discipline.
2. Does it improve behavioral realism, decision prediction, evidence quality, calibration, or throughput?
   Primarily `evidence_quality`, `auditability`, and `scalable_research_throughput`.
3. Does it move the platform closer to replacing interviewer-led work instead of only polishing peripheral workflow?
   Yes. Team review and support discipline are required before broader product use can trust synthetic evidence workflows.
4. If not, why is it still necessary now?
   Not applicable. Without it, public-launch preparation remains blocked by governance fragility.

## Current Architecture Decision

- keep collaboration and governance state attached to existing product objects instead of creating detached admin systems
- keep `study`, `decision_log`, and `support_snapshot` as the primary objects for review and handoff
- preserve backend-owned audit events and materialized artifacts as the source of truth for governance history
- avoid introducing separate notification or ticketing systems before responsibility contracts are explicit

## Implemented Slices

The first implemented M22 slice is `review assignment and support handoff discipline`.

It lands four capabilities:

1. explicit decision-review assignment
2. approval/revision permission tied to assignment or owner/admin authority
3. durable support-snapshot handoff status and history
4. study-activity and audit visibility for those governance transitions

## Decision Review Governance

### New endpoint

- `POST /api/v1/decision-logs/{decision_log_id}/review-assignment`

### Review assignment contract

Each decision log now carries backend-owned:

- `review_assignment`
- `review_assignment_history`

Assignment state is attached to the same durable decision-log object as:

- `review_status`
- threaded comments
- evidence linkage
- readiness-gate context

This keeps review governance inside the evidence path instead of creating a detached approval object.

### Permission rule

The key hardening rule is:

- any submitter-capable role may still move a decision into earlier working states such as `in_review`
- only `owner` / `admin` members or explicitly assigned reviewers may move a decision into `approved` or `needs_revision`

That is the first real M22 review-permission boundary.

## Support Handoff Governance

### New endpoint

- `POST /api/v1/support-snapshots/{support_snapshot_id}/handoff`

### Handoff state contract

Each support snapshot now carries backend-owned:

- `handoff`
- `handoff_history`

Supported states:

- `unassigned`
- `assigned`
- `acknowledged`
- `resolved`

### Permission rule

- submitter-capable roles may participate in support handoff updates
- only `owner` / `admin` members may clear assignment
- only the assigned handoff owner or `owner` / `admin` members may acknowledge or resolve the handoff

This makes support snapshots usable as real team handoff objects instead of passive diagnostic dumps.

## Second Implemented Slice

The second implemented M22 slice is `export/share governance history and release visibility`.

It lands four capabilities:

1. append-only export-bundle MVP promotion history
2. append-only share-bundle MVP release-review history
3. propagation of promotion history into share payloads and authenticated share/export summaries
4. study-activity visibility for export promotion and share release-review transitions

### Export governance hardening

`mvp_promotion` no longer stands alone as one latest-state object. Export bundles now also preserve:

- `mvp_promotion_history`

Each request/review transition appends one durable history record with:

- `event`
- `status`
- `changed_at`
- `changed_by_user_id`
- `note`

That same history is then copied into share payloads so bounded partner-facing circulation still carries its approval lineage.

### Share governance hardening

Share bundles now also preserve:

- `mvp_release_review_history`

Each request/review transition appends one durable history record with:

- `event`
- `status`
- `changed_at`
- `changed_by_user_id`
- `note`

This keeps final partner-facing release governance reconstructable instead of reducing it to one current status field.

### Activity implications

The runtime now emits and projects:

- `export_bundle.mvp_promotion_requested`
- `export_bundle.mvp_promotion_reviewed`
- `share_bundle.mvp_release_review_requested`
- `share_bundle.mvp_release_reviewed`

This keeps external-circulation governance inside the same study activity timeline as runs, evidence views, decisions, shares, and support handoff.

## Third Implemented Slice

The third implemented M22 slice is `workspace billing, quota, retention, and policy-governance history`.

It lands four capabilities:

1. append-only billing change history on the workspace billing object
2. append-only quota/retention policy history on the same workspace governance surface
3. optional operator note capture for billing/policy mutations
4. separate audit visibility for `workspace_billing.updated` and `workspace_policy.updated`

### Workspace policy hardening

The workspace settings and billing surface now preserve backend-owned:

- `billing_governance.billing_history`
- `billing_governance.policy_history`

Each history entry carries:

- `event`
- `changed_at`
- `changed_by_user_id`
- `actor_role`
- `note`
- `changes`

This keeps paid-pilot quota, seat, billing-state, and retention changes reconstructable instead of reducing them to one current settings snapshot.

### Audit implications

The runtime now emits:

- `workspace_billing.updated`
- `workspace_policy.updated`

Those events now keep account-state and operational-limit changes queryable from the workspace audit surface while the workspace settings snapshot exposes the same durable history directly.

## Audit And Activity Implications

The runtime now emits:

- `decision_log.review_assignment_updated`
- `support_snapshot.handoff_updated`

Those events now flow into study activity so governance transitions remain visible in the same study timeline as runs, evidence, exports, and shares.

## Completion Review

Milestone 22 is now complete.

What changed in the product:

- decision review now has explicit reviewer assignment and assignment-aware approval permission
- support snapshots now behave as real handoff objects with durable status/history
- export/share circulation review now keeps append-only governance history instead of only latest status
- workspace billing/quota/retention policy changes now keep append-only governance history and separate audit signals

Why this now satisfies M22:

- teams can collaborate on studies and decisions without losing evidence lineage
- governance events are auditable across workspace, decision, support, export, and share objects
- quota, billing, and retention controls now have both runtime effect and durable governance history strong enough for controlled paid pilots

Next milestone decision:

- keep `Milestone 23` next because the main remaining public-launch blocker is no longer team-governance ambiguity, but persona coverage and human-difference calibration depth
- keep `Milestone 24` and `Milestone 25` after that because public launch still depends on longitudinal learning plus high-stakes review boundaries

## Verification

Repository evidence for this slice:

- `src/ai_validation_swarm/saas/runtime.py` now enforces review-assignment-aware decision approval and persists support handoff state/history
- `src/ai_validation_swarm/saas/api.py` now exposes the review-assignment and support-handoff mutation endpoints
- `src/ai_validation_swarm/saas/job_store.py` now supports support-snapshot metadata updates for handoff history
- `tests/unit/test_saas_runtime.py` now verifies:
  - unassigned reviewers cannot approve decisions
  - assigned reviewers can approve decisions
  - support handoff cannot be acknowledged before assignment
  - assigned handoff owners can acknowledge and resolve snapshots
  - both governance events appear in study activity history
- `src/ai_validation_swarm/saas/runtime.py` now persists export/share governance histories and projects promotion/release-review audit events into study activity
- `tests/unit/test_saas_runtime.py` now also verifies promotion/release history persistence plus study-activity visibility for those transitions
- `src/ai_validation_swarm/saas/runtime.py` now persists workspace billing/policy governance histories and returns them through the workspace settings and billing mutation surfaces
- `tests/unit/test_saas_runtime.py` now also verifies billing/policy history persistence plus distinct workspace billing/policy audit actions

## Boundary Statement

These governance flows harden team operation and audit discipline. They do **not** widen the synthetic-evidence claim boundary, and they do **not** imply public-launch readiness by themselves.
