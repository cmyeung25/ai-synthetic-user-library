import React from "react";

export function EvidenceReviewPage() {
  return (
    <section className="card" data-m13-page="evidence-review">
      <div className="card-header">
        <div>
          <h3 className="section-title">Evidence Review</h3>
          <p className="section-copy">
            Review evidence before summary. Reliability status, calibration records, audit lineage,
            cross-run comparison, contradiction, and human_validation_gap must stay backend-owned and visible.
          </p>
        </div>
        <div className="status-pill queued" id="query-pill">query_pending</div>
      </div>
      <div className="card-body">
        <div className="toolbar">
          <button className="action-button" id="apply-evidence-query" type="button">refresh evidence</button>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="evidence-query-text">query text</label>
            <input id="evidence-query-text" type="text" defaultValue="" />
          </div>
          <div className="field">
            <label htmlFor="evidence-family">family</label>
            <select id="evidence-family" defaultValue="all">
              <option value="all">all</option>
              <option value="input">input</option>
              <option value="trace">trace</option>
              <option value="analysis">analysis</option>
              <option value="output">output</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="evidence-sort">sort</label>
            <select id="evidence-sort" defaultValue="relevance">
              <option value="relevance">relevance</option>
              <option value="newest">newest</option>
              <option value="family">family</option>
            </select>
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Evidence results</div>
            <p className="muted-note" id="evidence-note">
              Evidence query stays pending until a completed run is available.
            </p>
            <div className="product-stack" id="evidence-list" />
          </div>
          <div className="summary-card">
            <strong>Selected saved view</strong>
            <div className="summary-list" id="selected-evidence-view-summary" />
          </div>
        </div>

        <div className="split-grid">
          <div className="summary-card">
            <strong>Selected evidence</strong>
            <div className="summary-list" id="selected-evidence-summary" />
            <div className="detail-stack" id="selected-evidence-detail" />
          </div>
          <div className="summary-card">
            <strong>Cross-run comparison</strong>
            <div className="summary-list" id="cross-run-summary" />
            <div className="detail-stack" id="cross-run-detail" />
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="toolbar">
              <div className="inline-label">Selected decision review</div>
              <div className="status-pill queued" id="decision-review-pill">draft</div>
            </div>
            <div className="summary-card">
              <strong>Selected decision</strong>
              <div className="summary-list" id="selected-decision-log-summary" />
            </div>
            <div className="toolbar">
              <button className="action-button" id="reload-decision-review" type="button">reload review</button>
              <button className="action-button" id="request-decision-review" type="button">request review</button>
              <button className="action-button primary" id="approve-decision-log" type="button">approve</button>
              <button className="action-button" id="request-decision-revision" type="button">needs revision</button>
            </div>
            <div className="summary-card">
              <strong>Review status</strong>
              <div className="summary-list" id="decision-review-summary" />
            </div>
          </div>

          <div className="draft-panel">
            <div className="inline-label">Evidence challenge thread</div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="decision-comment-anchor">Comment anchor</label>
                <select id="decision-comment-anchor" defaultValue="general">
                  <option value="general">general</option>
                  <option value="decision_summary">decision_summary</option>
                  <option value="rationale">rationale</option>
                  <option value="evidence_view">evidence_view</option>
                  <option value="comparison">comparison</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="decision-review-note">Review note</label>
                <textarea
                  id="decision-review-note"
                  rows="3"
                  placeholder="Why the decision is approved, or what still needs revision."
                />
              </div>
              <div className="field">
                <label htmlFor="decision-comment-body">Thread comment</label>
                <textarea
                  id="decision-comment-body"
                  rows="4"
                  placeholder="Flag a weak rationale, ask for stronger evidence, or confirm the study conclusion."
                />
              </div>
            </div>
            <div className="toolbar">
              <button className="action-button primary" id="create-decision-comment" type="button">add comment</button>
              <button className="action-button" id="clear-decision-reply-target" type="button">clear reply target</button>
              <div className="status-pill queued" id="decision-reply-target">reply_to:none</div>
            </div>
            <p className="muted-note">
              Review stays attached to the decision log so approval, objections, and evidence challenges do
              not drift into separate notes or chat tools.
            </p>
            <div className="product-stack" id="decision-comment-list" />
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Export bundles</div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="export-title">Export title</label>
                <input id="export-title" type="text" placeholder="Exec review export" />
              </div>
              <div className="field">
                <label htmlFor="export-format">export_format</label>
                <select id="export-format" defaultValue="bundle_json">
                  <option value="bundle_json">bundle_json</option>
                  <option value="report_markdown">report_markdown</option>
                  <option value="report_json">report_json</option>
                  <option value="report_csv">report_csv</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="export-artifacts">artifact_ids (comma separated, optional)</label>
                <input id="export-artifacts" type="text" placeholder="report.json, summary.json" />
              </div>
            </div>
            <div className="toolbar">
              <button className="action-button primary" id="create-export-bundle" type="button">create export bundle</button>
              <button className="action-button" id="reload-export-bundles" type="button">reload exports</button>
            </div>
            <p className="muted-note">
              Each export preserves the synthetic boundary, source study, source job, and run lineage.
            </p>
            <div className="product-stack" id="export-list" />
          </div>
          <div className="summary-card">
            <strong>Selected export</strong>
            <div className="summary-list" id="selected-export-summary" />
          </div>
        </div>

        <div className="split-grid">
          <div className="draft-panel">
            <div className="inline-label">Share bundles</div>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="share-title">Share title</label>
                <input id="share-title" type="text" placeholder="Board review share" />
              </div>
              <div className="field">
                <label htmlFor="share-expires-days">expires_in_days</label>
                <input id="share-expires-days" type="number" min="1" max="90" step="1" defaultValue="7" />
              </div>
            </div>
            <div className="toolbar">
              <button className="action-button primary" id="create-share-bundle" type="button">create share bundle</button>
              <button className="action-button" id="reload-share-bundles" type="button">reload shares</button>
              <button className="action-button" id="revoke-share-bundle" type="button">revoke selected share</button>
            </div>
            <p className="muted-note">
              Share bundles expose a viewer-safe payload with public path, expiry, and revocation, while
              keeping synthetic boundary and run lineage visible.
            </p>
            <div className="product-stack" id="share-list" />
          </div>
          <div className="summary-card">
            <strong>Selected share</strong>
            <div className="summary-list" id="selected-share-summary" />
          </div>
        </div>
      </div>
    </section>
  );
}
