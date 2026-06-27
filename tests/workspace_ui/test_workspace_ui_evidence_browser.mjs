import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveStage9EvidenceBundle,
  deriveWorkspaceEvidenceBrowserState
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
        action_type: executionStatus === "completed" ? "view_results" : "await_run",
        label: executionStatus === "completed" ? "view results" : "await run"
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
    current_step: status === "completed" ? "report_packaging" : "persona_panel_execution",
    attempt_count: 1,
    last_event_at: "22:19",
    artifact_refs: status === "completed" ? ["runs/job_workspace_proto_008/report.json"] : []
  };
}

function makeCatalog() {
  return [
    {
      id: "artifact-input",
      title: "Founder brief",
      family: "input",
      kind: "context",
      artifact_path: "briefs/founder-brief.json",
      summary: "Source context",
      tags: ["source"],
      replay_steps: []
    },
    {
      id: "artifact-trace",
      title: "Observed action trace",
      family: "trace",
      kind: "observed_action_trace",
      artifact_path: "runs/job_workspace_proto_008/trace.json",
      summary: "Trace summary",
      tags: ["trace"],
      replay_steps: [
        { id: "trace-01", title: "Entered flow", timestamp: "00:00", note: "Started." },
        { id: "trace-02", title: "Hesitated", timestamp: "00:22", note: "Paused." }
      ]
    },
    {
      id: "artifact-output",
      title: "Run report",
      family: "output",
      kind: "report",
      artifact_path: "runs/job_workspace_proto_008/report.json",
      summary: "Report summary",
      tags: ["output"],
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

test("deriveWorkspaceEvidenceBrowserState gates evidence review until results are ready", () => {
  const browser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: makeDraftPlan("running"),
    runRecord: makeRunRecord("running"),
    evidenceCatalog: makeCatalog(),
    localUiState: { locale: "en", active_filter: "all" }
  });

  assert.equal(browser.browser_status, "results_pending");
  assert.equal(browser.visible_count, 0);
  assert.equal(browser.selected_artifact_id, null);
});

test("deriveWorkspaceEvidenceBrowserState filters artifacts by family", () => {
  const browser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: { locale: "en", active_filter: "trace", selected_artifact_id: "artifact-trace" }
  });

  assert.equal(browser.browser_status, "results_ready");
  assert.equal(browser.visible_count, 1);
  assert.equal(browser.visible_artifacts[0].id, "artifact-trace");
  assert.equal(browser.selected_artifact_id, "artifact-trace");
});

test("deriveWorkspaceEvidenceBrowserState falls back to first visible artifact when selection is invalid", () => {
  const browser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: { locale: "en", active_filter: "output", selected_artifact_id: "missing-artifact" }
  });

  assert.equal(browser.selected_artifact_id, "artifact-output");
  assert.equal(browser.selected_artifact.title, "Run report");
});

test("deriveWorkspaceEvidenceBrowserState returns replay focus for selected trace artifact", () => {
  const browser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: makeRunRecord("completed"),
    evidenceCatalog: makeCatalog(),
    localUiState: {
      locale: "en",
      active_filter: "trace",
      selected_artifact_id: "artifact-trace",
      selected_replay_step_id: "trace-02"
    }
  });

  assert.equal(browser.replay_sequence.length, 2);
  assert.equal(browser.replay_focus_step.id, "trace-02");
  assert.equal(browser.replay_focus_step.title, "Hesitated");
});

test("deriveStage9EvidenceBundle produces completed run with evidence browser and replay surface", () => {
  const bundle = deriveStage9EvidenceBundle({
    evidenceState: {
      activeFilter: "all",
      selectedArtifactId: "artifact-trace",
      selectedReplayStepId: "step-03"
    },
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "evidence_browser" }
  });

  assert.equal(bundle.adapter.run_state, "completed");
  assert.equal(bundle.run_monitor.results_available, true);
  assert.equal(bundle.evidence_browser.browser_status, "results_ready");
  assert.equal(bundle.evidence_browser.selected_artifact_id, "artifact-trace");
  assert.equal(bundle.evidence_browser.replay_focus_step.id, "step-03");
  assert.ok(bundle.evidence_browser.visible_count >= 5);
});
