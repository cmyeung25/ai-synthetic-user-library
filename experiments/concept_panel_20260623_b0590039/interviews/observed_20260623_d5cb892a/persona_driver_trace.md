# Persona Driver Trace: Iris Cheung

> This analysis is based on a synthetic persona artifact and interview transcript for AI pre-validation only. It does not replace human research evidence.

Research goal: Understand how unfinished V5 Hong Kong retail-banking personas currently manage investment portfolios, which Aladdin-based analytics functions would materially help them in real decisions, why those functions matter, and how each should be embedded into retail customer journeys without turning the experience into generic product selling.

## Surface Read

- Said: She checks her portfolio in ordinary household moments, specifically after dinner while supervising her son's homework, mainly to confirm where money stands rather than study markets (`exchange_1.persona`).
- Said: Her review flow is sequential and shallow-first: cash balance, upcoming card deductions and transfers, then MPF total and contribution status, with deeper inspection only if something looks off (`exchange_2.persona`).
- Said: A free portfolio health check feels somewhat useful because her holdings are split across apps, but only if she can quickly understand how it calculates and does not require too much external account data up front (`exchange_3.persona`).
- Said: She would initially allow only limited external-data access such as account type, products held, rough value range, and broad changes over time; she would not initially allow transaction details, family-related data, or transfer-capable permissions (`exchange_4.persona`).
- Said: If a risk alert appears, she would not trade immediately; she would first inspect the explanation, compare against her other apps, and only adjust gradually if it still seems valid (`exchange_5.persona`).
- Said: She wants the feature to appear at monthly review moments or after salary, and only lightly alert on meaningful changes; frequent prompts would become noise (`exchange_6.persona`).
- Said: She would reuse the feature if it saves time by surfacing key changes and risk shifts immediately, preserves rough cross-account distribution visibility, and avoids repeated reconnection or many steps; vague alerts or repeated permission expansion would stop usage (`exchange_7.persona`).
- Seemed to optimize for: Low-friction oversight with preserved control: fast situational clarity, reversible interpretation before action, and tight limits on data access and notification volume.
- Implicit: How much of her hesitation is about privacy versus simple setup burden.
- Implicit: Whether her current investing confidence is low, moderate, or merely low-attention.
- Implicit: How much she trusts the bank brand specifically versus trusting only transparent workflows.
- Implicit: Whether she would want human follow-up after an alert or prefers self-serve only.
- Implicit: What level of explanation would feel 'quickly understandable' in practice.

## Likely Drivers

- [high] Financial steadiness matters more to her than optimization upside, so she checks investments as part of broader cash-flow reassurance rather than as a separate investing activity. (core_value, mixed)
  Why: This explains why her portfolio review starts from bills, cash, and upcoming deductions before risk analysis. The health check is attractive only insofar as it helps her maintain an overall sense of stability.
  Transcript refs: exchange_1.persona, exchange_2.persona
  Profile refs: values.core_values, problem_context.jobs_to_be_done, human_difference_axes.relationship_to_money
- [high] She has a strong review-before-action habit and wants automation to inform, not decide. (decision_style, mixed)
  Why: Her response to alerts is to inspect, cross-check, and adjust slowly. A tool that jumps from analysis to recommendation or transaction would likely trigger resistance.
  Transcript refs: exchange_5.persona, exchange_7.persona
  Profile refs: technology_attitude.automation_openness, human_difference_axes.control_preference, personality_belief.decision_style
- [high] Trust is earned through transparent boundaries, especially around permissions and what the system can or cannot touch. (trust_pattern, mixed)
  Why: Her detailed distinction between analysis-only access and transfer-capable access suggests she is not reacting to 'data sharing' in the abstract; she is evaluating concrete exposure and controllability.
  Transcript refs: exchange_3.persona, exchange_4.persona, exchange_7.persona
  Profile refs: values.fears, technology_attitude.privacy_concern, adoption_style.trust_requirements, human_difference_axes.trust_style
- [high] Her daily life is fragmented but disciplined, so usefulness is judged by whether the next step is obvious inside a short attention window. (daily_constraint, mixed)
  Why: She describes checking during homework supervision and wants immediate key points, light prompts, and no repeated reconnection. That fits a phone-based, interruption-heavy routine rather than a dedicated portfolio-management session.
  Transcript refs: exchange_1.persona, exchange_6.persona, exchange_7.persona
  Profile refs: current_context, discovery_path_&_daily_friction.attention_shape, human_difference_axes.fragmentation_realit y, life_story.current_daily_routine
- [medium] She is willing to tolerate complexity only when it remains legible and under her control. (other, mixed)
  Why: She already manually reconstructs a cross-app picture in her head, which is cumbersome, yet still preferable to opaque automation. The feature becomes valuable only if it reduces effort without hiding the logic.
  Transcript refs: exchange_3.persona, exchange_7.persona
  Profile refs: contradiction_map, interests_that_affect_buying.how_it_shapes_purchase_behaviour, human_difference_axes.complexity_tolerance
- [high] She filters for signal quality quickly and drops tools that create background admin or alert fatigue. (decision_style, mixed)
  Why: Her threshold for repeated use is not novelty; it is whether the feature consistently highlights meaningful change and stays quiet otherwise.
  Transcript refs: exchange_6.persona, exchange_7.persona
  Profile refs: values.fears, deep_research_notes.dropoff_model, product_reaction_rules.negative_signals

## Unspoken Constraints

- [high] She likely has limited patience for any onboarding that feels like a second financial admin task.
  Why likely: She repeatedly anchors value to time saved, few steps, and not having to reconnect each time.
- [medium] She likely wants the feature to coexist with, not replace, her existing app-checking routine.
  Why likely: She describes verifying against other apps even after receiving a risk alert, suggesting continued parallel checking rather than full delegation.
- [high] She may be especially sensitive to anything that could expose household-linked information, not just her own holdings.
  Why likely: She explicitly excludes family-related data and the persona profile flags accidental family-information exposure as a fear.
- [medium] She probably needs explanation in plain operational terms, not market jargon.
  Why likely: She asks to quickly understand how the calculation works and focuses on practical questions like concentration and unusual movement rather than investment theory.

## Value Tensions

- [high] Convenience versus control: She wants one place that saves time across fragmented accounts. vs She resists broad permissions, opaque calculation, and direct action without review.
- [high] Monitoring for reassurance versus avoiding noise: She wants timely prompts around monthly review and material change. vs She does not want frequent alerts that become clutter or pressure.
- [high] Accepting useful institutional tools versus demanding higher privacy justification from new data flows: A bank-integrated view could reduce manual reconstruction across apps. vs External linking and sensitive permissions face a higher trust bar, especially if they touch family or transfer capability.

## Missed Follow-Up Questions

- [high] When you say you need to 'quickly understand how it calculates,' what exact explanation would be enough for you to trust the result on first use?
  Why: This would separate explanation needs from general privacy hesitation and make her trust threshold more concrete.
- [high] If the health check showed a concentration risk, what comparison or proof would make you believe it was not a false alarm?
  Why: Her transcript shows a verification habit, but not the actual evidence standard she would use.
- [medium] Which is the bigger reason you might stop using it after one try: too many permission requests, too many steps, or alerts that feel generic?
  Why: This would identify the main drop-off driver instead of treating several frictions as equal.
- [medium] Would you want this to stay fully self-serve, or would there be any point where you would want a banker to explain the result?
  Why: This would clarify service-embedding boundaries without assuming she wants sales follow-up.
