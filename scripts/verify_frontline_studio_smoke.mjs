import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const runLabel = new Date().toISOString().replace(/[:.]/g, "-");
const artifactDir = path.join(repoRoot, "output", "playwright", "frontline_studio_smoke", runLabel);
const runtimeRoot = path.join(artifactDir, "runtime");
const apiPort = Number.parseInt(process.env.FRONTLINE_STUDIO_SMOKE_PORT || "8051", 10);
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;
const apiToken = "token-frontline-smoke";

async function pathExists(candidatePath) {
  try {
    await fs.access(candidatePath);
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
  const candidateNodeModules = [
    process.env.PLAYWRIGHT_NODE_MODULE_DIR || "",
    path.join(repoRoot, "frontend", "workspace_shell_app", "node_modules"),
    path.join(repoRoot, "node_modules"),
  ].filter(Boolean);
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
    const entryPath = path.join(nodeModulesPath, "playwright", "index.mjs");
    if (await pathExists(entryPath)) {
      return pathToFileURL(entryPath).href;
    }
  }
  throw new Error("Unable to locate Playwright. Run the Stage15 smoke once or set PLAYWRIGHT_NODE_MODULE_DIR.");
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
    for (const candidatePath of [
      path.join(basePath, "chrome-win64", "chrome.exe"),
      path.join(basePath, "chrome-win", "chrome.exe"),
      path.join(basePath, "chrome-linux", "chrome"),
      path.join(basePath, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"),
    ]) {
      if (await pathExists(candidatePath)) {
        return candidatePath;
      }
    }
  }
  throw new Error("Unable to locate Chromium. Set PLAYWRIGHT_EXECUTABLE_PATH or install Playwright browsers.");
}

