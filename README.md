# AI Validation Swarm

AI Validation Swarm is building toward a synthetic-user human behavior simulation platform. The product north star is to replace parts of interview-led user research by simulating behaviorally plausible human decisions, objections, and adoption barriers at scale.

Today, this repository is still local-first and engineering-oriented, but it is no longer no-UI only: it now includes a local authenticated workspace shell that can take research intent, attach prototype artifacts, confirm an inferred plan, submit live validation jobs, and review evidence with replay, cross-run comparison, reliability labels, calibration records, and audit lineage from the same product-facing surface. Milestone 13 is implemented through real-user `New Study`, `Study Workspace`, and `Evidence Review` page components. Milestone 14 is also implemented: browser-observed clickable and live-app event logs can be safety-gated, normalized into `observed-action-trace/v1`, persisted, and synthesized without treating synthetic traces as human proof. Milestone 15 is implemented as a fixture-backed human calibration workflow: human-reviewed outcome signals can be attached to comparable synthetic runs, scored for alignment/divergence, and projected into evidence reliability records while preserving replacement-readiness boundaries. Milestone 17 is now implemented: suites can reference external benchmark definition JSON files, benchmarks can provide reviewer-coded `human_outcomes.review_findings`, prototype-validation traces can be calibrated directly against reviewer-coded human task outcomes, and calibration output now includes benchmark-level plus suite-level readiness projection. Milestone 18 is now implemented: `workflow_mapping` is a real first-class interview mode, and workflow-mapping runs now produce queryable workflow evidence that can persist into saved evidence views and decision logs. Milestone 19 is now implemented: backend-owned `readiness_gate` state carries through evidence review, decision logs, export bundles, and public-share restrictions. Milestone 20 is now implemented with four controlled-launch slices: backend-owned `mvp_launch_scope`, `mvp_promotion`, `partner_onboarding`, and `mvp_release_review` now gate export/share circulation from internal-only evidence through bounded design-partner public delivery. Milestone 21 is now implemented: the SaaS wrapper exposes deployment probes, readiness checks, service metadata, a machine-readable contract manifest, deployment-profile-controlled hosted bootstrap policy, opt-in structured request logs, and an authenticated workspace operations summary without moving research logic into the web layer. Milestone 22 is now implemented: decision logs carry explicit review assignment with assignment-aware approval permission, support snapshots carry durable handoff state and history, export/share circulation keeps append-only governance history, workspace billing/quota/retention mutations keep append-only governance history, and those governance transitions stay visible through study activity or workspace audit instead of living only in ad hoc notes. Milestone 23 is now implemented: persona-library summaries expose required human-difference-axis coverage and gap records, the metadata index persists every populated `human_difference_axes.*` trait for later explainable panel composition, human calibration artifacts attach heuristic miss attribution across persona coverage, facilitator behavior, stimulus interpretation, and synthesis/ranking, and panel sampling/report artifacts project backend-owned covered-vs-under-covered axes, similarity hotspots, and per-persona inclusion rationale instead of leaving panel composition implicit. Milestone 24 is now implemented: workspace evidence review carries repeated-study comparison across same-study runs, same-project neighboring studies, study-timeline evidence/decision artifacts, attached calibration lineage, recurring signal synthesis for objections, trust gaps, failure patterns, contradiction patterns, and panel-learning/decision-trend projection from report-level panel explainability and durable decision history instead of page-local reconstruction. Milestone 25 is now complete: studies are classified into backend-owned `regulated_review_boundary` state, regulated/high-stakes studies are blocked from execution until explicit governed acknowledgement is attached, study-level governed reviewer assignment now persists as backend-owned `governed_review` state, study-level viewer-safe redaction now persists as backend-owned `governed_redaction` state, partner-facing share creation stays blocked until both reviewer responsibility and active redaction exist, and export/share/support surfaces now materialize `compliance_audit_bundle.json` so classification, reviewer, redaction, circulation, and audit reconstruction remain inspectable without raw filesystem forensics. Milestone 26 is now complete: the runtime exposes one backend-owned `workspace_public_launch_readiness` summary with per-artifact `public_claims_boundary`, aggregated `launch_blockers`, `customer_operations_support_boundary`, and `self_serve_onboarding_pricing_boundary`, so benchmark disclosure, support posture, onboarding/pricing readiness, and customer-facing claim limits stay attached to workspace operations, export bundles, share bundles, and public-share payloads. Milestone 27 is now implemented: the normal frontend path can run the local personal MVP through live Codex-backed synthetic research for founder concept validation, UI/prototype comprehension validation with artifact handling, and pain/empathy/insight discovery inferred into `pain_point_discovery`, with provider-runtime boundary, saved evidence views, decision logs, share/support continuation, and responsive layout acceptance verified. Milestones 37-42 are now implemented: Frontline run detail exposes run progress, bounded run event stream, transcript, and trace provenance; messaging validation can be inferred from user intent; guided research playbooks and rerun templates preserve comparison-ready lineage; calibration health is visible through a backend-owned observatory; privacy/export controls expose retention, deletion request, redaction, data-residency, export/share, audit, and readiness boundaries; and integration events now preserve readiness, provenance, privacy/export controls, delivery audit, and simulated-evidence boundaries. Frontline Research Studio now supports deterministic English product chrome plus explicit Traditional Chinese (`zh-Hant`) for the user-facing IA, setup, persona selection, plan confirmation, run/evidence/report/decision/share route chrome, action feedback, loading/empty states, and boundary copy; generated evidence and backend artifacts remain in their original language. This is ready for local solo-user operation only; outputs remain simulated evidence, not human market proof.

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
- fixture-backed human calibration suite with prediction-alignment scoring and replacement-readiness boundary output
- first external benchmark-definition suite contract for human calibration through suite-level `benchmark_path` references
- reviewer-coded `human_outcomes.review_findings` mapping for human calibration benchmarks
- browser-trace task-failure, abandonment, and bounded trust-gap extraction for prototype-validation calibration
- benchmark-level and suite-level external readiness projection for human calibration
- first-class `workflow_mapping` discovery interview mode with runtime coverage and closure gates
- structured `workflow_map` evidence projection for workflow-mapping interviews, plus workflow-aware evidence-query and saved-review linkage
- Frontline run progress, transcript, facilitator trace, synthetic participant reasoning trace, and source-linked evidence provenance through route-safe APIs and UI panels
- Frontline messaging and positioning validation inference with message-specific evidence boundaries
- Frontline guided research playbooks, rerun plan proposals, and comparison-ready source-run lineage
- continuous calibration observatory with readiness-blocker projection for launch claims
- workspace privacy/export controls for retention, deletion requests, redaction, data residency, exports, shares, audit, and readiness boundaries
- bounded Frontline run event stream and workspace integration events with delivery-attempt audit, transcript/trace provenance, readiness gates, and privacy/export controls
- backend-owned `readiness_gate` status for evidence review, decision logs, export bundles, and share bundles
- backend-owned `mvp_launch_scope` status for export/share launch packaging, including `internal_only`, `blocked`, and `design_partner_candidate` circulation classes
- backend-owned `mvp_promotion` approval workflow for export bundles, including request/review state and design-partner share gating
- backend-owned `partner_onboarding` packs for approved design-partner shares, including named partner context, bounded circulation policy, acknowledgements, and support guidance
- backend-owned `mvp_release_review` approval workflow for the actual share artifact before partner-facing public delivery
- multi-turn local conversation sessions with synthetic personas
- SaaS-readiness contracts, tenant schemas, and market-distribution configs
- Workspace UI low-fi prototype, Moss stage-2 intake prototype, Moss stage-3 inference prototype, Moss stage-4 confirmation prototype, Moss stage-5 blocked-draft remediation prototype, Moss stage-6 converged single-page flow, Moss stage-7 state-machine adapter prototype with EN / Traditional Chinese review, Moss stage-8 queue and run status monitor prototype, Moss stage-9 evidence browser and replay prototype, Moss stage-10 metadata-backed evidence query and replay prototype, Moss stage-11 integrated operator-shell prototype, Moss stage-12 validation-job, session, and evidence-query runtime bridge prototype, Moss stage-13 product-facing workspace shell prototype, Moss stage-14 backend-driven workspace shell prototype with editable intake, real prototype-file selection state, collapsed advanced study controls, artifact-derived replay focus, backend-owned replay/comparison context, initial cross-run comparison guidance, and coverage/replay/comparison review cards, a repo-local engineering-demo launcher that boots Stage 14 after authenticated API readiness and resets the demo workspace before each run, a shared executable workspace UI adapter, run-monitor, evidence-browser, evidence-query, and integrated-shell module plus dedicated validation-job and session runtime bridge modules, a shared shell runtime client for live session/job/evidence-query/workspace-shell orchestration, a shared shell runtime sync module for heartbeat and optional auto-refresh, a shared shell app controller module for frontend orchestration and draft mutation, a page-level shell frontend adapter module with Node contract tests and a stable review-surface projection, a draft workspace research plan contract spec, a dedicated workspace UI adapter contract spec, a draft workspace evidence query contract spec, a draft workspace validation-job bridge contract spec, a draft workspace session runtime contract spec, a draft workspace shell frontend adapter contract spec, a draft workspace shell app contract spec, a draft workspace shell snapshot contract spec, and reusable design-system CSS foundation with Moss, Slate, and Ink theme variants for the planned workspace console
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

