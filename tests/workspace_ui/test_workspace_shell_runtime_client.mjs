import test from "node:test";
import assert from "node:assert/strict";

import {
  createWorkspaceDecisionComment,
  createWorkspaceExportBundle,
  createWorkspaceDecisionLog,
  createWorkspaceEvidenceView,
  createWorkspaceProject,
  createWorkspaceShareBundle,
  createWorkspaceSupportSnapshot,
  createWorkspaceStudy,
  cancelWorkspaceValidationJob,
  loadWorkspaceDecisionComments,
  loadWorkspaceDecisionLogDetail,
  loadWorkspaceDecisionLogs,
  loadWorkspaceEvidenceViewDetail,
  loadWorkspaceEvidenceViews,
  issueWorkspaceApiToken,
  loadWorkspaceAuditEvents,
  loadWorkspaceExportBundles,
  loadWorkspaceExportBundleDetail,
  loadWorkspaceProjects,
  loadWorkspaceProjectDetail,
  loadWorkspaceShareBundles,
  loadWorkspaceShareBundleDetail,
  loadWorkspaceSupportDiagnostics,
  loadWorkspaceSupportSnapshots,
  loadWorkspaceSupportSnapshotDetail,
  loadWorkspaceSettings,
  loadWorkspaceStudyActivity,
  loadWorkspaceStudies,
  loadWorkspaceStudyDetail,
  listWorkspaceValidationJobs,
  loadWorkspaceEvidenceQuery,
  loadWorkspaceShellSnapshot,
  loadWorkspaceRuntimeSession,
  loadWorkspaceValidationJobDetail,
  revokeWorkspaceApiToken,
  revokeWorkspaceShareBundle,
  retryWorkspaceValidationJob,
  selectWorkspaceRuntimeDecisionLog,
  selectWorkspaceRuntimeEvidenceView,
  selectWorkspaceRuntimeExportBundle,
  selectWorkspaceRuntimeProject,
  selectWorkspaceRuntimeShareBundle,
  selectWorkspaceRuntimeSupportSnapshot,
  selectWorkspaceRuntimeStudy,
  selectWorkspaceRuntimeJob,
  submitWorkspaceValidationJob,
  switchWorkspaceRuntimeToSample,
  updateWorkspaceDecisionReviewStatus,
  updateWorkspaceBilling,
  upsertWorkspaceMember
} from "../../demo/workspace_ui_shared/workspace_shell_runtime_client.mjs";

function makeState() {
  return {
    liveJobs: [],
    liveProjects: [],
    selectedProjectId: null,
    liveStudies: [],
    selectedStudyId: null,
    liveStudyActivity: null,
    liveEvidenceViews: [],
    selectedEvidenceViewId: null,
    liveDecisionLogs: [],
    selectedDecisionLogId: null,
    liveDecisionComments: [],
    liveExportBundles: [],
    selectedExportBundleId: null,
    liveShareBundles: [],
    selectedShareBundleId: null,
    liveSupportSnapshots: [],
    selectedSupportSnapshotId: null,
    liveSession: null,
    selectedJobId: null,
    liveEvidenceQuery: null,
    liveSupportDiagnostics: null,
    liveWorkspaceSettings: null,
    mode: "sample",
    lastApiResponse: null,
    lastIssuedApiToken: null,
    liveAuditEvents: [],
    liveAuditQuery: null,
    liveError: null,
    sessionError: null,
    runtimeSync: { interval_ms: 4000, auto_refresh_enabled: false }
  };
}

function fakeResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    }
  };
}

test("loadWorkspaceRuntimeSession stores authenticated session payload", async () => {
  const next = await loadWorkspaceRuntimeSession({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async () => fakeResponse(200, {
      session: {
        auth: { workspace_id: "ws_api_demo", role: "owner" }
      }
    })
  });

  assert.equal(next.liveSession.auth.workspace_id, "ws_api_demo");
  assert.equal(next.sessionError, null);
  assert.equal(next.lastApiResponse.session.auth.role, "owner");
});

test("loadWorkspaceRuntimeSession omits Authorization header when bearer token is blank", async () => {
  await loadWorkspaceRuntimeSession({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "",
    fetchImpl: async (_url, options = {}) => {
      assert.equal(options.headers.Authorization, undefined);
      return fakeResponse(200, {
        session: {
          auth: { workspace_id: "ws_api_demo", role: "owner", auth_type: "browser_session" }
        }
      });
    }
  });
});

test("submitWorkspaceValidationJob moves state into live mode", async () => {
  const next = await submitWorkspaceValidationJob({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    requestPayload: { brief_path: "briefs/brief.json" },
    fetchImpl: async () => fakeResponse(202, {
      job: { job_id: "job_001", status: "queued", provider_name: "mock" }
    })
  });

  assert.equal(next.mode, "live");
  assert.equal(next.selectedJobId, "job_001");
  assert.equal(next.liveJobs.length, 1);
  assert.equal(next.liveError, null);
});

