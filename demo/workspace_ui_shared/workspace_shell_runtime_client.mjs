function buildHeaders(bearerToken, extra = {}) {
  const normalizedToken = String(bearerToken || "").trim();
  if (!normalizedToken) {
    return {
      ...extra
    };
  }
  return {
    ...extra,
    Authorization: `Bearer ${normalizedToken}`
  };
}

function upsertById(items = [], nextItem = null, idField = "id") {
  if (!nextItem || !nextItem[idField]) {
    return items;
  }
  const existing = (items || []).filter((item) => item?.[idField] !== nextItem[idField]);
  return [nextItem, ...existing];
}

async function readJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const error = payload?.message || payload?.error || `HTTP ${response.status}`;
    throw new Error(error);
  }
  return payload;
}

function mergeRuntimeSyncState(currentRuntimeSync = {}, snapshotRuntimeSync = {}) {
  return {
    ...currentRuntimeSync,
    interval_ms: snapshotRuntimeSync.poll_recommended_ms || currentRuntimeSync.interval_ms || 4000
  };
}

function mergeProductSurfaceState(state, snapshot = {}) {
  const projects = snapshot.projects || state.liveProjects || [];
  const selectedProjectId = snapshot.selected_project_id || state.selectedProjectId || projects[0]?.project_id || null;
  const studies = snapshot.studies || state.liveStudies || [];
  const selectedStudyId = snapshot.selected_study_id || state.selectedStudyId || studies[0]?.study_id || null;
  const exportBundles = snapshot.export_bundles || state.liveExportBundles || [];
  const selectedExportBundleId = snapshot.selected_export_bundle_id || state.selectedExportBundleId || exportBundles[0]?.export_bundle_id || null;
  const shareBundles = snapshot.share_bundles || state.liveShareBundles || [];
  const selectedShareBundleId = snapshot.selected_share_bundle_id || state.selectedShareBundleId || shareBundles[0]?.share_bundle_id || null;
  const supportSnapshots = snapshot.support_snapshots || state.liveSupportSnapshots || [];
  const selectedSupportSnapshotId = (
    snapshot.selected_support_snapshot_id
    || state.selectedSupportSnapshotId
    || supportSnapshots[0]?.support_snapshot_id
    || null
  );
  return {
    liveProjects: projects,
    selectedProjectId,
    liveStudies: studies,
    selectedStudyId,
    liveExportBundles: exportBundles,
    selectedExportBundleId,
    liveShareBundles: shareBundles,
    selectedShareBundleId,
    liveSupportSnapshots: supportSnapshots,
    selectedSupportSnapshotId
  };
}

function applyWorkspaceSettingsPayload(state, payload) {
  const workspaceSettings = payload?.workspace_settings || null;
  if (!workspaceSettings) {
    return state;
  }
  return {
    ...state,
    liveWorkspaceSettings: workspaceSettings,
    liveError: null,
    lastApiResponse: payload
  };
}

function applyWorkspaceAuditEventsPayload(state, payload) {
  const auditHistory = payload?.audit_history || null;
  if (!auditHistory) {
    return state;
  }
  return {
    ...state,
    liveAuditEvents: auditHistory.audit_events || [],
    liveAuditQuery: auditHistory.filters || null,
    liveError: null,
    lastApiResponse: payload
  };
}

function applyWorkspaceShellSnapshot(state, payload) {
  const snapshot = payload?.snapshot || null;
  if (!snapshot) {
    return state;
  }
  const jobs = snapshot.jobs || [];
  const productSurface = mergeProductSurfaceState(state, snapshot);
  return {
    ...state,
    ...productSurface,
    mode: jobs.length || snapshot.selected_job ? "live" : state.mode,
    liveSession: snapshot.session || null,
    liveJobs: jobs,
    selectedJobId: snapshot.selected_job_id || jobs[0]?.job_id || null,
    liveEvidenceQuery: snapshot.evidence_query || null,
    liveError: null,
    sessionError: null,
    runtimeSync: mergeRuntimeSyncState(state.runtimeSync, snapshot.runtime_sync),
    lastApiResponse: payload
  };
}

function buildWorkspaceShellParams({
  state,
  queryText = "",
  activeFamily = "all",
  sortBy = "relevance",
  selectedResultId = "",
  selectedReplayStepId = "",
  selectedComparisonRunId = ""
}) {
  const params = new URLSearchParams({
    query_text: queryText,
    active_family: activeFamily,
    sort_by: sortBy
  });
  if (state.selectedProjectId) {
    params.set("project_id", state.selectedProjectId);
  }
  if (state.selectedStudyId) {
    params.set("study_id", state.selectedStudyId);
  }
  if (state.selectedJobId) {
    params.set("job_id", state.selectedJobId);
  }
  if (selectedResultId) {
    params.set("selected_result_id", selectedResultId);
  }
  if (selectedReplayStepId) {
    params.set("selected_replay_step_id", selectedReplayStepId);
  }
  if (selectedComparisonRunId) {
    params.set("selected_comparison_run_id", selectedComparisonRunId);
  }
  return params;
}

