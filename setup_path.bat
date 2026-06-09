@echo off
REM Add LAAP to user PATH
set "LAAP_DIR=%~dp0"
setx PATH "%PATH%;%LAAP_DIR%" /M
echo ✅ LAAP added to system PATH
echo    You can now type "laap" from any directory.
echo    Restart your terminal for changes to take effect.
pause
