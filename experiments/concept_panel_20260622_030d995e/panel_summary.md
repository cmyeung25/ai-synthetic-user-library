# HK Bank Portfolio Health Check V5 Two-Person Smoke Test Synthetic Persona Panel

> This panel contains synthetic AI pre-validation only. It cannot establish market demand, pricing, prevalence, or replace interviews with real people.

- Personas: 2
- Language: Natural Cantonese Traditional Chinese
- Average interview quality: 3.5
- Problem evidence: {'medium': 2}

## Persona Results

### su_2001 - Ivy Chan

- Problem evidence: medium
- Pricing: 未知；只知道定價要講清楚，唔好拆成幾層 plan。 (stated)
- Workflow effect: replaces_workflow
- Quality: 3/5

- 呢位受訪者唔係冇檢視投資，而係已經有固定月尾檢查習慣；真正 friction 係資料散、整合手動、理解成本高。
- 對 Portfolio Health Check 嘅價值判斷好務實：唔係因為『分析好勁』，而係要即刻幫佢見到集中、閒置或變化。
- 白話解釋係核心，不是加分項；太多行內字會直接削弱價值。
- 信任界線非常清晰：主動授權、只讀、最少資料、可隨時停、不可轉做推銷。
- 嵌入方式比功能清單更影響採用；首頁或投資總覽嘅輕量呈現，比獨立 analytics 專區更貼近佢現有行為。','進階付費有可能，但前提係免費核心先證明節省時間同提供持續實用提醒。','不應把人格判斷、風險貼標籤、監視式洞察直接暴露在零售 app。']

### su_2002 - Maggie Lau

- Problem evidence: medium
- Pricing: 未講明金額；偏向低價、可月付、可隨時停。 (stated)
- Workflow effect: replaces_workflow
- Quality: 4/5

- 對呢位 persona，『Portfolio Health Check』首先唔係投資優化工具，而係資金可動用性同風險提醒工具。
- 現時最大 friction 係手動整合多個來源，同埋睇到數字但唔知代表咩、應唔應該做啲咩。
- 初次採用門檻唔在於功能少，而在於設定同授權太重；先用銀行內資料係明顯較可接受嘅起點。
- 留存唔會靠日常 habit，本質更似事件觸發工具：大額支出、收入不穩、或者市場大波動時先會再開。
- 收費空間唔係靠更多圖表，而係靠實際減少對數工作、幫手避錯、同改善現金安排。

## Assumption Matrix

### 1. 客戶而家主要靠碎片化、手動方式管理投資組合，而唔係真正整體視圖。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者明確描述跨銀行 app 同券商 app 手動拼合，再用計數機對比例。
- su_2002 Maggie Lau: supported - 呢位受訪者明確講自己『冇好正式嗰種』整體組合管理，實際做法係分開 app 加截圖手動對數。

### 2. 簡化版整體分佈與風險說明，對零售客戶有明顯價值。
- Counts: {'supported': 1, 'partially_supported': 1}
- su_2001 Ivy Chan: supported - 受訪者第一時間指出最有用係一次過睇清持倉分佈，同埋風險要講得白。
- su_2002 Maggie Lau: partially_supported - 她清楚指出睇唔清實際蝕幾多、是否短期波動、以及應否做啲咩；但她最想解決的是可動用資金與簡單提醒，未見對更進階分析有強烈主動需求。

### 3. 免費會提升試用意願，但信任同銷售感仍然左右採用。
- Counts: {'supported': 1, 'partially_supported': 1}
- su_2001 Ivy Chan: supported - 受訪者願意考慮試用，但前提係只讀、有限資料、可停用、唔作推銷，否則唔會開。
- su_2002 Maggie Lau: partially_supported - 她接受『一眼睇』『清楚提醒』『避開咩錯』呢類具體輸出，但未有證據顯示她想理解較技術性的分析層。

### 4. 最好嵌入現有客戶流程，而唔係做成獨立複雜目的地。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者想放首頁或投資總覽，一打開就見到變化，並會將之納入固定月尾檢查。
- su_2002 Maggie Lau: supported - 她反覆強調要幫到判斷同現金安排，並直接否定『只是多幾個圖表』。

### 5. 部分能力應留喺簡單自助零售介面，部分唔應直接暴露畀用戶。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者明確拒絕貼標籤、過度判斷式建議同監視感分析。
- su_2002 Maggie Lau: supported - 她接受先用銀行內已有資料、自主決定是否擴充，亦偏好總覽頁旁邊的自然入口，而非重設定或強推式設計。

### 6. 重點盲點一定係重疊、集中度呢類 Aladdin 強項。
- Counts: {'partially_supported': 1, 'supported': 1}
- su_2001 Ivy Chan: partially_supported - 集中度對呢位受訪者有吸引力，但當前最直接痛點其實係跨 app 拼資料同節省時間，未見重疊視圖被主動提出。
- su_2002 Maggie Lau: supported - 即使免費，她仍介意外部資料連接、要先見價值，並在意入口唔似推銷。

### 7. 最佳嵌入位係現有客戶時刻，而唔係獨立複雜分析 destination。
- Counts: {'supported': 1}
- su_2002 Maggie Lau: supported - 她傾向在睇完結餘、基金或 MPF 後，於戶口總覽或投資頁面旁邊見到平實入口。

### 8. 客戶可以講得出零售銀行內應該暴露或唔應該暴露咩能力邊界。
- Counts: {'partially_supported': 1}
- su_2002 Maggie Lau: partially_supported - 她對資料授權邊界同入口語氣講得清楚，但未細分邊類分析該 self-serve、邊類該交畀 RM。

## Next Experiments

- su_2001: 用第二位香港 persona 重做同樣 concept interview，特別測試兩件事：1. 若本身冇固定月尾檢查習慣，首頁輕量提醒仲有冇價值；2. 對『外部持倉只讀連接』同『白話風險提示』嘅接受界線係咪一致。
- su_2002: 用同一概念測第二位香港 persona 時，刻意比較兩種入口同首屏：1.『幫你整理而家資產情況／可動用資金』式低負擔 summary；2.『投資健康分析』式較投資導向 summary，觀察邊個更自然、較少 sales 感、同更能帶出首次價值。