See [specs/persona_library_storage_and_saas_contract.md](./specs/persona_library_storage_and_saas_contract.md) for the accepted `artifact-first, SQL-indexed, object-store-ready` persona-library storage rule for local development and future SaaS/cloud deployment.
See [specs/frontline_research_studio_i18n_contract.md](./specs/frontline_research_studio_i18n_contract.md) for the Frontline Studio English / `zh-Hant` product-chrome i18n boundary and the rule that generated evidence remains original-language content unless a future evidence-translation contract is added. See [specs/frontline_research_studio_bilingual_terminology_glossary.md](./specs/frontline_research_studio_bilingual_terminology_glossary.md) for the canonical user-facing terminology: `專案`, `研究`, `研究計劃`, `研究執行`, `證據`, `決策`, and `合成受訪者` should be used instead of mixed Chinese/English platform labels.

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
- `run-human-calibration`
- `bootstrap-saas-workspace`
- `serve-saas-api`
- `run-saas-worker`
- `purge-saas-expired-artifacts`
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

For `--stimulus-type live_app`, `--stimulus-artifact` accepts either a JSON observed action trace artifact supplied by the application layer or a browser behavior trace artifact with browser session metadata and event logs. Browser behavior traces are blocked before synthesis when they indicate credentialed, high-stakes, destructive, payment, token, transfer, or non-local/non-allowed-origin execution.

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

