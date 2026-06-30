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
  createWorkspaceExportBundle,
  createWorkspaceDecisionLog,
  createWorkspaceDecisionComment,
  createWorkspaceProject,
  createWorkspaceShareBundle,
  createWorkspaceSupportSnapshot,
  createWorkspaceStudy,
  createWorkspaceEvidenceView,
  cancelWorkspaceValidationJob,
  issueWorkspaceApiToken,
  loadWorkspaceAuditEvents,
  loadWorkspaceDecisionLogDetail,
  loadWorkspaceDecisionComments,
  loadWorkspaceDecisionLogs,
  loadWorkspaceEvidenceViewDetail,
  loadWorkspaceEvidenceViews,
  loadWorkspaceExportBundles,
  loadWorkspaceExportBundleDetail,
  loadWorkspaceProjects,
  loadWorkspaceProjectDetail,
  loadWorkspaceShareBundles,
  loadWorkspaceShareBundleDetail,
  loadWorkspaceSettings,
  loadWorkspaceSupportDiagnostics,
  loadWorkspaceSupportSnapshots,
  loadWorkspaceSupportSnapshotDetail,
  loadWorkspaceStudyActivity,
  loadWorkspaceStudies,
  loadWorkspaceStudyDetail,
  listWorkspaceValidationJobs,
  loadWorkspaceEvidenceQuery,
  loadWorkspaceRuntimeSession,
  loadWorkspaceValidationJobDetail,
  revokeWorkspaceShareBundle,
  revokeWorkspaceApiToken,
  retryWorkspaceValidationJob,
  selectWorkspaceRuntimeExportBundle,
  selectWorkspaceRuntimeDecisionLog,
  selectWorkspaceRuntimeEvidenceView,
  selectWorkspaceRuntimeProject,
  selectWorkspaceRuntimeShareBundle,
  selectWorkspaceRuntimeSupportSnapshot,
  selectWorkspaceRuntimeStudy,
  selectWorkspaceRuntimeJob,
  submitWorkspaceValidationJob,
  switchWorkspaceRuntimeToSample,
  updateWorkspaceDecisionReviewStatus,
  updateWorkspaceBilling,
  upsertWorkspaceMember
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
        attachedArtifacts: ["onboarding-screen-01.png", "onboarding-screen-02.png"],
        firstTask: copy.firstTaskValue,
        lifecycle: "ready_to_queue"
      };
    },
    confirmed_draft() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        attachedArtifacts: ["onboarding-screen-01.png", "onboarding-screen-02.png"],
        firstTask: copy.firstTaskValue,
        lifecycle: "queued",
        attemptCount: 0
      };
    },
    completed_local_shell() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        attachedArtifacts: ["onboarding-screen-01.png", "onboarding-screen-02.png"],
        firstTask: copy.firstTaskValue,
        lifecycle: "completed",
        attemptCount: 1
      };
    },
    failed_local_shell() {
      return {
        ...createStage11WorkspaceShellDemoState(),
        hasScreenshots: true,
        attachedArtifacts: ["onboarding-screen-01.png", "onboarding-screen-02.png"],
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
  personaDir = "",
  panelType = "",
  sampleSize = "",
  providerName = "",
  runRoot = "",
  modeOverride = "",
  personaFilters = {}
} = {}) {
  return {
    ...state,
    workspaceContext: {
      ...state.workspaceContext,
      api_base_url: apiBaseUrl,
      brief_path: briefPath,
      persona_dir: personaDir,
      panel_type: panelType || state.workspaceContext?.panel_type || "mainstream",
      sample_size: sampleSize || state.workspaceContext?.sample_size || 5,
      provider_name: providerName || state.workspaceContext?.provider_name || "mock",
      run_root: runRoot || state.workspaceContext?.run_root || "runs",
      mode_override: modeOverride || null,
      persona_filters: personaFilters || {}
    }
  };
}

function nextEventStamp(events = []) {
  const nextIndex = events.length + 1;
  return `23:${String(10 + nextIndex).padStart(2, "0")}`;
}

function appendShellEvent(shellState, type) {
  const events = Array.isArray(shellState?.events) ? shellState.events : [];
  return {
    ...shellState,
    events: [{ type, at: nextEventStamp(events) }, ...events].slice(0, 8)
  };
}

