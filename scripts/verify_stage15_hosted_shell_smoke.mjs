import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "output", "playwright", "stage15_hosted_shell_smoke");
const apiBaseUrl = process.env.STAGE15_API_BASE_URL || "http://127.0.0.1:8011";
const apiToken = process.env.STAGE15_API_TOKEN || "token-api";
const validationProviderName = process.env.STAGE15_PROVIDER_NAME || "mock";
const validationSampleSize = process.env.STAGE15_SAMPLE_SIZE || "5";
const expectedJobStatuses = (process.env.STAGE15_EXPECTED_JOB_STATUS || "completed")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const providerAcceptanceOnly = process.env.STAGE15_PROVIDER_ACCEPTANCE_ONLY
  ? process.env.STAGE15_PROVIDER_ACCEPTANCE_ONLY === "1"
  : validationProviderName !== "mock";
const jobStatusTimeoutMs = Number.parseInt(
  process.env.STAGE15_JOB_STATUS_TIMEOUT_MS || (validationProviderName === "mock" ? "120000" : "900000"),
  10
);
const hostedUrl = `${apiBaseUrl}/app/workspace?token=${encodeURIComponent(apiToken)}`;
const runLabel = new Date().toISOString().replace(/[:.]/g, "-");
const artifactDir = path.join(outputDir, runLabel);
const personalMvpWorkflowId = process.env.STAGE15_PERSONAL_MVP_WORKFLOW || "";

const DEFAULT_SMOKE_WORKFLOW = {
  id: "generic_hosted_shell_smoke",
  projectNamePrefix: "Hosted Shell Smoke",
  studyTitlePrefix: "Milestone 11 study",
  modeOverride: "concept_validation",
  attachArtifacts: false,
  useFallback: true,
  firstTask: "review onboarding guidance",
  researchIntent: "Validate whether the onboarding shell explains reversibility clearly enough for first-time workspace setup.",
  desiredOutcome: "Need a concise evidence-backed readout with key hesitation points and trust gaps.",
  evidenceViewTitlePrefix: "Smoke evidence view",
  evidenceViewNote: "Generic hosted shell smoke evidence view.",
  decisionTitlePrefix: "Smoke decision",
  decisionSummary: "Generic smoke conclusion remains bounded to synthetic evidence.",
  decisionRationale: "Recorded to verify the study-first shell can preserve selected evidence into a decision log."
};

const PERSONAL_MVP_WORKFLOWS = {
  founder_concept_validation: {
    id: "founder_concept_validation",
    projectNamePrefix: "MVP Founder Concept",
    studyTitlePrefix: "Founder concept validation",
    modeOverride: "concept_validation",
    attachArtifacts: false,
    useFallback: true,
    firstTask: "explain the startup idea and ask whether the concept feels credible enough to try",
    researchIntent: "I have a startup idea for a lightweight research workspace that helps founders test concepts with synthetic users before scheduling human interviews. Validate whether first-time founders understand the concept, where trust breaks, what objections appear, and what adoption conditions would make them try it.",
    desiredOutcome: "Evidence-backed readout covering concept understanding, appeal, objections, trust gaps, adoption barriers, and what must be validated with real humans next.",
    evidenceViewTitlePrefix: "Founder concept evidence",
    evidenceViewNote: "Personal MVP acceptance view for startup idea concept validation.",
    decisionTitlePrefix: "Founder concept decision",
    decisionSummary: "Record whether the startup concept is directionally worth pursuing, while keeping synthetic evidence boundaries visible.",
    decisionRationale: "Decision should cite understanding, objection, trust-gap, and adoption-barrier evidence from the completed live run."
  },
  ui_prototype_comprehension_validation: {
    id: "ui_prototype_comprehension_validation",
    projectNamePrefix: "MVP Prototype Comprehension",
    studyTitlePrefix: "UI prototype comprehension validation",
    modeOverride: "prototype_validation",
    attachArtifacts: true,
    useFallback: false,
    firstTask: "review the uploaded prototype screens and describe what the main button and next action mean",
    researchIntent: "I have a UI/UX prototype and need to understand whether realistic users can interpret the page copy, primary button, secondary actions, and task flow without confusion. Focus on wording ambiguity, CTA/button meaning, layout friction, and likely hesitation points.",
    desiredOutcome: "Evidence-backed prototype comprehension review covering misunderstood text, button or CTA ambiguity, flow friction, trust gaps, and what requires real human usability validation.",
    evidenceViewTitlePrefix: "Prototype comprehension evidence",
    evidenceViewNote: "Personal MVP acceptance view for UI/prototype comprehension validation with an attached prototype artifact.",
    decisionTitlePrefix: "Prototype comprehension decision",
    decisionSummary: "Record whether the prototype is clear enough for the next iteration, preserving synthetic-only limits.",
    decisionRationale: "Decision should cite wording, CTA, flow-friction, and artifact-grounded evidence from the completed run."
  },
  pain_empathy_insight_discovery: {
    id: "pain_empathy_insight_discovery",
    projectNamePrefix: "MVP Pain Discovery",
    studyTitlePrefix: "Pain empathy insight discovery",
    modeOverride: "auto",
    attachArtifacts: false,
    useFallback: true,
    firstTask: "describe the last time the user tried to validate a product idea and where the workflow broke down",
    researchIntent: "I want to research the pain around early product discovery before deciding on a solution. Explore empathy, recurring pain, root causes, current workaround behavior, decision triggers, workflow fragmentation, and insight opportunities for later solution planning.",
    desiredOutcome: "Evidence-backed discovery readout covering pain reality, root cause, workaround behavior, workflow gaps, empathy signals, and next questions for real human validation.",
    evidenceViewTitlePrefix: "Pain discovery evidence",
    evidenceViewNote: "Personal MVP acceptance view for pain, empathy, root-cause, workflow, and insight discovery.",
    decisionTitlePrefix: "Pain discovery decision",
    decisionSummary: "Record the strongest pain and insight hypotheses to carry into solution planning, without treating synthetic signal as proof.",
    decisionRationale: "Decision should cite pain, root-cause, workaround, workflow-fragmentation, and human-validation-gap evidence from the completed run.",
    knownLimitation: ""
  }
};

