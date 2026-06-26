# Development Roadmap

## Purpose

This roadmap tracks the platform work that most directly improves:

- behavioral realism
- decision and adoption prediction quality
- evidence discipline and auditability
- reusable research workflows for discovery, concept evaluation, and prototype validation

The roadmap should be read as a capability roadmap for a `human behavior simulation platform`, not as a generic SaaS feature list.

## Status Legend

- `implemented`: already supported in the current repository
- `in_progress`: partially implemented, but not yet complete for the intended platform use
- `planned`: explicitly on roadmap, not yet implemented

## Interview Mode Roadmap

The platform should support `7 core single-interview modes` in Phase 1 and `9 total single-interview modes` in the fuller Phase 2 surface.

### Phase 1 Core Modes

1. `pain_point_discovery` - `implemented`
   Purpose: discover whether a problem exists, how often it appears, how painful it is, and what workaround is currently used.
   Primary stage: `discovery`

2. `explore_root_cause` - `implemented`
   Purpose: investigate why a known problem happens, what triggers it, and what deeper drivers keep it alive.
   Primary stage: `discovery`

3. `decision_reconstruction` - `implemented`
   Purpose: reconstruct one real recent decision, including evidence gaps, stakeholder pressure, internal uncertainty, and what actually changed.
   Primary stage: `discovery`

4. `validate_hypothesis` - `implemented`
   Purpose: test a specific causal or behavioral hypothesis against recalled experience without asking the participant to agree with the framing.
   Primary stage: `concept evaluation`

5. `concept_validation` - `implemented`
   Purpose: test understanding, appeal, objections, trust gaps, and stated adoption conditions for a concept.
   Primary stage: `concept evaluation`

6. `prototype_validation` - `planned`
   Purpose: test a prototype, image stimulus, flow, or live interface through observed task behavior rather than concept-only self-report.
   Primary stage: `prototype validation`

7. `adoption_barrier_validation` - `implemented`
   Purpose: identify why a user who sees value may still not adopt because of setup, permissions, trust, pricing, reversibility, or workflow burden.
   Primary stage: `concept evaluation` and `prototype validation`

### Phase 2 Expansion Modes

8. `workflow_mapping` - `planned`
   Purpose: map the current workflow, handoffs, fragmentation, and where information or responsibility breaks down.
   Primary stage: `discovery`

9. `messaging_validation` - `planned`
   Purpose: test wording, positioning, value proposition clarity, and whether the message creates the right mental model before use.
   Primary stage: `concept evaluation`

## Interview Mode Principles

- `pain_point_discovery` should not introduce the concept early.
- `explore_root_cause` should not assume the participant's stated cause is complete or correct.
- `decision_reconstruction` should stay anchored in a recent real event, not a generic preference summary.
- `validate_hypothesis` should seek contradiction and alternatives, not confirmation.
- `concept_validation` should separate understanding, curiosity, trial intent, payment intent, and durable adoption.
- `prototype_validation` should distinguish observed behavior from stated interpretation.
- `adoption_barrier_validation` should focus on the gap between "sounds useful" and "will actually enter routine use."

## Prototype Validation Roadmap

The current platform is still `text-first`. To reach real prototype validation, the platform should add a dedicated stimulus and action layer instead of overloading concept interviews.

### Prototype validation capability layers

1. `image_stimulus_review` - `planned`
   Input: screenshots, mocked UI frames, static prototype images
   Output: interpretation gaps, first-click expectations, trust signals, wording confusion, likely hesitation

2. `flow_stimulus_review` - `planned`
   Input: multi-screen prototype flow
   Output: step-by-step comprehension breakdown, likely drop-off points, hidden setup burden

3. `interactive_prototype_validation` - `planned`
   Input: clickable prototype or real app interface
   Output: observed task path, misclicks, backtracking, abandonment, and action-grounded follow-up probes

