# Portfolio Health Check Interview: Maggie Lau

> 以上只係單一 synthetic persona 嘅概念驗證前測證據，用嚟收窄假設同設計下一輪人類訪談；唔可以當做人類市場證據或需求證明。

## Problem Evidence

- Strength: medium
- "我其實冇點樣定期主動睇，最多係隔一排先撳入銀行app望下MPF同少少基金。" (exchange_1.persona)
- "我通常第一眼係睇總數有冇明顯跌咗一截，唔會一開始就逐隻睇。" (exchange_2.persona)
- "如果個總數只係輕微上落，我多數就算，唔會再搞咁多。" (exchange_3.persona)
- "我會有少少興趣，因為呢啲其實正正係我平時唔想自己慢慢拆開嚟睇嘅嘢。" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: low
- 用銀行 app 睇 MPF 同少少基金。
- 先用整體總數做快速檢查。
- 靠自己記憶中上一次的大概金額比較。
- 如果見到提示或覺得有問題，再返去銀行原本資料對一對。
- 需要思考時會擺低一陣，等夜晚有空先再諗。

## Trust Boundary

- 要明顯係幫佢理解持倉，而唔係包裝成免費檢查去推產品。
- 要用簡單語言講清楚邊部分集中、集中到咩程度。
- 最好有清楚但唔煩嘅前後比較，令佢知道情況係好咗定差咗。

## First Value

- 兩三下就睇到結果。
- 一眼幫佢拆開平時唔想自己慢慢睇嘅整體風險或集中情況。
- 唔止話你集中，仲講清楚集中喺邊同程度有幾多。
- 最好喺佢已經有疑問嗰刻出現，例如睇完總數或市況波動時。

## Pricing Signal

- Monthly comfort: 未測試；本次研究設為免費，冇可用月費區間證據。 (unknown)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 只係一次性提示，冇比較基準。
- Drop-off: 太多權限要求。
- Drop-off: 被視為廣告或產品推銷。
- Drop-off: 提醒太早或太遲。
- Drop-off: 資訊太複雜，唔夠簡單。

## Assumption Validation

- [supported] 好多零售客仍然用碎片化、產品層級、事件觸發方式管理投資，而唔係真正 whole-portfolio process。
- [partially_supported] 最重要 blind spot 會因人而異，唔應預設。
- [supported] 只要翻譯成實際零售決策語言，客戶可以指出有用嘅 Aladdin 類能力。
- [supported] 最高價值 use case 係綁定真實客戶時刻，而唔係單純展示機構級分析。
- [unknown] 有啲能力適合 self-serve，有啲可能更適合 RM 或 assisted service。
- [supported] 信任、資料授權舒適度、解釋方式、行動門檻會影響免費功能能否變成日常習慣。
- [partially_supported] 深層洞察要理解行為根因，而唔只係表面 feature preference。
- [supported] 客戶可以講出 Aladdin-powered retail experience 應該做同唔應該做嘅邊界。

## Key Insights

- 呢位參與者而家唔係做正式 portfolio management，而係用『見到市況唔穩就快速確認有冇出事』嘅事件觸發模式。
- 現有 workflow 係先睇總數，再靠記憶比較，只有異常先深入；真正缺口係缺少一個快速、簡單、整體化嘅解釋層。
- Portfolio Health Check 對佢有吸引力，因為可以代替手動拆開分析，但前提係真係簡單，唔好變成機構級術語堆砌。
- 最有潛力嘅輸出唔係單次『你太集中』，而係『集中喺邊、程度如何、同上次比有冇改善』呢種可比較、低負擔嘅 summary。
- 信任風險非常實際：任何多餘權限、過量資料請求、過早彈窗或後續推銷，都會即刻將功能由『有用工具』變成『廣告』。

## Next Experiment

用 2-3 個低保真 concept variant 做下一輪：1. 睇完總數後出現嘅簡短比較卡；2. 市況波動時嘅集中度 alert；3. 月度前後比較 summary。測試邊種輸出格式最唔似推銷、最容易明白、同最能推動佢返去再睇一次。
