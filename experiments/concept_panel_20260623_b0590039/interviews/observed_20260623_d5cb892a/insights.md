# Portfolio Health Check Interview: Iris Cheung

> 以上只係基於單一 synthetic persona 訪談逐句整理嘅概念驗證摘要，屬模擬前期研究材料，不可當作真人市場證據或普遍需求證明。

## Problem Evidence

- Strength: medium
- "「唔係想研究啲咩走勢，主要係…想確認下啲錢擺成點，自己心入面有個數。」" (exchange_1.persona)
- "「我通常唔會睇得好深…如果見到個數有啲唔對路，我先再撳入去睇邊一部分郁得比較多。」" (exchange_2.persona)

## Current Workaround

- Pain: medium; switching: medium
- 月尾或有生活開支壓力感時，手動開銀行 app 睇現金、扣數、自動轉賬。
- 再開 MPF app 睇總數變化同供款入帳。
- 靠自己『心入面砌返埋』銀行內外資產概況。
- 見到異常時，先再撳入去逐部分核對。

## Trust Boundary

- 要『好快睇得明佢點樣計』。
- 要清楚分開邊啲資料只係用嚟分析、邊啲唔會郁到佢啲錢。
- 如果提醒出現，內容要講清楚係集中度問題定波動變大，否則會先停一停。

## First Value

- 一入去已經見到重點。
- 清楚指出邊度變動大、風險有冇高咗。
- 可以對返其他戶口嘅大概分布。
- 唔使重新連接，亦唔使行好多步。

## Pricing Signal

- Monthly comfort: 不適用／未測。 (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 提醒太空泛。
- Drop-off: 推送太密。
- Drop-off: 經常要求更多權限。
- Drop-off: 每次都要重新連接。
- Drop-off: 操作流程太長。

## Assumption Validation

- [supported] 佢而家用分散式、淺層查看方式，主要係想快速確認資金安全感同現金節奏，而唔係主動做深入投資判斷。
- [partially_supported] 概念要被持續使用，關鍵可能唔係分析深度，而係輸出是否夠快、夠清楚，同埋唔需要交出太多資料。

## Key Insights

- Because 佢最近一次檢視其實係月尾順手對數、而且「唔係想研究啲咩走勢」, this persona would likely只喺對數時段或者見到明顯異常先打開呢類功能, unless 提示真係對應到大變動而且唔騷擾。 This means the product should 嵌入月尾／出糧後檢查時刻，同時用高門檻異常觸發，避免高頻推送。
- Because 佢而家要分開幾個 app 睇，仲要「自己心入面砌返埋」, this persona would likely試用一個整合檢視, unless 首屏仍然睇唔出重點或者每次都要重新連接。 This means the product should 首屏直接顯示變動最大項、風險變化同大概分布，並盡量保留連接狀態去取代手動拼湊。
- Because 佢對資料權限界線好敏感，收到提醒後亦會先對返自己幾個 app 啲數, this persona would likely延遲授權同延遲行動, unless 計法、資料用途同只讀邊界講得非常清楚。 This means the product should 先用最少只讀資料做分析，逐層申請額外資料，並把『分析權限』同『可轉賬權限』明確分開。
- Because 佢講明「多數唔會即刻做交易」同「唔會一下子郁太多」, this persona would likely把提醒當成核對與慢慢調整嘅起點, unless 提醒證據不足或似推銷。 This means the product should 先支援理解與核對，再支援小幅調整，而唔係把提醒直接設計成交易 CTA。

## Next Experiment

喺現有銀行 app 內，對少量有銀行資產加外部 MPF／投資帳戶嘅客戶，喺月尾或出糧後推一次只讀式『Portfolio Health Check』原型：首屏只顯示重點變動、風險變化、分布摘要，外部資料只申請最少授權。量度 1) 開啟後 60 秒內能否講得出「邊度變咗」；2) 最少授權接受率；3) 之後是否仍需返回原本 app 大量核對；4) 是否因提醒太空泛或權限要求而即時退出。