test("cancelWorkspaceValidationJob marks a queued job canceled and clears review state", async () => {
  const next = await cancelWorkspaceValidationJob({
    state: {
      ...makeState(),
      mode: "live",
      liveJobs: [
        { job_id: "job_001", status: "queued", provider_name: "mock" }
      ],
      selectedJobId: "job_001",
      liveEvidenceQuery: { query_status: "query_ready" },
      liveSupportDiagnostics: { job_diagnostic: { status: "queued" } }
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    reason: "Canceled from test",
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/validation-jobs/job_001/cancel");
      assert.equal(options.method, "POST");
      assert.equal(JSON.parse(options.body).reason, "Canceled from test");
      return fakeResponse(200, {
        job: { job_id: "job_001", status: "canceled", provider_name: "mock", last_error: "Canceled from test" }
      });
    }
  });

  assert.equal(next.selectedJobId, "job_001");
  assert.equal(next.liveJobs[0].status, "canceled");
  assert.equal(next.liveEvidenceQuery, null);
  assert.equal(next.liveSupportDiagnostics, null);
});

test("retryWorkspaceValidationJob creates a new queued job and selects it", async () => {
  const next = await retryWorkspaceValidationJob({
    state: {
      ...makeState(),
      mode: "live",
      selectedProjectId: "project_001",
      selectedStudyId: "study_001",
      liveJobs: [
        {
          job_id: "job_failed_001",
          status: "failed",
          provider_name: "mock",
          metadata: { project_id: "project_001", study_id: "study_001" }
        }
      ],
      selectedJobId: "job_failed_001",
      liveEvidenceQuery: { query_status: "query_ready" },
      liveSupportDiagnostics: { job_diagnostic: { status: "failed" } }
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/validation-jobs/job_failed_001/retry");
      assert.equal(options.method, "POST");
      return fakeResponse(202, {
        source_job_id: "job_failed_001",
        job: {
          job_id: "job_retry_001",
          status: "queued",
          provider_name: "mock",
          metadata: { project_id: "project_001", study_id: "study_001", retry_of_job_id: "job_failed_001" }
        }
      });
    }
  });

  assert.equal(next.selectedProjectId, "project_001");
  assert.equal(next.selectedStudyId, "study_001");
  assert.equal(next.selectedJobId, "job_retry_001");
  assert.equal(next.liveJobs[0].job_id, "job_retry_001");
  assert.equal(next.liveEvidenceQuery, null);
  assert.equal(next.liveSupportDiagnostics, null);
});

