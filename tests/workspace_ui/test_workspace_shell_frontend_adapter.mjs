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

test("frontend adapter projects provider runtime boundary into the study shell", () => {
  const selectedJob = {
    job_id: "job_codex_001",
    status: "queued",
    provider_name: "codex",
    retry_count: 0,
    metadata: {
      provider_runtime_boundary: {
        provider_name: "codex",
        provider_family: "codex",
        evidence_mode: "live_synthetic",
        is_supported: true,
        is_live_provider: true,
        is_codex_provider: true,
        requires_auth: true,
        auth_readiness: "missing_or_unverified",
        runtime_status: "missing_auth",
        failure_kind: "missing_auth",
        boundary_label: "Live synthetic evidence",
        boundary_message: "Codex auth is required before this run can produce live synthetic evidence.",
        next_actions: [
          "Sign in to Codex or configure a supported OpenAI API credential.",
          "Retry from the study surface after auth is ready."
        ]
      }
    }
  };
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "queued"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: {
      ...createWorkspaceValidationBridgeDemoContext(),
      provider_name: "codex",
      project_id: "project_001",
      study_id: "study_001"
    },
    jobList: [selectedJob],
    selectedJob,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob,
    providerRuntime: {
      selected_job_boundary: selectedJob.metadata.provider_runtime_boundary,
      catalog: [
        {
          provider_name: "mock",
          evidence_mode: "mock_demo",
          runtime_status: "ready_to_queue",
          auth_readiness: "not_required",
          boundary_label: "Mock demo evidence"
        },
        {
          provider_name: "codex",
          evidence_mode: "live_synthetic",
          runtime_status: "missing_auth",
          auth_readiness: "missing_or_unverified",
          boundary_label: "Live synthetic evidence",
          is_live_provider: true
        }
      ],
      job_counts: {
        mock_demo: 0,
        live_synthetic: 1,
        unsupported: 0
      }
    },
    mode: "live",
    lastApiResponse: { job: selectedJob }
  });

  assert.equal(frontend.pills.provider_runtime.tone, "failed");
  assert.equal(frontend.pills.provider_runtime.label, "missing_auth");
  assert.equal(frontend.selected_job_summary[3].value, "live_synthetic");
  assert.equal(frontend.selected_job_summary[4].value, "missing_auth");
  assert.equal(frontend.provider_runtime_surface.selected_boundary.provider_name, "codex");
  assert.equal(frontend.provider_runtime_surface.summary[1].value, "live_synthetic");
  assert.equal(frontend.provider_runtime_surface.summary[3].value, "missing_or_unverified");
  assert.equal(frontend.provider_runtime_surface.detail_cards[0].body.includes("Codex auth is required"), true);
  assert.equal(frontend.provider_runtime_surface.detail_cards[1].body.includes("Sign in to Codex"), true);
  assert.equal(frontend.provider_runtime_surface.catalog.length, 2);
});

