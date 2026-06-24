# Aladdin Solution In Retail Banking Synthetic Persona Panel

> This panel contains synthetic AI pre-validation only. It cannot establish market demand, pricing, prevalence, or replace interviews with real people.

- Personas: 5
- Language: Natural Cantonese Traditional Chinese
- Average interview quality: 3.0
- Problem evidence: {'medium': 2, 'unknown': 3}

## Persona Results

### su_2001 - Ivy Chan

- Problem evidence: medium
- Pricing: 不適用；今次冇測價格。 (unknown)
- Workflow effect: replaces_workflow
- Quality: 3/5

- Facilitator gap: Coverage was prioritized over depth after concept introduction, causing missed follow-ups on real past analogs, decision thresholds, and concrete next actions.
- Audit follow-up gap: Can you walk me through the last time you noticed something was off but chose not to act right away? What made it a 'note for later' instead of a follow-up then?
- Audit driver risk: The participant seemed to be expressing a feature preference for one type of signal over another. -> The stronger underlying driver may have been decision efficiency: reducing the work needed to judge whether follow-up is warranted.
- 呢位受訪者而家做緊嘅唔係正式再平衡流程，而係事件觸發式健康檢查：見市況波動就打開幾個 app，快速確認比例有冇偏離。
- 最有價值嘅唔係抽象 risk score，而係『集中度由邊隻持倉拉高、而家去到幾多、同原本差幾遠』呢類可直接判斷嘅資訊。
- 功能如果只提供 generic 風險提醒，會被視為噪音；要建立信任，必須把訊號翻譯成具體持倉、差距同不處理的後果。
- 呢個 persona 唔想被系統催促交易；佢要嘅係更快完成『要唔要跟進』判斷，而唔係自動化決策。
- 最佳嵌入位係主動檢查投資組合時，或者月尾本來會睇戶口的 routine moment；過多 push 會直接損害接受度。

### su_2002 - Maggie Lau

- Problem evidence: medium
- Pricing: 不適用；本次概念設定為免費，訪談中亦未測試付費意願。 (unknown)
- Workflow effect: replaces_workflow
- Quality: unknown/5

- 現況不是完整 portfolio 管理流程，而是跨銀行 app 與證券 app 的手動核對流程，主要目的是確認『數唔對路』究竟是市場波動還是資金未過帳。
- 對這位參與者有價值的不是抽象 risk score，而是可直接用於下一步決定的三件事：集中在哪類、波動去到邊、點解會有這個判斷。
- 功能應嵌在既有決策時刻，例如睇持倉、月供前、買入前；若在無意圖時亂推送，容易被視為打擾。
- 最重要的 trust boundary 是資料節制：先用本行已有資料證明價值，再談外部資產整合；一開始索取外部帳戶、MPF、其他券商、定位等會直接造成流失。
- 這位參與者的行動模式偏向漸進調整，不會因提示即時交易，所以輸出應支持『理解和記低，留待下次供款或買入時處理』的節奏。

### su_2003 - Wong Mei Lin

- Problem evidence: unknown
- Pricing: unknown (unknown)
- Workflow effect: unclear
- Quality: unknown/5


### su_2004 - Wong Mei Ling

- Problem evidence: unknown
- Pricing: unknown (unknown)
- Workflow effect: unclear
- Quality: unknown/5


### su_2005 - Iris Cheung

- Problem evidence: unknown
- Pricing: unknown (unknown)
- Workflow effect: unclear
- Quality: unknown/5


## Facilitator Audit Patterns

- Coverage was prioritized over depth after concept introduction, causing missed follow-ups on real past analogs, decision thresholds, and concrete next actions. across 1 personas: Ivy Chan
  Assessment: Good breadth and conversational flow; insufficient depth on the highest-signal clues once the participant revealed a concrete workaround and a credibility threshold.

## Common Missed High-Value Follow-Ups

- [workaround_contains_delay_or_deferral] Can you walk me through the last time you noticed something was off but chose not to act right away? What made it a 'note for later' instead of a follow-up then? across 1 personas: Ivy Chan
  Learning: When a participant describes deferral, ask for a specific recent instance and the threshold that separates noticing from acting.
- [hypothetical_action_claim] Have you ever received anything similar before, from any tool or person? What did you actually do next that time? across 1 personas: Ivy Chan
  Learning: Convert hypothetical action claims into evidence by asking for the closest real-world analog and observed follow-through.
- [workflow_timing_preference] If you saw it at that moment, what would be the very next step you would take in the product or outside it? across 1 personas: Ivy Chan
  Learning: Do not stop at timing preferences; ask for the immediate action path to ground embedding recommendations.
- [participant_names_trust_criterion] What is the minimum information that would still feel too weak to act on, even if the alert looked relevant? across 1 personas: Ivy Chan
  Learning: After a participant states what would build trust, add a contrast probe to define the failure boundary.
