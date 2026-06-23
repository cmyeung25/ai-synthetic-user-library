# Portfolio Health Check Interview: Clara Wong

> 以上只屬單一 synthetic persona 的概念預驗證，不可視為真人市場證據；所有洞察、假設支持度與產品方向，都需要再用真實香港零售銀行客戶訪談驗證。

## Problem Evidence

- Strength: medium
- "我夜晚食完飯就開返銀行app同幾份月結單對一對" (exchange_1.persona)
- "見到叫法唔一致嗰啲，我會停一停，截圖或者記低" (exchange_2.persona)
- "我第一下會想睇重疊" (exchange_3.persona)
- "佢要指出係邊幾項...再用簡單說明講清楚點解算同一類風險" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: low
- 先看銀行app內持倉名稱和大概金額。
- 再用幾份月結單逐項核對。
- 遇到命名不一致或不確定項目時，截圖或在手機記低，之後再問RM。
- 重要調整或新建議出現時，再自行比較前後變化。

## Trust Boundary

- 要清楚指出哪些持倉屬同一類風險。
- 要說明判定原因，例如同地區、同行業、底層持倉接近。
- 方法要講得明，資料權限要講得清楚。
- 不能只用幾個圖或較靚畫面包裝結論。

## First Value

- 第一次就要指出一兩個受訪者本身冇睇清嘅重疊。
- 結果要可被客戶自行對回月結單。
- 最好能直接講出『邊幾項其實係同一類風險』。

## Pricing Signal

- Monthly comfort: 未知；未提供明確金額。 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 如果只是靜態提醒，沒有新發現或比較價值。
- Drop-off: 如果無法支援RM建議前後的快速檢查。
- Drop-off: 如果分析太抽象、太技術化或像銷售話術。

## Assumption Validation

- [supported] 很多零售客戶現時以碎片化、手動方式管理投資組合，而不是真正 whole-portfolio view。
- [supported] 客戶今日能指出 Aladdin 類分析可解決的實際盲點，尤其是重疊、集中或貨幣風險。
- [supported] 零售客戶可理解簡化版機構級分析，只要解釋夠具體、不技術化。
- [supported] 最有價值的零售用例是簡化洞察與解釋，而不是機構細節本身。
- [supported] 部分能力適合直接放在零售自助渠道，部分應留在RM或 assisted-service。
- [supported] 免費有助試用，但信任、資料分享與銷售意圖仍影響採用。
- [supported] 最佳嵌入方式是放進現有客戶工作流，而不是一個獨立複雜分析目的地。
- [supported] 客戶能描述清楚哪些 Aladdin 能力應暴露給零售客戶，哪些不應。

## Key Insights

- 現時痛點不是『沒有任何資訊』，而是整體組合要靠手動拼湊，尤其在命名不一致時難以判斷真假分散。
- 對這位受訪者最強的價值點不是 general risk dashboard，而是可核對的 overlap detection。
- 信任不是靠品牌或視覺，而是靠『指出哪幾項』『為何算同類風險』『可以自己對回月結單』。
- 月二留存依賴事件觸發：第一次發現盲點、調整後複查、RM提出新建議後即時驗證。
- 零售自助適合做盤面診斷；牽涉動作建議、風險取向衝突與取捨時，受訪者仍要RM承接。

## Next Experiment

用人類受訪者測試一個低保真原型：只展示『具體重疊項目 + 簡單原因 + 調整前後比較』，放在RM建議後的app情境中，觀察他們是否能在首次使用內自行理解並完成一次核對。