test("frontend adapter projects selected project and study summaries into product surface", () => {
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "queued"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: {
      ...createWorkspaceValidationBridgeDemoContext(),
      project_id: "project_001",
      study_id: "study_001"
    },
    jobList: [],
    selectedJob: null,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedProject: {
      project_id: "project_001",
      name: "Inbox Coach Launch",
      slug: "inbox-coach-launch",
      study_count: 2,
      share_bundle_count: 1,
      latest_study_id: "study_001"
    },
    selectedStudy: {
      study_id: "study_001",
      project_id: "project_001",
      title: "Onboarding hesitation",
      status: "review_ready",
      run_count: 1,
      evidence_view_count: 2,
      decision_log_count: 1,
      export_bundle_count: 2,
      share_bundle_count: 1,
      latest_job_status: "completed",
      first_task: "connect CRM"
    },
    projects: [
      {
        project_id: "project_001",
        name: "Inbox Coach Launch",
        slug: "inbox-coach-launch",
        study_count: 2,
        share_bundle_count: 1,
        latest_study_id: "study_001"
      }
    ],
    studies: [
      {
        study_id: "study_001",
        project_id: "project_001",
        title: "Onboarding hesitation",
        status: "review_ready",
        run_count: 1,
        evidence_view_count: 2,
        decision_log_count: 1,
        export_bundle_count: 2,
        share_bundle_count: 1,
        latest_job_status: "completed",
        first_task: "connect CRM"
      }
    ],
    selectedExportBundle: {
      export_bundle_id: "export_001",
      study_id: "study_001",
      job_id: "job_001",
      title: "Exec review export",
      status: "published",
      export_format: "report_csv",
      exported_file_count: 1,
      share_bundle_count: 1,
      synthetic_boundary: "Synthetic evidence only."
    },
    exportBundles: [
      {
        export_bundle_id: "export_001",
        study_id: "study_001",
        job_id: "job_001",
        title: "Exec review export",
        status: "published",
        export_format: "report_csv",
        exported_file_count: 1,
        share_bundle_count: 1,
        synthetic_boundary: "Synthetic evidence only."
      }
    ],
    selectedShareBundle: {
      share_bundle_id: "share_001",
      export_bundle_id: "export_001",
      title: "Board share",
      status: "published",
      public_path: "/public/v1/share-bundles/shk_001",
      share_file_count: 2,
      expires_at: null,
      synthetic_boundary: "Synthetic evidence only."
    },
    shareBundles: [
      {
        share_bundle_id: "share_001",
        export_bundle_id: "export_001",
        title: "Board share",
        status: "published",
        public_path: "/public/v1/share-bundles/shk_001",
        share_file_count: 2,
        expires_at: null,
        synthetic_boundary: "Synthetic evidence only."
      }
    ],
    mode: "live",
    lastApiResponse: null
  });

  assert.equal(frontend.metrics.selected_project_id, "project_001");
  assert.equal(frontend.metrics.selected_study_id, "study_001");
  assert.equal(frontend.metrics.selected_export_bundle_id, "export_001");
  assert.equal(frontend.metrics.selected_share_bundle_id, "share_001");
  assert.equal(frontend.product_surface.projects[0].selected, true);
  assert.equal(frontend.product_surface.studies[0].selected, true);
  assert.equal(frontend.product_surface.export_bundles[0].selected, true);
  assert.equal(frontend.product_surface.share_bundles[0].selected, true);
  assert.equal(frontend.product_surface.selected_project_summary[0].value, "Inbox Coach Launch");
  assert.equal(frontend.product_surface.selected_study_summary[3].value, "2 items");
  assert.equal(frontend.product_surface.selected_study_summary[4].value, "1 item");
  assert.equal(frontend.product_surface.selected_study_summary[5].value, "not loaded");
  assert.equal(frontend.product_surface.selected_study_summary[9].value, "connect CRM");
  assert.equal(frontend.product_surface.selected_export_bundle_summary[0].value, "Exec review export");
  assert.equal(frontend.product_surface.selected_share_bundle_summary[0].value, "Board share");
});

