# Milestone 40: Continuous Calibration Observatory Design Spec

Status: implemented.

Owner layer: SaaS runtime, evidence reliability, calibration artifacts, public launch readiness boundary, Frontline workspace overview.

Last updated: 2026-07-02.

## Purpose

Milestone 40 turns calibration from a release-time checklist into an ongoing backend-owned quality signal.

Platform owners need to know which modes, evidence types, providers, models, and benchmark scopes are supported, under-covered, degrading, or repeatedly missing human-reviewed outcomes before any broader launch or stronger readiness claim.

## Alignment Check

- Research bottleneck improved: evidence confidence needs continuous calibration visibility instead of manual release judgment.
- Primary improvements: calibration, evidence quality, auditability, and launch-claim discipline.
- North-star fit: replacement-grade claims cannot be evaluated responsibly without continuous calibration health, drift, and miss attribution.

## Implemented Contract

- `GET /api/v1/calibration-observatory` exposes `calibration-observatory/v1`.
- The observatory aggregates run coverage by mode, provider, evidence type, calibration attachment, benchmark signals, unsupported evidence types, and readiness blockers.
- `describe_workspace_public_launch_readiness()` now embeds calibration-observatory summary and can add a `continuous_calibration_health_not_ready` blocker.
- Frontline Studio renders a workspace-level calibration observatory card so owners can inspect coverage and unsupported evidence signals without reading raw benchmark files.

## Evidence Boundary

- Calibration health is a readiness signal, not human market proof.
- Unsupported evidence types and missing benchmark coverage must remain visible.
- Customer-facing surfaces may consume bounded readiness state but should not expose raw benchmark internals by default.

## Acceptance Evidence

- `tests/unit/test_saas_runtime.py` verifies the calibration observatory endpoint and launch-readiness projection.
- `frontend/frontline_research_studio/src/main.jsx` renders `#calibration-observatory-card`.
- `scripts/verify_frontline_studio_smoke.mjs` verifies the workspace calibration observatory appears in the Frontline browser smoke.

## Out of Scope

- Replacement-readiness approval. That remains Milestone 45.
- Broad multi-market benchmark expansion. That remains Milestone 44.
- Provider routing based on calibration deltas. That remains Milestone 46.