function startServer() {
  const pythonCode = `
import os
import sys
from pathlib import Path
from wsgiref.simple_server import make_server
repo = Path(os.environ["FRONTLINE_REPO_ROOT"])
src = repo / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
from ai_validation_swarm.saas.api import SaasApiApplication
from ai_validation_swarm.saas.runtime import SaasRuntime
runtime = SaasRuntime(Path(os.environ["FRONTLINE_RUNTIME_ROOT"]))
runtime.bootstrap_workspace(
    workspace_id="ws_frontline_smoke",
    slug="frontline-smoke",
    display_name="Frontline Smoke",
    owner_user_id="owner_frontline_smoke",
    api_token="${apiToken}",
    plan_tier="pro",
    billing_status="active",
    settings={"daily_runs": 10, "max_concurrent_jobs": 2},
)
with make_server("127.0.0.1", int(os.environ["FRONTLINE_API_PORT"]), SaasApiApplication(runtime)) as server:
    server.serve_forever()
`;
  return spawn(process.env.PYTHON || "python", ["-c", pythonCode], {
    cwd: repoRoot,
    env: {
      ...process.env,
      FRONTLINE_REPO_ROOT: repoRoot,
      FRONTLINE_RUNTIME_ROOT: runtimeRoot,
      FRONTLINE_API_PORT: String(apiPort),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
}

async function waitForReady() {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/health`);
      if (response.ok) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  throw new Error("Frontline smoke server did not become ready.");
}

async function runWorkerOnce() {
  const workerEnv = {
    ...process.env,
    PYTHONPATH: [path.join(repoRoot, "src"), process.env.PYTHONPATH || ""].filter(Boolean).join(path.delimiter),
  };
  const child = spawn(
    process.env.PYTHON || "python",
    ["-m", "ai_validation_swarm.cli.main", "run-saas-worker", "--runtime-root", runtimeRoot, "--once", "--poll-seconds", "0.05"],
    {
      cwd: repoRoot,
      env: workerEnv,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let output = "";
  child.stdout.on("data", (chunk) => { output += chunk.toString(); });
  child.stderr.on("data", (chunk) => { output += chunk.toString(); });
  const exitCode = await new Promise((resolve) => {
    child.on("close", resolve);
  });
  if (exitCode !== 0) {
    throw new Error(`Frontline worker failed with code ${exitCode}: ${output}`);
  }
  if (!output.includes("Processed 1 SaaS validation jobs.")) {
    throw new Error(`Frontline worker did not process exactly one research attempt: ${output}`);
  }
  return output;
}

async function run() {
  await fs.mkdir(artifactDir, { recursive: true });
  const server = startServer();
  let serverLog = "";
  server.stdout.on("data", (chunk) => { serverLog += chunk.toString(); });
  server.stderr.on("data", (chunk) => { serverLog += chunk.toString(); });
  let browser;
  try {
    await waitForReady();
    const { chromium } = await import(await resolvePlaywrightImportUrl());
    browser = await chromium.launch({
      headless: true,
      executablePath: await resolveChromiumExecutablePath(),
    });
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const browserDiagnostics = [];
    page.on("pageerror", (error) => {
      browserDiagnostics.push(`pageerror: ${error.message}`);
    });
    page.on("console", (message) => {
      if (["error", "warning"].includes(message.type())) {
        browserDiagnostics.push(`${message.type()}: ${message.text()}`);
      }
    });

    async function waitForRouteTitle(expectedTitle) {
      try {
        await page.waitForFunction(
          (title) => document.querySelector("#route-title")?.textContent === title,
          expectedTitle,
          { timeout: 15000 },
        );
      } catch (error) {
        const state = await page.evaluate(() => ({
          url: window.location.href,
          routeTitle: document.querySelector("#route-title")?.textContent || "",
          routeKind: document.querySelector("#route-kind")?.textContent || "",
          injectedRouteKind: window.__FRONTLINE_ROUTE_CONTEXT__?.route_kind || "",
          injectedRoutePath: window.__FRONTLINE_ROUTE_CONTEXT__?.route_path || "",
          body: document.body?.innerText?.slice(0, 1200) || "",
        }));
        throw new Error(`Expected route title "${expectedTitle}" but saw ${JSON.stringify(state)}: ${error.message}`);
      }
      try {
        await page.waitForFunction(
          () => !document.querySelector(".loading-card"),
          undefined,
          { timeout: 15000 },
        );
      } catch (error) {
        const state = await page.evaluate(() => ({
          url: window.location.href,
          routeTitle: document.querySelector("#route-title")?.textContent || "",
          routeKind: document.querySelector("#route-kind")?.textContent || "",
          injectedRouteKind: window.__FRONTLINE_ROUTE_CONTEXT__?.route_kind || "",
          injectedRoutePath: window.__FRONTLINE_ROUTE_CONTEXT__?.route_path || "",
          errorCard: document.querySelector(".error-card")?.textContent || "",
          loadingText: document.querySelector(".loading-card")?.textContent || "",
          body: document.body?.innerText?.slice(0, 1200) || "",
        }));
        throw new Error(`Route "${expectedTitle}" did not finish loading: ${JSON.stringify({ ...state, browserDiagnostics })}: ${error.message}`);
      }
    }

    async function assertNoInternalTerms() {
      const visibleText = await page.locator("body").innerText();
      const lower = visibleText.toLowerCase();
      const forbiddenTerms = [
        "milestone",
        "roadmap",
        "operator",
        "provider",
        "job id",
        "runtime",
        "payload",
        "debug",
        "stage",
      ];
      const leaked = forbiddenTerms.filter((term) => lower.includes(term));
      if (leaked.length) {
        const snippets = leaked.map((term) => {
          const index = lower.indexOf(term);
          return `${term}: ${visibleText.slice(Math.max(0, index - 80), index + term.length + 120).replace(/\s+/g, " ")}`;
        });
        throw new Error(`Frontline Studio leaked internal terms: ${leaked.join(", ")} | ${snippets.join(" || ")}`);
      }
    }

    async function assertNoHorizontalOverflow(width) {
      await page.setViewportSize({ width, height: 900 });
      const layout = await page.evaluate(() => ({
        width: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        hasHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      }));
      if (layout.hasHorizontalOverflow) {
        throw new Error(`Frontline Studio has horizontal overflow at ${width}px viewport: ${JSON.stringify(layout)}`);
      }
      return layout;
    }

    async function assertNoCriticalOverlap() {
      const overlap = await page.evaluate(() => {
        const regionElements = Array.from(document.querySelectorAll(
          ".studio-rail, .rail-top, .rail-scroll, .rail-bottom, .ia-nav, .context-nav, .route-header, .study-context, .hero-panel, .copilot-panel, .paper-card, .object-list",
        ))
          .filter((element) => {
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 1 && rect.height > 1 && style.visibility !== "hidden" && style.display !== "none";
          });
        const regions = regionElements.map((element, index) => ({
            index,
            label: element.className || element.tagName,
            rect: element.getBoundingClientRect().toJSON(),
          }));
        for (let leftIndex = 0; leftIndex < regions.length; leftIndex += 1) {
          for (let rightIndex = leftIndex + 1; rightIndex < regions.length; rightIndex += 1) {
            if (regionElements[leftIndex].contains(regionElements[rightIndex]) || regionElements[rightIndex].contains(regionElements[leftIndex])) {
              continue;
            }
            const left = regions[leftIndex];
            const right = regions[rightIndex];
            const xOverlap = Math.max(0, Math.min(left.rect.right, right.rect.right) - Math.max(left.rect.left, right.rect.left));
            const yOverlap = Math.max(0, Math.min(left.rect.bottom, right.rect.bottom) - Math.max(left.rect.top, right.rect.top));
            const area = xOverlap * yOverlap;
            if (area > 16) {
              return { left: left.label, right: right.label, area, leftRect: left.rect, rightRect: right.rect };
            }
          }
        }
        return null;
      });
      if (overlap) {
        throw new Error(`Frontline Studio has critical panel overlap: ${JSON.stringify(overlap)}`);
      }
    }

    async function assertNavLevel(expectedLevel) {
      const state = await page.evaluate(() => ({
        hasProjectList: Boolean(document.querySelector("#project-list")),
        hasProjectStudyList: Boolean(document.querySelector("#project-study-list")),
        hasStudyNav: Boolean(document.querySelector("#study-nav")),
        hasBack: Boolean(document.querySelector("#nav-back")),
      }));
      const expected = {
        projects: { hasProjectList: true, hasProjectStudyList: false, hasStudyNav: false, hasBack: false },
        project: { hasProjectList: false, hasProjectStudyList: true, hasStudyNav: false, hasBack: true },
        study: { hasProjectList: false, hasProjectStudyList: false, hasStudyNav: true, hasBack: true },
      }[expectedLevel];
      for (const [key, value] of Object.entries(expected)) {
        if (state[key] !== value) {
          throw new Error(`Expected ${expectedLevel} nav level but found ${JSON.stringify(state)}`);
        }
      }
    }

    await page.goto(`${apiBaseUrl}/studio?token=${encodeURIComponent(apiToken)}`, { waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Home");
    for (const forbiddenGlobalNavId of ["#nav-studies", "#nav-evidence", "#nav-decisions", "#nav-share"]) {
      if (await page.locator(forbiddenGlobalNavId).count()) {
        throw new Error(`Frontline Studio should not expose ${forbiddenGlobalNavId} as level-1 navigation.`);
      }
    }
    await page.waitForSelector("#project-list");
    await assertNavLevel("projects");
    await assertNoInternalTerms();
    await assertNoHorizontalOverflow(1280);
    await assertNoCriticalOverlap();
    await assertNoHorizontalOverflow(1024);
    await assertNoCriticalOverlap();

    await page.click("#nav-projects");
    await waitForRouteTitle("Projects");
    await assertNavLevel("projects");
    await assertNoInternalTerms();

    if (await page.locator("#start-new-study").count()) {
      await page.click("#start-new-study");
    } else {
      await page.goto(`${apiBaseUrl}/studio/studies/new`, { waitUntil: "domcontentloaded" });
    }
    await waitForRouteTitle("New study");
    await page.waitForSelector("#create-study", { timeout: 15000 });
    await page.fill(
      "#intent",
      "I want to learn whether solo founders understand a scheduling assistant concept and what would stop them from trying it."
    );
    await page.fill(
      "#study-purpose",
      "Decide whether to continue with this concept and what objections need human follow-up."
    );
    await page.fill("#target-participant", "Solo founders who manage sales calls and follow-up tasks themselves.");
    await page.fill("#artifact-notes", "No clickable prototype yet; evaluate the concept description and expected workflow.");
    await page.click("#create-study");
    await page.waitForURL(/\/studio\/studies\/[^/]+\/setup$/);
    await waitForRouteTitle("Guided setup");
    await page.waitForFunction(() => document.querySelector("#selected-study")?.textContent?.trim().length > 0);
    await assertNavLevel("study");
    const studyId = page.url().match(/\/studio\/studies\/([^/]+)\/setup$/)?.[1] || "";
    if (!studyId) {
      throw new Error("Unable to derive created study id from setup route.");
    }
    await page.click("#nav-back");
    await page.waitForURL(/\/studio\/projects\/[^/]+$/);
    await page.waitForSelector("#project-study-list");
    await assertNavLevel("project");
    await page.click(`#project-study-nav-${studyId}`);
    await waitForRouteTitle("Concept validation study");
    await assertNavLevel("study");
    await page.click("#study-nav-setup");
    await waitForRouteTitle("Guided setup");
    await assertNavLevel("study");
    await page.waitForSelector("#persona-library-picker");
    await page.waitForSelector("#persona-picker-cards .persona-card");
    await page.fill("#audience-criteria", "Recently handled sales calls or follow-up work\nOwns the workflow decision or strongly influences it");
    await page.fill("#guide-questions", "What do you understand this assistant is meant to help with?\nWhere would trust, effort, or setup risk stop you?\nWhat would you need to see before trying it?");
    await page.fill("#guide-focus", "Probe current behavior first, then concept clarity, trust gaps, adoption barriers, and human follow-up.");
    await page.waitForFunction(() => {
      const count = Number.parseInt(document.querySelector("#selected-persona-count strong")?.textContent || "0", 10);
      return count > 0;
    });
    await page.click("#propose-plan");
    await page.waitForFunction(() => document.querySelector("#study-status")?.textContent === "Ready to run");
    await page.waitForSelector("#plan-persona-panel");
    await page.waitForFunction(() => document.querySelector("#plan-persona-panel")?.textContent?.includes("selected synthetic participant"));
    await page.waitForFunction(() => document.querySelector("#plan-guide-list")?.textContent?.includes("What do you understand this assistant"));
    await page.waitForSelector("#confirm-plan:not([disabled])");
    await page.click("#confirm-plan");
    await page.waitForFunction(() => document.querySelector("#plan-revision")?.textContent === "Approved");
    await page.waitForSelector("#start-research-run:not([disabled])");
    await page.click("#start-research-run");
    await waitForRouteTitle("Research attempts");
    await page.waitForSelector("#research-run-list");
    await page.waitForFunction(() => document.querySelector("#research-run-list")?.textContent?.includes("Research attempt 1"));
    await assertNoInternalTerms();
    await assertNavLevel("study");

    const workerOutput = await runWorkerOnce();
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Research attempts");
    await page.waitForFunction(() => document.querySelector("#research-run-list")?.textContent?.includes("Ready for evidence review"));
    await page.locator("#research-run-list button", { hasText: "Open attempt" }).first().click();
    await waitForRouteTitle("Research attempt");
    try {
      await page.waitForSelector("#source-evidence", { timeout: 15000 });
    } catch (error) {
      const state = await page.evaluate(() => ({
        url: window.location.href,
        routeTitle: document.querySelector("#route-title")?.textContent || "",
        routeKind: document.querySelector("#route-kind")?.textContent || "",
        errorCard: document.querySelector(".error-card")?.textContent || "",
        researchRunList: document.querySelector("#research-run-list")?.textContent || "",
        body: document.body?.innerText?.slice(0, 1600) || "",
      }));
      throw new Error(`Research attempt did not expose source evidence: ${JSON.stringify(state)}: ${error.message}`);
    }
    await page.waitForSelector("#run-audit-notes");
    await page.waitForFunction(() => document.querySelector("#source-evidence")?.textContent?.includes("Source evidence"));
    await page.waitForFunction(() => document.querySelector("#interpretation-panel")?.textContent?.includes("Interpretation"));
    await page.waitForFunction(() => document.querySelector("#human-validation-gaps")?.textContent?.includes("Human-validation gaps"));
    await assertNoInternalTerms();
    await assertNoHorizontalOverflow(1280);
    await assertNoCriticalOverlap();

    await page.click("#study-nav-evidence");
    await waitForRouteTitle("Evidence workspace");
    await page.waitForSelector("#source-evidence");
    await page.waitForSelector("#evidence-filters");
    await page.waitForSelector("#comparison-panel");
    await page.waitForFunction(() => document.querySelector("#contradiction-panel")?.textContent?.includes("Contradictions"));
    await page.waitForSelector("#save-evidence-view:not([disabled])");
    await assertNavLevel("study");
    await assertNoInternalTerms();
    await page.click("#save-evidence-view");
    await page.waitForURL(/\/studio\/studies\/[^/]+\/evidence-views\/[^/]+$/);
    await waitForRouteTitle("Saved evidence view");
    await page.waitForSelector("#saved-view-provenance");
    await page.waitForFunction(() => document.querySelector("#saved-view-provenance")?.textContent?.includes("Provenance retained"));
    await assertNoInternalTerms();
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Saved evidence view");
    await page.waitForSelector("#saved-view-provenance");
    await page.waitForFunction(() => document.querySelector("#selected-study")?.textContent?.includes("Concept validation study"));
    await assertNavLevel("study");
    await assertNoInternalTerms();

    await page.click("#study-nav-evidence");
    await waitForRouteTitle("Evidence workspace");
    await page.waitForSelector("#create-report");
    await page.click("#create-report");
    await page.waitForURL(/\/studio\/studies\/[^/]+\/reports\/[^/]+$/);
    await waitForRouteTitle("Study report");
    await page.waitForSelector("#report-cited-evidence");
    await page.waitForSelector("#report-contradictions");
    await page.waitForSelector("#report-human-gaps");
    await page.waitForFunction(() => document.querySelector("#report-cited-evidence")?.textContent?.includes("Cited attempts"));
    await assertNoInternalTerms();
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Study report");
    await page.waitForSelector("#report-cited-evidence");
    await assertNavLevel("study");
    await assertNoInternalTerms();

    await page.waitForSelector("#create-decision");
    await page.click("#create-decision");
    await page.waitForURL(/\/studio\/studies\/[^/]+\/decisions\/[^/]+$/);
    await waitForRouteTitle("Decision review");
    await page.waitForSelector("#decision-current-belief");
    await page.waitForSelector("#decision-evidence-basis");
    await page.waitForSelector("#decision-confidence-boundary");
    await page.waitForSelector("#decision-human-follow-up");
    await page.waitForFunction(() => document.querySelector("#decision-confidence-boundary")?.textContent?.includes("Market proof"));
    await assertNavLevel("study");
    await assertNoInternalTerms();
    await assertNoHorizontalOverflow(1280);
    await assertNoCriticalOverlap();

    await page.waitForSelector("#create-share:not([disabled])");
    await page.click("#create-share");
    await page.waitForURL(/\/studio\/share\/[^/]+$/);
    await waitForRouteTitle("Share view");
    await page.waitForSelector("#share-decision");
    await page.waitForSelector("#share-evidence-digest");
    await page.waitForSelector("#share-included-artifacts");
    await page.waitForSelector("#share-boundary");
    await page.waitForFunction(() => document.querySelector("#share-boundary")?.textContent?.includes("Synthetic-only signal"));
    await page.waitForFunction(() => document.querySelector("#share-public-link")?.textContent?.includes("/public/v1/share-bundles/"));
    await assertNoInternalTerms();
    await assertNoHorizontalOverflow(1280);
    await assertNoCriticalOverlap();
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Share view");
    await page.waitForSelector("#share-decision");
    await page.waitForSelector("#share-boundary");
    await assertNoInternalTerms();

    await page.goBack({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Decision review");
    await assertNavLevel("study");
    await page.goForward({ waitUntil: "domcontentloaded" });
    await waitForRouteTitle("Share view");
    await assertNoInternalTerms();

    const routeChecks = [
      [`/studio/projects/project_missing`, "Project"],
      [`/studio/studies/${studyId}`, "Concept validation study"],
      [`/studio/studies/${studyId}/runs`, "Research attempts"],
      [`/studio/studies/${studyId}/runs/run_missing`, "Research attempt"],
      [`/studio/studies/${studyId}/evidence-views/view_missing`, "Saved evidence view"],
      [`/studio/studies/${studyId}/reports/report_missing`, "Study report"],
      [`/studio/studies/${studyId}/decisions/decision_missing`, "Decision review"],
      [`/studio/share`, "Share"],
      [`/studio/share/share_missing`, "Share view"],
    ];
    for (const [routePath, expectedTitle] of routeChecks) {
      console.log(`Checking route ${routePath}`);
      await page.goto(`${apiBaseUrl}${routePath}`, { waitUntil: "domcontentloaded" });
      await waitForRouteTitle(expectedTitle);
      await assertNoInternalTerms();
      await assertNoHorizontalOverflow(1280);
      await assertNoCriticalOverlap();
    }

    const layout = await page.evaluate(() => ({
      title: document.title,
      routeKind: window.__FRONTLINE_ROUTE_CONTEXT__?.route_kind,
      hasHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      selectedStudy: document.querySelector("#selected-study")?.textContent || "",
      planRevision: document.querySelector("#plan-revision")?.textContent || "",
      routeTitle: document.querySelector("#route-title")?.textContent || "",
      hasCitedEvidence: Boolean(document.querySelector("#report-cited-evidence")),
    }));
    if (layout.hasHorizontalOverflow) {
      throw new Error("Frontline Studio has horizontal overflow at 1280px viewport.");
    }
    await page.screenshot({ path: path.join(artifactDir, "frontline-studio.png"), fullPage: true });
    const summary = {
      status: "passed",
      apiBaseUrl,
      artifactDir,
      layout,
      workerOutput,
      boundary: "Browser smoke verifies the /studio frontline path through completed synthetic evidence review, saved view, study report, decision logging, and boundary-preserving share creation; it does not prove human market validation.",
    };
    await fs.writeFile(path.join(artifactDir, "frontline_studio_smoke.summary.json"), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    server.kill();
    await fs.writeFile(path.join(artifactDir, "server.log"), serverLog);
  }
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
