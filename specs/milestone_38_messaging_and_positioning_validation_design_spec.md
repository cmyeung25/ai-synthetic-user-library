# Milestone 38: Messaging and Positioning Validation Design Spec

Status: implemented.

Owner layer: Frontline Research Studio, SaaS runtime plan inference, research playbook catalog, evidence boundary model.

Last updated: 2026-07-02.

## Purpose

Milestone 38 adds `messaging_validation` as a user-facing research capability for testing positioning, value proposition language, trust wording, and likely misunderstanding before acquisition spend.

This capability is not a product-adoption proof engine. It separates message comprehension and credibility from broader adoption behavior so users can inspect what a message causes people to understand, doubt, misread, or trust without overclaiming market demand.

## Alignment Check

- Research bottleneck improved: founders and product teams need to test whether target users understand and trust a message before building or spending.
- Primary improvements: evidence quality, decision prediction, and scalable concept evaluation throughput.
- North-star fit: message testing is part of replacing early interviewer-led concept evaluation, but only if transcript and evidence boundaries remain inspectable.

## User-Facing Scope

Messaging validation is exposed through natural-language guided setup and research playbooks, not as a required mode taxonomy choice.

The product may infer messaging validation when user intent mentions message, positioning, value proposition, headline, copy, landing page, tagline, or trust language.

## Evidence Boundary

Messaging validation must keep these evidence classes separate:

- message comprehension
- credibility objection
- trust language concern
- misunderstanding or false-positive appeal
- adoption boundary or human-validation gap

It must not collapse "people liked this wording" into proof of product adoption or market demand.

## Implemented Contract

- Runtime mode inference can classify plain-language message/positioning/copy intent as `messaging_validation`.
- Expected evidence types are mode-specific for message comprehension, credibility, trust, misunderstanding, and adoption-boundary review.
- Frontline setup can use the playbook metadata while still requiring explicit plan confirmation before execution.
- Evidence views, reports, decisions, and shares preserve synthetic-evidence boundary language.

## Acceptance Evidence

- `tests/unit/test_saas_runtime.py` verifies plan proposal mode inference into `messaging_validation` and playbook-driven rerun plan creation.
- `frontend/frontline_research_studio/src/main.jsx` renders the messaging playbook entry and selected playbook metadata in guided setup.
- `npm -C frontend/frontline_research_studio run build` passes after the messaging capability was added.

## Out of Scope

- Claiming message performance as human market proof.
- Replacing external ad tests, landing-page experiments, or human interviews for launch-grade demand validation.
- Forcing users to choose internal mode IDs before describing the research need.
