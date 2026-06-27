# AI Validation Swarm

AI Validation Swarm is building toward a synthetic-user human behavior simulation platform. The product north star is to replace parts of interview-led user research by simulating behaviorally plausible human decisions, objections, and adoption barriers at scale.

Today, this repository still operates as a local, no-UI validation engine for testing founder assumptions against a library of structured synthetic users while that replacement-grade capability is being built and calibrated.

This repository currently contains:

- Milestone 0 architecture documents
- Milestone 1 project skeleton
- local persona generation
- optional Agnes-backed persona enrichment and persona judging
- deterministic panel sampling
- offline validation flow using a mock provider
- Markdown, JSON, and CSV report export
- canonical `report.json` artifacts and run archive indexing
- fixture-driven evaluation harness with regression comparison
- multi-turn local conversation sessions with synthetic personas
- SaaS-readiness contracts, tenant schemas, and market-distribution configs
- basic tests

## North Star

The repository-wide working agreement lives in [AGENTS.md](/C:/Users/user/OneDrive/%E6%96%87%E4%BB%B6/AI%20Synthetic%20User%20Library/AGENTS.md).

- Positioning: `human behavior simulation platform`
- Long-term goal: replace parts of traditional user research workflows that depend on human interviews
- Initial target stages: `discovery`, `concept evaluation`, `prototype validation`
- Core belief: synthetic users are valuable only if they can generate behaviorally plausible responses that help predict real human behavior

See [PRODUCT_BRIEF.md](/C:/Users/user/OneDrive/%E6%96%87%E4%BB%B6/AI%20Synthetic%20User%20Library/PRODUCT_BRIEF.md) for the locked positioning and platform vision.
See [PLATFORM_BLUEPRINT.md](/C:/Users/user/OneDrive/%E6%96%87%E4%BB%B6/AI%20Synthetic%20User%20Library/PLATFORM_BLUEPRINT.md) for the higher-level capability blueprint that separates the simulation core, interview modes, stimulus layer, orchestration layer, and SaaS surface.

## Current Scope

This repository is not yet a market-proof engine. In its current stage it is an AI validation and calibration system designed to surface:

- concept blind spots
- trust and pricing objections
- segment differences
- sensitive-topic risks
- next-step real-world validation questions

See [PERSONA_MODELING_GUIDE.md](/C:/Users/user/OneDrive/文件/AI Synthetic User Library/PERSONA_MODELING_GUIDE.md) for what belongs in reusable persona core versus concept-specific sidecar outputs.
See [PERSONA_GENERATION_PRINCIPLES_FOR_REALISTIC_INTERVIEWS.md](/C:/Users/user/OneDrive/文件/AI Synthetic User Library/PERSONA_GENERATION_PRINCIPLES_FOR_REALISTIC_INTERVIEWS.md) for the platform-level rule that personas should remain people first, with pain discovered at interview time rather than pre-encoded around the concept.

## Commands

The CLI exposes these commands:

- `generate-personas`
- `list-personas`
- `sample-panel`
- `validate-personas`
- `summarize-personas`
- `inspect-openai-auth`
- `probe-codex-auth`
- `enrich-personas`
- `generate-v3-2-persona`
- `generate-v5-persona`
- `generate-v5-panel` (legacy project-specific preset path)
- `validate-personas-v3-2`
- `validate-personas-v5`
- `validate-brief`
- `run-validation`
- `audit-report`
- `export-report`
- `run-evaluation`
- `compare-evaluations`

## Persona generation backends

`generate-personas` supports four modes:

- `template`: deterministic seeded generation only
- `openai`: deterministic seeded generation plus LLM enrichment
- `agnes`: deterministic seeded generation plus Agnes OpenAI-compatible enrichment
- `codex`: deterministic seeded generation plus Codex-authenticated LLM enrichment

You can also add `--judge-personas` to run an LLM plausibility and stereotype-risk pass after generation.

### V3.2 direct persona synthesis

`generate-v3-2-persona` is the forward generation path for new personas. It samples only fixed coherence constraints in code, then asks the configured LLM adapter to author the biography, behaviour, economics, product reactions, local grounding, sensitive scenarios, voice, and lifestyle sections directly. It does not run the V1 to V3.1.2 upgrade chain.

V3.2 sections are declared in `personas/v3_2_sections.py`. The default registry includes `lifestyle_and_hobbies`, with structured interests, media habits, routines, social influence, taste, environment, emotional regulation, and hidden habits. Future sections can target either a typed profile field or `extensions.<name>` without changing the synthesis pipeline.

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m ai_validation_swarm.cli.main generate-v3-2-persona `
  --persona-id su_0031 `
  --backend agnes `
  --seed-offset 11 `
  --output-dir data/personas

& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m ai_validation_swarm.cli.main validate-personas-v3-2 `
  --data-dir data/personas
```

The V3.2 production command requires a live backend such as `agnes`, `codex`, `codex-sdk`, or `openai`; deterministic adapters are reserved for tests. Each output records provider, model, prompts, seed, attempt count, input hash, section hash, and section ownership in `generation_notes.json` and `section_manifest.json`. Similarity is written as `duplicate_report.json` for reporting and panel composition, not used to force every persona to be different.

Use `--backend codex-sdk` to reuse Codex Auth through a locally installed `@openai/codex-sdk` when the Codex CLI websocket transport is unavailable. Set `AI_VALIDATION_CODEX_SDK_MODULE` when the SDK is not installed under the workspace or the known sibling project path.

### V5 direct persona synthesis

`generate-v5-persona` keeps one reusable core persona profile and can optionally require domain-specific profile sections such as `banking_context`. It now treats `human_difference_axes` as first-class persona core so domain reactions can be inferred later instead of being pre-encoded into the person. Concept-specific reactions are written as sidecar `concept_outputs.json` artifacts instead of polluting the reusable profile.

Current V5 panel direction is:

- generate reusable V5 personas
- run interviews against selected V5 personas from the pool
- avoid treating fixed concept-shaped archetype sets as the default panel mechanism

`generate-v5-panel` remains only as a legacy project-specific preset generator for older banking POC artifacts.

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m ai_validation_swarm.cli.main generate-v5-panel `
  --panel-preset hk_retail_bank_portfolio_health_check `
  --starting-id 1201 `
  --backend codex-sdk `
  --output-dir data/personas
```

This legacy preset generates seven Hong Kong banking-investment personas for the `Portfolio Health Check` concept. Each persona stores reusable `human_difference_axes` inside `profile.json`, while concept-specific reactions are stored in `concept_outputs.json`.

Example:

```powershell
$env:PYTHONPATH='src'
$env:AGNES_API_KEY='...'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m ai_validation_swarm.cli.main generate-personas `
  --count 50 `
  --seed 11 `
  --backend agnes `
  --judge-personas `
  --output-dir data/personas
```

Agnes direct example:

```powershell
$env:PYTHONPATH='src'
$env:AGNES_API_KEY='...'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m ai_validation_swarm.cli.main generate-personas `
  --count 10 `
  --seed 11 `
  --backend agnes `
  --output-dir data/personas_agnes
```

Auth note:

- the default credential path for Python-run live API calls is `AGNES_API_KEY`
- explicit `openai` backend flows can still use `OPENAI_API_KEY`
- the code also accepts `CODEX_API_KEY` as a best-effort fallback if your Codex session exposes a compatible bearer token
- the code can also read `C:\Users\user\.codex\auth.json` and reuse the local ChatGPT/Codex access token for explicit Codex-backed paths
- the `codex` backend does not use the official `/v1/responses` API; it runs `codex exec` non-interactively with ChatGPT/Codex auth
- if `AGNES_API_KEY` is missing, the Agnes-backed Python API path will fail fast with a clear error

Transport note:

- on Windows, the Agnes-backed Python client defaults to `powershell_webrequest`
- override with `AI_VALIDATION_LLM_TRANSPORT=node_https` or `python_urllib` only if that transport is known-good in your environment
- Agnes transport retries default to `AI_VALIDATION_AGNES_TRANSPORT_RETRIES=2` with exponential backoff from `AI_VALIDATION_AGNES_TRANSPORT_RETRY_BACKOFF_SECONDS=2`
- Agnes thinking mode defaults to `AI_VALIDATION_AGNES_ENABLE_THINKING=true`
- repo-level CLI defaults for live backend/model now come from `configs/runtime_defaults.json`
- the checked-in default currently points live runs and persona-enrichment defaults to `codex`
- the `codex` backend defaults to `codex_cli` transport and now runs with:
  - global `CODEX_HOME`
  - `--ignore-user-config`
  - `--ignore-rules`
  - `gpt-5.4` + `high` reasoning effort
  - a higher default request timeout than the direct OpenAI HTTP path
  - automatic fallback to a workspace-local `.codex-cli-home` when the global Codex home is not writable in the current sandbox
