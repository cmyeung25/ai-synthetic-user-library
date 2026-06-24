# AI synthetic-user platform Interview: Janice Wong

> 以下只係基於單一合成受訪者逐字稿嘅模擬概念驗證整理，屬校準中嘅 simulated evidence，唔係人類市場證據，亦唔應被當作採納、付費或留存預測嘅充分證明。

## Problem Evidence

- Strength: medium
- "真係流失最多係嗰個位" (exchange_1.persona)
- "drop-off 明顯高" (exchange_2.persona)
- "會問自己做完呢步有咩用、會唔會整錯" (exchange_2.persona)
- "嗰種猶豫感係數字本身睇唔到" (exchange_2.persona)

## Current Workaround

- Pain: medium; switching: medium
- 用 analytics 搵出 drop-off 最集中的步驟。
- 用 user call notes 理解猶豫內容，例如用戶會問做完有咩用、會唔會整錯。
- 當新輸入出現時，會同現有 analytics 同真實 user notes 對一對，先用嚟收窄判斷。

## Trust Boundary

- 要喺真實 case 入面『指出嘅猶豫位同 analytics、user call notes 大致對得上』。
- 要『唔止俾結論，仲俾到我見到係基於咩假設、邊類情境先會反覆出現』。
- 要見到 pattern 點樣反覆出現，而唔係得一句 summary。

## First Value

- 喺一個真實優先排序問題上，快速指出重複出現嘅猶豫位。
- 輸出能夠按情境分布展示，而唔係只得總結句。
- 結果可以即場同現有 analytics 或 user notes 對照，幫佢收窄下一步驗證方向。

## Pricing Signal

- Monthly comfort: unknown (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 急近上線或 release 前修正問題時，工具只會增加核對負擔。
- Drop-off: 涉及 billing、法務、support 等高風險真實後果時，佢會優先睇真實用戶反應。
- Drop-off: 如果輸出不可解釋、不可追溯，或者同手上證據對唔上。

## Assumption Validation

- [supported] 呢位 PM 目前喺 feature priority 上有真實證據缺口，需要用多種來源補足。
- [supported] AI synthetic-user platform 對佢最合理角色係幫手收窄判斷，而唔係代替真實研究或 analytics。
- [weakened] 只要平台指出一個有意思嘅 pattern，佢就會直接改變排序決定。
- [partially_supported] 平台若提供可追溯假設同情境分布，會較容易被納入 workflow。
- [invalidated] 平台適合高壓、近上線、涉及 billing / legal / support 風險嘅決策。
- [partially_supported] 如果工具有用，佢會喺部分前期項目重複使用。

## Key Insights

- Because 佢最近真實上係先用 analytics 定位 drop-off，再用 notes 補『做完呢步有咩用、會唔會整錯』呢類猶豫，this persona would 只接受平台作前期收窄判斷嘅輔助輸入，unless 輸出可以脫離現有 evidence 單獨證成決策。 This means the product should 設計成 evidence-triangulation 工具，而唔係 autonomous recommender。
- Because 佢明確怕『增加我要解釋同核對嘅負擔』，this persona would 喺 release 前、涉 billing/法務/support 嘅高風險情境跳過平台，unless 工具幾乎零額外核對成本而且能處理真實後果責任。 This means the product should 先聚焦非緊急前期優先排序場景，避免把高壓修補工作流當主用例。
- Because 佢要求結果要『唔止俾結論』，仲要見到『基於咩假設、邊類情境先會反覆出現』，this persona would 對黑盒 summary 保持保留，unless 平台能展示 pattern、情境分布同假設來源。 This means the product should 先驗證 explainability 與 traceability 介面，而唔係先擴大輸出花巧度。
- Because 佢只喺『手上真實證據唔算好完整，但又未急到即日要拍板』時先覺得有幫助，this persona would 只喺證據半完整、仍有少量判斷空間嘅項目開平台，unless 已有足夠真實研究或決策時限太短。 This means the product should 把 first-use 切入點放喺 evidence gap 明確但仍可補驗證嘅 backlog prioritization。

## Next Experiment

搵 1 個真實、非緊急、前期優先排序案例（例如 onboarding 或定位文案），只輸入該團隊已知問題與現有 analytics 摘要，產出 3-5 個可追溯嘅合成猶豫 pattern，每個 pattern 都標示假設同情境。然後請呢位 PM 只做一件事：逐項標記『對得上 / 對唔上 / 未知』佢手上真實 notes 與 analytics，並記錄有無因此收窄到下一步要驗證嘅 1 條方向。成功標準唔係採納建議，而係能否低負擔地完成對照並收窄一條真實驗證方向。
