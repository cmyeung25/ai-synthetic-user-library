import test from "node:test";
import assert from "node:assert/strict";

import {
  createWorkspaceShellRuntimeSyncState,
  deriveWorkspaceShellRuntimeSyncView,
  syncWorkspaceShellRuntime
} from "../../demo/workspace_ui_shared/workspace_shell_runtime_sync.mjs";

function fakeResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    }
  };
}

function makeState(overrides = {}) {
  return {
    liveJobs: [],
    liveSession: null,
    selectedJobId: null,
    liveEvidenceQuery: null,
    mode: "sample",
    lastApiResponse: null,
    liveError: null,
    sessionError: null,
    runtimeSync: createWorkspaceShellRuntimeSyncState(),
    ...overrides
  };
}

test("deriveWorkspaceShellRuntimeSyncView reflects auto refresh toggle state", () => {
  const view = deriveWorkspaceShellRuntimeSyncView(createWorkspaceShellRuntimeSyncState({
    autoRefreshEnabled: true,
    intervalMs: 6000
  }));

  assert.equal(view.pill.label, "idle");
  assert.equal(view.actions.toggle_auto_refresh.intent, "stop_auto_refresh");
  assert.equal(view.summary[0].value, "on");
  assert.equal(view.summary[1].value, 6000);
});

test("syncWorkspaceShellRuntime marks missing token explicitly", async () => {
  const next = await syncWorkspaceShellRuntime({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: ""
  });

  assert.equal(next.runtimeSync.heartbeat_status, "missing_token");
  assert.equal(next.runtimeSync.last_action, "await_token");
  assert.equal(next.runtimeSync.is_syncing, false);
});

test("syncWorkspaceShellRuntime can refresh session without live job state", async () => {
  const next = await syncWorkspaceShellRuntime({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    now: () => new Date("2026-06-28T02:00:00.000Z"),
    fetchImpl: async (url) => {
      assert.equal(url, "http://127.0.0.1:8011/api/v1/workspace-shell?query_text=&active_family=all&sort_by=relevance");
      return fakeResponse(200, {
        snapshot: {
          session: {
            auth: { workspace_id: "ws_api_demo", role: "owner" }
          },
          jobs: [],
          selected_job_id: null,
          evidence_query: {
            query_status: "query_pending",
            result_count: 0,
            results: []
          },
          runtime_sync: {
            poll_recommended_ms: 4000
          }
        }
      });
    }
  });

  assert.equal(next.liveSession.auth.workspace_id, "ws_api_demo");
  assert.equal(next.runtimeSync.heartbeat_status, "session_synced");
  assert.equal(next.runtimeSync.last_action, "load_workspace_shell_snapshot");
  assert.equal(next.runtimeSync.sync_count, 1);
  assert.equal(next.runtimeSync.last_synced_at, "2026-06-28T02:00:00.000Z");
});

test("syncWorkspaceShellRuntime refreshes selected live job and completed evidence query", async () => {
  const calls = [];
  const next = await syncWorkspaceShellRuntime({
    state: makeState({
      mode: "live",
      selectedJobId: "job_001",
      liveJobs: [{ job_id: "job_001", status: "queued", provider_name: "mock" }]
    }),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    queryState: {
      queryText: "hesitate",
      activeFamily: "trace",
      sortBy: "newest"
    },
    fetchImpl: async (url) => {
      calls.push(url);
      if (url.includes("/api/v1/workspace-shell?")) {
        assert.match(url, /job_id=job_001/);
        assert.match(url, /query_text=hesitate/);
        assert.match(url, /active_family=trace/);
        assert.match(url, /sort_by=newest/);
        return fakeResponse(200, {
          snapshot: {
            session: {
              auth: { workspace_id: "ws_api_demo", role: "owner" }
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
              selected_replay_step_id: null,
              results: [{ id: "query-run_report" }]
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

  assert.deepEqual(calls, [
    "http://127.0.0.1:8011/api/v1/workspace-shell?query_text=hesitate&active_family=trace&sort_by=newest&job_id=job_001"
  ]);
  assert.equal(next.liveJobs[0].status, "completed");
  assert.equal(next.liveEvidenceQuery.query_status, "query_ready");
  assert.equal(next.runtimeSync.heartbeat_status, "live_synced");
  assert.equal(next.runtimeSync.last_action, "load_workspace_shell_snapshot");
});

test("syncWorkspaceShellRuntime forwards evidence selection overrides through the snapshot endpoint", async () => {
  const next = await syncWorkspaceShellRuntime({
    state: makeState({
      mode: "live",
      selectedJobId: "job_001",
      liveJobs: [{ job_id: "job_001", status: "completed", provider_name: "mock" }]
    }),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    queryState: {
      queryText: "hesitate",
      activeFamily: "trace",
      sortBy: "newest"
    },
    selectedResultId: "query-run_report",
    selectedReplayStepId: "step-03",
    selectedComparisonRunId: "run_002",
    fetchImpl: async (url) => {
      assert.match(url, /selected_result_id=query-run_report/);
      assert.match(url, /selected_replay_step_id=step-03/);
      assert.match(url, /selected_comparison_run_id=run_002/);
      return fakeResponse(200, {
        snapshot: {
          session: {
            auth: { workspace_id: "ws_api_demo", role: "owner" }
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
              selected_comparison_run_id: "run_002"
            },
            results: [{ id: "query-run_report" }]
          },
          runtime_sync: {
            poll_recommended_ms: 5000
          }
        }
      });
    }
  });

  assert.equal(next.liveEvidenceQuery.selected_result_id, "query-run_report");
  assert.equal(next.liveEvidenceQuery.selected_replay_step_id, "step-03");
  assert.equal(next.liveEvidenceQuery.cross_run_comparison.selected_comparison_run_id, "run_002");
  assert.equal(next.runtimeSync.interval_ms, 5000);
});

test("syncWorkspaceShellRuntime surfaces session auth errors as attention", async () => {
  const next = await syncWorkspaceShellRuntime({
    state: makeState(),
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "bad-token",
    fetchImpl: async () => fakeResponse(401, { message: "Invalid API token." })
  });

  assert.equal(next.sessionError, "Invalid API token.");
  assert.equal(next.runtimeSync.heartbeat_status, "attention");
  assert.equal(next.runtimeSync.last_action, "load_workspace_shell_snapshot");
  assert.equal(next.runtimeSync.sync_count, 1);
});
