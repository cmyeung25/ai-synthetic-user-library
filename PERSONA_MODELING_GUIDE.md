# Persona Modeling Guide

Use this guide before adding any new persona field, section, or generation requirement.

## First question

Ask:

`Does this describe who the person is, or how they react to this specific concept?`

- If it describes who the person is, consider `persona core`.
- If it describes a reaction to one concept, one prompt, one stimulus, or one interview setup, do not put it in core by default.

## Core vs Sidecar

### Put it in persona core when all are mostly true

- Reusable across future concepts, products, and studies
- Relatively stable over time
- Part of background, decision style, trust logic, constraints, or long-lived context
- Useful even if the current concept disappears
- Low risk of contaminating future tests

Examples:

- `banking_context`
- trust in banks
- investment experience
- advisory preference
- risk understanding level
- external asset fragmentation

### Keep it out of core when any of these are true

- It is a reaction to one concept card or one product framing
- It only exists because this study asked about it
- It may change materially when the concept wording changes
- Storing it in core would bias future interviews
- It is closer to an output than an identity trait

Examples:

- `aladdin_concept_reaction`
- first reaction to a pricing page
- opinion on one onboarding flow
- whether this specific concept would make them try

## Preferred storage layers

Use these layers in order:

1. `profile.json`
   Use for reusable persona traits and stable domain context.

2. `concept_outputs.json`
   Use for concept-specific structured reactions that are worth saving as artifacts.

3. interview/runtime response
   Use when the reaction should be generated live from persona + concept and does not need to become a reusable stored contract.

## Decision rules

### Add to core only after checking three tests

1. Reusability test
   If the current concept is removed, does the field still make sense?

2. Stability test
   Would the answer remain broadly true next month, with a different stimulus?

3. Contamination test
   If saved in core, would it distort a later study on another concept?

If any answer is `no`, default away from core.

## Practical pattern

For domain-heavy studies:

- put stable domain context into core
- put concept reaction contracts into sidecar outputs
- keep interview answers concept-bound unless they clearly generalize into stable persona structure

Example:

- `banking_context` belongs in core
- `portfolio_health_check` reaction belongs in `concept_outputs.json`

## Anti-patterns

Avoid these:

- putting concept-specific appeal/concern fields into reusable core
- treating one interview answer as a stable persona truth
- expanding core just because a field is useful in one POC
- mixing identity, context, and evaluation output in the same section

## Default rule

When unsure, keep the core smaller.

It is safer to add a sidecar artifact now than to pollute the persona library with concept-specific memory.
