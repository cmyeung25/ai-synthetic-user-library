# Development Roadmap

## Purpose

This roadmap tracks the platform work that most directly improves:

- behavioral realism
- decision and adoption prediction quality
- evidence discipline and auditability
- reusable research workflows for discovery, concept evaluation, and prototype validation

The roadmap should be read as a capability roadmap for a `human behavior simulation platform`, not as a generic SaaS feature list.

## Status Legend

- `implemented`: already supported in the current repository
- `in_progress`: partially implemented, but not yet complete for the intended platform use
- `planned`: explicitly on roadmap, not yet implemented

## Interview Mode Roadmap

The platform should support `7 core single-interview modes` in Phase 1 and `9 total single-interview modes` in the fuller Phase 2 surface.

### Phase 1 Core Modes

1. `pain_point_discovery` - `implemented`
   Purpose: discover whether a problem exists, how often it appears, how painful it is, and what workaround is currently used.
   Primary stage: `discovery`

2. `explore_root_cause` - `implemented`
   Purpose: investigate why a known problem happens, what triggers it, and what deeper drivers keep it alive.
   Primary stage: `discovery`

3. `decision_reconstruction` - `implemented`
   Purpose: reconstruct one real recent decision, including evidence gaps, stakeholder pressure, internal uncertainty, and what actually changed.
   Primary stage: `discovery`

4. `validate_hypothesis` - `implemented`
   Purpose: test a specific causal or behavioral hypothesis against recalled experience without asking the participant to agree with the framing.
   Primary stage: `concept evaluation`

5. `concept_validation` - `implemented`
   Purpose: test understanding, appeal, objections, trust gaps, and stated adoption conditions for a concept.
   Primary stage: `concept evaluation`

6. `prototype_validation` - `implemented`
   Purpose: test a prototype, image stimulus, flow, or live interface through observed task behavior rather than concept-only self-report.
   Primary stage: `prototype validation`

7. `adoption_barrier_validation` - `implemented`
   Purpose: identify why a user who sees value may still not adopt because of setup, permissions, trust, pricing, reversibility, or workflow burden.
   Primary stage: `concept evaluation` and `prototype validation`

### Phase 2 Expansion Modes

8. `workflow_mapping` - `planned`
   Purpose: map the current workflow, handoffs, fragmentation, and where information or responsibility breaks down.
   Primary stage: `discovery`

9. `messaging_validation` - `planned`
   Purpose: test wording, positioning, value proposition clarity, and whether the message creates the right mental model before use.
   Primary stage: `concept evaluation`

## Interview Mode Principles

- `pain_point_discovery` should not introduce the concept early.
- `explore_root_cause` should not assume the participant's stated cause is complete or correct.
- `decision_reconstruction` should stay anchored in a recent real event, not a generic preference summary.
- `validate_hypothesis` should seek contradiction and alternatives, not confirmation.
- `concept_validation` should separate understanding, curiosity, trial intent, payment intent, and durable adoption.
- `prototype_validation` should distinguish observed behavior from stated interpretation.
- `adoption_barrier_validation` should focus on the gap between "sounds useful" and "will actually enter routine use."

## Prototype Validation Roadmap

The current platform has moved beyond pure `text-first` interviewing with a static image stimulus layer, but it still needs richer stimulus and action layers to reach real prototype validation.

### Prototype validation capability layers

1. `image_stimulus_review` - `implemented`
   Input: screenshots, mocked UI frames, static prototype images
   Output: interpretation gaps, first-click expectations, trust signals, wording confusion, likely hesitation

2. `flow_stimulus_review` - `implemented`
   Input: multi-screen prototype flow
   Output: step-by-step comprehension breakdown, likely drop-off points, hidden setup burden

3. `interactive_prototype_validation` - `implemented`
   Input: clickable prototype task loop, scripted clickable manifest, or application-supplied observed action trace artifact
   Output: observed task path, misclicks, backtracking, abandonment, and action-grounded follow-up probes
   Current gap: the current native executor is manifest-backed rather than browser-driven, so richer clickable and live-app drivers remain future expansion

4. `live_app_task_simulation` - `planned`
   Input: live product URL or local app
   Output: observed behavior trace plus synthesis of where real-world activation may fail

## Milestone Roadmap

### Milestone 0: Architecture and Harness

Status: `implemented`

Scope:

- product brief
- system architecture
- data model
- workflow and safety constraints
- evaluation plan
- roadmap

Exit criteria:

- core platform direction is documented
- artifact model and repo structure are stable enough for implementation

### Milestone 1: Persona Generator

Status: `implemented`

Scope:

- seed generation
- structured persona artifacts
- audit metadata
- realism-oriented persona expansion

Exit criteria:

- personas can be generated reproducibly
- persona artifacts are inspectable and auditable

### Milestone 2: Sampling Engine

Status: `implemented`

Scope:

- panel presets
- filtering
- deterministic sampling
- rationale for panel selection

Exit criteria:

- persona selection is reproducible and explainable

### Milestone 3: Validation Runner

Status: `implemented`

Scope:

- founder brief loading
- persona response runner
- retry and artifact persistence

Exit criteria:

- end-to-end validation runs can be executed and archived

### Milestone 4: Auditor and Aggregator

Status: `implemented`

Scope:

- skeptic review
- sensitive-topic audit
- aggregation logic
- cross-persona summary

Exit criteria:

- runs produce structured audit and summary outputs

### Milestone 5: Report Generator

Status: `implemented`

Scope:

- Markdown and JSON outputs
- archive structure
- summary artifacts

Exit criteria:

- runs are readable and exportable without manual reconstruction

### Milestone 6: Evaluation Harness

Status: `implemented`

Scope:

- fixture suite
- deterministic tests
- regression checks
- quality gates

Exit criteria:

- core prompt and runtime changes can be regression-tested

### Milestone 7: Facilitated Interview Runtime

Status: `implemented`

Scope:

- facilitator-led interview loop
- observer-controlled interview loop
- concept panel runtime
- realism scoring
- over-optimism warnings

Current implemented surface:

- `pain_point_discovery`
- `explore_root_cause`
- `decision_reconstruction`
- `validate_hypothesis`
- `concept_validation`
- `adoption_barrier_validation`
- observer actions
- concept panel summary
- facilitator audit learning reports

Current gaps:

- `prototype_validation` now supports static image review, flow review, scripted clickable task execution, application-supplied observed traces, and browser-observed clickable/live-app trace ingestion
- replacement-readiness still depends on broader external human benchmark coverage beyond the fixture-backed Milestone 15 pipeline

Exit criteria:

- the 7 core interview modes are supported as explicit first-class modes
- each mode has mode-specific coverage requirements and synthesis schema
- concept and prototype evidence are clearly separated

### Milestone 8: Prototype Validation Layer

Status: `implemented`

Scope:

- image-based concept/prototype review
- multi-screen flow review
- interactive prototype task loop
- action trace capture
- observed behavior synthesis

