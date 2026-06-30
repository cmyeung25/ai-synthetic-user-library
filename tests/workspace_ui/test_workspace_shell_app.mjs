import test from "node:test";
import assert from "node:assert/strict";

import {
  createWorkspaceShellAppController,
  createWorkspaceShellAppState,
  deriveWorkspaceShellAppModel
} from "../../demo/workspace_ui_shared/workspace_shell_app.mjs";

function fakeResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    }
  };
}

test("deriveWorkspaceShellAppModel exposes draft-only shell by default", () => {
  const model = deriveWorkspaceShellAppModel({
    state: createWorkspaceShellAppState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });

  assert.equal(model.frontendState.metrics.bridge_status, "draft_only");
  assert.equal(model.frontendState.metrics.submission_ready, false);
  assert.equal(model.sessionBridgeState.session_status, "session_unloaded");
  assert.equal(model.runtimeSyncView.pill.label, "idle");
});

test("controller applies confirmed draft scenario and enables submission", () => {
  const controller = createWorkspaceShellAppController();
  controller.applyDraftScenario("confirmed_draft");
  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });

  assert.equal(model.frontendState.metrics.submission_ready, true);
  assert.equal(model.frontendState.metrics.shell_surface, "run_monitor");
  assert.equal(model.frontendState.actions.submit_live_job.enabled, true);
});

test("controller updates intake inputs and moves into confirmation through shared draft actions", () => {
  const controller = createWorkspaceShellAppController();

  controller.updateDraftInput({
    researchIntent: "Can a new operator understand the permissions step before connecting data?",
    desiredOutcome: "clarity and trust blockers",
    firstTask: "connect CRM"
  });
  controller.togglePrototypeArtifacts();

  let model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });

  assert.equal(model.bundle.conversation.latest_user_intent.includes("permissions step"), true);
  assert.equal(model.bundle.draft.source_intent.requested_outcome, "clarity and trust blockers");
  assert.equal(model.bundle.adapter.ui_phase, "ready_for_confirmation");

  controller.confirmDraftPlan({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });
  model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });

  assert.equal(model.bundle.draft.confirmation.status, "confirmed");
  assert.equal(model.frontendState.metrics.submission_ready, true);
  assert.equal(model.bundle.workspace_shell.active_surface, "run_monitor");
});

test("deriveWorkspaceShellAppModel projects advanced controls into draft and request summaries", () => {
  const controller = createWorkspaceShellAppController();

  controller.updateDraftInput({
    researchIntent: "Should the first pass stay concept-level until trust is clearer?",
    desiredOutcome: "clarity and trust blockers",
    firstTask: "connect CRM"
  });
  controller.togglePrototypeArtifacts();

  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/custom.json",
    personaDir: "personas_v2",
    runRoot: "runs/review",
    modeOverride: "concept_validation",
    panelType: "skeptic",
    sampleSize: 3,
    providerName: "codex",
    personaFilters: {
      location_type: "urban_core",
      privacy_concern: "high"
    }
  });

  assert.equal(model.bundle.draft.inference.primary_mode, "concept_validation");
  assert.equal(model.bundle.draft.proposed_run.panel_type, "skeptic");
  assert.equal(model.bridgeState.request_payload.panel_spec.sample_size, 3);
  assert.deepEqual(model.bridgeState.request_payload.panel_spec.filters, {
    location_type: "urban_core",
    privacy_concern: "high"
  });
  assert.equal(model.frontendState.request_summary[4].value, "location_type=urban_core, privacy_concern=high");
  assert.equal(model.frontendState.draft_summary[3].value, "concept_validation");
});

test("deriveWorkspaceShellAppModel infers discovery mode from plain-language pain research intent", () => {
  const controller = createWorkspaceShellAppController();

  controller.updateDraftInput({
    researchIntent: "Explore recurring product-discovery pain, root causes, workaround behavior, workflow fragmentation, and insight opportunities.",
    desiredOutcome: "pain, empathy, root-cause, workflow, and insight discovery",
    firstTask: "describe a recent product-discovery workflow breakdown"
  });
  controller.toggleFallbackMode();

  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    providerName: "codex",
    sampleSize: 1
  });

  assert.equal(model.bundle.draft.inference.primary_mode, "pain_point_discovery");
  assert.equal(model.bridgeState.request_payload.metadata.primary_mode, "pain_point_discovery");
  assert.equal(model.bridgeState.request_payload.metadata.mode_override, null);
  assert.deepEqual(model.bundle.draft.evidence_boundary.allowed_evidence, [
    "pain_reality",
    "root_cause",
    "workaround_behavior",
    "workflow_fragmentation",
    "human_validation_gap"
  ]);
});

test("controller stores selected prototype artifact names in the shared draft state", () => {
  const controller = createWorkspaceShellAppController();

  controller.setPrototypeArtifacts(["screen-01.png", "screen-02.png"]);
  controller.updateDraftInput({ firstTask: "connect CRM" });

  const model = controller.deriveModel();
  const selectedProject = model.frontendState.product_surface.projects.find((project) => project.project_id === "project_001");
  const selectedStudy = model.frontendState.product_surface.studies.find((study) => study.study_id === "study_001");

  assert.equal(model.state.shellState.hasScreenshots, true);
  assert.deepEqual(model.state.shellState.attachedArtifacts, ["screen-01.png", "screen-02.png"]);
  assert.equal(model.bundle.conversation.artifact_refs.includes("screen-01.png"), true);
  assert.equal(model.bundle.conversation.artifact_refs.includes("screen-02.png"), true);
});

