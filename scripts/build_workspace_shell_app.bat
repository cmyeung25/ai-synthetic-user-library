@echo off
setlocal

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "APP_DIR=%REPO_ROOT%\frontend\workspace_shell_app"

if not exist "%APP_DIR%\package.json" (
  echo Workspace shell app package manifest is missing.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm is required to build the workspace shell app.
  exit /b 1
)

pushd "%APP_DIR%"

if not exist "%APP_DIR%\node_modules" (
  echo Installing workspace shell app dependencies...
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo Failed to install workspace shell app dependencies.
    popd
    exit /b 1
  )
)

echo Building workspace shell app...
call npm run build
if errorlevel 1 (
  echo Failed to build workspace shell app.
  popd
  exit /b 1
)

popd
exit /b 0
