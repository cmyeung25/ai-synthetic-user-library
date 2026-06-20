# Development Roadmap

## Milestone 0: Architecture & Harness Plan

交付：

- product brief
- harness plan
- system architecture
- data model
- workflow
- safety policy
- evaluation plan
- roadmap
- folder structure

Exit criteria：

- 技術方向明確
- POC 邊界清楚
- schema 與 run artifact 已定義

## Milestone 1: Local Persona Generator

交付：

- demographic seed generator
- persona enrichment prompts
- 50 個 sample personas
- JSON / SQLite storage
- basic consistency checks

Exit criteria：

- persona 可生成、可儲存、可讀回
- persona audit metadata 存在
- 明確註記目前為小型 option set 的 POC 版本，不當成最終 persona vocabulary

## Milestone 2: Sampling Engine

交付：

- panel presets
- target market filters
- deterministic sampling
- sample explainability

Exit criteria：

- 可重跑
- 可解釋
- panel 差異清晰

## Milestone 3: Validation Runner

交付：

- founder brief loader
- persona response runner
- retry / error handling
- raw response storage

Exit criteria：

- 同一 brief 可讓多人格回應
- artifacts 完整保存

## Milestone 4: Auditor & Aggregator

交付：

- sensitive topic auditor
- skeptic agent
- aggregation logic
- objection clustering
- segment summary

Exit criteria：

- 可輸出安全格式風險觀察
- 可形成整體結論

## Milestone 5: Report Generator

交付：

- Markdown report
- JSON export
- run archive index
- sample report

Exit criteria：

- founder 可閱讀
- 章節完整
- disclaimer 正確注入

## Milestone 6: Evaluation Harness

交付：

- fixture suite
- deterministic tests
- safety tests
- manual rubric

Exit criteria：

- core quality gate 可自動檢查
- 變更後可做 regression comparison

## Milestone 7: SaaS Readiness Design

交付：

- service decomposition
- multi-tenant data model
- queue / async design
- auth / billing / privacy design
- persona diversity engine roadmap
- large-scale persona catalog strategy
- deduplication / similarity governance
- market-distribution configuration model

Exit criteria：

- POC 核心可被抽離成 SaaS backend
- 已規劃從小型 enum-based generator 遷移到 large-catalog generator

## 建議實作順序

1. 建 repo structure
2. 定 schema 與 sample configs
3. 寫 persona generator
4. 寫 sampler
5. 寫 validation runner
6. 寫 auditor / aggregator
7. 寫 report generator
8. 補 tests 與 sample fixtures
