# Agent Workflow

## 1. 角色定義

### Synthetic User Agent

- 讀取 frozen persona
- 根據 protocol 與 founder brief 產生第一人稱或準第一人稱回應
- 不可越權總結整體市場

### Moderator Agent

- 視需要對模糊答案追問 1 至 2 輪
- 只做 clarification，不主導結論

### Skeptic Agent

- 挑戰 founder 假設
- 標記過度樂觀、模糊價值主張、未驗證定價假設

### Sensitive Topic Auditor Agent

- 檢查輸出是否涉及 discrimination、stereotype、privacy、political sensitivity 等
- 將風險轉成安全格式觀察

### Aggregator Agent

- 歸納 segment reaction
- 聚類 objections / triggers
- 形成 score 與 risk map

### Report Writer Agent

- 依固定章節輸出 Markdown report
- 注入必需 disclaimer

### Real-World Validation Planner Agent

- 根據風險與不確定性輸出 7-day no-code validation plan
- 產出真人訪談建議問題

## 2. 標準執行順序

1. Load brief
2. Normalize brief
3. Load / sample personas
4. Run synthetic user responses
5. Optional moderator follow-up
6. Run skeptic review
7. Run sensitive topic audit
8. Aggregate findings
9. Write final report
10. Archive artifacts

## 3. 資料流規範

- synthetic user agent 只能讀：brief、protocol、persona
- moderator 可讀：persona response
- skeptic 可讀：brief、sample summary、selected raw responses
- auditor 可讀：brief、responses、draft findings
- aggregator 可讀：responses、skeptic、auditor
- report writer 可讀：aggregated findings、auditor output、planner output

## 4. Prompt 分層

- system prompt：固定角色與安全規則
- protocol prompt：任務型問題模板
- report template：輸出結構模板
- audit rubric：風險分類模板

所有 prompt 都必須有 version，例如：

- `persona-response/v1`
- `skeptic-review/v1`
- `sensitive-audit/v1`
- `report-writer/v1`

## 5. 失敗處理

- persona response timeout -> retry with same prompt version
- invalid JSON -> repair pass or mark partial failure
- auditor failure -> report 標記 audit incomplete，不可靜默略過
- provider error -> 記錄 model/provider/error code

## 6. Run Artifact 最低要求

每次 run 必須保存：

- normalized brief
- selected personas
- raw responses
- moderator outputs
- skeptic outputs
- audit findings
- aggregated summary
- final Markdown report
