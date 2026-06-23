# Portfolio Health Check Interview: Lau Mei-ling

> 以上結論只來自單一 synthetic interview，用於前期方向判斷和研究設計，不可當作真實用戶或市場證據；所有因果與需求判斷仍需真人訪談驗證。

## Problem Evidence

- Strength: medium
- "主要都係靠app逐頁截圖" (exchange_2.persona)
- "未必咁易發現原來幾樣都係押埋同一類風險" (exchange_3.persona)
- "如果佢可以直接講到我而家嘅收息來源有幾集中" (exchange_3.persona)

## Current Workaround

- Pain: medium; switching: low
- 用銀行 app 逐頁看產品資料。
- 以截圖方式把不同產品資訊拼湊起來給家人一起看。
- 偶爾翻查月結單作補充核對。

## Trust Boundary

- 要先講清楚邊個睇到資料。
- 要講清楚資料會唔會攞嚟做推銷。
- 資料使用範圍要與分析目的直接相關。

## First Value

- 直接看到重疊和集中度。
- 看懂收息來源有多集中。
- 看到如果某一類出問題，每月現金流大概受多少影響。
- 不是只給一個分數，而是指出哪部分集中。

## Pricing Signal

- Monthly comfort: 不支持月費；較偏好一次過收費。 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 只有分數沒有解釋。
- Drop-off: 沒有變化比較。
- Drop-off: 太技術化或要自己猜意思。
- Drop-off: 過度索取資料或帶有推銷感。

## Assumption Validation

- [supported] 很多零售客戶目前是以零散、手動、產品級視角管理投資，而非 whole-portfolio view。
- [supported] 客戶能指出 Aladdin 類 analytics 可補上的實際盲點，特別是 overlap、concentration、scenario 或 drift。
- [supported] 零售客戶能理解簡化版 institutional analytics，只要解釋夠白話。
- [supported] 真正有價值的不是 institutional 細節本身，而是簡化後的 insight、explanation 和 prioritization。
- [supported] 有些能力適合直接放進 self-serve retail channel，有些更適合 RM 或 assisted service。
- [supported] 免費會提高試用意願，但 trust、data sharing 和 sales intent 仍會影響 adoption。
- [supported] 最佳嵌入方式是在既有客戶時刻和 workflow 中，而不是獨立複雜分析目的地。
- [supported] 客戶能清楚描述哪些 Aladdin 功能應該或不應該暴露給零售客戶。

## Key Insights

- 這位受訪者現時做 portfolio 管理主要靠產品頁面和截圖拼湊，最大缺口不是沒有資料，而是沒有整體視角。
- 第一價值很集中：她最在意 overlap、concentration，以及這些風險怎樣影響每月收息現金流。
- Retail 版本要用白話和變化導向呈現；單一分數或偏 institutional 的輸出對她吸引力低。
- 免費核心有明確空間，但 adoption 受信任邊界強烈約束，尤其是外部資產連接和是否被拿去推銷。
- 付費層不是日常訂閱工具，更像在高風險決策時刻購買一次性深入解讀服務。

## Next Experiment

用兩個低保真原型做對比測試：1. app 內自助版只顯示集中度、重疊、到期分布和現金流影響；2. 同一基礎上加上利率/信用情景與人工解讀入口，觀察受訪者是否把第二類內容視為需要 assisted service 而非 self-serve。
