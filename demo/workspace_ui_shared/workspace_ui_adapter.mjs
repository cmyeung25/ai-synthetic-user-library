function compactStrings(values) {
  return [...new Set((values || []).filter((value) => typeof value === "string" && value.trim().length > 0))];
}

function normalizeSampleSize(value, fallback = 5) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  const rounded = Math.max(1, Math.round(numeric));
  return rounded;
}

function normalizeModeOverride(value) {
  const normalized = String(value || "").trim();
  return normalized && normalized !== "auto" ? normalized : null;
}

function normalizePersonaFilters(filters = {}) {
  const nextFilters = {};
  Object.entries(filters || {}).forEach(([key, value]) => {
    const normalized = String(value || "").trim();
    if (normalized) {
      nextFilters[key] = normalized;
    }
  });
  return nextFilters;
}

function summarizePersonaFilters(filters = {}) {
  const entries = Object.entries(normalizePersonaFilters(filters));
  if (!entries.length) {
    return "none";
  }
  return entries.map(([key, value]) => `${key}=${value}`).join(", ");
}

function inferRunState(draftPlan) {
  const executionStatus = draftPlan?.proposed_run?.execution_status;
  const draftStatus = draftPlan?.status;
  const confirmationStatus = draftPlan?.confirmation?.status;

  if (executionStatus === "completed") {
    return "completed";
  }
  if (executionStatus === "failed") {
    return "failed";
  }
  if (
    executionStatus === "queued" ||
    executionStatus === "leased" ||
    executionStatus === "running" ||
    executionStatus === "retrying" ||
    draftStatus === "confirmed" ||
    confirmationStatus === "confirmed"
  ) {
    return "queued";
  }
  return "draft";
}

function inferUiPhase({ draftPlan, runState, hasBlocking, savedForLater }) {
  if (runState === "queued" || runState === "completed" || runState === "failed") {
    return "queued";
  }
  if (savedForLater) {
    return "blocked_saved";
  }
  if (!hasBlocking && draftPlan?.confirmation?.required !== false) {
    return "ready_for_confirmation";
  }
  return "blocked";
}

function buildWaitingFor({ remediation, uiPhase, runState }) {
  const waiting = [
    ...(remediation?.required_artifacts || []),
    ...(remediation?.missing_inputs || [])
  ];

  if (uiPhase === "ready_for_confirmation") {
    waiting.push("final_confirmation");
  } else if (runState === "queued") {
    waiting.push("worker_execution");
  } else if (runState === "completed") {
    waiting.push("results_review");
  } else if (runState === "failed") {
    waiting.push("failure_review");
  } else if (uiPhase === "blocked_saved") {
    waiting.push("later_resume");
  }

  return compactStrings(waiting);
}

function buildPrimaryButton({ uiPhase, remediation, draftPlan, visibleWaitingFor, runState }) {
  const recommended = remediation?.recommended_next_action || {};

  if (runState === "completed") {
    return {
      label: recommended.label || "view_results",
      action_type: recommended.action_type || "view_results",
      enabled: true
    };
  }

  if (runState === "failed") {
    return {
      label: recommended.label || "inspect_failure",
      action_type: recommended.action_type || "inspect_failure",
      enabled: true
    };
  }

  if (uiPhase === "queued") {
    return {
      label: recommended.label || "queued",
      action_type: recommended.action_type || "await_run",
      enabled: true
    };
  }

  if (uiPhase === "blocked_saved") {
    return {
      label: recommended.label || "resume_later",
      action_type: recommended.action_type || "resume_blocked_draft",
      enabled: true
    };
  }

  if (uiPhase === "ready_for_confirmation") {
    return {
      label: recommended.label || "confirm_queueable_plan",
      action_type: recommended.action_type || "confirm_queueable_plan",
      enabled: true
    };
  }

  return {
    label: recommended.label || "request_missing_inputs",
    action_type: recommended.action_type || "request_artifact_upload_and_clarification",
    enabled: visibleWaitingFor.length > 0 || remediation?.blocking_reasons?.length > 0
  };
}

function buildSecondaryButton(uiPhase) {
  if (uiPhase === "queued") {
    return {
      label: "view_queue_status",
      action_type: "view_queue_status",
      enabled: true
    };
  }

  if (uiPhase === "blocked_saved") {
    return {
      label: "keep_blocked_draft",
      action_type: "keep_blocked_draft",
      enabled: true
    };
  }

  if (uiPhase === "ready_for_confirmation") {
    return {
      label: "return_to_conversation",
      action_type: "return_to_conversation",
      enabled: true
    };
  }

  return {
    label: "save_blocked_draft",
    action_type: "save_blocked_draft",
    enabled: true
  };
}

