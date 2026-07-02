# Frontline Research Studio Bilingual Terminology Glossary

Status: implemented M36 product-language contract.

Owner: platform-development-chief + platform-system-architect.

Last updated: 2026-07-02.

## Purpose

This glossary defines how Frontline Research Studio translates platform terminology for user-facing English and Traditional Chinese product chrome.

The goal is not literal word-for-word translation. The goal is consistent product language that helps users understand research objects, evidence boundaries, and next actions without learning internal API names.

## Alignment Check

- Research bottleneck improved: users need to move from research intent to plan, execution, evidence review, decision, and sharing without product terminology becoming the confusing part of the workflow.
- Primary improvements: evidence discipline, decision-quality review, and scalable research throughput.
- North-star fit: consistent terminology lowers the cost of replacing interviewer-led setup and synthesis work, while preserving the boundary between simulated evidence and human market proof.

## Translation Doctrine

User-facing `zh-Hant` product chrome should prefer Traditional Chinese terms.

Rules:

- Do not leave ordinary UI labels half English and half Chinese when a stable Chinese product term exists.
- Keep canonical English entity names in engineering specs, API contracts, database fields, audit artifacts, and code.
- If a term is a durable product object, the Chinese label should stay consistent across navigation, route titles, buttons, empty states, and boundary copy.
- If a term is a backend artifact or generated evidence content, do not translate it silently. Follow `specs/frontline_research_studio_i18n_contract.md`.
- Internal mode IDs, provider names, job IDs, runtime labels, raw payload names, and filesystem paths should remain hidden from default Frontline UI.

## Core Product Object Glossary

| Canonical English | zh-Hant Product Label | Notes |
| --- | --- | --- |
| Workspace | 工作區 | Tenancy, account, and governance context. |
| Project | 專案 | Long-lived product, idea, client, or initiative context. |
| Study | 研究 | Main user-facing research object. |
| New Study | 建立研究 | Action and route label. |
| Study home | 研究首頁 | Current study overview. |
| Study workspace | 研究工作區 | Study-context workspace, not a global dashboard. |
| Plan | 研究計劃 | User-confirmed execution basis. |
| Plan proposal | 計劃草稿 | Mutable proposal before confirmation. |
| Plan revision | 計劃版本 | Immutable confirmed plan version. |
| Confirm Plan | 確認研究計劃 | Required gate before execution. |
| Run | 研究執行 | One execution of a confirmed plan. Avoid using only `Run` in zh-Hant UI. |
| Research attempts | 研究執行紀錄 | Study-scoped run list. |
| Evidence | 證據 | Product object for inspectable evidence. |
| Evidence review | 證據檢視 | Evidence-first review surface. |
| Evidence slice | 證據片段 | A queryable evidence unit. |
| Saved Evidence View | 已儲存證據視圖 | Durable review slice. |
| Finding | 研究發現 | Synthesis claim linked to evidence. |
| Study report | 研究報告 | Study-level synthesis. |
| Decision | 決策 | Durable judgment outcome. |
| Decision log | 決策紀錄 | Durable decision artifact. |
| Share view | 分享視圖 | Boundary-preserving share page. |
| Export bundle | 匯出套件 | Packaged artifact set. |
| Privacy and export controls | 私隱及匯出控制 | Workspace/share governance surface; avoid leaving `Privacy controls` in zh-Hant UI. |
| Data residency region | 資料駐留區域 | Policy region for storage and processing boundary. |
| Retention days | 保留日數 | How long artifacts remain retained before purge/review behavior. |
| Deletion request | 刪除請求 | Governance request that preserves lineage unless explicitly destructive. |
| Redaction | 遮蔽 | Viewer-safe removal or replacement of sensitive content. |

## Research Workflow Glossary

