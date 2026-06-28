# Workspace Shell Frontend Adapter Contract (Draft)

## Purpose

This document defines the page-level frontend adapter contract that sits between:

- the integrated Workspace shell bundle
- the validation-job runtime bridge state
- the selected live or sample job
- the actual page components that render metrics, buttons, summaries, and JSON debug panels

The goal is to stop the real frontend from re-deriving button states, pill tones, summary cards, and shell status in many separate components.

## Why this contract exists

Research bottleneck improved:

- the workspace shell is close to a real operator console, but the frontend still lacks one explicit page-facing object that ties planning, runtime ingress, and review state together

What this improves:

- scalable research throughput
- evidence discipline
- frontend/backend integration clarity
- safer promotion from engineering prototype to real workspace shell

Why it matters now:

- the repository already has a shared planning adapter, run monitor, evidence browser/query bundle, and validation-job bridge
- Stage 12 proved live request mapping and live job loading
- the remaining gap is now less about raw prototype flow and more about making the actual frontend implementation consume one stable contract

## Architecture role

This contract is the `frontend composition layer` for the workspace shell.

It is:

- downstream of the base Workspace UI adapter and the validation-job bridge
- upstream of page components and framework-specific UI implementation
- responsible for page-facing summaries, action enablement, status tones, and debug projections

It is not:

- the draft-plan source of truth
- the validation-job request contract itself
- the backend evidence-query contract
- the final localization system

## Alignment to platform goals

1. Which research bottleneck does this improve?
   It reduces operator ambiguity between confirmation, job submission, run monitoring, and evidence review inside one workspace shell.
2. Does it improve realism, decision prediction, evidence quality, calibration, or throughput?
   It improves throughput and evidence discipline by making the operator surface consistent with the real runtime boundary.
3. Does it move the platform closer to replacing interviewer-led work?
   Yes. A replacement-grade operator flow needs a stable research intake to execution to review surface, not only isolated backend contracts.
4. Why is this necessary now?
   Because the shell already has enough capability layers that ad hoc component wiring would create contract drift and slow down the real frontend implementation.

## Contract layering

Recommended layering:

1. conversation state
2. draft plan object
3. base Workspace UI adapter
4. run monitor, evidence browser, and evidence query derivations
5. validation-job runtime bridge
6. workspace shell frontend adapter
7. framework-specific page components

The frontend adapter should compose stable upstream outputs. It should not duplicate the planning or runtime derivation logic internally.

## Input contracts

### 1. Workspace shell bundle

The adapter expects the integrated shell bundle produced from the shared workspace shell module.

Minimum consumed fields:

- `draft`
- `adapter`
- `run_monitor`
- `evidence_query`
- `workspace_shell.active_surface`
- `workspace_shell.stage_strip`
- `workspace_shell.section_status`

### 2. Validation bridge state

The adapter expects the runtime bridge state described in [workspace_validation_job_bridge_contract.md](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/specs/workspace_validation_job_bridge_contract.md>).

Minimum consumed fields:

- `bridge_status`
- `submission_ready`
- `request_payload`
- `selected_job_id`
- `derived_run_record`
- `endpoint_summary`
- `live_review_gap`
- `warning`

### 3. Effective review query state

The adapter may receive either:

- the local integrated-shell evidence query projection from the shared workspace bundle, or
- a backend completed-run evidence-query payload returned by `GET /api/v1/evidence-query`

Minimum consumed fields:

- `query_status`
- `result_count`
- `selected_result_id`
- `selected_replay_step_id`
- `results`
- `selected_result`
- `linked_artifact`
- `replay_sequence`
- `boundary_warning`

### 4. Selected job

The selected live or sample job may be `null`.

Minimum consumed fields when present:

- `job_id`
- `status`
- `provider_name`
- `output_run_path`
- `last_error`

### 5. View context

Example:

```json
{
  "mode": "live",
  "query_source": "backend",
  "last_api_response": {
    "job": {
      "job_id": "job_20260627_abcdef12",
      "status": "queued"
    }
  }
}
```

This view context is page-local. It should not alter planning or runtime meaning.

## Output contract

The adapter should output one page-facing object.

Example:

