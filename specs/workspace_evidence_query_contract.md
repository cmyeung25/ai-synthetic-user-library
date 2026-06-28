# Workspace Evidence Query Contract (Draft)

## Purpose

This document defines the query-facing contract that should sit between:

- the structured evidence metadata layer
- completed run artifacts and replay references
- the Workspace UI evidence browser and replay surface

The goal is to let the workspace query evidence through one normalized contract instead of hard-coding artifact lists, filters, or replay assumptions inside page-local prototype logic.

## Why this contract exists

Research bottleneck improved:

- completed runs are not useful at scale if operators still need raw folder inspection to find the relevant trace, analysis, or report artifact

What this improves:

- evidence discipline
- auditability
- scalable research throughput
- backend-owned replay and comparison context for the workspace review surface

Why it matters now:

- the repository already has a completed-run evidence browser prototype
- the next step needs a stable query boundary so replay depth and nearby comparison guidance stop depending on page-local frontend heuristics

## Architecture role

This contract is the query-and-replay bridge between backend evidence indexes and the Workspace UI.

It is:

- downstream of the machine-readable artifact and metadata store
- upstream of the operator-facing query surface
- responsible for search, family filtering, result projection, and replay-linked selection
- responsible for backend-owned cross-run reliability, contradiction, calibration, and audit-lineage projection

It is not:

- the canonical persistence schema
- the raw artifact file format
- a generic full-text search engine design
- human market proof or a replacement-readiness score

## Source-of-truth order

The source-of-truth order should be:

1. run artifact files and machine-readable outputs
2. structured metadata index records
3. query result projection
4. visible Workspace UI evidence-browser state

The frontend should never invent query results from page-local assumptions when index records already exist.

## Query scope

The query contract should decide:

1. whether the run is query-ready
2. which artifact families are available
3. how many results match a query and family filter
4. which result is selected
5. which replay steps are linked to that result
6. which same-run comparison candidates are worth checking next
7. which cross-run comparison candidates are worth checking next
8. whether the selected signal is stable, contradictory, missing context, or still single-run only
9. which calibration records and human-validation gaps must stay visible
10. which audit lineage links the selected evidence back to run, job, study, replay, and comparison set
11. which boundary warning still applies while reviewing the result

## Input contracts

### 1. Completed run record

Minimum run record fields consumed:

```json
{
  "job_id": "job_workspace_proto_008",
  "status": "completed",
  "worker_id": "worker-hkg-02",
  "artifact_refs": [
    "runs/job_workspace_proto_008/report.json",
    "runs/job_workspace_proto_008/summary.md",
    "runs/job_workspace_proto_008/trace.json"
  ]
}
```

### 2. Draft plan object

Minimum draft fields consumed:

- `proposed_run.execution_status`
- `evidence_boundary`
- `inference.primary_mode`

### 3. Evidence catalog or metadata result set

Minimum queryable artifact entry:

```json
{
  "id": "artifact-trace",
  "family": "trace",
  "kind": "observed_action_trace",
  "title": "Observed action trace",
  "artifact_path": "runs/job_workspace_proto_008/trace.json",
  "summary": "Structured task-path trace with hesitation and backtracking.",
  "tags": ["trace", "replay"],
  "replay_steps": [
    {
      "id": "step-03",
      "title": "Connect-data task hesitates",
      "timestamp": "00:28",
      "note": "Backtracking begins after uncertainty about reversibility."
    }
  ]
}
```

This can initially be assembled in-memory for prototypes, but the stable future source should be the structured metadata layer plus replay references.

Browser-observed clickable and live-app traces from Milestone 14 must enter this contract as `family: "trace"` and `kind: "observed_action_trace"`. Driver details such as URL, selector, viewport, browser driver, and safety-gate status belong in artifact metadata or replay-step detail; the Evidence Review surface must not introduce a parallel browser-only evidence family that bypasses reliability, replay, comparison, calibration, or audit-lineage handling.

### 4. Local UI query state

