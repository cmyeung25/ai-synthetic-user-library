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

- `prototype_validation` now supports static image review, flow review, and scripted clickable task execution, but still lacks browser-driven and live-app execution
- richer live-app capture still depends on later executor expansion

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

Status: `in_progress`

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
- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now extracts that state derivation into a shared executable adapter, run-monitor, evidence-browser, evidence-query, and integrated-shell module, while `demo/workspace_ui_shared/workspace_runtime_bridge.mjs` now defines the validation-job runtime bridge, `demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs` now defines the workspace-session runtime bridge, `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs` now defines the shared live runtime client for session/job/evidence-query/workspace-shell orchestration, `demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs` now defines the shared heartbeat and polling layer for backend workspace-shell snapshot refresh, `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now defines the page-level frontend adapter plus visible review-surface projection, `demo/workspace_ui_shared/workspace_shell_app.mjs` now defines the app-layer controller/model boundary for frontend shells, and `tests/workspace_ui/test_workspace_ui_adapter.mjs`, `tests/workspace_ui/test_workspace_ui_run_monitor.mjs`, `tests/workspace_ui/test_workspace_ui_evidence_browser.mjs`, `tests/workspace_ui/test_workspace_ui_evidence_query.mjs`, `tests/workspace_ui/test_workspace_ui_shell_bundle.mjs`, `tests/workspace_ui/test_workspace_runtime_bridge.mjs`, `tests/workspace_ui/test_workspace_session_runtime_bridge.mjs`, `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`, `tests/workspace_ui/test_workspace_shell_runtime_sync.mjs`, `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`, and `tests/workspace_ui/test_workspace_shell_app.mjs` now fix blocked, fallback-ready, queueable, queued, running, completed, failed, retry-ready, evidence-browser, evidence-query, integrated-shell, runtime-bridge, session-runtime-bridge, shell-runtime-client, shell-runtime-sync, shell-app-controller, and page-level frontend-adapter paths as contract coverage
- a draft workspace evidence query contract spec now exists under `specs/workspace_evidence_query_contract.md` to define the future metadata-backed query and replay boundary between structured evidence indexes and the workspace review surface
- a draft workspace research plan contract spec now exists under `specs/workspace_research_plan_contract.md` to define the shared planning object between conversational intake, clarification, confirmation, and backend execution adapters
- a dedicated frontend adapter contract now exists under `specs/workspace_ui_adapter_contract.md` to define the stable derivation boundary between draft-plan state, conversation state, remediation state, and visible Workspace UI state
- a draft workspace validation-job bridge contract now exists under `specs/workspace_validation_job_bridge_contract.md` to define the runtime ingress mapping between confirmed drafts, the `validation-jobs` API, and shell run-monitor state
- a draft workspace session runtime contract now exists under `specs/workspace_session_runtime_contract.md` to define the authenticated workspace-session boundary between local SaaS runtime auth and the session-aware shell surface
- a draft workspace shell frontend adapter contract now exists under `specs/workspace_shell_frontend_adapter_contract.md` to define the final page-facing object that real frontend components should consume on top of the shell bundle and validation-job bridge
- a draft workspace shell app contract now exists under `specs/workspace_shell_app_contract.md` to define the app-layer controller and render-model boundary between shared shell logic and future frontend components
- a draft workspace shell snapshot contract now exists under `specs/workspace_shell_snapshot_contract.md` to define the backend-driven shell hydration boundary between session, selected job, evidence query, and runtime heartbeat

Default interaction model:

- start from one conversational intake canvas, not a rigid multi-section form
- let the system infer the likely research mode from intent, stimulus, and available artifacts
- ask only the minimum follow-up questions needed to close missing inputs
- do not default the UI to workflow-builder panels, node graphs, or explicit orchestration wiring
- keep structured controls, persona filters, and mode overrides behind an advanced path
- require a final explicit plan confirmation step that shows inferred mode, selected inputs, evidence boundary, and expected outputs before execution
- keep reusable UI components in the shared design system as they enter the main workspace flow, instead of letting prototypes accumulate page-specific component styling

### Milestone 11: Full SaaS Product Surface

Status: `planned`

Scope:

- tenant admin, membership, and quota controls
- billing and plan management surface
- project, study, export, and evidence-sharing workflows
- API token and integration surface
- operator observability and support tooling

Exit criteria:

- the platform can be operated as a repeatable multi-tenant product surface without weakening evidence discipline or bypassing the core simulation boundaries

## Productization Tracking Layers

1. `SaaS Readiness (backend foundation)` - `implemented`
   Tracking intent: complete the service, tenancy, auth, quota, persistence, and worker boundaries needed to host the existing research engine without rewriting it.

2. `Workspace UI Readiness` - `in_progress`
   Tracking intent: expose the core research workflow through an operator-facing workspace console so teams can submit runs, inspect evidence, and review failures without living in the CLI or raw artifact folders.

3. `Full SaaS Product Surface` - `planned`
   Tracking intent: add the broader tenant-admin, billing, sharing, export, and support surface only after the workspace workflow is usable and the evidence layer remains queryable and auditable.

Tracking rules:

- finish the remaining replay-depth and deeper review-surface gap before broad UI expansion
- treat workspace UI as a research operating console first, not as generic dashboard polish
- keep the default user path conversational; do not make users learn internal mode taxonomy, run schemas, or builder-style workflow setup just to start research
- hide advanced controls behind a secondary path, but always expose an explicit final plan confirmation before execution
- do not expand to the full SaaS product surface until the workspace UI proves the end-to-end research workflow on top of the shared runtime

## Current Platform Readout

As of now, the platform has already proven:

- persona generation can support reusable structured synthetic users
- facilitated interviews can already produce usable synthetic evidence for pain discovery, decision reconstruction, root-cause, hypothesis, concept, and adoption-barrier work
- a first-class `prototype_validation` contract now exists for stimulus/task inputs, mode-specific coverage, and explicit evidence-boundary synthesis
- static image stimulus review now exists as real runtime surface, including artifact snapshotting and structured screen interpretation
- multi-screen flow stimulus review now exists as real runtime surface, including ordered screen analysis and transition-friction synthesis
- application-supplied observed action traces can now be normalized, persisted, and synthesized as distinct prototype evidence
- scripted clickable prototype manifests can now be executed through a native task loop that emits observed action traces before synthesis
- panel synthesis, conversation realism scoring, and over-optimism warnings are in place
- a workspace-scoped authenticated API ingress now exists for queued validation-job submission and status retrieval without reimplementing the research core
- a local async worker runtime now exists for leasing queued jobs and running the shared validation pipeline beyond the one-shot CLI shell
- workspace role gating, billing-status gating, plan-tier run limits, workspace-bound path isolation, and retention-driven artifact purge now exist as enforced SaaS controls

As of now, the platform has not yet proven:

- complete discovery-stage coverage
- live-interface behavior validation beyond scripted clickable manifests
- action-grounded adoption prediction from interface use

## Recommended Next Sequence

1. Finish `evidence_query_index_and_replay` by deepening replay-bearing artifacts and replay-linked review depth on top of the new backend `workspace-shell` snapshot surface.
2. Continue from the implemented intake, confirmation, adapter, queue/run monitor, evidence browser, evidence query, integrated-shell, workspace-session bridge, validation-job bridge, and backend evidence-query prototypes into a real workspace shell on top of the shared runtime.
3. Promote the new session/runtime bridges, shell snapshot contract, and shell frontend adapter from engineering demo wiring into the actual workspace shell first, then add richer worker observability and deeper replay/comparison surfaces.
4. Revisit browser-driven clickable execution only after the metadata and replay boundaries are stable enough to keep observed behavior evidence queryable and auditable.
5. Expand to `Full SaaS Product Surface` only after the workspace console can support repeatable research operations end to end.

## Unified Development Backlog

### Current architecture state

- the repository is still local-first, but it now has both a CLI shell and a lightweight authenticated WSGI API plus worker runtime for workspace-scoped validation jobs
- shared domain, facilitator, observer, persona, sampling, reporting, and evaluation modules already exist as reusable Python packages
- prototype validation already has explicit stimulus, synthesis, and observed-action contracts, plus a native manifest-backed clickable executor, but not yet a browser-driven driver
- the repository is not Markdown-first data storage; JSON files and filesystem artifacts already hold the primary machine-readable records, while Markdown mainly acts as a human-readable projection layer
- run and interview artifacts are file-backed and auditable, while the local SaaS runtime now stores workspace, billing, token, and validation-job lifecycle state in SQLite

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

6. `evidence_query_index_and_replay` - `in_progress` - `P1` - `3 SP`
   Purpose: build a query and replay surface on top of the structured metadata store and artifact paths for audit, replay, calibration comparison, and future workspace browsing.
   Evidence: `specs/workspace_evidence_query_contract.md` now defines the query/replay boundary; `specs/workspace_shell_snapshot_contract.md` now defines the backend-driven shell hydration boundary; `src/ai_validation_swarm/saas/evidence_query.py`, `src/ai_validation_swarm/saas/runtime.py`, and `src/ai_validation_swarm/saas/api.py` now serve completed-run evidence-query payloads through `GET /api/v1/evidence-query` and integrated shell snapshots through `GET /api/v1/workspace-shell`; `tests/unit/test_saas_runtime.py` now verifies completed and pending query flows plus the shell snapshot boundary; and `demo/workspace_ui_moss_stage10/`, `demo/workspace_ui_moss_stage11/`, `demo/workspace_ui_moss_stage12/`, `demo/workspace_ui_moss_stage13/`, `demo/workspace_ui_moss_stage14/`, and `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now prototype and progressively consume that backend evidence/review surface inside the workspace shell.

