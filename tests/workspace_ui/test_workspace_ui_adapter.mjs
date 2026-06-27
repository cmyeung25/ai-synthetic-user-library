import test from "node:test";
import assert from "node:assert/strict";

import {
  createStage7DemoState,
  deriveStage7DemoBundle,
  deriveWorkspaceUiState
} from "../../demo/workspace_ui_shared/workspace_ui_adapter.mjs";

function makeConversationState() {
  return {
    workspace_id: "ws_hk_ops",
    thread_id: "thread_workspace_new_study",
    latest_user_intent: "Where do new operators hesitate during onboarding, and do they continue after the first task?",
    artifact_refs: ["founder-brief.json", "homepage-copy.md"],
    clarification_answers: {},
    selected_fallback: null
  };
}

function makeDraftPlan(overrides = {}) {
  return {
    status: "blocked",
    inference: {
      primary_mode: "prototype_validation",
      secondary_lenses: ["onboarding_friction"]
    },
    proposed_run: {
      execution_status: "blocked",
      first_task: null
    },
    evidence_boundary: {
      allowed_evidence: ["message_interpretation"],
      forbidden_claims: ["task_friction"],
      boundary_note: "Prototype evidence still needs stronger artifacts."
    },
    remediation: {
      blocking_reasons: ["missing_prototype_artifacts", "missing_first_task_anchor"],
      missing_inputs: ["first_task_name"],
      required_artifacts: ["onboarding_screenshot_set"],
      fallback_options: ["downgrade_to_concept_review", "save_blocked_draft"],
      recommended_next_action: {
        action_type: "request_artifact_upload_and_clarification",
        label: "request_screenshots_and_task_anchor"
      }
    },
    confirmation: {
      required: true,
      status: "pending",
      blocking_reasons: ["missing_prototype_artifacts", "missing_first_task_anchor"]
    },
    audit: {},
    ...overrides
  };
}

function makeCopy() {
  return {
    questionValue: "Where do new operators hesitate during onboarding, and do they continue after the first task?",
    desiredValue: "task-friction and continuation risk",
    nextUpload: "request inputs",
    nextFallback: "confirm fallback",
    nextConfirm: "confirm queueable plan",
    nextSaved: "resume later",
    phaseQueued: "queued"
  };
}

test("deriveWorkspaceUiState returns blocked contract output when inputs are missing", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: makeConversationState(),
    draftPlan: makeDraftPlan(),
    localUiState: { locale: "en", active_panel: "default" }
  });

  assert.equal(adapter.ui_phase, "blocked");
  assert.equal(adapter.run_state, "draft");
  assert.deepEqual(adapter.visible_blockers, ["missing_prototype_artifacts", "missing_first_task_anchor"]);
  assert.deepEqual(adapter.visible_waiting_for, ["onboarding_screenshot_set", "first_task_name"]);
  assert.deepEqual(adapter.primary_button, {
    label: "request_screenshots_and_task_anchor",
    action_type: "request_artifact_upload_and_clarification",
    enabled: true
  });
  assert.deepEqual(adapter.secondary_button, {
    label: "save_blocked_draft",
    action_type: "save_blocked_draft",
    enabled: true
  });
});

test("deriveWorkspaceUiState returns ready_for_confirmation for queueable prototype path", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: makeConversationState(),
    draftPlan: makeDraftPlan({
      status: "ready_for_confirmation",
      proposed_run: {
        execution_status: "queueable_prototype_subset",
        first_task: "connect data"
      },
      remediation: {
        blocking_reasons: [],
        missing_inputs: [],
        required_artifacts: [],
        fallback_options: ["save_blocked_draft"],
        recommended_next_action: {
          action_type: "confirm_queueable_plan",
          label: "confirm queueable plan"
        }
      },
      confirmation: {
        required: true,
        status: "pending",
        blocking_reasons: []
      }
    }),
    localUiState: { locale: "en" }
  });

  assert.equal(adapter.ui_phase, "ready_for_confirmation");
  assert.equal(adapter.run_state, "draft");
  assert.deepEqual(adapter.visible_waiting_for, ["final_confirmation"]);
  assert.equal(adapter.primary_button.action_type, "confirm_queueable_plan");
  assert.equal(adapter.summary_view.first_task, "connect data");
});

