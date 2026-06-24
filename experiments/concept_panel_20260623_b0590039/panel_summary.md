# Aladdin Solution In Retail Banking Synthetic Persona Panel

> This panel contains synthetic AI pre-validation only. It cannot establish market demand, pricing, prevalence, or replace interviews with real people.

- Personas: 1
- Language: Natural Cantonese Traditional Chinese
- Average interview quality: 4.0
- Problem evidence: {'medium': 1}

## Persona Results

### su_2005 - Iris Cheung

- Problem evidence: medium
- Pricing: 不適用／未測。 (unknown)
- Workflow effect: adds_layer
- Quality: 4/5

- Facilitator gap: Coverage over depth after initial concept fit was established.
- Driver: Financial steadiness matters more to her than optimization upside, so she checks investments as part of broader cash-flow reassurance rather than as a separate investing activity. (core_value, high)
- Driver: She has a strong review-before-action habit and wants automation to inform, not decide. (decision_style, high)
- Tension: Convenience versus control (She wants one place that saves time across fragmented accounts. vs She resists broad permissions, opaque calculation, and direct action without review.)
- Missed follow-up: When you say you need to 'quickly understand how it calculates,' what exact explanation would be enough for you to trust the result on first use?
- Audit follow-up gap: What exact explanation would be enough for you to trust the result on first use?
- Audit driver risk: The participant appears privacy-sensitive about external data access. -> The stronger driver may be a mix of control preservation, setup burden, and desire for analysis-only boundaries, not privacy alone.

- Because 佢最近一次檢視其實係月尾順手對數、而且「唔係想研究啲咩走勢」, this persona would likely只喺對數時段或者見到明顯異常先打開呢類功能, unless 提示真係對應到大變動而且唔騷擾。 This means the product should 嵌入月尾／出糧後檢查時刻，同時用高門檻異常觸發，避免高頻推送。
- Because 佢而家要分開幾個 app 睇，仲要「自己心入面砌返埋」, this persona would likely試用一個整合檢視, unless 首屏仍然睇唔出重點或者每次都要重新連接。 This means the product should 首屏直接顯示變動最大項、風險變化同大概分布，並盡量保留連接狀態去取代手動拼湊。
- Because 佢對資料權限界線好敏感，收到提醒後亦會先對返自己幾個 app 啲數, this persona would likely延遲授權同延遲行動, unless 計法、資料用途同只讀邊界講得非常清楚。 This means the product should 先用最少只讀資料做分析，逐層申請額外資料，並把『分析權限』同『可轉賬權限』明確分開。
- Because 佢講明「多數唔會即刻做交易」同「唔會一下子郁太多」, this persona would likely把提醒當成核對與慢慢調整嘅起點, unless 提醒證據不足或似推銷。 This means the product should 先支援理解與核對，再支援小幅調整，而唔係把提醒直接設計成交易 CTA。

## Common Likely Drivers

- Financial steadiness matters more to her than optimization upside, so she checks investments as part of broader cash-flow reassurance rather than as a separate investing activity. [core_value] across 1 personas: Iris Cheung
  Why it mattered: This explains why her portfolio review starts from bills, cash, and upcoming deductions before risk analysis. The health check is attractive only insofar as it helps her maintain an overall sense of stability.
- Her daily life is fragmented but disciplined, so usefulness is judged by whether the next step is obvious inside a short attention window. [daily_constraint] across 1 personas: Iris Cheung
  Why it mattered: She describes checking during homework supervision and wants immediate key points, light prompts, and no repeated reconnection. That fits a phone-based, interruption-heavy routine rather than a dedicated portfolio-management session.
- She filters for signal quality quickly and drops tools that create background admin or alert fatigue. [decision_style] across 1 personas: Iris Cheung
  Why it mattered: Her threshold for repeated use is not novelty; it is whether the feature consistently highlights meaningful change and stays quiet otherwise.
- She has a strong review-before-action habit and wants automation to inform, not decide. [decision_style] across 1 personas: Iris Cheung
  Why it mattered: Her response to alerts is to inspect, cross-check, and adjust slowly. A tool that jumps from analysis to recommendation or transaction would likely trigger resistance.
- She is willing to tolerate complexity only when it remains legible and under her control. [other] across 1 personas: Iris Cheung
  Why it mattered: She already manually reconstructs a cross-app picture in her head, which is cumbersome, yet still preferable to opaque automation. The feature becomes valuable only if it reduces effort without hiding the logic.
- Trust is earned through transparent boundaries, especially around permissions and what the system can or cannot touch. [trust_pattern] across 1 personas: Iris Cheung
  Why it mattered: Her detailed distinction between analysis-only access and transfer-capable access suggests she is not reacting to 'data sharing' in the abstract; she is evaluating concrete exposure and controllability.

## Common Unspoken Constraints

- She likely has limited patience for any onboarding that feels like a second financial admin task. across 1 personas: Iris Cheung
  Why likely: She repeatedly anchors value to time saved, few steps, and not having to reconnect each time.
