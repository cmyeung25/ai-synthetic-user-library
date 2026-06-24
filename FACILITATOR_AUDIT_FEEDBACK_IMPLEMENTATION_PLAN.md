# Facilitator Audit Feedback Implementation Plan

## Objective

Turn `facilitator_audit_feedback` from a design principle into a real platform capability.

The implementation must:

- produce a structured offline facilitator-audit artifact
- keep feedback generic and reusable
- block project-specific contamination
- prepare the platform for safe facilitator evolution

This document focuses on the actual next engineering step, grounded in the current codebase.

## Current State

The platform already has three adjacent building blocks:

1. Structured facilitator quality evaluation
   - [src/ai_validation_swarm/facilitator/providers.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/providers.py:239)
   - `FACILITATOR_QUALITY_SCHEMA`
   - `evaluate_quality(...)`

2. Structured persona-side post-hoc audit
   - [src/ai_validation_swarm/conversation/providers.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/conversation/providers.py:1)
   - current `persona_driver_trace`

3. Interview runtime pattern for generating extra artifacts after synthesis
   - [src/ai_validation_swarm/facilitator/runtime.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/runtime.py:70)
   - synthesis is produced
   - then `persona_driver_trace` is generated
   - then artifacts are written to session folder

This means the platform does not need a brand-new architecture.
It needs one more structured artifact in the same family.

## Core Problem With Current Quality Output

Current `quality_evaluation` is useful, but it is not the right shape for safe facilitator learning.

Why:

- it mixes interview QA with prompt suggestions
- it is not explicitly filtered for project-specific contamination
- it does not force a reusable generic error taxonomy
- it does not separate "good local critique" from "safe global carry-forward rule"

Example risk:

- `next_interview_focus` may contain a valid suggestion for the current project
- but that suggestion may be unsafe to generalize into future facilitator behavior

So the new artifact should not replace `quality_evaluation`.
It should sit beside it.

## Proposed Deliverable

Add a new post-hoc artifact:

- `facilitator_audit_feedback.json`

Optional paired markdown:

- `facilitator_audit_feedback.md`

This artifact should be generated after:

1. transcript exists
2. insight report exists
3. quality evaluation exists
4. persona driver trace exists when available

This ordering matters because the audit should be able to inspect:

- what the facilitator asked
- what the participant said
- what the synthesis inferred
- what the quality evaluator already flagged
- what the driver trace later revealed as missed depth

## Recommended Phase Order

### Phase 1

Generate the artifact only.

Do not yet:

- inject anything back into facilitator prompt
- modify panel selection
- change stop rules

This phase is for observability, not learning.

### Phase 2

Add safe filtering and distillation:

- raw auditor output
- blocked feedback
- generic carry-forward rules

Still do not inject raw output.

### Phase 3

Inject only filtered `carry_forward_rules` into future runs in a bounded way.

## Proposed Runtime Shape

### New Prompt

Add a new prompt file:

- `src/ai_validation_swarm/prompts/facilitator-audit-feedback/v1.md`

Its job:

- review a completed interview or panel result
- produce only generic facilitator learning signals
- explicitly block project-specific feedback

This prompt should reference the schema in [FACILITATOR_AUDIT_FEEDBACK_SCHEMA.md](C:/Users/user/OneDrive/文件/AI Synthetic User Library/FACILITATOR_AUDIT_FEEDBACK_SCHEMA.md).

### New Provider Schema

Add a new structured schema in [src/ai_validation_swarm/facilitator/providers.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/providers.py:1).

Recommended constant name:

- `FACILITATOR_AUDIT_FEEDBACK_SCHEMA`

Recommended required top-level fields for v1:

- `artifact_version`
- `feedback_scope`
- `applies_to`
- `summary`
- `facilitator_feedback_tags`
- `high_value_missed_followups`
- `prompt_adjustments`
- `blocked_feedback`

Recommended optional but useful fields:

- `likely_misclassified_driver_patterns`
- `evidence_handling_issues`
- `carry_forward_rules`

### New Provider Method

Extend `FacilitatorProvider` with:

```python
def generate_audit_feedback(
    self, *, system_prompt: str, user_prompt: str, provider_session_id: str = "",
) -> tuple[dict[str, Any], str]: ...
```

Implement this in `OpenAIFacilitatorProvider` the same way `evaluate_quality(...)` and `synthesize_concept(...)` already work.

### New Session Fields

Extend [src/ai_validation_swarm/facilitator/models.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/models.py:35) with:

- `facilitator_audit_feedback_prompt_version`
- `facilitator_audit_feedback_provider_session_id`
- `facilitator_audit_feedback`

This keeps the audit artifact first-class and resumable.

## Recommended Generation Order In Interview Runtime

In [src/ai_validation_swarm/facilitator/runtime.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/runtime.py:70), the new post-run order should be:

1. run interview
2. generate synthesis
3. generate persona driver trace
4. generate quality evaluation if that run mode includes it
5. generate facilitator audit feedback
6. save all artifacts

Why this order:

- the audit should see the transcript
- it should see the synthesis
- it should see the quality evaluation
- it should see persona driver trace if present

The audit is an offline meta-review layer, so it should be last among diagnostic artifacts.

## Proposed User Prompt Contents For Audit Generation

The audit prompt input should include:

- interview mode
- research goal
- product context
- concept label if any
- stop reason
- coverage status
- transcript
- facilitator trace
- insight report
- quality evaluation
- persona driver trace

Important:

- persona hidden profile should not be passed directly unless there is a separate deliberate policy allowing it
- for v1, use only runtime artifacts already produced from the interview

Reason:

- we want to improve facilitator behavior based on what happened in the interview
- not based on hidden ground truth unavailable to the facilitator at run time

This keeps the learning loop honest.

## Why `persona_driver_trace` Should Be Input But Not Authority

`persona_driver_trace` is useful because it exposes missed follow-ups and likely drivers.
But it should be treated as:

- one offline inference aid

not:

- privileged truth

So the audit prompt should instruct:

- use driver trace as a candidate source of missed depth
- do not promote any driver pattern without transcript support

## Safe Filter Design

This should be a distinct normalization layer after the raw audit is generated.

Recommended helper:

- `normalize_facilitator_audit_feedback(payload: dict[str, Any]) -> dict[str, Any]`

Recommended validator:

- `validate_facilitator_audit_feedback(payload: dict[str, Any]) -> None`

Recommended filter responsibilities:

1. ensure all required top-level fields exist
2. block named concepts, brands, segments, markets, or asset classes in carry-forward rules
3. move unsafe rules into `blocked_feedback`
4. require `carry_forward_rules` to be short, generic, and domain-agnostic
5. downgrade `safe_for_global_reuse` when contamination is detected

### Examples of Strings That Should Trigger Blocking

These are examples of unsafe feedback content:

- "Ask about MPF overlap next time"
- "Probe Aladdin brand trust earlier"
- "Hong Kong retail customers fear RM upsell"
- "Portfolio Health Check should appear in the wealth dashboard"

These belong in:

- `blocked_feedback`

Possible generic rewrites:

- "If a participant identifies one opaque asset bucket, probe what that opacity prevents them from knowing about the whole picture."
- "If a participant introduces a trust boundary, clarify whether the boundary is about data scope, sequence, or sales intent."

## Markdown Renderer

Add a small renderer in runtime, similar to current trace renderers.

Recommended output sections:

- overall assessment
- feedback tags
- missed high-value follow-ups
- likely misclassified driver patterns
- prompt adjustments
- blocked feedback

This is useful because:

- the JSON is machine-usable
- the markdown is easier for human prompt tuning and review

## File Output Recommendation

Each interview folder should store:

- `facilitator_audit_feedback.json`
- `facilitator_audit_feedback.md`

If regeneration happens, follow the same convention used elsewhere:

- `facilitator_audit_feedback.previous.json`

only if a rerun actually overwrites an existing artifact

## Panel-Level Behavior

For v1, do not generate a panel-level audit from scratch first.

Instead:

1. generate per-interview `facilitator_audit_feedback`
2. later aggregate them in `concept_panel.py`

This is the safer route because:

- single-interview failures are easier to localize
- aggregation can remain generic
- it mirrors how `persona_driver_trace` is currently handled

## Panel Summary Integration

Once per-interview artifacts exist, [src/ai_validation_swarm/facilitator/concept_panel.py](C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/facilitator/concept_panel.py:1) can later aggregate:

- common facilitator failure tags
- most common missed follow-up trigger types
- common blocked feedback patterns
- most common generic carry-forward rules

But this should be Phase 2, not Phase 1.

Phase 1 should avoid turning panel summaries into an automatic learning system.

## CLI Exposure

Recommended CLI changes after artifact generation works:

- display path to `facilitator_audit_feedback.md`
- display path to `facilitator_audit_feedback.json`

This mirrors how `persona_driver_trace.md` is already surfaced.

## Test Plan

Minimum unit tests for v1:

1. provider returns artifact with required keys
2. validator rejects missing required fields
3. normalizer moves unsafe carry-forward rules into `blocked_feedback`
4. runtime writes JSON and markdown artifacts
5. rerun preserves existing behavior if audit generation fails

Recommended integration tests:

1. completed interview produces audit artifact
2. panel loader tolerates folders without the new artifact
3. markdown renderer prints high-value missed follow-ups and blocked feedback clearly

## Failure Handling

Audit generation must not destroy the interview result if it fails.

Recommended behavior:

- mark `failed_operation = "generate_facilitator_audit_feedback"`
- keep transcript and insight report intact
- leave the interview usable
- save partial state

This should follow the same resilience pattern already used around driver-trace and quality failures.

## Best v1 Boundary

The right first implementation is:

- per-interview only
- artifact generation only
- generic schema only
- safe filter included
- no self-learning injection yet

That is enough to validate:

- whether the auditor can reliably produce generic feedback
- whether contamination is common
- whether the resulting rules are actually reusable

## Recommended Immediate Engineering Step

Implement Phase 1 in this exact order:

1. add prompt `facilitator-audit-feedback/v1.md`
2. add schema and provider method in `facilitator/providers.py`
3. add session fields in `facilitator/models.py`
4. add runtime generation and file output in `facilitator/runtime.py`
5. add markdown renderer
6. add unit tests
7. do not yet inject output back into facilitator prompt

## Why This Is The Right Next Step

Because the platform's current gap is not "the facilitator cannot be critiqued."
The gap is:

- critique exists
- but it is not yet structured into a safe, reusable learning artifact

This plan fixes that exact gap without prematurely creating a self-reinforcing feedback loop.
