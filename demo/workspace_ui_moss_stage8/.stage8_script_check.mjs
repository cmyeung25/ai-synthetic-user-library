
    import {
      createStage8MonitorDemoState,
      deriveStage8MonitorBundle
    } from "../workspace_ui_shared/workspace_ui_adapter.mjs";

    const copy = {
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

    const eventLog = document.getElementById("event-log");
    const timeline = document.getElementById("timeline");
    const monitorStack = document.getElementById("monitor-stack");
    const queueBody = document.getElementById("queue-body");
    const draftSummary = document.getElementById("draft-summary");
    const adapterSummary = document.getElementById("adapter-summary");
    const artifactSummary = document.getElementById("artifact-summary");
    const failureSummary = document.getElementById("failure-summary");
    const draftJson = document.getElementById("draft-json");
    const adapterJson = document.getElementById("adapter-json");
    const runJson = document.getElementById("run-json");
    const monitorJson = document.getElementById("monitor-json");
    const sidecarStack = document.getElementById("sidecar-stack");
    const metricRunState = document.getElementById("metric-run-state");
    const metricMonitorStatus = document.getElementById("metric-monitor-status");
    const metricMonitorAction = document.getElementById("metric-monitor-action");
    const runPill = document.getElementById("run-pill");
    const monitorPill = document.getElementById("monitor-pill");
    const outcomePill = document.getElementById("outcome-pill");
    const outcomeBand = document.getElementById("outcome-band");
    const outcomeTitle = document.getElementById("outcome-title");
    const outcomeCopy = document.getElementById("outcome-copy");
    const actionQueue = document.getElementById("action-queue");
    const actionLease = document.getElementById("action-lease");
    const actionStart = document.getElementById("action-start");
    const actionComplete = document.getElementById("action-complete");
    const actionFail = document.getElementById("action-fail");
    const actionRetry = document.getElementById("action-retry");

    let state = {};

    function resetState() {
      state = createStage8MonitorDemoState();
    }

    function pushEvent(type, at, detail) {
      state.events.unshift({ type, at, detail });
      state.events = state.events.slice(0, 8);
    }

    function renderRows(node, rows) {
      node.innerHTML = "";
      rows.forEach(([label, value]) => {
        const row = document.createElement("div");
        row.className = "summary-row";
        row.innerHTML = `<strong>${label}</strong><span>${value}</span>`;
        node.appendChild(row);
      });
    }

    function renderStack(node, rows) {
      node.innerHTML = "";
      rows.forEach(([label, value]) => {
        const row = document.createElement("div");
        row.className = "stack-row";
        row.innerHTML = `<strong>${label}</strong><span>${value}</span>`;
        node.appendChild(row);
      });
    }

    function renderTimeline(items) {
      timeline.innerHTML = "";
      items.forEach((item) => {
        const card = document.createElement("div");
        card.className = `timeline-card${item.state === "active" ? " active" : ""}`;
        card.innerHTML = `<h4>${item.step}</h4><p>${item.state}</p>`;
        timeline.appendChild(card);
      });
    }

    function renderEvents() {
      eventLog.innerHTML = "";
      state.events.forEach((event) => {
        const item = document.createElement("div");
        item.className = "event-item";
        item.innerHTML = `<strong>${event.type}</strong><span>${event.at} - ${event.detail}</span>`;
        eventLog.appendChild(item);
      });
    }

    function render(bundle) {
      const monitor = bundle.run_monitor;

      metricRunState.textContent = bundle.adapter.run_state;
      metricMonitorStatus.textContent = monitor.status;
      metricMonitorAction.textContent = monitor.primary_action_type;
      runPill.className = `status-pill ${monitor.pill_class}`;
      runPill.textContent = monitor.status;
      monitorPill.className = `status-pill ${monitor.pill_class}`;
      monitorPill.textContent = monitor.monitor_phase;
      outcomePill.className = `status-pill ${monitor.pill_class}`;
      outcomePill.textContent = monitor.results_available ? "artifacts ready" : monitor.retry_available ? "retry needed" : "in progress";

      renderEvents();
      renderTimeline(monitor.timeline);
      renderStack(monitorStack, [
        ["Monitor phase", monitor.monitor_phase],
        ["Queue position", monitor.queue_position ?? "-"],
        ["Worker", monitor.worker_id || "-"],
        ["Current step", monitor.current_step || "-"],
        ["Attempt", String(monitor.attempt_count)]
      ]);

      queueBody.innerHTML = `
        <tr>
          <td>${bundle.run_record.job_id}</td>
          <td><span class="status-pill ${monitor.pill_class}">${monitor.status}</span></td>
          <td>${monitor.worker_id || "-"}</td>
          <td>${monitor.current_step || "-"}</td>
          <td>${monitor.attempt_count}</td>
        </tr>
      `;

      renderRows(draftSummary, [
        ["Primary mode", bundle.draft.inference.primary_mode],
        ["Execution status", bundle.draft.proposed_run.execution_status],
        ["First task", bundle.draft.proposed_run.first_task || "-"]
      ]);
      renderRows(adapterSummary, [
        ["UI phase", bundle.adapter.ui_phase],
        ["Run state", bundle.adapter.run_state],
        ["Primary button", bundle.adapter.primary_button.action_type],
        ["Waiting for", bundle.adapter.visible_waiting_for.join(", ") || "-"]
      ]);
      renderRows(artifactSummary, [
        ["Artifacts ready", monitor.artifact_refs.length ? "yes" : "not yet"],
        ["Artifact refs", monitor.artifact_refs.join(", ") || "-"]
      ]);
      renderRows(failureSummary, [
        ["Failure reason", monitor.failure_reason || "-"],
        ["Retry available", monitor.retry_available ? "yes" : "no"],
        ["Secondary action", monitor.secondary_action_type]
      ]);

      if (monitor.status === "ready_to_queue") {
        outcomeBand.className = "decision-band ready";
        outcomeTitle.textContent = "Ready to queue";
        outcomeCopy.textContent = "The draft is confirmed enough to create a queue record. Post-queue visibility is the next operator need.";
      } else if (monitor.status === "completed") {
        outcomeBand.className = "decision-band ready";
        outcomeTitle.textContent = "Completed";
        outcomeCopy.textContent = "Artifacts are ready for review inside the same workspace flow.";
      } else if (monitor.status === "failed") {
        outcomeBand.className = "decision-band blocked";
        outcomeTitle.textContent = "Failed";
        outcomeCopy.textContent = "The run stopped before artifact completion. The operator should review the visible failure reason and decide whether to retry.";
      } else {
        outcomeBand.className = "decision-band warn";
        outcomeTitle.textContent = "In progress";
        outcomeCopy.textContent = "The run is active. The operator should see queue or worker progress without leaving the workspace.";
      }

      renderStack(sidecarStack, [
        ["Status", monitor.status],
        ["Primary action", monitor.primary_action_type],
        ["Secondary action", monitor.secondary_action_type],
        ["Artifacts", monitor.artifact_refs.length ? String(monitor.artifact_refs.length) : "0"]
      ]);

      draftJson.textContent = JSON.stringify(bundle.draft, null, 2);
      adapterJson.textContent = JSON.stringify(bundle.adapter, null, 2);
      runJson.textContent = JSON.stringify(bundle.run_record, null, 2);
      monitorJson.textContent = JSON.stringify(bundle.run_monitor, null, 2);

      actionQueue.disabled = monitor.status !== "ready_to_queue";
      actionLease.disabled = monitor.status !== "queued";
      actionStart.disabled = monitor.status !== "leased";
      actionComplete.disabled = monitor.status !== "running";
      actionFail.disabled = monitor.status !== "running";
      actionRetry.disabled = monitor.status !== "failed";
    }

    function recompute() {
      render(deriveStage8MonitorBundle({
        monitorState: state,
        copy,
        localUiState: {
          locale: "en",
          active_panel: "run_monitor"
        }
      }));
    }

    actionQueue.addEventListener("click", () => {
      state.lifecycle = "queued";
      state.attemptCount = 1;
      state.failureReason = null;
      pushEvent("queued", "22:13", "Confirmed draft became a queued run record.");
      recompute();
    });

    actionLease.addEventListener("click", () => {
      state.lifecycle = "leased";
      pushEvent("leased", "22:14", "A worker lease was created for this run.");
      recompute();
    });

    actionStart.addEventListener("click", () => {
      state.lifecycle = "running";
      pushEvent("running", "22:16", "The worker started executing the persona panel.");
      recompute();
    });

    actionComplete.addEventListener("click", () => {
      state.lifecycle = "completed";
      pushEvent("completed", "22:19", "Artifacts are now available for workspace review.");
      recompute();
    });

    actionFail.addEventListener("click", () => {
      state.lifecycle = "failed";
      state.failureReason = "stimulus_capture_timeout";
      pushEvent("failed", "22:21", "The worker timed out during stimulus capture.");
      recompute();
    });

    actionRetry.addEventListener("click", () => {
      state.lifecycle = "queued";
      state.attemptCount += 1;
      state.failureReason = null;
      pushEvent("retried", "22:23", "The operator retried the run after inspecting the failure.");
      recompute();
    });

    document.getElementById("action-reset").addEventListener("click", () => {
      resetState();
      recompute();
    });

    resetState();
    recompute();
  