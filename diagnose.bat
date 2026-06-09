@echo off
title LAAP Diagnostic
echo ========================================
echo   LAAP Environment Diagnostic
echo ========================================
echo.

echo [1/6] Checking Python...
python --version 2>&1 || echo   ERROR: Python not found in PATH

echo.
echo [2/6] Checking laap package...
python -c "import laap; print('  OK: laap', laap.__version__)" 2>&1 || echo   ERROR: laap not installed

echo.
echo [3/6] Checking dependencies...
python -c "
deps = ['numpy','httpx','textual','rich','yaml','pydantic']
for d in deps:
    try:
        __import__(d)
        print(f'  OK: {d}')
    except:
        print(f'  MISSING: {d}')
" 2>&1

echo.
echo [4/6] Checking launcher files...
if exist "%~dp0laap.py" (echo   OK: laap.py) else (echo   MISSING: laap.py)
if exist "%~dp0laap.bat" (echo   OK: laap.bat) else (echo   MISSING: laap.bat)
if exist "%~dp0laap\__init__.py" (echo   OK: laap package) else (echo   MISSING: laap package)

echo.
echo [5/6] Testing CLI...
python "%~dp0laap.py" --help >nul 2>&1 && echo   OK: laap --help || echo   ERROR: laap --help failed

echo.
echo [6/6] Checking log...
set "LOG=%USERPROFILE%\.laap\logs\launcher.log"
if exist "%LOG%" (
    echo   Last 10 lines of launcher.log:
    type "%LOG%" 2>nul | findstr /n "." | findstr /r "^[1-9]:"
) else (
    echo   No log file yet
)

echo.
echo ========================================
echo Diagnostic complete.
echo If you see any errors above, please
echo share them for support.
echo ========================================
pause
