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
const hostedUrl = `${apiBaseUrl}/app/workspace?token=${encodeURIComponent(apiToken)}`;
const runLabel = new Date().toISOString().replace(/[:.]/g, "-");
const artifactDir = path.join(outputDir, runLabel);

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

async function waitForEnabled(locator, message) {
  await waitFor(async () => (await locator.isVisible()) && !(await locator.isDisabled()), message);
}

async function waitForJobStatus(jobId, expectedStatus) {
  return await waitFor(async () => {
    const payload = await requestJson(`${apiBaseUrl}/api/v1/validation-jobs/${jobId}`, {
      headers: {
        Authorization: `Bearer ${apiToken}`
      }
    });
    log(`Observed job ${jobId} status: ${payload?.job?.status || "unknown"}`);
    return payload?.job?.status === expectedStatus ? payload.job : null;
  }, `Timed out waiting for job ${jobId} to reach status '${expectedStatus}'.`);
}

async function waitForJobCreatedForStudy(studyId) {
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
}

async function waitForStudyCard(page, selector, expectedText, message) {
  return await waitFor(async () => {
    const texts = await page.locator(`${selector} .product-card`).allTextContents();
    return texts.some((text) => text.includes(expectedText)) ? texts : null;
  }, message);
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
  const projectName = `Hosted Shell Smoke ${timestampToken}`;
  const projectSlug = slugify(projectName);
  const studyTitle = `Milestone 11 study ${timestampToken}`;
  const firstTask = "review onboarding guidance";
  const researchIntent = "Validate whether the onboarding shell explains reversibility clearly enough for first-time workspace setup.";
  const desiredOutcome = "Need a concise evidence-backed readout with key hesitation points and trust gaps.";
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

    await page.selectOption("#mode-override", "concept_validation");
    await page.fill("#research-intent", researchIntent);
    await page.fill("#desired-outcome", desiredOutcome);
    await page.fill("#first-task", firstTask);
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

    const chooseFallbackButton = page.getByRole("button", { name: "choose fallback" });
    await waitForEnabled(chooseFallbackButton, "Choose fallback button never became enabled for concept-level study submission.");
    log("Switching the hosted shell into explicit fallback mode...");
    await chooseFallbackButton.click();

    const confirmPlanButton = page.getByRole("button", { name: "confirm plan" });
    await waitForEnabled(confirmPlanButton, "Confirm plan button never became enabled.");
    log("Confirming inferred study plan...");
    await confirmPlanButton.click();

    const submitLiveJobButton = page.locator("#submit-live-job");
    await waitForEnabled(submitLiveJobButton, "Submit live job button never became enabled after plan confirmation.");
    log("Submitting live validation job...");
    await submitLiveJobButton.click();
    const submittedJob = await waitForJobCreatedForStudy(studyId);
    const firstJobId = submittedJob.job_id;
    await waitForJobStatus(firstJobId, "completed");

    log("Reopening the completed job deep link inside the hosted shell...");
    await page.goto(`${apiBaseUrl}/app/jobs/${firstJobId}`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);
    await waitFor(async () => {
      const jobPillText = await page.locator("#job-pill").textContent();
      return String(jobPillText || "").trim() === "completed";
    }, "Completed job route did not hydrate back into the hosted shell.");

    log("Refreshing evidence review surface...");
    await page.click("#apply-evidence-query");
    await waitFor(
      async () => (await page.locator("#evidence-list .product-card").count()) > 0,
      "Evidence results did not appear after reopening the completed job route."
    );

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
      projectName,
      projectSlug,
      studyTitle,
      firstJobId,
      publicShareUrl,
      selectedProjectSummary: await readSummaryRows(page, "#selected-project-summary"),
      selectedStudySummary: await readSummaryRows(page, "#selected-study-summary"),
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
