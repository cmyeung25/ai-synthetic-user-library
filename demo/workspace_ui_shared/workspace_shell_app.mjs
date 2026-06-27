import {
  createStage11WorkspaceShellDemoState,
  deriveStage11WorkspaceShellBundle
} from "./workspace_ui_adapter.mjs";
import {
  buildValidationJobRequestFromDraftPlan,
  createWorkspaceValidationBridgeDemoContext,
  createWorkspaceValidationBridgeDemoJob,
  deriveWorkspaceValidationBridgeState
} from "./workspace_runtime_bridge.mjs";
import {
  deriveWorkspaceSessionRuntimeBridgeState
} from "./workspace_session_runtime_bridge.mjs";
import {
  listWorkspaceValidationJobs,
  loadWorkspaceEvidenceQuery,
  loadWorkspaceRuntimeSession,
  loadWorkspaceValidationJobDetail,
  selectWorkspaceRuntimeJob,
  submitWorkspaceValidationJob,
  switchWorkspaceRuntimeToSample
} from "./workspace_shell_runtime_client.mjs";
import {
  createWorkspaceShellRuntimeSyncState,
  deriveWorkspaceShellRuntimeSyncView,
  syncWorkspaceShellRuntime
} from "./workspace_shell_runtime_sync.mjs";
import {
  deriveWorkspaceShellFrontendAdapter
} from "./workspace_shell_frontend_adapter.mjs";

export const DEFAULT_WORKSPACE_SHELL_COPY = {
  firstTaskValue: "connect data",
  questionValue: "Where do new operators hesitate during onboarding, and do they continue after the first task?",
  desiredValue: "task-friction and continuation risk",
  nextUpload: "request inputs",
  nextFallback: "confirm fallback",
  nextConfirm: "confirm queueable plan",
  nextSaved: "resume later",
  phaseQueued: "queued",
  monitorAwait: "await worker progress",
  monitorViewResults: "view results",
  monitorInspectFailure: "inspect failure"
};

function lifecycleFromJobStatus(status) {
  if (status === "queued") return "queued";
  if (status === "running") return "running";
  if (status === "completed") return "completed";
  if (status === "failed" || status === "canceled") return "failed";
  return "ready_to_queue";
}

function buildDraftScenarios(copy = DEFAULT_WORKSPACE_SHELL_COPY) {
  return {
    blocked_draft() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        lifecycle: "ready_to_queue"
      };
    },
    ready_for_confirmation() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        firstTask: copy.firstTaskValue,
        lifecycle: "ready_to_queue"
      };
    },
    confirmed_draft() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        firstTask: copy.firstTaskValue,
        lifecycle: "queued",
        attemptCount: 0
      };
    },
    completed_local_shell() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        firstTask: copy.firstTaskValue,
        lifecycle: "completed",
        attemptCount: 1
      };
    },
    failed_local_shell() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        firstTask: copy.firstTaskValue,
        lifecycle: "failed",
        attemptCount: 1,
        failureReason: "stimulus render timeout before trace packaging"
      };
    }
  };
}

function withWorkspaceContext(state, {
  apiBaseUrl = "",
  briefPath = "",
  personaDir = ""
} = {}) {
  return {
    ...state,
    workspaceContext: {
      ...state.workspaceContext,
      api_base_url: apiBaseUrl,
      brief_path: briefPath,
      persona_dir: personaDir
    }
  };
}

function getSelectedJob(state) {
  const jobs = state.mode === "live" ? state.liveJobs : state.sampleJobs;
  return jobs.find((job) => job.job_id === state.selectedJobId) || null;
}

function buildBundle({
  state,
  copy = DEFAULT_WORKSPACE_SHELL_COPY,
  queryState = {}
}) {
  const job = getSelectedJob(state);
  const shellState = {
    ...state.shellState,
    queryText: queryState.queryText || "",
    activeFamily: queryState.activeFamily || "all",
    sortBy: queryState.sortBy || "relevance"
  };

  if (job) {
    shellState.lifecycle = lifecycleFromJobStatus(job.status);
    shellState.attemptCount = job.retry_count || 0;
    shellState.failureReason = job.last_error || null;
  }

  return deriveStage11WorkspaceShellBundle({
    shellState,
    copy,
    localUiState: {
      locale: "en",
      active_panel: "runtime_bridge"
    }
  });
}

export function createWorkspaceShellAppState() {
  return {
    shellState: createStage11WorkspaceShellDemoState(),
    workspaceContext: createWorkspaceValidationBridgeDemoContext(),
    sampleJobs: [
      createWorkspaceValidationBridgeDemoJob("queued"),
      createWorkspaceValidationBridgeDemoJob("completed"),
      createWorkspaceValidationBridgeDemoJob("failed")
    ],
    liveJobs: [],
    liveSession: null,
    selectedJobId: null,
    liveEvidenceQuery: null,
    mode: "sample",
    lastApiResponse: null,
    liveError: null,
    sessionError: null,
    runtimeSync: createWorkspaceShellRuntimeSyncState()
  };
}

