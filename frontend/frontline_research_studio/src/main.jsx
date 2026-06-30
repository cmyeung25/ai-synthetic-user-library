import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./main.css";

const api = async (path, options = {}) => {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const payload = response.status === 204 ? {} : await response.json();
  if (!response.ok) {
    throw new Error(payload.message || payload.error || `Request failed: ${response.status}`);
  }
  return payload;
};

const optionalApi = async (path) => {
  try {
    return await api(path);
  } catch {
    return null;
  }
};

const decodePart = (value) => {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
};

const parseStudioRoute = (pathname = "/studio") => {
  const normalized = (pathname || "/studio").replace(/\/+$/, "") || "/studio";
  const parts = normalized.split("/").filter(Boolean).map(decodePart);
  if (parts.length === 1 && parts[0] === "studio") {
    return { route_path: "/studio", route_kind: "workspace" };
  }
  if (parts[0] !== "studio") {
    return { route_path: "/studio", route_kind: "workspace" };
  }
  if (parts.length === 2 && parts[1] === "projects") {
    return { route_path: normalized, route_kind: "projects" };
  }
  if (parts.length === 3 && parts[1] === "projects") {
    return { route_path: normalized, route_kind: "project", project_id: parts[2] };
  }
  if (parts.length === 3 && parts[1] === "studies" && parts[2] === "new") {
    return { route_path: normalized, route_kind: "new_study" };
  }
  if (parts.length >= 3 && parts[1] === "studies") {
    const studyId = parts[2];
    if (parts.length === 3) {
      return { route_path: normalized, route_kind: "study", study_id: studyId };
    }
    if (parts.length === 4 && parts[3] === "setup") {
      return { route_path: normalized, route_kind: "study_setup", study_id: studyId };
    }
    if (parts.length === 4 && parts[3] === "runs") {
      return { route_path: normalized, route_kind: "study_runs", study_id: studyId };
    }
    if (parts.length === 5 && parts[3] === "runs") {
      return { route_path: normalized, route_kind: "run", study_id: studyId, run_id: parts[4] };
    }
    if (parts.length === 4 && parts[3] === "evidence") {
      return { route_path: normalized, route_kind: "study_evidence", study_id: studyId };
    }
    if (parts.length === 5 && parts[3] === "evidence-views") {
      return { route_path: normalized, route_kind: "evidence_view", study_id: studyId, evidence_view_id: parts[4] };
    }
    if (parts.length === 5 && parts[3] === "reports") {
      return { route_path: normalized, route_kind: "study_report", study_id: studyId, study_report_id: parts[4] };
    }
    if (parts.length === 5 && parts[3] === "decisions") {
      return { route_path: normalized, route_kind: "decision", study_id: studyId, decision_log_id: parts[4] };
    }
  }
  if (parts.length === 2 && parts[1] === "share") {
    return { route_path: normalized, route_kind: "share_collection" };
  }
  if (parts.length === 3 && parts[1] === "share") {
    return { route_path: normalized, route_kind: "share", share_bundle_id: parts[2] };
  }
  return { route_path: "/studio", route_kind: "workspace" };
};

const serverRouteContext = window.__FRONTLINE_ROUTE_CONTEXT__ || parseStudioRoute(window.location.pathname);

const STUDY_ROUTE_KINDS = new Set([
  "study",
  "study_setup",
  "study_runs",
  "run",
  "study_evidence",
  "evidence_view",
  "study_report",
  "decision"
]);

const formatStudyStatus = (status) => ({
  draft: "Draft",
  planning: "Planning",
  ready: "Ready",
  ready_to_run: "Ready to run",
  running: "Running",
  review_ready: "Ready for evidence review",
  reviewing: "Reviewing evidence",
  completed: "Completed",
  blocked: "Blocked",
  archived: "Archived"
}[status] || status || "-");

const formatRunStatus = (status) => ({
  queued: "Queued to start",
  running: "Running",
  completed: "Ready for evidence review",
  failed: "Needs attention",
  canceled: "Canceled"
}[status] || status || "Not started");

const formatStudyType = (mode) => ({
  concept_validation: "Concept validation",
  prototype_validation: "Prototype comprehension",
  pain_point_discovery: "Pain, empathy, and insight discovery",
  explore_root_cause: "Root-cause exploration",
  decision_reconstruction: "Decision reconstruction",
  validate_hypothesis: "Hypothesis validation",
  adoption_barrier_validation: "Adoption barrier review",
  workflow_mapping: "Workflow mapping"
}[mode] || "Inferred from your question");

const formatReportStatus = (status) => ({
  draft: "Draft",
  ready_for_review: "Ready for review",
  final: "Final"
}[status] || status || "Report");

const DEFAULT_EVIDENCE_QUERY = "";

const runIdFromRecord = (record) => String(record?.metadata?.run_id || record?.run_id || "");

const runIdentifier = (record) => runIdFromRecord(record) || String(record?.job_id || "");

const matchesRunIdentifier = (record, identifier) => {
  const value = String(identifier || "");
  if (!value) return false;
  return [runIdFromRecord(record), record?.run_id, record?.job_id]
    .map((item) => String(item || ""))
    .some((item) => item === value);
};

const findRunByRouteIdentifier = (runs, identifier) => (
  runs.find((run) => matchesRunIdentifier(run, identifier))
);

const completedStudyRuns = (runs) => runs.filter((run) => String(run?.status || "") === "completed" && runIdFromRecord(run));

const latestCompletedStudyRun = (runs) => completedStudyRuns(runs)[0] || null;

const pickEvidenceSourceRun = (route, runs, routeEvidenceView) => {
  if (route?.run_id) {
    return findRunByRouteIdentifier(runs, route.run_id) || null;
  }
  if (routeEvidenceView?.job_id) {
    return findRunByRouteIdentifier(runs, routeEvidenceView.job_id) || null;
  }
  if (routeEvidenceView?.run_id) {
    return findRunByRouteIdentifier(runs, routeEvidenceView.run_id) || null;
  }
  return latestCompletedStudyRun(runs) || runs[0] || null;
};

const evidenceQueryUrl = (run, options = {}) => {
  const params = new URLSearchParams();
  if (run?.job_id) {
    params.set("job_id", String(run.job_id));
  } else if (runIdFromRecord(run)) {
    params.set("run_id", runIdFromRecord(run));
  }
  params.set("query_text", options.queryText || DEFAULT_EVIDENCE_QUERY);
  params.set("active_family", options.activeFamily || "all");
  params.set("sort_by", options.sortBy || "relevance");
  if (options.selectedResultId) params.set("selected_result_id", options.selectedResultId);
  if (options.selectedReplayStepId) params.set("selected_replay_step_id", options.selectedReplayStepId);
  if (options.selectedComparisonRunId) params.set("selected_comparison_run_id", options.selectedComparisonRunId);
  return `/api/v1/evidence-query?${params.toString()}`;
};

const cleanEvidenceCopy = (value) => String(value || "")
  .replace(/\bstage\b/gi, "step")
  .replace(/\boperator\b/gi, "reviewer")
  .replace(/\bprovider\b/gi, "execution source")
  .replace(/\bpayload\b/gi, "record")
  .replace(/\bdebug\b/gi, "diagnostic")
  .replace(/\bjob\b/gi, "research attempt")
  .replace(/\bruntime\b/gi, "execution");

const humanizeStatus = (value, fallback = "Review") => {
  const text = cleanEvidenceCopy(String(value || "").replaceAll("_", " ").trim());
  return text || fallback;
};

const boundarySentence = (value, fallback = "Synthetic evidence only. Do not treat this as human market proof.") => (
  cleanEvidenceCopy(value || fallback)
);

const normalizeLines = (value) => String(value || "")
  .split(/\r?\n|;/)
  .map((item) => item.trim())
  .filter(Boolean);

const linesToText = (value) => (
  Array.isArray(value)
    ? value.map((item) => String(item || "").trim()).filter(Boolean).join("\n")
    : String(value || "")
);

const prependUniqueBy = (items, key, item) => {
  if (!item?.[key]) return items;
  return [item, ...items.filter((existing) => existing?.[key] !== item[key])];
};

const buildTargetAudiencePayload = (draft) => {
  const base = String(draft.targetParticipant || "").trim() || "Synthetic participants matching the study target segment.";
  const inclusionCriteria = normalizeLines(draft.audienceCriteria);
  const excludedContext = String(draft.audienceExclusions || "").trim();
  return {
    contract_version: "target-audience/v0-draft",
    summary: base,
    inclusion_criteria: inclusionCriteria,
    excluded_context: excludedContext,
    selection_boundary: "Synthetic participants are simulated for directional research only; this is not a recruited human sample."
  };
};

const buildPersonaPanelPayload = (draft, personaLibrary) => {
  const defaultSelection = personaLibrary?.default_selection || {};
  const selectedPersonaIds = (draft.selectedPersonaIds?.length
    ? draft.selectedPersonaIds
    : defaultSelection.selected_persona_ids || []
  ).map((item) => String(item || "").trim()).filter(Boolean);
  const personas = Array.isArray(personaLibrary?.personas) ? personaLibrary.personas : [];
  const selectedPersonas = personas
    .filter((persona) => selectedPersonaIds.includes(persona.synthetic_user_id))
    .map((persona) => ({
      synthetic_user_id: persona.synthetic_user_id,
      name: persona.name,
      panel_role: persona.panel_role,
      occupation: persona.occupation,
      location: persona.location,
      life_stage: persona.life_stage,
      workflow_maturity: persona.workflow_maturity,
      trust_threshold: persona.trust_threshold,
      proof_threshold: persona.proof_threshold
    }));
  return {
    contract_version: "persona-panel-selection/v0-draft",
    panel_type: draft.selectedPanelType || personaLibrary?.active_panel_type || defaultSelection.panel_type || "mainstream",
    sample_size: selectedPersonaIds.length || Number(draft.personaSampleSize || personaLibrary?.sample_size || 1),
    random_seed: Number(draft.personaRandomSeed || personaLibrary?.random_seed || 17),
    selected_persona_ids: selectedPersonaIds,
    filters: selectedPersonaIds.length ? { synthetic_user_id: selectedPersonaIds } : {},
    selected_personas: selectedPersonas,
    selection_mode: selectedPersonaIds.length ? "user_selected" : "system_suggested",
    selection_rationale: defaultSelection.selection_rationale || "Selected from the Frontline persona library.",
    coverage_snapshot: personaLibrary?.library_summary?.human_difference_axis_summary || {},
    synthetic_boundary: "Persona selection improves simulation coverage, but it does not create recruited human evidence."
  };
};

const externalizeEvidenceTitle = (item) => {
  const title = cleanEvidenceCopy(item?.title || "Evidence");
  const normalized = title.toLowerCase();
  if (normalized.includes("raw responses")) return "Synthetic participant responses";
  if (normalized.includes("stage results")) return "Execution progress evidence";
  if (normalized.includes("run contract")) return "Attempt provenance record";
  if (normalized.includes("run manifest")) return "Attempt record";
  if (normalized.includes("planner")) return "Research planning trace";
  return title;
};

const displayEvidenceFamily = (family) => ({
  all: "All evidence",
  input: "Source inputs",
  trace: "Behavior or response trace",
  analysis: "Interpretation",
  output: "Summary output"
}[family] || cleanEvidenceCopy(String(family || "Evidence").replaceAll("_", " ")));

const evidenceDetailLines = (result) => (
  Array.isArray(result?.detail_lines) ? result.detail_lines.map(cleanEvidenceCopy).filter(Boolean) : []
);

const externalizeActionError = (message = "") => {
  const text = String(message).toLowerCase();
  if (text.includes("plan")) {
    return "Approve a research plan before starting a run.";
  }
  if (text.includes("billing") || text.includes("quota") || text.includes("limit")) {
    return "This workspace cannot start another run right now. Check your plan limits or try again later.";
  }
  if (text.includes("not found") || text.includes("not visible")) {
    return "This study is no longer available in the current workspace.";
  }
  return "The research action could not be completed yet. Review the study context and try again.";
};

