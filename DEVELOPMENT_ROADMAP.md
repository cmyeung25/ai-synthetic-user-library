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

## Current Roadmap Snapshot

As of `2026-07-02`, **Milestone 42: Integration Surface, Run Event Stream, and Webhooks** is implemented. The active roadmap gate is **Milestone 43: Persona Profile Review and Study-Time Persona Creation**.

Current state:

- Milestones 0-42 are treated as implemented in the current roadmap, including scaled public launch readiness boundaries, governed review/redaction, longitudinal comparison, persona-library calibration, backend-owned launch-claim controls, frontend-to-Codex personal MVP activation, the Frontline Research Studio foundation, the first separate `/studio` frontline package, confirmed plan revisions, study-level multi-run reports, the route-aware Frontline Studio shell, the guided setup to live-run start flow, the Frontline evidence/run/report/comparison workspace, Frontline decision/share hardening, persona-library readiness plus panel contract hardening, the full Frontline personal-MVP reliability gate, live run observability, transcript/trace provenance, messaging validation, guided playbooks/reruns, continuous calibration observability, workspace privacy/export controls, and bounded integration/run-event surfaces.
- M27 is `implemented`: `5 / 5` stories complete, `26 / 26` story points complete, and `100.0%` complete by story-point rollup.
- M28 is `implemented`: `4 / 4` stories complete, `13 / 13` story points complete, and `100.0%` complete by story-point rollup.
- M29 is `implemented`: the separate Frontline Research Studio package exists under `frontend/frontline_research_studio`, the local SaaS wrapper serves `/studio`, and the frontline API can create plan proposals plus confirmed `StudyPlanRevision` records without exposing provider/job/filesystem controls as the default mental model.
- M30 is `implemented`: study-level reports are persisted as first-class `workspace_study_reports`, cite included run IDs and plan revision IDs, preserve stable/divergent signals plus human-validation gaps, and can be linked to decision logs.
- M31 is `implemented`: `/studio` is now a route-aware Frontline shell with backend-injected route context for workspace, projects, studies, setup, runs, evidence, reports, decisions, and share routes; the React shell renders route-specific pages with a fixed drill-down left rail where Projects, Project, and Study navigation levels are mutually exclusive, project/study levels have back navigation, the rail bottom preserves workspace/account identity, and the automated browser smoke gate covers refresh/back-forward/nav-level exclusivity/no-overflow/no-overlap/no-internal-term acceptance.
- M32 is `implemented`: `/studio/studies/new` and `/studio/studies/{study_id}/setup` now let users describe intent, create a study, tune target-audience criteria, choose a synthetic participant panel through a serious persona-library picker, draft a plan, approve it, and start a plan-linked synthetic research run from Frontline Studio without exposing provider/job/runtime controls as the default user model.
- M33 is `implemented`: `/studio/studies/{study_id}/runs/{run_id}`, `/evidence`, `/evidence-views/{evidence_view_id}`, and `/reports/{study_report_id}` now hydrate backend-owned evidence-query payloads into evidence-first user-facing review pages with source evidence, interpretation, summary boundary, contradictions, comparison, saved view provenance, cited report evidence, and human-validation gaps.
- M34 is `implemented`: `/studio/studies/{study_id}/decisions/{decision_log_id}` now shows current belief, evidence basis, confidence boundary, and human follow-up, and `/studio/share/{share_bundle_id}` now shows linked decision context, evidence digest, included viewer-safe artifacts, public boundary link, and synthetic-evidence limits without exposing internal platform language.
- M35 is `implemented`: `GET /api/v1/persona-library` exposes readiness states, selectable persona panels, coverage gaps, generation job history, and simulated-lens boundaries; `POST /api/v1/persona-library/generation-jobs` creates auditable gap-fill jobs; zero-selection plan approval is blocked; selected synthetic participant IDs, versions, artifact hashes, coverage snapshots, and provisional-persona status are preserved in approved plans, research-run metadata, and `frontline_persona_panel_snapshot.json`.
- M36 is `implemented`: the Frontline `/studio` personal-MVP loop now passes browser smoke from project and study setup through persona selection, plan approval, run execution, evidence review, saved evidence view, report, decision, and share; route refresh, back/forward, detail hydration, desktop layout, and explicit English / `zh-Hant` product chrome terminology checks are covered by the latest smoke artifact.
- M37 is `implemented`: `/studio/studies/{study_id}/runs/{run_id}` now exposes backend-owned run progress, transcript, and trace panels through route-safe APIs; evidence slices, saved evidence views, study reports, and decision logs can preserve `source_exchange_refs` and `source_trace_refs`.
- M38 is `implemented`: `messaging_validation` can be inferred from natural-language message, positioning, copy, landing-page, headline, or value-proposition intent, with message comprehension, credibility, trust language, misunderstanding, and adoption-boundary evidence kept distinct.
- M39 is `implemented`: `GET /api/v1/research-playbooks` exposes guided research playbooks and `POST /api/v1/studies/{study_id}/frontline-reruns` creates comparison-ready rerun plan proposals with source-run lineage and changed-assumption notes.
- M40 is `implemented`: `GET /api/v1/calibration-observatory` exposes continuous calibration health, unsupported evidence types, provider/mode/evidence coverage, and public-launch readiness now carries a calibration-observatory blocker when health is not ready.
- M41 is `implemented`: `GET /api/v1/privacy-export-controls`, `POST /api/v1/privacy-export-controls/policy`, and `POST /api/v1/privacy-export-controls/deletion-requests` expose backend-owned privacy, data-residency, retention, deletion, redaction, export/share, audit, and readiness controls; Frontline workspace and share review surfaces show privacy/export boundary cards.
- M42 is `implemented`: `GET /api/v1/studies/{study_id}/runs/{run_id}/events` exposes `workspace-run-event-stream/v1` for interview progress, safe transcript previews, observed-interview bridge metadata, and transcript/trace provenance; `GET /api/v1/integration-events` plus `POST /api/v1/integration-events/delivery-attempts` expose boundary-preserving integration events and delivery audit without bypassing evidence readiness or privacy/export controls.
- `specs/frontline_research_studio_ux_component_design_spec.md` is now the controlling UX/component spec for the next Studio implementation work. It defines route-level screens, component responsibilities, CTA placement, JTBD, UX rationale, and UX audit criteria.
- The frontend can now submit Codex-backed studies, complete live Codex-backed validation jobs, hydrate backend evidence-query results, preserve `live_synthetic` provider runtime boundaries through saved evidence views and decision logs, and complete the solo-user personal MVP workflows from the product shell.
- The latest Codex browser acceptances prove frontend-started live Codex completion for startup idea concept validation, UI/prototype comprehension validation with artifact handling, and pain/empathy/insight discovery with natural-language inference into `pain_point_discovery`.
- The personal MVP is locally usable for a solo founder/researcher, but outputs remain simulated evidence and are not human market proof or replacement-grade reliability.

Immediate next sequence:

1. Build Milestone 43 next: make persona profile review and study-time persona creation usable during plan setup so users can inspect who the study simulates before approving the plan.
2. Build Milestone 44 after M43: prepare procurement, workspace ownership, billing metadata, audit packs, and support boundary controls for enterprise evaluation.
3. Keep M45-M48 as public/replacement/scale reliability gates: multi-market benchmarks, replacement-readiness review, provider governance, and operational scale should not be pulled forward until calibration and evidence boundaries can survive higher volume.
4. Treat M37-M42 as completed research-quality and customer-operations gates, with M43 inserted as a missing persona-trust gate before broader enterprise work; future UI polish, broad SaaS, sales, or enterprise work must still preserve behavioral realism, decision prediction, evidence quality, calibration, privacy boundaries, integration boundaries, and scalable research throughput.

Next roadmap grouping:

- `Completed core quality gate (M35)`: synthetic participant selection is now auditable, reproducible, explicit, and separated from simulated public-figure/expert lenses.
- `Completed Frontline E2E reliability gate (M36)`: the personal-MVP study loop is now route-safe, refresh-safe, deep-link-safe, terminology-gated, and acceptance-test stable enough to support the next study type.
- `Completed interview observability gate (M37)`: live run progress, transcript, facilitator trace, synthetic participant reasoning trace, and source-linked evidence are now route-safe.
- `Completed Frontline workflow expansion (M38-M39)`: messaging validation, guided playbooks, rerun templates, and comparison-ready plan lineage are now implemented.
- `Completed calibration and launch-claim gate (M40)`: calibration health is now a continuous backend-owned quality signal with public-launch readiness impact.
- `Completed privacy/export hardening (M41)`: customer data controls, deletion request lineage, data-residency policy, export/share boundary copy, and privacy audit are now backend-owned.
- `Completed integration and run-event hardening (M42)`: run event streams, observed-interview bridge events, boundary-preserving integration events, and delivery audit are now backend-owned.
- `Active persona trust and study-time creation gate (M43)`: full profile review, explicit study-time persona generation, and selected-persona lineage must be visible before plan approval.
- `Upcoming enterprise operations hardening (M44)`: strengthen procurement, ownership, billing metadata, audit packs, and support boundary controls after persona trust and event surfaces are governed.
- `Public/replacement/scale readiness (M45-M48)`: expand benchmark coverage, provider governance, replacement-readiness review, and scale only after evidence boundaries can support those claims.

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

8. `workflow_mapping` - `implemented`
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
- `scripts/start_local_workspace_demo.bat` now boots the local engineering demo through one repo-local entrypoint that restarts the API and worker, waits for the authenticated session endpoint to respond, and opens the hosted workspace shell by default
- `scripts/start_local_workspace_demo.bat` now also resets the local `ws_api_demo` workspace before boot so repeated engineering-demo runs do not hit the retained trial daily-run quota and silently block new submissions
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
- `scripts/build_workspace_shell_app.bat` plus `scripts/start_local_workspace_demo.bat` now make that framework host a repeatable local workflow instead of a one-off manual build step
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

### Milestone 16: Post-Login Workspace IA and Active-Route Shell

Status: `implemented`

Scope:

- turn the accepted post-login IA into a shared route model for active-study landing, no-study intake landing, deep links, primary research navigation, and secondary governance navigation
- make the framework-hosted workspace shell route-owned so only one primary or secondary product surface is expanded at a time
- preserve Stage 15 controller DOM anchors while hiding inactive surfaces, avoiding a controller rewrite before the route contract is stable
- keep `/app/jobs/{job_id}` and related evidence deep links evidence-first instead of raw job-management-first

Implemented repository evidence:

- `specs/milestone_16_post_login_workspace_ia_design_spec.md` defines the implemented Milestone 16 route model, shell behavior, route rules, acceptance criteria, and verification path.
- `demo/workspace_ui_shared/post_login_workspace_ia.mjs` now defines the shared post-login IA contract with active surface derivation, primary/secondary nav, landing rules, deep-link handling, and acceptance gates.
- `frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx` now consumes the route model, exposes route metadata, and hides inactive route surfaces instead of rendering every research/settings/support/debug region as one long page.
- `frontend/workspace_shell_app/src/RealUserWorkspaceNav.jsx` now renders contract-driven primary research navigation before secondary governance/support navigation.
- `frontend/workspace_shell_app/src/main.css` now adds the active-route grid, hidden surface rule, route context drawer, and sidecar width guard against the previous overlap risk.
- `tests/workspace_ui/test_milestone16_post_login_workspace_ia.mjs` verifies active-study/no-study landing, deep-link behavior, nav order, route-owned React source behavior, and CSS overlap regression checks.

Exit criteria:

- post-login route behavior is study-first, not dashboard-first, job-first, prompt-first, or admin-first
- the visible shell expands only the active route surface while keeping governance/support reachable
- job and evidence deep links preserve the evidence review context required for comparison, calibration, decisions, and sharing boundaries

### Milestone 17: External Human Benchmark Calibration

Status: `implemented`

Scope:

- move Milestone 15 calibration beyond the checked-in fixture into external benchmark datasets or manually reviewed real study outcomes
- compare synthetic predictions against human-reviewed objections, trust gaps, adoption barriers, task failures, decision changes, and abandonment signals
- attach benchmark provenance, research stage, evidence type, sample coverage, and review quality to every calibration record
- keep readiness statuses scoped by research stage and evidence type instead of making broad replacement claims

Current proof-of-progress:

- `specs/milestone_17_external_human_benchmark_calibration_design_spec.md` now records the first M17 slice and its external benchmark-definition contract.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now resolves suite-level `benchmark_path` references to external benchmark definition JSON files and preserves `benchmark_definition_path` in calibration artifacts.
- `fixtures/human_calibration/external_suite.json` plus `fixtures/human_calibration/benchmarks/inbox_coach_followup_real_study_sample.json` now provide a checked-in external benchmark example with `source_type: real_human_study`.
- `tests/unit/test_human_calibration.py` now verifies external benchmark resolution and a scoped `real_human_study` benchmark path that can reach `candidate_replacement_ready`.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now also maps reviewer-coded `human_outcomes.review_findings` into normalized calibration signals without breaking the existing `human_outcomes.signals` contract.
- `fixtures/human_calibration/external_review_findings_suite.json` plus `fixtures/human_calibration/benchmarks/inbox_coach_followup_review_findings_sample.json` now provide a checked-in reviewer-coded benchmark example for the same run family.
- `tests/unit/test_human_calibration.py` now verifies that reviewer-coded findings are projected into calibration output and can still produce scoped readiness scoring.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now also extracts bounded `task_failure`, `abandonment`, and permission/trust-gap signals from `observed_action_trace.json` when prototype-validation traces are available.
- `fixtures/human_calibration/runs/browser_trace_permission_dropoff_sample/`, `fixtures/human_calibration/benchmarks/workspace_review_browser_trace_sample.json`, and `fixtures/human_calibration/external_browser_trace_suite.json` now provide a checked-in browser-trace calibration example.
- `tests/unit/test_human_calibration.py` now verifies direct browser-trace signal extraction and scoped browser-trace-to-human-outcome alignment for prototype validation.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now emits benchmark-level `readiness_projection` records plus suite-level aggregate readiness projection so external benchmark coverage, source type, threshold gaps, and gate reasons become explicit output rather than implied interpretation.
- `fixtures/human_calibration/mixed_external_suite.json` now provides a checked-in aggregate-readiness example covering candidate, high-stakes-gated, and threshold-gap scopes.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects that readiness summary into backend-owned evidence reliability records and missing-context review.

Exit criteria:

- at least one non-fixture benchmark suite can be loaded, scored, archived, and projected into evidence reliability records
- precision, recall, F1, alignment, missed human signals, and unsupported synthetic signals are available by research stage and evidence type
- browser-observed traces can be compared against human-reviewed task outcomes without collapsing observed behavior into stated intention

### Milestone 18: Discovery Coverage Completion

Status: `implemented`

Scope:

- implement `workflow_mapping` as the missing discovery expansion mode
- capture current workflow, handoffs, fragmentation, workaround chains, switching costs, and responsibility gaps
- preserve discovery discipline by avoiding early concept introduction
- connect workflow evidence to study activity, saved evidence views, and decision logs

Current proof-of-progress:

- `specs/milestone_18_workflow_mapping_design_spec.md` now records the first M18 slice and its workflow-mapping mode contract.
- `src/ai_validation_swarm/cli/main.py` now accepts `workflow_mapping` in facilitated and observer interview entrypoints.
- `src/ai_validation_swarm/facilitator/runtime.py` now treats `workflow_mapping` as a supported first-class mode with explicit coverage requirements, gap instructions, and premature-closure gate enforcement.
- `src/ai_validation_swarm/prompts/facilitator-interview/v2.md`, `src/ai_validation_swarm/prompts/facilitator-synthesis/v2.md`, and `src/ai_validation_swarm/prompts/facilitator-quality-evaluator/v2.md` now teach and audit workflow-mapping behavior explicitly.
- `tests/unit/test_facilitator_runtime.py` now verifies a full workflow-mapping runtime path, and `tests/unit/test_observer_runtime.py` now verifies the same mode reaches facilitator and quality contexts through the observer path.
- `src/ai_validation_swarm/facilitator/runtime.py` now writes a structured `workflow_map` projection into workflow-mapping insight reports instead of leaving discovery workflow evidence as prose only.
- `src/ai_validation_swarm/saas/evidence_query.py` now exposes workflow-map-aware evidence-query results, tags, and replay-style review steps for workflow sequence, handoff, fragmentation, workaround, switching-cost, and responsibility-gap evidence.
- `src/ai_validation_swarm/saas/runtime.py` now carries selected workflow evidence context into saved evidence views and decision logs so discovery review can preserve workflow-fragmentation lineage beyond the raw interview folder.
- `tests/unit/test_saas_runtime.py` now verifies workflow-map evidence context persists into saved evidence views and decision logs.

Exit criteria:

- discovery coverage includes problem reality, root cause, decision reconstruction, and workflow mapping
- workflow mapping outputs are queryable as evidence, not only prose summaries
- the platform can identify adoption barriers caused by process fragmentation before a solution concept is evaluated

Completion review:

- keep `Milestone 19` next because the core gap is no longer discovery coverage, but calibrated distribution and claim boundaries
- keep `Milestone 20` as the first MVP gate because discovery coverage plus calibration still need market-facing readiness controls before design-partner release

### Milestone 19: Calibration-Backed Evidence Readiness Gates

Status: `implemented`

Scope:

- define release-grade evidence readiness gates for discovery, concept evaluation, and prototype validation
- expose benchmark coverage, calibration confidence, contradiction density, missing-context risk, and human-validation gaps as backend-owned readiness signals
- prevent export/share flows from presenting uncalibrated synthetic outputs as market proof
- make calibration status visible in evidence review, decision logs, and share bundles

Completion evidence:

- `specs/milestone_19_calibration_backed_evidence_readiness_gates_design_spec.md` now records the implemented readiness-gate contract and milestone completion review.
- `src/ai_validation_swarm/saas/runtime.py` now derives one `readiness_gate` from completed-run evidence reliability plus attached human calibration.
- the same runtime now carries readiness-gate state into evidence-query API responses, saved evidence views, decision logs, export manifests, export bundle summaries, share payloads, and share bundle summaries.
- the same runtime now blocks high-stakes public share creation and re-checks readiness restrictions at public share read time.
- `tests/unit/test_saas_runtime.py` now verifies pending readiness state, human-validation-required export/share state, workflow review readiness inheritance, scoped externally ready export/share state when candidate-ready external calibration exists, and public-share blocking for high-stakes human-review-required evidence.

Exit criteria:

- every evidence review can show whether its claims are fixture-only, externally calibrated, insufficiently benchmarked, or human-review-required
- decision logs and share bundles inherit evidence readiness boundaries automatically
- high-stakes or uncalibrated contexts stay gated regardless of UI polish

### Milestone 20: Controlled Market MVP Launch

Status: `implemented`

MVP gate: `first controlled market release`

Scope:

- package the study-first workspace for design partners or tightly controlled paid pilots
- support the default loop: Ask -> Clarify -> Confirm Plan -> Run -> Review Evidence -> Compare -> Decide -> Share With Boundary
- include onboarding, sample study templates, clear synthetic-evidence disclaimers, benchmark coverage disclosure, and support handoff
- limit launch scope to discovery, concept evaluation, and prototype validation use cases that pass Milestone 19 readiness gates

Completion evidence:

- `specs/milestone_20_controlled_market_mvp_launch_design_spec.md` now records the first M20 slice and its controlled-launch boundary.
- `src/ai_validation_swarm/saas/runtime.py` now derives backend-owned `mvp_launch_scope` from `readiness_gate` state.
- export manifests, export bundle summaries, share payloads, and share bundle summaries now carry the same `mvp_launch_scope`.
- `specs/workspace_mvp_promotion_contract.md` now defines the second M20 slice for design-partner promotion review.
- `src/ai_validation_swarm/saas/runtime.py` now derives backend-owned `mvp_promotion` from `mvp_launch_scope`, persists that promotion state into export/share payloads, and blocks `design_partner_candidate` public share creation until explicit approval exists.
- `src/ai_validation_swarm/saas/api.py` now exposes request/review endpoints for export-bundle-scoped MVP promotion.
- `specs/workspace_partner_onboarding_contract.md` now defines the third M20 slice for approved design-partner onboarding and bounded circulation.
- `src/ai_validation_swarm/saas/runtime.py` now requires named partner context for approved design-partner shares and persists one backend-owned `partner_onboarding` pack into the public share payload.
- `specs/workspace_mvp_release_review_contract.md` now defines the fourth M20 slice for final public-share release review.
- `src/ai_validation_swarm/saas/runtime.py` now derives backend-owned `mvp_release_review` for design-partner shares, persists it into share payloads/summaries, and blocks public read until final release approval exists.
- `src/ai_validation_swarm/saas/api.py` now exposes request/review endpoints for share-bundle-scoped controlled MVP release review.
- `tests/unit/test_saas_runtime.py` now verifies:
  - uncalibrated evidence remains `internal_only`
  - high-stakes human-review-required evidence remains `blocked`
  - scoped externally ready evidence becomes `design_partner_candidate`
  - design-partner-candidate shares are blocked until MVP promotion is approved
  - approved design-partner shares still fail without named partner context and then persist a bounded onboarding pack when that context is provided
  - approved design-partner shares still stay non-public until final release review is approved

Completion review:

- Milestone 20 is now complete because the platform has one backend-owned controlled MVP path from readiness-gated evidence through promotion review, partner onboarding, and final share-artifact release review.
- Keep `Milestone 21` next because the main remaining gap is no longer MVP circulation policy, but production API and deployment boundary hardening.
- Do not broaden launch claims yet; this remains a bounded design-partner MVP, not public self-serve proof.

Exit criteria:

- a real external team can create a workspace, start a study, run a calibrated-supported research flow, review evidence boundaries, log a decision, and export/share bounded outputs
- every customer-facing claim stays inside the calibrated evidence boundary
- launch is positioned as `calibrated synthetic research support`, not replacement-grade human market proof

### Milestone 21: Production API and Deployment Boundary

Status: `implemented`

Scope:

- introduce a thin FastAPI or equivalent typed API adapter only after the existing WSGI route, worker, and frontend contracts remain stable
- add deployment environment profiles, secret handling, health checks, backup expectations, and structured operational logs
- preserve the Python research core as the owner of simulation, evidence ranking, calibration, and worker execution

Progress evidence:

- `specs/milestone_21_production_api_and_deployment_boundary_design_spec.md` now records the accepted first M21 slice and its boundary decisions.
- `src/ai_validation_swarm/saas/api.py` now exposes public `GET /api/v1/health`, `GET /api/v1/ready`, and `GET /api/v1/service-metadata` endpoints for deployment probes and hosted wrapper discovery.
- the same API wrapper now accepts one explicit `SaasApiDeploymentProfile` with `deployment_env`, `public_base_url`, `secret_source`, `expected_backup_mode`, `allow_query_token_bootstrap`, and `structured_logs`.
- hosted `/app/*?token=...` browser-session bootstrap is now deployment-profile-gated, so production-like environments can reject query-token bootstrap instead of inheriting the local MVP default.
- `src/ai_validation_swarm/saas/runtime.py` now exposes backend-owned runtime operations state, while `src/ai_validation_swarm/saas/job_store.py` now supports aggregate job and browser-session listing for that operations contract.
- `src/ai_validation_swarm/cli/main.py` now accepts deployment-profile arguments for `serve-saas-api`, so runtime operators can configure production-like readiness policy without changing research logic.
- `tests/unit/test_saas_runtime.py` now verifies local health/readiness success, service-metadata exposure, production readiness failure when deployment hardening is missing, hardened-production readiness success, and hosted query-token bootstrap rejection when disabled.
- the same API wrapper now also exposes public `GET /api/v1/contract-manifest`, giving hosted wrappers one machine-readable typed route contract without requiring a FastAPI rewrite first.
- the same runtime now also exposes authenticated `GET /api/v1/operations/summary`, making worker, evidence, calibration, decision, distribution, support, and audit paths observable from backend-owned state.
- `tests/unit/test_saas_runtime.py` now also verifies contract-manifest exposure plus authenticated workspace operations-summary counts across the study lifecycle.

Completion review:

- Milestone 21 is now complete because the platform has one explicit deployment boundary, wrapper contract boundary, and operations observability boundary around the existing research core.
- Keep `Milestone 22` next because the main remaining productization gap is no longer deployment contract ambiguity, but real team collaboration and governance hardening.
- Do not claim scaled public launch readiness yet; M22 through M25 still remain the gating path to M26.

Exit criteria:

- hosted wrappers can consume typed API contracts without duplicating research logic
- worker, evidence, calibration, and audit paths are observable in production-like environments
- deployment readiness improves throughput and reliability without changing evidence semantics

### Milestone 22: Team Collaboration and Governance Hardening

Status: `implemented`

Scope:

- harden workspace membership, roles, review permissions, billing/quota behavior, retention, audit history, and support snapshots for real team use
- improve decision review workflows, comments, approvals, and handoff history
- keep settings and billing secondary to the research loop

Progress evidence:

- `specs/milestone_22_team_collaboration_and_governance_hardening_design_spec.md` now records the accepted first M22 slice and its governance boundary.
- `src/ai_validation_swarm/saas/runtime.py` now persists backend-owned `review_assignment` and `review_assignment_history` on decision logs, and only `owner` / `admin` members or explicitly assigned reviewers may move decisions into `approved` or `needs_revision`.
- the same runtime now persists backend-owned `handoff` and `handoff_history` on support snapshots, including `unassigned`, `assigned`, `acknowledged`, and `resolved` states plus assignee-sensitive permission rules.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/decision-logs/{decision_log_id}/review-assignment` and `POST /api/v1/support-snapshots/{support_snapshot_id}/handoff`.
- `src/ai_validation_swarm/saas/job_store.py` now supports support-snapshot metadata mutation for durable handoff history.
- study activity now includes `decision_log.review_assignment_updated` and `support_snapshot.handoff_updated`, so governance transitions stay visible in the same study timeline as runs, exports, shares, and support creation.
- `tests/unit/test_saas_runtime.py` now verifies that unassigned reviewers cannot approve decisions, assigned reviewers can approve decisions, support handoff cannot be acknowledged before assignment, assigned handoff owners can acknowledge and resolve snapshots, and both governance transitions appear in study activity.
- export bundles now preserve append-only `mvp_promotion_history`, share bundles now preserve append-only `mvp_release_review_history`, and share payloads carry forward the same promotion history instead of collapsing circulation governance into one latest-status field.
- study activity now also includes `export_bundle.mvp_promotion_requested`, `export_bundle.mvp_promotion_reviewed`, `share_bundle.mvp_release_review_requested`, and `share_bundle.mvp_release_reviewed`, so external-circulation governance remains visible from the study surface.
- workspace settings and billing surfaces now preserve append-only `billing_history` and `policy_history`, accept optional operator notes on billing/quota/retention mutations, and emit separate `workspace_billing.updated` and `workspace_policy.updated` audit actions.

Completion review:

- Milestone 22 is now complete because governance history now spans decision review, support handoff, export/share circulation review, and workspace billing/quota/retention policy changes.
- Keep `Milestone 23` next because the main remaining public-launch blocker is persona coverage and human-difference calibration depth rather than collaboration/governance ambiguity.
- Keep `Milestone 24` and `Milestone 25` after that because scaled public launch still depends on longitudinal learning and explicit high-stakes review boundaries.

Exit criteria:

- a team can collaborate on studies and decisions without losing evidence lineage
- governance events are auditable and attached to the relevant workspace, study, evidence view, decision, export, or share object
- quota, billing, and retention controls are reliable enough for controlled paid pilots

### Milestone 23: Persona Library and Human Difference Calibration

Status: `implemented`

Scope:

- expand reusable persona libraries while preserving concept-neutral human difference axes
- calibrate persona/panel coverage against benchmark deltas and underrepresented decision patterns
- improve panel selection diversity, similarity, trait provenance, and explainability

Progress evidence:

- `specs/milestone_23_persona_library_and_human_difference_calibration_design_spec.md` now records the accepted M23 scope, story breakdown, and first implemented slice.
- `src/ai_validation_swarm/personas/analysis.py` now emits `human_difference_axis_summary`, including required-axis coverage, bucket distribution, supporting behavior-model coverage, and explicit coverage gaps.
- `src/ai_validation_swarm/saas/metadata_store.py` now persists every populated `human_difference_axes.*` value into `persona_trait_assignments`, so later panel-selection and calibration flows can query real trait provenance instead of only narrative persona text.
- `src/ai_validation_swarm/cli/main.py` now surfaces the same human-difference coverage summary through `summarize-personas`.
- `tests/unit/test_persona_analysis.py` and `tests/unit/test_metadata_store.py` now verify the new coverage/gap contract plus metadata-index persistence.
- `src/ai_validation_swarm/evaluation/human_calibration.py` now emits heuristic `miss_attribution` records so calibration can distinguish likely persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking causes instead of collapsing all misses into one score delta.
- `src/ai_validation_swarm/saas/evidence_query.py` now projects that attribution into product-facing reliability review as `calibration_miss_attribution`.
- `tests/unit/test_human_calibration.py` now verifies both aligned and mismatched calibration cases for the new attribution contract.
- `src/ai_validation_swarm/sampling/engine.py` now emits backend-owned panel explainability with selected-vs-eligible human-difference coverage, under-covered axis projection, similarity hotspots, and per-persona inclusion rationale instead of leaving panel composition implicit.
- `src/ai_validation_swarm/validation/runner.py` now persists that explainability into `sampling.json`, and `src/ai_validation_swarm/reporting/artifacts.py` now projects the same `panel_rationale` and `panel_explainability` into `report.json`.
- `tests/unit/test_sampling.py` and `tests/integration/test_validation_run.py` now verify the new panel explainability contract through direct sampling and end-to-end validation artifacts.

Exit criteria:

- panel composition can explain which human difference axes are covered and which are missing
- calibration reports can identify whether misses are caused by persona gaps, facilitator behavior, stimulus interpretation, or synthesis/ranking issues
- persona core remains reusable and does not bake in concept conclusions

Completion review:

- Milestone 23 is now complete because persona-library coverage, human-difference trait provenance, calibration miss attribution, and backend-owned panel explainability are all explicit, durable, and test-covered repository surface rather than implied narrative metadata.
- Keep `Milestone 24` next because the most important remaining research bottleneck is now longitudinal comparison across repeated studies and prototype revisions, not one-run panel composition opacity.
- Keep `Milestone 25` after that because high-stakes review hardening still depends on stronger evidence continuity and replayable longitudinal history.

### Milestone 24: Longitudinal Study and Panel Learning

Status: `implemented`

Scope:

- support repeated studies over time while preserving study, run, evidence, decision, and calibration lineage
- learn recurring failure modes, contradiction patterns, and adoption barriers across related studies
- keep longitudinal learning as evidence-linked study history, not chat-only memory

Progress evidence:

- `specs/milestone_24_longitudinal_study_and_panel_learning_design_spec.md` now records the accepted M24 scope, technical boundary, story breakdown, and first active slice for evidence-linked longitudinal comparison and lineage.
- `src/ai_validation_swarm/saas/runtime.py` now projects backend-owned `longitudinal_comparison` into workspace evidence-query payloads, including same-study repeated runs, same-project neighboring studies, study-timeline entries, and calibration-lineage summaries.
- the same runtime now projects `audit_lineage.longitudinal_set` plus lightweight `longitudinal_focus` snapshots for saved evidence views and decision logs, so longitudinal review stays attached to durable collaboration artifacts instead of transient page state.
- the same runtime now projects backend-owned `recurring_signal_synthesis` into longitudinal comparison, surfacing recurring objections, trust gaps, failure patterns, and contradiction patterns together with run observations and linked study-timeline artifacts.
- the same runtime now persists lightweight `recurring_signal_focus` snapshots into saved evidence views and decision logs so repeated-signal review focus survives beyond one page session.
- the same runtime now projects backend-owned `panel_learning_projection` into longitudinal comparison, reading report-level panel explainability plus decision-log history to summarize repeated hotspot axes, persistent under-covered axes, barrier fade/emergence, confidence trend, and evidence-backed versus assumption-led decision changes.
- decision-log creation now refreshes its own longitudinal snapshot after persistence so the durable decision artifact can include itself in study-timeline and panel-learning projection rather than keeping only a pre-create snapshot.
- `specs/workspace_evidence_query_contract.md` and `specs/workspace_shell_snapshot_contract.md` now record the longitudinal comparison extension to the evidence-query and shell-snapshot contracts.
- `tests/unit/test_saas_runtime.py` now verifies same-study repeated-run lineage, same-project neighboring-study lineage, study-timeline projection, recurring-signal synthesis, panel-learning projection, decision-trend projection, and durable longitudinal/recurring/panel-learning focus persistence on saved evidence views and decision logs.

Exit criteria:

- teams can compare evidence and decisions across study revisions or repeated prototype iterations
- recurring objections, trust gaps, and behavioral failures can be tracked without overwriting previous evidence
- panel learning improves decision prediction while preserving auditability

Completion review:

- Milestone 24 is now complete because repeated-study comparison, recurring-pattern synthesis, panel-learning projection, and decision-trend projection are all explicit backend-owned evidence surfaces instead of page-local reconstruction.
- Keep `Milestone 25` next because the strongest remaining public-launch blocker is explicit regulated and high-stakes review handling, not more repeated-study evidence continuity.
- Keep `Milestone 26` after that because broader public launch still depends on both governed-boundary hardening and production-grade customer-facing operations.

### Milestone 25: Regulated and High-Stakes Review Boundary

Status: `implemented`

Scope:

- formalize high-stakes review gates for finance, health, employment, legal, children, public safety, and destructive or credentialed workflows
- add redaction, reviewer handoff, policy labeling, and compliance-ready audit bundles
- ensure synthetic evidence cannot be presented as determinative proof in regulated contexts

Implemented repository evidence:

- `specs/milestone_25_regulated_and_high_stakes_review_boundary_design_spec.md` now records the accepted M25 scope, technical boundary, story breakdown, and first active slice for high-stakes classification plus governed review gating.
- `src/ai_validation_swarm/saas/runtime.py` now classifies study intent, desired output, first task, and artifact references into backend-owned `regulated_review_boundary` state and blocks validation-job submission when a regulated/high-stakes study lacks explicit governed boundary acknowledgement.
- the same runtime now projects that boundary into study summaries, workspace support diagnostics, validation-job metadata, export manifests, and share payloads so the governed state stays backend-owned across run, support, export, and share surfaces.
- `src/ai_validation_swarm/saas/api.py` now accepts `study_id` on `/api/v1/support-diagnostics`, and `tests/unit/test_saas_runtime.py` now verifies blocked governed-study submission, explicit acknowledgement-based allow execution, and export/share boundary propagation.
- the same runtime now persists study-level governed reviewer assignment, projects backend-owned `governed_review` state into evidence query, evidence views, decision logs, export manifests, share payloads, and support diagnostics, and blocks partner-facing share creation when reviewer responsibility is missing or escalated.
- regulated/high-stakes decision logs now inherit default reviewer assignment from the study-level governed handoff, and final decision approval now requires that named governed reviewer responsibility already exists.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/studies/{study_id}/governed-review-assignment`, and `tests/unit/test_saas_runtime.py` now verifies governed reviewer assignment mutation, study-activity audit history, evidence-query policy projection, decision-review inheritance, export refresh, and share release after reviewer assignment.
- the same runtime now persists study-level governed redaction policy, projects backend-owned `governed_redaction` state into evidence query, evidence views, decision logs, support diagnostics, export manifests, and share payloads, and blocks partner-facing share creation until active viewer-safe redaction exists.
- the same runtime now writes `compliance_audit_bundle.json` for export bundles, share bundles, and governed support snapshots so classification, reviewer, redaction, readiness, circulation, and audit-history state stay reconstructable without raw filesystem forensics.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/studies/{study_id}/governed-redaction`, and `tests/unit/test_saas_runtime.py` now verifies governed redaction mutation, share redaction application, compliance-audit-bundle persistence, and study-activity audit history.
- the repository already has three prerequisite boundary layers that M25 will extend rather than replace:
  - Milestone 14 browser-behavior safety gates for credentialed, destructive, external, payment, token, and transfer flows
  - Milestone 19 readiness-gate and high-stakes share-block restrictions
  - Milestone 22 reviewer assignment, support handoff, and append-only governance history
- Milestone 24 longitudinal learning is now explicit enough that governed review can reason over repeated-study evidence continuity instead of isolated one-run output.

Exit criteria:

- high-stakes studies require explicit review boundary handling before execution or sharing
- exported bundles carry safety, calibration, and human-review-required labels when applicable
- support and audit surfaces can reconstruct why a study was blocked, allowed, or escalated

Completion review:

- Milestone 25 is now complete because regulated/high-stakes classification, governed reviewer handoff, governed redaction, and compliance-audit reconstruction all exist as backend-owned runtime and artifact surface instead of page-local warnings.
- Keep `Milestone 26` next because the strongest remaining launch blocker is now broader public-claim discipline and production-grade customer operations around the bounded MVP surface, not additional governed-boundary plumbing.
- Keep one post-M26 activation gate after that because public launch should not scale until the normal frontend study flow can run live synthetic experiments with explicit provider lineage and mock-vs-live evidence boundaries.

### Milestone 26: Scaled Public Launch Readiness

Status: `implemented`

Scope:

- prepare the platform for broader self-serve or public launch after controlled MVP learning
- harden onboarding, pricing, billing operations, support playbooks, benchmark disclosure, observability, uptime expectations, and customer-facing documentation
- define which use cases can be marketed and which remain research-preview only

Current proof-of-progress:

- `specs/milestone_26_scaled_public_launch_readiness_design_spec.md` now records the accepted M26 scope, architecture boundary, implemented story breakdown, and completion review.
- `specs/workspace_public_launch_readiness_contract.md` now defines the backend-owned workspace launch-readiness summary, per-artifact public-claims boundary contract, customer-operations/support readiness boundary, and self-serve onboarding/pricing boundary.
- `src/ai_validation_swarm/saas/runtime.py` now exposes backend-owned `describe_workspace_public_launch_readiness()` and derives `public_claims_boundary` from readiness-gate, launch-scope, governed-review, and governed-redaction state instead of leaving customer-facing claim posture to page-local interpretation.
- the same runtime now projects `public_claims_boundary` into export-bundle summaries, share-bundle summaries, export manifests, share payloads, and public-share payloads so benchmark disclosure and customer-facing claim limits stay attached to the distributed artifact.
- the same runtime now also derives backend-owned `launch_blockers` plus `customer_operations_support_boundary` from billing/quota state, submission-gate rules, failed-job support coverage, and durable support handoff state so broader launch no longer depends on manual operator memory for customer-ops blockers.
- the same runtime now also derives backend-owned `self_serve_onboarding_pricing_boundary` from plan tier, billing status, price-book alignment, seat count, quota/retention limits, owner/submitter membership, and active token state so onboarding and pricing readiness are testable backend posture.
- `src/ai_validation_swarm/saas/api.py` now exposes authenticated `GET /api/v1/public-launch-readiness` and publishes that route through service metadata and the contract manifest for wrapper consumption.
- `tests/unit/test_saas_runtime.py` now verifies the public-launch-readiness endpoint, its inclusion inside operations summary, controlled-MVP public-claims boundary projection on export/share surfaces, bounded-ready ordinary-study support posture, explicit support-blocker transitions for failed jobs and open handoffs, and self-serve onboarding/pricing blocker transitions from trial setup to bounded paid-plan readiness.

Exit criteria:

- public-facing claims are backed by benchmark coverage and readiness gates
- production operations can support multiple teams without manual intervention for ordinary studies
- the platform can sell bounded synthetic research workflows without implying unsupported replacement-grade reliability

Completion review:

- Milestone 26 is now complete because public claim posture, benchmark disclosure, customer-operations/support readiness, self-serve onboarding/pricing readiness, and aggregate launch blockers are all backend-owned and test-covered through the authenticated launch-readiness summary and artifact projection path.
- Broader bounded public/self-serve launch can now be evaluated from backend-owned state, but unrestricted public signup, payment-provider checkout, enterprise procurement, open benchmark dashboards, and replacement-grade claims remain later milestones.
- Revise the next milestone because the largest current user-facing gap is not messaging. The workspace shell can submit validation jobs, but the validation-job runtime provider boundary still needs to support Codex-backed live synthetic experiments from the frontend instead of relying on mock-only validation-run provider construction.
- Defer messaging validation until after the frontend can start, monitor, audit, and review Codex-backed synthetic research from the normal study-first product path.

### Milestone 27: Frontend-to-Codex Live Experiment Runtime

Status: `implemented`

Personal MVP gate: `solo founder / researcher usable MVP`

Current product decision:

- this milestone is the completed personal MVP gate for a solo founder or researcher using the local product shell
- the normal frontend path now proves a complete live Codex-backed solo-user research loop across concept validation, UI/prototype comprehension validation, and pain/empathy/insight discovery
- personal MVP acceptance was judged from the frontend product surface, not from CLI-only execution or backend-only contracts
- the user can start from a research need, confirm the inferred plan, run the study, review evidence, compare, decide, and preserve the synthetic-evidence boundary without learning internal mode taxonomy

Latest checkpoint:

- M27 is `5 / 5` stories complete, `26 / 26` story points complete, and `100.0%` complete by story-point rollup.
- Completed M27 work covers live-provider construction, provider lineage, readiness/failure states, mock-vs-live evidence-boundary preservation, frontend provider-runtime projection, Windows-safe Codex CLI prompt transport, workflow-specific personal MVP browser acceptance, and discovery-intent inference into `pain_point_discovery`.
- The personal MVP is complete for local solo-user operation because all three personal workflows are browser-verified with live Codex-backed evidence, evidence review, saved evidence views, decision logs, share-boundary preservation, and layout overlap gates.
- This does not mean the platform has human market proof, broad benchmark coverage, or replacement-grade reliability.

Scope:

- connect the workspace validation-job runtime to a live `codex` / `codex-sdk` provider path instead of leaving the frontend study path dependent on the mock-only validation provider factory
- expose Codex auth/readiness, provider selection, runtime failure categories, timeout/retry state, and mock-vs-live evidence boundaries through backend-owned workspace snapshots
- preserve provider, model, prompt, auth-source, transport, latency, and failure metadata in run, evidence-query, audit-lineage, export/share, and support surfaces
- prove the three solo-user MVP research workflows from the normal frontend path: founder concept validation, UI/prototype comprehension validation, and pain/empathy/insight discovery
- browser-verify that a user can start from the frontend study flow, confirm a plan, submit a Codex-capable run, monitor completion or failure, and review evidence without dropping to CLI

Current proof-of-progress:

- `src/ai_validation_swarm/providers/openai_validation.py` now defines a live validation-run provider adapter around the existing `OpenAIResponsesClient`, mapping LLM JSON into `PersonaResponse`, `SkepticReview`, `AuditFinding`, and planner outputs used by the existing validation runner.
- `src/ai_validation_swarm/providers/factory.py` now supports `openai`, `agnes`, `codex`, and `codex-sdk` provider names while preserving `mock` as an explicit demo/fallback provider.
- `src/ai_validation_swarm/validation/runner.py` now writes `provider.provider_name` into `run_contract.json` when available, so completed evidence can distinguish `mock`, `codex`, and `codex-sdk` instead of only seeing the adapter class name.
- `tests/unit/test_openai_validation_provider.py` verifies live-provider JSON mapping, factory routing for `codex`, and run-contract provider lineage without making a real LLM call.
- `src/ai_validation_swarm/saas/runtime.py` now exposes backend-owned provider runtime boundaries through workspace session, workspace shell, evidence query, support diagnostics, operations summary, validation-job metadata, and failure audit payloads.
- provider runtime boundaries now distinguish `mock_demo`, `live_synthetic`, and `unsupported` evidence modes; expose Codex auth readiness without making a live model call; and classify unsupported provider, missing auth, timeout, refusal, and retryable transport states as product-visible runtime statuses.
- `specs/workspace_shell_snapshot_contract.md`, `specs/workspace_support_surface_contract.md`, and `specs/workspace_validation_job_bridge_contract.md` now record the provider runtime boundary contract.
- `tests/unit/test_saas_runtime.py` now verifies Codex provider boundary projection in workspace shell/evidence query/session and unsupported-provider failure projection in support diagnostics and operations summary.
- provider runtime boundaries now carry into saved evidence views, decision logs, export bundle summaries, export manifests, share bundle summaries, public share payloads, compliance audit distribution context, README projections, and export/share audit events.
- `specs/workspace_decision_review_surface_contract.md`, `specs/workspace_export_bundle_contract.md`, and `specs/workspace_share_bundle_contract.md` now record provider runtime boundary preservation for decision and distribution artifacts.
- `tests/unit/test_saas_runtime.py` now verifies that evidence views, decision logs, export manifests, share summaries, and public share payloads preserve `mock_demo` provider boundary instead of collapsing evidence mode during distribution.
- `demo/workspace_ui_shared/workspace_shell_runtime_client.mjs`, `demo/workspace_ui_shared/workspace_shell_app.mjs`, and `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now carry backend-owned `provider_runtime` state into the page-facing frontend model, including provider evidence mode, auth readiness, runtime status, boundary message, next actions, catalog, and mock-vs-live job counts.
- `frontend/workspace_shell_app/src/EvidenceReviewPage.jsx` and `demo/workspace_ui_moss_stage15/index.html` now expose a visible provider-runtime boundary card and provider catalog in the evidence-review path, so Codex readiness, transport failure, or missing-auth state can be reviewed without dropping to CLI.
- `tests/workspace_ui/test_workspace_shell_frontend_adapter.mjs`, `tests/workspace_ui/test_workspace_shell_runtime_client.mjs`, `tests/workspace_ui/test_workspace_shell_app.mjs`, and `tests/workspace_ui/test_stage15_shell_document.mjs` now verify provider-runtime projection, shell-snapshot hydration, controller compatibility, and Stage 15 document anchors.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now supports provider-parameterized browser smoke via `STAGE15_PROVIDER_NAME`, `STAGE15_SAMPLE_SIZE`, and multi-status `STAGE15_EXPECTED_JOB_STATUS`, and it records provider-runtime summary plus overlap gates in the smoke artifact summary.
- Browser smoke on `2026-06-29` first verified a `codex` provider frontend flow from New Study intake through plan confirmation, study creation, job submission, job deep-link hydration, provider runtime visibility, and critical layout gates; the terminal job state was `failed` with provider runtime `runtime_failure`, `live_synthetic`, and `auth_readiness=ready`, proving failure transparency instead of silently falling back to mock.
- `src/ai_validation_swarm/saas/runtime.py` now indexes completed SaaS worker run contracts into the workspace metadata root and no longer marks a validation job `completed` when the underlying research run status is `failed`; failed research runs retain output artifacts, run id, provider boundary, and support-visible `last_error`.
- `tests/unit/test_saas_runtime.py` now verifies worker-completed run artifacts are queryable from workspace evidence review and that failed research runs become failed workspace jobs instead of false completed jobs.
- `src/ai_validation_swarm/providers/openai_client.py` now passes Codex CLI prompts over stdin with `codex exec ... -` and injects the requested output JSON schema into the prompt, avoiding Windows command-line length failures while keeping the transport wrapper schema separate.
- `tests/unit/test_openai_persona_tools.py` now verifies long Codex prompts stay out of argv and that the requested output schema is delivered through stdin.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now gives non-mock providers a longer default terminal-status wait window and supports `STAGE15_JOB_STATUS_TIMEOUT_MS` for live-provider acceptance tuning.
- Browser smoke on `2026-06-29` at `output/playwright/stage15_hosted_shell_smoke/2026-06-29T10-54-15-576Z/stage15_hosted_shell_smoke.summary.json` verified a frontend-started `codex` provider flow with `terminalJobStatus=completed`, provider runtime `completed`, `evidence_mode=live_synthetic`, `auth_readiness=ready`, evidence review `query_status=query_ready`, no page errors, and no critical panel overlaps.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now supports `STAGE15_PERSONAL_MVP_WORKFLOW` presets for `founder_concept_validation`, `ui_prototype_comprehension_validation`, and `pain_empathy_insight_discovery`, including prototype artifact selection, evidence-view creation, decision-log creation, export/share/support continuation, and provider-boundary assertions.
- `demo/workspace_ui_shared/workspace_ui_adapter.mjs` now infers `pain_point_discovery` from plain-language pain/root-cause/workflow/discovery intent, while keeping the default path natural-language-first instead of exposing internal discovery mode taxonomy.
- `src/ai_validation_swarm/saas/runtime.py` no longer treats `911` embedded inside timestamps or IDs as a public-safety marker, avoiding false regulated/high-stakes blocking for ordinary discovery studies.
- `tests/workspace_ui/test_workspace_shell_app.mjs` verifies discovery intent inference into `pain_point_discovery`, and `tests/unit/test_saas_runtime.py` verifies the `911` timestamp false-positive regression.
- Browser smoke on `2026-06-29` at `output/playwright/stage15_hosted_shell_smoke/2026-06-29T11-22-36-610Z/stage15_hosted_shell_smoke.summary.json` verified the live Codex founder concept-validation workflow from frontend intake through completed job, evidence query, saved evidence view, decision log, share/support continuation, and `live_synthetic` provider-boundary preservation.
- Browser smoke on `2026-06-29` at `output/playwright/stage15_hosted_shell_smoke/2026-06-29T11-25-55-787Z/stage15_hosted_shell_smoke.summary.json` verified the live Codex UI/prototype comprehension workflow with prototype artifact attachment, completed job, evidence query, saved evidence view, decision log, share/support continuation, and `live_synthetic` provider-boundary preservation.
- Browser smoke on `2026-06-29` at `output/playwright/stage15_hosted_shell_smoke/2026-06-29T11-44-02-658Z/stage15_hosted_shell_smoke.summary.json` verified the live Codex pain/empathy/insight discovery workflow with `primary_mode=pain_point_discovery`, completed job, evidence query, saved evidence view, decision log, share/support continuation, and `live_synthetic` provider-boundary preservation.

