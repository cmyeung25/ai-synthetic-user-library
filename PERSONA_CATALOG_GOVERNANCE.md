# Persona Catalog Governance

## Objective

Provide the bridge from the current enum-based persona generator to a large, governed persona catalog suitable for 10k to 1M synthetic users.

## From Enum Generator to Catalog System

### Current POC State

- hardcoded option lists
- one-pass seeded enrichment
- local filesystem artifacts
- basic persona validation

### Required SaaS State

- versioned trait catalogs
- locale packs
- market overlays
- distribution planner
- quality scoring pipeline
- similarity governance
- lifecycle management for stale or low-quality personas

## Catalog Layers

### Layer 1: Trait Catalogs

- identity catalogs
- work and economic catalogs
- behavior catalogs
- life-stage catalogs
- accessibility and capability catalogs
- privacy and boundary catalogs

### Layer 2: Distribution Planner

- consumes market-distribution config
- converts target weights into seed quotas
- applies quota floors / caps and exclusion rules

### Layer 3: Persona Generation Pipeline

1. generate structural seeds
2. enrich values, life story, behavior, and decision policy
3. audit plausibility and stereotype risk
4. score uniqueness and quality
5. accept, reject, merge, or rewrite

### Layer 4: Sampling Index

- fast retrieval by panel role, locale, price sensitivity, trust style, and market tags
- seeded reproducible sampling
- explainability metadata for why a panel was assembled

## Deduplication / Similarity Governance

### Similarity Dimensions

- structural similarity
- narrative similarity
- decision-policy similarity
- risk-profile similarity

### Governance Actions

- `keep`
- `merge`
- `rewrite`
- `reject`

### Recommended Thresholds

- `>= 0.92`: auto-flag for merge or reject review
- `0.85 - 0.92`: human or policy-based review queue
- `< 0.85`: keep unless another quality gate fails

These thresholds should stay configurable because markets differ in acceptable density and diversity.

## Quality Score Stack

Each catalog entry should carry:

- consistency score
- plausibility score
- uniqueness score
- stereotype risk score
- audit completeness score
- panel-fit score

Low-quality personas should never silently enter the production catalog.

## Market-Distribution Configuration Model

The market config is the control surface that replaces ad hoc enum tweaking.

It should define:

- weighted dimensions
- minimum / maximum quota rules
- exclusion rules
- overlays for locale, product category, or regulatory context

The sample configs in [default_b2b_saas.json](</C:\Users\user\OneDrive\文件\AI Synthetic User Library\configs\markets\default_b2b_saas.json>) and [hk_smb_ops.json](</C:\Users\user\OneDrive\文件\AI Synthetic User Library\configs\markets\hk_smb_ops.json>) are the first step toward that model.

## Recommended Jobs in SaaS Phase

- catalog batch generation
- dedupe sweep
- similarity recluster
- quality-score recompute
- stale persona refresh
- fairness and safety regression scan
- coverage heatmap recompute

## Operational Guardrails

- do not target protected groups directly as product recommendations
- do not let sensitive attributes leak into exclusionary segmentation language
- retain full provenance: seed version, generation version, audit version
- separate global catalog from workspace overlays

## Phase Plan

### Phase A: 500 Personas

- trait catalogs
- market configs
- quality score contract

### Phase B: 10,000 Personas

- similarity index
- dedupe queue
- coverage dashboard

### Phase C: 100,000 Personas

- locale packs
- market overlays
- trait drift checks

### Phase D: 1,000,000 Personas

- distributed generation
- reclustering jobs
- lifecycle and archive policy

