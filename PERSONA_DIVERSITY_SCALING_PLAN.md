# Persona Diversity Scaling Plan

## 1. 目的

本文件定義 AI Validation Swarm 如何從目前的 POC persona generator，擴展到可支援 10,000 甚至 1,000,000 級 synthetic user library 的正式 SaaS 能力。

核心目標不是單純把 persona 數量變多，而是同時做到：

- 更高變異度
- 更好分布控制
- 更低重複率
- 更強可抽樣性
- 更高可審核性

## 2. POC 與正式系統的差別

### POC 現況

- 小型 hardcoded options
- 少量 panel roles
- 方便測試與抓一致性錯誤
- 適合 50 至數百 persona 的本地驗證

### 正式系統要求

- 大型 persona catalog
- 可配置的市場分布模型
- locale-aware 生成
- 去重與相似度治理
- 可追蹤的版本與 evidence score
- 支援 10k 到 1M 級 library 的抽樣與維護

## 3. 擴展原則

1. 先擴展 seed space，再擴展 narrative
2. 先建立 distribution controls，再擴展總量
3. 先控制去重與相似度，再擴展生成速度
4. persona 數量增加時，治理能力也要同步增加

## 4. 從小枚舉到大 catalog

目前很多欄位只有幾個 options。後續應拆成多層 catalog：

### Identity catalogs

- age bands
- gender identity expression
- family structure
- household size patterns
- housing situations
- city / region / country packs
- language packs

### Work and economic catalogs

- occupation families
- occupation titles
- income bands
- spending flexibility
- purchase authority types
- employment stability
- work tooling maturity

### Behavioral catalogs

- trust styles
- adoption styles
- switching-cost patterns
- information-source patterns
- social-proof sensitivity
- privacy-risk tolerance
- app-fatigue patterns

### Life-stage catalogs

- early-career individual contributor
- middle manager
- founder / operator
- self-employed specialist
- dual-income household
- caregiver-heavy household
- pre-retirement planner

## 4A. Trait Expansion Backlog

為了支援更豐富的人切，正式系統後期應把生成基礎擴展到更多表徵維度，而不只停留在身份、收入、職業、基本行為這幾層。

以下 trait families 應納入長期 persona foundation backlog：

### Time and energy traits

- schedule fragmentation
- attention span under workload
- recovery window after work
- decision speed
- tolerance for setup time
- tolerance for learning curves

### Cognitive and decision traits

- ambiguity tolerance
- need for certainty
- tendency to procrastinate
- tendency to over-research
- impulse vs deliberation bias
- preference for human review before action

### Trust and proof traits

- proof threshold
- institutional trust
- peer-trust dependence
- brand skepticism
- trust in automation
- trust recovery after mistakes

### Financial behavior traits

- cash-flow volatility
- budgeting discipline
- trial-to-paid conversion resistance
- preference for subscription vs one-off payment
- internal ROI threshold
- spending guilt sensitivity

### Workflow maturity traits

- documentation discipline
- tool sprawl level
- current process maturity
- delegation readiness
- follow-up consistency
- tolerance for workflow change

### Communication and articulation traits

- articulation level
- directness
- conflict avoidance
- preference for written vs spoken explanation
- verbosity tolerance
- ability to describe pain clearly

### Social and influence traits

- referral sensitivity
- tendency to copy peers
- desire to look competent in front of team
- manager approval dependence
- household approval dependence
- community reputation sensitivity

### Accessibility and capability traits

- visual accessibility needs
- motor accessibility needs
- cognitive load sensitivity
- language comprehension confidence
- form-filling fatigue
- tolerance for dense interfaces

### Privacy and boundary traits

- data-sharing comfort
- sensitivity to surveillance framing
- comfort with profiling
- boundary around third-party data
- retention-policy sensitivity
- preference for local control vs cloud convenience

### Emotional and stress traits

- anxiety under uncertainty
- frustration trigger pattern
- shame around disorganization
- need for reassurance
- burnout exposure
- tolerance for incomplete outputs

### Identity and self-concept traits

- self-image as early adopter / careful buyer / practical operator
- status signaling sensitivity
- identity tied to professionalism
- identity tied to independence
- identity tied to family responsibility
- resistance to labels

### Household and care traits

- caregiving intensity
- elder-care responsibility
- childcare unpredictability
- dependence on partner coordination
- household budget negotiation style
- time ownership constraints

### Cultural and worldview traits

- taboo topic comfort
- deference to authority
- preference for harmony vs blunt truth
- risk of public embarrassment
- sensitivity to prestige cues
- comfort with assertive sales language

### Channel and media traits

- email overload level
- messaging-app dependence
- video-call fatigue
- preference for short demos vs detailed docs
- social media influence channels
- search-first vs peer-first discovery

### Product adoption posture traits

- adopter archetype
- integration appetite
- sandboxing preference
- desire for manual override
- tolerance for false positives
- tolerance for false negatives

## 4B. Multi-layer Trait Model

後期建議把 persona traits 分成幾層，而不是全部混在同一個 profile：

1. Structural traits  
年齡、地區、家庭、收入、職業、裝置環境。

2. Constraint traits  
時間壓力、照護責任、現金流壓力、工作風險、轉換成本。

3. Decision traits  
信任方式、證據門檻、購買節奏、價格敏感、審批依賴。

4. Expression traits  
表達能力、直接程度、情緒顯露、寫作與口語偏好。

