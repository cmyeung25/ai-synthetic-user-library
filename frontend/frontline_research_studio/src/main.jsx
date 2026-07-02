import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  localeHtmlLang,
  resolveInitialLocale,
  translate
} from "./i18n.js";
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

const postJsonWithoutPayload = async (path, body) => {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
    throw new Error(payload.message || payload.error || `Request failed: ${response.status}`);
  }
  // The route loader fetches fresh study/job state; do not block navigation on a large action body.
  response.text().catch(() => {});
  return response;
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

const I18nContext = React.createContext({
  locale: DEFAULT_LOCALE,
  setLocale: () => {},
  t: (key, vars) => translate(DEFAULT_LOCALE, key, vars)
});

const useI18n = () => useContext(I18nContext);

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

const studyStatusLabels = {
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
};

const formatStudyStatus = (status, t) => {
  if (t && status && Object.prototype.hasOwnProperty.call(studyStatusLabels, status)) return t(`status.${status}`);
  return studyStatusLabels[status] || status || "-";
};

const runStatusLabels = {
  queued: "Queued to start",
  running: "Running",
  completed: "Ready for evidence review",
  failed: "Needs attention",
  canceled: "Canceled"
};

const formatRunStatus = (status, t) => {
  if (t && status && Object.prototype.hasOwnProperty.call(runStatusLabels, status)) return t(`runStatus.${status}`);
  return runStatusLabels[status] || status || "Not started";
};

const formatStudyType = (mode) => ({
  concept_validation: "Concept validation",
  prototype_validation: "Prototype comprehension",
  pain_point_discovery: "Pain, empathy, and insight discovery",
  explore_root_cause: "Root-cause exploration",
  decision_reconstruction: "Decision reconstruction",
  validate_hypothesis: "Hypothesis validation",
  adoption_barrier_validation: "Adoption barrier review",
  workflow_mapping: "Workflow mapping",
  messaging_validation: "Messaging and positioning validation",
}[mode] || "Inferred from your question");

const reportStatusLabels = {
  draft: "Draft",
  ready_for_review: "Ready for review",
  final: "Final"
};

const formatReportStatus = (status, t) => {
  if (t && status && Object.prototype.hasOwnProperty.call(reportStatusLabels, status)) return t(`status.${status}`);
  return reportStatusLabels[status] || status || "Report";
};

const DEFAULT_EVIDENCE_QUERY = "";

const runIdFromRecord = (record) => String(record?.metadata?.run_id || record?.run_id || "");

const runIdentifier = (record) => runIdFromRecord(record) || String(record?.job_id || "");

const executionBoundaryFromRun = (run, progress) => {
  const boundary = {
    ...(run?.metadata?.provider_runtime_boundary || {}),
    ...(progress?.provider_runtime_boundary || {})
  };
  const sourceName = String(boundary.provider_name || run?.provider_name || run?.metadata?.provider_name || "").trim();
  const sourceFamily = String(boundary.provider_family || "").trim();
  const evidenceMode = String(boundary.evidence_mode || "").trim();
  const modelVersion = String(run?.model_version || run?.metadata?.model_version || "").trim();
  const normalized = [sourceName, sourceFamily, evidenceMode, modelVersion].join(" ").toLowerCase();
  const isMock = normalized.includes("mock");
  const isLive = boundary.is_live_provider === true || evidenceMode === "live_synthetic";
  const tone = isMock ? "mock" : isLive ? "live" : "unknown";
  return {
    ...boundary,
    tone,
    labelKey: isMock ? "run.mockEvidenceLabel" : isLive ? "run.liveEvidenceLabel" : "run.unknownEvidenceLabel",
    messageKey: isMock ? "run.mockEvidenceBody" : isLive ? "run.liveEvidenceBody" : "run.unknownEvidenceBody",
    sourceName: sourceName || sourceFamily || modelVersion || "",
    evidenceMode,
    boundaryMessage: boundary.boundary_message || "",
  };
};

const numericOrNull = (value) => {
  const numberValue = Number.parseInt(value, 10);
  return Number.isFinite(numberValue) ? numberValue : null;
};

const transcriptStateForRun = (transcript, run, progress) => {
  const boundary = executionBoundaryFromRun(run, progress);
  const exchanges = Array.isArray(transcript?.exchanges) ? transcript.exchanges : [];
  const exchangeCount = numericOrNull(transcript?.exchange_count) ?? exchanges.length;
  const completedCount = numericOrNull(progress?.participant_progress?.completed_count)
    ?? numericOrNull(run?.successful_response_count)
    ?? numericOrNull(run?.metadata?.successful_response_count);
  const status = String(run?.status || progress?.status || "").toLowerCase();
  if (transcript === undefined) {
    return { state: "loading", titleKey: "run.transcriptLoadingTitle", bodyKey: "run.transcriptLoadingBody", tone: "loading", exchangeCount };
  }
  if (transcript === null) {
    return { state: "no_artifact", titleKey: "run.transcriptNoArtifactTitle", bodyKey: "run.transcriptNoArtifactBody", tone: "missing", exchangeCount };
  }
  if (exchanges.length === 0 && status === "completed" && (completedCount === 0 || exchangeCount === 0)) {
    return { state: "zero_responses", titleKey: "run.transcriptZeroResponsesTitle", bodyKey: "run.transcriptZeroResponsesBody", tone: "empty", exchangeCount };
  }
  if (boundary.tone === "mock") {
    return { state: "mock_summary", titleKey: "run.transcriptMockSummaryTitle", bodyKey: "run.transcriptMockSummaryBody", tone: "mock", exchangeCount };
  }
  if (exchanges.length === 0) {
    return { state: "preparing", titleKey: "run.transcriptPendingTitle", bodyKey: "run.transcriptPendingBody", tone: "loading", exchangeCount };
  }
  return { state: "ready", titleKey: "", bodyKey: "", tone: "ready", exchangeCount };
};

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
    : draft.personaSelectionUserEdited
      ? []
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
    readiness_status: personaLibrary?.readiness?.status || defaultSelection.readiness_status || "",
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

const evidenceFamilyLabelKeys = {
  all: "evidenceFamily.all",
  input: "evidenceFamily.input",
  trace: "evidenceFamily.trace",
  analysis: "evidenceFamily.analysis",
  output: "evidenceFamily.output"
};

const evidenceFamilyFallbackLabels = {
  all: "All evidence",
  input: "Source inputs",
  trace: "Behavior or response trace",
  analysis: "Interpretation",
  output: "Summary output"
};

const displayEvidenceFamily = (family, t) => {
  const key = String(family || "all");
  if (t && evidenceFamilyLabelKeys[key]) return t(evidenceFamilyLabelKeys[key]);
  return evidenceFamilyFallbackLabels[key] || cleanEvidenceCopy(String(family || "Evidence").replaceAll("_", " "));
};

const personaPanelLabelKeys = {
  mainstream: "persona.panel.mainstream",
  skeptic: "persona.panel.skeptic",
  privacy_sensitive: "persona.panel.privacySensitive",
  inclusion: "persona.panel.inclusion",
  political_risk: "persona.panel.politicalRisk",
  low_tech: "persona.panel.lowTech",
  budget_constrained: "persona.panel.budgetConstrained",
  extreme_user: "persona.panel.extremeUser",
  expert_advisor: "persona.panel.expertAdvisor"
};

const personaReadinessLabelKeys = {
  loading: "persona.readinessStatus.loading",
  ready: "persona.readinessStatus.ready",
  empty: "persona.readinessStatus.empty",
  generating: "persona.readinessStatus.generating",
  failed: "persona.readinessStatus.failed",
  stale: "persona.readinessStatus.stale",
  provisional: "persona.readinessStatus.provisional"
};

const personaReadinessMessageKeys = {
  ready: "persona.readinessMessage.ready",
  empty: "persona.readinessMessage.empty",
  generating: "persona.readinessMessage.generating",
  failed: "persona.readinessMessage.failed",
  stale: "persona.readinessMessage.stale",
  provisional: "persona.readinessMessage.provisional"
};

const personaSourceKindLabelKeys = {
  generated: "persona.source.generated",
  library: "persona.source.library",
  imported: "persona.source.imported"
};

const displayPersonaPanel = (panelType, t) => {
  const key = String(panelType || "mainstream");
  if (t && personaPanelLabelKeys[key]) return t(personaPanelLabelKeys[key]);
  return cleanEvidenceCopy(key.replaceAll("_", " "));
};

const displayPersonaReadinessStatus = (status, t) => {
  const key = String(status || "empty");
  if (t && personaReadinessLabelKeys[key]) return t(personaReadinessLabelKeys[key]);
  return cleanEvidenceCopy(key.replaceAll("_", " "));
};

const displayPersonaReadinessMessage = (readiness, t) => {
  const status = String(readiness?.status || "empty");
  if (t && personaReadinessMessageKeys[status]) return t(personaReadinessMessageKeys[status]);
  return cleanEvidenceCopy(readiness?.message || t("persona.readinessFallback"));
};

const displayPersonaSourceKind = (sourceKind, t) => {
  const key = String(sourceKind || "library");
  if (t && personaSourceKindLabelKeys[key]) return t(personaSourceKindLabelKeys[key]);
  return cleanEvidenceCopy(key.replaceAll("_", " "));
};

const zhHantKnownDataCopy = {
  "Do not treat synthetic participants as recruited market proof.": "不要把合成受訪者當成已招募真人市場證據。",
  "Synthetic participants are simulated for directional research only; this is not a recruited human sample.": "合成受訪者只用於方向性研究模擬，並不是已招募真人樣本。",
  "small business owner": "小企業東主",
  "program manager": "項目經理",
  "operations manager": "營運經理",
  "Kaohsiung": "高雄",
  "Hong Kong": "香港",
  "ad_hoc": "臨時處理",
  "tool heavy": "高度依賴工具",
  "repeatable": "有固定流程",
  "needs proof from concrete workflows, not just positioning": "需要具體工作流程證據，而不只看定位",
  "adopts when the payoff is concrete and the risk feels bounded": "當回報具體且風險可控時較願意採用",
  "control_preference": "控制偏好",
  "control preference": "控制偏好",
  "trust_style": "信任風格",
  "trust style": "信任風格",
  "complexity_tolerance": "複雜度承受度",
  "complexity tolerance": "複雜度承受度"
};

const displayKnownDataCopy = (value, locale) => {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (locale === "zh-Hant") {
    return zhHantKnownDataCopy[raw] || zhHantKnownDataCopy[raw.replaceAll("_", " ")] || raw.replaceAll("_", " ");
  }
  return raw.replaceAll("_", " ");
};

const evidenceDetailLines = (result) => (
  Array.isArray(result?.detail_lines) ? result.detail_lines.map(cleanEvidenceCopy).filter(Boolean) : []
);

const externalizeActionError = (message = "", t = (key, vars) => translate(DEFAULT_LOCALE, key, vars)) => {
  const text = String(message).toLowerCase();
  if (text.includes("select at least one synthetic participant")) {
    return t("error.selectPersona");
  }
  if (text.includes("provisional")) {
    return t("error.provisionalPersona");
  }
  if (text.includes("public-figure") || text.includes("celebrity") || text.includes("influencer")) {
    return t("error.simulatedLens");
  }
  if (text.includes("plan")) {
    return t("error.approvePlanFirst");
  }
  if (text.includes("billing") || text.includes("quota") || text.includes("limit")) {
    return t("error.quota");
  }
  if (text.includes("not found") || text.includes("not visible")) {
    return t("error.studyUnavailable");
  }
  return t("error.genericAction");
};

const nextActionForStudy = (study, t = (key, vars) => translate(DEFAULT_LOCALE, key, vars)) => {
  if (!study) return { label: t("action.startNewStudy"), path: "/studio/studies/new" };
  if (["draft", "planning"].includes(study.status)) {
    return { label: t("action.continueSetup"), path: `/studio/studies/${study.study_id}/setup` };
  }
  if (study.status === "ready_to_run") {
    return { label: t("action.startResearchRun"), path: `/studio/studies/${study.study_id}/setup` };
  }
  if (study.status === "running") {
    return { label: t("action.viewRunProgress"), path: `/studio/studies/${study.study_id}/runs` };
  }
  if (study.status === "reviewing") {
    return { label: t("action.reviewEvidence"), path: `/studio/studies/${study.study_id}/evidence` };
  }
  return { label: t("action.openDecision"), path: `/studio/studies/${study.study_id}` };
};

