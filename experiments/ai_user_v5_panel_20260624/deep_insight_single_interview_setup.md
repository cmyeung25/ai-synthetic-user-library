## Single-Person Deep-Insight Interview Setup

Date: 2026-06-24

### Alignment Check

1. Research bottleneck improved:
   current roadmap and feature-priority decisions are often made before strong user evidence is available, so we need to understand the participant's real decision process before testing where synthetic users fit.
2. Capability improved:
   this session is meant to improve behavioral realism and decision-prediction quality by eliciting how a real product operator weighs evidence, pressure, trust, and tradeoffs.
3. Replacement relevance:
   yes. this directly tests whether the platform can replace part of interviewer-led discovery or concept-shaping work, rather than only improving reporting.

### Why Start With One Persona

- The immediate goal is not breadth.
- The immediate goal is to test whether the deep-insight method can surface underlying motives, hidden constraints, and actual decision logic before concept reaction.
- If the method does not produce strong signal with one strong-fit persona, scaling to a three-person panel would add volume without stronger evidence.

### Selected Persona

- Persona ID: `su_2007`
- Name: Janice Wong
- Role fit: product manager
- Reason for selection:
  she is the strongest fit for roadmap and feature-priority decision questions and has explicit trust boundaries around weak evidence, tool claims, and stakeholder defensibility.

### Interview Design

- Mode: `concept_validation`
- Language: natural Cantonese Traditional Chinese
- Protocol: `src/ai_validation_swarm/prompts/concept-interview/ai-synthetic-user-platform-v1.md`
- Front-half emphasis:
  start from a recent real roadmap or feature-priority decision, then deepen on evidence, tradeoffs, hidden pressure, and what still felt uncertain.
- Concept timing rule:
  do not introduce the AI synthetic-user concept until the current-state process is concrete.
- Success criterion:
  the output should reveal not only what Janice says she does, but what she actually optimizes for when evidence is incomplete and time pressure is high.
