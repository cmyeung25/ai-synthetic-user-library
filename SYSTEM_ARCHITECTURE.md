# System Architecture

## 1. 架構決策

基於目前 workspace 為空，第一版 POC 建議採用：

- 語言：Python 3.11+
- 介面：CLI
- 持久化：local JSON + SQLite
- 報告：Markdown
- 設定：`.env` + versioned YAML / JSON
- prompts：檔案化管理，不散落在程式碼中

選 Python 的原因：

- 最少工程量即可完成 CLI、JSON Schema、SQLite 與報告生成
- 易於後續接多個 LLM provider
- 易於建立 deterministic test fixtures

## 2. 核心模組

### Ingress Layer

- brief loader
- schema validator
- config loader

### Persona Layer

- persona generator
- persona registry
- persona storage
- persona consistency checker

### Sampling Layer

- target-market matcher
- panel preset selector
- seeded sampler
- sample explainability writer

### Validation Layer

- protocol runner
- synthetic user responder
- moderator follow-up
- skeptic reviewer

### Safety Layer

- sensitive topic auditor
- forbidden-output checks
- report disclaimer injector

### Report Layer

- aggregation engine
- Markdown report writer
- JSON artifact exporter

### Infrastructure Layer

- LLM provider abstraction
- run archive manager
- observability logger
- retry / error handler

## 3. POC 高層流程

1. 讀取 founder brief
2. validate + normalize brief
3. 載入 persona library
4. 根據 target market + panel spec 抽樣
5. 逐一執行 persona response protocol
6. 執行 moderator / skeptic / auditor
7. 整合 report
8. 保存完整 run archive

## 4. 建議的邊界切法

未來 SaaS 化時，以下模組應可直接沿用：

- domain models
- sampling engine
- validation protocols
- auditor
- report generator
- provider abstraction

未來需要替換或擴展的模組：

- CLI ingress -> API server
- local file archive -> object storage
- SQLite -> PostgreSQL
- local execution -> queue / async workers

## 5. 與 `dot-skill` 的關係

可借用的方向：

- skill-as-files
- persona 與任務能力分層思維
- prompt / tool 資產版本化
- host-agnostic content assets

不建議直接依賴：

- 宿主安裝流程
- slash command entrypoint
- 人物蒸餾資料採集鏈
- 以模仿人物 voice 為主的設計

AI Validation Swarm 的核心不是「模仿某人」，而是「建立可抽樣、可比較、可審查的 synthetic market panel」。

## 6. Persona Diversity 擴展方向

目前 POC 的 persona generator 故意使用較小的選項集合，因為現階段目標是：

- 易於看懂
- 易於測試
- 易於發現低級一致性錯誤

這只是 POC 壓縮模型，不是 SaaS 終局模型。

正式系統若要支援 10k 到 1M 級 persona library，應改為：

- 大型 attribute catalogs，而不是少量 hardcoded lists
- weighted distributions，而不是均勻抽樣
- locale / region packs，而不是單層 location enum
- life-stage and workflow-state generators，而不是少量家庭與職業欄位
- deduplication and similarity controls，避免海量 persona 實際上高度重複
- evidence / realism scoring，讓高數量不會直接犧牲 plausibility

## 7. SaaS 遷移藍圖

Phase 1: Local CLI POC  
Phase 2: Single-tenant API service  
Phase 3: Multi-tenant SaaS with dashboard, queue, billing, audit logs

因此 POC 的程式結構要先把 domain logic 從 CLI 分離。
