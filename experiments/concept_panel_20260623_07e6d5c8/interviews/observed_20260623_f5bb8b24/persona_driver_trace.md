# Persona Driver Trace: Wong Mei Ling

> This trace is based on a synthetic persona artifact and interview transcript for AI pre-validation only. It does not replace human research evidence.

Research goal: Understand how unfinished V5 Hong Kong retail-banking personas currently manage investment portfolios, which Aladdin-based analytics functions would materially help them in real decisions, why those functions matter, and how each should be embedded into retail customer journeys without turning the experience into generic product selling.

## Surface Read

- Said: She last reviewed her portfolio seriously at the end of last month because school fees were due and market volatility news made her want to check whether her allocation had drifted. (`exchange_1.persona`)
- Said: She currently pieces together the full picture from the bank app, fund account, Notes with buy prices and intended role of holdings, and sometimes WhatsApp or email statements; having to assemble this across places feels annoying and leads to delay. (`exchange_2.persona`)
- Said: A free Portfolio Health Check sounds somewhat useful if it can show diversification and risk in one place, but she immediately wants to know whether it includes other accounts, how risk is calculated, and whether 'free' is really free or a pretext for product pushing. (`exchange_3.persona`)
- Said: She would allow access to holdings, product type, cost basis, approximate market value, and trade dates for portfolio analysis, but does not want unrelated banking data like spending, salary, or other irrelevant transactions; she wants itemized consent, retention clarity, and disclosure about marketing use. (`exchange_4.persona`)
- Said: If the tool says her allocation is off, she would not make a big move immediately; she first wants to distinguish short-term volatility from a real overweight and then consider small practical actions. Vague explanations reduce the chance she will follow the guidance. (`exchange_5.persona`)
- Said: She prefers the feature to appear when she is already in the investment overview or after a statement is issued, especially when there has been a meaningful change; she does not want random push notifications. (`exchange_6.persona`)
- Said: For regular use, it must remove the need to manually piece together data, explain why a prompt is appearing, use plain-language risk explanations, and let her quickly adjust or ignore. (`exchange_7.persona`)
- Said: If an asset class is overweight, she wants quantified context, comparison to target or usual level, and a few concrete next-step options without immediate product pushing. She also wants to understand the risk of doing nothing. (`exchange_8.persona`)
- Seemed to optimize for: Practical control with low-friction visibility: enough consolidated insight to prevent careless mistakes, without surrendering judgment, privacy, or attention to a sales-driven workflow.
- Implicit: Whether her current portfolio is mostly simple or spread across many institutions/products.
- Implicit: How often she would realistically review a health check in calm markets versus stress periods.
- Implicit: What level of explanation would feel 'plain enough' before she trusts the risk model.
- Implicit: Whether past negative experiences with sales-led banking advice are shaping her skepticism, though the transcript strongly suggests some learned caution.

## Likely Drivers

- [high] She uses review moments as preventive checks when ordinary-life cash obligations make downside feel concrete. (daily_constraint, mixed)
  Why: Her trigger was not abstract interest in investing; it was a budget-relevant moment where school fees and volatile news made allocation mistakes feel costly. That helps explain why she frames the feature around avoiding unpleasant surprises rather than maximizing returns.
  Transcript refs: exchange_1.persona
  Profile refs: values.core_values, values.fears, pricing_logic.what_makes_price_feel_fair, discovery_path.trial_trigger
- [high] She is highly sensitive to fragmentation because her attention is already split across many short mobile sessions. (daily_constraint, mixed)
  Why: Her strongest positive reaction is about not having to piece data together across apps, notes, WhatsApp, and statements. This fits a life where even useful tasks get delayed when they require stitching context across sources.
  Transcript refs: exchange_2.persona, exchange_3.persona, exchange_7.persona
  Profile refs: current_context, discovery_path.phone_use_pattern, human_difference_axes.fragmentation_reality, life_story.current_daily_routine
- [high] She follows a trust-by-proof pattern: immediate utility does not remove the need for method, scope, and motive transparency. (trust_pattern, mostly_observed)
  Why: Even when she says the feature sounds useful, her next questions are how risk is calculated, whether other accounts are included, whether it is truly free, and whether it is really a sales funnel. That is consistent with operational trust rather than brand-level trust.
  Transcript refs: exchange_3.persona, exchange_5.persona, exchange_8.persona
  Profile refs: values.trust_requirements, personality_belief.trust_orientation, human_difference_axes.trust_style, product_reaction_rules.first_checks