Exit criteria:

- the platform can test a prototype through task execution rather than concept-only discussion
- output distinguishes `stated intention` from `observed behavior`

### Milestone 9: SaaS Readiness (backend foundation)

Status: `implemented`

Scope:

- service decomposition
- multi-tenant design
- structured metadata persistence and evidence index
- async job model
- auth, privacy, and billing design
- persona catalog governance

Exit criteria:

- the platform can be decomposed into a scalable service design without changing the research core

### Milestone 10: Workspace UI Readiness

Status: `implemented`

Scope:

- reusable design-system tokens and console components for workspace prototypes
- authenticated workspace shell and session handling
- conversational research intake with natural-language prompt and artifact drop
- hidden mode inference and progressive clarification instead of up-front mode selection
- final research-plan confirmation before execution
- queue, run status, and failure visibility
- evidence browser and replay surface grounded in structured metadata and artifact paths
- advanced persona and study setup controls as a secondary path, not the default path

Exit criteria:

- an operator can start from research intent, confirm the system-inferred plan, run the workflow, inspect the evidence, and replay core research jobs from a workspace UI without dropping back to raw CLI or filesystem inspection

Current proof-of-progress:

- a reusable workspace-console design-system CSS foundation now exists under `demo/workspace_ui_design_system/`, including shared base styles plus `Moss Console`, `Slate Lab`, and `Ink Signal` theme directions
- the low-fi workspace flow prototype under `demo/workspace_ui_lowfi/` now consumes that shared theme instead of carrying one-off inline styling
- `Moss Console` is now the selected default direction, and a more detailed intake-focused stage-2 prototype now exists under `demo/workspace_ui_moss_stage2/`
- a stage-3 Moss prototype now exists under `demo/workspace_ui_moss_stage3/` to demonstrate intent inference, progressive clarification, and draft plan inspection before execution
- a stage-4 Moss prototype now exists under `demo/workspace_ui_moss_stage4/` to demonstrate the research-plan confirmation surface, explicit queueability states, and bilingual EN / Traditional Chinese review on the same interaction model
- a stage-5 Moss prototype now exists under `demo/workspace_ui_moss_stage5/` to demonstrate a single-path blocked-draft remediation flow, concrete supplement or fallback guidance, and removal of review-only scenario tabs from the default product path
- a stage-6 Moss prototype now exists under `demo/workspace_ui_moss_stage6/` to converge conversational intake, inferred draft planning, blocked confirmation, and remediation into one single-page operator flow
- a stage-7 Moss prototype now exists under `demo/workspace_ui_moss_stage7/` to model the same flow as a frontend state machine with live draft-plan, remediation, and adapter-state recomputation
- a stage-8 Moss prototype now exists under `demo/workspace_ui_moss_stage8/` to extend the queueable draft into queued, running, completed, failed, and retry-ready operator states
- a stage-9 Moss prototype now exists under `demo/workspace_ui_moss_stage9/` to extend the completed run into evidence browsing, artifact filtering, and replay-linked review inside the same workspace shell
- a stage-10 Moss prototype now exists under `demo/workspace_ui_moss_stage10/` to extend completed-run review into metadata-backed evidence querying, facet filtering, result selection, and replay-linked result focus
- a stage-11 Moss prototype now exists under `demo/workspace_ui_moss_stage11/` to converge intake, confirmation, run monitoring, and evidence query review into one integrated operator shell with an explicit runtime bridge
- a stage-12 Moss prototype now exists under `demo/workspace_ui_moss_stage12/` to connect the integrated shell to the authenticated `validation-jobs` API with live request mapping, job loading, authenticated workspace-session loading, normalized run-state projection, backend-query-driven evidence review, and a shared runtime heartbeat with optional auto-refresh
- a stage-13 Moss prototype now exists under `demo/workspace_ui_moss_stage13/` to consume the same runtime bridge through one shared shell app controller while shifting the review surface toward a more product-facing workspace composition
- a stage-14 Moss prototype now exists under `demo/workspace_ui_moss_stage14/` to move the review shell onto one backend-driven `workspace-shell` snapshot path so session state, selected job state, and evidence focus can be refreshed through one contract
- the Stage 14 shell now starts from editable research intent, desired-output, artifact, and first-task intake fields on top of that shared shell app controller instead of relying on scenario-only draft presets for the main path
- the Stage 14 shell now accepts real prototype file selection on the default intake path and keeps attached artifact names in shared shell state instead of using only a demo toggle for artifact readiness
- the Stage 14 shell now keeps `brief_path`, `persona_dir`, `run_root`, `mode override`, `panel_type`, `sample_size`, `provider_name`, and persona filters behind one collapsed `Advanced study controls` path instead of exposing that structured setup on the default intake canvas
- `scripts/start_stage12_demo.bat` now boots the local engineering demo through one repo-local entrypoint that restarts the API and worker, waits for the authenticated session endpoint to respond, and opens the Stage 14 shell by default
- `scripts/start_stage12_demo.bat` now also resets the local `ws_api_demo` workspace before boot so repeated engineering-demo runs do not hit the retained trial daily-run quota and silently block new submissions
- backend evidence replay now derives richer concrete replay-bearing steps from trace and planner artifacts such as `raw_responses.json`, `stage_results.json`, and `planner.json`, including persona-role and trust/pricing context on raw responses plus attempt/retry/error context on stage results, so the product-facing shell can show non-empty replay focus instead of only placeholder replay states
- backend evidence query now also emits backend-owned `replay_context`, `comparison_context`, and initial `cross_run_comparison` guidance so Stage 14 can render replay/comparison guidance from the same shell snapshot contract instead of recomputing nearby evidence meaning page-locally
- the shared shell frontend adapter and Stage 14 page now project evidence coverage, replay-focus detail, related-evidence comparison cards, and initial cross-run comparison cards from that backend review context so review can stay inside the shell instead of falling back immediately to raw JSON payloads
- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now extracts that state derivation into a shared executable adapter, run-monitor, evidence-browser, evidence-query, and integrated-shell module, while `demo/workspace_ui_shared/workspace_runtime_bridge.mjs` now defines the validation-job runtime bridge, `demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs` now defines the workspace-session runtime bridge, `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs` now defines the shared live runtime client for session/job/evidence-query/workspace-shell orchestration, `demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs` now defines the shared heartbeat and polling layer for backend workspace-shell snapshot refresh, `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now defines the page-level frontend adapter plus visible review-surface projection, `demo/workspace_ui_shared/workspace_shell_app.mjs` now defines the app-layer controller/model boundary for frontend shells, and `tests/workspace_ui/test_workspace_ui_adapter.mjs`, `tests/workspace_ui/test_workspace_ui_run_monitor.mjs`, `tests/workspace_ui/test_workspace_ui_evidence_browser.mjs`, `tests/workspace_ui/test_workspace_ui_evidence_query.mjs`, `tests/workspace_ui/test_workspace_ui_shell_bundle.mjs`, `tests/workspace_ui/test_workspace_runtime_bridge.mjs`, `tests/workspace_ui/test_workspace_session_runtime_bridge.mjs`, `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`, `tests/workspace_ui/test_workspace_shell_runtime_sync.mjs`, `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`, and `tests/workspace_ui/test_workspace_shell_app.mjs` now fix blocked, fallback-ready, queueable, queued, running, completed, failed, retry-ready, evidence-browser, evidence-query, integrated-shell, runtime-bridge, session-runtime-bridge, shell-runtime-client, shell-runtime-sync, shell-app-controller, and page-level frontend-adapter paths as contract coverage
- a draft workspace evidence query contract spec now exists under `specs/workspace_evidence_query_contract.md` to define the future metadata-backed query and replay boundary between structured evidence indexes and the workspace review surface
- a draft workspace research plan contract spec now exists under `specs/workspace_research_plan_contract.md` to define the shared planning object between conversational intake, clarification, confirmation, and backend execution adapters
- a dedicated frontend adapter contract now exists under `specs/workspace_ui_adapter_contract.md` to define the stable derivation boundary between draft-plan state, conversation state, remediation state, and visible Workspace UI state
- a draft workspace validation-job bridge contract now exists under `specs/workspace_validation_job_bridge_contract.md` to define the runtime ingress mapping between confirmed drafts, the `validation-jobs` API, and shell run-monitor state
- a draft workspace session runtime contract now exists under `specs/workspace_session_runtime_contract.md` to define the authenticated workspace-session boundary between local SaaS runtime auth and the session-aware shell surface
- a draft workspace shell frontend adapter contract now exists under `specs/workspace_shell_frontend_adapter_contract.md` to define the final page-facing object that real frontend components should consume on top of the shell bundle and validation-job bridge
- a draft workspace shell app contract now exists under `specs/workspace_shell_app_contract.md` to define the app-layer controller and render-model boundary between shared shell logic and future frontend components
- a draft workspace shell snapshot contract now exists under `specs/workspace_shell_snapshot_contract.md` to define the backend-driven shell hydration boundary between session, selected job, evidence query, and runtime heartbeat
- the Stage 14 engineering demo has now been browser-verified against the live local runtime on `2026-06-28`, including advanced-controls request mapping, real artifact-selection state, live job submission, snapshot-backed job selection, evidence review, and replay-ready completed-run inspection without dropping back to CLI or raw filesystem review

Default interaction model:

- start from one conversational intake canvas, not a rigid multi-section form
- let the system infer the likely research mode from intent, stimulus, and available artifacts
- ask only the minimum follow-up questions needed to close missing inputs
- do not default the UI to workflow-builder panels, node graphs, or explicit orchestration wiring
- keep structured controls, persona filters, and mode overrides behind an advanced path
- require a final explicit plan confirmation step that shows inferred mode, selected inputs, evidence boundary, and expected outputs before execution
- keep reusable UI components in the shared design system as they enter the main workspace flow, instead of letting prototypes accumulate page-specific component styling

### Milestone 11: Full SaaS Product Surface

Status: `implemented`

Scope:

- tenant admin, membership, and quota controls
- billing and plan management surface
- project, study, export, and evidence-sharing workflows
- API token and integration surface
- operator observability and support tooling
- framework-hosted workspace frontend promotion that preserves the shared shell contracts and keeps the Python research core as the source of truth
- later thin FastAPI adapter evaluation for typed hosted API contracts, only after frontend route/session ownership and current runtime consumers are stable

Design anchor:

- `specs/milestone_11_full_saas_product_surface_design_spec.md` is the canonical Milestone 11 product and architecture spec
- `specs/workspace_project_study_contract.md` now defines the first product-layer project/study contract and its workspace-shell integration boundary
- `specs/workspace_study_collaboration_surface_contract.md` now defines the first durable study-collaboration contract for saved evidence views and decision logs
- `specs/workspace_study_activity_surface_contract.md` now defines the first study-scoped cross-artifact activity timeline contract on top of workspace audit events
- `specs/workspace_export_bundle_contract.md` now defines the first export-layer product contract for study-scoped evidence packaging and audit-backed export creation
- `specs/workspace_share_bundle_contract.md` now defines the viewer-safe public share-bundle contract with expiry and revocation
- `specs/workspace_support_surface_contract.md` now defines the support diagnostics and support-snapshot contract for blocked submission, failed-run explanation, and operator handoff
- `specs/workspace_settings_surface_contract.md` now defines the first workspace-governance contract for membership, quota/retention visibility, billing overview, and token lifecycle
- `specs/workspace_billing_quota_surface_contract.md` now defines the first writable billing/quota contract for plan tier, billing status, seat count, renewal visibility, and runtime-effective quota overrides
- execute Milestone 11 from `project_and_study_management_surface` first, then `audit_export_and_sharing_surface`, then `operator_observability_and_support_surface`, and only after that expand governance beyond the now-started workspace settings slice
- keep the default user path study-centric and conversational; do not turn Milestone 11 into a generic admin dashboard or workflow-builder expansion

Current proof-of-progress:

- the local SaaS runtime now exposes `POST/GET /api/v1/projects` plus `POST/GET /api/v1/studies` so real product objects can exist above standalone validation jobs
- workspace-shell snapshots now accept `project_id` and `study_id`, and can hydrate selected project/study context alongside session, selected job, and evidence-query state
- validation-job submission now accepts workspace-visible `project_id` and `study_id` linkage through request metadata and updates the selected study with its latest submitted job
- the local SaaS runtime now exposes `POST/GET /api/v1/evidence-views` plus `POST/GET /api/v1/decision-logs`, persists durable study-collaboration objects, materializes collaboration artifacts under the workspace collaboration root, and records collaboration audit events
- the same local SaaS runtime now also exposes decision-log review state plus threaded decision comments through `POST /api/v1/decision-logs/{decision_log_id}/review-status` and `POST/GET /api/v1/decision-logs/{decision_log_id}/comments`, keeping approval and revision discussion attached to the same study evidence object
- the local SaaS runtime now also exposes `GET /api/v1/studies/{study_id}/activity`, projecting audit-backed study activity across run, collaboration, export/share, and support actions into one study timeline
- the local SaaS wrapper now exposes a direct-render same-origin hosted Stage 15 shell entrypoint at `GET /app/workspace` instead of requiring a separate static file server for the Milestone 11 product shell
- the same hosted shell is now route-aware for `/app/projects/{project_id}`, `/app/studies/{study_id}`, `/app/evidence-views/{evidence_view_id}`, `/app/decision-logs/{decision_log_id}`, `/app/export-bundles/{export_bundle_id}`, `/app/share-bundles/{share_bundle_id}`, `/app/support-snapshots/{support_snapshot_id}`, and `/app/jobs/{job_id}`, with backend-injected route context plus shared detail-loader bootstrap
- `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs` now owns the Stage 15 hosted-shell mount, route bootstrap, refresh wiring, and product-surface event orchestration, so the first same-origin product shell no longer depends on one large inline HTML module
- a framework-owned frontend host now exists under `frontend/workspace_shell_app/`, imports the Stage 15 shell document plus design-system assets into a React/Vite entrypoint, and builds a same-origin hosted app bundle under `frontend/workspace_shell_app/dist/`
- `src/ai_validation_swarm/saas/api.py` now prefers that framework build for `/app/*` hosted-shell routes, injecting backend route context before the framework app bootstraps while preserving the same shared shell controller and route semantics
- `scripts/build_workspace_shell_app.bat` plus `scripts/start_stage12_demo.bat` now make that framework host a repeatable local workflow instead of a one-off manual build step
- the framework host now owns the full visible Stage 15 shell surface as React-rendered sections, including the left rail, top header, workspace connection, workspace settings, projects, studies, study-workspace intake, run timeline, evidence review, saved views, decision logs, export/share, support, and debug trace, while still delegating interaction logic to the shared controller and route bootstrap contracts
- `demo/workspace_ui_moss_stage15/index.html` now proves a study-first product shell where project selection, study selection, intake, run submission, saved evidence views, decision logs, decision review threads, study activity timeline, and evidence refresh live in one Milestone 11 surface
- the local SaaS runtime now exposes `POST/GET /api/v1/export-bundles`, persists durable export-bundle objects, materializes export manifests under the workspace export root, and records export creation audit events
- the local SaaS runtime now exposes `POST/GET /api/v1/share-bundles`, `POST /api/v1/share-bundles/{share_bundle_id}/revoke`, and `GET /public/v1/share-bundles/{share_key}` so viewer-safe sharing, expiry, and revocation now exist as real repository behavior
- `demo/workspace_ui_moss_stage15/index.html` now also lets the selected study create and review export bundles plus share bundles from the same product surface
- the local SaaS runtime now exposes `GET /api/v1/support-diagnostics` plus `POST/GET /api/v1/support-snapshots`, persists durable support snapshots, and materializes support handoff bundles under the workspace support root
- the local SaaS runtime now also exposes `POST /api/v1/validation-jobs/{job_id}/cancel` plus `POST /api/v1/validation-jobs/{job_id}/retry`, records intervention audit events, and preserves retry lineage through new queued jobs instead of rewriting prior failures
- `demo/workspace_ui_moss_stage15/index.html` now also lets the selected study load blocked-submission, queued/running, or failed-run diagnostics, inspect a recent failure digest, cancel queued jobs, retry failed or canceled jobs, and generate support snapshots from the same product surface
- the local SaaS runtime now exposes `GET /api/v1/workspace-settings`, `POST /api/v1/workspace-members`, `POST /api/v1/api-tokens`, and `POST /api/v1/api-tokens/{token_id}/revoke` so the first workspace-governance surface can inspect membership, billing overview, quota/retention policy, and token lifecycle without raw store edits
- the local SaaS runtime now also exposes `GET /api/v1/audit-events` so workspace governance and operator events can be filtered and reviewed from the product shell instead of staying backend-only
- the local SaaS runtime now exposes `POST /api/v1/workspace-billing` so owner or billing_admin roles can update plan tier, billing status, seat count, renewal visibility, and effective quota overrides through a product contract instead of bootstrap-only configuration
- `demo/workspace_ui_moss_stage15/index.html` plus `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs` now also project a secondary `Workspace settings` surface where membership, policy, and masked token state live inside the same hosted shell instead of staying CLI-only
- `frontend/workspace_shell_app` now provides the first React/Vite framework host for the Stage 15 shell, reusing the shell document, `mountStage15WorkspaceShell`, and shared frontend contracts rather than reimplementing workspace behavior in framework-local state
- that same hosted Workspace settings surface now also lets operators update billing and quota controls, load filtered audit history, and immediately re-render session-effective limits from the same shell
- `src/ai_validation_swarm/saas/job_store.py` now preserves unrelated API tokens during workspace-member upserts by updating surviving members in place instead of deleting and recreating the whole membership set, closing a real token-cascade residual risk in the new governance slice
- `specs/workspace_audit_history_surface_contract.md` now defines the first read-side audit-history contract for Milestone 11 governance visibility
- `tests/unit/test_saas_runtime.py` now verifies `GET /app/workspace` plus routed hosted-shell object routes for study, collaboration, export, support, and same-origin static shell asset delivery so the first hosted-shell entrypoint is real repository behavior
- `tests/workspace_ui/test_stage15_shell_document.mjs` now verifies shared extraction of the Stage 15 title, inline style block, full stage grid, and split first-column/second-column markup so the framework host can progressively replace Stage 15 sections without duplicating one manual copy
- `specs/workspace_decision_review_surface_contract.md` now defines the first Milestone 11 decision-review contract for threaded decision comments plus `draft / in_review / approved / needs_revision` review state
- `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`, `tests/workspace_ui/test_workspace_shell_app.mjs`, `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`, `tests/workspace_ui/test_workspace_shell_stage15_app.mjs`, and `tests/workspace_ui/test_stage15_shell_document.mjs` now verify the shared shell can hydrate and project project/study product context end to end, including saved evidence views, decision logs, decision-review comments/status, study activity timeline state, queued-job cancel, failed/canceled retry actions, workspace settings membership/token flows, writable billing/quota updates, and hosted-shell bootstrap ownership outside inline HTML
- `tests/unit/test_saas_runtime.py` now verifies project creation, study creation, study-linked job submission, project/study-aware shell snapshot hydration, saved evidence view lifecycle, decision-log lifecycle, decision-review comment/status lifecycle, study-activity projection, export-bundle lifecycle, share-bundle lifecycle, support diagnostics, support snapshot creation, workspace settings member/token lifecycle, audit-history query lifecycle, billing/quota update lifecycle, queued-job cancel, failed-job retry, public viewer delivery, and share revocation
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now boots the hosted Stage 15 demo end to end, creates a project and study from `/app/workspace`, submits a live job, reopens the completed `/app/jobs/{job_id}` route for evidence refresh, creates export/share/support artifacts, validates the viewer-safe public share payload boundary, and writes browser artifacts under `output/playwright/stage15_hosted_shell_smoke/`

Exit criteria:

- the platform can be operated as a repeatable multi-tenant product surface without weakening evidence discipline or bypassing the core simulation boundaries

### Milestone 12: Evidence Reliability, Cross-Run Review, and Calibration

Status: `implemented`

Scope:

- cross-run comparison index for study-linked validation jobs, saved evidence views, decision logs, and run artifacts
- evidence stability and contradiction scoring across repeated runs, panel slices, modes, and artifact families
- calibration records that separate stable simulated signals from one-off synthetic artifacts and unsupported extrapolation
- replay and audit lineage that can trace a claim back to run, persona, prompt/stimulus version, response/action trace, artifact, and comparison set
- product-shell acceptance gates for visual overlap, text occlusion, and fixed/sticky layers blocking primary research actions across desktop and mobile viewports

Design anchor:

- `specs/milestone_12_evidence_reliability_design_spec.md` is the canonical Milestone 12 product and architecture design spec
- extend `specs/workspace_evidence_query_contract.md` from result query and initial cross-run candidates into a reliability contract that supports repeated-run comparison, stability labels, contradiction review, and calibration annotations
- keep comparison and calibration logic backend-owned inside the evidence/query/runtime layer; the frontend should render review state, not invent evidence reliability scores from page-local heuristics
- keep synthetic-evidence boundaries explicit: Milestone 12 may improve reliability and auditability, but it must not claim human market proof

Current proof-of-progress:

- `src/ai_validation_swarm/saas/evidence_query.py` now emits backend-owned `evidence_reliability` and `audit_lineage` payloads with stability labels, stability score, supporting evidence, contradicting evidence, missing context, calibration records, replay focus, selected evidence provenance, and synthetic boundary text.
- `src/ai_validation_swarm/saas/runtime.py` now enriches cross-run comparison and audit-lineage payloads with workspace job, project, and study context for study-linked validation jobs without fabricating linkage for legacy runs.
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now projects reliability summary rows, reliability detail cards, calibration cards, and audit-lineage summaries into the review surface so the frontend renders backend evidence state instead of inventing reliability scores.
- `src/ai_validation_swarm/saas/api.py` now streams hosted static assets in chunks, closing the large bundle truncation issue that blocked reliable hosted-shell smoke verification.
- `demo/workspace_ui_design_system/workspace-ui-base.css` plus the Stage 15 shell styles now prevent long run/job/artifact/contract identifiers from overflowing dense evidence cards into neighboring panels.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now verifies clean `/app/jobs/{job_id}` deep-link hydration after session bootstrap and fails on critical action blocking or critical product-panel overlap.
- `tests/unit/test_saas_runtime.py`, `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`, and the Stage 15 hosted smoke artifacts under `output/playwright/stage15_hosted_shell_smoke/` now prove the Milestone 12 backend, frontend projection, and browser layout acceptance path.

Exit criteria:

- a study can surface comparable completed runs with stable candidate selection and reason codes
- a selected insight or evidence result can show supporting, contradicting, and missing comparison context across runs
- the workspace shell can distinguish stable repeated signals from single-run signals and explicitly bounded synthetic assumptions
- replay lineage is deep enough for an operator to audit why a conclusion was shown without opening raw artifact folders
- browser acceptance checks can fail on product-shell layer overlap, text occlusion, or blocked primary actions

### Milestone 13: Real User Research Workspace

Status: `implemented`

Scope:

- production-grade `New Study` page centered on conversational research intake, artifact upload, inferred mode, missing-input follow-up, and explicit plan confirmation
- production-grade `Study Workspace` page for study context, run status, activity, collaboration objects, and next research action
- production-grade `Evidence Review` page for cross-run comparison, replay lineage, calibration status, saved evidence views, and decision logs
- component ownership cleanup inside `frontend/workspace_shell_app` so real product pages no longer depend on one large Stage 15 shell host

Design anchor:

- `specs/milestone_13_real_user_research_workspace_design_spec.md` is the canonical Milestone 13 product and architecture design spec
- `demo/workspace_ui_shared/milestone13_real_user_workspace.mjs` defines the shared page model for `New Study`, `Study Workspace`, `Evidence Review`, and the default research loop
- keep `frontend/workspace_shell_app` as the page-composition owner while preserving the Stage 15 shared controller until each functional control can be migrated safely

Current proof-of-progress:

- `specs/milestone_13_real_user_research_workspace_design_spec.md` now defines the canonical M13 page intent, non-goals, route intent, architecture boundaries, component ownership target, visual direction, acceptance criteria, and completion bar
- `demo/workspace_ui_shared/milestone13_real_user_workspace.mjs` now defines a testable M13 page model covering `Ask -> Clarify -> Confirm Plan -> Run -> Review Evidence -> Compare -> Decide -> Share With Boundary`, including backend-route-kind to active-page mapping
- `demo/workspace_ui_shared/workspace_shell_hosted_routes.mjs` plus `src/ai_validation_swarm/saas/api.py` now expose `/app/new-study` as a static hosted route with `route_kind: new_study`, so the New Study route intent is no longer only a design note
- `frontend/workspace_shell_app/src/NewStudyPage.jsx` owns conversational intake, artifact upload, explicit plan-confirmation gate, plan-action anchors, draft state, and synthetic-boundary visibility while preserving shared-controller DOM IDs
- `frontend/workspace_shell_app/src/StudyWorkspacePage.jsx` owns project/study selection, selected study context, run timeline, saved evidence views, decision logs, study activity, and next-action anchors while preserving shared-controller DOM IDs
- `frontend/workspace_shell_app/src/EvidenceReviewPage.jsx` owns evidence query/results, selected evidence, replay/detail anchors, cross-run comparison, decision review, export/share boundary actions, and Milestone 12 reliability/calibration/audit-lineage visibility while preserving shared-controller DOM IDs
- `frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx` is now reduced to a composition shell that renders research pages before settings/support/debug sections, with `RealUserWorkspaceNav`, `WorkspaceConnectionSection`, `WorkspaceSettingsSection`, `SupportOperationsSection`, and `DebugTraceSection` extracted into dedicated components
- `frontend/workspace_shell_app/src/main.css` now adds the M13 page visual layer and active route-page state using the existing editorial research-lab direction without turning the first screen into a generic SaaS dashboard
- `tests/workspace_ui/test_milestone13_real_user_workspace.mjs`, `tests/workspace_ui/test_workspace_shell_hosted_routes.mjs`, and `tests/unit/test_saas_runtime.py` now verify the M13 page model, evidence-boundary requirements, anti-patterns, route-level New Study behavior, React page ownership, controller-anchor preservation, and host composition cleanup
- `frontend/workspace_shell_app/README.md` now documents that the framework host is the starting point for M13 real user research pages

Exit criteria:

- a real user can start a study without understanding internal mode taxonomy, run schemas, or workflow-builder concepts
- the first-screen product experience is the actual research workflow, not a landing page or generic SaaS dashboard
- pages consume backend-owned shell/evidence contracts and preserve the final explicit execution confirmation step

### Milestone 14: Browser-Driven Prototype and Live-App Behavior Validation

Status: `implemented`

Scope:

- browser-driven clickable prototype execution beyond manifest-only task loops
- live-app session bootstrap, permission boundaries, and action trace capture
- observed hesitation, backtracking, abandonment, navigation, and completion events as first-class prototype evidence
- safety controls that keep high-stakes, credentialed, or destructive tasks outside automatic execution

Implemented repository evidence:

- `specs/milestone_14_browser_behavior_validation_design_spec.md` defines the browser behavior trace contract, safety gate, evidence boundary, and acceptance criteria
- `src/ai_validation_swarm/facilitator/stimulus_executor.py` now includes `BrowserBehaviorTraceExecutor`, which normalizes browser event logs into `observed-action-trace/v1`
- `src/ai_validation_swarm/facilitator/runtime.py` now routes browser-captured clickable and live-app trace artifacts through the executor chain before synthesis
- browser trace prompt/transcript/insight projections now expose driver, URL, safety-gate, and event-count context instead of treating the artifact as a static stimulus
- `tests/unit/test_stimulus_executor.py` and `tests/unit/test_facilitator_runtime.py` cover browser trace normalization, safety rejection, and runtime persistence

Exit criteria:

- prototype validation can ingest browser-observed behavior traces from real interactive surfaces
- synthesis separates observed interface behavior from stated intention and simulated explanation
- captured behavior remains queryable, replayable, and bounded by the evidence contract from Milestone 12

### Milestone 15: Human Calibration and Replacement-Readiness Evaluation

Status: `implemented`

Scope:

- attach human benchmark datasets or manually reviewed human study outcomes to comparable synthetic runs
- evaluate prediction accuracy for objections, trust gaps, adoption barriers, task failure, and decision changes
- calibrate persona/panel sampling and facilitator behavior against benchmark deltas
- define replacement-readiness thresholds by research stage, not as a blanket claim

Implemented repository evidence:

- `specs/milestone_15_human_calibration_design_spec.md` defines the Milestone 15 calibration contract, readiness statuses, architecture boundary, and evidence boundary.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now loads human benchmark suites, extracts synthetic prediction signals from run artifacts, scores precision/recall/F1/alignment against human-reviewed outcome signals, writes `human_calibration.json`, and summarizes replacement-readiness by research stage and evidence type.
- `fixtures/human_calibration/suite.json` plus the checked-in sample run provide a reproducible fixture-backed human outcome benchmark for calibration workflow verification.
- `src/ai_validation_swarm/cli/main.py` now exposes `run-human-calibration` as a CLI workflow for benchmark attachment and suite execution.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects attached `human_calibration.json` records into backend-owned evidence reliability payloads through a `human_benchmark_alignment` calibration record.
- `tests/unit/test_human_calibration.py` verifies calibration attachment, prediction accuracy scoring, fixture-only readiness boundaries, suite archive writing, and evidence reliability projection.

Exit criteria:

- the platform can report where synthetic evidence aligns or diverges from human research outcomes
- replacement-readiness is expressed as calibrated confidence by use case and evidence type
- high-stakes and uncalibrated domains remain explicitly gated

## Productization Tracking Layers

1. `SaaS Readiness (backend foundation)` - `implemented`
   Tracking intent: complete the service, tenancy, auth, quota, persistence, and worker boundaries needed to host the existing research engine without rewriting it.

2. `Workspace UI Readiness` - `implemented`
   Tracking intent: expose the core research workflow through an operator-facing workspace console so teams can submit runs, inspect evidence, and review failures without living in the CLI or raw artifact folders.

3. `Full SaaS Product Surface` - `implemented`
   Tracking intent: add the broader tenant-admin, billing, sharing, export, and support surface only after the workspace workflow is usable and the evidence layer remains queryable and auditable.

4. `Evidence Reliability and Calibration` - `implemented`
   Tracking intent: make repeated synthetic runs comparable, auditable, and calibratable before treating product-page polish or live-app automation as a reliability gain.

5. `Real User Research Workspace` - `implemented`
   Tracking intent: turn the proven study-first shell into actual user-facing research pages after the evidence reliability contract is clear enough for the UI to present confidence, contradiction, and replay lineage responsibly.

6. `Browser-Driven Prototype and Live-App Behavior Validation` - `implemented`
   Tracking intent: promote browser-observed clickable and live-app task traces into the existing observed-action evidence contract while safety-gating credentialed, destructive, and high-stakes automation.

7. `Post-Login Workspace IA and Active-Route Shell` - `planned`
   Tracking intent: turn the accepted study-first logged-in IA into framework-owned route behavior so the product stops behaving like one long page while preserving evidence review, comparison, decision logging, and governance boundaries.
   Design anchor: `specs/post_login_workspace_information_architecture_contract.md`

Tracking rules:

- keep reliability, contradiction, lineage, and calibration state backend-owned while product pages are promoted from the Stage 15 shell
- treat workspace UI as a research operating console first, not as generic dashboard polish
- keep the default user path conversational; do not make users learn internal mode taxonomy, run schemas, or builder-style workflow setup just to start research
- hide advanced controls behind a secondary path, but always expose an explicit final plan confirmation before execution
- do not let Milestone 13 page design hide stability, contradiction, replay lineage, calibration records, or synthetic-evidence boundaries
- do not let Milestone 14 browser traces bypass the Milestone 12 evidence query, replay, audit-lineage, or safety-boundary contracts
- do not let the post-login shell become dashboard-first, job-first, prompt-first, or admin-first; logged-in navigation must remain study-first

## Current Platform Readout

As of now, the platform has already proven:

- persona generation can support reusable structured synthetic users
- facilitated interviews can already produce usable synthetic evidence for pain discovery, decision reconstruction, root-cause, hypothesis, concept, and adoption-barrier work
- a first-class `prototype_validation` contract now exists for stimulus/task inputs, mode-specific coverage, and explicit evidence-boundary synthesis
- static image stimulus review now exists as real runtime surface, including artifact snapshotting and structured screen interpretation
- multi-screen flow stimulus review now exists as real runtime surface, including ordered screen analysis and transition-friction synthesis
- application-supplied observed action traces can now be normalized, persisted, and synthesized as distinct prototype evidence
- scripted clickable prototype manifests can now be executed through a native task loop that emits observed action traces before synthesis
- browser-observed clickable and live-app trace artifacts can now be normalized through the runtime executor boundary into first-class observed action traces with safety-gated evidence boundaries
- panel synthesis, conversation realism scoring, and over-optimism warnings are in place
- a workspace-scoped authenticated API ingress now exists for queued validation-job submission and status retrieval without reimplementing the research core
- a local async worker runtime now exists for leasing queued jobs and running the shared validation pipeline beyond the one-shot CLI shell
- workspace role gating, billing-status gating, plan-tier run limits, workspace-bound path isolation, and retention-driven artifact purge now exist as enforced SaaS controls
- a local authenticated workspace shell can now start from research intent, accept prototype artifacts, confirm the inferred plan, submit a live validation job, inspect evidence, replay core research artifacts, and surface initial cross-run comparison guidance without dropping back to raw CLI or filesystem inspection
- the evidence query contract now surfaces cross-run reliability, calibration records, contradiction/missing-context review, and audit lineage linked back to workspace job, project, and study context
- hosted browser smoke now verifies clean job deep-link hydration plus critical product-action and critical panel overlap acceptance gates, so layout overlap is part of ongoing milestone acceptance rather than manual visual inspection only
- the human calibration workflow now attaches fixture-backed human-reviewed outcomes to comparable synthetic runs, scores alignment and divergence, writes calibration artifacts, and projects human benchmark alignment into evidence reliability records without claiming blanket replacement-readiness

As of now, the platform has not yet proven:

- complete discovery-stage coverage
- broad external benchmark coverage across markets, domains, and repeated live human studies
- replacement-grade reliability across research stages or high-stakes domains
- final post-login IA behavior where the framework shell expands only the active research route instead of retaining one long-page composition

## Recommended Next Sequence

1. Expand human calibration beyond the checked-in fixture to external benchmark datasets and manually reviewed real study outcomes.
2. Evaluate whether browser-observed task failures, trust gaps, objections, and adoption barriers converge with broader human-reviewed outcomes.
3. Keep replacement-readiness thresholds scoped by research stage and evidence type, not as a blanket platform claim.
4. Keep observed browser behavior separate from stated intention, simulated explanation, and summary prose.
5. Defer broad marketing, generic dashboard, or workflow-builder surfaces until calibration can prove where synthetic behavior traces are reliable.
6. Keep the current Python runtime as the research core. Introduce a FastAPI layer only as a thin typed API adapter after the existing WSGI route contract, worker boundary, and frontend consumers are stable.
7. Keep broad SaaS surface expansion secondary to research-signal improvements, especially evidence depth, calibration, and behavior-grounded validation.
8. Implement the accepted post-login IA as a bounded framework-host workstream after preserving Milestone 15 calibration momentum: active-study landing, no-study intake landing, deep-link context preservation, and active-route page expansion.

## Unified Development Backlog

### Current architecture state

- the repository is still local-first, but it now has both a CLI shell and a lightweight authenticated WSGI API plus worker runtime for workspace-scoped validation jobs
- shared domain, facilitator, observer, persona, sampling, reporting, and evaluation modules already exist as reusable Python packages
- prototype validation already has explicit stimulus, synthesis, observed-action contracts, a native manifest-backed clickable executor, and a browser behavior trace executor for clickable/live-app artifacts
- the repository is not Markdown-first data storage; JSON files and filesystem artifacts already hold the primary machine-readable records, while Markdown mainly acts as a human-readable projection layer
- run and interview artifacts are file-backed and auditable, while the local SaaS runtime now stores workspace, billing, token, and validation-job lifecycle state in SQLite
- `frontend/workspace_shell_app` is the first React/Vite framework-hosted shell slice, reusing the Stage 15 shell document and shared shell controller instead of reimplementing product behavior inside framework components
- the accepted frontend direction is framework promotion first, with Next.js treated as a later hosted-product candidate rather than an immediate requirement
- the accepted backend direction is to keep `ai_validation_swarm` as the Python research core and add FastAPI only as a thin adapter when typed OpenAPI contracts, hosted auth integration, or deployment requirements justify it

### Accepted framework migration decision

Status: `accepted`

Decision:

- use the current React/Vite workspace shell as the first framework-hosted implementation slice
- keep Next.js as a later hosted-routing and production-session option, not a prerequisite for the current shell promotion
- keep `ai_validation_swarm` as the Python research core and avoid moving simulation, synthesis, evidence ranking, or worker execution into the frontend
- introduce FastAPI only as a thin ASGI/OpenAPI adapter after the framework-hosted frontend, current WSGI route contract, and worker boundary are stable

Why this improves the platform:

- improves scalable research throughput by giving teams a stable product shell for study setup, run monitoring, evidence review, export/share, support, and governance flows
- improves evidence quality and auditability by preserving the backend-owned workspace-shell snapshot, evidence-query, replay, and audit contracts instead of duplicating those rules in page-local UI state
- moves the platform closer to replacing interviewer-led workflow setup by keeping the default product path conversational, study-first, and confirmation-based

Non-goals:

- no broad backend rewrite before the evidence and worker contracts are stable
- no Next.js migration unless server routing, hosted auth/session behavior, or deployment needs justify it
- no generic SaaS dashboard expansion ahead of evidence depth, replay, calibration, and behavior-grounded validation

### Workspace UI delivery rule

The workspace product surface should act as a `research operating console`, not as a workflow builder.

- collect user intent conversationally and translate it into structured execution contracts behind the scenes
- keep internal mode taxonomy, panel contracts, and run-schema complexity off the default path
- avoid `n8n`-style orchestration panels and avoid large rigid forms that force schema learning before research can begin
- make the final confirmation sheet the point where the platform shows the inferred mode, selected artifacts, evidence boundary, and expected outputs before it creates a job

### Architecture upgrade backlog

The architecture backlog should strengthen the core simulation and evidence pipeline first, then expose those contracts through service boundaries later. Priority order below is highest first.

1. `shared_run_contract_layer` - `implemented` - `P0` - `3 SP`
   Purpose: define one canonical application-level request/result envelope for interview, panel, and prototype-validation runs so CLI, future API ingress, and future workers all call the same contract.
   Evidence: `run_contract.json` artifacts are now emitted from validation runs, facilitated interviews, observer-controlled interviews, and concept-panel runs through `src/ai_validation_swarm/saas/run_contract.py`, with focused runtime and integration coverage.

2. `observed_action_trace_contract` - `implemented` - `P0` - `5 SP`
   Purpose: add a typed observed-action schema for screen, click, navigation, timing, completion, backtracking, and abandonment evidence so prototype validation can move beyond task-guided self-report.

3. `structured_metadata_persistence` - `implemented` - `P1` - `5 SP`
   Purpose: keep JSON files and filesystem artifacts as the primary system-of-record, treat Markdown as a derived human-readable output, and add a SQLite-first, PostgreSQL-compatible metadata store for runs, interviews, personas, artifacts, and selection-facing indexes.
   Evidence: `src/ai_validation_swarm/saas/metadata_store.py` now projects run-contract and persona records into `metadata.sqlite3`, while `src/ai_validation_swarm/saas/run_contract.py` and `src/ai_validation_swarm/storage/files.py` update that index automatically as JSON/file artifacts are written.

4. `persona_selection_index_schema` - `implemented` - `P1` - `3 SP`
   Purpose: add relational persona-selection metadata, trait-assignment provenance, and similarity-edge tables that support deterministic filtering, quota-aware sampling, and explainable panel assembly while keeping full persona profiles in JSON artifacts.
   Evidence: `src/ai_validation_swarm/saas/metadata_store.py` now persists `persona_selection_records`, `persona_trait_assignments`, and `persona_similarity_edges`, while `src/ai_validation_swarm/storage/files.py` can both index freshly saved personas and rebuild the SQLite selection index from an existing versioned persona library.
   Review checkpoint: revisit whether MongoDB document storage or a graph projection is warranted only after the implemented relational selection index shows repeated similarity/diversity traversal bottlenecks.

5. `stimulus_executor_adapter` - `implemented` - `P1` - `5 SP`
   Purpose: isolate clickable-prototype and live-app drivers behind a normalized adapter boundary so facilitator and synthesis logic consume one stable action-trace shape instead of UI-driver-specific logic.

6. `evidence_query_index_and_replay` - `implemented` - `P1` - `3 SP`
   Purpose: build a query and replay surface on top of the structured metadata store and artifact paths for audit, replay, calibration comparison, and future workspace browsing.
   Evidence: `specs/workspace_evidence_query_contract.md` now defines the query/replay/reliability/audit-lineage boundary; `specs/workspace_shell_snapshot_contract.md` now defines the backend-driven shell hydration boundary; `src/ai_validation_swarm/saas/evidence_query.py`, `src/ai_validation_swarm/saas/runtime.py`, and `src/ai_validation_swarm/saas/api.py` now serve completed-run evidence-query payloads through `GET /api/v1/evidence-query` and integrated shell snapshots through `GET /api/v1/workspace-shell`; backend evidence replay now derives richer replay steps from trace and planner artifacts such as `raw_responses.json`, `stage_results.json`, `errors.json`, and `planner.json`; the same evidence query contract now emits backend-owned `replay_context`, `comparison_context`, `cross_run_comparison`, `evidence_reliability`, and `audit_lineage` guidance with selected comparison-run selection; `tests/unit/test_saas_runtime.py` now verifies completed, pending, cross-run comparison, reliability, calibration, and study-linked lineage flows plus the shell snapshot boundary; and `demo/workspace_ui_moss_stage10/`, `demo/workspace_ui_moss_stage11/`, `demo/workspace_ui_moss_stage12/`, `demo/workspace_ui_moss_stage13/`, `demo/workspace_ui_moss_stage14/`, `demo/workspace_ui_moss_stage15/`, and the shared frontend adapter progressively consume that backend evidence/review surface inside the workspace shell.

7. `async_job_ingress_boundary` - `implemented` - `P2` - `5 SP`
   Purpose: introduce the job envelope, status lifecycle, and worker handoff boundary needed for long-running prototype and panel runs without forcing a premature full SaaS rewrite.
   Evidence: `src/ai_validation_swarm/saas/job_store.py` and `src/ai_validation_swarm/saas/runtime.py` now persist queued/running/completed validation jobs in SQLite, lease queued jobs into a worker flow, and hand the existing validation runner a stable job envelope.

8. `authenticated_api_and_async_runtime` - `implemented` - `P2` - `5 SP`
   Purpose: expose the validation pipeline through authenticated service ingress and a reusable async runtime so hosted wrappers do not need to duplicate orchestration logic.
   Evidence: `src/ai_validation_swarm/saas/api.py` now exposes authenticated browser-callable `POST/GET /api/v1/validation-jobs` routes with CORS headers, `src/ai_validation_swarm/saas/runtime.py` processes queued jobs through the shared validation runner, and `src/ai_validation_swarm/cli/main.py` now exposes `bootstrap-saas-workspace`, `serve-saas-api`, and `run-saas-worker`.

9. `tenant_controls_and_billing_enforcement` - `implemented` - `P2` - `5 SP`
   Purpose: enforce workspace isolation, role permissions, billing gates, plan quotas, and retention behavior as real operational controls instead of design-only contracts.
   Evidence: the local SaaS runtime now blocks invalid roles and inactive billing states at submission time, enforces workspace-scoped path boundaries and plan-tier daily/concurrent limits, and purges expired run artifacts based on retention policy.

10. `framework_hosted_workspace_frontend` - `in_progress` - `P2` - `5 SP`
    Purpose: move the Stage 15 study-first shell from prototype HTML ownership into a framework-hosted frontend while preserving the shared shell app, snapshot, runtime-client, and frontend-adapter contracts.
    Evidence: `frontend/workspace_shell_app` now provides a React/Vite host that imports the Stage 15 shell document, mounts `mountStage15WorkspaceShell`, keeps route/app bootstrap behavior outside inline prototype ownership, and directly renders the full visible Stage 15 shell surface inside the framework boundary.
    Remaining gap: this is a first framework host, not yet the final production workspace frontend; the local hosted shell now has server-backed same-origin browser sessions plus first decision-log review threads and approval state, but broader identity integration, richer collaboration UX, fuller framework-native route ownership, deeper component decomposition, richer observability, and deployment integration remain open even though the visible shell is no longer injected from prototype markup.
    Decision: keep React as the current implementation path; revisit Next.js only when server routing, production auth/session handling, or deployment needs justify the added framework surface.

11. `fastapi_thin_api_adapter` - `planned` - `P2` - `3 SP`
    Purpose: add a typed ASGI/OpenAPI adapter around the existing SaaS runtime only after current route contracts and frontend consumers stabilize, so hosted wrappers can consume the same research core without rewriting it.
    Dependency: `framework_hosted_workspace_frontend` should prove route/session ownership first, and `evidence_query_index_and_replay` should remain stable enough that API migration does not weaken replay or audit behavior.
    Boundary: FastAPI must call the existing Python runtime modules and worker/job contracts; it must not move simulation, synthesis, evidence ranking, or worker execution into the web layer.

### Architecture sequencing rule

- do the observed-action trace contract before any clickable or live-app runtime
- keep JSON and file artifacts as the primary machine-readable records; do not treat Markdown as the canonical persistence layer
- do structured metadata persistence before API-first SaaS product surface work
- keep relational metadata as the primary query layer for persona selection; do not promote Mongo-first document storage or graph-first selection until scale or traversal needs justify them
- review whether a graph projection is needed only after persona selection indexes are stable and similarity/diversity queries become a repeated bottleneck
- do the stimulus executor adapter before any driver-specific browser or app automation expansion
- do the evidence query and replay surface after structured metadata persistence is stable
- do async ingress and worker boundaries before auth, billing, or dashboard expansion
- promote the framework-hosted frontend before changing the backend API framework, so frontend state and route ownership can be verified against the existing runtime contract
- introduce FastAPI as a thin adapter only after the WSGI API contract, worker boundary, and framework-hosted frontend consumers are stable
- keep Next.js as a deployment and routing option, not as a prerequisite for the current React shell promotion

### Verification gates for the architecture backlog

- contract tests for run envelopes, action traces, and index records
- replayable prototype-validation fixtures that prove `stimulus_reaction`, `task_guided_self_report`, and `observed_action_trace` stay separated
- artifact-to-index consistency checks for interviews, stimulus snapshots, and synthesized outputs
- integration coverage showing the same core contract can be called from current CLI flows and a future worker entrypoint