Personal MVP support assessment:

- `founder_concept_validation`: implemented for the personal MVP through frontend-started live Codex concept validation, evidence query, saved evidence view, decision log, and share-boundary preservation.
- `ui_prototype_comprehension_validation`: implemented for the personal MVP through frontend artifact selection, live Codex prototype-validation submission, evidence query, saved evidence view, decision log, and share-boundary preservation.
- `pain_empathy_insight_discovery`: implemented for the personal MVP through natural-language discovery intent inference into `pain_point_discovery`, live Codex completion, evidence query, saved evidence view, decision log, and share-boundary preservation.

Implementation order for the remaining M27 work:

1. completed: expose backend-owned Codex readiness, provider availability, missing-auth, unsupported-provider, timeout, retry, refusal, and fallback states through workspace snapshots and support diagnostics
2. completed: preserve provider lineage and mock-vs-live evidence boundaries across evidence query, audit lineage, support, decision, export, share, and public-share surfaces
3. completed: provider-runtime readiness and failure state now projects into the frontend shell, and Codex provider-state browser smoke verifies the frontend can submit a Codex-capable study and surface transport failure
4. completed: Codex CLI prompt transport is Windows-safe, and browser smoke verifies a live Codex run can complete and hydrate backend evidence-query results from the frontend path
5. completed: browser-verified the three personal MVP user stories from the normal frontend path: startup idea concept validation, UI/prototype comprehension validation, and pain/empathy/insight discovery

Exit criteria:

- the frontend study-first flow can submit a validation job with `provider_name=codex` or `provider_name=codex-sdk` through the same authenticated workspace API used by ordinary jobs
- unsupported provider, missing Codex auth, timeout, refusal, retryable transport failure, and explicit fallback-to-mock states are visible as product states rather than silent backend errors
- evidence query and audit lineage clearly distinguish mock demo evidence from live Codex-backed synthetic evidence
- a solo user can complete a concept-validation study for a startup idea and review understanding, objections, trust gaps, appeal, and adoption barriers
- a solo user can complete a prototype-validation study with UI/prototype artifacts and review likely comprehension gaps, wording confusion, button/CTA ambiguity, task friction, and observed/action-grounded evidence where available
- a solo user can complete a discovery study for pain, empathy, root cause, workflow fragmentation, and insight generation before solution planning
- contract and browser smoke coverage prove the frontend-to-runtime path without weakening the existing study, evidence, readiness, and governance boundaries

