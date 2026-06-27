import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveStage10EvidenceQueryBundle,
  deriveWorkspaceEvidenceQueryState
} from "../../demo/workspace_ui_shared/workspace_ui_adapter.mjs";

function makeDraftPlan(executionStatus = "completed") {
  return {
    status: "confirmed",
    inference: {
      primary_mode: "prototype_validation",
      secondary_lenses: ["onboarding_friction"]
    },
    proposed_run: {
      execution_status: executionStatus,
      first_task: "connect data"
    },
    evidence_boundary: {
      allowed_evidence: ["task_friction", "continuation_risk"],
      forbidden_claims: ["observed_real_user_behavior"],
      boundary_note: "Synthetic evidence remains bounded by the prototype-validation contract."
    },
    remediation: {
      blocking_reasons: [],
      missing_inputs: [],
      required_artifacts: [],
      fallback_options: [],
      recommended_next_action: {
        action_type: "view_results",
        label: "view results"
      }
    },
    confirmation: {
      required: true,
      status: "confirmed",
      blocking_reasons: []
    },
    audit: {}
  };
}

function makeRunRecord(status = "completed") {
  return {
    job_id: "job_workspace_proto_008",
    status,
    queue_position: 1,
    worker_id: "worker-hkg-02",
    current_step: "report_packaging",
    attempt_count: 1,
    last_event_at: "22:19",
    artifact_refs: status === "completed" ? ["runs/job_workspace_proto_008/report.json"] : []
  };
}

function makeCatalog() {
  return [
    {
      id: "artifact-brief",
      title: "Founder brief",
      family: "input",
      kind: "context",
      artifact_path: "briefs/founder-brief.json",
      summary: "Original context for the run.",
      tags: ["source", "context"],
      detail_lines: ["The brief defines the onboarding hesitation question."],
      replay_steps: []
    },
    {
      id: "artifact-trace",
      title: "Observed action trace",
      family: "trace",
      kind: "observed_action_trace",
      artifact_path: "runs/job_workspace_proto_008/trace.json",
      summary: "Trace shows where the persona hesitated and backtracked.",
      tags: ["trace", "replay"],
      detail_lines: ["Hesitation appears around permission cost and reversibility."],
      replay_steps: [
        { id: "trace-01", title: "Connect-data hesitation", timestamp: "00:28", note: "Backtracking begins." },
        { id: "trace-02", title: "Completion", timestamp: "00:51", note: "Task eventually completes." }
      ]
    },
    {
      id: "artifact-analysis",
      title: "Stimulus analysis",
      family: "analysis",
      kind: "stimulus_analysis",
      artifact_path: "runs/job_workspace_proto_008/stimulus_analysis.json",
      summary: "Analysis shows trust burden before the first task.",
      tags: ["analysis"],
      detail_lines: ["Trust burden rises before payoff is visible."],
      replay_steps: []
    },
    {
      id: "artifact-report",
      title: "Run report",
      family: "output",
      kind: "report",
      artifact_path: "runs/job_workspace_proto_008/report.json",
      summary: "Final report explains where operators hesitate and why continuation risk stays elevated.",
      tags: ["output", "report"],
      detail_lines: ["Continuation risk remains medium without explicit reversibility."],
      replay_steps: []
    }
  ];
}

function makeCopy() {
  return {
    firstTaskValue: "connect data",
    questionValue: "Where do new operators hesitate during onboarding, and do they continue after the first task?",
    desiredValue: "task-friction and continuation risk",
    nextUpload: "request inputs",
    nextFallback: "confirm fallback",
    nextConfirm: "confirm queueable plan",
    nextSaved: "resume later",
    phaseQueued: "queued",
    monitorAwait: "await worker progress",
    monitorViewResults: "view results",
    monitorInspectFailure: "inspect failure"
  };
}

test("deriveWorkspaceEvidenceQueryState remains pending until the run is completed", () => {
  const query = deriveWorkspaceEvidenceQueryState({
    draftPlan: makeDraftPlan("running"),
    runRecord: makeRunRecord("running"),
    evidenceCatalog: makeCatalog(),
    localUiState: { locale: "en", query_text: "hesitate", active_family: "all" }
  });

  assert.equal(query.query_status, "query_pending");
  assert.equal(query.result_count, 0);
  assert.equal(query.selected_result_id, null);
});

test("deriveWorkspaceEvidenceQueryState ranks results by relevance for text queries", () => {
  const query = deriveWorkspaceEvidenceQueryState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: {
      locale: "en",
      query_text: "hesitate",
      active_family: "all",
      sort_by: "relevance"
    }
  });

  assert.equal(query.query_status, "query_ready");
  assert.ok(query.result_count >= 2);
  assert.equal(query.results[0].artifact_id, "artifact-trace");
  assert.ok(query.results[0].relevance_score >= query.results.at(-1).relevance_score);
});

test("deriveWorkspaceEvidenceQueryState applies family facet and selection fallback", () => {
  const query = deriveWorkspaceEvidenceQueryState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: {
      locale: "en",
      query_text: "",
      active_family: "analysis",
      sort_by: "family",
      selected_result_id: "missing-result"
    }
  });

  assert.equal(query.result_count, 1);
  assert.equal(query.selected_result_id, "query-artifact-analysis");
  assert.equal(query.selected_artifact_id, "artifact-analysis");
});

test("deriveWorkspaceEvidenceQueryState returns replay focus from selected query result", () => {
  const query = deriveWorkspaceEvidenceQueryState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: {
      locale: "en",
      query_text: "trace",
      active_family: "trace",
      sort_by: "relevance",
      selected_result_id: "query-artifact-trace",
      selected_replay_step_id: "trace-02"
    }
  });

  assert.equal(query.selected_result_id, "query-artifact-trace");
  assert.equal(query.replay_focus_step.id, "trace-02");
  assert.equal(query.linked_artifact.id, "artifact-trace");
});

test("deriveStage10EvidenceQueryBundle produces metadata-backed query projection for the completed run", () => {
  const bundle = deriveStage10EvidenceQueryBundle({
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance",
      selectedResultId: "query-artifact-trace",
      selectedReplayStepId: "step-03"
    },
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "evidence_query" }
  });

  assert.equal(bundle.adapter.run_state, "completed");
  assert.equal(bundle.evidence_query.query_status, "query_ready");
  assert.equal(bundle.evidence_query.selected_result_id, "query-artifact-trace");
  assert.equal(bundle.evidence_query.selected_artifact_id, "artifact-trace");
  assert.equal(bundle.evidence_query.replay_focus_step.id, "step-03");
  assert.ok(bundle.evidence_query.result_count >= 1);
});
