import React from "react";

export function WorkspaceSettingsSection() {
  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Workspace settings</h3>
          <p className="section-copy">
            Governance stays secondary to the study workflow, but this product layer still needs
            visible membership, quota, retention, and API access controls.
          </p>
        </div>
        <div className="status-bar">
          <div className="status-pill queued" id="settings-pill">settings_unloaded</div>
        </div>
      </div>
      <div className="card-body">
        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Membership + policy</div>
            <div className="toolbar">
              <button className="action-button" id="load-workspace-settings" type="button">load settings</button>
              <button className="action-button" id="load-audit-events" type="button">load audit history</button>
              <button className="action-button primary" id="upsert-workspace-member" type="button">upsert member</button>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="member-user-id">Member user_id</label>
                <input id="member-user-id" type="text" placeholder="researcher_001" />
              </div>
              <div className="field">
                <label htmlFor="member-role">Role</label>
                <select id="member-role" defaultValue="editor">
                  <option value="editor">editor</option>
                  <option value="viewer">viewer</option>
                  <option value="admin">admin</option>
                  <option value="billing_admin">billing_admin</option>
                  <option value="owner">owner</option>
                </select>
              </div>
            </div>
            <div className="summary-grid">
              <div className="summary-card">
                <strong>Workspace</strong>
                <div className="summary-list" id="workspace-settings-summary" />
              </div>
              <div className="summary-card">
                <strong>Billing + limits</strong>
                <div className="summary-list" id="workspace-billing-summary" />
              </div>
            </div>
            <div className="summary-card">
              <strong>Policy</strong>
              <div className="summary-list" id="workspace-policy-summary" />
            </div>
            <div className="summary-card">
              <strong>Members</strong>
              <div className="product-stack" id="workspace-member-list" />
            </div>
            <div className="summary-card">
              <strong>Audit history</strong>
              <div className="summary-list" id="workspace-audit-summary" />
            </div>
          </div>

          <div className="draft-panel">
            <div className="inline-label">Billing + token administration</div>
            <div className="toolbar">
              <button className="action-button" id="update-workspace-billing" type="button">update billing</button>
              <button className="action-button primary" id="issue-api-token" type="button">issue token</button>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="audit-target-type">Audit target_type</label>
                <input id="audit-target-type" type="text" placeholder="api_token" />
              </div>
              <div className="field">
                <label htmlFor="audit-action-prefix">Audit action_prefix</label>
                <input id="audit-action-prefix" type="text" placeholder="workspace_" />
              </div>
              <div className="field">
                <label htmlFor="audit-limit">Audit limit</label>
                <input id="audit-limit" type="number" min="1" max="100" step="1" defaultValue="20" />
              </div>
              <div className="field">
                <label htmlFor="billing-plan-tier">Plan tier</label>
                <select id="billing-plan-tier" defaultValue="trial">
                  <option value="trial">trial</option>
                  <option value="pro">pro</option>
                  <option value="enterprise">enterprise</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="billing-status">Billing status</label>
                <select id="billing-status" defaultValue="trialing">
                  <option value="trialing">trialing</option>
                  <option value="active">active</option>
                  <option value="past_due">past_due</option>
                  <option value="canceled">canceled</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="billing-seat-count">Seat count</label>
                <input id="billing-seat-count" type="number" min="1" step="1" defaultValue="1" />
              </div>
              <div className="field">
                <label htmlFor="billing-renewal-at">Renewal at</label>
                <input id="billing-renewal-at" type="text" placeholder="2026-07-31T00:00:00+00:00" />
              </div>
              <div className="field">
                <label htmlFor="quota-daily-runs">Daily runs</label>
                <input id="quota-daily-runs" type="number" min="0" step="1" defaultValue="3" />
              </div>
              <div className="field">
                <label htmlFor="quota-concurrent-jobs">Concurrent jobs</label>
                <input id="quota-concurrent-jobs" type="number" min="0" step="1" defaultValue="1" />
              </div>
              <div className="field">
                <label htmlFor="quota-retention-days">Retention days</label>
                <input id="quota-retention-days" type="number" min="0" step="1" defaultValue="7" />
              </div>
            </div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="token-user-id">Token user_id</label>
                <input id="token-user-id" type="text" placeholder="researcher_001" />
              </div>
            </div>
            <p className="muted-note">
              Existing tokens stay masked. A full token value is only shown at the moment it is issued
              in this shell session.
            </p>
            <div className="summary-card">
              <strong>Last issued token</strong>
              <div className="summary-list" id="last-issued-token-summary" />
            </div>
            <div className="summary-card">
              <strong>API tokens</strong>
              <div className="product-stack" id="workspace-token-list" />
            </div>
            <div className="summary-card">
              <strong>Audit events</strong>
              <div className="product-stack" id="workspace-audit-list" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
