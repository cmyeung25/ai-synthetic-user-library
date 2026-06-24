# Portfolio Health Check Interview: Wong Mei Ling

> 以上只係基於單一 synthetic persona 訪談逐字稿嘅概念驗證整理，屬模擬前驗證證據，唔代表真人市場需求、採納率或付費意願。

## Problem Evidence

- Strength: medium
- "「上個月尾，我先至認真逐隻睇一次。」" (exchange_1.persona)
- "「我喺地鐵上面就開銀行app同基金戶口對一對，主要係想知而家個配置有冇太偏。」" (exchange_1.persona)
- "「如果要去幾個地方先拼得齊，我會覺得幾煩，亦容易拖住唔想再睇。」" (exchange_2.persona)

## Current Workaround

- Pain: medium; switching: medium
- 用銀行 app 睇部分投資持倉。
- 另外開基金戶口對資料。
- 用 Notes 記買入價同「大概用途」。
- 偶爾翻 WhatsApp 或 email 入面嘅月結單補資料。

## Trust Boundary

- 要可以逐項授權。
- 要講清楚資料會保存幾耐。
- 要講清楚會唔會用嚟推銷。
- 要講清楚點樣計風險。
- 要講清楚係咪真係免費。

## First Value

- 首次打開就要「一次過睇到分散成點、風險有冇偏咗」。
- 唔使再自己逐個戶口拼資料。
- 如果顯示偏離，要講清楚係短期波動定真係某類資產比重高咗好多。
- 風險解釋要夠白話。

## Pricing Signal

- Monthly comfort: 不適用／未測試。 (unknown)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 如果仍然要去幾個地方拼資料。
- Drop-off: 如果提醒頻繁或無端端推送。
- Drop-off: 如果偏離解釋含糊。
- Drop-off: 如果看起來借分析做產品推銷。
- Drop-off: 如果資料授權範圍過闊或保存用途不透明。

## Assumption Validation

- [supported] 此 persona 目前有整體投資組合檢視需要。
- [supported] 手動整合多來源資料係明顯摩擦點。
- [partially_supported] 如果 Portfolio Health Check 可一次過整合組合與風險，對此 persona 有實際價值。
- [partially_supported] 此 persona 願意為完整分析授權必要投資資料，但只限最小範圍。
- [weakened] 分析結果本身會直接推動佢即時調倉。
- [weakened] 只要有提醒，佢就會持續回來看。
- [invalidated] 銀行可用此服務自然承接到產品銷售。
- [partially_supported] 此 persona 需要銀行提供白話、可行動但保留自主權嘅解讀。

## Key Insights

- Because 佢最近真實係因現金需要同市況波動先臨時打開多個地方對配置，this persona would likely 只喺有事件觸發時先檢視整體組合，而唔係主動高頻管理，unless 服務可以喺相關時刻零額外整理成本咁呈現。 This means the product should 先服務事件觸發式檢視，而唔好假設每日或高頻使用。
- Because 跨 app、Notes、月結單手動拼資料會令佢覺得麻煩，甚至「拖住唔想再睇」，this persona would likely 放棄較完整但較費事嘅檢視，unless 一打開已經見到整體組合同偏離重點。 This means the product should 把首要價值放喺自動整合與即時摘要，而唔係先堆更多分析層。
- Because 佢對推銷動機、資料範圍、保存期限同風險算法都有明確戒心，this persona would likely 停留喺觀望甚至唔授權，unless 授權可逐項控制、用途透明，而且結果頁先提供中立選項而非產品推介。 This means the product should 把信任說明與非銷售式承接做成核心體驗，而唔係放喺次要說明。
- Because 佢見到偏離時「多數唔會即刻大郁」，而且如果解釋含糊就「未必會跟住做」，this persona would likely 把服務當作判斷輔助而非交易指令，unless 系統能清楚區分短期波動同結構性偏離。 This means the product should 以診斷、差距解釋同下一步選項為主，避免暗示單一路徑交易建議。

## Next Experiment

在現有銀行 app 做一個最小可點擊原型，只測一個入口同一個結果頁：於投資總覽頁或月結單後出現有理由的短提示，點入後即見整體資產分佈、偏離原因、資料來源範圍、及三個非產品式下一步選項（例如暫停加倉／改投另一邊／先觀察）。招募同類 persona 做 5-7 次任務式訪談，只觀察兩件事：1. 佢有冇即刻理解點解值得睇；2. 佢會唔會因資料授權與推銷疑慮而中止。