- use `probe-codex-auth` to run a minimal Codex-authenticated structured turn before a larger persona generation batch
- `enrich-personas` supports `--workers` for batch throughput and `--limit` now advances past already-resumed outputs instead of getting stuck on the first completed slice
- `enrich-personas` also supports `--target-count` plus `--batch-size` so a Codex enrichment run can keep resuming until the output library reaches a requested valid persona count
- target mode also supports `--max-stall-rounds` so transient Codex timeouts can be retried automatically before the runner gives up
- target mode can skip persona IDs that hit the `--max-persona-failures` threshold, so one flaky record does not block the library from growing toward the requested count
- persona enrichment now sends a compact anchor payload to Codex instead of the full stored profile, which improves batch reliability and keeps the prompt focused on fixed facts plus product-relevant behavioral signals
- override request timeout with `AI_VALIDATION_OPENAI_TIMEOUT_SECONDS` if a live Codex batch still needs more headroom
- Codex CLI requests now automatically retry retryable backend-refresh failures; tune with `AI_VALIDATION_CODEX_CLI_RETRIES` and `AI_VALIDATION_CODEX_CLI_RETRY_BACKOFF_SECONDS` if needed

## Typical local flow

1. Generate a persona library
2. Inspect available personas
3. Sample a panel
4. Run validation against a founder brief
5. Review the archived report and audit output
6. Export a shareable report in Markdown, JSON, or CSV
7. Run the fixture suite to check deterministic quality gates before changing prompts or logic

## Direct persona conversation

Start an offline smoke-test conversation:

```powershell
ai-validation-swarm chat-with-persona --persona-id su_0001 --backend mock
```

Use `--backend agnes`, `--backend codex`, or `--backend openai` when the corresponding live transport is available. Runtime model and reasoning can be selected with `--model MODEL --reasoning-effort medium`. Resume a saved conversation with `--resume SESSION_ID` and the same backend. Sessions are written to `conversations/{session_id}/session.json` and `transcript.md` with prompt, model, intent, and synthetic-only provenance.

## LLM-facilitated problem interview

Run an observed Design Thinking Empathize/Define interview:

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode explore_root_cause `
  --research-goal "Understand the root causes of trip replanning friction" `
  --product-context "A possible trip-planning platform" `
  --backend agnes `
  --model agnes-2.0-flash `
  --reasoning-effort medium `
  --max-turns 6
```

Use `explore_root_cause` to discover possible causes from observed behaviour. To test a specific explanation without asking the participant to agree with it, use:

Use `pain_point_discovery` when you need to establish whether the problem is real, how often it happens, what consequence makes it matter, and what workaround already exists before moving into root-cause analysis:

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode pain_point_discovery `
  --research-goal "Discover whether day-to-day finance tracking is a real recurring problem" `
  --backend agnes
```

Use `decision_reconstruction` when you need to reconstruct one real recent decision, including what evidence was still missing, what pressure existed, what felt defensible versus uncertain, and what actually changed at the end:

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode decision_reconstruction `
  --research-goal "Reconstruct the last real product-scope decision under time pressure" `
  --backend agnes
```

Use `adoption_barrier_validation` when something sounds useful but you need to understand why it still might not enter routine use because of setup, permissions, trust, pricing, reversibility, or workflow burden:

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode adoption_barrier_validation `
  --research-goal "Understand why a useful workflow tool still might not be adopted" `
  --product-context "A research workflow assistant that summarizes evidence and follow-up gaps" `
  --backend agnes
```

Use `prototype_validation` when you have a concrete prototype stimulus and one task, and you need a disciplined prototype-validation contract that separates task-guided self-report from real observed action:

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode prototype_validation `
  --research-goal "Validate whether the prototype supports a concrete review task" `
  --product-context "A workspace that summarizes evidence and links back to source material" `
  --stimulus-type image `
  --stimulus-artifact .\prototype-review-screen-v1.png `
  --prototype-task "Review one recommendation and decide whether to act on it" `
  --backend agnes
```

When `--stimulus-type image` is used, `--stimulus-artifact` must point to a real local image file. The runtime snapshots that file into the interview artifacts and generates a structured static-image review before the interview starts.

For `--stimulus-type flow`, point `--stimulus-artifact` at either:

- a directory of ordered screen images such as `01_start.png`, `02_review.png`, `03_confirm.png`; or
- a JSON manifest with a `screens` list that names each screen path in order.

The runtime snapshots the flow assets and generates a structured multi-screen flow review before the interview starts.

For `--stimulus-type clickable`, `--stimulus-artifact` can point to either:

- a JSON clickable prototype manifest with `screens` plus `task_script`, which the runtime executes through the native stimulus executor before the interview starts; or
- a JSON observed action trace artifact supplied by the prototype or application layer.

For `--stimulus-type live_app`, `--stimulus-artifact` currently accepts a JSON observed action trace artifact supplied by the application layer.