export function deriveWorkspaceUiState({
  conversationState,
  draftPlan,
  localUiState = {}
}) {
  const remediation = draftPlan?.remediation || {};
  const visibleBlockers = compactStrings(remediation.blocking_reasons);
  const savedForLater = Boolean(
    remediation.saved_for_later ||
    draftPlan?.audit?.saved_for_later ||
    draftPlan?.confirmation?.status === "saved_for_later"
  );
  const hasBlocking = visibleBlockers.length > 0;
  const runState = inferRunState(draftPlan);
  const uiPhase = inferUiPhase({ draftPlan, runState, hasBlocking, savedForLater });
  const visibleWaitingFor = buildWaitingFor({ remediation, uiPhase, runState });
  const primaryButton = buildPrimaryButton({ uiPhase, remediation, draftPlan, visibleWaitingFor, runState });
  const secondaryButton = buildSecondaryButton(uiPhase);
  const boundaryNote = draftPlan?.evidence_boundary?.boundary_note || null;

  return {
    ui_phase: uiPhase,
    run_state: runState,
    visible_blockers: visibleBlockers,
    visible_waiting_for: visibleWaitingFor,
    primary_button: primaryButton,
    secondary_button: secondaryButton,
    summary_view: {
      primary_mode: draftPlan?.inference?.primary_mode || null,
      execution_status: draftPlan?.proposed_run?.execution_status || null,
      first_task: draftPlan?.proposed_run?.first_task || null
    },
    sidecar_view: {
      status: uiPhase,
      waiting_for: visibleWaitingFor,
      primary_action_copy: primaryButton.label,
      boundary_warning: boundaryNote
    },
    adapter_meta: {
      locale: localUiState?.locale || "en",
      active_panel: localUiState?.active_panel || "default",
      source_thread: conversationState?.thread_id || null
    }
  };
}

export function createStage7DemoState() {
  return {
    hasScreenshots: false,
    attachedArtifacts: [],
    firstTask: null,
    fallbackChosen: false,
    savedBlocked: false,
    panelType: "mainstream",
    sampleSize: 5,
    providerName: "mock",
    modeOverride: null,
    personaFilters: {},
    queueConfirmed: false,
    events: [{ type: "reset", at: "21:46" }]
  };
}

function buildRunMonitorActions(status) {
  if (status === "ready_to_queue") {
    return {
      primary_action_type: "confirm_and_queue",
      secondary_action_type: "review_plan"
    };
  }
  if (status === "queued") {
    return {
      primary_action_type: "lease_worker",
      secondary_action_type: "view_queue_status"
    };
  }
  if (status === "leased") {
    return {
      primary_action_type: "start_run",
      secondary_action_type: "release_job"
    };
  }
  if (status === "running") {
    return {
      primary_action_type: "complete_run",
      secondary_action_type: "fail_run"
    };
  }
  if (status === "completed") {
    return {
      primary_action_type: "view_results",
      secondary_action_type: "open_artifacts"
    };
  }
  if (status === "failed") {
    return {
      primary_action_type: "inspect_failure",
      secondary_action_type: "retry_run"
    };
  }
  return {
    primary_action_type: "review_plan",
    secondary_action_type: "reset_demo"
  };
}

function buildTimeline(status) {
  const order = ["queued", "leased", "running", "completed"];
  const activeIndex = status === "failed"
    ? order.indexOf("running")
    : status === "ready_to_queue"
      ? -1
      : order.indexOf(status);

  return order.map((step, index) => {
    let state = "pending";
    if (activeIndex > index || (status === "completed" && step === "completed")) {
      state = "done";
    }
    if (activeIndex === index && status !== "completed") {
      state = "active";
    }
    if (status === "failed" && step === "running") {
      state = "active";
    }
    return { step, state };
  });
}

export function deriveWorkspaceRunMonitorState({
  draftPlan,
  runRecord,
  localUiState = {}
}) {
  const status = runRecord?.status || "ready_to_queue";
  const actions = buildRunMonitorActions(status);
  const timeline = buildTimeline(status);
  const pillClass = status === "leased"
    ? "running"
    : status === "ready_to_queue"
      ? "queued"
      : status;

  return {
    status,
    pill_class: pillClass,
    monitor_phase: status === "ready_to_queue"
      ? "pre_queue"
      : status === "queued" || status === "leased"
        ? "worker_wait"
        : status === "running"
          ? "worker_active"
          : status === "completed"
            ? "results_ready"
            : "retry_required",
    queue_position: runRecord?.queue_position ?? null,
    worker_id: runRecord?.worker_id || null,
    current_step: runRecord?.current_step || null,
    attempt_count: runRecord?.attempt_count ?? 0,
    last_event_at: runRecord?.last_event_at || null,
    failure_reason: runRecord?.failure_reason || null,
    retry_available: status === "failed",
    results_available: status === "completed",
    artifact_refs: runRecord?.artifact_refs || [],
    timeline,
    primary_action_type: actions.primary_action_type,
    secondary_action_type: actions.secondary_action_type,
    adapter_run_state: inferRunState(draftPlan),
    locale: localUiState?.locale || "en"
  };
}