test("deriveWorkspaceUiState returns ready_for_confirmation for fallback path", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: {
      ...makeConversationState(),
      selected_fallback: "concept_evaluation"
    },
    draftPlan: makeDraftPlan({
      status: "ready_for_confirmation",
      inference: {
        primary_mode: "concept_evaluation",
        secondary_lenses: ["adoption_barrier_validation"]
      },
      proposed_run: {
        execution_status: "queueable_fallback",
        first_task: null
      },
      remediation: {
        blocking_reasons: [],
        missing_inputs: [],
        required_artifacts: [],
        fallback_options: ["save_blocked_draft"],
        recommended_next_action: {
          action_type: "confirm_fallback_mode",
          label: "confirm fallback"
        }
      },
      confirmation: {
        required: true,
        status: "pending",
        blocking_reasons: []
      }
    }),
    localUiState: { locale: "en" }
  });

  assert.equal(adapter.ui_phase, "ready_for_confirmation");
  assert.equal(adapter.primary_button.action_type, "confirm_fallback_mode");
  assert.equal(adapter.summary_view.primary_mode, "concept_evaluation");
});

test("deriveWorkspaceUiState returns blocked_saved when draft is preserved for later", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: makeConversationState(),
    draftPlan: makeDraftPlan({
      remediation: {
        blocking_reasons: ["missing_prototype_artifacts"],
        missing_inputs: ["first_task_name"],
        required_artifacts: ["onboarding_screenshot_set"],
        fallback_options: ["save_blocked_draft"],
        recommended_next_action: {
          action_type: "resume_blocked_draft",
          label: "resume later"
        },
        saved_for_later: true
      },
      confirmation: {
        required: true,
        status: "saved_for_later",
        blocking_reasons: ["missing_prototype_artifacts"]
      },
      audit: {
        saved_for_later: true
      }
    }),
    localUiState: { locale: "en" }
  });

  assert.equal(adapter.ui_phase, "blocked_saved");
  assert.deepEqual(adapter.visible_waiting_for, ["onboarding_screenshot_set", "first_task_name", "later_resume"]);
  assert.equal(adapter.primary_button.action_type, "resume_blocked_draft");
});

test("deriveWorkspaceUiState returns queued for confirmed path", () => {
  const adapter = deriveWorkspaceUiState({
    conversationState: makeConversationState(),
    draftPlan: makeDraftPlan({
      status: "confirmed",
      proposed_run: {
        execution_status: "queued",
        first_task: "connect data"
      },
      remediation: {
        blocking_reasons: [],
        missing_inputs: [],
        required_artifacts: [],
        fallback_options: [],
        recommended_next_action: {
          action_type: "await_run",
          label: "queued"
        }
      },
      confirmation: {
        required: true,
        status: "confirmed",
        blocking_reasons: []
      }
    }),
    localUiState: { locale: "en" }
  });

  assert.equal(adapter.ui_phase, "queued");
  assert.equal(adapter.run_state, "queued");
  assert.deepEqual(adapter.visible_waiting_for, ["worker_execution"]);
  assert.deepEqual(adapter.primary_button, {
    label: "queued",
    action_type: "await_run",
    enabled: true
  });
});

test("deriveStage7DemoBundle produces a queueable prototype demo state after supplementing inputs", () => {
  const demoState = createStage7DemoState();
  demoState.hasScreenshots = true;
  demoState.firstTask = "connect data";

  const bundle = deriveStage7DemoBundle({
    demoState,
    copy: makeCopy(),
    localUiState: { locale: "en", active_panel: "default" }
  });

  assert.equal(bundle.adapter.ui_phase, "ready_for_confirmation");
  assert.equal(bundle.draft.proposed_run.execution_status, "queueable_prototype_subset");
  assert.deepEqual(bundle.adapter.visible_waiting_for, ["final_confirmation"]);
});
