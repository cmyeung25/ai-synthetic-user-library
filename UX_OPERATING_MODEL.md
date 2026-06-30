# UX Operating Model

## Purpose

This document defines how a user should operate the AI Validation Swarm workspace from first research question to durable decision.

It is not a screen inventory.
It is the intended operating model for the product.

## Alignment Check

- Research bottleneck improved: turning an initial research question into a disciplined study flow, then turning synthetic outputs into evidence-backed review and next-step action
- Primary improvements: `evidence quality`, `decision prediction`, `scalable research throughput`
- Why this is core: replacing interviewer-led work requires low-friction intake, high-discipline review, and durable judgment capture, not only good-looking outputs

## Operating Assumption

The product should help a researcher, founder, or product team do five things well:

1. express what they need to learn
2. clarify missing context without learning internal schemas
3. confirm a concrete research plan before execution
4. inspect evidence with boundaries and comparison intact
5. record what is believed, what is still uncertain, and what needs human validation

## Primary Users

### Research Lead

Needs to frame the question, review evidence quality, compare interpretations, and decide what requires human follow-up.

### Founder or Product Lead

Needs a fast path from question to credible directional signal without pretending synthetic evidence is final market proof.

### Reviewer or Approver

Needs to inspect what was concluded, what supports it, and what remains unproven.

## Product Object Model

The workspace should teach this object model through use, not through documentation-first onboarding.

### Workspace

Holds identity, governance, billing, retention, sharing, and audit context.

### Project

Groups business context or product area over time.

### Study

The primary research container.

A study owns:

- the research question
- target segment or panel assumptions
- attached stimuli and artifacts
- related runs
- saved evidence views
- decision logs
- collaboration context

### Run

One execution of a confirmed plan inside a study.

### Saved Evidence View

A durable, named slice of review state for a question, theme, contradiction, or comparison.

### Decision Log

A durable judgment artifact that records what the team currently believes and what still requires validation.

### Export or Share Bundle

A distribution artifact created after the study work, not the primary product object.

## Route Operating Model

The product should use a persistent shell with route-aware pages.
This means the shell can stay visually continuous, but the user's location must still map to a durable product object or review context.

Canonical route responsibilities:

- `/studio`: workspace overview and recent study entry points.
- `/studio/projects`: project list and project creation.
- `/studio/projects/{project_id}`: project context, studies, collaborators, and recent decisions.
- `/studio/studies/new`: start a new study through guided setup.
- `/studio/studies/{study_id}`: study home with question, plan state, latest runs, open evidence, and decisions.
- `/studio/studies/{study_id}/setup`: Research Copilot or Guided Setup for Ask, Clarify, and Confirm Plan.
- `/studio/studies/{study_id}/runs/{run_id}`: run monitor, transcript, artifacts, audit, and provider boundary.
- `/studio/studies/{study_id}/evidence`: evidence review and comparison workspace.
- `/studio/studies/{study_id}/evidence-views/{evidence_view_id}`: saved evidence slice.
- `/studio/studies/{study_id}/reports/{study_report_id}`: study-level synthesis.
- `/studio/studies/{study_id}/decisions/{decision_log_id}`: durable decision review.
- `/studio/share/{share_bundle_id}`: shared or export-ready boundary-preserving view.

Rules:

- If a user would bookmark it, share it, return to it after refresh, or cite it in a decision, it needs a route.
- If it is only a temporary step in the current guided setup, keep it as local study workflow state.
- Browser back/forward must not lose selected study, evidence view, decision log, or synthetic-evidence boundary.
- Route labels and left navigation must teach the product object model, not internal mode taxonomy.

## Default Operating Loop

The default user flow should be:

1. `Ask`
2. `Clarify`
3. `Confirm Plan`
4. `Run`
5. `Review Evidence`
6. `Compare`
7. `Decide`
8. `Share With Boundary`

### 1. Ask

User action:
- describe the research question in plain language

System responsibility:
- capture the question without forcing mode selection
- identify whether artifacts or constraints are already present

Exit criteria:
- the system has a first-pass understanding of what the user wants to learn

### 2. Clarify

User action:
- answer only the missing high-signal questions

System responsibility:
- ask the smallest useful follow-up set
- infer likely research mode, segment needs, and artifact requirements
- avoid large forms and premature advanced settings

Typical clarification topics:

- who the target user is
- what concept, message, or prototype is being tested
- what decision the team is trying to make
- what artifacts exist
- what uncertainty matters most

Exit criteria:
- enough context exists to propose a valid plan

### 3. Confirm Plan

User action:
- review and confirm the inferred plan

