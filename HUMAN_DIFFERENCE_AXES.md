# Human Difference Axes

Use this document when generating reusable personas, designing panel presets, or reviewing whether a synthetic interview sample is genuinely heterogeneous.

The purpose of human difference axes is to generate people before generating study conclusions.

They are not product pains.

They are not feature-priority buckets.

They are not segment labels invented to match the current concept.

They are the underlying dimensions of human variation that shape how a person notices problems, makes decisions, trusts institutions, uses tools, and responds in interviews.

## Why this exists

If personas are generated directly from project-shaped pain points, the panel becomes a disguised concept-confirmation exercise.

That produces:

- unnatural convergence
- less surprise
- weaker disconfirming evidence
- lower persona reuse
- lower realism in interviews

Human difference axes exist to prevent that.

## Platform rule

`Sample people on human variation first. Let pains, misunderstandings, and relevance emerge later.`

## What an axis is

A human difference axis is a stable dimension along which real people plausibly vary.

A good axis:

- applies across many studies
- is not tied to one product
- changes how a person interprets situations
- can influence multiple downstream behaviours
- helps explain divergence without pre-encoding the answer

## What an axis is not

These are not human difference axes:

- overlap-pain persona
- FX-risk persona
- wants stress tests
- needs RM support
- likely to buy premium analytics

Those are study outputs, domain-specific interpretations, or concept reactions.

## Recommended axis families

### 1. Control Preference

How strongly the person wants to stay personally in control of decisions and process.

Examples:

- high: wants to verify personally, dislikes black-box recommendations
- medium: accepts support but wants visibility
- low: comfortable delegating if trust is established

This axis often shapes:

- appetite for self-serve tools
- reaction to automation
- desire for explainability
- tolerance for RM involvement

### 2. Trust Style

How the person decides whether an institution, expert, or tool is credible.

Examples:

- institution-trusting
- evidence-trusting
- reputation-sensitive
- conflict-sensitive
- distrustful until proven otherwise

This axis often shapes:

- reaction to bank branding
- reaction to third-party brands
- tolerance for data sharing
- interpretation of recommendations

### 3. Complexity Tolerance

How much technical detail, ambiguity, or layered explanation the person can handle before disengaging.

Examples:

- low: wants simple summaries and clear takeaways
- medium: accepts detail if it is clearly useful
- high: comfortable with model assumptions, decomposition, methodology

This axis often shapes:

- preferred explanation format
- reaction to dashboards
- desire for raw detail versus guided interpretation

### 4. Decision Tempo

How quickly the person tends to move from observation to action.

Examples:

- reactive
- cautious
- scheduled and deliberate
- externally triggered

This axis often shapes:

- response to alerts
- use of reviews versus live monitoring
- whether insight leads to action or postponement

### 5. Financial Attention Cadence

How often the person pays active attention to financial decisions.

Examples:

- daily or market-attuned
- weekly check-in
- event-driven only
- reluctant and infrequent

This axis often shapes:

- what counts as a useful tool
- whether the person wants alerts
- whether a feature is part of a workflow or forgotten

### 6. Relationship To Money

What role money and investing play psychologically in the person's life.

Examples:

- hobby and mastery
- practical life tool
- security and stability
- family duty
- stress source
- identity/status signal
- necessary but avoided

This axis often shapes:

- how much energy they invest in understanding details
- emotional response to volatility
- what "success" means to them

### 7. Risk Orientation

How the person relates to downside, uncertainty, and trade-offs.

Examples:

- downside-sensitive
- growth-seeking
- income-stability-seeking
- uncertainty-avoidant
- willing to take risk if understood

This axis often shapes:

- response to scenario analysis
- whether they seek reassurance or opportunity
- what types of trade-offs feel acceptable

### 8. Need For Explanation

What kind of explanation the person needs before they trust or act.

Examples:

- intuitive story first
- evidence and decomposition first
- practical next-step first
- human confirmation first

This axis often shapes:

- UI copy preference
- RM demand
- reaction to summary scores or model outputs

