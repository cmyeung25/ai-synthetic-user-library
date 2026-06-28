function mapJobTone(status) {
  if (status === "failed" || status === "canceled") {
    return "failed";
  }
  if (status === "completed") {
    return "completed";
  }
  if (status === "running") {
    return "running";
  }
  return "queued";
}

function mapShellTone(status) {
  if (status === "failed") {
    return "failed";
  }
  if (status === "completed") {
    return "completed";
  }
  if (status === "running") {
    return "running";
  }
  return "queued";
}

function toSummaryRow(id, label, value) {
  return {
    id,
    label,
    value: value === null || value === undefined || value === "" ? "-" : value
  };
}

function toCountLabel(value) {
  const count = Number(value ?? 0);
  return `${count} item${count === 1 ? "" : "s"}`;
}

function summarizePersonaFilters(filters = {}) {
  const entries = Object.entries(filters || {}).filter(([, value]) => String(value || "").trim().length > 0);
  if (!entries.length) {
    return "none";
  }
  return entries.map(([key, value]) => `${key}=${value}`).join(", ");
}

function toReviewResult(result, selectedResultId) {
  return {
    id: result?.id || null,
    artifact_id: result?.artifact_id || null,
    title: result?.title || "Untitled evidence",
    family: result?.family || "-",
    kind: result?.kind || "-",
    summary: result?.summary || result?.artifact_path || "No summary available.",
    relevance_score: result?.relevance_score ?? null,
    selected: result?.id === selectedResultId
  };
}

function buildSelectedEvidenceSummary(reviewQueryState) {
  const selectedResult = reviewQueryState?.selected_result || null;
  const linkedArtifact = reviewQueryState?.linked_artifact || null;
  return [
    toSummaryRow("result_id", "result id", selectedResult?.id),
    toSummaryRow("artifact_id", "artifact id", selectedResult?.artifact_id || reviewQueryState?.selected_artifact_id),
    toSummaryRow("family", "family", selectedResult?.family),
    toSummaryRow("kind", "kind", selectedResult?.kind),
    toSummaryRow("path", "path", selectedResult?.artifact_path || linkedArtifact?.artifact_path),
    ...buildReliabilitySummary(reviewQueryState)
  ];
}

function buildSelectedEvidenceDetail(reviewQueryState) {
  const selectedResult = reviewQueryState?.selected_result || null;
  const linkedArtifact = reviewQueryState?.linked_artifact || null;
  const cards = [];

  if (!selectedResult && !linkedArtifact) {
    return [
      {
        id: "empty",
        title: "No selected evidence",
        body: "Pick a result after a completed run is available.",
        tone: "default"
      }
    ];
  }

  cards.push({
    id: "summary",
    title: selectedResult?.title || linkedArtifact?.title || "Selected evidence",
    body: selectedResult?.summary || linkedArtifact?.summary || "No summary available.",
    tone: "active"
  });

  (linkedArtifact?.detail_lines || []).forEach((line, index) => {
    cards.push({
      id: `detail_${index + 1}`,
      title: "Detail",
      body: line,
      tone: "default"
    });
  });

  return [
    ...cards,
    ...buildReliabilityDetail(reviewQueryState),
    ...buildCalibrationCards(reviewQueryState)
  ];
}

function buildReliabilitySummary(reviewQueryState) {
  const reliability = reviewQueryState?.evidence_reliability || {};
  return [
    toSummaryRow("reliability_status", "reliability", reliability.review_status || "reliability_pending"),
    toSummaryRow("stability_label", "stability", reliability.stability_label || "pending"),
    toSummaryRow("stability_score", "stability score", reliability.stability_score ?? 0),
    toSummaryRow("supporting_evidence", "supporting evidence", toCountLabel((reliability.supporting_evidence || []).length)),
    toSummaryRow("contradictions", "contradictions", toCountLabel((reliability.contradicting_evidence || []).length)),
    toSummaryRow("missing_context", "missing context", toCountLabel((reliability.missing_context || []).length))
  ];
}

function buildReliabilityDetail(reviewQueryState) {
  const reliability = reviewQueryState?.evidence_reliability || {};
  const cards = [
    {
      id: "reliability_status",
      title: `Reliability: ${reliability.stability_label || "pending"}`,
      body: `Score ${reliability.stability_score ?? 0}. ${reliability.synthetic_boundary || "Synthetic evidence boundary remains active."}`,
      tone: reliability.stability_label === "repeated_signal" ? "active" : "default"
    }
  ];

  (reliability.supporting_evidence || []).slice(0, 3).forEach((item, index) => {
    cards.push({
      id: `supporting_${index + 1}`,
      title: `Supporting ${item.source || "evidence"}: ${item.title || item.id || "Evidence"}`,
      body: item.relation || item.summary || "Supporting evidence is available.",
      tone: "active"
    });
  });

  (reliability.contradicting_evidence || []).slice(0, 3).forEach((item, index) => {
    cards.push({
      id: `contradicting_${index + 1}`,
      title: `Contradiction: ${item.title || item.id || "Evidence"}`,
      body: item.relation || item.summary || "Potential contradiction or risk signal is available.",
      tone: "failed"
    });
  });

  (reliability.missing_context || []).slice(0, 3).forEach((item, index) => {
    cards.push({
      id: `missing_context_${index + 1}`,
      title: item.label || `Missing context ${index + 1}`,
      body: item.note || "Missing context remains open.",
      tone: item.severity === "high" ? "failed" : "default"
    });
  });

  return cards;
}

function buildCalibrationCards(reviewQueryState) {
  const records = reviewQueryState?.evidence_reliability?.calibration_records || [];
  return records.map((record) => ({
    id: `calibration_${record.id || "record"}`,
    title: record.label || record.id || "Calibration record",
    body: [
      record.status ? `status ${record.status}` : "",
      record.score !== undefined ? `score ${record.score}` : "",
      record.note || ""
    ].filter(Boolean).join(" | "),
    tone: record.status === "requires_human_validation" ? "failed" : "default"
  }));
}