const nextActionForStudy = (study) => {
  if (!study) return { label: "Start a new study", path: "/studio/studies/new" };
  if (["draft", "planning"].includes(study.status)) {
    return { label: "Continue setup", path: `/studio/studies/${study.study_id}/setup` };
  }
  if (study.status === "ready_to_run") {
    return { label: "Start research run", path: `/studio/studies/${study.study_id}/setup` };
  }
  if (study.status === "running") {
    return { label: "View run progress", path: `/studio/studies/${study.study_id}/runs` };
  }
  if (study.status === "reviewing") {
    return { label: "Review evidence", path: `/studio/studies/${study.study_id}/evidence` };
  }
  return { label: "Open decision", path: `/studio/studies/${study.study_id}` };
};

function App() {
  const loadSequenceRef = useRef(0);
  const [routeContext, setRouteContext] = useState(() => ({
    ...parseStudioRoute(window.location.pathname),
    ...serverRouteContext
  }));
  const [model, setModel] = useState({
    loading: true,
    error: "",
    session: null,
    projects: [],
    studies: [],
    jobs: [],
    exportBundles: [],
    studyReports: [],
    evidenceViews: [],
    decisionLogs: [],
    shareBundles: [],
    personaLibrary: null,
    routeObjects: {},
    evidenceQuery: null,
    evidenceQueryJobId: "",
    evidenceQueryRunId: "",
    evidenceQueryError: ""
  });
  const [draft, setDraft] = useState({
    intent: "I need to test whether a founder concept is understandable, trusted, and worth trying.",
    projectName: "Frontline Research",
    projectDescription: "Product research context for synthetic evidence review.",
    studyTitle: "Concept validation study",
    newProjectName: "New research project",
    selectedProjectId: "",
    studyPurpose: "Decide whether this should move forward, what creates hesitation, and what needs human follow-up.",
    targetParticipant: "Potential early adopters who match the problem context.",
    audienceCriteria: "Feels the problem in a recent workflow\nCan describe current workaround or switching cost",
    audienceExclusions: "Do not treat synthetic participants as recruited market proof.",
    artifactNotes: "No external artifact yet; evaluate the concept from the description.",
    selectedPanelType: "mainstream",
    selectedPersonaIds: [],
    personaSampleSize: 3,
    personaRandomSeed: 17,
    guideQuestions: "What do you understand this is trying to help with?\nWhere would trust, effort, or setup risk appear?\nWhat would you need to see before trying it?",
    guideFocus: "Probe current behavior first, then test concept clarity, trust gaps, adoption barriers, and human-validation follow-up.",
    decisionSummary: "Current belief: the concept is worth exploring, but I still need human validation before treating it as market proof.",
    decisionRationale: "The evidence is directionally useful, but it should guide the next validation step rather than become a launch claim.",
    confidenceBoundary: "Confidence is directional only because the supporting evidence is synthetic and still needs human validation.",
    humanFollowUp: "Run targeted human interviews or prototype tests around the strongest objections before making a customer-facing claim.",
    proposal: null,
    revision: null,
    latestRun: null,
    actionError: "",
    actionNotice: ""
  });
  const [evidenceControls, setEvidenceControls] = useState({
    queryText: DEFAULT_EVIDENCE_QUERY,
    activeFamily: "all",
    sortBy: "relevance"
  });

  const navigate = (path, options = {}) => {
    const target = parseStudioRoute(path);
    const targetPath = target.route_path;
    if (options.replace) {
      window.history.replaceState({}, "", targetPath);
    } else {
      window.history.pushState({}, "", targetPath);
    }
    setRouteContext(target);
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  const loadWorkspace = async (route) => {
    const activeRoute = { ...route, ...parseStudioRoute(window.location.pathname) };
    const loadSequence = loadSequenceRef.current + 1;
    loadSequenceRef.current = loadSequence;
    setModel((current) => ({ ...current, loading: !current.session, error: "" }));
    try {
      const personaLibraryPath = `/api/v1/persona-library?panel_type=${encodeURIComponent(draft.selectedPanelType || "mainstream")}&sample_size=${encodeURIComponent(String(draft.personaSampleSize || 3))}&random_seed=${encodeURIComponent(String(draft.personaRandomSeed || 17))}`;
      const shouldLoadPersonaLibrary = ["new_study", "study_setup"].includes(activeRoute.route_kind);
      const [
        sessionPayload,
        projectsPayload,
        studiesPayload,
        jobsPayload,
        personaPayload
      ] = await Promise.all([
        api("/api/v1/session"),
        api("/api/v1/projects"),
        api("/api/v1/studies"),
        api("/api/v1/validation-jobs"),
        shouldLoadPersonaLibrary ? optionalApi(personaLibraryPath) : Promise.resolve(null)
      ]);
    const projects = projectsPayload.projects || [];
    const studies = studiesPayload.studies || [];
    const jobs = jobsPayload.jobs || [];
    const routeObjects = {};
    if (activeRoute.study_report_id) {
      const payload = await optionalApi(`/api/v1/study-reports/${encodeURIComponent(activeRoute.study_report_id)}`);
      routeObjects.studyReport = payload?.study_report || null;
    }
    if (activeRoute.evidence_view_id) {
      const payload = await optionalApi(`/api/v1/evidence-views/${encodeURIComponent(activeRoute.evidence_view_id)}`);
      routeObjects.evidenceView = payload?.evidence_view || null;
    }
    if (activeRoute.decision_log_id) {
      const payload = await optionalApi(`/api/v1/decision-logs/${encodeURIComponent(activeRoute.decision_log_id)}`);
      routeObjects.decisionLog = payload?.decision_log || null;
      routeObjects.decisionComments = payload?.decision_comments || [];
    }
    if (activeRoute.share_bundle_id) {
      const payload = await optionalApi(`/api/v1/share-bundles/${encodeURIComponent(activeRoute.share_bundle_id)}`);
      routeObjects.shareBundle = payload?.share_bundle || null;
    }

    const selectedStudyId = activeRoute.study_id
      || routeObjects.studyReport?.study_id
      || routeObjects.evidenceView?.study_id
      || routeObjects.decisionLog?.study_id
      || routeObjects.shareBundle?.study_id
      || "";
    const selectedStudy = studies.find((study) => study.study_id === selectedStudyId);
    const selectedProjectId = activeRoute.project_id
      || selectedStudy?.project_id
      || routeObjects.shareBundle?.project_id
      || projects[0]?.project_id
      || "";

    const [reportsPayload, viewsPayload, decisionsPayload, exportsPayload, sharesPayload] = selectedStudyId
      ? await Promise.all([
          api(`/api/v1/study-reports?study_id=${encodeURIComponent(selectedStudyId)}`),
          api(`/api/v1/evidence-views?study_id=${encodeURIComponent(selectedStudyId)}`),
          api(`/api/v1/decision-logs?study_id=${encodeURIComponent(selectedStudyId)}`),
          api(`/api/v1/export-bundles?study_id=${encodeURIComponent(selectedStudyId)}`),
          api(`/api/v1/share-bundles?study_id=${encodeURIComponent(selectedStudyId)}`)
        ])
      : [{ study_reports: [] }, { evidence_views: [] }, { decision_logs: [] }, { export_bundles: [] }, { share_bundles: [] }];

    const selectedStudyRuns = selectedStudyId
      ? jobs.filter((job) => String(job?.metadata?.study_id || "") === selectedStudyId)
      : [];
    const routeEvidenceView = routeObjects.evidenceView || null;
    const evidenceSourceRun = selectedStudyId ? pickEvidenceSourceRun(activeRoute, selectedStudyRuns, routeEvidenceView) : null;
    const evidenceOptions = routeEvidenceView
      ? {
          queryText: routeEvidenceView.query_text || evidenceControls.queryText,
          activeFamily: routeEvidenceView.active_family || evidenceControls.activeFamily,
          sortBy: routeEvidenceView.sort_by || evidenceControls.sortBy,
          selectedResultId: routeEvidenceView.selected_result_id || "",
          selectedReplayStepId: routeEvidenceView.selected_replay_step_id || "",
          selectedComparisonRunId: routeEvidenceView.selected_comparison_run_id || ""
        }
      : evidenceControls;
    const shouldLoadEvidenceQuery = ["run", "study_evidence", "evidence_view"].includes(activeRoute.route_kind);
    const evidencePayload = evidenceSourceRun && shouldLoadEvidenceQuery
      ? await optionalApi(evidenceQueryUrl(evidenceSourceRun, evidenceOptions))
      : null;
    const evidenceQuery = evidencePayload?.query || null;

      if (loadSequence !== loadSequenceRef.current) return null;
      setModel({
        loading: false,
        error: "",
        session: sessionPayload.session,
        projects,
        studies,
        jobs,
        exportBundles: exportsPayload.export_bundles || [],
        personaLibrary: personaPayload?.persona_library || null,
        studyReports: reportsPayload.study_reports || [],
        evidenceViews: viewsPayload.evidence_views || [],
        decisionLogs: decisionsPayload.decision_logs || [],
        shareBundles: sharesPayload.share_bundles || [],
        routeObjects,
        evidenceQuery,
        evidenceQueryJobId: String(evidenceSourceRun?.job_id || ""),
        evidenceQueryRunId: runIdFromRecord(evidenceSourceRun) || "",
        evidenceQueryError: evidenceSourceRun && !evidenceQuery ? "Evidence is not ready for this research attempt yet." : "",
        selectedProjectId,
        selectedStudyId
      });
      return null;
    } catch (error) {
      if (loadSequence === loadSequenceRef.current) {
        setModel((current) => ({ ...current, loading: false, error: error.message }));
      }
      throw error;
    }
  };

  useEffect(() => {
    const onPopState = () => setRouteContext(parseStudioRoute(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadWorkspace(routeContext).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [
    routeContext.route_path,
    evidenceControls.queryText,
    evidenceControls.activeFamily,
    evidenceControls.sortBy,
    draft.selectedPanelType,
    draft.personaSampleSize,
    draft.personaRandomSeed
  ]);

  const defaultPersonaSelectionKey = (model.personaLibrary?.default_selection?.selected_persona_ids || []).join("|");

  useEffect(() => {
    const defaultIds = model.personaLibrary?.default_selection?.selected_persona_ids || [];
    if (!defaultIds.length || draft.selectedPersonaIds.length) return;
    setDraft((current) => (
      current.selectedPersonaIds.length
        ? current
        : {
            ...current,
            selectedPersonaIds: defaultIds,
            selectedPanelType: model.personaLibrary?.active_panel_type || current.selectedPanelType,
            personaSampleSize: model.personaLibrary?.default_selection?.sample_size || current.personaSampleSize
          }
    ));
  }, [defaultPersonaSelectionKey, draft.selectedPersonaIds.length, model.personaLibrary?.active_panel_type, model.personaLibrary?.default_selection?.sample_size]);

  const routeHasStudyContext = STUDY_ROUTE_KINDS.has(routeContext.route_kind);
  const selectedStudy = routeHasStudyContext
    ? model.studies.find((study) => study.study_id === (routeContext.study_id || model.selectedStudyId))
    : null;
  const selectedProject = model.projects.find((project) => {
    const projectId = routeContext.project_id || selectedStudy?.project_id || (routeContext.route_kind === "new_study" ? model.selectedProjectId : "");
    return project.project_id === projectId;
  });
  const studyRuns = model.jobs.filter((job) => String(job?.metadata?.study_id || "") === selectedStudy?.study_id);
  const selectedRun = findRunByRouteIdentifier(studyRuns, routeContext.run_id);
  const latestEvidenceView = model.evidenceViews[0];
  const latestExportBundle = model.exportBundles[0];
  const latestReport = model.studyReports[0];
  const latestDecision = model.decisionLogs[0];
  const latestShare = model.shareBundles[0];

  useEffect(() => {
    if (!selectedStudy?.study_id) return;
    const plan = selectedStudy.frontline?.latest_plan_revision
      || selectedStudy.frontline?.latest_plan_proposal
      || selectedStudy.draft_plan
      || {};
    const planMetadata = plan.metadata && typeof plan.metadata === "object" ? plan.metadata : {};
    const intake = selectedStudy.metadata?.planning_intake && typeof selectedStudy.metadata.planning_intake === "object"
      ? selectedStudy.metadata.planning_intake
      : {};
    const audience = plan.target_audience
      || planMetadata.target_audience
      || intake.target_audience
      || {};
    const guide = plan.moderator_interview_guide && typeof plan.moderator_interview_guide === "object"
      ? plan.moderator_interview_guide
      : {};
    const guideQuestions = linesToText(guide.questions || intake.moderator_questions || []);
    setDraft((current) => ({
      ...current,
      intent: selectedStudy.research_intent || current.intent,
      studyPurpose: plan.study_purpose || selectedStudy.desired_output || current.studyPurpose,
      targetParticipant: audience.summary || plan.target_persona || intake.target_participant || current.targetParticipant,
      audienceCriteria: linesToText(audience.inclusion_criteria) || current.audienceCriteria,
      audienceExclusions: audience.excluded_context || current.audienceExclusions,
      artifactNotes: linesToText(plan.artifact_refs || selectedStudy.artifact_refs) || intake.artifact_notes || current.artifactNotes,
      guideQuestions: guideQuestions || current.guideQuestions,
      guideFocus: guide.focus || planMetadata.guide_focus || intake.guide_focus || current.guideFocus
    }));
  }, [selectedStudy?.study_id]);

  const navLevel = selectedStudy
    ? "study"
    : selectedProject && ["project", "new_study"].includes(routeContext.route_kind)
      ? "project"
      : "projects";
  const projectStudies = selectedProject
    ? model.studies.filter((study) => study.project_id === selectedProject.project_id)
    : [];
  const navBackPath = navLevel === "study"
    ? selectedProject
      ? `/studio/projects/${selectedProject.project_id}`
      : "/studio/projects"
    : navLevel === "project"
      ? "/studio/projects"
      : "/studio";
  const studyReportPath = selectedStudy && latestReport
    ? `/studio/studies/${selectedStudy.study_id}/reports/${latestReport.study_report_id}`
    : selectedStudy
      ? `/studio/studies/${selectedStudy.study_id}/evidence`
      : "/studio";
  const studyDecisionPath = selectedStudy && latestDecision
    ? `/studio/studies/${selectedStudy.study_id}/decisions/${latestDecision.decision_log_id}`
    : selectedStudy
      ? `/studio/studies/${selectedStudy.study_id}`
      : "/studio";
  const sharePath = latestShare ? `/studio/share/${latestShare.share_bundle_id}` : "/studio/share";

  const navLink = ({ id, label, detail, path, active = false }) => (
    <a
      className={`ia-nav-item ${active ? "is-active" : ""}`}
      href={path}
      id={id}
      key={id}
      onClick={(event) => {
        event.preventDefault();
        navigate(path);
      }}
    >
      <span>{label}</span>
      {detail ? <small>{detail}</small> : null}
    </a>
  );

  const createProject = async () => {
    const payload = await api("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({
        name: draft.newProjectName,
        description: draft.projectDescription
      })
    });
    navigate(`/studio/projects/${payload.project.project_id}`);
  };

  const createProjectAndStudy = async () => {
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      let projectId = draft.selectedProjectId || selectedProject?.project_id || "";
      if (projectId === "__new__") projectId = "";
      if (!projectId) {
        const project = await api("/api/v1/projects", {
          method: "POST",
          body: JSON.stringify({
            name: draft.projectName,
            description: "Frontline user-facing research workspace."
          })
        });
        projectId = project.project.project_id;
      }
      const artifactRefs = draft.artifactNotes?.trim() ? [draft.artifactNotes.trim()] : [];
      const targetAudience = buildTargetAudiencePayload(draft);
      const personaPanel = buildPersonaPanelPayload(draft, model.personaLibrary);
      const moderatorQuestions = normalizeLines(draft.guideQuestions);
      const study = await api("/api/v1/studies", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          title: draft.studyTitle,
          research_intent: draft.intent,
          desired_output: draft.studyPurpose,
          first_task: "Turn this question into a confirmed synthetic research plan.",
          artifact_refs: artifactRefs,
          draft_plan: {
            status: "intake_draft",
            target_persona: targetAudience.summary,
            target_audience: targetAudience,
            persona_panel: personaPanel,
            artifact_notes: draft.artifactNotes,
            moderator_interview_guide: {
              contract_version: "moderator-interview-guide/v0-draft",
              questions: moderatorQuestions,
              focus: draft.guideFocus
            },
            expected_evidence_types: ["objections", "trust gaps", "adoption barriers", "contradictions", "human-validation gaps"]
          },
          metadata: {
            source: "frontline_research_studio",
            planning_intake: {
              target_participant: targetAudience.summary,
              target_audience: targetAudience,
              persona_panel: personaPanel,
              study_purpose: draft.studyPurpose,
              artifact_notes: draft.artifactNotes,
              moderator_questions: moderatorQuestions,
              guide_focus: draft.guideFocus
            }
          }
        })
      });
      setDraft((current) => ({ ...current, selectedProjectId: projectId, actionNotice: "Study draft saved. Review the plan before starting research." }));
      navigate(`/studio/studies/${study.study.study_id}/setup`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message) }));
    }
  };

  const proposePlan = async () => {
    if (!selectedStudy?.study_id) return;
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      const targetAudience = buildTargetAudiencePayload(draft);
      const personaPanel = buildPersonaPanelPayload(draft, model.personaLibrary);
      const payload = await api(`/api/v1/studies/${selectedStudy.study_id}/frontline-plan-proposals`, {
        method: "POST",
        body: JSON.stringify({
          user_message: draft.intent || selectedStudy.research_intent,
          study_purpose: draft.studyPurpose || selectedStudy.desired_output,
          target_persona: targetAudience.summary,
          target_audience: targetAudience,
          persona_panel: personaPanel,
          artifacts: draft.artifactNotes?.trim() ? [draft.artifactNotes.trim()] : [],
          moderator_questions: normalizeLines(draft.guideQuestions),
          metadata: {
            source: "frontline_research_studio",
            target_audience: targetAudience,
            persona_panel: personaPanel,
            guide_focus: draft.guideFocus
          }
        })
      });
      setDraft((current) => ({ ...current, proposal: payload.plan_proposal, actionNotice: "Draft plan is ready for review." }));
      if (payload.study) {
        setModel((current) => ({
          ...current,
          studies: prependUniqueBy(current.studies, "study_id", payload.study),
          selectedStudyId: payload.study.study_id || current.selectedStudyId
        }));
      }
      await loadWorkspace(routeContext);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message) }));
    }
  };

  const confirmPlan = async () => {
    if (!selectedStudy?.study_id) return;
    const proposalId = draft.proposal?.plan_proposal_id || selectedStudy?.frontline?.latest_plan_proposal_id || "";
    if (!proposalId) return;
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      const payload = await api(`/api/v1/studies/${selectedStudy.study_id}/frontline-plan-revisions`, {
        method: "POST",
        body: JSON.stringify({
          plan_proposal_id: proposalId,
          confirmation_note: "Approved from Frontline Studio.",
          metadata: { source: "frontline_research_studio" }
        })
      });
      setDraft((current) => ({ ...current, revision: payload.plan_revision, actionNotice: "Plan approved. You can start the research run now." }));
      if (payload.study) {
        setModel((current) => ({
          ...current,
          studies: prependUniqueBy(current.studies, "study_id", payload.study),
          selectedStudyId: payload.study.study_id || current.selectedStudyId
        }));
      }
      await loadWorkspace(routeContext);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message) }));
    }
  };

  const startResearchRun = async () => {
    if (!selectedStudy?.study_id) return;
    const studyId = selectedStudy.study_id;
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      const payload = await api(`/api/v1/studies/${studyId}/frontline-runs`, {
        method: "POST",
        body: JSON.stringify({
          metadata: { source: "frontline_research_studio" }
        })
      });
      navigate(`/studio/studies/${studyId}/runs`);
      setModel((current) => ({
        ...current,
        loading: false,
        jobs: payload.job ? prependUniqueBy(current.jobs, "job_id", payload.job) : current.jobs,
        studies: payload.study ? prependUniqueBy(current.studies, "study_id", payload.study) : current.studies,
        selectedStudyId: studyId
      }));
      setDraft((current) => ({
        ...current,
        latestRun: payload.job,
        actionNotice: "Research run started. Review progress under Research attempts."
      }));
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message) }));
    }
  };

  const createEvidenceView = async () => {
    if (!selectedStudy?.study_id) return;
    const sourceRun = findRunByRouteIdentifier(studyRuns, model.evidenceQueryJobId)
      || findRunByRouteIdentifier(studyRuns, model.evidenceQueryRunId)
      || selectedRun
      || latestCompletedStudyRun(studyRuns);
    if (!sourceRun || String(sourceRun.status || "") !== "completed") {
      setDraft((current) => ({
        ...current,
        actionError: "Complete a research attempt before saving an evidence view with provenance.",
        actionNotice: ""
      }));
      return;
    }
    try {
      const query = model.evidenceQuery || {};
      const payload = await api("/api/v1/evidence-views", {
        method: "POST",
        body: JSON.stringify({
          study_id: selectedStudy.study_id,
          job_id: sourceRun.job_id,
          title: `${selectedStudy.title} evidence view`,
          note: "Saved from Frontline Studio for later decision review.",
          query_text: query.query_text || evidenceControls.queryText,
          active_family: query.active_family || evidenceControls.activeFamily,
          sort_by: query.sort_by || evidenceControls.sortBy,
          selected_result_id: query.selected_result_id || "",
          selected_replay_step_id: query.selected_replay_step_id || "",
          selected_comparison_run_id: query.cross_run_comparison?.selected_comparison_run_id || "",
          metadata: {
            source: "frontline_research_studio",
            saved_from_route: routeContext.route_kind
          }
        })
      });
      setModel((current) => ({
        ...current,
        loading: false,
        evidenceViews: prependUniqueBy(current.evidenceViews, "evidence_view_id", payload.evidence_view),
        routeObjects: { ...current.routeObjects, evidenceView: payload.evidence_view }
      }));
      navigate(`/studio/studies/${selectedStudy.study_id}/evidence-views/${payload.evidence_view.evidence_view_id}`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message), actionNotice: "" }));
    }
  };

  const createStudyReport = async () => {
    if (!selectedStudy?.study_id) return;
    const includedRunIds = completedStudyRuns(studyRuns).map(runIdFromRecord).filter(Boolean);
    if (!includedRunIds.length) {
      setDraft((current) => ({
        ...current,
        actionError: "Complete at least one research attempt before creating a study report.",
        actionNotice: ""
      }));
      return;
    }
    try {
      const payload = await api("/api/v1/study-reports", {
        method: "POST",
        body: JSON.stringify({
          study_id: selectedStudy.study_id,
          included_run_ids: includedRunIds,
          title: `${selectedStudy.title} synthesis`,
          status: "ready_for_review",
          metadata: {
            source: "frontline_research_studio",
            evidence_view_count: model.evidenceViews.length
          }
        })
      });
      setModel((current) => ({
        ...current,
        loading: false,
        studyReports: prependUniqueBy(current.studyReports, "study_report_id", payload.study_report),
        routeObjects: { ...current.routeObjects, studyReport: payload.study_report }
      }));
      navigate(`/studio/studies/${selectedStudy.study_id}/reports/${payload.study_report.study_report_id}`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message), actionNotice: "" }));
    }
  };

  const createDecisionLog = async () => {
    if (!selectedStudy?.study_id) return;
    const sourceReport = model.routeObjects.studyReport || latestReport || null;
    const sourceEvidenceView = model.routeObjects.evidenceView || latestEvidenceView || null;
    const sourceRun = findRunByRouteIdentifier(studyRuns, sourceEvidenceView?.job_id)
      || findRunByRouteIdentifier(studyRuns, sourceEvidenceView?.run_id)
      || findRunByRouteIdentifier(studyRuns, model.evidenceQueryJobId)
      || latestCompletedStudyRun(studyRuns);
    if (!sourceRun || String(sourceRun.status || "") !== "completed") {
      setDraft((current) => ({
        ...current,
        actionError: "Complete a research attempt before recording a decision.",
        actionNotice: ""
      }));
      return;
    }
    try {
      const payload = await api("/api/v1/decision-logs", {
        method: "POST",
        body: JSON.stringify({
          study_id: selectedStudy.study_id,
          job_id: sourceEvidenceView?.job_id || sourceRun.job_id || "",
          evidence_view_id: sourceEvidenceView?.evidence_view_id || "",
          selected_result_id: sourceEvidenceView?.selected_result_id || model.evidenceQuery?.selected_result_id || "",
          selected_comparison_run_id: sourceEvidenceView?.selected_comparison_run_id || model.evidenceQuery?.cross_run_comparison?.selected_comparison_run_id || "",
          title: `${selectedStudy.title} decision`,
          decision_summary: draft.decisionSummary,
          rationale: draft.decisionRationale,
          metadata: {
            source: "frontline_research_studio",
            study_report_id: sourceReport?.study_report_id || "",
            plan_revision_id: selectedStudy.current_plan_revision_id || sourceReport?.included_plan_revision_ids?.[0] || "",
            confidence_boundary: draft.confidenceBoundary,
            human_follow_up: draft.humanFollowUp,
            evidence_basis_label: sourceEvidenceView
              ? "Saved evidence view with selected source slice and comparison context."
              : "Completed research attempt plus study report.",
            human_validation_gap_required: true
          }
        })
      });
      setModel((current) => ({
        ...current,
        loading: false,
        decisionLogs: prependUniqueBy(current.decisionLogs, "decision_log_id", payload.decision_log),
        routeObjects: {
          ...current.routeObjects,
          decisionLog: payload.decision_log,
          decisionComments: payload.decision_comments || []
        }
      }));
      navigate(`/studio/studies/${selectedStudy.study_id}/decisions/${payload.decision_log.decision_log_id}`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message), actionNotice: "" }));
    }
  };

  const createShareBundle = async () => {
    if (!selectedStudy?.study_id) return;
    const decision = model.routeObjects.decisionLog || latestDecision;
    if (!decision?.decision_log_id) {
      setDraft((current) => ({
        ...current,
        actionError: "Record a decision before creating a share view.",
        actionNotice: ""
      }));
      return;
    }
    const sourceRun = findRunByRouteIdentifier(studyRuns, decision.job_id)
      || findRunByRouteIdentifier(studyRuns, decision.run_id)
      || latestCompletedStudyRun(studyRuns);
    if (!sourceRun || String(sourceRun.status || "") !== "completed") {
      setDraft((current) => ({
        ...current,
        actionError: "Complete a research attempt before creating a share view.",
        actionNotice: ""
      }));
      return;
    }
    try {
      let exportBundle = model.exportBundles.find((bundle) => (
        String(bundle.job_id || "") === String(sourceRun.job_id || "")
        || String(bundle.run_id || "") === runIdFromRecord(sourceRun)
      ));
      if (!exportBundle) {
        const exportPayload = await api("/api/v1/export-bundles", {
          method: "POST",
          body: JSON.stringify({
            study_id: selectedStudy.study_id,
            job_id: sourceRun.job_id,
            title: `${selectedStudy.title} evidence package`,
            export_format: "bundle_json",
            metadata: {
              source: "frontline_research_studio",
              decision_log_id: decision.decision_log_id,
              study_report_id: decision.metadata?.study_report_id || latestReport?.study_report_id || "",
              evidence_view_id: decision.evidence_view_id || ""
            }
          })
        });
        exportBundle = exportPayload.export_bundle;
      }
      const sharePayload = await api("/api/v1/share-bundles", {
        method: "POST",
        body: JSON.stringify({
          export_bundle_id: exportBundle.export_bundle_id,
          title: `${selectedStudy.title} boundary share`,
          expires_in_days: 14,
          metadata: {
            source: "frontline_research_studio",
            decision_log_id: decision.decision_log_id,
            study_report_id: decision.metadata?.study_report_id || latestReport?.study_report_id || "",
            evidence_view_id: decision.evidence_view_id || "",
            confidence_boundary: decision.metadata?.confidence_boundary || draft.confidenceBoundary,
            human_follow_up: decision.metadata?.human_follow_up || draft.humanFollowUp
          }
        })
      });
      setModel((current) => ({
        ...current,
        loading: false,
        exportBundles: prependUniqueBy(current.exportBundles, "export_bundle_id", exportBundle),
        shareBundles: prependUniqueBy(current.shareBundles, "share_bundle_id", sharePayload.share_bundle),
        routeObjects: { ...current.routeObjects, shareBundle: sharePayload.share_bundle }
      }));
      navigate(`/studio/share/${sharePayload.share_bundle.share_bundle_id}`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message), actionNotice: "" }));
    }
  };

  const pageProps = {
    model,
    draft,
    setDraft,
    routeContext,
    selectedProject,
    selectedStudy,
    selectedRun,
    studyRuns,
    navigate,
    createProject,
    createProjectAndStudy,
    proposePlan,
    confirmPlan,
    startResearchRun,
    createEvidenceView,
    createStudyReport,
    createDecisionLog,
    createShareBundle,
    evidenceControls,
    setEvidenceControls
  };

  return (
    <main className="studio" data-route-kind={routeContext.route_kind} data-contract-version="frontline-research-studio/v1-route-shell">
      <aside className="studio-rail">
        <div className="rail-top">
          {navLevel === "projects" ? (
            <a className="rail-home-link" href="/studio" onClick={(event) => {
              event.preventDefault();
              navigate("/studio");
            }}>
              Frontline Research Studio
            </a>
          ) : (
            <button id="nav-back" className="back-button" type="button" onClick={() => navigate(navBackPath)}>
              <span aria-hidden="true">←</span>
              {navLevel === "study" ? "Back to project" : "Back to projects"}
            </button>
          )}
          <p className="kicker">{navLevel === "study" ? "Study workspace" : navLevel === "project" ? "Project workspace" : "Projects"}</p>
          <h1>{navLevel === "study" ? selectedStudy.title : navLevel === "project" ? selectedProject.name : "Choose a project"}</h1>
        </div>
        <div className="rail-scroll">
          {navLevel === "projects" ? (
            <nav className="context-nav nav-level" id="project-list" aria-label="Project list">
              {navLink({ id: "nav-projects", label: "All projects", path: "/studio/projects", detail: "Browse and create research contexts", active: routeContext.route_kind === "projects" })}
              {model.projects.length ? model.projects.slice(0, 8).map((project) => navLink({
                id: `project-nav-${project.project_id}`,
                label: project.name,
                path: `/studio/projects/${project.project_id}`,
                detail: `${project.study_count || 0} studies`,
                active: false
              })) : <p className="nav-empty">No projects yet.</p>}
            </nav>
          ) : null}
          {navLevel === "project" ? (
            <nav className="context-nav nav-level" id="project-study-list" aria-label="Project studies">
              {navLink({ id: "project-nav-overview", label: "Project overview", path: `/studio/projects/${selectedProject.project_id}`, detail: "Studies and open decisions", active: routeContext.route_kind === "project" })}
              {navLink({ id: "project-nav-new-study", label: "New study", path: "/studio/studies/new", detail: "Start from a research question", active: routeContext.route_kind === "new_study" })}
              <span className="ia-nav-label">Studies</span>
              {projectStudies.length ? projectStudies.slice(0, 10).map((study) => navLink({
                id: `project-study-nav-${study.study_id}`,
                label: study.title,
                path: `/studio/studies/${study.study_id}`,
                detail: formatStudyStatus(study.status),
                active: false
              })) : <p className="nav-empty">No studies in this project yet.</p>}
            </nav>
          ) : null}
          {navLevel === "study" ? (
            <nav className="context-nav nav-level" id="study-nav" aria-label="Study workspace">
              {navLink({ id: "study-nav-home", label: "Study home", path: `/studio/studies/${selectedStudy.study_id}`, detail: "Question, plan, and next action", active: routeContext.route_kind === "study" })}
              {navLink({ id: "study-nav-setup", label: "Guided setup", path: `/studio/studies/${selectedStudy.study_id}/setup`, detail: "Ask, clarify, approve plan", active: routeContext.route_kind === "study_setup" })}
              {navLink({ id: "study-nav-runs", label: "Research attempts", path: `/studio/studies/${selectedStudy.study_id}/runs`, detail: "Attempts under this study", active: ["study_runs", "run"].includes(routeContext.route_kind) })}
              {navLink({ id: "study-nav-evidence", label: "Evidence", path: `/studio/studies/${selectedStudy.study_id}/evidence`, detail: "Signals and saved views", active: ["study_evidence", "evidence_view", "study_report"].includes(routeContext.route_kind) })}
              {navLink({ id: "study-nav-report", label: "Report", path: studyReportPath, detail: "Study-level synthesis", active: routeContext.route_kind === "study_report" })}
              {navLink({ id: "study-nav-decision", label: "Decision", path: studyDecisionPath, detail: "Belief, uncertainty, follow-up", active: routeContext.route_kind === "decision" })}
              {navLink({ id: "study-nav-share", label: "Share", path: sharePath, detail: "Boundary-safe collaboration", active: false })}
            </nav>
          ) : null}
          <EvidenceBoundaryNotice compact />
        </div>
        <RailAccount session={model.session} />
      </aside>

      <section className="studio-canvas">
        <RouteHeader routeContext={routeContext} selectedProject={selectedProject} selectedStudy={selectedStudy} />
        {selectedStudy ? <StudyContextHeader selectedStudy={selectedStudy} draft={draft} navigate={navigate} /> : null}
        {model.error ? <div className="error-card" role="alert">{model.error}</div> : null}
        {model.loading ? <LoadingState /> : <RouteSwitch {...pageProps} />}
      </section>
    </main>
  );
}

