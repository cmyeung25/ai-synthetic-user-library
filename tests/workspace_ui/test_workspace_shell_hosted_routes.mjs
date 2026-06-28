import test from "node:test";
import assert from "node:assert/strict";

import {
  createHostedWorkspaceRouteState,
  deriveHostedWorkspaceRoutePath,
  normalizeHostedWorkspaceRouteKind
} from "../../demo/workspace_ui_shared/workspace_shell_hosted_routes.mjs";

test("createHostedWorkspaceRouteState prefers backend route context and query fallbacks", () => {
  const routeState = createHostedWorkspaceRouteState({
    routeContext: {
      route_kind: "study",
      study_id: "study_001"
    },
    pathname: "/app/workspace",
    search: "?token=token-api&project_id=project_001"
  });

  assert.equal(routeState.routeKind, "study");
  assert.equal(routeState.selection.projectId, "project_001");
  assert.equal(routeState.selection.studyId, "study_001");
});

test("createHostedWorkspaceRouteState captures New Study as a static hosted route", () => {
  const routeState = createHostedWorkspaceRouteState({
    routeContext: {},
    pathname: "/app/new-study",
    search: "?token=token-api"
  });

  assert.equal(routeState.routeKind, "new_study");
  assert.equal(routeState.selection.projectId, "");
  assert.equal(routeState.selection.studyId, "");
});

test("createHostedWorkspaceRouteState captures collaboration-object route context", () => {
  const evidenceViewRoute = createHostedWorkspaceRouteState({
    routeContext: {
      route_kind: "evidence_view",
      evidence_view_id: "evidence_view_001"
    },
    pathname: "/app/evidence-views/evidence_view_001",
    search: "?token=token-api&study_id=study_001"
  });

  assert.equal(evidenceViewRoute.routeKind, "evidence_view");
  assert.equal(evidenceViewRoute.selection.evidenceViewId, "evidence_view_001");
  assert.equal(evidenceViewRoute.selection.studyId, "study_001");

  const decisionLogRoute = createHostedWorkspaceRouteState({
    routeContext: {},
    pathname: "/app/decision-logs/decision_log_001",
    search: "?token=token-api&project_id=project_001"
  });

  assert.equal(decisionLogRoute.routeKind, "decision_log");
  assert.equal(decisionLogRoute.selection.decisionLogId, "decision_log_001");
  assert.equal(decisionLogRoute.selection.projectId, "project_001");
});

test("deriveHostedWorkspaceRoutePath preserves explicit project scope during auto-hydrated study state", () => {
  const path = deriveHostedWorkspaceRoutePath({
    state: {
      selectedProjectId: "project_001",
      selectedStudyId: "study_001",
      selectedJobId: "job_001"
    },
    preferredRouteKind: "project"
  });

  assert.equal(path, "/app/projects/project_001");
});

test("deriveHostedWorkspaceRoutePath preserves explicit New Study scope without object identity", () => {
  const path = deriveHostedWorkspaceRoutePath({
    state: {
      selectedProjectId: "project_001",
      selectedStudyId: "study_001"
    },
    preferredRouteKind: "new_study"
  });

  assert.equal(path, "/app/new-study");
});

test("deriveHostedWorkspaceRoutePath preserves explicit job scope even when project and study are also selected", () => {
  const path = deriveHostedWorkspaceRoutePath({
    state: {
      selectedProjectId: "project_001",
      selectedStudyId: "study_001",
      selectedJobId: "job_001"
    },
    preferredRouteKind: "job"
  });

  assert.equal(path, "/app/jobs/job_001");
});

test("deriveHostedWorkspaceRoutePath falls back to the most concrete available object when preferred scope is missing", () => {
  const path = deriveHostedWorkspaceRoutePath({
    state: {
      selectedProjectId: "project_001",
      selectedStudyId: "study_001",
      selectedExportBundleId: "export_001"
    },
    preferredRouteKind: "share_bundle"
  });

  assert.equal(path, "/app/export-bundles/export_001");
});

test("deriveHostedWorkspaceRoutePath preserves explicit collaboration scope", () => {
  const evidenceViewPath = deriveHostedWorkspaceRoutePath({
    state: {
      selectedProjectId: "project_001",
      selectedStudyId: "study_001",
      selectedJobId: "job_001",
      selectedEvidenceViewId: "evidence_view_001"
    },
    preferredRouteKind: "evidence_view"
  });

  assert.equal(evidenceViewPath, "/app/evidence-views/evidence_view_001");

  const decisionLogPath = deriveHostedWorkspaceRoutePath({
    state: {
      selectedStudyId: "study_001",
      selectedDecisionLogId: "decision_log_001",
      selectedEvidenceViewId: "evidence_view_001"
    },
    preferredRouteKind: "decision_log"
  });

  assert.equal(decisionLogPath, "/app/decision-logs/decision_log_001");
});

test("normalizeHostedWorkspaceRouteKind rejects unknown route kinds", () => {
  assert.equal(normalizeHostedWorkspaceRouteKind("unknown"), "workspace");
  assert.equal(normalizeHostedWorkspaceRouteKind("new_study"), "new_study");
  assert.equal(normalizeHostedWorkspaceRouteKind("support_snapshot"), "support_snapshot");
  assert.equal(normalizeHostedWorkspaceRouteKind("decision_log"), "decision_log");
});