export function deriveStage7DemoBundle({
  demoState,
  copy,
  localUiState = {}
}) {
  const attachedArtifacts = Array.isArray(demoState.attachedArtifacts)
    ? demoState.attachedArtifacts.filter((value) => String(value || "").trim().length > 0)
    : [];
  const conversationState = {
    workspace_id: "ws_hk_ops",
    thread_id: "thread_workspace_new_study",
    latest_user_intent: copy.questionValue,
    artifact_refs: compactStrings([
      "founder-brief.json",
      "homepage-copy.md",
      ...(demoState.hasScreenshots
        ? (attachedArtifacts.length ? attachedArtifacts : ["onboarding-screens.zip"])
        : [])
    ]),
    clarification_answers: demoState.firstTask ? { first_task_name: demoState.firstTask } : {},
    selected_fallback: demoState.fallbackChosen ? "concept_evaluation" : null
  };

  const queueableFallback = demoState.fallbackChosen && !demoState.queueConfirmed;
  const queueablePrototype = demoState.hasScreenshots && Boolean(demoState.firstTask) && !demoState.queueConfirmed;

  const modeOverride = normalizeModeOverride(demoState.modeOverride);
  const panelType = String(demoState.panelType || "").trim() || "mainstream";
  const sampleSize = normalizeSampleSize(demoState.sampleSize, 5);
  const providerName = String(demoState.providerName || "").trim() || "mock";
  const personaFilters = normalizePersonaFilters(demoState.personaFilters);
  const primaryMode = modeOverride || (queueableFallback ? "concept_evaluation" : "prototype_validation");
  const executionStatus = demoState.queueConfirmed
    ? "queued"
    : queueableFallback
      ? "queueable_fallback"
      : queueablePrototype
        ? "queueable_prototype_subset"
        : "blocked";

  const allowedEvidence = queueableFallback
    ? ["message_interpretation", "concept_objections"]
    : queueablePrototype
      ? ["task_friction", "continuation_risk", "message_interpretation"]
      : ["message_interpretation"];

  const forbiddenClaims = queueableFallback
    ? ["task_friction", "observed_continuation"]
    : queueablePrototype
      ? ["observed_real_user_behavior"]
      : ["task_friction", "observed_continuation"];

  const blockingReasons = [];
  const missingInputs = [];
  const requiredArtifacts = [];

  if (!demoState.hasScreenshots && !demoState.fallbackChosen) {
    blockingReasons.push("missing_prototype_artifacts");
    requiredArtifacts.push("onboarding_screenshot_set");
  }

  if (!demoState.firstTask && !demoState.fallbackChosen) {
    blockingReasons.push("missing_first_task_anchor");
    missingInputs.push("first_task_name");
  }

  let recommendedNextAction = {
    action_type: "request_artifact_upload_and_clarification",
    label: copy.nextUpload
  };

  if (queueableFallback) {
    recommendedNextAction = {
      action_type: "confirm_fallback_mode",
      label: copy.nextFallback
    };
  } else if (queueablePrototype) {
    recommendedNextAction = {
      action_type: "confirm_queueable_plan",
      label: copy.nextConfirm
    };
  }

  if (demoState.savedBlocked && !demoState.queueConfirmed) {
    recommendedNextAction = {
      action_type: "resume_blocked_draft",
      label: copy.nextSaved
    };
  }

  if (demoState.queueConfirmed) {
    recommendedNextAction = {
      action_type: "await_run",
      label: copy.phaseQueued
    };
  }

  const remediation = {
    blocking_reasons: queueableFallback || queueablePrototype ? [] : blockingReasons,
    missing_inputs: queueableFallback || queueablePrototype ? [] : missingInputs,
    required_artifacts: queueableFallback || queueablePrototype ? [] : requiredArtifacts,
    fallback_options: ["downgrade_to_concept_review", "save_blocked_draft"],
    recommended_next_action: recommendedNextAction,
    saved_for_later: Boolean(demoState.savedBlocked && !demoState.queueConfirmed)
  };

  const draftPlan = {
    draft_plan_id: demoState.draftPlanId || "draft_plan_20260627_proto_07",
    status: demoState.queueConfirmed
      ? "confirmed"
      : queueableFallback || queueablePrototype
        ? "ready_for_confirmation"
        : "blocked",
    source_intent: {
      user_text: copy.questionValue,
      requested_outcome: copy.desiredValue
    },
    artifact_refs: conversationState.artifact_refs.map((path) => ({ path })),
    inference: {
      primary_mode: primaryMode,
      secondary_lenses: ["onboarding_friction", "continuation_risk"]
    },
    proposed_run: {
      primary_mode: primaryMode,
      first_task: demoState.firstTask,
      mode_override: modeOverride,
      panel_type: panelType,
      sample_size: sampleSize,
      provider_name: providerName,
      persona_filters: personaFilters,
      execution_status: executionStatus
    },
    evidence_boundary: {
      allowed_evidence: allowedEvidence,
      forbidden_claims: forbiddenClaims,
      boundary_note: queueableFallback
        ? "Fallback lowers the study to concept-level interpretation until stronger prototype evidence exists."
        : queueablePrototype
          ? "This path is queueable for prototype-oriented interpretation, but it still does not claim real observed user behavior."
          : "Prototype evidence still needs stronger artifacts before the workspace should claim task-friction signal."
    },
    advanced_controls: {
      mode_override_available: true,
      persona_filters_available: true,
      provider_override_available: true,
      selected_overrides: {
        mode_override: modeOverride,
        panel_type: panelType,
        sample_size: sampleSize,
        provider_name: providerName,
        persona_filters: personaFilters
      },
      summary: {
        mode: modeOverride || "auto",
        panel: `${panelType}:${sampleSize}`,
        filters: summarizePersonaFilters(personaFilters),
        provider: providerName
      }
    },
    remediation,
    confirmation: {
      required: true,
      status: demoState.queueConfirmed
        ? "confirmed"
        : demoState.savedBlocked
          ? "saved_for_later"
          : "pending",
      blocking_reasons: remediation.blocking_reasons
    },
    audit: {
      inferred_by: "workspace_ui_stage7_demo",
      contract_version: "workspace-research-plan/v0-draft",
      saved_for_later: remediation.saved_for_later,
      submission_key: demoState.submissionKey || null,
      confirmed_at: demoState.confirmedAt || null
    }
  };

  const adapter = deriveWorkspaceUiState({
    conversationState,
    draftPlan,
    localUiState
  });

  return {
    conversation: conversationState,
    draft: draftPlan,
    remediation,
    adapter
  };
}

export function createStage8MonitorDemoState() {
  return {
    lifecycle: "ready_to_queue",
    attemptCount: 0,
    failureReason: null,
    events: [{ type: "reset", at: "22:12" }]
  };
}