test("frontend adapter projects saved evidence views and decision logs into study collaboration surface", () => {
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "completed"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: {
      ...createWorkspaceValidationBridgeDemoContext(),
      project_id: "project_001",
      study_id: "study_001"
    },
    jobList: [createWorkspaceValidationBridgeDemoJob("completed")],
    selectedJob: createWorkspaceValidationBridgeDemoJob("completed"),
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedProject: {
      project_id: "project_001",
      name: "Inbox Coach Launch",
      slug: "inbox-coach-launch",
      study_count: 2,
      evidence_view_count: 1,
      decision_log_count: 1
    },
    selectedStudy: {
      study_id: "study_001",
      project_id: "project_001",
      title: "Onboarding hesitation",
      status: "review_ready",
      run_count: 1,
      evidence_view_count: 1,
      decision_log_count: 1,
      latest_job_status: "completed",
      first_task: "connect CRM"
    },
    selectedEvidenceView: {
      evidence_view_id: "view_001",
      study_id: "study_001",
      job_id: "job_001",
      title: "Trust blockers review",
      note: "Focus on output evidence first",
      active_family: "output",
      sort_by: "relevance"
    },
    selectedDecisionLog: {
      decision_log_id: "decision_001",
      study_id: "study_001",
      job_id: "job_001",
      evidence_view_id: "view_001",
      title: "Do not ship yet",
      decision_summary: "Trust blockers still dominate.",
      rationale: "Observed objections repeat across personas.",
      review_status: "in_review",
      comment_count: 2,
      review_thread_count: 1,
      latest_review_note: "Needs one cross-run check before approval."
    },
    studies: [
      {
        study_id: "study_001",
        project_id: "project_001",
        title: "Onboarding hesitation",
        status: "review_ready",
        run_count: 1,
        evidence_view_count: 1,
        decision_log_count: 1,
        latest_job_status: "completed",
        first_task: "connect CRM"
      }
    ],
    evidenceViews: [
      {
        evidence_view_id: "view_001",
        study_id: "study_001",
        job_id: "job_001",
        title: "Trust blockers review",
        note: "Focus on output evidence first",
        active_family: "output",
        sort_by: "relevance"
      }
    ],
    decisionLogs: [
      {
        decision_log_id: "decision_001",
        study_id: "study_001",
        job_id: "job_001",
        evidence_view_id: "view_001",
        title: "Do not ship yet",
        decision_summary: "Trust blockers still dominate.",
        rationale: "Observed objections repeat across personas.",
        review_status: "in_review",
        comment_count: 2,
        review_thread_count: 1,
        latest_review_note: "Needs one cross-run check before approval."
      }
    ],
    decisionComments: [
      {
        decision_comment_id: "decision_comment_001",
        decision_log_id: "decision_001",
        anchor_kind: "general",
        body: "Please justify why this is not only one-run noise.",
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
    ],
    studyActivity: [
      {
        activity_id: "activity_001",
        action: "evidence_view.saved",
        event_family: "collaboration",
        tone: "active",
        headline: "Saved evidence view",
        summary: "Trust blockers review was saved for the selected study.",
        actor_user_id: "owner_api",
        actor_role: "owner",
        created_at: "2026-06-28T02:10:00+00:00",
        route_kind: "evidence_view",
        route_id: "view_001",
        route_path: "/app/evidence-views/view_001"
      },
      {
        activity_id: "activity_002",
        action: "decision_log.review_status_updated",
        event_family: "review",
        tone: "active",
        headline: "Decision review updated",
        summary: "The review moved to in_review.",
        actor_user_id: "reviewer_001",
        actor_role: "editor",
        created_at: "2026-06-28T02:12:00+00:00",
        route_kind: "decision_log",
        route_id: "decision_001",
        route_path: "/app/decision-logs/decision_001"
      }
    ],
    mode: "live",
    lastApiResponse: null
  });

  assert.equal(frontend.metrics.selected_evidence_view_id, "view_001");
  assert.equal(frontend.metrics.selected_decision_log_id, "decision_001");
  assert.equal(frontend.product_surface.studies[0].evidence_view_count, 1);
  assert.equal(frontend.product_surface.studies[0].decision_log_count, 1);
  assert.equal(frontend.product_surface.evidence_views[0].selected, true);
  assert.equal(frontend.product_surface.decision_logs[0].selected, true);
  assert.equal(frontend.product_surface.selected_study_summary[3].value, "1 item");
  assert.equal(frontend.product_surface.selected_study_summary[4].value, "1 item");
  assert.equal(frontend.product_surface.selected_study_summary[5].value, "2 items");
  assert.equal(frontend.product_surface.study_activity.length, 2);
  assert.equal(frontend.product_surface.study_activity[0].route_kind, "evidence_view");
  assert.equal(frontend.product_surface.study_activity_summary[0].value, "2 items");
  assert.equal(frontend.product_surface.study_activity_summary[1].value, "Saved evidence view");
  assert.equal(frontend.product_surface.selected_evidence_view_summary[0].value, "Trust blockers review");
  assert.equal(frontend.product_surface.selected_decision_log_summary[0].value, "Do not ship yet");
  assert.equal(frontend.product_surface.selected_decision_log_summary[5].value, "in_review");
  assert.equal(frontend.product_surface.decision_review_summary[0].value, "in_review");
  assert.equal(frontend.product_surface.decision_review_comments.length, 2);
  assert.equal(frontend.product_surface.decision_review_comments[1].parent_comment_id, "decision_comment_001");
  assert.equal(frontend.decision_review_surface.pill.label, "in_review");
  assert.equal(frontend.actions.approve_decision_log.enabled, true);
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
  assert.equal(frontend.review_surface.evidence_coverage_cards.length, 5);
  assert.equal(frontend.review_surface.replay_focus_summary[0].label, "replay step");
});

