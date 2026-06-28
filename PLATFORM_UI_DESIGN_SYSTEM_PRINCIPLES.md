# Platform UI Design System Principles

## Purpose

This document defines the product-surface doctrine for the AI Validation Swarm workspace UI.

The goal is not to make the platform look more "AI-native."
The goal is to make the interface behave like a trustworthy research instrument that helps teams:

- express a research intent with low setup friction
- inspect synthetic evidence with clear boundaries
- compare runs, segments, and stimuli without losing context
- record decisions and unresolved human-validation gaps

## Alignment Check

- Research bottleneck improved: translating messy research intent into a valid study setup, then turning multiple synthetic outputs into evidence-backed judgment
- Primary improvements: `evidence quality`, `decision prediction`, `scalable research throughput`
- Why this is core: a weak product surface forces users to learn internal schemas and reduces evidence discipline; a strong product surface helps replace interviewer-led setup and early-stage synthesis work

## Core Product Surface Position

The interface should be treated as a `study-first research workspace`, not as:

- a generic AI chat app
- a workflow builder
- a report-export wizard
- a prompt playground disguised as a product

The primary unit of work is the `study`.

The product hierarchy should default to:

1. `workspace`
2. `project`
3. `study`
4. `run`
5. `saved evidence view`
6. `decision log`
7. `export or share bundle`

`Run` is an execution record inside a study.
It is not the top-level product object.

## Product-Surface Principles

### 1. Study-First Shell

The main workspace should orient the user around the current study, its question, its attached artifacts, its recent runs, and its open decisions.

Do not make the default experience `job-first`, `prompt-first`, or `chat-thread-first`.

### 2. Evidence Before Summary

The UI should never force users to accept a polished summary without seeing the evidence structure underneath it.

Default review surfaces should make it easy to inspect:

- objections
- trust breaks
- adoption barriers
- segment differences
- evidence-type boundaries
- contradictions
- unresolved validation gaps

### 3. Behavior Before Eloquence

When prototype or task-grounded material exists, observed or action-grounded evidence must outrank articulate self-report.

The surface should clearly separate:

- `stated belief`
- `recalled behavior`
- `decision reconstruction`
- `observed action`
- `simulated risk`
- `human validation gap`

### 4. Uncertainty Must Stay Visible

The UI must never hide uncertainty behind a clean narrative.

Confidence, coverage gaps, disagreement, contradictory evidence, and "needs human validation" states should be visible in the default review path, not buried behind an advanced panel.

### 5. Comparison Is Native

The product should assume that serious research work requires comparison.

The interface should make it natural to compare:

- one segment against another
- one run against another
- one concept or prototype version against another
- one study revision against another

### 6. Conversational Intake, Explicit Plan Confirmation

The main intake path should start from natural-language research intent.

The system should progressively gather missing context instead of exposing a large upfront form.

Before execution, the product must show a clear plan confirmation step that states:

- inferred research mode
- target question
- attached artifacts
- target synthetic panel or selection logic
- expected evidence types
- known limitations and unproven areas

### 7. Auditability Within One Click

Every meaningful conclusion should be close to its provenance.

Users should be able to move quickly from an insight to:

- the originating run
- the source evidence slice
- the relevant artifact or stimulus
- the plan assumptions
- the model, runtime, or execution metadata when needed

### 8. Dense Information, Calm Hierarchy

This platform should support information-dense research work without turning into visual noise.

The design target is not empty marketing-space minimalism.
It is a calm, structured review environment with strong hierarchy and disciplined emphasis.

### 9. Decision Logging Is First-Class

The product should not end at "generate a report."

Users need a durable place to record:

- what they currently believe
- what evidence supports it
- what is still only synthetic signal
- what needs human follow-up

### 10. Advanced Controls Stay Secondary

Mode overrides, persona filters, structured fields, and execution controls can exist, but they should not dominate the first-run experience.

Default flow should minimize learning cost.
Expert controls should be available without becoming the main mental model.

