import React from "react";

function NavigationItem({
  item,
  isActive,
  tier,
  onNavigateSurface
}) {
  return (
    <a
      className={`nav-item${isActive ? " active is-active" : ""}`}
      data-nav-tier={tier}
      data-nav-id={item.id}
      data-surface-id={item.surface_id}
      href={item.route_path}
      aria-current={isActive ? "page" : undefined}
      onClick={(event) => {
        if (!onNavigateSurface) {
          return;
        }
        event.preventDefault();
        onNavigateSurface(item);
      }}
    >
      <span>{item.label}</span>
      {item.research_loop_step ? <small>{item.research_loop_step}</small> : null}
    </a>
  );
}

export function RealUserWorkspaceNav({
  routeModel,
  onNavigateSurface
}) {
  return (
    <aside
      className="rail"
      data-m13-nav="real-user-workspace"
      data-m16-nav="post-login-workspace"
      data-active-nav={routeModel?.active_nav_id}
      data-active-surface={routeModel?.active_surface_id}
    >
      <div className="brand">
        <div className="eyebrow">Milestone 16 Product Surface</div>
        <h1>Moss Workspace</h1>
        <p>
          The logged-in workspace now follows a study-first IA: start research, continue studies,
          review evidence, decide, and only then drop into governance or support paths.
        </p>
      </div>

      <div className="nav-group">
        <div className="nav-label">Research loop</div>
        {routeModel?.primary_navigation?.map((item) => (
          <NavigationItem
            item={item}
            isActive={routeModel.active_nav_id === item.id}
            key={item.id}
            onNavigateSurface={onNavigateSurface}
            tier="primary"
          />
        ))}
      </div>

      <div className="nav-group secondary-nav-group">
        <div className="nav-label">Governance + support</div>
        {routeModel?.secondary_navigation?.map((item) => (
          <NavigationItem
            item={item}
            isActive={routeModel.active_nav_id === item.id}
            key={item.id}
            onNavigateSurface={onNavigateSurface}
            tier="secondary"
          />
        ))}
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
          <a href="/app-static/specs/post_login_workspace_information_architecture_contract.md">
            Post-login IA contract
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