test("frontend adapter projects support diagnostics and support snapshots into the product shell", () => {
  const selectedJob = createWorkspaceValidationBridgeDemoJob("failed");
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "failed",
    attemptCount: 1,
    failureReason: "Unknown provider: unknown-provider"
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: {
      ...createWorkspaceValidationBridgeDemoContext(),
      project_id: "project_001",
      study_id: "study_001"
    },
    jobList: [selectedJob],
    selectedJob,
    apiBaseUrl: "http://127.0.0.1:8011"
  });

  const frontend = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob: {
      ...selectedJob,
      job_id: "job_001",
      status: "failed",
      provider_name: "unknown-provider",
      last_error: "Unknown provider: unknown-provider"
    },
    selectedSupportSnapshot: {
      support_snapshot_id: "support_001",
      title: "Provider failure snapshot",
      status: "generated",
      summary: "Unknown provider: unknown-provider",
      job_id: "job_001",
      run_id: "run_001"
    },
    supportSnapshots: [
      {
        support_snapshot_id: "support_001",
        title: "Provider failure snapshot",
        status: "generated",
        summary: "Unknown provider: unknown-provider",
        job_id: "job_001"
      }
    ],
    supportDiagnostics: {
      selected_job_id: "job_001",
      submission_gate: {
        status: "blocked",
        blocked_reason_count: 1,
        blocked_reasons: [
          {
            code: "concurrency_limit_reached",
            message: "Workspace reached the max concurrent job limit (1).",
            next_action: "Wait for an in-flight run to finish or move to a higher plan limit."
          }
        ]
      },
      job_diagnostic: {
        job_id: "job_001",
        status: "failed",
        provider_name: "unknown-provider",
        failure_category: "provider_configuration",
        summary: "Unknown provider: unknown-provider",
        retry_count: 1,
        created_at: "2026-06-28T02:00:00+00:00",
        started_at: "2026-06-28T02:00:10+00:00",
        finished_at: "2026-06-28T02:00:30+00:00",
        can_retry: true,
        can_cancel: false,
        artifact_deleted_at: null,
        next_actions: [
          "Inspect the failed run inputs and retry from the study surface.",
          "Check provider_name or backend configuration before retrying."
        ]
      },
      recent_failed_jobs: [
        {
          job_id: "job_001",
          status: "failed",
          provider_name: "unknown-provider",
          retry_count: 1,
          project_id: "project_001",
          study_id: "study_001",
          run_id: "run_001",
          created_at: "2026-06-28T02:00:00+00:00",
          started_at: "2026-06-28T02:00:10+00:00",
          finished_at: "2026-06-28T02:00:30+00:00",
          last_error: "Unknown provider: unknown-provider"
        }
      ],
      support_snapshot_count: 1
    },
    mode: "live",
    lastApiResponse: null
  });

  assert.equal(frontend.metrics.selected_support_snapshot_id, "support_001");
  assert.equal(frontend.product_surface.support_snapshots.length, 1);
  assert.equal(frontend.product_surface.support_snapshots[0].selected, true);
  assert.equal(frontend.product_surface.selected_support_snapshot_summary[0].value, "Provider failure snapshot");
  assert.equal(frontend.support_surface.submission_gate_summary[0].value, "blocked");
  assert.equal(frontend.support_surface.submission_gate_summary[1].value, 1);
  assert.equal(frontend.support_surface.blocked_reasons[0].code, "concurrency_limit_reached");
  assert.equal(frontend.support_surface.job_diagnostic_summary[1].value, "provider_configuration");
  assert.equal(frontend.support_surface.job_diagnostic_summary[3].value, 1);
  assert.equal(frontend.support_surface.job_diagnostic_cards[0].title, "provider_configuration");
  assert.equal(frontend.support_surface.job_diagnostic_cards[1].body.includes("retry"), true);
  assert.equal(frontend.support_surface.recent_failures.length, 1);
  assert.equal(frontend.support_surface.recent_failures[0].provider_name, "unknown-provider");
  assert.equal(frontend.actions.retry_selected_job.enabled, true);
  assert.equal(frontend.actions.cancel_selected_job.enabled, false);
});

