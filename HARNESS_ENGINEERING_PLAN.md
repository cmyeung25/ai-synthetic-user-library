# Harness Engineering Plan

## 1. 目標

本文件定義 AI Validation Swarm 的 10 個核心 harness。每個 harness 都要把「輸入、控制、輸出、可測試性」固定下來，避免 POC 淪為一次性的聊天腳本。

## 2. Harness 總表

| Harness | 目的 | POC 產物 | 主要風險 |
| --- | --- | --- | --- |
| Context Harness | 把 founder brief 正規化 | `FounderBrief` schema、run manifest | prompt 過散、上下文遺失 |
| Persona Harness | 固定 synthetic user 結構與一致性 | persona schema、seed rules、consistency checks | stereotype、人格漂移 |
| Skill Harness | 定義 persona 的可重用格式 | `profile.json` + `persona.md` + `audit.json` | 格式失控、版本不可追 |
| Sampling Harness | 依市場與 panel 抽樣 | panel presets、sampling rationale | 抽樣黑箱、面板偏斜 |
| Validation Protocol Harness | 固定驗證任務類型 | protocol templates | 同題不同問法造成噪音 |
| Agent Orchestration Harness | 固定 agent 順序與責任邊界 | orchestration pipeline | agent 重工、結論互相污染 |
| Safety Harness | 約束敏感議題輸出 | auditor rubric、report policy | 放大偏見、危險建議 |
| Evaluation Harness | 定義 quality gate | fixtures、rubrics、golden outputs | 無法知道 POC 是否有用 |
| Observability Harness | 保存 run 過程 | run archive、logs、usage stats | 不可追溯、難 debug |
| Feedback Loop Harness | 規劃真人回寫路徑 | import contract、update policy | persona library 老化 |

## 3. 各 Harness 設計

### Context Harness

- 輸入統一為 `FounderBrief`
- 必填欄位：problem、target_market、offered_solution、validation_goal
- 選填欄位：pricing hypothesis、landing page、constraints、known risks
- 每次 run 都保存 normalized brief 與原始 brief

### Persona Harness

- persona 先有 deterministic demographic seed，再由 LLM 補完價值觀、人生故事、行為與敏感層
- persona 一經生成即凍結為版本化檔案，不在每次 run 重新生成
- 每個 persona 必須帶 `evidence_grade` 與 `stereotype_risk_score`
- 敏感欄位只用於 contextual reaction 與 risk audit，不用於 discriminatory targeting

#### 正確生成「合理人類」的規則

合理 persona 不是「像人說話」就夠，而是要同時滿足：

- 結構合理：年齡、教育、職業、收入、家庭、日常時間分配彼此一致
- 因果合理：價值觀、風險感、購買阻力能從生活背景推導
- 分布合理：persona library 不能全部是高表達、高數位、高反思樣本
- 任務相關：只生成會影響 validation 的特徵，不堆無用設定
- 安全合理：不把敏感身份直接映射成固定購買行為

POC 補充邊界：

- 現階段為了可控與可測，只使用小型枚舉值與少量模板
- 這不代表正式產品只會有這幾種人
- 進入 SaaS 階段時，persona diversity engine 必須擴展到至少 10k 甚至 1M 級 synthetic users 的生成、去重、加權抽樣與分布治理
- 因此目前的 enum-like options 應視為 `seed scaffold`，不是長期 persona vocabulary

建議生成流程：

1. 先定 `sampling frame`
2. 再抽 `demographic seed`
3. 再補 `structural constraints`
4. 再生成 `values + life story + behavior`
5. 最後才輸出成 skill artifacts

`structural constraints` 至少包括：

- 可支配時間
- 可支配金錢
- device / payment / app 使用條件
- 家庭責任
- 工作壓力
- 風險承受能力

這樣 persona 的回應會比較像「活在現實中的人」，而不是一堆標籤拼接。

### Skill Harness

POC 不直接依賴完整 `dot-skill` host framework，而採用簡化格式：

- `profile.json`: 結構化資料
- `persona.md`: 自述與 speaking/decision notes
- `audit.json`: 生成方法、風險評分、版本資訊

其中 `persona.md` 不應只是文案包裝，而應明確包含：

- how this person evaluates new tools
- what they distrust by default
- what makes them try anyway
- what topics they avoid
- what constraints dominate their decisions

這些內容比單純的口吻模仿更重要，因為 validation engine 需要的是 decision policy，不是角色扮演。

這樣可保留 skill-as-file 的優點，但避免一開始綁定外部 host、slash command、資料採集流程。

### Sampling Harness

- 支援 `mainstream`, `skeptic`, `privacy_sensitive`, `inclusion`, `political_risk`, `low_tech`, `budget_constrained`, `extreme_user`
- 支援 deterministic random seed
- 每次抽樣輸出 sampling rationale，說明為何抽到這批 persona

後期擴展要求：

- panel 不能只靠少量固定 label
- 需支援更細粒度的 latent traits、market slices、geo packs、life-stage packs、workflow maturity bands
- 需支援 distribution targets，例如收入分布、家庭責任分布、科技接受度分布、語言分布
- 需支援去重與近重複 persona 檢查，避免 1 萬或 100 萬人庫只是大量相似角色

### Validation Protocol Harness

首批 protocol：

- problem validation
- solution validation
- pricing reaction
- landing page comprehension
- concierge MVP feasibility
- founder assumption challenge

每個 protocol 都對應固定 prompt template、必答欄位與輸出 JSON shape。

### Agent Orchestration Harness

建議 pipeline：

1. Synthetic User Agent
2. Optional Moderator Agent
3. Skeptic Agent
4. Sensitive Topic Auditor Agent
5. Aggregator Agent
6. Report Writer Agent
7. Real-World Validation Planner Agent

關鍵規則：auditor 與 aggregator 必須看見 raw responses，但不可回寫 persona 本身。

### Safety Harness

- 敏感議題永遠輸出為「風險觀察」與「待驗證問題」
- 禁止輸出排斥性 segment recommendation
- 高風險領域加註額外 warning：medical、legal、financial、education、parenting

### Evaluation Harness

- schema validation
- persona consistency tests
- sampling diversity tests
- report completeness checks
- auditor recall tests
- seeded rerun stability checks
- human rubric review

### Observability Harness

每次 run 保存：

- input brief
- selected personas
- raw persona responses
- moderator / skeptic / auditor outputs
- final report
- prompt version
- model version
- token / cost estimate
- retries / errors

### Feedback Loop Harness

POC 先規劃接口，不做完整閉環：

- 真實訪談摘要匯入
- persona evidence upgrade
- panel / protocol revision note
- founder feedback 對 prompt 與 report 模板的修正記錄

## 4. Milestone 0 交付邊界

Milestone 0 的目標不是寫完整 engine，而是先把上述 harness 轉成：

- 可實作的 schema
- 可檢查的 folder structure
- 可追溯的 workflow
- 可測試的 quality gate