export function deriveStage8MonitorBundle({
  monitorState,
  copy,
  localUiState = {}
}) {
  const baseStage7State = {
    hasScreenshots: true,
    firstTask: copy.firstTaskValue,
    fallbackChosen: false,
    savedBlocked: false,
    queueConfirmed: monitorState.lifecycle !== "ready_to_queue",
    events: []
  };

  const baseBundle = deriveStage7DemoBundle({
    demoState: baseStage7State,
    copy,
    localUiState
  });

  const runRecord = {
    job_id: "job_workspace_proto_008",
    status: monitorState.lifecycle,
    queue_position: monitorState.lifecycle === "ready_to_queue" ? null : 1,
    worker_id: monitorState.lifecycle === "leased" || monitorState.lifecycle === "running" || monitorState.lifecycle === "completed" || monitorState.lifecycle === "failed"
      ? "worker-hkg-02"
      : null,
    current_step: monitorState.lifecycle === "running"
      ? "persona_panel_execution"
      : monitorState.lifecycle === "completed"
        ? "report_packaging"
        : monitorState.lifecycle === "failed"
          ? "stimulus_render"
          : null,
    attempt_count: monitorState.attemptCount,
    last_event_at: monitorState.events[0]?.at || null,
    failure_reason: monitorState.failureReason,
    artifact_refs: monitorState.lifecycle === "completed"
      ? [
          "runs/job_workspace_proto_008/report.json",
          "runs/job_workspace_proto_008/summary.md",
          "runs/job_workspace_proto_008/trace.json"
        ]
      : []
  };

  if (monitorState.lifecycle === "leased" || monitorState.lifecycle === "running") {
    baseBundle.draft.proposed_run.execution_status = monitorState.lifecycle;
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "await_run",
      label: copy.monitorAwait
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run is active. Review intermediate status, but do not treat partial worker progress as completed evidence.";
  } else if (monitorState.lifecycle === "completed") {
    baseBundle.draft.proposed_run.execution_status = "completed";
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "view_results",
      label: copy.monitorViewResults
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run artifacts are ready for operator review, but the evidence remains synthetic and bounded by the current prototype-validation contract.";
  } else if (monitorState.lifecycle === "failed") {
    baseBundle.draft.proposed_run.execution_status = "failed";
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "inspect_failure",
      label: copy.monitorInspectFailure
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run failed before artifact completion. Operators should review the failure cause before retrying.";
  }

  if (monitorState.lifecycle !== "ready_to_queue") {
    baseBundle.draft.status = "confirmed";
    baseBundle.draft.confirmation.status = "confirmed";
    baseBundle.draft.audit.saved_for_later = false;
    baseBundle.adapter = deriveWorkspaceUiState({
      conversationState: baseBundle.conversation,
      draftPlan: baseBundle.draft,
      localUiState
    });
  }

  const runMonitor = deriveWorkspaceRunMonitorState({
    draftPlan: baseBundle.draft,
    runRecord,
    localUiState
  });

  return {
    ...baseBundle,
    run_record: runRecord,
    run_monitor: runMonitor
  };
}

function filterEvidenceArtifacts(artifacts, activeFilter) {
  if (activeFilter === "all") {
    return artifacts;
  }
  return artifacts.filter((artifact) => artifact.family === activeFilter);
}

function pickSelectedArtifact(artifacts, selectedArtifactId) {
  if (!artifacts.length) {
    return null;
  }
  return artifacts.find((artifact) => artifact.id === selectedArtifactId) || artifacts[0];
}

function pickReplayFocus(selectedArtifact, selectedReplayStepId) {
  const replaySteps = selectedArtifact?.replay_steps || [];
  if (!replaySteps.length) {
    return {
      replay_sequence: [],
      replay_focus_step: null
    };
  }
  return {
    replay_sequence: replaySteps,
    replay_focus_step: replaySteps.find((step) => step.id === selectedReplayStepId) || replaySteps[0]
  };
}

export function deriveWorkspaceEvidenceBrowserState({
  draftPlan,
  runRecord,
  evidenceCatalog = [],
  localUiState = {}
}) {
  const runState = inferRunState(draftPlan);
  const browserStatus = runState === "completed" ? "results_ready" : "results_pending";
  const activeFilter = localUiState?.active_filter || "all";
  const visibleArtifacts = browserStatus === "results_ready"
    ? filterEvidenceArtifacts(evidenceCatalog, activeFilter)
    : [];
  const selectedArtifact = pickSelectedArtifact(visibleArtifacts, localUiState?.selected_artifact_id);
  const replay = pickReplayFocus(selectedArtifact, localUiState?.selected_replay_step_id);

  return {
    browser_status: browserStatus,
    active_filter: activeFilter,
    available_filters: ["all", "input", "trace", "analysis", "output"],
    visible_count: visibleArtifacts.length,
    selected_artifact_id: selectedArtifact?.id || null,
    selected_replay_step_id: replay.replay_focus_step?.id || null,
    visible_artifacts: visibleArtifacts.map((artifact) => ({
      id: artifact.id,
      title: artifact.title,
      family: artifact.family,
      kind: artifact.kind,
      artifact_path: artifact.artifact_path,
      summary: artifact.summary,
      tags: artifact.tags || []
    })),
    selected_artifact: selectedArtifact,
    replay_sequence: replay.replay_sequence,
    replay_focus_step: replay.replay_focus_step,
    artifact_count_by_family: {
      input: evidenceCatalog.filter((artifact) => artifact.family === "input").length,
      trace: evidenceCatalog.filter((artifact) => artifact.family === "trace").length,
      analysis: evidenceCatalog.filter((artifact) => artifact.family === "analysis").length,
      output: evidenceCatalog.filter((artifact) => artifact.family === "output").length
    },
    boundary_warning: draftPlan?.evidence_boundary?.boundary_note || null,
    locale: localUiState?.locale || "en"
  };
}

