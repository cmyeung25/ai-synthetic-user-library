# AI Follow-up Copilot Interview: Ethan Lee

> 以上只係單一 synthetic persona 嘅概念預驗證，能用嚟收窄假設同設計下一輪真人研究，唔可以當作真實市場證明或因果結論。

## Problem Evidence

- Strength: strong
- "我喺手機睇到佢訊息之後本來想夜晚整理再跟進...我就差啲完全漏咗。" (exchange_1.persona)
- "我通常會即刻補兩樣，先喺日曆加個短提醒，跟住直接回個客一句唔長嘅訊息。" (exchange_2.persona)
- "如果冇一個明確時間點彈出嚟，我都幾容易拖到。" (exchange_3.persona)
- "個客再追一次嗰下會有啲尷尬，因為對佢嚟講嗰個等待時間比個問題本身更明顯。" (exchange_4.persona)

## Current Workaround

- Pain: medium; switching: medium
- 喺日曆加短提醒
- 先回一個簡短確認訊息，交代幾時再詳細覆
- 刻意留住 WhatsApp 未讀
- 靠關鍵字翻舊訊息搵返線頭

## Trust Boundary

- 必須由用戶揀資料來源
- 唔可以自動發送
- 要清楚點樣判斷邊啲真係要跟進
- 如果成日捉錯，會被視為噪音而放棄

## First Value

- 第一次用就要捉到一兩件本來差啲漏咗、其實應該跟進嘅事
- 提醒或草稿可以直接用，最多少改
- 唔係只係整理得靚，而係真係避開一次真漏

## Pricing Signal

- Monthly comfort: 偏好月費、易停；未提供具體金額。 (stated)

## Retention Risk

- Workflow effect: adds_layer
- Drop-off: 新鮮感過後只剩低價值提醒
- Drop-off: 判斷錯誤太多，變成噪音
- Drop-off: 需要持續自己維持或分類
- Drop-off: 只係多一層確認而無明顯減少手動工作

## Assumption Validation

- [supported] 受訪者有 recurring follow-up 問題，而且有實際後果。
- [supported] 現有 workaround 不足，足以值得改變行為。
- [supported] 只開放揀選來源已足夠，不需要廣泛讀取私人訊息。
- [supported] review-before-action 會明顯提升信任。
- [supported] 產品可以喺第一星期內展示有意義價值。
- [partially_supported] 窄 onboarding path 可接受。
- [partially_supported] 有可信付費條件。
- [partially_supported] 產品可以取代現有一步，而唔係純粹加一層。
- [supported] 模型判斷跟進項目的準確度係最大風險。

## Key Insights

- 問題真實存在，而且唔係大災難式痛點，而係『細但尷尬』、會令客戶再追一次嘅 follow-up 遺漏。
- 現有行為唔係完全無系統；佢已有日曆提醒、未讀標記、關鍵字搜尋，所以新產品要明顯減少搜尋與整理，而唔係再加一個 inbox。
- 最大價值唔係自動發送，而係跨 WhatsApp 同電郵幫佢捉返『其實仲差我一句回覆』。
- 信任邊界好清楚：只限工作來源、自選對話、保留人工最後決定權。
- 首個價值門檻高但清晰：首次就要捉到真漏，草稿亦要可直接修改後使用。意思係 demo 漂亮無用，必須證明 recall 同 precision。','第二個月最大風險係噪音；一旦誤判多，產品會由『幫手執線』變成『另一堆提醒』。

## Next Experiment

做一個非常窄嘅真人測試：只連接 1 個工作電郵 inbox + 1 組自選客戶對話，唔讀私人來源；連續 2 星期每日只輸出『可能差一句回覆』清單同可編輯草稿，量度真正捉中率、誤報率、以及有幾多次成功取代手動翻舊訊息。
