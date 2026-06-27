import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveWorkspaceSessionRuntimeBridgeState
} from "../../demo/workspace_ui_shared/workspace_session_runtime_bridge.mjs";

test("session runtime bridge exposes loaded workspace session", () => {
  const bridge = deriveWorkspaceSessionRuntimeBridgeState({
    sessionPayload: {
      auth: {
        workspace_id: "ws_api_demo",
        user_id: "owner_api",
        role: "owner"
      },
      workspace: {
        workspace_id: "ws_api_demo",
        display_name: "Workspace API Demo",
        plan_tier: "trial"
      },
      billing_account: {
        status: "trialing",
        seat_count: 1
      },
      plan_limits: {
        daily_runs: 3,
        max_concurrent_jobs: 1,
        artifact_retention_days: 7
      },
      job_counts: {
        total: 4,
        queued: 1,
        running: 0,
        completed: 2,
        failed: 1
      },
      paths: {
        workspace_root: "C:/runtime/workspaces/ws_api_demo",
        briefs_root: "C:/runtime/workspaces/ws_api_demo/briefs",
        personas_root: "C:/runtime/workspaces/ws_api_demo/personas",
        runs_root: "C:/runtime/workspaces/ws_api_demo/runs"
      },
      capabilities: {
        validation_jobs: true,
        evidence_query: true,
        worker_runtime: true,
        session_auth: true
      },
      synthetic_boundary: "Synthetic evidence only."
    },
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "token-api"
  });

  assert.equal(bridge.session_status, "session_loaded");
  assert.equal(bridge.pill.tone, "completed");
  assert.equal(bridge.metrics.workspace_id, "ws_api_demo");
  assert.equal(bridge.metrics.role, "owner");
  assert.equal(bridge.limit_summary[0].value, 3);
  assert.equal(bridge.job_summary[3].value, 2);
  assert.equal(bridge.endpoint_summary[0].value, "http://127.0.0.1:8011/api/v1/session");
  assert.equal(bridge.capability_cards[1].active, true);
});

test("session runtime bridge keeps missing-token state explicit", () => {
  const bridge = deriveWorkspaceSessionRuntimeBridgeState({
    sessionPayload: null,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: ""
  });

  assert.equal(bridge.session_status, "missing_token");
  assert.equal(bridge.actions.load_workspace_session.enabled, false);
  assert.match(bridge.boundary_warning, /does not upgrade synthetic evidence/i);
});

test("session runtime bridge surfaces auth errors", () => {
  const bridge = deriveWorkspaceSessionRuntimeBridgeState({
    sessionPayload: null,
    apiBaseUrl: "http://127.0.0.1:8011",
    bearerToken: "bad-token",
    lastError: "Invalid API token."
  });

  assert.equal(bridge.session_status, "auth_error");
  assert.equal(bridge.pill.tone, "failed");
  assert.equal(bridge.boundary_warning, "Invalid API token.");
});
