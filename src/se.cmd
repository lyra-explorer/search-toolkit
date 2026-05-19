@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%..\.se\venv\Scripts\python.exe" (
    "%SCRIPT_DIR%..\.se\venv\Scripts\python.exe" "%SCRIPT_DIR%se.py" %*
) else (
    python "%SCRIPT_DIR%se.py" %*
)
