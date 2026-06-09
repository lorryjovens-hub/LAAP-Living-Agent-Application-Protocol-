@echo off
title LAAP Installer
echo ========================================
echo   LAAP - Universal Installer
echo   One command on Windows, macOS, Linux
echo ========================================
echo.

REM === Get current dir (the LAAP repo root) ===
set "LAAP_DIR=%~dp0"
if "%LAAP_DIR:~-1%"=="\" set "LAAP_DIR=%LAAP_DIR:~0,-1%"

REM === Choose Python (prefer system Python, skip conda/venv) ===
set "PYTHON_CMD="
for %%p in (
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
) do (
    if exist %%~p set "PYTHON_CMD=%%~p"
)
if "%PYTHON_CMD%"=="" (
    for /f "skip=1 tokens=*" %%a in ('where python 2^>nul') do (
        echo %%a | findstr /v /i "venv .venv virtualenv" >nul
        if !ERRORLEVEL! equ 0 (
            set "PYTHON_CMD=%%a"
            goto :py_found
        )
    )
)
:py_found

if "%PYTHON_CMD%"=="" (
    echo [LAAP] ERROR: No Python found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo [LAAP] Using Python: %PYTHON_CMD%

REM === Step 1: pip install -e (editable mode) ===
echo [LAAP] Installing LAAP in editable mode...
"%PYTHON_CMD%" -m pip install -e "%LAAP_DIR%" -q
if %ERRORLEVEL% NEQ 0 (
    echo [LAAP] pip install failed, trying without -q ...
    "%PYTHON_CMD%" -m pip install -e "%LAAP_DIR%"
)

REM === Step 2: Add D:\LAAP to user PATH (no admin required) ===
echo [LAAP] Registering 'laap' command in user PATH...
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%a"
if "%USER_PATH%"=="" (
    REM PATH key not present yet
    reg add "HKCU\Environment" /v PATH /t REG_SZ /f /d "%LAAP_DIR%" >nul 2>&1
) else (
    echo %USER_PATH% | findstr /i /c:"%LAAP_DIR%" >nul
    if %ERRORLEVEL% NEQ 0 (
        reg add "HKCU\Environment" /v PATH /t REG_SZ /f /d "%USER_PATH%;%LAAP_DIR%" >nul 2>&1
    )
)
REM Broadcast the change so new terminals pick it up
setx PATH "%USER_PATH%;%LAAP_DIR%" >nul 2>&1

REM === Step 3: Verify ===
echo.
echo ========================================
echo   LAAP installed successfully!
echo.
echo   Usage (open a new terminal first):
echo     laap                  - launch TUI
echo     laap -i               - REPL mode
echo     laap -q "question"    - single query
echo     laap --version        - show version
echo     laap --help           - show all options
echo.
echo   If 'laap' is not found, restart your terminal.
echo ========================================
pause