5. Risk traits  
隱私敏感、政治敏感、公平意識、品牌風險感、合規警覺。

6. Contextual traits  
locale、life-stage、workflow maturity、team context、household context。

這樣後期擴容時，可以分層控制：

- 哪些 traits 用於 sampling
- 哪些 traits 用於 response style
- 哪些 traits 用於 safety audit
- 哪些 traits 只作背景，不直接驅動結論

## 5. 生成架構升級

建議升級成四層生成：

1. Distribution Planner  
定義某一 persona batch 應符合哪些市場分布與覆蓋目標。

2. Seed Generator  
依 distribution targets 生成高維 seed，而不是只做少量均勻抽樣。

3. Enrichment Generator  
基於 seed 補完 values、life story、behavior、decision logic。

4. Judge / Deduper / Auditor  
做 plausibility、safety、similarity、coverage 檢查。

## 6. 分布控制

正式系統不能只靠 random sample。應支援：

- weighted distributions
- quota-based generation
- geo-specific distributions
- panel-specific distributions
- campaign-specific distributions
- target-market overlays

例子：

- 某市場可以要求 35% budget-constrained
- 某地區可以要求語言與支付習慣按 locale pack 分布
- 某 validation run 可以要求低科技接受度佔 20%

## 7. 去重與相似度治理

當 persona library 到 10k 或 1M，最大風險之一是「表面很多人，實際很像」。

至少要做三種檢查：

### Structural similarity

檢查 seed、occupation、family、income、device、trust style 是否高度重複。

### Narrative similarity

檢查 life story、frustrations、hidden needs、decision blockers 是否只是模板換詞。

### Decision similarity

檢查 adoption style、proof requirements、rejection triggers 是否過度收斂。

系統需要定義 similarity threshold，超過就：

- merge
- reject
- rewrite
- lower generation score

## 8. Persona Quality Score

正式 persona 應加入 quality scoring，例如：

- consistency score
- plausibility score
- uniqueness score
- stereotype risk score
- audit completeness score
- panel fit score

只有達標 persona 才進入 production library。

## 9. Library Governance

大規模 library 不是一次生成完就結束。需要持續治理：

- coverage heatmap
- over-representation alerts
- under-representation alerts
- stale persona detection
- high-similarity cluster detection
- safety regression checks

應能回答：

- 哪些 persona types 太多
- 哪些 market slices 太少
- 哪些 clusters 太相似
- 哪些地區或 life stages 未被覆蓋

## 10. Sampling at Scale

當 library 很大，抽樣引擎應支援：

- fast indexed retrieval
- stratified sampling
- weighted sampling
- hybrid panel assembly
- exclusion rules
- reproducible seeded runs
- explainable sampling rationale

抽樣輸出不只要說抽了誰，還要說：

- 為何抽這些 persona
- 分布是否符合目標
- 哪些 persona 被排除
- 哪些 panel coverage 仍不足

## 11. 儲存與索引

POC 可用 JSON + SQLite。正式系統建議：

- PostgreSQL 存 metadata 與 structured traits
- object storage 存 persona artifacts
- optional vector index 存 narrative / decision embeddings
- optional similarity index for dedupe workflows

每個 persona 應有：

- stable ID
- seed version
- generation version
- audit version
- quality score
- last reviewed timestamp

## 12. Locale 與 Cultural Expansion

未來 persona diversity 不能只靠翻譯。應有 locale packs：

- language defaults
- payment habits
- device habits
- privacy expectations
- trust signals
- buying friction patterns
- social risk patterns

同一 occupation 在不同 locale，可能有不同 workflow、價格感、資訊來源與風險感。

## 13. 安全與偏差治理

library 變大後，偏差風險通常會一起變大。正式系統要避免：

- stereotype amplification
- sensitive attribute leakage into targeting
- over-generalised political profiles
- false certainty around protected groups

所以 diversity scaling 不只是擴大 variety，還包括：

- fairness audits
- sensitive-topic regression tests
- prohibited-inference checks
- human review workflows for risky clusters

## 14. 分階段路線

### Phase A: 500 Personas

- 擴大 catalog
- 加入 validator + dedupe
- 加入 basic distribution controls

### Phase B: 10,000 Personas

- batch generation pipeline
- scoring and rejection pipeline
- similarity indexing
- coverage dashboard
- expanded trait catalogs and trait-governance rules

### Phase C: 100,000 Personas

- locale packs
- market overlays
- advanced governance
- production sampling engine
- multi-layer trait distributions

### Phase D: 1,000,000 Personas

- distributed generation jobs
- large-scale dedupe and reclustering
- versioned trait catalogs
- library lifecycle management
- trait drift monitoring

## 15. 對當前 repo 的影響

目前 repo 應保留這些未來可擴展點：

- `PersonaSeed` 與 `SyntheticUser` 分離
- generator 與 validator 分離
- panel config 外置
- provider abstraction 獨立
- prompt versioning 獨立

之後應新增的核心模組：

- catalog manager
- trait taxonomy manager
- distribution planner
- persona deduper
- similarity scorer
- library governance jobs
- persona quality evaluator

## 16. 結論

POC 可以先簡單，但正式產品的 persona system 必須從一開始就預留成：

- 可擴展的 catalog system
- 可控制的 distribution system
- 可治理的 library system

否則 persona 數量上去後，只會得到大量重複而不可信的 synthetic users。