const activeWorkflow = personalMvpWorkflowId ? PERSONAL_MVP_WORKFLOWS[personalMvpWorkflowId] : null;

function log(message) {
  process.stdout.write(`${message}\n`);
}

function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function ensureDir(targetPath) {
  await fs.mkdir(targetPath, { recursive: true });
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function listChildren(parentPath) {
  try {
    return await fs.readdir(parentPath, { withFileTypes: true });
  } catch {
    return [];
  }
}

async function resolvePlaywrightImportUrl() {
  const explicitNodeModules = process.env.PLAYWRIGHT_NODE_MODULE_DIR || "";
  const candidateNodeModules = [];

  if (explicitNodeModules) {
    candidateNodeModules.push(explicitNodeModules);
  }

  candidateNodeModules.push(
    path.join(repoRoot, "frontend", "workspace_shell_app", "node_modules"),
    path.join(repoRoot, "node_modules")
  );

  const codexRuntimeRoot = path.join(os.homedir(), "AppData", "Local", "OpenAI", "Codex", "runtimes", "cua_node");
  for (const entry of await listChildren(codexRuntimeRoot)) {
    if (entry.isDirectory()) {
      candidateNodeModules.push(path.join(codexRuntimeRoot, entry.name, "bin", "node_modules"));
    }
  }

  const npxCacheRoot = path.join(os.homedir(), "AppData", "Local", "npm-cache", "_npx");
  for (const entry of await listChildren(npxCacheRoot)) {
    if (entry.isDirectory()) {
      candidateNodeModules.push(path.join(npxCacheRoot, entry.name, "node_modules"));
    }
  }

  for (const nodeModulesPath of candidateNodeModules) {
    const packagePath = path.join(nodeModulesPath, "playwright", "package.json");
    const entryPath = path.join(nodeModulesPath, "playwright", "index.mjs");
    if (await pathExists(packagePath) && await pathExists(entryPath)) {
      return pathToFileURL(entryPath).href;
    }
  }

  throw new Error(
    "Unable to locate a Playwright package. Set PLAYWRIGHT_NODE_MODULE_DIR or install playwright locally."
  );
}

async function resolveChromiumExecutablePath() {
  if (process.env.PLAYWRIGHT_EXECUTABLE_PATH) {
    return process.env.PLAYWRIGHT_EXECUTABLE_PATH;
  }

  const playwrightRoot = path.join(os.homedir(), "AppData", "Local", "ms-playwright");
  const chromiumDirs = (await listChildren(playwrightRoot))
    .filter((entry) => entry.isDirectory() && entry.name.startsWith("chromium-"))
    .sort((left, right) => right.name.localeCompare(left.name, undefined, { numeric: true }));

  for (const entry of chromiumDirs) {
    const basePath = path.join(playwrightRoot, entry.name);
    const candidates = [
      path.join(basePath, "chrome-win64", "chrome.exe"),
      path.join(basePath, "chrome-win", "chrome.exe"),
      path.join(basePath, "chrome-linux", "chrome"),
      path.join(basePath, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium")
    ];
    for (const candidatePath of candidates) {
      if (await pathExists(candidatePath)) {
        return candidatePath;
      }
    }
  }

  throw new Error(
    "Unable to locate a Chromium executable. Set PLAYWRIGHT_EXECUTABLE_PATH or install Playwright browsers."
  );
}

async function runDemoBootstrap() {
  if (process.env.STAGE15_SKIP_START_DEMO === "1") {
    log("Skipping demo bootstrap because STAGE15_SKIP_START_DEMO=1.");
    return { skipped: true, output: "" };
  }

  log("Bootstrapping local Stage 15 demo runtime...");
  return await new Promise((resolve, reject) => {
    const child = spawn("cmd.exe", ["/c", "scripts\\start_stage12_demo.bat"], {
      cwd: repoRoot,
      env: {
        ...process.env,
        NO_OPEN_BROWSER: "1"
      },
      stdio: "ignore",
      windowsHide: true
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ skipped: false, output: "Stage 15 demo bootstrap completed with NO_OPEN_BROWSER=1.\n" });
        return;
      }
      reject(new Error(`Demo bootstrap failed with exit code ${code}.`));
    });
  });
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }
  if (!response.ok) {
    throw new Error(`Request failed for ${url}: ${response.status} ${response.statusText}\n${text}`);
  }
  return payload;
}

function authHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${apiToken}`,
    ...extra
  };
}

async function requestText(url, init = {}) {
  const response = await fetch(url, init);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Request failed for ${url}: ${response.status} ${response.statusText}\n${text}`);
  }
  return text;
}

async function waitForApiReady() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      await requestJson(`${apiBaseUrl}/api/v1/session`, {
        headers: {
          Authorization: `Bearer ${apiToken}`
        }
      });
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  throw new Error(`Timed out waiting for API readiness at ${apiBaseUrl}.`);
}

async function waitForHostedFrontendAssetsReady() {
  const assets = [
    `${apiBaseUrl}/app-static/frontend/workspace_shell_app/dist/assets/workspace-shell-app.js`,
    `${apiBaseUrl}/app-static/frontend/workspace_shell_app/dist/assets/workspace-shell-app.css`
  ];
  for (const assetUrl of assets) {
    await waitFor(async () => {
      const body = await requestText(assetUrl);
      return body.length > 1000 ? body.length : null;
    }, `Timed out waiting for hosted frontend asset readiness: ${assetUrl}`, {
      timeoutMs: 60000,
      intervalMs: 1000
    });
  }
}

async function waitFor(asyncPredicate, message, { timeoutMs = 120000, intervalMs = 500 } = {}) {
  const startedAt = Date.now();
  let lastError = null;
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const result = await asyncPredicate();
      if (result) {
        return result;
      }
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  if (lastError) {
    throw new Error(`${message}\nLast error: ${lastError.message}`);
  }
  throw new Error(message);
}

async function readSummaryRows(page, selector) {
  return await page.locator(`${selector} .summary-row`).evaluateAll((nodes) => (
    nodes.map((node) => {
      const label = node.querySelector("span")?.textContent?.trim() || "";
      const value = node.querySelector("strong")?.textContent?.trim() || "";
      return { label, value };
    })
  ));
}

async function waitForSummaryValue(page, selector, expectedValue, message) {
  return await waitFor(async () => {
    const rows = await readSummaryRows(page, selector);
    return rows.some((row) => row.value.includes(expectedValue)) ? rows : null;
  }, message);
}

async function waitForSummaryLabelValue(page, selector, label, expectedValue, message) {
  return await waitFor(async () => {
    const rows = await readSummaryRows(page, selector);
    return rows.some((row) => row.label === label && row.value.includes(expectedValue)) ? rows : null;
  }, message);
}

async function waitForEnabled(locator, message) {
  await waitFor(async () => (await locator.isVisible()) && !(await locator.isDisabled()), message);
}

async function waitForJobStatus(jobId, expectedStatuses, timeoutMs = jobStatusTimeoutMs) {
  const allowedStatuses = Array.isArray(expectedStatuses) ? expectedStatuses : [expectedStatuses];
  return await waitFor(async () => {
    const payload = await requestJson(`${apiBaseUrl}/api/v1/validation-jobs/${jobId}`, {
      headers: {
        Authorization: `Bearer ${apiToken}`
      }
    });
    log(`Observed job ${jobId} status: ${payload?.job?.status || "unknown"}`);
    return allowedStatuses.includes(payload?.job?.status) ? payload.job : null;
  }, `Timed out waiting for job ${jobId} to reach one of: ${allowedStatuses.join(", ")}.`, {
    timeoutMs,
    intervalMs: validationProviderName === "mock" ? 500 : 5000,
  });
}

async function readSubmitDebug(page) {
  if (!page) {
    return null;
  }
  return {
    bridgePill: String(await page.locator("#bridge-pill").textContent().catch(() => "") || "").trim(),
    jobPill: String(await page.locator("#job-pill").textContent().catch(() => "") || "").trim(),
    requestPayload: String(await page.locator("#request-payload-json").textContent().catch(() => "") || "").trim(),
    lastApiResponse: String(await page.locator("#last-api-json").textContent().catch(() => "") || "").trim()
  };
}

async function waitForJobCreatedForStudy(studyId, page = null) {
  try {
    return await waitFor(async () => {
      const payload = await requestJson(`${apiBaseUrl}/api/v1/validation-jobs`, {
        headers: {
          Authorization: `Bearer ${apiToken}`
        }
      });
      const matchingJob = (payload?.jobs || []).find((job) => String(job?.metadata?.study_id || "") === String(studyId));
      if (matchingJob?.job_id) {
        log(`Observed submitted job ${matchingJob.job_id} for study ${studyId}.`);
        return matchingJob;
      }
      return null;
    }, `Timed out waiting for a submitted job linked to study '${studyId}'.`);
  } catch (error) {
    const debug = await readSubmitDebug(page);
    throw new Error(`${error.message}\nSubmit debug:\n${JSON.stringify(debug, null, 2)}`);
  }
}

async function waitForStudyCard(page, selector, expectedText, message) {
  return await waitFor(async () => {
    const texts = await page.locator(`${selector} .product-card`).allTextContents();
    return texts.some((text) => text.includes(expectedText)) ? texts : null;
  }, message);
}