- [high] She wants bounded data sharing: relevant portfolio data is acceptable, unrelated behavioral or banking data is not. (core_value, mixed)
  Why: Her permission boundary is precise rather than absolute. She accepts data needed for the stated job, but rejects broader collection and wants granular consent, retention clarity, and limits on downstream use. That precision is a stable privacy logic, not a one-off objection.
  Transcript refs: exchange_4.persona
  Profile refs: technology_attitude.privacy_concern, contradiction_map, human_difference_axes.control_preference, product_reaction_rules.questions_they_would_ask
- [high] She resists automation that jumps from diagnosis to action; she prefers guided judgment with low-pressure options. (decision_style, mixed)
  Why: When told a category is overweight, she does not want an automatic strong recommendation or product pitch. She wants quantified explanation, option framing, and space to choose smaller actions or wait. That reflects a sequential, judgment-preserving decision style.
  Transcript refs: exchange_5.persona, exchange_8.persona
  Profile refs: personality_belief.decision_style, technology_attitude.automation_openness, human_difference_axes.control_preference, contradictions
- [medium] She is especially alert to hidden commercial intent because 'free' loses value if it creates pressure or cleanup work. (emotional_protection, mixed)
  Why: Her skepticism about whether free is really free and whether data will be used for marketing suggests a defensive filter against workflows that begin as service and end as sales pressure. That likely protects both time and dignity.
  Transcript refs: exchange_3.persona, exchange_4.persona, exchange_8.persona
  Profile refs: values.fears, behavior_profile.decision_blockers, childhood_environment.ordinary_childhood_scenes, deep_research_notes.trust_pattern
- [high] She needs prompts to be situationally justified, not constantly present, because interruption cost is part of product value. (daily_constraint, mixed)
  Why: She does not reject reminders outright; she rejects reminders without a clear reason. That matches a life where many systems already demand attention, so notification discipline becomes part of trust.
  Transcript refs: exchange_6.persona, exchange_7.persona
  Profile refs: life_story.frustrations, human_difference_axes.life_load, discovery_path.phone_use_pattern, product_reaction_rules.positive_signals

## Unspoken Constraints

- [high] The feature likely has to work in a very short mobile session, possibly during commute or between tasks.
  Why likely: She explicitly describes checking on the MTR and repeatedly emphasizes quick visibility, short prompts, and reduced assembly work.
- [high] She may not trust outputs that cannot distinguish temporary market moves from structural allocation drift.
  Why likely: Her next-step logic depends on whether the issue is short-term fluctuation versus real overweight, so a coarse alert would fail her decision process.
- [medium] A useful experience probably needs to respect existing mental categories such as 'long hold' versus 'cash-adjacent' money.
  Why likely: She already tracks holdings partly by intended role, not just product label. If the health check ignores that framing, it may feel mismatched to how she actually thinks about the portfolio.
- [medium] She may delay adoption if account-linking looks like a one-time admin burden with uncertain payoff.
  Why likely: She likes one narrow use case first and is sensitive to setup friction, especially when value is not immediate.

## Value Tensions

- [high] Convenience versus suspicion of convenience-led selling: She wants one place to see portfolio concentration and risk without manual stitching. vs She immediately questions whether the free tool is really a lead-in to product pushing.
- [high] Control versus low-maintenance usage: She wants granular permissions, quantified explanations, editable responses, and the option to ignore. vs She does not want to keep babysitting the system or tune it constantly; it should already be useful when opened.
- [high] Caution versus desire to avoid preventable mistakes: She will not react impulsively to a risk flag and wants to verify whether the issue is real. vs She still seeks tools that help her catch drift before needing money or discovering a problem too late.
- [high] Privacy protection versus willingness to share for clear utility: She rejects unrelated banking-data access and wants clear limits on retention and marketing use. vs She is willing to share specific holdings and transaction-related portfolio data when the purpose is obvious.

## Missed Follow-Up Questions

- [high] When you say a risk explanation needs to be '白話', what is the minimum version that would feel clear enough for you to act on?
  Why: This would distinguish whether she needs simple category-level summaries, scenario examples, benchmark comparisons, or explicit recommended thresholds.
- [high] Have you had a past experience where a 'free' banking tool or advisor flow turned into product pressure, or is this more a general concern?
  Why: It would separate a stable trust pattern from a specific learned scar, which changes how deeply embedded the skepticism is.
- [medium] If the health check showed all your holdings but could not include assets at another bank immediately, would that still be useful enough to revisit, or would it feel incomplete?
  Why: This would clarify the threshold for partial utility versus the need for full aggregation before habit formation.
- [high] How do you currently decide what counts as 'too偏' in your allocation if you do not have a formal target?
  Why: Her answer would reveal whether she relies on rough intuition, prior advice, product roles, or informal rules of thumb, which strongly affects interpretation needs.
- [medium] What kind of reminder wording would feel helpful rather than pushy when there is a meaningful change?
  Why: She clearly cares about timing and rationale of prompts; this would make the trigger and message standard more concrete.
