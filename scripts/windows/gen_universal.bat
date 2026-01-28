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
echo 🧠 Generating Universal Smart Skeleton (Tencent Dataset)...
echo This may take a moment to download metadata and process hierarchy...

wildcards-gen dataset tencent --smart -o output/universal_skeleton.yaml

echo ✅ Done! Skeleton saved to output/universal_skeleton.yaml
pause