function RouteSwitch(props) {
  const { routeContext } = props;
  switch (routeContext.route_kind) {
    case "projects":
      return <ProjectsRoute {...props} />;
    case "project":
      return <ProjectDetailRoute {...props} />;
    case "new_study":
      return <NewStudyRoute {...props} />;
    case "study":
      return <StudyHomeRoute {...props} />;
    case "study_setup":
      return <StudySetupRoute {...props} />;
    case "study_runs":
      return <RunsRoute {...props} />;
    case "run":
      return <RunDetailRoute {...props} />;
    case "study_evidence":
      return <EvidenceRoute {...props} />;
    case "evidence_view":
      return <EvidenceViewRoute {...props} />;
    case "study_report":
      return <StudyReportRoute {...props} />;
    case "decision":
      return <DecisionRoute {...props} />;
    case "share":
      return <ShareRoute {...props} />;
    case "share_collection":
      return <ShareCollectionRoute {...props} />;
    default:
      return <WorkspaceRoute {...props} />;
  }
}

function RailAccount({ session }) {
  const workspaceName = session?.workspace?.display_name || "Workspace";
  const role = session?.auth?.role || "member";
  const initials = workspaceName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "WS";
  return (
    <footer className="rail-bottom" aria-label="Workspace account">
      <div className="workspace-avatar" aria-hidden="true">{initials}</div>
      <div className="workspace-user">
        <strong>{workspaceName}</strong>
        <span>{role}</span>
      </div>
    </footer>
  );
}

