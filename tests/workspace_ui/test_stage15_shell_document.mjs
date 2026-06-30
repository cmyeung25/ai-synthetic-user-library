import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { extractStage15ShellDocumentParts } from "../../demo/workspace_ui_shared/stage15_shell_document.mjs";

test("extractStage15ShellDocumentParts returns title, styles, and shell markup from the Stage 15 document", async () => {
  const htmlSource = await readFile(
    new URL("../../demo/workspace_ui_moss_stage15/index.html", import.meta.url),
    "utf8"
  );

  const parts = extractStage15ShellDocumentParts(htmlSource);

  assert.equal(parts.title, "Workspace UI Moss Stage 15");
  assert.match(parts.inlineStyles, /\.stage15-shell\s*\{/);
  assert.match(parts.shellMarkup, /id="metric-project"/);
  assert.match(parts.stageGridMarkup, /id="session-pill"/);
  assert.match(parts.firstColumnMarkup, /id="api-base-url"/);
  assert.match(parts.secondColumnMarkup, /id="bridge-pill"/);
  assert.match(parts.secondColumnFirstSectionMarkup, /id="research-intent"/);
  assert.match(parts.secondColumnFirstSectionMarkup, /id="study-actions"/);
  assert.match(parts.secondColumnRemainingMarkup, /id="query-pill"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="query-pill"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="provider-runtime-pill"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="provider-runtime-summary"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="reload-study-activity"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="study-activity-list"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="create-export-bundle"/);
  assert.match(parts.secondColumnSecondSectionMarkup, /id="support-recent-failures"/);
  assert.match(parts.secondColumnTrailingMarkup, /id="last-api-json"/);
  assert.doesNotMatch(parts.secondColumnTrailingMarkup, /id="query-pill"/);
  assert.doesNotMatch(parts.stageGridMarkup, /<aside class="rail">/);
  assert.doesNotMatch(parts.shellMarkup, /<script type="module">/);
});