System responsibility:
- translate the conversation into a clear execution plan
- state the inferred mode and expected evidence classes
- declare known limitations and remaining ambiguity

The confirmation view must show:

- research goal
- inferred mode
- artifacts in scope
- target segment or panel logic
- expected evidence types
- known human-validation gaps

Exit criteria:
- the user explicitly approves the plan before a run starts

### 4. Run

User action:
- start the run and monitor progress as needed

System responsibility:
- keep execution status legible
- explain blocked, failed, or partial states in product language
- preserve study context while the run is active

Exit criteria:
- the run completes, fails, or returns a recoverable blocked state

### 5. Review Evidence

User action:
- inspect what happened and what the evidence supports

System responsibility:
- default to evidence-first review
- separate observation, interpretation, and summary
- keep contradictions, gaps, and risk signals visible

The first review pass should answer:

- what people objected to
- where trust broke
- what adoption barriers appeared
- what differed by segment or scenario
- what evidence is still only synthetic signal

Exit criteria:
- the user can state what the run suggests and what remains unresolved

### 6. Compare

User action:
- compare runs, segments, versions, or studies

System responsibility:
- preserve comparable context
- highlight stable patterns versus meaningful differences
- keep provenance clear for every compared item

Comparison should be routine, not hidden behind a specialist view.

Exit criteria:
- the user can tell whether a pattern is stable, divergent, or inconclusive

### 7. Decide

User action:
- convert findings into a working judgment

System responsibility:
- provide a decision-log surface
- require separation between current belief and proven fact
- keep supporting evidence attached

Decision logs should capture:

- current conclusion
- evidence basis
- synthetic-only boundary
- unresolved objections
- required human follow-up

Exit criteria:
- a durable decision artifact exists inside the study

### 8. Share With Boundary

User action:
- export or share the current state with collaborators

System responsibility:
- preserve evidence boundary language in shared artifacts
- avoid overstating synthetic findings as human proof
- make the current decision state and open validation gaps visible

Exit criteria:
- collaborators receive a usable view without losing provenance or limits

## Product Behavior Rules

### Rule 1. Do Not Start With Mode Taxonomy

The user should not need to choose between internal research modes before they can describe the problem.

### Rule 2. Ask Only the Next Useful Question

Clarification should be progressive.
Do not expose every field when only one missing input blocks a valid plan.

### Rule 3. The Plan Must Be Explicit

Inference is useful, but silent inference is dangerous.
Every run should start from a visible, confirmable plan.

### Rule 4. Evidence Types Must Stay Distinct

Do not collapse observed behavior, stated opinion, inferred driver, and summary prose into one undifferentiated output.

### Rule 5. Memory Must Persist Beyond One Run

The platform should remember the study context through saved evidence views, decision logs, deep links, and activity history.

### Rule 6. Comparison Should Be Easier Than Re-Explaining

When users want to revisit a question, the product should help them compare existing work before asking them to restate context.

### Rule 7. Uncertainty Is Part of the Product

The UX should make room for incomplete evidence, contradictions, and required human validation.
These are product outputs, not failure states.

### Rule 8. Governance Should Not Hijack the Main Flow

Settings, quotas, billing, and support matter, but they should not displace the research workflow as the product's main mental model.

## Secondary Flows

These flows should exist without replacing the main operating loop:

- reopen a study from a deep link
- rerun a study with revised artifacts or assumptions
- save an evidence view for a contradiction, theme, or comparison
- open a decision log and continue review comments
- inspect workspace activity and audit history
- manage sharing, export, support, and governance actions

## Blocked and Failure States

The operating model should handle failure as part of serious research work.

### Missing Artifact

If a needed prototype or document is missing, the product should explain the gap and keep the study draft intact.

### Unsupported Execution Mode

If a requested live-interface behavior test is not yet supported, the product should route the user toward the nearest supported evidence class instead of failing silently.

### Quota or Permission Block

The product should explain whether the block is due to membership, billing, rate, or retention policy.

### Inconclusive Evidence

The product should allow a study to end in "not yet clear" rather than forcing a crisp conclusion.

## Success Criteria

The UX is working if it reliably produces these behaviors:

- users can start from a natural-language question without learning platform internals
- users see and confirm a clear plan before execution
- users review evidence before over-trusting summaries
- users compare runs and segments inside one study context
- users record decisions with explicit synthetic-evidence boundaries
- users leave with clear next-step human validation gaps when proof is not yet strong enough

## Anti-Goals

The operating model should explicitly avoid becoming:

- a prompt playground
- a node-builder research IDE
- a one-shot report generator
- a generic AI chat history
- a polished conclusion machine that hides uncertainty
