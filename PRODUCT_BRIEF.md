# AI Validation Swarm Product Brief

## 1. 產品定位

AI Validation Swarm 是一個「AI pre-validation engine」，用大量結構化 synthetic users 幫 founder 在真人訪談之前，提早發現：

- 概念盲點
- 定位問題
- 價格阻力
- 關鍵 objection
- 敏感議題與品牌風險
- 下一步真人驗證方向

它不是 market proof system，也不是自動保證 PMF 的工具。

## 2. 核心主張

系統只應主張：

- 用 synthetic users 進行早期假設壓測
- 用多 persona 反應暴露盲點
- 用 auditor agent 提前標記敏感風險
- 用 report 把 AI 討論轉成可執行的真人驗證計劃

系統不應主張：

- AI users 可以證明市場一定會買
- synthetic users 可以取代真人研究
- 敏感族群可以被直接用來做歧視式 targeting

## 3. 主要用戶

- 早期 founder
- startup product lead
- growth / validation consultant
- agency strategist

## 4. 典型輸入

- startup idea brief
- target market 定義
- validation objective
- pricing / landing page / MVP 假設
- founder 明示限制與已知風險

## 5. 典型輸出

- problem resonance
- solution attractiveness
- willingness to pay signals
- objection map
- buying triggers
- segment fit summary
- sensitive topic / privacy / fairness / inclusion / political sensitivity risk
- recommended repositioning
- suggested concierge MVP
- suggested 7-day no-code validation plan
- suggested real-user interview script

## 6. POC 階段的產品邊界

本階段只做無 UI、本地可重跑的 validation engine：

- CLI / script based
- local JSON + SQLite
- prompt version-controlled
- run artifacts fully archived
- provider abstraction，不綁定單一 LLM vendor

本階段不做：

- frontend UI
- auth
- billing
- multi-tenant workspace
- team collaboration
- production queue / webhook

## 7. 成功標準

Milestone 0 到 Milestone 5 的 POC 成功條件：

1. 可生成並儲存 synthetic users
2. 可按 target market 與 panel type 抽樣
3. 可對同一 founder brief 進行多 persona 回應
4. 可輸出安全格式的 auditor findings
5. 可生成可閱讀的 Markdown report
6. 可保留完整 run trace，便於重跑、比對與評估

## 8. 一句話設計原則

先把「可重複、可追溯、可評估」做好，再考慮 UI 與 SaaS 化。
