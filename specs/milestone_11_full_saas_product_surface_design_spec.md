# Canonical Milestone 11 Design Spec: Full SaaS Product Surface

## Status

- milestone: `Milestone 11`
- status: `implemented`
- owner: `platform-development-chief` + `platform-system-architect`
- canonical scope: the first real user-facing product layer above the proven workspace runtime
- document role: the canonical Milestone 11 product, architecture, and delivery-contract spec
- canonical execution order:
  1. `project_and_study_management_surface`
  2. `audit_export_and_sharing_surface`
  3. `operator_observability_and_support_surface`
  4. `tenant_admin_and_membership_surface`
  5. `billing_plan_and_quota_surface`
  6. `integration_and_token_surface`

## 1. Purpose

Milestone 11 turns the current operator-grade workspace shell into a product surface that real teams can use without dropping into CLI commands, raw artifact folders, or engineering-only debug flows.

This milestone exists to make synthetic research operable as a study-centric product while preserving:

- conversational intake
- explicit evidence boundaries
- run lineage
- auditability
- supportability

This is not a generic dashboard milestone. It is the layer where the platform starts becoming a usable research product.

## 2. Mandatory Alignment Check

### Which research bottleneck does this improve?

The current bottleneck is not raw run execution. It is the lack of a durable user-facing layer for organizing studies, reviewing evidence in context, exporting and sharing safely, and handling blocked or failed work without filesystem inspection.

### What does it improve?

- `evidence_quality`
  by keeping project, study, export, share, and support flows tied to explicit lineage and synthetic boundaries
- `scalable_research_throughput`
  by making repeatable study operation possible without engineering intervention
- `decision_prediction`
  indirectly, by making evidence comparison, replay, and follow-up review usable in real product workflows

### Does it move the platform closer to replacing interviewer-led work?

Yes, but only if the default path stays study-centric and conversational instead of collapsing into admin-first SaaS chrome.

### Why is this necessary now?

Milestone 10 already proved the operator workflow. Milestone 11 is necessary because a credible team-facing product needs durable study objects, safe evidence sharing, and support surfaces on top of that workflow.

## 3. Product Principles

- default to `study-first`, not `workspace-settings-first`
- default to conversational intake, not a large setup form
- keep internal run schema and mode taxonomy off the default path
- preserve synthetic-only boundary language in review, export, and share surfaces
- treat runs as operational records inside study context, not as the top-level product object
- keep membership, billing, and token utilities secondary to the research workflow

## 4. Experience Direction

Milestone 11 is the first layer that real users should be able to operate directly. That means the product surface cannot feel like an internal admin console that happens to expose research jobs.

### Interaction direction

- use one `study workspace` as the primary operating canvas
- keep intake, run monitoring, evidence review, export/share, and support inside that same canvas
- prefer calm `operator console` language over system-internals language
- reveal admin and governance controls only when the user intentionally moves into workspace settings

### Visual and information design direction

- keep the current `Moss Console` direction as the baseline visual language
- favor editorial-density review cards and timelines over dashboard KPI tiles
- make evidence lineage, replay context, and synthetic boundary warnings visible without looking like error chrome
- treat support actions as contextual study operations, not as a detached ticketing tool

## 5. Current Execution Baseline

Milestone 11 is already active in the repository. The current repository-backed baseline is not only a design intention.

### What is repository-real now

- durable `project` and `study` objects above standalone validation jobs
- study-linked job submission and workspace-shell snapshot hydration
- durable `saved evidence view` creation and retrieval tied to study/job evidence scope
- durable `decision_log` creation and retrieval tied to study decision history
- a study-scoped activity timeline that summarizes cross-artifact study actions from audit-backed events
- durable `export_bundle` creation with lineage, synthetic-boundary manifest, and audit events
- durable `share_bundle` creation with viewer-safe public payloads, expiry, and revocation
- workspace support diagnostics plus durable `support_snapshot` creation
- a first workspace settings contract for membership, billing overview, quota/retention visibility, and API token lifecycle
- a same-origin hosted Stage 15 shell served by the local SaaS runtime
- a framework-owned frontend host build under `frontend/workspace_shell_app/` that now fronts the hosted shell routes while reusing the same shared controller and route bootstrap contract
- that framework host already owns the full visible Stage 15 shell surface as the first framework-owned product surface slice, while the shared shell controller still provides the interaction logic and hosted route bootstrap
- route-aware deep links for key Milestone 11 product and collaboration objects