test("controller can create and select project, study, export, and share product objects", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      if (url.endsWith("/api/v1/projects") && (options.method || "GET") === "GET") {
        return fakeResponse(200, {
          projects: [
            { project_id: "project_001", name: "Inbox Coach Launch", slug: "inbox-coach-launch", study_count: 1 }
          ]
        });
      }
      if (url.endsWith("/api/v1/projects") && options.method === "POST") {
        return fakeResponse(201, {
          project: { project_id: "project_002", name: "Ops Console", slug: "ops-console", study_count: 0 }
        });
      }
      if (url.includes("/api/v1/studies?project_id=project_001")) {
        return fakeResponse(200, {
          studies: [
            { study_id: "study_001", project_id: "project_001", title: "Onboarding hesitation", status: "review_ready", run_count: 1, latest_job_status: "completed" }
          ]
        });
      }
      if (url.endsWith("/api/v1/studies") && options.method === "POST") {
        return fakeResponse(201, {
          study: { study_id: "study_002", project_id: "project_001", title: "Permissions study", status: "draft", run_count: 0, latest_job_status: null }
        });
      }
      if (url.includes("/api/v1/export-bundles?study_id=study_001")) {
        return fakeResponse(200, {
          export_bundles: [
            { export_bundle_id: "export_001", study_id: "study_001", job_id: "job_001", title: "Exec review export", status: "published", export_format: "report_csv", exported_file_count: 1, synthetic_boundary: "Synthetic evidence only." }
          ]
        });
      }
      if (url.endsWith("/api/v1/export-bundles") && options.method === "POST") {
        return fakeResponse(201, {
          export_bundle: { export_bundle_id: "export_002", study_id: "study_001", job_id: "job_001", title: "Board export", status: "published", export_format: "report_json", exported_file_count: 1, synthetic_boundary: "Synthetic evidence only." }
        });
      }
      if (url.includes("/api/v1/share-bundles?") && url.includes("export_bundle_id=export_001")) {
        return fakeResponse(200, {
          share_bundles: [
            { share_bundle_id: "share_001", export_bundle_id: "export_001", study_id: "study_001", title: "Board share", status: "published", public_path: "/public/v1/share-bundles/shk_001", share_file_count: 2, synthetic_boundary: "Synthetic evidence only." }
          ]
        });
      }
      if (url.endsWith("/api/v1/share-bundles") && options.method === "POST") {
        return fakeResponse(201, {
          share_bundle: { share_bundle_id: "share_002", export_bundle_id: "export_001", study_id: "study_001", title: "Fresh share", status: "published", public_path: "/public/v1/share-bundles/shk_002", share_file_count: 2, synthetic_boundary: "Synthetic evidence only." }
        });
      }
      if (url.endsWith("/api/v1/share-bundles/share_001/revoke") && options.method === "POST") {
        return fakeResponse(200, {
          share_bundle: { share_bundle_id: "share_001", export_bundle_id: "export_001", study_id: "study_001", title: "Board share", status: "revoked", public_path: "/public/v1/share-bundles/shk_001", share_file_count: 2, synthetic_boundary: "Synthetic evidence only." }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  await controller.loadProjects({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api"
  });
  await controller.createProject({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { name: "Ops Console", slug: "ops-console" }
  });
  controller.selectProject("project_001");
  await controller.loadStudies({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    projectId: "project_001"
  });
  await controller.createStudy({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { project_id: "project_001", title: "Permissions study" }
  });
  controller.selectStudy("study_001");
  await controller.loadExportBundles({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001"
  });
  await controller.createExportBundle({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { study_id: "study_001", job_id: "job_001", export_format: "report_json" }
  });
  controller.selectExportBundle("export_001");
  await controller.loadShareBundles({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    exportBundleId: "export_001"
  });
  await controller.createShareBundle({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { export_bundle_id: "export_001", title: "Fresh share", expires_in_days: 7 }
  });
  controller.selectShareBundle("share_001");
  await controller.revokeShareBundle({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    shareBundleId: "share_001"
  });

  const model = controller.deriveModel();
  const selectedProject = model.frontendState.product_surface.projects.find((project) => project.project_id === "project_001");
  const selectedStudy = model.frontendState.product_surface.studies.find((study) => study.study_id === "study_001");
  const selectedExportBundle = model.frontendState.product_surface.export_bundles.find((exportBundle) => exportBundle.export_bundle_id === "export_001");
  const selectedShareBundle = model.frontendState.product_surface.share_bundles.find((shareBundle) => shareBundle.share_bundle_id === "share_001");

  assert.equal(model.state.liveProjects.length, 2);
  assert.equal(model.state.selectedProjectId, "project_001");
  assert.equal(model.state.liveStudies.length, 2);
  assert.equal(model.state.selectedStudyId, "study_001");
  assert.equal(model.state.liveExportBundles.length, 2);
  assert.equal(model.state.selectedExportBundleId, "export_001");
  assert.equal(model.state.liveShareBundles.length, 2);
  assert.equal(model.state.selectedShareBundleId, "share_001");
  assert.equal(selectedProject?.selected, true);
  assert.equal(selectedStudy?.selected, true);
  assert.equal(selectedExportBundle?.selected, true);
  assert.equal(selectedShareBundle?.selected, true);
  assert.equal(selectedShareBundle?.status, "revoked");
});

test("controller can load, create, and select study collaboration objects", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      if (url === "http://127.0.0.1:8011/api/v1/studies/study_001/activity?limit=20") {
        return fakeResponse(200, {
          study_activity: {
            project_id: "project_001",
            study_id: "study_001",
            activity_events: [
              {
                activity_id: "activity_001",
                action: "study.created",
                event_family: "study",
                headline: "Study created",
                summary: "Onboarding hesitation was created.",
                actor_user_id: "owner_api",
                created_at: "2026-06-28T00:10:00Z",
                route_kind: "study",
                route_id: "study_001"
              },
              {
                activity_id: "activity_002",
                action: "evidence_view.saved",
                event_family: "collaboration",
                headline: "Saved evidence view",
                summary: "Trust blockers review was saved.",
                actor_user_id: "owner_api",
                created_at: "2026-06-28T00:12:00Z",
                route_kind: "evidence_view",
                route_id: "view_001"
              }
            ]
          }
        });
      }
      if (url.includes("/api/v1/evidence-views?") && url.includes("study_id=study_001")) {
        return fakeResponse(200, {
          evidence_views: [
            {
              evidence_view_id: "view_001",
              project_id: "project_001",
              study_id: "study_001",
              job_id: "job_001",
              title: "Trust blockers review",
              note: "Focus on output evidence first",
              query_text: "trust",
              active_family: "output",
              sort_by: "relevance"
            }
          ]
        });
      }
      if (url.endsWith("/api/v1/evidence-views") && options.method === "POST") {
        return fakeResponse(201, {
          evidence_view: {
            evidence_view_id: "view_002",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            title: "Replay focus",
            note: "Save replay-linked context",
            query_text: "hesitate",
            active_family: "trace",
            sort_by: "newest",
            selected_result_id: "query-raw_responses",
            selected_replay_step_id: "response-02"
          }
        });
      }
      if (url.endsWith("/api/v1/evidence-views/view_001")) {
        return fakeResponse(200, {
          evidence_view: {
            evidence_view_id: "view_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            title: "Trust blockers review",
            note: "Focus on output evidence first",
            query_text: "trust",
            active_family: "output",
            sort_by: "relevance",
            selected_comparison_run_id: "run_002"
          }
        });
      }
      if (url.includes("/api/v1/decision-logs?") && url.includes("study_id=study_001")) {
        return fakeResponse(200, {
          decision_logs: [
            {
              decision_log_id: "decision_001",
              project_id: "project_001",
              study_id: "study_001",
              job_id: "job_001",
              evidence_view_id: "view_001",
              title: "Do not ship yet",
              decision_summary: "Trust blockers still dominate.",
              rationale: "Observed objections repeat across personas."
            }
          ]
        });
      }
      if (url.endsWith("/api/v1/decision-logs") && options.method === "POST") {
        return fakeResponse(201, {
          decision_log: {
            decision_log_id: "decision_002",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Retry onboarding copy",
            decision_summary: "Adjust the first-run copy before another test.",
            rationale: "The same hesitation appears in replay."
          }
        });
      }
      if (url.endsWith("/api/v1/decision-logs/decision_001")) {
        return fakeResponse(200, {
          decision_log: {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas.",
            selected_comparison_run_id: "run_002"
          },
          decision_comments: []
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.getState().mode = "live";
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  controller.getState().selectedJobId = "job_001";
  controller.getState().liveJobs = [
    { job_id: "job_001", status: "completed", provider_name: "mock" }
  ];

  await controller.loadEvidenceViews({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001"
  });
  await controller.loadStudyActivity({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001"
  });
  await controller.createEvidenceView({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { study_id: "study_001", job_id: "job_001", title: "Replay focus" }
  });
  await controller.loadEvidenceViewDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    evidenceViewId: "view_001"
  });
  controller.selectEvidenceView("view_001");
  await controller.loadDecisionLogs({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    evidenceViewId: "view_001"
  });
  await controller.createDecisionLog({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: {
      study_id: "study_001",
      job_id: "job_001",
      evidence_view_id: "view_001",
      title: "Retry onboarding copy",
      decision_summary: "Adjust the first-run copy before another test."
    }
  });
  await controller.loadDecisionLogDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001"
  });
  controller.selectDecisionLog("decision_001");

  const model = controller.deriveModel();
  assert.equal(model.state.liveEvidenceViews.length, 2);
  assert.equal(model.state.liveStudyActivity.length, 2);
  assert.equal(model.state.selectedEvidenceViewId, "view_001");
  assert.equal(model.state.liveDecisionLogs.length, 2);
  assert.equal(model.state.selectedDecisionLogId, "decision_001");
  assert.equal(model.frontendState.metrics.selected_evidence_view_id, "view_001");
  assert.equal(model.frontendState.metrics.selected_decision_log_id, "decision_001");
  assert.equal(model.frontendState.product_surface.evidence_views[0].selected, true);
  assert.equal(model.frontendState.product_surface.decision_logs[0].selected, true);
  assert.equal(model.frontendState.product_surface.study_activity[1].route_kind, "evidence_view");
  assert.equal(model.frontendState.product_surface.study_activity_summary[0].value, "2 items");
  assert.equal(model.frontendState.product_surface.selected_evidence_view_summary[0].value, "Trust blockers review");
  assert.equal(model.frontendState.product_surface.selected_decision_log_summary[0].value, "Do not ship yet");
  assert.deepEqual(model.state.liveDecisionComments, []);
});

