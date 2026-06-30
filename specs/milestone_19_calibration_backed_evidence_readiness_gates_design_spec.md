# Milestone 19 Calibration-Backed Evidence Readiness Gates Design Spec

Status: `implemented`

## Purpose

Milestone 19 turns calibration output into backend-owned readiness gates for evidence review, decision review, export, and sharing.

The research bottleneck is no longer raw evidence access. The platform can already produce evidence reliability, cross-run comparison, audit lineage, external benchmark calibration, and richer discovery workflow evidence. The remaining gap before a controlled MVP is distribution discipline: customer-facing surfaces still need an explicit gate that says whether evidence is only synthetic, fixture-calibrated, directionally externally calibrated, scoped externally ready, or still blocked by human review.

## First Implemented Slice

The first M19 slice adds a backend-owned `readiness_gate` layer on top of evidence reliability and human calibration.

The implemented gate now:

- derives one readiness status from completed-run evidence reliability plus attached `human_calibration.json`
- keeps `market_claims_allowed` false unless scoped external calibration reaches `candidate_replacement_ready`
- carries the same readiness gate into evidence views, decision logs, export bundles, and share bundles
- preserves synthetic-boundary language even when sharing remains technically allowed

Current implemented readiness statuses:

- `pending`
- `human_validation_required`
- `fixture_only`
- `directional_only`
- `scoped_external_ready`
- `human_review_required`
- `insufficient_benchmarking`

## Architecture Alignment

1. Research bottleneck improved: market-facing workflow still lacked a disciplined boundary between internal synthetic evidence review and customer-facing claims.
2. This improves evidence quality, calibration usability, and scalable research throughput.
3. It moves the platform closer to replacing interviewer-led work because distribution and decision surfaces can now preserve calibrated evidence boundaries instead of relying on operator memory.
4. This is necessary now because Milestone 20 cannot launch safely if export/share flows only expose a generic synthetic disclaimer without a scoped readiness gate.

## Repository Evidence

- `src/ai_validation_swarm/saas/runtime.py` now derives a backend-owned `readiness_gate` from evidence-query reliability plus attached human calibration records.
- `src/ai_validation_swarm/saas/runtime.py` now adds that gate to workspace evidence-query responses, evidence views, decision logs, export bundles, and share bundles.
- `src/ai_validation_swarm/saas/runtime.py` now persists readiness-gate state into export manifests, share payloads, collaboration payloads, and audit events.
- `tests/unit/test_saas_runtime.py` now verifies:
  - pending evidence-query readiness state
  - human-validation-required readiness on ordinary export/share flows
  - workflow evidence views and decision logs inheriting readiness state
  - scoped externally ready export/share state when a run has external candidate-ready human calibration attached

## Final Implemented Slice

The final M19 slice adds actual distribution gating on top of the readiness contract.

The repository now also proves:

- high-stakes `human_review_required` evidence is blocked from public share creation
- public share delivery re-checks readiness-gate restrictions instead of trusting an earlier create-time assumption
- export and share surfaces now also carry MVP-facing launch boundary context for the next milestone

Additional repository evidence:

- `src/ai_validation_swarm/saas/runtime.py` now blocks public share creation when readiness state requires explicit human review.
- `src/ai_validation_swarm/saas/runtime.py` now re-checks readiness-gate restrictions during public share read.
- `tests/unit/test_saas_runtime.py` now verifies that high-stakes readiness blocks public share creation.

## Milestone Completion Review

Milestone 19 is now complete.

Implemented capability now proves:

- every evidence review can surface a backend-owned readiness state
- decision logs, export bundles, and share bundles inherit readiness boundaries automatically
- high-stakes or human-review-required evidence stays gated regardless of UI polish

Current platform state after completion:

- strongest improvement: the platform now has a real contract between synthetic evidence review and market-facing circulation boundaries
- most important remaining bottleneck: the platform still needs one explicit controlled-MVP launch layer for design-partner use instead of only readiness-gated artifacts
- sequencing decision: move directly to Milestone 20, because the next capability is launch packaging and launch scope, not more calibration plumbing

## Boundary

Milestone 19 completion still does not imply public launch or replacement-grade proof.

Readiness gates now exist, but Milestone 20 is still required to package those gates into a controlled design-partner MVP operating model.