```json
{
  "contract_version": "workspace-shell-frontend-adapter/v0-draft",
  "metrics": {
    "bridge_status": "job_loaded",
    "submission_ready": true,
    "selected_project_id": "project_123",
    "selected_study_id": "study_123",
    "selected_export_bundle_id": "export_123",
    "selected_share_bundle_id": "share_123",
    "selected_support_snapshot_id": "support_123",
    "selected_job_id": "job_20260627_abcdef12",
    "shell_surface": "run_monitor"
  },
  "pills": {
    "bridge": { "tone": "completed", "label": "job_loaded" },
    "job": { "tone": "queued", "label": "queued" },
    "shell": { "tone": "queued", "label": "run_monitor" }
  },
  "actions": {
    "submit_live_job": { "intent": "submit_validation_job", "enabled": true },
    "list_live_jobs": { "intent": "list_validation_jobs", "enabled": true },
    "load_selected_job": { "intent": "load_validation_job_detail", "enabled": true },
    "load_live_evidence_query": { "intent": "load_evidence_query", "enabled": true },
    "apply_evidence_query": { "intent": "apply_evidence_query", "enabled": true },
    "use_sample_jobs": { "intent": "switch_to_sample_jobs", "enabled": true }
  },
  "request_summary": [
    { "id": "brief_path", "label": "brief_path", "value": "briefs/brief.json" },
    { "id": "filters", "label": "filters", "value": "none" },
    { "id": "provider_name", "label": "provider_name", "value": "mock" }
  ],
  "draft_summary": [
    { "id": "mode", "label": "mode", "value": "prototype_validation" },
    { "id": "mode_override", "label": "mode override", "value": "auto" },
    { "id": "persona_filters", "label": "persona filters", "value": "none" }
  ],
  "product_surface": {
    "projects": [
      { "project_id": "project_123", "title": "Inbox Coach Launch", "selected": true }
    ],
    "studies": [
      { "study_id": "study_123", "title": "Onboarding hesitation study", "selected": true }
    ],
    "export_bundles": [
      { "export_bundle_id": "export_123", "title": "Exec review export", "selected": true }
    ],
    "share_bundles": [
      { "share_bundle_id": "share_123", "title": "Board review share", "selected": true }
    ],
    "support_snapshots": [
      { "support_snapshot_id": "support_123", "title": "Provider failure handoff", "selected": true }
    ]
  },
  "support_surface": {
    "submission_gate_summary": [
      { "id": "submission_gate_status", "label": "submission gate", "value": "blocked" }
    ],
    "blocked_reasons": [
      {
        "code": "concurrency_limit_reached",
        "message": "Workspace reached the max concurrent job limit (1).",
        "next_action": "Wait for an in-flight run to finish or move to a higher plan limit."
      }
    ],
    "job_diagnostic_summary": [
      { "id": "job_status", "label": "job status", "value": "failed" },
      { "id": "failure_category", "label": "failure category", "value": "provider_configuration" }
    ],
    "job_diagnostic_cards": [
      {
        "id": "job_support_summary",
        "title": "provider_configuration",
        "body": "Unknown provider: unknown-provider",
        "tone": "active"
      }
    ]
  },
  "review_surface": {
    "query_status": "query_ready",
    "query_source": "backend",
    "result_count": 2,
    "selected_result_id": "query-run_report",
    "results": [
      {
        "id": "query-run_report",
        "title": "Run report",
        "family": "output",
        "kind": "report",
        "summary": "Final synthetic evidence package.",
        "selected": true
      }
    ],
    "selected_evidence_summary": [
      { "id": "result_id", "label": "result id", "value": "query-run_report" }
    ],
    "selected_evidence_detail": [
      {
        "id": "summary",
        "title": "Run report",
        "body": "Final synthetic evidence package.",
        "tone": "active"
      }
    ],
    "evidence_coverage_cards": [
      {
        "id": "coverage_trace",
        "title": "Trace evidence",
        "body": "1 item in backend snapshot | active filter.",
        "active": true
      }
    ],
    "replay_focus_summary": [
      { "id": "replay_step", "label": "replay step", "value": "su_0002 response" }
    ],
    "replay_focus_detail": [
      {
        "id": "replay_focus",
        "title": "su_0002 response",
        "body": "Objection: procurement review. Try signal: clearer onboarding evidence.",
        "tone": "active"
      }
    ],
    "replay_steps": [],
    "selected_comparison_run_id": "run_20260628_102100",
    "cross_run_summary": [
      { "id": "comparison_run_count", "label": "comparison runs", "value": 1 },
      { "id": "selected_comparison_run", "label": "selected comparison run", "value": "run_20260628_102100" }
    ],
    "cross_run_detail": [
      {
        "id": "cross_run_summary",
        "title": "run_20260628_102100",
        "body": "Compare same-kind artifacts across runs to check whether the same signal repeats under the same evidence surface.",
        "tone": "active"
      }
    ],
    "cross_run_candidates": [
      {
        "run_id": "run_20260628_102100",
        "job_id": "job_007",
        "title": "Raw responses",
        "run_kind": "validation_run",
        "status": "completed",
        "relation_note": "same brief",
        "result_count": 2,
        "replay_result_count": 1,
        "selected": true
      }
    ],
    "cross_run_result_cards": [
      {
        "id": "query-cross-run-raw_responses",
        "title": "Raw responses",
        "family": "trace",
        "kind": "raw_responses",
        "summary": "Persona-level raw response payloads.",
        "recommended": true
      }
    ],
    "cross_run_note": "1 comparable completed run is available for cross-run review.",
    "related_results": [
      {
        "id": "query-stage_results",
        "title": "Stage results",
        "family": "trace",
        "kind": "stage_results",
        "summary": "Execution-stage status summary.",
        "relation_note": "same family with replay context",
        "selected": false
      }
    ],
    "related_results_note": "Use same-family evidence to check whether the same signal repeats across nearby artifacts.",
    "replay_note": "2 replay step(s) are linked to the selected evidence. Current focus: response 2."
  },
  "bridge_gap": "The validation-job API and backend evidence query can now both be attached, but replay still depends on trace-linked artifacts and a fuller backend-driven review surface.",
  "stage_strip": [
    { "id": "intake", "label": "Conversational intake", "state": "done" }
  ],
  "json_panels": {
    "request_payload": {},
    "selected_job": {},
    "last_api_response": {},
    "derived_run_record": {},
    "bridge_state": {},
    "shell_state": {}
  }
}
```

