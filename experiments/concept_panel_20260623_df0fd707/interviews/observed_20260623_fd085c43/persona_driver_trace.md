# Persona Driver Trace: Ivy Chan

> This is a synthetic interpretation for AI pre-validation only. It does not replace human interview evidence.

Research goal: Understand how a Hong Kong retail-banking persona currently manages investment portfolios, which Aladdin-based analytics functions would materially help in real decisions, why those functions matter, and how they should be embedded into retail banking journeys without turning the experience into product selling.

## Surface Read

- Said: She checks her portfolio in short, practical moments tied to routine, such as after her daughter is asleep, and often in response to market-volatility news, but she does not act immediately (`exchange_1.persona`).
- Said: She judges 'too fast a drop' more by pattern and breadth than by a fixed threshold: several consecutive down days and multiple diversified holdings falling together trigger closer attention (`exchange_2.persona`).
- Said: She distinguishes normal noise from meaningful risk and deliberately avoids over-checking because too much monitoring can push her into bad reactive decisions (`exchange_3.persona`).
- Said: Her first reaction to a free Portfolio Health Check is guarded interest: she wants to know whether it is genuinely diagnostic or a disguised sales funnel (`exchange_4.persona`).
- Said: To trust the feature, she wants clear identification of the issue, some transparency into how the judgment was made, and an option to defer action rather than being pushed into switching or buying products (`exchange_5.persona`).
- Said: If a risk alert appears, she wants to inspect the underlying holdings and usually waits, cross-checks against her monthly contribution and cash setup, and only acts if the alert is specific and well reasoned (`exchange_6.persona`).
- Said: She would use the feature in two moments: lightweight periodic summaries after monthly contribution or month-end review, and stronger alerts only when conditions materially change, such as several down days or a concentration jump (`exchange_7.persona`).
- Said: She wants passive summaries embedded in normal account views and alerts that explain why they appeared and link to detail, without redirecting her into product purchase journeys (`exchange_8.persona`).
- Said: She would stop using the feature if it repeats generic warnings, hides the key point behind too many taps, or repeatedly routes into product recommendations (`exchange_9.persona`).
- Said: She defines 'new information' as change-based explanation: what changed, why it changed, and by how much versus her prior state or intended allocation (`exchange_10.persona`).
- Seemed to optimize for: Practical oversight with low noise: enough signal to notice real portfolio drift or risk, while preserving control, avoiding reactive moves, and filtering out product-selling or repetitive prompts.
- Implicit: Her portfolio review behavior appears shaped by fragmented time and mobile-first use, but she did not state that directly in the interview.
- Implicit: She did not explicitly discuss privacy or data permissions here, though her suspicion of hidden motives suggests broader trust boundaries.
- Implicit: She did not explicitly define a target risk framework or investing philosophy; her behavior is more heuristic and routine-based than formally model-driven in the transcript.

## Likely Drivers

- [high] Reliability-over-hype trust filter (core_value, mixed)
  Why: Her answers consistently test whether the feature is genuinely useful in ordinary use or just polished packaging for sales. She looks for plain explanation, visible logic, and restraint before trusting the output.
  Transcript refs: exchange_4.persona, exchange_5.persona, exchange_8.persona, exchange_9.persona
  Profile refs: values.core_values, personality_belief.trust_orientation, product_reaction_rules.negative_signals, human_difference_axes.trust_style
- [high] Control-preserving decision style (decision_style, mixed)
  Why: She does not want the tool to collapse analysis into action. She wants review control, the ability to inspect detail, and space to wait before making a move, especially under volatility.
  Transcript refs: exchange_3.persona, exchange_5.persona, exchange_6.persona, exchange_8.persona
  Profile refs: personality_belief.decision_style, technology_attitude.automation_openness, human_difference_axes.control_preference, contradiction_map
- [high] Interruption-shaped routine fit (daily_constraint, mixed)
  Why: She prefers short summaries at existing review moments and low-noise alerts only when something materially changes. That suggests the feature must fit into fragmented, time-limited checking habits rather than requiring a dedicated analysis session.
  Transcript refs: exchange_1.persona, exchange_7.persona, exchange_8.persona, exchange_9.persona
  Profile refs: life_story.current_daily_routine, problem_context.active_pain_points, human_difference_axes.life_load, human_difference_axes.fragmentation_reality
