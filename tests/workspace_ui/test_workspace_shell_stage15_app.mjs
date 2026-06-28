import test from "node:test";
import assert from "node:assert/strict";

import {
  clearPersistedStage15HostedSession,
  deriveStage15HostedBootstrap,
  persistStage15HostedSession,
  readPersistedStage15HostedSession
} from "../../demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs";

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, String(value));
    },
    removeItem(key) {
      values.delete(key);
    }
  };
}

test("deriveStage15HostedBootstrap preserves same-origin hosted shell bootstrap inputs", () => {
  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: {
      origin: "http://127.0.0.1:8011",
      pathname: "/app/studies/study_001",
      search: "?token=token-api&api_base_url=http%3A%2F%2F127.0.0.1%3A8011"
    },
    routeContext: {
      route_kind: "study",
      study_id: "study_001"
    }
  });

  assert.equal(bootstrap.hostedRouteEnabled, true);
  assert.equal(bootstrap.hostedApiBase, "http://127.0.0.1:8011");
  assert.equal(bootstrap.hostedToken, "token-api");
  assert.equal(bootstrap.hostedRouteState.routeKind, "study");
  assert.equal(bootstrap.routeSelection.studyId, "study_001");
});

test("deriveStage15HostedBootstrap preserves collaboration-object hosted route selection", () => {
  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: {
      origin: "http://127.0.0.1:8011",
      pathname: "/app/evidence-views/evidence_view_001",
      search: "?token=token-api&api_base_url=http%3A%2F%2F127.0.0.1%3A8011"
    },
    routeContext: {
      route_kind: "evidence_view",
      evidence_view_id: "evidence_view_001"
    }
  });

  assert.equal(bootstrap.hostedRouteEnabled, true);
  assert.equal(bootstrap.hostedRouteState.routeKind, "evidence_view");
  assert.equal(bootstrap.routeSelection.evidenceViewId, "evidence_view_001");
});

test("deriveStage15HostedBootstrap keeps static file usage explicit when not on hosted app routes", () => {
  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: {
      origin: "file://",
      pathname: "/demo/workspace_ui_moss_stage15/index.html",
      search: ""
    },
    routeContext: {}
  });

  assert.equal(bootstrap.hostedRouteEnabled, false);
  assert.equal(bootstrap.hostedApiBase, "");
  assert.equal(bootstrap.hostedToken, "");
  assert.equal(bootstrap.hostedRouteState.routeKind, "workspace");
});

test("persisted hosted session can be stored, read back, and cleared", () => {
  const storage = createMemoryStorage();

  assert.equal(
    persistStage15HostedSession({
      storageLike: storage,
      bearerToken: "token-saved"
    }),
    false
  );
  assert.equal(readPersistedStage15HostedSession({ storageLike: storage }).bearerToken, "");
  assert.equal(clearPersistedStage15HostedSession({ storageLike: storage }), true);
  assert.equal(readPersistedStage15HostedSession({ storageLike: storage }).hasSavedToken, false);
});

test("deriveStage15HostedBootstrap prefers server-backed hosted session flow when query token is missing", () => {
  const storage = createMemoryStorage();
  persistStage15HostedSession({
    storageLike: storage,
    bearerToken: "token-persisted"
  });

  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: {
      origin: "http://127.0.0.1:8011",
      pathname: "/app/workspace",
      search: ""
    },
    routeContext: {},
    storageLike: storage
  });

  assert.equal(bootstrap.hostedRouteEnabled, true);
  assert.equal(bootstrap.hostedToken, "");
  assert.equal(bootstrap.hostedTokenSource, "server_session");
});

test("deriveStage15HostedBootstrap prefers explicit query token over persisted hosted session token", () => {
  const storage = createMemoryStorage();
  persistStage15HostedSession({
    storageLike: storage,
    bearerToken: "token-persisted"
  });

  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: {
      origin: "http://127.0.0.1:8011",
      pathname: "/app/workspace",
      search: "?token=token-query"
    },
    routeContext: {},
    storageLike: storage
  });

  assert.equal(bootstrap.hostedToken, "token-query");
  assert.equal(bootstrap.hostedTokenSource, "query");
});
