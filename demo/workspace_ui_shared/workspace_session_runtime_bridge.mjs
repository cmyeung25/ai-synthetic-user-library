function toSummaryRow(id, label, value) {
  return {
    id,
    label,
    value: value === null || value === undefined || value === "" ? "-" : value
  };
}

function mapSessionTone(status) {
  if (status === "auth_error") {
    return "failed";
  }
  if (status === "session_loaded") {
    return "completed";
  }
  return "queued";
}

export function deriveWorkspaceSessionRuntimeBridgeState({
  sessionPayload = null,
  apiBaseUrl = "",
  bearerToken = "",
  lastError = null
}) {
  const trimmedToken = String(bearerToken || "").trim();
  const status = lastError
    ? "auth_error"
    : sessionPayload
      ? "session_loaded"
      : trimmedToken
        ? "session_unloaded"
        : "missing_token";

  const auth = sessionPayload?.auth || null;
  const workspace = sessionPayload?.workspace || null;
  const billing = sessionPayload?.billing_account || null;
  const limits = sessionPayload?.plan_limits || {};
  const jobCounts = sessionPayload?.job_counts || {};
  const paths = sessionPayload?.paths || {};
  const capabilities = sessionPayload?.capabilities || {};

  return {
    session_status: status,
    pill: {
      tone: mapSessionTone(status),
      label: status
    },
    actions: {
      load_workspace_session: {
        intent: "load_workspace_session",
        enabled: Boolean(trimmedToken)
      }
    },
    metrics: {
      workspace_id: auth?.workspace_id || workspace?.workspace_id || null,
      role: auth?.role || null,
      plan_tier: workspace?.plan_tier || null,
      billing_status: billing?.status || null
    },
    session_summary: [
      toSummaryRow("workspace_id", "workspace id", auth?.workspace_id || workspace?.workspace_id),
      toSummaryRow("user_id", "user id", auth?.user_id),
      toSummaryRow("role", "role", auth?.role),
      toSummaryRow("display_name", "display name", workspace?.display_name),
      toSummaryRow("plan_tier", "plan tier", workspace?.plan_tier),
      toSummaryRow("billing_status", "billing status", billing?.status)
    ],
    limit_summary: [
      toSummaryRow("daily_runs", "daily runs", limits?.daily_runs),
      toSummaryRow("max_concurrent_jobs", "max concurrent jobs", limits?.max_concurrent_jobs),
      toSummaryRow("artifact_retention_days", "artifact retention days", limits?.artifact_retention_days),
      toSummaryRow("seat_count", "seat count", billing?.seat_count)
    ],
    job_summary: [
      toSummaryRow("jobs_total", "jobs total", jobCounts?.total),
      toSummaryRow("jobs_queued", "jobs queued", jobCounts?.queued),
      toSummaryRow("jobs_running", "jobs running", jobCounts?.running),
      toSummaryRow("jobs_completed", "jobs completed", jobCounts?.completed),
      toSummaryRow("jobs_failed", "jobs failed", jobCounts?.failed)
    ],
    path_summary: [
      toSummaryRow("workspace_root", "workspace root", paths?.workspace_root),
      toSummaryRow("briefs_root", "briefs root", paths?.briefs_root),
      toSummaryRow("personas_root", "personas root", paths?.personas_root),
      toSummaryRow("runs_root", "runs root", paths?.runs_root)
    ],
    capability_cards: [
      {
        id: "validation_jobs",
        title: "Validation jobs",
        body: "Authenticated job submission and monitoring are available.",
        active: Boolean(capabilities?.validation_jobs)
      },
      {
        id: "evidence_query",
        title: "Evidence query",
        body: "Completed-run evidence query is available through the local runtime.",
        active: Boolean(capabilities?.evidence_query)
      },
      {
        id: "worker_runtime",
        title: "Worker runtime",
        body: "Queued validation jobs can be processed asynchronously by the worker loop.",
        active: Boolean(capabilities?.worker_runtime)
      },
      {
        id: "session_auth",
        title: "Session auth",
        body: "Workspace identity, role, and plan state can now be loaded as one session surface.",
        active: Boolean(capabilities?.session_auth)
      }
    ],
    endpoint_summary: [
      toSummaryRow("session_endpoint", "session endpoint", `${apiBaseUrl}/api/v1/session`),
      toSummaryRow("jobs_endpoint", "jobs endpoint", `${apiBaseUrl}/api/v1/validation-jobs`),
      toSummaryRow("query_endpoint", "query endpoint", `${apiBaseUrl}/api/v1/evidence-query`)
    ],
    boundary_warning: sessionPayload?.synthetic_boundary || (
      status === "auth_error"
        ? lastError
        : "Workspace auth exists to scope runtime access. It does not upgrade synthetic evidence into human proof."
    ),
    json_panel: sessionPayload
  };
}
