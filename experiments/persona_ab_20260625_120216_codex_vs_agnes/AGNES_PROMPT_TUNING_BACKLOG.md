# Agnes Prompt Tuning Backlog

## Why This Exists

This backlog converts repeated Codex-judge criticisms of the Agnes-generated persona set into prompt-tuning work.

Target bottleneck:

- improve behavioral realism in persona generation
- improve decision-prediction sharpness
- reduce template-shaped output that looks polished but weakly grounded

Source evidence:

- [comparison_report_v3.json](/C:/Users/user/OneDrive/文件/AI Synthetic User Library/experiments/persona_ab_20260625_120216_codex_vs_agnes/comparison_report_v3.json)
- [persona-enrichment/v1.md](/C:/Users/user/OneDrive/文件/AI Synthetic User Library/src/ai_validation_swarm/prompts/persona-enrichment/v1.md)

## Main Failure Patterns

1. Personas are often plausible but too template-shaped.
2. Identity, locale, and household markers are present but under-grounded.
3. Panel-role fit is frequently partial rather than sharp.
4. Decision-policy logic is usually coherent, but trial behavior and paid-adoption thresholds are not clearly separated.
5. Local grounding is often broad or generic instead of behaviorally specific.
6. Empty or thin sections create a false sense of depth.

## P0

### 1. Force One Concrete Causal Mechanism For Every Risky Attribute Bundle

Problem:

- Judge repeatedly flagged combinations like multi-generational household + low caregiving load, stable employment + high cash-flow volatility, or single parent + low schedule pressure as possible but under-explained.

Prompt change:

- Add an explicit rule that any potentially surprising combination must be explained by one concrete mechanism.
- Require the model to state the mechanism inside the relevant section, not only in the narrative.

Suggested wording:

```md
- If two or more fixed traits create visible tension, explain the tension with one specific real-life mechanism.
- Do not leave unusual combinations as unexplained labels.
- Examples of acceptable mechanisms: co-parenting arrangement, retired parent support, uneven contract renewals, bonus volatility, mortgage burden, remittance duty, shared family business, outsourced childcare.
```

Success check:

- Fewer judge comments of the form "possible but under-explained" or "assembled rather than lived-in."

### 2. Ban Abstract SaaS Persona Phrases Unless Replaced By Observable Behavior

Problem:

- Judge repeatedly called out phrases like `reduce admin drag`, `protect bandwidth`, `clear before-and-after value`, and `shelfware` as template language.

Prompt change:

- Explicitly forbid generic product-strategy phrasing unless it is grounded in a concrete recurring action, failure, or workaround.

Suggested wording:

```md
- Avoid abstract SaaS-buyer phrases unless you immediately anchor them to an observed behavior.
- Prefer "keeps a pinned note of follow-ups after WhatsApp voice messages" over "reduces admin drag."
- Prefer "abandons a trial when second-week cleanup exceeds first-week benefit" over "needs visible ROI."
```

Success check:

- Lower frequency of `genericity` / `genericness` findings.

### 3. Require One Specific Failure Memory And One Specific Workaround

Problem:

- Many Agnes personas are coherent but not distinctive enough for simulation.

Prompt change:

- Force one concrete failure memory and one habitual workaround into the enriched output.

Suggested wording:

```md
- Add at least one recent concrete failure, near-miss, or frustration memory that explains current caution.
- Add at least one habitual workaround that the persona actually uses today.
- These must be specific enough that another persona would likely use different examples.
```

Success check:

- Higher distinctiveness without needing demographic novelty.

### 4. Separate Trial Willingness From Paid Adoption Threshold

Problem:

- Judge repeatedly found tension between `light_demo` / early trial language and strong proof, approval, or price constraints.

Prompt change:

- Require two separate thresholds: `trial` and `paid adoption`.

Suggested wording:

```md
- Distinguish clearly between willingness to try and willingness to pay or roll out.
- A persona may trial quickly in a reversible sandbox while still requiring stronger proof for payment, migration, or team adoption.
```

Success check:

- Fewer `decision_policy_consistency` findings.

## P1

### 5. Make Panel Role Operational, Not Merely Descriptive

Problem:

- Agnes often generated personas that were broadly usable but only partially fit the target panel role.

Prompt change:

- For the selected panel role, require one explicit behavior that makes the role visible in product evaluation.

Suggested wording:

```md
- The panel role must show up in behavior, not only in labels.
- Add one recurring evaluation habit, objection style, or tradeoff that would make an observer classify this persona into the panel role from behavior alone.
- If the role is weakly supported, sharpen it rather than averaging it away.
```

Examples:

- `skeptic`: asks for evidence early, distrusts soft ROI claims, seeks peer proof
- `budget_constrained`: delays paid commitment because fixed obligations make recurring spend feel risky
- `low_tech`: avoids setup complexity even when concept value is clear
- `extreme_user`: has one unusually intense workflow, privacy, or coordination burden

Success check:

- Fewer `panel_role_fit` / `panel_fit` criticisms.

