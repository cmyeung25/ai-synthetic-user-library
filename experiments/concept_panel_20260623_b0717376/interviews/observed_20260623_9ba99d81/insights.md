# Portfolio Health Check Interview: Iris Cheung

> 以上只屬單一 synthetic persona 的概念前驗證，不可當作真人市場證據；所有因果與需求判斷都需要再用真人訪談驗證。

## Problem Evidence

- Strength: medium
- "銀行app睇基金，證券戶口睇股票，MPF就另外登入供應商個app，再開返手機備忘錄同之前截圖對一對" (exchange_2.persona)
- "佢最好一眼話畀我知邊度太重、邊度太散，唔使我自己逐個戶口拼返埋" (exchange_3.persona)
- "今個月邊類持倉重咗、重複咗，仲可以畀我自己再核對，不是亂咁嚇我，我先會再開" (exchange_5.persona)

## Current Workaround

- Pain: medium; switching: medium
- 銀行app看基金。
- 證券戶口看股票。
- MPF供應商app另外登入查看。
- 用手機備忘錄和之前截圖手動對照，粗略寫低各類持倉比例。

## Trust Boundary

- 明確只用作分析。
- 用戶看得到系統攞咗啲乜。
- 分析要可核對，不可黑箱或誇張化。
- RM介入時不能一開口就變成sell嘢。

## First Value

- 一眼看到有沒有表面分散但實際重複押在相近市場或大公司。
- 直接指出邊度太重、邊度太散。
- 免去逐個戶口手動拼湊。

## Pricing Signal

- Monthly comfort: 未知 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 只係一次性新鮮感。
- Drop-off: 輸出太誇張或像銷售前奏。
- Drop-off: 不能真正減少手動整理。

## Assumption Validation

- [supported] 很多零售客戶目前用碎片化、手動或產品級視角管理投資，而不是真正整體視角。
- [supported] 客戶能指出 Aladdin 類分析可解決的實際盲點。
- [partially_supported] 零售客戶能理解簡化版 institutional analytics，只要表達夠具體非技術。
- [supported] 最有價值的是簡化洞察與優先次序，不是 institutional detail 本身。
- [supported] 部分能力應直接放在零售自助渠道，部分應留在 RM 或受助流程。
- [supported] 免費會增加試用，但信任、資料分享和銷售感仍影響採用。
- [partially_supported] 最佳嵌入點是在既有 workflow 內，而不是獨立複雜 analytics 目的地。
- [supported] 客戶能說出哪些功能應或不應暴露給零售客戶。

## Key Insights

- 真正痛點不是『冇分析』，而是跨戶口拼湊整體視角太土法、太花時間。
- 最先有價值的不是深度機構級術語，而是直接指出重複押注、過重過散和近期變化。
- 信任門檻很清楚：只限分析、資料可見、可自行核對、不要交易權限、不要掃無關戶口。
- 留存取決於持續節省時間，不取決於新鮮感或視覺包裝。
- 零售端適合放簡單 summary 和 alert；涉及調整建議與取捨解釋時，較適合 RM 輔助，但要避免變成 sales trigger。

## Next Experiment

用另一位不同投資習慣的香港銀行 persona，測試較低參與度用戶是否同樣重視重複持倉/過重過散，並加入一個具體介面刺激物，比較『app內自助 summary』與『RM會前報告』哪種嵌入更自然。
