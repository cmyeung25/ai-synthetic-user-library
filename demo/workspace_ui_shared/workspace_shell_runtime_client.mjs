function buildHeaders(bearerToken, extra = {}) {
  return {
    ...extra,
    Authorization: `Bearer ${String(bearerToken || "").trim()}`
  };
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

function applyWorkspaceShellSnapshot(state, payload) {
  const snapshot = payload?.snapshot || null;
  if (!snapshot) {
    return state;
  }
  const jobs = snapshot.jobs || [];
  return {
    ...state,
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

function buildEvidenceQueryParams({
  state,
  queryText = "",
  activeFamily = "all",
  sortBy = "relevance",
  selectedResultId = "",
  selectedReplayStepId = ""
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
  return params;
}

export function selectWorkspaceRuntimeJob(state, jobId) {
  return {
    ...state,
    selectedJobId: jobId,
    liveEvidenceQuery: null
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
    lastApiResponse: { mode: "sample" }
  };
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
  fetchImpl = fetch
}) {
  try {
    const params = new URLSearchParams({
      query_text: queryText,
      active_family: activeFamily,
      sort_by: sortBy
    });
    if (state.selectedJobId) {
      params.set("job_id", state.selectedJobId);
    }
    if (selectedResultId) {
      params.set("selected_result_id", selectedResultId);
    }
    if (selectedReplayStepId) {
      params.set("selected_replay_step_id", selectedReplayStepId);
    }
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
      selectedReplayStepId
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