test("project, study, export, and share runtime helpers load, create, and select product objects", async () => {
  const loadedProjects = await loadWorkspaceProjects({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async () => fakeResponse(200, {
      projects: [
        { project_id: "project_001", name: "Inbox Coach Launch", slug: "inbox-coach-launch", study_count: 1 }
      ]
    })
  });

  assert.equal(loadedProjects.liveProjects.length, 1);
  assert.equal(loadedProjects.selectedProjectId, "project_001");

  const createdProject = await createWorkspaceProject({
    state: loadedProjects,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { name: "Ops Console", slug: "ops-console" },
    fetchImpl: async () => fakeResponse(201, {
      project: { project_id: "project_002", name: "Ops Console", slug: "ops-console", study_count: 0 }
    })
  });

  assert.equal(createdProject.liveProjects[0].project_id, "project_002");
  assert.equal(createdProject.selectedProjectId, "project_002");
  assert.deepEqual(createdProject.liveEvidenceViews, []);
  assert.equal(createdProject.selectedEvidenceViewId, null);
  assert.deepEqual(createdProject.liveDecisionLogs, []);
  assert.equal(createdProject.selectedDecisionLogId, null);

  const selectedProject = selectWorkspaceRuntimeProject(createdProject, "project_001");
  assert.equal(selectedProject.selectedProjectId, "project_001");
  assert.equal(selectedProject.selectedStudyId, null);

  const loadedStudies = await loadWorkspaceStudies({
    state: selectedProject,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    projectId: "project_001",
    fetchImpl: async (url) => {
      assert.match(url, /project_id=project_001/);
      return fakeResponse(200, {
        studies: [
          { study_id: "study_001", project_id: "project_001", title: "Onboarding hesitation", status: "review_ready", run_count: 2, latest_job_status: "completed" }
        ]
      });
    }
  });

  assert.equal(loadedStudies.liveStudies.length, 1);
  assert.equal(loadedStudies.selectedStudyId, "study_001");

  const createdStudy = await createWorkspaceStudy({
    state: loadedStudies,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { project_id: "project_001", title: "Permissions study" },
    fetchImpl: async () => fakeResponse(201, {
      study: { study_id: "study_002", project_id: "project_001", title: "Permissions study", status: "draft", run_count: 0, latest_job_status: null }
    })
  });

  assert.equal(createdStudy.liveStudies[0].study_id, "study_002");
  assert.equal(createdStudy.selectedStudyId, "study_002");
  assert.deepEqual(createdStudy.liveEvidenceViews, []);
  assert.equal(createdStudy.selectedEvidenceViewId, null);
  assert.deepEqual(createdStudy.liveDecisionLogs, []);
  assert.equal(createdStudy.selectedDecisionLogId, null);

  const selectedStudy = selectWorkspaceRuntimeStudy(createdStudy, "study_001");
  assert.equal(selectedStudy.selectedStudyId, "study_001");
  assert.equal(selectedStudy.selectedJobId, null);

  const loadedStudyActivity = await loadWorkspaceStudyActivity({
    state: selectedStudy,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    limit: 5,
    fetchImpl: async (url) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/studies/study_001/activity?limit=5");
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
              summary: "Permissions study was created.",
              actor_user_id: "owner_api",
              created_at: "2026-06-28T00:10:00Z",
              route_kind: "study",
              route_id: "study_001"
            }
          ]
        }
      });
    }
  });

  assert.equal(loadedStudyActivity.selectedProjectId, "project_001");
  assert.equal(loadedStudyActivity.selectedStudyId, "study_001");
  assert.equal(loadedStudyActivity.liveStudyActivity.length, 1);
  assert.equal(loadedStudyActivity.liveStudyActivity[0].action, "study.created");

  const loadedExportBundles = await loadWorkspaceExportBundles({
    state: loadedStudyActivity,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    fetchImpl: async (url) => {
      assert.match(url, /study_id=study_001/);
      return fakeResponse(200, {
        export_bundles: [
          {
            export_bundle_id: "export_001",
            study_id: "study_001",
            job_id: "job_001",
            title: "Exec review export",
            export_format: "report_csv",
            exported_file_count: 1
          }
        ]
      });
    }
  });

  assert.equal(loadedExportBundles.liveExportBundles.length, 1);
  assert.equal(loadedExportBundles.selectedExportBundleId, "export_001");

  const createdExportBundle = await createWorkspaceExportBundle({
    state: loadedExportBundles,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { study_id: "study_001", job_id: "job_001", export_format: "report_csv" },
    fetchImpl: async () => fakeResponse(201, {
      export_bundle: {
        export_bundle_id: "export_002",
        study_id: "study_001",
        job_id: "job_001",
        title: "Board export",
        export_format: "report_csv",
        exported_file_count: 1
      }
    })
  });

  assert.equal(createdExportBundle.liveExportBundles[0].export_bundle_id, "export_002");
  assert.equal(createdExportBundle.selectedExportBundleId, "export_002");

  const selectedExportBundle = selectWorkspaceRuntimeExportBundle(createdExportBundle, "export_001");
  assert.equal(selectedExportBundle.selectedExportBundleId, "export_001");

  const loadedShareBundles = await loadWorkspaceShareBundles({
    state: selectedExportBundle,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    exportBundleId: "export_001",
    fetchImpl: async (url) => {
      assert.match(url, /export_bundle_id=export_001/);
      return fakeResponse(200, {
        share_bundles: [
          {
            share_bundle_id: "share_001",
            export_bundle_id: "export_001",
            study_id: "study_001",
            title: "Board review share",
            status: "published",
            public_path: "/public/v1/share-bundles/shk_001",
            share_file_count: 2
          }
        ]
      });
    }
  });

  assert.equal(loadedShareBundles.liveShareBundles.length, 1);
  assert.equal(loadedShareBundles.selectedShareBundleId, "share_001");

  const createdShareBundle = await createWorkspaceShareBundle({
    state: loadedShareBundles,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { export_bundle_id: "export_001", title: "Fresh share", expires_in_days: 7 },
    fetchImpl: async () => fakeResponse(201, {
      share_bundle: {
        share_bundle_id: "share_002",
        export_bundle_id: "export_001",
        study_id: "study_001",
        title: "Fresh share",
        status: "published",
        public_path: "/public/v1/share-bundles/shk_002",
        share_file_count: 2
      }
    })
  });

  assert.equal(createdShareBundle.liveShareBundles[0].share_bundle_id, "share_002");
  assert.equal(createdShareBundle.selectedShareBundleId, "share_002");

  const selectedShareBundle = selectWorkspaceRuntimeShareBundle(createdShareBundle, "share_001");
  assert.equal(selectedShareBundle.selectedShareBundleId, "share_001");

  const revokedShareBundle = await revokeWorkspaceShareBundle({
    state: selectedShareBundle,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    shareBundleId: "share_001",
    fetchImpl: async () => fakeResponse(200, {
      share_bundle: {
        share_bundle_id: "share_001",
        export_bundle_id: "export_001",
        study_id: "study_001",
        title: "Board review share",
        status: "revoked",
        public_path: "/public/v1/share-bundles/shk_001",
        share_file_count: 2
      }
    })
  });

  assert.equal(revokedShareBundle.liveShareBundles.find((item) => item.share_bundle_id === "share_001")?.status, "revoked");
});

