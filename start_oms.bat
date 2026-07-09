@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "OMS_HOST=127.0.0.1"
set "OMS_PORT=8787"

if not exist "%PYTHON%" (
  echo [OMS] Bundled Python not found:
  echo %PYTHON%
  echo [OMS] Cannot start without bundled Python.
  exit /b 1
)

set "PYTHONPATH=%ROOT%"
set "OMS_LOCAL_OWNER_ACCESS_ENABLED=1"
set "OMS_LOCAL_OWNER_USER_ID=a2c82cb4"

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -State Listen -LocalPort %OMS_PORT% -ErrorAction SilentlyContinue) { exit 0 } exit 1" >nul 2>nul
if "%ERRORLEVEL%"=="0" (
  echo [OMS] OMS API is already listening on http://%OMS_HOST%:%OMS_PORT%/
  start "" "http://%OMS_HOST%:%OMS_PORT%/"
  endlocal
  exit /b 0
)

echo [OMS] Starting OMS API with bundled Python...
echo [OMS] URL: http://%OMS_HOST%:%OMS_PORT%/
echo [OMS] Python: %PYTHON%

start "OMS V1.0 API" /D "%ROOT%" "%PYTHON%" -m oms_v1.feishu_auth_server --host %OMS_HOST% --port %OMS_PORT%

timeout /t 2 >nul
start "" "http://%OMS_HOST%:%OMS_PORT%/"

endlocal