```json
{
  "query_text": "hesitate",
  "active_family": "trace",
  "sort_by": "relevance",
  "selected_result_id": "query-artifact-trace",
  "selected_replay_step_id": "step-03"
}
```

## Output contract

Example output:

```json
{
  "query_status": "query_ready",
  "query_text": "hesitate",
  "active_family": "trace",
  "sort_by": "relevance",
  "facet_counts": {
    "all": 6,
    "input": 2,
    "trace": 1,
    "analysis": 1,
    "output": 2
  },
  "result_count": 1,
  "selected_result_id": "query-artifact-trace",
  "selected_artifact_id": "artifact-trace",
  "selected_replay_step_id": "step-03",
  "results": [
    {
      "id": "query-artifact-trace",
      "artifact_id": "artifact-trace",
      "title": "Observed action trace",
      "family": "trace",
      "kind": "observed_action_trace",
      "artifact_path": "runs/job_workspace_proto_008/trace.json",
      "summary": "Structured task-path trace with hesitation and backtracking.",
      "tags": ["trace", "replay"],
      "replay_step_titles": ["Connect-data task hesitates"],
      "relevance_score": 2
    }
  ],
  "replay_context": {
    "selected_result_has_replay": true,
    "replay_result_count": 2,
    "selected_family_replay_result_count": 2,
    "note": "1 replay step(s) are linked to the selected evidence."
  },
  "comparison_context": {
    "selected_family_result_count": 1,
    "selected_family_replay_result_count": 1,
    "comparison_candidates": [
      {
        "id": "query-artifact-stage_results",
        "artifact_id": "artifact-stage_results",
        "title": "Stage results",
        "family": "trace",
        "kind": "stage_results",
        "artifact_path": "runs/job_workspace_proto_008/stage_results.json",
        "summary": "Execution-stage status summary.",
        "relation_note": "same family with replay context",
        "has_replay": true
      }
    ],
    "recommended_comparison_id": "query-artifact-stage_results",
    "recommended_comparison_reason": "A same-family artifact provides the tightest comparison for repeated signals.",
    "note": "Use same-family evidence to check whether the same signal repeats across nearby artifacts."
  },
  "cross_run_comparison": {
    "comparison_run_count": 2,
    "candidate_runs": [
      {
        "run_id": "run_20260628_102100",
        "job_id": "job_workspace_proto_007",
        "run_kind": "validation_run",
        "status": "completed",
        "finished_at": "2026-06-28T10:21:43+00:00",
        "brief_id": "brief_001",
        "research_goal": "",
        "interview_mode": "",
        "shared_signal_count": 4,
        "relation_note": "same brief",
        "result_count": 2,
        "replay_result_count": 1,
        "selected_family_result_count": 1,
        "top_result_id": "query-artifact-stage-results-json",
        "top_result_title": "Stage results"
      }
    ],
    "selected_comparison_run_id": "run_20260628_102100",
    "selected_comparison_job_id": "job_workspace_proto_007",
    "selected_comparison_run": {
      "run_id": "run_20260628_102100",
      "job_id": "job_workspace_proto_007",
      "run_kind": "validation_run",
      "status": "completed",
      "finished_at": "2026-06-28T10:21:43+00:00",
      "brief_id": "brief_001",
      "research_goal": "",
      "interview_mode": "",
      "shared_signal_count": 4,
      "relation_note": "same brief",
      "result_count": 2,
      "replay_result_count": 1,
      "selected_family_result_count": 1,
      "top_result_id": "query-artifact-stage-results-json",
      "top_result_title": "Stage results",
      "recommended_result_id": "query-artifact-stage-results-json",
      "recommended_result_title": "Stage results",
      "recommended_result_reason": "A same-family artifact preserves the current evidence layer even when the exact artifact kind differs.",
      "shared_family_result_count": 1,
      "shared_kind_result_count": 0,
      "shared_replay_result_count": 1,
      "comparison_results": [
        {
          "id": "query-artifact-stage-results-json",
          "artifact_id": "artifact-stage-results-json",
          "title": "Stage results",
          "family": "trace",
          "kind": "stage_results",
          "artifact_path": "runs/run_20260628_102100/stage_results.json",
          "summary": "Execution-stage status summary.",
          "tags": ["trace", "stage_results"],
          "replay_step_titles": ["Planner", "Responses"],
          "relevance_score": 1
        }
      ],
      "note": "Compare same-family artifacts across runs to see whether the same hesitation or objection repeats nearby."
    },
    "note": "2 comparable completed runs are available for cross-run review."
  },
  "evidence_reliability": {
    "contract_version": "workspace-evidence-reliability/v0-draft",
    "review_status": "reliability_ready",
    "stability_label": "comparison_available",
    "stability_score": 52,
    "selected_signal_id": "trace:observed_action_trace",
    "signal_terms": ["hesitate", "backtracking"],
    "supporting_evidence": [
      {
        "source": "cross_run",
        "run_id": "run_20260628_102100",
        "artifact_id": "artifact-stage-results-json",
        "title": "Stage results",
        "family": "trace",
        "kind": "stage_results",
        "relation": "cross-run comparable evidence",
        "summary": "Execution-stage status summary."
      }
    ],
    "contradicting_evidence": [],
    "missing_context": [
      {
        "id": "human_validation_gap",
        "label": "human validation gap",
        "severity": "high",
        "note": "Synthetic evidence has not been calibrated against human outcome data for this claim."
      }
    ],
    "calibration_records": [
      {
        "id": "synthetic_boundary",
        "status": "requires_human_validation",
        "label": "Synthetic evidence boundary",
        "note": "This reliability review is not human market proof."
      },
      {
        "id": "repeatability",
        "status": "comparison_available",
        "label": "Repeatability signal",
        "score": 52,
        "supporting_count": 1,
        "contradicting_count": 0
      }
    ],
    "synthetic_boundary": "Synthetic evidence only. Reliability labels require human calibration before replacement-grade claims."
  },
  "audit_lineage": {
    "contract_version": "workspace-evidence-audit-lineage/v0-draft",
    "source_run": {
      "run_id": "run_20260628_102000",
      "job_id": "job_workspace_proto_008",
      "project_id": "project_001",
      "study_id": "study_001",
      "job_status": "completed",
      "run_kind": "validation_run",
      "brief_id": "brief_001",
      "research_goal": "Find onboarding hesitation.",
      "interview_mode": "prototype_validation"
    },
    "selected_evidence": {
      "result_id": "query-artifact-trace",
      "artifact_id": "artifact-trace",
      "family": "trace",
      "kind": "observed_action_trace",
      "signal_id": "trace:observed_action_trace",
      "signal_terms": ["hesitate", "backtracking"]
    },
    "replay": {
      "selected_replay_step_id": "step-03",
      "selected_replay_step_title": "Connect-data task hesitates",
      "selected_replay_step_timestamp": "00:28"
    },
    "comparison_set": {
      "comparison_run_count": 2,
      "candidate_run_ids": ["run_20260628_102100"],
      "candidate_jobs": [
        {
          "run_id": "run_20260628_102100",
          "job_id": "job_workspace_proto_007",
          "project_id": "project_001",
          "study_id": "study_001",
          "job_status": "completed"
        }
      ],
      "selected_comparison_run_id": "run_20260628_102100",
      "selected_comparison_job_id": "job_workspace_proto_007",
      "selected_comparison_project_id": "project_001",
      "selected_comparison_study_id": "study_001",
      "selected_comparison_result_id": "query-artifact-stage-results-json"
    }
  },
  "boundary_warning": "The run artifacts are ready for operator review, but the evidence remains synthetic and bounded by the current prototype-validation contract."
}
```

