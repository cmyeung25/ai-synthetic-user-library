# AI synthetic-user platform Interview: Maggie Leung Wai-ting

> 以上只係基於本次 synthetic persona 訪談逐段內容整理嘅模擬證據，不構成人類市場驗證或採用證明。所有概念反應、信任門檻、留用與付費判斷都應視為待真人研究校準嘅暫時訊號。

## Problem Evidence

- Strength: medium
- "好多時唔係畫靚畫面，反而係將啲講得好散、好似有道理但未必站得住腳嘅 feedback，整理成真係可以判斷下一步嘅嘢。" (exchange_1.persona)
- "最後我唔係照抄「整體易用」呢類說法，而係拉返去睇邊個位開始猶豫、邊啲問題重複出現。" (exchange_2.persona)
- "如果幾個人都要自己腦補先肯行下一步，我會當呢個位唔係文案細節，而係系統未畀到足夠理由同安全感。" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: medium
- 手動將訪談重點拆成「表面評價」同「決定位卡住位」。來源：exchange_8.persona
- 回看受訪者喺關鍵步驟嘅停頓、重睇、發問同腦補內容，而唔跟從總結式正面評價。來源：exchange_2.persona, exchange_3.persona, exchange_4.persona
- review 前自己先執一次材料，避免討論畀「太順嘅說法」帶走。來源：exchange_8.persona
- 即使工具可信，仍會保留抽查；材料好亂或結論太快太乾淨時，會自己由頭再整理一次。來源：exchange_8.persona, exchange_9.persona

## Trust Boundary

- 顯示由原始輸入到結論嘅路徑。來源：exchange_6.persona
- 分開標示一致訊號、矛盾位、少數例外。來源：exchange_6.persona
- 可反查點解某個反對位重要、另一個只係表面意見。來源：exchange_6.persona
- 提供對照例子，證明唔係逢反對聲音都當高風險。來源：exchange_11.persona

## First Value

- 早啲指出邊啲位要用戶自己腦補先行得落去。來源：exchange_5.persona
- 保留分歧同反對位，而唔係整理成單一路徑故事。來源：exchange_5.persona
- 先標出互相撞嘅講法，幫佢決定之後邊啲位要自己再核對或喺真人訪談追問。來源：exchange_10.persona

## Pricing Signal

- Monthly comfort: unknown (unknown)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 一旦輸出過度平滑、缺少少數例外，佢會回到自己由頭整理。來源：exchange_9.persona
- Drop-off: 如果無法在 review 中 defend 判斷來源，平台只會停留喺內部草圖用途。來源：exchange_10.persona, exchange_11.persona
- Drop-off: 材料複雜混亂時，如工具不能保留衝突，只會削弱信任。來源：exchange_9.persona

## Assumption Validation

- [partially_supported] 呢個平台可以幫佢更早發現「表面上講得通，但去到決定位會露餡」嘅概念或 prototype 問題。
- [partially_supported] 呢個平台可以取代佢手動做嘅前期整理。
- [invalidated] 只要平台整理得夠順，佢就會信任並直接帶入 review。
- [partially_supported] 平台若能保留分歧、衝突與反對位，會較接近佢可接受嘅信任門檻。
- [unknown] 平台已具備明確付費或長期留用意向。

## Key Insights

- Because 佢最近實際係靠受訪者喺關鍵步驟嘅停頓、重睇、突然發問同腦補去判斷邊啲 feedback 值得改，而唔信『流程清楚』呢類表面評價，this persona would 優先用平台去標示決定位卡住位，而唔係收總結，unless 平台只輸出順滑結論冇行為依據。This means the product should 先對齊『決策行為證據』而非摘要美化。
- Because 佢公開 review 需要 defend 判斷來源，亦私下擔心工具會『執到好睇』變成砌故仔，this persona would 只將平台當前置 map 而唔直接帶入 review，unless 平台提供原始材料到結論嘅反查路徑、矛盾位同少數例外標示。This means the product should 把可審計證據鏈設成核心輸出，而唔係附加功能。
- Because 佢而家成日要手動先拆『表面評價』同『決定位卡住位』，而呢步對討論方向有實際影響，this persona would 接受平台減少一次前期整理工作，unless 材料中英夾雜、持份者講法互撞而平台只係幫手收順。This means the product should 先專注做亂料整理與衝突標記，而唔好假設可以端到端代替 synthesis。
- Because 佢明確保留反對位、少數例外同對照案例作為信任條件，this persona would 對任何『一致結論』保持懷疑，unless 平台同時證明自己唔會把所有反對聲音都升格成高風險。This means the product should 加入反例對照與風險分級邏輯，避免把 dissent 變成另一種過度簡化。

## Next Experiment

做一個最細嘅真人工作流測試：用佢最近類似嘅一組 prototype／訪談原始材料，產出兩份只限前置整理用途嘅輸出，一份由研究員手動整理，一份由平台先標示『決定位卡住位／互相撞講法／少數例外』並附反查路徑。要求佢只比較兩件事：1. 能否更快決定下一輪要追問乜；2. 有冇任何輸出因為過度平滑而令佢必須自己由頭再執。先唔測付費，亦唔直接放入正式 review。
