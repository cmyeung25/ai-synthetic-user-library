function compactStrings(values) {
  return [...new Set((values || []).filter((value) => typeof value === "string" && value.trim().length > 0))];
}

function normalizeJobStatus(status) {
  if (status === "canceled") {
    return "failed";
  }
  return status || "queued";
}

function buildArtifactRefsFromJob(job) {
  const metadataRefs = job?.metadata?.artifact_refs;
  if (Array.isArray(metadataRefs) && metadataRefs.length) {
    return metadataRefs;
  }

  const outputRunPath = job?.output_run_path;
  if (!outputRunPath) {
    return [];
  }

  return compactStrings([
    `${outputRunPath}/run_contract.json`,
    `${outputRunPath}/report.json`,
    `${outputRunPath}/summary.md`
  ]);
}

export function canSubmitValidationJobFromDraftPlan(draftPlan) {
  const confirmationStatus = draftPlan?.confirmation?.status;
  const draftStatus = draftPlan?.status;
  const blockingReasons = draftPlan?.remediation?.blocking_reasons || [];
  const confirmationDefined = confirmationStatus !== undefined && confirmationStatus !== null;

  return (
    blockingReasons.length === 0 &&
    (
      confirmationStatus === "confirmed" ||
      (!confirmationDefined && draftStatus === "confirmed")
    )
  );
}

export function createWorkspaceValidationBridgeDemoContext() {
  return {
    workspace_id: "ws_api_demo",
    brief_path: "briefs/brief.json",
    persona_dir: "personas",
    panel_type: "mainstream",
    sample_size: 5,
    provider_name: "mock",
    priority: "normal",
    max_retries: 1,
    run_root: "runs",
    idempotency_key: "stage12-demo-job"
  };
}

export function createWorkspaceValidationBridgeDemoJob(status = "completed") {
  return {
    job_id: `job_api_demo_${status}`,
    workspace_id: "ws_api_demo",
    brief_id: "brief_001",
    requested_by_user_id: "owner_api",
    panel_spec: {
      panel_type: "mainstream",
      sample_size: 5,
      random_seed: 11,
      filters: {},
      preset_name: "mainstream"
    },
    provider_name: "mock",
    status,
    priority: "normal",
    input_artifact_path: "briefs/brief.json",
    persona_dir_path: "personas",
    output_run_path: status === "completed" ? "runs/job_api_demo_completed" : null,
    retry_count: status === "failed" ? 1 : 0,
    created_at: "2026-06-27T22:45:00Z",
    started_at: status === "queued" ? null : "2026-06-27T22:46:00Z",
    finished_at: status === "completed" || status === "failed" ? "2026-06-27T22:47:00Z" : null,
    idempotency_key: "stage12-demo-job",
    last_error: status === "failed" ? "stimulus render timeout before trace packaging" : "",
    metadata: {
      workspace_id: "ws_api_demo",
      draft_plan_id: "draft_plan_20260627_proto_07",
      primary_mode: "prototype_validation",
      first_task: "connect data",
      artifact_refs: status === "completed"
        ? [
            "runs/job_api_demo_completed/run_contract.json",
            "runs/job_api_demo_completed/report.json",
            "runs/job_api_demo_completed/summary.md"
          ]
        : [],
      current_step: status === "running" ? "persona_panel_execution" : status === "completed" ? "report_packaging" : null
    }
  };
}

export function buildValidationJobRequestFromDraftPlan({
  draftPlan,
  workspaceContext
}) {
  const panelType = workspaceContext?.panel_type || draftPlan?.proposed_run?.panel_type || "mainstream";
  const sampleSize = workspaceContext?.sample_size || draftPlan?.proposed_run?.sample_size || 5;
  const providerName = workspaceContext?.provider_name || draftPlan?.proposed_run?.provider_name || "mock";

  return {
    brief_path: workspaceContext?.brief_path || "",
    persona_dir: workspaceContext?.persona_dir || "",
    panel_spec: {
      panel_type: panelType,
      sample_size: sampleSize,
      random_seed: workspaceContext?.random_seed || 11
    },
    provider_name: providerName,
    priority: workspaceContext?.priority || "normal",
    max_retries: workspaceContext?.max_retries || 1,
    idempotency_key: workspaceContext?.idempotency_key || "",
    run_root: workspaceContext?.run_root || "runs",
    metadata: {
      workspace_id: workspaceContext?.workspace_id || draftPlan?.workspace_id || null,
      draft_plan_id: draftPlan?.draft_plan_id || null,
      primary_mode: draftPlan?.inference?.primary_mode || null,
      first_task: draftPlan?.proposed_run?.first_task || null,
      source_intent: draftPlan?.source_intent?.user_text || null,
      evidence_boundary: draftPlan?.evidence_boundary || null,
      bridge_version: "workspace-validation-job-bridge/v0-draft"
    }
  };
}

export function deriveRunRecordFromValidationJob(job) {
  const status = normalizeJobStatus(job?.status);
  const metadata = job?.metadata || {};

  return {
    job_id: job?.job_id || null,
    status,
    queue_position: metadata.queue_position ?? null,
    worker_id: metadata.worker_id || null,
    current_step: metadata.current_step || (status === "completed" ? "report_packaging" : status === "running" ? "persona_panel_execution" : null),
    attempt_count: job?.retry_count ?? 0,
    last_event_at: job?.finished_at || job?.started_at || job?.created_at || null,
    failure_reason: job?.last_error || null,
    artifact_refs: buildArtifactRefsFromJob(job)
  };
}

export function deriveWorkspaceValidationBridgeState({
  draftPlan,
  workspaceContext,
  jobList = [],
  selectedJob = null,
  apiBaseUrl = "",
  lastError = null
}) {
  const requestPayload = buildValidationJobRequestFromDraftPlan({
    draftPlan,
    workspaceContext
  });
  const submissionReady = canSubmitValidationJobFromDraftPlan(draftPlan);
  const runRecord = selectedJob ? deriveRunRecordFromValidationJob(selectedJob) : null;

  return {
    bridge_status: lastError
      ? "bridge_error"
      : selectedJob
        ? "job_loaded"
        : submissionReady
          ? "ready_to_submit"
          : "draft_only",
    submission_ready: submissionReady,
    api_base_url: apiBaseUrl,
    request_payload: requestPayload,
    job_count: jobList.length,
    selected_job_id: selectedJob?.job_id || null,
    selected_job_status: selectedJob?.status || null,
    derived_run_record: runRecord,
    endpoint_summary: {
      submit: "POST /api/v1/validation-jobs",
      list: "GET /api/v1/validation-jobs",
      detail: "GET /api/v1/validation-jobs/{job_id}",
      query: "GET /api/v1/evidence-query"
    },
    live_review_gap: "The validation-job API and metadata-backed evidence query now exist, but replay remains limited to artifacts that actually carry trace-linked steps.",
    warning: lastError || null
  };
}
