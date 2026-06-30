export const POST_LOGIN_WORKSPACE_IA_CONTRACT_VERSION = "post-login-workspace-ia/v1";

export const POST_LOGIN_WORKSPACE_IA_MILESTONE_ID =
  "workstream.post_login_workspace_ia_and_active_route_shell";

export const POST_LOGIN_PRIMARY_NAVIGATION = [
  {
    id: "new-study",
    label: "New Study",
    route_path: "/app/new-study",
    surface_id: "new-study",
    research_loop_step: "Ask"
  },
  {
    id: "studies",
    label: "Studies",
    route_path: "/app/workspace",
    surface_id: "study-workspace",
    research_loop_step: "Run"
  },
  {
    id: "evidence",
    label: "Evidence",
    route_path: "/app/workspace#evidence-list",
    surface_id: "evidence-review",
    research_loop_step: "Review Evidence"
  },
  {
    id: "decisions",
    label: "Decisions",
    route_path: "/app/workspace#decision-log-list",
    surface_id: "evidence-review",
    research_loop_step: "Decide"
  },
  {
    id: "activity",
    label: "Activity",
    route_path: "/app/workspace#study-activity-list",
    surface_id: "study-workspace",
    research_loop_step: "Audit"
  }
];

export const POST_LOGIN_SECONDARY_NAVIGATION = [
  {
    id: "settings",
    label: "Workspace settings",
    route_path: "/app/workspace#workspace-settings-summary",
    surface_id: "settings"
  },
  {
    id: "support",
    label: "Support",
    route_path: "/app/workspace#support-gate-summary",
    surface_id: "support"
  },
  {
    id: "billing",
    label: "Billing",
    route_path: "/app/workspace#workspace-billing-summary",
    surface_id: "settings"
  },
  {
    id: "api-tokens",
    label: "API tokens",
    route_path: "/app/workspace#workspace-token-list",
    surface_id: "settings"
  },
  {
    id: "retention-governance",
    label: "Retention / governance",
    route_path: "/app/workspace#workspace-policy-summary",
    surface_id: "settings"
  }
];

export const POST_LOGIN_ROUTE_SURFACES = [
  {
    id: "new-study",
    title: "New Study",
    tier: "primary",
    route_intent: "/app/new-study",
    purpose:
      "Start with plain-language research intent, progressive clarification, and explicit plan confirmation before execution."
  },
  {
    id: "study-workspace",
    title: "Study Workspace",
    tier: "primary",
    route_intent: "/app/studies/{study_id}",
    purpose:
      "Continue a durable study with latest run state, activity, decision context, and next useful research action."
  },
  {
    id: "evidence-review",
    title: "Evidence Review",
    tier: "primary",
    route_intent: "/app/jobs/{job_id}",
    purpose:
      "Review evidence, replay lineage, cross-run comparison, calibration records, decisions, export, and share boundaries."
  },
  {
    id: "settings",
    title: "Workspace Settings",
    tier: "secondary",
    route_intent: "/app/settings/*",
    purpose:
      "Keep members, billing, quota, retention, audit, and API token controls reachable without becoming the landing model."
  },
  {
    id: "support",
    title: "Support",
    tier: "secondary",
    route_intent: "/app/support/*",
    purpose:
      "Handle blocked submissions, failed jobs, and support snapshots without replacing the study-first research loop."
  },
  {
    id: "debug",
    title: "Debug Trace",
    tier: "diagnostic",
    route_intent: "developer-only",
    purpose:
      "Keep raw payload trace available for operators without making debug state part of normal post-login navigation."
  }
];

