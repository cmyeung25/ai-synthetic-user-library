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

test("controller can submit job and reload session through shared app boundary", async () => {
  const fetchCalls = [];
  const controller = createWorkspaceShellAppController({
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push({ url, method: options.method || "GET" });
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
  assert.equal(model.frontendState.metrics.selected_job_id, "job_001");
  assert.equal(model.sessionBridgeState.metrics.workspace_id, "ws_api_demo");
  assert.equal(model.jobs[0].job_id, "job_001");
});

test("controller syncRuntime updates heartbeat and completed evidence state", async () => {
  const controller = createWorkspaceShellAppController({
    now: () => new Date("2026-06-28T03:00:00.000Z"),
    fetchImpl: async (url) => {
      if (url.includes("/api/v1/workspace-shell?")) {
        assert.match(url, /job_id=job_001/);
        assert.match(url, /query_text=hesitate/);
        assert.match(url, /active_family=trace/);
        assert.match(url, /sort_by=newest/);
        assert.match(url, /selected_result_id=query-run_report/);
        assert.match(url, /selected_replay_step_id=step-03/);
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
  controller.getState().liveJobs = [{ job_id: "job_001", status: "queued", provider_name: "mock" }];

  await controller.syncRuntime({
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    briefPath: "briefs/brief.json",
    personaDir: "personas",
    selectedResultId: "query-run_report",
    selectedReplayStepId: "step-03",
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
