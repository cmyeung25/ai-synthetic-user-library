# Portfolio Health Check Interview: Ivy Chan

> 以上只係單一 synthetic persona 的概念預驗證，不可當成人類用戶證據；所有洞察、需求同假設都需要再用真實香港零售銀行客戶訪談驗證。

## Problem Evidence

- Strength: medium
- "主要係見到市況有少少波動，想確認下啲基金同股票比例有冇偏得太離譜" (exchange_1.persona)
- "如果係某一兩隻升得太多，成個比重突出咗，我就會記低，但未必即刻郁" (exchange_2.persona)
- "第一下我會睇集中度，因為嗰樣最容易平時一路放住就偏咗但自己未必即刻察覺" (exchange_3.persona)
- "風險提醒如果太空泛，例如只係講『波動較高』，我會當佢冇講" (exchange_3.persona)

## Current Workaround

- Pain: medium; switching: medium
- 分開打開銀行 app 同券商 app 睇。
- 先睇資產分布頁判斷股票、基金、現金比例有冇偏離原本想像。
- 再逐隻掃持倉升跌，見到比重突出就自己記低。
- 之後再自己比較原因，同現金需要一齊考慮要唔要分幾次減持。

## Trust Boundary

- 要講清楚係邊一兩隻持倉造成問題。
- 要講到目前比重大概去到幾多。
- 要講到同原本預期分布差幾遠。
- 要講人話，而唔係抽象風險字眼。

## First Value

- 一頁內見到整體持倉分布同集中度。
- 即刻知道問題來自邊隻或邊兩隻持倉。
- 快速判斷要唔要跟進，而唔使再自己抄去第二度比較。

## Pricing Signal

- Monthly comfort: 不適用；今次冇測價格。 (unknown)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 提醒太籠統。
- Drop-off: 準確度低。
- Drop-off: 推送過多。
- Drop-off: 只係叫佢郁，但冇交代原因同影響。

## Assumption Validation

- [supported] 好多零售客仍然用碎片化、產品層級視角管理組合，而唔係真正 whole-portfolio process。
- [partially_supported] 最重要嘅 blind spot 因人而異，應由行為同情境浮現。
- [supported] 零售客如果用簡單語言包裝，可以指出具體 analytics 功能對實際決策有幫助。
- [supported] 最高價值 use case 會綁定真實客戶時刻，而唔係為咗展示機構級分析而展示。
- [unknown] 有啲能力適合 self-serve retail，有啲更適合 RM 或 assisted service。
- [supported] trust、資料邊界、解釋方式同 action threshold 會影響免費功能會唔會成為日常習慣。
- [supported] 深層洞察需要理解表面功能偏好背後嘅行為原因。
- [supported] 客戶可以講清楚呢類體驗應該做乜同唔應該做乜。

## Key Insights

- 呢位受訪者而家做緊嘅唔係正式再平衡流程，而係事件觸發式健康檢查：見市況波動就打開幾個 app，快速確認比例有冇偏離。
- 最有價值嘅唔係抽象 risk score，而係『集中度由邊隻持倉拉高、而家去到幾多、同原本差幾遠』呢類可直接判斷嘅資訊。
- 功能如果只提供 generic 風險提醒，會被視為噪音；要建立信任，必須把訊號翻譯成具體持倉、差距同不處理的後果。
- 呢個 persona 唔想被系統催促交易；佢要嘅係更快完成『要唔要跟進』判斷，而唔係自動化決策。
- 最佳嵌入位係主動檢查投資組合時，或者月尾本來會睇戶口的 routine moment；過多 push 會直接損害接受度。

## Next Experiment

用下一位 persona 測試對比場景：一版只顯示 generic 風險提醒，另一版顯示『持倉名稱 + 目前比重 + 與目標差距 + 不處理後果』，觀察邊種更能令受訪者描述出明確下一步，並再加入 RM/assisted-service 邊界問題。