function App() {
  const loadSequenceRef = useRef(0);
  const evidenceHydrationRetryRef = useRef(new Map());
  const [locale, setLocale] = useState(() => resolveInitialLocale());
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
    researchPlaybooks: null,
    calibrationObservatory: null,
    privacyExportControls: null,
    integrationEvents: null,
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
    playbookId: "concept_validation",
    selectedPersonaIds: [],
    personaSelectionUserEdited: false,
    personaSampleSize: 3,
    personaGenerationCount: 3,
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
  const i18n = useMemo(() => ({
    locale,
    setLocale,
    t: (key, vars) => translate(locale, key, vars)
  }), [locale]);
  const { t } = i18n;

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
        personaPayload,
        routeStudyPayload,
        routeStudyReportPayload,
        routeEvidenceViewPayload,
        routeDecisionLogPayload,
        routeShareBundlePayload,
        playbooksPayload,
        calibrationPayload,
        privacyPayload,
        integrationPayload
      ] = await Promise.all([
        api("/api/v1/session"),
        optionalApi("/api/v1/projects"),
        optionalApi("/api/v1/studies"),
        optionalApi("/api/v1/validation-jobs"),
        shouldLoadPersonaLibrary ? optionalApi(personaLibraryPath) : Promise.resolve(null),
        activeRoute.study_id ? optionalApi(`/api/v1/studies/${encodeURIComponent(activeRoute.study_id)}`) : Promise.resolve(null),
        activeRoute.study_report_id ? optionalApi(`/api/v1/study-reports/${encodeURIComponent(activeRoute.study_report_id)}`) : Promise.resolve(null),
        activeRoute.evidence_view_id ? optionalApi(`/api/v1/evidence-views/${encodeURIComponent(activeRoute.evidence_view_id)}`) : Promise.resolve(null),
        activeRoute.decision_log_id ? optionalApi(`/api/v1/decision-logs/${encodeURIComponent(activeRoute.decision_log_id)}`) : Promise.resolve(null),
        activeRoute.share_bundle_id ? optionalApi(`/api/v1/share-bundles/${encodeURIComponent(activeRoute.share_bundle_id)}`) : Promise.resolve(null),
        optionalApi("/api/v1/research-playbooks"),
        optionalApi("/api/v1/calibration-observatory"),
        optionalApi("/api/v1/privacy-export-controls"),
        optionalApi("/api/v1/integration-events?limit=12")
      ]);
    const projects = projectsPayload?.projects || [];
    const studies = routeStudyPayload?.study
      ? prependUniqueBy(studiesPayload?.studies || [], "study_id", routeStudyPayload.study)
      : studiesPayload?.studies || [];
    const jobs = jobsPayload?.jobs || [];
    const routeObjects = {};
    if (activeRoute.study_report_id) routeObjects.studyReport = routeStudyReportPayload?.study_report || null;
    if (activeRoute.evidence_view_id) routeObjects.evidenceView = routeEvidenceViewPayload?.evidence_view || null;
    if (activeRoute.decision_log_id) {
      routeObjects.decisionLog = routeDecisionLogPayload?.decision_log || null;
      routeObjects.decisionComments = routeDecisionLogPayload?.decision_comments || [];
    }
    if (activeRoute.share_bundle_id) routeObjects.shareBundle = routeShareBundlePayload?.share_bundle || null;

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
          optionalApi(`/api/v1/study-reports?study_id=${encodeURIComponent(selectedStudyId)}`),
          optionalApi(`/api/v1/evidence-views?study_id=${encodeURIComponent(selectedStudyId)}`),
          optionalApi(`/api/v1/decision-logs?study_id=${encodeURIComponent(selectedStudyId)}`),
          optionalApi(`/api/v1/export-bundles?study_id=${encodeURIComponent(selectedStudyId)}`),
          optionalApi(`/api/v1/share-bundles?study_id=${encodeURIComponent(selectedStudyId)}`)
        ])
      : [{ study_reports: [] }, { evidence_views: [] }, { decision_logs: [] }, { export_bundles: [] }, { share_bundles: [] }];
    const evidenceViews = viewsPayload?.evidence_views || [];
    if (activeRoute.evidence_view_id && !routeObjects.evidenceView) {
      routeObjects.evidenceView = evidenceViews.find((view) => view.evidence_view_id === activeRoute.evidence_view_id) || null;
    }

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
    if (activeRoute.route_kind === "run" && selectedStudyId && evidenceSourceRun) {
      const runDetailId = activeRoute.run_id || runIdentifier(evidenceSourceRun);
      const [progressPayload, transcriptPayload, tracePayload, eventStreamPayload] = await Promise.all([
        optionalApi(`/api/v1/studies/${encodeURIComponent(selectedStudyId)}/runs/${encodeURIComponent(runDetailId)}/progress`),
        optionalApi(`/api/v1/studies/${encodeURIComponent(selectedStudyId)}/runs/${encodeURIComponent(runDetailId)}/transcript`),
        optionalApi(`/api/v1/studies/${encodeURIComponent(selectedStudyId)}/runs/${encodeURIComponent(runDetailId)}/trace`),
        optionalApi(`/api/v1/studies/${encodeURIComponent(selectedStudyId)}/runs/${encodeURIComponent(runDetailId)}/events`)
      ]);
      routeObjects.runProgress = progressPayload?.run_progress || null;
      routeObjects.runTranscript = transcriptPayload?.run_transcript || null;
      routeObjects.runTrace = tracePayload?.run_trace || null;
      routeObjects.runEventStream = eventStreamPayload?.run_event_stream || null;
    }

      if (loadSequence !== loadSequenceRef.current) return null;
      setModel({
        loading: false,
        error: "",
        session: sessionPayload.session,
        projects,
        studies,
        jobs,
        exportBundles: exportsPayload?.export_bundles || [],
        personaLibrary: personaPayload?.persona_library || null,
        researchPlaybooks: playbooksPayload?.research_playbooks || null,
        calibrationObservatory: calibrationPayload?.calibration_observatory || null,
        privacyExportControls: privacyPayload?.privacy_export_controls || null,
        integrationEvents: integrationPayload?.integration_events || null,
        studyReports: reportsPayload?.study_reports || [],
        evidenceViews,
        decisionLogs: decisionsPayload?.decision_logs || [],
        shareBundles: sharesPayload?.share_bundles || [],
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
    document.documentElement.lang = localeHtmlLang(locale);
    try {
      window.localStorage.setItem("frontline_studio_locale", locale);
    } catch {
      // Locale persistence is a convenience; rendering should not depend on storage access.
    }
  }, [locale]);

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
    if (!defaultIds.length) return;
    setDraft((current) => (
      current.selectedPersonaIds.length
        || current.personaSelectionUserEdited
        || (
          model.personaLibrary?.active_panel_type
          && model.personaLibrary.active_panel_type !== current.selectedPanelType
        )
        ? current
        : {
            ...current,
            selectedPersonaIds: defaultIds,
            selectedPanelType: model.personaLibrary?.active_panel_type || current.selectedPanelType,
            personaSampleSize: model.personaLibrary?.default_selection?.sample_size || current.personaSampleSize
          }
    ));
  }, [defaultPersonaSelectionKey, draft.selectedPersonaIds.length, draft.personaSelectionUserEdited, model.personaLibrary?.active_panel_type, model.personaLibrary?.default_selection?.sample_size]);

  const routeHasStudyContext = STUDY_ROUTE_KINDS.has(routeContext.route_kind);
  const routeDetailObject = model.routeObjects.studyReport
    || model.routeObjects.evidenceView
    || model.routeObjects.decisionLog
    || model.routeObjects.shareBundle
    || null;
  const routeStudyId = routeContext.study_id || routeDetailObject?.study_id || model.selectedStudyId || "";
  const routeProjectId = routeContext.project_id || routeDetailObject?.project_id || model.selectedProjectId || "";
  const selectedStudyRecord = routeStudyId
    ? model.studies.find((study) => study.study_id === routeStudyId)
    : null;
  const hasRouteStudyArtifacts = Boolean(routeDetailObject)
    || model.jobs.some((job) => String(job?.metadata?.study_id || "") === routeStudyId)
    || model.studyReports.some((report) => String(report?.study_id || "") === routeStudyId)
    || model.evidenceViews.some((view) => String(view?.study_id || "") === routeStudyId)
    || model.decisionLogs.some((decision) => String(decision?.study_id || "") === routeStudyId)
    || model.shareBundles.some((share) => String(share?.study_id || "") === routeStudyId);
  const selectedStudyFallback = routeHasStudyContext && routeStudyId && hasRouteStudyArtifacts
    ? {
        study_id: routeStudyId,
        project_id: routeProjectId || selectedStudyRecord?.project_id || "",
        title: t("study.linkedStudy"),
        status: "reviewing",
        research_intent: "",
        desired_output: "",
        artifact_refs: [],
        metadata: {},
        frontline: {}
      }
    : null;
  const selectedStudy = routeHasStudyContext
    ? selectedStudyRecord || selectedStudyFallback
    : null;
  const selectedProject = model.projects.find((project) => {
    const projectId = routeContext.project_id || selectedStudy?.project_id || (routeContext.route_kind === "new_study" ? model.selectedProjectId : "");
    return project.project_id === projectId;
  });
  const studyRuns = model.jobs.filter((job) => String(job?.metadata?.study_id || "") === selectedStudy?.study_id);
  const selectedRun = findRunByRouteIdentifier(studyRuns, routeContext.run_id);
  const selectedRunIdentifier = runIdentifier(selectedRun);

  useEffect(() => {
    if (
      routeContext.route_kind !== "run"
      || model.loading
      || !selectedRunIdentifier
      || String(selectedRun?.status || "") !== "completed"
      || model.evidenceQuery?.query_status === "query_ready"
    ) {
      return undefined;
    }
    const retryKey = `${routeContext.route_path}:${selectedRunIdentifier}`;
    const attempts = evidenceHydrationRetryRef.current.get(retryKey) || 0;
    if (attempts >= 3) return undefined;
    evidenceHydrationRetryRef.current.set(retryKey, attempts + 1);
    const timer = window.setTimeout(() => {
      loadWorkspace(routeContext).catch(() => {});
    }, 800 + attempts * 1000);
    return () => window.clearTimeout(timer);
  }, [
    routeContext.route_path,
    routeContext.route_kind,
    selectedRunIdentifier,
    selectedRun?.status,
    model.loading,
    model.evidenceQuery?.query_status
  ]);
  const latestEvidenceView = model.evidenceViews[0];
  const latestExportBundle = model.exportBundles[0];
  const latestReport = model.studyReports[0];
  const latestDecision = model.decisionLogs[0];
  const latestShare = model.shareBundles[0];
  const selectedPlaybook = (model.researchPlaybooks?.playbooks || []).find((item) => item.playbook_id === draft.playbookId) || null;

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
            playbook_id: selectedPlaybook?.playbook_id || "",
            mode_inference: selectedPlaybook
              ? { mode: selectedPlaybook.mode, confidence: "playbook_selected", rationale: "Selected from guided research starts." }
              : {},
            moderator_interview_guide: {
              contract_version: "moderator-interview-guide/v0-draft",
              questions: moderatorQuestions,
              focus: draft.guideFocus
            },
            expected_evidence_types: selectedPlaybook?.expected_evidence_types || ["objections", "trust gaps", "adoption barriers", "contradictions", "human-validation gaps"]
          },
          metadata: {
            source: "frontline_research_studio",
            planning_intake: {
              playbook_id: selectedPlaybook?.playbook_id || "",
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
      setDraft((current) => ({ ...current, selectedProjectId: projectId, actionNotice: t("notice.studyDraftSaved") }));
      navigate(`/studio/studies/${study.study.study_id}/setup`);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t) }));
    }
  };

  const generatePersonaLibrary = async () => {
    setDraft((current) => ({ ...current, actionError: "", actionNotice: t("notice.buildingPersonas") }));
    try {
      const targetAudience = buildTargetAudiencePayload(draft);
      const payload = await api("/api/v1/persona-library/generation-jobs", {
        method: "POST",
        body: JSON.stringify({
          panel_type: draft.selectedPanelType || "mainstream",
          requested_count: Number(draft.personaGenerationCount || draft.personaSampleSize || 3),
          random_seed: Number(draft.personaRandomSeed || 41),
          target_audience: targetAudience,
          metadata: {
            source: "frontline_research_studio",
            reason: "persona_library_gap_fill"
          }
        })
      });
      await loadWorkspace(routeContext);
      const generatedCount = payload?.persona_generation_job?.generated_persona_ids?.length || 0;
      setDraft((current) => ({
        ...current,
        personaSelectionUserEdited: false,
        actionError: "",
        actionNotice: generatedCount
          ? t("notice.personasGenerated", { count: generatedCount })
          : t("notice.personaGenerationQueued")
      }));
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
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
          mode: selectedPlaybook?.mode || "",
          metadata: {
            source: "frontline_research_studio",
            playbook_id: selectedPlaybook?.playbook_id || "",
            target_audience: targetAudience,
            persona_panel: personaPanel,
            guide_focus: draft.guideFocus
          }
        })
      });
      setDraft((current) => ({ ...current, proposal: payload.plan_proposal, actionNotice: t("notice.draftPlanReady") }));
      if (payload.study) {
        setModel((current) => ({
          ...current,
          studies: prependUniqueBy(current.studies, "study_id", payload.study),
          selectedStudyId: payload.study.study_id || current.selectedStudyId
        }));
      }
      await loadWorkspace(routeContext);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t) }));
    }
  };

  const confirmPlan = async () => {
    if (!selectedStudy?.study_id) return;
    const proposalId = draft.proposal?.plan_proposal_id || selectedStudy?.frontline?.latest_plan_proposal_id || "";
    if (!proposalId) return;
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      await postJsonWithoutPayload(`/api/v1/studies/${selectedStudy.study_id}/frontline-plan-revisions`, {
        plan_proposal_id: proposalId,
        confirmation_note: "Approved from Frontline Studio.",
        metadata: { source: "frontline_research_studio" }
      });
      setDraft((current) => ({
        ...current,
        revision: {
          ...(current.proposal || {}),
          plan_revision_id: `approved_${proposalId}`,
          source_plan_proposal_id: proposalId
        },
        actionNotice: t("notice.planApproved")
      }));
      await loadWorkspace(routeContext);
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t) }));
    }
  };

  const startResearchRun = async () => {
    if (!selectedStudy?.study_id) return;
    const studyId = selectedStudy.study_id;
    const runsRoute = { route_path: `/studio/studies/${studyId}/runs`, route_kind: "study_runs", study_id: studyId };
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      await postJsonWithoutPayload(`/api/v1/studies/${studyId}/frontline-runs`, {
        metadata: { source: "frontline_research_studio" }
      });
      navigate(runsRoute.route_path);
      setModel((current) => ({
        ...current,
        loading: false,
        selectedStudyId: studyId
      }));
      await loadWorkspace(runsRoute);
      setDraft((current) => ({
        ...current,
        latestRun: current.latestRun,
        actionNotice: t("notice.researchRunStarted")
      }));
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t) }));
    }
  };

  const createRerunPlan = async (sourceRun = null) => {
    if (!selectedStudy?.study_id) return;
    const source = sourceRun || selectedRun || latestCompletedStudyRun(studyRuns);
    if (!source) return;
    setDraft((current) => ({ ...current, actionError: "", actionNotice: "" }));
    try {
      const payload = await api(`/api/v1/studies/${selectedStudy.study_id}/frontline-reruns`, {
        method: "POST",
        body: JSON.stringify({
          source_run_id: runIdentifier(source),
          playbook_id: draft.playbookId || selectedPlaybook?.playbook_id || "concept_validation",
          change_set: {
            moderator_questions: normalizeLines(draft.guideQuestions),
            guide_focus: draft.guideFocus,
            artifact_refs: draft.artifactNotes?.trim() ? [draft.artifactNotes.trim()] : []
          },
          metadata: {
            source: "frontline_research_studio",
            reason: "prepare_comparison_ready_rerun"
          }
        })
      });
      setDraft((current) => ({
        ...current,
        proposal: payload.rerun_plan,
        actionNotice: t("notice.rerunPlanReady")
      }));
      if (payload.study) {
        setModel((current) => ({
          ...current,
          studies: prependUniqueBy(current.studies, "study_id", payload.study),
          selectedStudyId: payload.study.study_id || current.selectedStudyId
        }));
      }
      navigate(`/studio/studies/${selectedStudy.study_id}/setup`);
      await loadWorkspace({ route_path: `/studio/studies/${selectedStudy.study_id}/setup`, route_kind: "study_setup", study_id: selectedStudy.study_id });
    } catch (error) {
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
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
        actionError: t("error.completeRunBeforeEvidenceView"),
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
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
    }
  };

  const createStudyReport = async () => {
    if (!selectedStudy?.study_id) return;
    const includedRunIds = completedStudyRuns(studyRuns).map(runIdFromRecord).filter(Boolean);
    if (!includedRunIds.length) {
      setDraft((current) => ({
        ...current,
        actionError: t("error.completeRunBeforeReport"),
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
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
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
        actionError: t("error.completeRunBeforeDecision"),
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
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
    }
  };

  const createShareBundle = async () => {
    if (!selectedStudy?.study_id) return;
    const decision = model.routeObjects.decisionLog || latestDecision;
    if (!decision?.decision_log_id) {
      setDraft((current) => ({
        ...current,
        actionError: t("error.decisionBeforeShare"),
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
        actionError: t("error.completeRunBeforeShare"),
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
      setDraft((current) => ({ ...current, actionError: externalizeActionError(error.message, t), actionNotice: "" }));
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
    generatePersonaLibrary,
    proposePlan,
    confirmPlan,
    startResearchRun,
    createRerunPlan,
    createEvidenceView,
    createStudyReport,
    createDecisionLog,
    createShareBundle,
    evidenceControls,
    setEvidenceControls
  };

  return (
    <I18nContext.Provider value={i18n}>
    <main className="studio" data-route-kind={routeContext.route_kind} data-contract-version="frontline-research-studio/v1-route-shell">
      <aside className="studio-rail">
        <div className="rail-top">
          {navLevel === "projects" ? (
            <a className="rail-home-link" href="/studio" onClick={(event) => {
              event.preventDefault();
              navigate("/studio");
            }}>
              {t("app.name")}
            </a>
          ) : (
            <button id="nav-back" className="back-button" type="button" onClick={() => navigate(navBackPath)}>
              <span aria-hidden="true">&lt;</span>
              {navLevel === "study" ? t("nav.backProject") : t("nav.backProjects")}
            </button>
          )}
          <p className="kicker">{navLevel === "study" ? t("nav.studyWorkspace") : navLevel === "project" ? t("nav.projectWorkspace") : t("nav.projects")}</p>
          <h1>{navLevel === "study" ? selectedStudy.title : navLevel === "project" ? selectedProject.name : t("nav.chooseProject")}</h1>
        </div>
        <div className="rail-scroll">
          {navLevel === "projects" ? (
            <nav className="context-nav nav-level" id="project-list" aria-label={t("nav.projectList")}>
              {navLink({ id: "nav-projects", label: t("nav.allProjects"), path: "/studio/projects", detail: t("nav.browseCreateContexts"), active: routeContext.route_kind === "projects" })}
              {model.projects.length ? model.projects.slice(0, 8).map((project) => navLink({
                id: `project-nav-${project.project_id}`,
                label: project.name,
                path: `/studio/projects/${project.project_id}`,
                detail: `${project.study_count || 0} ${t("nav.studies")}`,
                active: false
              })) : <p className="nav-empty">{t("nav.noProjects")}</p>}
            </nav>
          ) : null}
          {navLevel === "project" ? (
            <nav className="context-nav nav-level" id="project-study-list" aria-label={t("nav.projectStudies")}>
              {navLink({ id: "project-nav-overview", label: t("nav.projectOverview"), path: `/studio/projects/${selectedProject.project_id}`, detail: t("nav.studiesOpenDecisions"), active: routeContext.route_kind === "project" })}
              {navLink({ id: "project-nav-new-study", label: t("nav.newStudy"), path: "/studio/studies/new", detail: t("nav.startFromQuestion"), active: routeContext.route_kind === "new_study" })}
              <span className="ia-nav-label">{t("nav.studies")}</span>
              {projectStudies.length ? projectStudies.slice(0, 10).map((study) => navLink({
                id: `project-study-nav-${study.study_id}`,
                label: study.title,
                path: `/studio/studies/${study.study_id}`,
                detail: formatStudyStatus(study.status, t),
                active: false
              })) : <p className="nav-empty">{t("nav.noStudiesProject")}</p>}
            </nav>
          ) : null}
          {navLevel === "study" ? (
            <nav className="context-nav nav-level" id="study-nav" aria-label={t("nav.studyWorkspace")}>
              {navLink({ id: "study-nav-home", label: t("nav.studyHome"), path: `/studio/studies/${selectedStudy.study_id}`, detail: t("nav.questionPlanNext"), active: routeContext.route_kind === "study" })}
              {navLink({ id: "study-nav-setup", label: t("nav.guidedSetup"), path: `/studio/studies/${selectedStudy.study_id}/setup`, detail: t("nav.askClarifyApprove"), active: routeContext.route_kind === "study_setup" })}
              {navLink({ id: "study-nav-runs", label: t("nav.researchAttempts"), path: `/studio/studies/${selectedStudy.study_id}/runs`, detail: t("nav.attemptsUnderStudy"), active: ["study_runs", "run"].includes(routeContext.route_kind) })}
              {navLink({ id: "study-nav-evidence", label: t("nav.evidence"), path: `/studio/studies/${selectedStudy.study_id}/evidence`, detail: t("nav.signalsSavedViews"), active: ["study_evidence", "evidence_view", "study_report"].includes(routeContext.route_kind) })}
              {navLink({ id: "study-nav-report", label: t("nav.report"), path: studyReportPath, detail: t("nav.studyLevelSynthesis"), active: routeContext.route_kind === "study_report" })}
              {navLink({ id: "study-nav-decision", label: t("nav.decision"), path: studyDecisionPath, detail: t("nav.beliefUncertaintyFollowup"), active: routeContext.route_kind === "decision" })}
              {navLink({ id: "study-nav-share", label: t("nav.share"), path: sharePath, detail: t("nav.boundarySafeCollab"), active: false })}
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
    </I18nContext.Provider>
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
  const { locale, setLocale, t } = useI18n();
  const workspaceName = session?.workspace?.display_name || "Workspace";
  const role = session?.auth?.role || "member";
  const roleLabel = role === "member" ? t("account.member") : role;
  const initials = workspaceName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "WS";
  return (
    <footer className="rail-bottom" aria-label={t("account.label")}>
      <div className="language-switcher" aria-label={t("language.label")}>
        <span>{t("language.label")}</span>
        <div className="language-chip-row">
          {SUPPORTED_LOCALES.map((option) => (
            <button
              className={locale === option.code ? "language-chip is-active" : "language-chip"}
              key={option.code}
              onClick={() => setLocale(option.code)}
              type="button"
              aria-pressed={locale === option.code}
            >
              {option.shortLabel}
            </button>
          ))}
        </div>
      </div>
      <div className="workspace-avatar" aria-hidden="true">{initials}</div>
      <div className="workspace-user">
        <strong>{workspaceName}</strong>
        <span>{roleLabel}</span>
      </div>
    </footer>
  );
}

function RouteHeader({ routeContext, selectedProject, selectedStudy }) {
  const { t } = useI18n();
  const labels = {
    workspace: t("route.home"),
    projects: t("route.projects"),
    project: selectedProject?.name || t("route.project"),
    new_study: t("route.newStudy"),
    study: selectedStudy?.title || t("route.study"),
    study_setup: t("route.guidedSetup"),
    study_runs: t("route.researchAttempts"),
    run: t("route.researchAttempt"),
    study_evidence: t("route.evidenceWorkspace"),
    evidence_view: t("route.savedEvidenceView"),
    study_report: t("route.studyReport"),
    decision: t("route.decisionReview"),
    share: t("route.shareView"),
    share_collection: t("route.share")
  };
  const routeLabel = labels[routeContext.route_kind] || t("route.workspace");
  return (
    <header className="route-header">
      <div>
        <p className="kicker">{t("route.workspaceLocation")}</p>
        <h2 id="route-title">{routeLabel}</h2>
      </div>
      <div className="route-pill">
        <span>{t("route.currentPage")}</span>
        <strong id="route-kind">{routeLabel}</strong>
      </div>
    </header>
  );
}

function StudyContextHeader({ selectedStudy, draft, navigate }) {
  const { t } = useI18n();
  const action = nextActionForStudy(selectedStudy, t);
  const approvedPlanId = selectedStudy.current_plan_revision_id || draft?.revision?.plan_revision_id || "";
  const hasNewRun = Boolean(draft?.latestRun?.job_id);
  const hasDraftProposal = Boolean(
    draft?.proposal?.plan_proposal_id
    || selectedStudy.frontline?.latest_plan_proposal_id
    || selectedStudy.frontline?.latest_plan_proposal?.plan_proposal_id
    || selectedStudy.draft_plan?.plan_proposal_id
  );
  const displayStatus = hasNewRun && ["draft", "planning", "ready_to_run"].includes(selectedStudy.status)
    ? "running"
    : hasDraftProposal && ["draft", "planning"].includes(selectedStudy.status)
      ? "ready_to_run"
    : selectedStudy.status;
  return (
    <section className="study-context" aria-label="Study context">
      <div>
        <p className="kicker">{t("study.currentStudy")}</p>
        <h3 id="selected-study">{selectedStudy.title}</h3>
        <p>{selectedStudy.research_intent || t("study.noIntent")}</p>
      </div>
      <dl>
        <dt>{t("study.status")}</dt>
        <dd id="study-status">{formatStudyStatus(displayStatus, t)}</dd>
        <dt>{t("study.approvedPlan")}</dt>
        <dd id="plan-revision">{approvedPlanId ? t("study.approved") : t("study.notApprovedYet")}</dd>
      </dl>
      <button onClick={() => navigate(action.path)}>{action.label}</button>
    </section>
  );
}

function WorkspaceRoute({ model, navigate }) {
  const { t } = useI18n();
  const recentStudies = model.studies.slice(0, 5);
  return (
    <div className="route-stack">
      <section className="hero-panel">
        <div>
          <p className="kicker">{t("workspace.kicker")}</p>
          <h2>{t("workspace.heroTitle")}</h2>
          <p>{t("workspace.heroBody")}</p>
        </div>
        <div className="status-card">
          <span>{t("account.workspace")}</span>
          <strong>{model.session?.workspace?.display_name || t("account.workspace")}</strong>
          <small>{model.session?.auth?.role === "member" ? t("account.member") : model.session?.auth?.role || t("account.member")}</small>
        </div>
      </section>
      <section className="workspace-grid">
        <article className="paper-card primary-card">
          <p className="kicker">{t("workspace.startKicker")}</p>
          <h3>{t("workspace.startTitle")}</h3>
          <p>{t("workspace.startBody")}</p>
          <button id="start-new-study" onClick={() => navigate("/studio/studies/new")}>{t("action.startNewStudy")}</button>
        </article>
        <article className="paper-card">
          <p className="kicker">{t("workspace.boundaryKicker")}</p>
          <h3>{t("workspace.boundaryTitle")}</h3>
          <EvidenceBoundaryNotice />
        </article>
        <CalibrationObservatoryCard observatory={model.calibrationObservatory} />
        <PrivacyExportControlsCard controls={model.privacyExportControls} />
        <IntegrationEventsCard integrationEvents={model.integrationEvents} />
      </section>
      <section className="object-list" aria-label="Recent studies">
        <ListHeader title={t("workspace.recentStudies")} action={t("workspace.openAllProjects")} onAction={() => navigate("/studio/projects")} />
        {recentStudies.length ? recentStudies.map((study) => (
          <ObjectRow
            key={study.study_id}
            title={study.title}
            meta={`${formatStudyStatus(study.status, t)} | ${study.run_count || 0} ${t("metric.researchAttempts")} | ${study.study_report_count || 0} ${t("metric.studyReports")}`}
            cta={t("action.openStudy")}
            onClick={() => navigate(`/studio/studies/${study.study_id}`)}
          />
        )) : <EmptyState title={t("workspace.noStudies")} body={t("workspace.noStudiesBody")} cta={t("action.startNewStudy")} onClick={() => navigate("/studio/studies/new")} />}
      </section>
    </div>
  );
}

function CalibrationObservatoryCard({ observatory }) {
  const { t } = useI18n();
  const health = observatory?.health_summary || {};
  const segments = observatory?.segments || {};
  return (
    <article className="paper-card calibration-card" id="calibration-observatory-card">
      <p className="kicker">{t("calibration.kicker")}</p>
      <h3>{cleanEvidenceCopy(health.status || t("common.pending")).replaceAll("_", " ")}</h3>
      <MetricGrid items={[
        [t("calibration.completedRuns"), health.completed_run_count ?? 0],
        [t("calibration.calibratedRuns"), health.calibrated_run_count ?? 0],
        [t("calibration.providers"), Object.keys(segments.provider_counts || {}).length],
        [t("calibration.launchGate"), cleanEvidenceCopy(health.launch_gate_status || t("common.pending")).replaceAll("_", " ")]
      ]} />
      <p className="boundary">{cleanEvidenceCopy(observatory?.synthetic_boundary || t("calibration.boundary"))}</p>
    </article>
  );
}

function PrivacyExportControlsCard({ controls, compact = false }) {
  const { t } = useI18n();
  const readiness = controls?.privacy_readiness || {};
  const retention = controls?.retention_controls || {};
  const residency = controls?.data_residency || {};
  const deletion = controls?.deletion_controls || {};
  const distribution = controls?.export_share_controls || {};
  const blockers = Array.isArray(readiness.blocked_reasons) ? readiness.blocked_reasons : [];
  return (
    <article className={`paper-card privacy-card${compact ? " compact-privacy-card" : ""}`} id={compact ? "share-privacy-boundary" : "privacy-export-controls-card"}>
      <p className="kicker">{t("privacy.kicker")}</p>
      <h3>{cleanEvidenceCopy(readiness.status || t("common.pending")).replaceAll("_", " ")}</h3>
      <MetricGrid items={[
        [t("privacy.retentionDays"), retention.artifact_retention_days ?? 0],
        [t("privacy.region"), residency.data_residency_region || t("common.pending")],
        [t("privacy.exports"), distribution.export_bundle_count ?? 0],
        [t("privacy.shares"), distribution.share_bundle_count ?? 0]
      ]} />
      <SignalList
        items={blockers.map((reason) => ({
          label: cleanEvidenceCopy(reason).replaceAll("_", " "),
          note: t("privacy.blockerNote")
        }))}
        fallback={t("privacy.noBlockers")}
      />
      <p className="boundary">
        {cleanEvidenceCopy(distribution.user_boundary_copy || deletion.audit_note || controls?.synthetic_boundary || t("privacy.boundary"))}
      </p>
    </article>
  );
}

function IntegrationEventsCard({ integrationEvents }) {
  const { t } = useI18n();
  const events = Array.isArray(integrationEvents?.events) ? integrationEvents.events : [];
  const delivery = integrationEvents?.delivery_audit || {};
  const latest = events[0] || {};
  return (
    <article className="paper-card integration-card" id="integration-events-card">
      <p className="kicker">{t("integration.kicker")}</p>
      <h3>{latest.event_type ? cleanEvidenceCopy(latest.event_type).replaceAll("_", " ") : t("integration.title")}</h3>
      <MetricGrid items={[
        [t("integration.readyEvents"), events.length],
        [t("integration.deliveryAttempts"), delivery.attempt_count ?? 0],
        [t("integration.latestDelivery"), delivery.latest_attempt?.status ? cleanEvidenceCopy(delivery.latest_attempt.status) : t("common.pending")],
        [t("integration.boundaryMode"), t("integration.boundaryModeValue")]
      ]} />
      <SignalList
        items={events.slice(0, 3).map((event) => ({
          label: cleanEvidenceCopy(event.event_type || t("integration.event")).replaceAll("_", " "),
          note: cleanEvidenceCopy(event.synthetic_boundary || t("integration.eventBoundary"))
        }))}
        fallback={t("integration.noEvents")}
      />
      <p className="boundary">{cleanEvidenceCopy(integrationEvents?.synthetic_boundary || t("integration.boundary"))}</p>
    </article>
  );
}

function ProjectsRoute({ model, draft, setDraft, createProject, navigate }) {
  const { t } = useI18n();
  return (
    <div className="route-grid">
      <section className="object-list wide-list" aria-label="Projects">
        <ListHeader title={t("projects.title")} action={t("action.createProject")} onAction={createProject} />
        {model.projects.length ? model.projects.map((project) => (
          <ObjectRow
            key={project.project_id}
            title={project.name}
            meta={`${project.study_count || 0} ${t("nav.studies")} | ${project.active_decision_count || 0} ${t("nav.decision")}`}
            cta={t("action.openProject")}
            onClick={() => navigate(`/studio/projects/${project.project_id}`)}
          />
        )) : <EmptyState title={t("nav.noProjects")} body={t("projects.noProjectsBody")} cta={t("action.createProject")} onClick={createProject} />}
      </section>
      <aside className="paper-card">
        <p className="kicker">{t("projects.createKicker")}</p>
        <h3>{t("projects.createTitle")}</h3>
        <input value={draft.newProjectName} onChange={(event) => setDraft({ ...draft, newProjectName: event.target.value })} aria-label={t("newStudy.newProjectName")} />
        <textarea value={draft.projectDescription} onChange={(event) => setDraft({ ...draft, projectDescription: event.target.value })} aria-label="Project description" />
        <button onClick={createProject}>{t("action.createProject")}</button>
      </aside>
    </div>
  );
}

function ProjectDetailRoute({ selectedProject, model, navigate }) {
  const { t } = useI18n();
  if (!selectedProject) {
    return <EmptyState title={t("project.notFoundTitle")} body={t("project.notFoundBody")} cta={t("action.viewProjects")} onClick={() => navigate("/studio/projects")} />;
  }
  const studies = model.studies.filter((study) => study.project_id === selectedProject.project_id);
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{t("project.kicker")}</p>
          <h2>{selectedProject.name}</h2>
          <p>{selectedProject.description || t("project.defaultDescription")}</p>
        </div>
        <button onClick={() => navigate("/studio/studies/new")}>{t("project.startInProject")}</button>
      </section>
      <section className="object-list">
        <ListHeader title={t("project.studiesInProject")} action={t("action.startStudy")} onAction={() => navigate("/studio/studies/new")} />
        {studies.length ? studies.map((study) => (
          <ObjectRow
            key={study.study_id}
            title={study.title}
            meta={`${formatStudyStatus(study.status, t)} | ${study.evidence_view_count || 0} ${t("metric.savedEvidenceViews")} | ${study.decision_log_count || 0} ${t("metric.decisionLogs")}`}
            cta={t("action.openStudy")}
            onClick={() => navigate(`/studio/studies/${study.study_id}`)}
          />
        )) : <EmptyState title={t("project.noStudiesTitle")} body={t("project.noStudiesBody")} cta={t("action.startStudy")} onClick={() => navigate("/studio/studies/new")} />}
      </section>
    </div>
  );
}

function PlaybookQuickStarts({ model, draft, setDraft }) {
  const { t } = useI18n();
  const playbooks = Array.isArray(model.researchPlaybooks?.playbooks) ? model.researchPlaybooks.playbooks : [];
  if (!playbooks.length) return null;
  const selected = playbooks.find((item) => item.playbook_id === draft.playbookId) || playbooks[0];
  return (
    <section className="paper-card playbook-card" id="research-playbook-picker">
      <p className="kicker">{t("playbook.kicker")}</p>
      <h3>{t("playbook.title")}</h3>
      <p>{t("playbook.body")}</p>
      <select
        value={selected.playbook_id}
        onChange={(event) => setDraft({
          ...draft,
          playbookId: event.target.value,
          guideQuestions: linesToText((playbooks.find((item) => item.playbook_id === event.target.value) || selected).starter_questions || draft.guideQuestions)
        })}
        aria-label={t("playbook.selectLabel")}
      >
        {playbooks.map((playbook) => (
          <option key={playbook.playbook_id} value={playbook.playbook_id}>{playbook.label}</option>
        ))}
      </select>
      <SignalList
        items={(selected.expected_evidence_types || []).slice(0, 4).map((item) => ({ label: cleanEvidenceCopy(item).replaceAll("_", " ") }))}
        fallback={t("playbook.noEvidence")}
      />
      <p className="boundary">{model.researchPlaybooks?.synthetic_boundary || t("playbook.boundary")}</p>
    </section>
  );
}

function NewStudyRoute({ model, draft, setDraft, selectedProject, createProjectAndStudy }) {
  const { t } = useI18n();
  const projectValue = draft.selectedProjectId || selectedProject?.project_id || "__new__";
  const nextQuestion = !draft.intent.trim()
    ? t("newStudy.questionDecision")
    : !draft.targetParticipant.trim()
      ? t("newStudy.questionParticipant")
      : !draft.artifactNotes.trim()
        ? t("newStudy.questionArtifact")
        : t("newStudy.questionReview");
  return (
    <div className="route-grid">
      <section className="paper-card composer-card">
        <p className="kicker">{t("newStudy.kicker")}</p>
        <h3>{t("newStudy.title")}</h3>
        <p>{t("newStudy.body")}</p>
        <label className="field-label" htmlFor="intent">{t("newStudy.researchQuestion")}</label>
        <textarea id="intent" value={draft.intent} onChange={(event) => setDraft({ ...draft, intent: event.target.value })} />
        <label className="field-label" htmlFor="study-purpose">{t("newStudy.decision")}</label>
        <textarea id="study-purpose" value={draft.studyPurpose} onChange={(event) => setDraft({ ...draft, studyPurpose: event.target.value })} />
        <label className="field-label" htmlFor="target-participant">{t("newStudy.targetParticipant")}</label>
        <input id="target-participant" value={draft.targetParticipant} onChange={(event) => setDraft({ ...draft, targetParticipant: event.target.value })} />
        <label className="field-label" htmlFor="artifact-notes">{t("newStudy.artifactContext")}</label>
        <textarea id="artifact-notes" value={draft.artifactNotes} onChange={(event) => setDraft({ ...draft, artifactNotes: event.target.value })} />
        <div className="two-fields">
          <select
            id="project-context"
            value={projectValue}
            onChange={(event) => setDraft({ ...draft, selectedProjectId: event.target.value })}
            aria-label={t("newStudy.projectContext")}
          >
            {model.projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>{project.name}</option>
            ))}
            <option value="__new__">{t("newStudy.createNewProject")}</option>
          </select>
          <input id="project-name" value={draft.projectName} onChange={(event) => setDraft({ ...draft, projectName: event.target.value })} aria-label={t("newStudy.newProjectName")} />
          <input id="study-title" value={draft.studyTitle} onChange={(event) => setDraft({ ...draft, studyTitle: event.target.value })} aria-label={t("newStudy.studyTitle")} />
        </div>
        <ActionNotice draft={draft} />
        <button id="create-study" onClick={createProjectAndStudy}>{t("action.continueGuidedSetup")}</button>
      </section>
      <aside className="copilot-panel plan-preview-card">
        <p className="kicker">{t("newStudy.copilotKicker")}</p>
        <h3>{t("newStudy.nextUsefulQuestion")}</h3>
        <p>{nextQuestion}</p>
        <ol className="guided-loop">
          {[t("copilot.ask"), t("copilot.clarify"), t("copilot.confirmPlan"), t("copilot.run")].map((step, index) => (
            <li key={step}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {step}
            </li>
          ))}
        </ol>
        <PlaybookQuickStarts model={model} draft={draft} setDraft={setDraft} />
        <SignalCard title={t("newStudy.setupSignalTitle")} items={[
          { note: `Question: ${draft.intent}` },
          { note: `Participant: ${draft.targetParticipant}` },
          { note: `Audience criteria: ${normalizeLines(draft.audienceCriteria).length || 0} selected` },
          { note: `Guide questions: ${normalizeLines(draft.guideQuestions).length || 0} drafted` },
          { note: `Artifact context: ${draft.artifactNotes}` }
        ]} />
        <p className="boundary">{t("newStudy.noRunBoundary")}</p>
      </aside>
    </div>
  );
}

function StudyHomeRoute({ selectedStudy, studyRuns, model, navigate }) {
  const { t } = useI18n();
  if (!selectedStudy) {
    return <EmptyState title={t("study.noStudySelected")} body={t("study.noStudyBody")} cta={t("action.startNewStudy")} onClick={() => navigate("/studio/studies/new")} />;
  }
  const action = nextActionForStudy(selectedStudy, t);
  return (
    <div className="route-grid">
      <article className="paper-card primary-card">
        <p className="kicker">{t("study.nextAction")}</p>
        <h3>{action.label}</h3>
        <p>{t("study.homeBody")}</p>
        <button onClick={() => navigate(action.path)}>{action.label}</button>
      </article>
      <article className="paper-card">
        <p className="kicker">{t("study.state")}</p>
        <h3>{formatStudyStatus(selectedStudy.status, t)}</h3>
        <MetricGrid items={[
          [t("metric.researchAttempts"), studyRuns.length],
          [t("metric.savedEvidenceViews"), model.evidenceViews.length],
          [t("metric.studyReports"), model.studyReports.length],
          [t("metric.decisionLogs"), model.decisionLogs.length]
        ]} />
      </article>
    </div>
  );
}

function StudySetupRoute({ selectedStudy, model, draft, setDraft, generatePersonaLibrary, proposePlan, confirmPlan, startResearchRun }) {
  const { locale, t } = useI18n();
  if (!selectedStudy) {
    return <EmptyState title={t("study.noStudySelected")} body={t("study.openBeforePlan")} />;
  }
  const draftPlan = selectedStudy.draft_plan || {};
  const storedProposal = selectedStudy.frontline?.latest_plan_proposal || (draftPlan?.plan_proposal_id ? draftPlan : null);
  const storedRevision = selectedStudy.frontline?.latest_plan_revision || (draftPlan?.plan_revision_id ? draftPlan : null);
  const proposal = draft.proposal || storedProposal || {};
  const revision = draft.revision || storedRevision || {};
  const hasProposal = Boolean(proposal?.plan_proposal_id || selectedStudy.frontline?.latest_plan_proposal_id);
  const hasApprovedPlan = Boolean(selectedStudy.current_plan_revision_id || revision?.plan_revision_id);
  const studyMode = proposal?.mode_inference?.mode || revision?.mode_inference?.mode || "";
  const targetAudience = proposal?.target_audience || revision?.target_audience || buildTargetAudiencePayload(draft);
  const audienceCriteria = Array.isArray(targetAudience?.inclusion_criteria) ? targetAudience.inclusion_criteria : [];
  const personaPanel = proposal?.persona_panel || revision?.persona_panel || buildPersonaPanelPayload(draft, model.personaLibrary);
  const selectedPersonaIds = Array.isArray(personaPanel?.selected_persona_ids) ? personaPanel.selected_persona_ids : [];
  const hasPersonaSelection = selectedPersonaIds.length > 0 || Boolean(personaPanel?.empty_selection_exception?.reason);
  const guide = proposal?.moderator_interview_guide || revision?.moderator_interview_guide || {};
  const guideQuestions = guide?.questions || normalizeLines(draft.guideQuestions);
  const expectedEvidence = proposal?.expected_evidence_types || revision?.expected_evidence_types || [];
  const artifacts = proposal?.artifact_refs || revision?.artifact_refs || selectedStudy.artifact_refs || [];
  return (
    <div className="setup-grid">
      <div className="setup-side">
        <ResearchCopilotPanel />
        <PlaybookQuickStarts model={model} draft={draft} setDraft={setDraft} />
        <PersonaLibraryPicker model={model} draft={draft} setDraft={setDraft} hasApprovedPlan={hasApprovedPlan} generatePersonaLibrary={generatePersonaLibrary} />
        <PlanTuningCard draft={draft} setDraft={setDraft} hasApprovedPlan={hasApprovedPlan} />
      </div>
      <section className="paper-card plan-confirmation-card" id="plan-confirmation">
        <p className="kicker">{t("plan.confirmKicker")}</p>
        <h3>{t("plan.confirmTitle")}</h3>
        <ActionNotice draft={draft} />
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.goal")}</span>
          <p id="plan-goal">{proposal?.study_purpose || revision?.study_purpose || selectedStudy.research_intent || t("plan.goalFallback")}</p>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.targetParticipant")}</span>
          <p id="plan-target">{targetAudience?.summary || proposal?.target_persona || revision?.target_persona || t("plan.targetFallback")}</p>
        </div>
        <div className="plan-section" id="plan-audience-criteria">
          <span className="ia-nav-label">{t("plan.audienceSelection")}</span>
          <SignalList
            items={[
              ...audienceCriteria.map((item) => ({ label: item, note: t("plan.includeInPanel") })),
              ...(targetAudience?.excluded_context ? [{ label: t("plan.outsideRun"), note: displayKnownDataCopy(targetAudience.excluded_context, locale) }] : [])
            ]}
            fallback={t("plan.audienceFallback")}
          />
        </div>
        <div className="plan-section" id="plan-persona-panel">
          <span className="ia-nav-label">{t("plan.participantPanel")}</span>
          <p>{t("plan.panelSummary", {
            panel: displayPersonaPanel(personaPanel?.panel_type || "mainstream", t),
            count: selectedPersonaIds.length || personaPanel?.sample_size || 0
          })}</p>
          {!hasPersonaSelection ? (
            <p className="field-hint">{t("plan.noPersonaHint")}</p>
          ) : null}
          <SignalList
            items={(personaPanel?.selected_personas || []).map((persona) => ({
              label: persona.name || persona.synthetic_user_id,
              note: [persona.occupation, persona.location, persona.workflow_maturity].filter(Boolean).map((value) => displayKnownDataCopy(value, locale)).join(" - ")
            }))}
            fallback={t("plan.personaFallback")}
          />
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.studyType")}</span>
          <strong id="plan-study-type">{formatStudyType(studyMode)}</strong>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.artifacts")}</span>
          <p>{artifacts.length ? artifacts.join("; ") : t("plan.artifactFallback")}</p>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.expectedEvidence")}</span>
          <div className="tag-list" id="plan-evidence">
            {(expectedEvidence.length ? expectedEvidence : ["objections", "trust gaps", "adoption barriers", "contradictions", "human-validation gaps"]).map((item) => (
              <span key={item}>{String(item).replaceAll("_", " ")}</span>
            ))}
          </div>
        </div>
        <div className="plan-section">
          <span className="ia-nav-label">{t("plan.interviewGuide")}</span>
          <ol className="guide-list" id="plan-guide-list">
            {(guideQuestions.length ? guideQuestions : [t("plan.guideFallback")]).map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ol>
        </div>
        <div className="plan-section" id="plan-guide-focus">
          <span className="ia-nav-label">{t("plan.guideFocus")}</span>
          <p>{guide?.focus || draft.guideFocus || t("plan.guideFocusFallback")}</p>
        </div>
        <div className="plan-section" id="plan-limitations">
          <span className="ia-nav-label">{t("plan.limitations")}</span>
          <p>{t("plan.limitationsBody")}</p>
        </div>
        <div className="button-row">
          <button id="propose-plan" type="button" onClick={proposePlan} disabled={!hasPersonaSelection}>{hasProposal ? t("action.updateDraftPlan") : t("action.draftResearchPlan")}</button>
          <button id="confirm-plan" type="button" onClick={confirmPlan} disabled={!hasProposal || hasApprovedPlan || !hasPersonaSelection}>{hasApprovedPlan ? t("action.planApproved") : t("action.approvePlan")}</button>
          <button id="start-research-run" type="button" onClick={startResearchRun} disabled={!hasApprovedPlan}>{t("action.startResearchRun")}</button>
        </div>
      </section>
    </div>
  );
}

function PersonaLibraryPicker({ model, draft, setDraft, hasApprovedPlan, generatePersonaLibrary }) {
  const { locale, t } = useI18n();
  const library = model.personaLibrary || {};
  const libraryPanelMatchesDraft = !library.active_panel_type || library.active_panel_type === draft.selectedPanelType;
  const rawPersonas = Array.isArray(library.personas) ? library.personas : [];
  const personas = libraryPanelMatchesDraft ? rawPersonas : [];
  const simulatedLenses = Array.isArray(library.simulated_lenses) ? library.simulated_lenses : [];
  const panelOptions = Array.isArray(library.panel_options) ? library.panel_options : [];
  const readiness = library.readiness || {};
  const readinessStatus = libraryPanelMatchesDraft ? String(readiness.status || "empty") : "loading";
  const requestedPanelLabel = displayPersonaPanel(draft.selectedPanelType || "mainstream", t);
  const readinessMessage = libraryPanelMatchesDraft
    ? displayPersonaReadinessMessage(readiness, t)
    : t("persona.loadingPanel", { panel: requestedPanelLabel });
  const canGenerate = libraryPanelMatchesDraft && readiness.can_generate !== false && typeof generatePersonaLibrary === "function";
  const selectedIds = draft.selectedPersonaIds || [];
  const selectedCount = selectedIds.length;
  const coverageGaps = libraryPanelMatchesDraft ? library.library_summary?.human_difference_axis_summary?.coverage_gaps || [] : [];
  const defaultSelection = library.default_selection || {};
  const displayedSelectionCount = selectedCount || (
    libraryPanelMatchesDraft && !draft.personaSelectionUserEdited
      ? defaultSelection.selected_persona_ids?.length || 0
      : 0
  );
  const participantGroup = library.persona_groups?.participants || {};
  const lensGroup = library.persona_groups?.simulated_lenses || {};
  const togglePersona = (personaId) => {
    if (hasApprovedPlan) return;
    const id = String(personaId || "");
    setDraft((current) => {
      const existing = new Set(current.selectedPersonaIds || []);
      if (existing.has(id)) {
        existing.delete(id);
      } else {
        existing.add(id);
      }
      return {
        ...current,
        selectedPersonaIds: Array.from(existing),
        personaSampleSize: Math.max(1, existing.size),
        personaSelectionUserEdited: true
      };
    });
  };
  return (
    <section className="paper-card persona-picker-card" id="persona-library-picker">
      <p className="kicker">{t("persona.kicker")}</p>
      <h3>{t("persona.title")}</h3>
      <p className="field-hint">{t("persona.hint")}</p>
      <div className={`persona-readiness-strip is-${readinessStatus}`} id="persona-library-readiness">
        <strong>{displayPersonaReadinessStatus(readinessStatus, t)}</strong>
        <span>{readinessMessage || t("persona.readinessFallback")}</span>
      </div>
      <div className="two-fields">
        <select
          disabled={hasApprovedPlan}
          id="persona-panel-type"
          value={draft.selectedPanelType}
          onChange={(event) => setDraft((current) => ({
            ...current,
            selectedPanelType: event.target.value,
            selectedPersonaIds: [],
            personaSelectionUserEdited: false
          }))}
          aria-label={t("persona.panelType")}
        >
          {panelOptions.length ? panelOptions.map((option) => (
            <option key={option.panel_type} value={option.panel_type}>
              {displayPersonaPanel(option.panel_type, t)} ({option.persona_count})
            </option>
          )) : <option value="mainstream">{t("persona.mainstream")}</option>}
        </select>
        <select
          disabled={hasApprovedPlan}
          id="persona-sample-size"
          value={String(draft.personaSampleSize || selectedCount || 1)}
          onChange={(event) => setDraft((current) => ({
            ...current,
            personaSampleSize: Number(event.target.value),
            selectedPersonaIds: [],
            personaSelectionUserEdited: false
          }))}
          aria-label={t("persona.sampleSize")}
        >
          {[1, 2, 3, 4, 5, 6].map((size) => <option key={size} value={size}>{size} {size > 1 ? t("persona.participants") : t("persona.participant")}</option>)}
        </select>
        <select
          disabled={hasApprovedPlan}
          id="persona-generation-count"
          value={String(draft.personaGenerationCount || 3)}
          onChange={(event) => setDraft((current) => ({
            ...current,
            personaGenerationCount: Number(event.target.value)
          }))}
          aria-label={t("persona.generationCount")}
        >
          {[1, 2, 3, 4, 5, 6].map((size) => <option key={size} value={size}>{t("persona.generate", { count: size })}</option>)}
        </select>
      </div>
      <div className="persona-picker-summary" id="selected-persona-count">
        <strong>{displayedSelectionCount}</strong>
        <span>{t("persona.selectedCount")}</span>
      </div>
      <div className="persona-group-strip" id="persona-library-groups">
        <span>{t("persona.v5Participants")}: <strong>{participantGroup.count ?? personas.length}</strong></span>
        <span>{t("persona.legacyExcluded")}: <strong>{participantGroup.legacy_excluded_count ?? readiness.legacy_participant_count ?? 0}</strong></span>
        <span>{t("persona.simulatedLenses")}: <strong>{lensGroup.count ?? simulatedLenses.length}</strong></span>
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
              <span className="persona-card-status">{displayPersonaReadinessStatus(persona.readiness_status || "ready", t)} | {persona.source_schema_version || "v5+"} | {displayPersonaSourceKind(persona.source_kind, t)}</span>
              <span>{displayKnownDataCopy(persona.occupation, locale) || t("persona.participantFallback")} - {displayKnownDataCopy(persona.location, locale) || t("persona.localContext")}</span>
              <small>{displayPersonaPanel(persona.panel_role, t)} | {displayKnownDataCopy(persona.workflow_maturity, locale) || t("persona.workflowContext")} | {t("persona.trustLabel")} {displayKnownDataCopy(persona.trust_threshold, locale) || t("persona.contextualTrust")}</small>
              <em>{displayKnownDataCopy(policy.adoption_style, locale) || t("persona.behaviorFallback")}</em>
            </button>
          );
        }) : (
          <div className="persona-empty-state">
            <strong>{readinessStatus === "failed" ? t("persona.generationAttention") : t("persona.noParticipants")}</strong>
            <p>{readiness.message || t("persona.generateStarterBody")}</p>
            {canGenerate && !hasApprovedPlan ? (
              <button id="generate-persona-library" type="button" onClick={generatePersonaLibrary}>
                {t("persona.generateStarter", { count: draft.personaGenerationCount || draft.personaSampleSize || 3 })}
              </button>
            ) : null}
          </div>
        )}
      </div>
      {personas.length && canGenerate && !hasApprovedPlan ? (
        <button className="secondary-action" id="generate-persona-library" type="button" onClick={generatePersonaLibrary}>
          {t("persona.addReserve", { count: draft.personaGenerationCount || draft.personaSampleSize || 3 })}
        </button>
      ) : null}
      {simulatedLenses.length ? (
        <div className="simulated-lens-panel" id="simulated-lens-panel">
          <strong>{t("persona.lensTitle")}</strong>
          <p>{t("persona.lensBody")}</p>
          <div className="simulated-lens-list">
            {simulatedLenses.map((persona) => (
              <span key={persona.synthetic_user_id}>
                {persona.name}
                <small>{String(persona.persona_kind || "simulated_lens").replaceAll("_", " ")}</small>
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <SignalCard
        title={t("persona.coverageGaps")}
        items={coverageGaps.slice(0, 4).map((gap) => ({
          label: displayKnownDataCopy(gap.axis, locale),
          note: displayKnownDataCopy(gap.gap_type, locale)
        }))}
      />
      <p className="boundary">{locale === "zh-Hant" ? t("persona.syntheticBoundary") : library.synthetic_boundary || t("persona.syntheticBoundary")}</p>
    </section>
  );
}

function PlanTuningCard({ draft, setDraft, hasApprovedPlan }) {
  const { t } = useI18n();
  const guideCount = normalizeLines(draft.guideQuestions).length;
  const criteriaCount = normalizeLines(draft.audienceCriteria).length;
  return (
    <section className="paper-card plan-tuning-card" id="plan-tuning">
      <p className="kicker">{t("plan.tuningKicker")}</p>
      <h3>{t("plan.tuningTitle")}</h3>
      <p className="field-hint">{t("plan.tuningHint")}</p>
      <label className="field-label" htmlFor="setup-target-participant">{t("plan.audienceToSimulate")}</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="setup-target-participant"
        value={draft.targetParticipant}
        onChange={(event) => setDraft({ ...draft, targetParticipant: event.target.value })}
      />
      <label className="field-label" htmlFor="audience-criteria">{t("plan.audienceCriteria")}</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="audience-criteria"
        value={draft.audienceCriteria}
        onChange={(event) => setDraft({ ...draft, audienceCriteria: event.target.value })}
      />
      <label className="field-label" htmlFor="audience-exclusions">{t("plan.keepOutsideRun")}</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="audience-exclusions"
        value={draft.audienceExclusions}
        onChange={(event) => setDraft({ ...draft, audienceExclusions: event.target.value })}
      />
      <label className="field-label" htmlFor="guide-questions">{t("plan.guideQuestions")}</label>
      <textarea
        className="guide-textarea"
        disabled={hasApprovedPlan}
        id="guide-questions"
        value={draft.guideQuestions}
        onChange={(event) => setDraft({ ...draft, guideQuestions: event.target.value })}
      />
      <label className="field-label" htmlFor="guide-focus">{t("plan.moderatorFocus")}</label>
      <textarea
        className="compact-textarea"
        disabled={hasApprovedPlan}
        id="guide-focus"
        value={draft.guideFocus}
        onChange={(event) => setDraft({ ...draft, guideFocus: event.target.value })}
      />
      <MetricGrid items={[
        [t("metric.audienceCriteria"), criteriaCount],
        [t("metric.guideQuestions"), guideCount],
        [t("plan.approvalState"), hasApprovedPlan ? t("plan.locked") : t("plan.editable")],
        [t("plan.boundary"), t("plan.visible")]
      ]} />
      <p className="boundary">{t("plan.tuningBoundary")}</p>
    </section>
  );
}

function ExecutionSourceBadge({ run, progress }) {
  const { t } = useI18n();
  const boundary = executionBoundaryFromRun(run, progress);
  return (
    <div className={`execution-source-badge is-${boundary.tone}`}>
      <span>{t("run.executionSource")}</span>
      <strong>{t(boundary.labelKey)}</strong>
    </div>
  );
}

function ExecutionSourceBoundaryCard({ run, progress }) {
  const { t } = useI18n();
  const boundary = executionBoundaryFromRun(run, progress);
  return (
    <aside className={`execution-source-card is-${boundary.tone}`} id="run-execution-source-boundary">
      <div>
        <p className="kicker">{t("run.executionSourceKicker")}</p>
        <h3>{t(boundary.labelKey)}</h3>
        <p>{cleanEvidenceCopy(boundary.boundaryMessage || t(boundary.messageKey))}</p>
      </div>
      <MetricGrid items={[
        [t("run.executionSource"), t(boundary.labelKey)],
        [t("run.evidenceMode"), boundary.evidenceMode ? cleanEvidenceCopy(boundary.evidenceMode).replaceAll("_", " ") : t("common.pending")],
        [t("run.executionSourceName"), boundary.sourceName || t("common.pending")]
      ]} />
    </aside>
  );
}

function RunsRoute({ selectedStudy, studyRuns, navigate, startResearchRun }) {
  const { t } = useI18n();
  if (!selectedStudy) {
    return <EmptyState title={t("run.noStudyTitle")} body={t("run.noStudyBody")} />;
  }
  const hasApprovedPlan = Boolean(selectedStudy.current_plan_revision_id);
  return (
    <section className="object-list" id="research-run-list">
      <ListHeader title={t("run.listTitle")} action={hasApprovedPlan ? t("action.startResearchRun") : t("action.continueSetup")} onAction={hasApprovedPlan ? startResearchRun : () => navigate(`/studio/studies/${selectedStudy.study_id}/setup`)} />
      {studyRuns.length ? studyRuns.map((run, index) => (
        <ObjectRow
          key={run.job_id || index}
          title={t("run.itemTitle", { count: index + 1 })}
          meta={`${formatRunStatus(run.status, t)} - ${t("run.metaBoundary")}`}
          cta={t("action.openAttempt")}
          onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/runs/${runIdentifier(run) || run.job_id}`)}
        >
          <ExecutionSourceBadge run={run} />
        </ObjectRow>
      )) : <EmptyState title={t("run.emptyTitle")} body={t("run.emptyBody")} cta={hasApprovedPlan ? t("action.startResearchRun") : t("action.continueSetup")} onClick={hasApprovedPlan ? startResearchRun : () => navigate(`/studio/studies/${selectedStudy.study_id}/setup`)} />}
    </section>
  );
}

function RunProgressPanel({ progress, selectedRun }) {
  const { t } = useI18n();
  const events = Array.isArray(progress?.events) ? progress.events.slice(0, 7) : [];
  return (
    <section className="paper-card run-monitor-card" id="run-live-monitor">
      <div className="split-header">
        <div>
          <p className="kicker">{t("run.monitorKicker")}</p>
          <h3>{progress?.phase ? cleanEvidenceCopy(progress.phase).replaceAll("_", " ") : formatRunStatus(selectedRun?.status, t)}</h3>
          <p>{progress?.observed_interview_contract?.upgrade_path || t("run.monitorBody")}</p>
        </div>
        <div className="status-card compact-status">
          <span>{t("run.progress")}</span>
          <strong>{progress?.progress_percent ?? 0}%</strong>
          <small>{progress?.observed_interview_contract?.streaming_supported ? t("run.liveStream") : t("run.pollingRefresh")}</small>
        </div>
      </div>
      <div className="timeline-strip">
        {events.length ? events.map((event) => (
          <div className={`timeline-step is-${event.status || "pending"}`} key={event.event_id || event.stage_name}>
            <strong>{cleanEvidenceCopy(event.phase || event.stage_name).replaceAll("_", " ")}</strong>
            <span>{cleanEvidenceCopy(event.summary || event.status || "")}</span>
          </div>
        )) : <p>{t("run.monitorPreparing")}</p>}
      </div>
      <p className="boundary">{progress?.synthetic_boundary || t("run.monitorBoundary")}</p>
    </section>
  );
}

function RunEventStreamPanel({ eventStream }) {
  const { t } = useI18n();
  const events = Array.isArray(eventStream?.events) ? eventStream.events.slice(0, 8) : [];
  const participant = eventStream?.participant_progress || {};
  const latestTurn = eventStream?.latest_safe_turn || {};
  const observedBridge = eventStream?.observed_interview_bridge || {};
  return (
    <section className="paper-card run-event-stream-card" id="run-event-stream-panel">
      <div className="split-header">
        <div>
          <p className="kicker">{t("run.eventsKicker")}</p>
          <h3>{eventStream?.phase ? cleanEvidenceCopy(eventStream.phase).replaceAll("_", " ") : t("run.eventsTitle")}</h3>
          <p>{t("run.eventsBody")}</p>
        </div>
        <div className="status-card compact-status">
          <span>{t("run.eventStream")}</span>
          <strong>{eventStream?.progress_percent ?? 0}%</strong>
          <small>{eventStream?.transport?.streaming_supported ? t("run.liveStream") : t("run.pollingRefresh")}</small>
        </div>
      </div>
      <div className="run-event-grid">
        <div>
          <span>{t("run.participants")}</span>
          <strong>{participant.completed_count ?? 0}/{participant.selected_count ?? 0}</strong>
        </div>
        <div>
          <span>{t("run.observedBridge")}</span>
          <strong>{observedBridge.status ? cleanEvidenceCopy(observedBridge.status).replaceAll("_", " ") : t("common.pending")}</strong>
        </div>
        <div>
          <span>{t("run.latestSafeTurn")}</span>
          <strong>{latestTurn.exchange_id || t("common.pending")}</strong>
        </div>
      </div>
      {latestTurn.text_preview ? (
        <blockquote className="safe-turn-preview">
          {cleanEvidenceCopy(latestTurn.text_preview)}
        </blockquote>
      ) : null}
      <div className="event-stream-list">
        {events.length ? events.map((event) => (
          <div className="event-pill" key={event.event_id}>
            <strong>{cleanEvidenceCopy(event.phase || event.event_type || "").replaceAll("_", " ")}</strong>
            <span>{cleanEvidenceCopy(event.summary || "")}</span>
          </div>
        )) : <p>{t("run.eventStreamPreparing")}</p>}
      </div>
      <p className="boundary">{cleanEvidenceCopy(eventStream?.synthetic_boundary || t("run.eventsBoundary"))}</p>
    </section>
  );
}

function RunTranscriptPanel({ transcript, selectedRun, progress }) {
  const { t } = useI18n();
  const exchanges = Array.isArray(transcript?.exchanges) ? transcript.exchanges.slice(0, 4) : [];
  const transcriptState = transcriptStateForRun(transcript, selectedRun, progress);
  const hasExchanges = exchanges.length > 0;
  return (
    <article className="paper-card transcript-card" id="run-transcript-panel">
      <p className="kicker">{t("run.transcriptKicker")}</p>
      <h3>{hasExchanges ? t("run.transcriptTitle", { count: transcriptState.exchangeCount }) : t(transcriptState.titleKey)}</h3>
      {transcriptState.bodyKey ? (
        <div className={`transcript-state-note is-${transcriptState.tone}`}>
          <strong>{t(transcriptState.titleKey)}</strong>
          <span>{t(transcriptState.bodyKey)}</span>
        </div>
      ) : null}
      {hasExchanges ? exchanges.map((exchange) => {
        const participantTurn = (exchange.turns || []).find((turn) => turn.speaker === "synthetic_participant") || {};
        return (
          <div className="evidence-mini-row transcript-row" key={exchange.exchange_id}>
            <strong>{exchange.exchange_id} | {exchange.synthetic_user_id}</strong>
            <span>{cleanEvidenceCopy(participantTurn.text || "")}</span>
            <small>{(exchange.source_refs || []).join(", ")}</small>
          </div>
        );
      }) : null}
      <p className="boundary">{transcript?.synthetic_boundary || t("run.transcriptBoundary")}</p>
    </article>
  );
}

function RunTracePanel({ trace }) {
  const { t } = useI18n();
  const participantTrace = Array.isArray(trace?.synthetic_participant_reasoning_trace) ? trace.synthetic_participant_reasoning_trace : [];
  const facilitatorTrace = Array.isArray(trace?.facilitator_trace) ? trace.facilitator_trace : [];
  const observedActionTrace = Array.isArray(trace?.observed_action_trace) ? trace.observed_action_trace : [];
  const auditTrace = Array.isArray(trace?.audit_trace) ? trace.audit_trace : [];
  const traceItems = [
    ...participantTrace.slice(0, 2).map((item) => ({ label: item.synthetic_user_id || item.trace_id, note: item.top_objection || item.try_trigger || item.evidence_boundary })),
    ...facilitatorTrace.slice(0, 2).map((item) => ({ label: item.trace_id, note: item.summary })),
    ...observedActionTrace.slice(0, 1).map((item) => ({ label: item.trace_id, note: item.evidence_boundary })),
    ...auditTrace.slice(0, 1).map((item) => ({ label: item.trace_id, note: item.summary }))
  ];
  return (
    <article className="paper-card trace-card" id="run-trace-panel">
      <p className="kicker">{t("run.traceKicker")}</p>
      <h3>{t("run.traceTitle")}</h3>
      <MetricGrid items={[
        [t("run.participantTrace"), participantTrace.length],
        [t("run.facilitatorTrace"), facilitatorTrace.length],
        [t("run.observedActionTrace"), observedActionTrace.length],
        [t("run.auditTrace"), auditTrace.length]
      ]} />
      <SignalList items={traceItems} fallback={t("run.tracePreparing")} />
      <p className="boundary">{trace?.synthetic_boundary || t("run.traceBoundary")}</p>
    </article>
  );
}

function RunDetailRoute({ selectedStudy, selectedRun, model, navigate, createRerunPlan }) {
  const { t } = useI18n();
  if (!selectedStudy || !selectedRun) {
    return <EmptyState title={t("run.notFoundTitle")} body={t("run.notFoundBody")} cta={t("action.viewAttempts")} onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/runs`)} />;
  }
  const query = model.evidenceQuery;
  const reliability = query?.evidence_reliability || {};
  const missingContext = Array.isArray(reliability.missing_context) ? reliability.missing_context : [];
  const progress = model.routeObjects.runProgress;
  const transcript = model.routeObjects.runTranscript;
  const trace = model.routeObjects.runTrace;
  const eventStream = model.routeObjects.runEventStream;
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{t("run.detailKicker")}</p>
          <h2>{formatRunStatus(selectedRun.status, t)}</h2>
          <p>{cleanEvidenceCopy(query?.boundary_warning || t("run.inspectBoundary"))}</p>
          <ExecutionSourceBoundaryCard run={selectedRun} progress={progress} />
        </div>
        <div className="button-row">
          <button onClick={() => createRerunPlan(selectedRun)}>{t("action.prepareRerun")}</button>
          <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>{t("action.reviewEvidence")}</button>
        </div>
      </section>
      <RunEventStreamPanel eventStream={eventStream} />
      <RunProgressPanel progress={progress} selectedRun={selectedRun} />
      <div className="route-grid">
        <RunTranscriptPanel transcript={transcript} selectedRun={selectedRun} progress={progress} />
        <RunTracePanel trace={trace} />
      </div>
      <div className="route-grid">
        <PlanBasisCard selectedStudy={selectedStudy} selectedRun={selectedRun} />
        <article className="paper-card" id="run-audit-notes">
          <p className="kicker">{t("run.auditNotes")}</p>
          <h3>{reliability.stability_label ? cleanEvidenceCopy(reliability.stability_label).replaceAll("_", " ") : t("run.reliabilityPending")}</h3>
          <MetricGrid items={[
            [t("run.sourceSlices"), query?.result_count || 0],
            [t("evidence.contradictions"), Array.isArray(reliability.contradicting_evidence) ? reliability.contradicting_evidence.length : 0],
            [t("run.humanGaps"), missingContext.length],
            [t("run.comparisonRuns"), query?.cross_run_comparison?.comparison_run_count || 0]
          ]} />
          <p className="boundary">{reliability.synthetic_boundary || t("run.syntheticBoundary")}</p>
        </article>
      </div>
      <EvidenceReviewBoard query={query} sourceRun={selectedRun} compact={false} />
    </div>
  );
}

function EvidenceRoute({ selectedStudy, model, draft, evidenceControls, setEvidenceControls, createEvidenceView, createStudyReport, navigate }) {
  const { t } = useI18n();
  if (!selectedStudy) {
    return <EmptyState title={t("run.noStudyTitle")} body={t("evidence.noStudyBody")} />;
  }
  const query = model.evidenceQuery;
  const canSave = Boolean(query?.query_status === "query_ready" && model.evidenceQueryJobId);
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{t("evidence.beforeSummaryKicker")}</p>
          <h2>{t("evidence.beforeSummaryTitle")}</h2>
          <p>{cleanEvidenceCopy(query?.boundary_warning || t("evidence.notReadyBoundary"))}</p>
        </div>
        <div className="button-row">
          <button id="save-evidence-view" onClick={createEvidenceView} disabled={!canSave}>{t("action.saveEvidenceView")}</button>
          <button id="create-report" onClick={createStudyReport}>{t("action.createStudyReport")}</button>
        </div>
      </section>
      <ActionNotice draft={draft} />
      <section className="paper-card evidence-filter-card" id="evidence-filters">
        <div>
          <p className="kicker">{t("evidence.filtersKicker")}</p>
          <h3>{displayEvidenceFamily(evidenceControls.activeFamily, t)}</h3>
          <p>{t("evidence.filtersBody")}</p>
        </div>
        <div className="filter-chip-row">
          {["all", "input", "trace", "analysis", "output"].map((family) => (
            <button
              className={evidenceControls.activeFamily === family ? "filter-chip is-active" : "filter-chip"}
              key={family}
              onClick={() => setEvidenceControls({ ...evidenceControls, activeFamily: family })}
              type="button"
            >
              {displayEvidenceFamily(family, t)}
              <span>{query?.facet_counts?.[family] ?? 0}</span>
            </button>
          ))}
        </div>
      </section>
      <EvidenceReviewBoard query={query} sourceRun={findRunByRouteIdentifier(model.jobs, model.evidenceQueryJobId)} />
      <div className="route-grid">
        <section className="object-list wide-list">
          <ListHeader title={t("evidence.savedViews")} action={t("action.saveCurrentView")} actionId="save-evidence-view-secondary" onAction={createEvidenceView} disabled={!canSave} />
          {model.evidenceViews.length ? model.evidenceViews.map((view) => (
            <ObjectRow
              key={view.evidence_view_id}
              title={view.title}
              meta={`${displayEvidenceFamily(view.active_family || "all", t)} - ${cleanEvidenceCopy(view.query_text || t("evidence.savedReviewState"))}`}
              cta={t("action.openView")}
              onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence-views/${view.evidence_view_id}`)}
            />
          )) : <EmptyState title={t("evidence.noSavedViewsTitle")} body={t("evidence.noSavedViewsBody")} cta={t("action.saveEvidenceView")} onClick={createEvidenceView} />}
        </section>
        <ComparisonPanel query={query} />
      </div>
    </div>
  );
}

function EvidenceViewRoute({ selectedStudy, model, routeContext, createStudyReport, navigate }) {
  const { t } = useI18n();
  const view = model.routeObjects.evidenceView || model.evidenceViews.find((item) => item.evidence_view_id === routeContext.evidence_view_id);
  if (!selectedStudy || !view) {
    return <EmptyState title={t("evidence.viewNotFoundTitle")} body={t("evidence.viewNotFoundBody")} cta={t("action.reviewEvidence")} onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)} />;
  }
  const query = model.evidenceQuery;
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{t("evidence.viewKicker")}</p>
          <h2>{view.title}</h2>
          <p>{view.note || t("evidence.viewFallbackNote")}</p>
        </div>
        <div className="button-row">
          <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>{t("action.openEvidenceWorkspace")}</button>
          <button onClick={createStudyReport}>{t("action.createStudyReport")}</button>
        </div>
      </section>
      <div className="route-grid">
        <article className="paper-card primary-card" id="saved-view-provenance">
          <p className="kicker">{t("evidence.provenanceKicker")}</p>
          <h3>{view.selected_signal_id ? cleanEvidenceCopy(view.selected_signal_id).replaceAll("_", " ") : t("evidence.sourceRetained")}</h3>
          <MetricGrid items={[
            [t("evidence.family"), displayEvidenceFamily(view.active_family || "all", t)],
            [t("evidence.sourceAttempt"), view.run_id ? t("common.linked") : t("common.pending")],
            [t("evidence.replayFocus"), view.has_replay_focus ? t("common.attached") : t("common.notSelected")],
            [t("evidence.comparison"), view.has_comparison_focus ? t("common.attached") : t("common.availableInWorkspace")]
          ]} />
          <p className="boundary">{t("evidence.viewBoundary")}</p>
        </article>
        <article className="paper-card">
          <p className="kicker">{t("evidence.reviewScope")}</p>
          <h3>{displayEvidenceFamily(view.active_family || "all", t)}</h3>
          <p>{cleanEvidenceCopy(view.query_text || t("evidence.savedStateFallback"))}</p>
          <SignalCard title={t("evidence.humanGaps")} items={[...(view.readiness_gate?.gate_reasons || []).map((item) => ({ label: cleanEvidenceCopy(item).replaceAll("_", " ") }))]} />
        </article>
      </div>
      <EvidenceReviewBoard query={query} sourceRun={findRunByRouteIdentifier(model.jobs, view.job_id || view.run_id)} compact />
    </div>
  );
}

function StudyReportRoute({ selectedStudy, model, routeContext, createDecisionLog, navigate }) {
  const { t } = useI18n();
  const report = model.routeObjects.studyReport || model.studyReports.find((item) => item.study_report_id === routeContext.study_report_id);
  if (!selectedStudy || !report) {
    return <EmptyState title={t("report.notFoundTitle")} body={t("report.notFoundBody")} cta={t("action.reviewEvidence")} onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)} />;
  }
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{formatReportStatus(report.status, t)}</p>
          <h2>{report.title}</h2>
          <p>{report.synthetic_boundary}</p>
        </div>
        <div className="button-row">
          <button onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>{t("action.reviewSourceEvidence")}</button>
          <button id="create-decision" onClick={createDecisionLog}>{t("action.createDecisionFromReport")}</button>
        </div>
      </section>
      <section className="paper-card" id="report-cited-evidence">
        <p className="kicker">{t("report.citedEvidence")}</p>
        <h3>{t("report.citedTitle")}</h3>
        <MetricGrid items={[
          [t("report.includedAttempts"), report.included_run_ids?.length || 0],
          [t("report.planRevisions"), report.included_plan_revision_ids?.length || 0],
          [t("report.evidenceSlices"), report.metadata?.evidence_slice_count || 0],
          [t("report.decisionReady"), report.capabilities?.decision_workflow_ready ? t("common.yes") : t("common.review")]
        ]} />
      </section>
      <section className="report-grid">
        <SignalCard title={t("report.stablePatterns")} items={report.stable_patterns} />
        <SignalCard title={t("report.divergentSignals")} items={report.divergent_signals} />
        <SignalCard title={t("report.objections")} items={report.key_objections} />
        <SignalCard title={t("report.trustGaps")} items={report.trust_gaps} />
        <SignalCard title={t("report.adoptionBarriers")} items={report.adoption_barriers} />
        <SignalCard title={t("report.contradictions")} items={report.contradictions} cardId="report-contradictions" />
        <SignalCard title={t("report.humanGaps")} items={report.human_validation_gaps} cardId="report-human-gaps" />
      </section>
    </div>
  );
}

function PlanBasisCard({ selectedStudy, selectedRun }) {
  const { t } = useI18n();
  const revisionId = selectedRun?.metadata?.frontline_plan_revision_id || selectedRun?.metadata?.plan_revision_id || selectedStudy?.current_plan_revision_id || "";
  const revision = selectedStudy?.frontline?.latest_plan_revision || selectedStudy?.frontline?.latest_plan_proposal || {};
  return (
    <article className="paper-card primary-card" id="plan-basis">
      <p className="kicker">{t("run.planBasis")}</p>
      <h3>{revisionId ? t("run.approvedPlanAttached") : t("run.planContextPending")}</h3>
      <p>{revision.study_purpose || selectedStudy?.desired_output || selectedStudy?.research_intent || t("run.studyQuestionFallback")}</p>
      <MetricGrid items={[
        [t("run.studyType"), formatStudyType(revision?.mode_inference?.mode)],
        [t("run.target"), revision.target_persona || t("run.targetFallback")],
        [t("run.evidenceBoundary"), t("plan.visible")],
        [t("run.attemptStatus"), formatRunStatus(selectedRun?.status, t)]
      ]} />
    </article>
  );
}

function EvidenceReviewBoard({ query, sourceRun, compact = false }) {
  const { t } = useI18n();
  if (!query) {
    return (
      <section className="evidence-board">
        <EmptyState title={t("evidence.preparingTitle")} body={t("evidence.preparingBody")} />
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
        <p className="kicker">{t("evidence.sourceKicker")}</p>
        <h3>{selected ? externalizeEvidenceTitle(selected) : t("evidence.noSourceSelected")}</h3>
        <p>{cleanEvidenceCopy(selected?.summary || query.boundary_warning || t("evidence.pending"))}</p>
        {evidenceDetailLines(selected).length ? (
          <ul className="evidence-lines">
            {evidenceDetailLines(selected).slice(0, 4).map((line) => <li key={line}>{line}</li>)}
          </ul>
        ) : null}
        <MetricGrid items={[
          [t("evidence.visibleSlices"), query.result_count || visibleResults.length || 0],
          [t("evidence.family"), displayEvidenceFamily(query.active_family || selected?.family || "all", t)],
          [t("evidence.replaySteps"), replay.length],
          [t("evidence.sourceAttempt"), sourceRun ? formatRunStatus(sourceRun.status, t) : t("common.linked")]
        ]} />
      </article>
      <article className="paper-card" id="interpretation-panel">
        <p className="kicker">{t("evidence.interpretation")}</p>
        <h3>{reliability.selected_signal_id ? cleanEvidenceCopy(reliability.selected_signal_id).replaceAll("_", " ") : t("evidence.signalReview")}</h3>
        <p>{query.replay_context?.note || t("evidence.interpretationFallback")}</p>
        <SignalCard title={t("evidence.supportingEvidence")} items={supporting} />
      </article>
      <article className="paper-card" id="summary-panel">
        <p className="kicker">{t("evidence.summaryBoundary")}</p>
        <h3>{cleanEvidenceCopy(reliability.stability_label || t("evidence.directionalSignal")).replaceAll("_", " ")}</h3>
        <p>{reliability.synthetic_boundary || t("evidence.syntheticProofBoundary")}</p>
        <MetricGrid items={[
          [t("evidence.stabilityScore"), reliability.stability_score ?? 0],
          [t("evidence.supportingSlices"), supporting.length],
          [t("evidence.contradictions"), contradictions.length],
          [t("evidence.missingContext"), missingContext.length]
        ]} />
      </article>
      <article className="paper-card risk-card" id="contradiction-panel">
        <p className="kicker">{t("evidence.contradictions")}</p>
        <h3>{contradictions.length ? t("evidence.openContradictions", { count: contradictions.length }) : t("evidence.noStrongContradiction")}</h3>
        <SignalList items={contradictions} fallback={t("evidence.contradictionFallback")} />
      </article>
      <article className="paper-card risk-card" id="human-validation-gaps">
        <p className="kicker">{t("evidence.humanGaps")}</p>
        <h3>{missingContext.length ? t("evidence.openGaps", { count: missingContext.length }) : t("evidence.noGapRecord")}</h3>
        <SignalList items={missingContext} fallback={t("evidence.humanGapFallback")} />
      </article>
      <article className="paper-card evidence-result-list">
        <p className="kicker">{t("evidence.slices")}</p>
        <h3>{visibleResults.length ? t("evidence.visibleSlicesTitle", { count: visibleResults.length }) : t("evidence.noVisibleSlicesTitle")}</h3>
        {visibleResults.length ? visibleResults.map((item) => (
          <div className="evidence-mini-row" key={item.id}>
            <strong>{externalizeEvidenceTitle(item)}</strong>
            <span>{displayEvidenceFamily(item.family, t)} - {cleanEvidenceCopy(item.summary)}</span>
          </div>
        )) : <p>{t("evidence.noSourceAvailable")}</p>}
      </article>
    </section>
  );
}

function ComparisonPanel({ query }) {
  const { t } = useI18n();
  const comparison = query?.cross_run_comparison || {};
  const candidates = Array.isArray(comparison.candidate_runs) ? comparison.candidate_runs : [];
  const localComparison = query?.comparison_context || {};
  return (
    <aside className="paper-card" id="comparison-panel">
      <p className="kicker">{t("compare.kicker")}</p>
      <h3>{t("compare.title")}</h3>
      <p>{comparison.note || localComparison.note || t("compare.body")}</p>
      <MetricGrid items={[
        [t("compare.comparableAttempts"), comparison.comparison_run_count || 0],
        [t("compare.nearbySlices"), Array.isArray(localComparison.comparison_candidates) ? localComparison.comparison_candidates.length : 0],
        [t("compare.selectedComparison"), comparison.selected_comparison_run_id ? t("common.attached") : t("common.notSelected")],
        [t("compare.humanBoundary"), t("plan.visible")]
      ]} />
      <SignalList items={candidates.slice(0, 3)} fallback={t("compare.fallback")} />
    </aside>
  );
}

function SignalList({ items = [], fallback }) {
  const { t } = useI18n();
  const visibleItems = Array.isArray(items) ? items.slice(0, 4) : [];
  if (!visibleItems.length) {
    return <p>{fallback}</p>;
  }
  return (
    <ul className="signal-list">
      {visibleItems.map((item, index) => (
        <li key={item.id || item.result_id || item.signal_id || item.gap_id || item.run_id || index}>
          <strong>{cleanEvidenceCopy(item.label || item.title || item.top_result_title || item.run_id || t("signals.reviewItem"))}</strong>
          <span>{cleanEvidenceCopy(item.note || item.summary || item.relation || item.relation_note || "")}</span>
        </li>
      ))}
    </ul>
  );
}

function DecisionRoute({ selectedStudy, model, routeContext, draft, setDraft, createDecisionLog, createShareBundle, navigate }) {
  const { t } = useI18n();
  const decision = model.routeObjects.decisionLog || model.decisionLogs.find((item) => item.decision_log_id === routeContext.decision_log_id);
  if (!selectedStudy || !decision) {
    return (
      <div className="route-grid">
        <EmptyState title={t("decision.notFoundTitle")} body={t("decision.notFoundBody")} />
        <DecisionEditor draft={draft} setDraft={setDraft} createDecisionLog={createDecisionLog} />
      </div>
    );
  }
  const comments = Array.isArray(model.routeObjects.decisionComments) ? model.routeObjects.decisionComments : [];
  const confidenceBoundary = boundarySentence(
    decision.metadata?.confidence_boundary,
    t("evidence.syntheticProofBoundary")
  );
  const humanFollowUp = cleanEvidenceCopy(
    decision.metadata?.human_follow_up
    || t("decision.followUpFallback")
  );
  const evidenceBasis = cleanEvidenceCopy(
    decision.metadata?.evidence_basis_label
    || (decision.evidence_view_id ? t("evidence.viewFallbackNote") : t("run.metaBoundary"))
  );
  return (
    <div className="route-grid">
      <article className="paper-card primary-card" id="decision-current-belief">
        <p className="kicker">{t("decision.kicker")}</p>
        <h3>{t("decision.currentBelief")}</h3>
        <p>{decision.decision_summary}</p>
        <p className="boundary">{t("decision.currentBoundary")}</p>
        <div className="button-row">
          <button id="review-source-evidence" onClick={() => navigate(`/studio/studies/${selectedStudy.study_id}/evidence`)}>{t("action.reviewEvidence")}</button>
          <button id="create-share" onClick={createShareBundle}>{t("action.createShareView")}</button>
        </div>
      </article>
      <article className="paper-card" id="decision-evidence-basis">
        <p className="kicker">{t("decision.evidenceBasis")}</p>
        <h3>{evidenceBasis}</h3>
        <MetricGrid items={[
          [t("decision.reviewStatus"), humanizeStatus(decision.review_status, t("common.draft"))],
          [t("decision.evidenceView"), decision.evidence_view_id ? t("common.attached") : t("common.notAttached")],
          [t("decision.selectedSource"), decision.selected_signal_id ? t("common.attached") : decision.selected_result_id ? t("common.attached") : t("common.reviewNeeded")],
          [t("decision.comparison"), decision.has_comparison_focus ? t("common.attached") : t("common.notAttached")]
        ]} />
      </article>
      <article className="paper-card risk-card" id="decision-confidence-boundary">
        <p className="kicker">{t("decision.confidenceBoundary")}</p>
        <h3>{t("decision.keepProofLine")}</h3>
        <p>{confidenceBoundary}</p>
        <MetricGrid items={[
          [t("decision.readiness"), humanizeStatus(decision.readiness_gate?.status, t("common.humanValidationRequired"))],
          [t("decision.marketProof"), t("common.notClaimed")],
          [t("decision.reviewThreads"), decision.review_thread_count || 0],
          [t("decision.comments"), decision.comment_count || comments.length || 0]
        ]} />
      </article>
      <article className="paper-card risk-card" id="decision-human-follow-up">
        <p className="kicker">{t("decision.humanFollowUp")}</p>
        <h3>{t("decision.needsValidation")}</h3>
        <p>{humanFollowUp}</p>
        <SignalList
          items={decision.readiness_gate?.human_validation_gaps || decision.recurring_signal_focus?.patterns || []}
          fallback={t("decision.followUpFallback")}
        />
      </article>
    </div>
  );
}

function ShareCollectionRoute({ model, navigate }) {
  const { t } = useI18n();
  return (
    <section className="object-list">
      <ListHeader title={t("share.collectionTitle")} action={t("action.openWorkspace")} onAction={() => navigate("/studio")} />
      {model.shareBundles.length ? model.shareBundles.map((bundle) => (
        <ObjectRow
          key={bundle.share_bundle_id}
          title={bundle.title}
          meta={`${humanizeStatus(bundle.status, t("share.collectionTitle"))} - ${t("share.metaBoundary")}`}
          cta={t("action.openShare")}
          onClick={() => navigate(`/studio/share/${bundle.share_bundle_id}`)}
        />
      )) : <EmptyState title={t("share.noViewsTitle")} body={t("share.noViewsBody")} cta={t("action.returnWorkspace")} onClick={() => navigate("/studio")} />}
    </section>
  );
}

function ShareRoute({ selectedStudy, model, routeContext, navigate }) {
  const { t } = useI18n();
  const share = model.routeObjects.shareBundle || model.shareBundles.find((item) => item.share_bundle_id === routeContext.share_bundle_id);
  if (!share) {
    return <EmptyState title={t("share.notFoundTitle")} body={t("share.notFoundBody")} cta={t("action.viewShareArea")} onClick={() => navigate("/studio/share")} />;
  }
  const linkedDecisionId = share.metadata?.decision_log_id || "";
  const linkedDecision = model.decisionLogs.find((decision) => decision.decision_log_id === linkedDecisionId) || model.decisionLogs[0] || null;
  const files = Array.isArray(share.files) ? share.files : [];
  const shareUrl = share.public_path ? `${window.location.origin}${share.public_path}` : "";
  const shareBoundary = boundarySentence(
    share.synthetic_boundary,
    t("share.boundaryFallback")
  );
  return (
    <div className="route-stack">
      <section className="hero-panel compact-hero">
        <div>
          <p className="kicker">{t("share.viewKicker")}</p>
          <h2>{share.title}</h2>
          <p>{shareBoundary}</p>
        </div>
        <div className="button-row">
          <button
            id="copy-share-link"
            onClick={() => shareUrl && navigator.clipboard?.writeText(shareUrl)}
            disabled={!shareUrl}
          >
            {t("action.copyBoundaryLink")}
          </button>
          <button onClick={() => selectedStudy && navigate(`/studio/studies/${selectedStudy.study_id}/decisions/${linkedDecision?.decision_log_id || ""}`)} disabled={!selectedStudy || !linkedDecision}>
            {t("action.openDecision")}
          </button>
        </div>
      </section>
      <section className="share-grid">
        <article className="paper-card primary-card" id="share-decision">
          <p className="kicker">{t("share.decisionIncluded")}</p>
          <h3>{linkedDecision?.title || t("share.decisionPending")}</h3>
          <p>{linkedDecision?.decision_summary || t("share.decisionPendingBody")}</p>
          <p className="boundary">{boundarySentence(linkedDecision?.metadata?.confidence_boundary, t("share.decisionBoundary"))}</p>
        </article>
        <article className="paper-card" id="share-evidence-digest">
          <p className="kicker">{t("share.evidenceDigest")}</p>
          <h3>{t("share.relyTitle")}</h3>
          <MetricGrid items={[
            [t("share.status"), humanizeStatus(share.status, t("common.published"))],
            [t("share.readiness"), humanizeStatus(share.readiness_gate?.status, t("common.humanValidationRequired"))],
            [t("share.marketClaims"), share.market_claims_allowed ? t("common.scopedOnly") : t("common.notAllowed")],
            [t("share.circulation"), humanizeStatus(share.mvp_launch_scope?.status, t("common.internalOnly"))]
          ]} />
        </article>
        <PrivacyExportControlsCard controls={model.privacyExportControls} compact />
        <article className="paper-card" id="share-included-artifacts">
          <p className="kicker">{t("share.includedArtifacts")}</p>
          <h3>{t("share.viewerSafeItems", { count: share.share_file_count || files.length || 0 })}</h3>
          {files.length ? (
            <div className="artifact-list">
              {files.slice(0, 4).map((file) => (
                <div className="artifact-row" key={file.relative_path || file.file_name || file.artifact_id}>
                  <strong>{cleanEvidenceCopy(file.file_name || file.artifact_id || t("share.sharedArtifact"))}</strong>
                  <span>{humanizeStatus(file.export_kind, t("share.evidenceArtifact"))}</span>
                </div>
              ))}
            </div>
          ) : (
            <p>{t("share.hiddenFilesBody")}</p>
          )}
        </article>
        <article className="paper-card risk-card" id="share-boundary">
          <p className="kicker">{t("share.boundary")}</p>
          <h3>{t("share.syntheticOnlySignal")}</h3>
          <p>{shareBoundary}</p>
          <MetricGrid items={[
            [t("share.publicLink"), share.public_path ? t("common.available") : t("common.unavailable")],
            [t("share.expires"), share.expires_at ? t("common.scheduled") : t("common.noExpirySet")],
            [t("share.humanValidation"), t("common.stillRequired")],
            [t("share.replacementClaim"), t("common.notAllowed")]
          ]} />
          {shareUrl ? <p id="share-public-link" className="boundary">{shareUrl}</p> : null}
        </article>
      </section>
    </div>
  );
}

function ResearchCopilotPanel() {
  const { t } = useI18n();
  const steps = [
    t("copilot.ask"),
    t("copilot.clarify"),
    t("copilot.confirmPlan"),
    t("copilot.run"),
    t("copilot.reviewEvidence"),
    t("copilot.compare"),
    t("copilot.decide")
  ];
  return (
    <aside className="copilot-panel" aria-label={t("copilot.label")}>
      <div>
        <p className="kicker">{t("copilot.kicker")}</p>
        <h3>{t("copilot.title")}</h3>
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
  const { t } = useI18n();
  return (
    <article className="paper-card">
      <p className="kicker">{t("decision.recordKicker")}</p>
      <h3>{t("decision.editorTitle")}</h3>
      <label className="field-label" htmlFor="decision-summary">{t("decision.currentBelief")}</label>
      <textarea id="decision-summary" value={draft.decisionSummary} onChange={(event) => setDraft({ ...draft, decisionSummary: event.target.value })} />
      <label className="field-label" htmlFor="decision-rationale">{t("decision.rationale")}</label>
      <textarea id="decision-rationale" value={draft.decisionRationale} onChange={(event) => setDraft({ ...draft, decisionRationale: event.target.value })} />
      <label className="field-label" htmlFor="decision-confidence">{t("decision.confidenceBoundary")}</label>
      <textarea id="decision-confidence" value={draft.confidenceBoundary} onChange={(event) => setDraft({ ...draft, confidenceBoundary: event.target.value })} />
      <label className="field-label" htmlFor="decision-follow-up">{t("decision.humanFollowUp")}</label>
      <textarea id="decision-follow-up" value={draft.humanFollowUp} onChange={(event) => setDraft({ ...draft, humanFollowUp: event.target.value })} />
      <button onClick={createDecisionLog}>{t("action.saveDecision")}</button>
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
  const { t } = useI18n();
  return (
    <p className={compact ? "boundary compact-boundary" : "boundary"}>
      {t("boundary.syntheticSignal")}
    </p>
  );
}

function LoadingState() {
  const { t } = useI18n();
  return (
    <section className="paper-card loading-card">
      <p className="kicker">{t("loading.kicker")}</p>
      <h3>{t("loading.title")}</h3>
      <p>{t("loading.body")}</p>
    </section>
  );
}

function EmptyState({ title, body, cta, onClick }) {
  const { t } = useI18n();
  return (
    <article className="paper-card empty-state">
      <p className="kicker">{t("empty.kicker")}</p>
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

function ObjectRow({ title, meta, cta, onClick, children = null }) {
  return (
    <article className="object-row">
      <div>
        <h4>{title}</h4>
        <p>{meta}</p>
        {children}
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
  const { t } = useI18n();
  const visibleItems = Array.isArray(items) ? items.slice(0, 3) : [];
  return (
    <article className="paper-card" id={cardId || undefined}>
      <p className="kicker">{title}</p>
      <h3>{visibleItems.length ? `${visibleItems.length} ${t("signals.items")}` : t("signals.noItems")}</h3>
      {visibleItems.length ? visibleItems.map((item, index) => (
        <p key={item.pattern_id || item.signal_id || item.gap_id || item.result_id || index}>{cleanEvidenceCopy(item.label || item.title || item.note || t("signals.reviewItem"))}</p>
      )) : <p>{t("signals.noStronger")}</p>}
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