function RouteHeader({ routeContext, selectedProject, selectedStudy }) {
  const labels = {
    workspace: "Home",
    projects: "Projects",
    project: selectedProject?.name || "Project",
    new_study: "New study",
    study: selectedStudy?.title || "Study",
    study_setup: "Guided setup",
    study_runs: "Research attempts",
    run: "Research attempt",
    study_evidence: "Evidence workspace",
    evidence_view: "Saved evidence view",
    study_report: "Study report",
    decision: "Decision review",
    share: "Share view",
    share_collection: "Share"
  };
  return (
    <header className="route-header">
      <div>
        <p className="kicker">Workspace location</p>
        <h2 id="route-title">{labels[routeContext.route_kind] || "Workspace"}</h2>
      </div>
      <div className="route-pill">
        <span>Current page</span>
        <strong id="route-kind">{labels[routeContext.route_kind] || "Workspace"}</strong>
      </div>
    </header>
  );
}

function StudyContextHeader({ selectedStudy, draft, navigate }) {
  const action = nextActionForStudy(selectedStudy);
  const approvedPlanId = selectedStudy.current_plan_revision_id || draft?.revision?.plan_revision_id || "";
  const hasNewRun = Boolean(draft?.latestRun?.job_id);
  const displayStatus = hasNewRun && ["draft", "planning", "ready_to_run"].includes(selectedStudy.status)
    ? "running"
    : selectedStudy.status;
  return (
    <section className="study-context" aria-label="Study context">
      <div>
        <p className="kicker">Current study</p>
        <h3 id="selected-study">{selectedStudy.title}</h3>
        <p>{selectedStudy.research_intent || "No research intent recorded yet."}</p>
      </div>
      <dl>
        <dt>Status</dt>
        <dd id="study-status">{formatStudyStatus(displayStatus)}</dd>
        <dt>Approved plan</dt>
        <dd id="plan-revision">{approvedPlanId ? "Approved" : "Not approved yet"}</dd>
      </dl>
      <button onClick={() => navigate(action.path)}>{action.label}</button>
    </section>
  );
}