test("frontend adapter projects workspace settings, members, and issued-token state", () => {
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
    workspaceSettings: {
      auth: { workspace_id: "ws_api_demo", user_id: "owner_api", role: "owner" },
      workspace: { workspace_id: "ws_api_demo", display_name: "Workspace API Demo", plan_tier: "trial", status: "active" },
      billing_account: { status: "trialing", seat_count: 1, price_book_id: "trial", renewal_at: null },
      plan_limits: { daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 },
      members: [
        { user_id: "owner_api", role: "owner", joined_at: "2026-06-28T00:00:00Z" },
        { user_id: "researcher_001", role: "editor", joined_at: "2026-06-28T00:05:00Z" }
      ],
      api_tokens: [
        { token_id: "token_owner", token_hint: "token_...wner", user_id: "owner_api", role: "owner", issued_at: "2026-06-28T00:00:00Z", active: true, current: true },
        { token_id: "token_abcdef123456", token_hint: "token_...3456", user_id: "researcher_001", role: "editor", issued_at: "2026-06-28T00:06:00Z", active: false, current: false }
      ],
      capabilities: { workspace_settings: true, member_admin: true, token_admin: true, billing_mutation: true, billing_overview: true },
      policies: { region_code: "HK", data_residency_region: "ap-east-1", daily_runs: 3, max_concurrent_jobs: 1, artifact_retention_days: 7 }
    },
    lastIssuedApiToken: {
      token: "token_abcdef123456",
      token_hint: "token_...3456",
      user_id: "researcher_001",
      role: "editor"
    },
    auditEvents: [
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
    ],
    auditQuery: { target_type: "api_token", action_prefix: "api_token.", limit: 5 },
    mode: "live",
    lastApiResponse: null
  });

  assert.equal(frontend.product_surface.workspace_settings_summary[0].value, "Workspace API Demo");
  assert.equal(frontend.product_surface.workspace_billing_summary[1].value, 1);
  assert.equal(frontend.product_surface.workspace_billing_summary[2].value, "trial");
  assert.equal(frontend.product_surface.workspace_policy_summary[4].value, 7);
  assert.equal(frontend.product_surface.workspace_members.length, 2);
  assert.equal(frontend.product_surface.workspace_members[0].current, true);
  assert.equal(frontend.product_surface.workspace_members[1].role, "editor");
  assert.equal(frontend.product_surface.workspace_api_tokens.length, 2);
  assert.equal(frontend.product_surface.workspace_api_tokens[1].active, false);
  assert.equal(frontend.product_surface.last_issued_api_token_summary[0].value, "token_abcdef123456");
  assert.equal(frontend.product_surface.workspace_audit_summary[0].value, "1 item");
  assert.equal(frontend.product_surface.workspace_audit_events[0].summary, "user_id: researcher_001 | role: editor");
});