## Canonical fields

### `query_status`

Allowed values:

- `query_pending`
- `query_ready`

### `active_family`

Allowed baseline values:

- `all`
- `input`
- `trace`
- `analysis`
- `output`

### `sort_by`

Allowed baseline values:

- `relevance`
- `newest`
- `family`

### `facet_counts`

This should come from the current evidence result universe, not from hard-coded UI counts.

### `results`

Each result should be a stable query projection, not a direct raw artifact dump.

### `selected_result`

The query layer should choose the selected result, falling back to the first visible result if the local selection is stale.

### `replay_sequence`

Replay steps should be attached only when the selected result has replay context.

### `replay_context`

This is the backend-owned summary of replay depth for the current visible result set.

It should say:

- whether the selected result has replay
- how many visible results carry replay context
- whether replay exists inside the selected family
- the operator-facing replay note the frontend can render directly

### `comparison_context`

This is the backend-owned nearby-comparison summary for the current visible result set.

It should say:

- how many visible results sit in the selected family
- how many of those same-family results also carry replay
- which comparison candidates should be shown first
- why the first comparison path is recommended
- the operator-facing comparison note the frontend can render directly

### `cross_run_comparison`

This is the backend-owned cross-run comparison summary for the current workspace-visible scope.

It should say:

- how many comparable completed runs are available
- which runs should be shown first
- why each candidate is related to the current run
- which artifact inside the selected comparison run is the best comparison target
- whether that comparison preserves the same artifact family, kind, or replay-bearing surface

