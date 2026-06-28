import React from "react";

export function SupportOperationsSection() {
  return (
    <section className="card" data-m13-support-section="support-operations">
      <div className="card-header">
        <div>
          <h3 className="section-title">Support operations</h3>
          <p className="section-copy">
            Support stays secondary to the research flow, but blocked submissions, failed runs, and
            handoff snapshots must remain visible without dropping into CLI state.
          </p>
        </div>
      </div>
      <div className="card-body">
        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Support diagnostics</div>
            <div className="toolbar">
              <button className="action-button" id="load-support-diagnostics" type="button">load diagnostics</button>
              <button className="action-button primary" id="create-support-snapshot" type="button">generate snapshot</button>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="support-snapshot-title">Snapshot title</label>
                <input id="support-snapshot-title" type="text" placeholder="Provider failure handoff" />
              </div>
              <div className="field">
                <label htmlFor="support-snapshot-notes">Operator notes</label>
                <textarea
                  id="support-snapshot-notes"
                  rows="4"
                  placeholder="What blocked the study, what was already checked, and who should pick it up next."
                />
              </div>
            </div>
            <div className="summary-grid">
              <div className="summary-card">
                <strong>Submission gate</strong>
                <div className="summary-list" id="support-gate-summary" />
              </div>
              <div className="summary-card">
                <strong>Job diagnostic</strong>
                <div className="summary-list" id="support-diagnostic-summary" />
              </div>
            </div>
            <div className="split-grid">
              <div className="summary-card">
                <strong>Blocked reasons</strong>
                <div className="detail-stack" id="support-blocked-reasons" />
              </div>
              <div className="summary-card">
                <strong>Support actions</strong>
                <div className="detail-stack" id="support-diagnostic-cards" />
              </div>
            </div>
            <div className="summary-card">
              <strong>Recent failure digest</strong>
              <p className="muted-note">
                Use this to jump back into the most recent failed or canceled study jobs without leaving
                the support surface.
              </p>
              <div className="product-stack" id="support-recent-failures" />
            </div>
          </div>

          <div className="draft-panel">
            <div className="inline-label">Support snapshots</div>
            <div className="toolbar">
              <button className="action-button" id="reload-support-snapshots" type="button">reload snapshots</button>
              <div className="status-pill queued" id="support-pill">support_idle</div>
            </div>
            <p className="muted-note">
              Snapshots materialize a support handoff bundle for blocked submissions, failed runs, or
              operator audit follow-up without dropping into CLI state.
            </p>
            <div className="product-stack" id="support-list" />
            <div className="summary-card">
              <strong>Selected support snapshot</strong>
              <div className="summary-list" id="selected-support-summary" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
