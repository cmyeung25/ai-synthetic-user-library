import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

function fail(message) {
  process.stderr.write(String(message));
  process.exit(1);
}

function readJsonFromStdin() {
  return new Promise((resolve, reject) => {
    let raw = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      raw += chunk;
    });
    process.stdin.on("end", () => {
      try {
        resolve(JSON.parse(raw || "{}"));
      } catch (error) {
        reject(error);
      }
    });
  });
}

function buildLocalCodexConfig(workspaceRoot, model, reasoningEffort) {
  const projectKey = String(workspaceRoot || "").toLowerCase();
  return [
    `model = "${model}"`,
    `model_reasoning_effort = "${reasoningEffort}"`,
    'approval_policy = "never"',
    'sandbox_mode = "workspace-write"',
    "",
    "[windows]",
    'sandbox = "elevated"',
    "",
    `[projects.'${projectKey}']`,
    'trust_level = "trusted"',
    "",
    "[sandbox_workspace_write]",
    "network_access = true",
    `writable_roots = ['${String(workspaceRoot || "").replaceAll("\\", "\\\\")}']`,
    "",
  ].join("\n");
}

async function ensureCodexHome(workspaceRoot, authFile, model, reasoningEffort) {
  const localHome = path.join(workspaceRoot, ".codex-sdk-home");
  await fs.promises.mkdir(localHome, { recursive: true });

  const seedAuthFile = authFile && fs.existsSync(authFile)
    ? authFile
    : path.join(process.env.USERPROFILE || os.homedir(), ".codex", "auth.json");
  if (!fs.existsSync(seedAuthFile)) {
    throw new Error(`Codex auth file not found: ${seedAuthFile}`);
  }

  await fs.promises.copyFile(seedAuthFile, path.join(localHome, "auth.json"));
  await fs.promises.writeFile(
    path.join(localHome, "config.toml"),
    buildLocalCodexConfig(workspaceRoot, model, reasoningEffort),
    "utf8",
  );
  process.env.CODEX_HOME = localHome;
  return localHome;
}

function resolveCodexSdkModule(workspaceRoot, explicitModulePath) {
  const candidates = [];
  if (explicitModulePath) {
    candidates.push(explicitModulePath);
  }
  candidates.push(
    path.join(workspaceRoot, "node_modules", "@openai", "codex-sdk", "dist", "index.js"),
  );

  const workspaceParent = path.resolve(workspaceRoot, "..");
  try {
    const siblingEntries = fs.readdirSync(workspaceParent, { withFileTypes: true });
    for (const entry of siblingEntries) {
      if (!entry.isDirectory()) continue;
      candidates.push(
        path.join(
          workspaceParent,
          entry.name,
          "family-os-telegram-bot",
          "node_modules",
          "@openai",
          "codex-sdk",
          "dist",
          "index.js",
        ),
      );
    }
  } catch {
    // Ignore sibling scan failures and fall through to the collected candidates.
  }

  const seen = new Set();
  for (const candidate of candidates) {
    const normalized = path.resolve(candidate);
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    if (fs.existsSync(normalized)) {
      return normalized;
    }
  }

  throw new Error(
    "Could not find @openai/codex-sdk. Set AI_VALIDATION_CODEX_SDK_MODULE to a local dist/index.js path.",
  );
}

async function runStructuredTurn({ workspace, system_prompt, user_prompt, output_schema, model, model_reasoning_effort, codex_auth_file, codex_sdk_module_path }) {
  const emit = (event) => process.stderr.write(`${JSON.stringify({ ts: new Date().toISOString(), ...event })}\n`);
  const workspaceRoot = path.resolve(workspace || ".");
  emit({ type: "transport.started", workspace: workspaceRoot, model, model_reasoning_effort });
  await ensureCodexHome(
    workspaceRoot,
    codex_auth_file,
    String(model || "gpt-5.4"),
    String(model_reasoning_effort || "medium"),
  );

  const sdkModulePath = resolveCodexSdkModule(workspaceRoot, codex_sdk_module_path);
  emit({ type: "sdk.resolved", sdk_module_path: sdkModulePath });
  const { Codex } = await import(pathToFileURL(sdkModulePath).href);
  const codex = new Codex();
  const thread = codex.startThread({
    workingDirectory: workspaceRoot,
    skipGitRepoCheck: true,
    sandboxMode: "workspace-write",
    approvalPolicy: "never",
    networkAccessEnabled: true,
    webSearchMode: "disabled",
    modelReasoningEffort: String(model_reasoning_effort || "medium"),
    model: String(model || "gpt-5.4"),
  });

  const prompt = [
    String(system_prompt || "").trim(),
    "",
    String(user_prompt || "").trim(),
  ].join("\n");

  const runOptions = output_schema ? { outputSchema: output_schema } : {};
  const { events } = await thread.runStreamed(prompt, runOptions);
  emit({ type: "turn.started" });

  let finalResponse = "";
  let usage = null;
  for await (const event of events) {
    if (["thread.started", "turn.started", "turn.completed", "turn.failed", "error"].includes(event.type)) {
      emit({ type: "codex.event", event_type: event.type });
    }
    if (event.type === "turn.failed") {
      throw new Error(event.error?.message || "Codex structured turn failed.");
    }
    if (event.type === "error") {
      throw new Error(event.message || "Codex structured stream failed.");
    }
    if (event.type === "turn.completed") {
      usage = event.usage || null;
      continue;
    }
    if (!("item" in event) || !event.item) {
      continue;
    }
    if (event.item.type === "agent_message" && typeof event.item.text === "string") {
      finalResponse = event.item.text;
    }
  }

  emit({ type: "transport.completed", has_final_response: Boolean(finalResponse), usage });

  process.stdout.write(JSON.stringify({
    final_response: finalResponse,
    usage,
    sdk_module_path: sdkModulePath,
  }));
}

try {
  const payload = await readJsonFromStdin();
  await runStructuredTurn(payload);
} catch (error) {
  fail(error instanceof Error ? (error.stack || error.message) : String(error));
}
