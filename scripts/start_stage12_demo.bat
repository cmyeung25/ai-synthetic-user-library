@echo off
setlocal

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%"

set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

set "PYTHONPATH=src"
set "WORKSPACE_ID=ws_api_demo"
set "API_TOKEN=token-api"
set "API_HOST=127.0.0.1"
set "API_PORT=8011"
set "STATIC_PORT=4173"
set "HOSTED_STAGE15_URL=http://%API_HOST%:%API_PORT%/app/workspace?token=%API_TOKEN%"
set "DEMO_URL_STAGE12=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage12/index.html"
set "DEMO_URL_STAGE13=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage13/index.html"
set "DEMO_URL_STAGE14=http://127.0.0.1:%STATIC_PORT%/demo/workspace_ui_moss_stage14/index.html"
set "DEFAULT_DEMO_URL=%HOSTED_STAGE15_URL%"
set "WORKSPACE_ROOT=%REPO_ROOT%\saas_runtime\workspaces\%WORKSPACE_ID%"
set "BRIEF_SRC=%REPO_ROOT%\data\briefs\sample_brief.json"
set "BRIEF_DST=%WORKSPACE_ROOT%\briefs\brief.json"
set "PERSONA_SRC=%REPO_ROOT%\data\personas"
set "PERSONA_DST=%WORKSPACE_ROOT%\personas"

echo [0/7] Resetting demo workspace state...
"%PYTHON_EXE%" -c "from pathlib import Path; import shutil, sqlite3; runtime_root = Path(r'%REPO_ROOT%') / 'saas_runtime'; workspace_id = 'ws_api_demo'; shutil.rmtree(runtime_root / 'workspaces' / workspace_id, ignore_errors=True); db_path = runtime_root / 'saas_runtime.sqlite3'; conn = sqlite3.connect(str(db_path)) if db_path.exists() else None; conn and conn.execute('PRAGMA foreign_keys = ON'); conn and conn.execute('DELETE FROM workspaces WHERE workspace_id = ?', (workspace_id,)); conn and conn.commit(); conn and conn.close()"
if errorlevel 1 (
  echo Failed to reset demo workspace state.
  popd
  exit /b 1
)

echo [1/7] Bootstrapping Stage 12 demo workspace...
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

echo [2/7] Syncing sample brief and personas...
if not exist "%WORKSPACE_ROOT%\briefs" mkdir "%WORKSPACE_ROOT%\briefs"
if not exist "%WORKSPACE_ROOT%\personas" mkdir "%WORKSPACE_ROOT%\personas"
copy /Y "%BRIEF_SRC%" "%BRIEF_DST%" >nul
xcopy "%PERSONA_SRC%\*" "%PERSONA_DST%\" /E /I /Y >nul

echo [3/7] Building framework-hosted workspace shell...
call "%REPO_ROOT%\scripts\build_workspace_shell_app.bat"
if errorlevel 1 (
  echo Failed to build framework-hosted workspace shell.
  popd
  exit /b 1
)

echo [4/7] Ensuring static demo server on %STATIC_PORT%...
powershell -NoProfile -Command ^
  "if (-not (Get-NetTCPConnection -LocalPort %STATIC_PORT% -State Listen -ErrorAction SilentlyContinue)) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  start "" /MIN /D "%REPO_ROOT%" "%PYTHON_EXE%" -m http.server %STATIC_PORT%
  powershell -NoProfile -Command ^
    "for ($i = 0; $i -lt 20; $i++) { if (Get-NetTCPConnection -LocalPort %STATIC_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 0 }; Start-Sleep -Milliseconds 250 }; exit 1"
  if errorlevel 1 (
    echo Failed to start static server on %STATIC_PORT%.
    popd
    exit /b 1
  )
)

echo [5/7] Restarting SaaS API on %API_PORT%...
powershell -NoProfile -Command ^
  "$api = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ai_validation_swarm.cli.main serve-saas-api*' -and $_.CommandLine -like '*AI Synthetic User Library*' }; if ($api) { $api | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }"
start "" /MIN /D "%REPO_ROOT%" "%PYTHON_EXE%" -m ai_validation_swarm.cli.main serve-saas-api --port %API_PORT%
powershell -NoProfile -Command ^
  "$headers = @{ Authorization = 'Bearer %API_TOKEN%' }; for ($i = 0; $i -lt 20; $i++) { try { $response = Invoke-WebRequest -UseBasicParsing -Headers $headers -Uri 'http://%API_HOST%:%API_PORT%/api/v1/session'; if ($response.StatusCode -eq 200) { exit 0 } } catch { }; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 (
  echo Failed to start SaaS API on %API_PORT%.
  popd
  exit /b 1
)

echo [6/7] Restarting worker loop...
powershell -NoProfile -Command ^
  "$worker = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ai_validation_swarm.cli.main run-saas-worker*' -and $_.CommandLine -like '*AI Synthetic User Library*' }; if ($worker) { $worker | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }"
start "" /MIN /D "%REPO_ROOT%" "%PYTHON_EXE%" -m ai_validation_swarm.cli.main run-saas-worker

echo [7/7] Demo workspace is ready.

echo.
echo Workspace UI engineering demo is preparing.
echo Hosted Stage 15 URL: %HOSTED_STAGE15_URL%
echo Stage 12 URL: %DEMO_URL_STAGE12%
echo Stage 13 URL: %DEMO_URL_STAGE13%
echo Stage 14 URL: %DEMO_URL_STAGE14%
echo Default opened page: %DEFAULT_DEMO_URL%
echo API base URL: http://%API_HOST%:%API_PORT%
echo Bearer token: %API_TOKEN%
echo brief_path: briefs/brief.json
echo persona_dir: personas
echo.
if /I "%NO_OPEN_BROWSER%"=="1" (
  echo Browser auto-open skipped because NO_OPEN_BROWSER=1.
) else (
  start "" "%DEFAULT_DEMO_URL%"
)

popd
exit /b 0
