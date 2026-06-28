# Milestone 14 Design Spec: Browser-Driven Prototype and Live-App Behavior Validation

## Status

Implemented.

## Product Intent

Milestone 14 upgrades prototype validation from declared or manifest-scripted behavior into browser-observed behavior traces. The research bottleneck is action-grounded prototype validation: the platform needs to capture what an instrumented task run actually did on an interactive surface before asking a synthetic participant to explain likely hesitation, trust gaps, objections, and adoption barriers.

This improves evidence quality and decision prediction by separating:

- observed interface behavior from stated intention
- browser event telemetry from simulated explanation
- synthetic task evidence from human market proof

## Non-Goals

- Do not claim browser-observed synthetic traces are human usability proof.
- Do not run credentialed, high-stakes, destructive, payment, banking, or transfer flows automatically.
- Do not duplicate Milestone 12 evidence reliability scoring in a browser driver.
- Do not make Playwright, Chrome, or any one browser tool part of the core Python evidence contract.
- Do not turn the user-facing workspace into an automation-builder surface.

## Contract

Browser behavior artifacts are JSON objects accepted by `clickable` or `live_app` prototype-validation runs when they include one of:

- `trace_version: "browser-behavior-trace/v1"`
- `capture_kind: "browser_session"` or equivalent browser capture kind
- `browser_events`, `browser_trace_events`, or `events`

Required event shape is intentionally driver-neutral:

```json
{
  "trace_version": "browser-behavior-trace/v1",
  "prototype_label": "Hosted Evidence Workspace",
  "trace_label": "hosted-browser-review-run",
  "driver": "playwright",
  "session": {
    "start_url": "http://127.0.0.1:4173/prototype.html",
    "final_url": "http://127.0.0.1:4173/prototype.html#evidence",
    "viewport": {"width": 1280, "height": 800}
  },
  "events": [
    {"type": "navigation", "url": "http://127.0.0.1:4173/prototype.html"},
    {"type": "click", "selector": "[data-action='open-evidence']", "target": "evidence drawer"}
  ]
}
```

The runtime normalizes this into existing `observed-action-trace/v1` so Milestone 12 query, replay, reliability, audit-lineage, and Evidence Review contracts continue to consume one stable trace shape.

## Architecture Boundaries

`BrowserBehaviorTraceExecutor` owns:

- detecting browser-captured trace artifacts
- applying the browser safety gate before evidence promotion
- normalizing driver-specific event names into observed actions
- preserving selector, URL, driver, page, and coordinate metadata for replay
- returning `stimulus_analysis.analysis_type` as `browser_clickable_trace` or `live_app_browser_trace`

`FacilitatedInterviewRuntime` owns:

- resolving and snapshotting the supplied JSON artifact
- routing it through the executor chain
- persisting `stimulus_analysis.json` and `observed_action_trace.json`
- rendering prompt, transcript, and insight sections with the browser evidence boundary visible

Milestone 12 evidence query owns:

- selected evidence
- replay focus
- cross-run comparison
- reliability and calibration records
- audit lineage

## Safety Gate

The browser executor blocks artifacts when:

- payload flags indicate `credentialed_session`, `requires_credentials`, `high_stakes`, `destructive_actions_allowed`, or `external_network_allowed`
- URLs are outside `file://`, localhost, `127.0.0.1`, `::1`, or explicit `allowed_origins`
- event text, selectors, labels, targets, or URLs contain blocked destructive or sensitive tokens such as password, token, credential, payment, checkout, delete, revoke, publish, transfer, bank, or submit

Blocked artifacts fail before synthesis so unsafe traces do not become evidence.

## Evidence Boundary

Every browser trace is still simulated evidence. It can support claims such as:

- an instrumented task run clicked, navigated, backtracked, hesitated, stopped, or completed
- the interface path exposed a likely trust or comprehension boundary
- repeated synthetic task runs disagree or converge on a specific failure point

It must not support claims such as:

- real users behaved this way
- the market validated the prototype
- a credentialed or high-stakes flow is safe to automate
- task completion predicts adoption without calibration

## Acceptance

Milestone 14 is accepted when:

- browser-captured clickable artifacts are normalized into `observed_action_trace`
- live-app trace artifacts can use the same executor boundary and safety policy
- prompt, transcript, insight, and report outputs keep browser-observed behavior separate from stated intention
- safety-gated traces are rejected before becoming evidence
- unit tests cover normalization, runtime persistence, and safety rejection

## Verification

Current verification:

- `python -m py_compile src\ai_validation_swarm\facilitator\stimulus_executor.py src\ai_validation_swarm\facilitator\runtime.py src\ai_validation_swarm\domain\validators.py`
- `python -m unittest tests.unit.test_stimulus_executor tests.unit.test_input_validation tests.unit.test_facilitator_runtime`

`pytest` is not required for this milestone in the current environment.