The facilitator and persona use separate LLM sessions. The facilitator cannot read hidden persona artifacts and chooses its interview phase, probing method, next question, evidence updates, root-cause hypotheses, and stopping point from the transcript. Hypothesis validation explicitly seeks supporting, contradicting, and alternative evidence and returns `not_tested`, `unsupported`, `mixed`, or `provisionally_supported`; it never claims confirmation from synthetic evidence. The current `prototype_validation` mode now supports static image review, multi-screen flow review, scripted clickable task execution, application-supplied observed action traces, and browser-observed clickable/live-app traces with an explicit evidence boundary. Outputs are stored under `interviews/{interview_id}/`, including `transcript.md`, `facilitator_trace.json`, `insights.md`, `persona_driver_trace.md`, and, for prototype runs, `stimulus_analysis.json` and/or `observed_action_trace.json` plus snapshotted copies of the reviewed assets. Current outputs should still be treated as synthetic evidence, not human market proof, while the platform is being calibrated toward replacement-grade reliability.

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

The local runtime stores workspace, billing, API token, validation-job lifecycle state, export bundles, share bundles, and audit events in `saas_runtime/saas_runtime.sqlite3`, keeps run artifacts under `saas_runtime/workspaces/{workspace_id}/runs/`, and exposes:

- `POST /api/v1/validation-jobs`
- `GET /api/v1/validation-jobs`
- `GET /api/v1/validation-jobs/{job_id}`
- `POST /api/v1/validation-jobs/{job_id}/cancel`
- `POST /api/v1/validation-jobs/{job_id}/retry`
- `GET /api/v1/session`
- `GET /api/v1/workspace-settings`
- `GET /api/v1/audit-events`
- `GET /api/v1/persona-library`
- `POST /api/v1/persona-library/generation-jobs`
- `GET /api/v1/public-launch-readiness`
- `POST /api/v1/workspace-billing`
- `POST /api/v1/workspace-members`
- `POST /api/v1/api-tokens`
- `POST /api/v1/api-tokens/{token_id}/revoke`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/studies`
- `GET /api/v1/studies`
- `GET /api/v1/studies/{study_id}`
- `POST /api/v1/export-bundles`
- `GET /api/v1/export-bundles`
- `GET /api/v1/export-bundles/{export_bundle_id}`
- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request`
- `POST /api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review`
- `POST /api/v1/share-bundles`
- `GET /api/v1/share-bundles`
- `GET /api/v1/share-bundles/{share_bundle_id}`
- `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review-request`
- `POST /api/v1/share-bundles/{share_bundle_id}/mvp-release-review`
- `POST /api/v1/share-bundles/{share_bundle_id}/revoke`
- `GET /public/v1/share-bundles/{share_key}`
- `GET /api/v1/support-diagnostics`
- `POST /api/v1/support-snapshots`
- `GET /api/v1/support-snapshots`
- `GET /api/v1/support-snapshots/{support_snapshot_id}`
- `POST /api/v1/support-snapshots/{support_snapshot_id}/handoff`
- `POST /api/v1/evidence-views`
- `GET /api/v1/evidence-views`
- `GET /api/v1/evidence-views/{evidence_view_id}`
- `POST /api/v1/decision-logs`
- `GET /api/v1/decision-logs`
- `GET /api/v1/decision-logs/{decision_log_id}`
- `POST /api/v1/decision-logs/{decision_log_id}/review-assignment`
- `GET /api/v1/evidence-query`
- `GET /api/v1/workspace-shell`

