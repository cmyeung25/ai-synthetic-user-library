# Portfolio Health Check Interview: Chloe Lam Tsz-yan

> 以上只係單一 synthetic persona 嘅概念驗證前測，屬模擬證據，不能當作真人市場證據或因果定論。

## Problem Evidence

- Strength: medium
- "我啲美股同基金有啲位幾重疊，但我又唔係即刻敢郁" (exchange_1.persona)
- "有時買嗰陣覺得自己分散咗，之後先發現只係用唔同包裝買返差唔多嘅嘢" (exchange_2.persona)
- "知道有問題，但未有把握自己個解法係啱" (exchange_3.persona)

## Current Workaround

- Pain: medium; switching: medium
- 用銀行 app 逐個持倉睇
- 對返之前 cap 圖做人工比較
- 用『都係美股大科技／同一主題』去粗略判斷有冇撞倉

## Trust Boundary

- 清楚寫明 read-only
- 清楚寫明會睇到啲乜同連接範圍
- 講清壓力測試假設
- 先俾用戶慢慢睇分析，再決定下一步

## First Value

- 一入去就見到邊度重疊
- 指出風險集中喺邊，例如美股科技或美元 exposure
- 壓力測試唔只顯示跌幅，仲要解釋對呢種持倉代表咩
- 唔只話風險高，而係指出可以先由邊個位開始留意

## Pricing Signal

- Monthly comfort: 未知 (stated)

## Retention Risk

- Workflow effect: replaces_workflow
- Drop-off: 產品味太重
- Drop-off: 分析太 generic
- Drop-off: 結果嚇人但冇解釋
- Drop-off: 資料接入太重手或私隱界線唔清

## Assumption Validation

- [supported] 好多客戶覺得現有銀行投資指引太 product-led，唔夠 portfolio-led。
- [partially_supported] 客戶能理解簡化版 portfolio risk、集中度、壓力測試、scenario analysis。
- [partially_supported] 機構級 analytics 經銀行交付會增加信任多過增加懷疑。
- [partially_supported] 客戶願意分享足夠 portfolio data，包括部分非本行資產。
- [partially_supported] 功能會提升行動質素或 engagement，而唔只令人更驚或更被動。
- [supported] 有實際 self-serve 或 RM-assisted interpretation 需求，而唔係被忽略。
- [supported] 至少部分客戶對 premium analytics 或 advisory support 有可信付費條件。
- [partially_supported] 概念可以被視為中立理解工具，而唔係更高級嘅 sales surface。

## Key Insights

- 核心痛點唔止係『睇唔到數據』，而係見到疑似重疊後，唔知道嚴唔嚴重同應唔應該郁。
- Whole-portfolio 價值對呢位受訪者係真實存在，但必須直接對應自己持倉，而唔係 generic 教育內容。
- 信任邊界非常清楚：read-only、假設透明、範圍透明、逐戶口控制、唔做 marketing。
- 基本 portfolio analytics 被視為 app 應有能力；收費空間喺跨戶整合同更可執行嘅深度解讀。
- 如果功能只增加警報感但冇步驟感，可能只會延續現有『知道有問題但唔敢郁』嘅狀態。

## Next Experiment

用一個低保真 prototype 測試兩種首頁輸出：A 只顯示風險分數與跌幅，B 直接顯示重疊來源、集中 exposure、假設說明同『可先留意邊個位』。觀察邊個版本更能提升信任、理解同下次使用意願。
