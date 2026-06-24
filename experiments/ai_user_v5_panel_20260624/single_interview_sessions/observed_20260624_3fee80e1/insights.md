# AI synthetic-user platform Interview: Mandy Cheung

> 本報告只根據本次 synthetic concept-validation transcript 的已問已答內容整理，屬模擬性前驗證證據，不代表真人市場證明，亦不應外推為普遍需求或採用率。

## Problem Evidence

- Strength: strong
- "「有一次我睇住幾個 trial 新用戶，發現佢哋開咗 account 之後，卡咗喺一頁要填幾樣背景資料先可以繼續。」" (exchange_2.persona)
- "「其中一個人隔咗十幾分鐘先再郁，最後直頭無完成。」" (exchange_2.persona)
- "「嗰一下對我嚟講已經唔係 sample size 問題，因為個阻力太近門口，同埋我自己一睇都知我哋係要求咗信任先，但未畀到任何回報。」" (exchange_3.persona)
- "「分別唔係佢哋突然有耐性，而係佢知道填完會換到咩返嚟，個交易感清楚好多。」" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: medium
- 隔一段時間自己重新走一次 flow，判斷是否一眼看得明白『填呢步係換緊咩返嚟』。
- 看 trial 用戶填完後有沒有即刻繼續探索，或用該結果做下一步，作為承諾是否清楚的代理訊號。
- 當入口問題未能清楚換到回報時，直接延後或刪減前置問題。

## Trust Boundary

- 要講清楚『邊類輸入要求太早』。
- 要講清楚『價值交換點樣唔清楚』。
- 要講清楚『同前後步驟相比點解呢度特別易斷』。
- 最好提供可對照改法，讓她分辨是真摩擦還是被分析帶住走。

## First Value

- 能幫她判斷『呢條問題值唔值得放喺入口』。
- 能清楚拆出某一步為何會卡，支持她決定哪些問題延後、哪些必須保留。
- 輸出已把可疑位、判斷形成方式、其他合理解讀攤開，令她只需做取捨而不用重新拆題。

## Pricing Signal

- Monthly comfort: unknown (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 若每次仍要她自己重新拆題或補假設，她多數用一兩次就停。
- Drop-off: 若平台長期把曖昧位講得過分肯定，她會失去信任。
- Drop-off: 若短 sanity check 也變成額外工作，平台就變成加層而非減負。

## Assumption Validation

- [supported] 受訪者目前在 setup flow 入口問題上有真實、近期的決策痛點。
- [partially_supported] 若 AI synthetic-user platform 能指出最易卡住的一步，受訪者就會直接照住改。
- [partially_supported] 信任關鍵在於平台是否公開判斷路徑、假設和替代解讀。
- [partially_supported] 若平台能減少她每星期都會遇到的 setup 判斷重工，她會重複使用。
- [partially_supported] 若平台經常過度簡化曖昧問題或需要她替平台收尾，她會停用。

## Key Insights

- Because 受訪者最近親眼見到 trial 新用戶在前置背景資料頁停住，甚至隔十幾分鐘後仍未完成，她 would likely 先刪減或延後入口問題，而不是再等更多 sample， unless 後面的回報已被清楚說明並會即時改變體驗。 This means the product should 優先幫她判斷『哪些入口問題沒有足夠價值交換支撐』，而不是泛泛評分整個 onboarding。
- Because 她現時主要靠自己重走 flow，加上看 trial 後續動作去判斷承諾是否清楚，她 would likely 把平台當成前置判斷輔助，而不是最後決策者， unless 平台已把可疑位、形成原因與其他合理解讀一併攤開。 This means the product should 輸出可審核的推理結構，直接對接她現有的人工 sanity check。
- Because 她明確抗拒黑箱式『高風險』結論，也怕被講得太順的分析帶住走，她 would likely 拒絕只給單一路徑歸因的輸出， unless 平台同時說明假設、前後步驟對比，以及相近但相反的解讀。 This means the product should 把解釋透明度設為核心交付，而不是把結論包裝得更像權威答案。
- Because 她只會重開能直接改動每星期都遇到的 setup 判斷的工具，她 would likely 用一兩次後停用任何只增加閱讀工作量的分析工具， unless 輸出能把她的工作縮到只剩最終取捨。 This means the product should 先聚焦一個高頻決策切口，例如『入口問題保留／延後／刪走』，而不是做廣泛研究報告。

## Next Experiment

用一個真實但小範圍的 setup flow 決策做人工服務實驗：挑 1 個即將上線的入口問題，產出 1 份 synthetic-user 分析，只覆蓋『是否應留在入口、為何、有哪些替代解讀、兩個細改版選項及代價』。交付後只觀察兩件事：她是否用這份輸出直接做出保留／延後／刪走取捨，以及她的 sanity check 是否明顯短於平時。
