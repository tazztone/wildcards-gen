@echo off
setlocal enabledelayedexpansion

:: Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
:: Project root is two levels up from scripts\windows\
set "ROOT_DIR=%SCRIPT_DIR%..\.."

cd /d "%ROOT_DIR%"

echo 🚀 Starting installation of wildcards-gen...

:: Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✨ uv found! Using uv for faster installation.
    uv venv .venv
    call .venv\Scripts\activate.bat
    uv pip install -e .
) else (
    echo 🐍 uv not found. Falling back to standard venv/pip.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -e .
)

echo.
echo ✅ Installation complete!
echo -----------------------------------------------
echo To use wildcards-gen, always activate your venv first:
echo .venv\Scripts\activate
echo.
echo Then you can run commands like:
echo wildcards-gen --help
echo wildcards-gen gui
echo -----------------------------------------------
pause