function buildEvidenceQueryParams({
  state,
  queryText = "",
  activeFamily = "all",
  sortBy = "relevance",
  selectedResultId = "",
  selectedReplayStepId = "",
  selectedComparisonRunId = ""
}) {
  const params = new URLSearchParams({
    job_id: state.selectedJobId,
    query_text: queryText,
    active_family: activeFamily,
    sort_by: sortBy
  });
  if (selectedResultId) {
    params.set("selected_result_id", selectedResultId);
  }
  if (selectedReplayStepId) {
    params.set("selected_replay_step_id", selectedReplayStepId);
  }
  if (selectedComparisonRunId) {
    params.set("selected_comparison_run_id", selectedComparisonRunId);
  }
  return params;
}

export function selectWorkspaceRuntimeJob(state, jobId) {
  return {
    ...state,
    selectedJobId: jobId,
    liveEvidenceQuery: null
  };
}

export function selectWorkspaceRuntimeProject(state, projectId) {
  return {
    ...state,
    selectedProjectId: projectId,
    selectedStudyId: null,
    liveStudyActivity: null,
    selectedEvidenceViewId: null,
    selectedDecisionLogId: null,
    selectedExportBundleId: null,
    selectedShareBundleId: null,
    selectedSupportSnapshotId: null,
    selectedJobId: null,
    liveStudies: [],
    liveEvidenceViews: [],
    liveDecisionLogs: [],
    liveDecisionComments: [],
    liveExportBundles: [],
    liveShareBundles: [],
    liveSupportSnapshots: [],
    liveSupportDiagnostics: null,
    liveEvidenceQuery: null
  };
}

export function selectWorkspaceRuntimeStudy(state, studyId) {
  return {
    ...state,
    selectedStudyId: studyId,
    liveStudyActivity: null,
    selectedEvidenceViewId: null,
    selectedDecisionLogId: null,
    selectedExportBundleId: null,
    selectedShareBundleId: null,
    selectedSupportSnapshotId: null,
    selectedJobId: null,
    liveEvidenceViews: [],
    liveDecisionLogs: [],
    liveDecisionComments: [],
    liveExportBundles: [],
    liveShareBundles: [],
    liveSupportSnapshots: [],
    liveSupportDiagnostics: null,
    liveEvidenceQuery: null
  };
}

export function selectWorkspaceRuntimeExportBundle(state, exportBundleId) {
  return {
    ...state,
    selectedExportBundleId: exportBundleId,
    selectedShareBundleId: null,
    liveShareBundles: []
  };
}

export function selectWorkspaceRuntimeShareBundle(state, shareBundleId) {
  return {
    ...state,
    selectedShareBundleId: shareBundleId
  };
}

export function selectWorkspaceRuntimeSupportSnapshot(state, supportSnapshotId) {
  return {
    ...state,
    selectedSupportSnapshotId: supportSnapshotId
  };
}

export function selectWorkspaceRuntimeEvidenceView(state, evidenceViewId) {
  return {
    ...state,
    selectedEvidenceViewId: evidenceViewId
  };
}

export function selectWorkspaceRuntimeDecisionLog(state, decisionLogId) {
  return {
    ...state,
    selectedDecisionLogId: decisionLogId,
    liveDecisionComments: []
  };
}

export function switchWorkspaceRuntimeToSample(state, { selectedJobId = null } = {}) {
  return {
    ...state,
    mode: "sample",
    selectedJobId: selectedJobId || state.selectedJobId,
    liveError: null,
    sessionError: null,
    liveEvidenceQuery: null,
    liveSupportDiagnostics: null,
    liveSupportSnapshots: [],
    selectedSupportSnapshotId: null,
    liveEvidenceViews: state.liveEvidenceViews || [],
    selectedEvidenceViewId: state.selectedEvidenceViewId || null,
    liveDecisionLogs: state.liveDecisionLogs || [],
    selectedDecisionLogId: state.selectedDecisionLogId || null,
    liveDecisionComments: state.liveDecisionComments || [],
    liveWorkspaceSettings: state.liveWorkspaceSettings || null,
    liveAuditEvents: state.liveAuditEvents || [],
    liveAuditQuery: state.liveAuditQuery || null,
    lastIssuedApiToken: state.lastIssuedApiToken || null,
    lastApiResponse: { mode: "sample" }
  };
}

