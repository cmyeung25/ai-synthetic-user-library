# Suggested Folder Structure

```text
.
├─ PRODUCT_BRIEF.md
├─ HARNESS_ENGINEERING_PLAN.md
├─ SYSTEM_ARCHITECTURE.md
├─ POC_SCOPE.md
├─ DATA_MODEL.md
├─ AGENT_WORKFLOW.md
├─ SAFETY_AND_SENSITIVE_TOPIC_POLICY.md
├─ EVALUATION_PLAN.md
├─ DEVELOPMENT_ROADMAP.md
├─ SUGGESTED_FOLDER_STRUCTURE.md
├─ HUMAN_SKILL_FOUNDATION.md
├─ PERSONA_DIVERSITY_SCALING_PLAN.md
├─ README.md
├─ .env.example
├─ pyproject.toml
├─ src/
│  └─ ai_validation_swarm/
│     ├─ cli/
│     ├─ config/
│     ├─ domain/
│     ├─ providers/
│     ├─ prompts/
│     │  ├─ persona-response/
│     │  ├─ skeptic-review/
│     │  ├─ sensitive-audit/
│     │  └─ report-writer/
│     ├─ personas/
│     ├─ sampling/
│     ├─ protocols/
│     ├─ orchestration/
│     ├─ reporting/
│     ├─ storage/
│     └─ evaluation/
├─ configs/
│  ├─ panels/
│  ├─ protocols/
│  └─ models/
├─ schemas/
│  ├─ synthetic-user.schema.json
│  ├─ founder-brief.schema.json
│  └─ validation-run.schema.json
├─ data/
│  ├─ personas/
│  ├─ briefs/
│  └─ sample_runs/
├─ runs/
│  └─ .gitkeep
├─ reports/
│  └─ .gitkeep
├─ tests/
│  ├─ fixtures/
│  ├─ unit/
│  ├─ integration/
│  └─ safety/
└─ scripts/
```

## 設計說明

### `src/ai_validation_swarm/domain`

放核心 model 與 business rules。  
未來 CLI 換成 API 時，這層應保持不變。

### `src/ai_validation_swarm/prompts`

所有 prompt 檔案化與版本化，不允許散落在 Python 檔案內。

### `configs/panels`

定義 `mainstream`, `skeptic`, `privacy_sensitive` 等 panel preset。

### `data/personas`

每個 persona 一個資料夾，例如：

```text
data/personas/su_0001/
├─ profile.json
├─ persona.md
└─ audit.json
```

### `runs`

每次 validation run 一個資料夾，例如：

```text
runs/run_20260617_001/
├─ brief.json
├─ panel.json
├─ selected_personas.json
├─ raw_responses.json
├─ skeptic.json
├─ audit.json
├─ summary.json
└─ report.md
```

## POC Repo 初始化優先順序

1. `pyproject.toml`
2. `src/`
3. `schemas/`
4. `configs/`
5. `data/` sample fixtures
6. `tests/`

這樣可以先建 engine，再補 sample personas 與 reports。
