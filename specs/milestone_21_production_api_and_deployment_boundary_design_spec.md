# Milestone 21 Design Spec: Production API and Deployment Boundary

Status: `implemented`

## Purpose

Milestone 20 proved that the platform can circulate calibrated synthetic research through a bounded design-partner MVP flow. The next bottleneck is not more customer-facing circulation policy. The next bottleneck is production hardening around the same research core:

- hosted wrappers need one stable backend-owned operations contract
- deployment environments need explicit readiness signals before broader circulation
- the web wrapper must not keep local-dev bootstrap behavior enabled by accident in production-like environments

This milestone exists to improve `scalable_research_throughput` and `evidence_quality` without moving simulation, evidence ranking, calibration, or worker logic into the web layer.

## Alignment Check

1. Which research bottleneck does this improve?
   It reduces the deployment and operations fragility that still blocks broader product use after the controlled MVP gate.
2. Does it improve behavioral realism, decision prediction, evidence quality, calibration, or throughput?
   Primarily `scalable_research_throughput` and `evidence_quality`, because reliable deployment boundaries keep evidence-serving, worker visibility, and calibration-linked review stable in hosted use.
3. Does it move the platform closer to replacing interviewer-led work instead of only polishing peripheral workflow?
   Yes, indirectly. The research core already exists; this milestone makes the same core safely consumable in production-like environments.
4. If not, why is it still necessary now?
   Not applicable. The controlled MVP cannot become a broader launch path without this layer.

## Current Architecture Decision

- keep the Python research core in `src/ai_validation_swarm/saas/runtime.py`
- keep SQLite/filesystem/runtime artifacts as the current local-first store until a later storage migration is justified
- treat the web layer in `src/ai_validation_swarm/saas/api.py` as a thin delivery wrapper
- add explicit operations and deployment contracts at the wrapper boundary before introducing FastAPI or a fuller ASGI adapter

## First Implemented Slice

The first M21 slice is `production operations contract and deployment profile hardening`.

It lands four capabilities:

1. public health and readiness endpoints
2. public service metadata endpoint for wrapper consumption
3. deployment-profile-controlled hosted bootstrap policy
4. opt-in structured request logging

## Backend Contract

### Public operations endpoints

The WSGI wrapper now exposes:

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/service-metadata`

These endpoints are intentionally public because they support:

- deployment probes
- hosted wrapper discovery
- operational verification before browser-session auth is available

They must not expose customer evidence payloads or widen synthetic-evidence claims.

### Runtime operations payload

`SaasRuntime.describe_runtime_operations()` is now the backend-owned source for:

- runtime root and DB reachability
- runtime schema version
- workspace count
- aggregate job counts
- active browser-session count
- core runtime capabilities already available behind the wrapper

This keeps research-relevant operational truth in the runtime layer, not duplicated in the web wrapper.

### Deployment profile

`SaasApiDeploymentProfile` now defines the deployment-facing wrapper boundary:

- `deployment_env`
- `public_base_url`
- `secret_source`
- `expected_backup_mode`
- `allow_query_token_bootstrap`
- `structured_logs`

This profile exists so deployment policy can change without rewriting runtime logic.

### Hosted bootstrap hardening

The current local-first hosted shell still supports `?token=...` bootstrap for rapid same-origin browser-session setup. That remains useful for local MVP work, but it is unsafe as a production default.

Rule:

- local/preview environments may allow query-token bootstrap when explicitly desired
- staging/production readiness should fail if query-token bootstrap remains enabled
- if a deployment profile disables it, `/app/*?token=...` must reject the bootstrap request instead of silently accepting it

### Structured logs

When `structured_logs` is enabled, the wrapper emits one JSON line per request with:

- method
- path
- whether a query string was present
- auth kind
- HTTP status
- request duration
- deployment environment

This is an operations-layer log only. It must not be treated as evidence or calibration data.

## Second Implemented Slice

The second M21 slice is `typed wrapper contract manifest and workspace operations observability`.

It lands two additional capabilities:

1. one machine-readable API contract manifest for hosted wrappers
2. one authenticated workspace operations summary for worker, evidence, calibration, distribution, support, and audit observability

### Contract manifest

The wrapper now exposes `GET /api/v1/contract-manifest`.

This manifest is not a pretend full FastAPI migration. It is the explicit WSGI-era typed boundary that says:

- which routes are public vs authenticated
- which methods are supported
- which request fields or query parameters are expected
- which response roots and contract versions wrappers should consume
- which product contracts, such as evidence query, are the canonical linked specs

That gives hosted wrappers one backend-owned contract surface instead of duplicating route assumptions in frontend code.

### Workspace operations observability

The wrapper now exposes authenticated `GET /api/v1/operations/summary`.

The backend-owned runtime aggregates:

- worker job lifecycle counts
- evidence-view count
- evidence reliability review-state counts
- readiness-gate and calibration-status counts across completed jobs
- decision-log and decision-comment counts plus review-status counts
- export/share distribution counts plus MVP gate state counts
- support snapshot count
- recent audit-event action counts

This keeps production-like observability tied to real backend artifacts instead of page-local heuristics.

## Milestone Completion Decision

Milestone 21 is now complete because the repository now has:

- public deployment probes and readiness checks
- deployment-profile-controlled hosted bootstrap policy
- opt-in structured request logging
- a machine-readable typed contract manifest for wrapper consumption
- authenticated workspace-scoped operations observability across worker, evidence, calibration, distribution, support, and audit paths

The remaining platform gap is no longer the production API/deployment boundary itself. The next bottleneck is team-hardening on top of that boundary: collaboration roles, review governance, quota/billing/retention confidence, and handoff discipline for real team use.

## Verification

Repository evidence for this slice:

- `src/ai_validation_swarm/saas/api.py` now exposes the operations endpoints, deployment profile, structured logging hook, and hosted bootstrap policy gate
- `src/ai_validation_swarm/saas/runtime.py` now exposes backend-owned runtime operations state
- `src/ai_validation_swarm/saas/job_store.py` now supports aggregate job and browser-session listing for operations status
- `src/ai_validation_swarm/cli/main.py` now accepts deployment-profile arguments for `serve-saas-api`
- `tests/unit/test_saas_runtime.py` now verifies:
  - public health endpoint
  - local readiness success
  - public service metadata exposure
  - production readiness failure when deployment hardening is missing
  - production readiness success when deployment profile is hardened
  - hosted query-token bootstrap rejection when disabled
- `src/ai_validation_swarm/saas/api.py` now also exposes `GET /api/v1/contract-manifest` and authenticated `GET /api/v1/operations/summary`
- `src/ai_validation_swarm/saas/runtime.py` now also exposes backend-owned `describe_workspace_operations_summary()`
- `tests/unit/test_saas_runtime.py` now also verifies:
  - contract-manifest exposure
  - workspace operations summary authorization
  - worker/evidence/decision/distribution/support/audit observability counts in the authenticated operations payload

## Completion Review

- strongest current platform capability: one bounded study-first SaaS wrapper can run synthetic research, surface evidence/calibration/readiness, gate customer circulation, and now expose deployment plus operations contracts without moving research logic into the web layer
- most important remaining bottleneck: real team use still needs stronger collaboration governance and review/handoff hardening on top of the now-stabilized deployment boundary
- sequencing decision: move to Milestone 22 next
- do not broaden launch claims yet; public launch still waits for M22-M25

## Boundary Statement

These operations surfaces harden deployment and hosted wrapper integration. They do **not** convert synthetic evidence into human proof, and they do **not** change the calibration boundary already enforced by Milestones 19 and 20.