async function createPrototypeFixtureArtifact() {
  const pngBase64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lSXw4QAAAABJRU5ErkJggg==";
  const artifactPath = path.join(artifactDir, "personal_mvp_prototype_fixture.png");
  await fs.writeFile(artifactPath, Buffer.from(pngBase64, "base64"));
  return artifactPath;
}

async function waitForEvidenceViewDetail({ studyId, jobId, title }) {
  return await waitFor(async () => {
    const params = new URLSearchParams({ study_id: studyId, job_id: jobId });
    const payload = await requestJson(`${apiBaseUrl}/api/v1/evidence-views?${params.toString()}`, {
      headers: authHeaders()
    });
    const view = (payload?.evidence_views || []).find((item) => item?.title === title);
    if (!view?.evidence_view_id) {
      return null;
    }
    const detail = await requestJson(`${apiBaseUrl}/api/v1/evidence-views/${encodeURIComponent(view.evidence_view_id)}`, {
      headers: authHeaders()
    });
    return detail?.evidence_view || null;
  }, `Timed out waiting for evidence view '${title}' to be created.`);
}

async function waitForDecisionLogDetail({ studyId, jobId, evidenceViewId, title }) {
  return await waitFor(async () => {
    const params = new URLSearchParams({ study_id: studyId, job_id: jobId });
    if (evidenceViewId) {
      params.set("evidence_view_id", evidenceViewId);
    }
    const payload = await requestJson(`${apiBaseUrl}/api/v1/decision-logs?${params.toString()}`, {
      headers: authHeaders()
    });
    const decision = (payload?.decision_logs || []).find((item) => item?.title === title);
    if (!decision?.decision_log_id) {
      return null;
    }
    const detail = await requestJson(`${apiBaseUrl}/api/v1/decision-logs/${encodeURIComponent(decision.decision_log_id)}`, {
      headers: authHeaders()
    });
    return detail?.decision_log || null;
  }, `Timed out waiting for decision log '${title}' to be created.`);
}

function assertProviderBoundary(payload, expectedProviderName, artifactLabel) {
  const boundary = payload?.provider_runtime_boundary || {};
  assert(
    boundary.provider_name === expectedProviderName,
    `${artifactLabel} did not preserve provider_name='${expectedProviderName}'. Boundary: ${JSON.stringify(boundary)}`
  );
  if (expectedProviderName === "mock") {
    assert(
      boundary.evidence_mode === "mock_demo",
      `${artifactLabel} did not preserve mock_demo evidence mode. Boundary: ${JSON.stringify(boundary)}`
    );
    return boundary;
  }
  assert(
    boundary.evidence_mode === "live_synthetic",
    `${artifactLabel} did not preserve live_synthetic evidence mode. Boundary: ${JSON.stringify(boundary)}`
  );
  assert(
    boundary.runtime_status === "completed",
    `${artifactLabel} did not preserve completed provider runtime status. Boundary: ${JSON.stringify(boundary)}`
  );
  return boundary;
}

async function clickAndWaitForPath(page, trigger, pathnamePattern, message) {
  await trigger();
  await waitFor(async () => pathnamePattern.test(new URL(page.url()).pathname), message);
}

async function selectCardByText(page, selector, text, message) {
  const card = page.locator(`${selector} .product-card`).filter({ hasText: text }).first();
  await waitFor(async () => (await card.count()) > 0, message);
  await card.click();
}

async function openWorkspaceSurface(page, navId, visibleSelector) {
  const navItem = page.locator(`[data-nav-id="${navId}"]`).first();
  await waitForEnabled(navItem, `Navigation item '${navId}' was not visible and enabled.`);
  await navItem.click();
  await waitFor(async () => {
    const target = page.locator(visibleSelector).first();
    return (await target.count()) > 0 && (await target.isVisible()) ? true : null;
  }, `Workspace surface '${navId}' did not expose '${visibleSelector}'.`);
}

async function waitForHostedShellReady(page) {
  await waitFor(async () => {
    const sessionRows = await page.locator("#session-summary .summary-row").count();
    const projectSurfaceReady = (await page.locator("#project-list .product-empty, #project-list .product-card").count()) > 0;
    const studySurfaceReady = (await page.locator("#study-list .product-empty, #study-list .product-card").count()) > 0;
    return sessionRows > 0 && projectSurfaceReady && studySurfaceReady;
  }, "Hosted shell did not finish initial session/project/study hydration.");
}

async function assertCriticalActionsUnblocked(page) {
  const selectors = [
    "#create-project",
    "#create-study",
    "#submit-live-job",
    "#apply-evidence-query",
    "#create-export-bundle",
    "#create-share-bundle",
    "#create-support-snapshot"
  ];
  const failures = [];
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) === 0 || !(await locator.isVisible())) {
      continue;
    }
    await locator.scrollIntoViewIfNeeded();
    await page.waitForTimeout(100);
    const result = await locator.evaluate((element, selectorValue) => {
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) {
        return { selector: selectorValue, ok: false, reason: "empty bounding box" };
      }
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const hit = document.elementFromPoint(x, y);
      const ok = hit === element || element.contains(hit);
      return {
        selector: selectorValue,
        ok,
        reason: ok ? "" : `center point hit ${hit?.tagName || "nothing"}${hit?.id ? `#${hit.id}` : ""}${hit?.className ? `.${String(hit.className).replace(/\s+/g, ".")}` : ""}`,
        rect: {
          left: Math.round(rect.left),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        }
      };
    }, selector);
    if (!result.ok) {
      failures.push(result);
    }
  }
  assert(
    failures.length === 0,
    `Critical product actions are visually blocked or occluded:\n${JSON.stringify(failures, null, 2)}`
  );
  return { checked_action_count: selectors.length, failures };
}

