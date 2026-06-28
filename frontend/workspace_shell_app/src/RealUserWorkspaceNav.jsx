import React from "react";

export function RealUserWorkspaceNav() {
  return (
    <aside className="rail" data-m13-nav="real-user-workspace">
      <div className="brand">
        <div className="eyebrow">Stage 15 Product Surface</div>
        <h1>Moss Workspace</h1>
        <p>
          This stage turns the shell into a study-first product surface. Project and study objects are
          now the visible operating layer above the runtime, without dropping the conversational intake
          and evidence-review path.
        </p>
      </div>

      <div className="nav-group">
        <div className="nav-label">Milestone 13</div>
        <div className="nav-item active">New Study</div>
        <div className="nav-item">Study Workspace</div>
        <div className="nav-item">Evidence Review</div>
        <div className="nav-item">Decision + Share Boundary</div>
        <div className="nav-item">Runtime Support</div>
      </div>

      <div className="nav-group">
        <div className="nav-label">Linked Artifacts</div>
        <div className="nav-note">
          <a href="/app-static/demo/workspace_ui_moss_stage14/index.html">Stage 14 snapshot shell</a>
          <br />
          <a href="/app-static/demo/workspace_ui_shared/workspace_shell_app.mjs">Shared shell controller</a>
          <br />
          <a href="/app-static/specs/milestone_11_full_saas_product_surface_design_spec.md">
            Milestone 11 design spec
          </a>
          <br />
          <a href="/app-static/specs/milestone_13_real_user_research_workspace_design_spec.md">
            Milestone 13 design spec
          </a>
          <br />
          <a href="/app-static/specs/workspace_project_study_contract.md">Project / study contract</a>
          <br />
          <a href="/app-static/specs/workspace_study_activity_surface_contract.md">
            Study activity contract
          </a>
          <br />
          <a href="/app-static/specs/workspace_support_surface_contract.md">Support surface contract</a>
          <br />
          <a href="/app-static/specs/workspace_settings_surface_contract.md">Workspace settings contract</a>
          <br />
          <a href="/app-static/specs/workspace_billing_quota_surface_contract.md">Billing / quota contract</a>
          <br />
          <a href="/app-static/specs/workspace_shell_snapshot_contract.md">
            Workspace shell snapshot contract
          </a>
        </div>
      </div>

      <div className="nav-group">
        <div className="nav-label">Why This Surface</div>
        <div className="nav-note">
          The research bottleneck is no longer raw run execution. It is the lack of a durable
          user-facing layer that organizes studies, keeps evidence contextualized, and lets a team
          operate research work without filesystem inspection.
        </div>
      </div>
    </aside>
  );
}
