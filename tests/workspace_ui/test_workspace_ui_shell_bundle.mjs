import test from "node:test";
import assert from "node:assert/strict";

import {
  createStage11WorkspaceShellDemoState,
  deriveStage11WorkspaceShellBundle
} from "../../demo/workspace_ui_shared/workspace_ui_adapter.mjs";

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

test("deriveStage11WorkspaceShellBundle starts in blocked intake state", () => {
  const bundle = deriveStage11WorkspaceShellBundle({
    shellState: createStage11WorkspaceShellDemoState(),
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "workspace_shell" }
  });

  assert.equal(bundle.adapter.ui_phase, "blocked");
  assert.equal(bundle.run_monitor.status, "ready_to_queue");
  assert.equal(bundle.evidence_query.query_status, "query_pending");
  assert.equal(bundle.workspace_shell.active_surface, "conversation_intake");
  assert.equal(bundle.workspace_shell.stage_strip[0].state, "active");
});

test("deriveStage11WorkspaceShellBundle moves into confirmation when prototype inputs are complete", () => {
  const state = createStage11WorkspaceShellDemoState();
  state.hasScreenshots = true;
  state.firstTask = "connect data";

  const bundle = deriveStage11WorkspaceShellBundle({
    shellState: state,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "workspace_shell" }
  });

  assert.equal(bundle.adapter.ui_phase, "ready_for_confirmation");
  assert.equal(bundle.workspace_shell.active_surface, "confirmation");
  assert.equal(bundle.workspace_shell.stage_strip[1].state, "active");
  assert.deepEqual(bundle.adapter.visible_waiting_for, ["final_confirmation"]);
});

test("deriveStage11WorkspaceShellBundle keeps advanced study controls behind the same confirmation flow", () => {
  const state = createStage11WorkspaceShellDemoState();
  state.hasScreenshots = true;
  state.firstTask = "connect data";
  state.modeOverride = "concept_validation";
  state.panelType = "skeptic";
  state.sampleSize = 3;
  state.providerName = "codex";
  state.personaFilters = {
    location_type: "urban_core",
    privacy_concern: "high"
  };

  const bundle = deriveStage11WorkspaceShellBundle({
    shellState: state,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "workspace_shell" }
  });

  assert.equal(bundle.adapter.ui_phase, "ready_for_confirmation");
  assert.equal(bundle.draft.inference.primary_mode, "concept_validation");
  assert.equal(bundle.draft.proposed_run.panel_type, "skeptic");
  assert.equal(bundle.draft.proposed_run.sample_size, 3);
  assert.equal(bundle.draft.proposed_run.provider_name, "codex");
  assert.deepEqual(bundle.draft.proposed_run.persona_filters, {
    location_type: "urban_core",
    privacy_concern: "high"
  });
  assert.equal(bundle.draft.advanced_controls.summary.filters, "location_type=urban_core, privacy_concern=high");
  assert.equal(bundle.workspace_shell.conversation_feed[2].title, "Advanced study controls");
});

test("deriveStage11WorkspaceShellBundle unlocks evidence query after completion", () => {
  const state = createStage11WorkspaceShellDemoState();
  state.hasScreenshots = true;
  state.firstTask = "connect data";
  state.lifecycle = "completed";
  state.attemptCount = 1;

  const bundle = deriveStage11WorkspaceShellBundle({
    shellState: state,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "workspace_shell" }
  });

  assert.equal(bundle.adapter.run_state, "completed");
  assert.equal(bundle.run_monitor.status, "completed");
  assert.equal(bundle.evidence_browser.browser_status, "results_ready");
  assert.equal(bundle.evidence_query.query_status, "query_ready");
  assert.equal(bundle.workspace_shell.active_surface, "evidence_query");
  assert.ok(bundle.evidence_query.result_count >= 1);
});

test("deriveStage11WorkspaceShellBundle keeps review blocked when the run fails", () => {
  const state = createStage11WorkspaceShellDemoState();
  state.hasScreenshots = true;
  state.firstTask = "connect data";
  state.lifecycle = "failed";
  state.attemptCount = 1;
  state.failureReason = "stimulus render timeout before trace packaging";

  const bundle = deriveStage11WorkspaceShellBundle({
    shellState: state,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "workspace_shell" }
  });

  assert.equal(bundle.run_monitor.status, "failed");
  assert.equal(bundle.evidence_browser.browser_status, "results_pending");
  assert.equal(bundle.evidence_query.query_status, "query_pending");
  assert.equal(bundle.workspace_shell.active_surface, "failure_visibility");
  assert.equal(bundle.workspace_shell.stage_strip[2].state, "blocked");
  assert.equal(bundle.workspace_shell.stage_strip[3].state, "blocked");
});
