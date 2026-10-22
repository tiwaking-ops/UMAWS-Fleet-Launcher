@echo off
REM start.cmd - double-click to start the UMAWS Fleet Console.
REM It calls start.ps1, which launches the app and opens the browser.
setlocal
cd /d "%~dp0"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
endlocal