### Current hosted-shell route map

The local SaaS wrapper currently serves the same hosted shell for:

- `/app/workspace`
- `/app/projects/{project_id}`
- `/app/studies/{study_id}`
- `/app/evidence-views/{evidence_view_id}`
- `/app/decision-logs/{decision_log_id}`
- `/app/export-bundles/{export_bundle_id}`
- `/app/share-bundles/{share_bundle_id}`
- `/app/support-snapshots/{support_snapshot_id}`
- `/app/jobs/{job_id}`

The server injects route context into the page, and the shared shell controller bootstraps project, study, export, share, support, or job context from that route.

The same hosted shell now exchanges a first authenticated `?token=token-api` visit for a server-backed same-origin browser session. In practice that means the first visit can still use a bootstrap token, but the same browser can then reopen clean `/app/*` deep links and call the hosted API through an HttpOnly cookie without repeating the token query, explicit query tokens still take priority when re-bootstrap is needed, and the shell exposes a visible end-session control.

### What remains unfinished

- deeper decomposition of the now-framework-owned Stage 15 shell surface into durable production components beyond the initial one-host JSX ownership slice
- first server-backed hosted browser-session lifecycle now exists, but broader identity integration, richer session policy controls, and production deployment hardening are still open
- first decision-log review comments, approval state, and study-scoped activity timeline now exist, but broader notification delivery, subscriptions, and incident-thread collaboration are still open
- deeper operator observability and stuck-job intervention
- broader membership, billing, and token administration

## 6. User Model

### Primary roles

- `owner`
- `admin`
- `researcher`
- `viewer`

### Primary user jobs

- organize research by project and study
- submit and rerun studies without learning internal runtime contracts
- review evidence, replay, and cross-run comparison in one study context
- export and share synthetic evidence safely
- diagnose blocked or failed work from product language instead of raw errors

## 7. Product Object Model

Milestone 11 formalizes these durable product objects:

1. `workspace`
2. `project`
3. `study`
4. `run`
5. `export_bundle`
6. `share_bundle`
7. `support_snapshot`
8. `audit_event`
9. `evidence_view`
10. `decision_log`

### Object ownership rule

- `workspace` owns governance, billing, token, and membership boundaries
- `project` owns long-lived research area organization
- `study` owns the default operating surface
- `run` owns execution state and evidence outputs
- `export_bundle` and `share_bundle` own distribution-safe evidence packaging
- `support_snapshot` owns durable operator handoff state

## 8. Information Architecture

### Primary navigation

- `Projects`
- `Studies`
- `Runs`
- `Evidence`
- `Exports`
- `Support`
- `Workspace settings`

### Default home rule

The default user path should land in a study-oriented workspace, not in a generic overview dashboard.

## 9. Core Product Surfaces

### Project surface

- project summary
- active studies
- latest run context
- export/share counts
- future decision history

### Study surface

- conversational intake
- inferred plan confirmation
- run timeline
- evidence review
- saved evidence views
- decision logs
- decision review
- study activity timeline
- replay focus
- cross-run comparison
- export and share state
- support state

### Support surface

- blocked submission reasons
- failed run explanation
- queued-job cancel
- failed-job and canceled-job retry
- quota and permission visibility
- support snapshot generation

### Workspace settings surface

- members and roles
- plan and quota state
- retention and export policy
- API token management
- audit history

Current repository-backed subset:

- workspace settings snapshot loading
- workspace audit-history loading and filtering
- billing and quota mutation
- member upsert
- masked token listing
- token issue
- token revoke

## 10. Operator Intervention Model

Milestone 11 needs a minimal but real intervention layer so operators can keep research moving without filesystem access or direct database edits.

### Intervention rules

1. `cancel` is allowed only for `queued` validation jobs that have not yet been leased by a worker
2. `retry` is allowed only for `failed` or `canceled` validation jobs
3. retry must create a new queued job instead of mutating and reusing the old job row
4. the original job must stay visible as part of the audit trail
5. every intervention must preserve project/study lineage and emit audit events

### Explicit non-goal for this slice

This Milestone 11 support layer does not yet include:

- forced termination of `running` jobs
- worker-process kill controls
- streaming logs
- incident-thread collaboration

Those belong to a later observability layer once the first support contract is stable.

## 11. Hosted Shell Architecture Boundary

Milestone 11 should keep one clear boundary between the product shell and the research engine.

### Frontend responsibilities

- route-aware page composition
- study-first interaction flow
- local input state
- visible selection state for product objects
- rendering summaries, timelines, review cards, and support states

### Backend responsibilities

- authenticated session state
- product object persistence
- job execution and status lifecycle
- evidence-query projection
- workspace-shell snapshot hydration
- export/share/support materialization
- audit events

### Contract preservation rule

Milestone 11 must preserve these shared boundaries as the frontend is promoted:

- `workspace_research_plan_contract`
- `workspace_validation_job_bridge_contract`
- `workspace_evidence_query_contract`
- `workspace_shell_snapshot_contract`
- `workspace_shell_app_contract`
- `workspace_shell_frontend_adapter_contract`

## 12. Route and Deep-Link Contract

The current routed hosted shell is the first formal Milestone 11 route contract.

### Route rules

1. every product-object route must render the same shell entrypoint
2. the server must inject a backend-owned route context object
3. the shared shell controller must bootstrap selected object state from backend detail loaders, not from page-local heuristics
4. URL changes must preserve the current explicit route scope whenever that scoped object is still selected
5. route changes must not bypass session, study, or evidence boundaries

### Current route-scope behavior

The hosted shell should behave like this:

- if a user lands on `/app/projects/{project_id}`, the URL should stay project-scoped even when the shell auto-hydrates a visible study
- if a user lands on `/app/jobs/{job_id}`, the URL should stay job-scoped even when project and study context are also visible
- if a user lands on `/app/evidence-views/{evidence_view_id}` or `/app/decision-logs/{decision_log_id}`, the URL should stay collaboration-scoped while the shell hydrates the owning study, job, and evidence context
- when the user explicitly selects a study, evidence view, decision log, export bundle, share bundle, or support snapshot, the route may promote to that more specific object
- if the current explicit route object is no longer selected, the shell may fall back to the most concrete remaining visible object, and finally to `/app/workspace`

## 13. Evidence Discipline Rules

- every export must preserve project, study, run, and timestamp lineage
- every share surface must preserve synthetic-only boundary language
- cross-run comparison must stay workspace-scoped and metadata-backed
- support bundles must preserve failure and diagnostic context without implying human validation
- intervention controls must preserve audit history rather than rewriting run history
- no Milestone 11 surface may present synthetic evidence as market proof

## 14. Execution Plan

### Phase 1: Study-first hosted shell

Target:

- same-origin hosted shell
- project/study product objects
- study-linked job submission
- route-aware deep links
- product-context evidence refresh

Repository status:

- `in_progress`, with a concrete routed Stage 15 baseline already landed

### Phase 2: Export and sharing

Target:

- export-bundle lifecycle
- viewer-safe share-bundle lifecycle
- revocation and expiry
- audit-backed packaging

Repository status:

- `in_progress`

### Phase 3: Operator support and observability

Target:

- blocked-submission guidance
- failed-run diagnostics
- queued-job cancel
- failed/canceled retry
- support snapshot generation
- later stuck-job and intervention workflows

Repository status:

- `in_progress`

### Phase 4: Governance surfaces

Target:

- membership and project access controls
- billing and quota UX
- token lifecycle

Repository status:

- `in_progress`

Current repository-backed subset:

- membership snapshot loading and member upsert
- workspace audit history query and shell projection
- writable local billing/quota mutation
- token issue and revoke
- policy and retention visibility in the same hosted shell

## 15. Formal Delivery Sequence

Milestone 11 should be delivered in this order:

1. make the study-first shell repository-real and same-origin hosted
2. make product objects durable above raw jobs
3. make export/share/support flows durable and audit-backed
4. add minimal operator intervention controls that keep work moving inside the product surface
5. promote the shared shell contracts, routed product-object map, and collaboration surfaces into the actual framework-hosted frontend
6. only then expand into broader workspace governance surfaces

This sequencing keeps the first true user-facing layer centered on research operation rather than admin sprawl.

## 16. Current Execution Slice

The active Milestone 11 delivery slice is:

- `study_activity_timeline_surface`

### Why this slice is next