test("collaboration runtime helpers load, create, detail, and select evidence views and decision logs", async () => {
  const selectedStudy = {
    ...makeState(),
    mode: "live",
    selectedProjectId: "project_001",
    selectedStudyId: "study_001",
    selectedJobId: "job_001",
    liveJobs: [{ job_id: "job_001", status: "completed", provider_name: "mock" }]
  };

  const loadedEvidenceViews = await loadWorkspaceEvidenceViews({
    state: selectedStudy,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    jobId: "job_001",
    fetchImpl: async (url) => {
      assert.match(url, /study_id=study_001/);
      assert.match(url, /job_id=job_001/);
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
  });

  assert.equal(loadedEvidenceViews.liveEvidenceViews.length, 1);
  assert.equal(loadedEvidenceViews.selectedEvidenceViewId, "view_001");

  const createdEvidenceView = await createWorkspaceEvidenceView({
    state: loadedEvidenceViews,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: {
      study_id: "study_001",
      job_id: "job_001",
      title: "Replay focus",
      note: "Save selected replay step"
    },
    fetchImpl: async () => fakeResponse(201, {
      evidence_view: {
        evidence_view_id: "view_002",
        project_id: "project_001",
        study_id: "study_001",
        job_id: "job_001",
        title: "Replay focus",
        note: "Save selected replay step",
        query_text: "hesitate",
        active_family: "trace",
        sort_by: "newest",
        selected_result_id: "query-raw_responses",
        selected_replay_step_id: "response-02"
      }
    })
  });

  assert.equal(createdEvidenceView.liveEvidenceViews[0].evidence_view_id, "view_002");
  assert.equal(createdEvidenceView.selectedEvidenceViewId, "view_002");

  const evidenceViewDetail = await loadWorkspaceEvidenceViewDetail({
    state: createdEvidenceView,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    evidenceViewId: "view_001",
    fetchImpl: async () => fakeResponse(200, {
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
    })
  });

  assert.equal(evidenceViewDetail.selectedEvidenceViewId, "view_001");
  assert.equal(evidenceViewDetail.liveEvidenceViews[0].selected_comparison_run_id, "run_002");

  const selectedEvidenceView = selectWorkspaceRuntimeEvidenceView(evidenceViewDetail, "view_002");
  assert.equal(selectedEvidenceView.selectedEvidenceViewId, "view_002");

  const loadedDecisionLogs = await loadWorkspaceDecisionLogs({
    state: selectedEvidenceView,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    jobId: "job_001",
    evidenceViewId: "view_002",
    fetchImpl: async (url) => {
      assert.match(url, /study_id=study_001/);
      assert.match(url, /job_id=job_001/);
      assert.match(url, /evidence_view_id=view_002/);
      return fakeResponse(200, {
        decision_logs: [
          {
            decision_log_id: "decision_001",
            project_id: "project_001",
            study_id: "study_001",
            job_id: "job_001",
            evidence_view_id: "view_002",
            title: "Do not ship yet",
            decision_summary: "Trust blockers still dominate.",
            rationale: "Observed objections repeat across personas."
          }
        ]
      });
    }
  });

  assert.equal(loadedDecisionLogs.liveDecisionLogs.length, 1);
  assert.equal(loadedDecisionLogs.selectedDecisionLogId, "decision_001");

  const createdDecisionLog = await createWorkspaceDecisionLog({
    state: loadedDecisionLogs,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: {
      study_id: "study_001",
      job_id: "job_001",
      evidence_view_id: "view_002",
      title: "Retry onboarding copy",
      decision_summary: "Adjust the first-run copy before another test.",
      rationale: "The same hesitation appears in replay."
    },
    fetchImpl: async () => fakeResponse(201, {
      decision_log: {
        decision_log_id: "decision_002",
        project_id: "project_001",
        study_id: "study_001",
        job_id: "job_001",
        evidence_view_id: "view_002",
        title: "Retry onboarding copy",
        decision_summary: "Adjust the first-run copy before another test.",
        rationale: "The same hesitation appears in replay.",
        selected_result_id: "query-raw_responses"
      }
    })
  });

  assert.equal(createdDecisionLog.liveDecisionLogs[0].decision_log_id, "decision_002");
  assert.equal(createdDecisionLog.selectedDecisionLogId, "decision_002");

  const decisionLogDetail = await loadWorkspaceDecisionLogDetail({
    state: createdDecisionLog,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    fetchImpl: async () => fakeResponse(200, {
      decision_log: {
        decision_log_id: "decision_001",
        project_id: "project_001",
        study_id: "study_001",
        job_id: "job_001",
        evidence_view_id: "view_002",
        title: "Do not ship yet",
        decision_summary: "Trust blockers still dominate.",
        rationale: "Observed objections repeat across personas.",
        selected_comparison_run_id: "run_002"
      },
      decision_comments: []
    })
  });

  assert.equal(decisionLogDetail.selectedDecisionLogId, "decision_001");
  assert.equal(decisionLogDetail.selectedEvidenceViewId, "view_002");
  assert.deepEqual(decisionLogDetail.liveDecisionComments, []);

  const selectedDecisionLog = selectWorkspaceRuntimeDecisionLog(decisionLogDetail, "decision_002");
  assert.equal(selectedDecisionLog.selectedDecisionLogId, "decision_002");
  assert.deepEqual(selectedDecisionLog.liveDecisionComments, []);
});

test("decision review runtime helpers load comments, add replies, and update review status", async () => {
  const selected = {
    ...makeState(),
    mode: "live",
    selectedProjectId: "project_001",
    selectedStudyId: "study_001",
    selectedJobId: "job_001",
    selectedEvidenceViewId: "view_001",
    selectedDecisionLogId: "decision_001",
    liveDecisionLogs: [
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
    ]
  };

  const commentsLoaded = await loadWorkspaceDecisionComments({
    state: selected,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    fetchImpl: async () => fakeResponse(200, {
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
          body: "Please justify why this is not only one-run noise.",
          created_by_user_id: "reviewer_001",
          created_at: "2026-06-28T02:00:00+00:00",
          reply_count: 0
        }
      ]
    })
  });

  assert.equal(commentsLoaded.liveDecisionComments.length, 1);
  assert.equal(commentsLoaded.liveDecisionLogs[0].review_status, "in_review");

  const commentCreated = await createWorkspaceDecisionComment({
    state: commentsLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    payload: {
      parent_comment_id: "decision_comment_001",
      anchor_kind: "rationale",
      body: "The same objection repeats in the comparison run."
    },
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/decision-logs/decision_001/comments");
      assert.equal(options.method, "POST");
      assert.equal(JSON.parse(options.body).parent_comment_id, "decision_comment_001");
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
          review_status: "in_review",
          comment_count: 2
        },
        decision_comment: {
          decision_comment_id: "decision_comment_002",
          decision_log_id: "decision_001",
          parent_comment_id: "decision_comment_001",
          anchor_kind: "rationale",
          body: "The same objection repeats in the comparison run.",
          created_by_user_id: "owner_api",
          created_at: "2026-06-28T02:05:00+00:00",
          reply_count: 0
        }
      });
    }
  });

  assert.equal(commentCreated.liveDecisionComments.length, 2);
  assert.equal(commentCreated.liveDecisionComments[1].parent_comment_id, "decision_comment_001");

  const reviewUpdated = await updateWorkspaceDecisionReviewStatus({
    state: commentCreated,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    decisionLogId: "decision_001",
    payload: {
      review_status: "approved",
      note: "Cross-run evidence is now consistent enough to proceed."
    },
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/decision-logs/decision_001/review-status");
      assert.equal(options.method, "POST");
      assert.equal(JSON.parse(options.body).review_status, "approved");
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
          latest_review_note: "Cross-run evidence is now consistent enough to proceed.",
          comment_count: 2
        }
      });
    }
  });

  assert.equal(reviewUpdated.liveDecisionLogs[0].review_status, "approved");
});

