import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import {
  MILESTONE13_OPERATING_LOOP,
  MILESTONE13_REAL_USER_PAGES,
  deriveMilestone13ActivePageIdFromRouteKind,
  deriveMilestone13RealUserWorkspaceModel,
  getMilestone13PageById
} from "../../demo/workspace_ui_shared/milestone13_real_user_workspace.mjs";

test("Milestone 13 page model preserves the full research operating loop", () => {
  const model = deriveMilestone13RealUserWorkspaceModel();

  assert.equal(model.contract_version, "milestone13-real-user-workspace/v0-draft");
  assert.deepEqual(model.operating_loop, [
    "Ask",
    "Clarify",
    "Confirm Plan",
    "Run",
    "Review Evidence",
    "Compare",
    "Decide",
    "Share With Boundary"
  ]);
  assert.equal(model.pages.length, 3);
  assert.deepEqual(
    model.completion_bar.required_pages,
    ["new-study", "study-workspace", "evidence-review"]
  );
  assert.equal(model.completion_bar.component_cleanup_required, true);
});

test("Milestone 13 canonical pages keep study-first evidence boundaries explicit", () => {
  const newStudy = getMilestone13PageById("new-study");
  const studyWorkspace = getMilestone13PageById("study-workspace");
  const evidenceReview = getMilestone13PageById("evidence-review");

  assert.ok(newStudy.primary_selectors.includes("research-intent"));
  assert.ok(newStudy.default_loop_steps.includes("Confirm Plan"));
  assert.ok(newStudy.required_evidence_boundaries.includes("known human-validation gaps"));
  assert.ok(newStudy.anti_patterns.includes("mode-first setup"));

  assert.ok(studyWorkspace.primary_selectors.includes("selected-study-summary"));
  assert.ok(studyWorkspace.required_evidence_boundaries.includes("selected study remains primary object"));
  assert.ok(studyWorkspace.anti_patterns.includes("generic tenant dashboard"));

  assert.ok(evidenceReview.primary_selectors.includes("selected-evidence-summary"));
  assert.ok(evidenceReview.primary_selectors.includes("cross-run-summary"));
  assert.ok(evidenceReview.required_evidence_boundaries.includes("human_validation_gap"));
  assert.ok(evidenceReview.anti_patterns.includes("frontend reliability scoring"));
});

test("Milestone 13 page model covers every canonical loop step at least once", () => {
  const coveredSteps = new Set(
    MILESTONE13_REAL_USER_PAGES.flatMap((page) => page.default_loop_steps)
  );

  for (const step of MILESTONE13_OPERATING_LOOP) {
    assert.equal(coveredSteps.has(step), true, `${step} should be covered by a canonical M13 page`);
  }
});

test("Milestone 13 active page follows hosted route kind without frontend route heuristics", () => {
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("new_study"), "new-study");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("workspace"), "new-study");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("study"), "study-workspace");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("project"), "study-workspace");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("job"), "evidence-review");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("decision_log"), "evidence-review");
  assert.equal(deriveMilestone13ActivePageIdFromRouteKind("unknown"), "new-study");
});

test("React framework host exposes Milestone 13 real-user page sections", async () => {
  const source = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );

  assert.match(source, /RealUserResearchWorkspacePages/);
  assert.match(source, /deriveMilestone13ActivePageIdFromRouteKind\(routeContext\.route_kind\)/);
  assert.match(source, /data-contract-version=\{milestone13Model\.contract_version\}/);
  assert.match(source, /data-active-page=\{milestone13Model\.active_page_id\}/);
  assert.match(source, /m13-\$\{page\.id\}-page/);
  assert.match(source, /data-page=\{page\.id\}/);
  assert.match(source, /data-active=\{page\.is_active \? "true" : "false"\}/);
  assert.match(source, /Milestone 13 Real User Research Workspace/);
  assert.match(source, /New Study, Study Workspace, and Evidence Review/);
});

test("New Study page is framework-owned while preserving shared controller anchors", async () => {
  const hostSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );
  const pageSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/NewStudyPage.jsx", import.meta.url),
    "utf8"
  );

  assert.match(hostSource, /import \{ NewStudyPage \} from "\.\/NewStudyPage\.jsx"/);
  assert.doesNotMatch(hostSource, /function StudyWorkspaceSection/);
  assert.match(hostSource, /<NewStudyPage \/>/);

  assert.match(pageSource, /data-m13-page="new-study"/);
  assert.match(pageSource, /id="research-intent"/);
  assert.match(pageSource, /id="artifact-files"/);
  assert.match(pageSource, /id="study-actions"/);
  assert.match(pageSource, /id="draft-summary"/);
  assert.match(pageSource, /id="boundary-copy"/);
  assert.match(pageSource, /Confirm plan before execution/);
  assert.match(pageSource, /Plan confirmation gate/);
  assert.match(pageSource, /human_validation_gap/);
});

