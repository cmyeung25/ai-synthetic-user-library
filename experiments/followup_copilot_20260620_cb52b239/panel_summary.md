# AI Follow-up Copilot Synthetic Persona Panel

> This panel contains synthetic AI pre-validation only. It cannot establish market demand, pricing, prevalence, or replace interviews with real people.

- Personas: 2
- Language: Natural Cantonese Traditional Chinese
- Average interview quality: 4.0
- Problem evidence: {'medium': 1, 'strong': 1}

## Persona Results

### su_0004 - Ethan Lee

- Problem evidence: strong
- Pricing: 偏好月費、易停；未提供具體金額。 (stated)
- Workflow effect: adds_layer
- Quality: 4/5

- 問題真實存在，而且唔係大災難式痛點，而係『細但尷尬』、會令客戶再追一次嘅 follow-up 遺漏。
- 現有行為唔係完全無系統；佢已有日曆提醒、未讀標記、關鍵字搜尋，所以新產品要明顯減少搜尋與整理，而唔係再加一個 inbox。
- 最大價值唔係自動發送，而係跨 WhatsApp 同電郵幫佢捉返『其實仲差我一句回覆』。
- 信任邊界好清楚：只限工作來源、自選對話、保留人工最後決定權。
- 首個價值門檻高但清晰：首次就要捉到真漏，草稿亦要可直接修改後使用。意思係 demo 漂亮無用，必須證明 recall 同 precision。
- 第二個月最大風險係噪音；一旦誤判多，產品會由『幫手執線』變成『另一堆提醒』。

### su_0001 - Alex Chan

- Problem evidence: medium
- Pricing: 未知 (stated)
- Workflow effect: replaces_workflow
- Quality: 4/5

- 問題存在，但核心唔係『記性差』，而係亂週入面點整理、排序同補救 follow-up。
- 信任邊界比功能更前置；未講清資料範圍、可見性同退出機制，參與者會即刻停。
- 首個價值唔係自動發送，而係準確抽取承諾、辨識期限與對象，並保留人工最後審核。
- 要留到第二個月，產品必須取代現有私訊 note 同手動核對提醒，否則只係多一層管理負擔。
- 付費唔會因為清單靚，而係因為產品真係幫到一個混亂星期，同時長期維持準確度。

## Assumption Matrix

### 1. 參與者有 recurring follow-up 問題，而且有實際後果。
- Counts: {'supported': 2}
- su_0001 Alex Chan: supported - 有近期具體事件，亦講到亂週或多件急事同時出現時會影響交付同要補解釋。
- su_0004 Ethan Lee: supported - 有明確近期事件、拖延到第二日下午、客戶再追一次，屬真實 near-miss 而非純擔心。

### 2. 現有 workaround 不足以支撐高壓情境，值得改變行為。
- Counts: {'partially_supported': 1, 'supported': 1}
- su_0001 Alex Chan: partially_supported - 現有做法平時可用，但在多件急事並行時不夠分優先次序；是否足以驅動改變仍取決於新工具能否真正取代 note 同手動核對。
- su_0004 Ethan Lee: supported - 現時 workaround 存在，但一旦無明確時間點就容易拖，亦已出現客戶追問。

### 3. 只畀 selected-source access 已足夠，不需要 broad message access。
- Counts: {'supported': 2}
- su_0001 Alex Chan: supported - 參與者明確只接受窄範圍、手動選取嘅資料來源，並反對全帳戶授權。
- su_0004 Ethan Lee: supported - 明確接受工作電郵、日曆、自選客戶對話，明確拒絕私人 WhatsApp 同家庭群組。

### 4. review-before-action 會明顯提升信任。
- Counts: {'supported': 2}
- su_0001 Alex Chan: supported - 參與者反覆要求先過目，並拒絕自動改內容或發送。
- su_0004 Ethan Lee: supported - 受訪者直接表示『唔會自己發送』令佢安心，想保留最後決定權。

### 5. 產品可以喺第一星期展示有意義價值。
- Counts: {'partially_supported': 1, 'supported': 1}
- su_0001 Alex Chan: partially_supported - 第一次試用必須即時準確先唔會被放棄，但真正建立付費信心需要連續幾個星期表現。
- su_0004 Ethan Lee: supported - 佢明確要求第一次用就見到捉到一兩件差啲漏嘅事。

### 6. 窄範圍 onboarding 可接受。
- Counts: {'supported': 1, 'partially_supported': 1}
- su_0001 Alex Chan: supported - 參與者明確接受由指定 folder 或單一工作日曆逐步接入。
- su_0004 Ethan Lee: partially_supported - 接受自選來源，但只限唔需要逐個 thread 大量手動分類；窄 path 可以，但設計要再簡化。

### 7. 證明效果後有 credible willingness to pay。
- Counts: {'partially_supported': 2}
- su_0001 Alex Chan: partially_supported - 有明確付費條件，但未提供價位，亦屬概念層面的 stated evidence。
- su_0004 Ethan Lee: partially_supported - 有清楚付費前提，但屬假設性表述，未有實際價格範圍或既往付費行為支持。

### 8. 產品可以取代一步，而唔係只係再加一層。
- Counts: {'supported': 1, 'partially_supported': 1}
- su_0001 Alex Chan: supported - 參與者只會在能取代私訊 note 同手動核對提醒時留到第二個月，並指出核心問題是整理、可見性與補救，而唔係單純提醒。
- su_0004 Ethan Lee: partially_supported - 可取代『翻舊訊息搵線頭』，但日曆提醒仍會保留，所以整體仍偏向『少一輪人手搵，再加一層確認』。

## Additional Persona-Specific Risks

- su_0004 Ethan Lee: supported - 模型判斷跟進項目的準確度係最大風險。 (受訪者主動指出最唔信係分類判斷，若成日捉錯，第二個月就未必再開。)

## Next Experiments

- su_0004: 做一個非常窄嘅真人測試：只連接 1 個工作電郵 inbox + 1 組自選客戶對話，唔讀私人來源；連續 2 星期每日只輸出『可能差一句回覆』清單同可編輯草稿，量度真正捉中率、誤報率、以及有幾多次成功取代手動翻舊訊息。
- su_0001: 做一個超窄 onboarding 原型，只連單一郵箱 folder 或單一工作日曆，輸出『抽取到嘅承諾 + 期限 + 對象』清單，全部先經人工過目；測試參與者會否覺得已取代私訊 note 同手動提醒核對。