In both cases, the runtime snapshots the JSON, writes `observed_action_trace.json`, and upgrades the prototype evidence boundary to `observed_action_trace` when real actions are present.

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode validate_hypothesis `
  --hypothesis "Travellers recheck changed plans because responsibility for updates is unclear" `
  --research-goal "Test why travellers repeatedly check changed trip arrangements" `
  --backend agnes
```

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode prototype_validation `
  --research-goal "Validate whether the prototype flow supports a concrete review task" `
  --product-context "A workflow that summarizes evidence, lets the user inspect it, and then decide whether to act" `
  --stimulus-type flow `
  --stimulus-artifact .\prototype-flow\ `
  --prototype-task "Review one recommendation and decide whether to act on it" `
  --backend agnes
```

```powershell
ai-validation-swarm run-facilitated-interview `
  --persona-id su_0002 `
  --interview-mode prototype_validation `
  --research-goal "Validate whether the clickable prototype supports a concrete review task" `
  --product-context "A clickable workspace that summarizes evidence, shows source detail, and asks for permission before action" `
  --stimulus-type clickable `
  --stimulus-artifact .\prototype-clickable-manifest.json `
  --prototype-task "Review one recommendation and decide whether to act on it" `
  --backend agnes
```

The facilitator and persona use separate LLM sessions. The facilitator cannot read hidden persona artifacts and chooses its interview phase, probing method, next question, evidence updates, root-cause hypotheses, and stopping point from the transcript. Hypothesis validation explicitly seeks supporting, contradicting, and alternative evidence and returns `not_tested`, `unsupported`, `mixed`, or `provisionally_supported`; it never claims confirmation from synthetic evidence. The current `prototype_validation` mode now supports static image review, multi-screen flow review, scripted clickable task execution, and application-supplied observed action traces with an explicit evidence boundary. Live-app execution is still a later expansion. Outputs are stored under `interviews/{interview_id}/`, including `transcript.md`, `facilitator_trace.json`, `insights.md`, `persona_driver_trace.md`, and, for prototype runs, `stimulus_analysis.json` and/or `observed_action_trace.json` plus snapshotted copies of the reviewed assets. Current outputs should still be treated as synthetic evidence, not human market proof, while the platform is being calibrated toward replacement-grade reliability.

### Observer-controlled interview

Start an interactive observer session:

```powershell
ai-validation-swarm observe-facilitated-interview `
  --persona-id su_0002 `
  --research-goal "Understand the root causes of trip replanning friction" `
  --product-context "A possible trip-planning platform" `
  --backend agnes
```

At each pause, press Enter to approve the proposed question. Use `/steer TEXT` to ask the facilitator LLM to revise its direction, `/deepen TOPIC` to request more evidence, or `/ask QUESTION` to submit a question for neutral review and rewriting by the facilitator. `/ask-exact QUESTION` bypasses that review and is explicitly attributed as a direct observer question. `/pause`, `/retry`, `/status`, `/stop`, and `/quit` control the session. Resume later with `--resume INTERVIEW_ID`. Use `/reevaluate` to rerun only the quality audit, or `/resynthesize` to archive and rebuild both synthesis and quality from the saved transcript after prompt or evidence-gate upgrades.

Observer sessions add `observer_events.json`, `quality_evaluation.json`, `quality_evaluation.md`, and `persona_driver_trace.md`. The independent quality LLM audits leading questions, repetition, mechanical Five Whys, premature causal claims, evidence references, and synthesis overreach.

## SaaS readiness artifacts

- `SAAS_BACKEND_BLUEPRINT.md`
- `MULTI_TENANT_DATA_MODEL.md`
- `PERSONA_CATALOG_GOVERNANCE.md`
- `configs/markets/*.json`
- `schemas/market-distribution.schema.json`
- `schemas/tenant-workspace.schema.json`

## Local SaaS runtime

The repository now includes a local authenticated SaaS-style runtime on top of the same domain pipeline:

- `bootstrap-saas-workspace`
- `serve-saas-api`
- `run-saas-worker`
- `purge-saas-expired-artifacts`

The local runtime stores workspace, billing, API token, and validation-job lifecycle state in `saas_runtime/saas_runtime.sqlite3`, keeps run artifacts under `saas_runtime/workspaces/{workspace_id}/runs/`, and exposes:

- `POST /api/v1/validation-jobs`
- `GET /api/v1/validation-jobs`
- `GET /api/v1/validation-jobs/{job_id}`

This surface is still local-first and engineering-oriented, but it means authenticated API ingress, queued job execution, workspace isolation, billing gates, plan limits, and retention purge now exist as real repository behavior rather than design-only contracts.

## Bundled Python runtime

If your system Python is unavailable, this workspace already has a bundled Python runtime that can run the project and tests.

## Safety note

All reports must include this disclaimer:

> This result is synthetic research evidence only. It is not yet a substitute for real user interviews, market tests, professional advice, or compliance review.