test("controller can review a decision log with threaded comments and approval state", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      if (url.endsWith("/api/v1/decision-logs/decision_001")) {
        return fakeResponse(200, {
          decision_log: {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas.",
            review_status: "in_review",
            comment_count: 1
          },
          decision_comments: [
            {
              decision_comment_id: "decision_comment_001",
              decision_log_id: "decision_001",
              anchor_kind: "general",
              body: "Please justify why this is not one-run noise.",
              created_by_user_id: "reviewer_001",
              created_at: "2026-06-28T02:00:00+00:00",
              reply_count: 0
            }
          ]
        });
      }
      if (url.endsWith("/api/v1/decision-logs/decision_001/comments") && (options.method || "GET") === "GET") {
        return fakeResponse(200, {
          decision_log: {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas.",
            review_status: "approved",
            comment_count: 2
          },
          decision_comments: [
            {
              decision_comment_id: "decision_comment_001",
              decision_log_id: "decision_001",
              anchor_kind: "general",
              body: "Please justify why this is not one-run noise.",
              created_by_user_id: "reviewer_001",
              created_at: "2026-06-28T02:00:00+00:00",
              reply_count: 1
            },
            {
              decision_comment_id: "decision_comment_002",
              decision_log_id: "decision_001",
              parent_comment_id: "decision_comment_001",
              anchor_kind: "comparison",
              body: "The comparison run shows the same objection cluster.",
              created_by_user_id: "owner_api",
              created_at: "2026-06-28T02:05:00+00:00",
              reply_count: 0
            }
          ]
        });
      }
      if (url.endsWith("/api/v1/decision-logs/decision_001/comments") && options.method === "POST") {
        return fakeResponse(201, {
          decision_log: {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas.",
            review_status: "approved",
            comment_count: 2
          },
          decision_comment: {
            decision_comment_id: "decision_comment_002",
            decision_log_id: "decision_001",
            parent_comment_id: "decision_comment_001",
            anchor_kind: "comparison",
            body: "The comparison run shows the same objection cluster.",
            created_by_user_id: "owner_api",
            created_at: "2026-06-28T02:05:00+00:00",
            reply_count: 0
          }
        });
      }
      if (url.endsWith("/api/v1/decision-logs/decision_001/review-status") && options.method === "POST") {
        return fakeResponse(200, {
          decision_log: {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_001",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas.",
            review_status: "approved",
            latest_review_note: "Cross-run evidence is consistent enough to proceed.",
            comment_count: 1
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.getState().mode = "live";
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  controller.getState().selectedJobId = "job_001";
  controller.getState().selectedEvidenceViewId = "view_001";
  controller.getState().selectedDecisionLogId = "decision_001";
  controller.getState().liveDecisionLogs = [
    {
      decision_log_id: "decision_001",
      project_id: "project_001",
      study_id: "study_001",
      job_id: "job_001",
      evidence_view_id: "view_001",
      title: "Do not ship yet",
      decision_summary: "Trust blockers still dominate.",
      rationale: "Observed objections repeat across personas.",
      review_status: "draft",
      comment_count: 0
    }
  ];

  await controller.loadDecisionLogDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001"
  });
  await controller.updateDecisionReviewStatus({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    payload: {
      review_status: "approved",
      note: "Cross-run evidence is consistent enough to proceed."
    }
  });
  await controller.createDecisionComment({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    payload: {
      parent_comment_id: "decision_comment_001",
      anchor_kind: "comparison",
      body: "The comparison run shows the same objection cluster."
    }
  });
  await controller.loadDecisionComments({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001"
  });

  const model = controller.deriveModel();
  assert.equal(model.state.liveDecisionLogs[0].review_status, "approved");
  assert.equal(model.state.liveDecisionComments.length, 2);
  assert.equal(model.frontendState.decision_review_surface.pill.label, "approved");
  assert.equal(model.frontendState.product_surface.decision_review_comments[1].parent_comment_id, "decision_comment_001");
});

test("controller can load support diagnostics, create support snapshots, and project support state", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      if (url.includes("/api/v1/support-diagnostics?job_id=job_001")) {
        return fakeResponse(200, {
          support: {
            selected_job_id: "job_001",
            submission_gate: {
              status: "allowed",
              blocked_reason_count: 0,
              blocked_reasons: []
            },
            job_diagnostic: {
              job_id: "job_001",
              status: "failed",
              provider_name: "unknown-provider",
              failure_category: "provider_configuration",
              summary: "Unknown provider: unknown-provider",
              can_retry: true,
              artifact_deleted_at: null,
              next_actions: [
                "Inspect the failed run inputs and retry from the study surface.",
                "Check provider_name or backend configuration before retrying."
              ]
            },
            support_snapshot_count: 1
          }
        });
      }
      if (url.includes("/api/v1/support-snapshots?") && url.includes("study_id=study_001") && url.includes("job_id=job_001")) {
        return fakeResponse(200, {
          support_snapshots: [
            {
              support_snapshot_id: "support_001",
              study_id: "study_001",
              job_id: "job_001",
              title: "Provider failure snapshot",
              status: "generated",
              summary: "Unknown provider: unknown-provider",
              run_id: "run_001"
            }
          ]
        });
      }
      if (url.endsWith("/api/v1/support-snapshots") && options.method === "POST") {
        return fakeResponse(201, {
          support_snapshot: {
            support_snapshot_id: "support_002",
            study_id: "study_001",
            job_id: "job_001",
            title: "Fresh support handoff",
            status: "generated",
            summary: "Unknown provider: unknown-provider",
            run_id: "run_001"
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.getState().mode = "live";
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  controller.getState().selectedJobId = "job_001";
  controller.getState().liveJobs = [
    {
      job_id: "job_001",
      status: "failed",
      provider_name: "unknown-provider",
      last_error: "Unknown provider: unknown-provider"
    }
  ];

  await controller.loadSupportDiagnostics({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    jobId: "job_001"
  });
  await controller.loadSupportSnapshots({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    jobId: "job_001"
  });
  await controller.createSupportSnapshot({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { job_id: "job_001", title: "Fresh support handoff" }
  });
  controller.selectSupportSnapshot("support_001");

  const model = controller.deriveModel();

  assert.equal(model.state.liveSupportDiagnostics.job_diagnostic.failure_category, "provider_configuration");
  assert.equal(model.state.liveSupportSnapshots.length, 2);
  assert.equal(model.state.selectedSupportSnapshotId, "support_001");
  assert.equal(model.frontendState.metrics.selected_support_snapshot_id, "support_001");
  assert.equal(model.frontendState.product_surface.support_snapshots[0].support_snapshot_id, "support_002");
  assert.equal(model.frontendState.product_surface.support_snapshots[1].selected, true);
  assert.equal(model.frontendState.support_surface.submission_gate_summary[0].value, "allowed");
  assert.equal(model.frontendState.support_surface.job_diagnostic_summary[1].value, "provider_configuration");
  assert.equal(model.frontendState.support_surface.job_diagnostic_cards[1].body.includes("retry"), true);
});

test("controller can load workspace settings, upsert a member, issue a token, and revoke it", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      if (url.endsWith("/api/v1/workspace-settings")) {
        return fakeResponse(200, {
          workspace_settings: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial", status: "active" },
            billing_account: { status: "trialing", seat_count: 1, price_book_id: "trial", renewal_at: null },
            plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
            members: [
              { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" }
            ],
            api_tokens: [
              { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true }
            ],
            capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
            policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 }
          }
        });
      }
      if (url.endsWith("/api/v1/workspace-billing") && options.method === "POST") {
        return fakeResponse(200, {
          billing: {
            workspace: { workspace_id: "ws_api_demo", plan_tier: "pro" },
            billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
            plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
          },
          workspace_settings: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "pro", status: "active" },
            billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
            plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 },
            members: [
              { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" }
            ],
            api_tokens: [
              { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true }
            ],
            capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
            policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
          }
        });
      }
      if (url.endsWith("/api/v1/workspace-members") && options.method === "POST") {
        return fakeResponse(201, {
          member: { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" },
          workspace_settings: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial", status: "active" },
            billing_account: { status: "trialing", seat_count: 1, price_book_id: "trial", renewal_at: null },
            plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
            members: [
              { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" },
              { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" }
            ],
            api_tokens: [
              { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true }
            ],
            capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
            policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 }
          }
        });
      }
      if (url.endsWith("/api/v1/api-tokens") && options.method === "POST") {
        return fakeResponse(201, {
          api_token: {
            token: "token_abcdef123456",
            token_hint: "token_...3456",
            user_id: "researcher_001",
            role: "editor",
            issued_at: "2026-06-28T00:06:00Z",
            active: true,
            current: false
          },
          workspace_settings: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "pro", status: "active" },
            billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
            plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 },
            members: [
              { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" },
              { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" }
            ],
            api_tokens: [
              { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true },
              { token_id: "token_abcdef123456", token_hint: "token_...3456", user_id: "researcher_001", role: "editor", issued_at: "2026-06-28T00:06:00Z", active: true, current: false }
            ],
            capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
            policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
          }
        });
      }
      if (url.endsWith("/api/v1/api-tokens/token_abcdef123456/revoke") && options.method === "POST") {
        return fakeResponse(200, {
          api_token: {
            token_id: "token_abcdef123456",
            token_hint: "token_...3456",
            user_id: "researcher_001",
            role: "editor",
            issued_at: "2026-06-28T00:06:00Z",
            active: false,
            current: false
          },
          workspace_settings: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "pro", status: "active" },
            billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
            plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 },
            members: [
              { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" },
              { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" }
            ],
            api_tokens: [
              { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true },
              { token_id: "token_abcdef123456", token_hint: "token_...3456", user_id: "researcher_001", role: "editor", issued_at: "2026-06-28T00:06:00Z", active: false, current: false }
            ],
            capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
            policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
          }
        });
      }
      if (url.endsWith("/api/v1/audit-events?target_type=api_token&action_prefix=api_token.&limit=5")) {
        return fakeResponse(200, {
          audit_history: {
            filters: { target_type: "api_token", action_prefix: "api_token.", limit: 5 },
            audit_events: [
              {
                audit_event_id: "audit_001",
                workspace_id: "ws_api_demo",
                actor_user_id: "owner_api",
                actor_role: "owner",
                action: "api_token.issued",
                target_type: "api_token",
                target_id: "token_...3456",
                event_payload: { user_id: "researcher_001", role: "editor" },
                created_at: "2026-06-28T00:06:00Z"
              }
            ]
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  await controller.loadWorkspaceSettings({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api"
  });
  await controller.updateWorkspaceBilling({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: {
      plan_tier: "pro",
      billing_status: "active",
      seat_count: 4,
      renewal_at: "2026-07-31T00:00:00+00:00",
      daily_runs: 25,
      max_concurrent_jobs: 3,
      artifact_retention_days: 30
    }
  });
  await controller.upsertWorkspaceMember({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { user_id: "researcher_001", role: "editor" }
  });
  await controller.issueWorkspaceApiToken({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { user_id: "researcher_001" }
  });

  let model = controller.deriveModel();
  assert.equal(model.state.liveWorkspaceSettings.workspace.plan_tier, "pro");
  assert.equal(model.state.liveWorkspaceSettings.billing_account.seat_count, 4);
  assert.equal(model.state.liveWorkspaceSettings.members.length, 2);
  assert.equal(model.state.lastIssuedApiToken.token, "token_abcdef123456");
  assert.equal(model.frontendState.product_surface.workspace_members[1].user_id, "researcher_001");
  assert.equal(model.frontendState.product_surface.workspace_api_tokens[1].token_hint, "token_...3456");
  assert.equal(model.frontendState.product_surface.workspace_billing_summary[2].value, "pro");
  assert.equal(model.frontendState.product_surface.last_issued_api_token_summary[0].value, "token_abcdef123456");

  await controller.revokeWorkspaceApiToken({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    tokenId: "token_abcdef123456"
  });
  await controller.loadWorkspaceAuditEvents({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    targetType: "api_token",
    actionPrefix: "api_token.",
    limit: 5
  });

  model = controller.deriveModel();
  assert.equal(model.state.liveWorkspaceSettings.api_tokens[1].active, false);
  assert.equal(model.state.lastIssuedApiToken, null);
  assert.equal(model.state.liveAuditEvents.length, 1);
  assert.equal(model.frontendState.product_surface.workspace_audit_summary[1].value, "api_token");
  assert.equal(model.frontendState.product_surface.workspace_audit_events[0].action, "api_token.issued");
});

test("controller can cancel a queued job and retry a failed job through the shared app boundary", async () => {
  const fetchCalls = [];
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push(`${options.method || "GET"} ${url}`);
      if (url.endsWith("/api/v1/validation-jobs/job_queued_001/cancel")) {
        return fakeResponse(200, {
          job: {
            job_id: "job_queued_001",
            status: "canceled",
            provider_name: "mock",
            retry_count: 0,
            last_error: "Canceled from the workspace product surface.",
            metadata: { project_id: "project_001", study_id: "study_001" }
          }
        });
      }
      if (url.endsWith("/api/v1/validation-jobs/job_failed_001/retry")) {
        return fakeResponse(202, {
          source_job_id: "job_failed_001",
          job: {
            job_id: "job_retry_001",
            status: "queued",
            provider_name: "mock",
            retry_count: 0,
            metadata: { project_id: "project_001", study_id: "study_001", retry_of_job_id: "job_failed_001" }
          }
        });
      }
      if (url.endsWith("/api/v1/session")) {
        return fakeResponse(200, {
          session: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial" },
            billing_account: { status: "trialing", seat_count: 1 },
            plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
            job_counts: { total: 2, queued: 1, running: 0, completed: 0, failed: 0, canceled: 1 },
            paths: { workspace_root: "saas_runtime/workspaces/ws_api_demo" },
            capabilities: { validation_jobs: true, evidence_query: true, worker_runtime: true, session_auth: true },
            synthetic_boundary: "Synthetic evidence only."
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.getState().mode = "live";
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  controller.getState().selectedJobId = "job_queued_001";
  controller.getState().liveJobs = [
    { job_id: "job_queued_001", status: "queued", provider_name: "mock", retry_count: 0, metadata: { project_id: "project_001", study_id: "study_001" } },
    { job_id: "job_failed_001", status: "failed", provider_name: "mock", retry_count: 1, last_error: "boom", metadata: { project_id: "project_001", study_id: "study_001" } }
  ];

  await controller.cancelSelectedJob({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    reason: "Canceled from the workspace product surface."
  });

  assert.equal(controller.getState().liveJobs[0].status, "canceled");
  assert.equal(controller.getState().selectedJobId, "job_queued_001");

  controller.selectJob("job_failed_001");
  await controller.retrySelectedJob({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api"
  });

  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas"
  });

  assert.equal(model.state.selectedJobId, "job_retry_001");
  assert.equal(model.state.liveJobs[0].job_id, "job_retry_001");
  assert.equal(model.frontendState.actions.cancel_selected_job.enabled, true);
  assert.equal(model.frontendState.actions.retry_selected_job.enabled, false);
  assert.deepEqual(fetchCalls, [
    "POST http://127.0.0.1:8011/api/v1/validation-jobs/job_queued_001/cancel",
    "GET http://127.0.0.1:8011/api/v1/session",
    "POST http://127.0.0.1:8011/api/v1/validation-jobs/job_failed_001/retry",
    "GET http://127.0.0.1:8011/api/v1/session"
  ]);
});

test("controller can bootstrap route-scoped product context through detail loaders", async () => {
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url) => {
      if (url.endsWith("/api/v1/projects/project_001")) {
        return fakeResponse(200, {
          project: { project_id: "project_001", name: "Inbox Coach Launch", slug: "inbox-coach-launch", study_count: 1 }
        });
      }
      if (url.endsWith("/api/v1/studies/study_001")) {
        return fakeResponse(200, {
          study: { study_id: "study_001", project_id: "project_001", title: "Onboarding hesitation", status: "review_ready", run_count: 1, latest_job_status: "completed" }
        });
      }
      if (url.endsWith("/api/v1/export-bundles/export_001")) {
        return fakeResponse(200, {
          export_bundle: { export_bundle_id: "export_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Exec review export", status: "published", export_format: "report_csv", exported_file_count: 1, synthetic_boundary: "Synthetic evidence only." }
        });
      }
      if (url.endsWith("/api/v1/share-bundles/share_001")) {
        return fakeResponse(200, {
          share_bundle: { share_bundle_id: "share_001", export_bundle_id: "export_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Board share", status: "published", public_path: "/public/v1/share-bundles/shk_001", share_file_count: 2, synthetic_boundary: "Synthetic evidence only." }
        });
      }
      if (url.endsWith("/api/v1/support-snapshots/support_001")) {
        return fakeResponse(200, {
          support_snapshot: { support_snapshot_id: "support_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Provider failure snapshot", status: "generated", summary: "Unknown provider: unknown-provider", run_id: "run_001" }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  await controller.loadProjectDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    projectId: "project_001"
  });
  await controller.loadStudyDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001"
  });
  await controller.loadExportBundleDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    exportBundleId: "export_001"
  });
  await controller.loadShareBundleDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    shareBundleId: "share_001"
  });
  await controller.loadSupportSnapshotDetail({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    supportSnapshotId: "support_001"
  });

  const model = controller.deriveModel();
  assert.equal(model.state.selectedProjectId, "project_001");
  assert.equal(model.state.selectedStudyId, "study_001");
  assert.equal(model.state.selectedExportBundleId, "export_001");
  assert.equal(model.state.selectedShareBundleId, "share_001");
  assert.equal(model.state.selectedSupportSnapshotId, "support_001");
});

