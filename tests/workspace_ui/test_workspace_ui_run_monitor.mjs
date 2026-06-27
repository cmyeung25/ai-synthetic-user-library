import test from "node:test";
import assert from "node:assert/strict";

import {
  createStage8MonitorDemoState,
  deriveStage8MonitorBundle,
  deriveWorkspaceRunMonitorState,
  deriveWorkspaceUiState
} from "../../demo/workspace_ui_shared/workspace_ui_adapter.mjs";

function makeDraftPlan(executionStatus = "queued") {
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
      boundary_note: "Prototype path stays bounded."
    },
    remediation: {
      blocking_reasons: [],
      missing_inputs: [],
      required_artifacts: [],
      fallback_options: [],
      recommended_next_action: {
        action_type: executionStatus === "failed" ? "inspect_failure" : "await_run",
        label: executionStatus === "failed" ? "inspect failure" : "await run"
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

test("deriveWorkspaceRunMonitorState returns queue monitor for queued run", () => {
  const monitor = deriveWorkspaceRunMonitorState({
    draftPlan: makeDraftPlan("queued"),
    runRecord: {
      status: "queued",
      queue_position: 1,
      attempt_count: 1,
      last_event_at: "22:14"
    },
    localUiState: { locale: "en" }
  });

  assert.equal(monitor.status, "queued");
  assert.equal(monitor.monitor_phase, "worker_wait");
  assert.equal(monitor.primary_action_type, "lease_worker");
  assert.equal(monitor.timeline[0].state, "active");
});

test("deriveWorkspaceRunMonitorState returns running monitor for active worker", () => {
  const monitor = deriveWorkspaceRunMonitorState({
    draftPlan: makeDraftPlan("running"),
    runRecord: {
      status: "running",
      queue_position: 1,
      worker_id: "worker-hkg-02",
      current_step: "persona_panel_execution",
      attempt_count: 1,
      last_event_at: "22:16"
    },
    localUiState: { locale: "en" }
  });

  assert.equal(monitor.status, "running");
  assert.equal(monitor.monitor_phase, "worker_active");
  assert.equal(monitor.primary_action_type, "complete_run");
  assert.equal(monitor.secondary_action_type, "fail_run");
  assert.equal(monitor.timeline[2].state, "active");
});

test("deriveWorkspaceRunMonitorState returns completed monitor with artifacts", () => {
  const monitor = deriveWorkspaceRunMonitorState({
    draftPlan: makeDraftPlan("completed"),
    runRecord: {
      status: "completed",
      queue_position: 1,
      worker_id: "worker-hkg-02",
      current_step: "report_packaging",
      attempt_count: 1,
      last_event_at: "22:19",
      artifact_refs: ["runs/job_workspace_proto_008/report.json"]
    },
    localUiState: { locale: "en" }
  });

  assert.equal(monitor.status, "completed");
  assert.equal(monitor.monitor_phase, "results_ready");
  assert.equal(monitor.results_available, true);
  assert.equal(monitor.primary_action_type, "view_results");
  assert.equal(monitor.timeline.at(-1).state, "done");
});

test("deriveWorkspaceRunMonitorState returns failed monitor with retry path", () => {
  const monitor = deriveWorkspaceRunMonitorState({
    draftPlan: makeDraftPlan("failed"),
    runRecord: {
      status: "failed",
      queue_position: 1,
      worker_id: "worker-hkg-02",
      current_step: "stimulus_render",
      attempt_count: 2,
      last_event_at: "22:21",
      failure_reason: "stimulus_capture_timeout"
    },
    localUiState: { locale: "en" }
  });

  assert.equal(monitor.status, "failed");
  assert.equal(monitor.monitor_phase, "retry_required");
  assert.equal(monitor.retry_available, true);
  assert.equal(monitor.secondary_action_type, "retry_run");
  assert.equal(monitor.failure_reason, "stimulus_capture_timeout");
});

test("deriveWorkspaceUiState keeps post-queue completed path in queued ui phase while exposing completed run state", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: {
      workspace_id: "ws_hk_ops",
      thread_id: "thread_workspace_new_study"
    },
    draftPlan: {
      ...makeDraftPlan("completed"),
      remediation: {
        blocking_reasons: [],
        missing_inputs: [],
        required_artifacts: [],
        fallback_options: [],
        recommended_next_action: {
          action_type: "view_results",
          label: "view results"
        }
      }
    },
    localUiState: { locale: "en" }
  });

  assert.equal(adapter.ui_phase, "queued");
  assert.equal(adapter.run_state, "completed");
  assert.equal(adapter.primary_button.action_type, "view_results");
  assert.deepEqual(adapter.visible_waiting_for, ["results_review"]);
});

test("deriveStage8MonitorBundle returns failed run record with retry-ready monitor state", () => {
  const monitorState = createStage8MonitorDemoState();
  monitorState.lifecycle = "failed";
  monitorState.attemptCount = 2;
  monitorState.failureReason = "stimulus_capture_timeout";
  monitorState.events = [{ type: "fail", at: "22:21" }];

  const bundle = deriveStage8MonitorBundle({
    monitorState,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "default" }
  });

  assert.equal(bundle.draft.proposed_run.execution_status, "failed");
  assert.equal(bundle.adapter.run_state, "failed");
  assert.equal(bundle.run_monitor.retry_available, true);
  assert.equal(bundle.run_monitor.secondary_action_type, "retry_run");
});
