# Data Model

## 1. 建模原則

- `SyntheticUser` 是核心實體
- canonical schema 先以 TypeScript-style type 定義，後續落地為 JSON Schema
- 敏感屬性只用於 contextualization 與 risk audit，不用於 discriminatory targeting
- 每個可執行 run 都必須有對應的 artifact model

## 2. 核心實體

- `SyntheticUser`
- `FounderBrief`
- `PanelSpec`
- `PersonaResponse`
- `AuditFinding`
- `ValidationRun`
- `ValidationReport`

## 3. SyntheticUser 正式型別草稿

```ts
type EvidenceGrade =
  | "synthetic_seeded"
  | "synthetic_llm_enriched"
  | "synthetic_human_reviewed"
  | "evidence_augmented";

type Score1to5 = 1 | 2 | 3 | 4 | 5;

type BigFive = {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
};

type BasicIdentity = {
  synthetic_user_id: string;
  name: string;
  age: number;
  gender: string;
  location: string;
  language: string[];
  occupation: string;
  education_level: string;
  income_level: string;
  marital_status: string;
  family_structure: string;
  household_size: number;
  living_area: string;
  housing_status: string;
};

type PersonalityBelief = {
  mbti?: string;
  big_five?: BigFive;
  zodiac?: string;
  metaphysical_profile?: string;
  decision_style: string;
  risk_tolerance: string;
  trust_orientation: string;
  self_image: string;
  social_comparison_tendency: string;
};

type TechnologyProfile = {
  tech_savviness: string;
  ai_familiarity: string;
  digital_payment_comfort: string;
  privacy_concern: string;
  app_fatigue: string;
  automation_openness: string;
};

type EconomicProfile = {
  disposable_income: string;
  price_sensitivity: string;
  subscription_tolerance: string;
  purchase_decision_process: string;
  current_alternatives: string[];
  switching_cost: string;
};

type ValuesProfile = {
  core_values: string[];
  life_goals: string[];
  fears: string[];
  aspirations: string[];
  identity_anchors: string[];
  moral_boundaries: string[];
  status_concerns: string[];
};

type LifeStory = {
  childhood_background: string;
  education_journey: string;
  career_path: string;
  family_story: string;
  current_daily_routine: string;
  recent_life_events: string[];
  frustrations: string[];
  hidden_needs: string[];
};

type BehaviorProfile = {
  buying_behavior: string;
  information_sources: string[];
  social_media_usage: string[];
  referral_influence: string;
  brand_trust_signals: string[];
  decision_blockers: string[];
  emotional_triggers: string[];
};

type ProblemContext = {
  active_pain_points: string[];
  latent_pain_points: string[];
  jobs_to_be_done: string[];
  current_workaround: string[];
  urgency_level: string;
  willingness_to_change: string;
  willingness_to_pay: string;
};

type SensitiveRealityLayer = {
  sensitive_identity_context: string[];
  social_risk_profile: string;
  fairness_and_inclusion_profile: string;
  taboo_topic_comfort: string;
  political_sensitivity: string;
  discrimination_awareness: string;
  public_expression_risk_aversion: string;
  identity_labeling_comfort: string;
  response_boundaries: string[];
};

type AuditEvidenceLayer = {
  persona_generation_method: string;
  evidence_grade: EvidenceGrade;
  source_basis: string[];
  stereotype_risk_score: Score1to5;
  synthetic_only_disclaimer: string;
  do_not_use_for: string[];
  last_audited_at: string;
  persona_version: string;
};

type SyntheticUser = {
  basic_identity: BasicIdentity;
  personality_belief: PersonalityBelief;
  technology_profile: TechnologyProfile;
  economic_profile: EconomicProfile;
  values: ValuesProfile;
  life_story: LifeStory;
  behavior_profile: BehaviorProfile;
  problem_context: ProblemContext;
  sensitive_reality_layer: SensitiveRealityLayer;
  audit_evidence_layer: AuditEvidenceLayer;
};
```

## 4. 其他關鍵型別

