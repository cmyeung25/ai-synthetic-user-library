# Portfolio Health Check Interview: Chloe Ng

> 以上只屬 synthetic persona 預驗證，不能當作真人市場證據；所有洞察、價值判斷與因果解釋都需要用真人訪談與真實產品測試再驗證。

## Problem Evidence

- Strength: medium
- "最麻煩唔係逐個產品，而係要自己心入面再拼一次幣種同市場 exposure，因為每個app個分類方式都唔同。" (exchange_2.persona)
- "嗰晚最唔清楚其實係重疊 exposure，特別係美股嗰邊。" (exchange_3.persona)
- "如果個全貌都未睇清，我唔想靠感覺去調。" (exchange_4.persona)
- "如果第一次開已經只係好表面，我未必會特登返去睇第二次。" (exchange_7.persona)

## Current Workaround

- Pain: high; switching: medium
- 先開主要銀行 app 睇現金同基金。
- 再去券商睇 ETF 同美股持倉。
- 靠截圖同 Notes 手動對數。
- 用心算方式重新拼湊幣種同市場 exposure。

## Trust Boundary

- 清楚說明為何需要每類資料。
- 明確保證只讀取投資分析所需範圍。
- 讓用戶感到是中立分析，不是順便帶去產品建議。

## First Value

- 第一眼要清楚拆解重疊 exposure。
- 最好能看出是否其實集中在同一批大型美股或同一主題。
- 若可連同外部持倉一併計算，感知價值更高。
- 輸出不能只停留在表面總覽。

## Pricing Signal

- Monthly comfort: unknown (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 首次體驗太表面
- Drop-off: 無法整合外部持倉
- Drop-off: 呈現太 technical
- Drop-off: 感覺像銷售前置
- Drop-off: setup 或授權成本過高

## Assumption Validation

- [supported] 很多零售客戶目前用碎片化、手動或產品級視角管理投資組合，而不是 true whole-portfolio 視角。
- [supported] 客戶今天能指出 Aladdin 類 analytics 可解決的實際盲點，尤其 overlap、concentration、scenario 或 drift。
- [supported] 零售客戶可理解簡化後的 institutional analytics，只要解釋夠具體、非 technical。
- [supported] 最有價值的零售 use case 是簡化 insight、解釋與 prioritization，而不是 institutional detail 本身。
- [supported] 部分能力應直接在 self-serve retail channel 出現，另一部分應保留給 RM 或 assisted service。
- [supported] 即使核心免費，信任、資料分享與銷售意圖仍會影響採用。
- [partially_supported] 最佳嵌入方式應貼近既有客戶時刻，而不是一個獨立複雜 analytics destination。
- [supported] 客戶可以清楚描述哪些 Aladdin 功能該或不該暴露在 retail banking。

## Key Insights

- 這位受訪者的核心問題不是『看不到持倉』，而是跨平台下看不清 whole-portfolio 的重疊 exposure、集中度與幣種風險。
- Portfolio Health Check 的首要價值應是把 look-through overlap 用人話拆開，而不是先做漂亮 dashboard。
- 若不能納入外部持倉，分析容易被視為不完整；但外部整合必須以最少必要資料和明確控制權為前提。
- 留存觸發點偏事件化和節奏化：市場波動時，以及既有的月尾或週末 money admin 時刻。
- 零售端可承接的是簡化 insight 層；模型假設、壓力測試計算邏輯與深層指標更適合交由 RM 或詳細報告承接。

## Next Experiment

用真人受訪者測兩個原型對比：1. 只含銀行內部資產的重疊/集中度總覽；2. 可 read-only 連外部持倉並清楚拆解 overlap、幣種與簡單 scenario。比較首次理解、信任、授權意願與一週後再開意圖。
