# Workspace Shell App Contract

## Purpose

This contract defines the `app-layer boundary` between:

- the shared workspace shell logic
- any future frontend component tree or framework-hosted shell

It exists because Stage 12 proved the runtime bridge, but the page still owned too much orchestration directly.

Stage 13 introduces `demo/workspace_ui_shared/workspace_shell_app.mjs` so the next frontend can bind to one shared shell controller rather than reimplement:

- draft scenario transitions
- session loading
- validation-job submission
- live job selection and refresh
- evidence query loading
- runtime sync heartbeat and auto-refresh

Stage 14 extends that boundary so live shell hydration can flow through one backend `workspace-shell` snapshot instead of a page-local chain of session, job-detail, and evidence-query calls.

## Why this matters now

Research bottleneck improved:

- the platform now has enough runtime surface that frontend duplication itself becomes a delivery bottleneck

Platform value improved:

- scalable research throughput
- evidence discipline through one shared runtime path
- cleaner promotion path from engineering demo to real shell

This is not only UI polish. It is a boundary hardening step that reduces drift between prototype pages and future hosted shell behavior.

## Module

- `demo/workspace_ui_shared/workspace_shell_app.mjs`

## Primary exports

### `createWorkspaceShellAppState()`

Returns the default shell app state for:

- local draft shell state
- sample jobs
- live runtime state
- session state
- runtime sync state

### `deriveWorkspaceShellAppModel(input)`

Pure derivation layer that returns one composite model for rendering.

Expected inputs:

- `state`
- `apiBaseUrl`
- `bearerToken`
- `briefPath`
- `personaDir`
- `queryState`
- optional `copy`

Expected outputs:

- `state`
- `bundle`
- `jobs`
- `selectedJob`
- `sessionBridgeState`
- `bridgeState`
- `reviewQueryState`
- `querySource`
- `runtimeSyncView`
- `frontendState`

This is the main read contract for future frontend components.

### `createWorkspaceShellAppController(options)`

Stateful controller for mutating and refreshing shell state.

Supported responsibilities:

- reset shell state
- apply sample draft scenarios
- switch to sample jobs
- select live or sample jobs
- select local evidence result
- select local replay step
- clear local evidence selection
- toggle runtime auto refresh
- submit live job
- load workspace session
- list live jobs
- load selected live job
- load live evidence query
- sync runtime heartbeat
- derive one render model

When the live shell is already operating in backend mode, `syncRuntime(input)` should be treated as the default refresh action for:

- session state
- selected job state
- evidence query state
- selected result or replay focus

## Required controller methods

### Reads

- `getState()`
- `deriveModel(input)`

### Local transitions

- `reset()`
- `applyDraftScenario(scenarioId)`
- `useSampleJobs()`
- `selectJob(jobId)`
- `selectLocalEvidenceResult(resultId)`
- `selectLocalReplayStep(stepId)`
- `clearLocalEvidenceQuery()`
- `toggleRuntimeAutoRefresh()`

### Runtime actions

- `submitLiveJob(input)`
- `loadWorkspaceSession(input)`
- `listLiveJobs(input)`
- `loadSelectedLiveJob(input)`
- `loadLiveEvidenceQuery(input)`
- `syncRuntime(input)`

`syncRuntime(input)` may also accept:

- `selectedResultId`
- `selectedReplayStepId`

so frontend pages can keep evidence focus inside the same snapshot-driven refresh path.

## Composition rule

Future frontend pages should:

1. keep form inputs page-local
2. pass those inputs into `deriveModel(...)` and runtime actions
3. render from the returned model
4. avoid rebuilding runtime orchestration inside page-local scripts

## Non-goals

This contract does not yet define:

- framework-specific state management
- websocket or push subscriptions
- persistent browser session storage
- backend-owned conversational thread state
- server-rendered component contracts

## Verification

Executable coverage:

- `tests/workspace_ui/test_workspace_shell_app.mjs`

That coverage must at least prove:

- default draft-only model derivation
- confirmed-draft submission readiness
- controller-driven job submission and session loading
- controller-driven runtime sync
- controller-driven snapshot-focused evidence selection
- controller-managed auto-refresh toggle state