test("support runtime helpers load, create, and select support state", async () => {
  const selected = {
    ...makeState(),
    mode: "live",
    selectedStudyId: "study_001",
    selectedJobId: "job_001",
    liveJobs: [{ job_id: "job_001", status: "failed", provider_name: "mock" }]
  };

  const diagnosticsLoaded = await loadWorkspaceSupportDiagnostics({
    state: selected,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async (url) => {
      assert.match(url, /job_id=job_001/);
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
            failure_category: "provider_configuration",
            summary: "Unknown provider: unknown-provider",
            next_actions: ["Check provider_name or backend configuration before retrying."]
          },
          support_snapshot_count: 1
        }
      });
    }
  });

  assert.equal(diagnosticsLoaded.liveSupportDiagnostics.job_diagnostic.failure_category, "provider_configuration");

  const supportSnapshotsLoaded = await loadWorkspaceSupportSnapshots({
    state: diagnosticsLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    jobId: "job_001",
    fetchImpl: async (url) => {
      assert.match(url, /study_id=study_001/);
      assert.match(url, /job_id=job_001/);
      return fakeResponse(200, {
        support_snapshots: [
          {
            support_snapshot_id: "support_001",
            study_id: "study_001",
            job_id: "job_001",
            title: "Provider failure snapshot",
            status: "generated",
            summary: "Unknown provider: unknown-provider"
          }
        ]
      });
    }
  });

  assert.equal(supportSnapshotsLoaded.liveSupportSnapshots.length, 1);
  assert.equal(supportSnapshotsLoaded.selectedSupportSnapshotId, "support_001");

  const createdSupportSnapshot = await createWorkspaceSupportSnapshot({
    state: supportSnapshotsLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { job_id: "job_001", title: "Fresh support handoff" },
    fetchImpl: async () => fakeResponse(201, {
      support_snapshot: {
        support_snapshot_id: "support_002",
        study_id: "study_001",
        job_id: "job_001",
        title: "Fresh support handoff",
        status: "generated",
        summary: "Unknown provider: unknown-provider"
      }
    })
  });

  assert.equal(createdSupportSnapshot.liveSupportSnapshots[0].support_snapshot_id, "support_002");
  assert.equal(createdSupportSnapshot.selectedSupportSnapshotId, "support_002");

  const selectedSupportSnapshot = selectWorkspaceRuntimeSupportSnapshot(createdSupportSnapshot, "support_001");
  assert.equal(selectedSupportSnapshot.selectedSupportSnapshotId, "support_001");
});