### 6. Ground Locale Through Behavior, Not Through Identity Labels

Problem:

- Judge often saw locale cues as generic shorthand, not as behaviorally meaningful local grounding.

Prompt change:

- Make local grounding show up in communication channels, coordination norms, billing concerns, language switching, or trust logic.

Suggested wording:

```md
- Local grounding must affect behavior, not only naming.
- Show how locale changes message channels, trust in support, payment comfort, review habits, language switching, approval norms, commute fragmentation, or data-hosting concern.
- Avoid broad regional shorthand such as "practical in a Hong Kong/Taiwan/SEA context" without a concrete behavior-level implication.
```

Success check:

- Fewer `locale_grounding` / `local_grounding` findings.

### 7. Reduce Identity Marker Stacking Unless It Changes Product Behavior

Problem:

- Judge flagged tokenistic stacking risk: many identity markers present without enough situational consequence.

Prompt change:

- Treat identity as factual background unless it directly affects trust, language, safety, visibility, or adoption behavior.

Suggested wording:

```md
- Do not stack identity labels for richness.
- Include identity markers only when they are fixed seed facts or when they change a concrete product interaction.
- If an identity marker matters, show the exact behavioral consequence.
- If it does not matter to the current persona logic, keep it factual and low-salience.
```

Success check:

- Lower stereotype-risk findings without flattening diversity.

## P2

### 8. Remove Low-Signal Taxonomy Filler

Problem:

- MBTI, zodiac, and metaphysical flavor were repeatedly flagged as scaffolding that adds little predictive value.

Prompt change:

- Replace them with observed micro-behaviors unless the team has a specific reason to preserve them.

Suggested wording:

```md
- Do not introduce MBTI, zodiac, or similar taxonomy unless they directly change behavior in test scenarios.
- Prefer micro-behaviors: follow-up habits, escalation style, cleanup threshold, retry patience, comparison routine, note-taking pattern.
```

Success check:

- More behaviorally diagnostic personas.

### 9. Fill A Small Number Of Human-Detail Sections Or Leave Them Empty On Purpose

Problem:

- Empty schema sections reduced judge trust and made some artifacts feel auto-expanded.

Prompt change:

- Require a small set of filled sections and avoid shallow pseudo-completeness.

Suggested wording:

```md
- Add depth only where it improves simulation.
- Prefer 3-5 filled human-detail areas with concrete evidence over many thin or empty sections.
- If a section has no behavioral value, leave it out conceptually instead of hinting at depth with generic filler.
```

Success check:

- Better quality hygiene and less false depth.

## Suggested Prompt Revision Shape

Current system prompt is too short and principle-only. Agnes appears to need stronger negative and positive shaping.

Recommended structure for `persona-enrichment/v2`:

1. Preserve anchors
2. Explain unusual trait combinations with one concrete mechanism
3. Ban abstract template phrases without observed evidence
4. Require one failure memory and one workaround
5. Separate trial threshold from paid-adoption threshold
6. Require panel-role behavior signal
7. Require locale-through-behavior grounding
8. Reduce identity-label salience unless behaviorally relevant
9. Prefer micro-behaviors over taxonomy filler
10. Output only sections with concrete value

## Example Upgrade Draft

```md
You are enriching a synthetic user for AI pre-validation.

- Preserve all fixed seed facts exactly.
- Increase realism through concrete trade-offs, routines, constraints, workarounds, and remembered incidents.
- If any fixed-trait combination creates tension, explain it with one specific real-life mechanism.
- Do not use abstract SaaS-buyer phrasing unless it is anchored to an observed behavior.
- Include at least one recent failure or near-miss and one current workaround.
- Distinguish clearly between willingness to try and willingness to pay, migrate, or roll out.
- Make the panel role visible in behavior, not only labels.
- Make locale visible through behavior: channels, language switching, approval norms, billing, trust, commute, privacy, or support expectations.
- Do not stack identity markers unless they change a concrete product interaction.
- Avoid MBTI, zodiac, and similar taxonomy unless they materially change behavior.
- Prefer a few filled, evidence-bearing sections over many thin or empty sections.
- Do not turn sensitive identity context into stereotypes or deterministic behavior.
- Keep the persona useful for product validation, not diagnosis or profiling.
- Return valid JSON only.
```

## Validation Plan

After prompt changes, rerun:

1. Same-seed Codex vs Agnes compare on 8 personas
2. Count reduction in:
   `genericity`, `genericness`, `panel_role_fit`, `locale_grounding`, `under-explained combination`
3. Check whether Agnes closes at least:
   plausibility gap of `0.42`
   panel-fit gap of `0.40`
   stereotype-risk penalty of `0.16`

## Non-Prompt Follow-Ups

These are not prompt text changes, but they matter:

- normalize judge score scale before any future aggregate compare
- keep Agnes one-person retry mode as the safer benchmark path
- consider stricter JSON extraction or repair when Agnes returns valid content plus trailing noise