```ts
type FounderBrief = {
  brief_id: string;
  project_name: string;
  problem_statement: string;
  target_market: string;
  offered_solution: string;
  validation_goal: string;
  pricing_hypothesis?: string;
  landing_page_text?: string;
  mvp_scope?: string;
  concierge_mvp_idea?: string;
  assumptions: string[];
  constraints: string[];
  known_risks: string[];
};

type PanelSpec = {
  panel_type:
    | "mainstream"
    | "skeptic"
    | "privacy_sensitive"
    | "inclusion"
    | "political_risk"
    | "low_tech"
    | "budget_constrained"
    | "extreme_user";
  sample_size: number;
  random_seed?: number;
  filters?: Record<string, string | string[]>;
};

type PersonaResponse = {
  synthetic_user_id: string;
  protocol_id: string;
  first_impression: string;
  pain_relevance: string;
  solution_attractiveness: string;
  trust_concern: string;
  pricing_reaction: string;
  likely_objection: string;
  what_would_make_them_try: string;
  what_would_make_them_reject: string;
  sensitive_concern_if_any?: string;
  response_version: string;
};

type AuditFinding = {
  category:
    | "discrimination_risk"
    | "stereotype_risk"
    | "political_sensitivity"
    | "privacy_risk"
    | "inclusion_risk"
    | "manipulation_risk"
    | "accessibility_risk"
    | "cultural_risk"
    | "high_stakes_decision_risk"
    | "reporting_risk";
  severity: "low" | "medium" | "high";
  observation: string;
  evidence_refs: string[];
  recommended_validation_question: string;
};

type ValidationRun = {
  run_id: string;
  brief_id: string;
  panel_spec: PanelSpec;
  selected_persona_ids: string[];
  prompt_version: string;
  model_version: string;
  started_at: string;
  finished_at?: string;
  token_estimate?: number;
  cost_estimate?: number;
  status: "queued" | "running" | "completed" | "failed";
  artifact_paths: string[];
};
```

## 5. 實務規則

- `synthetic_user_id`, `brief_id`, `run_id` 必須穩定且可追溯
- 所有 array 欄位應優先用明確字串，不要塞自由格式 paragraph
- `metaphysical_profile` 只作 cultural flavor，不可當成強推論依據
- `do_not_use_for` 必須預設包含高風險決策場景

## 6. Human Skill Foundation 型別補充

為避免 persona generator 直接從空白 prompt 生成整個人，建議在 `SyntheticUser` 之前先有一層 `PersonaSeed`：

```ts
type PersonaSeed = {
  seed_id: string;
  panel_role:
    | "mainstream"
    | "skeptic"
    | "privacy_sensitive"
    | "inclusion"
    | "political_risk"
    | "low_tech"
    | "budget_constrained"
    | "extreme_user";
  age_band: string;
  location_type: string;
  household_structure: string;
  occupation_band: string;
  income_band: string;
  education_band: string;
  language: string[];
  device_environment: string;
  payment_environment: string;
  schedule_pressure: string;
  budget_flexibility: string;
  caregiving_load: string;
  trust_threshold: string;
  switching_cost_level: string;
  privacy_risk_tolerance: string;
  digital_literacy_ceiling: string;
};
```

建議實作流程是：

- `PersonaSeed` -> enrichment -> `SyntheticUser`
- `SyntheticUser` -> audit -> frozen persona skill

這樣能把「人的骨架」和「敘事補完」分開，減少人格漂移與模板化。

## 7. Persona Skill 封裝建議

POC 階段每個 persona 建議封裝成：

```ts
type PersonaSkill = {
  skill_version: string;
  profile: SyntheticUser;
  decision_policy: {
    adoption_style: string;
    trust_requirements: string[];
    rejection_triggers: string[];
    proof_requirements: string[];
  };
  response_style: {
    articulation_level: string;
    directness: string;
    detail_tendency: string;
  };
  audit: AuditEvidenceLayer;
};
```

`decision_policy` 比語氣設定更重要，因為 validation engine 主要依賴的是此人如何判斷，而不是此人如何說話。

## 8. POC 落地方式

建議儲存結構：

- `profile.json`: `SyntheticUser`
- `persona.md`: readable narrative summary
- `audit.json`: audit subset + generation metadata
- `brief.json`: normalized founder brief
- `responses.json`: persona responses
- `report.md`: final report
