import React from "react";

export function DebugTraceSection() {
  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Debug trace</h3>
          <p className="section-copy">
            These traces stay secondary. They are here only to verify the product surface is backed by
            the same contracts.
          </p>
        </div>
      </div>
      <div className="card-body">
        <div className="footer-grid">
          <div>
            <strong>Last API response</strong>
            <pre className="debug-panel" id="last-api-json" />
          </div>
          <div>
            <strong>Shell request payload</strong>
            <pre className="debug-panel" id="request-payload-json" />
          </div>
        </div>
      </div>
    </section>
  );
}