function buildAuditLineageSummary(reviewQueryState) {
  const lineage = reviewQueryState?.audit_lineage || reviewQueryState?.evidence_reliability?.audit_lineage || {};
  const sourceRun = lineage.source_run || {};
  const selectedEvidence = lineage.selected_evidence || {};
  const replay = lineage.replay || {};
  const comparisonSet = lineage.comparison_set || {};
  return [
    toSummaryRow("lineage_run", "lineage run", sourceRun.run_id),
    toSummaryRow("lineage_brief", "brief", sourceRun.brief_id),
    toSummaryRow("lineage_signal", "signal", selectedEvidence.signal_id),
    toSummaryRow("lineage_replay", "replay step", replay.selected_replay_step_id),
    toSummaryRow("lineage_comparisons", "comparison runs", comparisonSet.comparison_run_count ?? 0),
    toSummaryRow("lineage_selected_comparison", "selected comparison", comparisonSet.selected_comparison_run_id)
  ];
}

function buildReplaySteps(reviewQueryState) {
  return (reviewQueryState?.replay_sequence || []).map((step) => ({
    id: step.id,
    title: step.title,
    timestamp: step.timestamp || "-",
    note: step.note || "No replay note.",
    selected: step.id === reviewQueryState?.selected_replay_step_id
  }));
}

function pickReplayFocusStep(reviewQueryState) {
  const replayFocusStep = reviewQueryState?.replay_focus_step;
  if (replayFocusStep?.id) {
    return replayFocusStep;
  }
  const replaySequence = reviewQueryState?.replay_sequence || [];
  if (!replaySequence.length) {
    return null;
  }
  return replaySequence.find((step) => step.id === reviewQueryState?.selected_replay_step_id) || replaySequence[0];
}

function buildEvidenceCoverageCards(reviewQueryState, querySource) {
  const facetCounts = reviewQueryState?.facet_counts || {};
  const activeFamily = reviewQueryState?.active_family || "all";
  const families = [
    ["all", "All evidence"],
    ["trace", "Trace evidence"],
    ["analysis", "Analysis evidence"],
    ["output", "Output evidence"],
    ["input", "Input evidence"]
  ];

  return families.map(([family, title]) => {
    const count = Number(facetCounts?.[family] ?? 0);
    const isActive = activeFamily === family;
    const sourceNote = querySource === "backend" ? "backend snapshot" : "local projection";
    return {
      id: `coverage_${family}`,
      title,
      body: `${count} item${count === 1 ? "" : "s"} in ${sourceNote}${isActive ? " | active filter" : ""}.`,
      active: isActive
    };
  });
}

function buildReplayFocusSummary(reviewQueryState) {
  const replayFocusStep = pickReplayFocusStep(reviewQueryState);
  if (!replayFocusStep) {
    return [
      toSummaryRow("replay_step", "replay step", "not available"),
      toSummaryRow("step_timestamp", "timestamp", "-"),
      toSummaryRow("linked_result", "linked result", reviewQueryState?.selected_result?.title || "-")
    ];
  }
  return [
    toSummaryRow("replay_step", "replay step", replayFocusStep.title),
    toSummaryRow("step_timestamp", "timestamp", replayFocusStep.timestamp || "-"),
    toSummaryRow("linked_result", "linked result", reviewQueryState?.selected_result?.title || "-")
  ];
}

function buildReplayFocusDetail(reviewQueryState) {
  const replayFocusStep = pickReplayFocusStep(reviewQueryState);
  const selectedResult = reviewQueryState?.selected_result || null;
  if (!replayFocusStep) {
    return [
      {
        id: "replay_empty",
        title: "No replay focus",
        body: "Select trace-bearing evidence to review one concrete replay step.",
        tone: "default"
      }
    ];
  }
  const cards = [
    {
      id: "replay_focus",
      title: replayFocusStep.title || "Replay focus",
      body: replayFocusStep.note || "No replay note.",
      tone: "active"
    }
  ];
  if (selectedResult?.title) {
    cards.push({
      id: "replay_link",
      title: "Linked evidence",
      body: `${selectedResult.title} (${selectedResult.family || "unknown family"})`,
      tone: "default"
    });
  }
  return cards;
}

function buildRelatedResults(reviewQueryState) {
  const comparisonCandidates = reviewQueryState?.comparison_context?.comparison_candidates;
  if (Array.isArray(comparisonCandidates) && comparisonCandidates.length) {
    return comparisonCandidates.map((result) => ({
      id: result.id,
      artifact_id: result.artifact_id || null,
      title: result.title || "Untitled evidence",
      family: result.family || "-",
      kind: result.kind || "-",
      summary: result.summary || result.artifact_path || "No summary available.",
      relevance_score: result.relevance_score ?? null,
      relation_note: result.relation_note || "neighboring evidence surface",
      selected: false
    }));
  }

  const selectedResult = reviewQueryState?.selected_result || null;
  const results = Array.isArray(reviewQueryState?.results) ? reviewQueryState.results : [];
  if (!selectedResult || results.length <= 1) {
    return [];
  }
  return results
    .filter((result) => result?.id && result.id !== selectedResult.id)
    .sort((left, right) => {
      const leftSameFamily = left.family === selectedResult.family ? 1 : 0;
      const rightSameFamily = right.family === selectedResult.family ? 1 : 0;
      if (leftSameFamily !== rightSameFamily) {
        return rightSameFamily - leftSameFamily;
      }
      return Number(right.relevance_score ?? 0) - Number(left.relevance_score ?? 0);
    })
    .slice(0, 3)
    .map((result) => ({
      id: result.id,
      artifact_id: result.artifact_id || null,
      title: result.title || "Untitled evidence",
      family: result.family || "-",
      kind: result.kind || "-",
      summary: result.summary || result.artifact_path || "No summary available.",
      relevance_score: result.relevance_score ?? null,
      relation_note: result.family === selectedResult.family
        ? "same family as selected evidence"
        : "neighboring evidence surface",
      selected: false
    }));
}