### Milestone 28: Frontline Research Studio Terminology, IA, and Data Model Foundation

Status: `implemented`

Progress:

- `4 / 4` stories complete
- `13 / 13` story points complete
- `0` story points remaining

Scope:

- formalize the Frontline Research Studio vocabulary around `Project`, `Study`, `PlanningConversation`, `PlanProposal`, immutable `StudyPlanRevision`, `Run`, `EvidenceSlice`, `Finding`, `StudyReport`, and `DecisionLog`
- separate real user-facing product language from operator-shell internals such as provider, job ID, mode override, API payloads, and filesystem artifacts
- define the data and status boundary that lets LLM-guided planning create a confirmed plan without turning chat history into the audit record

Exit criteria:

- `specs/frontline_research_studio_terminology_and_data_model.md` is the canonical reference for frontline terminology and entity boundaries
- the roadmap and status registry treat the existing Stage 15 shell as an operator/engineering console, not the final frontline user experience
- Study status, plan revision, mode inference, moderator guide, run artifact, finding, audit report, and study-level report boundaries are explicit enough to guide frontend and backend implementation

Implemented evidence:

- `specs/frontline_research_studio_terminology_and_data_model.md` now defines the canonical Frontline Research Studio terminology and data boundaries
- `DEVELOPMENT_ROADMAP.md` and `PLATFORM_STATUS.yaml` now split the Frontline Research Studio work into M28 foundation, M29 single-study MVP, and M30 study-level report/multi-run decision workflow
- `specs/frontline_research_studio_terminology_and_data_model.md` now records the separate package decision: `frontend/frontline_research_studio` for the user-facing Frontline Studio and `frontend/workspace_shell_app` for the operator/engineering shell
- the same spec now defines the study status transition model, immutable plan revision creation rules, and LLM-guided intake contract needed before M29 implementation

### Milestone 29: Frontline Research Studio Single-Study MVP

Status: `implemented`

Scope:

- implement the first real frontline UX layer for one study at a time, separate from the operator shell
- let users create/select a project, start a study through LLM-guided conversational intake, receive a plan proposal, and explicitly confirm a `StudyPlanRevision`
- hide provider, job, filesystem, and internal mode controls by default while preserving audit access through secondary/operator surfaces
- run one live Codex-backed synthetic research run from the confirmed plan and return the user to study-scoped evidence review

Exit criteria:

- a real user can start a founder concept-validation, prototype-comprehension, or pain-discovery study without filling an operator form or choosing an internal mode taxonomy
- LLM-guided setup can propose target segment, artifacts needed, study purpose, inferred mode, and moderator guide, then require explicit confirmation before execution
- every frontend-started run references an immutable plan revision and preserves synthetic-evidence boundaries in evidence review
- browser acceptance verifies the frontline path, not only the Stage 15 engineering shell

Implemented evidence:

- `frontend/frontline_research_studio` now exists as a separate Frontline Research Studio package with source files and a hosted dist entrypoint.
- The local SaaS wrapper now serves `/studio` and `/studio/studies/{study_id}` with browser-session token bootstrap and `window.__FRONTLINE_ROUTE_CONTEXT__`.
- `POST /api/v1/studies/{study_id}/frontline-plan-proposals` creates mutable `PlanProposal` records in study metadata with inferred mode, target persona, moderator guide, expected evidence types, and boundary language.
- `POST /api/v1/studies/{study_id}/frontline-plan-revisions` confirms a proposal into an immutable `StudyPlanRevision` and stores `current_plan_revision_id` on the study.
- Frontline-started validation jobs can require a confirmed plan revision and carry `plan_revision_id` / `frontline_plan_revision_id` into validation-job metadata.
- `scripts/verify_frontline_studio_smoke.mjs` verifies the real browser `/studio` path can bootstrap a session, create a study, propose a plan, confirm a plan revision, and pass a 1280px horizontal-overflow gate; latest evidence: `output/playwright/frontline_studio_smoke/2026-06-30T07-58-52-260Z/frontline_studio_smoke.summary.json`.

### Milestone 30: Study-Level Report, Multi-Run Synthesis, and Decision Workflow

Status: `implemented`

Scope:

- aggregate multiple runs into a study-level report without flattening plan revisions, evidence slices, contradictions, or human-validation gaps
- make cross-run patterns, divergent signals, trust gaps, adoption barriers, prototype confusions, and pain signals reviewable inside the same study
- promote decision logs and saved evidence views as the durable outputs of a study, not optional collaboration features

Exit criteria:

- study-level reports can cite included run IDs and plan revision IDs, and can explain plan drift when compared runs differ
- users can save evidence views and decision logs from the frontline study workflow with explicit simulated-evidence and human-validation-gap boundaries
- the frontend can show study status moving from planning to running to reviewing to completed based on real study/report/decision state

Implemented evidence:

- `WorkspaceStudyReport` is now a runtime model backed by a durable `workspace_study_reports` SQLite table and materialized `study_report.json` / `README.md` artifacts.
- `POST /api/v1/study-reports`, `GET /api/v1/study-reports`, and `GET /api/v1/study-reports/{study_report_id}` expose study-level reports through the same authenticated SaaS runtime.
- Study reports preserve `included_job_ids`, `included_run_ids`, `included_plan_revision_ids`, stable patterns, divergent signals, key objections, trust gaps, adoption barriers, prototype confusions, contradictions, and human-validation gaps.
- Study status now advances through confirmed-plan execution: queued frontline runs set the study to `running`, completed runs set it to `reviewing`, and study report creation moves it to `completed`.
- `tests/unit/test_saas_runtime.py::SaasRuntimeTest::test_frontline_studio_plan_revision_and_study_report_workflow` verifies `/studio` hosting, plan proposal, plan revision confirmation, two plan-linked completed runs, study-level report creation, report listing, completed study status, and decision-log lineage to the report and plan revision.

### Milestone 31: Frontline Studio Route Architecture and Navigation Shell

Status: `implemented`

Scope:

- turn `/studio` from one long canvas into a persistent shell with route-aware product pages
- implement the route map from `specs/frontline_research_studio_ux_component_design_spec.md` for workspace, projects, studies, setup, runs, evidence, reports, decisions, and share contexts
- keep the left navigation tied to product IA, with a drill-down rail that shows only Projects, Project, or Study navigation at one time instead of permanently exposing every contextual layer
- preserve browser refresh, back/forward, and deep-link context without exposing provider, job, runtime, payload, milestone, or roadmap language

Exit criteria:

- `/studio`, `/studio/projects`, `/studio/projects/{project_id}`, `/studio/studies/new`, `/studio/studies/{study_id}`, `/studio/studies/{study_id}/setup`, `/studio/studies/{study_id}/runs`, `/studio/studies/{study_id}/evidence`, `/studio/studies/{study_id}/reports/{study_report_id}`, `/studio/studies/{study_id}/decisions/{decision_log_id}`, and `/studio/share/{share_bundle_id}` resolve through backend-injected route context
- each route has one primary product object, one clear empty/loading state, and one dominant CTA aligned with the UX spec
- browser smoke verifies route navigation, refresh persistence, no critical overlap, no horizontal overflow, and no visible internal roadmap/operator/runtime language

Implemented evidence:

- `src/ai_validation_swarm/saas/api.py` now injects explicit Frontline route context for `/studio`, `/studio/projects`, `/studio/projects/{project_id}`, `/studio/studies/new`, `/studio/studies/{study_id}`, `/studio/studies/{study_id}/setup`, `/studio/studies/{study_id}/runs`, `/studio/studies/{study_id}/runs/{run_id}`, `/studio/studies/{study_id}/evidence`, `/studio/studies/{study_id}/evidence-views/{evidence_view_id}`, `/studio/studies/{study_id}/reports/{study_report_id}`, `/studio/studies/{study_id}/decisions/{decision_log_id}`, `/studio/share`, and `/studio/share/{share_bundle_id}`.
- `frontend/frontline_research_studio/src/main.jsx` now renders route-specific pages inside one persistent shell instead of one long canvas, while the fixed left rail switches between Projects, Project, and Study levels rather than showing project and study context permanently together.
- `scripts/verify_frontline_studio_smoke.mjs` now verifies route navigation, deep-link refresh, browser back/forward, drill-down nav-level exclusivity, 1024px and 1280px horizontal overflow, DOM critical-overlap checks, loaded-page screenshots, plan approval, and absence of visible milestone/roadmap/operator/provider/job-id/runtime/payload/debug/stage language.
- `tests/unit/test_saas_runtime.py::SaasRuntimeTest::test_frontline_studio_plan_revision_and_study_report_workflow` now asserts backend-injected Frontline route context for the implemented route map and 404 behavior for invalid `/studio` routes.

### Milestone 32: Frontline Guided Setup, Plan Approval, and Live Run Flow

Status: `implemented`

Scope:

- implement the `/studio/studies/new` and `/studio/studies/{study_id}/setup` guided setup screens as the user-facing Research Copilot flow
- move the current create-study, plan-proposal, and plan-approval actions into route-level components with external-user copy and CTA placement from the UX spec
- let users start a plan-linked live run from the approved study plan without seeing provider, job, mode override, or raw runtime details
- preserve study status and approved-plan state as human-readable product states

Exit criteria:

- a user can start from `/studio/studies/new`, describe a research question, create a study, review a plan, approve it, and start a live synthetic research run from the Frontline Studio surface
- plan approval remains explicit and creates an immutable `StudyPlanRevision`
- the frontend hides internal mode/provider/job controls by default while still preserving audit lineage in backend metadata
- browser acceptance verifies the guided setup and live-run path from `/studio`, not only from the operator shell

Current proof-of-progress:

- `frontend/frontline_research_studio/src/main.jsx` now owns the New Study guided composer, Study Setup plan review, explicit plan approval CTA, and Start research run CTA as route-level Frontline components.
- `src/ai_validation_swarm/saas/api.py` now exposes `POST /api/v1/studies/{study_id}/frontline-runs`, and `src/ai_validation_swarm/saas/runtime.py` starts a plan-linked Frontline run while preserving hidden audit metadata for project, study, and approved plan lineage.
- `tests/unit/test_saas_runtime.py` verifies that a Frontline-started run requires the confirmed plan revision, returns a running study plus research-run summary, and preserves the hidden execution profile metadata.
- `scripts/verify_frontline_studio_smoke.mjs` now verifies the browser path from `/studio/studies/new` through user-entered research intent, guided setup, plan proposal, plan approval, Start research run, Research attempts, evidence navigation, refresh, back/forward, no-overflow, no-overlap, and no visible internal-term gates; latest evidence: `output/playwright/frontline_studio_smoke/2026-06-30T07-58-52-260Z/frontline_studio_smoke.summary.json`.

### Milestone 33: Frontline Evidence, Run, Report, and Comparison Workspace

Status: `implemented`

Scope:

- implement `/studio/studies/{study_id}/runs`, `/studio/studies/{study_id}/runs/{run_id}`, `/studio/studies/{study_id}/evidence`, `/studio/studies/{study_id}/evidence-views/{evidence_view_id}`, and `/studio/studies/{study_id}/reports/{study_report_id}`
- make run status, transcript/evidence slices, audit notes, evidence filters, comparison, saved views, and study reports visible through user-facing components
- default to evidence before summary and keep contradictions, divergent signals, and human-validation gaps visible
- carry plan basis and evidence boundary through every review route

Exit criteria:

- users can open a completed run, inspect source evidence, save an evidence view, compare evidence, and create/open a study report without dropping into `/app/workspace`
- evidence pages distinguish source evidence, interpretation, summary, contradiction, and human-validation gaps
- saved evidence views and reports are deep-linkable and retain provenance after refresh
- browser acceptance verifies evidence review and report creation against the Frontline Studio route map

Implemented repository evidence:

- `frontend/frontline_research_studio/src/main.jsx` hydrates `/studio` review routes with backend-owned `/api/v1/evidence-query` payloads and renders source evidence, interpretation, summary boundary, contradictions, human-validation gaps, comparison, saved view provenance, and report cited-evidence sections without returning to `/app/workspace`.
- `tests/unit/test_saas_runtime.py` verifies completed Frontline runs can be queried through `/api/v1/evidence-query`, saved as provenance-preserving evidence views, and aggregated into study reports with plan/run lineage.
- `scripts/verify_frontline_studio_smoke.mjs` now processes a Frontline run to completion in the isolated smoke runtime, opens run detail, reviews evidence, saves an evidence view, reloads the saved view, creates a study report, reloads the report, verifies browser back/forward, and keeps no-overflow/no-overlap/no-internal-term gates active; latest evidence: `output/playwright/frontline_studio_smoke/2026-06-30T07-58-52-260Z/frontline_studio_smoke.summary.json`.

### Milestone 34: Frontline Decision, Share, and UX Audit Hardening

Status: `implemented`

Scope:

- implement `/studio/studies/{study_id}/decisions/{decision_log_id}` and `/studio/share/{share_bundle_id}` as user-facing decision and share routes
- make decision logging preserve current belief, evidence basis, uncertainty, and required human follow-up
- make shared views preserve synthetic-evidence boundaries and avoid internal runtime/milestone/provider/job language
- add automated UX-audit gates for external-user copy, CTA hierarchy, route deep links, visual overlap, and evidence-boundary visibility

