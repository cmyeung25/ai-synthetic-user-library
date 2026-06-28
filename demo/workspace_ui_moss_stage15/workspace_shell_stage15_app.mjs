import { createWorkspaceShellAppController } from "../workspace_ui_shared/workspace_shell_app.mjs";
import {
  createHostedWorkspaceRouteState,
  deriveHostedWorkspaceRoutePath,
  normalizeHostedWorkspaceRouteKind
} from "../workspace_ui_shared/workspace_shell_hosted_routes.mjs";

const HOSTED_SESSION_STORAGE_KEY = "ai_validation_swarm.workspace_shell_session.v1";

function resolveStorage(storageLike) {
  if (
    storageLike
    && typeof storageLike.getItem === "function"
    && typeof storageLike.setItem === "function"
    && typeof storageLike.removeItem === "function"
  ) {
    return storageLike;
  }
  return null;
}

export function readPersistedStage15HostedSession({ storageLike } = {}) {
  const storage = resolveStorage(storageLike);
  if (storage) {
    try {
      storage.removeItem(HOSTED_SESSION_STORAGE_KEY);
    } catch {
      // Ignore local storage cleanup failures while removing bearer persistence.
    }
  }
  return {
    hasSavedToken: false,
    bearerToken: "",
    updatedAt: ""
  };
}

export function persistStage15HostedSession({ storageLike, bearerToken = "" } = {}) {
  void storageLike;
  void bearerToken;
  return false;
}