| Canonical English | zh-Hant Product Label | Notes |
| --- | --- | --- |
| Ask | 提出問題 | Research loop step. |
| Clarify | 澄清脈絡 | Research loop step. |
| Run | 執行研究 | Verb form in the research loop. |
| Review Evidence | 檢視證據 | Research loop step. |
| Compare | 比較 | Research loop step. |
| Decide | 作出決策 | Research loop step. |
| Share With Boundary | 帶邊界分享 | Boundary-preserving distribution. |
| Research Copilot | 研究助理 | Product-facing guided setup helper. |
| Guided setup | 引導式設定 | Setup route or mode. |
| Plan tuning | 調整研究計劃 | Editable setup controls before confirmation. |
| Moderator interview guide | 訪談引導 | Planned interview structure. |
| Guide questions | 訪談問題 | Do not leave as `Guide questions` in zh-Hant UI. |
| Target audience | 目標受眾 | Who the study intends to simulate. |
| Target participant | 目標受訪者 | Participant-specific phrasing. |
| Audience criteria | 受眾條件 | Inclusion criteria. |
| Artifact | 研究素材 | Concept, prototype, copy, trace, or file used as study input. |
| Prototype | 原型 | Preserve as product design term when needed. |
| Workflow | 工作流程 | User workflow being studied. |

## Synthetic Participant Glossary

| Canonical English | zh-Hant Product Label | Notes |
| --- | --- | --- |
| Persona | 合成受訪者 | Use for ordinary simulated participants. |
| Persona Library | 合成受訪者庫 | Product picker and reusable library. |
| Synthetic participant | 合成受訪者 | Avoid `synthetic participant` in zh-Hant UI. |
| Participant panel | 受訪者組合 | Selected sample for a study. |
| Persona panel | 受訪者組合 | Product label should not expose internal implementation wording. |
| Panel type | 組合類型 | Panel categorization. |
| Sample size | 樣本數 | Number of selected participants. |
| Coverage gaps | 覆蓋缺口 | Known missing or weak coverage. |
| Simulated lens | 模擬視角 | Public-figure or expert critique lens; not participant evidence. |
| Public-figure / expert lens | 名人或專家模擬視角 | Must be labeled unaffiliated and separate from participants. |

## Evidence Boundary Glossary

| Canonical English | zh-Hant Product Label | Notes |
| --- | --- | --- |
| Synthetic evidence | 合成證據 | Must remain bounded. |
| Simulated research signal | 模擬研究訊號 | Use when reducing overclaim risk. |
| Human validation gap | 真人驗證缺口 | Keep visible before proof claims. |
| Human market proof | 真人市場證明 | Avoid implying the current system has this. |
| Market proof | 市場證明 | Usually appears as "not claimed". |
| Replacement-grade claim | 可替代真人研究級聲稱 | Only future readiness-gated language. |
| Evidence boundary | 證據邊界 | Boundary label for synthetic evidence. |
| Provenance | 來源脈絡 | Product-facing provenance wording. |
| Audit notes | 審計備註 | Product review notes. |
| Reliability | 可靠度 | Evidence reliability label. |
| Confidence boundary | 信心邊界 | Confidence limitation. |
| Trust gap | 信任缺口 | Trust-related adoption risk. |
| Adoption barrier | 採用障礙 | Adoption blocker or friction. |
| Contradiction | 矛盾 | Evidence disagreement. |
| Stable pattern | 穩定模式 | Repeated signal across runs or slices. |
| Divergent signal | 分歧訊號 | Meaningful difference across runs or slices. |

## Allowed English Exceptions

English may remain visible in `zh-Hant` product chrome only when it is:

- the product brand: `Frontline Research Studio`
- locale switcher labels: `EN`, `繁中`
- user-entered content, model-generated evidence, transcript text, report-body content, or artifact names
- technical identifiers in operator, audit, or debug contexts, not default user UI
- common source-format names that are themselves artifacts, such as a file name or URL

## Anti-Patterns

Avoid these in zh-Hant UI:

- `Study 首頁`
- `Project 清單`
- `研究 Run`
- `Evidence 工作區`
- `Plan 草稿`
- `Persona Library`
- `synthetic participant`
- `human-validation gaps`
- `Evidence 邊界`
- `Share 視圖`
- `Privacy controls`
- `Data residency`
- `Deletion request`

Preferred replacements:

- `研究首頁`
- `專案清單`
- `研究執行`
- `證據工作區`
- `研究計劃草稿`
- `合成受訪者庫`
- `合成受訪者`
- `真人驗證缺口`
- `證據邊界`
- `分享視圖`
- `私隱及匯出控制`
- `資料駐留區域`
- `刪除請求`

## Implementation Rule

`frontend/frontline_research_studio/src/i18n.js` should follow this glossary for `zh-Hant` product chrome.

If a new visible string introduces a platform term, update this glossary in the same change unless the term is already covered here.
