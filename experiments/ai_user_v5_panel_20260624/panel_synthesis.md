## AI User V5 Panel Synthesis

Date: 2026-06-24

### Synthetic Evidence Boundary

This result is synthetic research evidence only.
It is not yet a substitute for real user interviews, market tests, professional advice, or compliance review.

### Alignment Check

1. Research bottleneck improved:
   this synthesis is aimed at the early-stage bottleneck of deciding roadmap, concept direction, and feature priority before strong human evidence is available.
2. Capability improved:
   it improves decision-prediction quality and workflow-fit understanding more than presentation quality.
3. Replacement relevance:
   yes, because it tests whether synthetic users can replace part of interviewer-led discovery and pre-validation work rather than only summarizing outputs after the fact.

### Panel Scope

Interviews included:

- `su_2007` Janice Wong
- `su_2006` Mandy Cheung
- `su_2008` Maggie Leung Wai-ting

Source sessions:

- `observed_20260624_d3bac2d8`
- `observed_20260624_3fee80e1`
- `observed_20260624_c61e8fc6`

### Executive Read

Across all three personas, the strongest shared signal is not "let AI decide."
It is:

- use synthetic users before real human research
- use them to narrow where the real uncertainty is
- use them to expose likely hesitation, objection, trust gaps, and weak value exchange
- never treat them as standalone decision proof

The concept is strongest when framed as a pre-validation and synthesis-pressure tool inside early discovery, concept evaluation, and prototype validation.
It is weakest when framed as:

- market proof
- autonomous prioritization
- late-stage decision authority
- polished summary generation without evidence trace

### Shared Panel Signals

#### 1. All three want narrowing, not replacement of judgment

Common signal:

- Janice wants help narrowing what to validate next.
- Mandy wants help deciding which setup questions are asking for trust too early.
- Maggie wants help spotting where users must self-justify before moving forward.

Panel-level interpretation:

- the core value is not synthetic opinions
- the core value is structured pre-human decision support

#### 2. Trust depends on traceability, not fluency

All three personas rejected smooth summary-only output.

Common trust requirements:

- show the reasoning path
- show assumptions
- show the pattern behind the conclusion
- preserve contradiction
- keep minority or edge-case reactions visible
- allow some form of cross-check or reverse lookup

Panel-level interpretation:

- "good sounding output" is a liability, not a strength, if evidence trace is weak

#### 3. The product fits earliest in the workflow

The clearest workflow insertion points were all before final human validation:

- Janice:
  early prioritization when evidence is incomplete but there is still time to compare against analytics and notes
- Mandy:
  setup-flow and entrance-question decisions before real trial learnings are fully available
- Maggie:
  pre-synthesis mapping before formal review or before deciding what to probe with real users next

Panel-level interpretation:

- the product belongs before or between human-research steps
- it should shrink ambiguity upstream, not replace downstream validation

#### 4. Late-stage and high-risk use is rejected

Shared non-use boundary:

- do not use it when the issue is already near release
- do not use it when legal, billing, support, or comparable real-world risk dominates
- do not use it when the tool creates more verification work than it removes

Panel-level interpretation:

- adoption is bounded by decision reversibility
- the product is for early, still-malleable questions

### Persona-Specific Signals

#### Janice Wong

Her strongest signal is evidence triangulation.

- analytics tells her where the drop-off is
- user notes tell her why the hesitation exists
- synthetic users are acceptable only if they help narrow the next question without pretending to settle it

Most relevant use cases:

- onboarding
- activation
- positioning copy
- early concept-direction decisions

Main risk:

- becoming another layer she still has to defend without enough proof

#### Mandy Cheung

Her strongest signal is trust-for-value exchange at the product entrance.

- she notices when the product asks users to give trust before seeing value
- she is willing to act even without a larger sample if friction happens right at the doorway
- she wants help deciding what to remove, delay, or justify in setup

Most relevant use case:

- onboarding and setup-flow structure

Main risk:

- the tool becomes cleanup work if she still has to repair its hidden assumptions every time

#### Maggie Leung Wai-ting

Her strongest signal is preservation of nuance.

- she does not trust surface-level "it seems clear" feedback
- she watches for the moment users need to invent their own explanation before proceeding
- she wants the tool to preserve conflict, minority reactions, and edge cases

Most relevant use case:

- pre-synthesis mapping for prototype and concept review

Main risk:

- the system cleans the story too early and flattens the evidence

### Candidate Workflow Position

Based on the panel, the strongest workflow position is:

1. A team enters a concept, flow, message, or prototype before or between rounds of real research.
2. The system surfaces likely hesitation points, trust gaps, missing value exchange, and conflicting reaction patterns.
3. The team uses that output to:
   narrow what to test with real humans,
   sharpen what to ask next,
   and decide what should be simplified, delayed, or re-explained.
4. Real human research, analytics, or trials remain the decision-confirming layer.

This is most consistent with the repository north star:

- discovery
- concept evaluation
- prototype validation

### Strongest Supported Assumptions

Across the three interviews, these assumptions look directionally supported:

- there is a real pre-research and pre-decision bottleneck worth solving
- current workarounds are not clean enough when evidence is partial and time is tight
- synthetic users are more useful as directional narrowing than as proof
- transparency and evidence trace materially affect trust
- the workflow insertion point should be before real interviews, not instead of them

### Weakened Or Rejected Assumptions

These assumptions were weakened or rejected:

- the tool can be sold as a replacement for human judgment
- neat synthetic output by itself creates trust
- the strongest value is generic "research speed"
- the same tool framing works equally well in late-stage or high-risk decisions

### Product Direction Hypotheses

These are candidate hypotheses from this panel, not conclusions:

- The best first product wedge may be:
  "help me find where users hesitate, what they need to believe, and what I should validate next."
- The product may need three output layers:
  pattern summary,
  evidence trace,
  contradiction / minority view layer.
- A strong trust feature may be:
  side-by-side display of likely interpretation, assumptions, and plausible alternative readings.
- A strong adoption feature may be:
  workflow-specific entry points such as onboarding review, activation friction review, concept-screening review, or pre-synthesis map.

### Method Limits

This synthesis is useful, but still method-limited.

Important limits:

- Janice's run introduced the concept too early.
- Mandy and Maggie had better openings and better trust probing, but still missed some research-goal dimensions.
- across all three, the biggest missing probes were:
  public defensibility versus private worry,
  direct conflict handling between synthetic output and other evidence,
  and one fully explicit "what current step gets replaced" question.
- some workflow and retention interpretations remain hypothetical because the personas did not use the product in a live real workflow.

### Bottom Line

This three-person synthetic panel supports a narrower and stronger platform claim:

- AI users are most credible as a behaviorally plausible pre-validation layer that helps teams see likely hesitation, objection, and trust breakdown before they spend more on real research or build work.

This panel does not support a stronger claim that:

- synthetic users can replace final human validation,
- replace cross-functional judgment,
- or serve as decision-grade evidence on their own.

### Next Move

Best next step after this synthesis:

- tighten the interview protocol so every future panel must explicitly cover:
  missing evidence,
  pressure,
  public defensibility versus private doubt,
  conflicting evidence handling,
  and current-step replacement
- then rerun a stricter panel or compare this panel against one real-human interview set on the same workflow question

### Related Files

- Janice summary:
  `experiments/ai_user_v5_panel_20260624/deep_insight_single_interview_summary.md`
- Mandy and Maggie summary:
  `experiments/ai_user_v5_panel_20260624/additional_interviews_summary.md`
