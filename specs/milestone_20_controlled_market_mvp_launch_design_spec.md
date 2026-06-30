# Milestone 20 Controlled Market MVP Launch Design Spec

Status: `in_progress`

## Purpose

Milestone 20 turns readiness-gated evidence into a bounded design-partner MVP operating layer.

The platform now has calibrated evidence boundaries, but it still needs one explicit launch scope that says whether a study artifact is internal-only, blocked, or suitable for controlled design-partner circulation. Without that layer, the system can generate readiness state but cannot yet package a disciplined MVP launch path.

## First Implemented Slice

The first M20 slice adds backend-owned `mvp_launch_scope` projection on top of `readiness_gate`.

The implemented launch scope now:

- classifies launch state as `internal_only`, `blocked`, or `design_partner_candidate`
- keeps launch scope backend-owned instead of page-local interpretation
- persists the same launch scope into export manifests, export bundle summaries, share payloads, and share bundle summaries
- makes design-partner eligibility depend on readiness-gated evidence rather than generic product-shell availability

## Architecture Alignment

1. Research bottleneck improved: the platform can now judge evidence readiness, but still lacked an explicit controlled-MVP packaging layer for real design-partner use.
2. This improves evidence quality, calibration usability, and scalable research throughput.
3. It moves the platform closer to replacing interviewer-led setup work because a bounded launch path can now be attached to study outputs instead of relying on manual interpretation.
4. This is necessary now because the first market release must be controlled by evidence scope, not only by internal operator judgment.

## Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` now derives `mvp_launch_scope` from backend-owned readiness-gate state.
- the same runtime now writes `mvp_launch_scope` into export manifests, export bundle summaries, share payloads, and share bundle summaries.
- `tests/unit/test_saas_runtime.py` now verifies:
  - uncalibrated evidence remains `internal_only`
  - high-stakes human-review-required evidence remains `blocked`
  - scoped externally ready evidence becomes `design_partner_candidate`

## Second Implemented Slice

The second M20 slice adds explicit design-partner promotion review on top of `mvp_launch_scope`.

The implemented promotion workflow now:

- derives backend-owned `mvp_promotion` state from `mvp_launch_scope`
- persists request/review state inside export-bundle manifests, export/share summaries, and share payloads
- adds explicit request and review endpoints for design-partner circulation approval
- blocks `design_partner_candidate` public share creation until promotion review is `approved`

Additional repository evidence:

- `specs/workspace_mvp_promotion_contract.md` now defines the promotion request/review contract and share gate.
- `src/ai_validation_swarm/saas/runtime.py` now exposes export-bundle-scoped promotion request/review methods and enforces approval before partner-facing share creation.
- `src/ai_validation_swarm/saas/api.py` now exposes:
  - `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request`
  - `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review`
- `tests/unit/test_saas_runtime.py` now verifies:
  - design-partner-candidate shares are blocked before approval
  - promotion can move through `approval_required -> pending_approval -> approved`
  - approved design-partner-candidate exports can create bounded public shares

## Third Implemented Slice

The third M20 slice adds bounded partner onboarding and circulation policy to approved design-partner shares.

The implemented onboarding layer now:

- requires named partner context before an approved design-partner-candidate share can be created
- writes one backend-owned `partner_onboarding` pack into share metadata and public payload
- attaches bounded circulation policy, required synthetic-evidence acknowledgements, support channel, and review-window guidance to the same partner-facing share
- prevents approved design-partner circulation from depending on operator memory or ad hoc email explanation

Additional repository evidence:

- `specs/workspace_partner_onboarding_contract.md` now defines the bounded partner-onboarding and circulation-policy contract.
- `src/ai_validation_swarm/saas/runtime.py` now derives `partner_onboarding` from approved promotion state plus named partner context and persists it into share payloads and summaries.
- `src/ai_validation_swarm/saas/api.py` now accepts partner context fields during share creation for approved design-partner circulation.
- `tests/unit/test_saas_runtime.py` now verifies:
  - approved design-partner shares still fail when partner context is missing
  - approved design-partner shares persist a `ready` onboarding pack when partner context is provided
  - public share payloads preserve bounded circulation-policy state for the named partner share

## Fourth Implemented Slice

The fourth M20 slice adds final controlled release review on the actual partner-facing share artifact.

The implemented release-review layer now:

- derives backend-owned `mvp_release_review` state on top of launch scope, promotion approval, and partner onboarding readiness
- keeps approved design-partner shares non-public until final release review approval is recorded
- adds explicit request and review endpoints for the actual public share artifact
- re-checks final release-review status during public share read instead of trusting create-time assumptions alone

Additional repository evidence:

- `specs/workspace_mvp_release_review_contract.md` now defines the final share-scoped release-review contract.
- `src/ai_validation_swarm/saas/runtime.py` now derives `mvp_release_review`, persists it into share payloads/summaries, and blocks public read until approval exists.
- `src/ai_validation_swarm/saas/api.py` now exposes:
  - `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review-request`
  - `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review`
- `tests/unit/test_saas_runtime.py` now verifies:
  - approved design-partner shares start with `approval_required`
  - public read stays blocked until final release review is approved
  - approved release review unlocks bounded public delivery

## Milestone Completion Review

Milestone 20 is now complete.

Implemented capability now proves:

- launch scope, promotion review, partner onboarding, and final release review all stay backend-owned
- design-partner circulation is gated at the export, share-creation, onboarding, and public-delivery layers
- the first controlled MVP launch path now exists without collapsing synthetic evidence into public-proof claims

Current platform state after completion:

- strongest improvement: the platform can now package one bounded design-partner MVP path from calibrated evidence through actual partner-facing release review
- most important remaining bottleneck: production deployment and typed API boundary are still missing, so the MVP is controlled and local-first rather than production-hardened
- sequencing decision: move to Milestone 21, because the next gap is deployment/runtime boundary hardening rather than more M20 circulation policy

## Boundary

It proves:

- launch scope is now a backend-owned contract rather than implicit launch interpretation
- design-partner circulation can be tied to readiness state
- partner-facing circulation now requires explicit approval instead of relying on implicit operator judgment
- approved partner-facing circulation now carries a backend-owned onboarding pack and bounded circulation policy instead of depending on informal handoff
- actual public delivery now requires a final release-review approval on the share artifact itself
- customer-facing launch packaging is beginning to separate internal-only evidence from bounded MVP candidates

It does not yet prove:

- production deployment readiness, hosted operations, or typed API hardening