## Canonical fields

### `metrics`

Use for top-line status only:

- bridge status
- submission readiness
- selected project, study, export, share, and support ids
- selected job id
- active shell surface

These should stay small and operational.

### `pills`

This field should carry:

- `tone`
- `label`

The tone is semantic UI state such as `queued`, `running`, `completed`, or `failed`. Components should not infer tones independently.

### `actions`

Each action should expose:

- `intent`
- `enabled`

The page may choose its own localized label, but action availability should come from this contract.

### `*_summary`

These summary arrays are the stable render input for compact cards and side rails.

Each row should expose:

- `id`
- `label`
- `value`

### `product_surface`

This field is the stable render contract for Milestone 11 product objects around the research shell.

It may now carry:

- `projects`
- `studies`
- `export_bundles`
- `share_bundles`
- `support_snapshots`
- `selected_project_summary`
- `selected_study_summary`
- `selected_export_bundle_summary`
- `selected_share_bundle_summary`
- `selected_support_snapshot_summary`

The adapter should preserve synthetic-boundary language inside the selected export summary instead of stripping it out as page copy.
The same rule applies to the selected share summary.
The same rule also applies to selected support snapshots: the adapter should preserve the current diagnostic summary instead of forcing the page to rediscover it from raw snapshot payloads.

### `support_surface`

This field is the stable render contract for the visible operator-support area.

It should carry:

- submission-gate summary rows
- blocked-reason objects
- job-diagnostic summary rows
- support action/detail cards

The page should not rebuild support-language explanations from raw error strings in many places.

### `bridge_gap`

This field keeps the remaining backend boundary explicit.

At the current stage that means:

- backend evidence query can exist for completed runs
- replay depth may still be partial or empty
- the engineering shell may still mix backend payloads with local projection while the fuller review surface is being promoted

### `review_surface`

This field is the stable render contract for the visible evidence-review area.

It should carry:

- effective query status
- effective query source
- selected result and replay ids
- selected comparison run id
- visible result cards
- evidence coverage cards
- selected evidence summary rows
- selected evidence detail cards
- replay-focus summary rows
- replay-focus detail cards
- replay-step cards
- cross-run comparison summary rows
- cross-run comparison detail cards
- selectable comparison-run cards
- comparison-run artifact cards
- related evidence comparison cards
- empty or boundary notes

### `stage_strip`

This should pass through the current shell progression state so the page can render intake, confirmation, run monitoring, and review without recomputing those transitions.

### `json_panels`

These are engineering-facing projections for demo, QA, and integration debugging. They are useful now because the workspace shell is still being hardened against the real runtime.

## Derivation rules

### Rule 1: upstream logic owns behavior

The frontend adapter should summarize upstream state. It should not redefine:

- submission readiness
- queueability
- evidence-query readiness
- shell active surface

### Rule 2: action enablement comes from runtime truth

`submit_live_job.enabled` must derive from the runtime bridge, not from local component heuristics.

### Rule 3: selected live job wins over local shell assumptions

When a selected live job exists, the shell-facing summaries should reflect the job-normalized run state already present in the integrated shell bundle.

### Rule 4: review rendering should consume one effective query state

The page should not rebuild result cards, selected evidence summaries, and replay notes from raw backend payloads in many places. It should consume the adapter's one effective review surface whether the source is local projection or backend query.

When backend `comparison_context`, `replay_context`, or `cross_run_comparison` exists, the adapter should prefer those backend notes and ranking decisions over page-local fallback heuristics.

### Rule 5: the remaining review boundary stays visible

Do not let the page imply that evidence review is complete just because backend query exists. Replay sparsity, synthetic-only constraints, and mixed local/backend composition must remain explicit.

### Rule 6: localization stays outside the contract

The contract may provide draft labels for engineering demos, but production localization should wrap these rows rather than changing the data meaning.

## Frontend function boundary

Recommended implementation shape:

```ts
type WorkspaceShellFrontendAdapterInput = {
  bundle: WorkspaceShellBundle;
  bridgeState: WorkspaceValidationBridgeState;
  selectedJob: ValidationJobApiRecord | null;
  mode: "sample" | "live";
  lastApiResponse: unknown;
  reviewQueryState?: WorkspaceEvidenceQueryOutput;
  querySource?: "local" | "backend";
};

type WorkspaceShellFrontendAdapterOutput = {
  contractVersion: string;
  metrics: FrontendMetrics;
  pills: FrontendPills;
  actions: FrontendActions;
  requestSummary: SummaryRow[];
  bridgeSummary: SummaryRow[];
  selectedJobSummary: SummaryRow[];
  draftSummary: SummaryRow[];
  adapterSummary: SummaryRow[];
  runMonitorSummary: SummaryRow[];
  reviewSummary: SummaryRow[];
  reviewSurface: ReviewSurfaceProjection;
  sidecarRows: SummaryRow[];
  bridgeGap: string | null;
  stageStrip: ShellStage[];
  shellProjection: ShellProjection;
  jsonPanels: FrontendJsonPanels;
};
```

## Verification plan

To know this contract is working:

1. contract tests for:
   - blocked draft with no selected job
   - submission-ready confirmed draft
   - completed live job projection
   - bridge warning projection
   - backend review-surface projection separate from the local shell bundle
2. Stage 12 should consume this shared adapter instead of mapping every summary card or evidence-review card inline
3. roadmap and status docs should name this layer explicitly so the next implementation step is unambiguous

## Current repository evidence

- [demo/workspace_ui_shared/workspace_ui_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_ui_adapter.mjs>) already defines the shared planning, run-monitor, evidence-browser, evidence-query, and integrated shell bundle
- [demo/workspace_ui_shared/workspace_runtime_bridge.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_runtime_bridge.mjs>) already defines the validation-job runtime bridge
- [demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs>) now defines the explicit page-level frontend adapter
- [demo/workspace_ui_moss_stage12/index.html](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_moss_stage12/index.html>) can now render the engineering shell from this shared adapter instead of recomputing page summaries ad hoc

This contract exists so the next real workspace frontend can wire against one stable page-level adapter, including the evidence-review surface, instead of reverse-engineering Stage 12 demo code.