function buildCrossRunCandidates(reviewQueryState) {
  const crossRun = reviewQueryState?.cross_run_comparison || {};
  const selectedRunId = crossRun?.selected_comparison_run_id || null;
  const candidates = Array.isArray(crossRun?.candidate_runs) ? crossRun.candidate_runs : [];
  return candidates.map((run) => ({
    run_id: run?.run_id || null,
    job_id: run?.job_id || null,
    title: run?.top_result_title || run?.run_id || "Comparison run",
    run_kind: run?.run_kind || "-",
    status: run?.status || "-",
    relation_note: run?.relation_note || "same workspace evidence scope",
    result_count: run?.result_count ?? 0,
    replay_result_count: run?.replay_result_count ?? 0,
    selected: run?.run_id === selectedRunId
  }));
}

function buildCrossRunSummary(reviewQueryState) {
  const crossRun = reviewQueryState?.cross_run_comparison || {};
  const selectedRun = crossRun?.selected_comparison_run || null;
  return [
    toSummaryRow("comparison_run_count", "comparison runs", crossRun?.comparison_run_count ?? 0),
    toSummaryRow("selected_comparison_run", "selected comparison run", selectedRun?.run_id || crossRun?.selected_comparison_run_id || "not selected"),
    toSummaryRow("comparison_job_id", "comparison job", selectedRun?.job_id || crossRun?.selected_comparison_job_id || "-"),
    toSummaryRow("recommended_result", "recommended result", selectedRun?.recommended_result_title || "-")
  ];
}

function buildCrossRunDetail(reviewQueryState) {
  const selectedRun = reviewQueryState?.cross_run_comparison?.selected_comparison_run || null;
  if (!selectedRun) {
    return [
      {
        id: "cross_run_empty",
        title: "No comparison run selected",
        body: "Choose one comparable completed run to inspect cross-run evidence alignment.",
        tone: "default"
      }
    ];
  }
  const cards = [
    {
      id: "cross_run_summary",
      title: selectedRun.run_id || "Comparison run",
      body: selectedRun.note || selectedRun.relation_note || "Cross-run comparison is available.",
      tone: "active"
    }
  ];
  if (selectedRun.recommended_result_title) {
    cards.push({
      id: "cross_run_recommended_result",
      title: "Recommended artifact",
      body: `${selectedRun.recommended_result_title}${selectedRun.recommended_result_reason ? ` | ${selectedRun.recommended_result_reason}` : ""}`,
      tone: "default"
    });
  }
  if (selectedRun.relation_note) {
    cards.push({
      id: "cross_run_relation",
      title: "Why this run",
      body: selectedRun.relation_note,
      tone: "default"
    });
  }
  return cards;
}

function buildCrossRunResultCards(reviewQueryState) {
  const selectedRun = reviewQueryState?.cross_run_comparison?.selected_comparison_run || null;
  const recommendedResultId = selectedRun?.recommended_result_id || null;
  const comparisonResults = Array.isArray(selectedRun?.comparison_results) ? selectedRun.comparison_results : [];
  return comparisonResults.map((result) => ({
    id: result?.id || null,
    artifact_id: result?.artifact_id || null,
    title: result?.title || "Untitled evidence",
    family: result?.family || "-",
    kind: result?.kind || "-",
    summary: result?.summary || result?.artifact_path || "No summary available.",
    relevance_score: result?.relevance_score ?? null,
    recommended: result?.id === recommendedResultId
  }));
}

function mapDecisionReviewTone(reviewStatus) {
  if (reviewStatus === "approved") {
    return "completed";
  }
  if (reviewStatus === "needs_revision") {
    return "failed";
  }
  if (reviewStatus === "in_review") {
    return "running";
  }
  return "queued";
}

function buildDecisionReviewSummary(selectedDecisionLog) {
  if (!selectedDecisionLog) {
    return [
      toSummaryRow("review_status", "review status", "No decision selected"),
      toSummaryRow("review_comments", "comments", "0 items"),
      toSummaryRow("review_threads", "threads", "0 items"),
      toSummaryRow("review_updated_at", "updated", "-"),
      toSummaryRow("review_updated_by", "reviewer", "-"),
      toSummaryRow("review_note", "latest note", "not set")
    ];
  }
  return [
    toSummaryRow("review_status", "review status", selectedDecisionLog.review_status || "draft"),
    toSummaryRow("review_comments", "comments", toCountLabel(selectedDecisionLog.comment_count ?? 0)),
    toSummaryRow("review_threads", "threads", toCountLabel(selectedDecisionLog.review_thread_count ?? 0)),
    toSummaryRow(
      "review_updated_at",
      "updated",
      selectedDecisionLog.review_status_updated_at || selectedDecisionLog.updated_at
    ),
    toSummaryRow("review_updated_by", "reviewer", selectedDecisionLog.review_status_updated_by_user_id || "-"),
    toSummaryRow("review_note", "latest note", selectedDecisionLog.latest_review_note || "not set")
  ];
}

function buildDecisionReviewComments(decisionComments = []) {
  return (decisionComments || []).map((comment) => ({
    decision_comment_id: comment?.decision_comment_id || null,
    parent_comment_id: comment?.parent_comment_id || null,
    anchor_kind: comment?.anchor_kind || "general",
    body: comment?.body || "",
    created_by_user_id: comment?.created_by_user_id || null,
    created_at: comment?.created_at || null,
    reply_count: Number(comment?.reply_count ?? 0),
    indent_level: comment?.parent_comment_id ? 1 : 0,
    is_reply: Boolean(comment?.parent_comment_id),
  }));
}

function buildReplayNote(reviewQueryState, replayFocusStep) {
  const backendNote = reviewQueryState?.replay_context?.note;
  if (backendNote) {
    if (replayFocusStep?.timestamp && !backendNote.includes(replayFocusStep.timestamp)) {
      return `${backendNote} Current focus: ${replayFocusStep.timestamp}.`;
    }
    return backendNote;
  }
  return (reviewQueryState?.replay_sequence || []).length
    ? `Replay remains limited to artifacts that actually carry trace-linked steps.${replayFocusStep?.timestamp ? ` Current focus: ${replayFocusStep.timestamp}.` : ""}`
    : "No replay-linked steps are available for the current selection.";
}