test("workspace settings helpers load members, issue tokens, and revoke them", async () => {
  const loadedSettings = await loadWorkspaceSettings({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async () => fakeResponse(200, {
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
    })
  });

  assert.equal(loadedSettings.liveWorkspaceSettings.members.length, 1);
  assert.equal(loadedSettings.lastIssuedApiToken, null);

  const upsertedMember = await upsertWorkspaceMember({
    state: loadedSettings,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { user_id: "researcher_001", role: "editor" },
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/workspace-members");
      assert.equal(options.method, "POST");
      assert.deepEqual(JSON.parse(options.body), { user_id: "researcher_001", role: "editor" });
      return fakeResponse(201, {
        member: { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" },
        workspace_settings: {
          ...loadedSettings.liveWorkspaceSettings,
          members: [
            { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" },
            { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" }
          ]
        }
      });
    }
  });

  assert.equal(upsertedMember.liveWorkspaceSettings.members.length, 2);
  assert.equal(upsertedMember.liveWorkspaceSettings.members[1].role, "editor");

  const billingUpdated = await updateWorkspaceBilling({
    state: upsertedMember,
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
    },
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/workspace-billing");
      assert.equal(options.method, "POST");
      assert.deepEqual(JSON.parse(options.body), {
        plan_tier: "pro",
        billing_status: "active",
        seat_count: 4,
        renewal_at: "2026-07-31T00:00:00+00:00",
        daily_runs: 25,
        max_concurrent_jobs: 3,
        artifact_retention_days: 30
      });
      return fakeResponse(200, {
        billing: {
          workspace: { workspace_id: "ws_api_demo", plan_tier: "pro" },
          billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
          plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
        },
        workspace_settings: {
          ...upsertedMember.liveWorkspaceSettings,
          workspace: { ...upsertedMember.liveWorkspaceSettings.workspace, plan_tier: "pro" },
          billing_account: { status: "active", seat_count: 4, price_book_id: "pro", renewal_at: "2026-07-31T00:00:00+00:00" },
          plan_limits: { daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 },
          capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
          policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 25, max_concurrent_jobs: 3, artifact_retention_days: 30 }
        }
      });
    }
  });

  assert.equal(billingUpdated.liveWorkspaceSettings.workspace.plan_tier, "pro");
  assert.equal(billingUpdated.liveWorkspaceSettings.billing_account.seat_count, 4);
  assert.equal(billingUpdated.liveWorkspaceSettings.plan_limits.daily_runs, 25);

  const issuedToken = await issueWorkspaceApiToken({
    state: billingUpdated,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    payload: { user_id: "researcher_001" },
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/api-tokens");
      assert.equal(options.method, "POST");
      assert.deepEqual(JSON.parse(options.body), { user_id: "researcher_001" });
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
          ...billingUpdated.liveWorkspaceSettings,
          api_tokens: [
            { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true },
            { token_id: "token_abcdef123456", token_hint: "token_...3456", user_id: "researcher_001", role: "editor", issued_at: "2026-06-28T00:06:00Z", active: true, current: false }
          ]
        }
      });
    }
  });

  assert.equal(issuedToken.lastIssuedApiToken.token, "token_abcdef123456");
  assert.equal(issuedToken.liveWorkspaceSettings.api_tokens.length, 2);

  const revokedToken = await revokeWorkspaceApiToken({
    state: issuedToken,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    tokenId: "token_abcdef123456",
    fetchImpl: async (url, options = {}) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/api-tokens/token_abcdef123456/revoke");
      assert.equal(options.method, "POST");
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
          ...issuedToken.liveWorkspaceSettings,
          api_tokens: [
            { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true },
            { token_id: "token_abcdef123456", token_hint: "token_...3456", user_id: "researcher_001", role: "editor", issued_at: "2026-06-28T00:06:00Z", active: false, current: false }
          ]
        }
      });
    }
  });

  assert.equal(revokedToken.liveWorkspaceSettings.api_tokens[1].active, false);
  assert.equal(revokedToken.lastIssuedApiToken, null);
});