### 9. Life Load

How much cognitive bandwidth the person realistically has in everyday life.

Examples:

- low load, lots of discretionary attention
- moderate load
- high load from work, caregiving, family admin, or health

This axis often shapes:

- patience for manual workflows
- openness to support tools
- preference for summaries versus exploration

### 10. Fragmentation Reality

The factual degree to which the person's relevant information is split across places, products, actors, or systems.

Examples:

- mostly one platform
- two or three systems
- highly fragmented across banks, brokers, household accounts, currencies, or documents

This axis is allowed because it is factual context, not yet a pain conclusion.

Important:

High fragmentation does not automatically mean high pain.

Some people tolerate fragmentation well.

### 11. Guidance Preference

What kind of support relationship the person is comfortable with.

Examples:

- self-serve first
- hybrid with optional human explanation
- expert-led if trust exists
- peer-influenced more than expert-influenced

This axis often shapes:

- use of RM
- use of app-only tools
- escalation behaviour after insight appears

### 12. Reflection Style

How the person tends to make sense of their own behaviour when interviewed.

Examples:

- articulate and introspective
- concrete but not abstract
- hesitant and under-specified
- rationalizing after the fact

This axis matters because real interviews do not only vary in beliefs.

They also vary in how well participants can explain themselves.

## Optional domain-linked axes

These can be used when appropriate, but only if they remain general enough to avoid becoming study conclusions.

Examples:

- digital fluency
- household financial centralization
- cross-border complexity
- dependence on recurring cash flow
- prior negative advisory experience
- portfolio review frequency

These are acceptable when treated as context, not as a forced concept fit.

## How axes should be used

### Step 1. Sample the skeleton

Choose a spread across human difference axes before generating biography details.

The axes should create meaningful variation in:

- how people notice issues
- what they optimize for
- what they ignore
- what they mistrust
- what they find overwhelming

### Step 2. Derive the person

Generate:

- demographics
- life context
- routines
- values
- domain context
- biographical memory

from the axis combination.

Do not reverse this order by deciding the target study output first.

### Step 3. Let the interview infer the rest

During the interview, the system should infer:

- whether the participant sees a problem
- what kind of problem it is
- whether current methods are good enough
- whether the concept matters
- which feature is valuable or irrelevant

These are interview-time discoveries.

## Constraints for realistic panels

A realistic panel should not converge too neatly on the same:

- trigger
- pain
- objection
- desired feature
- explanation format
- action tendency

It is acceptable for some overlap to happen.

It is not acceptable for the whole panel to look like variations of the same hypothesis.

## Good examples

Good persona divergence:

- one person mostly wants reassurance before the next trade
- one wants hidden overlap analysis
- one cares about monthly income continuity
- one cares about goal success probability
- one mainly wants to test RM credibility
- one mainly cares about FX and cross-market effects
- one thinks the whole feature may be well-designed but still untrustworthy

These outcomes can all emerge from stable human axes without hardcoding the result.

## Bad examples

Bad panel construction:

- every person is worried about concentration
- every person discovers ETF overlap in the opening
- every person wants the same dashboard element first
- every person says current workflow is fragmented
- every person lands at "this is useful if it is not sales"

That may happen occasionally in real life, but if it happens systematically, the platform is steering too much.

## Review checklist

Before accepting a persona set or preset, ask:

1. Are these people different as humans, or only different as packaging around the same study answer?
2. Could at least some of them legitimately say "this is not my main problem"?
3. Could at least some of them misunderstand the concept for reasons rooted in who they are?
4. Are we sampling life patterns and trust patterns, or are we sampling pre-decided feature needs?
5. If the concept changed tomorrow, would these personas still feel like useful people?

If the answer to 1 or 4 is bad, redesign the preset.

## Default rule

When there is a trade-off between:

- project-specific fit
- and reusable human realism

choose reusable human realism.

That is what keeps the platform aligned with the goal of approximating real interviews rather than staging synthetic agreement.
