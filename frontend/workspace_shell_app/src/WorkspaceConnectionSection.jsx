import React from "react";

export function WorkspaceConnectionSection() {
  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Workspace connection</h3>
          <p className="section-copy">
            Session, project, and study hydration stay backend-owned. Hosted routes now exchange a
            one-time bootstrap token for a server-backed browser session.
          </p>
        </div>
        <div className="status-bar">
          <div className="status-pill queued" id="session-pill">missing_token</div>
          <div className="status-pill queued" id="session-memory-pill">session_check_pending</div>
          <div className="status-pill queued" id="runtime-pill">idle</div>
        </div>
      </div>
      <div className="card-body">
        <div className="form-grid">
          <div className="field">
            <label htmlFor="api-base-url">API base URL</label>
            <input id="api-base-url" type="text" defaultValue="http://127.0.0.1:8011" />
          </div>
          <div className="field">
            <label htmlFor="api-token">Bootstrap token</label>
            <input id="api-token" type="text" defaultValue="" placeholder="optional one-time bootstrap token" />
          </div>
          <div className="field">
            <label htmlFor="brief-path">brief_path</label>
            <input id="brief-path" type="text" defaultValue="briefs/brief.json" />
          </div>
          <div className="field">
            <label htmlFor="persona-dir">persona_dir</label>
            <input id="persona-dir" type="text" defaultValue="personas" />
          </div>
        </div>
        <div className="toolbar">
          <button className="action-button" id="refresh-workspace" type="button">refresh workspace</button>
          <button className="action-button" id="load-session" type="button">load session</button>
          <button className="action-button" id="forget-saved-session" type="button">end browser session</button>
          <button className="action-button" id="load-shell" type="button">load study shell</button>
          <button className="action-button" id="toggle-auto-refresh" type="button">start auto refresh</button>
        </div>
        <div className="summary-grid">
          <div className="summary-card">
            <strong>Session summary</strong>
            <div className="summary-list" id="session-summary" />
          </div>
          <div className="summary-card">
            <strong>Workspace limits</strong>
            <div className="summary-list" id="limit-summary" />
          </div>
        </div>
      </div>
    </section>
  );
}
