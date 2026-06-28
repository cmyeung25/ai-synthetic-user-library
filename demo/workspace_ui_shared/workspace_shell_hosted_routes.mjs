const ROUTE_KIND_SEGMENTS = {
  workspace: "/app/workspace",
  new_study: "/app/new-study",
  project: "/app/projects/",
  study: "/app/studies/",
  evidence_view: "/app/evidence-views/",
  decision_log: "/app/decision-logs/",
  export_bundle: "/app/export-bundles/",
  share_bundle: "/app/share-bundles/",
  support_snapshot: "/app/support-snapshots/",
  job: "/app/jobs/"
};

const ROUTE_KIND_TO_SELECTION_FIELD = {
  project: "projectId",
  study: "studyId",
  evidence_view: "evidenceViewId",
  decision_log: "decisionLogId",
  export_bundle: "exportBundleId",
  share_bundle: "shareBundleId",
  support_snapshot: "supportSnapshotId",
  job: "jobId"
};

const ROUTE_KIND_TO_STATE_FIELD = {
  project: "selectedProjectId",
  study: "selectedStudyId",
  evidence_view: "selectedEvidenceViewId",
  decision_log: "selectedDecisionLogId",
  export_bundle: "selectedExportBundleId",
  share_bundle: "selectedShareBundleId",
  support_snapshot: "selectedSupportSnapshotId",
  job: "selectedJobId"
};

const FALLBACK_ROUTE_KINDS = [
  "support_snapshot",
  "share_bundle",
  "export_bundle",
  "decision_log",
  "evidence_view",
  "study",
  "project",
  "job",
  "new_study",
  "workspace"
];

const STATIC_ROUTE_KINDS = new Set(["workspace", "new_study"]);

function normalizeSearch(search = "") {
  return String(search || "").startsWith("?") ? String(search).slice(1) : String(search || "");
}

function inferRouteKindFromPath(pathname = "") {
  const normalizedPath = String(pathname || "").replace(/\/+$/, "") || "/app/workspace";
  if (normalizedPath === "/app/workspace") {
    return "workspace";
  }
  if (normalizedPath === ROUTE_KIND_SEGMENTS.new_study) {
    return "new_study";
  }
  const routeKinds = Object.keys(ROUTE_KIND_SEGMENTS).filter((routeKind) => routeKind !== "workspace");
  for (const routeKind of routeKinds) {
    if (normalizedPath.startsWith(ROUTE_KIND_SEGMENTS[routeKind])) {
      return routeKind;
    }
  }
  return "workspace";
}

function inferRouteKindFromSelection(selection = {}) {
  for (const routeKind of FALLBACK_ROUTE_KINDS) {
    const field = ROUTE_KIND_TO_SELECTION_FIELD[routeKind];
    if (field && String(selection[field] || "").trim()) {
      return routeKind;
    }
  }
  return "workspace";
}

function identifierFromPath(pathname = "", routeKind = "workspace") {
  if (routeKind === "workspace") {
    return "";
  }
  if (STATIC_ROUTE_KINDS.has(routeKind)) {
    return "";
  }
  const normalizedPath = String(pathname || "").replace(/\/+$/, "");
  const prefix = ROUTE_KIND_SEGMENTS[routeKind];
  if (!prefix || !normalizedPath.startsWith(prefix)) {
    return "";
  }
  return decodeURIComponent(normalizedPath.slice(prefix.length)).trim();
}

function selectionFromInputs(routeContext = {}, params = new URLSearchParams(), pathname = "") {
  const inferredRouteKind = normalizeHostedWorkspaceRouteKind(
    routeContext.route_kind || inferRouteKindFromPath(pathname)
  );
  return {
    projectId:
      routeContext.project_id ||
      params.get("project_id") ||
      (inferredRouteKind === "project" ? identifierFromPath(pathname, "project") : ""),
    studyId:
      routeContext.study_id ||
      params.get("study_id") ||
      (inferredRouteKind === "study" ? identifierFromPath(pathname, "study") : ""),
    evidenceViewId:
      routeContext.evidence_view_id ||
      params.get("evidence_view_id") ||
      (inferredRouteKind === "evidence_view" ? identifierFromPath(pathname, "evidence_view") : ""),
    decisionLogId:
      routeContext.decision_log_id ||
      params.get("decision_log_id") ||
      (inferredRouteKind === "decision_log" ? identifierFromPath(pathname, "decision_log") : ""),
    exportBundleId:
      routeContext.export_bundle_id ||
      params.get("export_bundle_id") ||
      (inferredRouteKind === "export_bundle" ? identifierFromPath(pathname, "export_bundle") : ""),
    shareBundleId:
      routeContext.share_bundle_id ||
      params.get("share_bundle_id") ||
      (inferredRouteKind === "share_bundle" ? identifierFromPath(pathname, "share_bundle") : ""),
    supportSnapshotId:
      routeContext.support_snapshot_id ||
      params.get("support_snapshot_id") ||
      (inferredRouteKind === "support_snapshot" ? identifierFromPath(pathname, "support_snapshot") : ""),
    jobId:
      routeContext.job_id ||
      params.get("job_id") ||
      (inferredRouteKind === "job" ? identifierFromPath(pathname, "job") : "")
  };
}

function routePathForKind(routeKind, identifier) {
  if (routeKind === "workspace") {
    return ROUTE_KIND_SEGMENTS.workspace;
  }
  if (routeKind === "new_study") {
    return ROUTE_KIND_SEGMENTS.new_study;
  }
  if (!identifier) {
    return ROUTE_KIND_SEGMENTS.workspace;
  }
  return `${ROUTE_KIND_SEGMENTS[routeKind]}${encodeURIComponent(identifier)}`;
}

function readSelectedIdentifier(state = {}, routeKind = "workspace") {
  const field = ROUTE_KIND_TO_STATE_FIELD[routeKind];
  return field ? String(state?.[field] || "").trim() : "";
}

export function normalizeHostedWorkspaceRouteKind(routeKind = "") {
  const candidate = String(routeKind || "").trim();
  return Object.hasOwn(ROUTE_KIND_SEGMENTS, candidate) ? candidate : "workspace";
}

export function createHostedWorkspaceRouteState({
  routeContext = {},
  pathname = "",
  search = ""
} = {}) {
  const params = new URLSearchParams(normalizeSearch(search));
  const selection = selectionFromInputs(routeContext, params, pathname);
  const preferredKind = normalizeHostedWorkspaceRouteKind(
    routeContext.route_kind || inferRouteKindFromPath(pathname) || inferRouteKindFromSelection(selection)
  );
  return {
    routeKind: preferredKind,
    selection
  };
}

export function deriveHostedWorkspaceRoutePath({
  state = {},
  preferredRouteKind = "workspace"
} = {}) {
  const normalizedKind = normalizeHostedWorkspaceRouteKind(preferredRouteKind);
  if (normalizedKind === "new_study") {
    return routePathForKind(normalizedKind, "");
  }
  const preferredIdentifier = readSelectedIdentifier(state, normalizedKind);
  if (normalizedKind !== "workspace" && preferredIdentifier) {
    return routePathForKind(normalizedKind, preferredIdentifier);
  }

  for (const routeKind of FALLBACK_ROUTE_KINDS) {
    if (routeKind === "workspace") {
      continue;
    }
    const identifier = readSelectedIdentifier(state, routeKind);
    if (identifier) {
      return routePathForKind(routeKind, identifier);
    }
  }
  return ROUTE_KIND_SEGMENTS.workspace;
}
