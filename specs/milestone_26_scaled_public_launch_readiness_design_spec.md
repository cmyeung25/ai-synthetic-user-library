# Milestone 26 Scaled Public Launch Readiness Design Spec

Status: `implemented`

## Purpose

Milestone 26 addresses the next launch bottleneck after regulated and high-stakes governance. The platform can now run a bounded controlled MVP path, but it still lacks one backend-owned public-launch boundary that tells operators and customers:

- what can be claimed publicly
- what remains research-preview only
- which benchmark disclosures must travel with customer-facing artifacts
- which operations and support boundaries still block broader self-serve launch

This milestone improves:

- evidence quality
- auditability
- scalable research throughput
- customer-facing launch discipline

It moves the platform closer to replacing interviewer-led work because broader launch requires trustworthy claim limits and benchmark disclosure around the same evidence engine, not only more SaaS surface.

## Architecture Alignment

1. Research bottleneck improved:
   controlled MVP circulation exists, but broader launch still depends on backend-owned public-claim posture and benchmark disclosure instead of page-local interpretation.
2. Platform dimension improved:
   evidence quality, calibration visibility, auditability, and scalable research throughput.
3. Replacement-work relevance:
   yes. Public launch without bounded claim discipline would weaken trust in the simulation engine and risk over-claiming synthetic evidence.
4. Why this work now:
   M25 completed the governed high-stakes boundary, so the next missing launch blocker is customer-facing launch discipline, not more high-stakes plumbing.

## Milestone Scope

- define backend-owned public-claim boundaries for broader customer-facing circulation
- harden benchmark disclosure, launch-readiness summary, and customer-facing boundary language
- harden onboarding, pricing, billing operations, support playbooks, and public documentation for ordinary multi-team use
- keep self-serve launch bounded to supported use cases without implying replacement-grade reliability

## Planned Slices

### First Active Slice

Add `public claims boundary and benchmark disclosure` so the platform can:

- derive one backend-owned `public_claims_boundary` from readiness-gate, launch-scope, governed-review, and governed-redaction state
- expose one authenticated `workspace_public_launch_readiness` summary for operator launch review
- keep customer-facing claim limits attached to export and share artifacts instead of page-local interpretation

### Second Slice

Add `customer operations and support readiness pack` so broader launch can:

- expose support playbook readiness and ordinary-study support boundaries
- keep launch-readiness blockers visible from the same backend-owned summary
- avoid manual operator memory as the launch gate

### Third Slice

Add `self-serve onboarding and pricing boundary` so broader launch can:

- define which onboarding paths are supported for ordinary studies
- define which pricing, billing, and quota states are safe for self-serve teams
- keep unsupported launch paths blocked with explicit product-language reasons

### Fourth Slice

Run the M26 completion review and decide whether broader public launch is actually credible or whether more calibration, support, privacy, or enterprise hardening is still required first.

## Initial Technical Boundary

- keep public-claim posture backend-owned in `src/ai_validation_swarm/saas/runtime.py`
- derive launch-readiness from existing readiness-gate, calibration, governed-boundary, and MVP-circulation contracts instead of introducing a second claim heuristic in frontend code
- expose one authenticated API route for workspace launch-readiness review
- project the same public-claims boundary into export and share artifacts so customer-facing distribution keeps benchmark disclosure and claim limits attached
- preserve the synthetic-evidence boundary explicitly; this milestone is about bounded launch discipline, not replacement-grade proof

## Proposed Story Breakdown

1. `story.public_launch.public_claims_boundary_and_benchmark_disclosure` - `implemented` - `5 SP`
   Outcome: public-facing claim posture and benchmark disclosure become explicit backend-owned runtime and artifact surface.

2. `story.public_launch.customer_operations_and_support_boundary` - `implemented` - `5 SP`
   Outcome: broader public launch can inspect support and customer-operations blockers without relying on manual operator memory.

3. `story.public_launch.self_serve_onboarding_and_pricing_boundary` - `implemented` - `8 SP`
   Outcome: onboarding, pricing, billing, and quota boundaries for broader ordinary-team use become explicit and testable.

4. `story.public_launch.exit_review` - `implemented` - `3 SP`
   Outcome: Milestone 26 can close only after bounded public-launch claims and customer operations are credible enough for broader circulation.

## Verification Plan

- runtime tests for authenticated public-launch-readiness summary and public-claims-boundary projection
- API contract tests for the new launch-readiness route plus service-metadata and contract-manifest exposure
- export/share contract tests proving customer-facing claim limits remain attached to distributed artifacts
- milestone review confirming broader launch claims remain backend-owned and benchmark-scoped rather than UI-banner-only

## Repository Evidence

- `specs/workspace_public_launch_readiness_contract.md` now defines the backend-owned launch-readiness and public-claims-boundary contract.
- `src/ai_validation_swarm/saas/runtime.py` now exposes `describe_workspace_public_launch_readiness()` and derives `public_claims_boundary` from readiness-gate, launch-scope, governed-review, and governed-redaction state.
- the same runtime now projects `public_claims_boundary` into export-bundle summaries, share-bundle summaries, export manifests, share payloads, and public-share payloads.
- `src/ai_validation_swarm/saas/api.py` now exposes `GET /api/v1/public-launch-readiness` and publishes it through service metadata plus the contract manifest.
- `tests/unit/test_saas_runtime.py` now verifies launch-readiness endpoint authorization, operations-summary inclusion, and controlled-MVP public-claims-boundary projection.
- the same runtime now also exposes backend-owned `launch_blockers` plus `customer_operations_support_boundary`, derived from workspace billing/quota state, submission-gate rules, failed-job support coverage, and durable support handoff history.
- `tests/unit/test_saas_runtime.py` now also verifies bounded-ready support posture for ordinary studies plus explicit blocker transitions when failed jobs lack support snapshots or active handoffs remain open.
- the same runtime now also exposes backend-owned `self_serve_onboarding_pricing_boundary`, derived from plan tier, billing status, price-book alignment, seat count, effective quota/retention limits, owner/submitter membership, and active token state.
- `tests/unit/test_saas_runtime.py` now verifies both trial/setup-required blockers and bounded-ready paid-plan self-serve posture after billing and quota updates.

## Completion Review

Milestone 26 is complete as a bounded public-launch-readiness layer.

Implemented evidence:

- public-facing claim posture is backend-owned through `public_claims_boundary` and remains attached to export/share artifacts
- benchmark disclosure and readiness-gate state are summarized through `workspace_public_launch_readiness`
- customer operations and support blockers are backend-owned through `customer_operations_support_boundary`
- self-serve onboarding, pricing, billing, quota, retention, member, and token requirements are backend-owned through `self_serve_onboarding_pricing_boundary`
- aggregate `launch_blockers` make claim, support, onboarding, billing, and quota blockers visible from one authenticated summary

Closure decision:

- close Milestone 26 as `implemented`
- broader bounded public/self-serve launch can now be evaluated from backend-owned launch posture
- replacement-grade claims remain explicitly out of scope and still require later review-board and multi-market benchmark milestones
- keep Milestone 27 next because public launch wording still needs dedicated messaging validation before acquisition or public positioning is scaled

## Boundary

This milestone does not prove that the platform is already ready for unrestricted public launch.

It completes the bounded public-launch-readiness layer required before broader self-serve claims can be evaluated responsibly.