4. `live_app_task_simulation` - `planned`
   Input: live product URL or local app
   Output: observed behavior trace plus synthesis of where real-world activation may fail

## Milestone Roadmap

### Milestone 0: Architecture and Harness

Status: `implemented`

Scope:

- product brief
- system architecture
- data model
- workflow and safety constraints
- evaluation plan
- roadmap

Exit criteria:

- core platform direction is documented
- artifact model and repo structure are stable enough for implementation

### Milestone 1: Persona Generator

Status: `implemented`

Scope:

- seed generation
- structured persona artifacts
- audit metadata
- realism-oriented persona expansion

Exit criteria:

- personas can be generated reproducibly
- persona artifacts are inspectable and auditable

### Milestone 2: Sampling Engine

Status: `implemented`

Scope:

- panel presets
- filtering
- deterministic sampling
- rationale for panel selection

Exit criteria:

- persona selection is reproducible and explainable

### Milestone 3: Validation Runner

Status: `implemented`

Scope:

- founder brief loading
- persona response runner
- retry and artifact persistence

Exit criteria:

- end-to-end validation runs can be executed and archived

### Milestone 4: Auditor and Aggregator

Status: `implemented`

Scope:

- skeptic review
- sensitive-topic audit
- aggregation logic
- cross-persona summary

Exit criteria:

- runs produce structured audit and summary outputs

### Milestone 5: Report Generator

Status: `implemented`

Scope:

- Markdown and JSON outputs
- archive structure
- summary artifacts

Exit criteria:

- runs are readable and exportable without manual reconstruction

### Milestone 6: Evaluation Harness

Status: `implemented`

Scope:

- fixture suite
- deterministic tests
- regression checks
- quality gates

Exit criteria:

- core prompt and runtime changes can be regression-tested

### Milestone 7: Facilitated Interview Runtime

Status: `in_progress`

Scope:

- facilitator-led interview loop
- observer-controlled interview loop
- concept panel runtime
- realism scoring
- over-optimism warnings

Current implemented surface:

- `pain_point_discovery`
- `explore_root_cause`
- `decision_reconstruction`
- `validate_hypothesis`
- `concept_validation`
- `adoption_barrier_validation`
- observer actions
- concept panel summary
- facilitator audit learning reports

Current gaps:

- no dedicated `prototype_validation` mode
- no real stimulus-aware or action-aware interview runtime

Exit criteria:

- the 7 core interview modes are supported as explicit first-class modes
- each mode has mode-specific coverage requirements and synthesis schema
- concept and prototype evidence are clearly separated

### Milestone 8: Prototype Validation Layer

Status: `planned`

Scope:

- image-based concept/prototype review
- multi-screen flow review
- interactive prototype task loop
- action trace capture
- observed behavior synthesis

Exit criteria:

- the platform can test a prototype through task execution rather than concept-only discussion
- output distinguishes `stated intention` from `observed behavior`

### Milestone 9: SaaS Readiness

Status: `in_progress`

Scope:

- service decomposition
- multi-tenant design
- async job model
- auth, privacy, and billing design
- persona catalog governance

Exit criteria:

- the platform can be decomposed into a scalable service design without changing the research core

## Current Platform Readout

As of now, the platform has already proven:

- persona generation can support reusable structured synthetic users
- facilitated interviews can already produce usable synthetic evidence for pain discovery, decision reconstruction, root-cause, hypothesis, concept, and adoption-barrier work
- panel synthesis, conversation realism scoring, and over-optimism warnings are in place

As of now, the platform has not yet proven:

- complete discovery-stage coverage
- prototype behavior validation
- action-grounded adoption prediction from interface use

## Recommended Next Sequence

1. Define the input and synthesis contract for `prototype_validation`.
2. Implement static image stimulus support before live interactive prototype support.
3. Add flow-based stimulus review after static image support is stable.
4. Add observed behavior outputs only after the stimulus layer is stable.