export function createStage9EvidenceDemoState() {
  return {
    activeFilter: "all",
    selectedArtifactId: "artifact-trace",
    selectedReplayStepId: "step-03"
  };
}

export function createWorkspaceEvidenceCatalog() {
  return [
    {
      id: "artifact-input-brief",
      title: "Founder brief",
      family: "input",
      kind: "context",
      artifact_path: "briefs/founder-brief.json",
      summary: "Original study framing, market context, and trust-risk assumptions used for the run.",
      tags: ["source", "context"],
      detail_lines: [
        "Problem framing: onboarding hesitation and post-first-task continuation.",
        "Audience: Hong Kong SMB operators.",
        "Evidence target: task friction and continuation risk."
      ],
      replay_steps: []
    },
    {
      id: "artifact-input-stimulus",
      title: "Onboarding screenshot set",
      family: "input",
      kind: "stimulus",
      artifact_path: "stimulus/onboarding-screens.zip",
      summary: "Static onboarding screens reviewed before the persona panel was executed.",
      tags: ["stimulus", "screenshots"],
      detail_lines: [
        "Three screen capture set used for prototype-oriented interpretation.",
        "Supports comprehension and friction inference, not real user observation."
      ],
      replay_steps: []
    },
    {
      id: "artifact-trace",
      title: "Observed action trace",
      family: "trace",
      kind: "observed_action_trace",
      artifact_path: "runs/job_workspace_proto_008/trace.json",
      summary: "Structured task-path trace with hesitation, backtracking, and final submit path.",
      tags: ["trace", "replay"],
      detail_lines: [
        "Trace shows the persona revisiting permissions before completing the connect-data task.",
        "One hesitation loop appears before the final confirmation action."
      ],
      replay_steps: [
        {
          id: "step-01",
          title: "Landing screen scanned",
          timestamp: "00:00",
          note: "Participant reads the promise and looks for setup cost."
        },
        {
          id: "step-02",
          title: "Permissions panel opened",
          timestamp: "00:16",
          note: "Trust concern appears when data access becomes explicit."
        },
        {
          id: "step-03",
          title: "Connect-data task hesitates",
          timestamp: "00:28",
          note: "Backtracking begins after uncertainty about reversibility."
        },
        {
          id: "step-04",
          title: "Task resumed and completed",
          timestamp: "00:51",
          note: "Completion follows only after the operator finds a clear fallback path."
        }
      ]
    },
    {
      id: "artifact-analysis",
      title: "Stimulus analysis",
      family: "analysis",
      kind: "stimulus_analysis",
      artifact_path: "runs/job_workspace_proto_008/stimulus_analysis.json",
      summary: "Screen-level interpretation of wording confusion, trust burden, and likely hesitation points.",
      tags: ["analysis", "stimulus"],
      detail_lines: [
        "Primary confusion: permissions language feels high-cost too early.",
        "Primary trust gap: unclear reversibility before connect-data action."
      ],
      replay_steps: [
        {
          id: "analysis-01",
          title: "Trust burden identified",
          timestamp: "screen-02",
          note: "Permission copy reads as high-stakes before value is proven."
        },
        {
          id: "analysis-02",
          title: "Reversibility gap identified",
          timestamp: "screen-03",
          note: "The interface does not foreground what happens after connection."
        }
      ]
    },
    {
      id: "artifact-output-report",
      title: "Run report",
      family: "output",
      kind: "report",
      artifact_path: "runs/job_workspace_proto_008/report.json",
      summary: "Final synthetic evidence package for review, including friction synthesis and continuation risk summary.",
      tags: ["output", "report"],
      detail_lines: [
        "Likely hesitation concentrates around permission cost and unclear reversibility.",
        "Continuation risk drops when the first-task payoff becomes explicit."
      ],
      replay_steps: [
        {
          id: "report-01",
          title: "Risk summary",
          timestamp: "report",
          note: "Continuation risk remains medium until the first-task payoff is shown clearly."
        }
      ]
    },
    {
      id: "artifact-output-summary",
      title: "Markdown summary",
      family: "output",
      kind: "summary",
      artifact_path: "runs/job_workspace_proto_008/summary.md",
      summary: "Human-readable summary for operator review and sharing inside the workspace.",
      tags: ["output", "summary"],
      detail_lines: [
        "Best used for quick operator review, not as the machine-readable source of truth."
      ],
      replay_steps: []
    }
  ];
}

export function deriveStage9EvidenceBundle({
  evidenceState,
  copy,
  localUiState = {}
}) {
  const baseBundle = deriveStage8MonitorBundle({
    monitorState: {
      lifecycle: "completed",
      attemptCount: 1,
      failureReason: null,
      events: [{ type: "completed", at: "22:19" }]
    },
    copy,
    localUiState
  });

  const evidenceCatalog = createWorkspaceEvidenceCatalog();

  const evidenceBrowser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: baseBundle.draft,
    runRecord: baseBundle.run_record,
    evidenceCatalog,
    localUiState: {
      ...localUiState,
      active_filter: evidenceState.activeFilter,
      selected_artifact_id: evidenceState.selectedArtifactId,
      selected_replay_step_id: evidenceState.selectedReplayStepId
    }
  });

  return {
    ...baseBundle,
    evidence_catalog: evidenceCatalog,
    evidence_browser: evidenceBrowser
  };
}

