@echo off
REM ╔══════════════════════════════════════════════════════╗
REM ║   LAAP AGI v5.0 — Advanced Cognitive Agent         ║
REM ║   Version Management System                        ║
REM ╚══════════════════════════════════════════════════════╝
REM
REM 用法:
REM   laap                  → 显示版本信息+启动V5 (默认)
REM   laap gen1             → 启动Gen1 (原生Hermes，无LAAP)
REM   laap gen2             → 启动Gen2 (v4.5 AGI Bridge)
REM   laap gen3             → 启动Gen3 (v5.0 Full Upgrade)
REM   laap v5               → 启动V5 (同gen3)
REM   laap version          → 版本管理
REM

set LAAP_ROOT=D:\LAAP
set HERMES_LAAP=D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP

if "%1"=="version" (
    cd /d %LAAP_ROOT%
    python laap-version.py %2 %3 %4
    goto :end
)

if "%1"=="gen1" goto :gen1
if "%1"=="gen2" goto :gen2
if "%1"=="gen3" goto :gen3
if "%1"=="v5" goto :v5
if "%1"=="1" goto :gen1
if "%1"=="2" goto :gen2
if "%1"=="3" goto :gen3

REM 默认: 启动V5
echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║   LAAP AGI v5.0 — Advanced Cognitive Agent  ║
echo   ║   V4.5 + V5.0 All Modules Active            ║
echo   ║   32 Cognitive Classes | 123 Knowledge Facts ║
echo   ╚══════════════════════════════════════════════╝
echo.
echo   用法: laap [gen1^|gen2^|gen3^|v5^|version]
echo.
echo   启动 V5.0...
goto :v5

:gen1
echo.
echo   启动 GEN1: Hermes Native (原生，无LAAP增强)
echo.
cd /d "%HERMES_LAAP%"
python -m hermes
goto :end

:gen2
echo.
echo   启动 GEN2: Ao Genesis (v4.5 AGI Bridge, 18模块)
echo.
cd /d "%HERMES_LAAP%"
set LAAP_ROOT=%LAAP_ROOT%
python laap-hermes
goto :end

:gen3
:v5
echo.
echo   启动 V5.0: Advanced Cognitive Agent (全部32模块)
echo.
cd /d "%HERMES_LAAP%"
set LAAP_ROOT=%LAAP_ROOT%
python laap-hermes-v5
goto :end

:end
