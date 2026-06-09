@echo off
title LAAP - Digital Lifeform
setlocal enabledelayedexpansion

REM === LAAP ULTIMATE LAUNCHER ===
REM Force system Python (NOT venv Python)
set "LAAP_DIR=%~dp0"
set "LOG_FILE=%USERPROFILE%\.laap\logs\launcher.log"

REM Make sure log dir exists
if not exist "%USERPROFILE%\.laap\logs\" mkdir "%USERPROFILE%\.laap\logs\"

REM === FIND SYSTEM PYTHON (skip conda/venv) ===
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

REM === FALLBACK: find any python NOT in a venv ===
if "%PYTHON_CMD%"=="" (
    for /f "skip=1 tokens=*" %%a in ('where python 2^>nul') do (
        echo %%a | findstr /v /i "venv .venv virtualenv" >nul
        if !ERRORLEVEL! equ 0 (
            set "PYTHON_CMD=%%a"
            goto :found
        )
    )
)
:found

REM === VERIFY ===
if "%PYTHON_CMD%"=="" (
    echo [LAAP] ========================================
    echo [LAAP] ERROR: No Python found!
    echo [LAAP] Install Python 3.10+ from https://python.org
    echo [LAAP] ========================================
    echo %date% %time% [FATAL] No Python found >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo [LAAP] Using: %PYTHON_CMD%
echo %date% %time% [LAUNCH] %PYTHON_CMD% >> "%LOG_FILE%"

REM === TEST PYTHON ===
"%PYTHON_CMD%" --version >nul 2>&1
if errorlevel 1 (
    echo [LAAP] ERROR: Python failed: %PYTHON_CMD%
    pause
    exit /b 1
)

REM === LAUNCH ===
echo %date% %time% [EXEC] "%PYTHON_CMD%" "%LAAP_DIR%laap.py" %* >> "%LOG_FILE%"
"%PYTHON_CMD%" "%LAAP_DIR%laap.py" %*
set EXIT_CODE=%ERRORLEVEL%

echo %date% %time% [EXIT] code=%EXIT_CODE% >> "%LOG_FILE%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo [LAAP] ========================================
    echo [LAAP] Exited with code %EXIT_CODE%
    echo [LAAP] Log: %LOG_FILE%
    echo [LAAP] ========================================
    timeout /t 5
)

exit /b %EXIT_CODE%
