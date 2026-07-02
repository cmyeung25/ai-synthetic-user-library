# Workspace UI Engineering Demo Testing Guide

## Purpose

This guide explains how to test the current engineering demo surfaces for the Workspace UI shell.

Use it to verify:

- the integrated shell flow from intake to review
- the runtime bridge from confirmed draft to `validation-jobs` API
- the current boundary between real job ingress, real completed-run evidence query, and still-limited replay depth

This is an engineering demo guide, not an end-user product guide.

## Demo surfaces

### Stage 11

URL:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage11/index.html`

Purpose:

- verify the integrated shell flow locally without a live backend dependency

What it proves:

- one shell can carry intake, confirmation, run monitor, and evidence query review
- shared adapter and shell derivations produce coherent state transitions

### Stage 12

URL:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage12/index.html`

Purpose:

- verify the shell can call the real local `validation-jobs` API

What it proves:

- confirmed draft maps into API request payload
- live job rows can drive shell run-monitor state
- completed runs can now query metadata-backed evidence through the local API
- shared runtime sync can keep session, selected job, and completed-run evidence query aligned from one heartbeat layer
- replay remains limited unless the run artifacts actually contain trace-linked steps

### Stage 14

URL:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage14/index.html`

Purpose:

- verify the backend-driven workspace shell can hydrate session, selected job, and evidence-query focus through one `workspace-shell` snapshot contract

What it proves:

- the current product-facing shell can refresh from one backend snapshot path instead of stitching state together in the page
- selected evidence and replay focus can stay aligned through the same live snapshot flow
- the engineering demo now defaults to the latest shell surface instead of the older contract-debug page

## Fast start

Double-click:

- `scripts/start_local_workspace_demo.bat`

That helper will:

1. bootstrap `ws_api_demo`
2. copy `data/briefs/sample_brief.json` into the workspace as `briefs/brief.json`
3. copy `data/personas/` into the workspace
4. start the static server on `4173` if needed
5. restart the SaaS API on `8011`, wait for `GET /api/v1/session` to respond, and make sure the demo uses the current repo code
6. restart the worker loop so queued jobs use the current repo code
7. open the Stage 14 page by default

Default live-mode values:

- `API base URL`: `http://127.0.0.1:8011`
- `Bearer token`: `token-api`
- `brief_path`: `briefs/brief.json`
- `persona_dir`: `personas`

## Quick smoke test

If you only want one short pass, use this sequence:

1. double-click `scripts/start_local_workspace_demo.bat`
2. wait until the browser opens Stage 14
3. keep or edit the research intent, desired output, and first-task anchor in the intake panel
4. click `attach screenshots`
5. click `confirm plan` once queueability becomes `ready for confirmation`
6. click `submit live job`
7. click `load shell snapshot`
8. if needed, click `start auto refresh`
9. once the newest job becomes `completed`, click the run card again or change one evidence query control
10. click one evidence result card
11. if replay steps are visible, click one replay step

Expected result:

- the shell snapshot loads a real workspace session, selected job, and evidence-query payload through one backend response
- `Selected job` becomes a real job id
- `Shell surface` moves out of the blocked intake state
- `Evidence review` shows `query source = backend evidence endpoint`
- selected evidence detail and replay focus stay aligned after snapshot refresh
- `Bridge gap` stays explicit about synthetic evidence and replay limits rather than pretending the system is production-complete

## Test pass 1: Stage 11 local shell flow

Open Stage 11.

### Case 1: blocked draft

Expected actions:

1. open the page
2. do nothing

Expected result:

- `UI phase` shows `blocked`
- `Run status` shows `ready_to_queue`
- `Query status` shows `query_pending`
- the conversation area explains missing inputs
- evidence review is still locked

### Case 2: ready for confirmation

Expected actions:

1. click `attach screenshots`
2. click `set first task`

Expected result:

- `UI phase` moves to `ready_for_confirmation`
- the primary action becomes confirmation-oriented
- blockers disappear

### Case 3: queued to completed

Expected actions:

1. click `confirm plan`
2. click `lease worker`
3. click `start run`
4. click `complete run`

Expected result:

- stage strip advances across confirmation, monitor, and review
- run monitor shows queue and worker progress
- evidence query unlocks after completion
- result cards appear in the evidence review area

### Case 4: failed run and retry

Expected actions:

1. reset the shell
2. attach screenshots
3. set first task
4. confirm the plan
5. click `fail run`
6. click `retry run`

Expected result:

- failure state is visible in the shell
- retry returns the run to queue state
- failure reason is shown before retry

## Test pass 2: Stage 12 sample-mode checks

Open Stage 12.

### Case 1: blocked sample draft

Expected actions:

1. click `blocked draft`

Expected result:

- `Bridge status` is `draft_only`
- `Submission ready` is `no`
- `submit live job` is disabled
- request JSON is still visible, but not submittable

### Case 2: confirmation-ready sample draft

Expected actions:

1. click `ready for confirmation`

Expected result:

- draft summary shows prototype-oriented path
- `Submission ready` stays `no`
- shell surface moves toward confirmation state, but not queued

### Case 3: confirmed sample draft

Expected actions:

1. click `confirmed draft`

Expected result:

- `Submission ready` becomes `yes`
- `submit live job` becomes enabled
- request summary shows:
  - `briefs/brief.json`
  - `personas`
  - `mainstream`
  - sample size `5`

### Case 4: sample completed and failed shell projections

Expected actions:

1. click `completed local shell`
2. then click `failed local shell`

Expected result:

