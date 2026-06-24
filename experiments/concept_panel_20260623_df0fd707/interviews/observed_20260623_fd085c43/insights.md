# Portfolio Health Check Interview: Ivy Chan

> 此報告只基於單一 synthetic interview transcript，屬模擬前期概念驗證材料，不代表真人市場證據或普遍需求。

## Problem Evidence

- Strength: medium
- "「短時間連住幾日都跌，連我本身分散開嗰幾樣都一齊明顯向下，我就會開始覺得唔對路」" (exchange_2.persona)
- "「再唔望清楚就可能太遲」" (exchange_2.persona)
- "「嗰種我會當係正常噪音，唔想自己愈望愈想亂郁」" (exchange_3.persona)

## Current Workaround

- Pain: medium; switching: medium
- 自己喺銀行 app 睇幾隻基金同月供表現。
- 同時檢查戶口現金是否足夠。
- 見到提示或波動時，先自行打開持倉明細判斷係集中、波動，定短期市場震盪。
- 通常再觀察一兩日，並對返原本月供同現金安排先決定。

## Trust Boundary

- 先講清楚而家個組合有咩問題，而唔係先推產品。
- 講到『用咗我現有持倉咩資料、界線大概點定』。
- 容許『暫時唔處理』或者只係再觀察，唔好將每個結果都變成交易建議。

## First Value

- 一眼睇到短的健康摘要，並清楚指出問題類型，例如太集中或風險同原設定唔夾。
- 能直接睇到點解會有提示，同埋可進一步睇明細。
- 語言要『講人話』，唔係黑箱。
- 用完之後仍由佢自己決定是否處理，而唔係被帶去買產品。

## Pricing Signal

- Monthly comfort: 未知／不適用 (hypothetical)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 內容重覆，只係換句話叫佢留意風險。
- Drop-off: 進入重點前要撳幾層。
- Drop-off: 再次變成產品銷售入口。
- Drop-off: 提醒過密。

## Assumption Validation

- [supported] 呢位零售銀行客會因市場波動主動檢查投資組合，而唔係完全被動。
- [partially_supported] 整體風險／集中度摘要對呢位客有潛在幫助。
- [weakened] 只要係免費，呢位客就會採用 Portfolio Health Check。
- [invalidated] 風險提示會直接推動佢即時買賣。
- [partially_supported] 將功能嵌入銀行 app 現有檢視節點，會比獨立銷售式入口更貼近佢流程。
- [partially_supported] 重複使用主要取決於是否持續提供『有變化』的新資訊。

## Key Insights

- Because 佢最近係見到市場波動先主動開 app，而且用『連跌幾日兼多個持倉一齊向下』做門檻，this persona would 只喺感覺可能『太遲』之前先再深入睇，unless 波動只屬單日、局部而且唔影響月供同現金。This means the product should 用事件觸發同摘要式呈現去配合佢現有檢視頻率，而唔好預設高頻常駐互動。
- Because 佢明確怕『愈望愈想亂郁』同『每次講嘅都差唔多』，this persona would 關掉過密或重覆訊息，unless 每次都講到今次點解同上次唔同、影響大細有幾多。This means the product should 只喺狀態有變化時提醒，並突出變化來源、偏離幅度同較上次的變化。
- Because 佢對『借檢查推產品』有即時防備，this persona would 先把功能當成潛在銷售包裝，unless 畫面先講問題、解釋判斷依據，並容許『暫時唔處理』。This means the product should 把分析、理據同非交易結尾放前面，將產品推薦明確後置甚至分離。
- Because 佢見到提示後通常會先自己打開持倉明細，再觀察一兩日對返原本安排，this persona would 把 Health Check 當成二次核對工具而唔係交易指令，unless 提示非常具體而且有理據。This means the product should 直接連到相關持倉明細與原因拆解，支援『理解』先於『行動』。
- Because 佢想喺月供後／月尾見到短摘要，但只喺異常時接受明確提示，this persona would 接受輕量嵌入現有銀行旅程，unless 功能打斷流程或一彈就導去買產品。This means the product should 分成被動摘要同異常提示兩種入口，並保持由總覽到明細的自助路徑。

## Next Experiment

用這位 persona 類型客戶的匿名持倉快照，做一個最小可點擊原型，只測兩個畫面：1) 月尾／月供後首頁短摘要；2) 連跌幾日後的異常提示。兩個版本唯一差異係結尾有冇產品 CTA。觀察佢會唔會打開、能否講出提示原因、是否覺得被銷售、以及會唔會去睇持倉明細而唔係即時交易。