- the framework-owned hosted shell entrypoint is now repository-real, but cross-artifact study continuity is still fragmented across separate collaboration, export, share, and support panels
- a study-scoped activity timeline is the minimum credible continuity layer before broader notifications or inbox patterns
- that timeline must preserve study-first routing, auditability, and object lineage instead of collapsing into generic workspace alerts

### Scope

This slice must:

1. expose a backend-owned study activity endpoint on top of workspace audit events
2. map study-visible audit actions into route-aware activity cards for runs, collaboration, export/share, and support objects
3. project that activity state through the shared runtime client, app controller, and frontend adapter
4. add a visible study activity panel to the hosted Stage 15 shell and framework host
5. add executable coverage for the new API, shared shell state, and hosted document surface

### Non-goals

This slice does not yet include:

- push notifications, subscriptions, or unread state
- workspace-wide inbox aggregation
- broader comments or approvals beyond decision-log review
- visual redesign away from the existing Moss product language

### Acceptance

This slice is complete when:

- `GET /api/v1/studies/{study_id}/activity` returns study-scoped, route-aware activity cards from workspace audit events
- the shared shell can load and clear study activity state through the runtime client and app controller
- the frontend adapter projects visible study activity summary rows and timeline cards
- the hosted shell renders a study activity panel inside the same study-first surface and can open linked product objects from activity cards

## 17. Post-Milestone Next Step

Milestone 11 is now complete as the first study-first hosted product layer.

The next execution step should move into post-Milestone-11 hardening rather than reopening the core product-surface contract:

1. deepen cross-run audit, comparison, and calibration workflows on top of the now-proven study shell
2. continue framework-host component decomposition without changing the backend-owned route, evidence, or audit contracts
3. add future product-shell acceptance checks for visual layer overlap, text occlusion, and fixed/sticky elements blocking primary research actions across desktop and mobile viewports
4. extend hosted identity, session policy, and deployment hardening as a separate productionization slice
5. keep broader notification, integration, and admin expansion behind evidence continuity and supportability gains

## 18. Verification Gates

Milestone 11 is not complete until all of the following are true.

### Product proof

- a user can create or open a study from a hosted shell route
- project and study context stays visible without filesystem inspection
- evidence review, replay, and cross-run comparison stay inside study context
- export and share flows preserve explicit synthetic boundaries
- operators can cancel queued work and retry failed/canceled work from the product shell

### Technical proof

- contract tests cover app-controller and route-bootstrap behavior
- API tests cover hosted shell routes and product-object detail routes
- API tests cover cancel/retry job lifecycle behavior
- API and shell tests cover collaboration-object route parsing and route-scope preservation
- browser verification covers study creation, run submission, evidence refresh, export/share, and support snapshot generation

Current repository proof:

- `tests/unit/test_saas_runtime.py`
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`
- `tests/workspace_ui/test_workspace_shell_app.mjs`
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`
- `tests/workspace_ui/test_workspace_shell_stage15_app.mjs`
- `tests/workspace_ui/test_stage15_shell_document.mjs`
- `tests/workspace_ui/test_workspace_shell_hosted_routes.mjs`
- `scripts/verify_stage15_hosted_shell_smoke.mjs`, with browser artifacts written under `output/playwright/stage15_hosted_shell_smoke/`

### Governance proof

- permission gates, quota language, and audit events remain visible and queryable

## 19. Deferred Work

The following remain outside Milestone 11 completion scope:

- browser-driven prototype/live-app research validation beyond the hosted-shell smoke coverage
- automated visual-layout regression gates for product-shell overlap, occlusion, and action-blocking layer issues
- generic workflow-builder surfaces
- broad integration marketplace
- any claim that synthetic evidence is equivalent to human proof

## 20. Canonical References

- `specs/workspace_project_study_contract.md`
- `specs/workspace_study_collaboration_surface_contract.md`
- `specs/workspace_study_activity_surface_contract.md`
- `specs/workspace_export_bundle_contract.md`
- `specs/workspace_share_bundle_contract.md`
- `specs/workspace_support_surface_contract.md`
- `specs/workspace_settings_surface_contract.md`
- `specs/workspace_billing_quota_surface_contract.md`
- `specs/workspace_audit_history_surface_contract.md`
- `specs/workspace_evidence_query_contract.md`
- `specs/workspace_shell_snapshot_contract.md`
- `specs/workspace_shell_app_contract.md`
- `specs/workspace_shell_frontend_adapter_contract.md`