export function clearPersistedStage15HostedSession({ storageLike } = {}) {
  const storage = resolveStorage(storageLike);
  if (!storage) {
    return false;
  }
  try {
    storage.removeItem(HOSTED_SESSION_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

export function deriveStage15HostedBootstrap({
  locationLike = {},
  routeContext = {},
  storageLike = null
} = {}) {
  const origin = String(locationLike.origin || "");
  const pathname = String(locationLike.pathname || "");
  const search = String(locationLike.search || "");
  const locationQuery = new URLSearchParams(search);
  const hostedRouteEnabled = origin.startsWith("http") && pathname.startsWith("/app");
  const hostedApiBase = locationQuery.get("api_base_url") || (hostedRouteEnabled ? origin : "");
  const explicitHostedToken = locationQuery.get("token") || "";
  const persistedHostedSession = { hasSavedToken: false, bearerToken: "", updatedAt: "" };
  const hostedToken = explicitHostedToken || "";
  const hostedTokenSource = explicitHostedToken ? "query" : hostedRouteEnabled ? "server_session" : "none";
  const hostedRouteState = createHostedWorkspaceRouteState({
    routeContext,
    pathname,
    search
  });
  return {
    locationQuery,
    hostedRouteEnabled,
    hostedApiBase,
    hostedToken,
    hostedTokenSource,
    hostedRouteState,
    routeSelection: hostedRouteState.selection,
    persistedHostedSession
  };
}

export function mountStage15WorkspaceShell({
  document: documentLike = document,
  window: windowLike = window,
  controller = createWorkspaceShellAppController()
} = {}) {
  const metricProject = documentLike.getElementById("metric-project");
  const metricStudy = documentLike.getElementById("metric-study");
  const metricShell = documentLike.getElementById("metric-shell");
  const metricRun = documentLike.getElementById("metric-run");

  const sessionPill = documentLike.getElementById("session-pill");
  const sessionMemoryPill = documentLike.getElementById("session-memory-pill");
  const runtimePill = documentLike.getElementById("runtime-pill");
  const projectPill = documentLike.getElementById("project-pill");
  const studyPill = documentLike.getElementById("study-pill");
  const bridgePill = documentLike.getElementById("bridge-pill");
  const jobPill = documentLike.getElementById("job-pill");
  const queryPill = documentLike.getElementById("query-pill");
  const supportPill = documentLike.getElementById("support-pill");
  const settingsPill = documentLike.getElementById("settings-pill");
  const decisionReviewPill = documentLike.getElementById("decision-review-pill");

  const apiBaseUrlInput = documentLike.getElementById("api-base-url");
  const apiTokenInput = documentLike.getElementById("api-token");
  const briefPathInput = documentLike.getElementById("brief-path");
  const personaDirInput = documentLike.getElementById("persona-dir");
  const modeOverrideSelect = documentLike.getElementById("mode-override");
  const panelTypeSelect = documentLike.getElementById("panel-type");
  const sampleSizeInput = documentLike.getElementById("sample-size");
  const providerNameSelect = documentLike.getElementById("provider-name");
  const personaFilterLocationSelect = documentLike.getElementById("persona-filter-location");
  const personaFilterPrivacySelect = documentLike.getElementById("persona-filter-privacy");

  const researchIntentInput = documentLike.getElementById("research-intent");
  const desiredOutcomeInput = documentLike.getElementById("desired-outcome");
  const firstTaskInput = documentLike.getElementById("first-task");
  const artifactFilesInput = documentLike.getElementById("artifact-files");
  const artifactNote = documentLike.getElementById("artifact-note");

  const projectNameInput = documentLike.getElementById("project-name");
  const projectSlugInput = documentLike.getElementById("project-slug");
  const studyTitleInput = documentLike.getElementById("study-title");
  const studyFirstTaskInput = documentLike.getElementById("study-first-task");

  const evidenceQueryTextInput = documentLike.getElementById("evidence-query-text");
  const evidenceFamilySelect = documentLike.getElementById("evidence-family");
  const evidenceSortSelect = documentLike.getElementById("evidence-sort");
  const evidenceViewTitleInput = documentLike.getElementById("evidence-view-title");
  const evidenceViewNoteInput = documentLike.getElementById("evidence-view-note");
  const decisionLogTitleInput = documentLike.getElementById("decision-log-title");
  const decisionLogSummaryInput = documentLike.getElementById("decision-log-summary");
  const decisionLogRationaleInput = documentLike.getElementById("decision-log-rationale");
  const decisionReviewNoteInput = documentLike.getElementById("decision-review-note");
  const decisionCommentAnchorSelect = documentLike.getElementById("decision-comment-anchor");
  const decisionCommentBodyInput = documentLike.getElementById("decision-comment-body");
  const exportTitleInput = documentLike.getElementById("export-title");
  const exportFormatSelect = documentLike.getElementById("export-format");
  const exportArtifactsInput = documentLike.getElementById("export-artifacts");
  const shareTitleInput = documentLike.getElementById("share-title");
  const shareExpiresDaysInput = documentLike.getElementById("share-expires-days");
  const supportSnapshotTitleInput = documentLike.getElementById("support-snapshot-title");
  const supportSnapshotNotesInput = documentLike.getElementById("support-snapshot-notes");
  const memberUserIdInput = documentLike.getElementById("member-user-id");
  const memberRoleSelect = documentLike.getElementById("member-role");
  const auditTargetTypeInput = documentLike.getElementById("audit-target-type");
  const auditActionPrefixInput = documentLike.getElementById("audit-action-prefix");
  const auditLimitInput = documentLike.getElementById("audit-limit");
  const billingPlanTierSelect = documentLike.getElementById("billing-plan-tier");
  const billingStatusSelect = documentLike.getElementById("billing-status");
  const billingSeatCountInput = documentLike.getElementById("billing-seat-count");
  const billingRenewalAtInput = documentLike.getElementById("billing-renewal-at");
  const quotaDailyRunsInput = documentLike.getElementById("quota-daily-runs");
  const quotaConcurrentJobsInput = documentLike.getElementById("quota-concurrent-jobs");
  const quotaRetentionDaysInput = documentLike.getElementById("quota-retention-days");
  const tokenUserIdInput = documentLike.getElementById("token-user-id");

  const refreshWorkspaceButton = documentLike.getElementById("refresh-workspace");
  const loadSessionButton = documentLike.getElementById("load-session");
  const loadShellButton = documentLike.getElementById("load-shell");
  const toggleAutoRefreshButton = documentLike.getElementById("toggle-auto-refresh");
  const forgetSavedSessionButton = documentLike.getElementById("forget-saved-session");
  const submitLiveJobButton = documentLike.getElementById("submit-live-job");
  const retrySelectedJobButton = documentLike.getElementById("retry-selected-job");
  const cancelSelectedJobButton = documentLike.getElementById("cancel-selected-job");
  const useSampleJobsButton = documentLike.getElementById("use-sample-jobs");
  const applyEvidenceQueryButton = documentLike.getElementById("apply-evidence-query");
  const createEvidenceViewButton = documentLike.getElementById("create-evidence-view");
  const reloadEvidenceViewsButton = documentLike.getElementById("reload-evidence-views");
  const createDecisionLogButton = documentLike.getElementById("create-decision-log");
  const reloadDecisionLogsButton = documentLike.getElementById("reload-decision-logs");
  const reloadStudyActivityButton = documentLike.getElementById("reload-study-activity");
  const reloadDecisionReviewButton = documentLike.getElementById("reload-decision-review");
  const requestDecisionReviewButton = documentLike.getElementById("request-decision-review");
  const approveDecisionLogButton = documentLike.getElementById("approve-decision-log");
  const requestDecisionRevisionButton = documentLike.getElementById("request-decision-revision");
  const createDecisionCommentButton = documentLike.getElementById("create-decision-comment");
  const clearDecisionReplyTargetButton = documentLike.getElementById("clear-decision-reply-target");
  const reloadProjectsButton = documentLike.getElementById("reload-projects");
  const reloadStudiesButton = documentLike.getElementById("reload-studies");
  const createExportBundleButton = documentLike.getElementById("create-export-bundle");
  const reloadExportBundlesButton = documentLike.getElementById("reload-export-bundles");
  const createShareBundleButton = documentLike.getElementById("create-share-bundle");
  const reloadShareBundlesButton = documentLike.getElementById("reload-share-bundles");
  const revokeShareBundleButton = documentLike.getElementById("revoke-share-bundle");
  const loadSupportDiagnosticsButton = documentLike.getElementById("load-support-diagnostics");
  const createSupportSnapshotButton = documentLike.getElementById("create-support-snapshot");
  const reloadSupportSnapshotsButton = documentLike.getElementById("reload-support-snapshots");
  const loadWorkspaceSettingsButton = documentLike.getElementById("load-workspace-settings");
  const loadAuditEventsButton = documentLike.getElementById("load-audit-events");
  const upsertWorkspaceMemberButton = documentLike.getElementById("upsert-workspace-member");
  const updateWorkspaceBillingButton = documentLike.getElementById("update-workspace-billing");
  const issueApiTokenButton = documentLike.getElementById("issue-api-token");

  const projectForm = documentLike.getElementById("project-form");
  const studyForm = documentLike.getElementById("study-form");
  const projectList = documentLike.getElementById("project-list");
  const studyList = documentLike.getElementById("study-list");
  const studyActions = documentLike.getElementById("study-actions");
  const jobList = documentLike.getElementById("job-list");
  const evidenceList = documentLike.getElementById("evidence-list");
  const exportList = documentLike.getElementById("export-list");
  const shareList = documentLike.getElementById("share-list");
  const supportList = documentLike.getElementById("support-list");
  const studyActivityList = documentLike.getElementById("study-activity-list");

  const sessionSummary = documentLike.getElementById("session-summary");
  const limitSummary = documentLike.getElementById("limit-summary");
  const selectedProjectSummary = documentLike.getElementById("selected-project-summary");
  const selectedStudySummary = documentLike.getElementById("selected-study-summary");
  const draftSummary = documentLike.getElementById("draft-summary");
  const adapterSummary = documentLike.getElementById("adapter-summary");
  const runSummary = documentLike.getElementById("run-summary");
  const reviewSummary = documentLike.getElementById("review-summary");
  const selectedEvidenceSummary = documentLike.getElementById("selected-evidence-summary");
  const selectedEvidenceDetail = documentLike.getElementById("selected-evidence-detail");
  const crossRunSummary = documentLike.getElementById("cross-run-summary");
  const crossRunDetail = documentLike.getElementById("cross-run-detail");
  const evidenceViewList = documentLike.getElementById("evidence-view-list");
  const selectedEvidenceViewSummary = documentLike.getElementById("selected-evidence-view-summary");
  const studyActivitySummary = documentLike.getElementById("study-activity-summary");
  const decisionLogList = documentLike.getElementById("decision-log-list");
  const selectedDecisionLogSummary = documentLike.getElementById("selected-decision-log-summary");
  const decisionReviewSummary = documentLike.getElementById("decision-review-summary");
  const decisionCommentList = documentLike.getElementById("decision-comment-list");
  const decisionReplyTargetPill = documentLike.getElementById("decision-reply-target");
  const selectedExportSummary = documentLike.getElementById("selected-export-summary");
  const selectedShareSummary = documentLike.getElementById("selected-share-summary");
  const supportGateSummary = documentLike.getElementById("support-gate-summary");
  const supportDiagnosticSummary = documentLike.getElementById("support-diagnostic-summary");
  const supportBlockedReasons = documentLike.getElementById("support-blocked-reasons");
  const supportDiagnosticCards = documentLike.getElementById("support-diagnostic-cards");
  const supportRecentFailures = documentLike.getElementById("support-recent-failures");
  const selectedSupportSummary = documentLike.getElementById("selected-support-summary");
  const workspaceSettingsSummary = documentLike.getElementById("workspace-settings-summary");
  const workspaceBillingSummary = documentLike.getElementById("workspace-billing-summary");
  const workspacePolicySummary = documentLike.getElementById("workspace-policy-summary");
  const workspaceAuditSummary = documentLike.getElementById("workspace-audit-summary");
  const workspaceMemberList = documentLike.getElementById("workspace-member-list");
  const lastIssuedTokenSummary = documentLike.getElementById("last-issued-token-summary");
  const workspaceTokenList = documentLike.getElementById("workspace-token-list");
  const workspaceAuditList = documentLike.getElementById("workspace-audit-list");
  const evidenceNote = documentLike.getElementById("evidence-note");
  const boundaryCopy = documentLike.getElementById("boundary-copy");
  const lastApiJson = documentLike.getElementById("last-api-json");
  const requestPayloadJson = documentLike.getElementById("request-payload-json");
  const createStudyButton = documentLike.getElementById("create-study");

  let autoRefreshTimer = null;
  let pendingDecisionReplyCommentId = "";

  const bootstrap = deriveStage15HostedBootstrap({
    locationLike: windowLike.location,
    routeContext: windowLike.__WORKSPACE_ROUTE_CONTEXT__ || {},
    storageLike: windowLike.localStorage
  });
  const {
    locationQuery,
    hostedRouteEnabled,
    hostedApiBase,
    hostedToken,
    hostedTokenSource,
    persistedHostedSession,
    routeSelection
  } = bootstrap;
  let hostedRouteState = bootstrap.hostedRouteState;
  let hostedSessionState = {
    cookieSessionActive: false,
    signedOut: false,
    tokenSource: hostedTokenSource
  };

  if (hostedApiBase) {
    apiBaseUrlInput.value = hostedApiBase;
  }
  if (hostedToken) {
    apiTokenInput.value = hostedToken;
  }

  function toPersonaFilters() {
    const filters = {};
    if (personaFilterLocationSelect.value !== "all") {
      filters.location_type = personaFilterLocationSelect.value;
    }
    if (personaFilterPrivacySelect.value !== "all") {
      filters.privacy_concern = personaFilterPrivacySelect.value;
    }
    return filters;
  }

  function readInputs() {
    return {
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      briefPath: briefPathInput.value.trim(),
      personaDir: personaDirInput.value.trim(),
      modeOverride: modeOverrideSelect.value === "auto" ? "" : modeOverrideSelect.value,
      panelType: panelTypeSelect.value,
      sampleSize: Number(sampleSizeInput.value || 5),
      providerName: providerNameSelect.value,
      personaFilters: toPersonaFilters(),
      queryState: {
        queryText: evidenceQueryTextInput.value.trim(),
        activeFamily: evidenceFamilySelect.value,
        sortBy: evidenceSortSelect.value
      }
    };
  }

  function hasWorkspaceAuthInput() {
    const apiBaseUrl = apiBaseUrlInput.value.trim();
    if (!apiBaseUrl) {
      return false;
    }
    return Boolean(apiTokenInput.value.trim() || hostedRouteEnabled);
  }

  function renderRows(target, rows = []) {
    target.innerHTML = "";
    rows.forEach((row) => {
      const item = documentLike.createElement("div");
      item.className = "summary-row";
      item.innerHTML = `<span>${row.label}</span><strong>${row.value}</strong>`;
      target.appendChild(item);
    });
  }

  function renderDetailCards(target, cards = []) {
    target.innerHTML = "";
    cards.forEach((card) => {
      const node = documentLike.createElement("div");
      node.className = `detail-card${card.tone === "active" ? " active" : ""}`;
      node.innerHTML = `<strong>${card.title}</strong><span>${card.body}</span>`;
      target.appendChild(node);
    });
  }

  function deriveSupportPill(model) {
    const supportSurface = model.frontendState.support_surface || {};
    const diagnostic = model.state.liveSupportDiagnostics?.job_diagnostic || supportSurface.job_diagnostic || null;
    const submissionGateStatus = supportSurface.submission_gate_summary?.[0]?.value || "unknown";
    if (diagnostic?.status === "failed" || diagnostic?.status === "canceled") {
      return {
        tone: "failed",
        label: diagnostic.failure_category || diagnostic.status
      };
    }
    if (submissionGateStatus === "blocked") {
      return {
        tone: "queued",
        label: "submission_blocked"
      };
    }
    if (model.state.liveSupportDiagnostics) {
      return {
        tone: "completed",
        label: "support_loaded"
      };
    }
    return {
      tone: "queued",
      label: "support_idle"
    };
  }

  function deriveSettingsPill(model) {
    const workspaceSettings = model.frontendState.product_surface.workspace_settings_summary || [];
    const capabilities = model.state.liveWorkspaceSettings?.capabilities || {};
    if (model.state.liveError && String(model.state.liveError).toLowerCase().includes("workspace")) {
      return {
        tone: "failed",
        label: "settings_error"
      };
    }
    if (model.state.liveWorkspaceSettings) {
      if (capabilities.member_admin || capabilities.token_admin) {
        return {
          tone: "completed",
          label: "settings_ready"
        };
      }
      return {
        tone: "queued",
        label: "settings_read_only"
      };
    }
    if (workspaceSettings.length) {
      return {
        tone: "queued",
        label: "settings_cached"
      };
    }
    return {
      tone: "queued",
      label: "settings_unloaded"
    };
  }

  function seedWorkspaceBillingInputs() {
    const workspaceSettings = controller.getState().liveWorkspaceSettings;
    if (!workspaceSettings) {
      return;
    }
    billingPlanTierSelect.value = workspaceSettings.workspace?.plan_tier || "trial";
    billingStatusSelect.value = workspaceSettings.billing_account?.status || "trialing";
    billingSeatCountInput.value = String(workspaceSettings.billing_account?.seat_count ?? 1);
    billingRenewalAtInput.value = workspaceSettings.billing_account?.renewal_at || "";
    quotaDailyRunsInput.value = String(workspaceSettings.plan_limits?.daily_runs ?? 0);
    quotaConcurrentJobsInput.value = String(workspaceSettings.plan_limits?.max_concurrent_jobs ?? 0);
    quotaRetentionDaysInput.value = String(workspaceSettings.plan_limits?.artifact_retention_days ?? 0);
  }

  function buildHostedRouteSearch() {
    const params = new URLSearchParams();
    if (locationQuery.get("token")) {
      params.set("token", locationQuery.get("token"));
    }
    if (locationQuery.get("api_base_url")) {
      params.set("api_base_url", locationQuery.get("api_base_url"));
    }
    return params;
  }

  function updateHostedSessionMemoryPill() {
    if (!sessionMemoryPill) {
      return;
    }
    const currentTokenValue = apiTokenInput.value.trim();
    if (!hostedRouteEnabled) {
      sessionMemoryPill.className = "status-pill queued";
      sessionMemoryPill.textContent = currentTokenValue ? "manual_token" : "session_memory_off";
      return;
    }
    if (hostedSessionState.cookieSessionActive) {
      sessionMemoryPill.className = "status-pill completed";
      sessionMemoryPill.textContent = "browser_session";
      return;
    }
    if (currentTokenValue) {
      sessionMemoryPill.className = "status-pill queued";
      sessionMemoryPill.textContent = hostedSessionState.tokenSource === "query"
        ? "bootstrap_token"
        : "manual_token";
      return;
    }
    sessionMemoryPill.className = "status-pill queued";
    sessionMemoryPill.textContent = hostedSessionState.signedOut ? "session_ended" : "session_check_pending";
  }

  function updateDecisionReplyTargetPill() {
    if (!decisionReplyTargetPill) {
      return;
    }
    if (pendingDecisionReplyCommentId) {
      decisionReplyTargetPill.className = "status-pill running";
      decisionReplyTargetPill.textContent = `reply_to:${pendingDecisionReplyCommentId}`;
      return;
    }
    decisionReplyTargetPill.className = "status-pill queued";
    decisionReplyTargetPill.textContent = "reply_to:none";
  }

  function markBrowserSessionActive() {
    if (!hostedRouteEnabled) {
      return;
    }
    hostedSessionState = {
      ...hostedSessionState,
      cookieSessionActive: true,
      signedOut: false
    };
    updateHostedSessionMemoryPill();
  }

  async function forgetHostedSessionIfPossible() {
    if (hostedRouteEnabled && apiBaseUrlInput.value.trim()) {
      try {
        await fetch(`${apiBaseUrlInput.value.trim()}/api/v1/session/logout`, {
          method: "POST"
        });
      } catch {
        // Allow local shell state to clear even if the logout request fails.
      }
    }
    clearPersistedStage15HostedSession({
      storageLike: windowLike.localStorage
    });
    hostedSessionState = {
      cookieSessionActive: false,
      signedOut: true,
      tokenSource: locationQuery.get("token") ? "query" : hostedRouteEnabled ? "server_session" : "none"
    };
    if (hostedRouteEnabled) {
      apiTokenInput.value = "";
    }
    render();
  }

  function setHostedRouteKind(routeKind) {
    hostedRouteState = {
      ...hostedRouteState,
      routeKind: normalizeHostedWorkspaceRouteKind(routeKind)
    };
  }

  function syncHostedRoute(model) {
    if (!hostedRouteEnabled) {
      return;
    }
    const params = buildHostedRouteSearch();
    const nextPath = deriveHostedWorkspaceRoutePath({
      state: model.state,
      preferredRouteKind: hostedRouteState.routeKind
    });
    const nextUrl = params.toString().length ? `${nextPath}?${params.toString()}` : nextPath;
    const currentUrl = `${windowLike.location.pathname}${windowLike.location.search}`;
    if (currentUrl !== nextUrl) {
      windowLike.history.replaceState({}, "", nextUrl);
    }
  }

  async function bootstrapRouteSelection() {
    const apiBaseUrl = apiBaseUrlInput.value.trim();
    const bearerToken = apiTokenInput.value.trim();
    if (!apiBaseUrl || !hasWorkspaceAuthInput()) {
      return;
    }
    if (!Object.values(routeSelection).some((value) => String(value || "").trim().length > 0)) {
      return;
    }

    if (routeSelection.projectId) {
      await controller.loadProjectDetail({ apiBaseUrl, bearerToken, projectId: routeSelection.projectId });
    }
    if (routeSelection.studyId) {
      await controller.loadStudyDetail({ apiBaseUrl, bearerToken, studyId: routeSelection.studyId });
    }
    if (routeSelection.evidenceViewId) {
      setHostedRouteKind("evidence_view");
      await controller.loadEvidenceViewDetail({
        apiBaseUrl,
        bearerToken,
        evidenceViewId: routeSelection.evidenceViewId
      });
    }
    if (routeSelection.decisionLogId) {
      setHostedRouteKind("decision_log");
      await controller.loadDecisionLogDetail({
        apiBaseUrl,
        bearerToken,
        decisionLogId: routeSelection.decisionLogId
      });
    }
    if (routeSelection.exportBundleId) {
      await controller.loadExportBundleDetail({ apiBaseUrl, bearerToken, exportBundleId: routeSelection.exportBundleId });
    }
    if (routeSelection.shareBundleId) {
      await controller.loadShareBundleDetail({ apiBaseUrl, bearerToken, shareBundleId: routeSelection.shareBundleId });
    }
    if (routeSelection.supportSnapshotId) {
      await controller.loadSupportSnapshotDetail({
        apiBaseUrl,
        bearerToken,
        supportSnapshotId: routeSelection.supportSnapshotId
      });
    }
    if (routeSelection.jobId) {
      setHostedRouteKind("job");
      controller.selectJob(routeSelection.jobId);
      await controller.loadSelectedLiveJob({ apiBaseUrl, bearerToken });
    }
  }

  function currentModel() {
    return controller.deriveModel(readInputs());
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  function refreshAutoSyncLoop(model) {
    stopAutoRefresh();
    if (!model.state.runtimeSync?.auto_refresh_enabled) {
      return;
    }
    const interval = model.state.runtimeSync?.interval_ms || 4000;
    autoRefreshTimer = setInterval(async () => {
      const liveModel = currentModel();
      if (liveModel.state.mode !== "live" || !liveModel.state.selectedStudyId) {
        return;
      }
      await performRuntimeSync();
    }, interval);
  }

  function updateDraftInputs(model) {
    researchIntentInput.value = model.state.shellState?.researchIntent || "";
    desiredOutcomeInput.value = model.state.shellState?.desiredOutcome || "";
    firstTaskInput.value = model.state.shellState?.firstTask || "";
    artifactNote.textContent = (model.state.shellState?.attachedArtifacts || []).length
      ? `${model.state.shellState.attachedArtifacts.length} artifact(s): ${model.state.shellState.attachedArtifacts.join(", ")}`
      : "No prototype artifacts attached yet.";
  }

  function renderStudyActions(model) {
    studyActions.innerHTML = "";
    const buttons = [
      {
        label: model.state.shellState?.hasScreenshots ? "clear artifacts" : "attach sample artifacts",
        disabled: false,
        onClick() {
          controller.togglePrototypeArtifacts();
          render();
        }
      },
      {
        label: model.state.shellState?.fallbackChosen ? "clear fallback" : "choose fallback",
        disabled: model.state.shellState?.lifecycle !== "ready_to_queue",
        onClick() {
          controller.toggleFallbackMode();
          render();
        }
      },
      {
        label: model.state.shellState?.savedBlocked ? "resume draft" : "save blocked draft",
        disabled: model.state.shellState?.lifecycle !== "ready_to_queue",
        onClick() {
          controller.toggleSavedDraft();
          render();
        }
      },
      {
        label: "confirm plan",
        primary: true,
        disabled: model.bundle?.adapter?.ui_phase !== "ready_for_confirmation",
        onClick() {
          controller.confirmDraftPlan(readInputs());
          render();
        }
      },
      {
        label: "reset draft",
        disabled: false,
        onClick() {
          controller.resetDraftFlow();
          render();
        }
      }
    ];

    buttons.forEach((action) => {
      const button = documentLike.createElement("button");
      button.type = "button";
      button.className = `action-button${action.primary ? " primary" : ""}`;
      button.textContent = action.label;
      button.disabled = Boolean(action.disabled);
      button.addEventListener("click", action.onClick);
      studyActions.appendChild(button);
    });
  }

  async function hydrateWorkspace({ loadProjects = true, loadStudies = true } = {}) {
    const input = readInputs();
    await controller.loadWorkspaceSession(input);
    if (controller.getState().liveSession) {
      markBrowserSessionActive();
    }
    await controller.loadWorkspaceSettings(input);
    seedWorkspaceBillingInputs();
    if (loadProjects) {
      await controller.loadProjects(input);
    }
    const projectId = controller.getState().selectedProjectId;
    if (loadStudies && projectId) {
      await controller.loadStudies({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        projectId
      });
    }
    const studyId = controller.getState().selectedStudyId;
    if (studyId) {
      await controller.loadEvidenceViews({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        studyId
      });
      await controller.loadStudyActivity({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        studyId
      });
      await controller.loadDecisionLogs({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        studyId
      });
      await controller.loadExportBundles({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        studyId
      });
      await controller.loadSupportSnapshots({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        studyId
      });
    }
    const exportBundleId = controller.getState().selectedExportBundleId;
    if (exportBundleId) {
      await controller.loadShareBundles({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        exportBundleId
      });
    }
    if (controller.getState().selectedJobId) {
      await controller.loadSupportDiagnostics({
        apiBaseUrl: input.apiBaseUrl,
        bearerToken: input.bearerToken,
        jobId: controller.getState().selectedJobId
      });
    }
  }

  async function performRuntimeSync(overrides = {}) {
    const input = readInputs();
    const model = currentModel();
    if (!model.state.selectedStudyId) {
      return;
    }
    await controller.syncRuntime({
      ...input,
      ...overrides,
      selectedResultId: overrides.selectedResultId ?? model.frontendState.review_surface.selected_result_id ?? "",
      selectedReplayStepId: overrides.selectedReplayStepId ?? model.frontendState.review_surface.selected_replay_step_id ?? "",
      selectedComparisonRunId: overrides.selectedComparisonRunId ?? model.frontendState.review_surface.selected_comparison_run_id ?? ""
    });
    render();
  }

  function renderProjects(model) {
    projectList.innerHTML = "";
    const projects = model.frontendState.product_surface.projects || [];
    projectPill.textContent = `${projects.length} project${projects.length === 1 ? "" : "s"}`;
    if (!projects.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No projects exist yet. Create one to give the workspace a durable research area.";
      projectList.appendChild(empty);
      return;
    }
    projects.forEach((project) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${project.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${project.title}</strong>
          <div class="product-meta">
            <span>${project.slug}</span>
            <span>${project.study_count} studies</span>
          </div>
          <p>${project.description}</p>
        `;
      card.addEventListener("click", async () => {
        setHostedRouteKind("project");
        controller.selectProject(project.project_id);
        controller.selectStudy(null);
        await controller.loadStudies({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          projectId: project.project_id
        });
        const studyId = controller.getState().selectedStudyId;
        if (studyId) {
          await controller.loadEvidenceViews({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            studyId
          });
          await controller.loadDecisionLogs({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            studyId
          });
          await controller.loadExportBundles({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            studyId
          });
          await controller.loadSupportSnapshots({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            studyId
          });
          const exportBundleId = controller.getState().selectedExportBundleId;
          if (exportBundleId) {
            await controller.loadShareBundles({
              apiBaseUrl: apiBaseUrlInput.value.trim(),
              bearerToken: apiTokenInput.value.trim(),
              exportBundleId
            });
          }
        }
        render();
      });
      projectList.appendChild(card);
    });
  }

  function renderStudies(model) {
    studyList.innerHTML = "";
    const studies = model.frontendState.product_surface.studies || [];
    studyPill.textContent = `${studies.length} stud${studies.length === 1 ? "y" : "ies"}`;
    if (!model.state.selectedProjectId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a project first. Studies live inside that project context.";
      studyList.appendChild(empty);
      return;
    }
    if (!studies.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No studies exist yet for this project. Create one from a concrete research intent.";
      studyList.appendChild(empty);
      return;
    }
    studies.forEach((study) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${study.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${study.title}</strong>
          <div class="product-meta">
            <span>${study.status}</span>
            <span>${study.run_count} runs</span>
            <span>${study.latest_job_status}</span>
          </div>
          <p>First task: ${study.first_task}</p>
        `;
      card.addEventListener("click", async () => {
        setHostedRouteKind("study");
        controller.selectStudy(study.study_id);
        await controller.loadStudyActivity({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          studyId: study.study_id
        });
        await controller.loadEvidenceViews({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          studyId: study.study_id
        });
        await controller.loadDecisionLogs({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          studyId: study.study_id
        });
        await controller.loadExportBundles({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          studyId: study.study_id
        });
        await controller.loadSupportSnapshots({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          studyId: study.study_id
        });
        const exportBundleId = controller.getState().selectedExportBundleId;
        if (exportBundleId) {
          await controller.loadShareBundles({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            exportBundleId
          });
        }
        render();
      });
      studyList.appendChild(card);
    });
  }

  function renderJobs(model) {
    jobList.innerHTML = "";
    const jobs = model.jobs || [];
    if (!jobs.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No runs are visible yet. Confirm the study plan and submit a run.";
      jobList.appendChild(empty);
      return;
    }
    jobs.forEach((job) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${job.job_id === model.state.selectedJobId ? " active" : ""}`;
      card.innerHTML = `
          <strong>${job.job_id}</strong>
          <div class="product-meta">
            <span>${job.status}</span>
            <span>${job.provider_name}</span>
          </div>
          <p>${job.output_run_path || job.last_error || "Run output not available yet."}</p>
        `;
      card.addEventListener("click", async () => {
        setHostedRouteKind("job");
        controller.selectJob(job.job_id);
        if (controller.getState().mode === "live") {
          await performRuntimeSync({
            selectedResultId: "",
            selectedReplayStepId: "",
            selectedComparisonRunId: ""
          });
          return;
        }
        render();
      });
      jobList.appendChild(card);
    });
  }

  function renderEvidence(model) {
    evidenceList.innerHTML = "";
    const reviewSurface = model.frontendState.review_surface;
    evidenceNote.textContent = reviewSurface.empty_note;
    (reviewSurface.results || []).forEach((result) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${result.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${result.title}</strong>
          <div class="product-meta">
            <span>${result.family}</span>
            <span>${result.kind}</span>
            <span>score ${result.relevance_score ?? "-"}</span>
          </div>
          <p>${result.summary}</p>
        `;
      card.addEventListener("click", async () => {
        if (model.state.mode === "live" && model.state.selectedJobId) {
          await performRuntimeSync({
            selectedResultId: result.id,
            selectedReplayStepId: "",
            selectedComparisonRunId: reviewSurface.selected_comparison_run_id || ""
          });
          return;
        }
        controller.selectLocalEvidenceResult(result.id);
        render();
      });
      evidenceList.appendChild(card);
    });
    if (!reviewSurface.results.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = reviewSurface.empty_note;
      evidenceList.appendChild(empty);
    }
    renderRows(selectedEvidenceSummary, reviewSurface.selected_evidence_summary || []);
    renderDetailCards(selectedEvidenceDetail, reviewSurface.selected_evidence_detail || []);
    renderRows(crossRunSummary, reviewSurface.cross_run_summary || []);
    renderDetailCards(crossRunDetail, reviewSurface.cross_run_detail || []);
  }

  function renderCollaboration(model) {
    const productSurface = model.frontendState.product_surface || {};
    const decisionReviewSurface = model.frontendState.decision_review_surface || {};
    const evidenceViews = productSurface.evidence_views || [];
    const decisionLogs = productSurface.decision_logs || [];

    evidenceViewList.innerHTML = "";
    if (!model.state.selectedStudyId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a study before loading saved evidence views.";
      evidenceViewList.appendChild(empty);
    } else if (!evidenceViews.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No saved evidence views yet for this study.";
      evidenceViewList.appendChild(empty);
    } else {
      evidenceViews.forEach((view) => {
        const card = documentLike.createElement("button");
        card.type = "button";
        card.className = `product-card${view.selected ? " active" : ""}`;
        card.innerHTML = `
            <strong>${view.title}</strong>
            <div class="product-meta">
              <span>${view.active_family}</span>
              <span>${view.sort_by}</span>
              <span>${view.job_id || "no job"}</span>
            </div>
            <p>${view.note}</p>
        `;
        card.addEventListener("click", async () => {
          setHostedRouteKind("evidence_view");
          controller.selectEvidenceView(view.evidence_view_id);
          if (hasWorkspaceAuthInput()) {
            await controller.loadEvidenceViewDetail({
              apiBaseUrl: apiBaseUrlInput.value.trim(),
              bearerToken: apiTokenInput.value.trim(),
              evidenceViewId: view.evidence_view_id
            });
          }
          const selectedView = controller.getState().liveEvidenceViews.find(
            (item) => item.evidence_view_id === view.evidence_view_id
          ) || model.state.liveEvidenceViews.find((item) => item.evidence_view_id === view.evidence_view_id) || null;
          evidenceQueryTextInput.value = selectedView?.query_text || "";
          evidenceFamilySelect.value = selectedView?.active_family || "all";
          evidenceSortSelect.value = selectedView?.sort_by || "relevance";
          if (selectedView?.job_id) {
            controller.selectJob(selectedView.job_id);
          }
          if (controller.getState().mode === "live" && selectedView?.job_id) {
            await performRuntimeSync({
              selectedResultId: selectedView.selected_result_id || "",
              selectedReplayStepId: selectedView.selected_replay_step_id || "",
              selectedComparisonRunId: selectedView.selected_comparison_run_id || ""
            });
            return;
          }
          render();
        });
        evidenceViewList.appendChild(card);
      });
    }

    decisionLogList.innerHTML = "";
    if (!model.state.selectedStudyId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a study before loading decision logs.";
      decisionLogList.appendChild(empty);
    } else if (!decisionLogs.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No decision logs yet for this study.";
      decisionLogList.appendChild(empty);
    } else {
      decisionLogs.forEach((log) => {
        const card = documentLike.createElement("button");
        card.type = "button";
        card.className = `product-card${log.selected ? " active" : ""}`;
        card.innerHTML = `
            <strong>${log.title}</strong>
            <div class="product-meta">
              <span>${log.job_id || "no job"}</span>
              <span>${log.evidence_view_id || "no linked view"}</span>
              <span>${log.review_status || "draft"}</span>
              <span>${log.comment_count ?? 0} comments</span>
            </div>
            <p>${log.decision_summary}</p>
        `;
        card.addEventListener("click", async () => {
          setHostedRouteKind("decision_log");
          controller.selectDecisionLog(log.decision_log_id);
          if (hasWorkspaceAuthInput()) {
            await controller.loadDecisionLogDetail({
              apiBaseUrl: apiBaseUrlInput.value.trim(),
              bearerToken: apiTokenInput.value.trim(),
              decisionLogId: log.decision_log_id
            });
          }
          render();
        });
        decisionLogList.appendChild(card);
      });
    }

    renderRows(selectedEvidenceViewSummary, productSurface.selected_evidence_view_summary || []);
    renderRows(selectedDecisionLogSummary, productSurface.selected_decision_log_summary || []);
    renderRows(decisionReviewSummary, productSurface.decision_review_summary || []);

    if (decisionReviewPill) {
      decisionReviewPill.className = `status-pill ${decisionReviewSurface.pill?.tone || "queued"}`;
      decisionReviewPill.textContent = decisionReviewSurface.pill?.label || "draft";
    }

    decisionCommentList.innerHTML = "";
    const decisionComments = productSurface.decision_review_comments || [];
    if (!model.state.selectedDecisionLogId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a decision log before reviewing comments or approval state.";
      decisionCommentList.appendChild(empty);
    } else if (!decisionComments.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No review comments yet for this decision.";
      decisionCommentList.appendChild(empty);
    } else {
      decisionComments.forEach((comment) => {
        const card = documentLike.createElement("div");
        card.className = "product-card";
        if (comment.indent_level) {
          card.style.marginLeft = `${comment.indent_level * 18}px`;
        }
        card.innerHTML = `
            <strong>${comment.anchor_kind}</strong>
            <div class="product-meta">
              <span>${comment.created_by_user_id || "unknown reviewer"}</span>
              <span>${comment.created_at || "unknown time"}</span>
              <span>${comment.reply_count ?? 0} replies</span>
            </div>
            <p>${comment.body}</p>
        `;
        const actions = documentLike.createElement("div");
        actions.className = "toolbar";
        const replyButton = documentLike.createElement("button");
        replyButton.type = "button";
        replyButton.className = "action-button";
        replyButton.textContent = "reply";
        replyButton.addEventListener("click", () => {
          pendingDecisionReplyCommentId = comment.decision_comment_id || "";
          updateDecisionReplyTargetPill();
        });
        actions.appendChild(replyButton);
        card.appendChild(actions);
        decisionCommentList.appendChild(card);
      });
    }
    updateDecisionReplyTargetPill();
  }

  async function openStudyActivityRoute(activityEvent) {
    const routeKind = String(activityEvent?.route_kind || "").trim();
    const routeId = String(activityEvent?.route_id || "").trim();
    if (!routeKind || !routeId) {
      return;
    }
    setHostedRouteKind(routeKind);
    if (routeKind === "study") {
      controller.selectStudy(routeId);
      await controller.loadStudyDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId: routeId
      });
      return;
    }
    if (routeKind === "job") {
      controller.selectJob(routeId);
      await controller.loadSelectedLiveJob({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim()
      });
      return;
    }
    if (routeKind === "evidence_view") {
      controller.selectEvidenceView(routeId);
      await controller.loadEvidenceViewDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        evidenceViewId: routeId
      });
      return;
    }
    if (routeKind === "decision_log") {
      controller.selectDecisionLog(routeId);
      await controller.loadDecisionLogDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        decisionLogId: routeId
      });
      return;
    }
    if (routeKind === "export_bundle") {
      controller.selectExportBundle(routeId);
      await controller.loadExportBundleDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        exportBundleId: routeId
      });
      return;
    }
    if (routeKind === "share_bundle") {
      controller.selectShareBundle(routeId);
      await controller.loadShareBundleDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        shareBundleId: routeId
      });
      return;
    }
    if (routeKind === "support_snapshot") {
      controller.selectSupportSnapshot(routeId);
      await controller.loadSupportSnapshotDetail({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        supportSnapshotId: routeId
      });
    }
  }

  function renderStudyActivity(model) {
    renderRows(studyActivitySummary, model.frontendState.product_surface.study_activity_summary || []);
    studyActivityList.innerHTML = "";
    if (!model.state.selectedStudyId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a study before loading collaboration activity.";
      studyActivityList.appendChild(empty);
      return;
    }
    const activityEvents = model.frontendState.product_surface.study_activity || [];
    if (!activityEvents.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No study activity loaded yet. Refresh the timeline to inspect cross-artifact review flow.";
      studyActivityList.appendChild(empty);
      return;
    }
    activityEvents.forEach((activityEvent) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = "product-card";
      card.innerHTML = `
          <strong>${activityEvent.headline}</strong>
          <div class="product-meta">
            <span>${activityEvent.event_family || "study"}</span>
            <span>${activityEvent.actor_user_id || "system"}</span>
            <span>${activityEvent.created_at || "unknown time"}</span>
          </div>
          <p>${activityEvent.summary}</p>
        `;
      card.disabled = !activityEvent.route_kind;
      if (activityEvent.route_kind) {
        card.addEventListener("click", async () => {
          await openStudyActivityRoute(activityEvent);
          render();
        });
      }
      studyActivityList.appendChild(card);
    });
  }

  function renderExportBundles(model) {
    exportList.innerHTML = "";
    const exportBundles = model.frontendState.product_surface.export_bundles || [];
    if (!model.state.selectedStudyId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a study before creating an export bundle.";
      exportList.appendChild(empty);
      renderRows(selectedExportSummary, model.frontendState.product_surface.selected_export_bundle_summary || []);
      return;
    }
    if (!exportBundles.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No export bundles exist yet for this study.";
      exportList.appendChild(empty);
    }
    exportBundles.forEach((exportBundle) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${exportBundle.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${exportBundle.title}</strong>
          <div class="product-meta">
            <span>${exportBundle.status}</span>
            <span>${exportBundle.export_format}</span>
            <span>${exportBundle.exported_file_count} files</span>
            <span>${exportBundle.share_bundle_count} shares</span>
          </div>
          <p>${exportBundle.job_id || "No source job recorded."}</p>
        `;
      card.addEventListener("click", async () => {
        setHostedRouteKind("export_bundle");
        controller.selectExportBundle(exportBundle.export_bundle_id);
        await controller.loadShareBundles({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          exportBundleId: exportBundle.export_bundle_id
        });
        render();
      });
      exportList.appendChild(card);
    });
    renderRows(selectedExportSummary, model.frontendState.product_surface.selected_export_bundle_summary || []);
  }

  function renderShareBundles(model) {
    shareList.innerHTML = "";
    const shareBundles = model.frontendState.product_surface.share_bundles || [];
    if (!model.state.selectedExportBundleId) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select an export bundle before creating a viewer-safe share bundle.";
      shareList.appendChild(empty);
      renderRows(selectedShareSummary, model.frontendState.product_surface.selected_share_bundle_summary || []);
      return;
    }
    if (!shareBundles.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No share bundles exist yet for this export.";
      shareList.appendChild(empty);
    }
    shareBundles.forEach((shareBundle) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${shareBundle.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${shareBundle.title}</strong>
          <div class="product-meta">
            <span>${shareBundle.status}</span>
            <span>${shareBundle.share_file_count} files</span>
          </div>
          <p>${shareBundle.public_path || "Public path not available."}</p>
        `;
      card.addEventListener("click", () => {
        setHostedRouteKind("share_bundle");
        controller.selectShareBundle(shareBundle.share_bundle_id);
        render();
      });
      shareList.appendChild(card);
    });
    renderRows(selectedShareSummary, model.frontendState.product_surface.selected_share_bundle_summary || []);
  }

  function renderSupport(model) {
    supportList.innerHTML = "";
    const supportSurface = model.frontendState.support_surface || {};
    const supportSnapshots = model.frontendState.product_surface.support_snapshots || [];
    const recentFailures = supportSurface.recent_failures || [];
    const blockedReasonCards = (supportSurface.blocked_reasons || []).map((reason) => ({
      id: reason.code,
      title: reason.code,
      body: `${reason.message}${reason.next_action ? ` | ${reason.next_action}` : ""}`,
      tone: "active"
    }));

    renderRows(supportGateSummary, supportSurface.submission_gate_summary || []);
    renderRows(supportDiagnosticSummary, supportSurface.job_diagnostic_summary || []);
    renderDetailCards(supportBlockedReasons, blockedReasonCards.length ? blockedReasonCards : [
      {
        id: "support_gate_clear",
        title: "No blocked reasons",
        body: "Submission is currently allowed, or diagnostics have not been loaded yet.",
        tone: "default"
      }
    ]);
    renderDetailCards(supportDiagnosticCards, supportSurface.job_diagnostic_cards || []);
    renderRows(selectedSupportSummary, model.frontendState.product_surface.selected_support_snapshot_summary || []);
    supportRecentFailures.innerHTML = "";
    if (!recentFailures.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No recent failed or canceled jobs are visible for this workspace yet.";
      supportRecentFailures.appendChild(empty);
    } else {
      recentFailures.forEach((job) => {
        const card = documentLike.createElement("button");
        card.type = "button";
        card.className = `product-card${job.job_id === model.state.selectedJobId ? " active" : ""}`;
        card.innerHTML = `
            <strong>${job.job_id}</strong>
            <div class="product-meta">
              <span>${job.status}</span>
              <span>${job.provider_name}</span>
              <span>retry ${job.retry_count}</span>
            </div>
            <p>${job.last_error}</p>
          `;
        card.disabled = !hasWorkspaceAuthInput();
        card.addEventListener("click", async () => {
          setHostedRouteKind("job");
          controller.selectJob(job.job_id);
          await controller.loadSelectedLiveJob({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim()
          });
          await controller.loadSupportDiagnostics({
            apiBaseUrl: apiBaseUrlInput.value.trim(),
            bearerToken: apiTokenInput.value.trim(),
            jobId: job.job_id
          });
          render();
        });
        supportRecentFailures.appendChild(card);
      });
    }

    if (!(model.state.selectedStudyId || model.state.selectedJobId)) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Select a study or run before loading support snapshots.";
      supportList.appendChild(empty);
      return;
    }

    if (!supportSnapshots.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No support snapshots have been generated yet for this scope.";
      supportList.appendChild(empty);
      return;
    }

    supportSnapshots.forEach((snapshot) => {
      const card = documentLike.createElement("button");
      card.type = "button";
      card.className = `product-card${snapshot.selected ? " active" : ""}`;
      card.innerHTML = `
          <strong>${snapshot.title}</strong>
          <div class="product-meta">
            <span>${snapshot.status}</span>
            <span>${snapshot.job_id || "no job"}</span>
          </div>
          <p>${snapshot.summary}</p>
        `;
      card.addEventListener("click", () => {
        setHostedRouteKind("support_snapshot");
        controller.selectSupportSnapshot(snapshot.support_snapshot_id);
        render();
      });
      supportList.appendChild(card);
    });
  }

  function renderSettings(model) {
    const productSurface = model.frontendState.product_surface || {};
    const workspaceSettings = model.state.liveWorkspaceSettings || null;
    const capabilities = workspaceSettings?.capabilities || {};
    const members = productSurface.workspace_members || [];
    const tokens = productSurface.workspace_api_tokens || [];

    renderRows(workspaceSettingsSummary, productSurface.workspace_settings_summary || []);
    renderRows(workspaceBillingSummary, productSurface.workspace_billing_summary || []);
    renderRows(workspacePolicySummary, productSurface.workspace_policy_summary || []);
    renderRows(workspaceAuditSummary, productSurface.workspace_audit_summary || []);
    renderRows(lastIssuedTokenSummary, productSurface.last_issued_api_token_summary || []);

    workspaceMemberList.innerHTML = "";
    if (!members.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Load workspace settings to inspect or update membership.";
      workspaceMemberList.appendChild(empty);
    } else {
      members.forEach((member) => {
        const card = documentLike.createElement("div");
        card.className = `product-card${member.current ? " active" : ""}`;
        card.innerHTML = `
            <strong>${member.user_id}</strong>
            <div class="product-meta">
              <span>${member.role}</span>
              <span>${member.joined_at || "joined time unavailable"}</span>
            </div>
            <p>${member.current ? "Current authenticated member." : "Workspace member."}</p>
          `;
        workspaceMemberList.appendChild(card);
      });
    }

    workspaceTokenList.innerHTML = "";
    if (!tokens.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "No API tokens are visible yet for this workspace.";
      workspaceTokenList.appendChild(empty);
    } else {
      tokens.forEach((token) => {
        const card = documentLike.createElement("div");
        card.className = `product-card${token.current ? " active" : ""}`;
        card.innerHTML = `
            <strong>${token.token_hint}</strong>
            <div class="product-meta">
              <span>${token.role}</span>
              <span>${token.user_id}</span>
              <span>${token.active ? "active" : "revoked"}</span>
            </div>
            <p>${token.current ? "Current authenticated token." : token.issued_at || "Issued time unavailable."}</p>
          `;
        if (capabilities.token_admin && token.active) {
          const actions = documentLike.createElement("div");
          actions.className = "toolbar";
          const revokeButton = documentLike.createElement("button");
          revokeButton.type = "button";
          revokeButton.className = "action-button";
          revokeButton.textContent = "revoke token";
          revokeButton.disabled = !hasWorkspaceAuthInput();
          revokeButton.addEventListener("click", async () => {
            await controller.revokeWorkspaceApiToken({
              apiBaseUrl: apiBaseUrlInput.value.trim(),
              bearerToken: apiTokenInput.value.trim(),
              tokenId: token.token_id
            });
            render();
          });
          actions.appendChild(revokeButton);
          card.appendChild(actions);
        }
        workspaceTokenList.appendChild(card);
      });
    }

    const auditEvents = productSurface.workspace_audit_events || [];
    workspaceAuditList.innerHTML = "";
    if (!auditEvents.length) {
      const empty = documentLike.createElement("div");
      empty.className = "product-empty";
      empty.textContent = "Load audit history to inspect workspace governance and operator events.";
      workspaceAuditList.appendChild(empty);
      return;
    }
    auditEvents.forEach((event) => {
      const card = documentLike.createElement("div");
      card.className = "product-card";
      card.innerHTML = `
          <strong>${event.action}</strong>
          <div class="product-meta">
            <span>${event.actor_user_id || "unknown actor"}</span>
            <span>${event.actor_role || "unknown role"}</span>
            <span>${event.created_at || "unknown time"}</span>
          </div>
          <p>${event.target_type || "target"}: ${event.target_id || "n/a"}</p>
          <p>${event.summary || "No event payload summary available."}</p>
        `;
      workspaceAuditList.appendChild(card);
    });
  }

  function render() {
    const model = currentModel();

    metricProject.textContent = model.frontendState.metrics.selected_project_id || "-";
    metricStudy.textContent = model.frontendState.metrics.selected_study_id || "-";
    metricShell.textContent = model.frontendState.metrics.shell_surface;
    metricRun.textContent = model.frontendState.metrics.selected_job_id || "-";

    sessionPill.className = `status-pill ${model.sessionBridgeState.pill.tone}`;
    sessionPill.textContent = model.sessionBridgeState.pill.label;
    updateHostedSessionMemoryPill();
    runtimePill.className = `status-pill ${model.runtimeSyncView.pill.tone}`;
    runtimePill.textContent = model.runtimeSyncView.pill.label;
    bridgePill.className = `status-pill ${model.frontendState.pills.bridge.tone}`;
    bridgePill.textContent = model.frontendState.pills.bridge.label;
    jobPill.className = `status-pill ${model.frontendState.pills.job.tone}`;
    jobPill.textContent = model.frontendState.pills.job.label;
    queryPill.className = `status-pill ${model.frontendState.review_surface.query_status === "query_ready" ? "completed" : "queued"}`;
    queryPill.textContent = model.frontendState.review_surface.query_status;
    const supportStatus = deriveSupportPill(model);
    supportPill.className = `status-pill ${supportStatus.tone}`;
    supportPill.textContent = supportStatus.label;
    const settingsStatus = deriveSettingsPill(model);
    settingsPill.className = `status-pill ${settingsStatus.tone}`;
    settingsPill.textContent = settingsStatus.label;

    renderRows(sessionSummary, model.sessionBridgeState.session_summary || []);
    renderRows(limitSummary, model.sessionBridgeState.limit_summary || []);
    renderRows(selectedProjectSummary, model.frontendState.product_surface.selected_project_summary || []);
    renderRows(selectedStudySummary, model.frontendState.product_surface.selected_study_summary || []);
    renderRows(draftSummary, model.frontendState.draft_summary || []);
    renderRows(adapterSummary, model.frontendState.adapter_summary || []);
    renderRows(runSummary, model.frontendState.run_monitor_summary || []);
    renderRows(reviewSummary, model.frontendState.review_summary || []);

    boundaryCopy.textContent = model.reviewQueryState?.boundary_warning
      || model.sessionBridgeState.boundary_warning
      || "Synthetic evidence remains bounded to the selected study and run.";

    lastApiJson.textContent = JSON.stringify(model.frontendState.json_panels.last_api_response, null, 2);
    requestPayloadJson.textContent = JSON.stringify(model.frontendState.json_panels.request_payload, null, 2);

    updateDraftInputs(model);
    renderStudyActions(model);
    renderProjects(model);
    renderStudies(model);
    renderJobs(model);
    renderEvidence(model);
    renderCollaboration(model);
    renderStudyActivity(model);
    renderExportBundles(model);
    renderShareBundles(model);
    renderSupport(model);
    renderSettings(model);

    submitLiveJobButton.disabled = !model.frontendState.actions.submit_live_job.enabled || !model.state.selectedStudyId;
    retrySelectedJobButton.disabled = !model.frontendState.actions.retry_selected_job.enabled;
    cancelSelectedJobButton.disabled = !model.frontendState.actions.cancel_selected_job.enabled;
    applyEvidenceQueryButton.disabled = !model.state.selectedStudyId;
    loadShellButton.disabled = !model.state.selectedStudyId;
    reloadStudiesButton.disabled = !model.state.selectedProjectId;
    createStudyButton.disabled = !model.state.selectedProjectId;
    if (forgetSavedSessionButton) {
      forgetSavedSessionButton.disabled = !(hostedRouteEnabled && (hostedSessionState.cookieSessionActive || apiTokenInput.value.trim()));
    }
    createEvidenceViewButton.disabled = !(model.state.selectedStudyId && model.state.selectedJobId);
    reloadEvidenceViewsButton.disabled = !model.state.selectedStudyId;
    createDecisionLogButton.disabled = !(model.state.selectedStudyId && decisionLogSummaryInput.value.trim());
    reloadDecisionLogsButton.disabled = !model.state.selectedStudyId;
    reloadStudyActivityButton.disabled = !model.state.selectedStudyId;
    reloadDecisionReviewButton.disabled = !(model.state.selectedDecisionLogId && hasWorkspaceAuthInput());
    requestDecisionReviewButton.disabled = !model.frontendState.actions.request_decision_review.enabled;
    approveDecisionLogButton.disabled = !model.frontendState.actions.approve_decision_log.enabled;
    requestDecisionRevisionButton.disabled = !model.frontendState.actions.request_decision_revision.enabled;
    createDecisionCommentButton.disabled = !(
      model.frontendState.actions.add_decision_comment.enabled
      && decisionCommentBodyInput.value.trim()
      && apiBaseUrlInput.value.trim()
      && hasWorkspaceAuthInput()
    );
    clearDecisionReplyTargetButton.disabled = !pendingDecisionReplyCommentId;
    createExportBundleButton.disabled = !(model.state.selectedStudyId && model.state.selectedJobId);
    reloadExportBundlesButton.disabled = !model.state.selectedStudyId;
    createShareBundleButton.disabled = !model.state.selectedExportBundleId;
    reloadShareBundlesButton.disabled = !model.state.selectedExportBundleId;
    revokeShareBundleButton.disabled = !model.state.selectedShareBundleId;
    loadSupportDiagnosticsButton.disabled = !hasWorkspaceAuthInput();
    createSupportSnapshotButton.disabled = !model.state.selectedJobId;
    reloadSupportSnapshotsButton.disabled = !(model.state.selectedStudyId || model.state.selectedJobId);
    loadWorkspaceSettingsButton.disabled = !hasWorkspaceAuthInput();
    loadAuditEventsButton.disabled = !hasWorkspaceAuthInput();
    upsertWorkspaceMemberButton.disabled = !hasWorkspaceAuthInput();
    updateWorkspaceBillingButton.disabled = !hasWorkspaceAuthInput();
    issueApiTokenButton.disabled = !hasWorkspaceAuthInput();
    toggleAutoRefreshButton.textContent = model.state.runtimeSync?.auto_refresh_enabled ? "stop auto refresh" : "start auto refresh";

    syncHostedRoute(model);
    refreshAutoSyncLoop(model);
  }

  async function refreshWorkspace() {
    await bootstrapRouteSelection();
    await hydrateWorkspace();
    if (controller.getState().selectedStudyId) {
      await performRuntimeSync();
      return;
    }
    render();
  }

  async function loadSessionOnly() {
    await controller.loadWorkspaceSession(readInputs());
    if (controller.getState().liveSession) {
      markBrowserSessionActive();
    } else if (hostedRouteEnabled) {
      hostedSessionState = {
        ...hostedSessionState,
        cookieSessionActive: false
      };
    }
    render();
  }

  async function loadWorkspaceSettingsAction() {
    await controller.loadWorkspaceSettings(readInputs());
    seedWorkspaceBillingInputs();
    render();
  }

  async function loadWorkspaceAuditEventsAction() {
    await controller.loadWorkspaceAuditEvents({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      targetType: auditTargetTypeInput.value.trim(),
      actionPrefix: auditActionPrefixInput.value.trim(),
      limit: Number(auditLimitInput.value || 20)
    });
    render();
  }

  async function upsertWorkspaceMemberAction() {
    const userId = memberUserIdInput.value.trim();
    if (!userId) {
      render();
      return;
    }
    await controller.upsertWorkspaceMember({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        user_id: userId,
        role: memberRoleSelect.value
      }
    });
    memberUserIdInput.value = "";
    render();
  }

  async function issueWorkspaceApiTokenAction() {
    const userId = tokenUserIdInput.value.trim();
    if (!userId) {
      render();
      return;
    }
    await controller.issueWorkspaceApiToken({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        user_id: userId
      }
    });
    tokenUserIdInput.value = "";
    render();
  }

  async function updateWorkspaceBillingAction() {
    await controller.updateWorkspaceBilling({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        plan_tier: billingPlanTierSelect.value,
        billing_status: billingStatusSelect.value,
        seat_count: Number(billingSeatCountInput.value || 1),
        renewal_at: billingRenewalAtInput.value.trim(),
        daily_runs: Number(quotaDailyRunsInput.value || 0),
        max_concurrent_jobs: Number(quotaConcurrentJobsInput.value || 0),
        artifact_retention_days: Number(quotaRetentionDaysInput.value || 0)
      }
    });
    seedWorkspaceBillingInputs();
    render();
  }

  async function createProject(event) {
    event.preventDefault();
    const name = projectNameInput.value.trim();
    const slug = projectSlugInput.value.trim();
    if (!name || !slug) {
      return;
    }
    await controller.createProject({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: { name, slug }
    });
    setHostedRouteKind("project");
    projectNameInput.value = "";
    projectSlugInput.value = "";
    render();
  }

  async function reloadProjects() {
    await controller.loadProjects(readInputs());
    const projectId = controller.getState().selectedProjectId;
    if (projectId) {
      await controller.loadStudies({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        projectId
      });
    }
    const studyId = controller.getState().selectedStudyId;
    if (studyId) {
      await controller.loadEvidenceViews({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadDecisionLogs({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadExportBundles({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadSupportSnapshots({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      const exportBundleId = controller.getState().selectedExportBundleId;
      if (exportBundleId) {
        await controller.loadShareBundles({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          exportBundleId
        });
      }
    }
    render();
  }

  async function createStudy(event) {
    event.preventDefault();
    const projectId = controller.getState().selectedProjectId;
    const title = studyTitleInput.value.trim();
    if (!projectId || !title) {
      return;
    }
    await controller.createStudy({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        project_id: projectId,
        title,
        research_intent: researchIntentInput.value.trim(),
        first_task: studyFirstTaskInput.value.trim()
      }
    });
    setHostedRouteKind("study");
    studyTitleInput.value = "";
    studyFirstTaskInput.value = "";
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function reloadStudies() {
    const projectId = controller.getState().selectedProjectId;
    if (!projectId) {
      render();
      return;
    }
    await controller.loadStudies({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      projectId
    });
    const studyId = controller.getState().selectedStudyId;
    if (studyId) {
      await controller.loadStudyActivity({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadEvidenceViews({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadDecisionLogs({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadExportBundles({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      await controller.loadSupportSnapshots({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        studyId
      });
      const exportBundleId = controller.getState().selectedExportBundleId;
      if (exportBundleId) {
        await controller.loadShareBundles({
          apiBaseUrl: apiBaseUrlInput.value.trim(),
          bearerToken: apiTokenInput.value.trim(),
          exportBundleId
        });
      }
    }
    render();
  }

  async function reloadExportBundles() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId) {
      render();
      return;
    }
    await controller.loadExportBundles({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId
    });
    await controller.loadSupportSnapshots({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId
    });
    const exportBundleId = controller.getState().selectedExportBundleId;
    if (exportBundleId) {
      await controller.loadShareBundles({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        exportBundleId
      });
    }
    render();
  }

  async function reloadEvidenceViews() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId) {
      render();
      return;
    }
    await controller.loadEvidenceViews({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId,
      jobId: controller.getState().selectedJobId || ""
    });
    render();
  }

  async function createEvidenceView() {
    const studyId = controller.getState().selectedStudyId;
    const jobId = controller.getState().selectedJobId;
    if (!studyId || !jobId) {
      render();
      return;
    }
    const reviewSurface = currentModel().frontendState.review_surface || {};
    await controller.createEvidenceView({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        study_id: studyId,
        job_id: jobId,
        title: evidenceViewTitleInput.value.trim(),
        note: evidenceViewNoteInput.value.trim(),
        query_text: evidenceQueryTextInput.value.trim(),
        active_family: evidenceFamilySelect.value,
        sort_by: evidenceSortSelect.value,
        selected_result_id: reviewSurface.selected_result_id || "",
        selected_replay_step_id: reviewSurface.selected_replay_step_id || "",
        selected_comparison_run_id: reviewSurface.selected_comparison_run_id || ""
      }
    });
    setHostedRouteKind("evidence_view");
    evidenceViewTitleInput.value = "";
    evidenceViewNoteInput.value = "";
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function reloadDecisionLogs() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId) {
      render();
      return;
    }
    await controller.loadDecisionLogs({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId,
      jobId: controller.getState().selectedJobId || "",
      evidenceViewId: controller.getState().selectedEvidenceViewId || ""
    });
    render();
  }

  async function reloadStudyActivity() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId) {
      render();
      return;
    }
    await controller.loadStudyActivity({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId
    });
    render();
  }

  async function refreshStudyActivityForCurrentStudy() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId || !hasWorkspaceAuthInput()) {
      return;
    }
    await controller.loadStudyActivity({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId
    });
  }

  async function createDecisionLog() {
    const studyId = controller.getState().selectedStudyId;
    if (!studyId) {
      render();
      return;
    }
    const summary = decisionLogSummaryInput.value.trim();
    if (!summary) {
      render();
      return;
    }
    const reviewSurface = currentModel().frontendState.review_surface || {};
    await controller.createDecisionLog({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        study_id: studyId,
        job_id: controller.getState().selectedJobId || "",
        evidence_view_id: controller.getState().selectedEvidenceViewId || "",
        title: decisionLogTitleInput.value.trim(),
        decision_summary: summary,
        rationale: decisionLogRationaleInput.value.trim(),
        selected_result_id: reviewSurface.selected_result_id || "",
        selected_comparison_run_id: reviewSurface.selected_comparison_run_id || ""
      }
    });
    setHostedRouteKind("decision_log");
    decisionLogTitleInput.value = "";
    decisionLogSummaryInput.value = "";
    decisionLogRationaleInput.value = "";
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function reloadDecisionReview() {
    const decisionLogId = controller.getState().selectedDecisionLogId;
    if (!decisionLogId) {
      render();
      return;
    }
    await controller.loadDecisionLogDetail({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      decisionLogId
    });
    render();
  }

  async function updateDecisionReviewStatus(reviewStatus) {
    const decisionLogId = controller.getState().selectedDecisionLogId;
    if (!decisionLogId) {
      render();
      return;
    }
    await controller.updateDecisionReviewStatus({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      decisionLogId,
      payload: {
        review_status: reviewStatus,
        note: decisionReviewNoteInput.value.trim()
      }
    });
    if (hasWorkspaceAuthInput()) {
      await controller.loadDecisionComments({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        decisionLogId
      });
    }
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function createDecisionComment() {
    const decisionLogId = controller.getState().selectedDecisionLogId;
    if (!decisionLogId) {
      render();
      return;
    }
    const body = decisionCommentBodyInput.value.trim();
    if (!body) {
      render();
      return;
    }
    await controller.createDecisionComment({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      decisionLogId,
      payload: {
        anchor_kind: decisionCommentAnchorSelect.value,
        parent_comment_id: pendingDecisionReplyCommentId,
        body
      }
    });
    decisionCommentBodyInput.value = "";
    pendingDecisionReplyCommentId = "";
    updateDecisionReplyTargetPill();
    if (hasWorkspaceAuthInput()) {
      await controller.loadDecisionComments({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        decisionLogId
      });
    }
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function createExportBundle() {
    const studyId = controller.getState().selectedStudyId;
    const jobId = controller.getState().selectedJobId;
    if (!studyId || !jobId) {
      render();
      return;
    }
    const artifactIds = exportArtifactsInput.value
      .split(",")
      .map((value) => value.trim())
      .filter((value) => value.length > 0);
    await controller.createExportBundle({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        study_id: studyId,
        job_id: jobId,
        title: exportTitleInput.value.trim(),
        export_format: exportFormatSelect.value,
        artifact_ids: artifactIds
      }
    });
    setHostedRouteKind("export_bundle");
    exportTitleInput.value = "";
    exportArtifactsInput.value = "";
    const exportBundleId = controller.getState().selectedExportBundleId;
    if (exportBundleId) {
      await controller.loadShareBundles({
        apiBaseUrl: apiBaseUrlInput.value.trim(),
        bearerToken: apiTokenInput.value.trim(),
        exportBundleId
      });
    }
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function reloadShareBundles() {
    const exportBundleId = controller.getState().selectedExportBundleId;
    if (!exportBundleId) {
      render();
      return;
    }
    await controller.loadShareBundles({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      exportBundleId
    });
    render();
  }

  async function createShareBundle() {
    const exportBundleId = controller.getState().selectedExportBundleId;
    if (!exportBundleId) {
      render();
      return;
    }
    await controller.createShareBundle({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        export_bundle_id: exportBundleId,
        title: shareTitleInput.value.trim(),
        expires_in_days: Number(shareExpiresDaysInput.value || 7)
      }
    });
    setHostedRouteKind("share_bundle");
    shareTitleInput.value = "";
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function revokeShareBundle() {
    const shareBundleId = controller.getState().selectedShareBundleId;
    if (!shareBundleId) {
      render();
      return;
    }
    await controller.revokeShareBundle({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      shareBundleId
    });
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function loadSupportDiagnostics() {
    await controller.loadSupportDiagnostics({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      jobId: controller.getState().selectedJobId || ""
    });
    render();
  }

  async function reloadSupportSnapshots() {
    if (!(controller.getState().selectedStudyId || controller.getState().selectedJobId)) {
      render();
      return;
    }
    await controller.loadSupportSnapshots({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      studyId: controller.getState().selectedStudyId || "",
      jobId: controller.getState().selectedJobId || ""
    });
    render();
  }

  async function createSupportSnapshot() {
    const jobId = controller.getState().selectedJobId;
    if (!jobId) {
      render();
      return;
    }
    await controller.createSupportSnapshot({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      payload: {
        job_id: jobId,
        title: supportSnapshotTitleInput.value.trim(),
        notes: supportSnapshotNotesInput.value.trim(),
        metadata: {
          source: "stage15_demo"
        }
      }
    });
    setHostedRouteKind("support_snapshot");
    supportSnapshotTitleInput.value = "";
    supportSnapshotNotesInput.value = "";
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function submitLiveJob() {
    await controller.submitLiveJob(readInputs());
    setHostedRouteKind("job");
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function retrySelectedJob() {
    await controller.retrySelectedJob(readInputs());
    setHostedRouteKind("job");
    await controller.loadSupportDiagnostics({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      jobId: controller.getState().selectedJobId || ""
    });
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function cancelSelectedJob() {
    await controller.cancelSelectedJob({
      ...readInputs(),
      reason: "Canceled from the Stage 15 product shell before worker lease."
    });
    setHostedRouteKind("job");
    await controller.loadSupportDiagnostics({
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      bearerToken: apiTokenInput.value.trim(),
      jobId: controller.getState().selectedJobId || ""
    });
    await refreshStudyActivityForCurrentStudy();
    render();
  }

  async function applyEvidenceQuery() {
    const model = currentModel();
    if (model.state.mode === "live" && model.state.selectedJobId) {
      await performRuntimeSync({
        selectedResultId: "",
        selectedReplayStepId: "",
        selectedComparisonRunId: ""
      });
      return;
    }
    controller.clearLocalEvidenceQuery();
    render();
  }

  function bindTextInput(node, updater) {
    node.addEventListener("input", () => {
      updater(node.value);
      render();
    });
  }

  bindTextInput(researchIntentInput, (value) => controller.updateDraftInput({ researchIntent: value }));
  bindTextInput(desiredOutcomeInput, (value) => controller.updateDraftInput({ desiredOutcome: value }));
  bindTextInput(firstTaskInput, (value) => controller.updateDraftInput({ firstTask: value }));

  artifactFilesInput.addEventListener("change", () => {
    controller.setPrototypeArtifacts(Array.from(artifactFilesInput.files || []).map((file) => file.name));
    render();
  });

  [
    apiBaseUrlInput,
    apiTokenInput,
    briefPathInput,
    personaDirInput,
    sampleSizeInput,
    evidenceQueryTextInput,
    evidenceViewTitleInput,
    evidenceViewNoteInput,
    decisionLogTitleInput,
    decisionLogSummaryInput,
    decisionLogRationaleInput,
    decisionReviewNoteInput,
    decisionCommentBodyInput
  ].forEach((node) => node.addEventListener("input", render));

  [
    modeOverrideSelect,
    panelTypeSelect,
    providerNameSelect,
    personaFilterLocationSelect,
    personaFilterPrivacySelect,
    evidenceFamilySelect,
    evidenceSortSelect,
    decisionCommentAnchorSelect
  ].forEach((node) => node.addEventListener("change", render));

  projectForm.addEventListener("submit", createProject);
  studyForm.addEventListener("submit", createStudy);
  refreshWorkspaceButton.addEventListener("click", refreshWorkspace);
  loadSessionButton.addEventListener("click", loadSessionOnly);
  forgetSavedSessionButton?.addEventListener("click", forgetHostedSessionIfPossible);
  loadWorkspaceSettingsButton.addEventListener("click", loadWorkspaceSettingsAction);
  loadAuditEventsButton.addEventListener("click", loadWorkspaceAuditEventsAction);
  updateWorkspaceBillingButton.addEventListener("click", updateWorkspaceBillingAction);
  loadShellButton.addEventListener("click", () => performRuntimeSync());
  reloadProjectsButton.addEventListener("click", reloadProjects);
  reloadStudiesButton.addEventListener("click", reloadStudies);
  createEvidenceViewButton.addEventListener("click", createEvidenceView);
  reloadEvidenceViewsButton.addEventListener("click", reloadEvidenceViews);
  reloadStudyActivityButton.addEventListener("click", reloadStudyActivity);
  createDecisionLogButton.addEventListener("click", createDecisionLog);
  reloadDecisionLogsButton.addEventListener("click", reloadDecisionLogs);
  reloadDecisionReviewButton.addEventListener("click", reloadDecisionReview);
  requestDecisionReviewButton.addEventListener("click", () => updateDecisionReviewStatus("in_review"));
  approveDecisionLogButton.addEventListener("click", () => updateDecisionReviewStatus("approved"));
  requestDecisionRevisionButton.addEventListener("click", () => updateDecisionReviewStatus("needs_revision"));
  createDecisionCommentButton.addEventListener("click", createDecisionComment);
  clearDecisionReplyTargetButton.addEventListener("click", () => {
    pendingDecisionReplyCommentId = "";
    updateDecisionReplyTargetPill();
    render();
  });
  reloadExportBundlesButton.addEventListener("click", reloadExportBundles);
  reloadShareBundlesButton.addEventListener("click", reloadShareBundles);
  submitLiveJobButton.addEventListener("click", submitLiveJob);
  retrySelectedJobButton.addEventListener("click", retrySelectedJob);
  cancelSelectedJobButton.addEventListener("click", cancelSelectedJob);
  createExportBundleButton.addEventListener("click", createExportBundle);
  createShareBundleButton.addEventListener("click", createShareBundle);
  revokeShareBundleButton.addEventListener("click", revokeShareBundle);
  loadSupportDiagnosticsButton.addEventListener("click", loadSupportDiagnostics);
  reloadSupportSnapshotsButton.addEventListener("click", reloadSupportSnapshots);
  createSupportSnapshotButton.addEventListener("click", createSupportSnapshot);
  upsertWorkspaceMemberButton.addEventListener("click", upsertWorkspaceMemberAction);
  issueApiTokenButton.addEventListener("click", issueWorkspaceApiTokenAction);
  useSampleJobsButton.addEventListener("click", () => {
    controller.useSampleJobs();
    render();
  });
  applyEvidenceQueryButton.addEventListener("click", applyEvidenceQuery);
  toggleAutoRefreshButton.addEventListener("click", () => {
    controller.toggleRuntimeAutoRefresh();
    render();
  });
  windowLike.addEventListener("beforeunload", stopAutoRefresh);

  controller.reset();
  render();
  refreshWorkspace().catch(() => render());

  return {
    controller,
    readInputs,
    render,
    refreshWorkspace,
    stopAutoRefresh,
    currentModel
  };
}
