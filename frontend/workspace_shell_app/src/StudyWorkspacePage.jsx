import React from "react";

export function StudyWorkspacePage() {
  return (
    <section className="card" data-m13-page="study-workspace">
      <div className="card-header">
        <div>
          <h3 className="section-title">Study Workspace</h3>
          <p className="section-copy">
            Keep project, study, latest run, collaboration objects, and activity in one durable
            research workspace. The study remains the primary object; runs are execution records inside it.
          </p>
        </div>
      </div>
      <div className="card-body">
        <div className="split-grid">
          <div className="draft-panel">
            <div className="toolbar">
              <div className="inline-label">Projects</div>
              <div className="status-pill completed" id="project-pill">0 projects</div>
            </div>
            <p className="muted-note">
              Projects are long-lived research areas. They orient studies, saved evidence, and later
              export or decision history.
            </p>
            <form className="product-form" id="project-form">
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="project-name">Project name</label>
                  <input id="project-name" type="text" placeholder="Inbox Coach Launch" />
                </div>
                <div className="field">
                  <label htmlFor="project-slug">Slug</label>
                  <input id="project-slug" type="text" placeholder="inbox-coach-launch" />
                </div>
              </div>
              <div className="toolbar">
                <button className="action-button primary" id="create-project" type="submit">create project</button>
                <button className="action-button" id="reload-projects" type="button">reload projects</button>
              </div>
            </form>
            <div className="product-stack" id="project-list" />
            <div className="summary-card">
              <strong>Selected project</strong>
              <div className="summary-list" id="selected-project-summary" />
            </div>
          </div>

          <div className="draft-panel">
            <div className="toolbar">
              <div className="inline-label">Studies</div>
              <div className="status-pill completed" id="study-pill">0 studies</div>
            </div>
            <p className="muted-note">
              The selected study is the default operating object. Intake, runs, evidence review, and
              reruns should all live here.
            </p>
            <form className="product-form" id="study-form">
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="study-title">Study title</label>
                  <input id="study-title" type="text" placeholder="Onboarding hesitation review" />
                </div>
                <div className="field">
                  <label htmlFor="study-first-task">First task seed</label>
                  <input id="study-first-task" type="text" placeholder="connect CRM" />
                </div>
              </div>
              <div className="toolbar">
                <button className="action-button primary" id="create-study" type="submit">create study</button>
                <button className="action-button" id="reload-studies" type="button">reload studies</button>
              </div>
            </form>
            <div className="product-stack" id="study-list" />
            <div className="summary-card">
              <strong>Selected study</strong>
              <div className="summary-list" id="selected-study-summary" />
            </div>
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Run timeline and next action</div>
            <p className="muted-note">
              Run state stays visible without making the job the top-level product object. Blocked,
              failed, and retryable states remain part of the study context.
            </p>
            <div className="toolbar">
              <button className="action-button primary" id="submit-live-job" type="button">submit live job</button>
              <button className="action-button" id="retry-selected-job" type="button">retry selected job</button>
              <button className="action-button" id="cancel-selected-job" type="button">cancel queued job</button>
              <button className="action-button" id="use-sample-jobs" type="button">use sample jobs</button>
            </div>
            <div className="product-stack" id="job-list" />
          </div>

          <div className="summary-card">
            <strong>Study activity</strong>
            <div className="summary-list" id="study-activity-summary" />
            <p className="muted-note">
              This timeline keeps study review continuity visible across runs, saved views, decisions,
              exports, shares, and support handoffs.
            </p>
            <div className="toolbar">
              <button className="action-button" id="reload-study-activity" type="button">reload timeline</button>
            </div>
            <div className="product-stack" id="study-activity-list" />
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Saved evidence views</div>
            <div className="toolbar">
              <button className="action-button primary" id="create-evidence-view" type="button">save current view</button>
              <button className="action-button" id="reload-evidence-views" type="button">reload saved views</button>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="evidence-view-title">View title</label>
                <input id="evidence-view-title" type="text" placeholder="Onboarding hesitation trace view" />
              </div>
              <div className="field">
                <label htmlFor="evidence-view-note">View note</label>
                <textarea
                  id="evidence-view-note"
                  rows="3"
                  placeholder="Why this slice matters, and what to revisit later."
                />
              </div>
            </div>
            <p className="muted-note">
              Saved views persist the current evidence query and selection state so the team can return
              to the same review angle later.
            </p>
            <div className="product-stack" id="evidence-view-list" />
          </div>

          <div className="draft-panel">
            <div className="inline-label">Decision logs</div>
            <div className="toolbar">
              <button className="action-button primary" id="create-decision-log" type="button">record decision</button>
              <button className="action-button" id="reload-decision-logs" type="button">reload decisions</button>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="decision-log-title">Decision title</label>
                <input
                  id="decision-log-title"
                  type="text"
                  placeholder="Keep onboarding guidance visible after the first action"
                />
              </div>
              <div className="field">
                <label htmlFor="decision-log-summary">Decision summary</label>
                <textarea
                  id="decision-log-summary"
                  rows="3"
                  placeholder="The evidence supports keeping guidance visible because hesitation clusters around confirmation and reversibility."
                />
              </div>
              <div className="field">
                <label htmlFor="decision-log-rationale">Rationale</label>
                <textarea
                  id="decision-log-rationale"
                  rows="4"
                  placeholder="Reference the specific run, evidence slice, and cross-run comparison that drove the decision."
                />
              </div>
            </div>
            <p className="muted-note">
              Decision logs keep research conclusions attached to the study, run lineage, and evidence
              context instead of drifting into external notes.
            </p>
            <div className="product-stack" id="decision-log-list" />
          </div>
        </div>

        <div className="signal-band">
          <strong>Synthetic boundary reminder</strong>
          <p>
            Study continuity does not turn simulated evidence into human proof. Keep blocked states,
            failed states, and unresolved validation gaps visible before deciding or sharing.
          </p>
        </div>
      </div>
    </section>
  );
}