7. `async_job_ingress_boundary` - `implemented` - `P2` - `5 SP`
   Purpose: introduce the job envelope, status lifecycle, and worker handoff boundary needed for long-running prototype and panel runs without forcing a premature full SaaS rewrite.
   Evidence: `src/ai_validation_swarm/saas/job_store.py` and `src/ai_validation_swarm/saas/runtime.py` now persist queued/running/completed validation jobs in SQLite, lease queued jobs into a worker flow, and hand the existing validation runner a stable job envelope.

8. `authenticated_api_and_async_runtime` - `implemented` - `P2` - `5 SP`
   Purpose: expose the validation pipeline through authenticated service ingress and a reusable async runtime so hosted wrappers do not need to duplicate orchestration logic.
   Evidence: `src/ai_validation_swarm/saas/api.py` now exposes authenticated browser-callable `POST/GET /api/v1/validation-jobs` routes with CORS headers, `src/ai_validation_swarm/saas/runtime.py` processes queued jobs through the shared validation runner, and `src/ai_validation_swarm/cli/main.py` now exposes `bootstrap-saas-workspace`, `serve-saas-api`, and `run-saas-worker`.

9. `tenant_controls_and_billing_enforcement` - `implemented` - `P2` - `5 SP`
   Purpose: enforce workspace isolation, role permissions, billing gates, plan quotas, and retention behavior as real operational controls instead of design-only contracts.
   Evidence: the local SaaS runtime now blocks invalid roles and inactive billing states at submission time, enforces workspace-scoped path boundaries and plan-tier daily/concurrent limits, and purges expired run artifacts based on retention policy.

### Architecture sequencing rule

- do the observed-action trace contract before any clickable or live-app runtime
- keep JSON and file artifacts as the primary machine-readable records; do not treat Markdown as the canonical persistence layer
- do structured metadata persistence before API-first SaaS product surface work
- keep relational metadata as the primary query layer for persona selection; do not promote Mongo-first document storage or graph-first selection until scale or traversal needs justify them
- review whether a graph projection is needed only after persona selection indexes are stable and similarity/diversity queries become a repeated bottleneck
- do the stimulus executor adapter before any driver-specific browser or app automation expansion
- do the evidence query and replay surface after structured metadata persistence is stable
- do async ingress and worker boundaries before auth, billing, or dashboard expansion

### Verification gates for the architecture backlog

- contract tests for run envelopes, action traces, and index records
- replayable prototype-validation fixtures that prove `stimulus_reaction`, `task_guided_self_report`, and `observed_action_trace` stay separated
- artifact-to-index consistency checks for interviews, stimulus snapshots, and synthesized outputs
- integration coverage showing the same core contract can be called from current CLI flows and a future worker entrypoint