- [high] Downside-aware financial mindset (core_value, mixed)
  Why: She monitors for signs that a situation may require attention, but avoids overreacting to ordinary market noise. Her behavior reflects caution, containment, and preserving stability over chasing optimization.
  Transcript refs: exchange_1.persona, exchange_2.persona, exchange_3.persona, exchange_6.persona
  Profile refs: values.fears, personality_belief.risk_tolerance, human_difference_axes.risk_orientation, problem_context.jobs_to_be_done
- [high] Need for concrete, change-based explanation (knowledge_gap, mixed)
  Why: She is not asking for abstract analytics sophistication. She wants the system to explain what changed, why it changed, and how far it moved from prior state or intended setup. That is a comprehension requirement, not just a UX preference.
  Transcript refs: exchange_5.persona, exchange_6.persona, exchange_10.persona
  Profile refs: values.trust_requirements, human_difference_axes.need_for_explanation, product_reaction_rules.first_checks
- [medium] Sales-resistance built from prior overpromising-software skepticism (past_experience, mostly_inferred)
  Why: Her repeated concern that the check could be a disguised product push likely reflects accumulated exposure to tools or services that claim to help but add agenda, friction, or noise. She is testing motive as much as function.
  Transcript refs: exchange_4.persona, exchange_5.persona, exchange_8.persona, exchange_9.persona
  Profile refs: life_story.frustrations, problem_context.active_pain_points, deep_research_notes.summary

## Unspoken Constraints

- [high] Any feature that requires too much tapping, reading, or session time will lose her quickly even if the analytics are sound.
  Why likely: She asks for a short summary in routine moments, dislikes repeated generic content, and says she will stop if it takes several layers to reach the point.
- [medium] She likely needs mobile-first continuity and resumability rather than a desktop-style analysis workflow.
  Why likely: Her portfolio check happens at night inside the bank app in short bursts, and her broader profile emphasizes phone-based fragmented management.
- [high] She will discount analytics that cannot separate structural risk change from temporary market movement.
  Why likely: She explicitly distinguishes normal one-day noise from multi-day, broad-based decline and asks for explanations of whether change came from her actions or market movement.
- [high] She may treat recommendation-heavy presentation as evidence the bank's incentives are misaligned with her needs.
  Why likely: She repeatedly frames the core trust question as 'help me understand' versus 'use this to sell me something.'

## Value Tensions

- [high] Wants more clarity, but resists being pushed into action: She is interested in a portfolio-level view that helps her see concentration and risk more clearly. vs She does not want alerts or diagnostics to bypass her judgment or funnel her into transactions.
- [high] Wants simplicity, but only if it is substantively informative: She asks for a short summary and low-friction entry points. vs She rejects simplified outputs when they become repetitive, generic, or black-box.
- [high] Wants timely warnings, but dislikes noise and emotional escalation: She wants alerts when there is a real change such as several down days or concentration jump. vs She explicitly avoids over-checking and wants alerts that are clear but not alarming or frequent.

## Missed Follow-Up Questions

- [high] When you say you would trust it more if it shows how it reached the judgment, what is the minimum explanation that feels enough to you: asset breakdown, comparison to your past allocation, or plain-language reason codes?
  Why: This would separate her need for transparency from any need for deeper technical analytics, and make the acceptable explanation boundary more concrete.
- [high] If the alert says concentration rose, which comparison matters more to you: versus your own target, versus last month, or versus a general benchmark?
  Why: She clearly values change-based context, but the transcript does not reveal which baseline would make the insight actionable to her.
- [high] What would make you feel an alert is informative rather than sales-led once you tap in: no product cards at all, product suggestions hidden behind a second step, or a clear separation between diagnosis and optional next actions?
  Why: Her strongest objection is motive-trust. This would identify the exact presentation boundary that preserves credibility.
- [medium] When you decide to wait one or two days before acting, what are you looking for in that period?
  Why: This would expose her real decision rule under uncertainty and show whether analytics could support that waiting phase without pushing a trade.