This surface is still local-first and engineering-oriented, but it means authenticated workspace session loading, workspace settings governance, visible workspace audit history, writable billing/quota controls, project/study product objects, a study-scoped activity timeline, durable saved evidence views, durable decision logs, explicit decision review assignment, assignment-aware approval permission, durable support handoff history, append-only export/share governance history, append-only billing/quota/retention governance history, API ingress, queued job execution, workspace isolation, billing gates, plan limits, retention purge, and token lifecycle controls now exist as real repository behavior rather than design-only contracts.

The local SaaS wrapper now also exposes a same-origin study-first operator shell entrypoint at `GET /app/workspace`, which directly renders the hosted Stage 15 product shell from the same local runtime instead of requiring a separate static file server.

That hosted Stage 15 shell now mounts through `demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs`, so the first Milestone 11 product shell no longer depends on one large inline HTML module for route bootstrap and product-surface event orchestration.

The same hosted shell is now route-aware for:

- `GET /app/workspace`
- `GET /app/new-study`
- `GET /app/projects/{project_id}`
- `GET /app/studies/{study_id}`
- `GET /app/evidence-views/{evidence_view_id}`
- `GET /app/decision-logs/{decision_log_id}`
- `GET /app/export-bundles/{export_bundle_id}`
- `GET /app/share-bundles/{share_bundle_id}`
- `GET /app/support-snapshots/{support_snapshot_id}`
- `GET /app/jobs/{job_id}`

The server injects route context, and the shared shell controller bootstraps the selected product object from the corresponding detail endpoint so deep links stay inside the same study-first shell.

The local SaaS wrapper now prefers a framework-owned frontend host build under `frontend/workspace_shell_app/dist/` for those `/app/*` routes. That host preserves the same Stage 15 controller, route bootstrap, and study-first product behavior while moving app entry ownership out of one prototype HTML file. It now owns the Milestone 13 real-user page components for `New Study`, `Study Workspace`, and `Evidence Review`, renders the research workflow before settings/support/debug surfaces, and maps backend route context to the active M13 page. This remains the operator / engineering shell rather than the final Frontline Research Studio. Use `scripts\build_workspace_shell_app.bat` to install dependencies when needed and rebuild that hosted frontend entrypoint.

Milestones 28-30 now implement the Frontline Research Studio boundary: the real user-facing Studio lives as a separate package under `frontend/frontline_research_studio` and is served from `/studio`, while `frontend/workspace_shell_app` remains the operator shell for provider, job, runtime, evidence-contract, support, export, and governance inspection. Both surfaces share the same SaaS runtime, session/auth, project/study/run/evidence contracts, Codex-backed worker, and synthetic-evidence boundaries.

