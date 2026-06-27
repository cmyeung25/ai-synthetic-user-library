import test from "node:test";
import assert from "node:assert/strict";

import {
  createStage11WorkspaceShellDemoState,
  deriveStage11WorkspaceShellBundle
} from "../../demo/workspace_ui_shared/workspace_ui_adapter.mjs";
import {
  createWorkspaceValidationBridgeDemoContext,
  createWorkspaceValidationBridgeDemoJob,
  deriveWorkspaceValidationBridgeState
} from "../../demo/workspace_ui_shared/workspace_runtime_bridge.mjs";
import {
  deriveWorkspaceShellFrontendAdapter
} from "../../demo/workspace_ui_shared/workspace_shell_frontend_adapter.mjs";

const copy = {
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

function buildBundle(shellOverrides = {}) {
  return deriveStage11WorkspaceShellBundle({
    shellState: {
      ...createStage11WorkspaceShellDemoState(),
      ...shellOverrides
    },
    copy,
    localUiState: {
      locale: "en",
      active_panel: "runtime_bridge"
    }
  });
}

test("frontend adapter keeps blocked draft non-submittable", () => {
  const bundle = buildBundle();
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [],
    selectedJob: null,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob: null,
    mode: "sample",
    lastApiResponse: null
  });

  assert.equal(frontend.metrics.submission_ready, false);
  assert.equal(frontend.metrics.shell_surface, "conversation_intake");
  assert.equal(frontend.actions.submit_live_job.enabled, false);
  assert.equal(frontend.adapter_summary[3].value.includes("onboarding_screenshot_set"), true);
});

test("frontend adapter exposes submission-ready confirmed draft", () => {
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "queued"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [],
    selectedJob: null,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob: null,
    mode: "sample",
    lastApiResponse: null
  });

  assert.equal(frontend.metrics.submission_ready, true);
  assert.equal(frontend.metrics.shell_surface, "run_monitor");
  assert.equal(frontend.actions.submit_live_job.enabled, true);
  assert.equal(frontend.draft_summary[2].value, "confirmed");
});

test("frontend adapter projects completed live job into review-ready shell", () => {
  const selectedJob = createWorkspaceValidationBridgeDemoJob("completed");
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "completed",
    attemptCount: 1
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [selectedJob],
    selectedJob,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob,
    mode: "live",
    lastApiResponse: { job: selectedJob }
  });

  assert.equal(frontend.metrics.selected_job_id, selectedJob.job_id);
  assert.equal(frontend.pills.job.tone, "completed");
  assert.equal(frontend.shell_projection.review_ready, true);
  assert.equal(frontend.review_summary[0].value, "query_ready");
  assert.equal(frontend.review_surface.query_status, "query_ready");
  assert.equal(frontend.review_surface.results.length >= 1, true);
  assert.equal(frontend.review_surface.selected_evidence_summary[0].id, "result_id");
});

test("frontend adapter surfaces bridge warnings without hiding the gap", () => {
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "queued"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [],
    selectedJob: null,
    apiBaseUrl: "http://127.0.0.1:8011",
    lastError: "HTTP 401"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob: null,
    mode: "live",
    lastApiResponse: { error: "HTTP 401" }
  });

  assert.equal(frontend.pills.bridge.tone, "failed");
  assert.equal(frontend.sidecar_rows[3].value, "HTTP 401");
  assert.match(frontend.bridge_gap, /replay remains limited/i);
});

test("frontend adapter can render backend review surface separately from local bundle query state", () => {
  const selectedJob = createWorkspaceValidationBridgeDemoJob("completed");
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "completed",
    attemptCount: 1
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [selectedJob],
    selectedJob,
    apiBaseUrl: "http://127.0.0.1:8011"
  });
  const reviewQueryState = {
    query_status: "query_ready",
    selected_result_id: "query-run_report",
    selected_artifact_id: "report.json",
    selected_replay_step_id: null,
    result_count: 2,
    boundary_warning: "Synthetic evidence only.",
    results: [
      {
        id: "query-run_report",
        artifact_id: "report.json",
        title: "Run report",
        family: "output",
        kind: "report",
        artifact_path: "runs/demo/report.json",
        summary: "Final synthetic evidence package.",
        relevance_score: 3
      },
      {
        id: "query-raw_responses",
        artifact_id: "raw_responses.json",
        title: "Raw responses",
        family: "trace",
        kind: "raw_responses",
        artifact_path: "runs/demo/raw_responses.json",
        summary: "Persona-level raw response payloads.",
        relevance_score: 1
      }
    ],
    selected_result: {
      id: "query-run_report",
      artifact_id: "report.json",
      title: "Run report",
      family: "output",
      kind: "report",
      artifact_path: "runs/demo/report.json",
      summary: "Final synthetic evidence package."
    },
    linked_artifact: {
      id: "report.json",
      title: "Run report",
      artifact_path: "runs/demo/report.json",
      summary: "Final synthetic evidence package.",
      detail_lines: [
        "Continuation risk remains medium until value becomes explicit."
      ]
    },
    replay_sequence: []
  };

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob,
    mode: "live",
    lastApiResponse: { query: reviewQueryState },
    reviewQueryState,
    querySource: "backend"
  });

  assert.equal(frontend.review_summary[3].value, "backend evidence endpoint");
  assert.equal(frontend.review_surface.query_source, "backend");
  assert.equal(frontend.review_surface.empty_note, "2 results from backend evidence endpoint.");
  assert.equal(frontend.review_surface.results[0].selected, true);
  assert.equal(frontend.review_surface.selected_evidence_detail[1].body.includes("Continuation risk"), true);
  assert.equal(frontend.review_surface.replay_note, "No replay-linked steps are available for the current selection.");
  assert.equal(frontend.actions.load_live_evidence_query.enabled, true);
  assert.equal(frontend.actions.apply_evidence_query.enabled, true);
});
