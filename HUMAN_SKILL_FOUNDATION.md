# Human Skill Foundation

## 1. 目標

本文件定義「如何正確生成一個合理的人類作為 skill 基礎」。

核心原則：  
我們不是在創作小說人物，也不是在模仿真實個人，而是在建立一個可重複、可審查、可抽樣的 synthetic human foundation。

## 2. 什麼叫合理的人類基礎

一個合格的 synthetic human 應同時滿足五件事：

1. 內部一致  
年齡、教育、工作、收入、家庭、日常生活彼此不矛盾。

2. 有現實約束  
不是只有人格標籤，而是真的有時間、金錢、責任、風險、科技能力限制。

3. 有決策邏輯  
能解釋為什麼會買、為什麼不信、為什麼延後、為什麼在意某些問題。

4. 不依賴 stereotype  
不把性別、年齡、地區、收入、政治傾向直接寫成固定行為。

5. 可被打包成 skill  
不只是一份 profile，而是能穩定驅動後續回應與評估的行為基礎。

## 3. 正確的生成流程

### Step 1: 先定 sampling frame，不先寫人物

先定你想覆蓋的是哪個市場現實：

- 誰可能遇到這個問題
- 誰可能付錢
- 誰會反對
- 誰會因隱私、公平、政治、文化而有顧慮

這一步的產物不是 persona，而是一個 panel frame，例如：

- mainstream buyer
- budget constrained buyer
- low-tech hesitant buyer
- privacy sensitive evaluator
- skeptical switcher

### Step 2: 先抽 demographic seed

seed 只定硬條件，不急著寫故事：

- age band
- location type
- household structure
- occupation band
- income band
- education band
- language
- device / payment environment

這一步要避免兩個錯誤：

- 一開始就用完整 narrative 讓 LLM 自由發散
- 用單一社會刻板印象補完整個人

### Step 3: 補 structural constraints

這一步很重要，因為真正影響購買決策的通常不是 MBTI，而是生活約束。

至少補以下約束：

- monthly budget flexibility
- schedule pressure
- family or caregiving load
- work risk exposure
- switching cost
- trust threshold
- privacy risk tolerance
- digital literacy ceiling

沒有這一層，persona 很容易變成「會說話的形容詞」。

### Step 4: 再生成 values, life story, behavior

此時才讓 LLM 補完：

- core values
- fears
- aspirations
- recent life events
- frustrations
- hidden needs
- information sources
- buying blockers
- emotional triggers

規則是：

- 每個抽象特質都要能回扣到前面的結構條件
- 每段 life story 都要能解釋目前的 decision posture
- 不要把所有 persona 都寫得很會自我表達

## 4. 把「人」轉成 skill 的正確方法

skill 的核心不是角色口吻，而是決策規則。

一個可用的 human skill 基礎應至少包含三層：

### `profile.json`

放穩定、可查詢、可抽樣的結構化欄位。

### `persona.md`

放可閱讀的 narrative summary，但重點要包括：

- what daily reality shapes this person
- what they are trying to protect
- what they are trying to improve
- how they judge a new product
- what makes them suspicious
- what kind of proof they need

### `audit.json`

放可追溯資訊：

- generation method
- evidence grade
- stereotype risk
- frozen version
- known uncertainty
- do-not-use boundaries

## 5. 推薦的 persona generation pipeline

建議採兩段生成加一段審核：

1. Seed Builder  
先建立 deterministic seed，來源是 panel frame + random seed + quota rules。

2. Enrichment Writer  
在 seed 基礎上生成 values, life story, behavior, sensitive reality layer。

3. Persona Judge  
檢查一致性、 plausibility、stereotype risk、panel fit。

Judge 至少要問：

- 這個人的生活條件和故事有沒有矛盾
- 這個人的購買阻力是否來自合理約束
- 是否把敏感身份偷換成行為結論
- 這個 persona 是否真的和同庫其他 persona 有區別

## 6. 生成時應避免的錯法

### 錯法 1: 先寫人格標籤

例如先寫「INTJ、理性、愛科技、怕風險」。  
這通常會生成空泛且高度模板化的人。

### 錯法 2: 把敏感身份當因果

例如把地區、性別、年齡、政治傾向直接變成固定購買偏好。  
這會把 stereotype 包裝成「洞察」。

### 錯法 3: 每個 persona 都很會講自己的感受

真實世界很多人並不擅長表達。  
應保留 low-articulation、low-reflection、time-poor 的 persona。

### 錯法 4: 用太多裝飾性設定

例如大量星座、玄學、興趣、口頭禪。  
這些可作 cultural flavor，但不應主導決策模型。

### 錯法 5: 每次 run 重新生成 persona

這會造成 identity drift。  
persona 應先生成、審核、凍結，再被多次重用。

## 7. POC 階段的最低可行標準

POC 不需要一開始做 10,000 個人。  
先做 50 個高質量、可審核、可區辨的 synthetic humans，比大量鬆散人物更有價值。

每個 persona 至少要通過：

- hard consistency check
- structural plausibility check
- stereotype risk check
- panel-role clarity check
- response-boundary check

## 8. 可操作的生成公式

建議把每個 persona 的生成想成：

`Human Seed = Market Frame + Demographic Seed + Structural Constraints + Decision Logic + Narrative Compression + Safety Audit`

其中最重要的不是 narrative，而是：

- 結構約束
- 決策邏輯
- 審核與凍結

## 9. 與後續實作的關係

後續 Milestone 1 的 persona generator，應直接依這個順序實作：

1. 先寫 seed schema
2. 再寫 enrichment prompt
3. 再寫 judge prompt
4. 再輸出 `profile.json`, `persona.md`, `audit.json`

而不是一次叫模型「生一個很真實的人」。

## 10. 從 POC 到 10k / 1M Persona 的擴展原則

POC 階段可以先用較少 options，因為目標是驗證 engine。

但正式 SaaS 若要建立 10,000 甚至 1,000,000 級 synthetic user library，不能停留在目前這種小型枚舉集。後期必須加入：

1. 更大的 attribute catalogs  
例如更細的職業、收入、居住型態、語言、裝置環境、購買流程、信任偏好。

2. Weighted distributions  
不是每種 persona 等機率出現，而是按市場假設、區域、客群結構去加權。

3. Locale packs  
不同城市、國家、語言環境要有不同的 defaults、常見 constraints、支付習慣與 trust patterns。

4. Life-stage generators  
例如單身職場、雙職家庭、新手父母、資深管理者、自僱人士、退休前群體，各自會有不同決策約束。

5. Deduplication and similarity controls  
要防止大量 personas 其實只是換名字。系統應能檢查結構近似度、故事近似度、決策近似度。

6. Diversity governance  
不是盲目擴容，而是追蹤整體 persona library 的覆蓋度、偏差、過度集中與過度 stereotype 風險。

所以目前 generator 裡的少量值，應被視為：

- POC scaffolding
- testing-friendly defaults
- 不是正式 vocabulary ceiling