The Frontline Studio now supports the first study-first user path: create/select project and study context, create a frontline `PlanProposal`, explicitly confirm it into an approved plan, start a plan-linked synthetic research run from the user-facing Studio, and create durable study-level reports through `/api/v1/study-reports`. Study reports persist included run IDs, plan revision IDs, stable patterns, divergent signals, objections, trust gaps, adoption barriers, prototype confusions, contradictions, and human-validation gaps, and decision logs can carry the report and plan lineage as durable judgment context.

Milestone 31 is now implemented: `/studio` is route-aware rather than one long page. The SaaS wrapper injects Frontline route context for workspace, projects, project detail, new study, study home, study setup, study runs, run detail, evidence workspace, saved evidence view, study report, decision review, share collection, and share view contexts. The React shell renders route-specific pages with one primary product object, clear loading/empty states, and dominant CTAs.

The `/studio` left navigation is now reserved for Frontline product IA without flattening study-owned objects into Level 1. The rail uses a drill-down model: the Projects level shows the project list, the Project level replaces that list with project-specific study navigation plus a back button, and the Study level replaces it with study-specific setup/runs/evidence/report/decision/share navigation plus a back button to the parent project. The rail is fixed on desktop and keeps workspace/account identity anchored at the bottom. The research loop `Ask -> Clarify -> Confirm Plan -> Run -> Review Evidence -> Compare -> Decide` belongs inside `Research Copilot / Guided Setup` as study-local progress, not as the global navigation model.

Milestone 32 is now implemented: `/studio/studies/new` and `/studio/studies/{study_id}/setup` let a user describe research intent, save a study draft, tune target-audience criteria, choose synthetic participants from a serious persona-library picker, review the inferred plan, explicitly approve the plan, and start the first research run from the Frontline Studio surface. The backend exposes `GET /api/v1/persona-library` plus `POST /api/v1/studies/{study_id}/frontline-runs` so the frontend can show panel coverage and start a plan-linked run without showing provider, job, mode override, or raw runtime controls by default, while backend metadata still preserves project, study, approved-plan, selected-persona, and target-audience lineage for audit.

Milestone 33 is now implemented: the Frontline Studio can open a completed research attempt, hydrate backend-owned evidence-query payloads into source evidence, interpretation, summary boundary, contradiction, comparison, and human-validation-gap panels, save a provenance-preserving evidence view, reload that view by URL, create a study report, and reopen the report with cited evidence, stable/divergent signals, contradictions, and human-validation gaps visible. This remains simulated evidence, not human market proof.

Milestone 34 is now implemented: the Frontline Studio can create a decision from the study report or saved evidence context, reopen `/studio/studies/{study_id}/decisions/{decision_log_id}` with current belief, evidence basis, confidence boundary, and human follow-up visible, then create and reopen `/studio/share/{share_bundle_id}` with linked decision context, evidence digest, included viewer-safe artifacts, public boundary link, and synthetic-evidence limits visible. This still does not convert synthetic evidence into human market proof.

Milestone 35 is now implemented: the Frontline persona library exposes explicit readiness states, coverage gaps, generation job history, and simulated-lens boundaries through `GET /api/v1/persona-library`; the product can create auditable gap-fill jobs through `POST /api/v1/persona-library/generation-jobs`; zero-persona plan approval is blocked; selected persona IDs, versions, artifact hashes, coverage snapshots, and provisional status are preserved through approved plans, run metadata, and `frontline_persona_panel_snapshot.json`. Public-figure, celebrity, expert, and influencer-inspired simulated lenses remain separate from normal participant evidence and are not presented as real-person views or endorsements.

Milestone 36 is now implemented: the Frontline personal-MVP loop is verified from project and study setup through persona selection, plan approval, run execution, evidence review, saved evidence view, study report, decision log, and boundary-preserving share view. The `/studio` product chrome now has deterministic English plus explicit Traditional Chinese (`zh-Hant`) terminology for durable product objects and workflow labels, while generated evidence, transcripts, findings, persona artifacts, backend JSON artifacts, and audit records remain in their original language.