function normalizeQueryText(value) {
  return (value || "").trim().toLowerCase();
}

function buildEvidenceQueryIndex(evidenceCatalog) {
  return evidenceCatalog.map((artifact, index) => ({
    id: `query-${artifact.id}`,
    artifact_id: artifact.id,
    title: artifact.title,
    family: artifact.family,
    kind: artifact.kind,
    artifact_path: artifact.artifact_path,
    summary: artifact.summary,
    tags: artifact.tags || [],
    replay_step_titles: (artifact.replay_steps || []).map((step) => step.title),
    detail_lines: artifact.detail_lines || [],
    sort_timestamp: 1000 - index
  }));
}

function computeQueryScore(record, queryText) {
  if (!queryText) {
    return 1;
  }

  let score = 0;
  const haystacks = [
    record.title,
    record.summary,
    record.family,
    record.kind,
    record.artifact_path,
    ...record.tags,
    ...record.replay_step_titles,
    ...record.detail_lines
  ].map((value) => String(value || "").toLowerCase());

  haystacks.forEach((value) => {
    if (value.includes(queryText)) {
      score += 1;
    }
  });

  return score;
}

function sortQueryResults(results, sortBy) {
  const items = [...results];
  if (sortBy === "family") {
    items.sort((a, b) => `${a.family}:${a.title}`.localeCompare(`${b.family}:${b.title}`));
    return items;
  }
  if (sortBy === "newest") {
    items.sort((a, b) => b.sort_timestamp - a.sort_timestamp);
    return items;
  }
  items.sort((a, b) => {
    if (b.relevance_score !== a.relevance_score) {
      return b.relevance_score - a.relevance_score;
    }
    return b.sort_timestamp - a.sort_timestamp;
  });
  return items;
}

function buildFacetCounts(indexRecords) {
  return {
    all: indexRecords.length,
    input: indexRecords.filter((record) => record.family === "input").length,
    trace: indexRecords.filter((record) => record.family === "trace").length,
    analysis: indexRecords.filter((record) => record.family === "analysis").length,
    output: indexRecords.filter((record) => record.family === "output").length
  };
}

export function deriveWorkspaceEvidenceQueryState({
  draftPlan,
  runRecord,
  evidenceCatalog = [],
  localUiState = {}
}) {
  const runState = inferRunState(draftPlan);
  const queryStatus = runState === "completed" ? "query_ready" : "query_pending";
  const indexRecords = buildEvidenceQueryIndex(evidenceCatalog);
  const facetCounts = buildFacetCounts(indexRecords);
  const queryText = normalizeQueryText(localUiState?.query_text);
  const activeFamily = localUiState?.active_family || "all";
  const sortBy = localUiState?.sort_by || "relevance";

  let results = queryStatus === "query_ready" ? indexRecords : [];
  if (activeFamily !== "all") {
    results = results.filter((record) => record.family === activeFamily);
  }
  results = results
    .map((record) => ({
      ...record,
      relevance_score: computeQueryScore(record, queryText)
    }))
    .filter((record) => queryText ? record.relevance_score > 0 : true);

  const sortedResults = sortQueryResults(results, sortBy);
  const selectedResult = sortedResults.find((record) => record.id === localUiState?.selected_result_id) || sortedResults[0] || null;
  const linkedArtifact = evidenceCatalog.find((artifact) => artifact.id === selectedResult?.artifact_id) || null;
  const replayFocus = pickReplayFocus(linkedArtifact, localUiState?.selected_replay_step_id);

  return {
    query_status: queryStatus,
    query_text: queryText,
    active_family: activeFamily,
    sort_by: sortBy,
    facet_counts: facetCounts,
    result_count: sortedResults.length,
    selected_result_id: selectedResult?.id || null,
    selected_artifact_id: linkedArtifact?.id || null,
    selected_replay_step_id: replayFocus.replay_focus_step?.id || null,
    results: sortedResults.map((record) => ({
      id: record.id,
      artifact_id: record.artifact_id,
      title: record.title,
      family: record.family,
      kind: record.kind,
      artifact_path: record.artifact_path,
      summary: record.summary,
      tags: record.tags,
      replay_step_titles: record.replay_step_titles,
      relevance_score: record.relevance_score
    })),
    selected_result: selectedResult,
    linked_artifact: linkedArtifact,
    replay_sequence: replayFocus.replay_sequence,
    replay_focus_step: replayFocus.replay_focus_step,
    boundary_warning: draftPlan?.evidence_boundary?.boundary_note || null,
    locale: localUiState?.locale || "en"
  };
}

export function createStage10EvidenceQueryDemoState() {
  return {
    queryText: "hesitate",
    activeFamily: "all",
    sortBy: "relevance",
    selectedResultId: "query-artifact-trace",
    selectedReplayStepId: "step-03"
  };
}

export function deriveStage10EvidenceQueryBundle({
  queryState,
  copy,
  localUiState = {}
}) {
  const baseBundle = deriveStage9EvidenceBundle({
    evidenceState: {
      activeFilter: "all",
      selectedArtifactId: "artifact-trace",
      selectedReplayStepId: "step-03"
    },
    copy,
    localUiState
  });

  const evidenceQuery = deriveWorkspaceEvidenceQueryState({
    draftPlan: baseBundle.draft,
    runRecord: baseBundle.run_record,
    evidenceCatalog: baseBundle.evidence_catalog,
    localUiState: {
      ...localUiState,
      query_text: queryState.queryText,
      active_family: queryState.activeFamily,
      sort_by: queryState.sortBy,
      selected_result_id: queryState.selectedResultId,
      selected_replay_step_id: queryState.selectedReplayStepId
    }
  });

  return {
    ...baseBundle,
    evidence_query: evidenceQuery
  };
}

