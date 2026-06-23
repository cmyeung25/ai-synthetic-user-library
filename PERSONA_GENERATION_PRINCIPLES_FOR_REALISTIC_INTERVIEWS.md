# Persona Generation Principles For Realistic Interviews

Use this document when changing persona schemas, generation prompts, panel presets, interview protocols, or evaluation rules.

The platform goal is not to generate personas that conveniently validate a concept.

The platform goal is to generate synthetic people that preserve enough heterogeneity, irrelevance, resistance, and surprise to approximate the value of interviewing real people.

## Core premise

Real interviews are valuable because participants do not arrive pre-shaped around the study hypothesis.

They arrive as people with:

- habits
- values
- constraints
- attention limits
- trust patterns
- routines
- family or work pressures
- uneven financial literacy
- inconsistent decision quality

The study should discover how those traits interact with a concept.

The study should not begin by encoding the intended concept conclusion into persona core.

## Platform rule

`Persona core may explain why a pain could arise, but it must not pre-encode which pain the study will discover.`

This rule takes precedence over project convenience.

## Three-layer model

### 1. Persona Core

Use for stable, reusable, long-lived traits.

Examples:

- values and motivations
- decision style
- trust style
- time pressure
- tolerance for complexity
- control preference
- family and work load
- media and learning habits
- emotional regulation
- digital behaviour

Core should remain meaningful if the current concept disappears.

### 2. Domain Context

Use for stable facts within a domain without deciding the research conclusion.

Examples in banking or investing:

- products held
- investable asset range
- number of platforms used
- whether an RM exists
- frequency of portfolio review
- currencies held
- external asset fragmentation
- comfort with data sharing

Domain context can explain what situations are plausible.

Domain context should not declare the study output in advance.

Do not encode as domain context:

- "main pain point is overlap"
- "needs stress testing"
- "biggest blind spot is concentration"
- "would value scenario analysis most"

Those belong to interview-time discovery unless proven stable across many studies.

### 3. Study-Time Inference

This is what the interview should discover from persona core + domain context + concept.

Examples:

- what triggered the last review
- what the participant actually worried about
- whether the current method feels good enough
- whether the real issue is trust, confidence, cash flow, FX, goals, or hidden overlap
- whether the concept is useful, excessive, confusing, or irrelevant

These are outputs, not starting assumptions.

## What realistic interviews require

To approximate real human interviews, the platform must preserve:

- heterogeneity
- disconfirming evidence
- low-pain cases
- off-target reactions
- misunderstandings
- irrelevant but honest priorities
- uneven articulation quality

If every persona quickly converges on the same pain or same feature value, the platform is no longer simulating discovery.

It is simulating confirmation.

## Non-negotiable generation rules

### Do not generate concept conclusions into persona core

Avoid fields that are already too close to the current study answer.

Examples to avoid in core:

- most salient blind spot
- feature that would help most
- likely reaction to this concept
- likely recent trigger if written to match the concept too neatly
- primary problem statement shaped around the product

These may be acceptable as:

- sidecar concept outputs
- panel sampling notes
- interview-time inferences

They should not become reusable persona truth by default.

### Do not make every persona concept-fit by design

A realistic panel must include people who:

- have the problem strongly
- have it weakly
- solve it differently
- misunderstand the concept
- reject the framing
- say their current workflow is good enough

If a panel is constructed so that every participant is already a likely convert, the sample is no longer interview-like.

### Preserve participant-level independence

The platform should not push every persona toward the same blind spot just because:

- the concept card highlights it
- the research team cares about it
- previous interviews surfaced it

Each persona should be able to land somewhere different for legitimate reasons.

## Recommended sampling axes

When building panels, sample on human difference axes, not concept conclusions.

Examples:

- control preference
- trust style
- complexity tolerance
- financial attention cadence
- life-load and available cognitive bandwidth
- relationship to money: hobby, tool, anxiety, duty, status, avoidance
- decision tempo: reactive, scheduled, delegated, instinctive, methodical
- fragmentation reality: single platform, multi-platform, household mix
- need for explanation: intuitive, evidence-seeking, reassurance-seeking

These axes create more realistic downstream divergence than pre-assigning product-shaped pain points.

## Panel design rule

`Panel design should maximize plausible human difference before testing concept response.`

Not:

`Panel design should maximize coverage of the concept's desired value propositions.`

## Anti-patterns

Avoid these:

- writing personas as disguised user stories for the product
- forcing every persona to produce one of the concept's headline pains
- assuming a feature named in the concept must matter to every participant
- treating relevance as mandatory rather than testable
- using panel presets to pre-route all participants into the same explanation
- collapsing stable context and study output into one field

## Good platform behaviours

Good platform behaviour looks like this:

- a retail investor with fragmented assets may still say current methods are fine
- a sophisticated investor may reject bank analytics as redundant
- a family planner may care more about education-goal translation than factor exposure
- a skeptical customer may ignore good analytics because the sales context destroys trust
- a beginner may not yet manage a real portfolio at all

These are not failures.

They are what makes the platform useful.

## Review checklist before changing schema or presets

Ask:

1. Does this field describe the person, or the likely study output?
2. If the concept changed tomorrow, would this still be true?
3. Are we encoding a pain because it is genuinely stable, or because we want the interview to surface it?
4. Would a real participant with this background necessarily mention this issue?
5. Are we preserving room for "no", "not really", "good enough", or "wrong problem" answers?

If the answer to 3, 4, or 5 is wrong, stop and redesign.

## Default decision

When there is tension between:

- cleaner concept coverage
- and more realistic participant variance

default toward more realistic participant variance.

That is the only path that moves the platform closer to replacing real interviews rather than merely staging synthetic agreement.
