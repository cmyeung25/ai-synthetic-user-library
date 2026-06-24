# Portfolio Health Check Interview: Maggie Lau

> 此報告只根據提供的 synthetic interview transcript 整理，屬模擬性前期概念驗證材料，不可視為真人市場證據。

## Problem Evidence

- Strength: weak
- "「其實我冇咩正式嘅投資組合」" (exchange_1.persona)
- "「主要係確認冇乜大波動，跟住就算。」" (exchange_1.persona)
- "「我唔會睇得好細」" (exchange_2.persona)
- "「我通常會再對一對自己手機入面啲notes」" (exchange_3.persona)

## Current Workaround

- Pain: medium; switching: low
- 用手機銀行看 MPF 大概結餘、是否明顯下跌、戶口現金餘額。
- 再對手機 notes 內已記下的學校、屋企、客戶相關支出時間。
- 有時翻 WhatsApp 或月曆提醒，確認有沒有快到期但銀行未見到的數。

## Trust Boundary

- 要先講清楚「邊一部分高咗」與「點解會咁講」。
- 輸出要可被原本銀行數字核對。
- 語氣不能太誇張，否則會被視為嚇人而不是有用。

## First Value

- 首次使用要一眼整合 MPF 與其他持有，減少自行拼湊。
- 要用簡單字說明風險。
- 要能快速進入，不需另外開太多權限。
- 第一次結果要夠準，且不誇張，讓用戶願意拿原始數字核對。

## Pricing Signal

- Monthly comfort: 不適用；訪談設定已指明此服務為免費，逐月付費訊號不可由本訪談推斷。 (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 參加者本身沒有正式投資組合管理習慣，天然重用頻率可能低。
- Drop-off: 若輸出空泛、誇張或通知過多，會很快被忽略。
- Drop-off: 若之後開始要求連更多資料，會增加棄用風險。

## Assumption Validation

- [invalidated] 這類零售客戶正主動做正式的投資組合管理，並有明確組合分析痛點。
- [supported] 參與者目前較少做正式投資組合管理，因為實際決策框架更偏向現金流與短期支出確認，而非投資配置優化。
- [partially_supported] 參與者採用新功能的門檻主要受『是否準確且不誇張』與『資料索取是否過度』影響。
- [partially_supported] 功能若嵌入喺支出後或有新提醒前後嘅檢查時刻，對參與者會比獨立投資儀表板更有實際價值。
- [partially_supported] 是否持續使用呢個功能，主要受輸出是否準確、不誇張同貼近手頭安排影響，而唔單係功能範圍多寡。
- [partially_supported] 一眼整合 MPF 與其他持有，對這位參加者會構成明顯首用價值。

## Key Insights

- Because 佢最近實際只係喺交完學校同屋企開支後「順手睇下MPF同戶口入面啲錢」去確認現金與大波動，而唔係做正式配置檢查, this persona would likely 把 Portfolio Health Check 當成支出前後的現金與風險 sanity check，而唔係長時間研究工具, unless 之後持倉變複雜到需要更主動管理. This means the product should 先服務『短期安排安全感』場景，避免一開始包裝成深度投資分析。
- Because 佢而家要自己用手機銀行、notes、WhatsApp、月曆去拼返支出時間差, this persona would likely 打開一個能夠即場整合現有資料的提醒, unless 個提醒只重複佢已知資訊. This means the product should 優先指出『銀行未必即時反映但快將影響安排』的情境，而唔係只講抽象風險。
- Because 佢明確話「未必即刻好信」，會先睇「講得準唔準」同「會唔會搞到太誇張嚇人」, this persona would likely 先核對提示與原本銀行數字，再決定之後有冇價值, unless 解釋已經清楚到可直接對上原始數據. This means the product should 每個風險提示都附上簡單原因與對應數字來源。
- Because 佢對資料索取邊界好敏感，尤其係其他銀行戶口、證券戶口、通訊錄、定位, this persona would likely 在首屏或首用就停下來, unless 功能先用現有銀行內資料證明到有用. This means the product should 採取『先用本行已有資料，後續再漸進要求擴展』的設計，而不是預設全量連結。
- Because 佢只會喺睇完結餘/MPF後順手望一望，而且容忍度低於誇張通知, this persona would likely 睇幾次後就忽略功能, unless 每次都快而且真係幫佢避到一次時間差或大額支出前的漏看. This means the product should 把成功門檻定義為少量高相關提醒，而不是高頻觸達。

## Next Experiment

在現有手機銀行原型內做一個最小可點擊流程：只用本行已有戶口與 MPF 資料，在『查看戶口結餘後』插入一張 Portfolio Health Check 卡片，僅顯示 1 個與即將到來大額支出/時間差相關的簡單風險提示與原因。找同類 persona 做 5-7 次任務式測試，觀察他們會否主動點入、能否用原始數字核對、以及會否覺得誇張或多餘。
