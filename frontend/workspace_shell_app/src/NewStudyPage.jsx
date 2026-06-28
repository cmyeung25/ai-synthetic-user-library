import React from "react";

export function NewStudyPage() {
  return (
    <section className="card" data-m13-page="new-study">
      <div className="card-header">
        <div>
          <h3 className="section-title">New Study</h3>
          <p className="section-copy">
            Start from conversational research intent, then confirm the inferred plan before any run starts.
            The selected study remains the product object, not the job or prompt.
          </p>
        </div>
        <div className="status-bar">
          <div className="status-pill queued" id="bridge-pill">draft_only</div>
          <div className="status-pill queued" id="job-pill">no job</div>
        </div>
      </div>
      <div className="card-body">
        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Ask and clarify</div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="research-intent">Research intent</label>
                <textarea id="research-intent" rows="5" />
              </div>
              <div className="field">
                <label htmlFor="desired-outcome">Desired output</label>
                <textarea id="desired-outcome" rows="4" />
              </div>
              <div className="field">
                <label htmlFor="first-task">First task</label>
                <input id="first-task" type="text" placeholder="connect CRM" />
              </div>
              <div className="field">
                <label htmlFor="artifact-files">Prototype artifacts</label>
                <input id="artifact-files" type="file" accept=".png,.jpg,.jpeg,.webp" multiple />
              </div>
            </div>
            <p className="muted-note" id="artifact-note">No prototype artifacts attached yet.</p>
          </div>

          <div className="draft-panel">
            <div className="inline-label">Confirm plan before execution</div>
            <p className="muted-note">
              The run should only start after the inferred mode, target question, artifacts, expected
              evidence, and known human-validation gaps are visible enough for explicit approval.
            </p>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="mode-override">mode override</label>
                <select id="mode-override" defaultValue="auto">
                  <option value="auto">auto infer</option>
                  <option value="prototype_validation">prototype_validation</option>
                  <option value="concept_validation">concept_validation</option>
                  <option value="adoption_barrier_validation">adoption_barrier_validation</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="panel-type">panel_type</label>
                <select id="panel-type" defaultValue="mainstream">
                  <option value="mainstream">mainstream</option>
                  <option value="skeptic">skeptic</option>
                  <option value="privacy_sensitive">privacy_sensitive</option>
                  <option value="budget_constrained">budget_constrained</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="sample-size">sample_size</label>
                <input id="sample-size" type="number" min="1" max="12" step="1" defaultValue="5" />
              </div>
              <div className="field">
                <label htmlFor="provider-name">provider_name</label>
                <select id="provider-name" defaultValue="mock">
                  <option value="mock">mock</option>
                  <option value="codex">codex</option>
                  <option value="openai">openai</option>
                  <option value="agnes">agnes</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="persona-filter-location">location_type</label>
                <select id="persona-filter-location" defaultValue="all">
                  <option value="all">all</option>
                  <option value="urban_core">urban_core</option>
                  <option value="suburban">suburban</option>
                  <option value="regional">regional</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="persona-filter-privacy">privacy_concern</label>
                <select id="persona-filter-privacy" defaultValue="all">
                  <option value="all">all</option>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>
            </div>
            <div className="summary-card">
              <strong>Plan confirmation gate</strong>
              <div className="summary-list">
                <span>Mode: infer from research intent unless overridden below.</span>
                <span>Question: preserve the plain-language target in the draft summary.</span>
                <span>Artifacts: attach only available concept or prototype materials.</span>
                <span>Evidence: objections, trust gaps, adoption barriers, comparison, and replay.</span>
                <span>Limits: synthetic signal only; unresolved human_validation_gap remains visible.</span>
              </div>
            </div>
            <div className="toolbar" id="study-actions" />
          </div>
        </div>

        <div className="summary-grid">
          <div className="summary-card">
            <strong>Draft state</strong>
            <div className="summary-list" id="draft-summary" />
          </div>
          <div className="summary-card">
            <strong>Study shell</strong>
            <div className="summary-list" id="adapter-summary" />
          </div>
          <div className="summary-card">
            <strong>Run monitor</strong>
            <div className="summary-list" id="run-summary" />
          </div>
          <div className="summary-card">
            <strong>Evidence readiness</strong>
            <div className="summary-list" id="review-summary" />
          </div>
        </div>

        <div className="signal-band">
          <strong>Synthetic evidence boundary</strong>
          <p id="boundary-copy">
            Synthetic evidence remains bounded to the selected study and run. This surface must never
            imply human market proof.
          </p>
        </div>
      </div>
    </section>
  );
}