function buildWorkspaceDemoRunRecord(shellState) {
  return {
    job_id: "job_workspace_proto_008",
    status: shellState.lifecycle,
    queue_position: shellState.lifecycle === "ready_to_queue" ? null : 1,
    worker_id: ["leased", "running", "completed", "failed"].includes(shellState.lifecycle)
      ? "worker-hkg-02"
      : null,
    current_step: shellState.lifecycle === "running"
      ? "persona_panel_execution"
      : shellState.lifecycle === "completed"
        ? "report_packaging"
        : shellState.lifecycle === "failed"
          ? "stimulus_render"
          : null,
    attempt_count: shellState.attemptCount ?? 0,
    last_event_at: shellState.events?.[0]?.at || null,
    failure_reason: shellState.failureReason || null,
    artifact_refs: shellState.lifecycle === "completed"
      ? [
          "runs/job_workspace_proto_008/report.json",
          "runs/job_workspace_proto_008/summary.md",
          "runs/job_workspace_proto_008/trace.json"
        ]
      : []
  };
}

function buildWorkspaceConversationFeed({ shellState, bundle }) {
  const feed = [
    {
      speaker: "user",
      title: "Research intent",
      body: bundle.conversation.latest_user_intent
    }
  ];

  if (bundle.adapter.ui_phase === "blocked") {
    feed.push({
      speaker: "system",
      title: "Missing evidence before confirmation",
      body: bundle.adapter.visible_waiting_for.join(", ") || "More prototype inputs are still required."
    });
  }

  if (bundle.adapter.ui_phase === "blocked_saved") {
    feed.push({
      speaker: "system",
      title: "Draft preserved",
      body: "The stronger prototype path remains intact, but the draft is saved until the missing evidence arrives."
    });
  }

  if (bundle.adapter.ui_phase === "ready_for_confirmation") {
    feed.push({
      speaker: "system",
      title: "Plan inferred",
      body: `Mode: ${bundle.draft.inference.primary_mode}. First task: ${bundle.draft.proposed_run.first_task || "not required"}`
    });
  }

  if (bundle.draft.advanced_controls?.summary) {
    const summary = bundle.draft.advanced_controls.summary;
    feed.push({
      speaker: "system",
      title: "Advanced study controls",
      body: `Mode override: ${summary.mode}. Panel: ${summary.panel}. Filters: ${summary.filters}. Provider: ${summary.provider}.`
    });
  }

  if (bundle.run_monitor.status === "queued") {
    feed.push({
      speaker: "system",
      title: "Run queued",
      body: "The plan has been confirmed and is waiting for worker execution."
    });
  }

  if (bundle.run_monitor.status === "leased" || bundle.run_monitor.status === "running") {
    feed.push({
      speaker: "system",
      title: "Worker active",
      body: "The shell now shifts from planning into run visibility while keeping the evidence boundary explicit."
    });
  }

  if (bundle.run_monitor.status === "failed") {
    feed.push({
      speaker: "system",
      title: "Run failed",
      body: bundle.run_monitor.failure_reason || "The worker stopped before artifact completion."
    });
  }

  if (bundle.run_monitor.status === "completed") {
    feed.push({
      speaker: "system",
      title: "Results ready",
      body: "The run completed. The operator can now inspect artifacts, replay moments, and query evidence from the same shell."
    });
  }

  if (bundle.evidence_query.selected_result) {
    feed.push({
      speaker: "system",
      title: "Selected evidence result",
      body: `${bundle.evidence_query.selected_result.title} is in focus for replay-linked review.`
    });
  }

  return feed;
}

function deriveWorkspaceShellState({ bundle }) {
  const activeSurface = bundle.run_monitor.status === "failed"
    ? "failure_visibility"
    : bundle.evidence_query.query_status === "query_ready"
      ? "evidence_query"
      : bundle.run_monitor.status === "queued" || bundle.run_monitor.status === "leased" || bundle.run_monitor.status === "running"
        ? "run_monitor"
        : bundle.adapter.ui_phase === "ready_for_confirmation"
          ? "confirmation"
          : bundle.adapter.ui_phase === "blocked_saved"
            ? "saved_draft"
            : "conversation_intake";

  const stageStrip = [
    {
      id: "intake",
      label: "Conversational intake",
      state: activeSurface === "conversation_intake" || activeSurface === "saved_draft"
        ? "active"
        : "done"
    },
    {
      id: "confirmation",
      label: "Plan confirmation",
      state: activeSurface === "confirmation"
        ? "active"
        : bundle.run_monitor.status !== "ready_to_queue"
          ? "done"
          : bundle.adapter.ui_phase === "blocked"
            ? "blocked"
            : "pending"
    },
    {
      id: "run_monitor",
      label: "Queue and run monitor",
      state: activeSurface === "run_monitor"
        ? "active"
        : bundle.run_monitor.status === "completed"
          ? "done"
          : bundle.run_monitor.status === "failed"
            ? "blocked"
            : "pending"
    },
    {
      id: "review",
      label: "Evidence review",
      state: activeSurface === "evidence_query"
        ? "active"
        : bundle.run_monitor.status === "completed"
          ? "pending"
          : bundle.run_monitor.status === "failed"
            ? "blocked"
            : "pending"
    }
  ];

  return {
    active_surface: activeSurface,
    next_action_label: bundle.adapter.primary_button.label,
    next_action_type: bundle.adapter.primary_button.action_type,
    review_ready: bundle.evidence_query.query_status === "query_ready",
    stage_strip: stageStrip,
    conversation_feed: buildWorkspaceConversationFeed({ shellState: null, bundle }),
    section_status: {
      conversation: bundle.adapter.ui_phase,
      monitor: bundle.run_monitor.status,
      browser: bundle.evidence_browser.browser_status,
      query: bundle.evidence_query.query_status
    }
  };
}