export function deriveWorkspaceShellAppModel({
  state,
  apiBaseUrl = "",
  bearerToken = "",
  briefPath = "",
  personaDir = "",
  queryState = {},
  copy = DEFAULT_WORKSPACE_SHELL_COPY
}) {
  const contextualState = withWorkspaceContext(state, {
    apiBaseUrl,
    briefPath,
    personaDir
  });
  const bundle = buildBundle({
    state: contextualState,
    copy,
    queryState
  });
  const jobs = contextualState.mode === "live" && contextualState.liveJobs.length
    ? contextualState.liveJobs
    : contextualState.sampleJobs;
  const selectedJob = getSelectedJob(contextualState);
  const sessionBridgeState = deriveWorkspaceSessionRuntimeBridgeState({
    sessionPayload: contextualState.liveSession,
    apiBaseUrl,
    bearerToken,
    lastError: contextualState.liveSession ? null : contextualState.sessionError
  });
  const bridgeState = deriveWorkspaceValidationBridgeState({
    draftPlan: bundle.draft,
    workspaceContext: contextualState.workspaceContext,
    jobList: jobs,
    selectedJob,
    apiBaseUrl,
    lastError: contextualState.liveError
  });
  const reviewQueryState = contextualState.mode === "live" && contextualState.liveEvidenceQuery
    ? contextualState.liveEvidenceQuery
    : bundle.evidence_query;
  const querySource = contextualState.mode === "live" && contextualState.liveEvidenceQuery
    ? "backend"
    : "local";
  const frontendState = deriveWorkspaceShellFrontendAdapter({
    bundle,
    bridgeState,
    selectedJob,
    mode: contextualState.mode,
    lastApiResponse: contextualState.lastApiResponse,
    reviewQueryState,
    querySource
  });

  return {
    state: contextualState,
    bundle,
    jobs,
    selectedJob,
    sessionBridgeState,
    bridgeState,
    reviewQueryState,
    querySource,
    runtimeSyncView: deriveWorkspaceShellRuntimeSyncView(contextualState.runtimeSync),
    frontendState
  };
}

export function createWorkspaceShellAppController({
  fetchImpl = fetch,
  now = () => new Date(),
  copy = DEFAULT_WORKSPACE_SHELL_COPY,
  initialState = createWorkspaceShellAppState()
} = {}) {
  let state = initialState;

  function setState(nextState) {
    state = nextState;
    return state;
  }

  return {
    getState() {
      return state;
    },

    reset() {
      return setState(createWorkspaceShellAppState());
    },

    deriveModel(input = {}) {
      return deriveWorkspaceShellAppModel({
        state,
        copy,
        ...input
      });
    },

    applyDraftScenario(scenarioId) {
      const scenarios = buildDraftScenarios(copy);
      const applyScenario = scenarios[scenarioId];
      if (!applyScenario) {
        return state;
      }
      const nextState = switchWorkspaceRuntimeToSample({
        ...state,
        shellState: applyScenario()
      }, {});
      nextState.selectedJobId = null;
      return setState(nextState);
    },

    useSampleJobs() {
      const nextState = switchWorkspaceRuntimeToSample(state, {});
      if (!nextState.selectedJobId) {
        nextState.selectedJobId = "job_api_demo_completed";
      }
      return setState(nextState);
    },

    selectJob(jobId) {
      return setState(selectWorkspaceRuntimeJob(state, jobId));
    },

    selectLocalEvidenceResult(resultId) {
      return setState({
        ...state,
        shellState: {
          ...state.shellState,
          selectedResultId: resultId,
          selectedReplayStepId: null
        }
      });
    },

    selectLocalReplayStep(stepId) {
      return setState({
        ...state,
        shellState: {
          ...state.shellState,
          selectedReplayStepId: stepId
        }
      });
    },

    clearLocalEvidenceQuery() {
      return setState({
        ...state,
        liveEvidenceQuery: null,
        shellState: {
          ...state.shellState,
          selectedResultId: null,
          selectedReplayStepId: null
        }
      });
    },

    toggleRuntimeAutoRefresh() {
      return setState({
        ...state,
        runtimeSync: {
          ...(state.runtimeSync || createWorkspaceShellRuntimeSyncState()),
          auto_refresh_enabled: !state.runtimeSync?.auto_refresh_enabled
        }
      });
    },

    async submitLiveJob({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      queryState = {}
    } = {}) {
      const model = deriveWorkspaceShellAppModel({
        state,
        apiBaseUrl,
        bearerToken,
        briefPath,
        personaDir,
        queryState,
        copy
      });
      const requestPayload = buildValidationJobRequestFromDraftPlan({
        draftPlan: model.bundle.draft,
        workspaceContext: model.state.workspaceContext
      });
      return setState(await submitWorkspaceValidationJob({
        state: model.state,
        apiBaseUrl,
        bearerToken,
        requestPayload,
        fetchImpl
      }));
    },

    async loadWorkspaceSession({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = ""
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir
      });
      return setState(await loadWorkspaceRuntimeSession({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async listLiveJobs({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = ""
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir
      });
      return setState(await listWorkspaceValidationJobs({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async loadSelectedLiveJob({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = ""
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir
      });
      return setState(await loadWorkspaceValidationJobDetail({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async loadLiveEvidenceQuery({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      queryState = {},
      selectedResultId = "",
      selectedReplayStepId = ""
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir
      });
      return setState(await loadWorkspaceEvidenceQuery({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        queryText: queryState.queryText || "",
        activeFamily: queryState.activeFamily || "all",
        sortBy: queryState.sortBy || "relevance",
        selectedResultId,
        selectedReplayStepId,
        fetchImpl
      }));
    },

    async syncRuntime({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      queryState = {},
      selectedResultId,
      selectedReplayStepId
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir
      });
      return setState(await syncWorkspaceShellRuntime({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        queryState,
        selectedResultId,
        selectedReplayStepId,
        fetchImpl,
        now
      }));
    }
  };
}
