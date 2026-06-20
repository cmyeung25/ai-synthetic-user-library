# V3.2 Five-Person Quality Review

## Result

All five personas pass:

- V3.2 required-file validation
- nested biography and childhood contracts
- protected constraint checks
- enum-leakage checks
- general runtime `load_persona` artifact validation

The full unit suite passes with 140 tests.

## Persona Summary

| Persona | Main behavioral contribution | Strongest evidence | Main residual risk |
|---|---|---|---|
| Alex Chan | Discreet flexibility buyer | Audience-control mistake, interrupted caregiving schedule, photography purchase logic | May still interpret several domains through privacy and recoverability |
| Priya Wong | Exception-first systems evaluator | Reimbursement exception, editable budget categories, observation-versus-interpretation hobby logic | Highly articulate and unusually systematic for an ordinary interview participant |
| Aisha Tan | Continuity-first data minimizer | Staff absence visibility, repair ownership, untracked leisure | Privacy and data minimization remain dominant across many categories |
| Ethan Lee | Relational activation booster with retention risk | Guided customer success, shared household use, inconsistent social habits | Immediate enthusiasm can remain more vivid than his later drop-off behavior |
| Casey Patel | Audience-context and escalation calibrator | Screenshot risk, public claims, optional identity disclosure, archival curation | Communications expertise may make reactions more polished than mainstream users |

## Quantitative Checks

- Biography length: 1,958 to 2,272 words
- Research kernel length: 864 to 907 words
- Persona skill length: 1,246 to 1,366 words
- Decade chapters: complete through current age
- Childhood scenes: 3 per persona
- Childhood-to-adult links: 4 per persona
- Contradictions: 4 to 5 per persona
- Cross-domain reaction categories: 10 per persona
- Pairwise overall similarity: 0.1584 to 0.1803
- Highest recurring similarity dimension: sensitive-topic reactions, 0.3984 to 0.4939

## Quality Scores

| Dimension | Score | Assessment |
|---|---:|---|
| Structural completeness | 5.0/5 | Complete and runtime-loadable after the validator contract fix |
| Biography and childhood depth | 4.5/5 | Concrete ordinary scenes with explicit but bounded adult links |
| Behavioral distinctiveness | 4.5/5 | Five different motivation and objection models, not demographic reskins |
| Voice distinctiveness | 4.5/5 | Question-led, case-led, terse, energetic, and editorial voices are clearly separated |
| Hobby-to-behavior causality | 4.5/5 | Hobbies affect spending, trust, interface preference, discovery, and retention |
| Local grounding | 3.5/5 | Context is specific and plausible, but not retrieval-verified |
| Sensitive scenario quality | 3.8/5 | Scenario coverage is strong, but control/trust/visibility language still overlaps |
| Runtime readiness | 4.5/5 | All five now pass the general loader and protected constraint report |
| Corpus representativeness | 2.5/5 | All five are working professionals aged 31–51 in Asian cities with middle or upper-middle income |
| Audit independence | 2.5/5 | Current audit scores remain deterministic and too uniform |

## Important Findings

### What improved

- Ethan adds a genuinely trial-positive persona whose main problem is retention, not skepticism.
- Casey adds public-context and reputation-risk judgment without defaulting to bland or risk-averse product preferences.
- Childhood, hobbies, spending, voice, and product logic reinforce each other rather than appearing as separate lists.
- The generator now blocks incomplete runtime artifacts instead of allowing V3.2-only validation to create a false pass.
- Structured fairness profiles are now compatible with the general runtime validator while legacy string values remain accepted.

### What remains weak

- The sample does not cover low-income, unemployed, student, retired, rural, low-literacy, disabled, manual-worker, or non-managerial service populations.
- Local service and cultural details are LLM-authored and plausible, not verified against maintained regional reference packs.
- Each persona is unusually coherent about why they behave as they do. Runtime answers still need low-attention, contradictory, vague, and low-cooperation modes.
- Sensitive-topic blocks share common safety vocabulary. The next prompt revision should vary salience, silence, disengagement, private workaround, and selective confrontation more strongly.
- Five manually reviewed personas demonstrate output quality, not unattended scale reliability.
- Live Codex CLI and SDK generation remain blocked by the current websocket HTTP 403; these five are recorded Codex-thread generations with explicit provenance.

## Overall Assessment

Individual persona quality is approximately 4.2/5 and is suitable for POC validation. The five personas are behaviorally distinct and materially richer than the prior deterministic upgrade-chain outputs. Generator readiness for unattended large-scale production is lower, approximately 3.2/5, because live transport, independent auditing, local-reference verification, and population coverage are not yet solved.
