# Portfolio Health Check Interview: Maggie Lau

> 以上只屬單一 synthetic persona 的概念驗證前置訊號，不可當作真人市場證據或因果結論；所有洞察與假設仍需用真人訪談進一步驗證。

## Problem Evidence

- Strength: medium
- "其實幾土法。" (exchange_2.persona)
- "最好一開就見到而家太集中喺邊類、波動大概去到邊，同埋點解佢咁判斷" (exchange_3.persona)
- "如果仲要我先填好多資料或者開一堆權限，我就未必會再撳落去。" (exchange_3.persona)
- "我多數唔會即刻調。" (exchange_5.persona)
- "最好係我本身已經喺睇持倉、月供或者準備買入之前出現" (exchange_6.persona)
- "要佢真係次次都幫到手先得。" (exchange_7.persona)

## Current Workaround

- Pain: medium; switching: medium
- 用銀行 app 檢查現金、扣款、入帳。
- 用證券 app 檢查持倉金額、盈虧和通知。
- 兩個 app 之間手動來回比對，靠自己判斷是市值波動還是資金未過帳。
- 若發現偏離明顯，先記低，等下次供款或再買時再慢慢拉平均。

## Trust Boundary

- 先證明實際用途，再談額外資料連結。
- 要解釋點解判斷集中或波動，而不是只給訊號燈。
- 提醒不能成日嚇人，否則會削弱信任。

## First Value

- 一打開就見到目前太集中喺邊類。
- 一打開就見到波動大概去到邊。
- 清楚解釋點解系統會咁判斷。
- 最好放在睇持倉、月供或買入前等本來已有決策意圖的時刻。

## Pricing Signal

- Monthly comfort: 不適用；本次概念設定為免費，訪談中亦未測試付費意願。 (unknown)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 只提供表面訊號，冇原因解釋。
- Drop-off: 提醒太頻密或太驚嚇。
- Drop-off: 要求外部資料或過多權限。
- Drop-off: 需要重複設定或操作成本高。
- Drop-off: 出現時機不對，打斷原本流程。

## Assumption Validation

- [supported] Many retail banking customers still manage portfolios through fragmented, product-level, or event-driven views rather than a true whole-portfolio process.
- [partially_supported] The most important retail blind spots vary by person and should emerge from behaviour and life context, not be assumed in advance.
- [supported] Retail customers can identify specific Aladdin-type capabilities that would help if translated into practical retail decisions and simple explanations.
- [supported] The highest-value retail use cases are tied to real customer moments and workflows, not to exposing institutional detail for its own sake.
- [unknown] Some capabilities belong directly in self-serve retail channels, while others are better as RM-supporting or assisted-service features.
- [supported] Trust, data-sharing comfort, explanation style, and action threshold materially affect whether a free feature becomes part of normal behaviour.
- [supported] Deep insight requires understanding the participant's behavioural root causes, not just their surface feature preferences.
- [supported] Customers can describe clear boundaries on what an Aladdin-powered retail experience should and should not do.

## Key Insights

- 現況不是完整 portfolio 管理流程，而是跨銀行 app 與證券 app 的手動核對流程，主要目的是確認『數唔對路』究竟是市場波動還是資金未過帳。
- 對這位參與者有價值的不是抽象 risk score，而是可直接用於下一步決定的三件事：集中在哪類、波動去到邊、點解會有這個判斷。
- 功能應嵌在既有決策時刻，例如睇持倉、月供前、買入前；若在無意圖時亂推送，容易被視為打擾。
- 最重要的 trust boundary 是資料節制：先用本行已有資料證明價值，再談外部資產整合；一開始索取外部帳戶、MPF、其他券商、定位等會直接造成流失。
- 這位參與者的行動模式偏向漸進調整，不會因提示即時交易，所以輸出應支持『理解和記低，留待下次供款或買入時處理』的節奏。

## Next Experiment

用同類 persona 測兩個低保真版本：1) 在持倉頁/買入前頁面內嵌一個『集中度+原因解釋』卡片；2) 同樣內容用獨立 dashboard 入口呈現。比較哪一種更容易被理解、被信任，及是否更貼近其原有月供/加減持倉流程。