Exit criteria:

- users can create/open a decision from a report or saved evidence view, attach evidence, record human-validation gaps, and share a boundary-preserving view
- share routes clearly state what is simulated evidence and what still needs human validation
- browser smoke fails if default Studio pages show milestone, roadmap, provider, job, runtime, payload, debug, or operator wording
- the Frontline Studio route-level UX matches the acceptance checklist in `specs/frontline_research_studio_ux_component_design_spec.md`

Implemented repository evidence:

- `frontend/frontline_research_studio/src/main.jsx` renders the decision route with explicit current belief, evidence basis, confidence boundary, and human follow-up sections plus a create-share CTA.
- `frontend/frontline_research_studio/src/main.jsx` renders the share route with linked decision context, evidence digest, included viewer-safe artifacts, public boundary link, and synthetic-evidence boundary language.
- `src/ai_validation_swarm/saas/runtime.py` projects viewer-safe share artifact files through the authenticated share summary so the Frontline share route can show included artifacts without exposing raw workspace internals.
- `tests/unit/test_saas_runtime.py::SaasRuntimeTest.test_frontline_studio_plan_revision_and_study_report_workflow` verifies decision logs preserve evidence view, selected source, confidence boundary, human follow-up, export lineage, share metadata, included files, and `/studio/share/{share_bundle_id}` route context.
- `scripts/verify_frontline_studio_smoke.mjs` now verifies the browser path from completed run to evidence view, report, decision logging, share creation, refresh, no internal terminology, no horizontal overflow, and no critical overlap; latest passing artifact: `output/playwright/frontline_studio_smoke/2026-06-30T07-58-52-260Z/frontline_studio_smoke.summary.json`.

### Milestone 35: Persona Library Readiness and Panel Contract Hardening

Status: `implemented`

Scope:

- harden the Frontline persona library from a selectable picker into an explicit research contract
- expose persona-library readiness states, coverage gaps, generation failures, and provisional personas without ambiguous preparing states
- create explicit dynamic gap-fill generation jobs instead of hidden read-time persona generation
- preserve selected persona IDs, persona versions, coverage snapshots, readiness status, and artifact hashes through approved plans and runs
- separate normal participant personas from public-figure, celebrity, expert, or influencer-inspired simulated lenses

Exit criteria:

- persona library responses expose `ready`, `empty`, `generating`, `failed`, `stale`, and `provisional` states without silently mutating library data from read endpoints
- Frontline plan approval blocks or clearly records exceptions when no personas are selected
- coverage gaps can trigger explicit persona generation jobs, and generated personas remain `provisional` until validation, duplicate, and coverage checks promote them to `ready`
- run artifacts prove which persona IDs and versions were used, including coverage snapshot and provisional-persona status
- public-figure-inspired lenses are labeled as simulated, unaffiliated critique/advisor lenses and are not mixed into normal participant evidence by default
- browser and unit acceptance cover picker readiness, zero-selection handling, generation-state handling, and selected-persona run snapshots

Canonical spec:

- `specs/milestone_35_persona_library_readiness_and_panel_contract_design_spec.md`
- `specs/persona_library_storage_and_saas_contract.md`

Current checkpoint:

- Implemented and verified through runtime/API contract coverage, Frontline picker behavior, run snapshot artifact, browser smoke, and UX/IA acceptance.
- Latest browser evidence: `output/playwright/frontline_studio_smoke/2026-06-30T16-47-06-247Z`.
- Unit evidence: `python -m unittest tests.unit.test_saas_runtime` passes and covers the M35 plan/run/persona snapshot contract.

### Milestone 36: Frontline Personal MVP End-to-End Reliability Gate

Status: `implemented`

Scope:

- harden the true user-facing `/studio` path from project selection through study setup, approved plan, research run, evidence review, report, decision, and share
- make durable routes refresh-safe and back/forward-safe for study, run, saved evidence view, report, decision, and share contexts
- eliminate silent blank states by tightening route-detail hydration, loading contracts, empty states, and backend fallback loading
- keep the acceptance focus on research continuity, provenance, and evidence boundaries rather than visual polish

Exit criteria:

- a user can complete the personal MVP loop without CLI operation, raw artifact inspection, provider/job/runtime terminology, or page-local reconstruction
- route refresh and browser back/forward preserve the selected product object and synthetic-evidence boundary for runs, saved views, reports, decisions, and shares
- browser smoke covers the full Frontline loop at desktop widths that previously exposed overlap or dense-grid problems, with no critical overlap, no horizontal overflow, and no internal-terminology leakage
- failed, missing, or delayed route-detail hydration produces an actionable product state rather than a silent blank page
- run, evidence view, report, decision, and share artifacts preserve plan revision, selected persona, provider boundary, evidence provenance, and human-validation-gap lineage

Canonical contract:

- `specs/frontline_research_studio_i18n_contract.md`
- `specs/frontline_research_studio_bilingual_terminology_glossary.md`

Implemented reliability slices:

- Frontline Studio product chrome now supports deterministic English default plus explicit Traditional Chinese (`zh-Hant`) through `?lang=zh-Hant` and a fixed left-rail language switcher.
- The bilingual layer covers route/navigation IA, workspace/project/study setup, Research Copilot, Persona Library picker, plan confirmation/tuning, run/evidence/report/decision/share route chrome, action feedback, loading/empty states, and synthetic-evidence boundary copy while preserving generated evidence, transcripts, findings, and backend artifacts in their original language.
- The `zh-Hant` product chrome now follows a formal terminology glossary so durable user-facing terms use `專案`, `研究`, `研究計劃`, `研究執行`, `證據`, `決策`, and `合成受訪者` instead of mixed Chinese/English labels.
- The left rail now constrains contextual navigation and the fixed account/language footer into separate height regions so long Study navigation does not overlap the footer at desktop widths.
- Starting a Frontline research run now uses the API response to immediately hydrate the queued run into the Study Runs model before route refresh catches up, reducing silent empty-list states after plan approval.
- Direct study-route hydration now fetches the selected study when a durable detail route is opened or refreshed, and durable route fallbacks keep linked study context visible while detail data loads.
- The full browser smoke now verifies project creation, study creation, guided setup, persona selection, plan approval, research run start/completion, evidence review, saved evidence view, study report, decision log, share view, refresh, back/forward, desktop layout, and `zh-Hant` terminology gates.

Current checkpoint:

- Implemented and verified through Frontline smoke, runtime unit tests, frontend build, i18n key coverage, UTF-8 content checks, and UX/IA review.
- Latest browser evidence: `output/playwright/frontline_studio_smoke/2026-07-01T17-21-45-013Z/frontline_studio_smoke.summary.json`.
- Unit evidence: `python -m unittest tests.unit.test_saas_runtime` passes.
- Frontend evidence: `npm -C frontend/frontline_research_studio run build` passes.

### Milestone 37: Live Interview Observability and Transcript Evidence

Status: `implemented`

Scope:

- make LLM-backed synthetic interview execution visible from the Frontline run monitor while the run is actually happening
- expose run progress phases such as queued, planning, sampling panel, interviewing, synthesizing, auditing, completed, blocked, and failed
- bridge existing transcript, facilitator trace, synthetic participant driver trace, observed interview artifacts, and observed action traces into route-safe Frontline review pages
- let evidence slices, reports, and decisions link back to transcript exchanges or trace entries rather than only showing processed summaries
- preserve the boundary that transcript and reasoning traces are simulated evidence artifacts, not human market proof or real-person mind reading

Exit criteria:

- a running Frontline study shows live or near-live interview phase progress without relying on raw CLI output
- completed runs expose transcript, facilitator trace, synthetic participant reasoning trace, audit boundary, provider lineage, and observed-action evidence where available
- evidence slices, study reports, and decision logs can cite source exchanges or trace entries
- transcript evidence, facilitator trace, synthetic participant reasoning trace, observed action trace, summary, and human-validation gaps remain visually and semantically distinct
- browser and API acceptance cover running, completed, blocked, and failed run observability plus transcript-backed evidence review

Canonical spec:

- `specs/milestone_37_live_interview_observability_and_transcript_evidence_design_spec.md`

Implemented evidence:

- `GET /api/v1/studies/{study_id}/runs/{run_id}/progress`, `/transcript`, and `/trace` expose route-safe run observability contracts.
- Frontline run detail now shows a run monitor, transcript panel, and trace provenance panel instead of only processed summaries.
- Evidence-query output, saved evidence views, study reports, and decision logs preserve `source_exchange_refs` and `source_trace_refs`.
- Browser smoke verifies the run monitor, transcript, trace, source-exchange visibility, and no critical layout overlap.

### Milestone 38: Messaging and Positioning Validation

Status: `implemented`

Scope:

- implement `messaging_validation` as the remaining Phase 2 concept-evaluation expansion mode
- test positioning, value proposition clarity, trust language, and likely misinterpretation before acquisition spend
- keep message evidence separate from product adoption evidence
- expose messaging studies through the Frontline setup only after transcript-backed evidence review and live interview observability are stable

Exit criteria:

- messaging studies can identify comprehension gaps, credibility objections, and wording-driven false positives
- message outputs are queryable and attachable to decisions without overwriting concept or prototype evidence
- public positioning can be validated through the Frontline Studio without claiming market proof from synthetic evidence alone

Canonical spec:

- `specs/milestone_38_messaging_and_positioning_validation_design_spec.md`

Implemented evidence:

- natural-language plan proposal inference now recognizes message, messaging, positioning, value proposition, copy, headline, tagline, and landing-page intent as `messaging_validation`
- expected evidence types keep comprehension, credibility, trust language, misunderstanding, and adoption-boundary signals separate
- the Frontline playbook picker includes messaging validation without requiring users to understand internal mode taxonomy first

### Milestone 39: Guided Research Playbooks and Rerun Templates

Status: `implemented`

Scope:

- add reusable guided study playbooks for discovery, concept evaluation, prototype validation, messaging, and adoption-barrier work
- support rerunning a study with revised target audience, artifact version, message variant, prototype version, or moderator guide
- keep playbooks as conversational starting points and confirmation-sheet defaults, not rigid workflow-builder configuration
- include evidence-boundary defaults, benchmark requirements, comparison setup, and recommended human-validation follow-ups

Exit criteria:

- new users can start common research workflows without learning internal mode taxonomy
- reruns preserve plan-revision lineage and make the changed assumption explicit
- playbooks preserve final plan confirmation, evidence readiness gates, and synthetic-evidence boundaries
- study setup becomes faster without weakening research discipline or comparison quality

Canonical spec:

- `specs/milestone_39_guided_research_playbooks_and_rerun_templates_design_spec.md`

Implemented evidence:

- `GET /api/v1/research-playbooks` returns the backend-owned guided playbook catalog
- `POST /api/v1/studies/{study_id}/frontline-reruns` creates rerun plan proposals with source run, source plan revision, selected playbook, changed assumption, and boundary text
- Frontline new-study/setup pages render guided playbook quick starts and run detail can prepare a rerun without bypassing explicit plan confirmation

### Milestone 40: Continuous Calibration Observatory

Status: `implemented`

Scope:

- create an operator-facing calibration observability layer across benchmarks, studies, models, modes, and evidence types
- track drift, repeated misses, unsupported synthetic signals, and benchmark coverage over time
- keep calibration diagnostics backend-owned and audit-linked
- connect calibration health to launch, export, share, and replacement-readiness gates

Exit criteria:

- platform owners can see which modes and evidence types are improving or degrading
- repeated calibration failures can be traced to persona coverage, facilitator behavior, stimulus handling, or synthesis/ranking
- launch readiness can be monitored continuously rather than re-evaluated manually each release
- customer-facing surfaces can show bounded readiness without exposing raw benchmark internals

Canonical spec:

- `specs/milestone_40_continuous_calibration_observatory_design_spec.md`

Implemented evidence:

- `GET /api/v1/calibration-observatory` exposes `calibration-observatory/v1`
- workspace public-launch readiness embeds calibration-observatory state and can block launch claims with `continuous_calibration_health_not_ready`
- Frontline workspace overview renders a calibration observatory card for provider/mode/evidence coverage and unsupported evidence signals

### Milestone 41: Privacy, Data Residency, and Export Controls

Status: `implemented`

Scope:

- strengthen data retention, export deletion, redaction, workspace isolation, and regional storage policy controls
- make customer data boundaries explicit for uploaded artifacts, study evidence, calibration records, exports, and shares
- support privacy review without weakening evidence lineage

Exit criteria:

- customers can understand and control what is retained, exported, redacted, or deleted
- audit records preserve why evidence was removed or redacted
- privacy controls are strong enough for broader team and enterprise pilots

Canonical spec:

- `specs/milestone_41_privacy_data_residency_and_export_controls_design_spec.md`

Implemented evidence:

- `GET /api/v1/privacy-export-controls` returns `workspace-privacy-export-controls/v1` with workspace isolation, data-residency, retention, deletion, redaction, export/share, downstream lineage, audit, and readiness fields.
- `POST /api/v1/privacy-export-controls/policy` records data-residency, retention, deletion policy, export review, share expiry, policy history, and audit events.
- `POST /api/v1/privacy-export-controls/deletion-requests` records deletion requests with reason, requester, scope, affected jobs/runs/exports/shares, and lineage-retained status.
- Frontline workspace and share review routes render `#privacy-export-controls-card` and `#share-privacy-boundary`.

