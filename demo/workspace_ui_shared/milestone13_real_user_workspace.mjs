export const MILESTONE13_OPERATING_LOOP = [
  "Ask",
  "Clarify",
  "Confirm Plan",
  "Run",
  "Review Evidence",
  "Compare",
  "Decide",
  "Share With Boundary"
];

export const MILESTONE13_REAL_USER_PAGES = [
  {
    id: "new-study",
    title: "New Study",
    route_intent: "/app/new-study",
    purpose: "Start from plain-language research intent, gather only missing high-signal context, infer the plan, and require explicit confirmation before execution.",
    user_job: "I need to describe what I need to learn without choosing an internal mode or filling a run schema.",
    default_loop_steps: ["Ask", "Clarify", "Confirm Plan"],
    primary_selectors: [
      "research-intent",
      "desired-outcome",
      "artifact-files",
      "study-actions",
      "draft-summary",
      "boundary-copy"
    ],
    required_evidence_boundaries: [
      "synthetic-evidence boundary",
      "known human-validation gaps",
      "explicit plan confirmation before run execution"
    ],
    anti_patterns: [
      "mode-first setup",
      "workflow-builder canvas",
      "brief_path as primary UX",
      "job-first navigation"
    ]
  },
  {
    id: "study-workspace",
    title: "Study Workspace",
    route_intent: "/app/studies/{study_id}",
    purpose: "Keep the selected study, its latest run, activity, collaboration objects, and next research action in one durable workspace.",
    user_job: "I need to continue a study and understand what has happened without reopening raw artifacts or reconstructing context.",
    default_loop_steps: ["Run", "Review Evidence", "Decide"],
    primary_selectors: [
      "selected-project-summary",
      "selected-study-summary",
      "job-list",
      "study-activity-list",
      "evidence-view-list",
      "decision-log-list"
    ],
    required_evidence_boundaries: [
      "selected study remains primary object",
      "blocked and failed states stay visible",
      "activity and decisions remain attached to study context"
    ],
    anti_patterns: [
      "generic tenant dashboard",
      "settings-first homepage",
      "chat-only memory",
      "report-only endpoint"
    ]
  },
  {
    id: "evidence-review",
    title: "Evidence Review",
    route_intent: "/app/jobs/{job_id}",
    purpose: "Review evidence before summary, inspect replay and lineage, compare runs, and preserve calibration and human-validation gaps.",
    user_job: "I need to judge what the synthetic evidence actually supports, what contradicts it, and what still needs human validation.",
    default_loop_steps: ["Review Evidence", "Compare", "Decide", "Share With Boundary"],
    primary_selectors: [
      "evidence-list",
      "selected-evidence-summary",
      "selected-evidence-detail",
      "cross-run-summary",
      "cross-run-detail",
      "selected-decision-log-summary"
    ],
    required_evidence_boundaries: [
      "reliability status",
      "calibration records",
      "audit lineage",
      "contradiction and missing context",
      "human_validation_gap"
    ],
    anti_patterns: [
      "summary-only review",
      "hidden uncertainty",
      "frontend reliability scoring",
      "share without boundary"
    ]
  }
];

export function deriveMilestone13ActivePageIdFromRouteKind(routeKind = "workspace") {
  const normalizedRouteKind = String(routeKind || "").trim();
  if (normalizedRouteKind === "new_study" || normalizedRouteKind === "workspace") {
    return "new-study";
  }
  if (normalizedRouteKind === "study" || normalizedRouteKind === "project") {
    return "study-workspace";
  }
  if (
    [
      "job",
      "evidence_view",
      "decision_log",
      "export_bundle",
      "share_bundle",
      "support_snapshot"
    ].includes(normalizedRouteKind)
  ) {
    return "evidence-review";
  }
  return "new-study";
}

export function deriveMilestone13RealUserWorkspaceModel({
  activePageId = "new-study",
  pages = MILESTONE13_REAL_USER_PAGES,
  operatingLoop = MILESTONE13_OPERATING_LOOP
} = {}) {
  const pageModels = pages.map((page, index) => ({
    ...page,
    ordinal: index + 1,
    is_active: page.id === activePageId,
    loop_coverage: operatingLoop.map((step) => ({
      step,
      state: page.default_loop_steps.includes(step) ? "primary" : "context"
    })),
    acceptance_summary: [
      ...page.required_evidence_boundaries,
      ...page.anti_patterns.map((pattern) => `avoid ${pattern}`)
    ]
  }));

  return {
    contract_version: "milestone13-real-user-workspace/v0-draft",
    milestone_id: "milestone.real_user_research_workspace",
    status: "in_progress",
    active_page_id: activePageId,
    operating_loop: operatingLoop,
    pages: pageModels,
    completion_bar: {
      required_pages: ["new-study", "study-workspace", "evidence-review"],
      component_cleanup_required: true,
      backend_reliability_contract_required: true,
      synthetic_boundary_required: true
    },
    warnings: [
      "Do not hide Milestone 12 reliability, contradiction, calibration, audit lineage, or human-validation-gap state.",
      "Do not make job, prompt, or mode taxonomy the first product object."
    ]
  };
}

export function getMilestone13PageById(pageId, pages = MILESTONE13_REAL_USER_PAGES) {
  return pages.find((page) => page.id === pageId) || null;
}