function compactDigits(value) {
  return String(value || "")
    .replace(/[^0-9]/g, "")
    .slice(0, 14) || "00000000000000";
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
  const effectiveCopy = {
    ...copy,
    questionValue: state.shellState?.researchIntent || copy.questionValue,
    desiredValue: state.shellState?.desiredOutcome || copy.desiredValue,
    firstTaskValue: state.shellState?.firstTask || copy.firstTaskValue
  };
  const shellState = {
    ...state.shellState,
    panelType: state.workspaceContext?.panel_type ?? state.shellState?.panelType,
    sampleSize: state.workspaceContext?.sample_size ?? state.shellState?.sampleSize,
    providerName: state.workspaceContext?.provider_name ?? state.shellState?.providerName,
    modeOverride: state.workspaceContext?.mode_override ?? state.shellState?.modeOverride,
    personaFilters: state.workspaceContext?.persona_filters ?? state.shellState?.personaFilters,
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
    copy: effectiveCopy,
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
    liveProjects: [],
    selectedProjectId: null,
    liveStudies: [],
    selectedStudyId: null,
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
    liveWorkspaceSettings: null,
    liveAuditEvents: [],
    liveAuditQuery: null,
    lastIssuedApiToken: null,
    liveJobs: [],
    liveSession: null,
    selectedJobId: null,
    liveProviderRuntime: null,
    liveEvidenceQuery: null,
    liveSupportDiagnostics: null,
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
  panelType = "",
  sampleSize = "",
  providerName = "",
  runRoot = "",
  modeOverride = "",
  personaFilters = {},
  queryState = {},
  copy = DEFAULT_WORKSPACE_SHELL_COPY
}) {
  const contextualState = withWorkspaceContext(state, {
    apiBaseUrl,
    briefPath,
    personaDir,
    panelType,
    sampleSize,
    providerName,
    runRoot,
    modeOverride,
    personaFilters
  });
  contextualState.workspaceContext = {
    ...contextualState.workspaceContext,
    project_id: contextualState.selectedProjectId || null,
    study_id: contextualState.selectedStudyId || null
  };
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
    selectedProject: contextualState.liveProjects.find((project) => project.project_id === contextualState.selectedProjectId) || null,
    selectedStudy: contextualState.liveStudies.find((study) => study.study_id === contextualState.selectedStudyId) || null,
    selectedEvidenceView: contextualState.liveEvidenceViews.find((view) => view.evidence_view_id === contextualState.selectedEvidenceViewId) || null,
    selectedDecisionLog: contextualState.liveDecisionLogs.find((log) => log.decision_log_id === contextualState.selectedDecisionLogId) || null,
    selectedExportBundle: contextualState.liveExportBundles.find((bundle) => bundle.export_bundle_id === contextualState.selectedExportBundleId) || null,
    selectedShareBundle: contextualState.liveShareBundles.find((bundle) => bundle.share_bundle_id === contextualState.selectedShareBundleId) || null,
    selectedSupportSnapshot: contextualState.liveSupportSnapshots.find((snapshot) => snapshot.support_snapshot_id === contextualState.selectedSupportSnapshotId) || null,
    studyActivity: contextualState.liveStudyActivity,
    projects: contextualState.liveProjects,
    studies: contextualState.liveStudies,
    evidenceViews: contextualState.liveEvidenceViews,
    decisionLogs: contextualState.liveDecisionLogs,
    decisionComments: contextualState.liveDecisionComments,
    exportBundles: contextualState.liveExportBundles,
    shareBundles: contextualState.liveShareBundles,
    supportSnapshots: contextualState.liveSupportSnapshots,
    supportDiagnostics: contextualState.liveSupportDiagnostics,
    providerRuntime: contextualState.liveProviderRuntime,
    workspaceSettings: contextualState.liveWorkspaceSettings,
    auditEvents: contextualState.liveAuditEvents,
    auditQuery: contextualState.liveAuditQuery,
    lastIssuedApiToken: contextualState.lastIssuedApiToken,
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
  let draftIdentityCounter = 0;

  function nextDraftIdentity() {
    draftIdentityCounter += 1;
    const stamp = compactDigits(now().toISOString());
    const suffix = String(draftIdentityCounter).padStart(2, "0");
    return {
      draftPlanId: `draft_plan_${stamp}_${suffix}`,
      submissionKey: null,
      confirmedAt: null
    };
  }

  function withDraftIdentity(shellState) {
    return {
      ...shellState,
      ...(shellState?.draftPlanId ? {} : nextDraftIdentity())
    };
  }

  let state = {
    ...initialState,
    shellState: withDraftIdentity(initialState.shellState)
  };

  function setState(nextState) {
    state = nextState;
    return state;
  }

  return {
    getState() {
      return state;
    },

    reset() {
      return setState({
        ...createWorkspaceShellAppState(),
        shellState: withDraftIdentity(createStage11WorkspaceShellDemoState())
      });
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
      const nextShellState = {
        ...applyScenario(),
        ...nextDraftIdentity(),
        researchIntent: state.shellState?.researchIntent || copy.questionValue,
        desiredOutcome: state.shellState?.desiredOutcome || copy.desiredValue
      };
      const nextState = switchWorkspaceRuntimeToSample({
        ...state,
        shellState: nextShellState
      }, {});
      nextState.selectedJobId = null;
      return setState(nextState);
    },

    updateDraftInput({
      researchIntent,
      desiredOutcome,
      firstTask
    } = {}) {
      const nextShellState = {
        ...state.shellState
      };
      if (researchIntent !== undefined) {
        nextShellState.researchIntent = String(researchIntent || "").trim();
      }
      if (desiredOutcome !== undefined) {
        nextShellState.desiredOutcome = String(desiredOutcome || "").trim();
      }
      if (firstTask !== undefined) {
        const normalizedTask = String(firstTask || "").trim();
        nextShellState.firstTask = normalizedTask || null;
      }
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    togglePrototypeArtifacts() {
      let nextShellState = {
        ...state.shellState,
        hasScreenshots: !state.shellState?.hasScreenshots,
        attachedArtifacts: state.shellState?.hasScreenshots
          ? []
          : ["sample-onboarding-01.png", "sample-onboarding-02.png"]
      };
      if (!nextShellState.hasScreenshots && state.shellState?.lifecycle === "ready_to_queue" && !state.shellState?.fallbackChosen) {
        nextShellState.selectedArtifactId = null;
      }
      nextShellState = appendShellEvent(nextShellState, "artifact_toggle");
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    setPrototypeArtifacts(artifactNames = []) {
      const attachedArtifacts = (artifactNames || [])
        .map((value) => String(value || "").trim())
        .filter((value) => value.length > 0);
      const nextShellState = appendShellEvent({
        ...state.shellState,
        hasScreenshots: attachedArtifacts.length > 0,
        attachedArtifacts
      }, "artifact_upload");
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    toggleFallbackMode() {
      if (state.shellState?.lifecycle !== "ready_to_queue") {
        return state;
      }
      const nextShellState = appendShellEvent({
        ...state.shellState,
        fallbackChosen: !state.shellState?.fallbackChosen,
        savedBlocked: false
      }, "fallback_toggle");
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    toggleSavedDraft() {
      if (state.shellState?.lifecycle !== "ready_to_queue") {
        return state;
      }
      const nextShellState = appendShellEvent({
        ...state.shellState,
        savedBlocked: !state.shellState?.savedBlocked
      }, "save_toggle");
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    confirmDraftPlan(input = {}) {
      const model = deriveWorkspaceShellAppModel({
        state,
        copy,
        ...input
      });
      if (model.bundle?.adapter?.ui_phase !== "ready_for_confirmation") {
        return state;
      }
      const nextShellState = appendShellEvent({
        ...state.shellState,
        lifecycle: "queued",
        savedBlocked: false,
        failureReason: null,
        attemptCount: Math.max(state.shellState?.attemptCount || 0, 1),
        submissionKey: state.shellState?.submissionKey || `submit_${compactDigits(now().toISOString())}_${String(draftIdentityCounter + 1).padStart(2, "0")}`,
        confirmedAt: now().toISOString()
      }, "confirmed");
      return setState({
        ...state,
        shellState: nextShellState
      });
    },

    resetDraftFlow() {
      return setState({
        ...createWorkspaceShellAppState(),
        shellState: withDraftIdentity(createStage11WorkspaceShellDemoState())
      });
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

    selectProject(projectId) {
      return setState(selectWorkspaceRuntimeProject(state, projectId));
    },

    selectStudy(studyId) {
      return setState(selectWorkspaceRuntimeStudy(state, studyId));
    },

    selectEvidenceView(evidenceViewId) {
      return setState(selectWorkspaceRuntimeEvidenceView(state, evidenceViewId));
    },

    selectDecisionLog(decisionLogId) {
      return setState(selectWorkspaceRuntimeDecisionLog(state, decisionLogId));
    },

    selectExportBundle(exportBundleId) {
      return setState(selectWorkspaceRuntimeExportBundle(state, exportBundleId));
    },

    selectShareBundle(shareBundleId) {
      return setState(selectWorkspaceRuntimeShareBundle(state, shareBundleId));
    },

    selectSupportSnapshot(supportSnapshotId) {
      return setState(selectWorkspaceRuntimeSupportSnapshot(state, supportSnapshotId));
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
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {},
      queryState = {}
    } = {}) {
      const model = deriveWorkspaceShellAppModel({
        state,
        apiBaseUrl,
        bearerToken,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters,
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

    async cancelSelectedJob({
      apiBaseUrl = "",
      bearerToken = "",
      reason = "",
      briefPath = "",
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {}
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
      });
      setState(await cancelWorkspaceValidationJob({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        reason,
        fetchImpl
      }));
      return setState(await loadWorkspaceRuntimeSession({
        state,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async retrySelectedJob({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {}
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
      });
      setState(await retryWorkspaceValidationJob({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
      return setState(await loadWorkspaceRuntimeSession({
        state,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async loadWorkspaceSession({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {}
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
      });
      return setState(await loadWorkspaceRuntimeSession({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async loadWorkspaceSettings({
      apiBaseUrl = "",
      bearerToken = ""
    } = {}) {
      return setState(await loadWorkspaceSettings({
        state,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async loadWorkspaceAuditEvents({
      apiBaseUrl = "",
      bearerToken = "",
      targetType = "",
      actionPrefix = "",
      limit = 20
    } = {}) {
      return setState(await loadWorkspaceAuditEvents({
        state,
        apiBaseUrl,
        bearerToken,
        targetType,
        actionPrefix,
        limit,
        fetchImpl
      }));
    },

    async upsertWorkspaceMember({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await upsertWorkspaceMember({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async updateWorkspaceBilling({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await updateWorkspaceBilling({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async issueWorkspaceApiToken({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await issueWorkspaceApiToken({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async revokeWorkspaceApiToken({
      apiBaseUrl = "",
      bearerToken = "",
      tokenId = ""
    } = {}) {
      return setState(await revokeWorkspaceApiToken({
        state,
        apiBaseUrl,
        bearerToken,
        tokenId,
        fetchImpl
      }));
    },

    async loadProjects({
      apiBaseUrl = "",
      bearerToken = ""
    } = {}) {
      return setState(await loadWorkspaceProjects({
        state,
        apiBaseUrl,
        bearerToken,
        fetchImpl
      }));
    },

    async createProject({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceProject({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadProjectDetail({
      apiBaseUrl = "",
      bearerToken = "",
      projectId = ""
    } = {}) {
      return setState(await loadWorkspaceProjectDetail({
        state,
        apiBaseUrl,
        bearerToken,
        projectId,
        fetchImpl
      }));
    },

    async loadStudies({
      apiBaseUrl = "",
      bearerToken = "",
      projectId = ""
    } = {}) {
      return setState(await loadWorkspaceStudies({
        state,
        apiBaseUrl,
        bearerToken,
        projectId,
        fetchImpl
      }));
    },

    async createStudy({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceStudy({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadStudyDetail({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = ""
    } = {}) {
      return setState(await loadWorkspaceStudyDetail({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        fetchImpl
      }));
    },

    async loadStudyActivity({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      limit = 20
    } = {}) {
      return setState(await loadWorkspaceStudyActivity({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        limit,
        fetchImpl
      }));
    },

    async loadEvidenceViews({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      jobId = ""
    } = {}) {
      return setState(await loadWorkspaceEvidenceViews({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        jobId,
        fetchImpl
      }));
    },

    async createEvidenceView({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceEvidenceView({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadEvidenceViewDetail({
      apiBaseUrl = "",
      bearerToken = "",
      evidenceViewId = ""
    } = {}) {
      return setState(await loadWorkspaceEvidenceViewDetail({
        state,
        apiBaseUrl,
        bearerToken,
        evidenceViewId,
        fetchImpl
      }));
    },

    async loadDecisionLogs({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      jobId = "",
      evidenceViewId = ""
    } = {}) {
      return setState(await loadWorkspaceDecisionLogs({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        jobId,
        evidenceViewId,
        fetchImpl
      }));
    },

    async createDecisionLog({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceDecisionLog({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadDecisionLogDetail({
      apiBaseUrl = "",
      bearerToken = "",
      decisionLogId = ""
    } = {}) {
      return setState(await loadWorkspaceDecisionLogDetail({
        state,
        apiBaseUrl,
        bearerToken,
        decisionLogId,
        fetchImpl
      }));
    },

    async loadDecisionComments({
      apiBaseUrl = "",
      bearerToken = "",
      decisionLogId = ""
    } = {}) {
      return setState(await loadWorkspaceDecisionComments({
        state,
        apiBaseUrl,
        bearerToken,
        decisionLogId,
        fetchImpl
      }));
    },

    async createDecisionComment({
      apiBaseUrl = "",
      bearerToken = "",
      decisionLogId = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceDecisionComment({
        state,
        apiBaseUrl,
        bearerToken,
        decisionLogId,
        payload,
        fetchImpl
      }));
    },

    async updateDecisionReviewStatus({
      apiBaseUrl = "",
      bearerToken = "",
      decisionLogId = "",
      payload = {}
    } = {}) {
      return setState(await updateWorkspaceDecisionReviewStatus({
        state,
        apiBaseUrl,
        bearerToken,
        decisionLogId,
        payload,
        fetchImpl
      }));
    },

    async loadExportBundles({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      jobId = ""
    } = {}) {
      return setState(await loadWorkspaceExportBundles({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        jobId,
        fetchImpl
      }));
    },

    async createExportBundle({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceExportBundle({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadExportBundleDetail({
      apiBaseUrl = "",
      bearerToken = "",
      exportBundleId = ""
    } = {}) {
      return setState(await loadWorkspaceExportBundleDetail({
        state,
        apiBaseUrl,
        bearerToken,
        exportBundleId,
        fetchImpl
      }));
    },

    async loadShareBundles({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      exportBundleId = ""
    } = {}) {
      return setState(await loadWorkspaceShareBundles({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        exportBundleId,
        fetchImpl
      }));
    },

    async createShareBundle({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceShareBundle({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadShareBundleDetail({
      apiBaseUrl = "",
      bearerToken = "",
      shareBundleId = ""
    } = {}) {
      return setState(await loadWorkspaceShareBundleDetail({
        state,
        apiBaseUrl,
        bearerToken,
        shareBundleId,
        fetchImpl
      }));
    },

    async revokeShareBundle({
      apiBaseUrl = "",
      bearerToken = "",
      shareBundleId = ""
    } = {}) {
      return setState(await revokeWorkspaceShareBundle({
        state,
        apiBaseUrl,
        bearerToken,
        shareBundleId,
        fetchImpl
      }));
    },

    async loadSupportDiagnostics({
      apiBaseUrl = "",
      bearerToken = "",
      jobId = ""
    } = {}) {
      return setState(await loadWorkspaceSupportDiagnostics({
        state,
        apiBaseUrl,
        bearerToken,
        jobId,
        fetchImpl
      }));
    },

    async loadSupportSnapshots({
      apiBaseUrl = "",
      bearerToken = "",
      studyId = "",
      jobId = ""
    } = {}) {
      return setState(await loadWorkspaceSupportSnapshots({
        state,
        apiBaseUrl,
        bearerToken,
        studyId,
        jobId,
        fetchImpl
      }));
    },

    async createSupportSnapshot({
      apiBaseUrl = "",
      bearerToken = "",
      payload = {}
    } = {}) {
      return setState(await createWorkspaceSupportSnapshot({
        state,
        apiBaseUrl,
        bearerToken,
        payload,
        fetchImpl
      }));
    },

    async loadSupportSnapshotDetail({
      apiBaseUrl = "",
      bearerToken = "",
      supportSnapshotId = ""
    } = {}) {
      return setState(await loadWorkspaceSupportSnapshotDetail({
        state,
        apiBaseUrl,
        bearerToken,
        supportSnapshotId,
        fetchImpl
      }));
    },

    async listLiveJobs({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {}
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
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
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {}
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
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
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {},
      queryState = {},
      selectedResultId = "",
      selectedReplayStepId = "",
      selectedComparisonRunId = ""
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
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
        selectedComparisonRunId,
        fetchImpl
      }));
    },

    async syncRuntime({
      apiBaseUrl = "",
      bearerToken = "",
      briefPath = "",
      personaDir = "",
      panelType = "",
      sampleSize = "",
      providerName = "",
      runRoot = "",
      modeOverride = "",
      personaFilters = {},
      queryState = {},
      selectedResultId,
      selectedReplayStepId,
      selectedComparisonRunId
    } = {}) {
      const contextualState = withWorkspaceContext(state, {
        apiBaseUrl,
        briefPath,
        personaDir,
        panelType,
        sampleSize,
        providerName,
        runRoot,
        modeOverride,
        personaFilters
      });
      return setState(await syncWorkspaceShellRuntime({
        state: contextualState,
        apiBaseUrl,
        bearerToken,
        queryState,
        selectedResultId,
        selectedReplayStepId,
        selectedComparisonRunId,
        fetchImpl,
        now
      }));
    }
  };
}
