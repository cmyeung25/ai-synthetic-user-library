# Agent Workflow

## 0. Mandatory Alignment Check

Before starting work, confirm that the task supports the repository north star in [AGENTS.md](/C:/Users/user/OneDrive/%E6%96%87%E4%BB%B6/AI%20Synthetic%20User%20Library/AGENTS.md).

The task should strengthen at least one of:

- behavioral realism
- prediction of human decisions, objections, or adoption behavior
- evidence quality and calibration
- scalable workflows for discovery, concept evaluation, or prototype validation

If a task does not support one of these goals, it should be deprioritized or explicitly justified.

## 1. Agent Roles

### Synthetic User Agent

- loads a frozen persona
- responds to the brief or interview protocol in character
- surfaces realistic motivations, tradeoffs, and behavior

### Moderator Agent

- asks one focused follow-up at a time
- clarifies ambiguous or weak evidence

### Skeptic Agent

- challenges founder assumptions
- looks for weak logic, missing evidence, and over-claimed conclusions

### Sensitive Topic Auditor Agent

- reviews outputs for discrimination, stereotypes, privacy risk, and political sensitivity
- flags findings that need caution or exclusion

### Aggregator Agent

- compares segment reactions
- extracts objections, triggers, and major patterns
- summarizes confidence and risk themes

### Report Writer Agent

- writes the final Markdown report
- includes the required disclaimer and evidence boundary

### Real-World Validation Planner Agent

- converts open questions into next-step fieldwork
- proposes follow-up tests only where synthetic evidence is still weak

## 2. Standard Workflow

1. Load brief
2. Normalize brief
3. Load or sample personas
4. Run synthetic user responses
5. Run optional moderator follow-up
6. Run skeptic review
7. Run sensitive topic audit
8. Aggregate findings
9. Write final report
10. Archive artifacts

## 3. Inputs By Agent

- synthetic user agent: brief, protocol, persona
- moderator: persona response and transcript state
- skeptic: brief, sample summary, selected raw responses
- auditor: brief, responses, draft findings
- aggregator: responses, skeptic output, auditor output
- report writer: aggregated findings, auditor output, planner output

## 4. Prompt Versioning

Prompt families should remain versioned and inspectable.

- `persona-response/v1`
- `skeptic-review/v1`
- `sensitive-audit/v1`
- `report-writer/v1`

## 5. Failure Handling

- persona response timeout: retry with the same prompt version
- invalid JSON: repair or mark partial failure
- auditor failure: report the audit as incomplete
- provider failure: log model, provider, and error code

## 6. Run Artifacts

Each run should archive:

- normalized brief
- selected personas
- raw responses
- moderator outputs
- skeptic outputs
- audit findings
- aggregated summary
- final Markdown report
