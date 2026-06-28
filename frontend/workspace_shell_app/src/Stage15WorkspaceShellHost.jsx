import React, { useEffect, useRef } from "react";

import "@demo/workspace_ui_design_system/workspace-ui-base.css";
import "@demo/workspace_ui_design_system/workspace-theme-moss.css";
import "./main.css";

import { DebugTraceSection } from "./DebugTraceSection.jsx";
import { EvidenceReviewPage } from "./EvidenceReviewPage.jsx";
import { NewStudyPage } from "./NewStudyPage.jsx";
import { RealUserWorkspaceNav } from "./RealUserWorkspaceNav.jsx";
import { StudyWorkspacePage } from "./StudyWorkspacePage.jsx";
import { SupportOperationsSection } from "./SupportOperationsSection.jsx";
import { WorkspaceConnectionSection } from "./WorkspaceConnectionSection.jsx";
import { WorkspaceSettingsSection } from "./WorkspaceSettingsSection.jsx";
import stage15ShellDocument from "@demo/workspace_ui_moss_stage15/index.html?raw";
import { mountStage15WorkspaceShell } from "@demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs";
import {
  MILESTONE13_OPERATING_LOOP,
  deriveMilestone13ActivePageIdFromRouteKind,
  deriveMilestone13RealUserWorkspaceModel
} from "@demo/workspace_ui_shared/milestone13_real_user_workspace.mjs";
import { extractStage15ShellDocumentParts } from "@demo/workspace_ui_shared/stage15_shell_document.mjs";

const {
  title,
  inlineStyles
} = extractStage15ShellDocumentParts(stage15ShellDocument);

function readWorkspaceRouteContext() {
  if (typeof window === "undefined") {
    return {};
  }
  return window.__WORKSPACE_ROUTE_CONTEXT__ || {};
}

function RealUserResearchWorkspacePages() {
  const routeContext = readWorkspaceRouteContext();
  const activePageId = deriveMilestone13ActivePageIdFromRouteKind(routeContext.route_kind);
  const milestone13Model = deriveMilestone13RealUserWorkspaceModel({ activePageId });

  return (
    <section
      className="m13-workspace"
      aria-labelledby="m13-title"
      data-contract-version={milestone13Model.contract_version}
      data-active-page={milestone13Model.active_page_id}
    >
      <div className="m13-hero">
        <div>
          <div className="framework-banner-eyebrow">Milestone 13 Real User Research Workspace</div>
          <h2 id="m13-title">Three product pages, one study-first research loop.</h2>
          <p>
            The next layer is not another dashboard. It is the real operating surface for starting a study,
            keeping the study alive, and reviewing evidence with reliability and human-validation gaps visible.
          </p>
        </div>
        <ol className="m13-loop" aria-label="Default research loop">
          {MILESTONE13_OPERATING_LOOP.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      <div className="m13-page-grid" data-milestone-id={milestone13Model.milestone_id}>
        {milestone13Model.pages.map((page) => (
          <article
            className={`m13-page-card${page.is_active ? " is-active" : ""}`}
            id={`m13-${page.id}-page`}
            data-page={page.id}
            data-active={page.is_active ? "true" : "false"}
            key={page.id}
          >
            <div className="m13-page-index">{String(page.ordinal).padStart(2, "0")}</div>
            <div className="m13-page-body">
              <div className="m13-page-kicker">{page.route_intent}</div>
              <h3>{page.title}</h3>
              <p>{page.purpose}</p>
              <div className="m13-user-job">{page.user_job}</div>
              <div className="m13-chip-row" aria-label={`${page.title} primary loop steps`}>
                {page.default_loop_steps.map((step) => (
                  <span className="m13-chip" key={step}>{step}</span>
                ))}
              </div>
              <div className="m13-contract-columns">
                <div>
                  <strong>Must preserve</strong>
                  <ul>
                    {page.required_evidence_boundaries.map((boundary) => (
                      <li key={boundary}>{boundary}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <strong>Must avoid</strong>
                  <ul>
                    {page.anti_patterns.map((pattern) => (
                      <li key={pattern}>{pattern}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="m13-selector-links" aria-label={`${page.title} functional anchors`}>
                {page.primary_selectors.slice(0, 4).map((selector) => (
                  <a href={`#${selector}`} key={selector}>#{selector}</a>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function Stage15WorkspaceShellHost() {
  const shellMountedRef = useRef(false);

  useEffect(() => {
    if (!title) {
      return;
    }
    document.title = `${title} Framework Host`;
  }, []);

  useEffect(() => {
    if (shellMountedRef.current) {
      return undefined;
    }

    shellMountedRef.current = true;
    const mounted = mountStage15WorkspaceShell({
      document,
      window
    });

    return () => {
      mounted?.stopAutoRefresh?.();
      shellMountedRef.current = false;
    };
  }, []);

  return (
    <div className="framework-host">
      <style>{inlineStyles}</style>
      <div className="framework-banner">
        <div className="framework-banner-copy">
          <div className="framework-banner-eyebrow">Milestone 13 Framework Host</div>
          <h1 className="framework-banner-title">Real user research pages are replacing the monolithic shell.</h1>
          <p className="framework-banner-text">
            This frontend app keeps the existing Moss operating surface intact while introducing real
            page ownership for New Study, Study Workspace, and Evidence Review.
          </p>
        </div>
        <div className="framework-banner-status">same-origin hosted route shell</div>
      </div>
      <RealUserResearchWorkspacePages />
      <div className="framework-shell-root">
        <div className="shell">
          <RealUserWorkspaceNav />

          <main className="main">
            <div className="stage15-shell">
              <header className="main-header">
                <div>
                  <div className="eyebrow">Study-First Hosted Shell Direction</div>
                  <h2>Project and study operations on top of the workspace runtime</h2>
                  <p>
                    The selected study is now the durable home for intake, run submission, snapshot
                    sync, and evidence review. Projects orient the work. Runs remain operational
                    records inside that study context.
                  </p>
                </div>
                <div className="top-metrics">
                  <div className="metric">
                    <span>Project</span>
                    <strong id="metric-project">-</strong>
                  </div>
                  <div className="metric">
                    <span>Study</span>
                    <strong id="metric-study">-</strong>
                  </div>
                  <div className="metric">
                    <span>Shell</span>
                    <strong id="metric-shell">conversation_intake</strong>
                  </div>
                  <div className="metric">
                    <span>Run</span>
                    <strong id="metric-run">-</strong>
                  </div>
                </div>
              </header>

              <div className="stage15-grid">
                <div className="stage15-column">
                  <NewStudyPage />
                  <StudyWorkspacePage />
                  <EvidenceReviewPage />
                </div>

                <div className="stage15-column">
                  <WorkspaceConnectionSection />
                  <WorkspaceSettingsSection />
                  <SupportOperationsSection />
                  <DebugTraceSection />
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
