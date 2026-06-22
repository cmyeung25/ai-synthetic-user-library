# Portfolio Health Check Interview: Iris Leung

> 以上只係單一 synthetic persona 的概念預驗證，不可當作真人市場證據或因果結論；最多用嚟收斂下一輪真人訪談與原型測試重點。

## Problem Evidence

- Strength: medium
- "如果佢連基金、ETF 同直接持股嘅重疊都捉到，呢個係我平時最花時間自己補嘅位。" (exchange_4.persona)
- "唔放埋同一個基準睇就好容易高估或者低估咗個集中度。" (exchange_3.persona)
- "原來幾個戶口加埋之後，某個行業或者幾隻核心名字集中得比我以為更高。" (exchange_6.persona)

## Current Workaround

- Pain: high; switching: medium
- 用 spreadsheet 手動整合資料。
- 把大持倉 ETF 主要成份同直接持股逐個對照。
- 跨戶口自己估算主題同名字重疊。

## Trust Boundary

- 要清楚說明外部資料會點用。
- 分析與銷售動作要明確分離。
- 輸出要透明可審視，而唔係只畀結論。

## First Value

- 第一次就要見到本身唔容易即刻睇到嘅跨戶口集中度洞察。
- 能捉到基金、ETF、直接持股之間重疊。
- 結果要解釋計算方法。
- 顯示資料更新時間。

## Pricing Signal

- Monthly comfort: 未知 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 功能被視為基本 banking feature，價值不足以獨立留存。
- Drop-off: 看起來像 sales funnel。
- Drop-off: 黑箱式輸出缺乏可驗證性。

## Assumption Validation

- [partially_supported] 很多客戶覺得現有銀行投資指引偏 product-led 而非 portfolio-led。
- [supported] 客戶能理解簡化後的 portfolio risk、集中度、情景分析。
- [weakened] 機構級 analytics 經由銀行提供，增加的信任會多於懷疑。
- [partially_supported] 客戶願意分享足夠 portfolio data，包括至少部分外部資產。
- [partially_supported] 功能可帶來更好行動或互動，而不只是令客戶更被動。
- [partially_supported] 至少部分客戶對 self-serve 或 RM-assisted interpretation 有需求。
- [supported] 部分客戶對 premium analytics 或 advisory support 有可信付費條件。
- [partially_supported] 概念可被視為中立理解工具，而非更高級的銷售介面。

## Key Insights

- 核心需求唔係『睇到重複名字』，而係用同一基準量化跨 ETF、個股、跨戶口的真實集中度。
- Portfolio Health Check 對這位受訪者有明顯問題對準度，因為正好補他現時用 spreadsheet 手補的缺口。
- 信任唔係來自『機構級 analytics』字眼本身，而係來自資料用途受限、權限可控、方法透明、同銷售分離。
- 銀行內已有資料的整合被視為 table stakes，不足以支撐獨立收費。
- 可收費價值來自更深層能力：外部資產整合、較快更新、深度情景分析、以及 rebalancing 前後風險變化追蹤。

## Next Experiment

用另一位相近但對銀行 RM 較信任或較不信任的香港投資者做對比訪談，並展示兩個低保真概念變體：一個純 self-serve 無任何 RM CTA，另一個可選擇生成 report 再自行決定是否聯絡 RM，測試同一分析輸出下銷售感知如何改變。
