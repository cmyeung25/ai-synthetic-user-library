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
- future metadata-backed replay and comparison workflows

Why it matters now:

- the repository already has a completed-run evidence browser prototype
- the next step needs a stable query boundary before fuller replay and comparison workflows are added

## Architecture role

This contract is the query-and-replay bridge between backend evidence indexes and the Workspace UI.

It is:

- downstream of the machine-readable artifact and metadata store
- upstream of the operator-facing query surface
- responsible for search, family filtering, result projection, and replay-linked selection

It is not:

- the canonical persistence schema
- the raw artifact file format
- a generic full-text search engine design

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
6. which boundary warning still applies while reviewing the result

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

## Current repository evidence

- [demo/workspace_ui_moss_stage9/index.html](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_moss_stage9/index.html>) already proves the completed-run evidence browser surface
- [demo/workspace_ui_shared/workspace_ui_adapter.mjs](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/demo/workspace_ui_shared/workspace_ui_adapter.mjs>) now contains shared evidence-browser derivation

- [src/ai_validation_swarm/saas/evidence_query.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/evidence_query.py>) now serves a real completed-run evidence-query projection from metadata and artifact files
- [src/ai_validation_swarm/saas/api.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/saas/api.py>) now exposes `GET /api/v1/evidence-query`
- [tests/unit/test_saas_runtime.py](</C:/Users/user/OneDrive/文件/AI Synthetic User Library/tests/unit/test_saas_runtime.py>) now verifies pending and completed evidence-query API behavior

This contract exists so the next query and replay step can converge on one metadata-backed frontend boundary instead of growing another page-local evidence list, while leaving richer replay depth and comparison workflows as the remaining expansion layer.
