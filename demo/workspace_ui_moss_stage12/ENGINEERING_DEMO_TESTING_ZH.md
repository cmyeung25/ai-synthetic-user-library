# Workspace UI Engineering Demo 測試說明

## 目的

這份文件說明現時 engineering demo 應怎樣測試。

適用範圍：

- Stage 11: 純前端本地 shell flow 驗證
- Stage 12: 接上本地 SaaS API / worker 的工程型 demo 驗證

這不是 end-user 使用手冊，而是用來檢查目前 milestone 的工程成果是否成立。

## 最快開始方式

直接雙擊：

- `scripts/start_stage12_demo.bat`

它會自動做以下事情：

1. 建立 demo workspace `ws_api_demo`
2. 複製 sample brief 到 `briefs/brief.json`
3. 複製 sample personas 到 `personas/`
4. 啟動 static server `http://127.0.0.1:4173`
5. 重新啟動 SaaS API `http://127.0.0.1:8011`，確保 demo 用的是目前 repo 代碼
6. 重新啟動 worker loop，確保 queued jobs 用的是目前 repo 代碼
7. 預設自動打開 Stage 14 頁面

預設 live-mode 參數：

- `API base URL`: `http://127.0.0.1:8011`
- `Bearer token`: `token-api`
- `brief_path`: `briefs/brief.json`
- `persona_dir`: `personas`

## Demo 入口

Stage 11:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage11/index.html`

Stage 12:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage12/index.html`

Stage 14:

- `http://127.0.0.1:4173/demo/workspace_ui_moss_stage14/index.html`

## 建議測試方式

先跑一個 smoke test，再做深入檢查。

### Smoke test

1. 雙擊 `scripts/start_stage12_demo.bat`
2. 等瀏覽器打開 Stage 14
3. 保留或修改 intake panel 內的 research intent、desired output、同 first-task anchor
4. 點 `attach screenshots`
5. 當 queueability 變成 `ready for confirmation` 後，點 `confirm plan`
6. 點 `submit live job`
7. 點 `load shell snapshot`
8. 如有需要，點 `start auto refresh`
9. 等最新 job 變成 `completed` 後，再點一次 run card 或改一個 evidence query control
10. 點一張 evidence result card
11. 如果有 replay steps，就再點其中一個

預期結果：

- shell snapshot 會一次帶回真實 workspace session、selected job、同 evidence-query payload
- `Selected job` 會變成真實 job id
- shell 不再停留於 blocked state
- evidence review 會顯示 backend evidence endpoint 回來的結果
- selected evidence detail 同 replay focus 會跟住 snapshot refresh 保持一致

## 深入檢查

### 1. Stage 11: 純前端流程驗證

這一頁不依賴 live backend，主要驗證 shell flow 是否連貫。

可檢查：

1. 初始打開頁面時，是否維持 blocked draft
2. 點 `attach screenshots` 和 `set first task` 後，是否進入 `ready_for_confirmation`
3. 點 `confirm plan`、`lease worker`、`start run`、`complete run` 後，是否能走完整條 flow
4. 點 `fail run` 後是否清楚顯示失敗狀態，再用 `retry run` 回到 queue state

這一層主要在驗證：

- conversational intake -> confirmation -> run monitor -> evidence review
- frontend adapter / shell state projection 是否合理

### 2. Stage 12 sample mode

這一頁可以先在 sample mode 看 state mapping 是否正確。

建議測：

1. `blocked draft`
2. `ready for confirmation`
3. `confirmed draft`
4. `completed local shell`
5. `failed local shell`

重點：

- `submit live job` 只應在 confirmed / submittable 狀態才可按
- request JSON 應反映 `briefs/brief.json`、`personas`、family、sample size
- completed / failed 的 review surface 應有清楚差異

### 3. Stage 12 live mode

這一段才是現時 engineering demo 的主要成果。

建議測：

1. `load workspace session`
2. `submit live job`
3. `list live jobs`
4. 選一個 job，再 `load selected live job`
5. 等 worker 跑完
6. job 完成後執行 `load live evidence query`

重點：

- confirmed draft 是否真的映射成 `POST /api/v1/validation-jobs`
- live job list / detail 是否真的由 API 讀回來
- selected job 是否能反向驅動 shell run-monitor state
- evidence review 是否真的由 `GET /api/v1/evidence-query` 驅動

## 如想直接驗證 API

可以在 PowerShell 直接打：

```powershell
$headers = @{ Authorization = "Bearer token-api" }
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8011/api/v1/validation-jobs"
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8011/api/v1/evidence-query?job_id=YOUR_JOB_ID&active_family=all&sort_by=relevance"
```

預期：

- 第一個 call 會回 `jobs`
- job 完成後，第二個 call 會回 `query_status = query_ready`

## 現時應視為正常的限制

以下是現階段限制，不一定是 bug：

- Stage 11 只是本地 state demo
- Stage 12 雖然接了真實本地 API，但仍是 engineering-facing surface
- auth 仍是 demo token，未是正式 end-user session
- replay depth 仍受 run artifacts 是否有 trace-linked steps 限制
- job refresh 仍主要靠手動，不是完整 product polling experience

## 常見問題

### `ModuleNotFoundError: No module named 'ai_validation_swarm'`

原因：

- `src/` 未加入 `PYTHONPATH`

解法：

```powershell
$env:PYTHONPATH='src'
python -m ai_validation_swarm.cli.main run-saas-worker
```

或者直接用 repo 內 venv：

```powershell
.\.venv\Scripts\python.exe -m ai_validation_swarm.cli.main run-saas-worker
```

### `submit live job` 按不到

原因：

- draft 未去到 confirmed / submittable state

解法：

- 先點 `confirmed draft`

### jobs 一直停留在 queued

原因：

- worker 未啟動

解法：

- 重新執行 `scripts/start_stage12_demo.bat`

## 建議 review 重點

當你 review 這個 milestone，可以集中看六件事：

1. blocked draft 有沒有清楚指出缺什麼資料
2. confirmation-ready draft 有沒有清楚下一步
3. live job ingress 有沒有真正用到現有 API contract
4. selected live job 有沒有真正驅動 shell state
5. failure 有沒有被明確保留，而不是被 UI 蓋掉
6. evidence / replay 的現有邊界有沒有被誠實地顯示出來

如果以上六點都成立，這個 engineering demo 就達到現時 milestone 想證明的東西。