- [repeat_use_claim] What would happen in the first two or three uses that would make you stop checking it, even if you liked the idea at first? across 1 personas: Ivy Chan
  Learning: Separate initial appeal from sustained use with an early-dropoff probe.

## Common Likely Misclassified Drivers

- The participant seemed to be expressing a feature preference for one type of signal over another. -> The stronger underlying driver may have been decision efficiency: reducing the work needed to judge whether follow-up is warranted. across 1 personas: Ivy Chan
  Learning: When a participant appears to prefer a feature, test whether the real driver is speed, confidence, coordination, or avoidance of extra work.
- The participant seemed to be describing a preferred notification moment. -> The stronger underlying driver may have been workflow protection: wanting support only when it fits an existing review routine and does not create interruption cost. across 1 personas: Ivy Chan
  Learning: Treat stated timing preferences as potential proxies for a deeper control or interruption boundary and probe that boundary directly.

## Assumption Matrix

### 1. 好多零售客仍然用碎片化、產品層級視角管理組合，而唔係真正 whole-portfolio process。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者係分開銀行 app 同券商 app 睇，再靠自己整合判斷。
- su_2002 Maggie Lau: supported - 參與者明確以銀行 app 與證券 app 之間手動比對方式處理，觸發亦來自市況反覆，屬事件驅動和分散視圖。

### 2. 最重要嘅 blind spot 因人而異，應由行為同情境浮現。
- Counts: {'partially_supported': 2}
- su_2001 Ivy Chan: partially_supported - 今次個案明確指出集中度最有用，但只係一位 persona，未足以代表其他人。
- su_2002 Maggie Lau: partially_supported - 此個案最在意的是集中度、波動解釋、提示不要過度驚嚇，以及操作 friction；未見其特別強調其他盲點如目標連結或 FX。單一個案只能部分支持異質性。

### 3. 零售客如果用簡單語言包裝，可以指出具體 analytics 功能對實際決策有幫助。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 集中度、分布差距、具體風險解釋都被視為有用，但前提係講人話。
- su_2002 Maggie Lau: supported - 參與者具體指出希望看到集中在哪類、波動程度及判斷原因，並說明這些資訊如何影響其供款或再買決定。

### 4. 最高價值 use case 會綁定真實客戶時刻，而唔係為咗展示機構級分析而展示。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者想喺主動檢查組合或月尾順手睇戶口時見到，而唔係平日被動轟炸。
- su_2002 Maggie Lau: supported - 參與者清楚把價值綁在睇持倉、月供、買入前等時刻，而非平常推送或抽象分析。

### 5. 有啲能力適合 self-serve retail，有啲更適合 RM 或 assisted service。
- Counts: {'unknown': 2}
- su_2001 Ivy Chan: unknown - 今次冇直接測 RM 或 assisted-service 邊界。
- su_2002 Maggie Lau: unknown - 訪談未有直接測試 RM 介入或哪些功能應保留在 assisted service。

### 6. trust、資料邊界、解釋方式同 action threshold 會影響免費功能會唔會成為日常習慣。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者明確要求具體解釋、少推送、提醒要準，先會持續用。
- su_2002 Maggie Lau: supported - 參與者多次把採納與重用條件連到資料邊界、清楚解釋、不過度驚嚇，以及自己通常不即時交易的節奏。

### 7. 深層洞察需要理解表面功能偏好背後嘅行為原因。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 佢唔即時賣出，係因為要先分辨成因，再連同現金需要一齊考慮；持續使用條件亦係節省判斷時間。
- su_2002 Maggie Lau: supported - 其真正工作不是『想看更多圖表』，而是想分辨異常是否來自資金流或市值波動，並避免在短期波動時亂動作。

### 8. 客戶可以講清楚呢類體驗應該做乜同唔應該做乜。
- Counts: {'supported': 2}
- su_2001 Ivy Chan: supported - 受訪者清楚講出應有解釋、出現時機、通知邊界同持續使用條件。
- su_2002 Maggie Lau: supported - 參與者能明確說出應做的事（清楚、快、指出忽略的集中位、在對的時刻出現）及不應做的事（過多權限、亂彈、重設、嚇人）。

## Next Experiments

- su_2001: 用下一位 persona 測試對比場景：一版只顯示 generic 風險提醒，另一版顯示『持倉名稱 + 目前比重 + 與目標差距 + 不處理後果』，觀察邊種更能令受訪者描述出明確下一步，並再加入 RM/assisted-service 邊界問題。
- su_2002: 用同類 persona 測兩個低保真版本：1) 在持倉頁/買入前頁面內嵌一個『集中度+原因解釋』卡片；2) 同樣內容用獨立 dashboard 入口呈現。比較哪一種更容易被理解、被信任，及是否更貼近其原有月供/加減持倉流程。
- su_2003: 
- su_2004: 
- su_2005:
