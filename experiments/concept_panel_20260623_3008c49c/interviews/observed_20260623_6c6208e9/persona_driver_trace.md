# Persona Driver Trace: Wong Mei Lin

> 呢份分析只根據合成角色資料同訪談逐字內容整理，唔係真人市場證據，亦唔可以代替真人研究。

Research goal: Understand how unfinished V5 Hong Kong retail-banking personas currently manage investment portfolios, which Aladdin-based analytics functions would materially help them in real decisions, why those functions matter, and how each should be embedded into retail customer journeys without turning the experience into generic product selling.

## Surface Read

- Said: 佢最近一次主動睇投資組合係上個月尾，情境係交學校費同對帳單時順手檢查資產擺位有冇太偏，同基金有冇跌多過預期。
- Said: 佢平時主要用銀行 app 總覽頁快速掃一次，再按入個別持倉頁；唔會做成套分析。
- Said: 對免費 `Portfolio Health Check` 第一反應係『有啲用』，因為可以省時間，但佢會即刻追問判斷方法。
- Said: 如果系統話風險高，佢要見到具體原因，例如集中喺邊個市場、行業，或者波動大，仲想有比例同一般分散做法嘅對比。
- Said: 見到風險提示後，佢唔會即刻買賣，而係先核實集中程度、來源，同埋分辨係短期波動定真係擺位太偏。
- Said: 佢想呢類總覽直接放喺投資總覽頁，或者月尾對戶口時以細提醒出現，而唔係額外彈窗打斷。
- Said: 月度提醒如果想令佢持續再睇，至少要指出今個月相對上月有咩具體變化，同點解而家值得睇。
- Said: 遇到複雜風險變化時，佢想先自己喺 app 睇明，之後先接受有人跟進，但唔想一開始有被 sales 追住嘅感覺。
- Seemed to optimize for: 用最短時間得到可核實、可解釋、唔帶推銷壓力嘅風險總覽，方便喺月尾對帳呢類本身已存在嘅理財時刻順手判斷要唔要處理。
- Implicit: 佢冇直接講自己投資知識高低，但回答方式顯示佢想保留判斷權，而唔係交畀模型結論。
- Implicit: 佢冇直接講私隱，但對『點樣判斷』、『唔好得一句』同『唔想 sales 跟住』反映咗對黑箱同被帶節奏有戒心。
- Implicit: 佢冇直接要求交易建議，重點一直係監察、解釋同分辨『係咪真係要處理』。

## Likely Drivers

- [high] 時間碎片化下嘅『快速核實』決策模式 (daily_constraint, mixed)
  Why: 佢習慣喺對帳、交費、晚間處理瑣事時順手睇投資，所以偏好一眼可掃嘅總覽，而唔會主動做長時間分析。產品如果要佢另開流程或者深度研究，就同佢現實使用場景唔配。
  Transcript refs: exchange_1.persona, exchange_2.persona, exchange_6.persona, exchange_7.persona
  Profile refs: life_story.current_daily_routine, problem_context.active_pain_points, deep_research_notes.attention_pattern, human_difference_axes.fragmentation reality
- [high] 信任建立靠可解釋性，而唔係權威式結論 (trust_pattern, mixed)
  Why: 佢唔抗拒總覽，但對『高風險／安全』呢類黑箱式標籤明顯唔夠信任；要見到風險來源、比例比較、同一般做法差距，先會當成可用資訊。
  Transcript refs: exchange_3.persona, exchange_4.persona, exchange_7.persona, exchange_8.persona
  Profile refs: personality_belief.trust_orientation, values.core_values, values.fears, deep_research_notes.interview_strength, childhood_environment.adult_decision_links
- [high] 先保住唔犯錯，再諗優化 (decision_style, mixed)
  Why: 佢見到風險提示後唔會即刻交易，而係先拆清楚『集中咗幾多』『點解買』『係短期波動定配置失衡』。呢個反映佢主要係避免做錯，而唔係追求即時行動。
  Transcript refs: exchange_5.persona, exchange_8.persona
  Profile refs: personality_belief.decision_style, values.fears, human_difference_axes.risk_orientation, life_arc_summary
- [high] 重視控制感，但抗拒被帶去銷售流程 (emotional_protection, mixed)
  Why: 佢接受後續跟進，只限於自己先睇明、確認真係複雜之後。即係話幫助可以有，但主導權要留喺自己度；如果一開始就似 sales lead capture，信任會跌。
  Transcript refs: exchange_6.persona, exchange_8.persona
  Profile refs: values.core_values, values.fears, human_difference_axes.control preference, human_difference_axes.guidance preference, contradiction_map
- [medium] 月尾財務檢查係佢自然會進入『檢視風險』嘅觸發點 (past_experience, mixed)
  Why: 佢主動檢視投資唔係因為市場新聞，而係因為學校費、帳單、對戶口呢類家庭財務節點。即係投資檢查被併入家庭穩定管理，而唔係獨立興趣行為。
  Transcript refs: exchange_1.persona, exchange_6.persona
  Profile refs: values.aspirations, pricing_logic.what makes price feel fair, human_difference_axes.financial attention cadence, childhood_environment.money_environment

## Unspoken Constraints

- [high] 唔可以要求長時間專注閱讀或者重新學一套投資分析語言
  Why likely: 佢明講自己通常係『好快咁掃』，又想放喺現有總覽頁入面；複雜內容都要求用普通講法。
- [high] 每次提醒都要有新資訊增量，否則會被當成噪音
  Why likely: 佢特別抗拒每月都係同一段廢話，表示注意力預算好低，重複訊息會快速失效。
- [high] 分析結果要支援『自己核實』，而唔係只支援『接受建議』
  Why likely: 佢持續追問比例、來源、比較基準，同埋先自行判斷係短期波動定真失衡。
- [high] 服務嵌入方式要避免令人覺得係借風險分析做銷售轉介
  Why likely: 佢唔反對有人跟進，但前提係 app 內已經講得清楚，同埋唔想一開始被 sales 追。

## Value Tensions

- [high] 想省時間，但又唔接受過度簡化: 有個總覽可以幫佢節省自行拆風險同分散度嘅時間。 vs 如果只係一句『高風險』而冇具體內容，佢唔會信，反而覺得浪費時間。
- [high] 想有指引，但又要保留自主判斷: 佢接受 Health Check 幫佢一眼睇整體風險，亦接受真係複雜時有人跟進。 vs 佢要先自己喺 app 睇明，唔想被直接帶去買賣或銷售節奏。
- [high] 關心家庭財務穩定，但未必想將投資管理變成額外負擔: 月尾對帳時會主動睇持倉，表示佢有責任感同穩定導向。 vs 佢唔會做成套分析，只接受順手、低打擾、講重點嘅方式。

## Missed Follow-Up Questions

- [high] 你講『一般分散做法』時，你心目中想比較嘅基準係同你自己過去配置比，定同相近風險取向客戶比？
  Why: 可以分清楚佢要嘅係自我追蹤式解釋，定群體基準式解釋，直接影響 Health Check 點樣呈現比較。
- [medium] 如果個提示話風險升咗，但你最後判斷暫時唔需要郁，你會唔會想 app 幫你標記『下次再睇』，定你只想自己記住？
  Why: 可以驗證佢對後續行動支援嘅接受程度，分辨佢要資訊型工具定輕量管理型工具。
- [high] 你話唔想似被 sales 追住，如果一定要有人跟進，咩形式會令你覺得舒服啲？
  Why: 可以更準確劃出信任邊界，知道通知、預約、聊天、RM 跟進之間邊條線先會觸發抗拒。