### `evidence_reliability`

This is the backend-owned reliability review for the currently selected evidence result.

It should say:

- whether reliability review is ready or pending
- which stability label applies to the selected signal
- which supporting evidence exists in the selected run or selected comparison run
- which contradicting evidence should be reviewed before using the signal
- which missing context still blocks stronger prediction claims
- which calibration records keep synthetic evidence boundaries explicit

Allowed baseline `stability_label` values:

- `pending`
- `single_run_signal`
- `comparison_available`
- `repeated_signal`
- `mixed_or_contradictory`

The frontend may render this payload, but must not invent or recalculate reliability labels from page-local state.

### `audit_lineage`

This is the backend-owned provenance map for the selected evidence result.

It should say:

- which run, job, project, and study produced the selected evidence
- which artifact and signal are currently selected
- which replay step is in focus when replay exists
- which comparison runs and jobs were eligible
- which comparison run and result were selected for review

Study/project/job fields may be `null` for legacy runs without workspace metadata, but study-linked validation jobs should populate them through the SaaS runtime wrapper.

### `boundary_warning`

The evidence boundary must remain visible during query review, not only on the earlier confirmation screen.

## Derivation rules

### Rule 1: completed-only gating

If the run is not completed, the query layer should return:

- `query_status = query_pending`
- `result_count = 0`
- no selected result

### Rule 2: family filter applies before selection

Selection fallback should happen only after the active family filter is applied.

### Rule 3: query result is metadata-backed

Result cards should come from index-like records, not from direct page-local assumptions about filenames.

### Rule 4: replay focus depends on selected result

The replay sequence must change when the selected result changes.

### Rule 5: boundary warning survives successful completion

Even completed runs must still surface the current evidence boundary and synthetic-only constraints.

### Rule 6: comparison guidance is backend-owned

When nearby comparison guidance exists, the backend should rank and annotate comparison candidates instead of leaving that decision to page-local sorting rules.

### Rule 7: replay notes summarize visible depth, not only the selected artifact

The replay note should tell the operator whether replay is available on the selected artifact, elsewhere in the visible result set, or nowhere in the current query scope.

### Rule 8: cross-run comparison stays metadata-backed and contract-safe

Cross-run candidates should be limited to comparable completed runs that stay within the current workspace scope and current run contract boundary. The backend should rank candidate runs before the frontend renders them.

### Rule 9: cross-run candidate visibility follows the current query scope

If the current query text or family filter removes all visible results from a comparison run, that run should not be surfaced as an active cross-run candidate for this query view.

### Rule 10: reliability scoring is backend-owned

Stability labels, supporting evidence, contradicting evidence, missing context, and calibration records must be emitted by the backend evidence-query/runtime layer. The frontend should render this state and preserve the boundary language.

### Rule 11: audit lineage is workspace-aware when workspace metadata exists