export function deriveWorkspaceShellFrontendAdapter({
  bundle,
  bridgeState,
  selectedJob = null,
  selectedProject = null,
  selectedStudy = null,
  studyActivity = null,
  selectedEvidenceView = null,
  selectedDecisionLog = null,
  decisionComments = [],
  selectedExportBundle = null,
  selectedShareBundle = null,
  selectedSupportSnapshot = null,
  projects = [],
  studies = [],
  evidenceViews = [],
  decisionLogs = [],
  exportBundles = [],
  shareBundles = [],
  supportSnapshots = [],
  supportDiagnostics = null,
  workspaceSettings = null,
  auditEvents = [],
  auditQuery = null,
  lastIssuedApiToken = null,
  mode = "sample",
  lastApiResponse = null,
  reviewQueryState = null,
  querySource = "local"
}) {
  const effectiveReviewQueryState = reviewQueryState || bundle?.evidence_query || {};
  const replayFocusStep = pickReplayFocusStep(effectiveReviewQueryState);
  const relatedResults = buildRelatedResults(effectiveReviewQueryState);
  const crossRunCandidates = buildCrossRunCandidates(effectiveReviewQueryState);
  const crossRunResultCards = buildCrossRunResultCards(effectiveReviewQueryState);
  const selectedJobId = bridgeState?.selected_job_id || selectedJob?.job_id || null;
  const shellSurface = bundle?.workspace_shell?.active_surface || "conversation_intake";
  const bridgeTone = bridgeState?.warning
    ? "failed"
    : bridgeState?.submission_ready
      ? "completed"
      : "queued";

  return {
    contract_version: "workspace-shell-frontend-adapter/v0-draft",
    metrics: {
      bridge_status: bridgeState?.bridge_status || "draft_only",
      submission_ready: Boolean(bridgeState?.submission_ready),
      selected_project_id: selectedProject?.project_id || null,
      selected_study_id: selectedStudy?.study_id || null,
      selected_evidence_view_id: selectedEvidenceView?.evidence_view_id || null,
      selected_decision_log_id: selectedDecisionLog?.decision_log_id || null,
      selected_export_bundle_id: selectedExportBundle?.export_bundle_id || null,
      selected_share_bundle_id: selectedShareBundle?.share_bundle_id || null,
      selected_support_snapshot_id: selectedSupportSnapshot?.support_snapshot_id || null,
      selected_job_id: selectedJobId,
      shell_surface: shellSurface
    },
    pills: {
      bridge: {
        tone: bridgeTone,
        label: bridgeState?.bridge_status || "draft_only"
      },
      job: {
        tone: mapJobTone(selectedJob?.status),
        label: selectedJob?.status || "no job"
      },
      shell: {
        tone: mapShellTone(bundle?.run_monitor?.status),
        label: shellSurface
      }
    },
    actions: {
      submit_live_job: {
        intent: "submit_validation_job",
        enabled: Boolean(bridgeState?.submission_ready)
      },
      list_live_jobs: {
        intent: "list_validation_jobs",
        enabled: true
      },
      load_selected_job: {
        intent: "load_validation_job_detail",
        enabled: Boolean(selectedJobId)
      },
      retry_selected_job: {
        intent: "retry_validation_job",
        enabled: selectedJob?.status === "failed" || selectedJob?.status === "canceled"
      },
      cancel_selected_job: {
        intent: "cancel_validation_job",
        enabled: selectedJob?.status === "queued"
      },
      load_live_evidence_query: {
        intent: "load_evidence_query",
        enabled: Boolean(selectedJobId)
      },
      apply_evidence_query: {
        intent: "apply_evidence_query",
        enabled: true
      },
      use_sample_jobs: {
        intent: "switch_to_sample_jobs",
        enabled: true
      },
      request_decision_review: {
        intent: "update_decision_review_status",
        enabled: Boolean(selectedDecisionLog)
      },
      approve_decision_log: {
        intent: "update_decision_review_status",
        enabled: Boolean(selectedDecisionLog)
      },
      request_decision_revision: {
        intent: "update_decision_review_status",
        enabled: Boolean(selectedDecisionLog)
      },
      add_decision_comment: {
        intent: "create_decision_comment",
        enabled: Boolean(selectedDecisionLog)
      }
    },
    request_summary: [
      toSummaryRow("brief_path", "brief_path", bridgeState?.request_payload?.brief_path),
      toSummaryRow("persona_dir", "persona_dir", bridgeState?.request_payload?.persona_dir),
      toSummaryRow("panel_type", "panel_type", bridgeState?.request_payload?.panel_spec?.panel_type),
      toSummaryRow("sample_size", "sample_size", bridgeState?.request_payload?.panel_spec?.sample_size),
      toSummaryRow("filters", "filters", summarizePersonaFilters(bridgeState?.request_payload?.panel_spec?.filters || {})),
      toSummaryRow("provider_name", "provider_name", bridgeState?.request_payload?.provider_name),
      toSummaryRow("run_root", "run_root", bridgeState?.request_payload?.run_root)
    ],
    bridge_summary: [
      toSummaryRow("submit_endpoint", "submit endpoint", bridgeState?.endpoint_summary?.submit),
      toSummaryRow("list_endpoint", "list endpoint", bridgeState?.endpoint_summary?.list),
      toSummaryRow("detail_endpoint", "detail endpoint", bridgeState?.endpoint_summary?.detail),
      toSummaryRow("query_endpoint", "query endpoint", bridgeState?.endpoint_summary?.query)
    ],
    selected_job_summary: selectedJob ? [
      toSummaryRow("job_id", "job_id", selectedJob.job_id),
      toSummaryRow("status", "status", selectedJob.status),
      toSummaryRow("provider", "provider", selectedJob.provider_name),
      toSummaryRow("retry_count", "retry count", selectedJob.retry_count),
      toSummaryRow("output_run_path", "output_run_path", selectedJob.output_run_path),
      toSummaryRow("last_error", "last_error", selectedJob.last_error)
    ] : [
      toSummaryRow("job", "Job", "No job selected")
    ],
    draft_summary: [
      toSummaryRow("mode", "mode", bundle?.draft?.inference?.primary_mode),
      toSummaryRow("first_task", "first task", bundle?.draft?.proposed_run?.first_task || "not set"),
      toSummaryRow("confirmation", "confirmation", bundle?.draft?.confirmation?.status),
      toSummaryRow("mode_override", "mode override", bundle?.draft?.advanced_controls?.summary?.mode || "auto"),
      toSummaryRow("panel_setup", "panel setup", bundle?.draft?.advanced_controls?.summary?.panel),
      toSummaryRow("persona_filters", "persona filters", bundle?.draft?.advanced_controls?.summary?.filters),
      toSummaryRow("shell_mode", "shell mode", mode)
    ],
    adapter_summary: [
      toSummaryRow("ui_phase", "ui phase", bundle?.adapter?.ui_phase),
      toSummaryRow("run_state", "run state", bundle?.adapter?.run_state),
      toSummaryRow("primary_action", "primary action", bundle?.adapter?.primary_button?.label),
      toSummaryRow(
        "waiting_for",
        "waiting for",
        bundle?.adapter?.visible_waiting_for?.length
          ? bundle.adapter.visible_waiting_for.join(", ")
          : "none"
      )
    ],
    run_monitor_summary: [
      toSummaryRow("status", "status", bundle?.run_monitor?.status),
      toSummaryRow("attempts", "attempts", bundle?.run_monitor?.attempt_count),
      toSummaryRow("current_step", "current step", bundle?.run_monitor?.current_step || "none"),
      toSummaryRow("failure", "failure", bundle?.run_monitor?.failure_reason)
    ],
    review_summary: [
      toSummaryRow("query_status", "query status", effectiveReviewQueryState?.query_status),
      toSummaryRow("selected_result", "selected result", effectiveReviewQueryState?.selected_result_id),
      toSummaryRow("artifact_count", "artifact count", effectiveReviewQueryState?.result_count),
      toSummaryRow("query_source", "query source", querySource === "backend" ? "backend evidence endpoint" : "local projection")
    ],
    sidecar_rows: [
      toSummaryRow("bridge", "bridge", bridgeState?.bridge_status),
      toSummaryRow("submission_ready", "submission ready", bridgeState?.submission_ready ? "yes" : "no"),
      toSummaryRow("selected_job", "selected job", selectedJobId),
      toSummaryRow("warning", "warning", bridgeState?.warning || "none")
    ],
    bridge_gap: bridgeState?.live_review_gap || null,
    stage_strip: bundle?.workspace_shell?.stage_strip || [],
    review_surface: {
      query_status: effectiveReviewQueryState?.query_status || "query_pending",
      query_source: querySource,
      boundary_warning: effectiveReviewQueryState?.boundary_warning || null,
      result_count: effectiveReviewQueryState?.result_count ?? 0,
      selected_result_id: effectiveReviewQueryState?.selected_result_id || null,
      selected_replay_step_id: effectiveReviewQueryState?.selected_replay_step_id || null,
      selected_comparison_run_id: effectiveReviewQueryState?.cross_run_comparison?.selected_comparison_run_id || null,
      empty_note: effectiveReviewQueryState?.query_status === "query_pending"
        ? "Evidence query stays pending until a completed run is available."
        : (effectiveReviewQueryState?.result_count ?? 0) > 0
          ? `${effectiveReviewQueryState.result_count} result${effectiveReviewQueryState.result_count === 1 ? "" : "s"} from ${querySource === "backend" ? "backend evidence endpoint" : "local projection"}.`
          : "No evidence results match the current query.",
      results: (effectiveReviewQueryState?.results || []).map((result) => (
        toReviewResult(result, effectiveReviewQueryState?.selected_result_id)
      )),
      selected_evidence_summary: buildSelectedEvidenceSummary(effectiveReviewQueryState),
      selected_evidence_detail: buildSelectedEvidenceDetail(effectiveReviewQueryState),
      evidence_coverage_cards: buildEvidenceCoverageCards(effectiveReviewQueryState, querySource),
      replay_focus_summary: buildReplayFocusSummary(effectiveReviewQueryState),
      replay_focus_detail: buildReplayFocusDetail(effectiveReviewQueryState),
      replay_steps: buildReplaySteps(effectiveReviewQueryState),
      related_results: relatedResults,
      related_results_note: relatedResults.length
        ? (effectiveReviewQueryState?.comparison_context?.note || "Use nearby evidence to compare whether the same hesitation shows up in other artifacts.")
        : "No additional evidence is available for side-by-side comparison.",
      cross_run_summary: buildCrossRunSummary(effectiveReviewQueryState),
      cross_run_detail: buildCrossRunDetail(effectiveReviewQueryState),
      cross_run_candidates: crossRunCandidates,
      cross_run_result_cards: crossRunResultCards,
      cross_run_note: effectiveReviewQueryState?.cross_run_comparison?.note || "No comparable completed runs are available for cross-run review.",
      evidence_reliability: effectiveReviewQueryState?.evidence_reliability || null,
      audit_lineage: effectiveReviewQueryState?.audit_lineage || effectiveReviewQueryState?.evidence_reliability?.audit_lineage || null,
      reliability_summary: buildReliabilitySummary(effectiveReviewQueryState),
      reliability_detail: buildReliabilityDetail(effectiveReviewQueryState),
      calibration_cards: buildCalibrationCards(effectiveReviewQueryState),
      audit_lineage_summary: buildAuditLineageSummary(effectiveReviewQueryState),
      replay_note: buildReplayNote(effectiveReviewQueryState, replayFocusStep)
    },
    shell_projection: {
      active_surface: shellSurface,
      section_status: bundle?.workspace_shell?.section_status || {},
      review_ready: Boolean(bundle?.workspace_shell?.review_ready)
    },
    product_surface: {
      projects: (projects || []).map((project) => ({
        project_id: project?.project_id || null,
        title: project?.name || "Untitled project",
        slug: project?.slug || "-",
        description: project?.description || "No description yet.",
        study_count: project?.study_count ?? 0,
        latest_study_id: project?.latest_study_id || null,
        selected: project?.project_id === selectedProject?.project_id
      })),
      studies: (studies || []).map((study) => ({
        study_id: study?.study_id || null,
        project_id: study?.project_id || null,
        title: study?.title || "Untitled study",
        status: study?.status || "draft",
        run_count: study?.run_count ?? 0,
        evidence_view_count: study?.evidence_view_count ?? 0,
        decision_log_count: study?.decision_log_count ?? 0,
        latest_job_status: study?.latest_job_status || "not started",
        first_task: study?.first_task || "not set",
        selected: study?.study_id === selectedStudy?.study_id
      })),
      study_activity: Array.isArray(studyActivity) ? studyActivity.map((event) => ({
        activity_id: event?.activity_id || null,
        action: event?.action || "unknown",
        event_family: event?.event_family || "study",
        tone: event?.tone || "queued",
        headline: event?.headline || "Study activity",
        summary: event?.summary || "No summary available.",
        actor_user_id: event?.actor_user_id || null,
        actor_role: event?.actor_role || null,
        created_at: event?.created_at || null,
        route_kind: event?.route_kind || null,
        route_id: event?.route_id || null,
        route_path: event?.route_path || null
      })) : [],
      evidence_views: (evidenceViews || []).map((view) => ({
        evidence_view_id: view?.evidence_view_id || null,
        study_id: view?.study_id || null,
        job_id: view?.job_id || null,
        title: view?.title || "Untitled saved view",
        note: view?.note || "No note yet.",
        active_family: view?.active_family || "all",
        sort_by: view?.sort_by || "relevance",
        selected: view?.evidence_view_id === selectedEvidenceView?.evidence_view_id
      })),
      decision_logs: (decisionLogs || []).map((log) => ({
        decision_log_id: log?.decision_log_id || null,
        study_id: log?.study_id || null,
        job_id: log?.job_id || null,
        evidence_view_id: log?.evidence_view_id || null,
        title: log?.title || "Untitled decision",
        decision_summary: log?.decision_summary || "No decision summary yet.",
        rationale: log?.rationale || "No rationale yet.",
        review_status: log?.review_status || "draft",
        comment_count: log?.comment_count ?? 0,
        selected: log?.decision_log_id === selectedDecisionLog?.decision_log_id
      })),
      export_bundles: (exportBundles || []).map((exportBundle) => ({
        export_bundle_id: exportBundle?.export_bundle_id || null,
        study_id: exportBundle?.study_id || null,
        job_id: exportBundle?.job_id || null,
        title: exportBundle?.title || "Untitled export",
        status: exportBundle?.status || "draft",
        export_format: exportBundle?.export_format || "bundle_json",
        exported_file_count: exportBundle?.exported_file_count ?? exportBundle?.exported_files?.length ?? 0,
        share_bundle_count: exportBundle?.share_bundle_count ?? 0,
        selected: exportBundle?.export_bundle_id === selectedExportBundle?.export_bundle_id
      })),
      share_bundles: (shareBundles || []).map((shareBundle) => ({
        share_bundle_id: shareBundle?.share_bundle_id || null,
        export_bundle_id: shareBundle?.export_bundle_id || null,
        title: shareBundle?.title || "Untitled share",
        status: shareBundle?.status || "draft",
        public_path: shareBundle?.public_path || "-",
        share_file_count: shareBundle?.share_file_count ?? 0,
        selected: shareBundle?.share_bundle_id === selectedShareBundle?.share_bundle_id
      })),
      selected_project_summary: selectedProject ? [
        toSummaryRow("project_name", "project", selectedProject.name),
        toSummaryRow("project_slug", "slug", selectedProject.slug),
        toSummaryRow("project_study_count", "studies", toCountLabel(selectedProject.study_count)),
        toSummaryRow("project_shares", "shares", toCountLabel(selectedProject.share_bundle_count)),
        toSummaryRow("latest_study_id", "latest study", selectedProject.latest_study_id)
      ] : [
        toSummaryRow("project", "project", "No project selected")
      ],
      selected_study_summary: selectedStudy ? [
        toSummaryRow("study_title", "study", selectedStudy.title),
        toSummaryRow("study_status", "status", selectedStudy.status),
        toSummaryRow("study_runs", "runs", toCountLabel(selectedStudy.run_count)),
        toSummaryRow("study_saved_views", "saved views", toCountLabel(selectedStudy.evidence_view_count)),
        toSummaryRow("study_decisions", "decisions", toCountLabel(selectedStudy.decision_log_count)),
        toSummaryRow("study_activity_items", "activity", Array.isArray(studyActivity) ? toCountLabel(studyActivity.length) : "not loaded"),
        toSummaryRow("study_job_status", "latest job", selectedStudy.latest_job_status || "not started"),
        toSummaryRow("study_exports", "exports", toCountLabel(selectedStudy.export_bundle_count)),
        toSummaryRow("study_shares", "shares", toCountLabel(selectedStudy.share_bundle_count)),
        toSummaryRow("study_first_task", "first task", selectedStudy.first_task || "not set")
      ] : [
        toSummaryRow("study", "study", "No study selected")
      ],
      study_activity_summary: Array.isArray(studyActivity) ? (
        studyActivity.length ? [
          toSummaryRow("activity_count", "events", toCountLabel(studyActivity.length)),
          toSummaryRow("latest_activity", "latest", studyActivity[0]?.headline || "unknown"),
          toSummaryRow("latest_actor", "actor", studyActivity[0]?.actor_user_id || "system"),
          toSummaryRow("latest_time", "time", studyActivity[0]?.created_at || "unknown")
        ] : [
          toSummaryRow("activity", "study activity", "No study activity recorded yet")
        ]
      ) : [
        toSummaryRow("activity", "study activity", "Study activity not loaded")
      ],
      selected_evidence_view_summary: selectedEvidenceView ? [
        toSummaryRow("evidence_view_title", "saved view", selectedEvidenceView.title),
        toSummaryRow("evidence_view_job_id", "job", selectedEvidenceView.job_id || "not set"),
        toSummaryRow("evidence_view_family", "family", selectedEvidenceView.active_family),
        toSummaryRow("evidence_view_sort", "sort", selectedEvidenceView.sort_by),
        toSummaryRow("evidence_view_note", "note", selectedEvidenceView.note || "not set")
      ] : [
        toSummaryRow("evidence_view", "saved view", "No saved evidence view selected")
      ],
      selected_decision_log_summary: selectedDecisionLog ? [
        toSummaryRow("decision_log_title", "decision", selectedDecisionLog.title),
        toSummaryRow("decision_log_job_id", "job", selectedDecisionLog.job_id || "not set"),
        toSummaryRow("decision_log_view", "saved view", selectedDecisionLog.evidence_view_id || "not linked"),
        toSummaryRow("decision_log_summary", "summary", selectedDecisionLog.decision_summary),
        toSummaryRow("decision_log_rationale", "rationale", selectedDecisionLog.rationale || "not set"),
        toSummaryRow("decision_log_review_status", "review status", selectedDecisionLog.review_status || "draft"),
        toSummaryRow("decision_log_comment_count", "comments", toCountLabel(selectedDecisionLog.comment_count ?? 0))
      ] : [
        toSummaryRow("decision_log", "decision", "No decision log selected")
      ],
      decision_review_summary: buildDecisionReviewSummary(selectedDecisionLog),
      decision_review_comments: buildDecisionReviewComments(decisionComments),
      selected_export_bundle_summary: selectedExportBundle ? [
        toSummaryRow("export_title", "export", selectedExportBundle.title),
        toSummaryRow("export_status", "status", selectedExportBundle.status),
        toSummaryRow("export_format", "format", selectedExportBundle.export_format),
        toSummaryRow("export_files", "files", toCountLabel(selectedExportBundle.exported_file_count ?? selectedExportBundle.exported_files?.length ?? 0)),
        toSummaryRow("export_shares", "shares", toCountLabel(selectedExportBundle.share_bundle_count)),
        toSummaryRow("export_job_id", "job", selectedExportBundle.job_id),
        toSummaryRow("export_boundary", "boundary", selectedExportBundle.synthetic_boundary)
      ] : [
        toSummaryRow("export", "export", "No export selected")
      ],
      selected_share_bundle_summary: selectedShareBundle ? [
        toSummaryRow("share_title", "share", selectedShareBundle.title),
        toSummaryRow("share_status", "status", selectedShareBundle.status),
        toSummaryRow("share_public_path", "public path", selectedShareBundle.public_path),
        toSummaryRow("share_files", "files", toCountLabel(selectedShareBundle.share_file_count)),
        toSummaryRow("share_expires_at", "expires", selectedShareBundle.expires_at || "not set"),
        toSummaryRow("share_boundary", "boundary", selectedShareBundle.synthetic_boundary)
      ] : [
        toSummaryRow("share", "share", "No share selected")
      ],
      support_snapshots: (supportSnapshots || []).map((snapshot) => ({
        support_snapshot_id: snapshot?.support_snapshot_id || null,
        title: snapshot?.title || "Untitled support snapshot",
        status: snapshot?.status || "generated",
        summary: snapshot?.summary || "No support summary available.",
        job_id: snapshot?.job_id || null,
        selected: snapshot?.support_snapshot_id === selectedSupportSnapshot?.support_snapshot_id
      })),
      selected_support_snapshot_summary: selectedSupportSnapshot ? [
        toSummaryRow("support_title", "support snapshot", selectedSupportSnapshot.title),
        toSummaryRow("support_status", "status", selectedSupportSnapshot.status),
        toSummaryRow("support_job_id", "job", selectedSupportSnapshot.job_id),
        toSummaryRow("support_run_id", "run", selectedSupportSnapshot.run_id),
        toSummaryRow("support_summary", "summary", selectedSupportSnapshot.summary)
      ] : [
        toSummaryRow("support", "support snapshot", "No support snapshot selected")
      ],
      workspace_settings_summary: workspaceSettings ? [
        toSummaryRow("workspace_name", "workspace", workspaceSettings.workspace?.display_name),
        toSummaryRow("workspace_plan", "plan", workspaceSettings.workspace?.plan_tier),
        toSummaryRow("workspace_status", "status", workspaceSettings.workspace?.status),
        toSummaryRow("member_count", "members", toCountLabel(workspaceSettings.members?.length ?? 0)),
        toSummaryRow("active_token_count", "active tokens", toCountLabel((workspaceSettings.api_tokens || []).filter((token) => token.active).length))
      ] : [
        toSummaryRow("workspace_settings", "workspace settings", "Workspace settings not loaded")
      ],
      workspace_billing_summary: workspaceSettings ? [
        toSummaryRow("billing_status", "billing", workspaceSettings.billing_account?.status),
        toSummaryRow("seat_count", "seats", workspaceSettings.billing_account?.seat_count),
        toSummaryRow("price_book_id", "price book", workspaceSettings.billing_account?.price_book_id),
        toSummaryRow("renewal_at", "renewal", workspaceSettings.billing_account?.renewal_at || "not set"),
        toSummaryRow("daily_runs", "daily runs", workspaceSettings.plan_limits?.daily_runs),
        toSummaryRow("concurrent_runs", "concurrent runs", workspaceSettings.plan_limits?.max_concurrent_jobs),
        toSummaryRow("retention_days", "retention days", workspaceSettings.plan_limits?.artifact_retention_days)
      ] : [
        toSummaryRow("billing", "billing", "Workspace settings not loaded")
      ],
      workspace_policy_summary: workspaceSettings ? [
        toSummaryRow("region_code", "region", workspaceSettings.policies?.region_code),
        toSummaryRow("data_residency_region", "data residency", workspaceSettings.policies?.data_residency_region),
        toSummaryRow("policy_daily_runs", "daily run cap", workspaceSettings.policies?.daily_runs),
        toSummaryRow("policy_concurrent_runs", "concurrent cap", workspaceSettings.policies?.max_concurrent_jobs),
        toSummaryRow("policy_retention_days", "artifact retention", workspaceSettings.policies?.artifact_retention_days)
      ] : [
        toSummaryRow("policy", "policy", "Workspace settings not loaded")
      ],
      workspace_members: (workspaceSettings?.members || []).map((member) => ({
        user_id: member?.user_id || null,
        role: member?.role || "viewer",
        joined_at: member?.joined_at || null,
        current: member?.user_id === workspaceSettings?.auth?.user_id
      })),
      workspace_api_tokens: (workspaceSettings?.api_tokens || []).map((token) => ({
        token_id: token?.token_id || null,
        token_hint: token?.token_hint || "-",
        user_id: token?.user_id || null,
        role: token?.role || "viewer",
        issued_at: token?.issued_at || null,
        active: Boolean(token?.active),
        current: Boolean(token?.current)
      })),
      last_issued_api_token_summary: lastIssuedApiToken ? [
        toSummaryRow("issued_token", "issued token", lastIssuedApiToken.token),
        toSummaryRow("issued_token_hint", "token hint", lastIssuedApiToken.token_hint),
        toSummaryRow("issued_token_user", "user", lastIssuedApiToken.user_id),
        toSummaryRow("issued_token_role", "role", lastIssuedApiToken.role)
      ] : [
        toSummaryRow("issued_token", "last issued token", "No token issued in this shell session")
      ],
      workspace_audit_summary: auditEvents.length ? [
        toSummaryRow("audit_events", "events", toCountLabel(auditEvents.length)),
        toSummaryRow("audit_target_type", "target type", auditQuery?.target_type || "all"),
        toSummaryRow("audit_action_prefix", "action prefix", auditQuery?.action_prefix || "all"),
        toSummaryRow("audit_latest_action", "latest action", auditEvents[0]?.action || "unknown")
      ] : [
        toSummaryRow("audit_history", "audit history", "Audit history not loaded")
      ],
      workspace_audit_events: (auditEvents || []).map((event) => ({
        audit_event_id: event?.audit_event_id || null,
        action: event?.action || "unknown",
        actor_user_id: event?.actor_user_id || null,
        actor_role: event?.actor_role || null,
        target_type: event?.target_type || null,
        target_id: event?.target_id || null,
        created_at: event?.created_at || null,
        summary: Object.entries(event?.event_payload || {}).slice(0, 3).map(([key, value]) => `${key}: ${String(value)}`).join(" | ")
      }))
    },
    support_surface: {
      submission_gate_summary: [
        toSummaryRow("submission_gate_status", "submission gate", supportDiagnostics?.submission_gate?.status || "unknown"),
        toSummaryRow("blocked_reason_count", "blocked reasons", supportDiagnostics?.submission_gate?.blocked_reason_count ?? 0),
        toSummaryRow("selected_job_id", "selected job", supportDiagnostics?.selected_job_id || selectedJobId),
        toSummaryRow("snapshot_count", "support snapshots", supportDiagnostics?.support_snapshot_count ?? supportSnapshots.length)
      ],
      blocked_reasons: supportDiagnostics?.submission_gate?.blocked_reasons || [],
      job_diagnostic_summary: supportDiagnostics?.job_diagnostic ? [
        toSummaryRow("job_status", "job status", supportDiagnostics.job_diagnostic.status),
        toSummaryRow("failure_category", "failure category", supportDiagnostics.job_diagnostic.failure_category),
        toSummaryRow("provider_name", "provider", supportDiagnostics.job_diagnostic.provider_name),
        toSummaryRow("retry_count", "retry count", supportDiagnostics.job_diagnostic.retry_count ?? 0),
        toSummaryRow("created_at", "created", supportDiagnostics.job_diagnostic.created_at || "unknown"),
        toSummaryRow("started_at", "started", supportDiagnostics.job_diagnostic.started_at || "not started"),
        toSummaryRow("finished_at", "finished", supportDiagnostics.job_diagnostic.finished_at || "not finished"),
        toSummaryRow("can_retry", "can retry", supportDiagnostics.job_diagnostic.can_retry ? "yes" : "no"),
        toSummaryRow("can_cancel", "can cancel", supportDiagnostics.job_diagnostic.can_cancel ? "yes" : "no"),
        toSummaryRow("artifact_deleted_at", "artifact deleted", supportDiagnostics.job_diagnostic.artifact_deleted_at || "not deleted")
      ] : [
        toSummaryRow("job_diagnostic", "job diagnostic", "No job diagnostic loaded")
      ],
      job_diagnostic_cards: supportDiagnostics?.job_diagnostic ? [
        {
          id: "job_support_summary",
          title: supportDiagnostics.job_diagnostic.failure_category || "support summary",
          body: supportDiagnostics.job_diagnostic.summary || "No support summary available.",
          tone: supportDiagnostics.job_diagnostic.status === "failed" || supportDiagnostics.job_diagnostic.status === "canceled" ? "active" : "default"
        },
        ...((supportDiagnostics.job_diagnostic.next_actions || []).map((action, index) => ({
          id: `job_support_next_${index + 1}`,
          title: "Next action",
          body: action,
          tone: "default"
        })))
      ] : [
        {
          id: "job_support_empty",
          title: "No support diagnostic",
          body: "Load support diagnostics to explain blocked submission or failed run state.",
          tone: "default"
        }
      ],
      recent_failures: (supportDiagnostics?.recent_failed_jobs || []).map((job) => ({
        job_id: job?.job_id || null,
        status: job?.status || "unknown",
        provider_name: job?.provider_name || "unknown provider",
        retry_count: job?.retry_count ?? 0,
        project_id: job?.project_id || null,
        study_id: job?.study_id || null,
        run_id: job?.run_id || null,
        created_at: job?.created_at || null,
        started_at: job?.started_at || null,
        finished_at: job?.finished_at || null,
        last_error: job?.last_error || "No failure detail recorded."
      }))
    },
    decision_review_surface: {
      pill: {
        tone: mapDecisionReviewTone(selectedDecisionLog?.review_status || "draft"),
        label: selectedDecisionLog?.review_status || "draft"
      },
      review_summary: buildDecisionReviewSummary(selectedDecisionLog),
      comments: buildDecisionReviewComments(decisionComments)
    },
    json_panels: {
      request_payload: bridgeState?.request_payload || null,
      selected_job: selectedJob,
      last_api_response: lastApiResponse,
      derived_run_record: bridgeState?.derived_run_record || null,
      bridge_state: bridgeState || null,
      shell_state: bundle?.workspace_shell || null
    }
  };
}
