@echo off
setlocal enabledelayedexpansion

:: Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
:: Project root is two levels up from scripts\windows\
set "ROOT_DIR=%SCRIPT_DIR%..\.."

cd /d "%ROOT_DIR%"

if not exist ".venv" (
    echo ❌ Virtual environment (.venv) not found. Please run scripts\windows\install.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
set HF_HUB_DISABLE_PROGRESS_BARS=1
echo 🎨 Launching wildcards-gen GUI...
python -m wildcards_gen.cli gui
pause