test("Study Workspace page is framework-owned while preserving study continuity anchors", async () => {
  const hostSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );
  const pageSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/StudyWorkspacePage.jsx", import.meta.url),
    "utf8"
  );

  assert.match(hostSource, /import \{ StudyWorkspacePage \} from "\.\/StudyWorkspacePage\.jsx"/);
  assert.match(hostSource, /<StudyWorkspacePage \/>/);
  assert.doesNotMatch(hostSource, /id="project-form"/);
  assert.doesNotMatch(hostSource, /id="study-form"/);
  assert.doesNotMatch(hostSource, /id="job-list"/);

  assert.match(pageSource, /data-m13-page="study-workspace"/);
  for (const selector of [
    "selected-project-summary",
    "selected-study-summary",
    "job-list",
    "study-activity-list",
    "evidence-view-list",
    "decision-log-list"
  ]) {
    assert.match(pageSource, new RegExp(`id="${selector}"`));
  }
  assert.match(pageSource, /The study remains the primary object/);
  assert.match(pageSource, /Synthetic boundary reminder/);
});

test("Evidence Review page is framework-owned while preserving reliability review anchors", async () => {
  const hostSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );
  const pageSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/EvidenceReviewPage.jsx", import.meta.url),
    "utf8"
  );

  assert.match(hostSource, /import \{ EvidenceReviewPage \} from "\.\/EvidenceReviewPage\.jsx"/);
  assert.match(hostSource, /<EvidenceReviewPage \/>/);
  assert.doesNotMatch(hostSource, /function RunTimelineEvidenceReviewSection/);
  assert.doesNotMatch(hostSource, /id="evidence-list"/);
  assert.doesNotMatch(hostSource, /id="cross-run-summary"/);

  assert.match(pageSource, /data-m13-page="evidence-review"/);
  for (const selector of [
    "query-pill",
    "evidence-list",
    "selected-evidence-summary",
    "selected-evidence-detail",
    "cross-run-summary",
    "cross-run-detail",
    "selected-decision-log-summary",
    "decision-comment-list",
    "export-list",
    "share-list"
  ]) {
    assert.match(pageSource, new RegExp(`id="${selector}"`));
  }
  assert.match(pageSource, /calibration records/);
  assert.match(pageSource, /audit lineage/);
  assert.match(pageSource, /human_validation_gap/);
});

test("Stage 15 host is reduced to composition for the M13 product surface", async () => {
  const hostSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/Stage15WorkspaceShellHost.jsx", import.meta.url),
    "utf8"
  );

  for (const component of [
    "RealUserWorkspaceNav",
    "WorkspaceConnectionSection",
    "WorkspaceSettingsSection",
    "NewStudyPage",
    "StudyWorkspacePage",
    "EvidenceReviewPage",
    "SupportOperationsSection",
    "DebugTraceSection"
  ]) {
    assert.match(hostSource, new RegExp(`<${component} />`));
  }

  assert.ok(
    hostSource.indexOf("<NewStudyPage />") < hostSource.indexOf("<WorkspaceSettingsSection />"),
    "research workflow pages should render before settings in the hosted shell"
  );

  assert.doesNotMatch(hostSource, /function DebugTraceSection/);
  assert.doesNotMatch(hostSource, /id="workspace-settings-summary"/);
  assert.doesNotMatch(hostSource, /id="support-gate-summary"/);
});

test("Framework host keeps dense evidence grids readable with clamped long content", async () => {
  const cssSource = await readFile(
    new URL("../../frontend/workspace_shell_app/src/main.css", import.meta.url),
    "utf8"
  );

  assert.match(cssSource, /\.framework-host \.product-card p/);
  assert.match(cssSource, /\.framework-host \.shell\s*\{\s*grid-template-columns: 248px minmax\(0, 1fr\)/s);
  assert.doesNotMatch(cssSource, /\.framework-host \.shell\s*\{[^}]*380px/s);
  assert.match(cssSource, /grid-template-columns: minmax\(0, 1\.35fr\) minmax\(300px, 0\.7fr\)/);
  assert.match(cssSource, /-webkit-line-clamp: 2/);
  assert.match(cssSource, /\.framework-host \.detail-card span/);
  assert.match(cssSource, /-webkit-line-clamp: 3/);
  assert.match(cssSource, /\.framework-host \.summary-row\s*\{\s*display: grid/s);
  assert.match(cssSource, /grid-template-columns: minmax\(110px, 0\.42fr\) minmax\(0, 1fr\)/);
  assert.match(cssSource, /@media \(min-width: 1440px\)/);
  assert.match(cssSource, /@media \(max-width: 1180px\)/);
  assert.match(cssSource, /\.framework-host \.summary-row:hover strong/);
});
