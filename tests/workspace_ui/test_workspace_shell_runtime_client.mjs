import test from "node:test";
import assert from "node:assert/strict";

import {
  listWorkspaceValidationJobs,
  loadWorkspaceEvidenceQuery,
  loadWorkspaceShellSnapshot,
  loadWorkspaceRuntimeSession,
  loadWorkspaceValidationJobDetail,
  selectWorkspaceRuntimeJob,
  submitWorkspaceValidationJob,
  switchWorkspaceRuntimeToSample
} from "../../demo/workspace_ui_shared/workspace_shell_runtime_client.mjs";

function makeState() {
  return {
    liveJobs: [],
    liveSession: null,
    selectedJobId: null,
    liveEvidenceQuery: null,
    mode: "sample",
    lastApiResponse: null,
    liveError: null,
    sessionError: null
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
    fetchImpl: async (url) => {
      assert.match(url, /query_text=report/);
      assert.match(url, /active_family=output/);
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
  assert.equal(sample.selectedJobId, "job_api_demo_completed");
});

test("loadWorkspaceShellSnapshot hydrates session, jobs, and evidence query in one fetch", async () => {
  const next = await loadWorkspaceShellSnapshot({
    state: {
      ...makeState(),
      runtimeSync: { interval_ms: 4000, auto_refresh_enabled: false }
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api",
    queryText: "hesitate",
    activeFamily: "trace",
    sortBy: "newest",
    fetchImpl: async (url) => {
      assert.match(url, /\/api\/v1\/workspace-shell\?/);
      assert.match(url, /query_text=hesitate/);
      assert.match(url, /active_family=trace/);
      assert.match(url, /sort_by=newest/);
      return fakeResponse(200, {
        snapshot: {
          session: {
            auth: { workspace_id: "ws_api_demo" }
          },
          jobs: [
            { job_id: "job_001", status: "completed", provider_name: "mock" }
          ],
          selected_job_id: "job_001",
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
  assert.equal(next.selectedJobId, "job_001");
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
