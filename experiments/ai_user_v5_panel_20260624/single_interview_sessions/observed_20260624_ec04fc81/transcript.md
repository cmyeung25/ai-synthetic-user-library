# Facilitated Interview: Janice Wong

> Synthetic-user interview for AI pre-validation only; not human market evidence.

Interview mode: concept_validation
Concept: AI synthetic-user platform

Research goal: Understand how this product manager currently decides roadmap and feature priority, what evidence was missing, what stakeholder or time pressure existed, what she could defend publicly versus what still felt privately uncertain, what actual scope/sequence/priority change she made, and only after that test whether an AI synthetic-user platform fits the workflow.

Turn policy: soft 14, hard 18
Coverage complete: True

## Exchange 1

**Facilitator (warm_context / background_scope)**

你最近主要貼近邊幾類產品決定？

**Janice Wong**

最近比較貼近嘅，通常係優先次序同概念判斷。好似某個功能值唔值得排入下個 cycle、某個新流程係咪真係解到用戶卡位，仲有原型出咗之後，邊啲反應係值得再追、邊啲其實只係表面上順。

## Exchange 2

**Facilitator (role_scope / responsibility_split)**

通常呢啲 prioritization call，你自己會揹到幾多，定係多數要同 design、engineering 或 leadership 一齊拍板？

**Janice Wong**

多數唔會係我一個人拍板，但個 framing 同初步取捨通常係我要揹得比較多。去到真係影響 scope、時程或者風險比較大嗰啲，就一定要拉 design 同 engineering 一齊對，必要時再畀 leadership 定方向。

## Exchange 3

**Facilitator (recent_event / recent_event_narrowing)**

最近一次由你去做呢種初步取捨嘅 feature priority 決定，實際係邊一次？

**Janice Wong**

最近一次係有個 onboarding flow 嘅改動，要決定係咪擺一個新提示同埋精簡其中一步。當時我先睇咗 drop-off 同 support feedback，覺得問題存在，但未去到要成個 flow 重做，所以我初步係偏向揀細改、快驗證，再拎去同 design 同 engineering 對可行性。

## Exchange 4

**Facilitator (missing_evidence / threshold_probe)**

當時要去到見到咩證據，你先會覺得唔係做細改，而係要重做成個 onboarding flow？

**Janice Wong**

如果我見到個問題唔係卡喺單一步，而係成條 flow 幾個位都跌，或者 support、session replay、用戶訪談都指向同一種迷失感，我先會覺得細改唔夠。另一種係你試咗一兩輪局部修補，數字有郁但核心完成率都係冇明顯改善，咁就比較似個結構本身有問題。

## Exchange 5

**Facilitator (defensible_vs_uncertain / confidence_boundary_probe)**

嗰陣有邊啲判斷你可以好肯定咁同人講，但邊啲其實你自己仲未夠肯定？

**Janice Wong**

我會幾肯定咁講，當時個 friction 係真係存在，唔係純粹個別意見，因為 analytics 同 support feedback 都對到一啲位。 但我未夠肯定嘅係，問題到底係文案提示唔清楚，定係成個步驟設計本身令人猶豫，所以我唔會一開始就講到要大改，最多只會話值得先用細啲嘅改動去驗證。

## Exchange 6

**Facilitator (pressure / constraint_probe)**

嗰次你哋有咩時間、交付或者 stakeholder 壓力，令你傾向先做細改快驗證？

**Janice Wong**

有，因為當時已經近一個既定 release，engineering 個 bandwidth 都幾緊，唔太現實突然開成個 flow 重做。另一邊 stakeholder 又想快啲見到 onboarding completion 有冇得改善，所以我會偏向揀一啲改動細、可以較快上線同睇數嘅做法。

## Exchange 7

**Facilitator (defensible_vs_uncertain / clarification)**

去到同 design、engineering 或 stakeholder 講嗰陣，邊部分你會直接拍心口講得實，邊部分你只係自己心入面仲有保留？

**Janice Wong**

我會講得比較實嘅，係而家個 onboarding 確實有 friction，而且值得優先處理，呢個我覺得證據算夠。 但如果要我拍心口講某一個細改一定會救到 completion，或者呢個已經係最啱嘅解法，嗰啲我會有保留，我通常只會講呢個係目前成本同時機下最合理嘅試法。

## Exchange 8

**Facilitator (current_workaround / workaround_function_probe)**

喺嗰次決定入面，你實際用咗咩工具或者方法去補你未肯定嗰部分？

**Janice Wong**

主要係幾樣比較基本嘅嘢。先睇 funnel 同 drop-off，跟住翻 support ticket 同 call note，睇下大家卡住嘅位係咪一致；如果 design 有 replay 或 prototype，我都會用嚟分清楚到底係理解問題，定係 flow 本身太重。

## Exchange 9

**Facilitator (concept_introduction / neutral_concept_intro)**

如果有個 AI synthetic-user platform，俾團隊喺做真人研究前，用一批唔同背景同顧慮嘅 synthetic users 先模擬訪談同反應，你第一下會點睇？

**Janice Wong**

第一下我會覺得可以當 early framing 工具睇，尤其係你仲未排到真人訪談、但又想快啲見下有冇明顯盲點嗰陣。 但我會即刻問得幾清楚：呢啲反應係點樣生成、邊啲係有用嘅啟發、邊啲唔可以當 evidence，如果講到好似可以代替真人研究，我會幾有保留。

## Exchange 10

**Facilitator (trust_boundary / trust_source_probe)**

要去到見到咩講法或者輸出，你先會覺得呢類 synthetic 反應真係值得你拎嚟參考？

**Janice Wong**

我要見到佢唔係淨係吐一段幾似真嘅說話，而係講得出個反應背後假設係咩、基於邊類 input、同埋邊度可能會錯。 如果輸出可以同我哋已有嘅 analytics、support feedback 或之前訪談對得返一部分，另外又清楚標示佢只適合用嚟做早期假設同問題 framing，咁我會覺得有參考價值。

## Exchange 11

**Facilitator (output_to_decision_probe / output_to_decision_probe)**

如果呢個工具指出 onboarding 有一個明確迷失位，但同你而家睇到嘅 drop-off 解讀唔同，你會即刻改 priority，定係先做咩驗證？

**Janice Wong**

我唔會即刻改 priority，我會先當佢係一個要驗證嘅新假設。通常我會返去對 event、replay、support case，睇下佢指出嗰個迷失位有冇其他證據托住；如果冇，我最多係調整下一輪想驗證嘅方向，未去到直接改 roadmap。

## Exchange 12

**Facilitator (retention_boundary / contrast_probe)**

如果你試過一兩次之後都唔再開返呢類工具，通常會係因為咩情況？

**Janice Wong**

通常係兩種情況。 一係佢每次都講到好似有道理，但最後都要我自己花好多時間再驗證，咁佢就只係多咗一層工作；二係佢啲輸出開始好似幾順，但其實好 generic，拎去同真實數據或者團隊討論一對，就企唔住。
