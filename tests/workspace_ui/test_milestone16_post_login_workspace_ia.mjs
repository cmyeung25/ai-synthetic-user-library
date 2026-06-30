import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import {
  POST_LOGIN_PRIMARY_NAVIGATION,
  POST_LOGIN_SECONDARY_NAVIGATION,
  derivePostLoginWorkspaceRouteModel,
  isPostLoginWorkspaceSurfaceActive
} from "../../demo/workspace_ui_shared/post_login_workspace_ia.mjs";

test("Milestone 16 route model lands active workspaces on Study Workspace", () => {
  const model = derivePostLoginWorkspaceRouteModel({
    routeKind: "workspace",
    hasActiveStudy: true
  });

  assert.equal(model.contract_version, "post-login-workspace-ia/v1");
  assert.equal(model.milestone_id, "workstream.post_login_workspace_ia_and_active_route_shell");
  assert.equal(model.active_surface_id, "study-workspace");
  assert.equal(model.active_nav_id, "studies");
  assert.equal(model.landing_rule, "active_study_lands_on_study_workspace");
  assert.equal(isPostLoginWorkspaceSurfaceActive(model, "study-workspace"), true);
  assert.equal(isPostLoginWorkspaceSurfaceActive(model, "new-study"), false);
});

test("Milestone 16 route model lands no-study workspaces on New Study", () => {
  const model = derivePostLoginWorkspaceRouteModel({
    routeKind: "workspace",
    hasActiveStudy: false
  });

  assert.equal(model.active_surface_id, "new-study");
  assert.equal(model.active_nav_id, "new-study");
  assert.equal(model.landing_rule, "no_study_lands_on_new_study");
});

test("Milestone 16 deep links preserve study-first route intent", () => {
  const jobRoute = derivePostLoginWorkspaceRouteModel({ routeKind: "job" });
  const decisionRoute = derivePostLoginWorkspaceRouteModel({ routeKind: "decision_log" });
  const supportRoute = derivePostLoginWorkspaceRouteModel({ routeKind: "support_snapshot" });

  assert.equal(jobRoute.active_surface_id, "evidence-review");
  assert.equal(jobRoute.active_nav_id, "evidence");
  assert.equal(jobRoute.preserves_study_context, true);
  assert.equal(jobRoute.landing_rule, "job_deep_link_opens_evidence_review_with_study_context");

  assert.equal(decisionRoute.active_surface_id, "evidence-review");
  assert.equal(decisionRoute.active_nav_id, "decisions");
  assert.equal(decisionRoute.preserves_study_context, true);

  assert.equal(supportRoute.active_surface_id, "support");
  assert.equal(supportRoute.active_nav_id, "support");
  assert.equal(supportRoute.preserves_study_context, true);
});

test("Milestone 16 navigation keeps research surfaces before governance", () => {
  assert.deepEqual(
    POST_LOGIN_PRIMARY_NAVIGATION.map((item) => item.id),
    ["new-study", "studies", "evidence", "decisions", "activity"]
  );
  assert.deepEqual(
    POST_LOGIN_SECONDARY_NAVIGATION.map((item) => item.id),
    ["settings", "support", "billing", "api-tokens", "retention-governance"]
  );

  const model = derivePostLoginWorkspaceRouteModel();
  assert.deepEqual(
    model.acceptance_gates,
    [
      "one_expanded_primary_or_secondary_surface",
      "research_nav_before_governance_nav",
      "job_deep_link_routes_to_evidence_review",
      "secondary_governance_available_but_not_default_landing",
      "visual_smoke_checks_for_overlap_text_occlusion_and_blocked_actions"
    ]
  );
});

test("React host implements route-owned surfaces instead of one always-expanded page", async () => {
  const hostSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );

  assert.match(hostSource, /derivePostLoginWorkspaceRouteModel/);
  assert.match(hostSource, /deriveHasActiveStudyFromRouteContext/);
  assert.match(hostSource, /data-contract-version=\{routeModel\.contract_version\}/);
  assert.match(hostSource, /data-active-route-kind=\{routeModel\.active_route_kind\}/);
  assert.match(hostSource, /data-active-surface=\{routeModel\.active_surface_id\}/);
  assert.match(hostSource, /data-active-nav=\{routeModel\.active_nav_id\}/);
  assert.match(hostSource, /data-active-route-shell="true"/);
  assert.match(hostSource, /hidden=\{!isActive\}/);
  assert.match(hostSource, /<RouteSurface surfaceId="new-study" routeModel=\{routeModel\}>/);
  assert.match(hostSource, /<RouteSurface surfaceId="study-workspace" routeModel=\{routeModel\}>/);
  assert.match(hostSource, /<RouteSurface surfaceId="evidence-review" routeModel=\{routeModel\}>/);
  assert.match(hostSource, /<RouteSurface surfaceId="settings" routeModel=\{routeModel\}>/);
  assert.match(hostSource, /<RouteSurface surfaceId="support" routeModel=\{routeModel\}>/);

  assert.ok(
    hostSource.indexOf('surfaceId="new-study"') < hostSource.indexOf('surfaceId="settings"'),
    "research route surfaces must be declared before secondary governance surfaces"
  );
  assert.ok(
    hostSource.indexOf("<WorkspaceConnectionSection />") < hostSource.indexOf("<DebugTraceSection />"),
    "debug trace must stay behind route context rather than above the research surface"
  );
});

test("React navigation is contract-driven with primary and secondary tiers", async () => {
  const navSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/RealUserWorkspaceNav.jsx", import.meta.url),
    "utf8"
  );

  assert.match(navSource, /routeModel\?\.primary_navigation\?\.map/);
  assert.match(navSource, /routeModel\?\.secondary_navigation\?\.map/);
  assert.match(navSource, /data-nav-tier=\{tier\}/);
  assert.match(navSource, /data-active-nav=\{routeModel\?\.active_nav_id\}/);
  assert.match(navSource, /onNavigateSurface\(item\)/);
  assert.match(navSource, /Research loop/);
  assert.match(navSource, /Governance \+ support/);
});

test("Milestone 16 CSS hides inactive surfaces and avoids fixed-width sidecar overlap", async () => {
  const cssSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/main.css", import.meta.url),
    "utf8"
  );

  assert.match(cssSource, /\.post-login-route-grid\s*\{\s*display: grid/s);
  assert.match(cssSource, /grid-template-columns: minmax\(0, 1fr\) minmax\(260px, 0\.28fr\)/);
  assert.match(cssSource, /\.route-surface\[hidden\]\s*\{\s*display: none !important/s);
  assert.match(cssSource, /\.route-context-drawer\s*\{[\s\S]*position: sticky/s);
  assert.match(cssSource, /@media \(max-width: 1180px\)/);
  assert.doesNotMatch(cssSource, /grid-template-columns:[^;]*380px/);
});