### Milestone 42: Integration Surface, Run Event Stream, and Webhooks

Status: `implemented`

Scope:

- add bounded integrations for study creation, job completion, decision export, evidence readiness updates, and support handoff
- promote run progress from polling-only UI into a bounded run-event stream contract for LLM provider execution, persona interviewing, synthesizing, auditing, blocked, failed, and completed states
- bridge observed-interview mode events into the same route-safe run monitor without making users inspect CLI output
- expose webhooks or integration events only from stable backend contracts
- avoid integration paths that bypass evidence readiness, audit lineage, or synthetic-evidence boundaries

Exit criteria:

- teams can connect research outcomes to existing product, analytics, or documentation systems
- Frontline can reflect provider/persona-interview state through a backend event contract while preserving M37 transcript/trace provenance and M41 privacy/export controls
- integration consumers receive boundary-preserving evidence and decision payloads
- integrations do not become an alternative uncalibrated reporting channel

Implementation summary:

- `GET /api/v1/studies/{study_id}/runs/{run_id}/events` returns `workspace-run-event-stream/v1` with run phase, progress, participant completion, safe latest-turn preview, observed-interview bridge metadata, transcript/trace provenance, privacy/export controls, and future-compatible transport guidance.
- `GET /api/v1/integration-events` returns `workspace-integration-events/v1` for study created, run completed/failed, evidence view saved, decision logged, readiness changed, and support handoff changed events.
- `workspace-integration-event-payload/v1` preserves readiness gates, source exchange refs, source trace refs, human-validation gaps, privacy/export controls, and synthetic-evidence boundaries.
- `POST /api/v1/integration-events/delivery-attempts` records queued/delivered/failed/retrying/skipped delivery state with payload boundary hashes and audit events.
- Frontline workspace and run routes render `#integration-events-card` and `#run-event-stream-panel` so users can inspect interview state, transcript preview, trace-linked events, and connected evidence status without reading CLI output or raw artifact folders.
- Design contract: `specs/milestone_42_integration_surface_run_event_stream_and_webhooks_design_spec.md`.

### Milestone 43: Persona Profile Review and Study-Time Persona Creation

Status: `planned`

Scope:

- expose a route-safe or study-local full synthetic participant profile review surface before plan approval
- let users generate additional synthetic participants during study planning from the current target audience, panel type, sample size, and coverage gaps
- keep generated personas explicit as generated/provisional/ready with generation job lineage, artifact hashes, readiness checks, and simulated-evidence boundaries
- allow users to inspect identity, context, decision behavior, trust/rejection triggers, proof requirements, human-difference axes, source/version, and readiness before selecting a participant
- preserve selected full-profile version, artifact hashes, coverage rationale, and generation job lineage in the approved plan and run snapshot
- keep public-figure, celebrity, expert, influencer, and founder-critique lenses separate from participant evidence

Exit criteria:

- users can review a complete synthetic participant profile from the setup flow without leaving the study context
- users can create study-time gap-fill personas before plan approval, then select or reject them with visible readiness and boundary state
- persona profile review improves panel trust without asking users to edit raw JSON, inspect local files, or learn internal schemas
- approved plans and runs preserve selected-persona profile/version/hash lineage for audit and rerun comparison
- generated personas are never silently created from `GET /api/v1/persona-library`, and generated/provisional state is visible before use

Architecture and UX notes:

- expose a bounded persona profile contract such as `frontline-persona-profile/v1` rather than serving raw artifact files directly
- keep full artifacts artifact-first and SQL-indexed according to `specs/persona_library_storage_and_saas_contract.md`
- implement the default UI as a setup-context profile drawer or study-local review page; do not make Personas a global Level 1 product area unless a future cross-project persona library workspace is deliberately designed
- keep the CTA language user-facing: `Review profile`, `Generate more participants`, `Add to this study`, and `Not human evidence`

### Milestone 44: Enterprise Readiness and Procurement Controls

Status: `planned`

Scope:

- add procurement-oriented controls such as workspace ownership, invoice metadata, audit exports, SSO-ready boundaries, and support SLAs
- document evidence, privacy, calibration, and safety boundaries for buyer review
- keep enterprise work secondary to calibrated research quality

Exit criteria:

- enterprise buyers can evaluate security, privacy, billing, and governance posture without custom manual explanation
- procurement artifacts accurately describe synthetic evidence limitations
- enterprise readiness does not expand claims beyond benchmark-backed capability

### Milestone 45: Multi-Market Benchmark Expansion

Status: `planned`

Scope:

- expand benchmark coverage across markets, domains, user segments, languages, and product categories
- compare synthetic performance across market context rather than averaging into one global readiness score
- identify where personas, prompts, or evidence models underperform by market

Exit criteria:

- benchmark reports can segment reliability by market, domain, research stage, and evidence type
- readiness gates can prevent unsupported market expansion
- localization and cultural context are treated as calibration variables, not copywriting tasks

### Milestone 46: Replacement-Readiness Review Board

Status: `planned`

Scope:

- create formal review workflows for deciding whether a bounded use case can be described as replacement-ready
- require benchmark evidence, calibration history, safety review, failure-mode analysis, and human-validation gap closure
- separate `research support`, `human-reducing`, and `replacement-ready` statuses

Exit criteria:

- replacement-readiness can be reviewed and approved only for scoped use cases
- rejected or deferred readiness decisions remain auditable
- marketing, product UI, and exports cannot use replacement-grade language without approved readiness evidence

### Milestone 47: Model and Provider Governance

Status: `planned`

Scope:

- evaluate model/provider performance across calibration suites, cost, latency, refusal behavior, and evidence quality
- route workloads by research mode, sensitivity, language, and benchmark-backed quality
- preserve prompt, model, provider, seed, and output lineage for calibration and audit

Exit criteria:

- provider changes can be evaluated against benchmark deltas before production use
- cost optimization does not silently reduce evidence quality
- every customer-facing result remains traceable to model and prompt lineage

### Milestone 48: Platform Scale and Reliability Expansion

Status: `planned`

Scope:

- scale workers, queues, evidence indexing, calibration jobs, browser behavior capture, and export/share delivery for larger customer volume
- add reliability SLOs, failure recovery, backpressure, and operational runbooks
- keep scale work subordinate to evidence correctness and auditability

Exit criteria:

- the platform can handle larger study volumes without losing run, evidence, calibration, or audit lineage
- operational failures are visible and recoverable without corrupting research records
- scale readiness supports public growth without weakening evidence boundaries

### MVP and Launch Gate Assessment

The controlled market MVP gate starts at **Milestone 20: Controlled Market MVP Launch**.

Milestone 16 makes the product usable, but it is not enough for market release because the strongest remaining risk is calibration, not navigation. Milestones 17-19 are the minimum evidence-quality bridge: external human benchmark calibration, complete discovery coverage, and calibrated evidence readiness gates.

For a single founder or researcher using the product personally, the practical MVP is achieved at **Milestone 27: Frontend-to-Codex Live Experiment Runtime**. The frontend product path now completes live Codex-backed research loops for concept validation, prototype comprehension validation, and discovery insight work. As of the current roadmap state, this personal MVP is **implemented for local solo-user operation**.

Personal MVP release criteria:

- `startup idea / concept validation`: the user can describe an idea in the frontend, confirm the inferred concept-validation plan, run live Codex-backed synthetic research, and review understanding, objections, trust gaps, appeal, and adoption barriers with evidence boundaries visible
- `UIUX prototype comprehension validation`: the user can attach or reference prototype material, confirm the prototype-validation plan, run the study, and review wording confusion, CTA/button ambiguity, flow friction, and action-grounded evidence where available
- `pain / empathy / insight discovery`: the user can describe a problem space before solution planning, let the product infer pain discovery, root cause, decision reconstruction, or workflow mapping as needed, then review insight evidence, contradictions, and human-validation gaps
- all three workflows must work from the frontend without requiring CLI operation, raw artifact inspection, or prior understanding of internal research mode names

Current release decision:

- `ready for local personal MVP`: the personal MVP is no longer blocked by frontend browser acceptance. It remains bounded to simulated evidence and local solo-user operation, not broad public launch or replacement-grade proof.
- `can be used as local engineering/operator demo`: the current Stage 15 shell can demonstrate the study-first loop, evidence review, and backend-owned evidence boundaries.
- `frontline personal-MVP loop implemented`: the Frontline Studio route-aware shell now supports guided setup, plan-linked run start, live run monitor, transcript/trace-backed run review, completed-run evidence review, saved evidence views, comparison, study reports, durable decision review, boundary-preserving share views, refresh/back-forward/detail hydration checks, and bilingual product-chrome terminology gates.
- `frontline design-partner beta preparation can begin after M43`: the route-complete Studio, persona readiness, E2E reliability gate, interview observability, messaging validation, playbooks/reruns, calibration observatory, privacy/export controls, integration events, and persona profile review should exist before broader real-customer onboarding.
- `broader public/self-serve launch should wait for customer-operations hardening`: M42 completes privacy-aware integration/run-event hardening, but public launch still needs M43 persona trust/profile review plus M44 enterprise procurement, ownership, billing metadata, audit packs, and support-boundary controls before broader team or enterprise expansion.

Market entry at Milestone 20 should be constrained to design partners or controlled paid pilots. M27 is the local solo-user MVP activation gate, not the broad public-launch gate. Broader bounded public/self-serve launch evaluation can now move past the M42 customer-operations integration gate, but should not proceed to broader team or enterprise onboarding before M43 persona profile review/study-time generation and M44 procurement, ownership, billing, audit-pack, and support-boundary behavior are credible.

Replacement-grade public claims should not start at either gate. They require Milestone 46 review for scoped use cases, backed by Milestone 45 multi-market benchmark history and explicit human-validation-gap closure.

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

7. `Post-Login Workspace IA and Active-Route Shell` - `implemented`
   Tracking intent: turn the accepted study-first logged-in IA into framework-owned route behavior so the product stops behaving like one long page while preserving evidence review, comparison, decision logging, and governance boundaries.
   Design anchors: `specs/post_login_workspace_information_architecture_contract.md`, `specs/milestone_16_post_login_workspace_ia_design_spec.md`

8. `External Human Benchmark Calibration` - `implemented`
   Tracking intent: move from fixture-backed calibration to externally reviewed human outcomes so readiness signals can support market-facing use cases.

9. `Discovery Coverage Completion` - `implemented`
   Tracking intent: complete the discovery-stage mode surface by adding workflow mapping and current-state fragmentation evidence.

10. `Calibration-Backed Evidence Readiness Gates` - `implemented`
    Tracking intent: make calibration confidence, contradiction, missing context, and human-validation gaps hard gates for decisions, exports, and shares.

11. `Controlled Market MVP Launch` - `implemented`
    Tracking intent: release a bounded MVP to design partners only after calibration and readiness gates protect customer-facing claims.

12. `Production API and Deployment Boundary` - `implemented`
    Tracking intent: add typed API and deployment operations only after the core runtime, worker, route, and evidence contracts are stable.

13. `Team Collaboration and Governance Hardening` - `implemented`
    Tracking intent: harden collaboration, roles, billing, quota, retention, audit, and support flows around the study-first workspace.

14. `Persona Library and Human Difference Calibration` - `implemented`
    Tracking intent: improve panel realism and coverage by calibrating persona and human-difference axes against benchmark deltas.

15. `Longitudinal Study and Panel Learning` - `implemented`
    Tracking intent: compare repeated studies and prototype iterations without turning evidence history into unstructured chat memory.

16. `Regulated and High-Stakes Review Boundary` - `implemented`
    Tracking intent: formalize safety, compliance, redaction, and reviewer handoff for contexts where synthetic evidence must stay gated.

17. `Scaled Public Launch Readiness` - `implemented`
   Tracking intent: prepare broader self-serve launch only after controlled MVP evidence, operations, benchmark disclosure, and support boundaries are credible.

18. `Frontend-to-Codex Live Experiment Runtime` - `implemented`
    Tracking intent: make the normal frontend study flow run live Codex-backed synthetic experiments with provider readiness, lineage, and mock-vs-live evidence boundaries visible.

19. `Frontline Research Studio Terminology, IA, and Data Model Foundation` - `implemented`
    Tracking intent: formalize the terminology, entity boundaries, status lifecycle, and plan-revision model needed before replacing the operator shell with a true user-facing research studio.

20. `Frontline Research Studio Single-Study MVP` - `implemented`
    Tracking intent: let ordinary users create, plan, run, and review one study without learning internal mode, provider, job, or filesystem concepts.

21. `Study-Level Report, Multi-Run Synthesis, and Decision Workflow` - `implemented`
    Tracking intent: aggregate multiple runs into study-level reports, saved evidence views, and decision logs without flattening plan revisions, contradictions, or human-validation gaps.

22. `Frontline Studio Route Architecture and Navigation Shell` - `implemented`
    Tracking intent: turn `/studio` from one long canvas into a persistent, route-aware product shell based on durable research objects.

23. `Frontline Guided Setup, Plan Approval, and Live Run Flow` - `implemented`
    Tracking intent: implement the Research Copilot setup path, approved-plan flow, and Frontline live-run start without exposing provider/job/runtime concepts.

