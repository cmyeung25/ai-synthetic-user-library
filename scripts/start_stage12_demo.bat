@echo off
setlocal

set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%"

set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

set "PYTHONPATH=src"
set "WORKSPACE_ID=ws_api_demo"
set "API_TOKEN=token-api"
set "API_HOST=127.0.0.1"
set "API_PORT=8011"
set "STATIC_PORT=4173"
set "DEMO_URL_STAGE12=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage12/index.html"
set "DEMO_URL_STAGE13=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage13/index.html"
set "DEMO_URL_STAGE14=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage14/index.html"
set "WORKSPACE_ROOT=%REPO_ROOT%\saas_runtime\workspaces\%WORKSPACE_ID%"
set "BRIEF_SRC=%REPO_ROOT%\data\briefs\sample_brief.json"
set "BRIEF_DST=%WORKSPACE_ROOT%\briefs\brief.json"
set "PERSONA_SRC=%REPO_ROOT%\data\personas"
set "PERSONA_DST=%WORKSPACE_ROOT%\personas"

echo [1/5] Bootstrapping Stage 12 demo workspace...
"%PYTHON_EXE%" -m ai_validation_swarm.cli.main bootstrap-saas-workspace ^
  --workspace-id "%WORKSPACE_ID%" ^
  --slug "ws-api-demo" ^
  --display-name "Workspace API Demo" ^
  --owner-user-id "owner_api" ^
  --api-token "%API_TOKEN%" >nul
if errorlevel 1 (
  echo Failed to bootstrap workspace.
  popd
  exit /b 1
)

echo [2/5] Syncing sample brief and personas...
if not exist "%WORKSPACE_ROOT%\briefs" mkdir "%WORKSPACE_ROOT%\briefs"
if not exist "%WORKSPACE_ROOT%\personas" mkdir "%WORKSPACE_ROOT%\personas"
copy /Y "%BRIEF_SRC%" "%BRIEF_DST%" >nul
xcopy "%PERSONA_SRC%\*" "%PERSONA_DST%\" /E /I /Y >nul

echo [3/5] Ensuring static demo server on %STATIC_PORT%...
powershell -NoProfile -Command ^
  "if (-not (Get-NetTCPConnection -LocalPort %STATIC_PORT% -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath '%PYTHON_EXE%' -WorkingDirectory '%REPO_ROOT%' -WindowStyle Hidden -ArgumentList '-m','http.server','%STATIC_PORT%' }"

echo [4/5] Restarting SaaS API on %API_PORT%...
powershell -NoProfile -Command ^
  "$env:PYTHONPATH='src'; $api = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ai_validation_swarm.cli.main serve-saas-api*' -and $_.CommandLine -like '*AI Synthetic User Library*' }; if ($api) { $api | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }; Start-Process -FilePath '%PYTHON_EXE%' -WorkingDirectory '%REPO_ROOT%' -WindowStyle Hidden -ArgumentList '-m','ai_validation_swarm.cli.main','serve-saas-api','--port','%API_PORT%'; for ($i = 0; $i -lt 20; $i++) { if (Get-NetTCPConnection -LocalPort %API_PORT% -State Listen -ErrorAction SilentlyContinue) { break }; Start-Sleep -Milliseconds 500 }"

echo [5/5] Restarting worker loop...
powershell -NoProfile -Command ^
  "$env:PYTHONPATH='src'; $worker = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ai_validation_swarm.cli.main run-saas-worker*' -and $_.CommandLine -like '*AI Synthetic User Library*' }; if ($worker) { $worker | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }; Start-Process -FilePath '%PYTHON_EXE%' -WorkingDirectory '%REPO_ROOT%' -WindowStyle Hidden -ArgumentList '-m','ai_validation_swarm.cli.main','run-saas-worker'"

echo.
echo Stage 12 demo is preparing.
echo Stage 12 URL: %DEMO_URL_STAGE12%
echo Stage 13 URL: %DEMO_URL_STAGE13%
echo Stage 14 URL: %DEMO_URL_STAGE14%
echo API base URL: http://%API_HOST%:%API_PORT%
echo Bearer token: %API_TOKEN%
echo brief_path: briefs/brief.json
echo persona_dir: personas
echo.
start "" "%DEMO_URL_STAGE14%"

popd
exit /b 0