The SaaS runtime should enrich run-artifact lineage with job, project, and study identifiers when those runs were created through workspace validation jobs. It must not fabricate study linkage for legacy runs that lack metadata.

### Rule 12: calibration does not imply human proof

Calibration records can mark repeatability or contradiction inside synthetic evidence, but every payload must preserve a human-validation gap unless real human outcome data has been explicitly attached by a future calibration workflow.

## Frontend function boundary

Recommended implementation shape:

```ts
type WorkspaceEvidenceQueryInput = {
  draftPlan: DraftPlan;
  runRecord: RunRecord;
  evidenceCatalog: EvidenceCatalogEntry[];
  localUiState: LocalQueryUiState;
};

type WorkspaceEvidenceQueryOutput = {
  queryStatus: QueryStatus;
  activeFamily: EvidenceFamily;
  sortBy: QuerySort;
  facetCounts: FacetCounts;
  resultCount: number;
  selectedResultId: string | null;
  selectedArtifactId: string | null;
  selectedReplayStepId: string | null;
  results: QueryResultProjection[];
  selectedResult: QueryResultProjection | null;
  linkedArtifact: EvidenceCatalogEntry | null;
  replaySequence: ReplayStep[];
  replayFocusStep: ReplayStep | null;
  boundaryWarning: string | null;
  evidenceReliability: EvidenceReliability | null;
  auditLineage: EvidenceAuditLineage | null;
};

declare function deriveWorkspaceEvidenceQueryState(
  input: WorkspaceEvidenceQueryInput
): WorkspaceEvidenceQueryOutput;
```

## Verification plan

To know this contract is working:

1. contract tests for:
   - completed-only gating
   - family filtering
   - selection fallback
   - replay-focus selection
2. prototype validation inside the Stage 10 workspace evidence-query demo
3. later metadata integration tests proving the same projection works against structured index records rather than in-memory mock data
4. SaaS runtime tests proving study-linked jobs enrich audit lineage with job/project/study identifiers
5. browser smoke tests proving product-shell review panels do not overlap, hide text, or block primary research actions

## Current repository evidence

- [demo/workspace_ui_moss_stage9/index.html](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_moss_stage9/index.html>) already proves the completed-run evidence browser surface
- [demo/workspace_ui_shared/workspace_ui_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_ui_adapter.mjs>) now contains shared evidence-browser derivation

- [src/ai_validation_swarm/saas/evidence_query.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/evidence_query.py>) now serves a real completed-run evidence-query projection from metadata and artifact files
- [src/ai_validation_swarm/saas/api.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/api.py>) now exposes `GET /api/v1/evidence-query`
- [tests/unit/test_saas_runtime.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/tests/unit/test_saas_runtime.py>) now verifies pending and completed evidence-query API behavior

## Milestone 12 implementation evidence

- `src/ai_validation_swarm/saas/evidence_query.py` now serves completed-run evidence-query projection, cross-run comparison, reliability review, calibration records, and audit-lineage payloads from metadata and artifact files.
- `src/ai_validation_swarm/saas/runtime.py` now enriches cross-run and audit-lineage payloads with workspace job/project/study context when run metadata exists.
- `src/ai_validation_swarm/saas/api.py` now exposes `GET /api/v1/evidence-query` and serves the hosted shell bundle through chunked static file responses.
- `demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs` now projects reliability summary/detail cards, calibration records, and audit-lineage summaries into the review surface.
- `scripts/verify_stage15_hosted_shell_smoke.mjs` now verifies clean job deep-link hydration plus Milestone 12 critical-action and critical-panel layout acceptance gates.
- `tests/unit/test_saas_runtime.py` now verifies pending, completed, cross-run comparison, evidence reliability, calibration records, and study-linked audit-lineage API behavior.

This contract now lets the workspace consume one metadata-backed query object for results, replay context, cross-run comparison, evidence reliability, calibration records, and audit lineage instead of growing page-local evidence heuristics. The remaining expansion layer is attaching real human outcome calibration data, not claiming replacement-grade proof from synthetic repeatability alone.
