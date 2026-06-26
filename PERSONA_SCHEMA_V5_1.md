# Persona Schema v5.1

`v5.1` is the active testing-phase persona contract.

The goal is to separate:

- stable person-level differences
- relational / psychological stance
- baseline conversation behavior
- runtime friction settings

## Core Rule

- `human_difference_axes` remain person-level traits.
- `friction_mode` remains a runtime/session control and is not persona truth.
- New `v5.1` blocks explain why a persona may show hesitation, misunderstanding, disinterest, short answers, permission concerns, or revision during an interview.

## New Optional Profile Fields

These are additive optional fields within the `v5.1` profile contract. Native `v5.1` generation should emit them.

### `relational_defense_model`

Required fields when present:

- `self_other_position`
- `default_trust_posture`
- `defensive_style`
- `status_sensitivity`
- `attribution_style`
- `conflict_pattern`
- `withdrawal_pattern`

Purpose:

- describes the persona's stable self-other and trust-protection posture
- should not be used as a synonym for friction or "bad personality"

### `communication_behavior_model`

Required fields when present:

- `baseline_answer_length`
- `clarification_tendency`
- `misunderstanding_risk`
- `topic_drift_tendency`
- `memory_lapse_tendency`
- `revision_tendency`
- `disinterest_expression_style`
- `permission_sensitivity`
- `pricing_confusion_risk`
- `dropoff_style`

Purpose:

- describes baseline conversational tendencies
- explains likely transcript behavior without turning every behavior into a runtime switch

### `behavior_generation_rules`

Expected shape when present:

- list of rule objects
- each rule should include `when`, `then`, `because`, `source`

Purpose:

- explicit mapping from person-level traits to expected conversation behavior
- used by runtime prompts and realism analysis

### `persona_schema_meta`

Required fields when present:

- `schema_version`
- `source_version`
- `upgrade_strategy`
- `optional_blocks_present`
- `canonicalizations_applied`

Purpose:

- records schema provenance and any internal canonicalization applied inside the `v5.1` contract

## V5 -> V5.1 Fallback Mapping

The fallback policy is additive. Existing authored `v5` values remain the source of truth. `v5.1` only backfills the new optional blocks when they are absent.

### `persona_schema_meta`

Fallback mapping:

- `schema_version` -> `v5.1`
- `source_version` -> `v5`
- `upgrade_strategy` -> `fallback_from_v5`
- `optional_blocks_present` -> derived after upgrade
- `canonicalizations_applied` -> list of actual fallback steps applied at load or generation time

### `relational_defense_model`

Fallback derivation inputs:

- `human_difference_axes`
- `technology_profile.privacy_concern`
- `values.fears`
- `emotional_regulation_style`

### `communication_behavior_model`

Fallback derivation inputs:

- `human_difference_axes`
- `product_reaction_rules.questions_they_would_ask`
- `objection_language_style.polite_objection_examples`

### `behavior_generation_rules`

Fallback derivation inputs:

- `human_difference_axes`
- `relational_defense_model`
- `communication_behavior_model`

Runtime implication:

- current runtime may open a legacy `v5` persona folder
- the profile is upgraded in memory to a `v5.1` behavioral contract before interview prompts are built
- native `v5.1` artifacts remain the preferred storage format

## Testing Phase Policy

- current work treats `v5.1` as the active persona contract
- legacy `v5` is supported only through the explicit fallback mapping above
- the generator may derive internal `behavior_generation_rules` defaults when they are not authored explicitly, and the same derivation logic is reused for `v5 -> v5.1` fallback upgrade

## Runtime Usage

Runtime should combine:

- `human_difference_axes`
- `relational_defense_model`
- `communication_behavior_model`
- `behavior_generation_rules`
- session-level `friction_mode`

Recommended interpretation:

- persona fields explain what this person tends to do
- `friction_mode` controls how strongly the interview should let those tendencies surface