export async function loadWorkspaceSettings({
  state,
  apiBaseUrl,
  bearerToken,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/workspace-settings`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return applyWorkspaceSettingsPayload(state, payload);
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceAuditEvents({
  state,
  apiBaseUrl,
  bearerToken,
  targetType = "",
  actionPrefix = "",
  limit = 20,
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    if (targetType) {
      params.set("target_type", targetType);
    }
    if (actionPrefix) {
      params.set("action_prefix", actionPrefix);
    }
    params.set("limit", String(limit));
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/audit-events?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return applyWorkspaceAuditEventsPayload(state, payload);
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function upsertWorkspaceMember({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/workspace-members`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const memberPayload = await readJsonResponse(response);
    return {
      ...applyWorkspaceSettingsPayload(state, memberPayload),
      lastIssuedApiToken: state.lastIssuedApiToken || null
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function updateWorkspaceBilling({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/workspace-billing`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const billingPayload = await readJsonResponse(response);
    return {
      ...applyWorkspaceSettingsPayload(state, billingPayload),
      lastIssuedApiToken: state.lastIssuedApiToken || null
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function issueWorkspaceApiToken({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/api-tokens`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const tokenPayload = await readJsonResponse(response);
    const nextState = applyWorkspaceSettingsPayload(state, tokenPayload);
    return {
      ...nextState,
      lastIssuedApiToken: tokenPayload.api_token || null
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function revokeWorkspaceApiToken({
  state,
  apiBaseUrl,
  bearerToken,
  tokenId = "",
  fetchImpl = fetch
}) {
  const effectiveTokenId = tokenId || "";
  if (!effectiveTokenId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/api-tokens/${encodeURIComponent(effectiveTokenId)}/revoke`, {
      method: "POST",
      headers: buildHeaders(bearerToken)
    });
    const tokenPayload = await readJsonResponse(response);
    const nextState = applyWorkspaceSettingsPayload(state, tokenPayload);
    return {
      ...nextState,
      lastIssuedApiToken: (
        state.lastIssuedApiToken && state.lastIssuedApiToken.token === effectiveTokenId
      ) ? null : state.lastIssuedApiToken
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceProjects({
  state,
  apiBaseUrl,
  bearerToken,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/projects`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const projects = payload.projects || [];
    return {
      ...state,
      liveProjects: projects,
      selectedProjectId: state.selectedProjectId || projects[0]?.project_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceProject({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/projects`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const projectPayload = await readJsonResponse(response);
    const nextProject = projectPayload.project || null;
    const existing = (state.liveProjects || []).filter((project) => project.project_id !== nextProject?.project_id);
    return {
      ...state,
      liveProjects: nextProject ? [nextProject, ...existing] : state.liveProjects,
      selectedProjectId: nextProject?.project_id || state.selectedProjectId,
      liveStudies: [],
      selectedStudyId: null,
      liveEvidenceViews: [],
      selectedEvidenceViewId: null,
      liveDecisionLogs: [],
      selectedDecisionLogId: null,
      liveDecisionComments: [],
      liveExportBundles: [],
      selectedExportBundleId: null,
      liveShareBundles: [],
      selectedShareBundleId: null,
      liveSupportSnapshots: [],
      selectedSupportSnapshotId: null,
      selectedJobId: null,
      liveSupportDiagnostics: null,
      liveEvidenceQuery: null,
      liveError: null,
      lastApiResponse: projectPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceProjectDetail({
  state,
  apiBaseUrl,
  bearerToken,
  projectId = "",
  fetchImpl = fetch
}) {
  const effectiveProjectId = projectId || state.selectedProjectId || "";
  if (!effectiveProjectId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/projects/${encodeURIComponent(effectiveProjectId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const project = payload.project || null;
    return {
      ...state,
      liveProjects: upsertById(state.liveProjects, project, "project_id"),
      selectedProjectId: project?.project_id || state.selectedProjectId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceStudies({
  state,
  apiBaseUrl,
  bearerToken,
  projectId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveProjectId = projectId || state.selectedProjectId || "";
    if (effectiveProjectId) {
      params.set("project_id", effectiveProjectId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/studies?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const studies = payload.studies || [];
    return {
      ...state,
      liveStudies: studies,
      selectedProjectId: effectiveProjectId || state.selectedProjectId,
      selectedStudyId: state.selectedStudyId || studies[0]?.study_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceStudy({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/studies`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const studyPayload = await readJsonResponse(response);
    const nextStudy = studyPayload.study || null;
    const existing = (state.liveStudies || []).filter((study) => study.study_id !== nextStudy?.study_id);
    return {
      ...state,
      selectedProjectId: nextStudy?.project_id || state.selectedProjectId,
      liveStudies: nextStudy ? [nextStudy, ...existing] : state.liveStudies,
      selectedStudyId: nextStudy?.study_id || state.selectedStudyId,
      liveStudyActivity: null,
      liveEvidenceViews: [],
      selectedEvidenceViewId: null,
      liveDecisionLogs: [],
      selectedDecisionLogId: null,
      liveDecisionComments: [],
      liveExportBundles: [],
      selectedExportBundleId: null,
      liveShareBundles: [],
      selectedShareBundleId: null,
      liveSupportSnapshots: [],
      selectedSupportSnapshotId: null,
      selectedJobId: null,
      liveSupportDiagnostics: null,
      liveEvidenceQuery: null,
      liveError: null,
      lastApiResponse: studyPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceStudyDetail({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  fetchImpl = fetch
}) {
  const effectiveStudyId = studyId || state.selectedStudyId || "";
  if (!effectiveStudyId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/studies/${encodeURIComponent(effectiveStudyId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const study = payload.study || null;
    return {
      ...state,
      selectedProjectId: study?.project_id || state.selectedProjectId,
      liveStudies: upsertById(state.liveStudies, study, "study_id"),
      selectedStudyId: study?.study_id || state.selectedStudyId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceStudyActivity({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  limit = 20,
  fetchImpl = fetch
}) {
  const effectiveStudyId = studyId || state.selectedStudyId || "";
  if (!effectiveStudyId) {
    return state;
  }
  try {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    const response = await fetchImpl(
      `${apiBaseUrl}/api/v1/studies/${encodeURIComponent(effectiveStudyId)}/activity?${params.toString()}`,
      {
        headers: buildHeaders(bearerToken)
      }
    );
    const payload = await readJsonResponse(response);
    return {
      ...state,
      selectedProjectId: payload?.study_activity?.project_id || state.selectedProjectId,
      selectedStudyId: payload?.study_activity?.study_id || state.selectedStudyId,
      liveStudyActivity: payload?.study_activity?.activity_events || [],
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceEvidenceViews({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  jobId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveStudyId = studyId || state.selectedStudyId || "";
    const effectiveJobId = jobId || state.selectedJobId || "";
    if (effectiveStudyId) {
      params.set("study_id", effectiveStudyId);
    }
    if (effectiveJobId) {
      params.set("job_id", effectiveJobId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/evidence-views?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const evidenceViews = payload.evidence_views || [];
    return {
      ...state,
      selectedStudyId: effectiveStudyId || state.selectedStudyId,
      selectedJobId: effectiveJobId || state.selectedJobId,
      liveEvidenceViews: evidenceViews,
      selectedEvidenceViewId: state.selectedEvidenceViewId || evidenceViews[0]?.evidence_view_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceEvidenceView({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/evidence-views`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const evidenceViewPayload = await readJsonResponse(response);
    const nextEvidenceView = evidenceViewPayload.evidence_view || null;
    const existing = (state.liveEvidenceViews || []).filter((item) => item.evidence_view_id !== nextEvidenceView?.evidence_view_id);
    return {
      ...state,
      selectedStudyId: nextEvidenceView?.study_id || state.selectedStudyId,
      selectedJobId: nextEvidenceView?.job_id || state.selectedJobId,
      liveEvidenceViews: nextEvidenceView ? [nextEvidenceView, ...existing] : state.liveEvidenceViews,
      selectedEvidenceViewId: nextEvidenceView?.evidence_view_id || state.selectedEvidenceViewId,
      liveError: null,
      lastApiResponse: evidenceViewPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceEvidenceViewDetail({
  state,
  apiBaseUrl,
  bearerToken,
  evidenceViewId = "",
  fetchImpl = fetch
}) {
  const effectiveEvidenceViewId = evidenceViewId || state.selectedEvidenceViewId || "";
  if (!effectiveEvidenceViewId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/evidence-views/${encodeURIComponent(effectiveEvidenceViewId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const evidenceView = payload.evidence_view || null;
    return {
      ...state,
      selectedProjectId: evidenceView?.project_id || state.selectedProjectId,
      selectedStudyId: evidenceView?.study_id || state.selectedStudyId,
      selectedJobId: evidenceView?.job_id || state.selectedJobId,
      liveEvidenceViews: upsertById(state.liveEvidenceViews, evidenceView, "evidence_view_id"),
      selectedEvidenceViewId: evidenceView?.evidence_view_id || state.selectedEvidenceViewId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceDecisionLogs({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  jobId = "",
  evidenceViewId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveStudyId = studyId || state.selectedStudyId || "";
    const effectiveJobId = jobId || state.selectedJobId || "";
    const effectiveEvidenceViewId = evidenceViewId || state.selectedEvidenceViewId || "";
    if (effectiveStudyId) {
      params.set("study_id", effectiveStudyId);
    }
    if (effectiveJobId) {
      params.set("job_id", effectiveJobId);
    }
    if (effectiveEvidenceViewId) {
      params.set("evidence_view_id", effectiveEvidenceViewId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const decisionLogs = payload.decision_logs || [];
    return {
      ...state,
      selectedStudyId: effectiveStudyId || state.selectedStudyId,
      selectedJobId: effectiveJobId || state.selectedJobId,
      selectedEvidenceViewId: effectiveEvidenceViewId || state.selectedEvidenceViewId,
      liveDecisionLogs: decisionLogs,
      selectedDecisionLogId: state.selectedDecisionLogId || decisionLogs[0]?.decision_log_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceDecisionLog({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const decisionLogPayload = await readJsonResponse(response);
    const nextDecisionLog = decisionLogPayload.decision_log || null;
    const existing = (state.liveDecisionLogs || []).filter((item) => item.decision_log_id !== nextDecisionLog?.decision_log_id);
    return {
      ...state,
      selectedStudyId: nextDecisionLog?.study_id || state.selectedStudyId,
      selectedJobId: nextDecisionLog?.job_id || state.selectedJobId,
      selectedEvidenceViewId: nextDecisionLog?.evidence_view_id || state.selectedEvidenceViewId,
      liveDecisionLogs: nextDecisionLog ? [nextDecisionLog, ...existing] : state.liveDecisionLogs,
      selectedDecisionLogId: nextDecisionLog?.decision_log_id || state.selectedDecisionLogId,
      liveDecisionComments: [],
      liveError: null,
      lastApiResponse: decisionLogPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceDecisionLogDetail({
  state,
  apiBaseUrl,
  bearerToken,
  decisionLogId = "",
  fetchImpl = fetch
}) {
  const effectiveDecisionLogId = decisionLogId || state.selectedDecisionLogId || "";
  if (!effectiveDecisionLogId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs/${encodeURIComponent(effectiveDecisionLogId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const decisionLog = payload.decision_log || null;
    const decisionComments = payload.decision_comments || [];
    return {
      ...state,
      selectedProjectId: decisionLog?.project_id || state.selectedProjectId,
      selectedStudyId: decisionLog?.study_id || state.selectedStudyId,
      selectedJobId: decisionLog?.job_id || state.selectedJobId,
      selectedEvidenceViewId: decisionLog?.evidence_view_id || state.selectedEvidenceViewId,
      liveDecisionLogs: upsertById(state.liveDecisionLogs, decisionLog, "decision_log_id"),
      selectedDecisionLogId: decisionLog?.decision_log_id || state.selectedDecisionLogId,
      liveDecisionComments: decisionComments,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceDecisionComments({
  state,
  apiBaseUrl,
  bearerToken,
  decisionLogId = "",
  fetchImpl = fetch
}) {
  const effectiveDecisionLogId = decisionLogId || state.selectedDecisionLogId || "";
  if (!effectiveDecisionLogId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs/${encodeURIComponent(effectiveDecisionLogId)}/comments`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const decisionLog = payload.decision_log || null;
    return {
      ...state,
      selectedProjectId: decisionLog?.project_id || state.selectedProjectId,
      selectedStudyId: decisionLog?.study_id || state.selectedStudyId,
      selectedJobId: decisionLog?.job_id || state.selectedJobId,
      selectedEvidenceViewId: decisionLog?.evidence_view_id || state.selectedEvidenceViewId,
      liveDecisionLogs: upsertById(state.liveDecisionLogs, decisionLog, "decision_log_id"),
      selectedDecisionLogId: decisionLog?.decision_log_id || state.selectedDecisionLogId,
      liveDecisionComments: payload.decision_comments || [],
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceDecisionComment({
  state,
  apiBaseUrl,
  bearerToken,
  decisionLogId = "",
  payload = {},
  fetchImpl = fetch
}) {
  const effectiveDecisionLogId = decisionLogId || state.selectedDecisionLogId || "";
  if (!effectiveDecisionLogId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs/${encodeURIComponent(effectiveDecisionLogId)}/comments`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const commentPayload = await readJsonResponse(response);
    const decisionLog = commentPayload.decision_log || null;
    const nextComment = commentPayload.decision_comment || null;
    const existing = (state.liveDecisionComments || []).filter(
      (item) => item.decision_comment_id !== nextComment?.decision_comment_id
    );
    return {
      ...state,
      selectedProjectId: decisionLog?.project_id || state.selectedProjectId,
      selectedStudyId: decisionLog?.study_id || state.selectedStudyId,
      selectedJobId: decisionLog?.job_id || state.selectedJobId,
      selectedEvidenceViewId: decisionLog?.evidence_view_id || state.selectedEvidenceViewId,
      liveDecisionLogs: upsertById(state.liveDecisionLogs, decisionLog, "decision_log_id"),
      selectedDecisionLogId: decisionLog?.decision_log_id || state.selectedDecisionLogId,
      liveDecisionComments: nextComment ? [...existing, nextComment] : state.liveDecisionComments,
      liveError: null,
      lastApiResponse: commentPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function updateWorkspaceDecisionReviewStatus({
  state,
  apiBaseUrl,
  bearerToken,
  decisionLogId = "",
  payload = {},
  fetchImpl = fetch
}) {
  const effectiveDecisionLogId = decisionLogId || state.selectedDecisionLogId || "";
  if (!effectiveDecisionLogId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/decision-logs/${encodeURIComponent(effectiveDecisionLogId)}/review-status`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const decisionLogPayload = await readJsonResponse(response);
    const decisionLog = decisionLogPayload.decision_log || null;
    return {
      ...state,
      selectedProjectId: decisionLog?.project_id || state.selectedProjectId,
      selectedStudyId: decisionLog?.study_id || state.selectedStudyId,
      selectedJobId: decisionLog?.job_id || state.selectedJobId,
      selectedEvidenceViewId: decisionLog?.evidence_view_id || state.selectedEvidenceViewId,
      liveDecisionLogs: upsertById(state.liveDecisionLogs, decisionLog, "decision_log_id"),
      selectedDecisionLogId: decisionLog?.decision_log_id || state.selectedDecisionLogId,
      liveError: null,
      lastApiResponse: decisionLogPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceExportBundles({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  jobId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveStudyId = studyId || state.selectedStudyId || "";
    const effectiveJobId = jobId || "";
    if (effectiveStudyId) {
      params.set("study_id", effectiveStudyId);
    }
    if (effectiveJobId) {
      params.set("job_id", effectiveJobId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/export-bundles?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const exportBundles = payload.export_bundles || [];
    return {
      ...state,
      selectedStudyId: effectiveStudyId || state.selectedStudyId,
      liveExportBundles: exportBundles,
      selectedExportBundleId: state.selectedExportBundleId || exportBundles[0]?.export_bundle_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceExportBundle({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/export-bundles`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const exportPayload = await readJsonResponse(response);
    const nextExportBundle = exportPayload.export_bundle || null;
    const existing = (state.liveExportBundles || []).filter((item) => item.export_bundle_id !== nextExportBundle?.export_bundle_id);
    return {
      ...state,
      selectedStudyId: nextExportBundle?.study_id || state.selectedStudyId,
      selectedJobId: nextExportBundle?.job_id || state.selectedJobId,
      liveExportBundles: nextExportBundle ? [nextExportBundle, ...existing] : state.liveExportBundles,
      selectedExportBundleId: nextExportBundle?.export_bundle_id || state.selectedExportBundleId,
      liveShareBundles: [],
      selectedShareBundleId: null,
      liveError: null,
      lastApiResponse: exportPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceExportBundleDetail({
  state,
  apiBaseUrl,
  bearerToken,
  exportBundleId = "",
  fetchImpl = fetch
}) {
  const effectiveExportBundleId = exportBundleId || state.selectedExportBundleId || "";
  if (!effectiveExportBundleId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/export-bundles/${encodeURIComponent(effectiveExportBundleId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const exportBundle = payload.export_bundle || null;
    return {
      ...state,
      selectedProjectId: exportBundle?.project_id || state.selectedProjectId,
      selectedStudyId: exportBundle?.study_id || state.selectedStudyId,
      selectedJobId: exportBundle?.job_id || state.selectedJobId,
      liveExportBundles: upsertById(state.liveExportBundles, exportBundle, "export_bundle_id"),
      selectedExportBundleId: exportBundle?.export_bundle_id || state.selectedExportBundleId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceShareBundles({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  exportBundleId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveStudyId = studyId || state.selectedStudyId || "";
    const effectiveExportBundleId = exportBundleId || state.selectedExportBundleId || "";
    if (effectiveStudyId) {
      params.set("study_id", effectiveStudyId);
    }
    if (effectiveExportBundleId) {
      params.set("export_bundle_id", effectiveExportBundleId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/share-bundles?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const shareBundles = payload.share_bundles || [];
    return {
      ...state,
      selectedStudyId: effectiveStudyId || state.selectedStudyId,
      selectedExportBundleId: effectiveExportBundleId || state.selectedExportBundleId,
      liveShareBundles: shareBundles,
      selectedShareBundleId: state.selectedShareBundleId || shareBundles[0]?.share_bundle_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceShareBundle({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/share-bundles`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const sharePayload = await readJsonResponse(response);
    const nextShareBundle = sharePayload.share_bundle || null;
    const existing = (state.liveShareBundles || []).filter((item) => item.share_bundle_id !== nextShareBundle?.share_bundle_id);
    return {
      ...state,
      selectedStudyId: nextShareBundle?.study_id || state.selectedStudyId,
      selectedExportBundleId: nextShareBundle?.export_bundle_id || state.selectedExportBundleId,
      liveShareBundles: nextShareBundle ? [nextShareBundle, ...existing] : state.liveShareBundles,
      selectedShareBundleId: nextShareBundle?.share_bundle_id || state.selectedShareBundleId,
      liveError: null,
      lastApiResponse: sharePayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceShareBundleDetail({
  state,
  apiBaseUrl,
  bearerToken,
  shareBundleId = "",
  fetchImpl = fetch
}) {
  const effectiveShareBundleId = shareBundleId || state.selectedShareBundleId || "";
  if (!effectiveShareBundleId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/share-bundles/${encodeURIComponent(effectiveShareBundleId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const shareBundle = payload.share_bundle || null;
    return {
      ...state,
      selectedProjectId: shareBundle?.project_id || state.selectedProjectId,
      selectedStudyId: shareBundle?.study_id || state.selectedStudyId,
      selectedJobId: shareBundle?.job_id || state.selectedJobId,
      selectedExportBundleId: shareBundle?.export_bundle_id || state.selectedExportBundleId,
      liveShareBundles: upsertById(state.liveShareBundles, shareBundle, "share_bundle_id"),
      selectedShareBundleId: shareBundle?.share_bundle_id || state.selectedShareBundleId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function revokeWorkspaceShareBundle({
  state,
  apiBaseUrl,
  bearerToken,
  shareBundleId = "",
  fetchImpl = fetch
}) {
  const effectiveShareBundleId = shareBundleId || state.selectedShareBundleId || "";
  if (!effectiveShareBundleId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/share-bundles/${encodeURIComponent(effectiveShareBundleId)}/revoke`, {
      method: "POST",
      headers: buildHeaders(bearerToken)
    });
    const sharePayload = await readJsonResponse(response);
    const updatedShareBundle = sharePayload.share_bundle || null;
    const nextShareBundles = (state.liveShareBundles || []).map((item) => (
      item.share_bundle_id === updatedShareBundle?.share_bundle_id ? updatedShareBundle : item
    ));
    return {
      ...state,
      liveShareBundles: nextShareBundles,
      selectedShareBundleId: updatedShareBundle?.share_bundle_id || state.selectedShareBundleId,
      liveError: null,
      lastApiResponse: sharePayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceSupportDiagnostics({
  state,
  apiBaseUrl,
  bearerToken,
  jobId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveJobId = jobId || state.selectedJobId || "";
    if (effectiveJobId) {
      params.set("job_id", effectiveJobId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/support-diagnostics?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return {
      ...state,
      selectedJobId: effectiveJobId || state.selectedJobId,
      liveSupportDiagnostics: payload.support || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceSupportSnapshots({
  state,
  apiBaseUrl,
  bearerToken,
  studyId = "",
  jobId = "",
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams();
    const effectiveStudyId = studyId || state.selectedStudyId || "";
    const effectiveJobId = jobId || state.selectedJobId || "";
    if (effectiveStudyId) {
      params.set("study_id", effectiveStudyId);
    }
    if (effectiveJobId) {
      params.set("job_id", effectiveJobId);
    }
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/support-snapshots?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const supportSnapshots = payload.support_snapshots || [];
    return {
      ...state,
      selectedStudyId: effectiveStudyId || state.selectedStudyId,
      selectedJobId: effectiveJobId || state.selectedJobId,
      liveSupportSnapshots: supportSnapshots,
      selectedSupportSnapshotId: state.selectedSupportSnapshotId || supportSnapshots[0]?.support_snapshot_id || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function createWorkspaceSupportSnapshot({
  state,
  apiBaseUrl,
  bearerToken,
  payload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/support-snapshots`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const supportPayload = await readJsonResponse(response);
    const nextSupportSnapshot = supportPayload.support_snapshot || null;
    const existing = (state.liveSupportSnapshots || []).filter((item) => item.support_snapshot_id !== nextSupportSnapshot?.support_snapshot_id);
    return {
      ...state,
      selectedStudyId: nextSupportSnapshot?.study_id || state.selectedStudyId,
      selectedJobId: nextSupportSnapshot?.job_id || state.selectedJobId,
      liveSupportSnapshots: nextSupportSnapshot ? [nextSupportSnapshot, ...existing] : state.liveSupportSnapshots,
      selectedSupportSnapshotId: nextSupportSnapshot?.support_snapshot_id || state.selectedSupportSnapshotId,
      liveError: null,
      lastApiResponse: supportPayload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceSupportSnapshotDetail({
  state,
  apiBaseUrl,
  bearerToken,
  supportSnapshotId = "",
  fetchImpl = fetch
}) {
  const effectiveSupportSnapshotId = supportSnapshotId || state.selectedSupportSnapshotId || "";
  if (!effectiveSupportSnapshotId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/support-snapshots/${encodeURIComponent(effectiveSupportSnapshotId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const supportSnapshot = payload.support_snapshot || null;
    return {
      ...state,
      selectedProjectId: supportSnapshot?.project_id || state.selectedProjectId,
      selectedStudyId: supportSnapshot?.study_id || state.selectedStudyId,
      selectedJobId: supportSnapshot?.job_id || state.selectedJobId,
      liveSupportSnapshots: upsertById(state.liveSupportSnapshots, supportSnapshot, "support_snapshot_id"),
      selectedSupportSnapshotId: supportSnapshot?.support_snapshot_id || state.selectedSupportSnapshotId,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceRuntimeSession({
  state,
  apiBaseUrl,
  bearerToken,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/session`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return {
      ...state,
      liveSession: payload.session || null,
      liveWorkspaceSettings: state.liveWorkspaceSettings || null,
      sessionError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveSession: null,
      sessionError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceShellSnapshot({
  state,
  apiBaseUrl,
  bearerToken,
  queryText = "",
  activeFamily = "all",
  sortBy = "relevance",
  selectedResultId = "",
  selectedReplayStepId = "",
  selectedComparisonRunId = "",
  fetchImpl = fetch
}) {
  try {
    const params = buildWorkspaceShellParams({
      state,
      queryText,
      activeFamily,
      sortBy,
      selectedResultId,
      selectedReplayStepId,
      selectedComparisonRunId
    });
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/workspace-shell?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return applyWorkspaceShellSnapshot(state, payload);
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      sessionError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function submitWorkspaceValidationJob({
  state,
  apiBaseUrl,
  bearerToken,
  requestPayload,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/validation-jobs`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify(requestPayload)
    });
    const payload = await readJsonResponse(response);
    const nextJob = payload.job || null;
    const existing = (state.liveJobs || []).filter((job) => job.job_id !== nextJob?.job_id);
    return {
      ...state,
      mode: nextJob ? "live" : state.mode,
      selectedJobId: nextJob?.job_id || state.selectedJobId,
      liveJobs: nextJob ? [nextJob, ...existing] : state.liveJobs,
      liveEvidenceQuery: null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function cancelWorkspaceValidationJob({
  state,
  apiBaseUrl,
  bearerToken,
  jobId = "",
  reason = "",
  fetchImpl = fetch
}) {
  const effectiveJobId = jobId || state.selectedJobId || "";
  if (!effectiveJobId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/validation-jobs/${encodeURIComponent(effectiveJobId)}/cancel`, {
      method: "POST",
      headers: buildHeaders(bearerToken, { "Content-Type": "application/json" }),
      body: JSON.stringify({ reason })
    });
    const payload = await readJsonResponse(response);
    const nextJob = payload.job || null;
    const liveJobs = (state.liveJobs || []).map((job) => (
      job.job_id === nextJob?.job_id ? nextJob : job
    ));
    return {
      ...state,
      mode: "live",
      liveJobs,
      selectedJobId: nextJob?.job_id || state.selectedJobId,
      liveEvidenceQuery: null,
      liveSupportDiagnostics: null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function retryWorkspaceValidationJob({
  state,
  apiBaseUrl,
  bearerToken,
  jobId = "",
  fetchImpl = fetch
}) {
  const effectiveJobId = jobId || state.selectedJobId || "";
  if (!effectiveJobId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/validation-jobs/${encodeURIComponent(effectiveJobId)}/retry`, {
      method: "POST",
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const nextJob = payload.job || null;
    const nextMetadata = nextJob?.metadata || {};
    const existing = (state.liveJobs || []).filter((job) => job.job_id !== nextJob?.job_id);
    return {
      ...state,
      mode: nextJob ? "live" : state.mode,
      selectedProjectId: nextMetadata.project_id || state.selectedProjectId,
      selectedStudyId: nextMetadata.study_id || state.selectedStudyId,
      selectedJobId: nextJob?.job_id || state.selectedJobId,
      liveJobs: nextJob ? [nextJob, ...existing] : state.liveJobs,
      liveEvidenceQuery: null,
      liveSupportDiagnostics: null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function listWorkspaceValidationJobs({
  state,
  apiBaseUrl,
  bearerToken,
  fetchImpl = fetch
}) {
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/validation-jobs`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const jobs = payload.jobs || [];
    return {
      ...state,
      mode: "live",
      liveJobs: jobs,
      selectedJobId: state.selectedJobId || jobs[0]?.job_id || null,
      liveEvidenceQuery: null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceValidationJobDetail({
  state,
  apiBaseUrl,
  bearerToken,
  fetchImpl = fetch
}) {
  if (!state.selectedJobId) {
    return state;
  }
  try {
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/validation-jobs/${encodeURIComponent(state.selectedJobId)}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    const nextJob = payload.job || null;
    const remaining = (state.liveJobs || []).filter((job) => job.job_id !== nextJob?.job_id);
    return {
      ...state,
      mode: nextJob ? "live" : state.mode,
      liveJobs: nextJob ? [nextJob, ...remaining] : state.liveJobs,
      liveEvidenceQuery: null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}

export async function loadWorkspaceEvidenceQuery({
  state,
  apiBaseUrl,
  bearerToken,
  queryText = "",
  activeFamily = "all",
  sortBy = "relevance",
  selectedResultId = "",
  selectedReplayStepId = "",
  selectedComparisonRunId = "",
  fetchImpl = fetch
}) {
  const jobId = state.selectedJobId;
  if (!jobId) {
    return state;
  }
  try {
    const params = buildEvidenceQueryParams({
      state,
      queryText,
      activeFamily,
      sortBy,
      selectedResultId,
      selectedReplayStepId,
      selectedComparisonRunId
    });
    const response = await fetchImpl(`${apiBaseUrl}/api/v1/evidence-query?${params.toString()}`, {
      headers: buildHeaders(bearerToken)
    });
    const payload = await readJsonResponse(response);
    return {
      ...state,
      liveEvidenceQuery: payload.query || null,
      liveError: null,
      lastApiResponse: payload
    };
  } catch (error) {
    return {
      ...state,
      liveEvidenceQuery: null,
      liveError: error.message,
      lastApiResponse: { error: error.message }
    };
  }
}
