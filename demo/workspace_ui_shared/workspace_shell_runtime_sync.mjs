import {
  loadWorkspaceShellSnapshot
} from "./workspace_shell_runtime_client.mjs";

function nowIso(now) {
  return now().toISOString();
}

function heartbeatTone(status) {
  if (status === "attention" || status === "missing_token") {
    return "failed";
  }
  if (status === "syncing") {
    return "running";
  }
  if (status === "live_synced" || status === "session_synced") {
    return "completed";
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

export function createWorkspaceShellRuntimeSyncState({
  autoRefreshEnabled = false,
  intervalMs = 4000
} = {}) {
  return {
    auto_refresh_enabled: autoRefreshEnabled,
    interval_ms: intervalMs,
    is_syncing: false,
    last_synced_at: null,
    last_action: "idle",
    heartbeat_status: "idle",
    sync_count: 0
  };
}

export function deriveWorkspaceShellRuntimeSyncView(syncState = {}) {
  return {
    pill: {
      tone: heartbeatTone(syncState.heartbeat_status),
      label: syncState.heartbeat_status || "idle"
    },
    actions: {
      toggle_auto_refresh: {
        intent: syncState.auto_refresh_enabled ? "stop_auto_refresh" : "start_auto_refresh",
        enabled: true
      },
      sync_now: {
        intent: "sync_now",
        enabled: !syncState.is_syncing
      }
    },
    summary: [
      toSummaryRow("auto_refresh", "auto refresh", syncState.auto_refresh_enabled ? "on" : "off"),
      toSummaryRow("interval_ms", "interval ms", syncState.interval_ms),
      toSummaryRow("last_action", "last action", syncState.last_action),
      toSummaryRow("last_synced_at", "last synced at", syncState.last_synced_at),
      toSummaryRow("sync_count", "sync count", syncState.sync_count)
    ]
  };
}

export async function syncWorkspaceShellRuntime({
  state,
  apiBaseUrl,
  bearerToken,
  queryState = {},
  selectedResultId,
  selectedReplayStepId,
  selectedComparisonRunId,
  fetchImpl = fetch,
  now = () => new Date()
}) {
  const syncState = state.runtimeSync || createWorkspaceShellRuntimeSyncState();
  const token = String(bearerToken || "").trim();
  if (!token) {
    return {
      ...state,
      runtimeSync: {
        ...syncState,
        is_syncing: false,
        heartbeat_status: "missing_token",
        last_action: "await_token"
      }
    };
  }

  let nextState = {
    ...state,
    runtimeSync: {
      ...syncState,
      is_syncing: true,
      heartbeat_status: "syncing"
    }
  };

  nextState = await loadWorkspaceShellSnapshot({
    state: nextState,
    apiBaseUrl,
    bearerToken: token,
    queryText: queryState.queryText || "",
    activeFamily: queryState.activeFamily || "all",
    sortBy: queryState.sortBy || "relevance",
    selectedResultId: selectedResultId ?? nextState.liveEvidenceQuery?.selected_result_id ?? "",
    selectedReplayStepId: selectedReplayStepId ?? nextState.liveEvidenceQuery?.selected_replay_step_id ?? "",
    selectedComparisonRunId: selectedComparisonRunId ?? nextState.liveEvidenceQuery?.cross_run_comparison?.selected_comparison_run_id ?? "",
    fetchImpl
  });
  let lastAction = "load_workspace_shell_snapshot";

  if (nextState.sessionError || nextState.liveError) {
    return {
      ...nextState,
      runtimeSync: {
        ...nextState.runtimeSync,
        is_syncing: false,
        heartbeat_status: "attention",
        last_action: lastAction,
        last_synced_at: nowIso(now),
        sync_count: (syncState.sync_count || 0) + 1
      }
    };
  }

  const hasError = Boolean(nextState.sessionError || nextState.liveError);
  return {
    ...nextState,
    runtimeSync: {
      ...nextState.runtimeSync,
      is_syncing: false,
      heartbeat_status: hasError
        ? "attention"
        : nextState.mode === "live"
          ? "live_synced"
          : "session_synced",
      last_action: lastAction,
      last_synced_at: nowIso(now),
      sync_count: (syncState.sync_count || 0) + 1
    }
  };
}
