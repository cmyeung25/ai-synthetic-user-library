# Portfolio Health Check Interview: Wong Mei Lin

> 以上只係根據提供嘅 synthetic interview transcript 整理嘅概念驗證報告，屬模擬性 pre-validation evidence，唔可以當成人類市場證據。

## Problem Evidence

- Strength: medium
- "主要係想確認自己啲錢擺位有冇太偏，同埋有冇啲基金跌得比我想像中多。" (exchange_1.persona)
- "通常一邊對住月結單同戶口數，一邊好快咁掃下有冇啲位怪怪哋。" (exchange_2.persona)

## Current Workaround

- Pain: medium; switching: low
- 用銀行 app 總覽頁先睇大概有幾多、邊幾樣跌得明顯。
- 再按入逐隻基金或者股票個持倉頁睇。
- 同時對住月結單同戶口數，快速掃視有冇異常。
- 唔會『整套分析』咁睇。

## Trust Boundary

- 講清楚『係邊個位高風險』。
- 指出係太集中喺某個市場、某個行業，定係波動本身大。
- 畀到而家各類資產比例同對比基準。
- 用普通講法講清楚發生咩事、影響邊度、係唔係真係要處理。

## First Value

- 一眼睇到整體風險同分散情況，節省自己拆解時間。
- 結果要可追問判斷依據，而唔係純標籤。
- 若提示高風險，能立即指出集中來源與比例。
- 初次使用應留喺 app 內自助理解，不需即時人手介入。

## Pricing Signal

- Monthly comfort: 不適用 (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 如果每月都係同一段『有風險』廢話，會降低再看意願。
- Drop-off: 如果需要額外彈層或打斷原流程，配合度會下降。
- Drop-off: 若複雜情況一開始就轉成人工跟進，可能引發抗拒。

## Assumption Validation

- [supported] 此 persona 會把 Portfolio Health Check 當作節省理解時間的輔助總覽，而唔係自動觸發交易決定的工具。
- [partially_supported] 此 persona 是否持續使用，主要取決於輸出有冇具體解釋同可對比基準，而唔係單有風險標籤。

## Key Insights

- Because 月尾對戶口同帳單時只會『好快咁掃』持倉、而且平時『唔會整套分析咁睇』, this persona would likely ignore a deep standalone analytics flow, unless it appears directly inside the existing投資總覽 moment. This means the product should embed the check as an in-context summary on the overview page, not as a separate analysis journey.
- Because 佢對風險提示嘅核心疑慮係『想知佢點樣判斷』同『冇實際內容』, this persona would likely distrust generic health labels, unless each alert explains the concentrated market/industry or volatility source with current allocation percentages and a comparison baseline. This means the product should make explanation mechanics visible before any recommendation language.
- Because 見到高風險後『第一步唔會即刻買賣』而係先核對集中來源、再對返原本買入理由, this persona would likely use the feature as a diagnostic checkpoint, unless the issue is clear enough and serious enough to justify later adjustment. This means the product should support inspection and reflection first, not push direct transaction CTAs.
- Because 佢只願意每月再撳入去睇有『好具體嘅變化』同『點解我要而家睇』, this persona would likely stop reopening repetitive monthly reminders, unless the notification highlights what changed since last month. This means the product should trigger only on materially new changes and show delta-based summaries rather than static risk copy.
- Because 佢話想先喺 app 自己睇明，亦明講『唔想一開始就好似被 sales 追住咁』, this persona would likely resist human follow-up at first contact, unless the case is genuinely複雜 and the app has already explained the issue in plain language. This means the product should default to self-serve explanation and gate human outreach behind clear complexity thresholds or explicit user choice.

## Next Experiment

喺現有銀行 app 投資總覽頁做一個最小可測試原型，只顯示 1 個『組合健康摘要卡』加 1 個月尾變化提醒文案；用同類 persona 做 5 次任務式測試，觀察佢哋會唔會在原本月尾對戶口情境中主動打開、能否講返系統點解判斷集中/波動、以及會否覺得似 sales。