export function createStage11WorkspaceShellDemoState() {
  return {
    researchIntent: "Where do new operators hesitate during onboarding, and do they continue after the first task?",
    desiredOutcome: "task-friction and continuation risk",
    hasScreenshots: false,
    attachedArtifacts: [],
    firstTask: null,
    fallbackChosen: false,
    savedBlocked: false,
    panelType: "mainstream",
    sampleSize: 5,
    providerName: "mock",
    modeOverride: null,
    personaFilters: {},
    lifecycle: "ready_to_queue",
    attemptCount: 0,
    failureReason: null,
    queryText: "hesitate",
    activeFamily: "all",
    sortBy: "relevance",
    activeFilter: "all",
    selectedArtifactId: "artifact-trace",
    selectedResultId: "query-artifact-trace",
    selectedReplayStepId: "step-03",
    events: [{ type: "reset", at: "22:32" }]
  };
}

export function deriveStage11WorkspaceShellBundle({
  shellState,
  copy,
  localUiState = {}
}) {
  const baseBundle = deriveStage7DemoBundle({
    demoState: {
      draftPlanId: shellState.draftPlanId,
      submissionKey: shellState.submissionKey,
      confirmedAt: shellState.confirmedAt,
      hasScreenshots: Boolean(shellState.hasScreenshots),
      attachedArtifacts: shellState.attachedArtifacts || [],
      firstTask: shellState.firstTask,
      fallbackChosen: Boolean(shellState.fallbackChosen),
      savedBlocked: Boolean(shellState.savedBlocked),
      panelType: shellState.panelType,
      sampleSize: shellState.sampleSize,
      providerName: shellState.providerName,
      modeOverride: shellState.modeOverride,
      personaFilters: shellState.personaFilters,
      queueConfirmed: shellState.lifecycle !== "ready_to_queue",
      events: shellState.events || []
    },
    copy,
    localUiState
  });

  const runRecord = buildWorkspaceDemoRunRecord(shellState);

  if (shellState.lifecycle === "leased" || shellState.lifecycle === "running") {
    baseBundle.draft.proposed_run.execution_status = shellState.lifecycle;
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "await_run",
      label: copy.monitorAwait
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run is active. Review intermediate status, but do not treat partial worker progress as completed evidence.";
  } else if (shellState.lifecycle === "completed") {
    baseBundle.draft.proposed_run.execution_status = "completed";
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "view_results",
      label: copy.monitorViewResults
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run artifacts are ready for operator review, but the evidence remains synthetic and bounded by the current prototype-validation contract.";
  } else if (shellState.lifecycle === "failed") {
    baseBundle.draft.proposed_run.execution_status = "failed";
    baseBundle.draft.remediation.recommended_next_action = {
      action_type: "inspect_failure",
      label: copy.monitorInspectFailure
    };
    baseBundle.draft.evidence_boundary.boundary_note = "The run failed before artifact completion. Operators should review the failure cause before retrying.";
  }

  if (shellState.lifecycle !== "ready_to_queue") {
    baseBundle.draft.status = "confirmed";
    baseBundle.draft.confirmation.status = "confirmed";
    baseBundle.draft.audit.saved_for_later = false;
    baseBundle.adapter = deriveWorkspaceUiState({
      conversationState: baseBundle.conversation,
      draftPlan: baseBundle.draft,
      localUiState
    });
  }

  const runMonitor = deriveWorkspaceRunMonitorState({
    draftPlan: baseBundle.draft,
    runRecord,
    localUiState
  });

  const evidenceCatalog = createWorkspaceEvidenceCatalog();
  const evidenceBrowser = deriveWorkspaceEvidenceBrowserState({
    draftPlan: baseBundle.draft,
    runRecord,
    evidenceCatalog,
    localUiState: {
      ...localUiState,
      active_filter: shellState.activeFilter || "all",
      selected_artifact_id: shellState.selectedArtifactId || "artifact-trace",
      selected_replay_step_id: shellState.selectedReplayStepId || "step-03"
    }
  });

  const evidenceQuery = deriveWorkspaceEvidenceQueryState({
    draftPlan: baseBundle.draft,
    runRecord,
    evidenceCatalog,
    localUiState: {
      ...localUiState,
      query_text: shellState.queryText,
      active_family: shellState.activeFamily || "all",
      sort_by: shellState.sortBy || "relevance",
      selected_result_id: shellState.selectedResultId || "query-artifact-trace",
      selected_replay_step_id: shellState.selectedReplayStepId || "step-03"
    }
  });

  const bundle = {
    ...baseBundle,
    run_record: runRecord,
    run_monitor: runMonitor,
    evidence_catalog: evidenceCatalog,
    evidence_browser: evidenceBrowser,
    evidence_query: evidenceQuery
  };

  return {
    ...bundle,
    workspace_shell: deriveWorkspaceShellState({ bundle })
  };
}
