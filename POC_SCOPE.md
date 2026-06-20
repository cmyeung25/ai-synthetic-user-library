# POC Scope

## 1. Repo 現況評估

目前 workspace 沒有現成 repo，也沒有既有程式碼。  
因此最合理做法是從 Milestone 0 開始，先建立文件、資料模型與 repo structure，再進入實作。

## 2. 第一階段 POC 目標

POC 必須驗證的是 engine，不是 UI。

### 必做

- generate personas
- list personas
- sample panels
- run validation
- audit sensitive topics
- export Markdown report
- archive all run artifacts

### 不做

- web UI
- authentication
- billing
- multi-tenant
- production deployment
- CRM / review ingestion

## 3. 技術選型建議

建議第一版採用 Python：

- CLI：`argparse` 或 `typer`
- schema：Pydantic 或 JSON Schema
- storage：`data/` JSON files + SQLite metadata
- tests：`pytest`
- templating：Jinja2 或簡單 Markdown templates

## 4. 對 `colleague-skill / dot-skill` 的評估

### 適合作為靈感來源的部分

- 把 persona / skill 當成檔案化資產管理
- prompt、tools、references 分目錄管理
- Persona + Work 分層的設計思路
- host-agnostic 的內容資產觀念

### 不應直接依賴的部分

- 其主要目標是「蒸餾具體人物」而非市場驗證 persona panel
- 其資料來源與自動採集流程偏重 Feishu / Slack / 關係對象
- 其宿主整合、slash command、安裝器對本 POC 不是必要路徑
- 其 voice / character imitation 目標不等於我們需要的 synthetic user realism

### 結論

可借思想，不可借整體依賴。

POC 建議先採用 simplified skill format：

- `profile.json`
- `persona.md`
- `audit.json`

而不是先整合完整 `.skill` 生態。

## 5. 建議 CLI 指令

- `generate-personas`
- `list-personas`
- `sample-panel`
- `run-validation`
- `audit-report`
- `export-report`

## 6. 驗收標準

POC 第一輪完成時，至少要能：

1. 從 sample founder brief 讀入輸入
2. 生成或載入 20 至 50 個 persona
3. 根據 panel spec 抽樣
4. 得到每個 persona 的結構化回應
5. 產出 auditor findings
6. 產出 Markdown report
7. 在本地重跑並保存完整 artifacts