async function assertNoCriticalPanelOverlap(page) {
  const selectorGroups = [
    ["selected-project-summary", "#selected-project-summary"],
    ["selected-study-summary", "#selected-study-summary"],
    ["evidence-list", "#evidence-list"],
    ["provider-runtime-summary", "#provider-runtime-summary"],
    ["provider-runtime-catalog", "#provider-runtime-catalog"],
    ["selected-evidence-summary", "#selected-evidence-summary"],
    ["cross-run-summary", "#cross-run-summary"],
    ["selected-export-summary", "#selected-export-summary"],
    ["selected-share-summary", "#selected-share-summary"],
    ["selected-support-summary", "#selected-support-summary"]
  ];
  const overlaps = await page.evaluate((groups) => {
    const boxes = [];
    for (const [label, selector] of groups) {
      const element = document.querySelector(selector);
      if (!element) {
        continue;
      }
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if (style.display === "none" || style.visibility === "hidden" || rect.width <= 0 || rect.height <= 0) {
        continue;
      }
      boxes.push({
        label,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height
      });
    }
    const findings = [];
    for (let leftIndex = 0; leftIndex < boxes.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < boxes.length; rightIndex += 1) {
        const left = boxes[leftIndex];
        const right = boxes[rightIndex];
        const xOverlap = Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left));
        const yOverlap = Math.max(0, Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top));
        const overlapArea = xOverlap * yOverlap;
        const smallerArea = Math.min(left.width * left.height, right.width * right.height);
        const ratio = smallerArea > 0 ? overlapArea / smallerArea : 0;
        if (overlapArea > 16 && ratio > 0.08) {
          findings.push({
            left: left.label,
            right: right.label,
            overlap_area: Math.round(overlapArea),
            overlap_ratio: Number(ratio.toFixed(3))
          });
        }
      }
    }
    return findings;
  }, selectorGroups);
  assert(
    overlaps.length === 0,
    `Critical product panels overlap visually:\n${JSON.stringify(overlaps, null, 2)}`
  );
  return { checked_panel_count: selectorGroups.length, overlaps };
}

async function assertMilestone12LayoutAcceptance(page) {
  return {
    criticalActions: await assertCriticalActionsUnblocked(page),
    criticalPanels: await assertNoCriticalPanelOverlap(page)
  };
}

