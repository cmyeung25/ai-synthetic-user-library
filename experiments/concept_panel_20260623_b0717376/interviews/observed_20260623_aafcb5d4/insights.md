# Portfolio Health Check Interview: Maggie Lau

> 以上只屬單一 synthetic persona 的概念前驗證訊號，不能當作真人市場證據；所有因果與產品判斷都需要再用真人訪談驗證。

## Problem Evidence

- Strength: medium
- "我冇一個正式dashboard。" (exchange_2.persona)
- "之後喺手機notes寫返幾個數，當自己拼一個總數出嚟。" (exchange_2.persona)
- "其實係MPF嗰部分最冇把握" (exchange_3.persona)
- "我會先想佢幫我睇清楚，原來我成個組合有幾多其實係重複咗同一類風險" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: low
- 分開查看銀行 app 的現金與定期。
- 分開查看投資 app 的基金與股票市值。
- 另外登入 MPF 只看大概比例。
- 在手機 notes 手動記數並拼成總數。

## Trust Boundary

- 先清楚顯示目前分布與風險在說什麼。
- 將健康檢查分析與產品建議分開。
- 如有推介，需另外清楚說明推介內容與原因。

## First Value

- 快速看清整體組合是否重複承受同一類風險。
- 特別看清 MPF、基金、股票之間是否表面分散但實際吃相近市場波動。
- 不需要再自己每次重新拼數也能得出整體 view。

## Pricing Signal

- Monthly comfort: unknown (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 第一次新鮮，之後沒有持續幫助。
- Drop-off: 只有靜態總覽而沒有變化追蹤。
- Drop-off: 只有視覺包裝或泛泛分析，沒有具體提醒。
- Drop-off: 需要重複自己手動拼數。

## Assumption Validation

- [supported] 很多零售客戶目前以零散、手動或產品級視角管理投資，而非真正 whole-portfolio view。
- [supported] 客戶今天能指出 Aladdin 類分析可補到的實際 blind spot。
- [partially_supported] 零售客戶可理解簡化版機構級投資分析，前提是說法夠具體、不技術化。
- [supported] 最有價值的零售用例是簡化洞察與提醒，而不是機構級細節本身。
- [supported] 部分能力適合直接放在 self-serve 零售渠道。
- [supported] 免費會提升試用，但信任、資料分享和銷售感仍影響採用。
- [partially_supported] 最佳嵌入方式是在既有客戶 workflow 內，而不是獨立複雜 analytics 目的地。
- [supported] 客戶能清楚描述哪些 Aladdin 功能不應暴露或不應怎樣暴露。

## Key Insights

- 這位受訪者的核心痛點不是『沒有數據』，而是無法快速把分散資產拼成可信的整體 view。
- MPF 是最大不確定來源，因為只見到大類比例、更新節奏又不同，令 whole-portfolio 判斷只可當大概。
- 最打動受訪者的不是廣義風險分析，而是看穿跨 MPF、基金、股票之間重複承受的同類風險。
- 免費核心已能滿足不少價值；若做付費層，必須是可行動提醒與調整指引，而不是更華麗的分析展示。
- 信任邊界很清楚：可接受有限度持倉摘要，不接受深層憑證、逐筆交易與現金流全面暴露。

## Next Experiment

用真人受訪者測兩個原型方向：一個是『重複風險＋比例偏離』的輕量 monthly check-in 卡片；另一個是同內容加上產品推介入口分離設計，對比理解度、信任感、銷售感與回訪意願。