test("workspace audit helper loads filtered audit history", async () => {
  const loadedAudit = await loadWorkspaceAuditEvents({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    targetType: "api_token",
    actionPrefix: "api_token.",
    limit: 5,
    fetchImpl: async (url) => {
      assert.equal(
        url,
        "http://127.0.0.1:8011/api/v1/audit-events?target_type=api_token&action_prefix=api_token.&limit=5"
      );
      return fakeResponse(200, {
        audit_history: {
          filters: { target_type: "api_token", action_prefix: "api_token.", limit: 5 },
          audit_events: [
            {
              audit_event_id: "audit_001",
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
  });

  assert.equal(loadedAudit.liveAuditEvents.length, 1);
  assert.equal(loadedAudit.liveAuditQuery.target_type, "api_token");
  assert.equal(loadedAudit.liveAuditEvents[0].action, "api_token.issued");
});

test("detail runtime helpers can bootstrap route-scoped product selection", async () => {
  const projectLoaded = await loadWorkspaceProjectDetail({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    projectId: "project_001",
    fetchImpl: async () => fakeResponse(200, {
      project: { project_id: "project_001", name: "Inbox Coach Launch", slug: "inbox-coach-launch", study_count: 1 }
    })
  });
  assert.equal(projectLoaded.selectedProjectId, "project_001");

  const studyLoaded = await loadWorkspaceStudyDetail({
    state: projectLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    studyId: "study_001",
    fetchImpl: async () => fakeResponse(200, {
      study: { study_id: "study_001", project_id: "project_001", title: "Onboarding hesitation", status: "review_ready", run_count: 1, latest_job_status: "completed" }
    })
  });
  assert.equal(studyLoaded.selectedStudyId, "study_001");
  assert.equal(studyLoaded.selectedProjectId, "project_001");

  const exportLoaded = await loadWorkspaceExportBundleDetail({
    state: studyLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    exportBundleId: "export_001",
    fetchImpl: async () => fakeResponse(200, {
      export_bundle: { export_bundle_id: "export_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Exec review export" }
    })
  });
  assert.equal(exportLoaded.selectedExportBundleId, "export_001");
  assert.equal(exportLoaded.selectedJobId, "job_001");

  const shareLoaded = await loadWorkspaceShareBundleDetail({
    state: exportLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    shareBundleId: "share_001",
    fetchImpl: async () => fakeResponse(200, {
      share_bundle: { share_bundle_id: "share_001", export_bundle_id: "export_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Board share" }
    })
  });
  assert.equal(shareLoaded.selectedShareBundleId, "share_001");
  assert.equal(shareLoaded.selectedExportBundleId, "export_001");

  const supportLoaded = await loadWorkspaceSupportSnapshotDetail({
    state: shareLoaded,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    supportSnapshotId: "support_001",
    fetchImpl: async () => fakeResponse(200, {
      support_snapshot: { support_snapshot_id: "support_001", project_id: "project_001", study_id: "study_001", job_id: "job_001", title: "Provider failure snapshot" }
    })
  });
  assert.equal(supportLoaded.selectedSupportSnapshotId, "support_001");
  assert.equal(supportLoaded.selectedStudyId, "study_001");
  assert.equal(supportLoaded.selectedJobId, "job_001");
});

test("listWorkspaceValidationJobs and detail loading refresh the selected job set", async () => {
  const listed = await listWorkspaceValidationJobs({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async () => fakeResponse(200, {
      jobs: [
        { job_id: "job_001", status: "queued", provider_name: "mock" },
        { job_id: "job_000", status: "completed", provider_name: "mock" }
      ]
    })
  });

  assert.equal(listed.mode, "live");
  assert.equal(listed.selectedJobId, "job_001");

  const detailed = await loadWorkspaceValidationJobDetail({
    state: listed,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    fetchImpl: async () => fakeResponse(200, {
      job: { job_id: "job_001", status: "completed", provider_name: "mock", output_run_path: "runs/job_001" }
    })
  });

  assert.equal(detailed.liveJobs[0].status, "completed");
  assert.equal(detailed.liveEvidenceQuery, null);
});

test("loadWorkspaceEvidenceQuery stores backend query payload and sample-mode helper stays explicit", async () => {
  const selected = selectWorkspaceRuntimeJob({
    ...makeState(),
    mode: "live",
    liveJobs: [{ job_id: "job_001", status: "completed" }]
  }, "job_001");

  const next = await loadWorkspaceEvidenceQuery({
    state: selected,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    queryText: "report",
    activeFamily: "output",
    sortBy: "relevance",
    selectedComparisonRunId: "run_002",
    fetchImpl: async (url) => {
      assert.match(url, /query_text=report/);
      assert.match(url, /active_family=output/);
      assert.match(url, /selected_comparison_run_id=run_002/);
      return fakeResponse(200, {
        query: {
          query_status: "query_ready",
          result_count: 1,
          results: [{ id: "query-run_report" }]
        }
      });
    }
  });

  assert.equal(next.liveEvidenceQuery.query_status, "query_ready");
  assert.equal(next.liveError, null);

  const sample = switchWorkspaceRuntimeToSample(next, { selectedJobId: "job_api_demo_completed" });
  assert.equal(sample.mode, "sample");
  assert.equal(sample.liveEvidenceQuery, null);
  assert.equal(sample.liveSupportDiagnostics, null);
  assert.deepEqual(sample.liveSupportSnapshots, []);
  assert.equal(sample.selectedSupportSnapshotId, null);
  assert.equal(sample.selectedJobId, "job_api_demo_completed");
});

test("loadWorkspaceShellSnapshot hydrates session, jobs, and evidence query in one fetch", async () => {
  const next = await loadWorkspaceShellSnapshot({
    state: {
      ...makeState(),
      liveProjects: [{ project_id: "project_001" }],
      selectedProjectId: "project_001",
      liveStudies: [{ study_id: "study_001" }],
      selectedStudyId: "study_001",
      runtimeSync: { interval_ms: 4000, auto_refresh_enabled: false }
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    queryText: "hesitate",
    activeFamily: "trace",
    sortBy: "newest",
    selectedComparisonRunId: "run_002",
    fetchImpl: async (url) => {
      assert.match(url, /\/api\/v1\/workspace-shell\?/);
      assert.match(url, /query_text=hesitate/);
      assert.match(url, /project_id=project_001/);
      assert.match(url, /study_id=study_001/);
      assert.match(url, /active_family=trace/);
      assert.match(url, /sort_by=newest/);
      assert.match(url, /selected_comparison_run_id=run_002/);
      return fakeResponse(200, {
        snapshot: {
          session: {
            auth: { workspace_id: "ws_api_demo" }
          },
          projects: [
            { project_id: "project_001", name: "Inbox Coach Launch", slug: "inbox-coach-launch", study_count: 1 }
          ],
          selected_project_id: "project_001",
          studies: [
            { study_id: "study_001", project_id: "project_001", title: "Onboarding hesitation", status: "review_ready", run_count: 1, latest_job_status: "completed" }
          ],
          selected_study_id: "study_001",
          export_bundles: [
            { export_bundle_id: "export_001", study_id: "study_001", title: "Exec review export" }
          ],
          selected_export_bundle_id: "export_001",
          share_bundles: [
            { share_bundle_id: "share_001", export_bundle_id: "export_001", title: "Board review share" }
          ],
          selected_share_bundle_id: "share_001",
          support_snapshots: [
            { support_snapshot_id: "support_001", study_id: "study_001", job_id: "job_001", title: "Provider failure snapshot" }
          ],
          selected_support_snapshot_id: "support_001",
          jobs: [
            { job_id: "job_001", status: "completed", provider_name: "mock" }
          ],
          selected_job_id: "job_001",
          provider_runtime: {
            selected_job_boundary: {
              provider_name: "mock",
              evidence_mode: "mock_demo",
              runtime_status: "completed",
              auth_readiness: "not_required"
            },
            catalog: [
              { provider_name: "mock", evidence_mode: "mock_demo", runtime_status: "ready_to_queue" },
              { provider_name: "codex", evidence_mode: "live_synthetic", auth_readiness: "missing_or_unverified" }
            ],
            job_counts: {
              mock_demo: 1,
              live_synthetic: 0,
              unsupported: 0
            }
          },
          evidence_query: {
            query_status: "query_ready",
            result_count: 1,
            results: [{ id: "query-run_report" }]
          },
          runtime_sync: {
            poll_recommended_ms: 6000
          }
        }
      });
    }
  });

  assert.equal(next.mode, "live");
  assert.equal(next.liveSession.auth.workspace_id, "ws_api_demo");
  assert.equal(next.selectedProjectId, "project_001");
  assert.equal(next.selectedStudyId, "study_001");
  assert.equal(next.selectedExportBundleId, "export_001");
  assert.equal(next.selectedShareBundleId, "share_001");
  assert.equal(next.selectedSupportSnapshotId, "support_001");
  assert.equal(next.selectedJobId, "job_001");
  assert.equal(next.liveProviderRuntime.selected_job_boundary.evidence_mode, "mock_demo");
  assert.equal(next.liveProviderRuntime.catalog[1].provider_name, "codex");
  assert.equal(next.liveEvidenceQuery.query_status, "query_ready");
  assert.equal(next.runtimeSync.interval_ms, 6000);
});

test("runtime client surfaces fetch errors without mutating happy-path payloads", async () => {
  const next = await loadWorkspaceRuntimeSession({
    state: {
      ...makeState(),
      liveSession: { auth: { workspace_id: "ws_old" } }
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "bad-token",
    fetchImpl: async () => fakeResponse(401, { message: "Invalid API token." })
  });

  assert.equal(next.sessionError, "Invalid API token.");
  assert.equal(next.liveSession, null);
});