const ROUTE_KIND_RULES = {
  new_study: {
    active_surface_id: "new-study",
    active_nav_id: "new-study",
    landing_rule: "explicit_new_study_route"
  },
  project: {
    active_surface_id: "study-workspace",
    active_nav_id: "studies",
    landing_rule: "project_deep_link_preserves_study_context"
  },
  study: {
    active_surface_id: "study-workspace",
    active_nav_id: "studies",
    landing_rule: "study_deep_link_opens_study_workspace"
  },
  job: {
    active_surface_id: "evidence-review",
    active_nav_id: "evidence",
    landing_rule: "job_deep_link_opens_evidence_review_with_study_context"
  },
  evidence_view: {
    active_surface_id: "evidence-review",
    active_nav_id: "evidence",
    landing_rule: "saved_evidence_view_deep_link"
  },
  decision_log: {
    active_surface_id: "evidence-review",
    active_nav_id: "decisions",
    landing_rule: "decision_log_deep_link_opens_decision_review"
  },
  export_bundle: {
    active_surface_id: "evidence-review",
    active_nav_id: "evidence",
    landing_rule: "export_review_deep_link_preserves_evidence_context"
  },
  share_bundle: {
    active_surface_id: "evidence-review",
    active_nav_id: "evidence",
    landing_rule: "share_review_deep_link_preserves_boundary_context"
  },
  support_snapshot: {
    active_surface_id: "support",
    active_nav_id: "support",
    landing_rule: "support_snapshot_deep_link_opens_secondary_support_surface"
  }
};

function normalizeRouteKind(routeKind = "workspace") {
  const normalized = String(routeKind || "").trim();
  return normalized || "workspace";
}

function deriveWorkspaceLandingRule({ hasActiveStudy = true } = {}) {
  if (hasActiveStudy) {
    return {
      active_surface_id: "study-workspace",
      active_nav_id: "studies",
      landing_rule: "active_study_lands_on_study_workspace"
    };
  }
  return {
    active_surface_id: "new-study",
    active_nav_id: "new-study",
    landing_rule: "no_study_lands_on_new_study"
  };
}

export function derivePostLoginWorkspaceRouteModel({
  routeKind = "workspace",
  hasActiveStudy = true,
  primaryNavigation = POST_LOGIN_PRIMARY_NAVIGATION,
  secondaryNavigation = POST_LOGIN_SECONDARY_NAVIGATION,
  routeSurfaces = POST_LOGIN_ROUTE_SURFACES
} = {}) {
  const activeRouteKind = normalizeRouteKind(routeKind);
  const routeRule =
    activeRouteKind === "workspace"
      ? deriveWorkspaceLandingRule({ hasActiveStudy })
      : ROUTE_KIND_RULES[activeRouteKind] || deriveWorkspaceLandingRule({ hasActiveStudy });
  const surfaces = routeSurfaces.map((surface) => ({
    ...surface,
    is_active: surface.id === routeRule.active_surface_id
  }));

  return {
    contract_version: POST_LOGIN_WORKSPACE_IA_CONTRACT_VERSION,
    milestone_id: POST_LOGIN_WORKSPACE_IA_MILESTONE_ID,
    active_route_kind: activeRouteKind,
    active_surface_id: routeRule.active_surface_id,
    active_nav_id: routeRule.active_nav_id,
    landing_rule: routeRule.landing_rule,
    preserves_study_context: [
      "project",
      "study",
      "job",
      "evidence_view",
      "decision_log",
      "export_bundle",
      "share_bundle",
      "support_snapshot"
    ].includes(activeRouteKind),
    primary_navigation: primaryNavigation,
    secondary_navigation: secondaryNavigation,
    surfaces,
    debug_surface_expanded_by_default: false,
    acceptance_gates: [
      "one_expanded_primary_or_secondary_surface",
      "research_nav_before_governance_nav",
      "job_deep_link_routes_to_evidence_review",
      "secondary_governance_available_but_not_default_landing",
      "visual_smoke_checks_for_overlap_text_occlusion_and_blocked_actions"
    ]
  };
}

export function isPostLoginWorkspaceSurfaceActive(routeModel = {}, surfaceId = "") {
  return routeModel.active_surface_id === surfaceId;
}
