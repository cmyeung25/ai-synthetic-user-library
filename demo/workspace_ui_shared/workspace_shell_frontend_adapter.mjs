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
    toSummaryRow("path", "path", selectedResult?.artifact_path || linkedArtifact?.artifact_path)
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

  return cards;
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

export function deriveWorkspaceShellFrontendAdapter({
  bundle,
  bridgeState,
  selectedJob = null,
  mode = "sample",
  lastApiResponse = null,
  reviewQueryState = null,
  querySource = "local"
}) {
  const effectiveReviewQueryState = reviewQueryState || bundle?.evidence_query || {};
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
      }
    },
    request_summary: [
      toSummaryRow("brief_path", "brief_path", bridgeState?.request_payload?.brief_path),
      toSummaryRow("persona_dir", "persona_dir", bridgeState?.request_payload?.persona_dir),
      toSummaryRow("panel_type", "panel_type", bridgeState?.request_payload?.panel_spec?.panel_type),
      toSummaryRow("sample_size", "sample_size", bridgeState?.request_payload?.panel_spec?.sample_size)
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
      toSummaryRow("output_run_path", "output_run_path", selectedJob.output_run_path),
      toSummaryRow("last_error", "last_error", selectedJob.last_error)
    ] : [
      toSummaryRow("job", "Job", "No job selected")
    ],
    draft_summary: [
      toSummaryRow("mode", "mode", bundle?.draft?.inference?.primary_mode),
      toSummaryRow("first_task", "first task", bundle?.draft?.proposed_run?.first_task || "not set"),
      toSummaryRow("confirmation", "confirmation", bundle?.draft?.confirmation?.status),
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
      replay_steps: buildReplaySteps(effectiveReviewQueryState),
      replay_note: (effectiveReviewQueryState?.replay_sequence || []).length
        ? "Replay remains limited to artifacts that actually carry trace-linked steps."
        : "No replay-linked steps are available for the current selection."
    },
    shell_projection: {
      active_surface: shellSurface,
      section_status: bundle?.workspace_shell?.section_status || {},
      review_ready: Boolean(bundle?.workspace_shell?.review_ready)
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
