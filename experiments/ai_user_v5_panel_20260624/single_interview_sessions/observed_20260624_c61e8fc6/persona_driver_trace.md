# Persona Driver Trace: Maggie Leung Wai-ting

> 呢份分析只係基於 synthetic persona 同訪談逐字稿嘅推論，用作 AI pre-validation，唔係真人市場證據。

Research goal: Understand how this senior UX designer currently decides roadmap and feature priority with research and prototype signals, what evidence and pressure shape those calls, what she can defend publicly versus what she privately worries about, and only after that test whether an AI synthetic-user platform fits her workflow.

## Surface Read

- Said: 佢近排主要做前期概念驗證、prototype 測試，同埋將訪談後好散嘅發現整理成可以判斷下一步嘅材料。
- Said: 佢判斷 feedback 時，唔會先信口頭上『清楚』『易用』，而係睇用戶去到邊一刻停低、重睇、開始自己補故事先敢繼續。
- Said: 如果幾個人都要自己腦補先行到下一步，佢會視為系統未提供足夠理由同安全感，屬於值得改嘅決定位問題。
- Said: 對 synthetic users 平台，佢第一下最想試係可唔可以提早指出表面講得通、但去到決定位會露餡嘅概念或 prototype。
- Said: 佢要見到由原始輸入去到結論嘅反查路徑，包括一致訊號、矛盾、少數例外，先會信平台唔係砌故仔。
- Said: 如果平台可信，佢會用嚟減少自己手動做『表面評價』同『決定位卡住位』嘅初步拆解，但仍然會保留抽查。
- Said: 如果結論太快變得乾淨，或者反對位、少數例外消失，尤其材料本身又亂，佢仍然會自己由頭整理。
- Said: 要直接拎入 review，平台除咗標衝突，仲要畀到清楚證據路徑同對照例子，證明唔係逢反對都當高風險。
- Seemed to optimize for: 佢明顯係喺優化『可防守嘅判斷質素』，唔係單純追求整理速度；重點係保留矛盾、分清表面說法同決定行為，令 research signal 喺 review 壓力下都站得住腳。
- Implicit: 佢好在意自己喺 review 入面要講得出判斷點樣嚟，背後有 reputational risk，但訪談入面冇直接講出口。
- Implicit: 佢對工具嘅接受門檻，其實唔只係準唔準，仲包括會唔會令自己變成永久 cleanup layer。
- Implicit: 佢對『乾淨得太快』特別敏感，反映佢預設 smooth synthesis 可能掩蓋咗真實摩擦。

## Likely Drivers

- [high] 將『行為證據』放喺『口頭評價』之前 (core_value, mixed)
  Why: 所以佢一路都用停頓、重睇、自己補故事呢啲行為訊號去定義問題，而唔係畀『清楚』『易用』呢類表面描述帶走。呢個直接解釋咗佢點解會對 synthetic 平台最在意能否捉到決定位露餡。
  Transcript refs: exchange_2.persona, exchange_3.persona, exchange_4.persona, exchange_5.persona
  Profile refs: values.core_values, problem_context.active_pain_points, personality_belief.trust_orientation
- [high] 對可追溯性同 audit trail 有高要求 (trust_pattern, mostly_observed)
  Why: 佢唔係只想要一個結論，而係要 review 入面都 defend 到個結論點嚟，所以多次要求反查路徑、一致訊號、少數意見、對照例子。
  Transcript refs: exchange_6.persona, exchange_10.persona, exchange_11.persona
  Profile refs: values.trust_requirements, behavior_profile.decision_blockers, product_reaction_rules.first_checks
- [high] 長期做 messy synthesis，形成咗對『太順』輸出嘅戒心 (past_experience, mixed)
  Why: 佢日常已經成日要將散亂 input 改寫成 testable decision，亦見慣團隊俾好聽說法帶走，所以一見到平台結論太乾淨，就會直覺懷疑有冇 flatten 咗衝突。
  Transcript refs: exchange_1.persona, exchange_8.persona, exchange_9.persona
  Profile refs: life_story.current_daily_routine, life_story.frustrations, deep_research_notes.attention_pattern
- [high] 願意試新工具，但只接受 bounded trial (decision_style, mixed)
  Why: 佢唔係全盤拒絕 AI，反而好快指出一個前置 map 嘅使用位；但同時又劃清界線，暫時唔會直接拎入 review。即係 curiosity 同 adoption threshold 係分開嘅。
  Transcript refs: exchange_5.persona, exchange_8.persona, exchange_10.persona, exchange_11.persona
  Profile refs: values.adoption_style, personality_belief.risk_tolerance, product_reaction_rules.difference_between_curiosity_and_purchase
- [medium] 有限注意力同高工作碎片化，令佢想減少重覆整理，但唔會放棄抽查 (daily_constraint, mixed)
  Why: 佢講到如果平台可信，可以少做一次手動初步整理，表示佢真係有 rework 壓力；但仍然保留抽查，反映效率永遠次於 credibility。
  Transcript refs: exchange_8.persona, exchange_10.persona
  Profile refs: life_story.current_daily_routine, human_difference_axes.life_load, human_difference_axes.fragmentation_reality
- [medium] 避免喺團隊面前用薄弱證據做判斷 (emotional_protection, mostly_inferred)
  Why: 佢對『review 入面畀人問到都講得出』講得好具體，顯示唔單止係分析偏好，仲有一層自我保護: 唔想用一個站唔住腳嘅結論公開背書。
  Transcript refs: exchange_6.persona, exchange_11.persona
  Profile refs: values.fears, problem_context.active_pain_points, behavior_profile.buying_behavior

## Unspoken Constraints

- [high] 工具輸出唔可以增加佢嘅 cleanup 負擔
  Why likely: 佢接受平台做前置 map，但如果最後都要自己由頭執，價值就會大減；呢個限制雖然冇直接講成一句原則，但喺使用邊界度好明顯。
- [high] 材料一亂、語境一撞，佢對自動整理嘅容忍度會即刻下降
  Why likely: 佢特別點名中英夾雜、持份者講法互撞，表示真實工作環境嘅 messy context 係 adoption gate，而唔係邊角情況。
- [high] 平台要幫佢保留 minority / contradiction，而唔係只產出可講故事嘅共識
  Why likely: 佢重覆要求少數例外、反對位、衝突保留，代表如果系統天然偏向平均化，佢會視為核心失真。

## Value Tensions

- [high] 效率 vs 證據可防守性: 佢想少做一次手動初步整理，減少重覆勞動。 vs 只要結論太順、材料太亂、反對位消失，佢就寧願自己由頭核對。
- [high] 開放試 AI vs 反感 AI 過度流暢: 佢一聽到 synthetic users 已經講到清楚試用場景。 vs 但一旦輸出似砌故仔、太快變乾淨，信任會即刻抽走。
- [medium] 合作導向 vs 個人最終把關: 佢想平台幫 review 前整理，支援團隊判斷。 vs 但未去到可直接背書前，佢仍然要自己抽查甚至重做，避免團隊被太順嘅說法帶走。

## Missed Follow-Up Questions

- [high] 你講到『review 入面畀人問到都講得出』，通常邊類 stakeholder 會最常挑戰你個判斷？佢哋會用咩方式逼到你要再補證據？
  Why: 可以分清楚佢而家要求 audit trail，主要係研究方法上嘅原則，定其實係被特定組織壓力塑造出嚟嘅防守需求。
- [high] 有冇一次你原本覺得某個反對位好重要，但之後發現只係表面 noise？你最後靠咩分辨？
  Why: 可以更具體拆出佢點樣判斷 minority signal 同 false alarm，呢個係 synthetic 平台最需要對齊嘅 decision rule。
- [medium] 如果平台畀到完整反查路徑，但初步判斷同你自己直覺唔同，你通常會先懷疑邊一邊？
  Why: 可以測到佢對工具與自我判斷之間嘅校準方式，亦即真正 adoption 天花板喺邊。