### 11. Governance Must Support, Not Interrupt, Research

Billing, membership, quotas, retention, sharing, and support tools matter, but they should stay adjacent to the research workflow rather than taking over the main shell.

### 12. The Product Should Feel Like a Research Lab

The visual language should communicate disciplined inquiry, not AI spectacle.

The platform should feel closer to:

- an editorial dossier
- a research console
- a decision lab

than to:

- a glowing AI toy
- a trend-driven SaaS dashboard
- a generic card wall

## Visual System Direction

### Tone

Use an `editorial research lab` direction:

- serious
- legible
- evidence-forward
- precise
- calm under density

### Typography

Pair a characterful editorial face with a pragmatic technical sans.

Preferred behavior:

- display or emphasis text may use a restrained serif
- body and UI text should use a highly legible technical sans
- avoid defaulting to generic SaaS typography stacks

Typography should signal that this is a research tool, not a landing page.

### Color

Color should carry meaning rather than decoration.

Recommended palette behavior:

- paper, graphite, slate, deep ink, or muted mineral neutrals for the base
- one disciplined accent family for focus and active study state
- separate warning and risk colors for contradictions, trust gaps, and human-validation boundaries

Do not use celebratory or glowing colors for uncertain findings.

### Layout

Favor persistent study context with a clear reading order.

Common layout behavior:

- persistent study or navigation rail
- main analysis canvas
- optional detail drawer or side panel
- sticky context elements only when they preserve evidence continuity

### Motion

Motion should explain state change, not decorate emptiness.

Use motion primarily for:

- staged reveal of a confirmed plan
- run-state transitions
- evidence expansion
- comparison changes

Avoid constant shimmer, floating effects, or decorative motion that suggests confidence without evidence.

## Canonical Screen Patterns

### Intake Workspace

Purpose:
- capture research intent and available artifacts

Rules:
- start from plain-language input
- ask only the next most useful missing question
- keep advanced controls collapsed by default

### Plan Confirmation

Purpose:
- let the user verify what the system inferred before execution

Rules:
- state the inferred mode plainly
- show evidence classes the run is expected to produce
- show key risks or known limitations
- require an explicit confirm action

### Run Monitor

Purpose:
- show execution progress without forcing raw log reading

Rules:
- distinguish queued, running, blocked, failed, completed states clearly
- explain blocked and failed states in operational language
- preserve the study context while the run is in flight

### Evidence Review

Purpose:
- inspect one run with evidence boundaries intact

Rules:
- default to evidence slices, not only summary prose
- let users pivot from summary to source detail quickly
- keep contradictions and human-validation gaps visible

### Comparison Workspace

Purpose:
- compare multiple runs, segments, or artifacts inside one study context

Rules:
- preserve the same question across the compared items
- surface both stable patterns and meaningful differences
- make provenance of each compared item obvious

### Decision Review

Purpose:
- convert evidence into a durable working judgment

Rules:
- force a distinction between current belief and proven fact
- keep the supporting evidence attached
- require explicit notation of unresolved human-validation gaps

## Anti-Patterns

Do not ship these as the default experience:

- a landing page that asks users to choose among internal modes before they can describe the research problem
- an `n8n`-style node graph for ordinary study setup
- a giant setup form that exposes every internal schema field on first use
- a chat transcript as the only durable memory of research work
- a report-only end state with no comparison or decision workflow
- visual treatment that implies certainty, authority, or celebration where the evidence remains synthetic or incomplete

## Acceptance Checklist

Any new product-surface work should be rejected or revised if it fails one or more of these checks:

- Does it keep `study` as the primary object instead of `run`, `job`, or `prompt`?
- Does it lower user learning cost instead of teaching internal platform taxonomy?
- Does it preserve the boundary between evidence types?
- Does it make uncertainty and human-validation gaps visible?
- Does it help comparison and replay instead of creating isolated one-off outputs?
- Does it improve durable decision-making rather than only report polish?
- Does it strengthen the platform's ability to replace interviewer-led setup or synthesis work?