- She likely wants the feature to coexist with, not replace, her existing app-checking routine. across 1 personas: Iris Cheung
  Why likely: She describes verifying against other apps even after receiving a risk alert, suggesting continued parallel checking rather than full delegation.
- She may be especially sensitive to anything that could expose household-linked information, not just her own holdings. across 1 personas: Iris Cheung
  Why likely: She explicitly excludes family-related data and the persona profile flags accidental family-information exposure as a fear.
- She probably needs explanation in plain operational terms, not market jargon. across 1 personas: Iris Cheung
  Why likely: She asks to quickly understand how the calculation works and focuses on practical questions like concentration and unusual movement rather than investment theory.

## Common Value Tensions

- Accepting useful institutional tools versus demanding higher privacy justification from new data flows across 1 personas: Iris Cheung
  Frame: A bank-integrated view could reduce manual reconstruction across apps. vs External linking and sensitive permissions face a higher trust bar, especially if they touch family or transfer capability.
- Convenience versus control across 1 personas: Iris Cheung
  Frame: She wants one place that saves time across fragmented accounts. vs She resists broad permissions, opaque calculation, and direct action without review.
- Monitoring for reassurance versus avoiding noise across 1 personas: Iris Cheung
  Frame: She wants timely prompts around monthly review and material change. vs She does not want frequent alerts that become clutter or pressure.

## Facilitator Audit Patterns

- Coverage over depth after initial concept fit was established. across 1 personas: Iris Cheung
  Assessment: The interview covered all required areas in seven exchanges, but depth was thin in the most decision-relevant areas: what explanation earns trust, what evidence prevents false-alarm dismissal, which friction is most disqualifying, and what concrete output would change behavior.

## Common Missed High-Value Follow-Ups

- [positive_concept_reaction] Even if it were clear and low-permission, in what situation would this still not be useful to you? across 1 personas: Iris Cheung
  Learning: After an initial positive reaction, add one disconfirming probe to learn the concept's non-use boundary.
- [multi-friction_dropoff] If only one of those problems remained, which one by itself would be most likely to make you stop using it? across 1 personas: Iris Cheung
  Learning: When multiple frictions are listed, force prioritization so the strongest driver is not lost in an undifferentiated list.
- [trust_boundary_statement] What exact explanation would be enough for you to trust the result on first use? across 1 personas: Iris Cheung
  Learning: When a participant asks for clarity or transparency, probe for the minimum explanation standard rather than recording 'needs clarity' as a complete insight.
- [timing_preference] What would make a notification feel meaningfully important versus just more noise? across 1 personas: Iris Cheung
  Learning: When participants mention alert fatigue, probe for the threshold between signal and noise rather than treating 'too frequent' as sufficiently specific.
- [verification_habit] What would you need to see to believe the alert is valid enough that you would not need a manual cross-check? across 1 personas: Iris Cheung
  Learning: If a participant says they would verify a recommendation elsewhere, ask for the evidence standard that would reduce or eliminate that verification step.

## Common Likely Misclassified Drivers

- The participant wants quick, simple summaries. -> The deeper need may be confidence-efficient review: fast comprehension that still feels auditable before action. across 1 personas: Iris Cheung
  Learning: Do not equate a request for speed or simplicity with low engagement; probe whether the participant wants less depth, or just faster access to defensible depth.
- The participant appears privacy-sensitive about external data access. -> The stronger driver may be a mix of control preservation, setup burden, and desire for analysis-only boundaries, not privacy alone. across 1 personas: Iris Cheung
  Learning: When permission resistance appears, separate sensitivity to data exposure, operational control, onboarding effort, and action authority before labeling the driver.
- The participant would use the feature if it saves time. -> Time saving may be secondary to reducing uncertainty without surrendering control. across 1 personas: Iris Cheung
  Learning: When 'save time' appears, ask what protected value the time-saving preserves: confidence, control, reduced stress, fewer mistakes, or something else.

## Assumption Matrix

### 1. 佢而家用分散式、淺層查看方式，主要係想快速確認資金安全感同現金節奏，而唔係主動做深入投資判斷。
- Counts: {'supported': 1}
- su_2005 Iris Cheung: supported - 有直接近期行為支持：佢明講『唔係想研究啲咩走勢』，而且通常『唔會睇得好深』，先看現金、扣數、供款，異常先再追查。

### 2. 概念要被持續使用，關鍵可能唔係分析深度，而係輸出是否夠快、夠清楚，同埋唔需要交出太多資料。
- Counts: {'partially_supported': 1}
- su_2005 Iris Cheung: partially_supported - 方向上有明確偏好證據，但主要來自概念後反應，不是已發生的採用或留存行為；因此只能部分支持。

## Next Experiments

- su_2005: 喺現有銀行 app 內，對少量有銀行資產加外部 MPF／投資帳戶嘅客戶，喺月尾或出糧後推一次只讀式『Portfolio Health Check』原型：首屏只顯示重點變動、風險變化、分布摘要，外部資料只申請最少授權。量度 1) 開啟後 60 秒內能否講得出「邊度變咗」；2) 最少授權接受率；3) 之後是否仍需返回原本 app 大量核對；4) 是否因提醒太空泛或權限要求而即時退出。