function WorkspaceRoute({ model, navigate }) {
  const recentStudies = model.studies.slice(0, 5);
  return (
    <div className="route-stack">
      <section className="hero-panel">
        <div>
          <p className="kicker">Guided research workspace</p>
          <h2>Start with a question. Leave with a decision you can inspect.</h2>
          <p>Describe what you need to learn, confirm the study plan, inspect simulated evidence, and keep human-validation gaps visible before deciding.</p>
        </div>
        <div className="status-card">
          <span>Workspace</span>
          <strong>{model.session?.workspace?.display_name || "Workspace"}</strong>
          <small>{model.session?.auth?.role || "member"}</small>
        </div>
      </section>
      <section className="workspace-grid">
        <article className="paper-card primary-card">
          <p className="kicker">Start</p>
          <h3>Start a new study</h3>
          <p>Begin in plain language. The setup flow will infer the study type and ask only for missing high-signal context.</p>
          <button id="start-new-study" onClick={() => navigate("/studio/studies/new")}>Start a new study</button>
        </article>
        <article className="paper-card">
          <p className="kicker">Evidence boundary</p>
          <h3>Use as simulated research signal</h3>
          <EvidenceBoundaryNotice />
        </article>
      </section>
      <section className="object-list" aria-label="Recent studies">
        <ListHeader title="Recent studies" action="Open all projects" onAction={() => navigate("/studio/projects")} />
        {recentStudies.length ? recentStudies.map((study) => (
          <ObjectRow
            key={study.study_id}
            title={study.title}
            meta={`${formatStudyStatus(study.status)} · ${study.run_count || 0} research attempts · ${study.study_report_count || 0} reports`}
            cta="Open study"
            onClick={() => navigate(`/studio/studies/${study.study_id}`)}
          />
        )) : <EmptyState title="No studies yet" body="Start a study to turn an open research question into a confirmable plan." cta="Start a new study" onClick={() => navigate("/studio/studies/new")} />}
      </section>
    </div>
  );
}

function ProjectsRoute({ model, draft, setDraft, createProject, navigate }) {
  return (
    <div className="route-grid">
      <section className="object-list wide-list" aria-label="Projects">
        <ListHeader title="Projects" action="Create project" onAction={createProject} />
        {model.projects.length ? model.projects.map((project) => (
          <ObjectRow
            key={project.project_id}
            title={project.name}
            meta={`${project.study_count || 0} studies · ${project.active_decision_count || 0} active decisions`}
            cta="Open project"
            onClick={() => navigate(`/studio/projects/${project.project_id}`)}
          />
        )) : <EmptyState title="No projects yet" body="Create a project to group studies around one product area, idea, or client context." cta="Create project" onClick={createProject} />}
      </section>
      <aside className="paper-card">
        <p className="kicker">Create project</p>
        <h3>Group research over time</h3>
        <input value={draft.newProjectName} onChange={(event) => setDraft({ ...draft, newProjectName: event.target.value })} aria-label="New project name" />
        <textarea value={draft.projectDescription} onChange={(event) => setDraft({ ...draft, projectDescription: event.target.value })} aria-label="Project description" />
        <button onClick={createProject}>Create project</button>
      </aside>
    </div>
  );
}

function ProjectDetailRoute({ selectedProject, model, navigate }) {
  if (!selectedProject) {
    return <EmptyState title="Project not found" body="This project is not available in the current workspace." cta="View projects" onClick={() => navigate("/studio/projects")} />;
  }
  const studies = model.studies.filter((study) => study.project_id === selectedProject.project_id);
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">Project</p>
          <h2>{selectedProject.name}</h2>
          <p>{selectedProject.description || "A long-lived research context for studies, evidence, and decisions."}</p>
        </div>
        <button onClick={() => navigate("/studio/studies/new")}>Start study in this project</button>
      </section>
      <section className="object-list">
        <ListHeader title="Studies in this project" action="Start study" onAction={() => navigate("/studio/studies/new")} />
        {studies.length ? studies.map((study) => (
          <ObjectRow
            key={study.study_id}
            title={study.title}
            meta={`${formatStudyStatus(study.status)} · ${study.evidence_view_count || 0} saved views · ${study.decision_log_count || 0} decisions`}
            cta="Open study"
            onClick={() => navigate(`/studio/studies/${study.study_id}`)}
          />
        )) : <EmptyState title="No studies in this project" body="Start a study to connect this project to evidence and decisions." cta="Start study" onClick={() => navigate("/studio/studies/new")} />}
      </section>
    </div>
  );
}

function NewStudyRoute({ model, draft, setDraft, selectedProject, createProjectAndStudy }) {
  const projectValue = draft.selectedProjectId || selectedProject?.project_id || "__new__";
  const nextQuestion = !draft.intent.trim()
    ? "What decision are you trying to make with this study?"
    : !draft.targetParticipant.trim()
      ? "Who should the synthetic participants represent?"
      : !draft.artifactNotes.trim()
        ? "Do you have a concept, copy, screen, prototype, or workflow artifact to include?"
        : "Review the saved context, then continue to inspect the research plan before anything runs.";
  return (
    <div className="route-grid">
      <section className="paper-card composer-card">
        <p className="kicker">Ask / Clarify</p>
        <h3>Describe the research you need</h3>
        <p>Start in plain language. The system will turn this into a plan you can inspect before anything runs.</p>
        <label className="field-label" htmlFor="intent">Research question</label>
        <textarea id="intent" value={draft.intent} onChange={(event) => setDraft({ ...draft, intent: event.target.value })} />
        <label className="field-label" htmlFor="study-purpose">Decision you need to make</label>
        <textarea id="study-purpose" value={draft.studyPurpose} onChange={(event) => setDraft({ ...draft, studyPurpose: event.target.value })} />
        <label className="field-label" htmlFor="target-participant">Target participant</label>
        <input id="target-participant" value={draft.targetParticipant} onChange={(event) => setDraft({ ...draft, targetParticipant: event.target.value })} />
        <label className="field-label" htmlFor="artifact-notes">Artifact or prototype context</label>
        <textarea id="artifact-notes" value={draft.artifactNotes} onChange={(event) => setDraft({ ...draft, artifactNotes: event.target.value })} />
        <div className="two-fields">
          <select
            id="project-context"
            value={projectValue}
            onChange={(event) => setDraft({ ...draft, selectedProjectId: event.target.value })}
            aria-label="Project context"
          >
            {model.projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>{project.name}</option>
            ))}
            <option value="__new__">Create a new project</option>
          </select>
          <input id="project-name" value={draft.projectName} onChange={(event) => setDraft({ ...draft, projectName: event.target.value })} aria-label="New project name" />
          <input id="study-title" value={draft.studyTitle} onChange={(event) => setDraft({ ...draft, studyTitle: event.target.value })} aria-label="Study title" />
        </div>
        <ActionNotice draft={draft} />
        <button id="create-study" onClick={createProjectAndStudy}>Continue to guided setup</button>
      </section>
      <aside className="copilot-panel plan-preview-card">
        <p className="kicker">Research Copilot</p>
        <h3>Next useful question</h3>
        <p>{nextQuestion}</p>
        <ol className="guided-loop">
          {["Ask", "Clarify", "Confirm Plan", "Run"].map((step, index) => (
            <li key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {step}
            </li>
          ))}
        </ol>
        <SignalCard title="Study setup" items={[
          { note: `Question: ${draft.intent}` },
          { note: `Participant: ${draft.targetParticipant}` },
          { note: `Audience criteria: ${normalizeLines(draft.audienceCriteria).length || 0} selected` },
          { note: `Guide questions: ${normalizeLines(draft.guideQuestions).length || 0} drafted` },
          { note: `Artifact context: ${draft.artifactNotes}` }
        ]} />
        <p className="boundary">No run starts from this screen. You will approve the plan first.</p>
      </aside>
    </div>
  );
}

function StudyHomeRoute({ selectedStudy, studyRuns, model, navigate }) {
  if (!selectedStudy) {
    return <EmptyState title="No study selected" body="Start or open a study to see its plan state, latest evidence, and decisions." cta="Start a new study" onClick={() => navigate("/studio/studies/new")} />;
  }
  const action = nextActionForStudy(selectedStudy);
  return (
    <div className="route-grid">
      <article className="paper-card primary-card">
        <p className="kicker">Next action</p>
        <h3>{action.label}</h3>
        <p>Use this page as the study home: question, plan state, latest research attempts, evidence, and decisions stay together.</p>
        <button onClick={() => navigate(action.path)}>{action.label}</button>
      </article>
      <article className="paper-card">
        <p className="kicker">Study state</p>
        <h3>{formatStudyStatus(selectedStudy.status)}</h3>
        <MetricGrid items={[
          ["Research attempts", studyRuns.length],
          ["Saved evidence views", model.evidenceViews.length],
          ["Study reports", model.studyReports.length],
          ["Decision logs", model.decisionLogs.length]
        ]} />
      </article>
    </div>
  );
}

function StudySetupRoute({ selectedStudy, model, draft, setDraft, proposePlan, confirmPlan, startResearchRun }) {
  if (!selectedStudy) {
    return <EmptyState title="No study selected" body="Open a study before reviewing or approving a plan." />;
  }
  const proposal = draft.proposal || selectedStudy.frontline?.latest_plan_proposal || selectedStudy.draft_plan || {};
  const revision = draft.revision || selectedStudy.frontline?.latest_plan_revision || {};
  const hasProposal = Boolean(proposal?.plan_proposal_id || selectedStudy.frontline?.latest_plan_proposal_id);
  const hasApprovedPlan = Boolean(selectedStudy.current_plan_revision_id || revision?.plan_revision_id);
  const studyMode = proposal?.mode_inference?.mode || revision?.mode_inference?.mode || "";
  const targetAudience = proposal?.target_audience || revision?.target_audience || buildTargetAudiencePayload(draft);
  const audienceCriteria = Array.isArray(targetAudience?.inclusion_criteria) ? targetAudience.inclusion_criteria : [];
  const personaPanel = proposal?.persona_panel || revision?.persona_panel || buildPersonaPanelPayload(draft, model.personaLibrary);
  const selectedPersonaIds = Array.isArray(personaPanel?.selected_persona_ids) ? personaPanel.selected_persona_ids : [];
  const guide = proposal?.moderator_interview_guide || revision?.moderator_interview_guide || {};
  const guideQuestions = guide?.questions || normalizeLines(draft.guideQuestions);
  const expectedEvidence = proposal?.expected_evidence_types || revision?.expected_evidence_types || [];
  const artifacts = proposal?.artifact_refs || revision?.artifact_refs || selectedStudy.artifact_refs || [];
  return (
    <div className="setup-grid">
      <div className="setup-side">
        <ResearchCopilotPanel />
        <PersonaLibraryPicker model={model} draft={draft} setDraft={setDraft} hasApprovedPlan={hasApprovedPlan} />
        <PlanTuningCard draft={draft} setDraft={setDraft} hasApprovedPlan={hasApprovedPlan} />
      </div>
      <section className="paper-card plan-confirmation-card">
        <p className="kicker">Confirm Plan</p>
        <h3>Review assumptions before research starts</h3>
        <ActionNotice draft={draft} />
        <div className="plan-section">
          <span className="ia-nav-label">Goal</span>
          <p id="plan-goal">{proposal?.study_purpose || revision?.study_purpose || selectedStudy.research_intent || "Draft a plan to clarify the research goal."}</p>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">Target participant</span>
          <p id="plan-target">{targetAudience?.summary || proposal?.target_persona || revision?.target_persona || "Synthetic participants matching the study context."}</p>
        </div>
        <div className="plan-section" id="plan-audience-criteria">
          <span className="ia-nav-label">Audience selection</span>
          <SignalList
            items={[
              ...audienceCriteria.map((item) => ({ label: item, note: "Include in this synthetic panel brief." })),
              ...(targetAudience?.excluded_context ? [{ label: "Outside this run", note: targetAudience.excluded_context }] : [])
            ]}
            fallback="Use Plan tuning to describe who the simulated participants should represent."
          />
        </div>
        <div className="plan-section" id="plan-persona-panel">
          <span className="ia-nav-label">Participant panel</span>
          <p>{String(personaPanel?.panel_type || "mainstream").replaceAll("_", " ")} panel with {selectedPersonaIds.length || personaPanel?.sample_size || 0} selected synthetic participant(s).</p>
          <SignalList
            items={(personaPanel?.selected_personas || []).map((persona) => ({
              label: persona.name || persona.synthetic_user_id,
              note: [persona.occupation, persona.location, persona.workflow_maturity].filter(Boolean).join(" - ")
            }))}
            fallback="Choose personas from the library before approving the plan."
          />
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">Study type</span>
          <strong id="plan-study-type">{formatStudyType(studyMode)}</strong>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">Artifacts</span>
          <p>{artifacts.length ? artifacts.join("; ") : "No external artifact attached yet."}</p>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">Expected evidence</span>
          <div className="tag-list" id="plan-evidence">
            {(expectedEvidence.length ? expectedEvidence : ["objections", "trust gaps", "adoption barriers", "contradictions", "human-validation gaps"]).map((item) => (
              <span key={item}>{String(item).replaceAll("_", " ")}</span>
            ))}
          </div>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">Interview guide</span>
          <ol className="guide-list" id="plan-guide-list">
            {(guideQuestions.length ? guideQuestions : ["Draft the research plan to generate the interview guide."]).map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ol>
        </div>
        <div className="plan-section" id="plan-guide-focus">
          <span className="ia-nav-label">Guide focus</span>
          <p>{guide?.focus || draft.guideFocus || "Probe current behavior, understanding, trust, effort, and adoption barriers."}</p>
        </div>
        <div className="plan-section" id="plan-limitations">
          <span className="ia-nav-label">Limitations</span>
          <p>Synthetic evidence only. Treat findings as simulated signal until calibrated or validated with humans.</p>
        </div>
        <div className="button-row">
          <button id="propose-plan" onClick={proposePlan}>{hasProposal ? "Update draft plan" : "Draft research plan"}</button>
          <button id="confirm-plan" onClick={confirmPlan} disabled={!hasProposal || hasApprovedPlan}>{hasApprovedPlan ? "Plan approved" : "Approve plan"}</button>
          <button id="start-research-run" onClick={startResearchRun} disabled={!hasApprovedPlan}>Start research run</button>
        </div>
      </section>
    </div>
  );
}

function PersonaLibraryPicker({ model, draft, setDraft, hasApprovedPlan }) {
  const library = model.personaLibrary || {};
  const personas = Array.isArray(library.personas) ? library.personas : [];
  const panelOptions = Array.isArray(library.panel_options) ? library.panel_options : [];
  const selectedIds = draft.selectedPersonaIds || [];
  const selectedCount = selectedIds.length;
  const coverageGaps = library.library_summary?.human_difference_axis_summary?.coverage_gaps || [];
  const defaultSelection = library.default_selection || {};
  const togglePersona = (personaId) => {
    if (hasApprovedPlan) return;
    const id = String(personaId || "");
    const existing = new Set(selectedIds);
    if (existing.has(id)) {
      existing.delete(id);
    } else {
      existing.add(id);
    }
    setDraft({ ...draft, selectedPersonaIds: Array.from(existing), personaSampleSize: Math.max(1, existing.size) });
  };
  return (
    <section className="paper-card persona-picker-card" id="persona-library-picker">
      <p className="kicker">Persona library</p>
      <h3>Choose who this study simulates</h3>
      <p className="field-hint">Select a participant panel with visible coverage rationale. This improves simulation quality, but it is not recruited human evidence.</p>
      <div className="two-fields">
        <select
          disabled={hasApprovedPlan}
          id="persona-panel-type"
          value={draft.selectedPanelType}
          onChange={(event) => setDraft({ ...draft, selectedPanelType: event.target.value, selectedPersonaIds: [] })}
          aria-label="Persona panel type"
        >
          {panelOptions.length ? panelOptions.map((option) => (
            <option key={option.panel_type} value={option.panel_type}>
              {option.label} ({option.persona_count})
            </option>
          )) : <option value="mainstream">Mainstream</option>}
        </select>
        <select
          disabled={hasApprovedPlan}
          id="persona-sample-size"
          value={String(draft.personaSampleSize || selectedCount || 1)}
          onChange={(event) => setDraft({ ...draft, personaSampleSize: Number(event.target.value), selectedPersonaIds: [] })}
          aria-label="Persona sample size"
        >
          {[1, 2, 3, 4, 5, 6].map((size) => <option key={size} value={size}>{size} participant{size > 1 ? "s" : ""}</option>)}
        </select>
      </div>
      <div className="persona-picker-summary" id="selected-persona-count">
        <strong>{selectedCount || defaultSelection.selected_persona_ids?.length || 0}</strong>
        <span>selected synthetic participant(s)</span>
      </div>
      <div className="persona-card-grid" id="persona-picker-cards">
        {personas.length ? personas.map((persona) => {
          const isSelected = selectedIds.includes(persona.synthetic_user_id);
          const policy = persona.decision_policy || {};
          return (
            <button
              aria-pressed={isSelected}
              className={isSelected ? "persona-card is-selected" : "persona-card"}
              disabled={hasApprovedPlan}
              key={persona.synthetic_user_id}
              onClick={() => togglePersona(persona.synthetic_user_id)}
              type="button"
            >
              <span className="persona-card-name">{persona.name}</span>
              <span>{persona.occupation || "Participant"} - {persona.location || "Local context"}</span>
              <small>{String(persona.panel_role || "").replaceAll("_", " ")} | {persona.workflow_maturity || "workflow context"} | trust {persona.trust_threshold || "contextual"}</small>
              <em>{policy.adoption_style || "Decision behavior is available in the persona record."}</em>
            </button>
          );
        }) : <p className="nav-empty">Persona library is preparing. Try refreshing this setup page.</p>}
      </div>
      <SignalCard
        title="Coverage gaps to remember"
        items={coverageGaps.slice(0, 4).map((gap) => ({
          label: String(gap.axis || "").replaceAll("_", " "),
          note: String(gap.gap_type || "").replaceAll("_", " ")
        }))}
      />
      <p className="boundary">{library.synthetic_boundary || "Synthetic persona selection does not create human market proof."}</p>
    </section>
  );
}

function PlanTuningCard({ draft, setDraft, hasApprovedPlan }) {
  const guideCount = normalizeLines(draft.guideQuestions).length;
  const criteriaCount = normalizeLines(draft.audienceCriteria).length;
  return (
    <section className="paper-card plan-tuning-card" id="plan-tuning">
      <p className="kicker">Plan tuning</p>
      <h3>Shape the study before approval</h3>
      <p className="field-hint">Keep this as plain research language. The plan preview on the right is what will be approved before the run starts.</p>
      <label className="field-label" htmlFor="setup-target-participant">Audience to simulate</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="setup-target-participant"
        value={draft.targetParticipant}
        onChange={(event) => setDraft({ ...draft, targetParticipant: event.target.value })}
      />
      <label className="field-label" htmlFor="audience-criteria">Audience criteria</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="audience-criteria"
        value={draft.audienceCriteria}
        onChange={(event) => setDraft({ ...draft, audienceCriteria: event.target.value })}
      />
      <label className="field-label" htmlFor="audience-exclusions">Keep outside this run</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="audience-exclusions"
        value={draft.audienceExclusions}
        onChange={(event) => setDraft({ ...draft, audienceExclusions: event.target.value })}
      />
      <label className="field-label" htmlFor="guide-questions">Interview guide questions</label>
      <textarea
        className="guide-textarea"
        disabled={hasApprovedPlan}
        id="guide-questions"
        value={draft.guideQuestions}
        onChange={(event) => setDraft({ ...draft, guideQuestions: event.target.value })}
      />
      <label className="field-label" htmlFor="guide-focus">Moderator focus</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="guide-focus"
        value={draft.guideFocus}
        onChange={(event) => setDraft({ ...draft, guideFocus: event.target.value })}
      />
      <MetricGrid items={[
        ["Audience criteria", criteriaCount],
        ["Guide questions", guideCount],
        ["Approval state", hasApprovedPlan ? "Locked" : "Editable"],
        ["Boundary", "Visible"]
      ]} />
      <p className="boundary">These controls tune the synthetic study plan. They do not turn the panel into recruited human participants.</p>
    </section>
  );
}

function RunsRoute({ selectedStudy, studyRuns, navigate, startResearchRun }) {
  if (!selectedStudy) {
    return <EmptyState title="No study selected" body="Open a study before reviewing research attempts." />;
  }
  const hasApprovedPlan = Boolean(selectedStudy.current_plan_revision_id);
  return (
    <section className="object-list" id="research-run-list">
      <ListHeader title="Research attempts" action={hasApprovedPlan ? "Start research run" : "Continue setup"} onAction={hasApprovedPlan ? startResearchRun : () => navigate(`/studio/studies/${selectedStudy.study_id}/setup`)} />
      {studyRuns.length ? studyRuns.map((run, index) => (
        <ObjectRow
          key={run.job_id || index}
          title={`Research attempt ${index + 1}`}
          meta={`${formatRunStatus(run.status)} - plan basis and evidence boundary preserved`}
          cta="Open attempt"
          onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/runs/${runIdentifier(run) || run.job_id}`)}
        />
      )) : <EmptyState title="No research attempts yet" body="Approve a plan first, then start the first synthetic research run from this study." cta={hasApprovedPlan ? "Start research run" : "Continue setup"} onClick={hasApprovedPlan ? startResearchRun : () => navigate(`/studio/studies/${selectedStudy.study_id}/setup`)} />}
    </section>
  );
}

function RunDetailRoute({ selectedStudy, selectedRun, model, navigate }) {
  if (!selectedStudy || !selectedRun) {
    return <EmptyState title="Research attempt not found" body="Open the study's research attempts list to choose an available attempt." cta="View attempts" onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/runs`)} />;
  }
  const query = model.evidenceQuery;
  const reliability = query?.evidence_reliability || {};
  const missingContext = Array.isArray(reliability.missing_context) ? reliability.missing_context : [];
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">Research attempt</p>
          <h2>{formatRunStatus(selectedRun.status)}</h2>
          <p>{cleanEvidenceCopy(query?.boundary_warning || "Use this page to inspect evidence before accepting any summary.")}</p>
        </div>
        <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>Review evidence</button>
      </section>
      <div className="route-grid">
        <PlanBasisCard selectedStudy={selectedStudy} selectedRun={selectedRun} />
        <article className="paper-card" id="run-audit-notes">
          <p className="kicker">Audit notes</p>
          <h3>{reliability.stability_label ? cleanEvidenceCopy(reliability.stability_label).replaceAll("_", " ") : "Reliability pending"}</h3>
          <MetricGrid items={[
            ["Source slices", query?.result_count || 0],
            ["Contradictions", Array.isArray(reliability.contradicting_evidence) ? reliability.contradicting_evidence.length : 0],
            ["Human gaps", missingContext.length],
            ["Comparison runs", query?.cross_run_comparison?.comparison_run_count || 0]
          ]} />
          <p className="boundary">{reliability.synthetic_boundary || "Synthetic evidence only. Keep human-validation gaps visible."}</p>
        </article>
      </div>
      <EvidenceReviewBoard query={query} sourceRun={selectedRun} compact={false} />
    </div>
  );
}

function EvidenceRoute({ selectedStudy, model, draft, evidenceControls, setEvidenceControls, createEvidenceView, createStudyReport, navigate }) {
  if (!selectedStudy) {
    return <EmptyState title="No study selected" body="Open a study before reviewing evidence." />;
  }
  const query = model.evidenceQuery;
  const canSave = Boolean(query?.query_status === "query_ready" && model.evidenceQueryJobId);
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">Evidence before summary</p>
          <h2>Review source evidence, contradictions, and gaps first.</h2>
          <p>{cleanEvidenceCopy(query?.boundary_warning || "Complete a research attempt before evidence can be inspected.")}</p>
        </div>
        <div className="button-row">
          <button id="save-evidence-view" onClick={createEvidenceView} disabled={!canSave}>Save evidence view</button>
          <button id="create-report" onClick={createStudyReport}>Create study report</button>
        </div>
      </section>
      <ActionNotice draft={draft} />
      <section className="paper-card evidence-filter-card" id="evidence-filters">
        <div>
          <p className="kicker">Evidence filters</p>
          <h3>{displayEvidenceFamily(evidenceControls.activeFamily)}</h3>
          <p>Filter by evidence family while keeping the selected study and attempt provenance attached.</p>
        </div>
        <div className="filter-chip-row">
          {["all", "input", "trace", "analysis", "output"].map((family) => (
            <button
              className={evidenceControls.activeFamily === family ? "filter-chip is-active" : "filter-chip"}
              key={family}
              onClick={() => setEvidenceControls({ ...evidenceControls, activeFamily: family })}
              type="button"
            >
              {displayEvidenceFamily(family)}
              <span>{query?.facet_counts?.[family] ?? 0}</span>
            </button>
          ))}
        </div>
      </section>
      <EvidenceReviewBoard query={query} sourceRun={findRunByRouteIdentifier(model.jobs, model.evidenceQueryJobId)} />
      <div className="route-grid">
        <section className="object-list wide-list">
          <ListHeader title="Saved evidence views" action="Save current view" actionId="save-evidence-view-secondary" onAction={createEvidenceView} disabled={!canSave} />
          {model.evidenceViews.length ? model.evidenceViews.map((view) => (
            <ObjectRow
              key={view.evidence_view_id}
              title={view.title}
              meta={`${displayEvidenceFamily(view.active_family || "all")} - ${cleanEvidenceCopy(view.query_text || "saved review state")}`}
              cta="Open view"
              onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence-views/${view.evidence_view_id}`)}
            />
          )) : <EmptyState title="No saved evidence views yet" body="Save a view for a theme, contradiction, or comparison you may cite later." cta="Save evidence view" onClick={createEvidenceView} />}
        </section>
        <ComparisonPanel query={query} />
      </div>
    </div>
  );
}

function EvidenceViewRoute({ selectedStudy, model, routeContext, createStudyReport, navigate }) {
  const view = model.routeObjects.evidenceView || model.evidenceViews.find((item) => item.evidence_view_id === routeContext.evidence_view_id);
  if (!selectedStudy || !view) {
    return <EmptyState title="Saved evidence view not found" body="Open the evidence workspace to choose an available saved view." cta="Open evidence" onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)} />;
  }
  const query = model.evidenceQuery;
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">Saved evidence view</p>
          <h2>{view.title}</h2>
          <p>{view.note || "A durable evidence slice for review, citation, or decision logging."}</p>
        </div>
        <div className="button-row">
          <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>Open evidence workspace</button>
          <button onClick={createStudyReport}>Create study report</button>
        </div>
      </section>
      <div className="route-grid">
        <article className="paper-card primary-card" id="saved-view-provenance">
          <p className="kicker">Provenance retained</p>
          <h3>{view.selected_signal_id ? cleanEvidenceCopy(view.selected_signal_id).replaceAll("_", " ") : "Source evidence retained"}</h3>
          <MetricGrid items={[
            ["Evidence family", displayEvidenceFamily(view.active_family || "all")],
            ["Source attempt", view.run_id ? "Linked" : "Pending"],
            ["Replay focus", view.has_replay_focus ? "Attached" : "Not selected"],
            ["Comparison", view.has_comparison_focus ? "Attached" : "Available in workspace"]
          ]} />
          <p className="boundary">This saved view keeps the selected evidence context attached after refresh. It remains simulated evidence, not human market proof.</p>
        </article>
        <article className="paper-card">
          <p className="kicker">Review scope</p>
          <h3>{displayEvidenceFamily(view.active_family || "all")}</h3>
          <p>{cleanEvidenceCopy(view.query_text || "Saved review state for a source evidence slice, contradiction, or comparison.")}</p>
          <SignalCard title="Human-validation gaps" items={[...(view.readiness_gate?.gate_reasons || []).map((item) => ({ label: cleanEvidenceCopy(item).replaceAll("_", " ") }))]} />
        </article>
      </div>
      <EvidenceReviewBoard query={query} sourceRun={findRunByRouteIdentifier(model.jobs, view.job_id || view.run_id)} compact />
    </div>
  );
}

function StudyReportRoute({ selectedStudy, model, routeContext, createDecisionLog, navigate }) {
  const report = model.routeObjects.studyReport || model.studyReports.find((item) => item.study_report_id === routeContext.study_report_id);
  if (!selectedStudy || !report) {
    return <EmptyState title="Study report not found" body="Create a study report after completed research attempts exist." cta="Review evidence" onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)} />;
  }
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{formatReportStatus(report.status)}</p>
          <h2>{report.title}</h2>
          <p>{report.synthetic_boundary}</p>
        </div>
        <div className="button-row">
          <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>Review source evidence</button>
          <button id="create-decision" onClick={createDecisionLog}>Create decision from report</button>
        </div>
      </section>
      <section className="paper-card" id="report-cited-evidence">
        <p className="kicker">Cited evidence</p>
        <h3>Cited attempts and plan revisions</h3>
        <MetricGrid items={[
          ["Included attempts", report.included_run_ids?.length || 0],
          ["Plan revisions", report.included_plan_revision_ids?.length || 0],
          ["Evidence slices", report.metadata?.evidence_slice_count || 0],
          ["Decision ready", report.capabilities?.decision_workflow_ready ? "Yes" : "Review"]
        ]} />
      </section>
      <section className="report-grid">
        <SignalCard title="Stable patterns" items={report.stable_patterns} />
        <SignalCard title="Divergent signals" items={report.divergent_signals} />
        <SignalCard title="Objections" items={report.key_objections} />
        <SignalCard title="Trust gaps" items={report.trust_gaps} />
        <SignalCard title="Adoption barriers" items={report.adoption_barriers} />
        <SignalCard title="Contradictions" items={report.contradictions} cardId="report-contradictions" />
        <SignalCard title="Human-validation gaps" items={report.human_validation_gaps} cardId="report-human-gaps" />
      </section>
    </div>
  );
}

function PlanBasisCard({ selectedStudy, selectedRun }) {
  const revisionId = selectedRun?.metadata?.frontline_plan_revision_id || selectedRun?.metadata?.plan_revision_id || selectedStudy?.current_plan_revision_id || "";
  const revision = selectedStudy?.frontline?.latest_plan_revision || selectedStudy?.frontline?.latest_plan_proposal || {};
  return (
    <article className="paper-card primary-card" id="plan-basis">
      <p className="kicker">Plan basis</p>
      <h3>{revisionId ? "Approved plan attached" : "Plan context pending"}</h3>
      <p>{revision.study_purpose || selectedStudy?.desired_output || selectedStudy?.research_intent || "This attempt stays tied to the selected study question."}</p>
      <MetricGrid items={[
        ["Study type", formatStudyType(revision?.mode_inference?.mode)],
        ["Target", revision.target_persona || "Study participant context"],
        ["Evidence boundary", "Visible"],
        ["Attempt status", formatRunStatus(selectedRun?.status)]
      ]} />
    </article>
  );
}

function EvidenceReviewBoard({ query, sourceRun, compact = false }) {
  if (!query) {
    return (
      <section className="evidence-board">
        <EmptyState title="Evidence is preparing" body="Complete a research attempt before reviewing source evidence, interpretation, contradictions, and human-validation gaps." />
      </section>
    );
  }
  const selected = query.selected_result || query.results?.[0] || null;
  const reliability = query.evidence_reliability || {};
  const missingContext = Array.isArray(reliability.missing_context) ? reliability.missing_context : [];
  const contradictions = Array.isArray(reliability.contradicting_evidence) ? reliability.contradicting_evidence : [];
  const supporting = Array.isArray(reliability.supporting_evidence) ? reliability.supporting_evidence : [];
  const replay = Array.isArray(query.replay_sequence) ? query.replay_sequence : [];
  const visibleResults = Array.isArray(query.results) ? query.results.slice(0, compact ? 3 : 5) : [];
  return (
    <section className="evidence-board" id="source-evidence">
      <article className="paper-card evidence-source-card">
        <p className="kicker">Source evidence</p>
        <h3>{selected ? externalizeEvidenceTitle(selected) : "No source evidence selected"}</h3>
        <p>{cleanEvidenceCopy(selected?.summary || query.boundary_warning || "Evidence remains pending.")}</p>
        {evidenceDetailLines(selected).length ? (
          <ul className="evidence-lines">
            {evidenceDetailLines(selected).slice(0, 4).map((line) => <li key={line}>{line}</li>)}
          </ul>
        ) : null}
        <MetricGrid items={[
          ["Visible slices", query.result_count || visibleResults.length || 0],
          ["Evidence family", displayEvidenceFamily(query.active_family || selected?.family || "all")],
          ["Replay steps", replay.length],
          ["Source attempt", sourceRun ? formatRunStatus(sourceRun.status) : "Linked"]
        ]} />
      </article>
      <article className="paper-card" id="interpretation-panel">
        <p className="kicker">Interpretation</p>
        <h3>{reliability.selected_signal_id ? cleanEvidenceCopy(reliability.selected_signal_id).replaceAll("_", " ") : "Signal review"}</h3>
        <p>{query.replay_context?.note || "Interpret the source slice together with replay and nearby evidence, not as a standalone quote."}</p>
        <SignalCard title="Supporting evidence" items={supporting} />
      </article>
      <article className="paper-card" id="summary-panel">
        <p className="kicker">Summary boundary</p>
        <h3>{cleanEvidenceCopy(reliability.stability_label || "Directional signal").replaceAll("_", " ")}</h3>
        <p>{reliability.synthetic_boundary || "Synthetic evidence only. Do not treat this as human market proof."}</p>
        <MetricGrid items={[
          ["Stability score", reliability.stability_score ?? 0],
          ["Supporting slices", supporting.length],
          ["Contradictions", contradictions.length],
          ["Missing context", missingContext.length]
        ]} />
      </article>
      <article className="paper-card risk-card" id="contradiction-panel">
        <p className="kicker">Contradictions</p>
        <h3>{contradictions.length ? `${contradictions.length} open contradiction(s)` : "No strong contradiction yet"}</h3>
        <SignalList items={contradictions} fallback="Keep checking disagreement across attempts before trusting a polished synthesis." />
      </article>
      <article className="paper-card risk-card" id="human-validation-gaps">
        <p className="kicker">Human-validation gaps</p>
        <h3>{missingContext.length ? `${missingContext.length} gap(s) still visible` : "No gap record attached"}</h3>
        <SignalList items={missingContext} fallback="Human validation is still required before market-proof or replacement-grade claims." />
      </article>
      <article className="paper-card evidence-result-list">
        <p className="kicker">Evidence slices</p>
        <h3>{visibleResults.length || "No"} visible slices</h3>
        {visibleResults.length ? visibleResults.map((item) => (
          <div className="evidence-mini-row" key={item.id}>
            <strong>{externalizeEvidenceTitle(item)}</strong>
            <span>{displayEvidenceFamily(item.family)} - {cleanEvidenceCopy(item.summary)}</span>
          </div>
        )) : <p>No source evidence is available yet.</p>}
      </article>
    </section>
  );
}

function ComparisonPanel({ query }) {
  const comparison = query?.cross_run_comparison || {};
  const candidates = Array.isArray(comparison.candidate_runs) ? comparison.candidate_runs : [];
  const localComparison = query?.comparison_context || {};
  return (
    <aside className="paper-card" id="comparison-panel">
      <p className="kicker">Compare</p>
      <h3>Stable patterns vs. uncertainty</h3>
      <p>{comparison.note || localComparison.note || "Compare attempts and nearby evidence before turning signals into decisions."}</p>
      <MetricGrid items={[
        ["Comparable attempts", comparison.comparison_run_count || 0],
        ["Nearby slices", Array.isArray(localComparison.comparison_candidates) ? localComparison.comparison_candidates.length : 0],
        ["Selected comparison", comparison.selected_comparison_run_id ? "Attached" : "Not selected"],
        ["Human boundary", "Visible"]
      ]} />
      <SignalList items={candidates.slice(0, 3)} fallback="Run another attempt to make cross-run comparison stronger." />
    </aside>
  );
}

function SignalList({ items = [], fallback }) {
  const visibleItems = Array.isArray(items) ? items.slice(0, 4) : [];
  if (!visibleItems.length) {
    return <p>{fallback}</p>;
  }
  return (
    <ul className="signal-list">
      {visibleItems.map((item, index) => (
        <li key={item.id || item.result_id || item.signal_id || item.gap_id || item.run_id || index}>
          <strong>{cleanEvidenceCopy(item.label || item.title || item.top_result_title || item.run_id || "Review item")}</strong>
          <span>{cleanEvidenceCopy(item.note || item.summary || item.relation || item.relation_note || "")}</span>
        </li>
      ))}
    </ul>
  );
}

function DecisionRoute({ selectedStudy, model, routeContext, draft, setDraft, createDecisionLog, createShareBundle, navigate }) {
  const decision = model.routeObjects.decisionLog || model.decisionLogs.find((item) => item.decision_log_id === routeContext.decision_log_id);
  if (!selectedStudy || !decision) {
    return (
      <div className="route-grid">
        <EmptyState title="Decision not found" body="Record a decision once evidence is strong enough to support a working belief." />
        <DecisionEditor draft={draft} setDraft={setDraft} createDecisionLog={createDecisionLog} />
      </div>
    );
  }
  const comments = Array.isArray(model.routeObjects.decisionComments) ? model.routeObjects.decisionComments : [];
  const confidenceBoundary = boundarySentence(
    decision.metadata?.confidence_boundary,
    "This is a working belief from synthetic evidence. It is not human market proof."
  );
  const humanFollowUp = cleanEvidenceCopy(
    decision.metadata?.human_follow_up
    || "Validate the strongest objection and trust gap with real participants before acting as if the signal is proven."
  );
  const evidenceBasis = cleanEvidenceCopy(
    decision.metadata?.evidence_basis_label
    || (decision.evidence_view_id ? "Saved evidence view with selected source slice and comparison context." : "Completed research attempt and study report.")
  );
  return (
    <div className="route-grid">
      <article className="paper-card primary-card" id="decision-current-belief">
        <p className="kicker">Decision</p>
        <h3>Current belief</h3>
        <p>{decision.decision_summary}</p>
        <p className="boundary">Current belief, not human market proof. Keep unresolved validation gaps visible before sharing.</p>
        <div className="button-row">
          <button id="review-source-evidence" onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>Review evidence</button>
          <button id="create-share" onClick={createShareBundle}>Create share view</button>
        </div>
      </article>
      <article className="paper-card" id="decision-evidence-basis">
        <p className="kicker">Evidence basis</p>
        <h3>{evidenceBasis}</h3>
        <MetricGrid items={[
          ["Review status", humanizeStatus(decision.review_status, "Draft")],
          ["Evidence view", decision.evidence_view_id ? "Attached" : "Not attached"],
          ["Selected source", decision.selected_signal_id ? "Attached" : decision.selected_result_id ? "Attached" : "Review needed"],
          ["Comparison", decision.has_comparison_focus ? "Attached" : "Not attached"]
        ]} />
      </article>
      <article className="paper-card risk-card" id="decision-confidence-boundary">
        <p className="kicker">Confidence boundary</p>
        <h3>Keep the proof line visible</h3>
        <p>{confidenceBoundary}</p>
        <MetricGrid items={[
          ["Readiness", humanizeStatus(decision.readiness_gate?.status, "Human validation required")],
          ["Market proof", "Not claimed"],
          ["Review threads", decision.review_thread_count || 0],
          ["Comments", decision.comment_count || comments.length || 0]
        ]} />
      </article>
      <article className="paper-card risk-card" id="decision-human-follow-up">
        <p className="kicker">Human follow-up</p>
        <h3>What still needs validation</h3>
        <p>{humanFollowUp}</p>
        <SignalList
          items={decision.readiness_gate?.human_validation_gaps || decision.recurring_signal_focus?.patterns || []}
          fallback="Human validation is still required before treating this decision as market proof."
        />
      </article>
    </div>
  );
}

function ShareCollectionRoute({ model, navigate }) {
  return (
    <section className="object-list">
      <ListHeader title="Share" action="Open workspace" onAction={() => navigate("/studio")} />
      {model.shareBundles.length ? model.shareBundles.map((bundle) => (
        <ObjectRow
          key={bundle.share_bundle_id}
          title={bundle.title}
          meta={`${humanizeStatus(bundle.status, "Share")} - evidence boundary visible`}
          cta="Open share"
          onClick={() => navigate(`/studio/share/${bundle.share_bundle_id}`)}
        />
      )) : <EmptyState title="No share views yet" body="Create reports and decisions first, then share findings with the synthetic-evidence boundary intact." cta="Return to workspace" onClick={() => navigate("/studio")} />}
    </section>
  );
}

function ShareRoute({ selectedStudy, model, routeContext, navigate }) {
  const share = model.routeObjects.shareBundle || model.shareBundles.find((item) => item.share_bundle_id === routeContext.share_bundle_id);
  if (!share) {
    return <EmptyState title="Share view not found" body="This share view is not available in the current workspace." cta="View share area" onClick={() => navigate("/studio/share")} />;
  }
  const linkedDecisionId = share.metadata?.decision_log_id || "";
  const linkedDecision = model.decisionLogs.find((decision) => decision.decision_log_id === linkedDecisionId) || model.decisionLogs[0] || null;
  const files = Array.isArray(share.files) ? share.files : [];
  const shareUrl = share.public_path ? `${window.location.origin}${share.public_path}` : "";
  const shareBoundary = boundarySentence(
    share.synthetic_boundary,
    "Synthetic evidence only. Shared readers should treat this as simulated research signal until validated with humans."
  );
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">Share view</p>
          <h2>{share.title}</h2>
          <p>{shareBoundary}</p>
        </div>
        <div className="button-row">
          <button
            id="copy-share-link"
            onClick={() => shareUrl && navigator.clipboard?.writeText(shareUrl)}
            disabled={!shareUrl}
          >
            Copy boundary link
          </button>
          <button onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/decisions/${linkedDecision?.decision_log_id || ""}`)} disabled={!selectedStudy || !linkedDecision}>
            Open decision
          </button>
        </div>
      </section>
      <section className="share-grid">
        <article className="paper-card primary-card" id="share-decision">
          <p className="kicker">Decision included</p>
          <h3>{linkedDecision?.title || "Decision context pending"}</h3>
          <p>{linkedDecision?.decision_summary || "Attach a decision before treating this share as decision-ready."}</p>
          <p className="boundary">{boundarySentence(linkedDecision?.metadata?.confidence_boundary, "The shared decision remains a synthetic-evidence working belief.")}</p>
        </article>
        <article className="paper-card" id="share-evidence-digest">
          <p className="kicker">Evidence digest</p>
          <h3>What readers can rely on</h3>
          <MetricGrid items={[
            ["Share status", humanizeStatus(share.status, "Published")],
            ["Readiness", humanizeStatus(share.readiness_gate?.status, "Human validation required")],
            ["Market claims", share.market_claims_allowed ? "Scoped only" : "Not allowed"],
            ["Circulation", humanizeStatus(share.mvp_launch_scope?.status, "Internal only")]
          ]} />
        </article>
        <article className="paper-card" id="share-included-artifacts">
          <p className="kicker">Included artifacts</p>
          <h3>{share.share_file_count || files.length || 0} viewer-safe item(s)</h3>
          {files.length ? (
            <div className="artifact-list">
              {files.slice(0, 4).map((file) => (
                <div className="artifact-row" key={file.relative_path || file.file_name || file.artifact_id}>
                  <strong>{cleanEvidenceCopy(file.file_name || file.artifact_id || "Shared artifact")}</strong>
                  <span>{humanizeStatus(file.export_kind, "Evidence artifact")}</span>
                </div>
              ))}
            </div>
          ) : (
            <p>The share carries a packaged evidence artifact count even when file details are hidden from this review page.</p>
          )}
        </article>
        <article className="paper-card risk-card" id="share-boundary">
          <p className="kicker">Boundary</p>
          <h3>Synthetic-only signal</h3>
          <p>{shareBoundary}</p>
          <MetricGrid items={[
            ["Public link", share.public_path ? "Available" : "Unavailable"],
            ["Expires", share.expires_at ? "Scheduled" : "No expiry set"],
            ["Human validation", "Still required"],
            ["Replacement claim", "Not allowed"]
          ]} />
          {shareUrl ? <p id="share-public-link" className="boundary">{shareUrl}</p> : null}
        </article>
      </section>
    </div>
  );
}

function ResearchCopilotPanel() {
  const steps = ["Ask", "Clarify", "Confirm Plan", "Run", "Review Evidence", "Compare", "Decide"];
  return (
    <aside className="copilot-panel" aria-label="Research Copilot guided setup">
      <div>
        <p className="kicker">Research Copilot / Guided Setup</p>
        <h3>The research loop stays inside the study.</h3>
      </div>
      <ol className="guided-loop">
        {steps.map((step, index) => (
          <li key={step}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            {step}
          </li>
        ))}
      </ol>
    </aside>
  );
}

function DecisionEditor({ draft, setDraft, createDecisionLog }) {
  return (
    <article className="paper-card">
      <p className="kicker">Record decision</p>
      <h3>Separate belief from proof</h3>
      <label className="field-label" htmlFor="decision-summary">Current belief</label>
      <textarea id="decision-summary" value={draft.decisionSummary} onChange={(event) => setDraft({ ...draft, decisionSummary: event.target.value })} />
      <label className="field-label" htmlFor="decision-rationale">Evidence basis</label>
      <textarea id="decision-rationale" value={draft.decisionRationale} onChange={(event) => setDraft({ ...draft, decisionRationale: event.target.value })} />
      <label className="field-label" htmlFor="decision-confidence">Confidence boundary</label>
      <textarea id="decision-confidence" value={draft.confidenceBoundary} onChange={(event) => setDraft({ ...draft, confidenceBoundary: event.target.value })} />
      <label className="field-label" htmlFor="decision-follow-up">Human follow-up</label>
      <textarea id="decision-follow-up" value={draft.humanFollowUp} onChange={(event) => setDraft({ ...draft, humanFollowUp: event.target.value })} />
      <button onClick={createDecisionLog}>Save decision</button>
    </article>
  );
}

function ActionNotice({ draft }) {
  if (!draft.actionError && !draft.actionNotice) return null;
  return (
    <div className={`action-notice ${draft.actionError ? "is-error" : ""}`} role={draft.actionError ? "alert" : "status"}>
      {draft.actionError || draft.actionNotice}
    </div>
  );
}

function EvidenceBoundaryNotice({ compact = false }) {
  return (
    <p className={compact ? "boundary compact-boundary" : "boundary"}>
      Synthetic evidence only. Use this as simulated research signal until calibrated or validated with humans.
    </p>
  );
}

function LoadingState() {
  return (
    <section className="paper-card loading-card">
      <p className="kicker">Loading</p>
      <h3>Loading studio context...</h3>
      <p>Preparing the selected object, page state, and evidence boundary.</p>
    </section>
  );
}

function EmptyState({ title, body, cta, onClick }) {
  return (
    <article className="paper-card empty-state">
      <p className="kicker">Empty state</p>
      <h3>{title}</h3>
      <p>{body}</p>
      {cta ? <button onClick={onClick}>{cta}</button> : null}
    </article>
  );
}

function ListHeader({ title, action, actionId, onAction, disabled = false }) {
  return (
    <header className="list-header">
      <h3>{title}</h3>
      {action ? <button id={actionId} onClick={onAction} disabled={disabled}>{action}</button> : null}
    </header>
  );
}

function ObjectRow({ title, meta, cta, onClick }) {
  return (
    <article className="object-row">
      <div>
        <h4>{title}</h4>
        <p>{meta}</p>
      </div>
      <button onClick={onClick}>{cta}</button>
    </article>
  );
}

function MetricGrid({ items }) {
  return (
    <div className="metric-grid">
      {items.map(([label, value]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function SignalCard({ title, items = [], cardId = "" }) {
  const visibleItems = Array.isArray(items) ? items.slice(0, 3) : [];
  return (
    <article className="paper-card" id={cardId || undefined}>
      <p className="kicker">{title}</p>
      <h3>{visibleItems.length || "No"} items</h3>
      {visibleItems.length ? visibleItems.map((item, index) => (
        <p key={item.pattern_id || item.signal_id || item.gap_id || item.result_id || index}>{cleanEvidenceCopy(item.label || item.title || item.note || "Review item")}</p>
      )) : <p>No stronger signal is available yet. Treat this as a review prompt, not proof.</p>}
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
