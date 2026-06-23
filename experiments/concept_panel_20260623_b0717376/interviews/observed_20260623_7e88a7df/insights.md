# Portfolio Health Check Interview: Ivy Chan

> 以上只屬 synthetic persona 預驗證，不可視為真人市場證據；所有因果與產品判斷都需要真人訪談再驗證。

## Problem Evidence

- Strength: strong
- "我會先睇總額，再逐個戶口拉返最近啲交易" (exchange_2.persona)
- "有啲唔肯定嘅，我會順手cap低，之後先再慢慢追" (exchange_2.persona)
- "有時幾個app分開睇，個時間差一兩日，我都會停一停先當自己未對清" (exchange_3.persona)
- "我第一下會想佢直接指出邊啲位同我平時認知唔一致" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: medium
- 先看總額，再逐個戶口拉最近交易逐項比對。
- 靠自己記憶核對供款、轉帳和收費。
- 對唔準或未確定的項目先截圖，之後再慢慢追查。

## Trust Boundary

- 先證明功能有用，再要求更多授權。
- 清楚說明資料會存多久。
- 清楚說明資料用來做什麼。
- 清楚說明停用後能否刪除資料。

## First Value

- 直接指出與用戶平時認知不一致的地方。
- 快速找出比例偏移、細額收費增加、自動轉帳金額變動。
- 打開即見變動，不用重新設定一輪。

## Pricing Signal

- Monthly comfort: 未知 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 只增加幾個圖表。
- Drop-off: 每次都要重設或重連。
- Drop-off: 功能看起來像索取資料或推銷前置，而非中性檢查。

## Assumption Validation

- [supported] 很多零售客戶現在以碎片化、手動或產品層級視角管理投資組合，而不是整體視角。
- [supported] 客戶今天能指出實際盲點，而 Aladdin 類分析可幫到，特別是異常、偏移、變化偵測。
- [partially_supported] 零售客戶能理解簡化版機構級分析，只要表達夠具體、不技術化。
- [supported] 最有價值的不是機構級細節本身，而是簡化洞察、解釋和優先次序。
- [supported] 有些能力應直接放入自助零售渠道，另一些應留在 RM 或受助服務。
- [supported] 即使功能免費，信任、資料共享和銷售意圖仍會影響採用。
- [supported] 最好嵌入現有客戶流程，而不是另開一個複雜分析目的地。
- [supported] 客戶能描述哪些功能應該或不應該暴露在零售銀行介面。

## Key Insights

- 這位受訪者的核心痛點不是『看不懂投資分析』，而是跨 app 對數太手動，且微小但累積性的變動難追。
- 對他而言，Portfolio Health Check 的核心價值是『指出和我認知不一致的地方』，不是總覽圖表。
- 免費會降低嘗試門檻，但不會自動解決信任問題；未證明價值前要求連接外部戶口會直接造成流失。
- 月二留存取決於持續節省時間與低操作負擔，尤其是免重設、免重連、直接看到自上次以來的變化。
- 進階付費只有在自動化與準確性真的替代手動工作時才有可能成立；單純增加分析展示沒有升級價值。

## Next Experiment

用下一位香港銀行 persona 測試一個更具體的產品嵌入原型：銀行 app 內首頁或投資頁直接顯示『自上次檢查以來的3個異常變動』，並分開測試兩種外部資產連接方式，觀察是否仍出現相同的信任阻力。