- shell summary changes between completed and failed
- failure state shows visible failure detail
- evidence review remains explicit about whether it is using local projection or backend query

## Test pass 3: Stage 12 live-mode checks

Precondition:

- `scripts/start_local_workspace_demo.bat` already ran successfully

### Case 1: submit live job

Expected actions:

1. click `confirmed draft`
2. click `submit live job`

Expected result:

- last API response includes a `job`
- mode effectively moves into live job usage
- selected job id becomes populated

### Case 0: load workspace session

Expected actions:

1. click `load workspace session`

Expected result:

- session status becomes `session_loaded`
- session summary shows workspace id, user id, role, display name, plan tier, and billing status
- plan limits and job counts become visible
- runtime paths and capability cards appear without needing raw filesystem inspection

### Case 2: list live jobs

Expected actions:

1. click `list live jobs`

Expected result:

- live or sample jobs panel shows real API jobs
- a new queued or completed row appears depending on worker timing

### Case 3: load selected live job

Expected actions:

1. click one job card
2. click `load selected live job`

Expected result:

- selected job JSON updates
- derived run record updates
- shell projection updates from the selected live job state

### Case 4: worker progression

Expected actions:

1. wait a few seconds after submit
2. either wait for auto refresh
3. or click `sync now`
4. or list / reload the selected job again

Expected result:

- if the worker is healthy and the sample workspace data is valid, the job should move from `queued` toward `completed`
- if it fails, the shell should show failure state rather than silently hiding it
- if `auto refresh` is enabled, the runtime sync card should move through `syncing` into `live_synced`
- if `auto refresh` is off, `sync now` should still refresh the same state path without re-clicking every individual fetch button

### Case 5: live evidence query

Expected actions:

1. ensure one live job is already `completed`
2. click that job card
3. click `load live evidence query`
4. click one evidence result card
5. if replay steps are visible, click one replay step

Expected result:

- last API response switches to an evidence-query payload
- review summary shows `query source = backend evidence endpoint`
- query status becomes `query_ready`
- artifact count becomes greater than `0`
- the bridge gap copy changes from missing-endpoint language to a real boundary warning about synthetic evidence and replay limits
- the evidence result grid becomes populated with backend results
- the selected evidence panel shows summary and detail lines for the active result
- replay focus updates only when the selected result actually carries trace-linked steps
- these review panels now derive from the shared shell frontend adapter rather than page-local summary mapping
- the live session, job, and evidence-query actions now derive from the shared shell runtime client rather than one page-local fetch script
- the runtime sync card now derives from the shared shell runtime sync module rather than page-local polling logic

### Case 6: query controls

Expected actions:

1. in sample mode or live mode, change `query text`, `family`, or `sort`
2. click `apply evidence query`

Expected result:

- in sample mode, the visible result grid reprojects immediately from local demo evidence
- in live mode, the page refetches `GET /api/v1/evidence-query` with the new query parameters
- the result count, active result, and replay focus stay aligned with the new query universe

## Optional API sanity check

If you want to verify the backend without relying only on the page:

1. submit one live job from Stage 12
2. run `list live jobs`
3. copy the selected `job_id`
4. call the API directly

PowerShell example:

```powershell
$headers = @{ Authorization = "Bearer token-api" }
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8011/api/v1/validation-jobs"
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8011/api/v1/evidence-query?job_id=YOUR_JOB_ID&active_family=all&sort_by=relevance"
```

Expected result:

- the first call returns a `jobs` list
- once the job is completed, the second call returns `query_status = query_ready`
- if the job is still queued or running, the second call returns a pending query state instead of failing silently

## Expected boundaries

These are current expected limitations, not bugs:

- Stage 11 is local-state only
- Stage 12 uses a real local API for both job ingress and completed-run evidence query
- the page still uses engineering-facing JSON panels for visibility
- the demo still requires a manual token rather than real end-user session auth
- replay remains sparse or empty for validation runs that do not produce trace-linked step artifacts
- auto refresh is still engineering-grade polling rather than a production subscription or websocket layer

## Common failure modes

### `ModuleNotFoundError: No module named 'ai_validation_swarm'`

Cause:

- `src/` is not on `PYTHONPATH`

Fix:

```powershell
$env:PYTHONPATH='src'
python -m ai_validation_swarm.cli.main run-saas-worker
```

Or use:

```powershell
.\.venv\Scripts\python.exe -m ai_validation_swarm.cli.main run-saas-worker
```

### `submit live job` stays disabled

Cause:

- the draft is not in the confirmed submittable state

Fix:

- click `confirmed draft`

### API returns auth error

Cause:

- wrong token

Fix:

- use `token-api`

### API returns path-not-found error

Cause:

- workspace data is missing

Fix:

- rerun `scripts/start_local_workspace_demo.bat`

### jobs remain queued

Cause:

- worker loop is not running

Fix:

- rerun `scripts/start_local_workspace_demo.bat`
- or start the worker manually:

```powershell
$env:PYTHONPATH='src'
python -m ai_validation_swarm.cli.main run-saas-worker
```

## Review checklist

Use this checklist when reviewing the engineering demo:

1. Can blocked drafts explain what evidence is missing?
2. Can confirmation-ready drafts enable a concrete next action?
3. Can live job submission use the real API contract?
4. Can selected live jobs drive shell run-monitor state?
5. Does failure stay visible instead of disappearing?
6. Does the demo keep the remaining replay and evidence-boundary limits explicit even when backend query is live?

If all six hold, the engineering demo is behaving as intended for the current milestone.