test("controller can submit job and reload session through shared app boundary", async () => {
  const fetchCalls = [];
  const controller = createWorkspaceShellAppController({
    now: (() => {
      const values = [
        new Date("2026-06-28T02:00:00.000Z"),
        new Date("2026-06-28T02:00:01.000Z"),
        new Date("2026-06-28T02:00:02.000Z")
      ];
      let index = 0;
      return () => values[Math.min(index++, values.length - 1)];
    })(),
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push({
        url,
        method: options.method || "GET",
        body: options.body ? JSON.parse(options.body) : null
      });
      if (url.endsWith("/api/v1/validation-jobs")) {
        return fakeResponse(202, {
          job: {
            job_id: "job_001",
            status: "queued",
            provider_name: "mock"
          }
        });
      }
      if (url.endsWith("/api/v1/session")) {
        return fakeResponse(200, {
          session: {
            auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
            workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial" },
            billing_account: { status: "trialing", seat_count: 1 },
            plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
            job_counts: { total: 1, queued: 1, running: 0, completed: 0, failed: 0 },
            paths: { workspace_root: "saas_runtime/workspaces/ws_api_demo" },
            capabilities: { validation_jobs: true, evidence_query: true, worker_runtime: true, session_auth: true },
            synthetic_boundary: "Synthetic evidence only."
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.applyDraftScenario("confirmed_draft");
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  await controller.submitLiveJob({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });
  await controller.loadWorkspaceSession({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas"
  });

  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "all",
      sortBy: "relevance"
    }
  });

  assert.deepEqual(fetchCalls.map((call) => `${call.method} ${call.url}`), [
    "POST http://127.0.0.1:8011/api/v1/validation-jobs",
    "GET http://127.0.0.1:8011/api/v1/session"
  ]);
  assert.match(fetchCalls[0].body.idempotency_key, /^stage12-demo-job:(submit_|draft_plan_)/);
  assert.equal(fetchCalls[0].body.metadata.project_id, "project_001");
  assert.equal(fetchCalls[0].body.metadata.study_id, "study_001");
  assert.equal(model.frontendState.metrics.selected_job_id, "job_001");
  assert.equal(model.sessionBridgeState.metrics.workspace_id, "ws_api_demo");
  assert.equal(model.jobs[0].job_id, "job_001");
});

test("controller resets draft identity so repeated demo submissions do not collapse onto one static idempotency key", async () => {
  const requestBodies = [];
  let submitCount = 0;
  const controller = createWorkspaceShellAppController({
    now: (() => {
      const values = [
        new Date("2026-06-28T04:00:00.000Z"),
        new Date("2026-06-28T04:00:01.000Z"),
        new Date("2026-06-28T04:00:02.000Z"),
        new Date("2026-06-28T04:00:03.000Z"),
        new Date("2026-06-28T04:00:04.000Z"),
        new Date("2026-06-28T04:00:05.000Z")
      ];
      let index = 0;
      return () => values[Math.min(index++, values.length - 1)];
    })(),
    fetchImpl: async (url, options = {}) => {
      if (url.endsWith("/api/v1/validation-jobs")) {
        submitCount += 1;
        requestBodies.push(JSON.parse(options.body));
        return fakeResponse(202, {
          job: {
            job_id: `job_00${submitCount}`,
            status: "queued",
            provider_name: "mock"
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.applyDraftScenario("confirmed_draft");
  await controller.submitLiveJob({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas"
  });

  controller.resetDraftFlow();
  controller.applyDraftScenario("confirmed_draft");
  await controller.submitLiveJob({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas"
  });

  assert.equal(requestBodies.length, 2);
  assert.notEqual(requestBodies[0].idempotency_key, requestBodies[1].idempotency_key);
  assert.match(requestBodies[0].metadata.draft_plan_id, /^draft_plan_/);
  assert.match(requestBodies[1].metadata.draft_plan_id, /^draft_plan_/);
});

test("controller syncRuntime updates heartbeat and completed evidence state", async () => {
  const controller = createWorkspaceShellAppController({
    now: () => new Date("2026-06-28T03:00:00.000Z"),
    fetchImpl: async (url) => {
      if (url.includes("/api/v1/workspace-shell?")) {
        assert.match(url, /job_id=job_001/);
        assert.match(url, /project_id=project_001/);
        assert.match(url, /study_id=study_001/);
        assert.match(url, /query_text=hesitate/);
        assert.match(url, /active_family=trace/);
        assert.match(url, /sort_by=newest/);
        assert.match(url, /selected_result_id=query-run_report/);
        assert.match(url, /selected_replay_step_id=step-03/);
        assert.match(url, /selected_comparison_run_id=run_002/);
        return fakeResponse(200, {
          snapshot: {
            session: {
              auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
              workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial" },
              billing_account: { status: "trialing", seat_count: 1 },
              plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
              job_counts: { total: 1, queued: 0, running: 0, completed: 1, failed: 0 },
              paths: { workspace_root: "saas_runtime/workspaces/ws_api_demo" },
              capabilities: { validation_jobs: true, evidence_query: true, worker_runtime: true, session_auth: true },
              synthetic_boundary: "Synthetic evidence only."
            },
            jobs: [
              {
                job_id: "job_001",
                status: "completed",
                provider_name: "mock",
                output_run_path: "runs/job_001"
              }
            ],
            selected_job_id: "job_001",
            evidence_query: {
              query_status: "query_ready",
              result_count: 1,
              selected_result_id: "query-run_report",
              selected_replay_step_id: "step-03",
              cross_run_comparison: {
                selected_comparison_run_id: "run_002",
                comparison_run_count: 1,
                candidate_runs: [
                  {
                    run_id: "run_002",
                    relation_note: "same brief",
                    result_count: 2,
                    replay_result_count: 1,
                    top_result_title: "Raw responses"
                  }
                ]
              },
              results: [{ id: "query-run_report", title: "Run report" }]
            },
            runtime_sync: {
              poll_recommended_ms: 4000
            }
          }
        });
      }
      throw new Error(`Unexpected URL: ${url}`);
    }
  });

  controller.applyDraftScenario("confirmed_draft");
  controller.selectJob("job_001");
  controller.getState().mode = "live";
  controller.getState().selectedProjectId = "project_001";
  controller.getState().selectedStudyId = "study_001";
  controller.getState().liveJobs = [{ job_id: "job_001", status: "queued", provider_name: "mock" }];

  await controller.syncRuntime({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    selectedResultId: "query-run_report",
    selectedReplayStepId: "step-03",
    selectedComparisonRunId: "run_002",
    queryState: {
      queryText: "hesitate",
      activeFamily: "trace",
      sortBy: "newest"
    }
  });

  const model = controller.deriveModel({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    queryState: {
      queryText: "hesitate",
      activeFamily: "trace",
      sortBy: "newest"
    }
  });

  assert.equal(model.runtimeSyncView.pill.label, "live_synced");
  assert.equal(model.state.runtimeSync.last_synced_at, "2026-06-28T03:00:00.000Z");
  assert.equal(model.frontendState.review_surface.query_status, "query_ready");
  assert.equal(model.frontendState.review_surface.results.length, 1);
  assert.equal(model.state.liveEvidenceQuery.selected_replay_step_id, "step-03");
  assert.equal(model.frontendState.review_surface.selected_comparison_run_id, "run_002");
});

test("controller toggles runtime auto refresh in shared state", () => {
  const controller = createWorkspaceShellAppController();
  controller.toggleRuntimeAutoRefresh();
  let model = controller.deriveModel();
  assert.equal(model.runtimeSyncView.summary[0].value, "on");

  controller.toggleRuntimeAutoRefresh();
  model = controller.deriveModel();
  assert.equal(model.runtimeSyncView.summary[0].value, "off");
});