Milestones 37-42 are now implemented: `/studio/studies/{study_id}/runs/{run_id}` shows run progress, bounded interview event stream, transcript, and trace provenance; evidence views, reports, and decisions can retain source exchange and trace references; messaging validation can be inferred from natural-language positioning/copy intent; guided playbooks and rerun templates create comparison-ready plan proposals; the workspace shows a calibration observatory that also feeds public-launch readiness blockers; privacy/export controls expose retention, deletion request, redaction, data-residency, export/share, audit, and readiness boundaries; and workspace integration events expose boundary-preserving study, run, evidence, decision, readiness, support, and delivery-attempt state.

The detailed Frontline Studio UX/component guide is recorded in `specs/frontline_research_studio_ux_component_design_spec.md`. It defines the route-level screens, component hierarchy, CTA placement, user job-to-be-done, UX rationale, and audit criteria for keeping `/studio` external-user-facing rather than milestone, roadmap, provider, job, runtime, or debug oriented.

Run `node scripts\\verify_frontline_studio_smoke.mjs` to execute the browser smoke for `/studio`. The smoke starts an isolated temporary SaaS runtime, bootstraps a browser session, creates a study, uses the persona-library picker plus target-audience and moderator-guide fields, proposes a plan, confirms an approved plan, starts and processes a plan-linked research run, opens run monitor, run event stream, transcript, trace, evidence review, saved evidence view, study report, decision, and share routes, verifies the workspace connected-events card, drill-down nav-level exclusivity, route navigation, refresh persistence, browser back/forward, 1024px and 1280px horizontal overflow, critical panel overlap, visible-copy guards, and `zh-Hant` terminology checks, then writes artifacts under `output/playwright/frontline_studio_smoke/`.

Run `scripts\\start_local_workspace_demo.bat` to launch the local workspace engineering demo. The launcher resets only the local `ws_api_demo` workspace before boot so repeated demo sessions do not get blocked by retained trial quota state.
Set `NO_OPEN_BROWSER=1` when another script should bootstrap the demo without spawning a visible browser window.

For the current operator-shell product slice, open `http://127.0.0.1:8011/app/workspace?token=token-api` or `http://127.0.0.1:8011/app/new-study?token=token-api` after the demo boot script starts the API. That first authenticated hit now exchanges the bootstrap token for a server-backed same-origin browser session, so the same browser can revisit clean `/app/*` routes and call the hosted API without repeating the token query. Explicit query tokens still override the current browser session when you need to re-bootstrap, and the shell exposes an `end browser session` action when you need to clear it. That hosted shell lifts the shared shell into a study-first operator surface where project selection, study selection, conversational intake, explicit plan confirmation, run submission, evidence refresh, reliability review, calibration records, audit lineage, study activity timeline, saved evidence views, decision logs, in-place decision review comments, explicit reviewer assignment, assignment-aware approval state, export-bundle creation, viewer-safe share-bundle creation, promotion/release governance history, blocked-submission diagnostics, queued/running support visibility, recent failure digest, failed-run explanation, queued-job cancel, failed/canceled retry, support-snapshot generation, support handoff assignment and resolution history, and secondary workspace settings actions for membership, audit-history review, billing/quota updates, plus API-token lifecycle all operate inside one visible product context. Once product objects exist, the same flow can also be opened through route-aware deep links such as `/app/studies/{study_id}`, `/app/jobs/{job_id}`, `/app/evidence-views/{evidence_view_id}`, `/app/decision-logs/{decision_log_id}`, or `/app/export-bundles/{export_bundle_id}`.
Run `node scripts/verify_stage15_hosted_shell_smoke.mjs` to execute the hosted-shell browser smoke flow and write the screenshot plus JSON summary under `output/playwright/stage15_hosted_shell_smoke/`. The smoke now also verifies clean job deep-link hydration and Milestone 12 layout acceptance for blocked primary actions and critical panel overlap.

## Bundled Python runtime

If your system Python is unavailable, this workspace already has a bundled Python runtime that can run the project and tests.

## Safety note

All reports must include this disclaimer:

> This result is synthetic research evidence only. It is not yet a substitute for real user interviews, market tests, professional advice, or compliance review.