test("frontend adapter exposes queued-job cancel action and hides retry until failure", () => {
  const selectedJob = {
    ...createWorkspaceValidationBridgeDemoJob("queued"),
    job_id: "job_queued_001",
    status: "queued",
    provider_name: "mock",
    retry_count: 0
  };
  const bundle = buildBundle({
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    lifecycle: "queued",
    attemptCount: 0
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

  assert.equal(frontend.actions.cancel_selected_job.enabled, true);
  assert.equal(frontend.actions.retry_selected_job.enabled, false);
  assert.equal(frontend.selected_job_summary.find((row) => row.id === "retry_count").value, 0);
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
    facet_counts: { all: 4, input: 0, trace: 1, analysis: 1, output: 2 },
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
    replay_sequence: [],
    comparison_context: {
      selected_family_result_count: 1,
      selected_family_replay_result_count: 0,
      comparison_candidates: [
        {
          id: "query-raw_responses",
          artifact_id: "raw_responses.json",
          title: "Raw responses",
          family: "trace",
          kind: "raw_responses",
          artifact_path: "runs/demo/raw_responses.json",
          summary: "Persona-level raw response payloads.",
          relevance_score: 1,
          relation_note: "neighboring replay-bearing evidence"
        }
      ],
      note: "Selected evidence has no direct replay steps. Compare with replay-bearing artifacts for execution context."
    },
    replay_context: {
      selected_result_has_replay: false,
      replay_result_count: 1,
      selected_family_replay_result_count: 0,
      note: "Selected evidence has no replay steps. 1 other visible result(s) carry replay context."
    },
    cross_run_comparison: {
      comparison_run_count: 1,
      selected_comparison_run_id: "run_002",
      selected_comparison_job_id: "job_002",
      note: "1 comparable completed run is available for cross-run review.",
      candidate_runs: [
        {
          run_id: "run_002",
          job_id: "job_002",
          run_kind: "validation_run",
          status: "completed",
          relation_note: "same brief",
          result_count: 2,
          replay_result_count: 1,
          top_result_title: "Raw responses"
        }
      ],
      selected_comparison_run: {
        run_id: "run_002",
        job_id: "job_002",
        note: "Compare same-kind artifacts across runs to check whether the same signal repeats under the same evidence surface.",
        relation_note: "same brief",
        recommended_result_id: "query-cross-run-raw_responses",
        recommended_result_title: "Raw responses",
        recommended_result_reason: "A same-kind artifact is the closest cross-run comparison for the current evidence focus.",
        comparison_results: [
          {
            id: "query-cross-run-raw_responses",
            artifact_id: "raw_responses.json",
            title: "Raw responses",
            family: "trace",
            kind: "raw_responses",
            artifact_path: "runs/demo-2/raw_responses.json",
            summary: "Persona-level raw response payloads.",
            relevance_score: 2
          }
        ]
      }
    },
    evidence_reliability: {
      contract_version: "workspace-evidence-reliability/v0-draft",
      review_status: "reliability_ready",
      stability_label: "comparison_available",
      stability_score: 52,
      selected_signal_id: "output:report",
      signal_terms: ["risk"],
      supporting_evidence: [
        {
          source: "cross_run",
          id: "query-cross-run-raw_responses",
          run_id: "run_002",
          artifact_id: "raw_responses.json",
          title: "Raw responses",
          family: "trace",
          kind: "raw_responses",
          relation: "cross-run comparable evidence",
          summary: "Persona-level raw response payloads."
        }
      ],
      contradicting_evidence: [],
      missing_context: [
        {
          id: "human_validation_gap",
          label: "human validation gap",
          severity: "high",
          note: "Synthetic evidence has not been calibrated against human outcome data for this claim."
        }
      ],
      calibration_records: [
        {
          id: "synthetic_boundary",
          status: "requires_human_validation",
          label: "Synthetic evidence boundary",
          note: "This reliability review is not human market proof."
        },
        {
          id: "repeatability",
          status: "comparison_available",
          label: "Repeatability signal",
          score: 52,
          supporting_count: 1,
          contradicting_count: 0
        }
      ],
      synthetic_boundary: "Synthetic evidence only. Reliability labels require human calibration."
    },
    audit_lineage: {
      contract_version: "workspace-evidence-audit-lineage/v0-draft",
      source_run: {
        run_id: "run_001",
        run_kind: "validation_run",
        brief_id: "brief_001",
        research_goal: "Find onboarding risk.",
        interview_mode: "prototype_validation",
        finished_at: "2026-06-28T02:00:00+00:00",
        output_path: "runs/demo",
        primary_artifact_path: "runs/demo/run.json"
      },
      selected_evidence: {
        result_id: "query-run_report",
        artifact_id: "report.json",
        family: "output",
        kind: "report",
        artifact_path: "runs/demo/report.json",
        signal_id: "output:report",
        signal_terms: ["risk"]
      },
      replay: {
        selected_replay_step_id: null,
        selected_replay_step_title: null,
        selected_replay_step_timestamp: null
      },
      comparison_set: {
        comparison_run_count: 1,
        candidate_run_ids: ["run_002"],
        selected_comparison_run_id: "run_002",
        selected_comparison_result_id: "query-cross-run-raw_responses"
      }
    }
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
  assert.equal(frontend.review_surface.evidence_coverage_cards[0].active, true);
  assert.equal(frontend.review_surface.related_results.length, 1);
  assert.equal(frontend.review_surface.related_results[0].relation_note, "neighboring replay-bearing evidence");
  assert.equal(frontend.review_surface.related_results_note, "Selected evidence has no direct replay steps. Compare with replay-bearing artifacts for execution context.");
  assert.equal(frontend.review_surface.replay_focus_detail[0].title, "No replay focus");
  assert.equal(frontend.review_surface.replay_note, "Selected evidence has no replay steps. 1 other visible result(s) carry replay context.");
  assert.equal(frontend.review_surface.selected_comparison_run_id, "run_002");
  assert.equal(frontend.review_surface.cross_run_candidates.length, 1);
  assert.equal(frontend.review_surface.cross_run_candidates[0].selected, true);
  assert.equal(frontend.review_surface.cross_run_summary[1].value, "run_002");
  assert.equal(frontend.review_surface.cross_run_detail[0].body.includes("same signal repeats"), true);
  assert.equal(frontend.review_surface.cross_run_result_cards[0].recommended, true);
  assert.equal(frontend.review_surface.cross_run_note, "1 comparable completed run is available for cross-run review.");
  assert.equal(frontend.review_surface.evidence_reliability.stability_label, "comparison_available");
  assert.equal(frontend.review_surface.reliability_summary[1].value, "comparison_available");
  assert.equal(frontend.review_surface.reliability_summary[2].value, 52);
  assert.equal(frontend.review_surface.calibration_cards[0].title, "Synthetic evidence boundary");
  assert.equal(frontend.review_surface.audit_lineage_summary[0].value, "run_001");
  assert.equal(frontend.review_surface.selected_evidence_summary[5].value, "reliability_ready");
  assert.equal(frontend.review_surface.selected_evidence_detail.some((card) => card.id === "reliability_status"), true);
  assert.equal(frontend.actions.load_live_evidence_query.enabled, true);
  assert.equal(frontend.actions.apply_evidence_query.enabled, true);
});

test("frontend adapter exposes replay focus detail when backend query includes trace steps", () => {
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
    selected_result_id: "query-raw_responses",
    selected_artifact_id: "raw_responses.json",
    selected_replay_step_id: "response-02",
    active_family: "trace",
    facet_counts: { all: 3, input: 0, trace: 2, analysis: 1, output: 0 },
    result_count: 3,
    boundary_warning: "Synthetic evidence only.",
    results: [
      {
        id: "query-raw_responses",
        artifact_id: "raw_responses.json",
        title: "Persona responses",
        family: "trace",
        kind: "raw_responses",
        artifact_path: "runs/demo/raw_responses.json",
        summary: "Persona-level raw response payloads.",
        relevance_score: 4
      },
      {
        id: "query-stage_results",
        artifact_id: "stage_results.json",
        title: "Stage results",
        family: "trace",
        kind: "stage_results",
        artifact_path: "runs/demo/stage_results.json",
        summary: "Execution-stage status summary.",
        relevance_score: 3
      },
      {
        id: "query-summary",
        artifact_id: "summary.json",
        title: "Run summary",
        family: "analysis",
        kind: "run_summary",
        artifact_path: "runs/demo/summary.json",
        summary: "Run summary with status completed.",
        relevance_score: 1
      }
    ],
    selected_result: {
      id: "query-raw_responses",
      artifact_id: "raw_responses.json",
      title: "Persona responses",
      family: "trace",
      kind: "raw_responses",
      artifact_path: "runs/demo/raw_responses.json",
      summary: "Persona-level raw response payloads."
    },
    linked_artifact: {
      id: "raw_responses.json",
      title: "Persona responses",
      artifact_path: "runs/demo/raw_responses.json",
      summary: "Persona-level raw response payloads.",
      detail_lines: [
        "su_0002: objection procurement review | try signal clearer onboarding evidence"
      ]
    },
    replay_sequence: [
      {
        id: "response-01",
        title: "su_0001 response",
        timestamp: "response 1",
        note: "Objection: integration effort. Try signal: clearer migration path."
      },
      {
        id: "response-02",
        title: "su_0002 response",
        timestamp: "response 2",
        note: "Objection: procurement review. Try signal: clearer onboarding evidence."
      }
    ],
    replay_focus_step: {
      id: "response-02",
      title: "su_0002 response",
      timestamp: "response 2",
      note: "Objection: procurement review. Try signal: clearer onboarding evidence."
    },
    comparison_context: {
      selected_family_result_count: 2,
      selected_family_replay_result_count: 2,
      comparison_candidates: [
        {
          id: "query-stage_results",
          artifact_id: "stage_results.json",
          title: "Stage results",
          family: "trace",
          kind: "stage_results",
          artifact_path: "runs/demo/stage_results.json",
          summary: "Execution-stage status summary.",
          relevance_score: 3,
          relation_note: "same family with replay context"
        },
        {
          id: "query-summary",
          artifact_id: "summary.json",
          title: "Run summary",
          family: "analysis",
          kind: "run_summary",
          artifact_path: "runs/demo/summary.json",
          summary: "Run summary with status completed.",
          relevance_score: 1,
          relation_note: "neighboring evidence surface"
        }
      ],
      note: "Use same-family evidence to check whether the same signal repeats across nearby artifacts."
    },
    replay_context: {
      selected_result_has_replay: true,
      replay_result_count: 2,
      selected_family_replay_result_count: 2,
      note: "2 replay step(s) are linked to the selected evidence."
    }
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

  assert.equal(frontend.review_surface.evidence_coverage_cards[1].active, true);
  assert.equal(frontend.review_surface.replay_focus_summary[0].value, "su_0002 response");
  assert.equal(frontend.review_surface.replay_focus_detail[0].body.includes("procurement review"), true);
  assert.equal(frontend.review_surface.related_results.length, 2);
  assert.equal(frontend.review_surface.related_results[0].relation_note, "same family with replay context");
  assert.equal(frontend.review_surface.related_results_note, "Use same-family evidence to check whether the same signal repeats across nearby artifacts.");
  assert.equal(frontend.review_surface.replay_note, "2 replay step(s) are linked to the selected evidence. Current focus: response 2.");
});