async function writeJson(targetPath, payload) {
  await fs.writeFile(targetPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function main() {
  await ensureDir(artifactDir);
  assert(
    !personalMvpWorkflowId || activeWorkflow,
    `Unknown STAGE15_PERSONAL_MVP_WORKFLOW='${personalMvpWorkflowId}'. Expected one of: ${Object.keys(PERSONAL_MVP_WORKFLOWS).join(", ")}.`
  );

  const bootstrap = await runDemoBootstrap();
  await fs.writeFile(path.join(artifactDir, "demo_bootstrap.log"), bootstrap.output || "", "utf8");

  await waitForApiReady();
  await waitForHostedFrontendAssetsReady();
  await new Promise((resolve) => setTimeout(resolve, 3000));

  const playwrightModuleUrl = await resolvePlaywrightImportUrl();
  const chromiumExecutablePath = await resolveChromiumExecutablePath();
  const { chromium } = await import(playwrightModuleUrl);

  const browser = await chromium.launch({
    headless: process.env.STAGE15_HEADLESS !== "0",
    executablePath: chromiumExecutablePath
  });

  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 }
  });

  const consoleMessages = [];
  const pageErrors = [];
  page.on("console", (message) => {
    consoleMessages.push({ type: message.type(), text: message.text() });
  });
  page.on("pageerror", (error) => {
    pageErrors.push(String(error));
  });

  const timestampToken = Date.now();
  const workflow = activeWorkflow || DEFAULT_SMOKE_WORKFLOW;
  const personalMvpAcceptance = Boolean(activeWorkflow);
  const projectName = `${workflow.projectNamePrefix} ${timestampToken}`;
  const projectSlug = slugify(projectName);
  const studyTitle = `${workflow.studyTitlePrefix} ${timestampToken}`;
  const firstTask = workflow.firstTask;
  const researchIntent = workflow.researchIntent;
  const desiredOutcome = workflow.desiredOutcome;
  const evidenceViewTitle = `${workflow.evidenceViewTitlePrefix} ${timestampToken}`;
  const decisionLogTitle = `${workflow.decisionTitlePrefix} ${timestampToken}`;
  const exportTitle = `Smoke export ${timestampToken}`;
  const shareTitle = `Smoke share ${timestampToken}`;
  const supportSnapshotTitle = `Smoke support snapshot ${timestampToken}`;

  try {
    log(`Opening hosted shell at ${hostedUrl}`);
    await page.goto(hostedUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    await waitForHostedShellReady(page);

    assert(pageErrors.length === 0, `Hosted shell hit page errors before interaction: ${pageErrors.join("\n")}`);

    await page.fill("#project-name", projectName);
    await page.fill("#project-slug", projectSlug);
    log("Creating project from hosted shell...");
    await clickAndWaitForPath(
      page,
      () => page.click("#create-project"),
      /\/app\/projects\/[^/?#]+$/,
      "Project route did not promote into a project-scoped hosted path."
    );
    await waitFor(async () => {
      const metricText = String(await page.locator("#metric-project").textContent() || "").trim();
      return metricText && metricText !== "-" ? metricText : null;
    }, "Hosted shell did not expose a selected project after project creation.");

    await openWorkspaceSurface(page, "new-study", "#mode-override");
    await page.selectOption("#mode-override", workflow.modeOverride);
    await page.selectOption("#provider-name", validationProviderName);
    await page.fill("#sample-size", validationSampleSize);
    await page.fill("#research-intent", researchIntent);
    await page.fill("#desired-outcome", desiredOutcome);
    await page.fill("#first-task", firstTask);
    if (workflow.attachArtifacts) {
      const prototypeArtifactPath = await createPrototypeFixtureArtifact();
      log(`Attaching prototype fixture artifact: ${prototypeArtifactPath}`);
      await page.setInputFiles("#artifact-files", prototypeArtifactPath);
      await waitFor(async () => {
        const text = String(await page.locator("#artifact-note").textContent() || "");
        return text.includes("personal_mvp_prototype_fixture.png") ? text : null;
      }, "Prototype artifact file selection did not update the hosted shell artifact state.");
    }

    const chooseFallbackButton = page.getByRole("button", { name: "choose fallback" });
    if (workflow.useFallback) {
      await waitForEnabled(chooseFallbackButton, "Choose fallback button never became enabled for concept-level study submission.");
      log("Switching the hosted shell into explicit fallback mode...");
      await chooseFallbackButton.click();
    }

    const confirmPlanButton = page.getByRole("button", { name: "confirm plan" });
    await waitForEnabled(confirmPlanButton, "Confirm plan button never became enabled.");
    log("Confirming inferred study plan...");
    await confirmPlanButton.click();

    await openWorkspaceSurface(page, "studies", "#study-title");
    await page.fill("#study-title", studyTitle);
    await page.fill("#study-first-task", firstTask);

    log("Creating study from hosted shell...");
    await clickAndWaitForPath(
      page,
      () => page.click("#create-study"),
      /\/app\/studies\/[^/?#]+$/,
      "Study route did not promote into a study-scoped hosted path."
    );
    const studyId = await waitFor(async () => {
      const metricText = String(await page.locator("#metric-study").textContent() || "").trim();
      return metricText && metricText !== "-" ? metricText : null;
    }, "Hosted shell did not expose a selected study after study creation.");

    const submitLiveJobButton = page.locator("#submit-live-job");
    await waitForEnabled(submitLiveJobButton, "Submit live job button never became enabled after plan confirmation.");
    log("Submitting live validation job...");
    await submitLiveJobButton.click();
    const submittedJob = await waitForJobCreatedForStudy(studyId, page);
    const firstJobId = submittedJob.job_id;
    const terminalJob = await waitForJobStatus(firstJobId, expectedJobStatuses);
    const terminalJobStatus = terminalJob.status;

    log(`Reopening the ${terminalJobStatus} job deep link inside the hosted shell...`);
    await page.goto(`${apiBaseUrl}/app/jobs/${firstJobId}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    await waitFor(async () => {
      const jobPillText = await page.locator("#job-pill").textContent();
      return String(jobPillText || "").trim() === terminalJobStatus;
    }, `${terminalJobStatus} job route did not hydrate back into the hosted shell.`);

    const providerRuntimeSummary = await waitForSummaryLabelValue(
      page,
      "#provider-runtime-summary",
      "provider",
      validationProviderName,
      "Provider runtime summary did not show the selected validation provider."
    );
    assert(
      providerRuntimeSummary.some((row) => row.label === "evidence mode" && row.value !== "-"),
      "Provider runtime summary did not expose evidence mode."
    );

    if (terminalJobStatus !== "completed") {
      assert(pageErrors.length === 0, `Hosted shell hit page errors during provider-state smoke flow: ${pageErrors.join("\n")}`);
      log("Running provider-state layout acceptance gates...");
      const layoutAcceptance = await assertMilestone12LayoutAcceptance(page);
      const summary = {
        hostedUrl,
        apiBaseUrl,
        artifactDir,
        playwrightModuleUrl,
        chromiumExecutablePath,
        validationProviderName,
        validationSampleSize,
        expectedJobStatuses,
        workflowId: workflow.id,
        personalMvpWorkflowId,
        terminalJobStatus,
        projectName,
        projectSlug,
        studyTitle,
        firstJobId,
        providerRuntimeSummary,
        selectedProjectSummary: await readSummaryRows(page, "#selected-project-summary"),
        selectedStudySummary: await readSummaryRows(page, "#selected-study-summary"),
        layoutAcceptance,
        consoleMessages,
        pageErrors
      };
      await page.screenshot({ path: path.join(artifactDir, "stage15_hosted_shell_smoke.png"), fullPage: true });
      await writeJson(path.join(artifactDir, "stage15_hosted_shell_smoke.summary.json"), summary);
      log(`Stage 15 hosted shell provider-state smoke verification passed. Artifacts: ${artifactDir}`);
      return;
    }

    log("Refreshing evidence review surface...");
    await page.click("#apply-evidence-query");
    await waitFor(
      async () => (await page.locator("#evidence-list .product-card").count()) > 0,
      "Evidence results did not appear after reopening the completed job route."
    );

    let personalMvpWorkflowAcceptance = null;
    if (personalMvpAcceptance) {
      log(`Creating saved evidence view for personal MVP workflow '${workflow.id}'...`);
      await openWorkspaceSurface(page, "studies", "#create-evidence-view");
      await page.fill("#evidence-view-title", evidenceViewTitle);
      await page.fill("#evidence-view-note", workflow.evidenceViewNote);
      const createEvidenceViewButton = page.locator("#create-evidence-view");
      await waitForEnabled(createEvidenceViewButton, "Create evidence view button never became enabled for personal MVP acceptance.");
      await clickAndWaitForPath(
        page,
        () => createEvidenceViewButton.click(),
        /\/app\/evidence-views\/[^/?#]+$/,
        "Evidence view route did not promote into an evidence-view hosted path."
      );
      const evidenceViewDetail = await waitForEvidenceViewDetail({
        studyId,
        jobId: firstJobId,
        title: evidenceViewTitle
      });
      const evidenceViewBoundary = assertProviderBoundary(
        evidenceViewDetail,
        validationProviderName,
        "Saved evidence view"
      );
      await waitForSummaryValue(
        page,
        "#selected-evidence-view-summary",
        evidenceViewTitle,
        "Selected evidence-view summary did not show the created personal MVP evidence view."
      );

      log(`Creating decision log for personal MVP workflow '${workflow.id}'...`);
      await openWorkspaceSurface(page, "studies", "#create-decision-log");
      await page.fill("#decision-log-title", decisionLogTitle);
      await page.fill("#decision-log-summary", workflow.decisionSummary);
      await page.fill("#decision-log-rationale", workflow.decisionRationale);
      const createDecisionLogButton = page.locator("#create-decision-log");
      await waitForEnabled(createDecisionLogButton, "Create decision log button never became enabled for personal MVP acceptance.");
      await clickAndWaitForPath(
        page,
        () => createDecisionLogButton.click(),
        /\/app\/decision-logs\/[^/?#]+$/,
        "Decision-log route did not promote into a decision-log hosted path."
      );
      const decisionLogDetail = await waitForDecisionLogDetail({
        studyId,
        jobId: firstJobId,
        evidenceViewId: evidenceViewDetail.evidence_view_id,
        title: decisionLogTitle
      });
      const decisionLogBoundary = assertProviderBoundary(
        decisionLogDetail,
        validationProviderName,
        "Decision log"
      );
      await waitForSummaryValue(
        page,
        "#selected-decision-log-summary",
        decisionLogTitle,
        "Selected decision-log summary did not show the created personal MVP decision log."
      );

      personalMvpWorkflowAcceptance = {
        workflow_id: workflow.id,
        primary_mode: terminalJob?.metadata?.primary_mode || "",
        mode_override: workflow.modeOverride,
        attach_artifacts: workflow.attachArtifacts,
        used_fallback: workflow.useFallback,
        known_limitation: workflow.knownLimitation || "",
        evidence_view_id: evidenceViewDetail.evidence_view_id,
        evidence_view_title: evidenceViewDetail.title,
        evidence_view_provider_runtime_boundary: evidenceViewBoundary,
        decision_log_id: decisionLogDetail.decision_log_id,
        decision_log_title: decisionLogDetail.title,
        decision_log_provider_runtime_boundary: decisionLogBoundary
      };
    }

    if (providerAcceptanceOnly && !personalMvpAcceptance) {
      assert(pageErrors.length === 0, `Hosted shell hit page errors during provider acceptance flow: ${pageErrors.join("\n")}`);
      log("Running provider acceptance layout gates...");
      const layoutAcceptance = await assertMilestone12LayoutAcceptance(page);
      const summary = {
        hostedUrl,
        apiBaseUrl,
        artifactDir,
        playwrightModuleUrl,
        chromiumExecutablePath,
        validationProviderName,
        validationSampleSize,
        expectedJobStatuses,
        workflowId: workflow.id,
        personalMvpWorkflowId,
        terminalJobStatus,
        projectName,
        projectSlug,
        studyTitle,
        firstJobId,
        providerRuntimeSummary: await readSummaryRows(page, "#provider-runtime-summary"),
        reviewSummary: await readSummaryRows(page, "#review-summary"),
        selectedEvidenceSummary: await readSummaryRows(page, "#selected-evidence-summary"),
        personalMvpWorkflowAcceptance,
        selectedProjectSummary: await readSummaryRows(page, "#selected-project-summary"),
        selectedStudySummary: await readSummaryRows(page, "#selected-study-summary"),
        layoutAcceptance,
        consoleMessages,
        pageErrors
      };
      await page.screenshot({ path: path.join(artifactDir, "stage15_hosted_shell_smoke.png"), fullPage: true });
      await writeJson(path.join(artifactDir, "stage15_hosted_shell_smoke.summary.json"), summary);
      log(`Stage 15 hosted shell provider acceptance smoke verification passed. Artifacts: ${artifactDir}`);
      return;
    }

    await openWorkspaceSurface(page, "evidence", "#export-title");
    await page.fill("#export-title", exportTitle);
    log("Creating export bundle...");
    await clickAndWaitForPath(
      page,
      () => page.click("#create-export-bundle"),
      /\/app\/export-bundles\/[^/?#]+$/,
      "Export route did not promote into an export-scoped hosted path."
    );
    const exportSummary = await waitForSummaryValue(
      page,
      "#selected-export-summary",
      exportTitle,
      "Selected export summary did not show the created export bundle."
    );
    assert(
      exportSummary.some((row) => row.label === "boundary" && /synthetic/i.test(row.value)),
      "Export summary did not expose a synthetic boundary value."
    );

    await page.fill("#share-title", shareTitle);
    log("Creating share bundle...");
    await clickAndWaitForPath(
      page,
      () => page.click("#create-share-bundle"),
      /\/app\/share-bundles\/[^/?#]+$/,
      "Share route did not promote into a share-scoped hosted path."
    );
    const shareSummary = await waitForSummaryValue(
      page,
      "#selected-share-summary",
      shareTitle,
      "Selected share summary did not show the created share bundle."
    );
    const publicPathRow = shareSummary.find((row) => row.label === "public path");
    assert(publicPathRow?.value, "Share summary did not expose a public path.");
    assert(
      shareSummary.some((row) => row.label === "boundary" && /synthetic/i.test(row.value)),
      "Share summary did not expose a synthetic boundary value."
    );

    const publicShareUrl = new URL(publicPathRow.value, apiBaseUrl).toString();
    const publicSharePayload = await requestJson(publicShareUrl);
    assert(
      /synthetic/i.test(String(publicSharePayload?.share_bundle?.synthetic_boundary || "")),
      "Public share payload did not preserve a synthetic boundary."
    );

    await openWorkspaceSurface(page, "support", "#load-support-diagnostics");
    log("Loading support diagnostics...");
    await page.click("#load-support-diagnostics");
    await waitFor(async () => {
      const rows = await readSummaryRows(page, "#support-diagnostic-summary");
      return rows.some((row) => row.label === "job status" && row.value === "completed") ? rows : null;
    }, "Support diagnostics did not load the selected completed job.");

    await page.fill("#support-snapshot-title", supportSnapshotTitle);
    await page.fill("#support-snapshot-notes", "Smoke harness verifying hosted support handoff generation.");
    log("Creating support snapshot...");
    await clickAndWaitForPath(
      page,
      () => page.click("#create-support-snapshot"),
      /\/app\/support-snapshots\/[^/?#]+$/,
      "Support route did not promote into a support-snapshot hosted path."
    );
    await waitForSummaryValue(
      page,
      "#selected-support-summary",
      supportSnapshotTitle,
      "Selected support summary did not show the generated support snapshot."
    );

    assert(pageErrors.length === 0, `Hosted shell hit page errors during smoke flow: ${pageErrors.join("\n")}`);
    log("Running Milestone 12 product-shell layout acceptance gates...");
    const layoutAcceptance = await assertMilestone12LayoutAcceptance(page);

    const summary = {
      hostedUrl,
      apiBaseUrl,
      artifactDir,
      playwrightModuleUrl,
      chromiumExecutablePath,
      validationProviderName,
      validationSampleSize,
      expectedJobStatuses,
      workflowId: workflow.id,
      personalMvpWorkflowId,
      terminalJobStatus,
      projectName,
      projectSlug,
      studyTitle,
      firstJobId,
      publicShareUrl,
      selectedProjectSummary: await readSummaryRows(page, "#selected-project-summary"),
      selectedStudySummary: await readSummaryRows(page, "#selected-study-summary"),
      providerRuntimeSummary: await readSummaryRows(page, "#provider-runtime-summary"),
      reviewSummary: await readSummaryRows(page, "#review-summary"),
      selectedEvidenceSummary: await readSummaryRows(page, "#selected-evidence-summary"),
      personalMvpWorkflowAcceptance,
      selectedExportSummary: await readSummaryRows(page, "#selected-export-summary"),
      selectedShareSummary: await readSummaryRows(page, "#selected-share-summary"),
      selectedSupportSummary: await readSummaryRows(page, "#selected-support-summary"),
      layoutAcceptance,
      consoleMessages,
      pageErrors
    };

    await page.screenshot({ path: path.join(artifactDir, "stage15_hosted_shell_smoke.png"), fullPage: true });
    await writeJson(path.join(artifactDir, "stage15_hosted_shell_smoke.summary.json"), summary);

    log(`Stage 15 hosted shell smoke verification passed. Artifacts: ${artifactDir}`);
  } finally {
    await page.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

main().catch(async (error) => {
  try {
    await ensureDir(artifactDir);
    await fs.writeFile(
      path.join(artifactDir, "stage15_hosted_shell_smoke.error.log"),
      `${error.stack || error.message}\n`,
      "utf8"
    );
  } catch {
    // Ignore secondary artifact write failures.
  }
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
