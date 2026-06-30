# Workspace Partner Onboarding Contract (Draft)

## Purpose

This document defines the Milestone 20 share-time onboarding contract for approved design-partner circulation.

The goal is to ensure that an approved design-partner share always carries:

- named partner context
- bounded circulation policy
- explicit synthetic-evidence acknowledgements
- support and review expectations

## Why this contract exists

Research bottleneck improved:

- promotion approval can now unlock design-partner circulation, but controlled MVP launch still needs one partner-facing onboarding pack so approved shares are bounded by policy instead of informal operator explanation

What this improves:

- evidence quality
- auditability
- scalable research throughput
- safer MVP delivery for the first real external users

Why it matters now:

- M20 is no longer blocked only by approval workflow
- the next gap is making approved external circulation self-describing and bounded

## Contract location

`partner_onboarding` now lives inside share payloads and share-bundle metadata for any design-partner-candidate share.

It is backend-owned and created at share-creation time.

## Minimum fields

- `contract_version`
- `status`
- `partner_name`
- `partner_team_label`
- `partner_use_case`
- `study_title`
- `study_status`
- `support_channel`
- `review_window_days`
- `required_acknowledgements`
- `circulation_policy`
- `note`

## Status model

Current statuses:

- `not_applicable`
- `blocked`
- `approval_or_partner_context_required`
- `ready`

Interpretation:

- `not_applicable`: the share is internal-only and does not need partner onboarding
- `blocked`: readiness or launch scope still blocks partner circulation
- `approval_or_partner_context_required`: design-partner circulation is conceptually possible, but required approval or named partner context is still missing
- `ready`: the share can circulate to the named design partner under the attached bounded policy

## Share creation rule

For `mvp_launch_scope.status = design_partner_candidate`:

1. `mvp_promotion.status` must already be `approved`
2. `partner_name` is required
3. `partner_use_case` is required
4. the runtime materializes one backend-owned `partner_onboarding` object
5. the same object persists in share metadata and public payload

Current optional inputs:

- `partner_team_label`
- `support_channel`
- `review_window_days`

## Circulation policy

`partner_onboarding.circulation_policy` now defines:

- the named audience
- whether resharing is allowed
- which research workflows are allowed
- which actions remain prohibited
- the boundary note that must stay visible during circulation

Current bounded policy:

- audience: `named_design_partner_team`
- resharing: `false`
- allowed use cases:
  - `discovery_review`
  - `concept_evaluation_review`
  - `prototype_validation_review`
- prohibited actions:
  - `public_marketing_claims`
  - `replacement_grade_claims`
  - `high_stakes_approval_without_human_review`
  - `secondary_external_reshare`

## Verification

Repository coverage:

- `tests/unit/test_saas_runtime.py`

Current implementation entrypoints:

- `src/ai_validation_swarm/saas/runtime.py`
- `src/ai_validation_swarm/saas/api.py`
- `specs/workspace_share_bundle_contract.md`

## Boundary

This contract still does not prove:

- partner workspace provisioning
- partner-specific template bundles
- commercial pilot support operations
- final M20 release review
