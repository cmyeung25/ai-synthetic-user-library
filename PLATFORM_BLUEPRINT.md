# Platform Blueprint

## 1. Platform Mission

AI Validation Swarm is a `human behavior simulation platform` built to replace selected parts of interviewer-led user research.

The platform is not trying to automate note-taking, transcript formatting, or interview logistics first.

The platform is trying to help teams predict:

- whether a problem is real
- why the problem happens
- how people actually decide
- how people interpret a concept or prototype
- where trust breaks
- why adoption stalls even when the value sounds good

The core output is not polished narrative. The core output is `behaviorally plausible synthetic evidence`.

## 2. Platform Job To Be Done

At the platform level, the system should let a founder, product team, or researcher:

1. select the right research mode for the question
2. run that mode against suitable synthetic users
3. produce evidence with clear boundaries
4. identify what remains unproven and must still be validated with humans

This means the platform must behave like a `research capability system`, not just a CLI wrapper around personas.

## 3. Platform Scope

### In Scope

- discovery research support
- concept evaluation
- prototype validation
- trust and adoption risk prediction
- persona-driven panel synthesis
- calibration toward human-like behavior

### Out of Scope For Early Platform Stages

- generic interview automation without stronger simulation quality
- report polish as a primary goal
- broad SaaS workflow surface that does not strengthen simulation quality
- claiming market proof from synthetic evidence

## 4. Platform Capability Stack

The platform should be understood as five stacked layers.

### Layer 1: Simulation Core

This is the non-negotiable engine.

It contains:

- persona truth model
- human difference modeling
- relational and communication behavior models
- friction and realism controls
- evidence and audit structures

Question this layer answers:

- Can the synthetic user behave in ways that are plausibly human rather than merely articulate?

### Layer 2: Research Mode Layer

This layer defines what kinds of research the platform can actually perform.

The target single-interview modes are:

- `pain_point_discovery`
- `explore_root_cause`
- `decision_reconstruction`
- `validate_hypothesis`
- `concept_validation`
- `prototype_validation`
- `adoption_barrier_validation`

Expansion modes:

- `workflow_mapping`
- `messaging_validation`

Question this layer answers:

- What exact research job is the platform doing right now?

### Layer 3: Stimulus and Behavior Layer

This is the layer that separates concept interviews from prototype validation.

Stimulus maturity path:

1. text concept
2. image stimulus
3. multi-screen flow stimulus
4. clickable prototype
5. live app interface

Behavior maturity path:

1. stated reaction
2. interpreted friction
3. task-guided reaction
4. observed action trace
5. action-grounded synthesis

Question this layer answers:

- Is the system only asking what the user says, or can it observe what the user does?

### Layer 4: Research Orchestration Layer

This is how the platform turns one synthetic user into a reusable research workflow.

It contains:

- single facilitator interview
- observer-controlled interview
- panel runs
- panel synthesis
- facilitator audit learning
- over-optimism detection

Question this layer answers:

- How does the platform convert one or more synthetic users into a research-grade output?

### Layer 5: Product and Delivery Layer

This is how users access the engine.

Access surfaces should evolve in this order:

1. CLI shell
2. structured APIs and job orchestration
3. workspace product UI
4. SaaS controls such as auth, billing, roles, and retention

Question this layer answers:

- How does a team operate the platform?

Important rule:

- `CLI` is the first execution shell, not the platform itself.

## 5. Evidence Model

The platform should distinguish at least these evidence classes:

- `stated_belief`
- `recalled_behavior`
- `decision_reconstruction`
- `inferred_driver`
- `observed_action`
- `simulated_risk`
- `human_validation_gap`

The platform should never collapse these into one undifferentiated "insight."

The most important boundary is:

- `concept_validation` is mostly stated and interpreted evidence
- `prototype_validation` should move toward observed behavior evidence

## 6. Primary Research Flows

### Discovery

Use:

- `pain_point_discovery`
- `explore_root_cause`
- `decision_reconstruction`
- `workflow_mapping`

Primary output:

- problem reality
- problem frequency
- real decision context
- current workaround and fragmentation

### Concept Evaluation

Use:

- `validate_hypothesis`
- `concept_validation`
- `messaging_validation`
- `adoption_barrier_validation`

Primary output:

- understanding
- trust and objection structure
- adoption conditions
- wording clarity
- stated willingness versus likely inertia

### Prototype Validation

Use:

- `prototype_validation`

Primary output:

- interpretation breakdown
- first-action expectation
- setup confusion
- drop-off
- observed task difficulty

## 7. Maturity Model

### What Is Already Proven

- reusable persona generation exists
- structured synthetic interviews exist
- observer-controlled interviews exist
- panel synthesis exists
- realism scoring exists
- over-optimism warnings exist

### What Is Partially Proven

- concept evaluation workflows
- hypothesis-oriented interview discipline
- prototype-validation mode contract with static image review, flow review, and browser-independent clickable task execution, but without live-interface execution yet
- synthetic panel reporting

### What Is Not Yet Proven

- full discovery-stage coverage
- live-interface prototype behavior validation beyond scripted clickable manifests
- action-grounded adoption prediction

## 8. Platform Sequencing Principle

The platform should not grow in random feature order.

Build order should follow:

1. `execution shell`
   CLI and deterministic orchestration

2. `mode contract layer`
   explicit interview modes with mode-specific coverage and synthesis schemas

3. `evidence model layer`
   clear boundaries between stated, inferred, and observed evidence

4. `stimulus layer`
   text, image, flow, prototype, live app

5. `behavior layer`
   task loop, action trace, abandonment, backtracking, observed confusion

6. `panel learning layer`
   cross-persona synthesis, conflict detection, recurring failure mode learning

7. `product layer`
   workspace UI, run setup, asset upload, synthesis browsing

8. `SaaS layer`
   auth, teams, billing, retention, async workers, governance

## 9. Strategic Design Rules

- Do not treat every user request as a new product surface request.
- Do not expand SaaS scope ahead of core simulation quality.
- Do not claim prototype validation before stimuli and action traces exist.
- Do not let concept-specific conclusions leak into reusable persona core.
- Do not confuse eloquent synthetic agreement with realism.
- Do not count report polish as platform progress unless evidence quality improves.

## 10. Current Strategic Recommendation

The fastest path toward a stronger platform is:

1. extend the implemented clickable executor boundary from scripted manifests to browser-driven prototype execution

2. add a normalized executor adapter before driver-specific browser or app automation expansion

3. add live app execution only after clickable prototype behavior is proven

This keeps the platform aligned with its real bottleneck:

- better prediction of human behavior
- not broader workflow surface