24. `Frontline Evidence, Run, Report, and Comparison Workspace` - `implemented`
    Tracking intent: make run detail, evidence review, saved evidence views, comparison, and study reports first-class Frontline routes.

25. `Frontline Decision, Share, and UX Audit Hardening` - `implemented`
    Tracking intent: complete decision and share routes with boundary-preserving copy and automated UX-audit gates against internal terminology leaks.

26. `Persona Library Readiness and Panel Contract Hardening` - `in_progress`
    Tracking intent: make persona readiness, dynamic gap-fill generation, selected-panel snapshots, and public-figure/expert lens boundaries explicit before further user-facing validation modes depend on the panel layer.

27. `Messaging and Positioning Validation` - `planned`
    Tracking intent: validate wording, positioning, and value-proposition comprehension only after the real Frontline journey is route-complete enough to test.

28. `Guided Research Playbooks and Rerun Templates` - `planned`
    Tracking intent: accelerate common research workflows while preserving conversational intake, final confirmation, and evidence readiness gates.

29. `Continuous Calibration Observatory` - `planned`
    Tracking intent: monitor calibration health, drift, repeated misses, and benchmark coverage as an ongoing product quality system.

30. `Privacy, Data Residency, and Export Controls` - `implemented`
    Tracking intent: make retention, redaction, deletion, export, and storage controls credible for broader customer use.

31. `Integration Surface, Run Event Stream, and Webhooks` - `implemented`
    Tracking intent: connect bounded study, run, observed-interview, evidence, decision, readiness, and support events to customer systems without bypassing evidence or privacy boundaries.

32. `Persona Profile Review and Study-Time Persona Creation` - `active`
    Tracking intent: let users inspect and create synthetic participants during study planning so selected panels are understandable, auditable, and trusted before plan approval.

33. `Enterprise Readiness and Procurement Controls` - `planned`
    Tracking intent: support enterprise evaluation through governance, procurement, billing, and boundary documentation without overclaiming capability.

34. `Multi-Market Benchmark Expansion` - `planned`
    Tracking intent: expand calibration by market, language, segment, and domain instead of averaging reliability into one unsupported global score.

35. `Replacement-Readiness Review Board` - `planned`
    Tracking intent: approve replacement-grade language only for scoped use cases with benchmark evidence and human-validation-gap closure.

36. `Model and Provider Governance` - `planned`
    Tracking intent: route model/provider usage by benchmark-backed quality, cost, latency, sensitivity, and audit lineage.

37. `Platform Scale and Reliability Expansion` - `planned`
    Tracking intent: scale workers, queues, evidence indexing, calibration, browser capture, and exports without weakening research records.

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
- a local authenticated workspace shell can now start from research intent, accept prototype artifacts, confirm the inferred plan, submit an authenticated workspace validation job, inspect evidence, replay core research artifacts, and surface initial cross-run comparison guidance without dropping back to raw CLI or filesystem inspection
- the evidence query contract now surfaces cross-run reliability, calibration records, contradiction/missing-context review, and audit lineage linked back to workspace job, project, and study context
- hosted browser smoke now verifies clean job deep-link hydration plus critical product-action and critical panel overlap acceptance gates, so layout overlap is part of ongoing milestone acceptance rather than manual visual inspection only
- the human calibration workflow now attaches fixture-backed human-reviewed outcomes to comparable synthetic runs, scores alignment and divergence, writes calibration artifacts, and projects human benchmark alignment into evidence reliability records without claiming blanket replacement-readiness
- workflow mapping is now a real first-class discovery mode, so discovery coverage is no longer blocked by the old workflow-gap placeholder
- deployment probes, readiness checks, service metadata, contract-manifest exposure, and authenticated operations summary now exist as backend-owned production-boundary surface
- the first Milestone 22 governance slice now attaches explicit review assignment to decision logs, ties approval permission to assignment or owner/admin authority, and keeps support handoff ownership/history visible in study activity
- the second Milestone 22 governance slice now preserves append-only export/share approval history and projects partner-circulation review transitions into study activity
- the third Milestone 22 governance slice now preserves append-only workspace billing/quota/retention policy history and keeps those mutations auditable from the workspace governance surface
- the first Milestone 23 persona-library slice now exposes `human_difference_axis_summary` for persona-library coverage/gap review and persists every populated `human_difference_axes.*` value into the metadata trait index for later explainable panel composition
- the second Milestone 23 persona-library slice now exposes heuristic calibration miss attribution across persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking instead of leaving miss diagnosis implicit
- the third Milestone 23 persona-library slice now projects backend-owned panel explainability, under-covered axis detection, similarity hotspots, and per-persona selection rationale into sampling and report artifacts
- Milestone 24 is now complete: repeated-study comparison, recurring-pattern synthesis, panel-learning projection, and decision-trend projection are all explicit backend-owned evidence surfaces instead of page-local reconstruction
- Milestone 25 is now complete: regulated/high-stakes classification, governed reviewer handoff, governed redaction, and compliance-audit bundles now stay backend-owned across study, evidence, export, share, support, and audit surfaces
- Milestone 26 is now complete: backend-owned `public_claims_boundary`, `launch_blockers`, `customer_operations_support_boundary`, and `self_serve_onboarding_pricing_boundary` now make benchmark disclosure, support posture, onboarding/pricing readiness, and bounded customer-facing claims inspectable without page-local interpretation
- Milestone 37 is now complete: Frontline run detail can show near-live progress, transcript exchanges, facilitator trace, synthetic participant reasoning trace, audit/provider lineage, and source-linked evidence provenance
- Milestone 38 is now complete: messaging and positioning validation can be inferred from user intent while keeping message comprehension, credibility, trust language, misunderstanding, and adoption-boundary evidence separate
- Milestone 39 is now complete: guided playbooks and rerun templates let users repeat studies with changed assumptions while preserving source-run and plan-revision lineage
- Milestone 40 is now complete: calibration observability is backend-owned, visible in the Frontline workspace, and connected to public-launch readiness blockers
- Milestone 41 is now complete: privacy/export controls are backend-owned, visible in the Frontline workspace/share surfaces, and preserve retention, deletion-request, redaction, data-residency, export/share, and audit lineage
- Milestone 42 is now complete: run-event streaming, observed-interview bridge metadata, integration events, boundary-preserving payloads, and delivery-attempt audit are backend-owned and visible from Frontline run/workspace surfaces

As of now, the platform has not yet proven:

- full persona profile review and study-time persona creation from the Frontline setup flow before plan approval
- broader self-serve onboarding, pricing, support, and customer-operations readiness strong enough for ordinary multi-team studies without manual intervention
- hosted outbound webhook workers, customer-managed destinations, and retry queues beyond the current local delivery-attempt audit
- broad external benchmark coverage across markets, domains, and repeated live human studies
- replacement-grade reliability across research stages or high-stakes domains
- broader public-launch route and documentation coverage across every future customer-facing workflow beyond the current bounded MVP shell

## Recommended Next Sequence

1. Build M43 next: persona profile review and study-time persona creation during Frontline setup, with selected-profile lineage preserved into approved plans and runs.
2. Build M44 after M43: procurement, workspace ownership, billing metadata, audit packs, and support-boundary controls for enterprise review.
3. Keep M45-M48 as public/replacement/scale reliability gates: multi-market benchmark expansion, replacement-readiness review, provider governance, and platform scale.
4. Keep the product claim boundary unchanged: Frontline reports, decisions, transcripts, traces, calibration summaries, privacy/export summaries, and shares are usable simulated evidence surfaces, not human market proof or replacement-grade reliability.

## Unified Development Backlog

### Current architecture state

- the repository is still local-first, but it now has both a CLI shell and a lightweight authenticated WSGI API plus worker runtime for workspace-scoped validation jobs
- shared domain, facilitator, observer, persona, sampling, reporting, and evaluation modules already exist as reusable Python packages
- prototype validation already has explicit stimulus, synthesis, observed-action contracts, a native manifest-backed clickable executor, and a browser behavior trace executor for clickable/live-app artifacts
- the repository is not Markdown-first data storage; JSON files and filesystem artifacts already hold the primary machine-readable records, while Markdown mainly acts as a human-readable projection layer
- run and interview artifacts are file-backed and auditable, while the local SaaS runtime now stores workspace, billing, token, and validation-job lifecycle state in SQLite
- persona-library storage now follows the accepted `artifact-first, SQL-indexed, object-store-ready` rule: local development keeps SQLite indexes plus local artifacts, while future SaaS/cloud should use Postgres plus object storage and never treat production server local disk as the source of truth
- `frontend/workspace_shell_app` is the first React/Vite framework-hosted shell slice, reusing the Stage 15 shell document and shared shell controller instead of reimplementing product behavior inside framework components
- the accepted frontend direction is framework promotion first, with Next.js treated as a later hosted-product candidate rather than an immediate requirement
- the accepted backend direction is to keep `ai_validation_swarm` as the Python research core and add FastAPI only as a thin adapter when typed OpenAPI contracts, hosted auth integration, or deployment requirements justify it

### Accepted persona library storage decision

Status: `accepted`

Decision:

- keep the current local shape as SQLite indexes plus local persona artifacts
- treat JSON and Markdown persona artifacts as durable research records rather than opaque database blobs
- use SQL for catalog, selection, readiness, generation jobs, permissions, trait indexes, and UI queries
- use Postgres plus object storage for future SaaS/cloud rather than production server local disk
- keep generated personas provisional until validation, duplicate, and coverage checks promote them to ready
- keep public-figure, celebrity, expert, or influencer-inspired personas as separate simulated lenses rather than normal participant personas

Why this improves the platform:

- improves behavioral realism and panel quality by making target-audience coverage gaps queryable
- improves evidence quality and auditability by preserving immutable persona artifacts, version lineage, hashes, and selected-persona run snapshots
- improves scalable research throughput by allowing dynamic gap-fill generation without hiding mutation behind read endpoints

Canonical spec:

- `specs/persona_library_storage_and_saas_contract.md`

Non-goals:

- no immediate cloud migration as part of the current local MVP
- no silent read-time persona generation from `GET /persona-library`
- no production SaaS dependency on server local disk as the durable persona store
- no use of public-figure-inspired lenses as human market proof

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

10. `cloud_persona_catalog_and_object_artifact_storage` - `planned` - `P2` - `5 SP`
    Purpose: when SaaS/cloud migration becomes active, migrate persona catalog, readiness, generation jobs, trait indexes, and tenant permissions to Postgres while storing immutable persona artifacts, manifests, hashes, generation notes, and selected-persona snapshots in object storage.
    Dependency: this should wait until the product needs hosted multi-tenant persona management, backup/restore, or cloud generation workers; local MVP should continue using SQLite plus local artifacts.
    Boundary: keep full persona artifacts versioned and restorable; do not make production server local disk the source of truth, and do not replace auditable artifacts with opaque database blobs.

11. `framework_hosted_workspace_frontend` - `in_progress` - `P2` - `5 SP`
   Purpose: move the Stage 15 study-first shell from prototype HTML ownership into a framework-hosted frontend while preserving the shared shell app, snapshot, runtime-client, and frontend-adapter contracts.
   Evidence: `frontend/workspace_shell_app` now provides a React/Vite host that imports the Stage 15 shell document, mounts `mountStage15WorkspaceShell`, keeps route/app bootstrap behavior outside inline prototype ownership, and directly renders the full visible Stage 15 shell surface inside the framework boundary.
   Remaining gap: this is a first framework host, not yet the final production workspace frontend; the local hosted shell now has server-backed same-origin browser sessions plus first decision-log review threads and approval state, but broader identity integration, richer collaboration UX, fuller framework-native route ownership, deeper component decomposition, richer observability, and deployment integration remain open even though the visible shell is no longer injected from prototype markup.
   Decision: keep React as the current implementation path; revisit Next.js only when server routing, production auth/session handling, or deployment needs justify the added framework surface.

12. `fastapi_thin_api_adapter` - `planned` - `P2` - `3 SP`
   Purpose: add a typed ASGI/OpenAPI adapter around the existing SaaS runtime only after current route contracts and frontend consumers stabilize, so hosted wrappers can consume the same research core without rewriting it.
   Dependency: `framework_hosted_workspace_frontend` should prove route/session ownership first, and `evidence_query_index_and_replay` should remain stable enough that API migration does not weaken replay or audit behavior.
   Boundary: FastAPI must call the existing Python runtime modules and worker/job contracts; it must not move simulation, synthesis, evidence ranking, or worker execution into the web layer.

### Architecture sequencing rule

- do the observed-action trace contract before any clickable or live-app runtime
- keep JSON and file artifacts as the primary machine-readable records; do not treat Markdown as the canonical persistence layer
- do structured metadata persistence before API-first SaaS product surface work
- keep relational metadata as the primary query layer for persona selection; do not promote Mongo-first document storage or graph-first selection until scale or traversal needs justify them
- keep persona storage `artifact-first, SQL-indexed, object-store-ready`: local uses SQLite plus local artifacts; SaaS/cloud should use Postgres plus object storage; production server local disk must not become the durable persona source of truth
- review whether a graph projection is needed only after persona selection indexes are stable and similarity/diversity queries become a repeated bottleneck
- make dynamic persona generation an explicit job with provisional-to-ready promotion; do not silently mutate persona libraries from read endpoints
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
