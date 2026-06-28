import test from "node:test";
import assert from "node:assert/strict";

import {
  buildValidationJobRequestFromDraftPlan,
  canSubmitValidationJobFromDraftPlan,
  createWorkspaceValidationBridgeDemoContext,
  createWorkspaceValidationBridgeDemoJob,
  deriveRunRecordFromValidationJob,
  deriveWorkspaceValidationBridgeState
} from "../../demo/workspace_ui_shared/workspace_runtime_bridge.mjs";

function makeDraftPlan(overrides = {}) {
  return {
    draft_plan_id: "draft_plan_20260627_proto_07",
    workspace_id: "ws_api_demo",
    status: "confirmed",
    source_intent: {
      user_text: "Where do new operators hesitate during onboarding, and do they continue after the first task?"
    },
    inference: {
      primary_mode: "prototype_validation"
    },
    proposed_run: {
      first_task: "connect data",
      provider_name: "mock"
    },
    evidence_boundary: {
      boundary_note: "Synthetic evidence remains bounded by the prototype-validation contract."
    },
    remediation: {
      blocking_reasons: []
    },
    confirmation: {
      status: "confirmed"
    },
    ...overrides
  };
}

test("buildValidationJobRequestFromDraftPlan maps draft plan into validation-job payload", () => {
  const payload = buildValidationJobRequestFromDraftPlan({
    draftPlan: makeDraftPlan(),
    workspaceContext: createWorkspaceValidationBridgeDemoContext()
  });

  assert.equal(payload.brief_path, "briefs/brief.json");
  assert.equal(payload.persona_dir, "personas");
  assert.equal(payload.panel_spec.panel_type, "mainstream");
  assert.equal(payload.panel_spec.sample_size, 5);
  assert.equal(payload.provider_name, "mock");
  assert.equal(payload.metadata.project_id, null);
  assert.equal(payload.metadata.study_id, null);
  assert.equal(payload.metadata.primary_mode, "prototype_validation");
  assert.equal(payload.metadata.first_task, "connect data");
  assert.deepEqual(payload.panel_spec.filters, {});
});

test("buildValidationJobRequestFromDraftPlan carries advanced study controls into the request payload", () => {
  const payload = buildValidationJobRequestFromDraftPlan({
    draftPlan: makeDraftPlan({
      inference: {
        primary_mode: "concept_validation"
      },
      proposed_run: {
        first_task: "connect data",
        provider_name: "codex",
        panel_type: "skeptic",
        sample_size: 3,
        mode_override: "concept_validation",
        persona_filters: {
          location_type: "urban_core",
          privacy_concern: "high"
        }
      }
    }),
    workspaceContext: {
      workspace_id: "ws_api_demo",
      project_id: "project_001",
      study_id: "study_001",
      brief_path: "briefs/custom.json",
      persona_dir: "personas_v2",
      run_root: "runs/review"
    }
  });

  assert.equal(payload.brief_path, "briefs/custom.json");
  assert.equal(payload.persona_dir, "personas_v2");
  assert.equal(payload.panel_spec.panel_type, "skeptic");
  assert.equal(payload.panel_spec.sample_size, 3);
  assert.deepEqual(payload.panel_spec.filters, {
    location_type: "urban_core",
    privacy_concern: "high"
  });
  assert.equal(payload.provider_name, "codex");
  assert.equal(payload.run_root, "runs/review");
  assert.equal(payload.metadata.project_id, "project_001");
  assert.equal(payload.metadata.study_id, "study_001");
  assert.equal(payload.metadata.primary_mode, "concept_validation");
  assert.equal(payload.metadata.mode_override, "concept_validation");
  assert.equal(payload.metadata.persona_filter_summary, "location_type=urban_core, privacy_concern=high");
});

test("canSubmitValidationJobFromDraftPlan requires confirmed and unblocked draft", () => {
  assert.equal(canSubmitValidationJobFromDraftPlan(makeDraftPlan()), true);
  assert.equal(
    canSubmitValidationJobFromDraftPlan(
      makeDraftPlan({
        confirmation: { status: "pending" }
      })
    ),
    false
  );
  assert.equal(
    canSubmitValidationJobFromDraftPlan(
      makeDraftPlan({
        remediation: { blocking_reasons: ["missing_prototype_artifacts"] }
      })
    ),
    false
  );
});

test("deriveRunRecordFromValidationJob maps completed job into shell run record", () => {
  const runRecord = deriveRunRecordFromValidationJob(
    createWorkspaceValidationBridgeDemoJob("completed")
  );

  assert.equal(runRecord.status, "completed");
  assert.equal(runRecord.current_step, "report_packaging");
  assert.equal(runRecord.artifact_refs.length, 3);
  assert.equal(runRecord.failure_reason, null);
});

test("deriveRunRecordFromValidationJob maps failed job into retry-visible record", () => {
  const runRecord = deriveRunRecordFromValidationJob(
    createWorkspaceValidationBridgeDemoJob("failed")
  );

  assert.equal(runRecord.status, "failed");
  assert.equal(runRecord.failure_reason, "stimulus render timeout before trace packaging");
  assert.equal(runRecord.attempt_count, 1);
});

test("deriveWorkspaceValidationBridgeState exposes request, endpoints, and selected job summary", () => {
  const selectedJob = createWorkspaceValidationBridgeDemoJob("queued");
  const bridge = deriveWorkspaceValidationBridgeState({
    draftPlan: makeDraftPlan(),
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    jobList: [selectedJob],
    selectedJob,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  assert.equal(bridge.bridge_status, "job_loaded");
  assert.equal(bridge.submission_ready, true);
  assert.equal(bridge.job_count, 1);
  assert.equal(bridge.selected_job_status, "queued");
  assert.equal(bridge.derived_run_record.status, "queued");
  assert.equal(bridge.endpoint_summary.submit, "POST /api/v1/validation-jobs");
  assert.equal(bridge.endpoint_summary.query, "GET /api/v1/evidence-query");
});
