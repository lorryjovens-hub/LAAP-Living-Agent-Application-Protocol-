@echo off
chcp 65001 >nul 2>&1
echo === Working dir: %CD% ===
echo === Test 1: where laap ===
where laap
echo.
echo === Test 2: laap --version ===
call laap --version
echo.
echo === Done ===
