@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "PYTHON=C:\Users\75859\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHONPATH=%ROOT%"
"%PYTHON%" -m oms_v1 %*
endlocal
